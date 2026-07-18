#!/usr/bin/env python3
"""Validate an AI Video Keyframe Continuity Pack with the Python standard library."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from ai_video_input_contracts import (
    validate_global_look as validate_look,
    validate_manifest as validate_project_canon,
    validate_receipt,
    validate_shot_contract,
    verify_artifact_files as verify_project_canon_files,
    verify_look_files,
    verify_shot_files,
)


HEX64 = set("0123456789abcdef")
APPROVALS = {"draft", "assistant_validated", "user_approved", "stale", "blocked"}
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
FORBIDDEN_PROMPT_TEXT = (
    "text-to-video", "text to video", "t2v", "first-frame", "last-frame",
    "first_frame", "last_frame", "start_frame", "end_frame", "endpoint frame",
    "single-image-to-video", "single image to video", "standalone_single_image_to_video",
    "classic single-image i2v",
)
REQUIRED_FORBIDDEN_VIDEO_MODES = {
    "text_to_video", "first_last_frame", "standalone_single_image_to_video",
}
ENVELOPE_FIELDS = {"contract_version", "artifact_id", "owner_skill", "version", "sha256", "approval_status", "dependencies", "affected_shot_uids", "stale_reason"}
MANIFEST_FIELDS = ENVELOPE_FIELDS | {
    "schema_version", "manifest_role", "project_id", "package_id", "package_status",
    "assistant_qa_status", "production_approval_status", "timing_source", "authority_inventory",
    "forbidden_video_generation_modes",
    "scripted_shot_uids", "shot_records", "inferred_execution_decisions", "upstream_change_requests",
    "qa_report_path", "invalidation_report_path",
}
AUTHORITY_FIELDS = {"artifact_id", "owner_skill", "version", "sha256", "file_sha256", "locator", "authority_type", "approval_status", "affected_shot_uids"}
SHOT_RECORD_FIELDS = {
    "shot_uid", "storyboard_artifact_id", "required_authority_artifact_ids", "global_directing_prompt_full",
    "global_look_artifact_id", "global_look_prompt_full", "look_state_id", "look_state_prompt_full",
    "shot_look_delta_prompt_full", "look_reference_asset_ids", "anchor_route", "keyframes",
    "character_state_ledger", "product_state_ledger", "material_control_required", "material_control_reason",
    "material_anchor_keyframe_ids", "material_state_trajectory", "dynamic_state_ladder", "continuity_in", "continuity_out",
}
KEYFRAME_FIELDS = {
    "artifact", "keyframe_id", "shot_uid", "frame_role", "usage_mode", "source_mode", "file_path",
    "file_sha256", "prompt_path", "prompt_file_sha256", "time_anchor", "terminal_generation_call",
    "generation_turn", "inspection_turn", "visual_qa_status", "promotion_evidence",
}
SUPPLEMENT_FIELDS = ENVELOPE_FIELDS | {
    "schema_version", "project_id", "core_keyframe_manifest", "prompt_preflight", "scripted_shot_uids",
    "generation_units", "supplemental_keyframes", "cross_generation_unit_boundaries", "exemption",
}
UNIT_FIELDS = {"generation_unit_id", "ordered_shot_uids"}
SUPPLEMENTAL_FRAME_FIELDS = {"artifact", "keyframe_id", "shot_uid", "usage_mode", "frame_role", "file_path", "file_sha256", "prompt_path", "prompt_file_sha256", "time_anchor"}
BOUNDARY_FIELDS = {"boundary_id", "boundary_type", "from_generation_unit_id", "to_generation_unit_id", "from_shot_uid", "to_shot_uid", "from_keyframe_id", "to_keyframe_id", "locked_character_state", "locked_product_material_state", "locked_spatial_state", "locked_scene_look_state"}
STORYBOARD_CLEANLINESS_FIELDS = {
    "no_shot_number_overlay", "no_duration_overlay", "no_editorial_caption_overlay",
    "no_arrow_overlay", "no_grid", "no_ui", "no_watermark", "no_layout_chrome",
    "intrinsic_text_policy", "intrinsic_text_source_refs",
}
STORYBOARD_ANNOTATION_FIELDS = STORYBOARD_CLEANLINESS_FIELDS - {"intrinsic_text_policy", "intrinsic_text_source_refs"}
INTRINSIC_TEXT_CATEGORY_TOKENS = {
    "product", "packaging", "package", "label", "scene", "environment",
    "location", "signage", "sign", "storefront",
}
PROMOTION_EVIDENCE_GATES = [
    "independent_source_file",
    "exact_shot_uid_owner",
    "final_approved_storyboard_version",
    "identity_wardrobe_fidelity",
    "product_geometry_material_label_fidelity",
    "scene_global_look_match",
    "composition_action_time_match",
    "dimensions_binary_hash_verified",
    "later_visual_inspection_passed",
    "no_storyboard_annotation_intrinsic_text_source_bound",
    "no_unsupported_completion_or_conflict",
    "promotion_evidence_persisted",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"non-finite number: {x}")))


def is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX64


def safe_file(root: Path, relative: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(relative, str) or not relative:
        errors.append(f"{label}: file path missing")
        return None
    if "\\" in relative or relative.startswith("/") or (
        len(relative) > 1 and relative[0].isalpha() and relative[1] == ":"
    ):
        errors.append(f"{label}: file path must use portable POSIX package-relative syntax")
        return None
    if any(part == ".." for part in relative.split("/")):
        errors.append(f"{label}: file path escapes package root")
        return None
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{label}: file path escapes package root")
        return None
    if not candidate.is_file():
        errors.append(f"{label}: file missing")
        return None
    return candidate


def load_canonical_authority(
    inventory: dict[str, Any],
    canon_manifest: dict[str, Any],
    project_root: Path,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    """Resolve one inventory lock through Project Canon and verify actual JSON bytes."""
    active = canon_manifest.get("active_artifacts")
    entry = next(
        (
            item for item in active if isinstance(item, dict)
            and all(item.get(field) == inventory.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256", "locator", "file_sha256", "approval_status", "affected_shot_uids"))
        ),
        None,
    ) if isinstance(active, list) else None
    if entry is None:
        errors.append(f"{label}: inventory lock is not the exact active Project Canon artifact")
        return None
    if entry.get("approval_status") not in {"assistant_validated", "user_approved"} or entry.get("eligible_for_downstream") is not True or entry.get("stale_reason") is not None:
        errors.append(f"{label}: Project Canon authority is not downstream-eligible")
        return None
    locator = inventory.get("locator")
    file_hash = inventory.get("file_sha256")
    if not isinstance(locator, str) or not locator or not is_hash(file_hash):
        errors.append(f"{label}: authority requires locator and file_sha256")
        return None
    candidate = (project_root / locator).resolve()
    try:
        candidate.relative_to(project_root.resolve())
    except ValueError:
        errors.append(f"{label}: authority locator escapes project root")
        return None
    if not candidate.is_file() or hashlib.sha256(candidate.read_bytes()).hexdigest() != file_hash:
        errors.append(f"{label}: authority file missing or byte hash mismatch")
        return None
    if inventory.get("authority_type") in {"global_look_reference", "character", "product", "packaging", "material", "scene"}:
        return {"_binary_authority": True, **inventory}
    try:
        artifact = load_json(candidate)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"{label}: authority JSON unreadable: {exc}")
        return None
    for field in ("artifact_id", "owner_skill", "version", "sha256", "approval_status", "affected_shot_uids"):
        if artifact.get(field) != inventory.get(field):
            errors.append(f"{label}: authority {field} differs from inventory/Canon lock")
    if artifact.get("approval_status") not in {"assistant_validated", "user_approved"}:
        errors.append(f"{label}: authority artifact is not approved")
    if artifact.get("sha256") != canonical_envelope_hash(artifact):
        errors.append(f"{label}: authority artifact canonical sha256 mismatch")
    if inventory.get("authority_type") == "shot_contract":
        errors.extend(f"{label}: invalid Shot Contract: {item}" for item in [*validate_shot_contract(artifact), *verify_shot_files(artifact, project_root)])
    elif inventory.get("authority_type") == "global_look":
        errors.extend(f"{label}: invalid Global Look: {item}" for item in [*validate_look(artifact), *verify_look_files(artifact, project_root)])
        active_entries = canon_manifest.get("active_artifacts", [])
        for look_ref in artifact.get("look_reference_set", []):
            if not isinstance(look_ref, dict) or not isinstance(look_ref.get("artifact"), dict):
                continue
            ref_artifact = look_ref["artifact"]
            registered = next(
                (
                    item for item in active_entries if isinstance(item, dict)
                    and all(item.get(field) == ref_artifact.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))
                    and item.get("locator") == look_ref.get("locator")
                    and item.get("file_sha256") == look_ref.get("file_sha256")
                ),
                None,
            )
            if registered is None or registered.get("eligible_for_downstream") is not True:
                errors.append(f"{label}: unregistered look reference artifact {ref_artifact.get('artifact_id')}")
    return artifact


def storyboard_intrinsic_text_source_ids(
    frame: dict[str, Any],
    canon_manifest: dict[str, Any],
    storyboard_package_root: Path,
    label: str,
    errors: list[str],
) -> set[str]:
    cleanliness = frame.get("content_cleanliness")
    if not isinstance(cleanliness, dict) or set(cleanliness) != STORYBOARD_CLEANLINESS_FIELDS:
        errors.append(f"{label}: content_cleanliness must contain exact annotation and intrinsic-text fields")
        return set()
    if any(cleanliness.get(field) is not True for field in STORYBOARD_ANNOTATION_FIELDS):
        errors.append(f"{label}: storyboard overlay annotation assertions failed")
    policy = cleanliness.get("intrinsic_text_policy")
    refs = cleanliness.get("intrinsic_text_source_refs")
    if policy not in {"none_visible", "source_authorized_only"} or not isinstance(refs, list):
        errors.append(f"{label}: invalid intrinsic-text policy/source list")
        return set()
    signatures: list[tuple[Any, Any, Any, Any]] = []
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != {"artifact_id", "owner_skill", "version", "sha256"}:
            errors.append(f"{label}: intrinsic text source must be an exact artifact reference")
            continue
        signatures.append(tuple(ref.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256")))
    if len(signatures) != len(set(signatures)):
        errors.append(f"{label}: intrinsic text source references must be unique")
    if policy == "none_visible":
        if refs:
            errors.append(f"{label}: none_visible requires no intrinsic text source references")
        return set()
    if not refs:
        errors.append(f"{label}: source_authorized_only requires intrinsic text source references")
        return set()
    prompt_path = safe_file(storyboard_package_root, frame.get("generation_prompt_path"), f"{label}: Storyboard prompt", errors)
    prompt_text = ""
    if prompt_path is not None:
        if hashlib.sha256(prompt_path.read_bytes()).hexdigest() != frame.get("generation_prompt_file_sha256"):
            errors.append(f"{label}: Storyboard generation prompt hash mismatch")
        prompt_text = prompt_path.read_text(encoding="utf-8", errors="ignore")
    active = canon_manifest.get("active_artifacts")
    active = active if isinstance(active, list) else []
    dependency_signatures = {
        tuple(dep.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))
        for dep in frame.get("dependencies", []) if isinstance(dep, dict)
    }
    result: set[str] = set()
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        signature = tuple(ref.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))
        if signature not in dependency_signatures:
            errors.append(f"{label}: intrinsic text source is not a Storyboard frame dependency: {ref.get('artifact_id')}")
        entry = next(
            (
                item for item in active if isinstance(item, dict)
                and all(item.get(field) == ref.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))
            ),
            None,
        )
        if (
            entry is None
            or entry.get("eligible_for_downstream") is not True
            or entry.get("approval_status") not in {"assistant_validated", "user_approved"}
            or entry.get("stale_reason") is not None
        ):
            errors.append(f"{label}: intrinsic text source is not an exact downstream-eligible Canon authority: {ref.get('artifact_id')}")
            continue
        tokens = set(
            token for token in re.split(
                r"[^a-z0-9]+",
                f"{entry.get('artifact_type', '')} {entry.get('artifact_slot', '')}".lower(),
            ) if token
        )
        if not tokens.intersection(INTRINSIC_TEXT_CATEGORY_TOKENS):
            errors.append(f"{label}: intrinsic text source is not a product/packaging/label/scene authority: {ref.get('artifact_id')}")
        if frame.get("shot_uid") not in entry.get("affected_shot_uids", []):
            errors.append(f"{label}: intrinsic text source does not cover this shot: {ref.get('artifact_id')}")
        if ref.get("artifact_id") not in prompt_text:
            errors.append(f"{label}: intrinsic text source artifact ID missing from Storyboard prompt: {ref.get('artifact_id')}")
        result.add(str(ref.get("artifact_id")))
    return result


def storyboard_frames_by_uid(
    storyboard: dict[str, Any],
    canon_manifest: dict[str, Any],
    project_root: Path,
    storyboard_package_root: Path,
    scripted: list[str],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    """Validate the model-facing semantic projection of the real Storyboard authority."""
    if storyboard.get("owner_skill") != "ai-video-modular-storyboard" or storyboard.get("storyboard_stage") != "look_applied_final":
        errors.append("storyboard authority must be a look_applied_final modular storyboard")
    if storyboard.get("package_status") not in {"assistant_validated", "user_approved"}:
        errors.append("storyboard authority must be validated or user-approved")
    frames = storyboard.get("frames")
    if not isinstance(frames, list):
        errors.append("storyboard authority frames must be an array")
        return {}
    frame_uids = [frame.get("shot_uid") for frame in frames if isinstance(frame, dict)]
    if frame_uids != scripted or storyboard.get("script_shot_count") != len(scripted):
        errors.append("storyboard authority must preserve exact N/order from scripted_shot_uids")
    result: dict[str, dict[str, Any]] = {}
    for index, frame in enumerate(frames):
        label = f"storyboard authority frame[{index}]"
        if not isinstance(frame, dict):
            errors.append(f"{label}: invalid frame record")
            continue
        uid = frame.get("shot_uid")
        result[uid] = frame
        if frame.get("stage") != "look_applied_final" or frame.get("is_model_input_eligible") is not True:
            errors.append(f"{label}: only final independently generated frames are keyframe inputs")
        if frame.get("generation_mode") != "independent_full_frame" or frame.get("independently_generated") is not True or frame.get("derived_from_multipanel") is not False:
            errors.append(f"{label}: frame must be an independent full-frame artifact")
        if frame.get("approval_status") not in {"assistant_validated", "user_approved"} or frame.get("sha256") != canonical_envelope_hash(frame):
            errors.append(f"{label}: frame envelope/hash is not approved canonical authority")
        storyboard_intrinsic_text_source_ids(frame, canon_manifest, storyboard_package_root, label, errors)
        canon_entry = next(
            (
                item for item in canon_manifest.get("active_artifacts", []) if isinstance(item, dict)
                and all(item.get(field) == frame.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))
            ),
            None,
        )
        locator = canon_entry.get("locator") if isinstance(canon_entry, dict) else None
        candidate = (project_root / locator).resolve() if isinstance(locator, str) else None
        if candidate is None:
            errors.append(f"{label}: exact frame artifact is not active in Project Canon")
        else:
            try:
                candidate.relative_to(project_root.resolve())
            except ValueError:
                errors.append(f"{label}: file_path escapes project root")
            else:
                if not candidate.is_file() or hashlib.sha256(candidate.read_bytes()).hexdigest() != frame.get("file_sha256"):
                    errors.append(f"{label}: source frame bytes do not match authority")
    return result


def canonical_envelope_hash(record: dict[str, Any]) -> str:
    payload = dict(record)
    payload.pop("sha256", None)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_envelope(record: Any, label: str, exact_fields: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return [f"{label}: artifact envelope must be an object"]
    required = ENVELOPE_FIELDS
    missing = sorted(required - set(record))
    if missing:
        return [f"{label}: missing envelope fields {missing}"]
    expected_fields = exact_fields if exact_fields is not None else ENVELOPE_FIELDS
    if set(record) != expected_fields:
        errors.append(f"{label}: must contain exact fields {sorted(expected_fields)}")
    if record["contract_version"] != "ai-video-artifact-v1":
        errors.append(f"{label}: contract_version must be ai-video-artifact-v1")
    if not isinstance(record.get("artifact_id"), str) or not record["artifact_id"].strip():
        errors.append(f"{label}: artifact_id must be non-empty")
    if not isinstance(record.get("owner_skill"), str) or not record["owner_skill"].strip():
        errors.append(f"{label}: owner_skill must be non-empty")
    if not isinstance(record["version"], str) or not SEMVER.fullmatch(record["version"]):
        errors.append(f"{label}: version must be SemVer")
    if record["approval_status"] not in APPROVALS:
        errors.append(f"{label}: invalid approval_status")
    if record["approval_status"] == "draft":
        if record["sha256"] is not None:
            errors.append(f"{label}: draft sha256 must be null")
    else:
        if not is_hash(record["sha256"]):
            errors.append(f"{label}: non-draft sha256 must be 64 lowercase hex")
        elif record["sha256"] != canonical_envelope_hash(record):
            errors.append(f"{label}: canonical envelope hash mismatch")
    if record["approval_status"] == "stale":
        if not isinstance(record["stale_reason"], str) or not record["stale_reason"].strip():
            errors.append(f"{label}: stale artifact requires stale_reason")
    elif record["stale_reason"] is not None:
        errors.append(f"{label}: non-stale artifact stale_reason must be null")
    if not isinstance(record["dependencies"], list):
        errors.append(f"{label}: dependencies must be an array")
    else:
        for i, dep in enumerate(record["dependencies"]):
            if not isinstance(dep, dict) or set(dep) != {"artifact_id", "owner_skill", "version", "sha256"} or not is_hash(dep.get("sha256")):
                errors.append(f"{label}: dependency[{i}] must contain exact id/owner/version/hash")
            elif not isinstance(dep.get("version"), str) or not SEMVER.fullmatch(dep["version"]):
                errors.append(f"{label}: dependency[{i}] version must be SemVer")
    shots = record.get("affected_shot_uids")
    if not isinstance(shots, list) or not all(isinstance(item, str) and item.strip() for item in shots):
        errors.append(f"{label}: affected_shot_uids must be a string array")
    elif len(shots) != len(set(shots)):
        errors.append(f"{label}: affected_shot_uids must be unique")
    return errors


def validate_boundary_supplement(
    root: Path,
    supplement: Any,
    core_manifest: dict[str, Any],
    core_keyframe_ids: set[str],
) -> list[str]:
    """Validate the post-preflight boundary artifact without changing the core hash."""
    errors = validate_envelope(supplement, "boundary_supplement", SUPPLEMENT_FIELDS)
    if not isinstance(supplement, dict):
        return errors
    if supplement.get("schema_version") != "ai-video-keyframe-boundary-supplement.v1":
        errors.append("boundary_supplement: wrong schema_version")
    if supplement.get("owner_skill") != "ai-video-keyframe-continuity-pack":
        errors.append("boundary_supplement: wrong owner_skill")
    if supplement.get("approval_status") not in {"assistant_validated", "user_approved"}:
        errors.append("boundary_supplement: must be validated or approved")

    core_ref = supplement.get("core_keyframe_manifest")
    preflight_ref = supplement.get("prompt_preflight")
    for label, ref in (("core_keyframe_manifest", core_ref), ("prompt_preflight", preflight_ref)):
        if not isinstance(ref, dict) or set(ref) != {"artifact_id", "owner_skill", "version", "sha256"}:
            errors.append(f"boundary_supplement/{label}: exact artifact reference required")
            continue
        if not isinstance(ref.get("artifact_id"), str) or not ref["artifact_id"] or not isinstance(ref.get("owner_skill"), str) or not ref["owner_skill"]:
            errors.append(f"boundary_supplement/{label}: ID and owner required")
        if not isinstance(ref.get("version"), str) or not SEMVER.fullmatch(ref["version"]):
            errors.append(f"boundary_supplement/{label}: SemVer required")
        if not is_hash(ref.get("sha256")):
            errors.append(f"boundary_supplement/{label}: hash invalid")
    if isinstance(core_ref, dict):
        expected_core = {
            "artifact_id": core_manifest.get("artifact_id"),
            "owner_skill": core_manifest.get("owner_skill"),
            "version": core_manifest.get("version"),
            "sha256": core_manifest.get("sha256"),
        }
        if core_ref != expected_core:
            errors.append("boundary_supplement: core manifest lock mismatch")
    if isinstance(preflight_ref, dict) and preflight_ref.get("owner_skill") != "ai-video-omni-reference-prompt-director":
        errors.append("boundary_supplement: prompt_preflight owner mismatch")

    expected_deps = {
        tuple(ref.get(key) for key in ("artifact_id", "owner_skill", "version", "sha256"))
        for ref in (core_ref, preflight_ref) if isinstance(ref, dict)
    }
    actual_deps = {
        tuple(ref.get(key) for key in ("artifact_id", "owner_skill", "version", "sha256"))
        for ref in supplement.get("dependencies", []) if isinstance(ref, dict)
    }
    if actual_deps != expected_deps:
        errors.append("boundary_supplement: dependencies must exactly lock core manifest and prompt preflight")

    scripted = supplement.get("scripted_shot_uids")
    if scripted != core_manifest.get("scripted_shot_uids"):
        errors.append("boundary_supplement: scripted_shot_uids must exactly match core manifest order")
        scripted = core_manifest.get("scripted_shot_uids", [])
    if supplement.get("affected_shot_uids") != scripted:
        errors.append("boundary_supplement: affected_shot_uids must equal scripted shots")

    units = supplement.get("generation_units")
    if not isinstance(units, list) or not units:
        errors.append("boundary_supplement: generation_units must be non-empty")
        units = []
    flattened: list[str] = []
    unit_ids: list[str] = []
    for index, unit in enumerate(units):
        if not isinstance(unit, dict):
            errors.append(f"boundary_supplement/generation_units[{index}]: invalid record")
            continue
        if set(unit) != UNIT_FIELDS:
            errors.append(f"boundary_supplement/generation_units[{index}]: unexpected fields")
        unit_id = unit.get("generation_unit_id")
        shots = unit.get("ordered_shot_uids")
        if not isinstance(unit_id, str) or not unit_id or not isinstance(shots, list) or not shots:
            errors.append(f"boundary_supplement/generation_units[{index}]: ID and shots required")
            continue
        unit_ids.append(unit_id)
        flattened.extend(shots)
    if len(unit_ids) != len(set(unit_ids)):
        errors.append("boundary_supplement: generation unit IDs must be unique")
    if flattened != scripted:
        errors.append("boundary_supplement: units must preserve exact scripted shot order")

    supplemental = supplement.get("supplemental_keyframes")
    if not isinstance(supplemental, list):
        errors.append("boundary_supplement: supplemental_keyframes must be an array")
        supplemental = []
    supplemental_ids: set[str] = set()
    core_records_by_uid = {
        item.get("shot_uid"): item for item in core_manifest.get("shot_records", []) if isinstance(item, dict)
    }
    for index, frame in enumerate(supplemental):
        label = f"boundary_supplement/supplemental_keyframes[{index}]"
        if not isinstance(frame, dict):
            errors.append(f"{label}: invalid record")
            continue
        if set(frame) != SUPPLEMENTAL_FRAME_FIELDS:
            errors.append(f"{label}: must contain exact supplemental-keyframe fields")
        frame_id = frame.get("keyframe_id")
        shot_uid = frame.get("shot_uid")
        if not isinstance(frame_id, str) or not frame_id or frame_id in supplemental_ids or frame_id in core_keyframe_ids:
            errors.append(f"{label}: keyframe_id must be unique")
        else:
            supplemental_ids.add(frame_id)
        if shot_uid not in scripted:
            errors.append(f"{label}: shot_uid is not canonical")
        if frame.get("usage_mode") != "omni_reference_anchor" or frame.get("frame_role") != "boundary_handoff":
            errors.append(f"{label}: must be an Omni boundary_handoff anchor")
        errors.extend(validate_envelope(frame.get("artifact"), f"{label}.artifact"))
        frame_artifact = frame.get("artifact") if isinstance(frame.get("artifact"), dict) else {}
        if frame_artifact.get("owner_skill") != "ai-video-keyframe-continuity-pack" or frame_artifact.get("approval_status") not in {"assistant_validated", "user_approved"}:
            errors.append(f"{label}: artifact owner/approval invalid")
        frame_dependencies = {
            tuple(dep.get(key) for key in ("artifact_id", "owner_skill", "version", "sha256"))
            for dep in frame_artifact.get("dependencies", []) if isinstance(dep, dict)
        }
        if frame_dependencies != expected_deps:
            errors.append(f"{label}: artifact dependencies must exactly lock K1 and P1")
        file_path = frame.get("file_path")
        resolved_file = safe_file(root, file_path, label, errors)
        if resolved_file is not None and hashlib.sha256(resolved_file.read_bytes()).hexdigest() != frame.get("file_sha256"):
            errors.append(f"{label}: file_sha256 mismatch")
        prompt_path = frame.get("prompt_path")
        resolved_prompt = safe_file(root, prompt_path, f"{label}: prompt sidecar", errors)
        if resolved_prompt is not None:
            if hashlib.sha256(resolved_prompt.read_bytes()).hexdigest() != frame.get("prompt_file_sha256"):
                errors.append(f"{label}: prompt_file_sha256 mismatch")
            prompt_text = resolved_prompt.read_text(encoding="utf-8", errors="ignore").lower()
            for forbidden in FORBIDDEN_PROMPT_TEXT:
                if forbidden in prompt_text:
                    errors.append(f"{label}: forbidden generation mode in prompt: {forbidden}")
            exact_prompt_text = resolved_prompt.read_text(encoding="utf-8", errors="ignore")
            core_record = core_records_by_uid.get(shot_uid, {})
            for field in ("global_directing_prompt_full", "global_look_prompt_full", "look_state_id", "look_state_prompt_full", "shot_look_delta_prompt_full"):
                value = core_record.get(field)
                if not isinstance(value, str) or value not in exact_prompt_text:
                    errors.append(f"{label}: exact {field} missing from K2 generation prompt")
            for reference_id in core_record.get("look_reference_asset_ids", []):
                if reference_id not in exact_prompt_text:
                    errors.append(f"{label}: look reference artifact {reference_id} missing from K2 generation prompt")

    boundaries = supplement.get("cross_generation_unit_boundaries")
    if not isinstance(boundaries, list):
        errors.append("boundary_supplement: cross_generation_unit_boundaries must be an array")
        boundaries = []
    exemption = supplement.get("exemption")
    if len(units) == 1:
        if exemption != "single_generation_unit" or boundaries:
            errors.append("boundary_supplement: one unit requires single_generation_unit exemption and zero boundaries")
    else:
        if exemption is not None:
            errors.append("boundary_supplement: multi-unit package cannot use exemption")
        if len(boundaries) != len(units) - 1:
            errors.append("boundary_supplement: exactly one record per adjacent generation-unit boundary required")

    all_keyframe_ids = core_keyframe_ids | supplemental_ids
    for index, boundary in enumerate(boundaries):
        label = f"boundary_supplement/boundaries[{index}]"
        if not isinstance(boundary, dict):
            errors.append(f"{label}: invalid record")
            continue
        if set(boundary) != BOUNDARY_FIELDS:
            errors.append(f"{label}: must contain exact boundary fields")
        if boundary.get("boundary_type") != "between_shots":
            errors.append(f"{label}: only between_shots boundaries are legal; split the Shot Contract into stable Shot UIDs upstream")
        if index + 1 < len(units):
            left = units[index]
            right = units[index + 1]
            if boundary.get("from_generation_unit_id") != left.get("generation_unit_id") or boundary.get("to_generation_unit_id") != right.get("generation_unit_id"):
                errors.append(f"{label}: must join adjacent units in order")
            if boundary.get("from_shot_uid") not in left.get("ordered_shot_uids", []) or boundary.get("to_shot_uid") not in right.get("ordered_shot_uids", []):
                errors.append(f"{label}: boundary shots must belong to adjacent units")
        for field in ("from_keyframe_id", "to_keyframe_id"):
            if boundary.get(field) not in all_keyframe_ids:
                errors.append(f"{label}: unknown {field}")
        for field in ("locked_character_state", "locked_product_material_state", "locked_spatial_state", "locked_scene_look_state"):
            if not isinstance(boundary.get(field), str) or not boundary[field].strip():
                errors.append(f"{label}: missing {field}")
    return errors


def _validate_package(
    root: Path,
    canon_manifest: dict[str, Any] | None = None,
    project_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    required = [
        "00_manifest/KEYFRAME_CONTINUITY_MANIFEST.json",
        "00_manifest/KEYFRAME_CONTINUITY_MANIFEST.md",
        "02_ledgers/CHARACTER_STATE_LEDGER.json",
        "02_ledgers/PRODUCT_STATE_LEDGER.json",
        "02_ledgers/MATERIAL_STATE_TRAJECTORY.json",
        "02_ledgers/DYNAMIC_STATE_LADDER.json",
        "04_reports/PROMOTION_REPORT.md",
        "04_reports/QA_REPORT.md",
        "04_reports/INVALIDATION_REPORT.md",
    ]
    for rel in required:
        if not (root / rel).is_file():
            errors.append(f"missing required file: {rel}")
    if errors:
        return errors

    try:
        manifest = load_json(root / required[0])
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"manifest read failed: {exc}"]

    errors.extend(validate_envelope(manifest, "manifest", MANIFEST_FIELDS))
    if manifest.get("schema_version") != "ai-video-keyframe-continuity-pack.v1":
        errors.append("manifest: wrong schema_version")
    if manifest.get("manifest_role") != "core_keyframe_authority_before_generation_unit_preflight":
        errors.append("manifest: wrong manifest_role")
    if manifest.get("owner_skill") != "ai-video-keyframe-continuity-pack":
        errors.append("manifest: wrong owner_skill")
    forbidden_video_modes = manifest.get("forbidden_video_generation_modes")
    if (
        not isinstance(forbidden_video_modes, list)
        or len(forbidden_video_modes) != len(set(forbidden_video_modes))
        or set(forbidden_video_modes) != REQUIRED_FORBIDDEN_VIDEO_MODES
    ):
        errors.append(
            "manifest: forbidden_video_generation_modes must exactly deny T2V, "
            "first/last-frame, and standalone single-image I2V"
        )
    canon_ready = False
    if canon_manifest is not None or project_root is not None:
        if canon_manifest is None or project_root is None:
            errors.append("optional Project Canon integration requires both manifest and project root")
        else:
            canon_structure_errors = validate_project_canon(canon_manifest)
            canon_errors = list(canon_structure_errors)
            if not canon_structure_errors:
                canon_errors.extend(verify_project_canon_files(canon_manifest, project_root))
            errors.extend(f"Project Canon invalid: {item}" for item in canon_errors)
            # A drifted downstream K1 file must fail the package, but it must not
            # prevent independent verification of unchanged upstream authorities.
            canon_ready = not canon_structure_errors

    scripted = manifest.get("scripted_shot_uids")
    records = manifest.get("shot_records")
    if not isinstance(scripted, list) or not scripted:
        errors.append("scripted_shot_uids must be a non-empty array")
        scripted = []
    if len(scripted) != len(set(scripted)):
        errors.append("scripted_shot_uids must be unique")
    if not isinstance(records, list):
        errors.append("shot_records must be an array")
        records = []
    record_uids = [r.get("shot_uid") for r in records if isinstance(r, dict)]
    if len(record_uids) != len(records) or len(record_uids) != len(set(record_uids)):
        errors.append("shot_records must have unique shot_uid values")
    if set(record_uids) != set(scripted):
        errors.append("shot record coverage must exactly equal scripted_shot_uids")

    authorities = manifest.get("authority_inventory")
    if not isinstance(authorities, list):
        errors.append("authority_inventory must be an array")
        authorities = []
    authority_by_id: dict[str, dict[str, Any]] = {}
    authority_artifacts: dict[str, dict[str, Any]] = {}
    types: set[str] = set()
    for index, authority in enumerate(authorities):
        label = f"authority_inventory[{index}]"
        if not isinstance(authority, dict):
            errors.append(f"{label}: must be an object")
            continue
        if set(authority) != AUTHORITY_FIELDS:
            errors.append(f"{label}: must contain exact authority fields including locator/file_sha256")
        authority_id = authority.get("artifact_id")
        if not isinstance(authority_id, str) or not authority_id:
            errors.append(f"{label}: artifact_id required")
            continue
        if authority_id in authority_by_id:
            errors.append(f"{label}: duplicate artifact_id")
        authority_by_id[authority_id] = authority
        authority_type = authority.get("authority_type")
        if not isinstance(authority_type, str):
            errors.append(f"{label}: authority_type required")
        else:
            types.add(authority_type)
        if not isinstance(authority.get("owner_skill"), str) or not authority["owner_skill"]:
            errors.append(f"{label}: owner_skill required")
        if not isinstance(authority.get("version"), str) or not SEMVER.fullmatch(authority["version"]):
            errors.append(f"{label}: version must be SemVer")
        if not is_hash(authority.get("sha256")):
            errors.append(f"{label}: sha256 invalid")
        if authority.get("approval_status") not in {"assistant_validated", "user_approved"}:
            errors.append(f"{label}: authority must be validated or approved")
        locator = authority.get("locator")
        if (
            not isinstance(locator, str)
            or not locator
            or "\\" in locator
            or locator.startswith("/")
            or (len(locator) > 1 and locator[0].isalpha() and locator[1] == ":")
            or Path(locator).is_absolute()
            or ".." in Path(locator).parts
            or not is_hash(authority.get("file_sha256"))
        ):
            errors.append(f"{label}: locator/file_sha256 required")
        scope = authority.get("affected_shot_uids")
        if not isinstance(scope, list) or not all(isinstance(item, str) and item in scripted for item in scope):
            errors.append(f"{label}: affected_shot_uids must be canonical shots")
        if canon_ready and canon_manifest is not None and project_root is not None:
            loaded = load_canonical_authority(authority, canon_manifest, project_root, label, errors)
            if loaded is not None:
                authority_artifacts[authority_id] = loaded
    for required_type in ("shot_contract", "storyboard", "global_look", "global_look_reference"):
        if required_type not in types:
            errors.append(f"authority_inventory missing required {required_type}")
    manifest_deps = {
        (dep.get("artifact_id"), dep.get("owner_skill"), dep.get("version"), dep.get("sha256"))
        for dep in manifest.get("dependencies", []) if isinstance(dep, dict)
    }
    authority_locks = {
        (item.get("artifact_id"), item.get("owner_skill"), item.get("version"), item.get("sha256"))
        for item in authorities if isinstance(item, dict)
    }
    if manifest_deps != authority_locks:
        errors.append("manifest dependencies must exactly lock authority_inventory")

    shot_authority = next((authority_artifacts[item["artifact_id"]] for item in authorities if isinstance(item, dict) and item.get("authority_type") == "shot_contract" and item.get("artifact_id") in authority_artifacts), None)
    look_authority = next((authority_artifacts[item["artifact_id"]] for item in authorities if isinstance(item, dict) and item.get("authority_type") == "global_look" and item.get("artifact_id") in authority_artifacts), None)
    storyboard_inventory = next((item for item in authorities if isinstance(item, dict) and item.get("authority_type") == "storyboard"), None)
    storyboard_authority = authority_artifacts.get(storyboard_inventory.get("artifact_id")) if isinstance(storyboard_inventory, dict) else None
    if shot_authority is not None:
        authoritative_uids = [shot.get("shot_uid") for shot in shot_authority.get("shots", []) if isinstance(shot, dict)]
        if authoritative_uids != scripted:
            errors.append("scripted_shot_uids must exactly equal the real Shot Contract order")
    storyboard_package_root: Path | None = None
    if isinstance(storyboard_inventory, dict) and project_root is not None and isinstance(storyboard_inventory.get("locator"), str):
        storyboard_manifest_path = (project_root / storyboard_inventory["locator"]).resolve()
        storyboard_package_root = storyboard_manifest_path.parent.parent
    storyboard_frames = storyboard_frames_by_uid(
        storyboard_authority, canon_manifest, project_root, storyboard_package_root, scripted, errors
    ) if storyboard_authority is not None and canon_manifest is not None and project_root is not None and storyboard_package_root is not None else {}

    keyframe_ids: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        if set(record) != SHOT_RECORD_FIELDS:
            errors.append(f"shot_records[{record.get('shot_uid')}]: must contain exact shot-record fields")
        shot = record.get("shot_uid")
        required_authorities = record.get("required_authority_artifact_ids")
        if not isinstance(required_authorities, list) or not required_authorities:
            errors.append(f"{shot}: required_authority_artifact_ids must be non-empty")
            required_authorities = []
        elif len(required_authorities) != len(set(required_authorities)):
            errors.append(f"{shot}: required_authority_artifact_ids must be unique")
        unknown_authorities = set(required_authorities) - set(authority_by_id)
        if unknown_authorities:
            errors.append(f"{shot}: unknown required authorities {sorted(unknown_authorities)}")
        shot_authority_types = {
            authority_by_id[authority_id].get("authority_type")
            for authority_id in required_authorities if authority_id in authority_by_id
        }
        for required_type in ("shot_contract", "storyboard", "global_look", "global_look_reference"):
            if required_type not in shot_authority_types:
                errors.append(f"{shot}: missing required {required_type} authority")
        for authority_id in required_authorities:
            if authority_id in authority_by_id and shot not in authority_by_id[authority_id].get("affected_shot_uids", []):
                errors.append(f"{shot}: required authority {authority_id} does not cover this shot")
        global_look_id = record.get("global_look_artifact_id")
        if global_look_id not in required_authorities or authority_by_id.get(global_look_id, {}).get("authority_type") != "global_look":
            errors.append(f"{shot}: global_look_artifact_id must identify the required Global Look authority")
        look_prompt_fields = (
            ("global_directing_prompt_full", 40),
            ("global_look_prompt_full", 200),
            ("look_state_id", 1),
            ("look_state_prompt_full", 80),
            ("shot_look_delta_prompt_full", 1),
        )
        for field, minimum in look_prompt_fields:
            value = record.get(field)
            if not isinstance(value, str) or len(value.strip()) < minimum:
                errors.append(f"{shot}: {field} must be a frozen non-empty block")
        look_reference_ids = record.get("look_reference_asset_ids")
        if not isinstance(look_reference_ids, list) or not look_reference_ids or not all(isinstance(item, str) and item for item in look_reference_ids) or len(look_reference_ids) != len(set(look_reference_ids)):
            errors.append(f"{shot}: look_reference_asset_ids must be non-empty and unique")
            look_reference_ids = []
        for reference_id in look_reference_ids:
            if reference_id not in required_authorities or authority_by_id.get(reference_id, {}).get("authority_type") != "global_look_reference":
                errors.append(f"{shot}: look reference artifact {reference_id} must be an exact required global_look_reference authority")
        if shot_authority is not None and record.get("global_directing_prompt_full") != shot_authority.get("global_directing_prompt_full"):
            errors.append(f"{shot}: Global Directing block differs from real Shot Contract")
        if look_authority is not None:
            assignment = next((item for item in look_authority.get("shot_look_assignments", []) if isinstance(item, dict) and item.get("shot_uid") == shot), None)
            states = {item.get("state_id"): item for item in look_authority.get("look_states", []) if isinstance(item, dict)}
            if not isinstance(assignment, dict):
                errors.append(f"{shot}: real Global Look has no shot assignment")
            else:
                state = states.get(assignment.get("state_id"), {})
                reference_artifact_by_id = {
                    item.get("reference_id"): item.get("artifact", {}).get("artifact_id")
                    for item in look_authority.get("look_reference_set", []) if isinstance(item, dict) and isinstance(item.get("artifact"), dict)
                }
                expected_look = {
                    "global_look_artifact_id": look_authority.get("artifact_id"),
                    "global_look_prompt_full": look_authority.get("global_look_prompt_full"),
                    "look_state_id": assignment.get("state_id"),
                    "look_state_prompt_full": state.get("state_prompt_full"),
                    "shot_look_delta_prompt_full": assignment.get("shot_look_delta_prompt_full"),
                    "look_reference_asset_ids": [reference_artifact_by_id.get(ref_id) for ref_id in state.get("reference_ids", [])],
                }
                for field, expected in expected_look.items():
                    if record.get(field) != expected:
                        errors.append(f"{shot}: {field} differs from real Global Look authority")
        storyboard_frame = storyboard_frames.get(shot)
        if storyboard_frame is not None:
            if record.get("storyboard_artifact_id") != storyboard_frame.get("artifact_id"):
                errors.append(f"{shot}: storyboard_artifact_id must select the real per-shot Storyboard frame")
            for field in ("global_directing_prompt_full", "global_look_prompt_full", "look_state_id", "look_state_prompt_full", "shot_look_delta_prompt_full", "look_reference_asset_ids"):
                if record.get(field) != storyboard_frame.get(field):
                    errors.append(f"{shot}: {field} differs from real Storyboard frame")
            intrinsic_source_ids = {
                ref.get("artifact_id")
                for ref in storyboard_frame.get("content_cleanliness", {}).get("intrinsic_text_source_refs", [])
                if isinstance(ref, dict)
            }
            if not intrinsic_source_ids.issubset(set(required_authorities)):
                errors.append(f"{shot}: intrinsic text source authorities must remain required Keyframe authorities")
            for source_id in intrinsic_source_ids:
                if authority_by_id.get(source_id, {}).get("authority_type") not in {"product", "packaging", "scene"}:
                    errors.append(f"{shot}: intrinsic text source must be inventoried as product, packaging, or scene authority: {source_id}")
        expected_frame_dependencies = {
            (
                authority_by_id[authority_id].get("artifact_id"),
                authority_by_id[authority_id].get("owner_skill"),
                authority_by_id[authority_id].get("version"),
                authority_by_id[authority_id].get("sha256"),
            )
            for authority_id in required_authorities if authority_id in authority_by_id
        }
        frames = record.get("keyframes")
        if not isinstance(frames, list) or not frames:
            errors.append(f"{shot}: requires at least one keyframe")
            continue
        route = record.get("anchor_route")
        if route not in {"independent_keyframe", "validated_storyboard_promotion"}:
            errors.append(f"{shot}: invalid anchor_route")
        ladder = record.get("dynamic_state_ladder")
        if not isinstance(ladder, list) or not ladder:
            errors.append(f"{shot}: dynamic_state_ladder must be non-empty")
        else:
            orders = [node.get("order") for node in ladder if isinstance(node, dict)]
            if orders != list(range(1, len(ladder) + 1)):
                errors.append(f"{shot}: dynamic state order must be contiguous from 1")

        material_required = record.get("material_control_required")
        material_reason = record.get("material_control_reason")
        trajectories = record.get("material_state_trajectory")
        material_anchor_ids = record.get("material_anchor_keyframe_ids")
        if not isinstance(material_required, bool):
            errors.append(f"{shot}: material_control_required must be boolean")
        if not isinstance(material_reason, str) or not material_reason.strip():
            errors.append(f"{shot}: material_control_reason required")
        if not isinstance(trajectories, list):
            errors.append(f"{shot}: material_state_trajectory must be an array")
            trajectories = []
        if not isinstance(material_anchor_ids, list) or not all(isinstance(item, str) and item for item in material_anchor_ids):
            errors.append(f"{shot}: material_anchor_keyframe_ids must be a string array")
            material_anchor_ids = []
        elif len(material_anchor_ids) != len(set(material_anchor_ids)):
            errors.append(f"{shot}: material_anchor_keyframe_ids must be unique")
        if material_required and (not trajectories or not material_anchor_ids):
            errors.append(f"{shot}: required material control needs trajectory and anchor keyframe IDs")
        if material_required is False and (trajectories or material_anchor_ids):
            errors.append(f"{shot}: material trajectory/anchors require material_control_required true")

        for frame in frames:
            if not isinstance(frame, dict):
                errors.append(f"{shot}: keyframe record must be an object")
                continue
            if set(frame) != KEYFRAME_FIELDS:
                errors.append(f"{shot}: keyframe record must contain exact fields")
            frame_id = frame.get("keyframe_id")
            if frame_id in keyframe_ids:
                errors.append(f"duplicate keyframe_id: {frame_id}")
            keyframe_ids.add(frame_id)
            if frame.get("shot_uid") != shot:
                errors.append(f"{shot}/{frame_id}: shot_uid mismatch")
            if frame.get("usage_mode") != "omni_reference_anchor":
                errors.append(f"{shot}/{frame_id}: only omni_reference_anchor is allowed")
            if frame.get("frame_role") not in {"primary_anchor", "action_state", "material_state", "boundary_handoff"}:
                errors.append(f"{shot}/{frame_id}: invalid frame_role")
            if frame.get("frame_role") == "material_state" and material_required is not True:
                errors.append(f"{shot}/{frame_id}: material_state frame requires material_control_required true")
            source = frame.get("source_mode")
            if source != route:
                errors.append(f"{shot}/{frame_id}: source_mode must match anchor_route")
            if not is_hash(frame.get("file_sha256")):
                errors.append(f"{shot}/{frame_id}: invalid file_sha256")
            rel = frame.get("file_path")
            resolved_frame = safe_file(root, rel, f"{shot}/{frame_id}: keyframe", errors)
            if resolved_frame is not None and hashlib.sha256(resolved_frame.read_bytes()).hexdigest() != frame.get("file_sha256"):
                errors.append(f"{shot}/{frame_id}: file_sha256 mismatch")
            if canon_manifest is not None and project_root is not None and resolved_frame is not None:
                try:
                    expected_locator = resolved_frame.resolve().relative_to(project_root.resolve()).as_posix()
                except ValueError:
                    expected_locator = None
                frame_artifact_for_canon = frame.get("artifact") if isinstance(frame.get("artifact"), dict) else {}
                canon_frame_entry = next(
                    (
                        item for item in canon_manifest.get("active_artifacts", []) if isinstance(item, dict)
                        and all(item.get(field) == frame_artifact_for_canon.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))
                    ),
                    None,
                )
                if expected_locator is None or canon_frame_entry is None or canon_frame_entry.get("locator") != expected_locator or canon_frame_entry.get("file_sha256") != frame.get("file_sha256"):
                    errors.append(f"{shot}/{frame_id}: primary keyframe bytes are not the exact active Project Canon entry")
            errors.extend(validate_envelope(frame.get("artifact"), f"{shot}/{frame_id}.artifact"))
            artifact = frame.get("artifact") if isinstance(frame.get("artifact"), dict) else {}
            if artifact.get("approval_status") not in {"assistant_validated", "user_approved"}:
                errors.append(f"{shot}/{frame_id}: keyframe artifact must be approved")
            actual_frame_dependencies = {
                tuple(dep.get(key) for key in ("artifact_id", "owner_skill", "version", "sha256"))
                for dep in artifact.get("dependencies", []) if isinstance(dep, dict)
            }
            if actual_frame_dependencies != expected_frame_dependencies:
                errors.append(f"{shot}/{frame_id}: artifact dependencies must exactly lock required shot authorities")
            if source == "independent_keyframe":
                prompt = frame.get("prompt_path")
                if frame.get("terminal_generation_call") != "executed":
                    errors.append(f"{shot}/{frame_id}: independent generation must be executed")
                resolved_prompt = safe_file(root, prompt, f"{shot}/{frame_id}: generation prompt sidecar", errors)
                if resolved_prompt is not None:
                    if hashlib.sha256(resolved_prompt.read_bytes()).hexdigest() != frame.get("prompt_file_sha256"):
                        errors.append(f"{shot}/{frame_id}: prompt_file_sha256 mismatch")
                    prompt_text = resolved_prompt.read_text(encoding="utf-8", errors="ignore").lower()
                    for forbidden in FORBIDDEN_PROMPT_TEXT:
                        if forbidden in prompt_text:
                            errors.append(f"{shot}/{frame_id}: forbidden generation mode in prompt: {forbidden}")
                    exact_prompt_text = resolved_prompt.read_text(encoding="utf-8", errors="ignore")
                    for field, _ in look_prompt_fields:
                        if isinstance(record.get(field), str) and record[field] not in exact_prompt_text:
                            errors.append(f"{shot}/{frame_id}: exact {field} missing from generation prompt")
                    for reference_id in look_reference_ids:
                        if reference_id not in exact_prompt_text:
                            errors.append(f"{shot}/{frame_id}: look reference {reference_id} missing from generation prompt")
                gt, it = frame.get("generation_turn"), frame.get("inspection_turn")
                if not isinstance(gt, int) or not isinstance(it, int) or it <= gt:
                    errors.append(f"{shot}/{frame_id}: later visual inspection must follow generation")
            elif source == "validated_storyboard_promotion":
                if frame.get("terminal_generation_call") != "not_applicable_promoted":
                    errors.append(f"{shot}/{frame_id}: promoted frame terminal state invalid")
                if frame.get("generation_turn") is not None:
                    errors.append(f"{shot}/{frame_id}: promoted frame generation_turn must be null")
                if frame.get("prompt_path") is not None or frame.get("prompt_file_sha256") is not None:
                    errors.append(f"{shot}/{frame_id}: promoted frame prompt path/hash must be null")
                evidence = frame.get("promotion_evidence")
                if evidence != PROMOTION_EVIDENCE_GATES:
                    errors.append(f"{shot}/{frame_id}: promotion needs the exact ordered 12 evidence gates")
                if storyboard_frame is None or frame.get("file_sha256") != storyboard_frame.get("file_sha256"):
                    errors.append(f"{shot}/{frame_id}: promoted bytes must exactly equal the selected real Storyboard frame")
            if frame.get("visual_qa_status") != "passed":
                errors.append(f"{shot}/{frame_id}: visual QA must pass")
        shot_frame_ids = {frame.get("keyframe_id") for frame in frames if isinstance(frame, dict)}
        if not set(material_anchor_ids).issubset(shot_frame_ids):
            errors.append(f"{shot}: material_anchor_keyframe_ids must reference this shot's keyframes")
        for trajectory_index, trajectory in enumerate(trajectories):
            if not isinstance(trajectory, dict):
                errors.append(f"{shot}: material trajectory {trajectory_index} must be an object")
                continue
            states = trajectory.get("states")
            if not isinstance(states, list) or not states:
                errors.append(f"{shot}: material trajectory {trajectory_index} requires states")
                continue
            for state_index, state in enumerate(states):
                if not isinstance(state, dict):
                    errors.append(f"{shot}: material state {state_index} must be an object")
                    continue
                for field in ("state_id", "fill_level", "viscosity_flow", "droplet_stream_meniscus", "wetting_footprint", "reflection_refraction", "surface_highlight_state"):
                    if not isinstance(state.get(field), str) or not state[field].strip():
                        errors.append(f"{shot}: material state {state_index} missing {field}")

    timing = manifest.get("timing_source")
    if not isinstance(timing, dict):
        errors.append("timing_source must be an object")
    elif timing.get("mode") == "single_static_shot_exemption":
        if len(scripted) != 1 or any(timing.get(k) is not None for k in ("artifact_id", "owner_skill", "version", "sha256")):
            errors.append("single-static-shot exemption is valid only for one shot and null timing reference")
    elif timing.get("mode") == "v1_timing_animatic":
        if not timing.get("artifact_id") or not timing.get("owner_skill") or not timing.get("version") or not SEMVER.fullmatch(str(timing.get("version"))) or not is_hash(timing.get("sha256")):
            errors.append("V1 timing animatic requires exact id/owner/SemVer/hash")
        elif "timing_animatic_v1" not in types:
            errors.append("authority_inventory missing timing_animatic_v1")
    else:
        errors.append("invalid timing_source mode")

    projection_specs = [
        ("02_ledgers/CHARACTER_STATE_LEDGER.json", "character_state_ledger", "character_state_ledger"),
        ("02_ledgers/PRODUCT_STATE_LEDGER.json", "product_state_ledger", "product_state_ledger"),
        ("02_ledgers/MATERIAL_STATE_TRAJECTORY.json", "material_state_trajectory", "material_state_trajectory"),
        ("02_ledgers/DYNAMIC_STATE_LADDER.json", "dynamic_state_ladder", "dynamic_state_ladder"),
    ]
    for rel, projection_type, source_field in projection_specs:
        try:
            projection = load_json(root / rel)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{rel}: projection read failed: {exc}")
            continue
        errors.extend(validate_envelope(projection, rel, ENVELOPE_FIELDS | {"schema_version", "projection_type", "records"}))
        if projection.get("owner_skill") != "ai-video-keyframe-continuity-pack":
            errors.append(f"{rel}: wrong owner_skill")
        if projection.get("schema_version") != "ai-video-keyframe-continuity-projection.v1" or projection.get("projection_type") != projection_type:
            errors.append(f"{rel}: projection contract mismatch")
        if projection.get("approval_status") not in {"assistant_validated", "user_approved"}:
            errors.append(f"{rel}: projection must be approved")
        expected_records = [{"shot_uid": record.get("shot_uid"), "data": record.get(source_field)} for record in records if isinstance(record, dict)]
        if projection.get("records") != expected_records:
            errors.append(f"{rel}: projection records do not exactly match manifest")
        if not any(dep.get("artifact_id") == manifest.get("artifact_id") and dep.get("sha256") == manifest.get("sha256") for dep in projection.get("dependencies", []) if isinstance(dep, dict)):
            errors.append(f"{rel}: manifest dependency lock missing")

    supplement_path = root / "03_boundaries/BOUNDARY_SUPPLEMENT.json"
    if supplement_path.exists():
        try:
            supplement = load_json(supplement_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"03_boundaries/BOUNDARY_SUPPLEMENT.json: read failed: {exc}")
        else:
            errors.extend(validate_boundary_supplement(root, supplement, manifest, keyframe_ids))

    receipt_path = root / "00_manifest/MANIFEST_UPDATE_RECEIPT.json"
    if receipt_path.is_file():
        try:
            receipt = load_json(receipt_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"manifest update receipt read failed: {exc}")
        else:
            expected_registered = {manifest.get("artifact_id"), *keyframe_ids}
            for rel, _, _ in projection_specs:
                try:
                    projection_for_receipt = load_json(root / rel)
                except (OSError, json.JSONDecodeError, ValueError):
                    continue
                if isinstance(projection_for_receipt, dict):
                    expected_registered.add(projection_for_receipt.get("artifact_id"))
            if supplement_path.is_file():
                try:
                    supplement_for_receipt = load_json(supplement_path)
                except (OSError, json.JSONDecodeError, ValueError):
                    pass
                else:
                    if isinstance(supplement_for_receipt, dict):
                        expected_registered.add(supplement_for_receipt.get("artifact_id"))
            errors.extend(
                f"manifest update receipt: {item}"
                for item in validate_receipt(
                    receipt,
                    "ai-video-keyframe-continuity-pack",
                    expected_registered,
                    canon_manifest,
                )
            )
    elif canon_manifest is not None:
        errors.append("optional Project Canon integration requires MANIFEST_UPDATE_RECEIPT.json")

    if manifest.get("package_status") == "packaged":
        if manifest.get("assistant_qa_status") != "passed":
            errors.append("packaged manifest requires assistant_qa_status passed")
        if manifest.get("approval_status") not in {"assistant_validated", "user_approved"}:
            errors.append("packaged manifest envelope must be approved")

    return errors


def validate_package(
    root: Path,
    canon_manifest: dict[str, Any] | None = None,
    project_root: Path | None = None,
) -> list[str]:
    try:
        return _validate_package(root, canon_manifest, project_root)
    except (TypeError, KeyError, AttributeError, ValueError, OverflowError) as exc:
        return [f"malformed keyframe package rejected safely: {type(exc).__name__}: {exc}"]


def main(argv: list[str]) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_root", type=Path)
    parser.add_argument("--project-canon-manifest", type=Path)
    parser.add_argument("--project-root", type=Path, help="whole project root for Canon and cross-owner locators")
    args = parser.parse_args(argv[1:])
    root = args.package_root.resolve()
    canon_manifest = None
    project_root = None
    if args.project_canon_manifest is not None:
        if args.project_root is None:
            print("ERROR: --project-root is required with --project-canon-manifest", file=sys.stderr)
            return 2
        try:
            canon_manifest = load_json(args.project_canon_manifest)
            project_root = args.project_root.resolve()
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"ERROR: Project Canon manifest unreadable: {exc}", file=sys.stderr)
            return 2
    errors = validate_package(root, canon_manifest, project_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: keyframe continuity package contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
