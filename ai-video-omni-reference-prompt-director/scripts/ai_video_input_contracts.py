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


def validate_owner_input(
    value: Any,
    expected_owner: str,
    expected_schema_version: str,
) -> list[str]:
    """Validate only the stable fields consumed from an upstream artifact."""
    if expected_schema_version == "ai-video-shot-contract.v1":
        return validate_shot_contract(value)
    if expected_schema_version == "ai-video-global-look.v1":
        return validate_global_look(value)
    errors = validate_artifact_envelope(value, expected_owner)
    if not isinstance(value, dict):
        return errors
    if value.get("schema_version") != expected_schema_version:
        errors.append(f"schema_version must be {expected_schema_version}")
        return errors
    required_by_version = {
        "ai-video-modular-storyboard.v1": ("script_shot_count", "frames", "storyboard_stage"),
        "ai-video-keyframe-continuity-pack.v1": ("scripted_shot_uids", "shot_records", "authority_inventory"),
        "ai-video-keyframe-boundary-supplement.v1": (
            "scripted_shot_uids", "generation_units", "cross_generation_unit_boundaries",
        ),
        "ai-video-timed-animatic-previs.v1": (
            "shot_count", "source_authorities", "timing_animatic_v1", "control_previs_v2_units",
        ),
        "ai-video-generation-unit-preflight.v1": (
            "generation_units", "project_canon_read_receipt",
        ),
    }
    required = required_by_version.get(expected_schema_version)
    if required is None:
        errors.append(f"unsupported upstream input schema: {expected_schema_version}")
        return errors
    for field in required:
        if field not in value:
            errors.append(f"upstream input missing {field}")
    return errors


def validate_owner_asset_export(record: Any, project_root: Path | None = None) -> list[str]:
    """Validate the portable owner-export interface consumed by Prompt Director."""
    errors = validate_artifact_envelope(record)
    if not isinstance(record, dict):
        return errors
    if record.get("schema_version") != "ai-video-owner-asset-export.v1":
        errors.append("owner asset input requires schema_version ai-video-owner-asset-export.v1")
    for field in (
        "profile_id", "asset_key", "artifact_slot", "artifact_type", "authority_mode",
        "authority_stage", "terminal_route_decision",
    ):
        if not _text(record.get(field)):
            errors.append(f"owner asset input requires {field}")
    roles = record.get("control_roles_authorized")
    if not isinstance(roles, list) or not roles or not all(_text(role) for role in roles) or len(roles) != len(set(roles or [])):
        errors.append("control_roles_authorized must be a non-empty unique string array")
    if record.get("export_status") != "canon_ready":
        errors.append("owner asset export_status must be canon_ready")
    primary = record.get("primary_asset")
    if not isinstance(primary, dict):
        errors.append("owner asset input requires primary_asset")
    elif project_root is not None:
        _verify_file(project_root, primary.get("locator"), primary.get("file_sha256"), "owner asset primary", errors)
    prompt_evidence = record.get("prompt_evidence")
    if not isinstance(prompt_evidence, list) or not prompt_evidence:
        errors.append("owner asset input requires prompt_evidence")
    elif project_root is not None:
        for index, item in enumerate(prompt_evidence):
            if not isinstance(item, dict):
                errors.append(f"prompt_evidence[{index}] must be an object")
                continue
            _verify_file(project_root, item.get("locator"), item.get("file_sha256"), f"prompt_evidence[{index}]", errors)
    approval = record.get("production_approval")
    if not isinstance(approval, dict) or approval.get("status") not in {"user_granted", "external_pipeline_granted"}:
        errors.append("owner asset input requires explicit production approval")
    elif project_root is not None:
        _verify_file(
            project_root, approval.get("evidence_locator"), approval.get("evidence_file_sha256"),
            "owner asset approval evidence", errors,
        )
    authority = record.get("authority_evidence")
    if authority is not None and project_root is not None:
        if not isinstance(authority, dict):
            errors.append("authority_evidence must be an object or null")
        else:
            _verify_file(project_root, authority.get("locator"), authority.get("file_sha256"), "owner asset authority evidence", errors)
    return errors


__all__ = [
    "canonical_hash", "validate_artifact_envelope", "validate_global_look",
    "validate_owner_asset_export", "validate_owner_input", "validate_shot_contract",
]
