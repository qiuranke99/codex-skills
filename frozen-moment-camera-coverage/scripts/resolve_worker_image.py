#!/usr/bin/env python3
"""Bind one fresh frozen-coverage worker to its exact prompt, references, call, and PNG."""

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

from PIL import Image, UnidentifiedImageError


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JSON_DECODER = json.JSONDecoder()
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
REFERENCE_ROLES = {
    "moment_anchor", "identity_anchor", "wardrobe_anchor",
    "scene_topology_anchor", "look_anchor",
}
RIGHTS_STATES = {"user_supplied", "owned", "licensed", "public_reference_only", "unknown"}


class ContractError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def normalized_path(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def source_agent_path(source: str) -> tuple[str | None, str | None]:
    try:
        spawn = json.loads(source)["subagent"]["thread_spawn"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None, None
    return spawn.get("agent_path"), spawn.get("parent_thread_id")


def resolve_worker_thread(state_db: Path, agent_path: str, not_before_ms: int, parent_thread_id: str) -> dict[str, Any]:
    if not state_db.is_file():
        raise ContractError("blocked_worker_state_unavailable", f"state database not found: {state_db}")
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(f"file:{state_db.as_posix()}?mode=ro", uri=True)
        rows = connection.execute(
            "SELECT id, rollout_path, created_at, created_at_ms, source FROM threads WHERE source LIKE ?",
            (f"%{agent_path}%",),
        ).fetchall()
    except sqlite3.Error as exc:
        raise ContractError("blocked_worker_state_unavailable", str(exc)) from exc
    finally:
        if connection is not None:
            connection.close()
    matches: list[dict[str, Any]] = []
    for thread_id, rollout_path, created_at, created_at_ms, source in rows:
        exact_path, exact_parent = source_agent_path(source)
        created_ms = created_at_ms if created_at_ms is not None else int(created_at) * 1000
        if exact_path == agent_path and exact_parent == parent_thread_id and created_ms >= not_before_ms:
            matches.append(
                {
                    "thread_id": thread_id,
                    "rollout_path": rollout_path,
                    "created_at_ms": created_ms,
                    "parent_thread_id": exact_parent,
                }
            )
    if not matches:
        raise ContractError("blocked_worker_thread_not_found", f"no fresh worker matched {agent_path!r}")
    if len(matches) != 1:
        raise ContractError("blocked_worker_thread_ambiguous", f"expected one worker, found {[item['thread_id'] for item in matches]}")
    return matches[0]


def resolve_thread_rollout(state_db: Path, thread_id: str, code: str) -> Path:
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(f"file:{state_db.as_posix()}?mode=ro", uri=True)
        rows = connection.execute("SELECT rollout_path FROM threads WHERE id = ?", (thread_id,)).fetchall()
    except sqlite3.Error as exc:
        raise ContractError(code, str(exc)) from exc
    finally:
        if connection is not None:
            connection.close()
    if len(rows) != 1 or not isinstance(rows[0][0], str):
        raise ContractError(code, f"thread rollout not uniquely available: {thread_id}")
    return Path(rows[0][0].removeprefix("\\\\?\\"))


def read_rollout(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ContractError("blocked_worker_rollout_unavailable", f"rollout not found: {path}")
    events: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                value = json.loads(line)
                value["_line"] = line_number
                events.append(value)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("blocked_worker_rollout_unavailable", str(exc)) from exc
    return events


def extract_js_json_value(source: str, key: str) -> Any:
    match = re.search(rf"(?<![A-Za-z0-9_])[\"']?{re.escape(key)}[\"']?\s*:\s*", source)
    if match is None:
        raise ContractError("blocked_worker_call_unparseable", f"missing image-generation argument: {key}")
    try:
        value, _ = JSON_DECODER.raw_decode(source[match.end() :])
    except json.JSONDecodeError as exc:
        raise ContractError("blocked_worker_call_unparseable", f"argument {key} is not a JSON literal: {exc}") from exc
    return value


def response_message_text(payload: dict[str, Any]) -> str:
    content = payload.get("content", "")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "".join(item.get("text", "") for item in content if isinstance(item, dict) and isinstance(item.get("text"), str))


def normalized_view_slug(view_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", view_id.lower()).strip("_")
    if not slug:
        raise ContractError("blocked_worker_view_invalid", f"view id cannot form a task slug: {view_id}")
    return slug


def validate_worker_name_binding(agent_path: str, view_id: str, nonce: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{32}", nonce):
        raise ContractError("blocked_worker_nonce_invalid", "worker nonce must be exactly 32 lowercase hexadecimal characters")
    task_name = agent_path.rsplit("/", 1)[-1]
    expected = f"frozen_coverage_image_{normalized_view_slug(view_id)}_{nonce}"
    if not re.fullmatch(r"[a-z0-9_]+", task_name) or task_name != expected:
        raise ContractError("blocked_worker_nonce_mismatch", f"expected worker task {expected!r}, received {task_name!r}")
    return task_name


def load_reference_manifest(
    path: Path,
    run_id: str,
    view_id: str,
    attempt_id: str,
    source_evidence_sha256: str,
    moment_canon_sha256: str,
    expected_reference_plan_sha256: str,
) -> dict[str, Any]:
    if not path.is_file():
        raise ContractError("blocked_reference_manifest_missing", f"reference manifest missing: {path}")
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ContractError("blocked_reference_manifest_invalid", "reference manifest must be UTF-8/LF without BOM")
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("blocked_reference_manifest_invalid", str(exc)) from exc
    required_keys = {
        "schema_version",
        "run_id",
        "view_id",
        "attempt_id",
        "source_evidence_sha256",
        "moment_canon_sha256",
        "reference_plan_sha256",
        "ordered_references",
        "ordered_bundle_sha256",
        "immutability_contract",
        "provider_reference_count",
    }
    if not isinstance(manifest, dict) or set(manifest) != required_keys:
        raise ContractError("blocked_reference_manifest_invalid", "reference manifest fields are incomplete or unexpected")
    if manifest["schema_version"] != "frozen_moment_reference_bundle.v1":
        raise ContractError("blocked_reference_manifest_invalid", "reference manifest schema mismatch")
    if manifest["run_id"] != run_id or manifest["view_id"] != view_id or manifest["attempt_id"] != attempt_id:
        raise ContractError("blocked_reference_manifest_invalid", "reference manifest targets a different run, view, or attempt")
    if (
        manifest["source_evidence_sha256"] != source_evidence_sha256
        or manifest["moment_canon_sha256"] != moment_canon_sha256
        or manifest["reference_plan_sha256"] != expected_reference_plan_sha256
    ):
        raise ContractError("blocked_reference_manifest_invalid", "reference manifest does not bind the current source, Canon, and prompt plan")
    entries = manifest["ordered_references"]
    synthetic_empty_sha = sha256_bytes(
        canonical_json(
            {
                "schema_version": "frozen_moment_reference_bundle.v1",
                "ordered_references": [],
                "input_mode": "text_anchor",
            }
        )
    )
    empty_text_anchor = (
        entries == []
        and view_id == "V00"
        and expected_reference_plan_sha256 == synthetic_empty_sha
    )
    if (
        not isinstance(entries, list)
        or not 0 <= len(entries) <= 5
        or (not entries and not empty_text_anchor)
        or manifest["provider_reference_count"] != len(entries)
    ):
        raise ContractError("blocked_reference_manifest_invalid", "reference count or empty text-anchor authority is invalid")
    root = path.parent.resolve() / "references"
    if not root.is_dir() or root.is_symlink():
        raise ContractError("blocked_reference_manifest_location", "run-scoped reference directory is invalid")
    verified_paths: list[Path] = []
    aliases: set[str] = set()
    ids: set[str] = set()
    planned: list[dict[str, Any]] = []
    for expected_index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            raise ContractError("blocked_reference_manifest_invalid", "reference entry must be an object")
        if entry.get("index") != expected_index:
            raise ContractError("blocked_reference_manifest_invalid", "reference indexes must be contiguous and ordered")
        alias = entry.get("alias")
        reference_id = entry.get("reference_id")
        role = entry.get("role")
        frozen_raw = entry.get("frozen_path")
        if not all(isinstance(item, str) and item for item in (alias, reference_id, role, frozen_raw)) or role not in REFERENCE_ROLES:
            raise ContractError("blocked_reference_manifest_invalid", "reference identity fields are invalid")
        if alias in aliases or reference_id in ids:
            raise ContractError("blocked_reference_manifest_invalid", "reference aliases and IDs must be unique")
        aliases.add(alias)
        ids.add(reference_id)
        if expected_index == 1 and role != "moment_anchor":
            raise ContractError("blocked_reference_manifest_invalid", "reference 1 must be moment_anchor")
        expected_authority = "source_anchor"
        source_path = entry.get("source_path")
        if (
            entry.get("authority_class") != expected_authority
            or entry.get("source_record_id") != reference_id
            or not isinstance(source_path, str)
            or not Path(source_path).is_absolute()
            or entry.get("rights_state") not in RIGHTS_STATES
            or not isinstance(entry.get("scope_include"), str)
            or not entry["scope_include"]
            or not isinstance(entry.get("scope_exclude"), str)
            or not entry["scope_exclude"]
        ):
            raise ContractError("blocked_reference_manifest_invalid", "reference authority, source, rights, or scope is invalid")
        frozen = Path(frozen_raw)
        if not frozen.is_absolute() or frozen.is_symlink():
            raise ContractError("blocked_reference_manifest_location", f"invalid frozen reference path: {frozen}")
        try:
            frozen.resolve().relative_to(root)
        except ValueError as exc:
            raise ContractError("blocked_reference_manifest_location", f"frozen reference escapes run root: {frozen}") from exc
        if not frozen.is_file():
            raise ContractError("blocked_reference_bytes_changed", f"frozen reference missing: {frozen}")
        expected_sha = entry.get("sha256")
        if not isinstance(expected_sha, str) or not SHA_RE.fullmatch(expected_sha):
            raise ContractError("blocked_reference_manifest_invalid", "reference hash invalid")
        if frozen.stat().st_size != entry.get("size_bytes") or sha256_file(frozen) != expected_sha:
            raise ContractError("blocked_reference_bytes_changed", f"reference bytes changed: {frozen}")
        try:
            with Image.open(frozen) as image:
                image.verify()
                image_format = image.format
        except (OSError, UnidentifiedImageError) as exc:
            raise ContractError("blocked_reference_bytes_changed", f"reference is not a decodable image: {frozen}: {exc}") from exc
        if image_format != entry.get("media_format") or image_format not in {"PNG", "JPEG", "WEBP"}:
            raise ContractError("blocked_reference_manifest_invalid", f"reference media format is invalid: {frozen}")
        if any(entry.get(field) is not None for field in ("origin_view_id", "origin_attempt_id", "origin_inspection_sha256", "origin_inspection_path")):
            raise ContractError("blocked_reference_manifest_invalid", "v1 references cannot carry generated bridge origins")
        planned.append(
            {
                "index": expected_index,
                "reference_id": reference_id,
                "role": role,
                "source_path": entry.get("source_path"),
                "rights_state": entry.get("rights_state"),
                "bridge_origin": None,
            }
        )
        verified_paths.append(frozen)
    actual_files = {normalized_path(item) for item in root.iterdir() if item.is_file()}
    expected_files = {normalized_path(item) for item in verified_paths}
    if any(item.is_dir() for item in root.iterdir()) or actual_files != expected_files:
        raise ContractError("blocked_reference_manifest_invalid", "reference directory contains missing, extra, or nested files")
    if sha256_bytes(canonical_json(entries)) != manifest["ordered_bundle_sha256"]:
        raise ContractError("blocked_reference_manifest_hash_mismatch", "ordered bundle digest mismatch")
    computed_plan_sha = sha256_bytes(canonical_json(planned)) if planned else synthetic_empty_sha
    if computed_plan_sha != manifest["reference_plan_sha256"]:
        raise ContractError("blocked_reference_manifest_hash_mismatch", "reference plan digest mismatch")
    return {
        "paths": verified_paths,
        "manifest_sha256": sha256_bytes(raw),
        "ordered_bundle_sha256": manifest["ordered_bundle_sha256"],
        "reference_plan_sha256": manifest["reference_plan_sha256"],
        "reference_count": len(verified_paths),
    }


def validate_worker_rollout(
    *,
    events: list[dict[str, Any]],
    thread_id: str,
    agent_path: str,
    parent_thread_id: str,
    view_id: str,
    nonce: str,
    expected_prompt_bytes: bytes,
    expected_references: list[Path],
) -> dict[str, Any]:
    task_name = validate_worker_name_binding(agent_path, view_id, nonce)
    if not events or events[0].get("type") != "session_meta":
        raise ContractError("blocked_worker_session_mismatch", "worker rollout lacks leading session metadata")
    session = events[0].get("payload", {})
    if session.get("id") != thread_id or session.get("agent_path") != agent_path:
        raise ContractError("blocked_worker_session_mismatch", "worker session identity mismatch")
    if session.get("parent_thread_id") != parent_thread_id:
        raise ContractError("blocked_worker_parent_mismatch", "worker parent mismatch")
    task_starts = [index for index, event in enumerate(events) if event.get("type") == "event_msg" and event.get("payload", {}).get("type") == "task_started"]
    if not task_starts:
        raise ContractError("blocked_worker_task_trace_missing", "worker has no task_started event")
    worker_events = events[task_starts[-1] :]
    worker_turn_id = worker_events[0].get("payload", {}).get("turn_id")
    if not isinstance(worker_turn_id, str) or not worker_turn_id:
        raise ContractError("blocked_worker_task_trace_incomplete", "task_started lacks a turn id")
    contexts = [(i, event.get("payload", {})) for i, event in enumerate(worker_events) if event.get("type") == "turn_context"]
    completions = [
        (i, event.get("payload", {}))
        for i, event in enumerate(worker_events)
        if event.get("type") == "event_msg" and event.get("payload", {}).get("type") == "task_complete"
    ]
    if len(contexts) != 1 or contexts[0][1].get("turn_id") != worker_turn_id or len(completions) != 1:
        raise ContractError("blocked_worker_turn_mismatch", "worker does not contain one matching context and completion")
    completion_index, completion = completions[0]
    if completion.get("turn_id") != worker_turn_id or completion.get("last_agent_message") not in {None, ""}:
        raise ContractError("blocked_worker_nonempty_final", "worker completion is non-empty or belongs to another turn")
    deliveries = [
        (i, event.get("payload", {}))
        for i, event in enumerate(worker_events)
        if event.get("type") == "response_item"
        and event.get("payload", {}).get("type") == "agent_message"
        and event.get("payload", {}).get("recipient") == agent_path
    ]
    triggers = [(i, event.get("payload", {})) for i, event in enumerate(worker_events) if event.get("type") == "inter_agent_communication_metadata"]
    if len(deliveries) != 1 or len(triggers) != 1 or triggers[0][1].get("trigger_turn") is not True:
        raise ContractError("blocked_worker_task_delivery_mismatch", "worker lacks one exact triggered task delivery")
    delivery_index, delivery = deliveries[0]
    content = delivery.get("content")
    encrypted = [item for item in content if isinstance(item, dict) and item.get("type") == "encrypted_content"] if isinstance(content, list) else []
    if len(encrypted) != 1 or delivery.get("internal_chat_message_metadata_passthrough", {}).get("turn_id") != worker_turn_id:
        raise ContractError("blocked_worker_task_delivery_mismatch", "task delivery lacks one encrypted body for this turn")
    ciphertext = encrypted[0].get("encrypted_content")
    if not isinstance(ciphertext, str) or not ciphertext:
        raise ContractError("blocked_worker_task_delivery_mismatch", "task delivery ciphertext is empty")
    expected_author = agent_path.rsplit("/", 1)[0]
    header = "".join(item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "input_text")
    if delivery.get("author") != expected_author or not all(
        marker in header
        for marker in ("Message Type: NEW_TASK", f"Task name: {agent_path}", f"Sender: {expected_author}", "Payload:")
    ):
        raise ContractError("blocked_worker_task_delivery_mismatch", "task delivery does not bind parent and worker")
    image_calls = [
        (i, event.get("payload", {}))
        for i, event in enumerate(worker_events)
        if event.get("type") == "response_item"
        and event.get("payload", {}).get("type") == "custom_tool_call"
        and "tools.image_gen__imagegen" in event.get("payload", {}).get("input", "")
    ]
    image_events = [
        (i, event.get("payload", {}))
        for i, event in enumerate(worker_events)
        if event.get("type") == "event_msg" and event.get("payload", {}).get("type") == "image_generation_end"
    ]
    tool_calls = [
        event
        for event in worker_events
        if event.get("type") == "response_item"
        and event.get("payload", {}).get("type") in {"function_call", "custom_tool_call"}
    ]
    final_events = [
        (i, event.get("payload", {}))
        for i, event in enumerate(worker_events)
        if event.get("type") == "event_msg"
        and event.get("payload", {}).get("type") == "agent_message"
        and event.get("payload", {}).get("phase") == "final_answer"
    ]
    final_responses = [
        (i, event.get("payload", {}))
        for i, event in enumerate(worker_events)
        if event.get("type") == "response_item"
        and event.get("payload", {}).get("type") == "message"
        and event.get("payload", {}).get("role") == "assistant"
        and event.get("payload", {}).get("phase") == "final_answer"
    ]
    if len(image_calls) != 1 or len(image_events) != 1:
        raise ContractError("blocked_worker_image_call_count", f"expected one image call/end, found {len(image_calls)}/{len(image_events)}")
    if len(tool_calls) != 1 or tool_calls[0].get("payload") != image_calls[0][1]:
        raise ContractError("blocked_worker_tool_violation", "image worker used a tool other than its single image call")
    if len(final_events) != 1 or len(final_responses) != 1:
        raise ContractError("blocked_worker_final_trace_incomplete", "worker lacks one empty final event and response")
    call_index, image_call = image_calls[0]
    end_index, image_event = image_events[0]
    event_final_index, event_final = final_events[0]
    response_final_index, response_final = final_responses[0]
    context_index = contexts[0][0]
    trigger_index = triggers[0][0]
    if not (
        0 < context_index < trigger_index < delivery_index < call_index < end_index
        and end_index < event_final_index < completion_index
        and end_index < response_final_index < completion_index
    ):
        raise ContractError("blocked_worker_event_order", "worker event order is not context/delivery/call/end/empty-final/complete")
    if event_final.get("message") not in {None, ""} or response_message_text(response_final) != "":
        raise ContractError("blocked_worker_nonempty_final", "worker emitted final text")
    call_input = image_call.get("input", "")
    prompt = extract_js_json_value(call_input, "prompt")
    if not isinstance(prompt, str) or prompt.encode("utf-8") != expected_prompt_bytes:
        raise ContractError("blocked_worker_prompt_mismatch", "tool prompt does not exactly match frozen prompt bytes")
    if expected_references:
        references = extract_js_json_value(call_input, "referenced_image_paths")
        if not isinstance(references, list) or not all(isinstance(item, str) for item in references):
            raise ContractError("blocked_worker_reference_mismatch", "referenced_image_paths must be a string list")
    else:
        if "referenced_image_paths" in call_input:
            raise ContractError("blocked_worker_reference_mismatch", "empty text-anchor generation must omit referenced_image_paths")
        references = []
    if [normalized_path(Path(item)) for item in references] != [normalized_path(item) for item in expected_references]:
        raise ContractError("blocked_worker_reference_mismatch", "tool reference order differs from frozen manifest")
    if image_event.get("status") != "completed":
        raise ContractError("blocked_worker_generation_failed", f"generation ended with {image_event.get('status')!r}")
    call_id = image_event.get("call_id")
    saved_path = image_event.get("saved_path")
    if not isinstance(call_id, str) or not call_id or not isinstance(saved_path, str) or not saved_path:
        raise ContractError("blocked_worker_image_event_incomplete", "completed image event lacks call id or saved path")
    return {
        "worker_task_name": task_name,
        "worker_turn_id": worker_turn_id,
        "call_id": call_id,
        "saved_path": saved_path,
        "tool_prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "task_delivery_ciphertext": ciphertext,
    }


def validate_parent_spawn_chain(
    *,
    events: list[dict[str, Any]],
    parent_thread_id: str,
    worker_thread_id: str,
    agent_path: str,
    view_id: str,
    nonce: str,
    ciphertext: str,
    not_before_ms: int,
) -> dict[str, Any]:
    task_name = validate_worker_name_binding(agent_path, view_id, nonce)
    if not events or events[0].get("type") != "session_meta" or events[0].get("payload", {}).get("id") != parent_thread_id:
        raise ContractError("blocked_worker_spawn_chain_mismatch", "parent rollout identity mismatch")
    calls: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for index, event in enumerate(events):
        payload = event.get("payload", {})
        if event.get("type") != "response_item" or payload.get("type") != "function_call" or payload.get("name") != "spawn_agent":
            continue
        try:
            arguments = json.loads(payload.get("arguments", ""))
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(arguments, dict) and arguments.get("task_name") == task_name:
            calls.append((index, payload, arguments))
    if len(calls) != 1:
        raise ContractError("blocked_worker_spawn_chain_mismatch", f"expected one parent spawn for {task_name}, found {len(calls)}")
    spawn_index, spawn, arguments = calls[0]
    spawn_call_id = spawn.get("call_id")
    parent_turn_id = spawn.get("internal_chat_message_metadata_passthrough", {}).get("turn_id")
    if not isinstance(spawn_call_id, str) or arguments.get("fork_turns") != "none" or arguments.get("message") != ciphertext:
        raise ContractError("blocked_worker_spawn_chain_mismatch", "spawn lacks fork_turns=none or exact encrypted task body")
    activities = [
        (i, event.get("payload", {}))
        for i, event in enumerate(events)
        if event.get("type") == "event_msg"
        and event.get("payload", {}).get("type") == "sub_agent_activity"
        and event.get("payload", {}).get("event_id") == spawn_call_id
    ]
    outputs = [
        (i, event.get("payload", {}))
        for i, event in enumerate(events)
        if event.get("type") == "response_item"
        and event.get("payload", {}).get("type") == "function_call_output"
        and event.get("payload", {}).get("call_id") == spawn_call_id
    ]
    start_activities = [(index, value) for index, value in activities if value.get("kind") == "started"]
    completed_activities = [
        (index, value)
        for index, event in enumerate(events)
        if event.get("type") == "event_msg"
        and (value := event.get("payload", {})).get("type") == "sub_agent_activity"
        and value.get("kind") in {"completed", "finished"}
        and value.get("agent_thread_id") == worker_thread_id
        and value.get("agent_path") == agent_path
    ]
    if len(start_activities) != 1 or len(completed_activities) != 1 or len(outputs) != 1:
        raise ContractError("blocked_worker_spawn_chain_mismatch", "spawn lacks one start, completion, and output")
    activity_index, activity = start_activities[0]
    completion_activity_index, completion_activity = completed_activities[0]
    output_index, output = outputs[0]
    try:
        output_value = json.loads(output.get("output", ""))
    except (json.JSONDecodeError, TypeError) as exc:
        raise ContractError("blocked_worker_spawn_chain_mismatch", str(exc)) from exc
    if not (
        spawn_index < activity_index
        and spawn_index < output_index
        and activity_index < completion_activity_index
        and activity.get("kind") == "started"
        and isinstance(activity.get("occurred_at_ms"), int)
        and activity["occurred_at_ms"] >= not_before_ms
        and activity.get("agent_thread_id") == worker_thread_id
        and activity.get("agent_path") == agent_path
        and isinstance(completion_activity.get("occurred_at_ms"), int)
        and completion_activity["occurred_at_ms"] >= activity["occurred_at_ms"]
        and isinstance(parent_turn_id, str)
        and parent_turn_id
        and output.get("internal_chat_message_metadata_passthrough", {}).get("turn_id") == parent_turn_id
        and isinstance(output_value, dict)
        and output_value.get("task_name") == agent_path
    ):
        raise ContractError("blocked_worker_spawn_chain_mismatch", "spawn, activity, output, thread, and path do not form one chain")
    result = {
        "binding_mode": "parent_spawn_cipher_chain_v1",
        "parent_spawn_call_id": spawn_call_id,
        "parent_spawn_turn_id": parent_turn_id,
        "parent_spawn_activity_ms": activity["occurred_at_ms"],
        "parent_spawn_event_index": spawn_index,
        "parent_completion_event_index": completion_activity_index,
        "parent_completion_activity_ms": completion_activity.get("occurred_at_ms"),
        "task_delivery_ciphertext_sha256": sha256_bytes(ciphertext.encode("utf-8")),
    }
    result["parent_spawn_chain_sha256"] = sha256_bytes(canonical_json(result))
    return result


def inspect_png(path: Path) -> tuple[int, int, str]:
    if not path.is_file():
        raise ContractError("blocked_worker_image_missing", f"generated image missing: {path}")
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != PNG_SIGNATURE or data[12:16] != b"IHDR":
        raise ContractError("blocked_worker_image_invalid", f"generated file is not a valid PNG: {path}")
    width, height = struct.unpack(">II", data[16:24])
    if width <= 0 or height <= 0:
        raise ContractError("blocked_worker_image_invalid", "generated PNG dimensions are invalid")
    return width, height, sha256_bytes(data)


def copy_bound_image(source: Path, destination: Path, expected_sha: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256_file(destination) != expected_sha:
            raise ContractError("blocked_worker_destination_conflict", f"destination has different bytes: {destination}")
        return
    shutil.copy2(source, destination)
    if sha256_file(destination) != expected_sha:
        raise ContractError("blocked_worker_copy_mismatch", "copied image digest differs from source")


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def load_coverage_contract(path: Path, run_id: str, view_id: str, expected_prompt: Path) -> dict[str, Any]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ContractError("blocked_coverage_contract_invalid", f"coverage manifest path is invalid: {path}")
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ContractError("blocked_coverage_contract_invalid", "coverage manifest must be UTF-8/LF without BOM")
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("blocked_coverage_contract_invalid", str(exc)) from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "frozen_moment_coverage_manifest.v1":
        raise ContractError("blocked_coverage_contract_invalid", "coverage manifest schema is invalid")
    if manifest.get("job", {}).get("job_id") != run_id:
        raise ContractError("blocked_coverage_contract_invalid", "coverage manifest run_id differs")
    source = manifest.get("source_evidence")
    moment = manifest.get("moment_canon")
    if not isinstance(source, dict) or not isinstance(moment, dict):
        raise ContractError("blocked_coverage_contract_invalid", "coverage source or Canon is missing")
    expected_source_sha = sha256_bytes(canonical_json({key: value for key, value in source.items() if key != "source_evidence_sha256"}))
    expected_moment_sha = sha256_bytes(canonical_json({key: value for key, value in moment.items() if key != "moment_canon_sha256"}))
    if source.get("source_evidence_sha256") != expected_source_sha or moment.get("moment_canon_sha256") != expected_moment_sha:
        raise ContractError("blocked_coverage_contract_invalid", "coverage source or Canon digest differs")
    contract = {
        key: manifest[key]
        for key in (
            "schema_version", "job", "source_evidence", "evidence_ledger", "moment_canon",
            "camera_families", "prompts", "prompt_set_sha256",
        )
    }
    contract["views"] = [
        {key: value for key, value in view.items() if key != "status"}
        for view in manifest["views"]
    ]
    expected_contract_sha = sha256_bytes(canonical_json(contract))
    if manifest.get("coverage_contract_sha256") != expected_contract_sha:
        raise ContractError("blocked_coverage_contract_invalid", "coverage contract digest differs")
    prompt = next((item for item in manifest.get("prompts", []) if item.get("view_id") == view_id), None)
    if not isinstance(prompt, dict):
        raise ContractError("blocked_coverage_contract_invalid", f"coverage prompt is missing for {view_id}")
    run_root = path.parent.parent.resolve()
    prompt_path = (run_root / prompt.get("prompt_path", "")).resolve()
    if prompt_path != expected_prompt.resolve() or not prompt_path.is_file() or sha256_file(prompt_path) != prompt.get("prompt_sha256"):
        raise ContractError("blocked_coverage_contract_invalid", "expected prompt does not match the frozen coverage prompt")
    return {
        "manifest": manifest,
        "manifest_bytes": raw,
        "manifest_sha256": sha256_bytes(raw),
        "run_root": run_root,
        "source_evidence_sha256": expected_source_sha,
        "moment_canon_sha256": expected_moment_sha,
        "coverage_contract_sha256": expected_contract_sha,
        "prompt_sha256": prompt["prompt_sha256"],
        "reference_plan_sha256": prompt["reference_plan_sha256"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-path", required=True)
    parser.add_argument("--not-before-ms", required=True, type=int)
    parser.add_argument("--parent-thread-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--view-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--attempt-revision", type=int, default=1)
    parser.add_argument("--worker-run-nonce", required=True)
    parser.add_argument("--coverage-manifest", required=True, type=Path)
    parser.add_argument("--expected-prompt", required=True, type=Path)
    parser.add_argument("--reference-manifest", required=True, type=Path)
    parser.add_argument("--copy-to", required=True, type=Path)
    parser.add_argument("--result-json", required=True, type=Path)
    parser.add_argument("--state-db", type=Path)
    parser.add_argument("--codex-home", type=Path)
    return parser


def resolve(args: argparse.Namespace) -> dict[str, Any]:
    view_id = args.view_id.upper()
    task_name = validate_worker_name_binding(args.agent_path, view_id, args.worker_run_nonce)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,127}", args.attempt_id):
        raise ContractError("blocked_worker_attempt_invalid", "attempt id is invalid")
    if not isinstance(args.attempt_revision, int) or args.attempt_revision < 1:
        raise ContractError("blocked_worker_attempt_invalid", "attempt revision must be positive")
    coverage = load_coverage_contract(args.coverage_manifest.resolve(), args.run_id, view_id, args.expected_prompt)
    for path, label in (
        (args.reference_manifest.resolve(), "reference manifest"),
        (args.copy_to.resolve(), "bound image"),
        (args.result_json.resolve(), "worker result"),
    ):
        try:
            path.relative_to(coverage["run_root"])
        except ValueError as exc:
            raise ContractError("blocked_worker_destination_conflict", f"{label} must remain inside the run root") from exc
    prompt_bytes = args.expected_prompt.read_bytes()
    if prompt_bytes.startswith(b"\xef\xbb\xbf") or b"\r" in prompt_bytes:
        raise ContractError("blocked_generation_prompt_persistence", "prompt must be UTF-8/LF without BOM")
    try:
        prompt_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError("blocked_generation_prompt_persistence", str(exc)) from exc
    references = load_reference_manifest(
        args.reference_manifest,
        args.run_id,
        view_id,
        args.attempt_id,
        coverage["source_evidence_sha256"],
        coverage["moment_canon_sha256"],
        coverage["reference_plan_sha256"],
    )
    codex_home = (args.codex_home or default_codex_home()).resolve()
    state_db = args.state_db or codex_home / "state_5.sqlite"
    worker = resolve_worker_thread(state_db, args.agent_path, args.not_before_ms, args.parent_thread_id)
    worker_rollout = Path(str(worker["rollout_path"]).removeprefix("\\\\?\\"))
    worker_evidence = validate_worker_rollout(
        events=read_rollout(worker_rollout),
        thread_id=worker["thread_id"],
        agent_path=args.agent_path,
        parent_thread_id=args.parent_thread_id,
        view_id=view_id,
        nonce=args.worker_run_nonce,
        expected_prompt_bytes=prompt_bytes,
        expected_references=references["paths"],
    )
    parent_rollout = resolve_thread_rollout(state_db, args.parent_thread_id, "blocked_worker_parent_rollout_unavailable")
    spawn = validate_parent_spawn_chain(
        events=read_rollout(parent_rollout),
        parent_thread_id=args.parent_thread_id,
        worker_thread_id=worker["thread_id"],
        agent_path=args.agent_path,
        view_id=view_id,
        nonce=args.worker_run_nonce,
        ciphertext=worker_evidence["task_delivery_ciphertext"],
        not_before_ms=args.not_before_ms,
    )
    source = Path(worker_evidence["saved_path"])
    expected_source = codex_home / "generated_images" / worker["thread_id"] / f"{worker_evidence['call_id']}.png"
    if normalized_path(source) != normalized_path(expected_source):
        raise ContractError("blocked_worker_image_path_mismatch", f"event path {source} differs from bound path {expected_source}")
    width, height, image_sha = inspect_png(source)
    copy_bound_image(source, args.copy_to, image_sha)
    coverage_snapshot = args.result_json.resolve().with_name("coverage-manifest-at-resolution.json")
    coverage_snapshot.parent.mkdir(parents=True, exist_ok=True)
    if coverage_snapshot.exists():
        if coverage_snapshot.is_symlink() or coverage_snapshot.read_bytes() != coverage["manifest_bytes"]:
            raise ContractError("blocked_worker_destination_conflict", "coverage snapshot has different bytes")
    else:
        coverage_snapshot.write_bytes(coverage["manifest_bytes"])
    parent_snapshot = args.result_json.resolve().with_name("parent-rollout-at-resolution.jsonl")
    parent_bytes = parent_rollout.read_bytes()
    if parent_snapshot.exists():
        if parent_snapshot.is_symlink() or parent_snapshot.read_bytes() != parent_bytes:
            raise ContractError("blocked_worker_destination_conflict", "parent rollout snapshot has different bytes")
    else:
        parent_snapshot.write_bytes(parent_bytes)
    result = {
        "schema_version": "frozen_moment_view_worker_result.v1",
        "ok": True,
        "resolved_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_id,
        "view_id": view_id,
        "attempt_id": args.attempt_id,
        "attempt_revision": args.attempt_revision,
        "agent_path": args.agent_path,
        "worker_task_name": task_name,
        "worker_run_nonce": args.worker_run_nonce,
        "not_before_ms": args.not_before_ms,
        "parent_thread_id": args.parent_thread_id,
        "parent_rollout_path": str(parent_snapshot),
        "parent_source_rollout_path": str(parent_rollout),
        "parent_rollout_sha256": sha256_file(parent_snapshot),
        "parent_spawn_call_id": spawn["parent_spawn_call_id"],
        "parent_spawn_turn_id": spawn["parent_spawn_turn_id"],
        "parent_spawn_event_index": spawn["parent_spawn_event_index"],
        "parent_spawn_activity_ms": spawn["parent_spawn_activity_ms"],
        "parent_completion_event_index": spawn["parent_completion_event_index"],
        "parent_completion_activity_ms": spawn["parent_completion_activity_ms"],
        "binding_mode": spawn["binding_mode"],
        "parent_spawn_chain_sha256": spawn["parent_spawn_chain_sha256"],
        "task_delivery_ciphertext_sha256": spawn["task_delivery_ciphertext_sha256"],
        "worker_thread_id": worker["thread_id"],
        "worker_turn_id": worker_evidence["worker_turn_id"],
        "worker_rollout_path": str(worker_rollout),
        "worker_rollout_sha256": sha256_file(worker_rollout),
        "image_generation_call_id": worker_evidence["call_id"],
        "worker_saved_path": str(source),
        "run_image_path": str(args.copy_to.resolve()),
        "image_sha256": image_sha,
        "width_px": width,
        "height_px": height,
        "format": "PNG",
        "coverage_manifest_path": str(args.coverage_manifest.resolve()),
        "coverage_manifest_snapshot_path": str(coverage_snapshot),
        "coverage_manifest_sha256_at_resolution": coverage["manifest_sha256"],
        "coverage_contract_sha256": coverage["coverage_contract_sha256"],
        "source_evidence_sha256": coverage["source_evidence_sha256"],
        "moment_canon_sha256": coverage["moment_canon_sha256"],
        "generation_prompt_path": str(args.expected_prompt.resolve()),
        "generation_prompt_sha256": sha256_bytes(prompt_bytes),
        "tool_prompt_sha256": worker_evidence["tool_prompt_sha256"],
        "prompt_binding_mode": "exact_bytes",
        "prompt_sha_match": worker_evidence["tool_prompt_sha256"] == sha256_bytes(prompt_bytes),
        "reference_manifest_path": str(args.reference_manifest.resolve()),
        "reference_manifest_sha256": references["manifest_sha256"],
        "reference_plan_sha256": references["reference_plan_sha256"],
        "ordered_reference_bundle_sha256": references["ordered_bundle_sha256"],
        "reference_count": references["reference_count"],
        "reference_bytes_verified": True,
    }
    write_json_atomic(args.result_json, result)
    return result


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = resolve(args)
    except ContractError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}, ensure_ascii=False), file=sys.stderr)
        return 2
    except OSError as exc:
        print(json.dumps({"ok": False, "error_code": "blocked_worker_filesystem", "detail": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
