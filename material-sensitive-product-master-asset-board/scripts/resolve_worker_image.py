#!/usr/bin/env python3
"""Resolve one v4 material worker from an exact exec artifact and full rollout."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from material_contract import (
    ATTEMPT_RE,
    MaterialContractError,
    create_only_bytes,
    inspect_image_bytes,
    load_json_file,
    load_reference_manifest,
    load_source_contract,
    normalized_path,
    pretty_json_bytes,
    read_prompt_bytes,
    render_worker_exec_bytes,
    require_exact_keys,
    require_exact_path,
    require_inside,
    require_prompt_block_once,
    sha256_bytes,
)


UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
EXEC_CALL_RE = re.compile(
    r"^exec-[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
SPAWN_KEYS = {
    "schema_version",
    "attempt_id",
    "agent_path",
    "parent_thread_id",
    "worker_spawn_not_before_ms",
    "worker_run_nonce",
    "generation_prompt_path",
    "generation_prompt_sha256",
    "reference_manifest_path",
    "reference_manifest_sha256",
    "source_contract_path",
    "source_contract_sha256",
    "prompt_block_sha256",
    "worker_exec_source_path",
    "worker_exec_source_sha256",
    "worker_exec_receipt_path",
    "worker_exec_receipt_sha256",
    "pre_spawn_state",
}
EXEC_RECEIPT_KEYS = {
    "schema_version",
    "attempt_id",
    "worker_run_nonce",
    "generation_prompt_path",
    "generation_prompt_sha256",
    "reference_manifest_path",
    "reference_manifest_sha256",
    "ordered_reference_bundle_sha256",
    "ordered_reference_paths",
    "source_contract_path",
    "source_contract_sha256",
    "prompt_block_sha256",
    "exec_source_path",
    "exec_source_sha256",
    "call_contract",
}
TOOL_OUTPUT_TYPES = {"custom_tool_call_output", "function_call_output"}


class ContractArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise MaterialContractError("blocked_worker_cli_contract", message)


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def source_agent_path(source: str) -> tuple[str | None, str | None]:
    try:
        spawn = json.loads(source)["subagent"]["thread_spawn"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None, None
    return spawn.get("agent_path"), spawn.get("parent_thread_id")


def resolve_worker_thread(
    state_db: Path,
    *,
    agent_path: str,
    not_before_ms: int,
    parent_thread_id: str,
) -> dict[str, Any]:
    if not state_db.is_file():
        raise MaterialContractError(
            "blocked_worker_state_unavailable", f"state DB not found: {state_db}"
        )
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(f"file:{state_db.as_posix()}?mode=ro", uri=True)
        rows = connection.execute(
            """
            SELECT id, rollout_path, created_at, created_at_ms, source
            FROM threads
            WHERE source LIKE ?
            """,
            (f"%{agent_path}%",),
        ).fetchall()
    except sqlite3.Error as exc:
        raise MaterialContractError("blocked_worker_state_unavailable", str(exc)) from exc
    finally:
        if connection is not None:
            connection.close()
    matches: list[dict[str, Any]] = []
    for thread_id, rollout_path, created_at, created_at_ms, source in rows:
        exact_agent_path, exact_parent = source_agent_path(source)
        created_ms = created_at_ms if created_at_ms is not None else int(created_at) * 1000
        if (
            exact_agent_path == agent_path
            and exact_parent == parent_thread_id
            and created_ms >= not_before_ms
        ):
            matches.append(
                {
                    "thread_id": thread_id,
                    "rollout_path": rollout_path,
                    "created_at_ms": created_ms,
                    "parent_thread_id": exact_parent,
                }
            )
    if not matches:
        raise MaterialContractError(
            "blocked_worker_thread_not_found",
            f"no fresh worker matched {agent_path!r} and parent {parent_thread_id!r}",
        )
    if len(matches) != 1:
        raise MaterialContractError(
            "blocked_worker_thread_ambiguous",
            f"expected one fresh worker, found {len(matches)}",
        )
    return matches[0]


def read_rollout(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise MaterialContractError(
            "blocked_worker_rollout_unavailable", f"worker rollout missing: {path}"
        )
    events: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError(f"line {line_number} is not an object")
                event["_line"] = line_number
                events.append(event)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise MaterialContractError("blocked_worker_rollout_unavailable", str(exc)) from exc
    return events


def tool_output_text(payload: dict[str, Any]) -> str:
    output = payload.get("output", "")
    if isinstance(output, str):
        return output
    if not isinstance(output, list):
        return ""
    return "".join(
        item.get("text", "")
        for item in output
        if isinstance(item, dict) and isinstance(item.get("text"), str)
    )


def response_message_text(payload: dict[str, Any]) -> str:
    content = payload.get("content", "")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "".join(
        item.get("text", "")
        for item in content
        if isinstance(item, dict) and isinstance(item.get("text"), str)
    )


def is_call_like(payload: dict[str, Any]) -> bool:
    payload_type = payload.get("type")
    if not isinstance(payload_type, str):
        return "call_id" in payload
    if payload_type in TOOL_OUTPUT_TYPES or payload_type in {
        "image_generation_begin",
        "image_generation_end",
    }:
        return False
    return payload_type.endswith("_call") or payload_type.endswith("_call_output") or (
        "call_id" in payload and payload_type not in {"message", "reasoning"}
    )


def bind_exec_transport(expected_exec_bytes: bytes, observed_exec_source: str) -> dict[str, Any]:
    """Bind a rollout exec call without mistaking one file-terminal LF for JS body drift.

    Codex rollout transport can omit the sole final LF that terminates a frozen text
    artifact.  That omission is accepted only when the frozen file uses LF (not CR),
    ends in exactly one LF, and every preceding UTF-8 byte is identical.  No general
    whitespace, newline, Unicode, or syntax normalization is permitted.
    """
    try:
        recorded_bytes = observed_exec_source.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise MaterialContractError("blocked_worker_exec_source_mismatch", str(exc)) from exc
    has_single_terminal_lf = all(
        (
            expected_exec_bytes.endswith(b"\n"),
            not expected_exec_bytes.endswith(b"\n\n"),
            b"\r" not in expected_exec_bytes,
        )
    )
    if recorded_bytes == expected_exec_bytes:
        mode = "exact"
    elif (
        has_single_terminal_lf
        and recorded_bytes == expected_exec_bytes[:-1]
        and not recorded_bytes.endswith(b"\n")
    ):
        mode = "single_terminal_lf_omitted"
    else:
        raise MaterialContractError(
            "blocked_worker_exec_source_mismatch",
            "rollout exec source differs beyond omission of the frozen file's sole terminal LF",
        )
    return {
        "frozen_exec_file_sha256": sha256_bytes(expected_exec_bytes),
        "recorded_exec_content_sha256": sha256_bytes(recorded_bytes),
        "exec_transport_mode": mode,
        "exec_body_match": True,
    }


def validate_worker_rollout(
    events: list[dict[str, Any]],
    *,
    thread_id: str,
    agent_path: str,
    parent_thread_id: str,
    expected_exec_bytes: bytes,
) -> dict[str, Any]:
    """Audit the entire rollout; an earlier task or unknown call is fatal."""
    if not events or events[0].get("type") != "session_meta":
        raise MaterialContractError("blocked_worker_session_mismatch", "missing leading session_meta")
    if sum(event.get("type") == "session_meta" for event in events) != 1:
        raise MaterialContractError("blocked_worker_session_mismatch", "rollout has multiple sessions")
    session = events[0].get("payload", {})
    if (
        not UUID_RE.fullmatch(thread_id)
        or session.get("id") != thread_id
        or session.get("agent_path") != agent_path
    ):
        raise MaterialContractError(
            "blocked_worker_session_mismatch", "session id or agent path does not match state DB"
        )
    if session.get("parent_thread_id") != parent_thread_id:
        raise MaterialContractError("blocked_worker_parent_mismatch", "session parent mismatch")

    task_starts = [
        (index, event.get("payload", {}))
        for index, event in enumerate(events)
        if event.get("type") == "event_msg"
        and event.get("payload", {}).get("type") == "task_started"
    ]
    contexts = [
        (index, event.get("payload", {}))
        for index, event in enumerate(events)
        if event.get("type") == "turn_context"
    ]
    completions = [
        (index, event.get("payload", {}))
        for index, event in enumerate(events)
        if event.get("type") == "event_msg"
        and event.get("payload", {}).get("type") == "task_complete"
    ]
    if len(task_starts) != 1 or len(contexts) != 1 or len(completions) != 1:
        raise MaterialContractError(
            "blocked_worker_task_count",
            f"entire worker rollout must contain exactly one task/context/completion; got {len(task_starts)}/{len(contexts)}/{len(completions)}",
        )
    task_index, task_start = task_starts[0]
    context_index, context = contexts[0]
    completion_index, completion = completions[0]
    turn_id = task_start.get("turn_id")
    if (
        not isinstance(turn_id, str)
        or not turn_id
        or context.get("turn_id") != turn_id
        or completion.get("turn_id") != turn_id
    ):
        raise MaterialContractError("blocked_worker_turn_mismatch", "task/context/completion turn mismatch")
    if completion.get("last_agent_message") not in {None, ""}:
        raise MaterialContractError("blocked_worker_nonempty_final", "task_complete final is non-empty")

    exec_calls: list[tuple[int, dict[str, Any]]] = []
    wait_calls: list[tuple[int, dict[str, Any]]] = []
    outputs: list[tuple[int, dict[str, Any]]] = []
    image_ends: list[tuple[int, dict[str, Any]]] = []
    agent_finals: list[tuple[int, dict[str, Any]]] = []
    response_finals: list[tuple[int, dict[str, Any]]] = []
    for index, event in enumerate(events):
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            continue
        if event.get("type") != "response_item" and is_call_like(payload):
            raise MaterialContractError(
                "blocked_worker_unexpected_tool_call",
                f"call-shaped payload appears outside response_item: {payload.get('type')!r}",
            )
        if event.get("type") == "response_item":
            payload_type = payload.get("type")
            if is_call_like(payload):
                if payload_type == "custom_tool_call" and payload.get("name") == "exec":
                    exec_calls.append((index, payload))
                elif payload_type == "function_call" and payload.get("name") == "wait":
                    wait_calls.append((index, payload))
                else:
                    raise MaterialContractError(
                        "blocked_worker_unexpected_tool_call",
                        f"unknown worker call type/name: {payload_type!r}/{payload.get('name')!r}",
                    )
            elif payload_type in TOOL_OUTPUT_TYPES:
                outputs.append((index, payload))
            if (
                payload_type == "message"
                and payload.get("role") == "assistant"
                and payload.get("phase") == "final_answer"
            ):
                response_finals.append((index, payload))
        if event.get("type") == "event_msg" and payload.get("type") == "image_generation_end":
            image_ends.append((index, payload))
        if (
            event.get("type") == "event_msg"
            and payload.get("type") == "agent_message"
            and payload.get("phase") == "final_answer"
        ):
            agent_finals.append((index, payload))

    if len(exec_calls) != 1:
        raise MaterialContractError(
            "blocked_worker_image_call_count", f"expected one exec call, found {len(exec_calls)}"
        )
    if len(image_ends) != 1:
        raise MaterialContractError(
            "blocked_worker_image_event_count", f"expected one image end, found {len(image_ends)}"
        )
    if len(agent_finals) != 1 or len(response_finals) != 1:
        raise MaterialContractError(
            "blocked_worker_final_trace_incomplete", "worker must have one event final and one response final"
        )

    call_index, exec_call = exec_calls[0]
    actual_source = exec_call.get("input")
    if not isinstance(actual_source, str):
        raise MaterialContractError("blocked_worker_exec_source_mismatch", "exec input is not text")
    exec_transport = bind_exec_transport(expected_exec_bytes, actual_source)

    exec_call_id = exec_call.get("call_id")
    if not isinstance(exec_call_id, str) or not exec_call_id:
        raise MaterialContractError("blocked_worker_task_trace_incomplete", "exec call lacks call_id")
    exec_outputs = [(index, payload) for index, payload in outputs if payload.get("call_id") == exec_call_id]
    if len(exec_outputs) != 1:
        raise MaterialContractError(
            "blocked_worker_task_trace_incomplete", "exec call must have exactly one matching output"
        )
    bound_output_ids = {exec_call_id}
    wait_output_indices: list[int] = []
    if wait_calls:
        yielded = re.search(
            r"Script running with cell ID ([A-Za-z0-9_-]+)",
            tool_output_text(exec_outputs[0][1]),
        )
        if yielded is None:
            raise MaterialContractError(
                "blocked_worker_wait_mismatch", "wait used without a yielded exec cell"
            )
        cell_id = yielded.group(1)
        for wait_index, wait_call in wait_calls:
            raw_arguments = wait_call.get("arguments", wait_call.get("input", ""))
            try:
                arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
            except json.JSONDecodeError as exc:
                raise MaterialContractError("blocked_worker_wait_mismatch", str(exc)) from exc
            if (
                not isinstance(arguments, dict)
                or str(arguments.get("cell_id")) != cell_id
                or arguments.get("terminate") is True
            ):
                raise MaterialContractError(
                    "blocked_worker_wait_mismatch", "wait is not bound to the yielded image cell"
                )
            wait_call_id = wait_call.get("call_id")
            if not isinstance(wait_call_id, str) or not wait_call_id:
                raise MaterialContractError("blocked_worker_wait_mismatch", "wait lacks call_id")
            matching = [
                (index, payload)
                for index, payload in outputs
                if payload.get("call_id") == wait_call_id
            ]
            if len(matching) != 1 or matching[0][0] <= wait_index:
                raise MaterialContractError(
                    "blocked_worker_task_trace_incomplete", "wait lacks one later matching output"
                )
            wait_output_indices.append(matching[0][0])
            bound_output_ids.add(wait_call_id)
        last_wait_output = max(wait_output_indices)
        if "Script running with cell ID" in tool_output_text(events[last_wait_output].get("payload", {})):
            raise MaterialContractError(
                "blocked_worker_task_trace_incomplete", "last wait still reports a running image cell"
            )
    if any(payload.get("call_id") not in bound_output_ids for _, payload in outputs):
        raise MaterialContractError(
            "blocked_worker_unexpected_tool_call", "rollout contains an unbound tool output"
        )

    end_index, image_end = image_ends[0]
    agent_final_index, agent_final = agent_finals[0]
    response_final_index, response_final = response_finals[0]
    last_tool_index = max(
        call_index,
        exec_outputs[0][0],
        *[index for index, _ in wait_calls],
        *wait_output_indices,
    )
    if not (
        0 < task_index < context_index < call_index
        and call_index < end_index
        and call_index < exec_outputs[0][0] < end_index
        and all(call_index < index < end_index for index, _ in wait_calls)
        # The image-generation end event is emitted while the final wait call
        # is still in flight, so that wait's matching tool output may follow
        # the image event.  A wait *call* after the image event remains fatal.
        and all(call_index < index < min(agent_final_index, response_final_index) for index in wait_output_indices)
        and last_tool_index < min(agent_final_index, response_final_index)
        and end_index < agent_final_index < completion_index
        and end_index < response_final_index < completion_index
    ):
        raise MaterialContractError(
            "blocked_worker_event_order",
            "worker trace is not one context/call/image-end/empty-final/completion sequence",
        )
    if agent_final.get("message") not in {None, ""} or response_message_text(response_final) != "":
        raise MaterialContractError("blocked_worker_nonempty_final", "worker final text is non-empty")
    if image_end.get("status") != "completed":
        raise MaterialContractError(
            "blocked_worker_generation_failed", f"image status is {image_end.get('status')!r}"
        )
    image_call_id = image_end.get("call_id")
    saved_path = image_end.get("saved_path")
    if (
        not isinstance(image_call_id, str)
        or not EXEC_CALL_RE.fullmatch(image_call_id)
        or not isinstance(saved_path, str)
        or not saved_path
    ):
        raise MaterialContractError(
            "blocked_worker_image_event_incomplete", "image event lacks canonical call id or saved path"
        )
    return {
        "worker_turn_id": turn_id,
        "image_generation_call_id": image_call_id,
        "saved_path": saved_path,
        # Keep the legacy field canonical: downstream publication binds the
        # immutable frozen file, not the rollout transport representation.
        "exec_source_sha256": exec_transport["frozen_exec_file_sha256"],
        **exec_transport,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = ContractArgumentParser(description=__doc__)
    parser.add_argument("--worker-spawn", type=Path)
    parser.add_argument("--copy-to", required=True, type=Path)
    parser.add_argument("--result-json", required=True, type=Path)
    parser.add_argument("--state-db", type=Path)
    parser.add_argument("--codex-home", type=Path)
    # Parsed only to return a stable migration blocker for historical v1 invocations.
    parser.add_argument("--agent-path")
    parser.add_argument("--not-before-ms", type=int)
    parser.add_argument("--parent-thread-id")
    parser.add_argument("--worker-run-nonce")
    parser.add_argument("--expected-prompt", type=Path)
    parser.add_argument("--reference-manifest", type=Path)
    parser.add_argument("--expected-reference", action="append", type=Path)
    parser.add_argument("--expected-recent-image-count", type=int)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    legacy_values = {
        "agent_path": args.agent_path,
        "not_before_ms": args.not_before_ms,
        "parent_thread_id": args.parent_thread_id,
        "worker_run_nonce": args.worker_run_nonce,
        "expected_prompt": args.expected_prompt,
        "reference_manifest": args.reference_manifest,
        "expected_reference": args.expected_reference,
        "expected_recent_image_count": args.expected_recent_image_count,
    }
    supplied_legacy = sorted(name for name, value in legacy_values.items() if value is not None)
    if args.worker_spawn is None or supplied_legacy:
        raise MaterialContractError(
            "blocked_legacy_material_run_v1",
            "v1 direct resolver inputs cannot be resumed or mixed with v4; "
            f"start a new v4 run with only worker_spawn.json (legacy={supplied_legacy})",
        )
    spawn_path = args.worker_spawn.expanduser().resolve(strict=False)
    attempt_dir = spawn_path.parent
    run_dir = attempt_dir.parent.parent
    attempt_id = attempt_dir.name
    if (
        not ATTEMPT_RE.fullmatch(attempt_id)
        or attempt_dir.parent != run_dir / "attempts"
        or spawn_path != attempt_dir / "worker_spawn.json"
    ):
        raise MaterialContractError(
            "blocked_worker_attempt_scope_mismatch", "worker spawn path is not run/attempts/01..03/worker_spawn.json"
        )
    copy_to = require_exact_path(
        args.copy_to,
        attempt_dir / "board.png",
        "blocked_worker_attempt_scope_mismatch",
        "bound board",
    )
    result_path = require_exact_path(
        args.result_json,
        attempt_dir / "worker_result.json",
        "blocked_worker_attempt_scope_mismatch",
        "worker result",
    )
    if copy_to.exists() or result_path.exists():
        raise MaterialContractError(
            "blocked_worker_output_conflict", "board.png and worker_result.json are create-only"
        )

    spawn, spawn_bytes = load_json_file(
        spawn_path, "blocked_worker_spawn_invalid", "worker spawn record"
    )
    if spawn.get("schema_version") in {None, "material_worker_spawn.v1"}:
        raise MaterialContractError(
            "blocked_legacy_material_run_v1", "legacy worker spawn cannot be resumed as v4"
        )
    require_exact_keys(spawn, SPAWN_KEYS, "blocked_worker_spawn_invalid", "worker spawn record")
    if (
        spawn["schema_version"] != "material_worker_spawn.v2"
        or spawn["attempt_id"] != attempt_id
        or spawn["pre_spawn_state"] != "one_non_decision_worker_spawned_unresolved"
    ):
        raise MaterialContractError("blocked_worker_spawn_invalid", "worker spawn schema/state mismatch")
    agent_path = spawn["agent_path"]
    parent_thread_id = spawn["parent_thread_id"]
    checkpoint = spawn["worker_spawn_not_before_ms"]
    nonce = spawn["worker_run_nonce"]
    if (
        not isinstance(agent_path, str)
        or not agent_path.startswith("/root/")
        or ".." in agent_path.split("/")
        or "\\" in agent_path
    ):
        raise MaterialContractError("blocked_worker_agent_path_invalid", "invalid canonical agent path")
    if not isinstance(parent_thread_id, str) or not UUID_RE.fullmatch(parent_thread_id):
        raise MaterialContractError("blocked_worker_parent_mismatch", "invalid parent thread id")
    if type(checkpoint) is not int or checkpoint < 0:
        raise MaterialContractError("blocked_worker_checkpoint_invalid", "invalid spawn checkpoint")
    if not isinstance(nonce, str) or not re.fullmatch(r"[0-9a-f]{32}", nonce):
        raise MaterialContractError("blocked_worker_nonce_invalid", "invalid worker nonce")

    manifest_path = Path(spawn["reference_manifest_path"])
    contract_path = Path(spawn["source_contract_path"])
    prompt_path = Path(spawn["generation_prompt_path"])
    exec_path = Path(spawn["worker_exec_source_path"])
    receipt_path = Path(spawn["worker_exec_receipt_path"])
    if prompt_path.parent != attempt_dir:
        raise MaterialContractError("blocked_worker_attempt_scope_mismatch", "prompt is outside attempt")
    require_exact_path(exec_path, attempt_dir / "worker_exec.js", "blocked_worker_attempt_scope_mismatch", "exec source")
    require_exact_path(receipt_path, attempt_dir / "worker_exec.json", "blocked_worker_attempt_scope_mismatch", "exec receipt")
    manifest_record = load_reference_manifest(manifest_path, run_dir)
    contract_record = load_source_contract(contract_path, run_dir, manifest_record)
    prompt_bytes = read_prompt_bytes(prompt_path, "blocked_worker_prompt_sidecar_invalid", "generation prompt")
    require_prompt_block_once(
        prompt_bytes, contract_record["prompt_block_bytes"], "blocked_worker_prompt_contract_mismatch"
    )
    exec_bytes = exec_path.read_bytes() if exec_path.is_file() else b""
    receipt, receipt_bytes = load_json_file(
        receipt_path, "blocked_worker_exec_receipt_invalid", "worker exec receipt"
    )
    require_exact_keys(receipt, EXEC_RECEIPT_KEYS, "blocked_worker_exec_receipt_invalid", "worker exec receipt")
    expected_exec = render_worker_exec_bytes(nonce, prompt_bytes.decode("utf-8"), manifest_record["paths"])
    if exec_bytes != expected_exec:
        raise MaterialContractError(
            "blocked_worker_exec_source_mismatch", "frozen exec source is not the deterministic render"
        )
    expected_spawn_locks = {
        "generation_prompt_sha256": sha256_bytes(prompt_bytes),
        "reference_manifest_sha256": manifest_record["sha256"],
        "source_contract_sha256": contract_record["sha256"],
        "prompt_block_sha256": contract_record["prompt_block_sha256"],
        "worker_exec_source_sha256": sha256_bytes(exec_bytes),
        "worker_exec_receipt_sha256": sha256_bytes(receipt_bytes),
    }
    if any(spawn[field] != value for field, value in expected_spawn_locks.items()):
        raise MaterialContractError("blocked_worker_spawn_invalid", "worker spawn hash locks mismatch")
    expected_receipt = {
        "schema_version": "material_render_worker_exec.v1",
        "attempt_id": attempt_id,
        "worker_run_nonce": nonce,
        "generation_prompt_path": str(prompt_path),
        "generation_prompt_sha256": sha256_bytes(prompt_bytes),
        "reference_manifest_path": str(manifest_path),
        "reference_manifest_sha256": manifest_record["sha256"],
        "ordered_reference_bundle_sha256": manifest_record["ordered_bundle_sha256"],
        "ordered_reference_paths": [str(path) for path in manifest_record["paths"]],
        "source_contract_path": str(contract_path),
        "source_contract_sha256": contract_record["sha256"],
        "prompt_block_sha256": contract_record["prompt_block_sha256"],
        "exec_source_path": str(exec_path),
        "exec_source_sha256": sha256_bytes(exec_bytes),
        "call_contract": "exactly_one_imagegen;no_decision;empty_worker_final",
    }
    if receipt != expected_receipt:
        raise MaterialContractError(
            "blocked_worker_exec_receipt_invalid", "exec receipt does not match frozen artifacts"
        )

    codex_home = (args.codex_home or default_codex_home()).expanduser().resolve(strict=False)
    state_db = (args.state_db or codex_home / "state_5.sqlite").expanduser().resolve(strict=False)
    worker = resolve_worker_thread(
        state_db,
        agent_path=agent_path,
        not_before_ms=checkpoint,
        parent_thread_id=parent_thread_id,
    )
    rollout_path = Path(str(worker["rollout_path"]).removeprefix("\\\\?\\"))
    evidence = validate_worker_rollout(
        read_rollout(rollout_path),
        thread_id=worker["thread_id"],
        agent_path=agent_path,
        parent_thread_id=parent_thread_id,
        expected_exec_bytes=exec_bytes,
    )
    expected_generated_root = (codex_home / "generated_images").resolve(strict=False)
    expected_source = (
        expected_generated_root
        / worker["thread_id"]
        / f"{evidence['image_generation_call_id']}.png"
    ).resolve(strict=False)
    source_path = Path(evidence["saved_path"]).expanduser().resolve(strict=False)
    require_inside(
        expected_generated_root,
        source_path,
        "blocked_worker_image_path_mismatch",
        "generated image",
    )
    if normalized_path(source_path) != normalized_path(expected_source):
        raise MaterialContractError(
            "blocked_worker_image_path_mismatch",
            "saved image path is not derived from worker thread id plus image call id",
        )
    if not source_path.is_file():
        raise MaterialContractError("blocked_worker_image_missing", f"generated image missing: {source_path}")
    image_bytes = source_path.read_bytes()
    image_metadata = inspect_image_bytes(
        image_bytes,
        code="blocked_worker_image_invalid",
        label="generated board",
        required_format="PNG",
    )
    image_sha = sha256_bytes(image_bytes)
    if image_sha in set(manifest_record["hashes"]):
        raise MaterialContractError(
            "blocked_worker_output_matches_source", "generated board bytes equal a frozen source image"
        )

    result = {
        "ok": True,
        "schema_version": "delegated_product_image_worker_result.v2",
        "attempt_id": attempt_id,
        "resolved_at_utc": datetime.now(timezone.utc).isoformat(),
        "agent_path": agent_path,
        "worker_thread_id": worker["thread_id"],
        "worker_turn_id": evidence["worker_turn_id"],
        "parent_thread_id": parent_thread_id,
        "worker_rollout_path": str(rollout_path),
        "image_generation_call_id": evidence["image_generation_call_id"],
        "worker_saved_path": str(source_path),
        "run_image_path": str(copy_to),
        "image_sha256": image_sha,
        "width_px": image_metadata["width_px"],
        "height_px": image_metadata["height_px"],
        "observed_aspect_ratio": image_metadata["width_px"] / image_metadata["height_px"],
        "exact_16_9": image_metadata["width_px"] * 9 == image_metadata["height_px"] * 16,
        "png_validation": "pillow_verify_and_full_load",
        "generation_prompt_sha256": sha256_bytes(prompt_bytes),
        "prompt_sha_match": True,
        "prompt_bytes_match": True,
        "reference_mode": "frozen_manifest_v2",
        "reference_count": len(manifest_record["paths"]),
        "reference_bytes_verified": True,
        "reference_bytes_match": True,
        "reference_manifest_path": str(manifest_path),
        "reference_manifest_sha256": manifest_record["sha256"],
        "ordered_reference_bundle_sha256": manifest_record["ordered_bundle_sha256"],
        "source_contract_path": str(contract_path),
        "source_contract_sha256": contract_record["sha256"],
        "prompt_block_sha256": contract_record["prompt_block_sha256"],
        "worker_spawn_path": str(spawn_path),
        "worker_spawn_sha256": sha256_bytes(spawn_bytes),
        "worker_exec_source_path": str(exec_path),
        "worker_exec_source_sha256": sha256_bytes(exec_bytes),
        "frozen_exec_file_sha256": evidence["frozen_exec_file_sha256"],
        "recorded_exec_content_sha256": evidence["recorded_exec_content_sha256"],
        "exec_transport_mode": evidence["exec_transport_mode"],
        "exec_body_match": evidence["exec_body_match"],
        "worker_exec_receipt_path": str(receipt_path),
        "worker_exec_receipt_sha256": sha256_bytes(receipt_bytes),
        "output_distinct_from_all_sources": True,
    }
    result_bytes = pretty_json_bytes(result)
    board_created = False
    try:
        board_created = create_only_bytes(
            copy_to,
            image_bytes,
            code="blocked_worker_output_conflict",
            idempotent=False,
        )
        create_only_bytes(
            result_path,
            result_bytes,
            code="blocked_worker_output_conflict",
            idempotent=False,
        )
    except BaseException:
        if board_created:
            try:
                copy_to.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MaterialContractError as exc:
        print(
            json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}),
            file=sys.stderr,
        )
        raise SystemExit(2)
    except OSError as exc:
        print(
            json.dumps(
                {"ok": False, "error_code": "blocked_worker_filesystem", "detail": str(exc)}
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)
