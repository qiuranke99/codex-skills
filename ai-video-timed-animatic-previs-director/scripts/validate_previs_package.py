#!/usr/bin/env python3
"""Validate a Timing Animatic / Control Previs package using only stdlib."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

from ai_video_input_contracts import (
    validate_receipt,
    validate_manifest as validate_project_canon,
    verify_artifact_files as verify_project_canon_files,
)
from probe_control_media import MediaProbeError, probe_media

OWNER = "ai-video-timed-animatic-previs-director"
CONTRACT_VERSION = "ai-video-artifact-v1"
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
ENVELOPE_STATUSES = {"draft", "assistant_validated", "user_approved", "stale", "blocked"}
HASH_STATUSES = ENVELOPE_STATUSES - {"draft"}
READY_STATUSES = {"assistant_validated", "user_approved"}
ALLOWED_CONTROLS = {
    "shot_boundaries", "target_timing", "camera_trajectory", "subject_blocking",
    "object_motion", "material_physics",
}
FORBIDDEN_DIMENSIONS = {
    "character_identity", "wardrobe_identity", "product_geometry", "packaging_text",
    "scene_identity", "global_look", "final_color_grade", "music", "final_edit", "output_qc",
}
ALLOWED_GENERATION_MODES = {"deterministic_animatic", "neutral_2d_blocking", "neutral_3d_blocking"}
PROHIBITED_GENERATION_MODES = {
    "text_to_video", "first_last_frame", "standalone_single_image_to_video",
}
TIME_TOLERANCE = 0.001
MEDIA_DURATION_TOLERANCE = 0.05
ENVELOPE_FIELDS = {
    "contract_version", "artifact_id", "owner_skill", "version", "sha256",
    "approval_status", "dependencies", "affected_shot_uids", "stale_reason",
}
MANIFEST_FIELDS = ENVELOPE_FIELDS | {
    "schema_version", "project_id", "package_status", "delivery_stage", "execution_mode",
    "shot_count", "total_duration_seconds", "source_authorities", "input_file_evidence",
    "skip_record", "timing_animatic_v1", "control_previs_v2_units",
    "motion_physics_tracks", "generation_modes_used", "forbidden_generation_modes",
    "downstream_invalidations",
}
V1_FIELDS = ENVELOPE_FIELDS | {
    "phase", "provider_neutral", "uses_keyframes", "model_input_role", "is_model_input",
    "final_edit_asset", "silent", "render_style", "file_path", "file_sha256",
    "actual_duration_seconds", "media_probe", "timeline", "control_dimensions",
    "forbidden_dimensions",
}
V2_FIELDS = ENVELOPE_FIELDS | {
    "phase", "generation_unit_id", "shot_uids", "target_duration_seconds",
    "provider_max_duration_seconds", "multimodal_reference_video_supported", "local_timeline",
    "file_path", "file_sha256", "actual_duration_seconds", "media_probe", "model_input_role",
    "is_model_input", "final_edit_asset", "silent", "render_style", "identity_authority",
    "look_authority", "control_dimensions", "forbidden_dimensions", "motion_track_ids",
}
SKIP_FIELDS = ENVELOPE_FIELDS | {"reason", "previs_needed", "complexity_flags"}
MOTION_FIELDS = ENVELOPE_FIELDS | {
    "track_id", "motion_class", "shot_uids", "generation_unit_ids", "source_basis",
    "confidence", "assumptions", "required_for_generation", "absolute_anchors",
    "local_anchors", "start_state", "end_state", "parameters",
}
TIMELINE_FIELDS = {
    "shot_uid", "display_order", "start_seconds", "end_seconds", "duration_seconds",
    "cut_motivation", "rough_camera_path", "rough_blocking", "motion_anchors",
}
MEDIA_PROBE_FIELDS = {
    "probe_contract_version", "container_format", "media_type", "video_codec", "duration_seconds", "width_pixels",
    "height_pixels", "frame_rate", "decoded_video_frame_count", "decoded_video_packet_count",
    "video_stream_count", "audio_stream_count", "shot_chapters",
}
CHAPTER_FIELDS = {"shot_uid", "start_seconds", "end_seconds"}
AUTHORITY_FIELDS = {
    "artifact_id", "owner_skill", "version", "sha256", "approval_status",
    "snapshot_path", "snapshot_file_sha256",
}
INPUT_EVIDENCE_FIELDS = {
    "input_id", "source_artifact_id", "role", "shot_uids", "copied_file_path",
    "file_sha256", "upstream_declared_path", "upstream_declared_file_sha256",
}
INPUT_ROLES = {
    "storyboard_frame", "storyboard_generation_prompt", "keyframe_image",
    "keyframe_generation_prompt", "provider_schema_snapshot",
}
PROVIDER_PROFILE_FIELDS = {
    "profile_type", "profile_id", "provider", "model_family", "model_id", "surface",
    "documented_backend_profile_id", "generation_mode", "surface_status",
    "supported_modalities", "effective_limits", "input_constraints",
    "capability_claims", "evidence",
}
PROVIDER_LIMIT_FIELDS = {
    "max_duration_seconds", "max_image_inputs", "max_video_inputs", "max_audio_inputs",
    "max_total_multimodal_inputs",
}
PROVIDER_EVIDENCE_FIELDS = {
    "evidence_tier", "retrieved_at", "locator", "supports", "snapshot_path",
    "snapshot_file_sha256",
}
PROVIDER_RUNTIME_SNAPSHOT_FIELDS = {
    "schema_version", "profile_id", "provider", "model_family", "model_id", "surface",
    "documented_backend_profile_id", "generation_mode", "surface_status",
    "supported_modalities", "effective_limits", "video_input_constraints",
}
PROVIDER_INPUT_CONSTRAINT_FIELDS = {"image", "video", "audio"}
PROVIDER_VIDEO_CONSTRAINT_FIELDS = {
    "accepted_media_types", "accepted_containers", "accepted_video_codecs",
    "max_file_bytes", "min_duration_seconds", "max_duration_seconds",
    "min_width_px", "max_width_px", "min_height_px", "max_height_px",
    "min_aspect_ratio", "max_aspect_ratio", "min_fps", "max_fps",
    "audio_track_policy",
}
DOWNSTREAM_INVALIDATION_FIELDS = {
    "artifact_id", "owner_skill", "version", "sha256", "reason", "affected_shot_uids",
}
SOURCE_CANON_SLOTS = {
    "shot_contract": "professional_shot_contract",
    "storyboard": "storyboard_manifest",
    "keyframe_pack": "keyframe_continuity_manifest",
    "keyframe_boundary_supplement": "keyframe_boundary_supplement",
    "provider_preflight": "generation_unit_preflight_plan",
    "provider_capability": "provider_capability",
}
SOURCE_CONTRACTS = {
    "shot_contract": ("ai-video-shot-script-director", "ai-video-shot-contract.v1"),
    "storyboard": ("ai-video-modular-storyboard", "ai-video-modular-storyboard.v1"),
    "keyframe_pack": ("ai-video-keyframe-continuity-pack", "ai-video-keyframe-continuity-pack.v1"),
    "keyframe_boundary_supplement": ("ai-video-keyframe-continuity-pack", "ai-video-keyframe-boundary-supplement.v1"),
    "provider_preflight": ("ai-video-omni-reference-prompt-director", "ai-video-generation-unit-preflight.v1"),
    "provider_capability": ("ai-video-omni-reference-prompt-director", "ai-video-capability-profile.v1"),
}


def canonical_artifact_hash(value: dict[str, Any]) -> str:
    payload = copy.deepcopy(value)
    payload.pop("sha256", None)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def is_semver(value: Any) -> bool:
    return isinstance(value, str) and SEMVER_RE.fullmatch(value) is not None


def semver_tuple(value: Any) -> tuple[int, int, int] | None:
    if not is_semver(value):
        return None
    return tuple(int(part) for part in value.split("."))


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def close(a: Any, b: Any, tolerance: float = TIME_TOLERANCE) -> bool:
    return is_number(a) and is_number(b) and abs(float(a) - float(b)) <= tolerance


def safe_file(root: Path, rel: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(rel, str) or not rel:
        errors.append(f"{label}: missing file_path")
        return None
    if "\\" in rel or rel.startswith("/") or (len(rel) > 1 and rel[0].isalpha() and rel[1] == ":"):
        errors.append(f"{label}: file_path must use portable POSIX package-relative syntax")
        return None
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{label}: file_path escapes package root")
        return None
    if not candidate.is_file():
        errors.append(f"{label}: file missing: {rel}")
        return None
    return candidate


def require_exact_fields(value: Any, expected: set[str], label: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label}: must be object")
        return
    missing = sorted(expected - set(value))
    extra = sorted(set(value) - expected)
    if missing:
        errors.append(f"{label}: missing fields {missing}")
    if extra:
        errors.append(f"{label}: extra fields forbidden {extra}")


def validate_provider_video_constraints(
    value: Any, label: str, errors: list[str]
) -> dict[str, Any] | None:
    require_exact_fields(value, PROVIDER_VIDEO_CONSTRAINT_FIELDS, label, errors)
    if not isinstance(value, dict):
        return None
    for field in ("accepted_media_types", "accepted_containers", "accepted_video_codecs"):
        items = value.get(field)
        if (
            not isinstance(items, list)
            or not items
            or len(items) != len(set(items))
            or not all(isinstance(item, str) and item.strip() for item in items)
        ):
            errors.append(f"{label}.{field} must be non-empty unique strings")
    integer_fields = (
        "max_file_bytes", "min_width_px", "max_width_px", "min_height_px", "max_height_px",
    )
    for field in integer_fields:
        item = value.get(field)
        if not isinstance(item, int) or isinstance(item, bool) or item < 1:
            errors.append(f"{label}.{field} must be a positive integer")
    number_fields = (
        "min_duration_seconds", "max_duration_seconds", "min_aspect_ratio",
        "max_aspect_ratio", "min_fps", "max_fps",
    )
    for field in number_fields:
        if not is_number(value.get(field)) or float(value[field]) <= 0:
            errors.append(f"{label}.{field} must be a positive finite number")
    for lower, upper in (
        ("min_duration_seconds", "max_duration_seconds"),
        ("min_width_px", "max_width_px"),
        ("min_height_px", "max_height_px"),
        ("min_aspect_ratio", "max_aspect_ratio"),
        ("min_fps", "max_fps"),
    ):
        if is_number(value.get(lower)) and is_number(value.get(upper)) and float(value[lower]) > float(value[upper]):
            errors.append(f"{label}.{lower} must not exceed {upper}")
    if value.get("audio_track_policy") not in {"forbidden", "optional", "required"}:
        errors.append(f"{label}.audio_track_policy is invalid")
    return value


def validate_live_provider_video_constraints(
    path: Path,
    live_probe: dict[str, Any],
    constraints: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    """Prove the real V2 control-video bytes satisfy the selected provider input gate."""
    media_types = constraints.get("accepted_media_types", [])
    if live_probe.get("media_type") not in media_types:
        errors.append(f"{label}: live media type is outside provider video input constraints")
    accepted_containers = {
        item.lower() for item in constraints.get("accepted_containers", []) if isinstance(item, str)
    }
    format_name = live_probe.get("container_format")
    format_tokens = set(format_name.lower().split(",")) if isinstance(format_name, str) else set()
    if not accepted_containers.intersection(format_tokens | ({format_name.lower()} if isinstance(format_name, str) else set())):
        errors.append(f"{label}: live container is outside provider video input constraints")
    codecs = constraints.get("accepted_video_codecs", [])
    if live_probe.get("video_codec") not in codecs:
        errors.append(f"{label}: live video codec is outside provider video input constraints")
    max_bytes = constraints.get("max_file_bytes")
    if isinstance(max_bytes, int) and not isinstance(max_bytes, bool) and path.stat().st_size > max_bytes:
        errors.append(f"{label}: live file bytes exceed provider video input constraints")
    duration = live_probe.get("duration_seconds")
    if is_number(duration):
        minimum, maximum = constraints.get("min_duration_seconds"), constraints.get("max_duration_seconds")
        if is_number(minimum) and float(duration) + MEDIA_DURATION_TOLERANCE < float(minimum):
            errors.append(f"{label}: live duration is below provider video input constraints")
        if is_number(maximum) and float(duration) - MEDIA_DURATION_TOLERANCE > float(maximum):
            errors.append(f"{label}: live duration exceeds provider video input constraints")
    width, height = live_probe.get("width_pixels"), live_probe.get("height_pixels")
    if isinstance(width, int) and isinstance(height, int) and height > 0:
        for value, lower, upper, dimension in (
            (width, "min_width_px", "max_width_px", "width"),
            (height, "min_height_px", "max_height_px", "height"),
        ):
            if isinstance(constraints.get(lower), int) and value < constraints[lower]:
                errors.append(f"{label}: live {dimension} is below provider video input constraints")
            if isinstance(constraints.get(upper), int) and value > constraints[upper]:
                errors.append(f"{label}: live {dimension} exceeds provider video input constraints")
        aspect = width / height
        if is_number(constraints.get("min_aspect_ratio")) and aspect < float(constraints["min_aspect_ratio"]):
            errors.append(f"{label}: live aspect ratio is below provider video input constraints")
        if is_number(constraints.get("max_aspect_ratio")) and aspect > float(constraints["max_aspect_ratio"]):
            errors.append(f"{label}: live aspect ratio exceeds provider video input constraints")
    try:
        fps = float(Fraction(str(live_probe.get("frame_rate"))))
    except (ValueError, ZeroDivisionError):
        fps = None
    if fps is None:
        errors.append(f"{label}: live frame rate cannot be evaluated against provider constraints")
    else:
        if is_number(constraints.get("min_fps")) and fps < float(constraints["min_fps"]):
            errors.append(f"{label}: live frame rate is below provider video input constraints")
        if is_number(constraints.get("max_fps")) and fps > float(constraints["max_fps"]):
            errors.append(f"{label}: live frame rate exceeds provider video input constraints")
    audio_count = live_probe.get("audio_stream_count")
    policy = constraints.get("audio_track_policy")
    if policy == "forbidden" and audio_count != 0:
        errors.append(f"{label}: provider video input constraints forbid audio tracks")
    if policy == "required" and (not isinstance(audio_count, int) or audio_count < 1):
        errors.append(f"{label}: provider video input constraints require an audio track")


def validate_dependency(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label}: dependency must be object")
        return
    if set(value) != {"artifact_id", "owner_skill", "version", "sha256"}:
        errors.append(f"{label}: dependency must contain exactly artifact_id/owner_skill/version/sha256")
    if not isinstance(value.get("artifact_id"), str) or not value["artifact_id"]:
        errors.append(f"{label}: artifact_id missing")
    if not isinstance(value.get("owner_skill"), str) or not value["owner_skill"]:
        errors.append(f"{label}: owner_skill missing")
    if not is_semver(value.get("version")):
        errors.append(f"{label}: version must be SemVer")
    if not is_sha(value.get("sha256")):
        errors.append(f"{label}: sha256 invalid")


def validate_envelope(
    value: Any,
    label: str,
    errors: list[str],
    exact_fields: set[str] | None = None,
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label}: artifact must be object")
        return
    required = ENVELOPE_FIELDS
    missing = sorted(required - value.keys())
    if missing:
        errors.append(f"{label}: missing envelope fields {missing}")
        return
    if exact_fields is not None:
        require_exact_fields(value, exact_fields, label, errors)
    if value["contract_version"] != CONTRACT_VERSION:
        errors.append(f"{label}: contract_version must be {CONTRACT_VERSION}")
    if value["owner_skill"] != OWNER:
        errors.append(f"{label}: owner_skill must be {OWNER}")
    if not isinstance(value["artifact_id"], str) or not value["artifact_id"]:
        errors.append(f"{label}: artifact_id missing")
    if not is_semver(value["version"]):
        errors.append(f"{label}: version must be SemVer")
    status = value["approval_status"]
    if status not in ENVELOPE_STATUSES:
        errors.append(f"{label}: invalid approval_status")
    dependencies = value["dependencies"]
    if not isinstance(dependencies, list):
        errors.append(f"{label}: dependencies must be list")
    else:
        for index, dependency in enumerate(dependencies):
            validate_dependency(dependency, f"{label}.dependencies[{index}]", errors)
    scope = value["affected_shot_uids"]
    if not isinstance(scope, list) or not all(isinstance(uid, str) and uid for uid in scope) or len(scope) != len(set(scope)):
        errors.append(f"{label}: affected_shot_uids must be unique string list")
    if status == "stale" and (not isinstance(value["stale_reason"], str) or not value["stale_reason"].strip()):
        errors.append(f"{label}: stale artifact requires non-empty stale_reason")
    if status != "stale" and value["stale_reason"] is not None:
        errors.append(f"{label}: non-stale artifact must have stale_reason null")
    if status in HASH_STATUSES:
        try:
            expected = canonical_artifact_hash(value)
        except (TypeError, ValueError) as exc:
            errors.append(f"{label}: non-canonical JSON value: {exc}")
        else:
            if value["sha256"] != expected:
                errors.append(f"{label}: canonical artifact sha256 mismatch")
    elif value["sha256"] is not None:
        errors.append(f"{label}: draft sha256 must be null")


def validate_authority(
    root: Path,
    value: Any,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{label}: authority must be object")
        return None
    require_exact_fields(value, AUTHORITY_FIELDS, label, errors)
    for field in ("artifact_id", "owner_skill"):
        if not isinstance(value.get(field), str) or not value[field]:
            errors.append(f"{label}: {field} missing")
    if not is_semver(value.get("version")):
        errors.append(f"{label}: version must be SemVer")
    if not is_sha(value.get("sha256")):
        errors.append(f"{label}: sha256 invalid")
    if value.get("approval_status") not in READY_STATUSES:
        errors.append(f"{label}: authority must be assistant_validated or user_approved")
    snapshot_path = safe_file(root, value.get("snapshot_path"), f"{label}.snapshot", errors)
    if snapshot_path is None:
        return None
    if sha256_file(snapshot_path) != value.get("snapshot_file_sha256"):
        errors.append(f"{label}: snapshot_file_sha256 mismatch")
        return None
    try:
        snapshot = json.loads(
            snapshot_path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"{label}: authority snapshot unreadable: {exc}")
        return None
    if not isinstance(snapshot, dict):
        errors.append(f"{label}: authority snapshot root must be object")
        return None
    for field in ("artifact_id", "owner_skill", "version", "sha256", "approval_status"):
        if snapshot.get(field) != value.get(field):
            errors.append(f"{label}: authority snapshot {field} mismatch")
    try:
        expected_hash = canonical_artifact_hash(snapshot)
    except (TypeError, ValueError) as exc:
        errors.append(f"{label}: authority snapshot is not canonical JSON: {exc}")
    else:
        if snapshot.get("sha256") != expected_hash:
            errors.append(f"{label}: authority snapshot canonical artifact sha256 mismatch")
    return snapshot


def load_canon_artifact(
    project_root: Path | None,
    entry: dict[str, Any],
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    """Load one active Project Canon artifact from its hash-bound real locator."""

    if project_root is None:
        errors.append(f"{label}: project root is required to verify Canon locator bytes")
        return None
    locator = entry.get("artifact_record_locator")
    file_hash = entry.get("artifact_record_file_sha256")
    if not isinstance(locator, str) or not locator or not is_sha(file_hash):
        errors.append(f"{label}: active Canon entry requires artifact_record_locator and artifact_record_file_sha256")
        return None
    candidate = (project_root / locator).resolve()
    try:
        candidate.relative_to(project_root.resolve())
    except ValueError:
        errors.append(f"{label}: Canon locator escapes project root")
        return None
    if not candidate.is_file():
        errors.append(f"{label}: Canon artifact record missing: {locator}")
        return None
    if sha256_file(candidate) != file_hash:
        errors.append(f"{label}: Canon artifact record byte hash mismatch")
        return None
    try:
        value = json.loads(
            candidate.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"{label}: Canon artifact JSON unreadable: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label}: Canon artifact root must be an object")
        return None
    return value


def bind_artifact_to_active_canon(
    artifact: dict[str, Any],
    active_by_id: dict[str, dict[str, Any]],
    project_root: Path | None,
    label: str,
    errors: list[str],
    expected_slot: str | None = None,
) -> dict[str, Any] | None:
    """Prove an artifact is the exact active, eligible, real-file Canon authority."""

    artifact_id = artifact.get("artifact_id")
    entry = active_by_id.get(artifact_id) if isinstance(artifact_id, str) else None
    if not isinstance(entry, dict):
        errors.append(f"{label}: artifact is not active in Project Canon")
        return None
    if expected_slot is not None and entry.get("artifact_slot") != expected_slot:
        errors.append(f"{label}: Canon artifact_slot must be {expected_slot}")
    for field in ("artifact_id", "owner_skill", "version", "sha256", "approval_status", "stale_reason", "affected_shot_uids"):
        if entry.get(field) != artifact.get(field):
            errors.append(f"{label}: Canon {field} differs from artifact")
    if entry.get("eligible_for_downstream") is not True:
        errors.append(f"{label}: active Canon entry is not downstream-eligible")
    if entry.get("approval_status") not in READY_STATUSES or entry.get("stale_reason") is not None:
        errors.append(f"{label}: active Canon entry is not approved and current")
    if entry.get("dependencies") != artifact.get("dependencies"):
        errors.append(f"{label}: Canon dependency locks differ from artifact")
    loaded = load_canon_artifact(project_root, entry, label, errors)
    if loaded is not None and loaded != artifact:
        errors.append(f"{label}: Canon locator JSON differs from the bound artifact")
        return None
    return loaded


def require_canon_primary(
    entry: dict[str, Any],
    expected_path: Path,
    expected_hash: Any,
    project_root: Path | None,
    label: str,
    errors: list[str],
) -> None:
    if project_root is None:
        return
    try:
        expected_locator = expected_path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        errors.append(f"{label}: expected primary file escapes project root")
        return
    if entry.get("locator") != expected_locator:
        errors.append(f"{label}: Canon primary locator differs from artifact primary file")
    if entry.get("file_sha256") != expected_hash:
        errors.append(f"{label}: Canon primary file_sha256 differs from artifact")


def require_owned_record_locator(
    entry: dict[str, Any],
    package_root: Path,
    project_root: Path | None,
    artifact_id: Any,
    label: str,
    errors: list[str],
) -> None:
    if project_root is None or not isinstance(artifact_id, str):
        return
    expected = package_root / f"00_manifest/owned_artifacts/{artifact_id}.json"
    try:
        expected_locator = expected.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        errors.append(f"{label}: owned artifact record escapes project root")
        return
    if entry.get("artifact_record_locator") != expected_locator:
        errors.append(f"{label}: Canon artifact_record_locator must point to the package owned_artifacts sidecar")
    if expected.is_file() and entry.get("artifact_record_file_sha256") != sha256_file(expected):
        errors.append(f"{label}: Canon artifact_record_file_sha256 differs from owned sidecar")


def validate_project_canon_binding(
    package_root: Path,
    data: dict[str, Any],
    snapshots: dict[str, dict[str, Any] | None],
    canon_manifest: dict[str, Any] | None,
    project_root: Path | None,
    errors: list[str],
) -> None:
    if canon_manifest is None:
        return
    canon_errors = validate_project_canon(canon_manifest)
    errors.extend(f"Project Canon invalid: {item}" for item in canon_errors)
    if canon_errors:
        return
    if project_root is not None:
        errors.extend(
            f"Project Canon files invalid: {item}"
            for item in verify_project_canon_files(canon_manifest, project_root)
        )
    if canon_manifest.get("project_id") != data.get("project_id"):
        errors.append("Project Canon project_id differs from previs package")
    if canon_manifest.get("canonical_shot_uids") != data.get("affected_shot_uids"):
        errors.append("Project Canon canonical_shot_uids differ from previs package")
    expected_phase = {
        "timing_animatic_v1": "timing_animatic_v1",
        "control_previs_v2": "control_previs_v2",
    }.get(data.get("delivery_stage"))
    if expected_phase is not None and canon_manifest.get("current_phase") != expected_phase:
        errors.append(f"Project Canon current_phase must be {expected_phase}")
    if data.get("delivery_stage") == "skipped_simple_single_shot" and canon_manifest.get("current_phase") not in {"storyboard_final", "timing_animatic_v1"}:
        errors.append("skipped Previs Canon phase must remain storyboard_final or timing_animatic_v1")
    active = canon_manifest.get("active_artifacts")
    active_by_id = {
        item.get("artifact_id"): item
        for item in active
        if isinstance(item, dict) and isinstance(item.get("artifact_id"), str)
    } if isinstance(active, list) else {}

    for name, snapshot in snapshots.items():
        if isinstance(snapshot, dict):
            bind_artifact_to_active_canon(
                snapshot, active_by_id, project_root, f"source_authorities.{name}", errors,
                SOURCE_CANON_SLOTS.get(name),
            )

    owned: list[dict[str, Any]] = [data]
    for key in ("skip_record", "timing_animatic_v1"):
        value = data.get(key)
        if isinstance(value, dict):
            owned.append(value)
    for key in ("control_previs_v2_units", "motion_physics_tracks"):
        owned.extend(item for item in data.get(key, []) if isinstance(item, dict))
    for artifact in owned:
        if artifact is data:
            expected_slot = "previs_manifest"
        elif artifact.get("phase") == "timing_animatic_v1":
            expected_slot = "timing_animatic_v1"
        elif artifact.get("phase") == "control_previs_v2":
            expected_slot = f"control_previs_v2:{artifact.get('generation_unit_id')}"
        elif artifact.get("track_id") is not None:
            expected_slot = f"motion_track:{artifact.get('track_id')}"
        elif artifact.get("reason") == "static_or_near_static_single_shot":
            expected_slot = "previs_skip"
        else:
            expected_slot = None
        bind_artifact_to_active_canon(
            artifact, active_by_id, project_root,
            f"owned_artifact[{artifact.get('artifact_id')}]", errors, expected_slot,
        )
        entry = active_by_id.get(artifact.get("artifact_id"))
        if not isinstance(entry, dict):
            continue
        label = f"owned_artifact[{artifact.get('artifact_id')}]"
        require_owned_record_locator(
            entry, package_root, project_root, artifact.get("artifact_id"), label, errors,
        )
        if artifact is data:
            primary_path = package_root / "00_manifest/PREVIS_MANIFEST.json"
            primary_hash = sha256_file(primary_path) if primary_path.is_file() else None
        elif artifact.get("phase") in {"timing_animatic_v1", "control_previs_v2"}:
            primary_path = package_root / str(artifact.get("file_path"))
            primary_hash = artifact.get("file_sha256")
        elif artifact.get("track_id") is not None:
            primary_path = package_root / f"03_motion/tracks/{artifact.get('track_id')}.json"
            primary_hash = sha256_file(primary_path) if primary_path.is_file() else None
            if primary_path.is_file():
                try:
                    primary_record = json.loads(
                        primary_path.read_text(encoding="utf-8"),
                        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
                    )
                except (OSError, json.JSONDecodeError, ValueError) as exc:
                    errors.append(f"{label}: motion-track primary JSON unreadable: {exc}")
                else:
                    if primary_record != artifact:
                        errors.append(f"{label}: motion-track primary JSON differs from artifact record")
        else:
            primary_path = package_root / f"00_manifest/owned_artifacts/{artifact.get('artifact_id')}.json"
            primary_hash = sha256_file(primary_path) if primary_path.is_file() else None
        require_canon_primary(entry, primary_path, primary_hash, project_root, label, errors)

    if data.get("delivery_stage") == "control_previs_v2":
        superseded = canon_manifest.get("superseded_artifacts")
        predecessors = [
            item for item in superseded if isinstance(item, dict)
            and item.get("artifact_slot") == "previs_manifest"
            and item.get("owner_skill") == OWNER
            and item.get("superseded_by_artifact_id") == data.get("artifact_id")
        ] if isinstance(superseded, list) else []
        if len(predecessors) != 1:
            errors.append("V2 Canon must contain exactly one superseded V1 previs_manifest predecessor")
        else:
            predecessor = predecessors[0]
            old_version = semver_tuple(predecessor.get("version"))
            new_version = semver_tuple(data.get("version"))
            if old_version is None or new_version is None or old_version >= new_version:
                errors.append("V2 previs_manifest version must exceed superseded V1 version")
            previous = load_canon_artifact(project_root, predecessor, "superseded V1 previs_manifest", errors)
            if previous is not None:
                if previous.get("artifact_id") != predecessor.get("artifact_id") or previous.get("sha256") != predecessor.get("sha256"):
                    errors.append("superseded V1 locator artifact lock mismatch")
                if previous.get("delivery_stage") != "timing_animatic_v1" or previous.get("control_previs_v2_units") != []:
                    errors.append("superseded previs_manifest must be the V1-only package state")


def authority_dependency(authority: dict[str, Any]) -> dict[str, Any]:
    return {field: authority.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256")}


def dependency_signature(value: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    return tuple(value.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))


def require_dependencies(artifact: dict[str, Any], required: list[dict[str, Any]], label: str, errors: list[str], exact: bool = False) -> None:
    actual_records = [dependency_signature(item) for item in artifact.get("dependencies", []) if isinstance(item, dict)]
    actual = set(actual_records)
    expected = {dependency_signature(item) for item in required}
    if len(actual_records) != len(actual):
        errors.append(f"{label}: duplicate dependency records forbidden")
    missing = expected - actual
    if missing:
        errors.append(f"{label}: missing required dependency records")
    if exact and (actual != expected or len(actual_records) != len(expected)):
        errors.append(f"{label}: dependency records must exactly equal required authorities")


def validate_control_dimensions(value: dict[str, Any], label: str, errors: list[str]) -> None:
    controls = value.get("control_dimensions")
    forbidden = value.get("forbidden_dimensions")
    if not isinstance(controls, list) or len(controls) != len(set(controls)):
        errors.append(f"{label}: control_dimensions must be unique list")
        return
    unknown = set(controls) - ALLOWED_CONTROLS
    if unknown:
        errors.append(f"{label}: forbidden ownership/control dimensions present: {sorted(unknown)}")
    if not {"shot_boundaries", "target_timing"} <= set(controls):
        errors.append(f"{label}: shot_boundaries and target_timing are required")
    if not isinstance(forbidden, list) or not FORBIDDEN_DIMENSIONS <= set(forbidden):
        errors.append(f"{label}: forbidden_dimensions must explicitly include all non-owned dimensions")


def validate_input_evidence(
    root: Path,
    values: Any,
    errors: list[str],
) -> tuple[list[dict[str, Any]], set[str]]:
    if not isinstance(values, list):
        errors.append("input_file_evidence must be a list")
        return [], set()
    ids: set[str] = set()
    valid: list[dict[str, Any]] = []
    for index, value in enumerate(values):
        label = f"input_file_evidence[{index}]"
        require_exact_fields(value, INPUT_EVIDENCE_FIELDS, label, errors)
        if not isinstance(value, dict):
            continue
        input_id = value.get("input_id")
        if not isinstance(input_id, str) or not input_id:
            errors.append(f"{label}: input_id missing")
        elif input_id in ids:
            errors.append(f"{label}: duplicate input_id")
        else:
            ids.add(input_id)
        if not isinstance(value.get("source_artifact_id"), str) or not value["source_artifact_id"]:
            errors.append(f"{label}: source_artifact_id missing")
        if value.get("role") not in INPUT_ROLES:
            errors.append(f"{label}: role invalid")
        scope = value.get("shot_uids")
        if not isinstance(scope, list) or not all(isinstance(uid, str) and uid for uid in scope) or len(scope) != len(set(scope)):
            errors.append(f"{label}: shot_uids must be a unique string list")
        for field in ("file_sha256", "upstream_declared_file_sha256"):
            if not is_sha(value.get(field)):
                errors.append(f"{label}: {field} invalid")
        if value.get("file_sha256") != value.get("upstream_declared_file_sha256"):
            errors.append(f"{label}: copied file hash differs from upstream declaration")
        if not isinstance(value.get("upstream_declared_path"), str) or not value["upstream_declared_path"]:
            errors.append(f"{label}: upstream_declared_path missing")
        path = safe_file(root, value.get("copied_file_path"), label, errors)
        if path is not None and sha256_file(path) != value.get("file_sha256"):
            errors.append(f"{label}: copied input file_sha256 mismatch")
        valid.append(value)
    return valid, set()


def consume_input_evidence(
    evidence: list[dict[str, Any]],
    consumed_ids: set[str],
    source_artifact_id: Any,
    role: str,
    shot_uids: list[str],
    declared_path: Any,
    declared_hash: Any,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    matches = [
        item for item in evidence
        if item.get("source_artifact_id") == source_artifact_id
        and item.get("role") == role
        and item.get("shot_uids") == shot_uids
        and item.get("upstream_declared_path") == declared_path
        and item.get("upstream_declared_file_sha256") == declared_hash
    ]
    if len(matches) != 1:
        errors.append(f"{label}: requires exactly one hash-bound copied input evidence record")
        return None
    consumed_ids.add(matches[0].get("input_id"))
    return matches[0]


def validate_shot_and_storyboard_sources(
    data: dict[str, Any],
    v1: dict[str, Any],
    shot_snapshot: dict[str, Any] | None,
    storyboard_snapshot: dict[str, Any] | None,
    evidence: list[dict[str, Any]],
    consumed_ids: set[str],
    complete_v2: bool,
    errors: list[str],
) -> None:
    if not isinstance(shot_snapshot, dict) or not isinstance(storyboard_snapshot, dict):
        return
    timeline = shot_snapshot.get("timeline")
    shots = shot_snapshot.get("shots")
    if not isinstance(timeline, dict) or not isinstance(shots, list):
        errors.append("Shot Contract snapshot lacks timeline/shots semantics")
        return
    v1_entries = v1.get("timeline") if isinstance(v1.get("timeline"), list) else []
    expected_uids = [entry.get("shot_uid") for entry in v1_entries if isinstance(entry, dict)]
    shot_uids = [shot.get("shot_uid") for shot in shots if isinstance(shot, dict)]
    if shot_uids != expected_uids:
        errors.append("V1 Shot UID order must exactly match Shot Contract snapshot")
    if timeline.get("shot_count") != data.get("shot_count"):
        errors.append("V1 shot_count must exactly match Shot Contract snapshot")
    if not close(timeline.get("total_duration_seconds"), data.get("total_duration_seconds")):
        errors.append("V1 total duration must exactly match Shot Contract snapshot")
    by_uid = {entry.get("shot_uid"): entry for entry in v1_entries if isinstance(entry, dict)}
    for index, shot in enumerate(shots):
        if not isinstance(shot, dict):
            errors.append(f"Shot Contract shots[{index}] malformed")
            continue
        uid = shot.get("shot_uid")
        entry = by_uid.get(uid)
        if entry is None:
            continue
        if shot.get("display_no") != entry.get("display_order"):
            errors.append(f"Shot Contract {uid}: display order differs from V1")
        if not close(shot.get("target_duration_seconds"), entry.get("duration_seconds")):
            errors.append(f"Shot Contract {uid}: duration differs from V1")

    stage = storyboard_snapshot.get("storyboard_stage")
    if stage not in {"structure_draft", "look_applied_final"}:
        errors.append("Storyboard snapshot stage is not eligible for V1")
    if complete_v2 and stage != "look_applied_final":
        errors.append("V2 requires look_applied_final Storyboard authority")
    frames = storyboard_snapshot.get("frames")
    if not isinstance(frames, list):
        errors.append("Storyboard snapshot frames missing")
        return
    frame_uids = [frame.get("shot_uid") for frame in frames if isinstance(frame, dict)]
    if frame_uids != expected_uids or storyboard_snapshot.get("script_shot_count") != len(expected_uids):
        errors.append("Storyboard frame order/count must exactly match V1 Shot UIDs")
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            errors.append(f"Storyboard frames[{index}] malformed")
            continue
        uid = frame.get("shot_uid")
        entry = by_uid.get(uid)
        if entry is not None:
            if frame.get("display_order") != entry.get("display_order"):
                errors.append(f"Storyboard {uid}: display order differs from V1")
            if not close(frame.get("target_duration_seconds"), entry.get("duration_seconds")):
                errors.append(f"Storyboard {uid}: duration differs from V1")
        expected_stage = "look_applied_final" if stage == "look_applied_final" else "structure_draft"
        if frame.get("stage") != expected_stage:
            errors.append(f"Storyboard {uid}: frame stage differs from manifest stage")
        if complete_v2 and frame.get("is_model_input_eligible") is not True:
            errors.append(f"Storyboard {uid}: V2 requires model-input-eligible final frame")
        if not complete_v2 and stage == "structure_draft" and frame.get("is_model_input_eligible") is not False:
            errors.append(f"Storyboard {uid}: structure frame must not be model-input eligible")
        consume_input_evidence(
            evidence, consumed_ids, storyboard_snapshot.get("artifact_id"), "storyboard_frame", [uid],
            frame.get("file_path"), frame.get("file_sha256"), f"Storyboard {uid} frame", errors,
        )
        prompt_path = frame.get("generation_prompt_path")
        prompt_hash = frame.get("generation_prompt_file_sha256")
        if not isinstance(prompt_path, str) or not prompt_path or not is_sha(prompt_hash):
            errors.append(f"Storyboard {uid}: generation prompt path/hash required")
        else:
            consume_input_evidence(
                evidence, consumed_ids, storyboard_snapshot.get("artifact_id"),
                "storyboard_generation_prompt", [uid], prompt_path, prompt_hash,
                f"Storyboard {uid} generation prompt", errors,
            )


def validate_v2_source_semantics(
    root: Path,
    v1: dict[str, Any],
    v1_uids: list[str],
    units: list[dict[str, Any]],
    keyframe_snapshot: dict[str, Any] | None,
    boundary_snapshot: dict[str, Any] | None,
    preflight_snapshot: dict[str, Any] | None,
    provider_snapshot: dict[str, Any] | None,
    authorities: dict[str, Any],
    evidence: list[dict[str, Any]],
    consumed_ids: set[str],
    errors: list[str],
) -> dict[str, Any] | None:
    if not all(isinstance(item, dict) for item in (keyframe_snapshot, boundary_snapshot, preflight_snapshot, provider_snapshot)):
        return None
    assert keyframe_snapshot is not None and boundary_snapshot is not None
    assert preflight_snapshot is not None and provider_snapshot is not None
    require_dependencies(
        preflight_snapshot,
        [
            authority_dependency(authorities["shot_contract"]),
            authority_dependency(authorities["storyboard"]),
            authority_dependency(authorities["keyframe_pack"]),
            authority_dependency(authorities["provider_capability"]),
            authority_dependency(v1),
        ],
        "Prompt preflight", errors,
    )
    require_dependencies(
        boundary_snapshot,
        [authority_dependency(authorities["keyframe_pack"]), authority_dependency(authorities["provider_preflight"])],
        "K2 Boundary Supplement", errors, exact=True,
    )
    if keyframe_snapshot.get("scripted_shot_uids") != v1_uids:
        errors.append("Keyframe snapshot Shot UIDs must exactly match V1")
    shot_records = keyframe_snapshot.get("shot_records")
    if not isinstance(shot_records, list):
        errors.append("Keyframe snapshot shot_records missing")
    else:
        record_uids = [item.get("shot_uid") for item in shot_records if isinstance(item, dict)]
        if record_uids != v1_uids:
            errors.append("Keyframe snapshot shot record order must exactly match V1")
        for index, record in enumerate(shot_records):
            if not isinstance(record, dict):
                errors.append(f"Keyframe shot_records[{index}] malformed")
                continue
            uid = record.get("shot_uid")
            keyframes = record.get("keyframes")
            if not isinstance(keyframes, list) or not keyframes:
                errors.append(f"Keyframe {uid}: at least one generation-ready keyframe required")
                continue
            for keyframe in keyframes:
                if not isinstance(keyframe, dict):
                    errors.append(f"Keyframe {uid}: record malformed")
                    continue
                consume_input_evidence(
                    evidence, consumed_ids, keyframe_snapshot.get("artifact_id"), "keyframe_image", [uid],
                    keyframe.get("file_path"), keyframe.get("file_sha256"), f"Keyframe {uid} image", errors,
                )
                consume_input_evidence(
                    evidence, consumed_ids, keyframe_snapshot.get("artifact_id"),
                    "keyframe_generation_prompt", [uid], keyframe.get("prompt_path"),
                    keyframe.get("prompt_file_sha256"), f"Keyframe {uid} generation prompt", errors,
                )

    expected_units = [
        {"generation_unit_id": unit.get("generation_unit_id"), "ordered_shot_uids": unit.get("shot_uids")}
        for unit in units
    ]
    if boundary_snapshot.get("scripted_shot_uids") != v1_uids or boundary_snapshot.get("generation_units") != expected_units:
        errors.append("K2 Boundary Supplement must exactly bind V2 Generation Unit Map")
    for key, authority_key in (("core_keyframe_manifest", "keyframe_pack"), ("prompt_preflight", "provider_preflight")):
        ref = boundary_snapshot.get(key)
        authority = authorities.get(authority_key)
        if not isinstance(ref, dict) or not isinstance(authority, dict):
            errors.append(f"K2 Boundary Supplement {key} reference missing")
        elif any(ref.get(field) != authority.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256")):
            errors.append(f"K2 Boundary Supplement {key} reference mismatch")

    if preflight_snapshot.get("plan_status") != "ready_for_boundary_supplement" or preflight_snapshot.get("generation_mode") != "omni_reference_to_video":
        errors.append("Prompt preflight is not ready for omni-reference V2")
    if preflight_snapshot.get("ordered_shot_uids") != v1_uids:
        errors.append("Prompt preflight Shot UIDs must exactly match V1")
    planned = preflight_snapshot.get("generation_units")
    if not isinstance(planned, list) or len(planned) != len(units):
        errors.append("Prompt preflight Generation Unit count differs from V2")
    else:
        for index, (plan, unit) in enumerate(zip(planned, units)):
            if not isinstance(plan, dict):
                errors.append(f"Prompt preflight unit {index} malformed")
                continue
            if plan.get("generation_unit_id") != unit.get("generation_unit_id") or plan.get("ordered_shot_uids") != unit.get("shot_uids"):
                errors.append(f"Prompt preflight unit {index} mapping differs from V2")
            if not close(plan.get("target_duration_seconds"), unit.get("target_duration_seconds")):
                errors.append(f"Prompt preflight unit {index} duration differs from V2")
            if plan.get("control_previs_requirement") != "required" or plan.get("preflight_status") != "ready":
                errors.append(f"Prompt preflight unit {index} does not authorize V2")

    provider_profile_id = preflight_snapshot.get("provider_profile_id")
    profiles = provider_snapshot.get("profiles")
    profile_ids = [item.get("profile_id") for item in profiles if isinstance(item, dict)] if isinstance(profiles, list) else []
    if not all(isinstance(item, str) and item for item in profile_ids):
        errors.append("Provider capability snapshot profile_id values must be non-empty strings")
    elif len(profile_ids) != len(set(profile_ids)):
        errors.append("Provider capability snapshot contains duplicate profile_id values")
    profile = next((item for item in profiles if isinstance(item, dict) and item.get("profile_id") == provider_profile_id), None) if isinstance(profiles, list) else None
    if not isinstance(profile, dict):
        errors.append("Provider capability snapshot lacks the preflight-selected runtime profile")
        return None
    require_exact_fields(profile, PROVIDER_PROFILE_FIELDS, "provider runtime profile", errors)
    if profile.get("profile_type") != "provider_runtime" or profile.get("surface_status") != "provider_schema_verified" or profile.get("generation_mode") != "omni_reference_to_video":
        errors.append("Provider runtime profile is not schema-verified omni-reference")
    if not isinstance(profile.get("capability_claims"), list):
        errors.append("Provider runtime profile capability_claims must be a list")
    if "video" not in profile.get("supported_modalities", []):
        errors.append("Provider runtime profile lacks reference-video modality")
    input_constraints = profile.get("input_constraints")
    require_exact_fields(
        input_constraints, PROVIDER_INPUT_CONSTRAINT_FIELDS,
        "provider runtime profile.input_constraints", errors,
    )
    video_constraints = (
        input_constraints.get("video") if isinstance(input_constraints, dict) else None
    )
    video_constraints = validate_provider_video_constraints(
        video_constraints, "provider runtime profile.input_constraints.video", errors,
    )
    limits = profile.get("effective_limits")
    require_exact_fields(limits, PROVIDER_LIMIT_FIELDS, "provider runtime profile.effective_limits", errors)
    max_duration = limits.get("max_duration_seconds") if isinstance(limits, dict) else None
    if not is_number(max_duration) or float(max_duration) <= 0:
        errors.append("Provider runtime profile has no verified max duration")
    else:
        for unit in units:
            if not close(unit.get("provider_max_duration_seconds"), max_duration):
                errors.append(f"V2 unit {unit.get('generation_unit_id')}: provider max differs from verified runtime profile")
    provider_artifact_id = provider_snapshot.get("artifact_id")
    modalities = profile.get("supported_modalities")
    if not isinstance(modalities, list) or len(modalities) != len(set(modalities)) or not all(isinstance(item, str) and item for item in modalities):
        errors.append("Provider runtime profile supported_modalities must be unique strings")
    if isinstance(limits, dict):
        for field in PROVIDER_LIMIT_FIELDS - {"max_duration_seconds"}:
            value = limits.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"Provider runtime profile {field} must be a non-negative integer")
        if not isinstance(limits.get("max_video_inputs"), int) or isinstance(limits.get("max_video_inputs"), bool) or limits.get("max_video_inputs", 0) < 1:
            errors.append("Provider runtime profile must prove at least one video input")
        if not isinstance(limits.get("max_total_multimodal_inputs"), int) or isinstance(limits.get("max_total_multimodal_inputs"), bool) or limits.get("max_total_multimodal_inputs", 0) < 1:
            errors.append("Provider runtime profile must prove a positive multimodal-input limit")
    all_evidence = profile.get("evidence")
    if not isinstance(all_evidence, list):
        errors.append("Provider runtime profile evidence must be a list")
        all_evidence = []
    for index, item in enumerate(all_evidence):
        require_exact_fields(item, PROVIDER_EVIDENCE_FIELDS, f"provider runtime profile.evidence[{index}]", errors)
        if isinstance(item, dict):
            for field in ("retrieved_at", "locator", "supports", "snapshot_path"):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    errors.append(f"provider runtime profile.evidence[{index}]: {field} missing")
            if item.get("supports") != profile.get("profile_id"):
                errors.append(f"provider runtime profile.evidence[{index}]: supports must equal profile_id")
            if not is_sha(item.get("snapshot_file_sha256")):
                errors.append(f"provider runtime profile.evidence[{index}]: snapshot_file_sha256 invalid")
    runtime_evidence = [
        item for item in all_evidence if isinstance(item, dict)
        and item.get("evidence_tier") == "provider_schema_verified"
        and item.get("snapshot_path") is not None
        and item.get("snapshot_file_sha256") is not None
    ]
    if len(runtime_evidence) != 1:
        errors.append("Provider runtime profile requires exactly one hash-bound runtime schema evidence snapshot")
    for index, item in enumerate(runtime_evidence):
        record = consume_input_evidence(
            evidence, consumed_ids, provider_artifact_id, "provider_schema_snapshot", [],
            item.get("snapshot_path"), item.get("snapshot_file_sha256"),
            f"Provider schema evidence[{index}]", errors,
        )
        if record is None:
            continue
        copied_path = safe_file(root, record.get("copied_file_path"), f"Provider schema evidence[{index}]", errors)
        if copied_path is None:
            continue
        try:
            runtime_snapshot = json.loads(
                copied_path.read_text(encoding="utf-8"),
                parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
            )
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"Provider schema evidence[{index}]: local snapshot unreadable: {exc}")
            continue
        require_exact_fields(
            runtime_snapshot, PROVIDER_RUNTIME_SNAPSHOT_FIELDS,
            f"Provider schema evidence[{index}].snapshot", errors,
        )
        if not isinstance(runtime_snapshot, dict):
            continue
        if runtime_snapshot.get("schema_version") != "provider-runtime-capability-evidence.v1":
            errors.append(f"Provider schema evidence[{index}]: snapshot schema_version invalid")
        for field in (
            "profile_id", "provider", "model_family", "model_id", "surface",
            "documented_backend_profile_id", "generation_mode", "surface_status",
            "supported_modalities", "effective_limits",
        ):
            if runtime_snapshot.get(field) != profile.get(field):
                errors.append(f"Provider schema evidence[{index}]: snapshot {field} differs from runtime profile")
        if runtime_snapshot.get("video_input_constraints") != video_constraints:
            errors.append(
                f"Provider schema evidence[{index}]: snapshot video_input_constraints "
                "differs from runtime profile"
            )
        validate_provider_video_constraints(
            runtime_snapshot.get("video_input_constraints"),
            f"Provider schema evidence[{index}].snapshot.video_input_constraints",
            errors,
        )
        require_exact_fields(
            runtime_snapshot.get("effective_limits"), PROVIDER_LIMIT_FIELDS,
            f"Provider schema evidence[{index}].snapshot.effective_limits", errors,
        )
    return video_constraints


def validate_timeline(
    timeline: Any,
    expected_uids: list[str],
    expected_total: float,
    label: str,
    errors: list[str],
    global_entries: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    if not isinstance(timeline, list):
        errors.append(f"{label}: timeline must be list")
        return {}
    actual_uids = [entry.get("shot_uid") for entry in timeline if isinstance(entry, dict)]
    if actual_uids != expected_uids:
        errors.append(f"{label}: Shot UID order/coverage mismatch")
    cursor = 0.0
    result: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(timeline):
        item_label = f"{label}[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{item_label}: entry must be object")
            continue
        require_exact_fields(entry, TIMELINE_FIELDS, item_label, errors)
        uid = entry.get("shot_uid")
        start, end, duration = entry.get("start_seconds"), entry.get("end_seconds"), entry.get("duration_seconds")
        if not close(start, cursor):
            errors.append(f"{item_label}: timeline gap or overlap")
        if not is_number(end) or not is_number(start) or float(end) <= float(start):
            errors.append(f"{item_label}: end must exceed start")
        if not is_number(duration) or float(duration) <= 0 or not close(float(end) - float(start), duration):
            errors.append(f"{item_label}: duration inconsistent with boundaries")
        if global_entries is None:
            if entry.get("display_order") != index + 1:
                errors.append(f"{item_label}: global display_order mismatch")
        elif uid in global_entries:
            source = global_entries[uid]
            if entry.get("display_order") != source.get("display_order"):
                errors.append(f"{item_label}: display_order differs from V1")
            if not close(duration, source.get("duration_seconds")):
                errors.append(f"{item_label}: duration differs from V1")
        for field in ("cut_motivation", "rough_camera_path", "rough_blocking"):
            if not isinstance(entry.get(field), str) or not entry[field]:
                errors.append(f"{item_label}: {field} missing")
        anchors = entry.get("motion_anchors")
        if not isinstance(anchors, list):
            errors.append(f"{item_label}: motion_anchors must be list")
        else:
            for anchor_index, anchor in enumerate(anchors):
                anchor_label = f"{item_label}.motion_anchors[{anchor_index}]"
                require_exact_fields(anchor, {"time_seconds", "state"}, anchor_label, errors)
                if isinstance(anchor, dict):
                    if not is_number(anchor.get("time_seconds")):
                        errors.append(f"{anchor_label}: time_seconds invalid")
                    if not isinstance(anchor.get("state"), str) or not anchor["state"]:
                        errors.append(f"{anchor_label}: state missing")
        if is_number(end):
            cursor = float(end)
        if isinstance(uid, str):
            result[uid] = entry
    if not close(cursor, expected_total):
        errors.append(f"{label}: final end does not equal target duration")
    return result


def validate_media_artifact(
    root: Path,
    value: dict[str, Any],
    target_duration: float,
    timeline: list[dict[str, Any]],
    label: str,
    errors: list[str],
    ffprobe_binary: str,
    provider_video_constraints: dict[str, Any] | None = None,
) -> None:
    path = safe_file(root, value.get("file_path"), label, errors)
    if path is not None and sha256_file(path) != value.get("file_sha256"):
        errors.append(f"{label}: file_sha256 mismatch")
    actual_duration = value.get("actual_duration_seconds")
    if not close(actual_duration, target_duration, MEDIA_DURATION_TOLERANCE):
        errors.append(f"{label}: actual duration differs from target")
    stored_probe = value.get("media_probe")
    require_exact_fields(stored_probe, MEDIA_PROBE_FIELDS, f"{label}.media_probe", errors)
    if not isinstance(stored_probe, dict) or path is None:
        return
    chapters = stored_probe.get("shot_chapters")
    if not isinstance(chapters, list):
        errors.append(f"{label}.media_probe: shot_chapters must be list")
    else:
        for index, chapter in enumerate(chapters):
            require_exact_fields(chapter, CHAPTER_FIELDS, f"{label}.media_probe.shot_chapters[{index}]", errors)
    try:
        live_probe = probe_media(path, ffprobe_binary)
    except MediaProbeError as exc:
        errors.append(f"{label}: live media probe failed closed: {exc}")
        return
    for field in (
        "probe_contract_version", "container_format", "media_type", "video_codec", "width_pixels", "height_pixels", "frame_rate",
        "decoded_video_frame_count", "decoded_video_packet_count", "video_stream_count", "audio_stream_count",
    ):
        if stored_probe.get(field) != live_probe.get(field):
            errors.append(f"{label}: stored media probe {field} differs from live probe")
    if not close(stored_probe.get("duration_seconds"), live_probe.get("duration_seconds"), 0.000001):
        errors.append(f"{label}: stored media probe duration differs from live probe")
    if not close(actual_duration, live_probe.get("duration_seconds"), MEDIA_DURATION_TOLERANCE):
        errors.append(f"{label}: actual_duration_seconds differs from live media")
    if live_probe.get("audio_stream_count") != 0:
        errors.append(f"{label}: silent control media must have zero audio streams")
    if provider_video_constraints is not None:
        validate_live_provider_video_constraints(
            path, live_probe, provider_video_constraints, label, errors,
        )
    live_chapters = live_probe.get("shot_chapters")
    if stored_probe.get("shot_chapters") != live_chapters:
        errors.append(f"{label}: stored shot chapters differ from live media")
    expected_chapters = [
        {
            "shot_uid": entry.get("shot_uid"),
            "start_seconds": round(float(entry.get("start_seconds")), 6),
            "end_seconds": round(float(entry.get("end_seconds")), 6),
        }
        for entry in timeline
        if isinstance(entry, dict) and is_number(entry.get("start_seconds")) and is_number(entry.get("end_seconds"))
    ]
    if live_chapters != expected_chapters:
        errors.append(f"{label}: live media shot chapters do not exactly encode manifest boundaries")


def owned_artifact_ids(data: dict[str, Any]) -> set[str]:
    expected = {data.get("artifact_id")}
    for key in ("skip_record", "timing_animatic_v1"):
        value = data.get(key)
        if isinstance(value, dict):
            expected.add(value.get("artifact_id"))
    for key in ("control_previs_v2_units", "motion_physics_tracks"):
        for value in data.get(key, []) if isinstance(data.get(key), list) else []:
            if isinstance(value, dict):
                expected.add(value.get("artifact_id"))
    return {item for item in expected if isinstance(item, str) and item}


def validate_manifest_receipt(
    root: Path,
    data: dict[str, Any],
    canon_manifest: dict[str, Any] | None,
    errors: list[str],
) -> None:
    path = root / "00_manifest/MANIFEST_UPDATE_RECEIPT.json"
    if not path.is_file():
        if canon_manifest is not None:
            errors.append("optional Project Canon integration requires 00_manifest/MANIFEST_UPDATE_RECEIPT.json")
        return
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"manifest update receipt unreadable: {exc}")
        return
    errors.extend(
        f"manifest update receipt: {item}"
        for item in validate_receipt(receipt, OWNER, owned_artifact_ids(data), canon_manifest)
    )


def validate_active_reports(root: Path, data: dict[str, Any], v1: dict[str, Any], errors: list[str]) -> None:
    required = [
        root / "01_timing_animatic_v1/timing_map.json",
        root / "04_qa/timeline_validation.json",
        root / "04_qa/control_boundary_report.md",
    ]
    if data.get("delivery_stage") == "control_previs_v2":
        required.extend([
            root / "03_motion/camera_trajectory_map.json",
            root / "03_motion/blocking_map.json",
            root / "03_motion/motion_physics_tracks.json",
        ])
    for path in required:
        if not path.is_file():
            errors.append(f"missing required output: {path.relative_to(root)}")
    timing_path = root / "01_timing_animatic_v1/timing_map.json"
    if timing_path.is_file():
        try:
            timing_map = json.loads(timing_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"timing map unreadable: {exc}")
        else:
            require_exact_fields(timing_map, {"source_artifact_id", "timeline"}, "timing map", errors)
            if timing_map.get("source_artifact_id") != v1.get("artifact_id") or timing_map.get("timeline") != v1.get("timeline"):
                errors.append("timing map must exactly project V1 timeline")
    timeline_report_path = root / "04_qa/timeline_validation.json"
    if timeline_report_path.is_file():
        try:
            report = json.loads(timeline_report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"timeline validation report unreadable: {exc}")
        else:
            require_exact_fields(report, {"status", "validated_manifest_sha256"}, "timeline validation report", errors)
            if report.get("status") != "passed" or report.get("validated_manifest_sha256") != data.get("sha256"):
                errors.append("timeline validation report must lock current manifest hash")
    boundary_path = root / "04_qa/control_boundary_report.md"
    if boundary_path.is_file() and not boundary_path.read_text(encoding="utf-8", errors="ignore").strip():
        errors.append("control boundary report must not be empty")
    if data.get("delivery_stage") == "control_previs_v2":
        projections = (
            (root / "03_motion/camera_trajectory_map.json", [item for item in data.get("motion_physics_tracks", []) if isinstance(item, dict) and item.get("motion_class") == "camera"], "camera trajectory projection"),
            (root / "03_motion/blocking_map.json", [item for item in data.get("motion_physics_tracks", []) if isinstance(item, dict) and item.get("motion_class") == "subject_blocking"], "blocking projection"),
            (root / "03_motion/motion_physics_tracks.json", data.get("motion_physics_tracks"), "motion physics projection"),
        )
        for projection_path, expected_tracks, projection_label in projections:
            if not projection_path.is_file():
                continue
            try:
                projection = json.loads(projection_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{projection_label} unreadable: {exc}")
            else:
                require_exact_fields(projection, {"tracks"}, projection_label, errors)
                if projection.get("tracks") != expected_tracks:
                    errors.append(f"{projection_label} must exactly match manifest tracks")


def validate_motion_track(
    track: Any,
    all_uids: set[str],
    unit_ids: set[str],
    complete: bool,
    label: str,
    errors: list[str],
) -> None:
    validate_envelope(track, label, errors, MOTION_FIELDS)
    if not isinstance(track, dict):
        return
    required = {
        "track_id", "motion_class", "shot_uids", "generation_unit_ids", "source_basis", "confidence",
        "assumptions", "required_for_generation", "absolute_anchors", "local_anchors",
        "start_state", "end_state", "parameters",
    }
    missing = sorted(required - track.keys())
    if missing:
        errors.append(f"{label}: missing motion fields {missing}")
        return
    shot_uids = track["shot_uids"]
    if not isinstance(shot_uids, list) or not shot_uids or not set(shot_uids) <= all_uids:
        errors.append(f"{label}: invalid shot_uids")
    if set(track.get("affected_shot_uids", [])) != set(shot_uids):
        errors.append(f"{label}: affected_shot_uids must equal motion shot_uids")
    generation_units = track["generation_unit_ids"]
    if not isinstance(generation_units, list) or not set(generation_units) <= unit_ids:
        errors.append(f"{label}: invalid generation_unit_ids")
    if complete and len(generation_units) != 1:
        errors.append(f"{label}: complete-stage motion track must be split to exactly one generation unit")
    if track.get("confidence") not in {"high", "medium", "low"}:
        errors.append(f"{label}: invalid confidence")
    for field in ("assumptions", "absolute_anchors", "local_anchors"):
        if not isinstance(track.get(field), list):
            errors.append(f"{label}: {field} must be list")
    for field in ("absolute_anchors", "local_anchors"):
        if isinstance(track.get(field), list) and complete and len(track[field]) < 2:
            errors.append(f"{label}: {field} must contain entry and exit anchors")
    for field in ("absolute_anchors", "local_anchors"):
        for index, anchor in enumerate(track.get(field, []) if isinstance(track.get(field), list) else []):
            anchor_label = f"{label}.{field}[{index}]"
            require_exact_fields(anchor, {"time_seconds", "state"}, anchor_label, errors)
            if isinstance(anchor, dict):
                if not is_number(anchor.get("time_seconds")):
                    errors.append(f"{anchor_label}: time_seconds invalid")
                if not isinstance(anchor.get("state"), str) or not anchor["state"]:
                    errors.append(f"{anchor_label}: state missing")
    for field in ("source_basis", "start_state", "end_state"):
        if not isinstance(track.get(field), str) or not track[field]:
            errors.append(f"{label}: {field} missing")
    motion_class = track.get("motion_class")
    requirements = {
        "camera": {"position_orientation", "primary_move", "path", "speed_easing", "focus_behavior", "start_end_framing"},
        "subject_blocking": {"positions_facing", "screen_direction", "contacts_handoffs", "path_spacing"},
        "rigid_object": {"pivot_or_path", "acceleration_easing", "orientation", "contacts_collisions", "state_at_cut"},
        "liquid": {"volume_continuity", "viscosity_behavior", "gravity_direction", "wetting_adhesion", "contact_surfaces", "breakup_coalescence", "state_at_cut"},
        "cloth": {"anchor_points", "drape_stiffness_intent", "wind_acceleration", "body_object_collisions", "settling_behavior", "state_at_cut"},
        "hair": {"root_lock", "inertia", "gravity_wind", "body_wardrobe_collisions", "settling_behavior", "state_at_cut"},
        "smoke_or_particles": {"emission_source", "advection", "dissipation", "collisions", "state_at_cut"},
    }
    if motion_class not in requirements:
        errors.append(f"{label}: invalid motion_class")
        return
    parameters = track.get("parameters")
    if not isinstance(parameters, dict):
        errors.append(f"{label}: parameters must be object")
    else:
        missing_parameters = sorted(requirements[motion_class] - parameters.keys())
        if missing_parameters:
            errors.append(f"{label}: {motion_class} parameters missing {missing_parameters}")
        extra_parameters = sorted(set(parameters) - requirements[motion_class])
        if extra_parameters:
            errors.append(f"{label}: {motion_class} parameters contain forbidden extras {extra_parameters}")


def _validate_package(
    root: Path,
    ffprobe_binary: str,
    canon_manifest: dict[str, Any] | None,
    project_root: Path | None,
) -> list[str]:
    errors: list[str] = []
    if project_root is not None:
        if root.resolve() == project_root.resolve():
            errors.append("package_root must be a strict child of project_root")
        try:
            root.resolve().relative_to(project_root.resolve())
        except ValueError:
            errors.append("package_root must be contained by project_root")
    manifest_path = root / "00_manifest" / "PREVIS_MANIFEST.json"
    if not manifest_path.is_file():
        return ["missing 00_manifest/PREVIS_MANIFEST.json"]
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"manifest unreadable: {exc}"]
    if not isinstance(data, dict):
        return ["manifest root must be an object"]
    validate_envelope(data, "manifest", errors, MANIFEST_FIELDS)
    validate_manifest_receipt(root, data, canon_manifest, errors)

    if data.get("schema_version") != "ai-video-timed-animatic-previs.v1":
        errors.append("schema_version invalid")
    package_status = data.get("package_status")
    if package_status not in {"draft", "generating", "assistant_validated", "user_approved", "repair_required", "stale", "blocked"}:
        errors.append("package_status invalid")
    stage = data.get("delivery_stage")
    if stage not in {"timing_animatic_v1", "control_previs_v2", "skipped_simple_single_shot"}:
        errors.append("delivery_stage invalid")
    execution_mode = data.get("execution_mode")
    count = data.get("shot_count")
    total = data.get("total_duration_seconds")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        errors.append("shot_count must be positive integer")
        count = 0
    if not is_number(total) or float(total) <= 0:
        errors.append("total_duration_seconds must be positive")
        total = 0.0

    authorities = data.get("source_authorities")
    if not isinstance(authorities, dict):
        errors.append("source_authorities missing")
        authorities = {}
    authority_names = {
        "shot_contract", "storyboard", "keyframe_pack", "keyframe_boundary_supplement",
        "provider_preflight", "provider_capability",
    }
    if set(authorities) != authority_names:
        errors.append("source_authorities must use exact authority slots")
    shot_contract = authorities.get("shot_contract")
    storyboard = authorities.get("storyboard")
    snapshots: dict[str, dict[str, Any] | None] = {}
    snapshots["shot_contract"] = validate_authority(root, shot_contract, "source_authorities.shot_contract", errors)
    snapshots["storyboard"] = validate_authority(root, storyboard, "source_authorities.storyboard", errors)
    keyframes = authorities.get("keyframe_pack")
    boundary_supplement = authorities.get("keyframe_boundary_supplement")
    preflight = authorities.get("provider_preflight")
    provider_capability = authorities.get("provider_capability")
    if keyframes is not None:
        snapshots["keyframe_pack"] = validate_authority(root, keyframes, "source_authorities.keyframe_pack", errors)
    if boundary_supplement is not None:
        snapshots["keyframe_boundary_supplement"] = validate_authority(root, boundary_supplement, "source_authorities.keyframe_boundary_supplement", errors)
    if preflight is not None:
        snapshots["provider_preflight"] = validate_authority(root, preflight, "source_authorities.provider_preflight", errors)
    if provider_capability is not None:
        snapshots["provider_capability"] = validate_authority(root, provider_capability, "source_authorities.provider_capability", errors)
    for name, snapshot in snapshots.items():
        if not isinstance(snapshot, dict):
            continue
        expected_owner, expected_schema = SOURCE_CONTRACTS[name]
        if snapshot.get("owner_skill") != expected_owner:
            errors.append(f"source_authorities.{name}: owner_skill must be {expected_owner}")
        if snapshot.get("schema_version") != expected_schema:
            errors.append(f"source_authorities.{name}: schema_version must be {expected_schema}")
    external_authorities = [item for item in (shot_contract, storyboard, keyframes, boundary_supplement, preflight, provider_capability) if isinstance(item, dict)]
    require_dependencies(data, [authority_dependency(item) for item in external_authorities], "manifest", errors, exact=True)
    input_evidence, consumed_evidence_ids = validate_input_evidence(root, data.get("input_file_evidence"), errors)
    validate_project_canon_binding(root, data, snapshots, canon_manifest, project_root, errors)

    used_modes = data.get("generation_modes_used")
    forbidden_modes = data.get("forbidden_generation_modes")
    if not isinstance(used_modes, list) or len(used_modes) != len(set(used_modes)) or not set(used_modes) <= ALLOWED_GENERATION_MODES:
        errors.append("generation_modes_used contains unsupported or prohibited mode")
    if not isinstance(forbidden_modes, list) or not PROHIBITED_GENERATION_MODES <= set(forbidden_modes):
        errors.append(
            "forbidden_generation_modes must include text_to_video, first_last_frame, "
            "and standalone_single_image_to_video"
        )
    if isinstance(used_modes, list) and set(used_modes) & PROHIBITED_GENERATION_MODES:
        errors.append("T2V, first/last-frame, and standalone single-image I2V generation are forbidden")
    invalidations = data.get("downstream_invalidations")
    if not isinstance(invalidations, list):
        errors.append("downstream_invalidations must be a list")
    else:
        seen_invalidations: set[tuple[Any, Any, Any, Any]] = set()
        for index, item in enumerate(invalidations):
            label = f"downstream_invalidations[{index}]"
            require_exact_fields(item, DOWNSTREAM_INVALIDATION_FIELDS, label, errors)
            if not isinstance(item, dict):
                continue
            signature = dependency_signature(item)
            if signature in seen_invalidations:
                errors.append(f"{label}: duplicate invalidation target")
            seen_invalidations.add(signature)
            validate_dependency(
                {field: item.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256")},
                label, errors,
            )
            if not isinstance(item.get("reason"), str) or not item["reason"].strip():
                errors.append(f"{label}: reason missing")
            scope = item.get("affected_shot_uids")
            if not isinstance(scope, list) or not all(isinstance(uid, str) and uid for uid in scope) or len(scope) != len(set(scope)):
                errors.append(f"{label}: affected_shot_uids must be unique strings")

    skip = data.get("skip_record")
    v1 = data.get("timing_animatic_v1")
    units = data.get("control_previs_v2_units")
    tracks = data.get("motion_physics_tracks")
    if not isinstance(units, list):
        errors.append("control_previs_v2_units must be list")
        units = []
    if not isinstance(tracks, list):
        errors.append("motion_physics_tracks must be list")
        tracks = []

    if stage == "skipped_simple_single_shot":
        if execution_mode != "skipped_simple_single_shot" or count != 1:
            errors.append("skip is allowed only for exactly one shot")
        if not isinstance(skip, dict):
            errors.append("skip_record required")
        else:
            validate_envelope(skip, "skip_record", errors, SKIP_FIELDS)
            if skip.get("affected_shot_uids") is None or len(skip.get("affected_shot_uids", [])) != 1:
                errors.append("skip_record must affect exactly one shot")
            if skip.get("reason") != "static_or_near_static_single_shot" or skip.get("previs_needed") is not False:
                errors.append("invalid skip reason")
            flags = skip.get("complexity_flags")
            required_flags = {
                "complex_camera", "multi_subject_blocking", "consequential_object_motion", "liquid_motion",
                "cloth_motion", "hair_motion", "smoke_or_particles", "timing_sensitive_transition",
            }
            if not isinstance(flags, dict) or set(flags) != required_flags or any(flags.get(flag) is not False for flag in required_flags):
                errors.append("simple-shot skip requires every complexity flag false")
            if isinstance(shot_contract, dict) and isinstance(storyboard, dict):
                require_dependencies(skip, [authority_dependency(shot_contract), authority_dependency(storyboard)], "skip_record", errors, exact=True)
        if v1 is not None or units or tracks:
            errors.append("skip package must not create V1, V2, or motion placeholders")
        if keyframes is not None or boundary_supplement is not None or preflight is not None or provider_capability is not None:
            errors.append("skip package must not claim unused keyframe/boundary/provider preflight")
        if used_modes:
            errors.append("skip package must not claim generation modes")
        if isinstance(skip, dict) and data.get("affected_shot_uids") != skip.get("affected_shot_uids"):
            errors.append("manifest affected_shot_uids must equal skip scope")
        if input_evidence:
            errors.append("skip package must not contain unused input files")
        return errors

    if execution_mode != "active":
        errors.append("active stage requires execution_mode active")
    if skip is not None:
        errors.append("active package must not contain skip_record")
    if not isinstance(v1, dict):
        errors.append("active package requires timing_animatic_v1")
        return errors
    validate_envelope(v1, "timing_animatic_v1", errors, V1_FIELDS)
    v1_uids = [entry.get("shot_uid") for entry in v1.get("timeline", []) if isinstance(entry, dict)]
    if len(v1_uids) != count:
        errors.append("V1 timeline count must equal shot_count")
    global_entries = validate_timeline(v1.get("timeline"), v1_uids, float(total), "timing_animatic_v1.timeline", errors)
    if v1.get("affected_shot_uids") != v1_uids:
        errors.append("V1 affected_shot_uids must equal timeline order")
    if data.get("affected_shot_uids") != v1_uids:
        errors.append("manifest affected_shot_uids must equal V1 timeline order")
    if v1.get("phase") != "timing_animatic_v1" or v1.get("provider_neutral") is not True or v1.get("uses_keyframes") is not False:
        errors.append("V1 must be provider-neutral and keyframe-independent")
    if v1.get("model_input_role") != "timing_review_only" or v1.get("is_model_input") is not False:
        errors.append("V1 must remain timing-review only")
    if v1.get("final_edit_asset") is not False or v1.get("silent") is not True:
        errors.append("V1 must be silent and non-final")
    if v1.get("render_style") not in {"storyboard_cut_animatic", "neutral_2d_blocking", "neutral_3d_blocking"}:
        errors.append("V1 render_style invalid")
    validate_control_dimensions(v1, "timing_animatic_v1", errors)
    validate_media_artifact(
        root, v1, float(total), v1.get("timeline", []), "timing_animatic_v1", errors, ffprobe_binary,
    )
    validate_active_reports(root, data, v1, errors)
    if isinstance(shot_contract, dict) and isinstance(storyboard, dict):
        require_dependencies(v1, [authority_dependency(shot_contract), authority_dependency(storyboard)], "timing_animatic_v1", errors, exact=True)
    validate_shot_and_storyboard_sources(
        data, v1, snapshots.get("shot_contract"), snapshots.get("storyboard"), input_evidence,
        consumed_evidence_ids, stage == "control_previs_v2", errors,
    )

    if stage == "timing_animatic_v1":
        if units or tracks:
            errors.append("V1-ready stage must not claim V2 units or final motion tracks")
        if any(item is not None for item in (keyframes, boundary_supplement, preflight, provider_capability)):
            errors.append("V1-ready stage must not bind K1/K2/P1/provider authorities")
        if package_status in READY_STATUSES and v1.get("approval_status") not in READY_STATUSES:
            errors.append("validated V1 package requires validated V1 artifact")
        unused = {item.get("input_id") for item in input_evidence} - consumed_evidence_ids
        if unused:
            errors.append(f"unconsumed input evidence records forbidden: {sorted(unused)}")
        return errors

    if keyframes is None or boundary_supplement is None or preflight is None or provider_capability is None:
        errors.append("V2 requires core keyframe, boundary supplement, provider preflight, and provider capability authorities")
    if v1.get("approval_status") not in READY_STATUSES:
        errors.append("V2 requires validated V1")
    if not units:
        errors.append("V2 stage requires at least one control unit")

    unit_ids = {unit.get("generation_unit_id") for unit in units if isinstance(unit, dict)}
    if None in unit_ids or len(unit_ids) != len(units):
        errors.append("generation_unit_id values must be present and unique")
        unit_ids.discard(None)
    track_ids = {track.get("track_id") for track in tracks if isinstance(track, dict)}
    if None in track_ids or len(track_ids) != len(tracks):
        errors.append("motion track IDs must be present and unique")
        track_ids.discard(None)
    all_uids = set(v1_uids)
    for index, track in enumerate(tracks):
        validate_motion_track(track, all_uids, unit_ids, True, f"motion_physics_tracks[{index}]", errors)
        if isinstance(track, dict) and all(isinstance(item, dict) for item in (shot_contract, storyboard, keyframes, boundary_supplement, preflight)):
            require_dependencies(
                track,
                [
                    authority_dependency(shot_contract), authority_dependency(storyboard),
                    {"artifact_id": v1["artifact_id"], "owner_skill": OWNER, "version": v1["version"], "sha256": v1["sha256"]},
                    authority_dependency(keyframes), authority_dependency(boundary_supplement),
                    authority_dependency(preflight),
                ],
                f"motion_physics_tracks[{index}]", errors, exact=True,
            )

    provider_video_constraints = validate_v2_source_semantics(
        root,
        v1,
        v1_uids,
        [unit for unit in units if isinstance(unit, dict)],
        snapshots.get("keyframe_pack"),
        snapshots.get("keyframe_boundary_supplement"),
        snapshots.get("provider_preflight"),
        snapshots.get("provider_capability"),
        authorities,
        input_evidence,
        consumed_evidence_ids,
        errors,
    )

    flattened: list[str] = []
    units_by_id: dict[str, dict[str, Any]] = {}
    for index, unit in enumerate(units):
        label = f"control_previs_v2_units[{index}]"
        validate_envelope(unit, label, errors, V2_FIELDS)
        if not isinstance(unit, dict):
            continue
        unit_id = unit.get("generation_unit_id")
        units_by_id[unit_id] = unit
        shot_uids = unit.get("shot_uids")
        if not isinstance(shot_uids, list) or not shot_uids or len(shot_uids) != len(set(shot_uids)):
            errors.append(f"{label}: shot_uids must be non-empty unique list")
            shot_uids = []
        flattened.extend(shot_uids)
        if unit.get("affected_shot_uids") != shot_uids:
            errors.append(f"{label}: affected_shot_uids must equal unit shot_uids")
        target = unit.get("target_duration_seconds")
        maximum = unit.get("provider_max_duration_seconds")
        if not is_number(target) or float(target) <= 0 or not is_number(maximum) or float(maximum) <= 0:
            errors.append(f"{label}: target/provider duration invalid")
            target = 0.0
        elif float(target) - float(maximum) > TIME_TOLERANCE:
            errors.append(f"{label}: unit exceeds provider max duration")
        if unit.get("multimodal_reference_video_supported") is not True:
            errors.append(f"{label}: provider lacks multimodal reference-video support")
        validate_timeline(unit.get("local_timeline"), shot_uids, float(target), f"{label}.local_timeline", errors, global_entries)
        validate_media_artifact(
            root,
            unit,
            float(target),
            unit.get("local_timeline", []),
            label,
            errors,
            ffprobe_binary,
            provider_video_constraints,
        )
        if unit.get("phase") != "control_previs_v2" or unit.get("model_input_role") != "control_reference_video" or unit.get("is_model_input") is not True:
            errors.append(f"{label}: V2 must be a control reference video")
        if unit.get("final_edit_asset") is not False or unit.get("silent") is not True:
            errors.append(f"{label}: V2 must be silent and non-final")
        if unit.get("identity_authority") is not False or unit.get("look_authority") is not False:
            errors.append(f"{label}: V2 cannot own identity or look")
        if unit.get("render_style") not in {"neutral_diagrammatic_or_simple_3d", "neutral_2d_blocking", "neutral_3d_blocking"}:
            errors.append(f"{label}: render_style invalid")
        validate_control_dimensions(unit, label, errors)
        motion_ids = unit.get("motion_track_ids")
        if not isinstance(motion_ids, list) or not set(motion_ids) <= track_ids:
            errors.append(f"{label}: motion_track_ids reference unknown track")
        required_dependencies: list[dict[str, Any]] = [
            authority_dependency(shot_contract), authority_dependency(storyboard),
            {"artifact_id": v1["artifact_id"], "owner_skill": OWNER, "version": v1["version"], "sha256": v1["sha256"]},
        ]
        if isinstance(keyframes, dict):
            required_dependencies.append(authority_dependency(keyframes))
        if isinstance(boundary_supplement, dict):
            required_dependencies.append(authority_dependency(boundary_supplement))
        if isinstance(preflight, dict):
            required_dependencies.append(authority_dependency(preflight))
        if isinstance(provider_capability, dict):
            required_dependencies.append(authority_dependency(provider_capability))
        for motion_id in motion_ids if isinstance(motion_ids, list) else []:
            track = next((item for item in tracks if item.get("track_id") == motion_id), None)
            if track:
                required_dependencies.append({"artifact_id": track["artifact_id"], "owner_skill": OWNER, "version": track["version"], "sha256": track["sha256"]})
        require_dependencies(unit, required_dependencies, label, errors, exact=True)

    for index, track in enumerate(tracks):
        if not isinstance(track, dict):
            continue
        label = f"motion_physics_tracks[{index}]"
        scoped_units = [units_by_id.get(item) for item in track.get("generation_unit_ids", [])]
        scoped_units = [item for item in scoped_units if isinstance(item, dict)]
        scoped_shots = set().union(*(set(item.get("shot_uids", [])) for item in scoped_units)) if scoped_units else set()
        track_shots = set(track.get("shot_uids", []))
        ordered_track_shots = [uid for uid in v1_uids if uid in track_shots]
        if track.get("shot_uids") != ordered_track_shots:
            errors.append(f"{label}: motion Shot UIDs must follow V1 order")
        positions = [v1_uids.index(uid) for uid in ordered_track_shots]
        if positions and positions != list(range(positions[0], positions[-1] + 1)):
            errors.append(f"{label}: one motion track must cover a contiguous Shot range")
        if not track_shots <= scoped_shots:
            errors.append(f"{label}: motion Shot UIDs are outside the declared generation unit")
        for unit in scoped_units:
            if not track_shots.intersection(unit.get("shot_uids", [])):
                errors.append(f"{label}: declared generation unit has no affected motion Shot UID")
        absolute_windows = [global_entries[uid] for uid in track_shots if uid in global_entries]
        if absolute_windows:
            for anchor in track.get("absolute_anchors", []):
                if isinstance(anchor, dict) and is_number(anchor.get("time_seconds")):
                    value = float(anchor["time_seconds"])
                    if not any(
                        float(item["start_seconds"]) - TIME_TOLERANCE <= value <= float(item["end_seconds"]) + TIME_TOLERANCE
                        for item in absolute_windows
                    ):
                        errors.append(f"{label}: absolute anchor is outside affected Shot timing")
        if len(scoped_units) == 1:
            unit_duration = scoped_units[0].get("target_duration_seconds")
            if is_number(unit_duration):
                for anchor in track.get("local_anchors", []):
                    if isinstance(anchor, dict) and is_number(anchor.get("time_seconds")):
                        value = float(anchor["time_seconds"])
                        if value < -TIME_TOLERANCE or value > float(unit_duration) + TIME_TOLERANCE:
                            errors.append(f"{label}: local anchor is outside generation-unit timing")

    if flattened != v1_uids:
        errors.append("V2 generation units must cover all Shot UIDs exactly once in V1 order")
    for track in tracks:
        if not isinstance(track, dict) or track.get("required_for_generation") is not True:
            continue
        for unit_id in track.get("generation_unit_ids", []):
            unit = units_by_id.get(unit_id)
            if unit and track.get("track_id") not in unit.get("motion_track_ids", []):
                errors.append(f"required motion track {track.get('track_id')} missing from unit {unit_id}")

    if package_status in READY_STATUSES:
        current = [data, v1, *units, *tracks]
        if any(isinstance(item, dict) and item.get("approval_status") not in READY_STATUSES for item in current):
            errors.append("validated package contains non-ready current artifact")
    unused = {item.get("input_id") for item in input_evidence} - consumed_evidence_ids
    if unused:
        errors.append(f"unconsumed input evidence records forbidden: {sorted(unused)}")
    return errors


def validate_package(
    root: Path,
    ffprobe_binary: str = "ffprobe",
    canon_manifest: dict[str, Any] | None = None,
    project_root: Path | None = None,
) -> list[str]:
    try:
        return _validate_package(root, ffprobe_binary, canon_manifest, project_root)
    except (TypeError, KeyError, AttributeError, ValueError, OverflowError) as exc:
        return [f"malformed previs package rejected safely: {type(exc).__name__}: {exc}"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_root", type=Path)
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument(
        "--project-canon-manifest", type=Path,
        help="optional integration input; binds authorities, owned artifacts, and receipt to an explicit registry",
    )
    parser.add_argument(
        "--project-root", type=Path,
        help="explicit project root used for Canon locators; package_root may be a nested sibling of other artifact packages",
    )
    args = parser.parse_args()
    canon_manifest = None
    project_root = args.project_root.resolve() if args.project_root is not None else None
    if args.project_canon_manifest is not None:
        if project_root is None:
            print("ERROR: --project-root is required with --project-canon-manifest")
            return 2
        canon_path = args.project_canon_manifest.resolve()
        expected_canon_path = project_root / "00_project_canon/PROJECT_CANON_MANIFEST.json"
        if canon_path != expected_canon_path.resolve():
            print("ERROR: Project Canon manifest must be <project_root>/00_project_canon/PROJECT_CANON_MANIFEST.json")
            return 2
        try:
            canon_manifest = json.loads(
                canon_path.read_text(encoding="utf-8"),
                parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
            )
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"ERROR: Project Canon manifest unreadable: {exc}")
            return 2
    errors = validate_package(args.package_root.resolve(), args.ffprobe, canon_manifest, project_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"FAILED: {len(errors)} error(s)")
        return 1
    print("PASS: timing animatic / control previs package contract is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
