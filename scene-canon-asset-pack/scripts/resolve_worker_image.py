#!/usr/bin/env python3
"""Bind one delegated Codex image worker to its exact generated PNG.

The main agent uses this after a fresh, uniquely named subagent has made one
terminal built-in image-generation call.  The script rejects newest-file
guessing: it resolves the worker thread from Codex state, validates the worker
rollout, checks that the exact frozen prompt reached imagegen, and copies the
bound PNG into the run directory.
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
SCENE_CANON_ASSET_TASK_SLUGS = {
    "cdm_001", "srm_001", "cov_001", "cov_002", "cov_003", "scl_001",
}
JSON_DECODER = json.JSONDecoder()


class ContractError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_path(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def source_agent_path(source: str) -> tuple[str | None, str | None]:
    try:
        data = json.loads(source)
        spawn = data["subagent"]["thread_spawn"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None, None
    return spawn.get("agent_path"), spawn.get("parent_thread_id")


def resolve_worker_thread(
    state_db: Path,
    agent_path: str,
    not_before_ms: int,
    parent_thread_id: str | None,
) -> dict[str, Any]:
    if not state_db.is_file():
        raise ContractError("blocked_worker_state_unavailable", f"state DB not found: {state_db}")

    uri = f"file:{state_db.as_posix()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
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
        if exact_path != agent_path or created_ms < not_before_ms:
            continue
        if parent_thread_id is not None and actual_parent != parent_thread_id:
            continue
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
            f"no fresh worker thread matched agent_path={agent_path!r}",
        )
    if len(matches) != 1:
        ids = ", ".join(sorted(row["thread_id"] for row in matches))
        raise ContractError(
            "blocked_worker_thread_ambiguous",
            f"expected one fresh worker thread, found {len(matches)}: {ids}",
        )
    return matches[0]


def resolve_thread_rollout(state_db: Path, thread_id: str, error_code: str) -> Path:
    uri = f"file:{state_db.as_posix()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
        rows = connection.execute(
            "SELECT rollout_path FROM threads WHERE id = ?",
            (thread_id,),
        ).fetchall()
    except sqlite3.Error as exc:
        raise ContractError(error_code, str(exc)) from exc
    finally:
        try:
            connection.close()
        except UnboundLocalError:
            pass
    if len(rows) != 1 or not isinstance(rows[0][0], str):
        raise ContractError(error_code, f"thread rollout not uniquely available: {thread_id}")
    return Path(rows[0][0].removeprefix("\\\\?\\"))


def extract_js_json_value(source: str, key: str) -> Any:
    match = re.search(
        rf"(?<![A-Za-z0-9_])[\"']?{re.escape(key)}[\"']?\s*:\s*",
        source,
    )
    if match is None:
        raise ContractError("blocked_worker_call_unparseable", f"missing imagegen argument: {key}")
    try:
        value, _ = JSON_DECODER.raw_decode(source[match.end() :])
    except json.JSONDecodeError as exc:
        raise ContractError(
            "blocked_worker_call_unparseable",
            f"imagegen argument {key} is not a JSON literal: {exc}",
        ) from exc
    return value


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


def load_reference_manifest(manifest_path: Path, expected_asset_id: str | None = None) -> dict[str, Any]:
    if not manifest_path.is_file():
        raise ContractError(
            "blocked_reference_manifest_missing",
            f"reference manifest not found: {manifest_path}",
        )
    manifest_bytes = manifest_path.read_bytes()
    if manifest_bytes.startswith(b"\xef\xbb\xbf") or b"\r" in manifest_bytes:
        raise ContractError(
            "blocked_reference_manifest_invalid",
            "reference manifest must be UTF-8 without BOM and use LF line endings",
        )
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("blocked_reference_manifest_invalid", str(exc)) from exc
    manifest_keys = {"schema_version", "asset_id", "source_reference_id", "ordered_references", "ordered_bundle_sha256"}
    if set(manifest) != manifest_keys or manifest.get("schema_version") != "scene_canon_reference_bundle.v1":
        raise ContractError("blocked_reference_manifest_invalid", "unexpected reference manifest schema")
    asset_id = manifest.get("asset_id")
    source_reference_id = manifest.get("source_reference_id")
    if asset_id not in {slug.upper() for slug in SCENE_CANON_ASSET_TASK_SLUGS} or not isinstance(source_reference_id, str) or not source_reference_id:
        raise ContractError("blocked_reference_manifest_invalid", "reference manifest lacks Scene Canon asset/source binding")
    if expected_asset_id is not None and asset_id != expected_asset_id:
        raise ContractError("blocked_reference_manifest_invalid", "reference manifest targets the wrong Scene Canon asset")
    entries = manifest.get("ordered_references")
    if not isinstance(entries, list) or not entries:
        raise ContractError("blocked_reference_manifest_invalid", "ordered_references must be non-empty")

    reference_root = manifest_path.parent.resolve() / "references"
    normalized_root = normalized_path(reference_root)
    aliases: list[str] = []
    paths: list[Path] = []
    verified_entries: list[dict[str, Any]] = []
    for expected_index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            raise ContractError("blocked_reference_manifest_invalid", "reference entry is not an object")
        entry_keys = {"index", "alias", "kind", "source_reference_id", "asset_id", "source_path", "frozen_path", "size_bytes", "sha256"}
        if set(entry) != entry_keys:
            raise ContractError("blocked_reference_manifest_invalid", "reference entry fields are incomplete or unexpected")
        alias = entry.get("alias")
        frozen_path = entry.get("frozen_path")
        size_bytes = entry.get("size_bytes")
        expected_sha = entry.get("sha256")
        kind = entry.get("kind")
        if entry.get("index") != expected_index or not isinstance(alias, str):
            raise ContractError("blocked_reference_manifest_invalid", "reference order/index is invalid")
        if not isinstance(frozen_path, str) or not isinstance(size_bytes, int):
            raise ContractError("blocked_reference_manifest_invalid", "reference path/size is invalid")
        if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
            raise ContractError("blocked_reference_manifest_invalid", "reference SHA-256 is invalid")
        path = Path(frozen_path)
        if not path.is_absolute():
            raise ContractError("blocked_reference_manifest_invalid", f"reference path is not absolute: {path}")
        normalized_frozen = normalized_path(path)
        try:
            common = os.path.commonpath([normalized_root, normalized_frozen])
        except ValueError as exc:
            raise ContractError("blocked_reference_manifest_invalid", str(exc)) from exc
        if common != normalized_root:
            raise ContractError(
                "blocked_reference_manifest_location",
                f"frozen reference is outside the run-scoped references directory: {path}",
            )
        if not path.is_file():
            raise ContractError("blocked_reference_bytes_changed", f"frozen reference missing: {path}")
        data = path.read_bytes()
        actual_sha = sha256_bytes(data)
        if len(data) != size_bytes or actual_sha != expected_sha:
            raise ContractError(
                "blocked_reference_bytes_changed",
                f"frozen reference bytes changed after materialization: {path}",
            )
        if expected_index == 1:
            if kind != "source_reference" or entry.get("source_reference_id") != source_reference_id or entry.get("asset_id") is not None:
                raise ContractError("blocked_reference_manifest_invalid", "reference 1 must be the bound original scene source")
        elif kind != "approved_predecessor" or entry.get("source_reference_id") is not None or entry.get("asset_id") not in {slug.upper() for slug in SCENE_CANON_ASSET_TASK_SLUGS}:
            raise ContractError("blocked_reference_manifest_invalid", "later references must be bound approved predecessors")
        aliases.append(alias)
        paths.append(path)
        verified_entries.append(entry)

    if len(set(aliases)) != len(aliases):
        raise ContractError("blocked_reference_manifest_invalid", "reference aliases are not unique")
    normalized_paths = [normalized_path(path) for path in paths]
    if len(set(normalized_paths)) != len(normalized_paths):
        raise ContractError("blocked_reference_manifest_invalid", "frozen reference paths are not unique")
    actual_files = [path for path in reference_root.iterdir() if path.is_file()]
    if any(path.is_dir() for path in reference_root.iterdir()) or {normalized_path(path) for path in actual_files} != set(normalized_paths):
        raise ContractError("blocked_reference_manifest_invalid", "run-scoped references contain missing or unlisted files")

    digest_payload = json.dumps(
        verified_entries,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    actual_bundle_sha = sha256_bytes(digest_payload)
    if manifest.get("ordered_bundle_sha256") != actual_bundle_sha:
        raise ContractError(
            "blocked_reference_manifest_hash_mismatch",
            "ordered reference bundle hash does not match manifest entries",
        )
    return {
        "paths": paths,
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "ordered_bundle_sha256": actual_bundle_sha,
        "reference_count": len(paths),
        "asset_id": asset_id,
        "source_reference_id": source_reference_id,
    }


def response_message_text(payload: dict[str, Any]) -> str:
    content = payload.get("content", "")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            parts.append(item["text"])
    return "".join(parts)


def validate_worker_name_binding(agent_path: str, worker_run_nonce: str) -> str:
    """Bind the observable worker name to the complete run nonce.

    Codex stores inter-agent task bodies as encrypted content in worker
    rollouts.  The canonical agent path and its leaf task name remain visible,
    so the full nonce must live in that name rather than in an unverifiable
    plaintext task-body marker.
    """
    if not re.fullmatch(r"[0-9a-f]{32}", worker_run_nonce):
        raise ContractError(
            "blocked_worker_nonce_invalid",
            "worker run nonce must be exactly 32 lowercase hexadecimal characters",
        )
    task_name = agent_path.rsplit("/", 1)[-1]
    valid_task_names = {
        f"scene_canon_image_{asset_slug}_{worker_run_nonce}"
        for asset_slug in SCENE_CANON_ASSET_TASK_SLUGS
    }
    if not re.fullmatch(r"[a-z0-9_]+", task_name) or task_name not in valid_task_names:
        raise ContractError(
            "blocked_worker_nonce_mismatch",
            "worker task name must bind one exact Scene Canon asset slug and the complete run nonce",
        )
    return task_name


def validate_parent_spawn_chain(
    parent_events: list[dict[str, Any]],
    *,
    parent_thread_id: str,
    worker_thread_id: str,
    agent_path: str,
    worker_run_nonce: str,
    delivery_ciphertext: str,
    not_before_ms: int,
) -> dict[str, Any]:
    task_name = validate_worker_name_binding(agent_path, worker_run_nonce)
    if not parent_events or parent_events[0].get("type") != "session_meta":
        raise ContractError("blocked_worker_spawn_chain_mismatch", "parent rollout lacks session metadata")
    if parent_events[0].get("payload", {}).get("id") != parent_thread_id:
        raise ContractError("blocked_worker_spawn_chain_mismatch", "parent rollout session id mismatch")

    spawn_calls: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for index, event in enumerate(parent_events):
        payload = event.get("payload", {})
        if (
            event.get("type") != "response_item"
            or payload.get("type") != "function_call"
            or payload.get("name") != "spawn_agent"
        ):
            continue
        try:
            arguments = json.loads(payload.get("arguments", ""))
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(arguments, dict) and arguments.get("task_name") == task_name:
            spawn_calls.append((index, payload, arguments))
    if len(spawn_calls) != 1:
        raise ContractError(
            "blocked_worker_spawn_chain_mismatch",
            f"expected one parent spawn call for {task_name!r}, found {len(spawn_calls)}",
        )

    spawn_index, spawn_payload, spawn_arguments = spawn_calls[0]
    spawn_call_id = spawn_payload.get("call_id")
    parent_turn_id = spawn_payload.get("internal_chat_message_metadata_passthrough", {}).get("turn_id")
    if (
        not isinstance(spawn_call_id, str)
        or not spawn_call_id
        or spawn_arguments.get("fork_turns") != "none"
        or spawn_arguments.get("message") != delivery_ciphertext
    ):
        raise ContractError(
            "blocked_worker_spawn_chain_mismatch",
            "spawn call lacks fork_turns=none or its encrypted task body differs from worker delivery",
        )

    activities = [
        (index, event.get("payload", {}))
        for index, event in enumerate(parent_events)
        if event.get("type") == "event_msg"
        and event.get("payload", {}).get("type") == "sub_agent_activity"
        and event.get("payload", {}).get("event_id") == spawn_call_id
    ]
    outputs = [
        (index, event.get("payload", {}))
        for index, event in enumerate(parent_events)
        if event.get("type") == "response_item"
        and event.get("payload", {}).get("type") == "function_call_output"
        and event.get("payload", {}).get("call_id") == spawn_call_id
    ]
    if len(activities) != 1 or len(outputs) != 1:
        raise ContractError(
            "blocked_worker_spawn_chain_mismatch",
            "parent spawn call does not have one matching started activity and one result",
        )
    activity_index, activity = activities[0]
    output_index, output = outputs[0]
    output_turn_id = output.get("internal_chat_message_metadata_passthrough", {}).get("turn_id")
    try:
        output_value = json.loads(output.get("output", ""))
    except (json.JSONDecodeError, TypeError) as exc:
        raise ContractError("blocked_worker_spawn_chain_mismatch", str(exc)) from exc
    if not (
        spawn_index < activity_index
        and spawn_index < output_index
        and activity.get("kind") == "started"
        and isinstance(activity.get("occurred_at_ms"), int)
        and activity.get("occurred_at_ms") >= not_before_ms
        and activity.get("agent_thread_id") == worker_thread_id
        and activity.get("agent_path") == agent_path
        and isinstance(parent_turn_id, str)
        and parent_turn_id
        and output_turn_id == parent_turn_id
        and isinstance(output_value, dict)
        and output_value.get("task_name") == agent_path
    ):
        raise ContractError(
            "blocked_worker_spawn_chain_mismatch",
            "parent spawn call, activity, result, worker thread, and agent path do not form one chain",
        )
    return {
        "binding_mode": "parent_spawn_cipher_chain_v1",
        "parent_spawn_call_id": spawn_call_id,
        "parent_spawn_turn_id": parent_turn_id,
        "parent_spawn_activity_ms": str(activity["occurred_at_ms"]),
        "parent_spawn_event_index": spawn_index,
        "task_delivery_ciphertext_sha256": sha256_bytes(delivery_ciphertext.encode("utf-8")),
    }


def validate_worker_rollout(
    events: list[dict[str, Any]],
    thread_id: str,
    agent_path: str,
    parent_thread_id: str,
    worker_run_nonce: str,
    expected_prompt_bytes: bytes,
    expected_references: list[Path],
    allow_no_references: bool,
) -> dict[str, Any]:
    worker_task_name = validate_worker_name_binding(agent_path, worker_run_nonce)
    if not events or events[0].get("type") != "session_meta":
        raise ContractError("blocked_worker_session_mismatch", "worker rollout lacks leading session_meta")
    session_payload = events[0].get("payload", {})
    session_id = session_payload.get("id")
    if session_id != thread_id:
        raise ContractError(
            "blocked_worker_session_mismatch",
            f"leading rollout session id {session_id!r} does not equal worker thread {thread_id!r}",
        )
    if session_payload.get("agent_path") != agent_path:
        raise ContractError("blocked_worker_session_mismatch", "leading session agent_path mismatch")
    if session_payload.get("parent_thread_id") != parent_thread_id:
        raise ContractError("blocked_worker_parent_mismatch", "leading session parent thread mismatch")

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
    worker_turn_id = task_started.get("turn_id")
    if not isinstance(worker_turn_id, str) or not worker_turn_id:
        raise ContractError("blocked_worker_task_trace_incomplete", "task_started lacks turn_id")

    turn_contexts = [
        (index, event.get("payload", {}))
        for index, event in enumerate(worker_events)
        if event.get("type") == "turn_context"
    ]
    task_completions = [
        (index, event.get("payload", {}))
        for index, event in enumerate(worker_events)
        if event.get("type") == "event_msg"
        and event.get("payload", {}).get("type") == "task_complete"
    ]
    if len(turn_contexts) != 1 or turn_contexts[0][1].get("turn_id") != worker_turn_id:
        raise ContractError(
            "blocked_worker_turn_mismatch",
            "worker task_started and turn_context do not identify one identical turn",
        )
    if len(task_completions) != 1:
        raise ContractError(
            "blocked_worker_task_trace_incomplete",
            f"expected one task_complete after the latest task_started, found {len(task_completions)}",
        )
    completion_index, completion_payload = task_completions[0]
    if completion_payload.get("turn_id") != worker_turn_id:
        raise ContractError("blocked_worker_turn_mismatch", "task_complete turn_id mismatch")
    if completion_payload.get("last_agent_message") not in {None, ""}:
        raise ContractError("blocked_worker_nonempty_final", "worker task_complete is not empty")

    task_deliveries = [
        (index, event.get("payload", {}))
        for index, event in enumerate(worker_events)
        if event.get("type") == "response_item"
        and event.get("payload", {}).get("type") == "agent_message"
        and event.get("payload", {}).get("recipient") == agent_path
    ]
    if len(task_deliveries) != 1:
        raise ContractError(
            "blocked_worker_task_delivery_mismatch",
            "latest worker task must contain one encrypted delivery addressed to the exact agent path",
        )
    delivery_index, task_delivery = task_deliveries[0]
    trigger_events = [
        (index, event.get("payload", {}))
        for index, event in enumerate(worker_events)
        if event.get("type") == "inter_agent_communication_metadata"
    ]
    if len(trigger_events) != 1 or trigger_events[0][1].get("trigger_turn") is not True:
        raise ContractError(
            "blocked_worker_task_delivery_mismatch",
            "worker task delivery lacks one trigger_turn envelope",
        )
    trigger_index = trigger_events[0][0]
    delivery_content = task_delivery.get("content")
    encrypted_parts = [
        item
        for item in delivery_content
        if isinstance(item, dict) and item.get("type") == "encrypted_content"
    ] if isinstance(delivery_content, list) else []
    delivery_turn_id = task_delivery.get("internal_chat_message_metadata_passthrough", {}).get("turn_id")
    if len(encrypted_parts) != 1 or delivery_turn_id != worker_turn_id:
        raise ContractError(
            "blocked_worker_task_delivery_mismatch",
            "worker task delivery is missing encrypted content or uses a different turn id",
        )
    delivery_ciphertext = encrypted_parts[0].get("encrypted_content")
    if not isinstance(delivery_ciphertext, str) or not delivery_ciphertext:
        raise ContractError(
            "blocked_worker_task_delivery_mismatch",
            "worker task delivery contains no encrypted task body",
        )
    expected_author = agent_path.rsplit("/", 1)[0]
    if task_delivery.get("author") != expected_author:
        raise ContractError(
            "blocked_worker_task_delivery_mismatch",
            "worker task delivery author does not equal the parent agent path",
        )
    header_text = "".join(
        item.get("text", "")
        for item in delivery_content
        if isinstance(item, dict) and item.get("type") == "input_text"
    )
    if not all(
        marker in header_text
        for marker in [
            "Message Type: NEW_TASK",
            f"Task name: {agent_path}",
            f"Sender: {expected_author}",
            "Payload:",
        ]
    ):
        raise ContractError(
            "blocked_worker_task_delivery_mismatch",
            "worker task-delivery header does not bind its task name and sender",
        )

    image_calls: list[tuple[int, dict[str, Any]]] = []
    image_events: list[tuple[int, dict[str, Any]]] = []
    final_agent_messages: list[tuple[int, dict[str, Any]]] = []
    final_response_messages: list[tuple[int, dict[str, Any]]] = []
    for index, event in enumerate(worker_events):
        payload = event.get("payload", {})
        if (
            event.get("type") == "response_item"
            and payload.get("type") == "custom_tool_call"
            and "tools.image_gen__imagegen" in payload.get("input", "")
        ):
            image_calls.append((index, payload))
        if event.get("type") == "event_msg" and payload.get("type") == "image_generation_end":
            image_events.append((index, payload))
        if (
            event.get("type") == "event_msg"
            and payload.get("type") == "agent_message"
            and payload.get("phase") == "final_answer"
        ):
            final_agent_messages.append((index, payload))
        if (
            event.get("type") == "response_item"
            and payload.get("type") == "message"
            and payload.get("role") == "assistant"
            and payload.get("phase") == "final_answer"
        ):
            final_response_messages.append((index, payload))

    if len(image_calls) != 1:
        raise ContractError(
            "blocked_worker_image_call_count",
            f"expected exactly one imagegen call, found {len(image_calls)}",
        )
    if len(image_events) != 1:
        raise ContractError(
            "blocked_worker_image_event_count",
            f"expected exactly one image_generation_end event, found {len(image_events)}",
        )
    if len(final_agent_messages) != 1 or len(final_response_messages) != 1:
        raise ContractError(
            "blocked_worker_final_trace_incomplete",
            "worker must contain one event_msg final and one response_item final",
        )

    call_index, image_call = image_calls[0]
    image_end_index, image_event = image_events[0]
    agent_final_index, agent_final = final_agent_messages[0]
    response_final_index, response_final = final_response_messages[0]
    context_index = turn_contexts[0][0]
    if not (
        0 < context_index < trigger_index < delivery_index < call_index < image_end_index
        and image_end_index < agent_final_index < completion_index
        and image_end_index < response_final_index < completion_index
    ):
        raise ContractError(
            "blocked_worker_event_order",
            "worker events do not follow task/context/user/call/end/empty-final/complete order",
        )
    if agent_final.get("message") not in {None, ""} or response_message_text(response_final) != "":
        raise ContractError("blocked_worker_nonempty_final", "worker emitted non-empty final text")

    call_input = image_call.get("input", "")
    tool_prompt = extract_js_json_value(call_input, "prompt")
    if not isinstance(tool_prompt, str):
        raise ContractError("blocked_worker_call_unparseable", "imagegen prompt is not a string")
    tool_prompt_bytes = tool_prompt.encode("utf-8")
    if tool_prompt_bytes != expected_prompt_bytes:
        raise ContractError(
            "blocked_worker_prompt_mismatch",
            "the prompt sent to imagegen does not exactly match the frozen prompt sidecar",
        )

    if expected_references:
        actual = extract_js_json_value(call_input, "referenced_image_paths")
        if not isinstance(actual, list) or not all(isinstance(item, str) for item in actual):
            raise ContractError(
                "blocked_worker_reference_mismatch",
                "referenced_image_paths is not a string list",
            )
        expected_list = [normalized_path(path) for path in expected_references]
        actual_list = [normalized_path(Path(path)) for path in actual]
        if actual_list != expected_list:
            raise ContractError(
                "blocked_worker_reference_mismatch",
                f"expected ordered references {expected_list!r}, received {actual_list!r}",
            )
    elif not allow_no_references:
        raise ContractError(
            "blocked_worker_reference_contract_missing",
            "production resolution requires a frozen reference manifest",
        )

    if image_event.get("status") != "completed":
        raise ContractError(
            "blocked_worker_generation_failed",
            f"image generation status is {image_event.get('status')!r}",
        )
    call_id = image_event.get("call_id")
    saved_path = image_event.get("saved_path")
    if not isinstance(call_id, str) or not call_id or not isinstance(saved_path, str) or not saved_path:
        raise ContractError(
            "blocked_worker_image_event_incomplete",
            "completed image event lacks call_id or saved_path",
        )
    return {
        "worker_turn_id": worker_turn_id,
        "call_id": call_id,
        "saved_path": saved_path,
        "tool_prompt_sha256": sha256_bytes(tool_prompt_bytes),
        "reference_mode": "frozen_manifest" if expected_references else "none_test_only",
        "worker_task_name": worker_task_name,
        "worker_run_nonce": worker_run_nonce,
        "task_delivery_ciphertext": delivery_ciphertext,
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
        existing_sha = sha256_bytes(destination.read_bytes())
        if existing_sha != expected_sha256:
            raise ContractError(
                "blocked_worker_destination_conflict",
                f"destination exists with different bytes: {destination}",
            )
        return
    shutil.copy2(source, destination)
    copied_sha = sha256_bytes(destination.read_bytes())
    if copied_sha != expected_sha256:
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


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-path", required=True, help="Exact canonical worker path returned by spawn_agent")
    parser.add_argument("--not-before-ms", required=True, type=int, help="Checkpoint captured before worker spawn")
    parser.add_argument("--parent-thread-id", required=True, help="Exact finalizing parent thread id")
    parser.add_argument("--asset-id", required=True, choices=sorted(slug.upper() for slug in SCENE_CANON_ASSET_TASK_SLUGS))
    parser.add_argument("--attempt-id", required=True, help="Exact accepted-attempt candidate id")
    parser.add_argument("--worker-run-nonce", required=True, help="Exact 32-character lowercase hex run nonce")
    parser.add_argument("--expected-prompt", required=True, type=Path)
    parser.add_argument("--reference-manifest", type=Path)
    parser.add_argument("--allow-no-references", action="store_true", help="Test-only; forbidden in production")
    parser.add_argument("--copy-to", required=True, type=Path)
    parser.add_argument("--result-json", required=True, type=Path)
    parser.add_argument("--state-db", type=Path)
    parser.add_argument("--codex-home", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    task_name = validate_worker_name_binding(args.agent_path, args.worker_run_nonce)
    expected_task_name = f"scene_canon_image_{args.asset_id.lower()}_{args.worker_run_nonce}"
    if task_name != expected_task_name:
        raise ContractError("blocked_worker_asset_mismatch", "worker task name does not match --asset-id")
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{3,127}", args.attempt_id):
        raise ContractError("blocked_worker_attempt_invalid", "attempt id must be a stable uppercase identifier")
    if args.reference_manifest is None and not args.allow_no_references:
        raise ContractError(
            "blocked_reference_manifest_missing",
            "production resolution requires --reference-manifest",
        )

    codex_home = args.codex_home or default_codex_home()
    state_db = args.state_db or codex_home / "state_5.sqlite"
    prompt_bytes = args.expected_prompt.read_bytes()
    if prompt_bytes.startswith(b"\xef\xbb\xbf") or b"\r" in prompt_bytes:
        raise ContractError(
            "blocked_generation_prompt_persistence",
            "frozen prompt sidecar must be UTF-8 without BOM and use LF line endings",
        )
    try:
        prompt_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError("blocked_generation_prompt_persistence", str(exc)) from exc

    reference_evidence = (
        load_reference_manifest(args.reference_manifest, args.asset_id)
        if args.reference_manifest is not None
        else {
            "paths": [],
            "manifest_sha256": None,
            "ordered_bundle_sha256": None,
            "reference_count": 0,
        }
    )

    worker = resolve_worker_thread(
        state_db=state_db,
        agent_path=args.agent_path,
        not_before_ms=args.not_before_ms,
        parent_thread_id=args.parent_thread_id,
    )
    rollout_path = Path(str(worker["rollout_path"]).removeprefix("\\\\?\\"))
    worker_events = read_rollout(rollout_path)
    evidence = validate_worker_rollout(
        events=worker_events,
        thread_id=worker["thread_id"],
        agent_path=args.agent_path,
        parent_thread_id=args.parent_thread_id,
        worker_run_nonce=args.worker_run_nonce,
        expected_prompt_bytes=prompt_bytes,
        expected_references=reference_evidence["paths"],
        allow_no_references=args.allow_no_references,
    )
    parent_rollout_path = resolve_thread_rollout(
        state_db,
        args.parent_thread_id,
        "blocked_worker_parent_rollout_unavailable",
    )
    spawn_evidence = validate_parent_spawn_chain(
        read_rollout(parent_rollout_path),
        parent_thread_id=args.parent_thread_id,
        worker_thread_id=worker["thread_id"],
        agent_path=args.agent_path,
        worker_run_nonce=args.worker_run_nonce,
        delivery_ciphertext=evidence["task_delivery_ciphertext"],
        not_before_ms=args.not_before_ms,
    )

    source_path = Path(evidence["saved_path"])
    expected_source = codex_home / "generated_images" / worker["thread_id"] / f"{evidence['call_id']}.png"
    if normalized_path(source_path) != normalized_path(expected_source):
        raise ContractError(
            "blocked_worker_image_path_mismatch",
            f"event path {source_path} does not equal bound path {expected_source}",
        )
    width, height, image_sha = inspect_png(source_path)
    copy_bound_image(source_path, args.copy_to, image_sha)

    result = {
        "ok": True,
        "contract": "delegated_image_worker_result.v3",
        "resolved_at_utc": datetime.now(timezone.utc).isoformat(),
        "agent_path": args.agent_path,
        "asset_id": args.asset_id,
        "attempt_id": args.attempt_id,
        "worker_task_name": evidence["worker_task_name"],
        "worker_run_nonce": evidence["worker_run_nonce"],
        "worker_thread_id": worker["thread_id"],
        "worker_turn_id": evidence["worker_turn_id"],
        "parent_thread_id": worker["parent_thread_id"],
        "worker_rollout_path": str(rollout_path),
        "parent_rollout_path": str(parent_rollout_path),
        "binding_mode": spawn_evidence["binding_mode"],
        "parent_spawn_call_id": spawn_evidence["parent_spawn_call_id"],
        "parent_spawn_turn_id": spawn_evidence["parent_spawn_turn_id"],
        "parent_spawn_activity_ms": int(spawn_evidence["parent_spawn_activity_ms"]),
        "parent_spawn_event_index": spawn_evidence["parent_spawn_event_index"],
        "task_delivery_ciphertext_sha256": spawn_evidence["task_delivery_ciphertext_sha256"],
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
        "reference_mode": evidence["reference_mode"],
        "reference_manifest_path": str(args.reference_manifest) if args.reference_manifest else None,
        "reference_manifest_sha256": reference_evidence["manifest_sha256"],
        "ordered_reference_bundle_sha256": reference_evidence["ordered_bundle_sha256"],
        "reference_count": reference_evidence["reference_count"],
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
