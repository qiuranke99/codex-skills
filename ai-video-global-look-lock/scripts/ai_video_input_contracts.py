#!/usr/bin/env python3
"""Package-local validation for portable AI-video input artifacts.

This module intentionally validates the stable interchange surface used by a
consumer Skill.  It does not import, locate, or execute a sibling Skill.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


SHA_RE = re.compile(r"^[a-f0-9]{64}$")
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
APPROVALS = {"draft", "assistant_validated", "user_approved", "stale", "blocked"}
ENVELOPE_FIELDS = {
    "contract_version", "artifact_id", "owner_skill", "version", "sha256",
    "approval_status", "dependencies", "affected_shot_uids", "stale_reason",
}
REF_FIELDS = {"artifact_id", "owner_skill", "version", "sha256"}
RECEIPT_FIELDS = {
    "schema_version", "canonical_manifest_locator", "updated_by_skill",
    "base_manifest_sha256", "resulting_manifest_sha256",
    "registered_artifact_ids", "delta_status",
}
PREDECESSOR_FIELDS = {"artifact_id", "owner_skill", "version", "sha256"}
REVISION_METADATA_ROOTS = {"sha256", "version", "approval_status", "stale_reason", "revision_scope"}


def canonical_hash(record: dict[str, Any]) -> str:
    payload = dict(record)
    payload.pop("sha256", None)
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


canonical_sha256 = canonical_hash


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha(value: Any) -> bool:
    return isinstance(value, str) and SHA_RE.fullmatch(value) is not None


def _safe_path(root: Path, locator: Any, label: str, errors: list[str]) -> Path | None:
    if not _text(locator):
        errors.append(f"{label}: non-empty project-relative locator required")
        return None
    assert isinstance(locator, str)
    if "\\" in locator or locator.startswith("/") or (len(locator) > 1 and locator[0].isalpha() and locator[1] == ":"):
        errors.append(f"{label}: locator must use portable project-relative POSIX syntax")
        return None
    relative = Path(locator)
    if relative.is_absolute() or ".." in relative.parts:
        errors.append(f"{label}: absolute paths and traversal are forbidden")
        return None
    candidate = (root.resolve() / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{label}: locator escapes project root")
        return None
    return candidate


def _verify_file(root: Path, locator: Any, digest: Any, label: str, errors: list[str]) -> None:
    path = _safe_path(root, locator, label, errors)
    if path is None:
        return
    if not path.is_file():
        errors.append(f"{label}: file missing")
        return
    if not _sha(digest):
        errors.append(f"{label}: lowercase SHA-256 required")
        return
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        errors.append(f"{label}: file SHA-256 mismatch")


def validate_artifact_envelope(value: Any, expected_owner: str | None = None) -> list[str]:
    if not isinstance(value, dict):
        return ["artifact root must be an object"]
    errors: list[str] = []
    missing = ENVELOPE_FIELDS - set(value)
    if missing:
        errors.append(f"artifact envelope missing fields: {sorted(missing)}")
        return errors
    if value.get("contract_version") != "ai-video-artifact-v1":
        errors.append("contract_version must be ai-video-artifact-v1")
    if not _text(value.get("artifact_id")):
        errors.append("artifact_id must be non-empty")
    if not _text(value.get("owner_skill")):
        errors.append("owner_skill must be non-empty")
    if expected_owner is not None and value.get("owner_skill") != expected_owner:
        errors.append(f"owner_skill must be {expected_owner}")
    if not isinstance(value.get("version"), str) or SEMVER_RE.fullmatch(value["version"]) is None:
        errors.append("version must be SemVer")
    status = value.get("approval_status")
    if status not in APPROVALS:
        errors.append("approval_status is invalid")
    if status == "draft":
        if value.get("sha256") is not None:
            errors.append("draft artifact sha256 must be null")
    elif not _sha(value.get("sha256")) or value.get("sha256") != canonical_hash(value):
        errors.append("frozen artifact sha256 is invalid")
    if status == "stale" and not _text(value.get("stale_reason")):
        errors.append("stale artifact requires stale_reason")
    if status != "stale" and value.get("stale_reason") is not None:
        errors.append("non-stale artifact stale_reason must be null")
    shot_uids = value.get("affected_shot_uids")
    if not isinstance(shot_uids, list) or not all(_text(uid) for uid in shot_uids) or len(shot_uids) != len(set(shot_uids or [])):
        errors.append("affected_shot_uids must be a unique string array")
    dependencies = value.get("dependencies")
    if not isinstance(dependencies, list):
        errors.append("dependencies must be an array")
    else:
        ids: list[str] = []
        for index, dependency in enumerate(dependencies):
            if not isinstance(dependency, dict) or set(dependency) != REF_FIELDS:
                errors.append(f"dependencies[{index}] must contain the exact artifact reference fields")
                continue
            if not all(_text(dependency.get(field)) for field in ("artifact_id", "owner_skill")):
                errors.append(f"dependencies[{index}] identity is invalid")
            if not isinstance(dependency.get("version"), str) or SEMVER_RE.fullmatch(dependency["version"]) is None:
                errors.append(f"dependencies[{index}].version must be SemVer")
            if not _sha(dependency.get("sha256")):
                errors.append(f"dependencies[{index}].sha256 must be lowercase SHA-256")
            if _text(dependency.get("artifact_id")):
                ids.append(dependency["artifact_id"])
        if len(ids) != len(set(ids)):
            errors.append("dependencies must not repeat artifact IDs")
    return errors


def validate_manifest(value: Any) -> list[str]:
    errors = validate_artifact_envelope(value, "ai-video-shot-script-director")
    if not isinstance(value, dict):
        return errors
    if value.get("schema_version") != "ai-video-project-canon-manifest.v1":
        errors.append("invalid Project Canon schema_version")
    if value.get("dependencies") != []:
        errors.append("Project Canon registry dependencies must be empty")
    active = value.get("active_artifacts")
    if not isinstance(active, list):
        errors.append("Project Canon active_artifacts must be an array")
        return errors
    ids: list[str] = []
    slots: list[str] = []
    for index, entry in enumerate(active):
        if not isinstance(entry, dict):
            errors.append(f"active_artifacts[{index}] must be an object")
            continue
        for field in (
            "artifact_slot", "artifact_id", "artifact_type", "owner_skill", "version",
            "sha256", "approval_status", "eligible_for_downstream",
            "affected_shot_uids", "locator", "file_sha256",
            "artifact_record_locator", "artifact_record_file_sha256", "dependencies",
        ):
            if field not in entry:
                errors.append(f"active_artifacts[{index}] missing {field}")
        if _text(entry.get("artifact_id")):
            ids.append(entry["artifact_id"])
        if _text(entry.get("artifact_slot")):
            slots.append(entry["artifact_slot"])
        if not _sha(entry.get("sha256")):
            errors.append(f"active_artifacts[{index}].sha256 must be lowercase SHA-256")
        dependencies = entry.get("dependencies")
        if isinstance(dependencies, list) and any(
            isinstance(dep, dict) and dep.get("artifact_id") == value.get("artifact_id")
            for dep in dependencies
        ):
            errors.append(f"active_artifacts[{index}] must not depend on the Project Canon registry")
    if len(ids) != len(set(ids)):
        errors.append("Project Canon active artifact IDs must be unique")
    if len(slots) != len(set(slots)):
        errors.append("Project Canon active artifact slots must be unique")
    return errors


def verify_artifact_files(value: dict[str, Any], project_root: Path) -> list[str]:
    errors: list[str] = []
    for collection in ("active_artifacts", "superseded_artifacts"):
        entries = value.get(collection)
        for index, entry in enumerate(entries if isinstance(entries, list) else []):
            if not isinstance(entry, dict):
                continue
            _verify_file(project_root, entry.get("locator"), entry.get("file_sha256"), f"{collection}[{index}]/primary", errors)
            _verify_file(
                project_root, entry.get("artifact_record_locator"), entry.get("artifact_record_file_sha256"),
                f"{collection}[{index}]/artifact_record", errors,
            )
    return errors


def validate_receipt(
    value: Any,
    expected_skill: str | None = None,
    expected_ids: set[str] | None = None,
    canonical_manifest: Any | None = None,
) -> list[str]:
    if not isinstance(value, dict):
        return ["receipt root must be an object"]
    errors: list[str] = []
    if set(value) != RECEIPT_FIELDS:
        errors.append("receipt must contain exact shared fields")
    if value.get("schema_version") != "ai-video-manifest-update-receipt.v1":
        errors.append("invalid receipt schema_version")
    if value.get("canonical_manifest_locator") != "00_project_canon/PROJECT_CANON_MANIFEST.json":
        errors.append("invalid canonical manifest locator")
    owner = value.get("updated_by_skill")
    if expected_skill is not None and owner != expected_skill:
        errors.append(f"updated_by_skill must equal {expected_skill}")
    for field in ("base_manifest_sha256", "resulting_manifest_sha256"):
        if not _sha(value.get(field)):
            errors.append(f"{field} must be lowercase SHA-256")
    registered = value.get("registered_artifact_ids")
    if not isinstance(registered, list) or not registered or not all(_text(item) for item in registered):
        errors.append("registered_artifact_ids must be a non-empty string array")
        registered = []
    elif len(registered) != len(set(registered)):
        errors.append("registered_artifact_ids must be unique")
    if expected_ids is not None and set(registered) != expected_ids:
        errors.append("registered_artifact_ids do not match expected owned artifacts")
    if value.get("delta_status") != "applied":
        errors.append("delta_status must be applied")
    if isinstance(canonical_manifest, dict):
        if value.get("resulting_manifest_sha256") != canonical_manifest.get("sha256"):
            errors.append("resulting_manifest_sha256 must equal canonical manifest sha256")
        if value.get("base_manifest_sha256") != canonical_manifest.get("base_manifest_sha256"):
            errors.append("base_manifest_sha256 must equal canonical manifest base_manifest_sha256")
        if owner != canonical_manifest.get("updated_by_skill"):
            errors.append("updated_by_skill must equal canonical manifest updated_by_skill")
        active = canonical_manifest.get("active_artifacts")
        active_by_id = {
            item.get("artifact_id"): item for item in active
            if isinstance(item, dict) and _text(item.get("artifact_id"))
        } if isinstance(active, list) else {}
        for artifact_id in registered:
            entry = active_by_id.get(artifact_id)
            if entry is None:
                errors.append(f"registered artifact is not active in canonical manifest: {artifact_id}")
            elif entry.get("owner_skill") != owner:
                errors.append(f"registered artifact owner mismatch in canonical manifest: {artifact_id}")
    elif canonical_manifest is not None:
        errors.append("canonical manifest must be an object")
    return errors


def semver_tuple(value: Any) -> tuple[int, int, int] | None:
    if not isinstance(value, str) or SEMVER_RE.fullmatch(value) is None:
        return None
    return tuple(int(part) for part in value.split("."))  # type: ignore[return-value]


def _escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def semantic_diff_pointers(before: Any, after: Any, path: str = "") -> list[str]:
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
        pointers: list[str] = []
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
    errors: list[str] = []
    mode = revision.get("mode")
    predecessor = revision.get("predecessor_artifact")
    declared = revision.get("changed_json_pointers")
    if not isinstance(declared, list) or not all(isinstance(item, str) and item.startswith("/") for item in declared):
        errors.append("revision_scope.changed_json_pointers must be a unique JSON-pointer array")
        declared = []
    elif len(declared) != len(set(declared)):
        errors.append("revision_scope.changed_json_pointers must be unique")
    if mode == initial_mode:
        if predecessor is not None:
            errors.append("initial revision must have predecessor_artifact null")
        if declared:
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
    if previous.get("approval_status") == "draft" or previous.get("sha256") != canonical_hash(previous):
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
    if sorted(declared) != sorted(pointers):
        errors.append("revision_scope.changed_json_pointers does not exactly match the real predecessor-to-current diff")
    return errors, pointers


def keyed_changes(before: Any, after: Any, key: str) -> tuple[set[str], bool]:
    if not isinstance(before, list) or not isinstance(after, list):
        return set(), True
    before_map = {item.get(key): item for item in before if isinstance(item, dict) and _text(item.get(key))}
    after_map = {item.get(key): item for item in after if isinstance(item, dict) and _text(item.get(key))}
    malformed = len(before_map) != len(before) or len(after_map) != len(after)
    changed = {identity for identity in set(before_map) | set(after_map) if before_map.get(identity) != after_map.get(identity)}
    return changed, malformed


__all__ = [
    "canonical_hash", "keyed_changes", "revision_semantic_view",
    "semantic_diff_pointers", "validate_artifact_envelope", "validate_manifest",
    "validate_predecessor_evidence", "validate_receipt", "verify_artifact_files",
]
