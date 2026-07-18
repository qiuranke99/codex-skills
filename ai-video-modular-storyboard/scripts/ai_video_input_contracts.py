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


def validate_shot_contract(value: Any) -> list[str]:
    errors = validate_artifact_envelope(value, "ai-video-shot-script-director")
    if not isinstance(value, dict):
        return errors
    if not _text(value.get("global_directing_prompt_full")):
        errors.append("Shot Contract input requires global_directing_prompt_full")
    shots = value.get("shots")
    if not isinstance(shots, list) or not shots:
        errors.append("Shot Contract input requires a non-empty shots array")
        return errors
    uids: list[str] = []
    total = 0.0
    for index, shot in enumerate(shots):
        if not isinstance(shot, dict):
            errors.append(f"shots[{index}] must be an object")
            continue
        uid = shot.get("shot_uid")
        if not _text(uid):
            errors.append(f"shots[{index}].shot_uid must be non-empty")
        else:
            uids.append(uid)
        duration = shot.get("target_duration_seconds")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
            errors.append(f"shots[{index}].target_duration_seconds must be positive")
        else:
            total += float(duration)
        if not isinstance(shot.get("action_path"), list) or not shot["action_path"]:
            errors.append(f"shots[{index}] requires an observable action_path")
        if not _text(shot.get("ending_state")):
            errors.append(f"shots[{index}] requires ending_state")
    if len(uids) != len(set(uids)):
        errors.append("Shot Contract input shot_uids must be unique")
    affected = value.get("affected_shot_uids")
    if isinstance(affected, list) and set(affected) != set(uids):
        errors.append("Shot Contract affected_shot_uids must equal its shots")
    timeline = value.get("timeline")
    if isinstance(timeline, dict) and isinstance(timeline.get("total_duration_seconds"), (int, float)):
        if abs(float(timeline["total_duration_seconds"]) - total) > 0.001:
            errors.append("Shot Contract timeline does not equal summed shot durations")
    return errors


def validate_global_look(value: Any) -> list[str]:
    errors = validate_artifact_envelope(value, "ai-video-global-look-lock")
    if not isinstance(value, dict):
        return errors
    if not _text(value.get("global_look_prompt_full")):
        errors.append("Global Look input requires global_look_prompt_full")
    states = value.get("look_states")
    assignments = value.get("shot_look_assignments")
    references = value.get("look_reference_set")
    if not isinstance(states, list) or not states:
        errors.append("Global Look input requires look_states")
        states = []
    state_ids: set[str] = set()
    for index, state in enumerate(states):
        if not isinstance(state, dict) or not _text(state.get("state_id")) or not _text(state.get("state_prompt_full")):
            errors.append(f"look_states[{index}] requires state_id and state_prompt_full")
            continue
        state_ids.add(state["state_id"])
    if not isinstance(assignments, list) or not assignments:
        errors.append("Global Look input requires shot_look_assignments")
        assignments = []
    assigned_uids: list[str] = []
    for index, assignment in enumerate(assignments):
        if not isinstance(assignment, dict) or not _text(assignment.get("shot_uid")):
            errors.append(f"shot_look_assignments[{index}] requires shot_uid")
            continue
        assigned_uids.append(assignment["shot_uid"])
        if assignment.get("state_id") not in state_ids:
            errors.append(f"shot_look_assignments[{index}] references an unknown State")
        if not _text(assignment.get("shot_look_delta_prompt_full")):
            errors.append(f"shot_look_assignments[{index}] requires shot_look_delta_prompt_full")
    if len(assigned_uids) != len(set(assigned_uids)):
        errors.append("Global Look input assigns a shot more than once")
    affected = value.get("affected_shot_uids")
    if isinstance(affected, list) and set(affected) != set(assigned_uids):
        errors.append("Global Look affected_shot_uids must equal its assignments")
    if not isinstance(references, list) or not references:
        errors.append("Global Look input requires look_reference_set")
    else:
        for index, reference in enumerate(references):
            artifact = reference.get("artifact") if isinstance(reference, dict) else None
            errors.extend(
                f"look_reference_set[{index}]: {error}"
                for error in validate_artifact_envelope(artifact, "ai-video-global-look-lock")
            )
    return errors


def verify_declared_file_hashes(record: dict[str, Any], file_root: Path) -> list[str]:
    errors: list[str] = []
    for collection in ("source_inputs", "look_reference_set"):
        values = record.get(collection)
        for index, item in enumerate(values if isinstance(values, list) else []):
            if not isinstance(item, dict) or item.get("integrity_status") != "verified_bytes":
                continue
            _verify_file(file_root, item.get("locator"), item.get("file_sha256"), f"{collection}[{index}]", errors)
    return errors


verify_shot_files = verify_declared_file_hashes
verify_look_files = verify_declared_file_hashes


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


__all__ = [
    "canonical_hash", "validate_artifact_envelope", "validate_global_look",
    "validate_manifest", "validate_receipt", "validate_shot_contract",
    "verify_artifact_files", "verify_declared_file_hashes",
    "verify_look_files", "verify_shot_files",
]
