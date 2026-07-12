"""Shared immutable-predecessor and field-level revision evidence helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any


PREDECESSOR_FIELDS = {"artifact_id", "owner_skill", "version", "sha256"}
REVISION_METADATA_ROOTS = {"sha256", "version", "approval_status", "stale_reason", "revision_scope"}


def canonical_hash(record: dict[str, Any]) -> str:
    payload = dict(record)
    payload.pop("sha256", None)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def semver_tuple(value: Any) -> tuple[int, int, int] | None:
    if not isinstance(value, str):
        return None
    parts = value.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def semantic_diff_pointers(before: Any, after: Any, path: str = "") -> list[str]:
    """Return deterministic JSON pointers for every semantic leaf change."""
    if type(before) is not type(after):
        return [path or "/"]
    if isinstance(before, dict):
        pointers: list[str] = []
        for key in sorted(set(before) | set(after)):
            child = f"{path}/{_escape(str(key))}"
            if key not in before or key not in after:
                pointers.append(child)
            else:
                pointers.extend(semantic_diff_pointers(before[key], after[key], child))
        return pointers
    if isinstance(before, list):
        pointers = []
        common = min(len(before), len(after))
        for index in range(common):
            pointers.extend(semantic_diff_pointers(before[index], after[index], f"{path}/{index}"))
        for index in range(common, max(len(before), len(after))):
            pointers.append(f"{path}/{index}")
        return pointers
    return [] if before == after else [path or "/"]


def revision_semantic_view(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key not in REVISION_METADATA_ROOTS}


def validate_predecessor_evidence(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    revision: dict[str, Any],
    *,
    initial_mode: str = "initial",
) -> tuple[list[str], list[str]]:
    """Validate one exact predecessor and return actual semantic diff pointers."""
    errors: list[str] = []
    mode = revision.get("mode")
    predecessor = revision.get("predecessor_artifact")
    declared_pointers = revision.get("changed_json_pointers")
    if not isinstance(declared_pointers, list) or not all(isinstance(item, str) and item.startswith("/") for item in declared_pointers):
        errors.append("revision_scope.changed_json_pointers must be a unique JSON-pointer array")
        declared_pointers = []
    elif len(declared_pointers) != len(set(declared_pointers)):
        errors.append("revision_scope.changed_json_pointers must be unique")

    if mode == initial_mode:
        if predecessor is not None:
            errors.append("initial revision must have predecessor_artifact null")
        if declared_pointers:
            errors.append("initial revision must have no changed_json_pointers because no predecessor exists")
        if previous is not None:
            errors.append("initial revision must not be validated against a predecessor")
        return errors, []

    if not isinstance(predecessor, dict) or set(predecessor) != PREDECESSOR_FIELDS:
        errors.append("non-initial revision requires exactly one predecessor_artifact lock")
        return errors, []
    if previous is None:
        errors.append("non-initial revision requires the actual --previous-contract bytes")
        return errors, []
    if previous.get("approval_status") == "draft" or not isinstance(previous.get("sha256"), str) or previous.get("sha256") != canonical_hash(previous):
        errors.append("predecessor must be a frozen artifact with a valid canonical sha256")
    for field in PREDECESSOR_FIELDS:
        if predecessor.get(field) != previous.get(field):
            errors.append(f"predecessor_artifact.{field} does not match actual predecessor")
    for field in ("artifact_id", "owner_skill", "project_id"):
        if current.get(field) != previous.get(field):
            errors.append(f"revision must preserve predecessor {field}")
    before_version, after_version = semver_tuple(previous.get("version")), semver_tuple(current.get("version"))
    if before_version is None or after_version is None or after_version <= before_version:
        errors.append("revision SemVer must be greater than predecessor SemVer")

    pointers = semantic_diff_pointers(revision_semantic_view(previous), revision_semantic_view(current))
    if not pointers:
        errors.append("non-initial revision must contain a real semantic change")
    if sorted(declared_pointers) != sorted(pointers):
        errors.append("revision_scope.changed_json_pointers does not exactly match the real predecessor-to-current diff")
    return errors, pointers


def keyed_changes(before: Any, after: Any, key: str) -> tuple[set[str], bool]:
    """Return changed stable IDs and whether the collection was structurally invalid."""
    if not isinstance(before, list) or not isinstance(after, list):
        return set(), True
    before_map = {item.get(key): item for item in before if isinstance(item, dict) and isinstance(item.get(key), str)}
    after_map = {item.get(key): item for item in after if isinstance(item, dict) and isinstance(item.get(key), str)}
    malformed = len(before_map) != len(before) or len(after_map) != len(after)
    changed = {identity for identity in set(before_map) | set(after_map) if before_map.get(identity) != after_map.get(identity)}
    return changed, malformed
