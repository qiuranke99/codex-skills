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


def decode_static_js_template_literal_token(
    source: str,
    key: str,
    *,
    raw: bool = False,
) -> tuple[str, int]:
    if not source.startswith("`"):
        raise ContractError("blocked_worker_call_unparseable", f"argument {key} is not a template literal")
    output: list[str] = []
    index = 1
    simple_escapes = {
        "`": "`",
        "\\": "\\",
        "$": "$",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "b": "\b",
        "f": "\f",
        "v": "\v",
        "0": "\0",
    }
    while index < len(source):
        character = source[index]
        if character == "`":
            return "".join(output), index + 1
        if character == "$" and index + 1 < len(source) and source[index + 1] == "{":
            raise ContractError(
                "blocked_worker_call_unparseable",
                f"argument {key} contains dynamic template interpolation",
            )
        if raw:
            if character == "\\" and index + 1 < len(source) and source[index + 1] == "`":
                output.extend(("\\", "`"))
                index += 2
                continue
            output.append(character)
            index += 1
            continue
        if character != "\\":
            output.append(character)
            index += 1
            continue
        index += 1
        if index >= len(source):
            break
        escaped = source[index]
        if escaped in {"\n", "\r"}:
            if escaped == "\r" and index + 1 < len(source) and source[index + 1] == "\n":
                index += 1
            index += 1
            continue
        if escaped in simple_escapes:
            if escaped == "0" and index + 1 < len(source) and source[index + 1].isdigit():
                raise ContractError(
                    "blocked_worker_call_unparseable",
                    f"argument {key} contains an ambiguous numeric escape",
                )
            output.append(simple_escapes[escaped])
            index += 1
            continue
        if escaped == "x":
            digits = source[index + 1 : index + 3]
            if len(digits) != 2 or not re.fullmatch(r"[0-9A-Fa-f]{2}", digits):
                raise ContractError("blocked_worker_call_unparseable", f"argument {key} has an invalid hex escape")
            output.append(chr(int(digits, 16)))
            index += 3
            continue
        if escaped == "u":
            if index + 1 < len(source) and source[index + 1] == "{":
                close = source.find("}", index + 2)
                digits = source[index + 2 : close] if close != -1 else ""
                if not digits or not re.fullmatch(r"[0-9A-Fa-f]{1,6}", digits):
                    raise ContractError("blocked_worker_call_unparseable", f"argument {key} has an invalid Unicode escape")
                codepoint = int(digits, 16)
                if codepoint > 0x10FFFF or 0xD800 <= codepoint <= 0xDFFF:
                    raise ContractError("blocked_worker_call_unparseable", f"argument {key} has an invalid Unicode codepoint")
                output.append(chr(codepoint))
                index = close + 1
                continue
            digits = source[index + 1 : index + 5]
            if len(digits) != 4 or not re.fullmatch(r"[0-9A-Fa-f]{4}", digits):
                raise ContractError("blocked_worker_call_unparseable", f"argument {key} has an invalid Unicode escape")
            codepoint = int(digits, 16)
            if 0xD800 <= codepoint <= 0xDFFF:
                raise ContractError("blocked_worker_call_unparseable", f"argument {key} has an unsupported surrogate escape")
            output.append(chr(codepoint))
            index += 5
            continue
        raise ContractError(
            "blocked_worker_call_unparseable",
            f"argument {key} contains an unsupported template escape: \\{escaped}",
        )
    raise ContractError("blocked_worker_call_unparseable", f"argument {key} has an unterminated template literal")


def decode_static_js_template_literal(source: str, key: str) -> str:
    value, _ = decode_static_js_template_literal_token(source, key)
    return value


def mask_js_literals(source: str) -> str:
    """Mask JS string/template bodies while preserving offsets and line endings."""
    masked = list(source)
    index = 0
    while index < len(source):
        quote = source[index]
        if quote not in {"'", '"', "`"}:
            index += 1
            continue
        masked[index] = " "
        index += 1
        while index < len(source):
            character = source[index]
            if character in {"\r", "\n"}:
                index += 1
                continue
            masked[index] = " "
            if character == "\\":
                index += 1
                if index < len(source):
                    if source[index] not in {"\r", "\n"}:
                        masked[index] = " "
                    index += 1
                continue
            if character == quote:
                index += 1
                break
            index += 1
        else:
            raise ContractError("blocked_worker_call_unparseable", "unterminated JavaScript literal")
    return "".join(masked)


def find_matching_js_delimiter(source: str, start: int, key: str) -> int:
    pairs = {"{": "}", "[": "]", "(": ")"}
    if start >= len(source) or source[start] not in pairs:
        raise ContractError("blocked_worker_call_unparseable", f"argument {key} lacks a static container")
    stack = [source[start]]
    index = start + 1
    while index < len(source):
        character = source[index]
        if character in {"'", '"', "`"}:
            quote = character
            index += 1
            while index < len(source):
                character = source[index]
                if quote == "`" and character == "$" and index + 1 < len(source) and source[index + 1] == "{":
                    raise ContractError(
                        "blocked_worker_call_unparseable",
                        f"argument {key} contains dynamic template interpolation",
                    )
                if character == "\\":
                    index += 2
                    continue
                index += 1
                if character == quote:
                    break
            else:
                raise ContractError("blocked_worker_call_unparseable", f"argument {key} has an unterminated literal")
            continue
        if character in pairs:
            stack.append(character)
        elif character in pairs.values():
            if not stack or pairs[stack[-1]] != character:
                raise ContractError("blocked_worker_call_unparseable", f"argument {key} has mismatched delimiters")
            stack.pop()
            if not stack:
                return index + 1
        index += 1
    raise ContractError("blocked_worker_call_unparseable", f"argument {key} has an unterminated container")


def split_js_top_level(source: str, separator: str, key: str) -> list[str]:
    parts: list[str] = []
    start = 0
    stack: list[str] = []
    pairs = {"{": "}", "[": "]", "(": ")"}
    index = 0
    while index < len(source):
        character = source[index]
        if character in {"'", '"', "`"}:
            quote = character
            index += 1
            while index < len(source):
                character = source[index]
                if quote == "`" and character == "$" and index + 1 < len(source) and source[index + 1] == "{":
                    raise ContractError(
                        "blocked_worker_call_unparseable",
                        f"argument {key} contains dynamic template interpolation",
                    )
                if character == "\\":
                    index += 2
                    continue
                index += 1
                if character == quote:
                    break
            else:
                raise ContractError("blocked_worker_call_unparseable", f"argument {key} has an unterminated literal")
            continue
        if character in pairs:
            stack.append(character)
        elif character in pairs.values():
            if not stack or pairs[stack[-1]] != character:
                raise ContractError("blocked_worker_call_unparseable", f"argument {key} has mismatched delimiters")
            stack.pop()
        elif character == separator and not stack:
            parts.append(source[start:index])
            start = index + 1
        index += 1
    if stack:
        raise ContractError("blocked_worker_call_unparseable", f"argument {key} has an unterminated container")
    parts.append(source[start:])
    return parts


def imagegen_call_object(source: str) -> tuple[str, str, int]:
    matches = list(re.finditer(r"(?<![A-Za-z0-9_$])tools\.image_gen__imagegen\s*\(", source))
    if len(matches) != 1:
        raise ContractError("blocked_worker_call_unparseable", "image-generation call object is not unique")
    object_start = matches[0].end()
    while object_start < len(source) and source[object_start].isspace():
        object_start += 1
    if object_start >= len(source) or source[object_start] != "{":
        raise ContractError("blocked_worker_call_unparseable", "image-generation arguments must be a static object literal")
    object_end = find_matching_js_delimiter(source, object_start, "image-generation arguments")
    return source[:object_start], source[object_start + 1 : object_end - 1], object_start


def parse_imagegen_properties(source: str) -> tuple[str, dict[str, str | None], int]:
    prefix, body, object_start = imagegen_call_object(source)
    properties: dict[str, str | None] = {}
    for segment in split_js_top_level(body, ",", "image-generation arguments"):
        segment = segment.strip()
        if not segment:
            continue
        pieces = split_js_top_level(segment, ":", "image-generation arguments")
        if len(pieces) == 1:
            name = pieces[0].strip()
            expression = None
        elif len(pieces) == 2:
            name = pieces[0].strip()
            expression = pieces[1].strip()
        else:
            raise ContractError("blocked_worker_call_unparseable", "image-generation property is ambiguous")
        if name.startswith('"'):
            try:
                decoded_name, consumed = JSON_DECODER.raw_decode(name)
            except json.JSONDecodeError as exc:
                raise ContractError("blocked_worker_call_unparseable", f"invalid quoted property key: {name!r}") from exc
            if consumed != len(name) or not isinstance(decoded_name, str):
                raise ContractError("blocked_worker_call_unparseable", f"invalid quoted property key: {name!r}")
            name = decoded_name
        elif len(name) >= 2 and name[0] == name[-1] == "'":
            name = name[1:-1]
        if not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", name):
            raise ContractError("blocked_worker_call_unparseable", f"unsupported image-generation property key: {name!r}")
        if name in properties:
            raise ContractError("blocked_worker_call_unparseable", f"duplicate image-generation property: {name}")
        properties[name] = expression
    return prefix, properties, object_start


def parse_static_string_expression(expression: str, key: str, *, raw_template: bool = False) -> str:
    encoded = expression.lstrip()
    leading = len(expression) - len(encoded)
    raw_match = re.fullmatch(r"String\s*\.\s*raw\s*(`(?:\\.|[^`])*`)\s*", encoded, flags=re.DOTALL)
    if raw_match is not None:
        value, consumed = decode_static_js_template_literal_token(raw_match.group(1), key, raw=True)
        if consumed != len(raw_match.group(1)):
            raise ContractError("blocked_worker_call_unparseable", f"argument {key} has trailing raw-template content")
        return value
    if encoded.startswith("`"):
        value, end = decode_static_js_template_literal_token(encoded, key, raw=raw_template)
    else:
        try:
            value, end = JSON_DECODER.raw_decode(encoded)
        except json.JSONDecodeError as exc:
            raise ContractError("blocked_worker_call_unparseable", f"argument {key} is not a static string literal: {exc}") from exc
    if not isinstance(value, str) or expression[leading + end :].strip():
        raise ContractError("blocked_worker_call_unparseable", f"argument {key} contains a non-static string expression")
    return value


def resolve_static_const_prompt(source: str, prefix: str, object_start: int, key: str) -> str:
    masked = mask_js_literals(source)
    declarations = list(re.finditer(r"(?<![A-Za-z0-9_$])(const|let|var)\s+prompt\b", masked))
    if len(declarations) != 1 or declarations[0].group(1) != "const" or declarations[0].start() >= object_start:
        raise ContractError("blocked_worker_call_unparseable", "prompt shorthand requires one preceding immutable const prompt")
    declaration = declarations[0]
    assignments = list(re.finditer(r"(?<![A-Za-z0-9_$])prompt\s*(?:\+\+|--|[+\-*/%&|^]?=)", masked))
    prefix_mutations = list(re.finditer(r"(?:\+\+|--)\s*prompt\b", masked))
    variable_start = declaration.end() - len("prompt")
    if len(assignments) != 1 or assignments[0].start() != variable_start or prefix_mutations:
        raise ContractError("blocked_worker_call_unparseable", "prompt shorthand binding is reassigned or ambiguous")
    equals = re.match(r"\s*=\s*", source[declaration.end() :])
    if equals is None:
        raise ContractError("blocked_worker_call_unparseable", "const prompt lacks a static initializer")
    literal_start = declaration.end() + equals.end()
    encoded = source[literal_start:object_start]
    if encoded.startswith("`"):
        value, end = decode_static_js_template_literal_token(encoded, key)
    else:
        try:
            value, end = JSON_DECODER.raw_decode(encoded)
        except json.JSONDecodeError as exc:
            raise ContractError("blocked_worker_call_unparseable", f"const prompt is not a static string literal: {exc}") from exc
    if not isinstance(value, str) or re.match(r"\s*;", encoded[end:]) is None:
        raise ContractError("blocked_worker_call_unparseable", "const prompt initializer is not an immutable string literal")
    return value


def parse_static_reference_array(expression: str, key: str) -> list[str]:
    encoded = expression.strip()
    if not encoded.startswith("["):
        raise ContractError("blocked_worker_call_unparseable", f"argument {key} is not a static array")
    end = find_matching_js_delimiter(encoded, 0, key)
    if encoded[end:].strip():
        raise ContractError("blocked_worker_call_unparseable", f"argument {key} contains a dynamic array expression")
    values: list[str] = []
    for item in split_js_top_level(encoded[1 : end - 1], ",", key):
        item = item.strip()
        if not item:
            continue
        raw_match = re.fullmatch(r"String\s*\.\s*raw\s*(`(?:\\.|[^`])*`)", item, flags=re.DOTALL)
        if raw_match is not None:
            value, consumed = decode_static_js_template_literal_token(raw_match.group(1), key, raw=True)
            if consumed != len(raw_match.group(1)):
                raise ContractError("blocked_worker_call_unparseable", f"argument {key} has trailing raw-template content")
            values.append(value)
            continue
        values.append(parse_static_string_expression(item, key))
    return values


def extract_js_json_value(source: str, key: str) -> Any:
    prefix, properties, object_start = parse_imagegen_properties(source)
    if key not in properties:
        raise ContractError("blocked_worker_call_unparseable", f"missing image-generation argument: {key}")
    expression = properties[key]
    if expression is None:
        if key != "prompt":
            raise ContractError("blocked_worker_call_unparseable", f"argument {key} cannot use property shorthand")
        return resolve_static_const_prompt(source, prefix, object_start, key)
    if key == "prompt":
        return parse_static_string_expression(expression, key)
    if key == "referenced_image_paths":
        return parse_static_reference_array(expression, key)
    try:
        value, end = JSON_DECODER.raw_decode(expression)
    except json.JSONDecodeError as exc:
        raise ContractError("blocked_worker_call_unparseable", f"argument {key} is not a JSON literal: {exc}") from exc
    if expression[end:].strip():
        raise ContractError("blocked_worker_call_unparseable", f"argument {key} contains a dynamic expression")
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
        (i, event.get("payload", {}))
        for i, event in enumerate(worker_events)
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
    image_tool_calls = [(index, payload) for index, payload in tool_calls if payload.get("type") == "custom_tool_call"]
    wait_calls = [(index, payload) for index, payload in tool_calls if payload.get("type") == "function_call"]
    if image_tool_calls != image_calls or len(wait_calls) > 5 or any(payload.get("name") != "wait" for _, payload in wait_calls):
        raise ContractError("blocked_worker_tool_violation", "image worker used a tool other than its single image call or bounded wait continuation")
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
    if wait_calls:
        initial_call_id = image_call.get("call_id")
        initial_outputs = [
            (i, event.get("payload", {}))
            for i, event in enumerate(worker_events)
            if event.get("type") == "response_item"
            and event.get("payload", {}).get("type") == "custom_tool_call_output"
            and event.get("payload", {}).get("call_id") == initial_call_id
        ]
        if len(initial_outputs) != 1 or not isinstance(initial_outputs[0][1].get("output"), str):
            raise ContractError("blocked_worker_tool_violation", "wait continuation lacks one running-cell receipt from the image call")
        running_match = re.search(r"(?:^|\n)Script running with cell ID ([A-Za-z0-9_-]+)(?:\r?\n|$)", initial_outputs[0][1]["output"])
        if not running_match:
            raise ContractError("blocked_worker_tool_violation", "wait continuation is not bound to a yielded image-call cell")
        running_cell_id = running_match.group(1)
        if not (call_index < initial_outputs[0][0] < event_final_index and initial_outputs[0][0] < response_final_index):
            raise ContractError("blocked_worker_event_order", "image-call yield receipt is outside the active worker turn")
        previous_wait_output_index = initial_outputs[0][0]
        for wait_index, wait_call in wait_calls:
            try:
                arguments = json.loads(wait_call.get("arguments", ""))
            except (TypeError, json.JSONDecodeError) as exc:
                raise ContractError("blocked_worker_tool_violation", "wait continuation arguments are not static JSON") from exc
            allowed_wait_fields = {"cell_id", "yield_time_ms", "max_tokens", "terminate"}
            if not isinstance(arguments, dict) or set(arguments) - allowed_wait_fields:
                raise ContractError("blocked_worker_tool_violation", "wait continuation contains unsupported arguments")
            yield_time_ms = arguments.get("yield_time_ms", 10000)
            max_tokens = arguments.get("max_tokens", 10000)
            terminate = arguments.get("terminate", False)
            if (
                arguments.get("cell_id") != running_cell_id
                or terminate is not False
                or isinstance(yield_time_ms, bool)
                or not isinstance(yield_time_ms, int)
                or not 1 <= yield_time_ms <= 120000
                or isinstance(max_tokens, bool)
                or not isinstance(max_tokens, int)
                or not 1 <= max_tokens <= 10000
            ):
                raise ContractError("blocked_worker_tool_violation", "wait continuation is not a bounded non-terminating wait for the yielded image-call cell")
            wait_call_id = wait_call.get("call_id")
            wait_outputs = [
                (i, event.get("payload", {}))
                for i, event in enumerate(worker_events)
                if event.get("type") == "response_item"
                and event.get("payload", {}).get("type") == "function_call_output"
                and event.get("payload", {}).get("call_id") == wait_call_id
            ]
            if len(wait_outputs) != 1 or not isinstance(wait_call_id, str) or not wait_call_id:
                raise ContractError("blocked_worker_tool_violation", "wait continuation lacks one matching completion receipt")
            wait_output_index = wait_outputs[0][0]
            if not (previous_wait_output_index < wait_index < wait_output_index < event_final_index and wait_output_index < response_final_index):
                raise ContractError("blocked_worker_event_order", "wait continuation is not ordered within the active worker turn")
            previous_wait_output_index = wait_output_index
    if event_final.get("message") not in {None, ""} or response_message_text(response_final) != "":
        raise ContractError("blocked_worker_nonempty_final", "worker emitted final text")
    call_input = image_call.get("input", "")
    _, call_properties, _ = parse_imagegen_properties(call_input)
    expected_properties = {"prompt", "referenced_image_paths"} if expected_references else {"prompt"}
    if set(call_properties) != expected_properties:
        raise ContractError(
            "blocked_worker_tool_arguments_invalid",
            f"image-generation arguments must be exactly {sorted(expected_properties)}",
        )
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
    tool_call_id = image_call.get("call_id")
    call_id = image_event.get("call_id")
    saved_path = image_event.get("saved_path")
    if (
        not isinstance(tool_call_id, str)
        or not tool_call_id
        or not isinstance(call_id, str)
        or not call_id
        or not isinstance(saved_path, str)
        or not saved_path
    ):
        raise ContractError("blocked_worker_image_event_incomplete", "image call/end lacks its namespaced call id or saved path")
    if image_event.get("revised_prompt") != prompt:
        raise ContractError(
            "blocked_worker_image_event_prompt_mismatch",
            "image-generation completion does not bind the exact frozen prompt",
        )
    wrapper_outputs = [
        (i, event.get("payload", {}))
        for i, event in enumerate(worker_events)
        if event.get("type") == "response_item"
        and event.get("payload", {}).get("type") == "custom_tool_call_output"
        and event.get("payload", {}).get("call_id") == tool_call_id
    ]
    if len(wrapper_outputs) != 1 or not (call_index < wrapper_outputs[0][0] < event_final_index):
        raise ContractError("blocked_worker_image_wrapper_incomplete", "image exec wrapper lacks one matching output receipt")
    if not wait_calls and not (end_index < wrapper_outputs[0][0]):
        raise ContractError("blocked_worker_event_order", "completed image event must precede its non-yielded wrapper receipt")
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
    expected_mailbox_header = (
        f"Message Type: FINAL_ANSWER\nTask name: {agent_path.rsplit('/', 1)[0]}\n"
        f"Sender: {agent_path}\nPayload:\n"
    )
    mailbox_completions: list[tuple[int, dict[str, Any]]] = []
    for index, event in enumerate(events):
        payload = event.get("payload", {})
        if (
            event.get("type") != "response_item"
            or payload.get("type") != "agent_message"
            or payload.get("author") != agent_path
            or payload.get("recipient") != agent_path.rsplit("/", 1)[0]
        ):
            continue
        content = payload.get("content")
        text = "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "input_text"
        ) if isinstance(content, list) else ""
        if (
            isinstance(content, list)
            and all(isinstance(item, dict) and item.get("type") == "input_text" for item in content)
            and text == expected_mailbox_header
            and index > 0
            and events[index - 1].get("type") == "inter_agent_communication_metadata"
            and events[index - 1].get("payload", {}).get("trigger_turn") is False
        ):
            mailbox_completions.append((index, payload))
    if (
        len(start_activities) != 1
        or len(outputs) != 1
        or len(completed_activities) + len(mailbox_completions) != 1
    ):
        raise ContractError("blocked_worker_spawn_chain_mismatch", "spawn lacks one start, one unambiguous completion receipt, and one output")
    activity_index, activity = start_activities[0]
    output_index, output = outputs[0]
    if completed_activities:
        completion_activity_index, completion_activity = completed_activities[0]
        completion_mode = "sub_agent_activity"
        completion_activity_ms = completion_activity.get("occurred_at_ms")
        completion_identity_valid = (
            isinstance(completion_activity_ms, int)
            and completion_activity_ms >= activity.get("occurred_at_ms", 0)
        )
    else:
        completion_activity_index, completion_activity = mailbox_completions[0]
        completion_mode = "empty_final_mailbox_receipt"
        try:
            completion_activity_ms = int(
                datetime.fromisoformat(events[completion_activity_index]["timestamp"].replace("Z", "+00:00")).timestamp() * 1000
            )
        except (KeyError, TypeError, ValueError):
            completion_activity_ms = None
        completion_identity_valid = (
            isinstance(completion_activity_ms, int)
            and completion_activity_ms >= activity.get("occurred_at_ms", 0)
            and completion_activity.get("internal_chat_message_metadata_passthrough", {}).get("turn_id") == parent_turn_id
        )
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
        and completion_identity_valid
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
        "parent_completion_activity_ms": completion_activity_ms,
        "parent_completion_mode": completion_mode,
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


def resolve_run_artifact(run_root: Path, value: str, code: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(code, "artifact path is missing")
    candidate = Path(value)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (run_root / candidate).resolve()
    try:
        resolved.relative_to(run_root)
    except ValueError as exc:
        raise ContractError(code, f"artifact escapes run root: {resolved}") from exc
    if resolved.is_symlink() or not resolved.is_file():
        raise ContractError(code, f"artifact is missing or linked: {resolved}")
    return resolved


def load_repair_publication(
    *,
    run_root: Path,
    manifest: dict[str, Any],
    publication_path: Path,
    expected_prompt: Path,
    view_id: str,
    attempt_id: str,
    attempt_revision: int,
) -> dict[str, Any]:
    if not publication_path.is_absolute() or publication_path.is_symlink() or not publication_path.is_file():
        raise ContractError("blocked_repair_prompt_invalid", f"repair publication path is invalid: {publication_path}")
    try:
        publication_path.resolve().relative_to(run_root)
    except ValueError as exc:
        raise ContractError("blocked_repair_prompt_invalid", "repair publication escapes the run root") from exc
    raw = publication_path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ContractError("blocked_repair_prompt_invalid", "repair publication must be UTF-8/LF without BOM")
    try:
        receipt = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("blocked_repair_prompt_invalid", str(exc)) from exc
    if not isinstance(receipt, dict) or receipt.get("schema_version") != "frozen_moment_repair_prompt_publication.v1":
        raise ContractError("blocked_repair_prompt_invalid", "repair publication schema is invalid")
    if (
        receipt.get("publication_status") != "repair_prompt_frozen"
        or receipt.get("run_id") != manifest.get("job", {}).get("job_id")
        or receipt.get("view_id") != view_id
        or receipt.get("attempt_id") != attempt_id
        or receipt.get("attempt_revision") != attempt_revision
    ):
        raise ContractError("blocked_repair_prompt_invalid", "repair publication identity differs")
    maximum = manifest.get("job", {}).get("max_attempts_per_view")
    if not isinstance(maximum, int) or not 2 <= attempt_revision <= maximum:
        raise ContractError("blocked_repair_prompt_invalid", "repair attempt revision is outside the frozen budget")
    prior_attempts = [
        item for item in manifest.get("attempts", [])
        if isinstance(item, dict) and item.get("view_id") == view_id and isinstance(item.get("attempt_revision"), int)
        and item["attempt_revision"] < attempt_revision
    ]
    if not prior_attempts:
        raise ContractError("blocked_repair_prompt_invalid", "repair publication lacks a prior bound attempt")
    if any(
        isinstance(item, dict) and item.get("view_id") == view_id
        and isinstance(item.get("attempt_revision"), int) and item["attempt_revision"] > attempt_revision
        for item in manifest.get("attempts", [])
    ):
        raise ContractError("blocked_repair_prompt_invalid", "repair publication has been superseded by a later attempt")
    previous = max(prior_attempts, key=lambda item: item["attempt_revision"])
    if (
        previous.get("attempt_revision") != attempt_revision - 1
        or previous.get("decision") not in {"rejected", "repair_required"}
        or receipt.get("previous_attempt_id") != previous.get("attempt_id")
        or receipt.get("previous_attempt_revision") != previous.get("attempt_revision")
        or receipt.get("previous_image_sha256") != previous.get("image_sha256")
        or any(item.get("decision") == "approved" for item in prior_attempts)
    ):
        raise ContractError("blocked_repair_prompt_invalid", "repair publication does not bind the immediately preceding failed attempt")
    previous_inspection = resolve_run_artifact(
        run_root, previous.get("inspection_path"), "blocked_repair_prompt_invalid"
    )
    if (
        sha256_file(previous_inspection) != previous.get("inspection_sha256")
        or receipt.get("previous_inspection_path") != previous.get("inspection_path")
        or receipt.get("previous_inspection_sha256") != previous.get("inspection_sha256")
    ):
        raise ContractError("blocked_repair_prompt_invalid", "repair publication inspection lineage differs")
    try:
        inspection = json.loads(previous_inspection.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("blocked_repair_prompt_invalid", f"previous inspection is invalid: {exc}") from exc
    failure_codes = inspection.get("failure_codes")
    repair_scope = inspection.get("repair_scope")
    if (
        inspection.get("decision") not in {"rejected", "repair_required"}
        or not isinstance(failure_codes, list) or not failure_codes
        or not all(isinstance(item, str) and item.strip() for item in failure_codes)
        or not isinstance(repair_scope, list) or not repair_scope
        or not all(isinstance(item, str) and item.strip() for item in repair_scope)
        or receipt.get("failure_codes") != failure_codes
        or receipt.get("repair_scope") != repair_scope
    ):
        raise ContractError("blocked_repair_prompt_invalid", "repair publication does not bind a concrete failed inspection")
    prompt = next((item for item in manifest.get("prompts", []) if item.get("view_id") == view_id), None)
    view = next((item for item in manifest.get("views", []) if item.get("view_id") == view_id), None)
    if not isinstance(prompt, dict) or not isinstance(view, dict):
        raise ContractError("blocked_repair_prompt_invalid", "repair view or base prompt is missing")
    base_prompt = resolve_run_artifact(run_root, prompt.get("prompt_path"), "blocked_repair_prompt_invalid")
    parent_prompt = resolve_run_artifact(run_root, previous.get("prompt_path"), "blocked_repair_prompt_invalid")
    repair_prompt = resolve_run_artifact(run_root, receipt.get("repair_prompt_path"), "blocked_repair_prompt_invalid")
    expected_prompt_path = run_root / "00_manifest" / "repair-prompts" / view_id / f"{attempt_id}.zh.txt"
    expected_publication_path = run_root / "00_manifest" / "repair-prompts" / view_id / f"{attempt_id}.publication.json"
    repair_sha = sha256_file(repair_prompt)
    if (
        publication_path.resolve() != expected_publication_path.resolve()
        or repair_prompt.resolve() != expected_prompt_path.resolve()
        or receipt.get("base_prompt_path") != prompt.get("prompt_path")
        or receipt.get("base_prompt_sha256") != prompt.get("prompt_sha256")
        or sha256_file(base_prompt) != prompt.get("prompt_sha256")
        or receipt.get("parent_prompt_path") != previous.get("prompt_path")
        or receipt.get("parent_prompt_sha256") != previous.get("prompt_sha256")
        or sha256_file(parent_prompt) != previous.get("prompt_sha256")
        or receipt.get("repair_prompt_sha256") != repair_sha
        or repair_prompt.resolve() != expected_prompt.resolve()
        or repair_sha in {item.get("prompt_sha256") for item in prior_attempts}
    ):
        raise ContractError("blocked_repair_prompt_invalid", "repair prompt bytes or ancestry differ")
    source = manifest.get("source_evidence", {})
    moment = manifest.get("moment_canon", {})
    if (
        receipt.get("coverage_contract_sha256") != manifest.get("coverage_contract_sha256")
        or receipt.get("source_evidence_sha256") != source.get("source_evidence_sha256")
        or receipt.get("moment_canon_sha256") != moment.get("moment_canon_sha256")
        or receipt.get("camera_contract_sha256") != view.get("camera_contract_sha256")
        or receipt.get("reference_plan_sha256") != prompt.get("reference_plan_sha256")
    ):
        raise ContractError("blocked_repair_prompt_invalid", "repair publication changed frozen coverage authority")
    published_ms = receipt.get("published_at_unix_ms")
    if not isinstance(published_ms, int) or isinstance(published_ms, bool) or published_ms <= 0:
        raise ContractError("blocked_repair_prompt_invalid", "repair publication lacks a valid time checkpoint")
    try:
        published_utc_ms = int(
            datetime.fromisoformat(str(receipt.get("published_at_utc", "")).replace("Z", "+00:00")).timestamp()
            * 1000
        )
    except (ValueError, TypeError) as exc:
        raise ContractError("blocked_repair_prompt_invalid", f"repair UTC publication checkpoint is invalid: {exc}") from exc
    if abs(published_utc_ms - published_ms) > 1:
        raise ContractError("blocked_repair_prompt_invalid", "repair UTC and Unix publication checkpoints differ")
    previous_worker = resolve_run_artifact(
        run_root, previous.get("worker_result_path"), "blocked_repair_prompt_invalid"
    )
    try:
        worker_record = json.loads(previous_worker.read_text(encoding="utf-8"))
        inspection_ms = int(
            datetime.fromisoformat(str(inspection.get("inspected_at_utc", "")).replace("Z", "+00:00")).timestamp()
            * 1000
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        raise ContractError("blocked_repair_prompt_invalid", f"prior completion timestamps are invalid: {exc}") from exc
    completion_ms = worker_record.get("parent_completion_activity_ms")
    if (
        not isinstance(completion_ms, int)
        or isinstance(completion_ms, bool)
        or published_ms < completion_ms
        or published_ms < inspection_ms
    ):
        raise ContractError("blocked_repair_prompt_invalid", "repair prompt was published before the failed attempt completed and was inspected")
    return {
        "receipt": receipt,
        "publication_path": publication_path.resolve(),
        "publication_sha256": sha256_bytes(raw),
        "prompt_path": repair_prompt,
        "prompt_sha256": repair_sha,
        "published_at_unix_ms": published_ms,
        "base_prompt_sha256": prompt["prompt_sha256"],
    }


def load_coverage_contract(
    path: Path,
    run_id: str,
    view_id: str,
    expected_prompt: Path,
    *,
    attempt_id: str,
    attempt_revision: int,
    repair_publication: Path | None = None,
) -> dict[str, Any]:
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
    if not prompt_path.is_file() or sha256_file(prompt_path) != prompt.get("prompt_sha256"):
        raise ContractError("blocked_coverage_contract_invalid", "frozen base prompt is missing or changed")
    bound_for_view = [
        item
        for item in manifest.get("attempts", [])
        if isinstance(item, dict) and item.get("view_id") == view_id
    ]
    if attempt_revision != len(bound_for_view) + 1:
        raise ContractError(
            "blocked_worker_attempt_invalid",
            "bound attempt revisions must be contiguous from one; an unbound call cannot self-authorize a skipped revision",
        )
    prior_bound = [
        item for item in manifest.get("attempts", [])
        if isinstance(item, dict) and item.get("view_id") == view_id
        and isinstance(item.get("attempt_revision"), int) and item["attempt_revision"] < attempt_revision
    ]
    repair = None
    if prior_bound:
        view = next((item for item in manifest.get("views", []) if item.get("view_id") == view_id), None)
        latest_revision = max(item["attempt_revision"] for item in prior_bound)
        if (
            not isinstance(view, dict)
            or view.get("status") != "repair_required"
            or manifest.get("state", {}).get("current") != "repair_required"
            or latest_revision != attempt_revision - 1
            or any(item.get("decision") == "approved" for item in prior_bound)
            or any(
                isinstance(item, dict) and item.get("view_id") == view_id
                and isinstance(item.get("attempt_revision"), int) and item["attempt_revision"] >= attempt_revision
                for item in manifest.get("attempts", [])
            )
        ):
            raise ContractError("blocked_repair_prompt_invalid", "live run is not at the exact repair dispatch gate")
        if repair_publication is None:
            raise ContractError("blocked_repair_prompt_required", "a bound failed attempt requires a versioned repair prompt")
        repair = load_repair_publication(
            run_root=run_root,
            manifest=manifest,
            publication_path=repair_publication.resolve(),
            expected_prompt=expected_prompt,
            view_id=view_id,
            attempt_id=attempt_id,
            attempt_revision=attempt_revision,
        )
        authority_mode = "repair_prompt"
        prompt_sha = repair["prompt_sha256"]
    else:
        if repair_publication is not None:
            raise ContractError("blocked_repair_prompt_invalid", "base dispatch cannot claim repair authority")
        if prompt_path != expected_prompt.resolve():
            raise ContractError("blocked_coverage_contract_invalid", "expected prompt does not match the frozen base prompt")
        authority_mode = "base_prompt"
        prompt_sha = prompt["prompt_sha256"]
    return {
        "manifest": manifest,
        "manifest_bytes": raw,
        "manifest_sha256": sha256_bytes(raw),
        "run_root": run_root,
        "source_evidence_sha256": expected_source_sha,
        "moment_canon_sha256": expected_moment_sha,
        "coverage_contract_sha256": expected_contract_sha,
        "prompt_sha256": prompt_sha,
        "base_prompt_sha256": prompt["prompt_sha256"],
        "prompt_authority_mode": authority_mode,
        "repair_publication": repair,
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
    parser.add_argument("--repair-publication", type=Path)
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
    coverage = load_coverage_contract(
        args.coverage_manifest.resolve(),
        args.run_id,
        view_id,
        args.expected_prompt,
        attempt_id=args.attempt_id,
        attempt_revision=args.attempt_revision,
        repair_publication=args.repair_publication,
    )
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
    if sha256_bytes(prompt_bytes) != coverage["prompt_sha256"]:
        raise ContractError("blocked_generation_prompt_persistence", "prompt bytes differ from their frozen authority")
    repair = coverage["repair_publication"]
    if repair is not None and args.not_before_ms < repair["published_at_unix_ms"]:
        raise ContractError("blocked_repair_prompt_invalid", "worker checkpoint predates repair prompt publication")
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
        "parent_completion_mode": spawn["parent_completion_mode"],
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
        "prompt_authority_mode": coverage["prompt_authority_mode"],
        "repair_publication_path": str(repair["publication_path"]) if repair is not None else None,
        "repair_publication_sha256": repair["publication_sha256"] if repair is not None else None,
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
