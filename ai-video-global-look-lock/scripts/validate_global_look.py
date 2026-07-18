#!/usr/bin/env python3
"""Validate an AI Video Global Look artifact using only the Python standard library."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from ai_video_input_contracts import (
    keyed_changes,
    validate_manifest as validate_project_canon,
    validate_predecessor_evidence,
    validate_receipt,
    verify_artifact_files as verify_project_canon_files,
)


HASH_RE = re.compile(r"^[a-f0-9]{64}$")
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
SHOT_RE = re.compile(r"^[A-Z][A-Z0-9_-]*[0-9][A-Z0-9_-]*$")
STATE_RE = re.compile(r"^LOOK_STATE_[A-Z0-9_-]+$")
REF_RE = re.compile(r"^LOOK_REF_[A-Z0-9_-]+$")

SOURCE_FIELDS = {"source_id", "locator", "source_type", "file_sha256", "integrity_status", "authority_scope", "inspection_status"}
SOURCE_EVIDENCE_FIELDS = {"reference_id", "look_evidence", "intrinsic_facts_deferred_to", "conflicts"}
CONSTRAINT_FIELDS = {"products_present", "characters_present", "multiple_look_states"}
CORE_FIELDS = {"identity", "palette_relationships", "lighting_architecture", "contrast_curve", "black_floor", "highlight_rolloff", "skin_rendering", "material_response", "optical_texture", "grain_and_texture", "atmosphere", "invariant_rules"}
REFERENCE_FIELDS = {"artifact", "reference_id", "locator", "role", "source_type", "source_input_ids", "authority_scope", "applicable_state_ids", "approval_status", "inspection_status", "integrity_status", "file_sha256", "generation_prompt_sha256", "actual_dimensions", "independent_full_frame", "derived_from_multipanel", "intrinsic_boundary_check"}
REFERENCE_ARTIFACT_FIELDS = {"contract_version", "artifact_id", "owner_skill", "version", "sha256", "approval_status", "dependencies", "affected_shot_uids", "stale_reason"}
STATE_FIELDS = {"state_id", "name", "core_relation", "state_prompt_full", "activation_conditions", "illumination_architecture", "exposure_relation", "color_temperature_relation", "light_direction", "contrast_behavior", "skin_tone_protection", "product_color_protection", "material_response_rules", "allowed_deltas", "forbidden_changes", "reference_ids"}
ASSIGNMENT_FIELDS = {"shot_uid", "state_id", "shot_look_delta", "shot_look_delta_prompt_full"}
DELTA_FIELDS = {"active", "scope", "description", "reason", "preserves_look_core"}
RISK_FIELDS = {"risk_id", "risk_type", "subject_asset_ids", "state_ids", "reference_ids", "affected_shot_uids", "coverage_status", "resolution"}
PRODUCT_BOUNDARY_FIELDS = {"product_id", "source_asset_ids", "invariant_base_colors", "invariant_material_properties", "packaging_copy_policy", "prohibited_style_overrides"}
SKIN_BOUNDARY_FIELDS = {"character_id", "source_asset_ids", "preserved_features", "allowed_rendering_variation", "prohibited_identity_changes"}
LOCK_FIELDS = {"textual_contract_frozen", "visual_reference_set_approved", "inheritance_contract_required", "exact_prompt_injection_required", "look_version_binding_required", "look_applied_storyboard_required", "look_applied_keyframe_required", "every_video_prompt_required"}
INVALIDATION_FIELDS = {"core_change_invalidates", "state_change_assigned_shots_only", "shot_delta_change_named_shots_only", "reference_repair_propagates_to_bindings", "neutral_motion_timing_data_preserved_on_look_change"}
REVISION_FIELDS = {"mode", "requested_state_ids", "changed_state_ids", "requested_shot_uids", "changed_shot_uids", "look_core_changed", "invalidated_artifact_ids", "preserved_artifact_ids", "predecessor_artifact", "changed_json_pointers"}


def canonical_sha256(record: dict[str, Any]) -> str:
    payload = dict(record)
    payload.pop("sha256", None)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def verify_declared_file_hashes(record: dict[str, Any], file_root: Path) -> list[str]:
    errors: list[str] = []
    resolved_root = file_root.resolve()
    collections = (("source_inputs", "integrity_status"), ("look_reference_set", "integrity_status"))
    for collection, status_field in collections:
        values = record.get(collection)
        for index, item in enumerate(values if isinstance(values, list) else []):
            if not isinstance(item, dict) or item.get(status_field) != "verified_bytes":
                continue
            locator = item.get("locator")
            if not isinstance(locator, str) or not locator:
                errors.append(f"{collection}[{index}] verified locator missing")
                continue
            if "\\" in locator or locator.startswith("/") or (len(locator) > 1 and locator[0].isalpha() and locator[1] == ":"):
                errors.append(f"{collection}[{index}] verified locator must be project-root-relative and use portable POSIX syntax: {locator}")
                continue
            path = Path(locator)
            if path.is_absolute() or ".." in path.parts:
                errors.append(f"{collection}[{index}] verified locator must be project-root-relative without traversal: {locator}")
                continue
            candidate = (resolved_root / path).resolve()
            try:
                candidate.relative_to(resolved_root)
            except ValueError:
                errors.append(f"{collection}[{index}] verified locator escapes file root: {locator}")
                continue
            if not candidate.is_file():
                errors.append(f"{collection}[{index}] verified file missing: {locator}")
                continue
            actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if actual != item.get("file_sha256"):
                errors.append(f"{collection}[{index}] file_sha256 mismatch")
    return errors


def validate_canon_registration(
    record: dict[str, Any],
    canon_manifest: dict[str, Any],
    project_root: Path,
    receipt: dict[str, Any] | None = None,
) -> list[str]:
    errors = [f"Project Canon invalid: {item}" for item in validate_project_canon(canon_manifest)]
    if not errors:
        errors.extend(f"Project Canon invalid: {item}" for item in verify_project_canon_files(canon_manifest, project_root))
    active = canon_manifest.get("active_artifacts", []) if isinstance(canon_manifest, dict) else []
    root_entry = next(
        (
            item for item in active if isinstance(item, dict)
            and all(item.get(field) == record.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))
        ),
        None,
    )
    if root_entry is None or root_entry.get("eligible_for_downstream") is not True:
        errors.append("root Global Look artifact is not the exact downstream-eligible Project Canon entry")
    expected_ids = {record.get("artifact_id")}
    for index, reference in enumerate(record.get("look_reference_set", [])):
        if not isinstance(reference, dict) or not isinstance(reference.get("artifact"), dict):
            continue
        artifact = reference["artifact"]
        expected_ids.add(artifact.get("artifact_id"))
        entry = next(
            (
                item for item in active if isinstance(item, dict)
                and all(item.get(field) == artifact.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))
                and item.get("locator") == reference.get("locator")
                and item.get("file_sha256") == reference.get("file_sha256")
            ),
            None,
        )
        if entry is None or entry.get("eligible_for_downstream") is not True:
            errors.append(f"look_reference_set[{index}] nested artifact is not registered as exact downstream-eligible Canon asset")
    if receipt is not None:
        errors.extend(
            f"manifest update receipt: {item}"
            for item in validate_receipt(receipt, "ai-video-global-look-lock", expected_ids, canon_manifest)
        )
    return errors


def _object(record: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = record.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key}: required object")
        return {}
    return value


def _array(record: dict[str, Any], key: str, errors: list[str]) -> list[Any]:
    value = record.get(key)
    if not isinstance(value, list):
        errors.append(f"{key}: required array")
        return []
    return value


def _nonempty_string_array(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_text(item) for item in value)


def _exact_fields(value: Any, expected: set[str], label: str, errors: list[str]) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return False
    if set(value) != expected:
        errors.append(f"{label} must contain exact fields: {sorted(expected)}")
        return False
    return True


def render_shot_look_delta_prompt(delta: dict[str, Any]) -> str:
    """Render the only legal frozen prompt form for a structured Shot Look Delta.

    Keeping this deterministic prevents a semantically similar paraphrase from
    silently becoming a second authority.  Every structured value is serialized
    verbatim into the prompt block consumed downstream.
    """
    active = "true" if delta.get("active") is True else "false"
    preserves = "true" if delta.get("preserves_look_core") is True else "false"
    scope = json.dumps(delta.get("scope"), ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return "\n".join(
        (
            "SHOT LOOK DELTA — FROZEN STRUCTURED AUTHORITY",
            f"active: {active}",
            f"scope: {scope}",
            f"description: {delta.get('description')}",
            f"reason: {delta.get('reason')}",
            f"preserves_look_core: {preserves}",
        )
    )


def validate_reference_artifact(
    artifact: Any,
    root_dependencies: list[Any],
    outer_approval: Any,
    label: str,
    errors: list[str],
) -> dict[str, Any]:
    if not _exact_fields(artifact, REFERENCE_ARTIFACT_FIELDS, label, errors):
        return artifact if isinstance(artifact, dict) else {}
    if artifact.get("contract_version") != "ai-video-artifact-v1" or artifact.get("owner_skill") != "ai-video-global-look-lock":
        errors.append(f"{label} contract_version/owner invalid")
    if not _text(artifact.get("artifact_id")) or not str(artifact["artifact_id"]).startswith("LOOK_REFERENCE_ASSET_"):
        errors.append(f"{label}.artifact_id must start with LOOK_REFERENCE_ASSET_")
    version = artifact.get("version")
    if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
        errors.append(f"{label}.version must be SemVer")
    if artifact.get("dependencies") != root_dependencies:
        errors.append(f"{label}.dependencies must exactly equal Global Look upstream locks")
    status = artifact.get("approval_status")
    if outer_approval == "approved" and status not in {"assistant_validated", "user_approved"}:
        errors.append(f"{label} approved outer reference requires validated nested artifact")
    if outer_approval == "draft" and status != "draft":
        errors.append(f"{label} draft outer reference requires draft nested artifact")
    if status == "draft":
        if artifact.get("sha256") is not None:
            errors.append(f"{label} draft sha256 must be null")
    else:
        digest = artifact.get("sha256")
        if not isinstance(digest, str) or not HASH_RE.fullmatch(digest) or digest != canonical_sha256(artifact):
            errors.append(f"{label} canonical sha256 mismatch")
    if status == "stale":
        if not _text(artifact.get("stale_reason")):
            errors.append(f"{label} stale artifact requires stale_reason")
    elif artifact.get("stale_reason") is not None:
        errors.append(f"{label} non-stale artifact requires stale_reason null")
    return artifact


def _validate_look(record: dict[str, Any], previous_record: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version", "contract_version", "artifact_id", "owner_skill", "version", "sha256", "approval_status",
        "dependencies", "affected_shot_uids", "stale_reason", "project_id", "source_inputs", "project_shot_uids", "project_constraints",
        "source_evidence_decomposition", "look_core", "global_look_prompt_full", "look_state_matrix_id", "look_reference_set", "look_states",
        "shot_look_assignments", "look_risk_coverage", "intrinsic_product_boundaries", "skin_tone_boundaries", "allowed_look_delta",
        "negative_look", "three_layer_lock", "invalidation_rules", "revision_scope",
    }
    missing = sorted(required - record.keys())
    if missing:
        errors.append("missing root fields: " + ", ".join(missing))
    extra = sorted(set(record) - required)
    if extra:
        errors.append("unexpected root fields: " + ", ".join(extra))
    if record.get("schema_version") != "ai-video-global-look.v1":
        errors.append("schema_version must be ai-video-global-look.v1")
    if record.get("contract_version") != "ai-video-artifact-v1":
        errors.append("contract_version must be ai-video-artifact-v1")
    if record.get("owner_skill") != "ai-video-global-look-lock":
        errors.append("owner_skill must be ai-video-global-look-lock")
    if not _text(record.get("artifact_id")) or not _text(record.get("project_id")):
        errors.append("artifact_id and project_id must be non-empty")
    if not isinstance(record.get("version"), str) or not SEMVER_RE.fullmatch(record["version"]):
        errors.append("version must use semantic x.y.z form")

    approval = record.get("approval_status")
    if approval not in {"draft", "assistant_validated", "user_approved", "stale", "blocked"}:
        errors.append("approval_status invalid")
    digest = record.get("sha256")
    if approval == "draft":
        if digest is not None:
            errors.append("draft sha256 must be null")
    else:
        if not isinstance(digest, str) or not HASH_RE.fullmatch(digest):
            errors.append("non-draft sha256 must be 64 lowercase hex characters")
        elif digest != canonical_sha256(record):
            errors.append(f"sha256 mismatch: expected {canonical_sha256(record)}")
    stale_reason = record.get("stale_reason")
    if approval == "stale" and not _text(stale_reason):
        errors.append("stale artifact requires stale_reason")
    if approval != "stale" and stale_reason is not None:
        errors.append("non-stale artifact must use stale_reason: null")

    dependencies = _array(record, "dependencies", errors)
    if not dependencies:
        errors.append("dependencies must include the Professional Shot Contract")
    for index, dep in enumerate(dependencies):
        if not isinstance(dep, dict):
            errors.append(f"dependencies[{index}] must be an object")
            continue
        if set(dep) != {"artifact_id", "owner_skill", "version", "sha256"}:
            errors.append(f"dependencies[{index}] must contain exactly artifact_id/owner_skill/version/sha256")
        if not _text(dep.get("artifact_id")) or not _text(dep.get("owner_skill")):
            errors.append(f"dependencies[{index}] artifact_id/owner_skill required")
        version = dep.get("version")
        if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
            errors.append(f"dependencies[{index}].version must be SemVer")
        dep_hash = dep.get("sha256")
        if not isinstance(dep_hash, str) or not HASH_RE.fullmatch(dep_hash):
            errors.append(f"dependencies[{index}].sha256 invalid")
    if not any(isinstance(dep, dict) and dep.get("owner_skill") == "ai-video-shot-script-director" for dep in dependencies):
        errors.append("dependencies must bind ai-video-shot-script-director")

    source_inputs = _array(record, "source_inputs", errors)
    source_ids: list[str] = []
    for index, source in enumerate(source_inputs):
        if not isinstance(source, dict):
            errors.append(f"source_inputs[{index}] must be an object")
            continue
        _exact_fields(source, SOURCE_FIELDS, f"source_inputs[{index}]", errors)
        source_id = source.get("source_id")
        if not _text(source_id):
            errors.append(f"source_inputs[{index}].source_id required")
        else:
            source_ids.append(source_id)
        if not _text(source.get("locator")) or not _nonempty_string_array(source.get("authority_scope")):
            errors.append(f"source_inputs[{index}] locator/authority_scope required")
        if source.get("inspection_status") not in {"pending", "passed", "failed"}:
            errors.append(f"source_inputs[{index}].inspection_status invalid")
        integrity = source.get("integrity_status")
        if integrity not in {"verified_bytes", "runtime_reference_bound", "unavailable"}:
            errors.append(f"source_inputs[{index}].integrity_status invalid")
        if integrity == "verified_bytes":
            file_hash = source.get("file_sha256")
            if not isinstance(file_hash, str) or not HASH_RE.fullmatch(file_hash):
                errors.append(f"source_inputs[{index}] verified_bytes requires file_sha256")
    if len(source_ids) != len(set(source_ids)):
        errors.append("source input IDs must be unique")
    source_id_set = set(source_ids)

    decompositions = _array(record, "source_evidence_decomposition", errors)
    for index, item in enumerate(decompositions):
        if not isinstance(item, dict):
            errors.append(f"source_evidence_decomposition[{index}] must be an object")
            continue
        _exact_fields(item, SOURCE_EVIDENCE_FIELDS, f"source_evidence_decomposition[{index}]", errors)
        if item.get("reference_id") not in source_id_set:
            errors.append(f"source_evidence_decomposition[{index}] references unknown source input")
        if not _nonempty_string_array(item.get("look_evidence")):
            errors.append(f"source_evidence_decomposition[{index}].look_evidence required")

    project_shots = _array(record, "project_shot_uids", errors)
    if not project_shots or len(project_shots) != len(set(project_shots)):
        errors.append("project_shot_uids must be non-empty and unique")
    for uid in project_shots:
        if not isinstance(uid, str) or not SHOT_RE.fullmatch(uid):
            errors.append(f"invalid project shot UID: {uid!r}")
    shot_set = set(project_shots)
    affected = _array(record, "affected_shot_uids", errors)
    if len(affected) != len(set(affected)) or not set(affected).issubset(shot_set):
        errors.append("affected_shot_uids must be unique and belong to project_shot_uids")

    constraints = _object(record, "project_constraints", errors)
    _exact_fields(constraints, CONSTRAINT_FIELDS, "project_constraints", errors)
    for key in ("products_present", "characters_present", "multiple_look_states"):
        if not isinstance(constraints.get(key), bool):
            errors.append(f"project_constraints.{key} must be boolean")

    core = _object(record, "look_core", errors)
    _exact_fields(core, CORE_FIELDS, "look_core", errors)
    for field in ("identity", "contrast_curve", "black_floor", "highlight_rolloff"):
        if not _text(core.get(field)):
            errors.append(f"look_core.{field} must be non-empty")
    for field in ("palette_relationships", "lighting_architecture", "skin_rendering", "material_response", "optical_texture", "grain_and_texture", "atmosphere", "invariant_rules"):
        if not _nonempty_string_array(core.get(field)):
            errors.append(f"look_core.{field} must be a non-empty string array")
    if isinstance(core.get("invariant_rules"), list) and len(core["invariant_rules"]) < 3:
        errors.append("look_core.invariant_rules requires at least 3 rules")
    prompt = record.get("global_look_prompt_full")
    if not _text(prompt) or len(prompt.strip()) < 200:
        errors.append("global_look_prompt_full must be complete, not a short style tag")
    else:
        for field in ("identity", "contrast_curve", "black_floor", "highlight_rolloff"):
            value = core.get(field)
            if _text(value) and value not in prompt:
                errors.append(f"global_look_prompt_full missing exact look_core.{field}")
        for field in ("palette_relationships", "lighting_architecture", "skin_rendering", "material_response", "optical_texture", "grain_and_texture", "atmosphere", "invariant_rules"):
            values = core.get(field)
            for value in values if isinstance(values, list) else []:
                if _text(value) and value not in prompt:
                    errors.append(f"global_look_prompt_full missing exact rule from look_core.{field}: {value}")
    matrix_id = record.get("look_state_matrix_id")
    if not isinstance(matrix_id, str) or not matrix_id.startswith("LOOK_STATE_MATRIX_"):
        errors.append("look_state_matrix_id must start with LOOK_STATE_MATRIX_")

    references = _array(record, "look_reference_set", errors)
    ref_ids: list[str] = []
    ref_artifact_ids: list[str] = []
    ref_artifact_by_reference_id: dict[str, dict[str, Any]] = {}
    approved_ref_ids: set[str] = set()
    hero_ids: list[str] = []
    ref_state_coverage: dict[str, set[str]] = {}
    frozen = approval in {"assistant_validated", "user_approved"}
    for index, ref in enumerate(references):
        if not isinstance(ref, dict):
            errors.append(f"look_reference_set[{index}] must be an object")
            continue
        _exact_fields(ref, REFERENCE_FIELDS, f"look_reference_set[{index}]", errors)
        ref_id = ref.get("reference_id")
        if not isinstance(ref_id, str) or not REF_RE.fullmatch(ref_id):
            errors.append(f"look_reference_set[{index}].reference_id invalid")
            continue
        ref_ids.append(ref_id)
        ref_artifact = validate_reference_artifact(
            ref.get("artifact"), dependencies, ref.get("approval_status"),
            f"look_reference_set[{index}].artifact", errors,
        )
        if isinstance(ref_artifact.get("artifact_id"), str):
            ref_artifact_ids.append(ref_artifact["artifact_id"])
            ref_artifact_by_reference_id[ref_id] = ref_artifact
        if ref.get("role") == "hero_core":
            hero_ids.append(ref_id)
        states = ref.get("applicable_state_ids")
        if not isinstance(states, list) or not states:
            errors.append(f"look_reference_set[{index}].applicable_state_ids required")
            states = []
        ref_state_coverage[ref_id] = set(states)
        if not _nonempty_string_array(ref.get("authority_scope")):
            errors.append(f"look_reference_set[{index}].authority_scope required")
        input_ids = ref.get("source_input_ids")
        if not isinstance(input_ids, list) or not set(input_ids).issubset(source_id_set):
            errors.append(f"look_reference_set[{index}].source_input_ids reference unknown sources")
        if not _text(ref.get("locator")):
            errors.append(f"look_reference_set[{index}].locator required")
        if ref.get("derived_from_multipanel") is not False or ref.get("independent_full_frame") is not True:
            errors.append(f"look_reference_set[{index}] must be an independent full-frame reference")
        if ref.get("integrity_status") == "verified_bytes":
            file_hash = ref.get("file_sha256")
            if not isinstance(file_hash, str) or not HASH_RE.fullmatch(file_hash):
                errors.append(f"look_reference_set[{index}] verified_bytes requires file_sha256")
        if ref.get("source_type") == "machine_generated" and frozen:
            prompt_hash = ref.get("generation_prompt_sha256")
            if not isinstance(prompt_hash, str) or not HASH_RE.fullmatch(prompt_hash):
                errors.append(f"look_reference_set[{index}] generated reference requires generation_prompt_sha256")
        dimensions = ref.get("actual_dimensions")
        if dimensions is not None:
            if not isinstance(dimensions, dict) or any(not isinstance(dimensions.get(k), int) or dimensions[k] < 1 for k in ("width", "height")):
                errors.append(f"look_reference_set[{index}].actual_dimensions invalid")
        if frozen:
            if ref.get("approval_status") != "approved" or ref.get("inspection_status") != "passed" or ref.get("intrinsic_boundary_check") != "passed":
                errors.append(f"look_reference_set[{index}] must be approved, inspected and boundary-checked")
            if ref.get("integrity_status") not in {"verified_bytes", "runtime_reference_bound"}:
                errors.append(f"look_reference_set[{index}] requires usable integrity status")
            approved_ref_ids.add(ref_id)
    if len(ref_ids) != len(set(ref_ids)):
        errors.append("look reference IDs must be unique")
    if len(ref_artifact_ids) != len(set(ref_artifact_ids)) or record.get("artifact_id") in ref_artifact_ids:
        errors.append("look reference artifact IDs must be unique and distinct from the root Global Look artifact")
    if len(hero_ids) != 1:
        errors.append("exactly one hero_core reference is required")

    states = _array(record, "look_states", errors)
    state_ids: list[str] = []
    state_to_refs: dict[str, set[str]] = {}
    for index, state in enumerate(states):
        if not isinstance(state, dict):
            errors.append(f"look_states[{index}] must be an object")
            continue
        _exact_fields(state, STATE_FIELDS, f"look_states[{index}]", errors)
        state_id = state.get("state_id")
        if not isinstance(state_id, str) or not STATE_RE.fullmatch(state_id):
            errors.append(f"look_states[{index}].state_id invalid")
            continue
        state_ids.append(state_id)
        for field in ("name", "core_relation", "illumination_architecture", "exposure_relation", "color_temperature_relation", "light_direction", "contrast_behavior", "skin_tone_protection", "product_color_protection"):
            if not _text(state.get(field)):
                errors.append(f"look_states[{index}].{field} must be non-empty")
        for field in ("activation_conditions", "material_response_rules", "allowed_deltas", "forbidden_changes"):
            if not _nonempty_string_array(state.get(field)):
                errors.append(f"look_states[{index}].{field} must be a non-empty string array")
        ref_list = state.get("reference_ids")
        if not isinstance(ref_list, list) or not ref_list:
            errors.append(f"look_states[{index}].reference_ids required")
            ref_list = []
        state_to_refs[state_id] = set(ref_list)
        state_prompt = state.get("state_prompt_full")
        if not _text(state_prompt) or len(state_prompt.strip()) < 80:
            errors.append(f"look_states[{index}].state_prompt_full must be a frozen complete block")
        else:
            for field in ("core_relation", "illumination_architecture", "exposure_relation", "color_temperature_relation", "light_direction", "contrast_behavior", "skin_tone_protection", "product_color_protection"):
                value = state.get(field)
                if isinstance(value, str) and value not in state_prompt:
                    errors.append(f"look_states[{index}].state_prompt_full missing exact {field}")
            for field in ("activation_conditions", "material_response_rules", "allowed_deltas", "forbidden_changes"):
                for value in state.get(field, []) if isinstance(state.get(field), list) else []:
                    if value not in state_prompt:
                        errors.append(f"look_states[{index}].state_prompt_full missing exact rule from {field}: {value}")
    if len(state_ids) != len(set(state_ids)):
        errors.append("Look State IDs must be unique")
    state_set = set(state_ids)
    if constraints.get("multiple_look_states") is True and len(state_set) < 2:
        errors.append("multiple_look_states requires at least two Look States")
    if constraints.get("multiple_look_states") is False and len(state_set) != 1:
        errors.append("single-state project must contain exactly one Look State")
    for ref_id, covered_states in ref_state_coverage.items():
        unknown = covered_states - state_set
        if unknown:
            errors.append(f"reference {ref_id} covers unknown states: {sorted(unknown)}")
    for state_id, state_refs in state_to_refs.items():
        unknown = state_refs - set(ref_ids)
        if unknown:
            errors.append(f"state {state_id} references unknown look references: {sorted(unknown)}")
        for ref_id in state_refs & set(ref_ids):
            if state_id not in ref_state_coverage.get(ref_id, set()):
                errors.append(f"state/reference coverage is not bidirectional: {state_id} / {ref_id}")
        if frozen and not (state_refs & approved_ref_ids):
            errors.append(f"state {state_id} lacks an approved visual reference")

    assignments = _array(record, "shot_look_assignments", errors)
    mapped_shots: list[str] = []
    assigned_state_by_shot: dict[str, str] = {}
    for index, assignment in enumerate(assignments):
        if not isinstance(assignment, dict):
            errors.append(f"shot_look_assignments[{index}] must be an object")
            continue
        _exact_fields(assignment, ASSIGNMENT_FIELDS, f"shot_look_assignments[{index}]", errors)
        uid, state_id = assignment.get("shot_uid"), assignment.get("state_id")
        mapped_shots.append(uid)
        assigned_state_by_shot[uid] = state_id
        if state_id not in state_set:
            errors.append(f"shot_look_assignments[{index}] references unknown State")
        delta = assignment.get("shot_look_delta")
        if not isinstance(delta, dict):
            errors.append(f"shot_look_assignments[{index}].shot_look_delta required")
            continue
        _exact_fields(delta, DELTA_FIELDS, f"shot_look_assignments[{index}].shot_look_delta", errors)
        if delta.get("preserves_look_core") is not True:
            errors.append(f"shot_look_assignments[{index}] delta must preserve Look Core")
        if delta.get("active") is True and not delta.get("scope"):
            errors.append(f"shot_look_assignments[{index}] active delta requires bounded scope")
        if delta.get("active") is False and delta.get("scope"):
            errors.append(f"shot_look_assignments[{index}] inactive delta cannot declare scope")
        delta_prompt = assignment.get("shot_look_delta_prompt_full")
        if not _text(delta_prompt) or len(delta_prompt.strip()) < 40:
            errors.append(f"shot_look_assignments[{index}].shot_look_delta_prompt_full must be a frozen complete block")
        else:
            expected_prompt = render_shot_look_delta_prompt(delta)
            if delta_prompt != expected_prompt:
                errors.append(
                    f"shot_look_assignments[{index}].shot_look_delta_prompt_full must exactly equal the deterministic structured Delta authority"
                )
    if len(mapped_shots) != len(set(mapped_shots)) or set(mapped_shots) != shot_set:
        errors.append("shot_look_assignments must map every project Shot UID exactly once")
    expected_reference_shots: dict[str, list[str]] = {ref_id: [] for ref_id in ref_ids}
    for uid in project_shots:
        state_id = assigned_state_by_shot.get(uid)
        for ref_id in state_to_refs.get(state_id, set()):
            if ref_id in expected_reference_shots:
                expected_reference_shots[ref_id].append(uid)
    for ref_id, expected_shots in expected_reference_shots.items():
        artifact = ref_artifact_by_reference_id.get(ref_id)
        if not isinstance(artifact, dict):
            errors.append(f"reference {ref_id} has no valid nested artifact")
        elif artifact.get("affected_shot_uids") != expected_shots:
            errors.append(f"reference {ref_id} nested artifact scope must equal assigned shots in project order")

    risks = _array(record, "look_risk_coverage", errors)
    risk_ids: list[str] = []
    risk_types: set[str] = set()
    for index, risk in enumerate(risks):
        if not isinstance(risk, dict):
            errors.append(f"look_risk_coverage[{index}] must be an object")
            continue
        _exact_fields(risk, RISK_FIELDS, f"look_risk_coverage[{index}]", errors)
        risk_id = risk.get("risk_id")
        if not _text(risk_id):
            errors.append(f"look_risk_coverage[{index}].risk_id required")
        else:
            risk_ids.append(risk_id)
        risk_type = risk.get("risk_type")
        if risk_type not in {"product_color", "material_response", "packaging_legibility", "skin_rendering", "low_light_black_floor", "highlight_rolloff", "state_transition", "other"}:
            errors.append(f"look_risk_coverage[{index}].risk_type invalid")
        else:
            risk_types.add(risk_type)
        if not set(risk.get("state_ids", [])).issubset(state_set) or not risk.get("state_ids"):
            errors.append(f"look_risk_coverage[{index}] must reference known States")
        if not set(risk.get("reference_ids", [])).issubset(set(ref_ids)) or not risk.get("reference_ids"):
            errors.append(f"look_risk_coverage[{index}] must reference known look references")
        if not set(risk.get("affected_shot_uids", [])).issubset(shot_set) or not risk.get("affected_shot_uids"):
            errors.append(f"look_risk_coverage[{index}] must reference known shots")
        if not _text(risk.get("resolution")):
            errors.append(f"look_risk_coverage[{index}].resolution required")
        if frozen and risk.get("coverage_status") != "covered":
            errors.append(f"look_risk_coverage[{index}] must be covered before approval")
    if len(risk_ids) != len(set(risk_ids)):
        errors.append("look risk IDs must be unique")
    if constraints.get("products_present") and not risk_types.intersection({"product_color", "material_response", "packaging_legibility"}):
        errors.append("products_present requires structured product/material look risk coverage")
    if constraints.get("characters_present") and "skin_rendering" not in risk_types:
        errors.append("characters_present requires structured skin-rendering risk coverage")

    product_boundaries = _array(record, "intrinsic_product_boundaries", errors)
    if constraints.get("products_present") and not product_boundaries:
        errors.append("products_present requires intrinsic_product_boundaries")
    for index, boundary in enumerate(product_boundaries):
        if not isinstance(boundary, dict):
            errors.append(f"intrinsic_product_boundaries[{index}] must be an object")
            continue
        _exact_fields(boundary, PRODUCT_BOUNDARY_FIELDS, f"intrinsic_product_boundaries[{index}]", errors)
        for field in ("source_asset_ids", "invariant_base_colors", "invariant_material_properties", "prohibited_style_overrides"):
            if not _nonempty_string_array(boundary.get(field)):
                errors.append(f"intrinsic_product_boundaries[{index}].{field} required")
        if not _text(boundary.get("product_id")) or not _text(boundary.get("packaging_copy_policy")):
            errors.append(f"intrinsic_product_boundaries[{index}] identity/copy policy required")

    skin_boundaries = _array(record, "skin_tone_boundaries", errors)
    if constraints.get("characters_present") and not skin_boundaries:
        errors.append("characters_present requires skin_tone_boundaries")
    for index, boundary in enumerate(skin_boundaries):
        if not isinstance(boundary, dict):
            errors.append(f"skin_tone_boundaries[{index}] must be an object")
            continue
        _exact_fields(boundary, SKIN_BOUNDARY_FIELDS, f"skin_tone_boundaries[{index}]", errors)
        for field in ("source_asset_ids", "preserved_features", "allowed_rendering_variation", "prohibited_identity_changes"):
            if not _nonempty_string_array(boundary.get(field)):
                errors.append(f"skin_tone_boundaries[{index}].{field} required")
        if not _text(boundary.get("character_id")):
            errors.append(f"skin_tone_boundaries[{index}].character_id required")

    if not _nonempty_string_array(record.get("allowed_look_delta")):
        errors.append("allowed_look_delta must be non-empty")
    negative = record.get("negative_look")
    if not _nonempty_string_array(negative) or len(negative) < 5:
        errors.append("negative_look requires at least five explicit prohibitions")

    lock = _object(record, "three_layer_lock", errors)
    _exact_fields(lock, LOCK_FIELDS, "three_layer_lock", errors)
    always_true = (
        "inheritance_contract_required", "exact_prompt_injection_required", "look_version_binding_required",
        "look_applied_storyboard_required", "look_applied_keyframe_required", "every_video_prompt_required",
    )
    for field in always_true:
        if lock.get(field) is not True:
            errors.append(f"three_layer_lock.{field} must be true")
    if frozen:
        if lock.get("textual_contract_frozen") is not True or lock.get("visual_reference_set_approved") is not True:
            errors.append("frozen artifact requires all three lock layers approved")

    invalidation = _object(record, "invalidation_rules", errors)
    _exact_fields(invalidation, INVALIDATION_FIELDS, "invalidation_rules", errors)
    required_invalidations = {"look_applied_storyboard_frame", "generation_ready_keyframe", "video_generation_prompt"}
    if set(invalidation.get("core_change_invalidates", [])) != required_invalidations:
        errors.append("core_change_invalidates must cover storyboard, keyframe and video prompt")
    for field in ("state_change_assigned_shots_only", "shot_delta_change_named_shots_only", "reference_repair_propagates_to_bindings", "neutral_motion_timing_data_preserved_on_look_change"):
        if invalidation.get(field) is not True:
            errors.append(f"invalidation_rules.{field} must be true")

    revision = _object(record, "revision_scope", errors)
    _exact_fields(revision, REVISION_FIELDS, "revision_scope", errors)
    mode = revision.get("mode")
    if mode not in {"initial", "core_revision", "state_revision", "shot_delta_revision", "reference_repair"}:
        errors.append("revision_scope.mode invalid")
    changed_states = revision.get("changed_state_ids")
    changed_shots = revision.get("changed_shot_uids")
    if not isinstance(changed_states, list) or not set(changed_states).issubset(state_set):
        errors.append("revision_scope.changed_state_ids invalid")
        changed_states = []
    if not isinstance(changed_shots, list) or not set(changed_shots).issubset(shot_set):
        errors.append("revision_scope.changed_shot_uids invalid")
        changed_shots = []
    if not set(changed_shots).issubset(set(affected)):
        errors.append("affected_shot_uids must include every changed shot")
    if mode == "initial":
        if set(changed_states) != state_set or set(changed_shots) != shot_set or revision.get("look_core_changed") is not True:
            errors.append("initial look artifact must mark Core, all States and all Shots changed")
    if mode == "core_revision":
        if revision.get("look_core_changed") is not True or set(affected) != shot_set:
            errors.append("core_revision must affect every project shot")
        if not revision.get("invalidated_artifact_ids"):
            errors.append("core_revision must list invalidated artifacts")
    if mode == "state_revision":
        if revision.get("look_core_changed") is not False or not changed_states:
            errors.append("state_revision requires changed States and unchanged Core")
        expected = {uid for uid, state_id in assigned_state_by_shot.items() if state_id in set(changed_states)}
        if set(changed_shots) != expected:
            errors.append("state_revision changed_shot_uids must equal shots assigned to changed States")
    if mode == "shot_delta_revision":
        if revision.get("look_core_changed") is not False or not changed_shots:
            errors.append("shot_delta_revision requires named shots and unchanged Core")

    if set(revision.get("invalidated_artifact_ids", [])) & set(revision.get("preserved_artifact_ids", [])):
        errors.append("revision_scope invalidated_artifact_ids and preserved_artifact_ids must be disjoint")
    predecessor_errors, diff_pointers = validate_predecessor_evidence(record, previous_record, revision)
    errors.extend(predecessor_errors)
    if mode != "initial" and previous_record is not None:
        actual_state_changes, malformed_states = keyed_changes(previous_record.get("look_states"), record.get("look_states"), "state_id")
        assignment_changes, malformed_assignments = keyed_changes(previous_record.get("shot_look_assignments"), record.get("shot_look_assignments"), "shot_uid")
        reference_changes, malformed_references = keyed_changes(previous_record.get("look_reference_set"), record.get("look_reference_set"), "reference_id")
        if malformed_states or malformed_assignments or malformed_references:
            errors.append("cannot prove Global Look revision against stable State/Shot/Reference IDs")

        def state_map(value: Any) -> dict[str, str]:
            if not isinstance(value, list):
                return {}
            return {
                item["shot_uid"]: item["state_id"]
                for item in value
                if isinstance(item, dict) and isinstance(item.get("shot_uid"), str) and isinstance(item.get("state_id"), str)
            }

        before_assignments = state_map(previous_record.get("shot_look_assignments"))
        after_assignments = state_map(record.get("shot_look_assignments"))
        reference_state_changes: set[str] = set()
        for collection in (previous_record.get("look_reference_set"), record.get("look_reference_set")):
            for reference in collection if isinstance(collection, list) else []:
                if isinstance(reference, dict) and reference.get("reference_id") in reference_changes:
                    reference_state_changes.update(
                        item for item in reference.get("applicable_state_ids", []) if isinstance(item, str)
                    )
        expected_changed_states = actual_state_changes | reference_state_changes
        if set(changed_states) != expected_changed_states:
            errors.append(
                "revision_scope.changed_state_ids must exactly equal real State/reference-binding changes: "
                + ", ".join(sorted(expected_changed_states))
            )

        actual_core_change = any(
            previous_record.get(field) != record.get(field)
            for field in ("look_core", "global_look_prompt_full", "look_state_matrix_id")
        )
        if revision.get("look_core_changed") is not actual_core_change:
            errors.append("revision_scope.look_core_changed does not match the real predecessor diff")
        expected_changed_shots = set(assignment_changes)
        affected_states = expected_changed_states
        expected_changed_shots.update(
            uid for uid, state_id in {**before_assignments, **after_assignments}.items()
            if state_id in affected_states
        )
        if actual_core_change:
            expected_changed_shots = set(record.get("project_shot_uids", []))
        if set(changed_shots) != expected_changed_shots:
            errors.append(
                "revision_scope.changed_shot_uids must exactly equal real Look propagation scope: "
                + ", ".join(sorted(expected_changed_shots))
            )

        if mode == "state_revision" and (reference_changes or assignment_changes):
            errors.append("state_revision cannot conceal reference or assignment changes")
        if mode == "shot_delta_revision":
            allowed = all(pointer.startswith("/shot_look_assignments/") for pointer in diff_pointers)
            if not allowed or actual_state_changes or reference_changes or actual_core_change:
                errors.append("shot_delta_revision may change only named shot_look_assignments")
        if mode == "reference_repair" and not reference_changes:
            errors.append("reference_repair requires a real look_reference_set change")

    return errors


def validate_look(record: dict[str, Any], previous_record: dict[str, Any] | None = None) -> list[str]:
    try:
        return _validate_look(record, previous_record)
    except (TypeError, KeyError, AttributeError, ValueError, OverflowError) as exc:
        return [f"malformed look contract rejected safely: {type(exc).__name__}: {exc}"]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("root JSON value must be an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--print-hash", action="store_true")
    parser.add_argument("--verify-files-root", type=Path, help="resolve and re-hash verified_bytes locators")
    parser.add_argument("--project-root", type=Path, help="project root for all project-relative authority and Canon locators")
    parser.add_argument("--project-canon-manifest", type=Path)
    parser.add_argument("--manifest-update-receipt", type=Path)
    parser.add_argument("--previous-contract", type=Path, help="required immutable predecessor bytes for every non-initial revision")
    args = parser.parse_args()
    try:
        record = load_json(args.contract)
        previous_record = load_json(args.previous_contract) if args.previous_contract is not None else None
        errors = validate_look(record, previous_record)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    verified_records = []
    for collection in ("source_inputs", "look_reference_set"):
        verified_records.extend(item for item in record.get(collection, []) if isinstance(item, dict) and item.get("integrity_status") == "verified_bytes")
    file_root = args.project_root or args.verify_files_root
    if record.get("approval_status") != "draft" and verified_records and file_root is None:
        errors.append("non-draft verified_bytes references require --project-root")
    if file_root is not None:
        errors.extend(verify_declared_file_hashes(record, file_root.resolve()))
    canon_args = (args.project_root, args.project_canon_manifest, args.manifest_update_receipt)
    if any(item is not None for item in canon_args):
        if not all(item is not None for item in canon_args):
            errors.append(
                "optional Project Canon integration requires --project-root, "
                "--project-canon-manifest, and --manifest-update-receipt together"
            )
        elif record.get("approval_status") in {"assistant_validated", "user_approved"}:
            try:
                canon = load_json(args.project_canon_manifest)
                receipt = load_json(args.manifest_update_receipt)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"Canon/receipt unreadable: {exc}")
            else:
                errors.extend(validate_canon_registration(record, canon, args.project_root.resolve(), receipt))
    if args.print_hash:
        print(canonical_sha256(record))
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"OK: {args.contract}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
