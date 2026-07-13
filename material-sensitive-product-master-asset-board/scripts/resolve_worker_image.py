#!/usr/bin/env python3
"""Resolve one delegated image worker to its exact generated PNG.

The finalizing main agent runs this after a fresh non-decision worker has made
one terminal built-in image-generation call.  Resolution is evidence based:
Codex state identifies the worker thread, its rollout proves the exact prompt
and reference contract, and the image event binds the thread and call id to a
single PNG under ``generated_images``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JSON_DECODER = json.JSONDecoder()
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
EXEC_CALL_RE = re.compile(
    r"^exec-[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class ContractError(RuntimeError):
    """A stable, machine-readable delegated-worker contract failure."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        if not code.startswith("blocked_worker_"):
            raise ValueError(f"worker error code must use blocked_worker_*: {code}")
        self.code = code
        self.detail = detail


class ContractArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ContractError("blocked_worker_cli_contract", message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_path(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def source_agent_path(source: str) -> tuple[str | None, str | None]:
    try:
        spawn = json.loads(source)["subagent"]["thread_spawn"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None, None
    return spawn.get("agent_path"), spawn.get("parent_thread_id")


def resolve_worker_thread(
    state_db: Path,
    agent_path: str,
    not_before_ms: int,
    parent_thread_id: str,
) -> dict[str, Any]:
    """Return the only fresh thread matching the exact spawn identity."""
    if not state_db.is_file():
        raise ContractError("blocked_worker_state_unavailable", f"state DB not found: {state_db}")
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
        raise ContractError("blocked_worker_state_unavailable", str(exc)) from exc
    finally:
        try:
            connection.close()
        except UnboundLocalError:
            pass

    matches: list[dict[str, Any]] = []
    for thread_id, rollout_path, created_at, created_at_ms, source in rows:
        exact_path, actual_parent = source_agent_path(source)
        created_ms = created_at_ms if created_at_ms is not None else int(created_at) * 1000
        if (
            exact_path == agent_path
            and actual_parent == parent_thread_id
            and created_ms >= not_before_ms
        ):
            matches.append(
                {
                    "thread_id": thread_id,
                    "rollout_path": rollout_path,
                    "created_at_ms": created_ms,
                    "parent_thread_id": actual_parent,
                }
            )

    if not matches:
        raise ContractError(
            "blocked_worker_thread_not_found",
            f"no fresh worker matched agent_path={agent_path!r} and parent={parent_thread_id!r}",
        )
    if len(matches) != 1:
        ids = ", ".join(sorted(row["thread_id"] for row in matches))
        raise ContractError(
            "blocked_worker_thread_ambiguous",
            f"expected one fresh worker thread, found {len(matches)}: {ids}",
        )
    return matches[0]


def read_rollout(rollout_path: Path) -> list[dict[str, Any]]:
    if not rollout_path.is_file():
        raise ContractError("blocked_worker_rollout_unavailable", f"rollout not found: {rollout_path}")
    events: list[dict[str, Any]] = []
    try:
        with rollout_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                event = json.loads(line)
                event["_line"] = line_number
                events.append(event)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("blocked_worker_rollout_unavailable", str(exc)) from exc
    return events


def load_reference_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load and re-hash one material-specific run-scoped reference bundle."""
    if not manifest_path.is_file():
        raise ContractError(
            "blocked_worker_reference_manifest_missing",
            f"reference manifest not found: {manifest_path}",
        )
    manifest_bytes = manifest_path.read_bytes()
    if manifest_bytes.startswith(b"\xef\xbb\xbf") or b"\r" in manifest_bytes:
        raise ContractError(
            "blocked_worker_reference_manifest_invalid",
            "reference manifest must be UTF-8 without BOM and use LF line endings",
        )
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("blocked_worker_reference_manifest_invalid", str(exc)) from exc
    if manifest.get("schema_version") != "material_reference_bundle.v1":
        raise ContractError(
            "blocked_worker_reference_manifest_invalid",
            "unexpected reference manifest schema",
        )
    entries = manifest.get("ordered_references")
    if not isinstance(entries, list) or not entries:
        raise ContractError(
            "blocked_worker_reference_manifest_invalid",
            "ordered_references must be non-empty",
        )

    reference_root = manifest_path.parent.resolve() / "references"
    normalized_root = normalized_path(reference_root)
    aliases: list[str] = []
    paths: list[Path] = []
    verified_entries: list[dict[str, Any]] = []
    for expected_index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            raise ContractError(
                "blocked_worker_reference_manifest_invalid",
                "reference entry is not an object",
            )
        alias = entry.get("alias")
        frozen_path = entry.get("frozen_path")
        size_bytes = entry.get("size_bytes")
        expected_sha = entry.get("sha256")
        if entry.get("index") != expected_index or not isinstance(alias, str):
            raise ContractError(
                "blocked_worker_reference_manifest_invalid",
                "reference order/index is invalid",
            )
        if not isinstance(frozen_path, str) or not isinstance(size_bytes, int):
            raise ContractError(
                "blocked_worker_reference_manifest_invalid",
                "reference path/size is invalid",
            )
        if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
            raise ContractError(
                "blocked_worker_reference_manifest_invalid",
                "reference SHA-256 is invalid",
            )
        path = Path(frozen_path)
        if not path.is_absolute():
            raise ContractError(
                "blocked_worker_reference_manifest_invalid",
                f"reference path is not absolute: {path}",
            )
        try:
            common = os.path.commonpath([normalized_root, normalized_path(path)])
        except ValueError as exc:
            raise ContractError("blocked_worker_reference_manifest_invalid", str(exc)) from exc
        if common != normalized_root:
            raise ContractError(
                "blocked_worker_reference_manifest_location",
                f"frozen reference is outside manifest-scoped references/: {path}",
            )
        if not path.is_file():
            raise ContractError(
                "blocked_worker_reference_bytes_changed",
                f"frozen reference missing: {path}",
            )
        data = path.read_bytes()
        if len(data) != size_bytes or sha256_bytes(data) != expected_sha:
            raise ContractError(
                "blocked_worker_reference_bytes_changed",
                f"frozen reference bytes changed: {path}",
            )
        aliases.append(alias)
        paths.append(path)
        verified_entries.append(entry)

    if len(set(aliases)) != len(aliases) or len(set(map(normalized_path, paths))) != len(paths):
        raise ContractError(
            "blocked_worker_reference_manifest_invalid",
            "reference aliases and frozen paths must be unique",
        )
    digest_payload = json.dumps(
        verified_entries,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    bundle_sha = sha256_bytes(digest_payload)
    if manifest.get("ordered_bundle_sha256") != bundle_sha:
        raise ContractError(
            "blocked_worker_reference_manifest_hash_mismatch",
            "ordered reference bundle hash does not match manifest entries",
        )
    return {
        "paths": paths,
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "ordered_bundle_sha256": bundle_sha,
        "reference_count": len(paths),
    }


def parse_imagegen_argument_object(source: str) -> dict[str, Any]:
    """Parse only the unique imagegen call's direct JSON object argument.

    Requiring a direct JSON object intentionally rejects prompt variables,
    shorthand properties, shell-output wrappers, and decoy keys elsewhere in
    the worker's exec source.
    """
    marker = "tools.image_gen__imagegen"
    if source.count(marker) != 1:
        raise ContractError(
            "blocked_worker_call_unparseable",
            "worker exec must contain exactly one imagegen invocation",
        )
    cursor = source.index(marker) + len(marker)
    while cursor < len(source) and source[cursor].isspace():
        cursor += 1
    if cursor >= len(source) or source[cursor] != "(":
        raise ContractError("blocked_worker_call_unparseable", "imagegen invocation lacks '('")
    cursor += 1
    while cursor < len(source) and source[cursor].isspace():
        cursor += 1
    if cursor >= len(source) or source[cursor] != "{":
        raise ContractError(
            "blocked_worker_call_unparseable",
            "imagegen must receive one direct JSON object literal",
        )

    start = cursor
    depth = 0
    in_string = False
    escaped = False
    end: int | None = None
    for index in range(start, len(source)):
        character = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    if end is None or in_string:
        raise ContractError("blocked_worker_call_unparseable", "unterminated imagegen JSON object")
    cursor = end
    while cursor < len(source) and source[cursor].isspace():
        cursor += 1
    if cursor >= len(source) or source[cursor] != ")":
        raise ContractError(
            "blocked_worker_call_unparseable",
            "imagegen call must close immediately after its JSON object",
        )
    try:
        value = json.loads(source[start:end])
    except json.JSONDecodeError as exc:
        raise ContractError(
            "blocked_worker_call_unparseable",
            f"imagegen argument is not strict JSON: {exc}",
        ) from exc
    if not isinstance(value, dict):
        raise ContractError("blocked_worker_call_unparseable", "imagegen argument is not an object")
    allowed = {"prompt", "referenced_image_paths", "num_last_images_to_include"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ContractError(
            "blocked_worker_call_unparseable",
            f"unexpected imagegen arguments: {unknown}",
        )
    return value


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
        item["text"]
        for item in content
        if isinstance(item, dict) and isinstance(item.get("text"), str)
    )


def validate_reference_cli_contract(
    expected_references: list[Path] | None,
    expected_recent_image_count: int | None,
    reference_manifest: Path | None,
) -> tuple[list[Path], int | None, dict[str, Any]]:
    references = expected_references or []
    if expected_recent_image_count is not None:
        raise ContractError(
            "blocked_worker_reference_contract_invalid",
            "production material resolution forbids recent-image-count because it cannot prove reference bytes",
        )
    selected = sum(
        [
            bool(references),
            reference_manifest is not None,
        ]
    )
    if selected != 1:
        raise ContractError(
            "blocked_worker_reference_contract_invalid",
            "provide a material reference manifest, repeated expected references, or a recent-image count, exclusively",
        )
    if reference_manifest is not None:
        manifest = load_reference_manifest(reference_manifest)
        return manifest["paths"], None, manifest
    normalized: list[str] = []
    for reference in references:
        if not reference.is_absolute():
            raise ContractError(
                "blocked_worker_reference_contract_invalid",
                f"expected reference is not absolute: {reference}",
            )
        if not reference.is_file():
            raise ContractError(
                "blocked_worker_reference_contract_invalid",
                f"expected reference is unavailable: {reference}",
            )
        normalized.append(normalized_path(reference))
    if len(set(normalized)) != len(normalized):
        raise ContractError(
            "blocked_worker_reference_contract_invalid",
            "expected references must be unique while preserving their exact order",
        )
    return references, None, {
        "manifest_sha256": None,
        "ordered_bundle_sha256": None,
        "reference_count": len(references),
    }


def validate_reference_tool_contract(
    call_arguments: dict[str, Any],
    expected_references: list[Path],
    expected_recent_image_count: int | None,
) -> dict[str, Any]:
    has_paths = "referenced_image_paths" in call_arguments
    has_recent = "num_last_images_to_include" in call_arguments
    if has_paths == has_recent:
        raise ContractError(
            "blocked_worker_reference_mismatch",
            "imagegen must contain exactly one reference transport mechanism",
        )

    if expected_references:
        if not has_paths:
            raise ContractError(
                "blocked_worker_reference_mismatch",
                "expected referenced_image_paths but worker used recent conversation images",
            )
        actual = call_arguments["referenced_image_paths"]
        if not isinstance(actual, list) or not actual or not all(isinstance(item, str) for item in actual):
            raise ContractError(
                "blocked_worker_reference_mismatch",
                "referenced_image_paths must be a non-empty string list",
            )
        expected_paths = [normalized_path(path) for path in expected_references]
        actual_paths = [normalized_path(Path(path)) for path in actual]
        if actual_paths != expected_paths:
            raise ContractError(
                "blocked_worker_reference_mismatch",
                f"expected ordered references {expected_paths!r}, received {actual_paths!r}",
            )
        return {"reference_mode": "explicit_paths", "reference_count": len(expected_paths)}

    if not has_recent:
        raise ContractError(
            "blocked_worker_reference_mismatch",
            "expected num_last_images_to_include but worker used explicit paths",
        )
    actual_count = call_arguments["num_last_images_to_include"]
    if type(actual_count) is not int or actual_count != expected_recent_image_count:
        raise ContractError(
            "blocked_worker_reference_mismatch",
            f"expected recent-image count {expected_recent_image_count}, received {actual_count!r}",
        )
    return {"reference_mode": "recent_images", "reference_count": actual_count}


def validate_worker_rollout(
    events: list[dict[str, Any]],
    *,
    thread_id: str,
    agent_path: str,
    parent_thread_id: str,
    worker_run_nonce: str,
    expected_prompt_bytes: bytes,
    expected_references: list[Path],
    expected_recent_image_count: int | None,
) -> dict[str, Any]:
    """Validate one terminal image call and return its bound event evidence."""
    if not events or events[0].get("type") != "session_meta":
        raise ContractError("blocked_worker_session_mismatch", "rollout lacks leading session_meta")
    session = events[0].get("payload", {})
    if not UUID_RE.fullmatch(thread_id) or not UUID_RE.fullmatch(parent_thread_id):
        raise ContractError(
            "blocked_worker_session_mismatch",
            "resolved worker and parent thread IDs must be canonical UUIDs",
        )
    if session.get("id") != thread_id or session.get("agent_path") != agent_path:
        raise ContractError(
            "blocked_worker_session_mismatch",
            "session id or canonical agent_path does not match the resolved worker thread",
        )
    if session.get("parent_thread_id") != parent_thread_id:
        raise ContractError("blocked_worker_parent_mismatch", "session parent thread mismatch")

    task_starts = [
        index
        for index, event in enumerate(events)
        if event.get("type") == "event_msg"
        and event.get("payload", {}).get("type") == "task_started"
    ]
    if not task_starts:
        raise ContractError("blocked_worker_task_trace_missing", "worker rollout has no task_started event")
    worker_events = events[task_starts[-1] :]
    task_started = worker_events[0].get("payload", {})
    turn_id = task_started.get("turn_id")
    if not isinstance(turn_id, str) or not turn_id:
        raise ContractError("blocked_worker_task_trace_incomplete", "task_started lacks turn_id")

    turn_contexts = [
        (index, event.get("payload", {}))
        for index, event in enumerate(worker_events)
        if event.get("type") == "turn_context"
    ]
    completions = [
        (index, event.get("payload", {}))
        for index, event in enumerate(worker_events)
        if event.get("type") == "event_msg"
        and event.get("payload", {}).get("type") == "task_complete"
    ]
    if len(turn_contexts) != 1 or turn_contexts[0][1].get("turn_id") != turn_id:
        raise ContractError("blocked_worker_turn_mismatch", "task and context do not identify one turn")
    if len(completions) != 1:
        raise ContractError(
            "blocked_worker_task_trace_incomplete",
            f"expected one task_complete, found {len(completions)}",
        )
    completion_index, completion = completions[0]
    if completion.get("turn_id") != turn_id:
        raise ContractError("blocked_worker_turn_mismatch", "task_complete turn_id mismatch")
    if completion.get("last_agent_message") not in {None, ""}:
        raise ContractError("blocked_worker_nonempty_final", "worker task_complete is not empty")

    all_tool_calls: list[tuple[int, dict[str, Any]]] = []
    image_calls: list[tuple[int, dict[str, Any]]] = []
    wait_calls: list[tuple[int, dict[str, Any]]] = []
    tool_outputs: list[tuple[int, dict[str, Any]]] = []
    image_ends: list[tuple[int, dict[str, Any]]] = []
    agent_finals: list[tuple[int, dict[str, Any]]] = []
    response_finals: list[tuple[int, dict[str, Any]]] = []
    for index, event in enumerate(worker_events):
        payload = event.get("payload", {})
        if event.get("type") == "response_item" and payload.get("type") in {
            "custom_tool_call",
            "function_call",
        }:
            all_tool_calls.append((index, payload))
            if payload.get("type") == "function_call" and payload.get("name") == "wait":
                wait_calls.append((index, payload))
        if event.get("type") == "response_item" and payload.get("type") in {
            "custom_tool_call_output",
            "function_call_output",
        }:
            tool_outputs.append((index, payload))
        if (
            event.get("type") == "response_item"
            and payload.get("type") == "custom_tool_call"
            and "tools.image_gen__imagegen" in payload.get("input", "")
        ):
            image_calls.append((index, payload))
        if event.get("type") == "event_msg" and payload.get("type") == "image_generation_end":
            image_ends.append((index, payload))
        if (
            event.get("type") == "event_msg"
            and payload.get("type") == "agent_message"
            and payload.get("phase") == "final_answer"
        ):
            agent_finals.append((index, payload))
        if (
            event.get("type") == "response_item"
            and payload.get("type") == "message"
            and payload.get("role") == "assistant"
            and payload.get("phase") == "final_answer"
        ):
            response_finals.append((index, payload))

    if len(all_tool_calls) != len(image_calls) + len(wait_calls):
        raise ContractError(
            "blocked_worker_unexpected_tool_call",
            "worker made a tool call other than the imagegen exec and its bound waits",
        )

    if len(image_calls) != 1:
        raise ContractError(
            "blocked_worker_image_call_count",
            f"expected exactly one imagegen call, found {len(image_calls)}",
        )
    if len(image_ends) != 1:
        raise ContractError(
            "blocked_worker_image_event_count",
            f"expected exactly one image_generation_end, found {len(image_ends)}",
        )
    if len(agent_finals) != 1 or len(response_finals) != 1:
        raise ContractError(
            "blocked_worker_final_trace_incomplete",
            "worker must contain one event final and one response final",
        )

    call_index, image_call = image_calls[0]
    end_index, image_end = image_ends[0]
    agent_final_index, agent_final = agent_finals[0]
    response_final_index, response_final = response_finals[0]
    context_index = turn_contexts[0][0]
    image_exec_call_id = image_call.get("call_id")
    image_outputs = [
        (index, payload)
        for index, payload in tool_outputs
        if payload.get("call_id") == image_exec_call_id
    ]
    if len(image_outputs) != 1:
        raise ContractError(
            "blocked_worker_task_trace_incomplete",
            "imagegen exec must have exactly one matching tool output",
        )

    wait_output_indices: list[int] = []
    if wait_calls:
        yielded = re.search(r"Script running with cell ID ([A-Za-z0-9_-]+)", tool_output_text(image_outputs[0][1]))
        if yielded is None:
            raise ContractError(
                "blocked_worker_wait_mismatch",
                "worker used wait without a yielded imagegen exec cell",
            )
        cell_id = yielded.group(1)
        for wait_index, wait_call in wait_calls:
            raw_arguments = wait_call.get("arguments", wait_call.get("input", ""))
            try:
                arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
            except json.JSONDecodeError as exc:
                raise ContractError("blocked_worker_wait_mismatch", str(exc)) from exc
            if (
                not isinstance(arguments, dict)
                or str(arguments.get("cell_id")) != cell_id
                or arguments.get("terminate") is True
                or not call_index < wait_index < end_index
            ):
                raise ContractError(
                    "blocked_worker_wait_mismatch",
                    "wait is not bound to the yielded imagegen exec cell before image completion",
                )
            matching_outputs = [
                (index, payload)
                for index, payload in tool_outputs
                if payload.get("call_id") == wait_call.get("call_id")
            ]
            if len(matching_outputs) != 1 or matching_outputs[0][0] <= wait_index:
                raise ContractError(
                    "blocked_worker_task_trace_incomplete",
                    "wait call lacks one later matching output",
                )
            wait_output_indices.append(matching_outputs[0][0])
        last_wait_output = max(wait_output_indices)
        if "Script running with cell ID" in tool_output_text(worker_events[last_wait_output].get("payload", {})):
            raise ContractError(
                "blocked_worker_task_trace_incomplete",
                "last imagegen wait still reports a running cell",
            )
    elif image_outputs[0][0] <= call_index:
        raise ContractError(
            "blocked_worker_task_trace_incomplete",
            "imagegen exec output does not follow its call",
        )

    last_tool_activity = max(
        [call_index, image_outputs[0][0], *[index for index, _ in wait_calls], *wait_output_indices]
    )
    final_boundary = max(end_index, last_tool_activity)
    if not (
        0 < context_index < call_index < end_index
        and final_boundary < agent_final_index < completion_index
        and final_boundary < response_final_index < completion_index
    ):
        raise ContractError(
            "blocked_worker_event_order",
            "worker trace is not context/user/call/end/empty-final/complete ordered",
        )
    if agent_final.get("message") not in {None, ""} or response_message_text(response_final) != "":
        raise ContractError("blocked_worker_nonempty_final", "worker emitted non-empty final text")

    call_input = image_call.get("input", "")
    nonce_declarations = re.findall(
        r'(?m)^const worker_run_nonce = "([0-9a-f]{32})";\s*$',
        call_input,
    )
    if nonce_declarations != [worker_run_nonce]:
        raise ContractError(
            "blocked_worker_nonce_mismatch",
            "imagegen exec does not contain exactly one literal declaration of the expected run nonce",
        )
    call_arguments = parse_imagegen_argument_object(call_input)
    tool_prompt = call_arguments.get("prompt")
    if not isinstance(tool_prompt, str):
        raise ContractError("blocked_worker_call_unparseable", "imagegen prompt is not a string")
    tool_prompt_bytes = tool_prompt.encode("utf-8")
    if tool_prompt_bytes != expected_prompt_bytes:
        raise ContractError(
            "blocked_worker_prompt_mismatch",
            "imagegen prompt bytes do not equal the frozen prompt sidecar",
        )
    reference_evidence = validate_reference_tool_contract(
        call_arguments,
        expected_references,
        expected_recent_image_count,
    )

    if image_end.get("status") != "completed":
        raise ContractError(
            "blocked_worker_generation_failed",
            f"image generation status is {image_end.get('status')!r}",
        )
    call_id = image_end.get("call_id")
    saved_path = image_end.get("saved_path")
    if not isinstance(call_id, str) or not call_id or not isinstance(saved_path, str) or not saved_path:
        raise ContractError(
            "blocked_worker_image_event_incomplete",
            "completed image event lacks call_id or saved_path",
        )
    if not EXEC_CALL_RE.fullmatch(call_id):
        raise ContractError(
            "blocked_worker_image_event_incomplete",
            f"image call id is not canonical exec UUID: {call_id!r}",
        )
    return {
        "worker_turn_id": turn_id,
        "call_id": call_id,
        "saved_path": saved_path,
        "tool_prompt_sha256": sha256_bytes(tool_prompt_bytes),
        **reference_evidence,
    }


def inspect_png(path: Path) -> tuple[int, int, str]:
    if not path.is_file():
        raise ContractError("blocked_worker_image_missing", f"generated PNG not found: {path}")
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != PNG_SIGNATURE or data[12:16] != b"IHDR":
        raise ContractError("blocked_worker_image_invalid", f"invalid PNG header: {path}")
    width, height = struct.unpack(">II", data[16:24])
    if width <= 0 or height <= 0:
        raise ContractError("blocked_worker_image_invalid", f"invalid PNG dimensions: {width}x{height}")
    return width, height, sha256_bytes(data)


def copy_bound_image(source: Path, destination: Path, expected_sha256: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256_bytes(destination.read_bytes()) != expected_sha256:
            raise ContractError(
                "blocked_worker_destination_conflict",
                f"destination exists with different bytes: {destination}",
            )
        return
    shutil.copy2(source, destination)
    if sha256_bytes(destination.read_bytes()) != expected_sha256:
        raise ContractError("blocked_worker_copy_mismatch", "copied image hash does not match source")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def read_prompt_sidecar(path: Path) -> bytes:
    if not path.is_file():
        raise ContractError("blocked_worker_prompt_sidecar_missing", f"prompt sidecar not found: {path}")
    data = path.read_bytes()
    if not data or data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise ContractError(
            "blocked_worker_prompt_sidecar_invalid",
            "prompt sidecar must be non-empty UTF-8 without BOM and use LF line endings",
        )
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError("blocked_worker_prompt_sidecar_invalid", str(exc)) from exc
    return data


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def build_parser() -> argparse.ArgumentParser:
    parser = ContractArgumentParser(description=__doc__)
    parser.add_argument("--agent-path", required=True, help="Exact canonical path returned by spawn_agent")
    parser.add_argument("--not-before-ms", required=True, type=int, help="Checkpoint captured before spawn")
    parser.add_argument("--parent-thread-id", required=True, help="Exact finalizing main-agent thread id")
    parser.add_argument("--worker-run-nonce", required=True, help="Exact 32-character lowercase hex nonce")
    parser.add_argument("--expected-prompt", required=True, type=Path, help="Frozen prompt sidecar")
    reference = parser.add_mutually_exclusive_group(required=True)
    reference.add_argument(
        "--reference-manifest",
        type=Path,
        help="Material-specific run-scoped frozen reference manifest",
    )
    reference.add_argument(
        "--expected-reference",
        action="append",
        type=Path,
        help="Expected absolute referenced_image_paths entry; repeat in exact order",
    )
    reference.add_argument(
        "--expected-recent-image-count",
        type=int,
        help="Forbidden compatibility input; material production requires byte-verifiable references",
    )
    parser.add_argument("--copy-to", required=True, type=Path)
    parser.add_argument("--result-json", required=True, type=Path)
    parser.add_argument("--state-db", type=Path)
    parser.add_argument("--codex-home", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.not_before_ms < 0:
        raise ContractError("blocked_worker_checkpoint_invalid", "spawn checkpoint must be non-negative")
    if not re.fullmatch(r"[0-9a-f]{32}", args.worker_run_nonce):
        raise ContractError(
            "blocked_worker_nonce_invalid",
            "worker run nonce must be exactly 32 lowercase hexadecimal characters",
        )
    if (
        not args.agent_path.startswith("/root/")
        or ".." in args.agent_path.split("/")
        or "\\" in args.agent_path
    ):
        raise ContractError(
            "blocked_worker_agent_path_invalid",
            "agent path must be a canonical /root/... path without traversal",
        )
    if not UUID_RE.fullmatch(args.parent_thread_id):
        raise ContractError(
            "blocked_worker_parent_mismatch",
            "parent thread ID must be a canonical UUID",
        )
    attempt_dir = args.expected_prompt.expanduser().resolve().parent
    if (
        args.copy_to.expanduser().resolve().parent != attempt_dir
        or args.result_json.expanduser().resolve().parent != attempt_dir
    ):
        raise ContractError(
            "blocked_worker_attempt_scope_mismatch",
            "expected prompt, copied board, and worker result must share one attempt directory",
        )
    expected_references, expected_recent_count, reference_record = validate_reference_cli_contract(
        args.expected_reference,
        args.expected_recent_image_count,
        args.reference_manifest,
    )
    prompt_bytes = read_prompt_sidecar(args.expected_prompt)
    codex_home = args.codex_home or default_codex_home()
    state_db = args.state_db or codex_home / "state_5.sqlite"

    worker = resolve_worker_thread(
        state_db,
        args.agent_path,
        args.not_before_ms,
        args.parent_thread_id,
    )
    rollout_path = Path(str(worker["rollout_path"]).removeprefix("\\\\?\\"))
    evidence = validate_worker_rollout(
        read_rollout(rollout_path),
        thread_id=worker["thread_id"],
        agent_path=args.agent_path,
        parent_thread_id=args.parent_thread_id,
        worker_run_nonce=args.worker_run_nonce,
        expected_prompt_bytes=prompt_bytes,
        expected_references=expected_references,
        expected_recent_image_count=expected_recent_count,
    )

    source_path = Path(evidence["saved_path"])
    expected_source = codex_home / "generated_images" / worker["thread_id"] / f"{evidence['call_id']}.png"
    if normalized_path(source_path) != normalized_path(expected_source):
        raise ContractError(
            "blocked_worker_image_path_mismatch",
            f"event path {source_path} does not equal thread+call path {expected_source}",
        )
    width, height, image_sha = inspect_png(source_path)
    copy_bound_image(source_path, args.copy_to, image_sha)

    result = {
        "ok": True,
        "contract": "delegated_product_image_worker_result.v1",
        "resolved_at_utc": datetime.now(timezone.utc).isoformat(),
        "agent_path": args.agent_path,
        "worker_thread_id": worker["thread_id"],
        "worker_turn_id": evidence["worker_turn_id"],
        "parent_thread_id": worker["parent_thread_id"],
        "worker_rollout_path": str(rollout_path),
        "image_generation_call_id": evidence["call_id"],
        "worker_saved_path": str(source_path),
        "run_image_path": str(args.copy_to),
        "image_sha256": image_sha,
        "width_px": width,
        "height_px": height,
        "observed_aspect_ratio": width / height,
        "exact_16_9": width * 9 == height * 16,
        "generation_prompt_sha256": sha256_bytes(prompt_bytes),
        "tool_prompt_sha256": evidence["tool_prompt_sha256"],
        "prompt_sha_match": evidence["tool_prompt_sha256"] == sha256_bytes(prompt_bytes),
        "reference_mode": "frozen_manifest" if args.reference_manifest else evidence["reference_mode"],
        "reference_count": evidence["reference_count"],
        "expected_references": [str(path) for path in expected_references],
        "expected_recent_image_count": expected_recent_count,
        "reference_bytes_verified": args.reference_manifest is not None,
        "reference_manifest_path": str(args.reference_manifest) if args.reference_manifest else None,
        "reference_manifest_sha256": reference_record["manifest_sha256"],
        "ordered_reference_bundle_sha256": reference_record["ordered_bundle_sha256"],
    }
    write_json(args.result_json, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}), file=sys.stderr)
        raise SystemExit(2)
    except OSError as exc:
        print(
            json.dumps({"ok": False, "error_code": "blocked_worker_filesystem", "detail": str(exc)}),
            file=sys.stderr,
        )
        raise SystemExit(2)
