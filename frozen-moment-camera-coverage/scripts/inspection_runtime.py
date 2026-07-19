#!/usr/bin/env python3
"""Freeze and replay main-agent evidence that exact image pixels were opened."""

from __future__ import annotations

import base64
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import resolve_worker_image as runtime


class InspectionRuntimeError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def clean_event(event: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in event.items() if key != "_line"}


def event_sha256(event: dict[str, Any]) -> str:
    return runtime.sha256_bytes(runtime.canonical_json(clean_event(event)))


def parse_timestamp(value: Any, code: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise InspectionRuntimeError(code, "runtime evidence lacks an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InspectionRuntimeError(code, f"invalid runtime timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise InspectionRuntimeError(code, "runtime timestamp must include a timezone")
    return parsed


def _property_name(value: str) -> str:
    name = value.strip()
    if name.startswith('"'):
        try:
            decoded, consumed = runtime.JSON_DECODER.raw_decode(name)
        except json.JSONDecodeError as exc:
            raise InspectionRuntimeError("inspection_runtime_unparseable", "invalid quoted view_image property") from exc
        if consumed != len(name) or not isinstance(decoded, str):
            raise InspectionRuntimeError("inspection_runtime_unparseable", "invalid quoted view_image property")
        return decoded
    if len(name) >= 2 and name[0] == name[-1] == "'":
        return name[1:-1]
    if not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", name):
        raise InspectionRuntimeError("inspection_runtime_unparseable", f"unsupported view_image property: {name!r}")
    return name


def static_view_image_calls(source: str) -> list[dict[str, str]]:
    calls: list[dict[str, str]] = []
    for match in re.finditer(r"(?<![A-Za-z0-9_$])tools\.view_image\s*\(", source):
        object_start = match.end()
        while object_start < len(source) and source[object_start].isspace():
            object_start += 1
        if object_start >= len(source) or source[object_start] != "{":
            continue
        try:
            object_end = runtime.find_matching_js_delimiter(source, object_start, "view_image arguments")
            body = source[object_start + 1 : object_end - 1]
            properties: dict[str, str] = {}
            for segment in runtime.split_js_top_level(body, ",", "view_image arguments"):
                if not segment.strip():
                    continue
                pieces = runtime.split_js_top_level(segment, ":", "view_image arguments")
                if len(pieces) != 2:
                    raise InspectionRuntimeError(
                        "inspection_runtime_unparseable", "view_image arguments must be explicit static properties"
                    )
                name = _property_name(pieces[0])
                if name in properties:
                    raise InspectionRuntimeError("inspection_runtime_unparseable", f"duplicate view_image property: {name}")
                properties[name] = pieces[1].strip()
            if set(properties) != {"path", "detail"}:
                continue
            path = runtime.parse_static_string_expression(properties["path"], "path")
            detail = runtime.parse_static_string_expression(properties["detail"], "detail")
        except (runtime.ContractError, InspectionRuntimeError):
            continue
        if detail == "original":
            calls.append({"path": path, "detail": detail})
    return calls


def decoded_output_images(payload: dict[str, Any]) -> list[dict[str, Any]]:
    output = payload.get("output")
    if not isinstance(output, list):
        return []
    decoded: list[dict[str, Any]] = []
    for index, item in enumerate(output):
        if not isinstance(item, dict) or item.get("type") != "input_image":
            continue
        image_url = item.get("image_url")
        if not isinstance(image_url, str):
            continue
        match = re.fullmatch(r"data:image/[A-Za-z0-9.+-]+;base64,([A-Za-z0-9+/=\r\n]+)", image_url)
        if match is None:
            continue
        try:
            image_bytes = base64.b64decode(match.group(1), validate=True)
        except ValueError:
            continue
        decoded.append(
            {
                "content_index": index,
                "image_sha256": runtime.sha256_bytes(image_bytes),
                "image_byte_count": len(image_bytes),
            }
        )
    return decoded


def find_pixel_open(
    *,
    events: list[dict[str, Any]],
    inspector_thread_id: str,
    image_path: Path,
    image_sha256: str,
    inspected_at_utc: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f-]{27,}", inspector_thread_id):
        raise InspectionRuntimeError("inspection_runtime_identity_invalid", "inspector_task_id must be an exact thread UUID")
    session = next((event for event in events if event.get("type") == "session_meta"), None)
    if not isinstance(session, dict) or session.get("payload", {}).get("id") != inspector_thread_id:
        raise InspectionRuntimeError("inspection_runtime_identity_invalid", "inspector rollout identity mismatch")
    inspected_at = parse_timestamp(inspected_at_utc, "inspection_runtime_time_invalid")
    expected_path = runtime.normalized_path(image_path)
    candidates: list[tuple[int, dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    for call_index, call in enumerate(events):
        payload = call.get("payload", {})
        if (
            call.get("type") != "response_item"
            or payload.get("type") != "custom_tool_call"
            or payload.get("name") != "exec"
            or not isinstance(payload.get("call_id"), str)
        ):
            continue
        calls = static_view_image_calls(payload.get("input", ""))
        if not any(runtime.normalized_path(Path(item["path"])) == expected_path for item in calls):
            continue
        call_time = parse_timestamp(call.get("timestamp"), "inspection_runtime_time_invalid")
        if call_time > inspected_at:
            continue
        outputs = [
            (output_index, output)
            for output_index, output in enumerate(events)
            if output_index > call_index
            and output.get("type") == "response_item"
            and output.get("payload", {}).get("type") == "custom_tool_call_output"
            and output.get("payload", {}).get("call_id") == payload["call_id"]
        ]
        if len(outputs) != 1:
            continue
        output_index, output = outputs[0]
        output_time = parse_timestamp(output.get("timestamp"), "inspection_runtime_time_invalid")
        if output_time > inspected_at:
            continue
        matches = [item for item in decoded_output_images(output.get("payload", {})) if item["image_sha256"] == image_sha256]
        if len(matches) == 1:
            candidates.append((output_index, call, output, matches[0]))
    if not candidates:
        raise InspectionRuntimeError(
            "inspection_runtime_pixel_open_missing",
            "no completed original-detail view_image call exposed the exact bound image bytes before inspection",
        )
    _, call, output, decoded = max(candidates, key=lambda item: item[0])
    call_payload = call["payload"]
    proof = {
        "schema_version": "frozen_moment_pixel_open_receipt.v1",
        "inspector_thread_id": inspector_thread_id,
        "image_path": str(image_path.resolve()),
        "image_sha256": image_sha256,
        "view_detail": "original",
        "exec_call_id": call_payload["call_id"],
        "call_event_source_line": call.get("_line"),
        "output_event_source_line": output.get("_line"),
        "call_at_utc": call.get("timestamp"),
        "output_at_utc": output.get("timestamp"),
        "call_event_sha256": event_sha256(call),
        "output_event_sha256": event_sha256(output),
        "output_content_index": decoded["content_index"],
        "decoded_image_byte_count": decoded["image_byte_count"],
    }
    return proof, [clean_event(session), clean_event(call), clean_event(output)]


def snapshot_bytes(events: list[dict[str, Any]]) -> bytes:
    return b"".join(runtime.canonical_json(event) + b"\n" for event in events)


def replay_receipt(
    *,
    root: Path,
    receipt: dict[str, Any],
    slice_events: list[dict[str, Any]],
    inspector_thread_id: str,
    image_path: Path,
    image_sha256: str,
    inspected_at_utc: str,
) -> None:
    proof, _ = find_pixel_open(
        events=slice_events,
        inspector_thread_id=inspector_thread_id,
        image_path=image_path,
        image_sha256=image_sha256,
        inspected_at_utc=inspected_at_utc,
    )
    for field in (
        "schema_version",
        "inspector_thread_id",
        "image_sha256",
        "view_detail",
        "exec_call_id",
        "call_at_utc",
        "output_at_utc",
        "call_event_sha256",
        "output_event_sha256",
        "output_content_index",
        "decoded_image_byte_count",
    ):
        if receipt.get(field) != proof.get(field):
            raise InspectionRuntimeError("inspection_runtime_receipt_mismatch", f"pixel-open receipt field differs: {field}")
    if runtime.normalized_path(Path(str(receipt.get("image_path", "")))) != runtime.normalized_path(image_path):
        raise InspectionRuntimeError("inspection_runtime_receipt_mismatch", "pixel-open receipt image path differs")
    slice_path = root / str(receipt.get("rollout_slice_path", ""))
    try:
        slice_path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise InspectionRuntimeError("inspection_runtime_receipt_mismatch", "pixel-open slice escapes run root") from exc
    if not slice_path.is_file() or slice_path.is_symlink():
        raise InspectionRuntimeError("inspection_runtime_receipt_mismatch", "pixel-open slice is missing")
    if runtime.sha256_file(slice_path) != receipt.get("rollout_slice_sha256"):
        raise InspectionRuntimeError("inspection_runtime_receipt_mismatch", "pixel-open slice hash differs")
