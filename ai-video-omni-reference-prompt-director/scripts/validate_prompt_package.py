#!/usr/bin/env python3
"""Validate an Omni-reference package with Pillow and live ffprobe evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from build_reference_atlas import (
    ALLOWED_ATLAS_CONTROL_ROLES,
    ATLAS_CODEC,
    ATLAS_LAYOUT_POLICY,
    ATLAS_LEGIBILITY_POLICY,
    ATLAS_SPEC_VERSION,
    MINIMUM_ATLAS_PANEL_HEIGHT_PIXELS,
    MINIMUM_ATLAS_PANEL_WIDTH_PIXELS,
    OUTPUT_ENCODE_POLICY,
    SOURCE_DECODE_POLICY,
    build_from_spec,
    decode_common_raster,
)
from ai_video_input_contracts import validate_owner_asset_export, validate_owner_input
from json_schema_runtime import validate_instance
from probe_control_media import MediaProbeError, probe_media


OWNER = "ai-video-omni-reference-prompt-director"


def _skill_name(*parts: str) -> str:
    """Build external owner IDs without encoding package-relative paths."""
    return "-".join(parts)


SHOT_OWNER = _skill_name("ai", "video", "shot", "script", "director")
LOOK_OWNER = _skill_name("ai", "video", "global", "look", "lock")
STORYBOARD_OWNER = _skill_name("ai", "video", "modular", "storyboard")
KEYFRAME_OWNER = _skill_name("ai", "video", "keyframe", "continuity", "pack")
PREVIS_OWNER = _skill_name("ai", "video", "timed", "animatic", "previs", "director")
CASTING_OWNER = _skill_name("character", "casting", "lock", "board")
CHARACTER_FINAL_OWNER = _skill_name("character", "final", "lock", "board")
SINGLE_FACE_OWNER = _skill_name("single", "face", "character", "lock", "board")
MULTI_ANGLE_OWNER = _skill_name("multi", "angle", "product", "identity", "lock", "board")
PACKAGING_OWNER = _skill_name("packaging", "product", "identity", "label", "lock", "board")
MATERIAL_OWNER = _skill_name("material", "sensitive", "product", "master", "asset", "board")
SCENE_OWNER = _skill_name("scene", "canon", "asset", "pack")
APPROVALS = {"draft", "assistant_validated", "user_approved", "stale", "blocked"}
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
HEX64 = re.compile(r"^[a-f0-9]{64}$")
TIME_TOLERANCE = 0.001
REQUIRED_PROMPT_SECTIONS = (
    "[生成任务与输出规格]", "[素材及控制权映射]", "[主要主体]", "[场景与环境初始状态]",
    "[情绪与广告目标的可见表现]", "[全局导演语法", "[全局影调", "[全局连续性与禁止项]",
    "[分段镜头]", "[稳定与负面约束]",
)
FORBIDDEN_PAYLOAD_TOKENS = (
    "text_to_video", "text-to-video", "text to video", "t2v",
    "first_frame", "first-frame", "first frame", "last_frame", "last-frame", "last frame",
    "start_frame", "start-frame", "end_frame", "end-frame", "first_last", "first-last",
    "endpoint_frame", "endpoint-frame", "endpoint frame", "frame_interpolation", "endpoint_interpolation",
)
FORBIDDEN_NORMALIZED_PAYLOAD_TOKENS = (
    "text_to_video", "text2video", "t2v", "image_to_video", "image2video", "i2v",
    "first_frame", "last_frame", "start_frame", "end_frame", "head_frame", "tail_frame",
    "first_image", "last_image", "start_image", "end_image", "head_image", "tail_image",
    "initial_image", "final_image", "first_last", "endpoint_frame", "frame_interpolation",
    "endpoint_interpolation",
)

PREFLIGHT_SNAPSHOT = "00_manifest/PROJECT_CANON_PREFLIGHT_INPUT_SNAPSHOT.json"
COMPILE_SNAPSHOT = "00_manifest/PROJECT_CANON_COMPILE_INPUT_SNAPSHOT.json"
MANIFEST_RECEIPT = "00_manifest/MANIFEST_UPDATE_RECEIPT.json"
PREFLIGHT_PLAN = "00_manifest/GENERATION_UNIT_PREFLIGHT_PLAN.json"
IR_PATH = "00_manifest/CANONICAL_VIDEO_GENERATION_IR.json"
MODEL_CAPS = "00_manifest/MODEL_CAPABILITY_PROFILE.json"
PROVIDER_CAPS = "00_manifest/PROVIDER_CAPABILITY_PROFILE.json"
LOCKFILE = "00_manifest/DEPENDENCY_LOCKFILE.json"
BINDINGS = "01_bindings/MULTIMODAL_BINDING_MANIFEST.json"
UNIT_PROMPTS = "02_prompts/GENERATION_UNIT_PROMPTS.json"
REPAIR_PROMPTS = "02_prompts/SHOT_LEVEL_REPAIR_PROMPTS.json"
PAYLOAD = "03_payload/PROVIDER_PAYLOAD_MANIFEST.json"
FEEDBACK = "04_reports/FEEDBACK_ROUTE.json"
DEFAULT_POST_CANON = "00_project_canon/PROJECT_CANON_MANIFEST.json"

JSON_FILES = [
    PREFLIGHT_SNAPSHOT, COMPILE_SNAPSHOT, MANIFEST_RECEIPT, PREFLIGHT_PLAN, IR_PATH, MODEL_CAPS,
    PROVIDER_CAPS, LOCKFILE, BINDINGS, UNIT_PROMPTS, REPAIR_PROMPTS, PAYLOAD, FEEDBACK,
]
TEXT_FILES = [
    "02_prompts/PROJECT_GLOBAL_BLOCK.md",
    "02_prompts/SEEDANCE_2_5_MASTER_PROMPT.md",
    "02_prompts/SEEDANCE_2_0_COMPATIBLE_RENDER.md",
    "04_reports/CAPACITY_DEGRADATION_REPORT.md",
    "04_reports/PROMPT_REVISION_DIFF.md",
]
EXPECTED_OUTPUT_LOCK_PATHS = {
    IR_PATH, MODEL_CAPS, PROVIDER_CAPS, BINDINGS, UNIT_PROMPTS, REPAIR_PROMPTS,
    PAYLOAD, FEEDBACK, *TEXT_FILES,
}
RUNTIME_SCHEMA_BY_FILE = {
    PREFLIGHT_PLAN: "generation_unit_preflight.schema.json",
    IR_PATH: "canonical_ir.schema.json",
    MODEL_CAPS: "capability_profile.schema.json",
    PROVIDER_CAPS: "capability_profile.schema.json",
    LOCKFILE: "dependency_lockfile.schema.json",
    BINDINGS: "binding_manifest.schema.json",
    PAYLOAD: "provider_payload_manifest.schema.json",
    FEEDBACK: "feedback_route.schema.json",
}
def load_json(path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number: {value}")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)


def resolve_package_path(root: Path, value: Any, label: str) -> tuple[Path | None, list[str]]:
    if not isinstance(value, str) or not value:
        return None, [f"{label}: non-empty file path required"]
    candidate = Path(value)
    if candidate.is_absolute():
        return None, [f"{label}: absolute paths are forbidden"]
    if "\\" in value or (len(value) > 1 and value[0].isalpha() and value[1] == ":"):
        return None, [f"{label}: file path must use portable POSIX package-relative syntax"]
    candidate = root / candidate
    try:
        resolved = candidate.resolve()
        resolved.relative_to(root.resolve())
    except (OSError, ValueError):
        return None, [f"{label}: path escapes declared root"]
    return resolved, []


def read_hash_locked_file(root: Path, file_path: Any, expected_hash: Any, label: str) -> tuple[Path | None, bytes | None, list[str]]:
    path, errors = resolve_package_path(root, file_path, label)
    if path is None:
        return None, None, errors
    if not path.is_file():
        return path, None, errors + [f"{label}: file missing"]
    data = path.read_bytes()
    actual_hash = hashlib.sha256(data).hexdigest()
    if expected_hash != actual_hash:
        errors.append(f"{label}: file SHA-256 mismatch")
    return path, data, errors


def read_hash_locked_json(root: Path, file_path: Any, expected_hash: Any, label: str) -> tuple[dict[str, Any] | None, list[str]]:
    path, data, errors = read_hash_locked_file(root, file_path, expected_hash, label)
    if data is None:
        return None, errors
    try:
        value = json.loads(data.decode("utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return None, errors + [f"{label}: JSON parse failed: {exc}"]
    if not isinstance(value, dict):
        errors.append(f"{label}: top-level JSON object required")
        return None, errors
    return value, errors


def is_hash(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX64.fullmatch(value))


def is_semver(value: Any) -> bool:
    return isinstance(value, str) and bool(SEMVER.fullmatch(value))


def semver_tuple(value: Any) -> tuple[int, int, int] | None:
    if not is_semver(value):
        return None
    return tuple(int(part) for part in value.split("."))  # type: ignore[return-value]


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def close(left: Any, right: Any) -> bool:
    return is_number(left) and is_number(right) and abs(float(left) - float(right)) <= TIME_TOLERANCE


def canonical_envelope_hash(record: dict[str, Any]) -> str:
    payload = copy.deepcopy(record)
    payload.pop("sha256", None)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def dependency_tuple(value: Any) -> tuple[Any, Any, Any, Any] | None:
    if not isinstance(value, dict):
        return None
    return tuple(value.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))


def validate_dependency(dep: Any, label: str) -> list[str]:
    if not isinstance(dep, dict) or set(dep) != {"artifact_id", "owner_skill", "version", "sha256"}:
        return [f"{label}: dependency must contain exact artifact_id/owner_skill/version/sha256"]
    errors: list[str] = []
    if not isinstance(dep.get("artifact_id"), str) or not dep["artifact_id"]:
        errors.append(f"{label}: artifact_id must be non-empty")
    if not isinstance(dep.get("owner_skill"), str) or not dep["owner_skill"]:
        errors.append(f"{label}: owner_skill must be non-empty")
    if not is_semver(dep.get("version")):
        errors.append(f"{label}: version must be SemVer")
    if not is_hash(dep.get("sha256")):
        errors.append(f"{label}: sha256 invalid")
    return errors


def validate_envelope(record: Any, label: str, expected_owner: str | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return [f"{label}: artifact envelope must be an object"]
    required = {
        "contract_version", "artifact_id", "owner_skill", "version", "sha256",
        "approval_status", "dependencies", "affected_shot_uids", "stale_reason",
    }
    missing = sorted(required - set(record))
    if missing:
        return [f"{label}: missing envelope fields {missing}"]
    if record.get("contract_version") != "ai-video-artifact-v1":
        errors.append(f"{label}: contract_version must be ai-video-artifact-v1")
    if not isinstance(record.get("artifact_id"), str) or not record["artifact_id"].strip():
        errors.append(f"{label}: artifact_id must be non-empty")
    if not isinstance(record.get("owner_skill"), str) or not record["owner_skill"].strip():
        errors.append(f"{label}: owner_skill must be non-empty")
    elif expected_owner is not None and record["owner_skill"] != expected_owner:
        errors.append(f"{label}: owner_skill must be {expected_owner}")
    if not is_semver(record.get("version")):
        errors.append(f"{label}: version must be SemVer")
    status = record.get("approval_status")
    if status not in APPROVALS:
        errors.append(f"{label}: invalid approval_status")
    digest = record.get("sha256")
    if status == "draft":
        if digest is not None:
            errors.append(f"{label}: draft sha256 must be null")
    else:
        if not is_hash(digest):
            errors.append(f"{label}: non-draft sha256 must be 64 lowercase hex")
        else:
            try:
                expected = canonical_envelope_hash(record)
            except (TypeError, ValueError) as exc:
                errors.append(f"{label}: non-canonical JSON: {exc}")
            else:
                if digest != expected:
                    errors.append(f"{label}: canonical envelope hash mismatch")
    stale_reason = record.get("stale_reason")
    if status == "stale" and (not isinstance(stale_reason, str) or not stale_reason.strip()):
        errors.append(f"{label}: stale artifact requires stale_reason")
    if status != "stale" and stale_reason is not None:
        errors.append(f"{label}: non-stale artifact stale_reason must be null")
    dependencies = record.get("dependencies")
    if not isinstance(dependencies, list):
        errors.append(f"{label}: dependencies must be an array")
    else:
        for index, dep in enumerate(dependencies):
            errors.extend(validate_dependency(dep, f"{label}.dependencies[{index}]"))
    shots = record.get("affected_shot_uids")
    if not isinstance(shots, list) or not all(isinstance(item, str) and item for item in shots):
        errors.append(f"{label}: affected_shot_uids must be a string array")
    elif len(shots) != len(set(shots)):
        errors.append(f"{label}: affected_shot_uids must be unique")
    return errors


def validate_consumed_envelope(record: Any, label: str) -> list[str]:
    """Validate a manifest-locked envelope projection without rehashing omitted payload fields."""
    if not isinstance(record, dict):
        return [f"{label}: consumed artifact envelope must be an object"]
    required = {
        "contract_version", "artifact_id", "owner_skill", "version", "sha256",
        "approval_status", "dependencies", "affected_shot_uids", "stale_reason",
    }
    errors: list[str] = []
    missing = required - set(record)
    if missing:
        return [f"{label}: missing envelope fields {sorted(missing)}"]
    if record.get("contract_version") != "ai-video-artifact-v1":
        errors.append(f"{label}: contract_version invalid")
    if not isinstance(record.get("artifact_id"), str) or not record["artifact_id"]:
        errors.append(f"{label}: artifact_id required")
    if not isinstance(record.get("owner_skill"), str) or not record["owner_skill"]:
        errors.append(f"{label}: owner_skill required")
    if not is_semver(record.get("version")) or not is_hash(record.get("sha256")):
        errors.append(f"{label}: SemVer and sha256 required")
    if record.get("approval_status") not in APPROVALS:
        errors.append(f"{label}: approval_status invalid")
    if record.get("approval_status") == "stale":
        if not isinstance(record.get("stale_reason"), str) or not record["stale_reason"].strip():
            errors.append(f"{label}: stale_reason required")
    elif record.get("stale_reason") is not None:
        errors.append(f"{label}: non-stale artifact must have null stale_reason")
    dependencies = record.get("dependencies")
    if not isinstance(dependencies, list):
        errors.append(f"{label}: dependencies must be an array")
    else:
        for index, dep in enumerate(dependencies):
            errors.extend(validate_dependency(dep, f"{label}.dependencies[{index}]"))
    shots = record.get("affected_shot_uids")
    if not isinstance(shots, list) or not all(isinstance(item, str) and item for item in shots):
        errors.append(f"{label}: affected_shot_uids invalid")
    elif len(shots) != len(set(shots)):
        errors.append(f"{label}: affected_shot_uids must be unique")
    return errors


def validate_manifest_snapshot(snapshot: Any, label: str) -> tuple[list[str], dict[str, dict[str, Any]]]:
    errors = validate_envelope(snapshot, label, "ai-video-shot-script-director")
    if not isinstance(snapshot, dict):
        return errors, {}
    if snapshot.get("schema_version") != "ai-video-project-canon-manifest.v1":
        errors.append(f"{label}: wrong schema_version")
    if snapshot.get("manifest_role") != "artifact_registry_only":
        errors.append(f"{label}: wrong manifest_role")
    if snapshot.get("dependencies") != []:
        errors.append(f"{label}: manifest dependencies must be empty")
    shots = snapshot.get("canonical_shot_uids")
    if not isinstance(shots, list) or not shots or not all(isinstance(item, str) and item for item in shots):
        errors.append(f"{label}: canonical_shot_uids must be non-empty strings")
        shots = []
    elif len(shots) != len(set(shots)):
        errors.append(f"{label}: canonical_shot_uids must be unique")
    if snapshot.get("affected_shot_uids") != shots:
        errors.append(f"{label}: affected_shot_uids must equal canonical shots")
    active = snapshot.get("active_artifacts")
    if not isinstance(active, list):
        errors.append(f"{label}: active_artifacts must be an array")
        active = []
    by_id: dict[str, dict[str, Any]] = {}
    slots: set[str] = set()
    for index, entry in enumerate(active):
        item_label = f"{label}.active_artifacts[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{item_label}: must be an object")
            continue
        required = {
            "artifact_slot", "artifact_id", "artifact_type", "owner_skill", "version", "sha256",
            "approval_status", "stale_reason", "eligible_for_downstream", "affected_shot_uids",
            "locator", "file_sha256", "artifact_record_locator", "artifact_record_file_sha256", "dependencies",
        }
        missing = required - set(entry)
        if missing:
            errors.append(f"{item_label}: missing fields {sorted(missing)}")
            continue
        artifact_id = entry.get("artifact_id")
        slot = entry.get("artifact_slot")
        if not isinstance(artifact_id, str) or not artifact_id or artifact_id in by_id:
            errors.append(f"{item_label}: artifact_id must be non-empty and unique")
            continue
        if artifact_id == snapshot.get("artifact_id"):
            errors.append(f"{item_label}: manifest cannot register itself")
        by_id[artifact_id] = entry
        if not isinstance(slot, str) or not slot or slot in slots:
            errors.append(f"{item_label}: artifact_slot must be non-empty and unique")
        else:
            slots.add(slot)
        if not isinstance(entry.get("owner_skill"), str) or not entry["owner_skill"] or not is_semver(entry.get("version")) or not is_hash(entry.get("sha256")):
            errors.append(f"{item_label}: owner/version/hash invalid")
        status = entry.get("approval_status")
        eligible = entry.get("eligible_for_downstream")
        if status not in APPROVALS or not isinstance(eligible, bool):
            errors.append(f"{item_label}: approval/eligibility invalid")
        if eligible and (status not in {"assistant_validated", "user_approved"} or entry.get("stale_reason") is not None):
            errors.append(f"{item_label}: downstream eligibility invalid")
        scope = entry.get("affected_shot_uids")
        if not isinstance(scope, list) or not all(isinstance(item, str) and item in shots for item in scope):
            errors.append(f"{item_label}: affected shots invalid")
        file_hash = entry.get("file_sha256")
        if file_hash is not None and not is_hash(file_hash):
            errors.append(f"{item_label}: file_sha256 invalid")
        record_hash = entry.get("artifact_record_file_sha256")
        if not isinstance(entry.get("artifact_record_locator"), str) or not entry["artifact_record_locator"] or not is_hash(record_hash):
            errors.append(f"{item_label}: artifact record locator/hash required")
        dependencies = entry.get("dependencies")
        if not isinstance(dependencies, list):
            errors.append(f"{item_label}: dependencies must be an array")
        else:
            for dep_index, dep in enumerate(dependencies):
                errors.extend(validate_dependency(dep, f"{item_label}.dependencies[{dep_index}]"))
                if isinstance(dep, dict) and dep.get("artifact_id") == snapshot.get("artifact_id"):
                    errors.append(f"{item_label}: reverse manifest dependency forbidden")
    return errors, by_id


def validate_manifest_receipt(root: Path, receipt: Any, snapshot: dict[str, Any], expected_path: str, label: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(receipt, dict):
        return [f"{label}: read receipt must be an object"]
    path = root / expected_path
    if receipt.get("snapshot_path") != expected_path:
        errors.append(f"{label}: snapshot_path mismatch")
    if not path.is_file():
        errors.append(f"{label}: snapshot file missing")
    else:
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if receipt.get("snapshot_file_sha256") != file_hash:
            errors.append(f"{label}: snapshot_file_sha256 mismatch")
    if receipt.get("manifest_artifact_id") != snapshot.get("artifact_id"):
        errors.append(f"{label}: manifest_artifact_id mismatch")
    if receipt.get("manifest_version") != snapshot.get("version"):
        errors.append(f"{label}: manifest_version mismatch")
    if receipt.get("manifest_sha256") != snapshot.get("sha256"):
        errors.append(f"{label}: manifest_sha256 mismatch")
    return errors


def validate_manifest_update_receipt(
    receipt: Any,
    compile_snapshot: dict[str, Any],
    owned_docs: dict[str, dict[str, Any]],
    additional_owned_artifact_ids: set[str],
) -> list[str]:
    label = "manifest_update_receipt"
    if not isinstance(receipt, dict):
        return [f"{label}: must be an object"]
    errors: list[str] = []
    if set(receipt) != {
        "schema_version", "canonical_manifest_locator", "updated_by_skill", "delta_status", "base_manifest_sha256",
        "resulting_manifest_sha256", "registered_artifact_ids",
    }:
        errors.append(f"{label}: exact receipt fields required")
    if receipt.get("schema_version") != "ai-video-manifest-update-receipt.v1" or receipt.get("canonical_manifest_locator") != "00_project_canon/PROJECT_CANON_MANIFEST.json" or receipt.get("updated_by_skill") != OWNER or receipt.get("delta_status") != "applied":
        errors.append(f"{label}: contract mismatch")
    if receipt.get("base_manifest_sha256") != compile_snapshot.get("sha256"):
        errors.append(f"{label}: base hash must equal compile manifest snapshot hash")
    if not is_hash(receipt.get("resulting_manifest_sha256")):
        errors.append(f"{label}: resulting manifest hash invalid")
    expected = {value.get("artifact_id") for value in owned_docs.values()} | additional_owned_artifact_ids
    registered = receipt.get("registered_artifact_ids")
    if not isinstance(registered, list) or not all(isinstance(item, str) and item for item in registered) or len(registered) != len(set(registered)) or set(registered) != expected:
        errors.append(f"{label}: must register every Prompt-owned artifact exactly")
    return errors


def validate_actual_post_canon(
    package_root: Path,
    project_root: Path,
    actual_manifest_path: Path | None,
    preflight_snapshot: dict[str, Any],
    compile_snapshot: dict[str, Any],
    receipt: dict[str, Any],
    owned_docs: dict[str, dict[str, Any]],
    additional_owned_artifact_ids: set[str],
) -> list[str]:
    """Prove P1 ancestry and Prompt's applied delta against the real post-write Canon."""
    if actual_manifest_path is None:
        return ["actual post-Canon: --project-canon-manifest is required for a final package"]
    try:
        actual_manifest_path.resolve().relative_to(project_root.resolve())
    except (OSError, ValueError):
        return ["actual post-Canon: manifest path must be inside --project-root"]
    canonical_locator = receipt.get("canonical_manifest_locator")
    if not isinstance(canonical_locator, str) or (project_root / canonical_locator).resolve() != actual_manifest_path.resolve():
        return ["actual post-Canon: CLI path must equal receipt canonical_manifest_locator under --project-root"]
    try:
        actual = load_json(actual_manifest_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"actual post-Canon: unreadable: {exc}"]
    if not isinstance(actual, dict):
        return ["actual post-Canon: top-level object required"]
    errors, active = validate_manifest_snapshot(actual, "actual post-Canon")
    if compile_snapshot.get("base_manifest_sha256") != preflight_snapshot.get("sha256"):
        errors.append("Canon ancestry: compile snapshot must directly descend from the preflight snapshot")
    if actual.get("base_manifest_sha256") != compile_snapshot.get("sha256"):
        errors.append("actual post-Canon: base_manifest_sha256 must equal compile snapshot sha256")
    preflight_version = semver_tuple(preflight_snapshot.get("version"))
    compile_version = semver_tuple(compile_snapshot.get("version"))
    actual_version = semver_tuple(actual.get("version"))
    if preflight_version is None or compile_version is None or compile_version <= preflight_version:
        errors.append("Canon ancestry: compile manifest version must exceed preflight manifest version")
    if compile_version is None or actual_version is None or actual_version <= compile_version:
        errors.append("actual post-Canon: version must exceed compile manifest version")
    preflight_revision = preflight_snapshot.get("revision_counter")
    compile_revision = compile_snapshot.get("revision_counter")
    actual_revision = actual.get("revision_counter")
    if (
        not isinstance(preflight_revision, int) or isinstance(preflight_revision, bool)
        or not isinstance(compile_revision, int) or isinstance(compile_revision, bool)
        or compile_revision != preflight_revision + 1
    ):
        errors.append("Canon ancestry: compile revision_counter must equal preflight revision_counter + 1")
    if (
        not isinstance(compile_revision, int) or isinstance(compile_revision, bool)
        or not isinstance(actual_revision, int) or isinstance(actual_revision, bool)
        or actual_revision != compile_revision + 1
    ):
        errors.append("actual post-Canon: revision_counter must equal compile revision_counter + 1")
    if actual.get("updated_by_skill") != OWNER:
        errors.append("actual post-Canon: updated_by_skill must be Prompt Director")
    if receipt.get("base_manifest_sha256") != compile_snapshot.get("sha256"):
        errors.append("manifest update receipt: base hash differs from compile snapshot")
    if receipt.get("resulting_manifest_sha256") != actual.get("sha256"):
        errors.append("manifest update receipt: result hash differs from actual post-Canon")
    if receipt.get("updated_by_skill") != OWNER:
        errors.append("manifest update receipt: updated_by_skill differs from Prompt Director")

    compile_active = {
        item.get("artifact_id"): item for item in compile_snapshot.get("active_artifacts", []) if isinstance(item, dict)
    }
    for artifact_id, compile_entry in compile_active.items():
        if active.get(artifact_id) != compile_entry:
            errors.append(f"actual post-Canon: compile-active artifact was changed or removed by Prompt: {artifact_id}")
    plan = owned_docs.get(PREFLIGHT_PLAN, {})
    plan_entry = compile_active.get(plan.get("artifact_id"))
    if not isinstance(plan_entry, dict) or plan_entry.get("artifact_slot") != "generation_unit_preflight_plan":
        errors.append("Canon ancestry: P1 must be an active compile-snapshot entry")
    else:
        expected_plan_file_hash = hashlib.sha256((package_root / PREFLIGHT_PLAN).read_bytes()).hexdigest()
        expected_plan_locator = (package_root / PREFLIGHT_PLAN).resolve().relative_to(project_root.resolve()).as_posix()
        if (
            plan_entry.get("owner_skill") != OWNER
            or plan_entry.get("version") != plan.get("version")
            or plan_entry.get("sha256") != plan.get("sha256")
            or plan_entry.get("locator") != expected_plan_locator
            or plan_entry.get("file_sha256") != expected_plan_file_hash
            or plan_entry.get("artifact_record_locator") != expected_plan_locator
            or plan_entry.get("artifact_record_file_sha256") != expected_plan_file_hash
        ):
            errors.append("Canon ancestry: compile P1 identity/file lock differs from the actual plan")
        read_receipt = plan.get("project_canon_read_receipt") if isinstance(plan.get("project_canon_read_receipt"), dict) else {}
        if read_receipt.get("manifest_sha256") != preflight_snapshot.get("sha256"):
            errors.append("Canon ancestry: P1 read receipt does not bind the preflight ancestor")

    registered = receipt.get("registered_artifact_ids") if isinstance(receipt.get("registered_artifact_ids"), list) else []
    expected_registered = {value.get("artifact_id") for value in owned_docs.values()} | additional_owned_artifact_ids
    if set(registered) != expected_registered:
        errors.append("actual post-Canon: receipt registered IDs must equal all Prompt-owned artifacts")
    for rel, document in owned_docs.items():
        artifact_id = document.get("artifact_id")
        entry = active.get(artifact_id)
        if not isinstance(entry, dict):
            errors.append(f"actual post-Canon: Prompt artifact missing from active entries: {artifact_id}")
            continue
        output_path = (package_root / rel).resolve()
        try:
            expected_locator = output_path.relative_to(project_root.resolve()).as_posix()
        except ValueError:
            errors.append(f"actual post-Canon: Prompt package escapes project root: {rel}")
            continue
        actual_file_hash = hashlib.sha256(output_path.read_bytes()).hexdigest()
        expected = {
            "owner_skill": OWNER, "version": document.get("version"), "sha256": document.get("sha256"),
            "approval_status": document.get("approval_status"), "stale_reason": document.get("stale_reason"),
            "affected_shot_uids": document.get("affected_shot_uids"), "dependencies": document.get("dependencies"),
            "locator": expected_locator, "file_sha256": actual_file_hash,
            "artifact_record_locator": expected_locator, "artifact_record_file_sha256": actual_file_hash,
            "eligible_for_downstream": True,
        }
        if any(entry.get(field) != value for field, value in expected.items()):
            errors.append(f"actual post-Canon: active identity/hash/file lock mismatch for {artifact_id}")
    for artifact_id in additional_owned_artifact_ids:
        entry = active.get(artifact_id)
        if not isinstance(entry, dict) or entry.get("owner_skill") != OWNER or entry.get("eligible_for_downstream") is not True:
            errors.append(f"actual post-Canon: Prompt-owned transport artifact missing or ineligible: {artifact_id}")
    return errors


def artifact_ref(value: dict[str, Any]) -> dict[str, Any]:
    return {field: value.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256")}


def validate_preflight_plan(
    root: Path,
    plan: dict[str, Any],
    snapshot: dict[str, Any],
    active: dict[str, dict[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    errors = validate_envelope(plan, "preflight_plan", OWNER)
    if plan.get("schema_version") != "ai-video-generation-unit-preflight.v1":
        errors.append("preflight_plan: wrong schema_version")
    if plan.get("generation_mode") != "omni_reference_to_video":
        errors.append("preflight_plan: wrong generation_mode")
    if plan.get("generation_unit_boundary_policy") != "whole_shot_uids_only":
        errors.append("preflight_plan: generation units may split only at complete Shot UIDs")
    if plan.get("plan_status") not in {
        "ready_for_boundary_supplement", "blocked_conflict", "blocked_capacity",
        "blocked_unsupported_required_modality", "stale",
    }:
        errors.append("preflight_plan: invalid plan_status")
    errors.extend(validate_manifest_receipt(root, plan.get("project_canon_read_receipt"), snapshot, PREFLIGHT_SNAPSHOT, "preflight_plan"))
    ordered = plan.get("ordered_shot_uids")
    if ordered != snapshot.get("canonical_shot_uids"):
        errors.append("preflight_plan: shots must equal preflight manifest canonical order")
        ordered = snapshot.get("canonical_shot_uids", [])
    required_slots = {
        "professional_shot_contract", "global_look_contract", "storyboard_manifest",
        "previs_manifest", "timing_animatic_v1", "keyframe_continuity_manifest",
    }
    slots = {entry.get("artifact_slot") for entry in active.values()}
    missing_slots = required_slots - slots
    if missing_slots:
        errors.append(f"preflight_plan: manifest missing core slots {sorted(missing_slots)}")
    dep_ids = {dep.get("artifact_id") for dep in plan.get("dependencies", []) if isinstance(dep, dict)}
    for slot in required_slots - {"previs_manifest"}:
        entry = next((item for item in active.values() if item.get("artifact_slot") == slot), None)
        if entry and entry.get("artifact_id") not in dep_ids:
            errors.append(f"preflight_plan: dependency missing core slot {slot}")
    units = plan.get("generation_units")
    if not isinstance(units, list) or not units:
        errors.append("preflight_plan: generation_units must be non-empty")
        units = []
    flattened: list[str] = []
    unit_ids: set[str] = set()
    for index, unit in enumerate(units):
        label = f"preflight_plan.units[{index}]"
        if not isinstance(unit, dict):
            errors.append(f"{label}: must be an object")
            continue
        unit_id = unit.get("generation_unit_id")
        shots = unit.get("ordered_shot_uids")
        if not isinstance(unit_id, str) or not unit_id or unit_id in unit_ids:
            errors.append(f"{label}: generation_unit_id must be unique")
        else:
            unit_ids.add(unit_id)
        if not isinstance(shots, list) or not shots or not all(isinstance(item, str) for item in shots):
            errors.append(f"{label}: ordered_shot_uids required")
            shots = []
        flattened.extend(shots)
        duration = unit.get("target_duration_seconds")
        if not is_number(duration) or float(duration) <= 0:
            errors.append(f"{label}: target duration invalid")
        requirement = unit.get("control_previs_requirement")
        timing_sensitive = unit.get("timing_sensitive")
        required_modalities = unit.get("required_modalities")
        if not isinstance(required_modalities, list):
            errors.append(f"{label}: required_modalities must be an array")
            required_modalities = []
        must_have_v2 = len(shots) > 1 or timing_sensitive is True
        if must_have_v2 and (requirement != "required" or "video" not in required_modalities):
            errors.append(f"{label}: multi-shot/timing-sensitive unit requires Control Previs video")
        if requirement == "exempt_single_static_shot":
            if len(ordered) != 1 or len(units) != 1 or len(shots) != 1 or timing_sensitive is not False or "video" in required_modalities:
                errors.append(f"{label}: invalid single-static-shot exemption")
        counts = unit.get("planned_reference_counts")
        if not isinstance(counts, dict):
            errors.append(f"{label}: planned_reference_counts required")
        elif counts.get("total_multimodal") != sum(counts.get(key, 0) for key in ("image", "video", "audio")):
            errors.append(f"{label}: planned reference counts inconsistent")
    if flattened != ordered:
        errors.append("preflight_plan: units must preserve exact shot order")
    if plan.get("affected_shot_uids") != ordered:
        errors.append("preflight_plan: affected_shot_uids must equal canonical shots")
    return errors, units


PREFLIGHT_REQUIRED_GLOBAL_SLOTS = {
    "professional_shot_contract", "global_look_contract", "storyboard_manifest",
    "previs_manifest", "timing_animatic_v1", "keyframe_continuity_manifest",
    "model_capability", "provider_capability",
}
PREFLIGHT_USED_DECISIONS = {
    "selected_direct", "transported_via_atlas_planned", "inline_text",
}
PREFLIGHT_VISUAL_TYPE_TOKENS = (
    "CHARACTER_ASSET", "PRODUCT_ASSET", "PACKAGING_ASSET", "MATERIAL_ASSET", "SCENE_ASSET",
    "GLOBAL_LOOK_REFERENCE", "STORYBOARD_FRAME", "KEYFRAME_ANCHOR", "ASSET_BOARD",
    "ENVIRONMENT_PLATE", "IMAGE_REFERENCE",
)
PREFLIGHT_VISUAL_SLOT_PREFIXES = (
    "character:", "product:", "packaging:", "material:", "scene:",
    "global_look_reference", "storyboard_frame:", "keyframe:",
)
PREFLIGHT_AUDIO_TYPE_TOKENS = (
    "AUDIO_REFERENCE", "DIALOGUE_AUDIO", "VOICE_AUDIO", "SFX_AUDIO", "SYNCHRONOUS_SFX",
)
PREFLIGHT_VIDEO_TYPE_TOKENS = (
    "VIDEO_REFERENCE", "MOTION_REFERENCE", "CAMERA_REFERENCE_VIDEO", "BLOCKING_REFERENCE_VIDEO",
)
PREFLIGHT_AUDIO_SLOT_PREFIXES = ("audio:", "dialogue_audio:", "voice_audio:", "sfx_audio:")
PREFLIGHT_VIDEO_SLOT_PREFIXES = ("video_reference:", "motion_reference:", "camera_reference_video:")
REGISTERED_ASSET_OWNERS = {
    CASTING_OWNER, CHARACTER_FINAL_OWNER, SINGLE_FACE_OWNER, MULTI_ANGLE_OWNER,
    PACKAGING_OWNER, MATERIAL_OWNER, SCENE_OWNER,
}
SOURCE_CODEC_MEDIA_TYPES = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}


def validate_image_properties(
    *, media_type: Any, file_bytes: Any, width: Any, height: Any,
    constraints: Any, label: str,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(constraints, dict):
        return [f"{label}: verified provider image upload constraints are missing"]
    if media_type not in set(constraints.get("accepted_media_types", [])):
        errors.append(f"{label}: image media type is not accepted by the provider")
    if not isinstance(file_bytes, int) or isinstance(file_bytes, bool) or file_bytes < 1:
        errors.append(f"{label}: image file byte size is invalid")
    elif not isinstance(constraints.get("max_file_bytes"), int) or file_bytes > constraints["max_file_bytes"]:
        errors.append(f"{label}: image file exceeds provider max_file_bytes")
    if not isinstance(width, int) or isinstance(width, bool) or not isinstance(height, int) or isinstance(height, bool) or width < 1 or height < 1:
        return errors + [f"{label}: image dimensions are invalid"]
    for value, minimum_key, maximum_key, dimension in (
        (width, "min_width_px", "max_width_px", "width"),
        (height, "min_height_px", "max_height_px", "height"),
    ):
        if not is_number(constraints.get(minimum_key)) or not is_number(constraints.get(maximum_key)):
            errors.append(f"{label}: provider {dimension} constraints are unknown")
        elif value < float(constraints[minimum_key]) or value > float(constraints[maximum_key]):
            errors.append(f"{label}: image {dimension} is outside provider constraints")
    aspect = width / height
    if not is_number(constraints.get("min_aspect_ratio")) or not is_number(constraints.get("max_aspect_ratio")):
        errors.append(f"{label}: provider aspect-ratio constraints are unknown")
    elif aspect < float(constraints["min_aspect_ratio"]) or aspect > float(constraints["max_aspect_ratio"]):
        errors.append(f"{label}: image aspect ratio is outside provider constraints")
    return errors


def validate_image_file_for_provider(
    root: Path, file_path: Any, file_sha256: Any, constraints: Any, label: str,
) -> list[str]:
    path, value, errors = read_hash_locked_file(root, file_path, file_sha256, label)
    if path is None or value is None:
        return errors
    try:
        decoded = decode_common_raster(path, (0, 0, 0))
    except (OSError, ValueError, TypeError) as exc:
        return errors + [f"{label}: provider image preflight decode failed: {exc}"]
    errors.extend(validate_image_properties(
        media_type=SOURCE_CODEC_MEDIA_TYPES.get(decoded.get("source_codec")),
        file_bytes=len(value), width=decoded.get("normalized_width"), height=decoded.get("normalized_height"),
        constraints=constraints, label=label,
    ))
    return errors


def parse_frame_rate(value: Any) -> float | None:
    if not isinstance(value, str) or "/" not in value:
        return None
    numerator, denominator = value.split("/", 1)
    try:
        rate = float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        return None
    return rate if math.isfinite(rate) and rate > 0 else None


def validate_video_item_for_provider(
    root: Path, item: dict[str, Any], constraints: Any, label: str,
) -> list[str]:
    if not isinstance(constraints, dict):
        return [f"{label}: verified provider video upload constraints are missing"]
    artifact = item.get("artifact") if isinstance(item.get("artifact"), dict) else {}
    path, data, errors = read_hash_locked_file(root, artifact.get("file_path"), artifact.get("file_sha256"), label)
    record, record_errors = read_hash_locked_json(
        root, artifact.get("artifact_record_locator"), artifact.get("artifact_record_file_sha256"), f"{label}/record"
    )
    errors.extend(record_errors)
    if path is None or data is None or record is None:
        return errors
    probe = record.get("media_probe") if isinstance(record.get("media_probe"), dict) else None
    if probe is None:
        return errors + [f"{label}: owner-verified ffprobe media evidence is required"]
    try:
        live_probe = probe_media(path)
    except MediaProbeError as exc:
        return errors + [f"{label}: live ffprobe provider preflight failed closed: {exc}"]
    for field in (
        "probe_contract_version", "container_format", "media_type", "video_codec",
        "width_pixels", "height_pixels", "frame_rate", "video_stream_count", "audio_stream_count",
    ):
        if probe.get(field) != live_probe.get(field):
            errors.append(f"{label}: stored media probe {field} differs from live file")
    if (
        not is_number(probe.get("duration_seconds"))
        or not is_number(live_probe.get("duration_seconds"))
        or abs(float(probe["duration_seconds"]) - float(live_probe["duration_seconds"])) > TIME_TOLERANCE
    ):
        errors.append(f"{label}: stored media probe duration differs from live file")
    probe = live_probe
    if probe.get("media_type") not in set(constraints.get("accepted_media_types", [])):
        errors.append(f"{label}: video media type is not accepted by the provider")
    format_tokens = set(str(probe.get("container_format", "")).lower().split(","))
    if not format_tokens & {str(value).lower() for value in constraints.get("accepted_containers", [])}:
        errors.append(f"{label}: video container is not accepted by the provider")
    if probe.get("video_codec") not in set(constraints.get("accepted_video_codecs", [])):
        errors.append(f"{label}: video codec is not accepted by the provider")
    if not isinstance(constraints.get("max_file_bytes"), int) or len(data) > constraints["max_file_bytes"]:
        errors.append(f"{label}: video file exceeds provider max_file_bytes")
    for value, minimum_key, maximum_key, dimension in (
        (probe.get("duration_seconds"), "min_duration_seconds", "max_duration_seconds", "duration"),
        (probe.get("width_pixels"), "min_width_px", "max_width_px", "width"),
        (probe.get("height_pixels"), "min_height_px", "max_height_px", "height"),
    ):
        if not is_number(value) or not is_number(constraints.get(minimum_key)) or not is_number(constraints.get(maximum_key)):
            errors.append(f"{label}: video {dimension} constraint/probe is invalid")
        elif float(value) < float(constraints[minimum_key]) or float(value) > float(constraints[maximum_key]):
            errors.append(f"{label}: video {dimension} is outside provider constraints")
    width = probe.get("width_pixels")
    height = probe.get("height_pixels")
    if not is_number(width) or not is_number(height) or float(height) <= 0:
        errors.append(f"{label}: video aspect ratio cannot be derived")
    else:
        aspect = float(width) / float(height)
        if not is_number(constraints.get("min_aspect_ratio")) or not is_number(constraints.get("max_aspect_ratio")):
            errors.append(f"{label}: provider video aspect-ratio constraints are unknown")
        elif aspect < float(constraints["min_aspect_ratio"]) or aspect > float(constraints["max_aspect_ratio"]):
            errors.append(f"{label}: video aspect ratio is outside provider constraints")
    fps = parse_frame_rate(probe.get("frame_rate"))
    if fps is None or not is_number(constraints.get("min_fps")) or not is_number(constraints.get("max_fps")):
        errors.append(f"{label}: video fps constraint/probe is invalid")
    elif fps < float(constraints["min_fps"]) or fps > float(constraints["max_fps"]):
        errors.append(f"{label}: video fps is outside provider constraints")
    audio_streams = probe.get("audio_stream_count")
    policy = constraints.get("audio_track_policy")
    if policy == "forbidden" and audio_streams != 0:
        errors.append(f"{label}: provider forbids an audio track on the control video")
    elif policy == "required" and (not isinstance(audio_streams, int) or audio_streams < 1):
        errors.append(f"{label}: provider requires an audio track on the control video")
    return errors


def validate_audio_file_for_provider(
    root: Path, file_path: Any, file_sha256: Any, constraints: Any, label: str,
) -> list[str]:
    if not isinstance(constraints, dict):
        return [f"{label}: verified provider audio upload constraints are missing"]
    path, data, errors = read_hash_locked_file(root, file_path, file_sha256, label)
    if path is None or data is None:
        return errors
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        return errors + [f"{label}: ffprobe is required for actual audio provider preflight"]
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_format", "-show_streams", "-print_format", "json", str(path)],
            check=True, capture_output=True, text=True, timeout=120,
        )
        raw = json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return errors + [f"{label}: live ffprobe audio preflight failed closed: {exc}"]
    streams = raw.get("streams") if isinstance(raw.get("streams"), list) else []
    audio_streams = [item for item in streams if isinstance(item, dict) and item.get("codec_type") == "audio"]
    video_streams = [item for item in streams if isinstance(item, dict) and item.get("codec_type") == "video"]
    if len(audio_streams) != 1 or video_streams:
        return errors + [f"{label}: provider audio input must contain exactly one audio stream and no video stream"]
    stream = audio_streams[0]
    format_record = raw.get("format") if isinstance(raw.get("format"), dict) else {}
    format_tokens = set(str(format_record.get("format_name", "")).lower().split(","))
    if "wav" in format_tokens:
        media_type = "audio/wav"
    elif "mp3" in format_tokens:
        media_type = "audio/mpeg"
    else:
        media_type = None
    if media_type not in set(constraints.get("accepted_media_types", [])):
        errors.append(f"{label}: audio media type is not accepted by the provider")
    if stream.get("codec_name") not in set(constraints.get("accepted_audio_codecs", [])):
        errors.append(f"{label}: audio codec is not accepted by the provider")
    if not isinstance(constraints.get("max_file_bytes"), int) or len(data) > constraints["max_file_bytes"]:
        errors.append(f"{label}: audio file exceeds provider max_file_bytes")
    duration_raw = format_record.get("duration", stream.get("duration"))
    try:
        duration = float(duration_raw)
    except (TypeError, ValueError):
        duration = math.nan
    if not math.isfinite(duration) or not is_number(constraints.get("max_duration_seconds")) or duration > float(constraints["max_duration_seconds"]):
        errors.append(f"{label}: audio duration is invalid or exceeds provider constraints")
    channels = stream.get("channels")
    if not isinstance(channels, int) or not isinstance(constraints.get("min_channels"), int) or not isinstance(constraints.get("max_channels"), int) or channels < constraints["min_channels"] or channels > constraints["max_channels"]:
        errors.append(f"{label}: audio channel count is outside provider constraints")
    try:
        sample_rate = int(stream.get("sample_rate"))
    except (TypeError, ValueError):
        sample_rate = 0
    if not isinstance(constraints.get("min_sample_rate_hz"), int) or not isinstance(constraints.get("max_sample_rate_hz"), int) or sample_rate < constraints["min_sample_rate_hz"] or sample_rate > constraints["max_sample_rate_hz"]:
        errors.append(f"{label}: audio sample rate is outside provider constraints")
    return errors


def preflight_requires_visual_transport(entry: dict[str, Any]) -> bool:
    artifact_type = str(entry.get("artifact_type", "")).upper()
    artifact_slot = str(entry.get("artifact_slot", "")).lower()
    return entry.get("owner_skill") in REGISTERED_ASSET_OWNERS or any(
        token in artifact_type for token in PREFLIGHT_VISUAL_TYPE_TOKENS
    ) or any(
        artifact_slot.startswith(prefix) for prefix in PREFLIGHT_VISUAL_SLOT_PREFIXES
    )


def preflight_required_binary_modality(entry: dict[str, Any]) -> str | None:
    """Return source media that cannot be truthfully collapsed into inline text."""
    artifact_type = str(entry.get("artifact_type", "")).upper()
    artifact_slot = str(entry.get("artifact_slot", "")).lower()
    if artifact_slot in {"timing_animatic_v1", "previs_manifest"} or artifact_type in {
        "TIMING_ANIMATIC_V1_MEDIA", "PREVIS_MANIFEST",
    }:
        return None
    if any(token in artifact_type for token in PREFLIGHT_AUDIO_TYPE_TOKENS) or any(
        artifact_slot.startswith(prefix) for prefix in PREFLIGHT_AUDIO_SLOT_PREFIXES
    ):
        return "audio"
    if any(token in artifact_type for token in PREFLIGHT_VIDEO_TYPE_TOKENS) or any(
        artifact_slot.startswith(prefix) for prefix in PREFLIGHT_VIDEO_SLOT_PREFIXES
    ):
        return "video"
    return None


def validate_preflight_decision_matrix(
    plan: dict[str, Any],
    active: dict[str, dict[str, Any]],
    provider: dict[str, Any] | None,
    effective_limits: dict[str, Any],
    fixed_owner_roles: dict[str, list[str]] | None = None,
    project_root: Path | None = None,
) -> list[str]:
    """Validate P1 as a closed all-Canon reference plan before K2/V2 exist."""
    errors: list[str] = []
    active_entries = list(active.values())
    active_ids = [entry.get("artifact_id") for entry in active_entries]
    active_refs = [artifact_ref(entry) for entry in active_entries]

    dependencies = plan.get("dependencies")
    if not isinstance(dependencies, list):
        dependencies = []
    dependency_tuples = [dependency_tuple(item) for item in dependencies]
    expected_dependency_tuples = [dependency_tuple(item) for item in active_refs]
    if any(item is None for item in dependency_tuples):
        errors.append("preflight_plan: every dependency must be a complete artifact ref")
    elif len(dependency_tuples) != len(set(dependency_tuples)):
        errors.append("preflight_plan: dependencies must be unique")
    if set(dependency_tuples) != set(expected_dependency_tuples):
        errors.append("preflight_plan: dependencies must directly lock every preflight Canon active artifact exactly")

    supported_modalities = set(provider.get("supported_modalities", [])) if isinstance(provider, dict) else set()
    provider_input_constraints = provider.get("input_constraints") if isinstance(provider, dict) and isinstance(provider.get("input_constraints"), dict) else {}
    units = plan.get("generation_units") if isinstance(plan.get("generation_units"), list) else []
    any_conflict = False
    all_units_ready = True

    for unit_index, unit in enumerate(units):
        if not isinstance(unit, dict):
            continue
        unit_id = unit.get("generation_unit_id")
        label = f"preflight_plan/{unit_id or unit_index}"
        unit_shots = unit.get("ordered_shot_uids") if isinstance(unit.get("ordered_shot_uids"), list) else []
        unit_shot_set = set(unit_shots)
        decisions = unit.get("artifact_decisions")
        if not isinstance(decisions, list):
            errors.append(f"{label}: artifact_decisions must be an array")
            decisions = []
        decision_ids: list[str] = []
        used_ids: list[str] = []
        direct_counts = {"image": 0, "video": 0, "audio": 0}
        atlas_groups: set[str] = set()
        atlas_sources: dict[str, list[str]] = {}
        decision_by_id: dict[str, dict[str, Any]] = {}
        unit_has_conflict = False

        for decision_index, decision in enumerate(decisions):
            item_label = f"{label}.artifact_decisions[{decision_index}]"
            if not isinstance(decision, dict):
                errors.append(f"{item_label}: must be an object")
                continue
            ref = decision.get("artifact") if isinstance(decision.get("artifact"), dict) else {}
            artifact_id = ref.get("artifact_id")
            if not isinstance(artifact_id, str) or not artifact_id:
                errors.append(f"{item_label}: artifact_id required")
                continue
            decision_ids.append(artifact_id)
            decision_by_id[artifact_id] = decision
            entry = active.get(artifact_id)
            if not isinstance(entry, dict):
                errors.append(f"{item_label}: artifact is not active in the preflight Canon snapshot")
                continue
            if ref != artifact_ref(entry):
                errors.append(f"{item_label}: artifact ref differs from the active Canon identity/version/hash")
            if decision.get("artifact_slot") != entry.get("artifact_slot") or decision.get("artifact_type") != entry.get("artifact_type"):
                errors.append(f"{item_label}: artifact slot/type differs from active Canon")
            controlled = decision.get("controlled_shot_uids")
            if not isinstance(controlled, list) or not set(controlled) <= unit_shot_set:
                errors.append(f"{item_label}: controlled_shot_uids must be a subset of the generation unit")
                controlled = []
            status = decision.get("decision")
            modality = decision.get("transport_modality")
            group_id = decision.get("transport_group_id")
            control_roles = decision.get("control_roles")
            if (
                not isinstance(control_roles, list) or not control_roles
                or len(control_roles) != len(set(control_roles))
                or any(not isinstance(role, str) or not role for role in control_roles)
                or decision.get("control_role") not in control_roles
            ):
                errors.append(f"{item_label}: control_roles must be non-empty unique and contain primary control_role")
                control_roles = []
            if entry.get("owner_skill") in REGISTERED_ASSET_OWNERS and fixed_owner_roles is not None:
                if control_roles != fixed_owner_roles.get(artifact_id):
                    errors.append(f"{item_label}: control_roles must exactly equal the fixed-owner Canon export authorization")
            entry_scope = set(entry.get("affected_shot_uids", []))
            relevant_here = bool(entry_scope & unit_shot_set) or entry.get("artifact_slot") in PREFLIGHT_REQUIRED_GLOBAL_SLOTS
            expected_controlled = [uid for uid in unit_shots if uid in entry_scope]
            if entry.get("artifact_slot") in PREFLIGHT_REQUIRED_GLOBAL_SLOTS:
                expected_controlled = list(unit_shots)
            if status in PREFLIGHT_USED_DECISIONS | {"conflict_blocked"} and controlled != expected_controlled:
                errors.append(f"{item_label}: controlled_shot_uids must exactly equal Canon scope intersected with unit scope")
            if not relevant_here and status != "irrelevant":
                errors.append(f"{item_label}: out-of-scope active artifact must be classified irrelevant")
            if relevant_here and status in {"irrelevant", "superseded"}:
                errors.append(f"{item_label}: relevant active Canon artifact cannot be classified {status}")
            if relevant_here and preflight_requires_visual_transport(entry) and status not in {
                "selected_direct", "transported_via_atlas_planned", "conflict_blocked",
            }:
                errors.append(f"{item_label}: visual control artifact must remain a planned image transport or conflict")
            required_binary_modality = preflight_required_binary_modality(entry)
            if relevant_here and required_binary_modality is not None and status not in {"selected_direct", "conflict_blocked"}:
                errors.append(
                    f"{item_label}: relevant {required_binary_modality} control media must remain selected_direct or conflict, never inline text"
                )
            if status == "selected_direct" and required_binary_modality is not None and modality != required_binary_modality:
                errors.append(f"{item_label}: selected direct media modality differs from Canon media type")
            if status == "superseded":
                errors.append(f"{item_label}: an active Canon artifact cannot be classified superseded")
            if status in PREFLIGHT_USED_DECISIONS:
                used_ids.append(artifact_id)
                if entry.get("eligible_for_downstream") is not True or entry.get("approval_status") not in {"assistant_validated", "user_approved"} or entry.get("stale_reason") is not None:
                    errors.append(f"{item_label}: selected artifact is not downstream-eligible and approved")
            if status == "selected_direct":
                if modality not in direct_counts or group_id is not None or not controlled:
                    errors.append(f"{item_label}: selected_direct requires image/video/audio, no group, and controlled shots")
                else:
                    direct_counts[modality] += 1
                if modality == "image":
                    if project_root is None:
                        errors.append(f"{item_label}: project root is required to inspect a direct image")
                    else:
                        errors.extend(validate_image_file_for_provider(
                            project_root, entry.get("locator"), entry.get("file_sha256"),
                            provider_input_constraints.get("image"), item_label,
                        ))
                elif modality == "video":
                    if project_root is None:
                        errors.append(f"{item_label}: project root is required to inspect a direct video")
                    else:
                        errors.extend(validate_video_item_for_provider(
                            project_root,
                            {"artifact": {
                                "file_path": entry.get("locator"), "file_sha256": entry.get("file_sha256"),
                                "artifact_record_locator": entry.get("artifact_record_locator"),
                                "artifact_record_file_sha256": entry.get("artifact_record_file_sha256"),
                            }},
                            provider_input_constraints.get("video"), item_label,
                        ))
                elif modality == "audio":
                    if project_root is None:
                        errors.append(f"{item_label}: project root is required to inspect direct audio")
                    else:
                        errors.extend(validate_audio_file_for_provider(
                            project_root, entry.get("locator"), entry.get("file_sha256"),
                            provider_input_constraints.get("audio"), item_label,
                        ))
            elif status == "transported_via_atlas_planned":
                if modality != "image" or not isinstance(group_id, str) or not group_id or not controlled:
                    errors.append(f"{item_label}: atlas planning requires image modality, a group ID, and controlled shots")
                else:
                    atlas_groups.add(group_id)
                    atlas_sources.setdefault(group_id, []).append(artifact_id)
                type_and_slot = f"{entry.get('artifact_type', '')} {entry.get('artifact_slot', '')}".upper()
                is_packaging = (
                    entry.get("owner_skill") == "packaging-product-identity-label-lock-board"
                    or "PACKAGING" in type_and_slot
                )
                if "LABEL" in type_and_slot or "MICROCOPY" in type_and_slot or is_packaging or "label_copy" in control_roles:
                    errors.append(f"{item_label}: packaging, label, or microcopy evidence must remain a direct image binding, not an atlas panel")
            elif status == "inline_text":
                if modality != "text" or group_id is not None or not controlled:
                    errors.append(f"{item_label}: inline_text requires text modality, no group, and controlled shots")
            elif status in {"irrelevant", "superseded"}:
                if group_id is not None or controlled:
                    errors.append(f"{item_label}: {status} must not claim transport group or controlled shots")
            elif status == "conflict_blocked":
                unit_has_conflict = True
                any_conflict = True
                if group_id is not None or not controlled:
                    errors.append(f"{item_label}: conflict_blocked requires controlled shots and no transport group")

        if len(decision_ids) != len(set(decision_ids)):
            errors.append(f"{label}: every active Canon artifact must have exactly one decision")
        if set(decision_ids) != set(active_ids) or len(decision_ids) != len(active_ids):
            errors.append(f"{label}: artifact decisions must cover every preflight Canon active artifact exactly")
        planned_ids = unit.get("planned_reference_artifact_ids")
        if planned_ids != used_ids:
            errors.append(f"{label}: planned_reference_artifact_ids must exactly equal used decisions in decision order")

        planned_atlas_groups = unit.get("planned_atlas_groups")
        if not isinstance(planned_atlas_groups, list):
            errors.append(f"{label}: planned_atlas_groups must be an array")
            planned_atlas_groups = []
        group_records = {
            group.get("transport_group_id"): group
            for group in planned_atlas_groups if isinstance(group, dict)
        }
        if len(group_records) != len(planned_atlas_groups) or set(group_records) != atlas_groups:
            errors.append(f"{label}: planned_atlas_groups must exactly equal the decision transport groups")
        for group_id, source_ids in atlas_sources.items():
            group = group_records.get(group_id)
            group_label = f"{label}.planned_atlas_groups/{group_id}"
            if not isinstance(group, dict):
                continue
            if len(source_ids) < 2:
                errors.append(f"{group_label}: deterministic atlas requires at least two source artifacts")
            if group.get("source_artifact_ids") != source_ids:
                errors.append(f"{group_label}: source_artifact_ids must exactly equal decision source order")
            if project_root is None:
                errors.append(f"{group_label}: project root is required to prove atlas realizability")
                continue
            spec = {
                "schema_version": ATLAS_SPEC_VERSION,
                "atlas_id": group.get("planned_atlas_id"),
                "generation_unit_id": unit_id,
                "layout_columns": group.get("layout_columns"),
                "background_rgb": group.get("background_rgb"),
                "minimum_panel_width_pixels": group.get("minimum_panel_width_pixels"),
                "minimum_panel_height_pixels": group.get("minimum_panel_height_pixels"),
                "legibility_policy": group.get("legibility_policy"),
                "source_decode_policy": group.get("source_decode_policy"),
                "output_encode_policy": group.get("output_encode_policy"),
                "layout_policy": group.get("layout_policy"),
                "output_codec": group.get("output_codec"),
                "sources": [{
                    "artifact_id": artifact_id,
                    "file_path": active[artifact_id].get("locator"),
                    "file_sha256": active[artifact_id].get("file_sha256"),
                    "control_roles": decision_by_id[artifact_id].get("control_roles"),
                    "control_role": decision_by_id[artifact_id].get("control_role"),
                } for artifact_id in source_ids],
            }
            try:
                preview_bytes, preview_receipt = build_from_spec(project_root, spec)
            except (OSError, ValueError, TypeError) as exc:
                errors.append(f"{group_label}: deterministic atlas dry-build failed: {exc}")
                continue
            expected_build = {
                "file_sha256": hashlib.sha256(preview_bytes).hexdigest(),
                "file_bytes": len(preview_bytes),
                "width": preview_receipt.get("width"),
                "height": preview_receipt.get("height"),
                "codec": preview_receipt.get("codec"),
                "media_type": preview_receipt.get("media_type"),
                "decoder_runtime": preview_receipt.get("decoder_runtime"),
                "encoder_runtime": preview_receipt.get("encoder_runtime"),
            }
            if group.get("preflight_build") != expected_build:
                errors.append(f"{group_label}: preflight_build must exactly equal the deterministic dry-build receipt projection")
            errors.extend(validate_image_properties(
                media_type=preview_receipt.get("media_type"), file_bytes=len(preview_bytes),
                width=preview_receipt.get("width"), height=preview_receipt.get("height"),
                constraints=provider_input_constraints.get("image"), label=group_label,
            ))

        future_inputs = unit.get("planned_future_inputs")
        if not isinstance(future_inputs, list):
            errors.append(f"{label}: planned_future_inputs must be an array")
            future_inputs = []
        future_ids: list[str] = []
        future_counts = {"image": 0, "video": 0, "audio": 0}
        v2_inputs: list[dict[str, Any]] = []
        k2_supplement_inputs: list[dict[str, Any]] = []
        for future_index, future in enumerate(future_inputs):
            future_label = f"{label}.planned_future_inputs[{future_index}]"
            if not isinstance(future, dict):
                errors.append(f"{future_label}: must be an object")
                continue
            future_id = future.get("planned_input_id")
            if not isinstance(future_id, str) or not future_id:
                errors.append(f"{future_label}: planned_input_id required")
            else:
                future_ids.append(future_id)
            modality = future.get("transport_modality")
            if modality == "text":
                pass
            elif modality not in future_counts:
                errors.append(f"{future_label}: invalid transport modality")
            else:
                future_counts[modality] += 1
            controlled = future.get("controlled_shot_uids")
            if not isinstance(controlled, list) or set(controlled) != unit_shot_set:
                errors.append(f"{future_label}: future control must cover the exact generation-unit Shot UIDs")
            if future.get("control_role") == "control_previs_v2":
                v2_inputs.append(future)
                if future.get("producer_skill") != "ai-video-timed-animatic-previs-director" or modality != "video":
                    errors.append(f"{future_label}: Control Previs V2 must be one Previs-owned video input")
                video_constraints = provider_input_constraints.get("video")
                if not isinstance(video_constraints, dict):
                    errors.append(f"{future_label}: verified provider video upload constraints are required before V2")
                elif (
                    not is_number(video_constraints.get("min_duration_seconds"))
                    or not is_number(video_constraints.get("max_duration_seconds"))
                    or not is_number(unit.get("target_duration_seconds"))
                    or float(unit["target_duration_seconds"]) < float(video_constraints["min_duration_seconds"])
                    or float(unit["target_duration_seconds"]) > float(video_constraints["max_duration_seconds"])
                ):
                    errors.append(f"{future_label}: target duration is outside verified provider video upload constraints")
            elif future.get("control_role") == "keyframe_boundary_supplement":
                k2_supplement_inputs.append(future)
                if future.get("producer_skill") != "ai-video-keyframe-continuity-pack" or modality != "text":
                    errors.append(f"{future_label}: K2 Boundary Supplement must be one Keyframe-owned inline authority")
            elif future.get("control_role") == "keyframe_boundary_anchor":
                if future.get("producer_skill") != "ai-video-keyframe-continuity-pack" or modality != "image":
                    errors.append(f"{future_label}: boundary anchor must be one Keyframe-owned image input")
        if len(future_ids) != len(set(future_ids)):
            errors.append(f"{label}: planned future input IDs must be unique")
        if len(k2_supplement_inputs) != 1:
            errors.append(f"{label}: every ready unit must reserve exactly one future K2 Boundary Supplement authority")
        if unit.get("control_previs_requirement") == "required":
            if len(v2_inputs) != 1:
                errors.append(f"{label}: required Control Previs must reserve exactly one future V2 video input")
        elif v2_inputs:
            errors.append(f"{label}: single-static-shot exemption cannot reserve a V2 input")

        derived = {
            "image": direct_counts["image"] + len(atlas_groups) + future_counts["image"],
            "video": direct_counts["video"] + future_counts["video"],
            "audio": direct_counts["audio"] + future_counts["audio"],
        }
        derived["total_multimodal"] = derived["image"] + derived["video"] + derived["audio"]
        if unit.get("planned_reference_counts") != derived:
            errors.append(f"{label}: planned_reference_counts must be derived exactly from decisions, atlas groups, and future inputs")

        for modality, limit_key in (
            ("image", "max_image_inputs"), ("video", "max_video_inputs"), ("audio", "max_audio_inputs")
        ):
            if derived[modality] > 0 and modality not in supported_modalities:
                errors.append(f"{label}: planned {modality} input is unsupported by the selected provider")
            limit = effective_limits.get(limit_key)
            if not is_number(limit) or derived[modality] > float(limit):
                errors.append(f"{label}: planned {modality} count exceeds effective provider/backend capacity")
            if modality in set(unit.get("required_modalities", [])) and derived[modality] < 1:
                errors.append(f"{label}: required modality {modality} has no planned input")
        total_limit = effective_limits.get("max_total_multimodal_inputs")
        if not is_number(total_limit) or derived["total_multimodal"] > float(total_limit):
            errors.append(f"{label}: planned total count exceeds effective provider/backend capacity")
        duration_limit = effective_limits.get("max_duration_seconds")
        if not is_number(duration_limit) or not is_number(unit.get("target_duration_seconds")) or float(unit["target_duration_seconds"]) > float(duration_limit) + TIME_TOLERANCE:
            errors.append(f"{label}: target duration exceeds effective provider/backend capacity")
        if not set(unit.get("required_modalities", [])) <= supported_modalities:
            errors.append(f"{label}: required modalities exceed the selected provider surface")
        if "text" not in set(unit.get("required_modalities", [])):
            errors.append(f"{label}: every generation unit requires text prompt modality")
        if unit_has_conflict:
            if unit.get("preflight_status") != "blocked_conflict":
                errors.append(f"{label}: conflict decisions require blocked_conflict status")
        elif unit.get("preflight_status") != "ready":
            all_units_ready = False

    if all_units_ready and not any_conflict:
        if plan.get("plan_status") != "ready_for_boundary_supplement":
            errors.append("preflight_plan: all ready units require ready_for_boundary_supplement")
        if plan.get("approval_status") not in {"assistant_validated", "user_approved"} or plan.get("stale_reason") is not None:
            errors.append("preflight_plan: ready P1 must be approved or assistant-validated and non-stale")
        if plan.get("blocked_reasons") != []:
            errors.append("preflight_plan: ready P1 must not retain blocked reasons")
    elif any_conflict and plan.get("plan_status") != "blocked_conflict":
        errors.append("preflight_plan: conflict decisions require blocked_conflict plan status")
    return errors


def source_inventory_tuple(item: dict[str, Any]) -> tuple[Any, ...]:
    artifact = item.get("artifact") if isinstance(item, dict) else {}
    return (
        artifact.get("artifact_id"), artifact.get("owner_skill"), artifact.get("version"), artifact.get("sha256"),
        item.get("file_path"), item.get("file_sha256"), item.get("artifact_record_locator"), item.get("artifact_record_file_sha256"),
    )


def manifest_entry_tuple(entry: dict[str, Any]) -> tuple[Any, ...]:
    return (
        entry.get("artifact_id"), entry.get("owner_skill"), entry.get("version"), entry.get("sha256"),
        entry.get("locator"), entry.get("file_sha256"), entry.get("artifact_record_locator"), entry.get("artifact_record_file_sha256"),
    )


def manifest_entries_as_inventory(entries: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        artifact_id: {
            "artifact": {
                "contract_version": "ai-video-artifact-v1", "artifact_id": entry.get("artifact_id"),
                "owner_skill": entry.get("owner_skill"), "version": entry.get("version"),
                "sha256": entry.get("sha256"), "approval_status": entry.get("approval_status"),
                "dependencies": entry.get("dependencies"), "affected_shot_uids": entry.get("affected_shot_uids"),
                "stale_reason": entry.get("stale_reason"),
            },
            "artifact_slot": entry.get("artifact_slot"), "artifact_type": entry.get("artifact_type"),
            "approval_status": entry.get("approval_status"), "eligible_for_downstream": entry.get("eligible_for_downstream"),
            "file_path": entry.get("locator"), "file_sha256": entry.get("file_sha256"),
            "artifact_record_locator": entry.get("artifact_record_locator"),
            "artifact_record_file_sha256": entry.get("artifact_record_file_sha256"),
        }
        for artifact_id, entry in entries.items()
    }


def compact_semantic_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def load_original_authority(
    root: Path,
    inventory: dict[str, dict[str, Any]],
    slot: str,
    expected_owner: str,
    expected_schema_version: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Read the owner artifact named by the active Canon entry; projections are forbidden."""
    matches = [item for item in inventory.values() if item.get("artifact_slot") == slot]
    if len(matches) != 1:
        return None, [f"upstream authority/{slot}: exactly one active artifact required"]
    item = matches[0]
    value, errors = read_hash_locked_json(
        root, item.get("artifact_record_locator"), item.get("artifact_record_file_sha256"), f"upstream authority/{slot} record"
    )
    if value is None:
        return None, errors
    artifact = item.get("artifact") if isinstance(item.get("artifact"), dict) else {}
    errors.extend(validate_envelope(value, f"upstream authority/{slot}", expected_owner))
    for field in (
        "contract_version", "artifact_id", "owner_skill", "version", "sha256", "approval_status",
        "dependencies", "affected_shot_uids", "stale_reason",
    ):
        if value.get(field) != artifact.get(field):
            errors.append(f"upstream authority/{slot}: original artifact {field} differs from active Canon entry")
    if value.get("schema_version") != expected_schema_version:
        errors.append(f"upstream authority/{slot}: expected original schema {expected_schema_version}")
    errors.extend(
        f"upstream authority/{slot}: input contract: {item}"
        for item in validate_owner_input(value, expected_owner, expected_schema_version)
    )
    if value.get("schema_version") == "ai-video-upstream-authority-projection.v1" or "authority_artifact_ref" in value:
        errors.append(f"upstream authority/{slot}: Prompt-made authority projection is forbidden")
    return value, errors


def copy_status_for_ir(value: Any) -> str:
    return {
        "not_used": "not_used",
        "supplied_exact": "supplied_exact",
        "source_supported_claim": "supplied_exact",
        "provisional_nonclaim": "supplied_provisional",
    }.get(value, "unsourced_prohibited")


def copy_item_for_ir(value: Any, delivery_mode: str) -> dict[str, Any]:
    value = value if isinstance(value, dict) else {}
    return {
        "text": value.get("text", ""),
        "copy_status": copy_status_for_ir(value.get("copy_status")),
        "source_reference_ids": value.get("source_reference_ids", []),
        "claim_ids": value.get("claim_ids", []),
        "delivery_mode": delivery_mode,
    }


def shot_contract_projection(source: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    claims = source.get("claim_boundary") if isinstance(source.get("claim_boundary"), dict) else {}
    used_claim_ids = set(claims.get("used_claim_ids", []))
    claim_records = [
        {
            "claim_id": item.get("claim_id"), "text": item.get("text"),
            "source_reference_ids": item.get("source_reference_ids"), "usage": "used_source_supported",
        }
        for item in claims.get("supplied_claims", [])
        if isinstance(item, dict) and item.get("claim_id") in used_claim_ids
    ]
    claim_by_id = {item["claim_id"]: item for item in claim_records}
    cursor = 0.0
    projected: list[dict[str, Any]] = []
    for item in source.get("shots", []) if isinstance(source.get("shots"), list) else []:
        if not isinstance(item, dict):
            continue
        duration = item.get("target_duration_seconds")
        end = cursor + float(duration) if is_number(duration) else cursor
        spoken_mode = "model_spoken" if item.get("spoken_content", {}).get("mode") in {"voiceover", "dialogue"} else "prohibited_model_text"
        spoken = copy_item_for_ir(item.get("spoken_content"), spoken_mode)
        screen_copy = [copy_item_for_ir(value, "external_overlay_handoff") for value in item.get("on_screen_copy", []) if isinstance(value, dict)]
        shot_claim_ids = set(spoken.get("claim_ids", []))
        for copy_item in screen_copy:
            shot_claim_ids.update(copy_item.get("claim_ids", []))
        projected.append({
            "shot_uid": item.get("shot_uid"),
            "target_start_seconds": cursor,
            "target_end_seconds": end,
            "advertising_function": item.get("advertising_function"),
            "subjects": item.get("subjects"),
            "scene_initial_state": compact_semantic_json({"scene": item.get("scene"), "initial_state": item.get("initial_state")}),
            "visible_action_expression": compact_semantic_json({
                "action_path": item.get("action_path"), "visible_emotional_expression": item.get("visible_emotional_expression"),
            }),
            "camera_composition": compact_semantic_json({field: item.get(field) for field in (
                "shot_size", "camera_height", "camera_angle", "lens_intent", "composition",
                "subject_placement", "primary_camera_movement", "focus_behavior",
            )}),
            "blocking_spatial_change": compact_semantic_json({
                "blocking": item.get("blocking"), "screen_direction": item.get("screen_direction"),
                "continuity_in": item.get("continuity_in"),
            }),
            "ending_continuity_state": compact_semantic_json({
                "ending_state": item.get("ending_state"), "continuity_out": item.get("continuity_out"),
                "cut_motivation": item.get("cut_motivation"), "transition_intent": item.get("transition_intent"),
            }),
            "spoken_content": spoken,
            "on_screen_copy": screen_copy,
            "claim_provenance": [claim_by_id[claim_id] for claim_id in sorted(shot_claim_ids) if claim_id in claim_by_id],
            "must_preserve": item.get("must_preserve"),
            "must_avoid": item.get("must_avoid"),
        })
        cursor = end
    return projected, {
        "claims": claim_records,
        "prohibited_unsourced_claims": claims.get("prohibited_unsourced_claims", []),
        "compliance_unknowns": claims.get("compliance_unknowns", []),
    }


def validate_upstream_semantics(
    root: Path,
    ir: dict[str, Any],
    inventory: dict[str, dict[str, Any]],
    plan: dict[str, Any],
    preflight_active: dict[str, dict[str, Any]],
    canon_snapshot: dict[str, Any],
) -> list[str]:
    """Project the IR from original owner JSON named by active Canon entries."""
    errors: list[str] = []
    for artifact_id, item in inventory.items():
        file_path, file_sha = item.get("file_path"), item.get("file_sha256")
        if (file_path is None) != (file_sha is None):
            errors.append(f"upstream file/{artifact_id}: file_path and file_sha256 must both be null or present")
        elif file_path is not None:
            _, _, file_errors = read_hash_locked_file(root, file_path, file_sha, f"upstream file/{artifact_id}")
            errors.extend(file_errors)
        record_path, record_sha = item.get("artifact_record_locator"), item.get("artifact_record_file_sha256")
        if not isinstance(record_path, str) or not is_hash(record_sha):
            errors.append(f"upstream record/{artifact_id}: artifact record locator/hash required")
        else:
            record, record_errors = read_hash_locked_json(root, record_path, record_sha, f"upstream record/{artifact_id}")
            errors.extend(record_errors)
            if record is not None:
                source_artifact = item.get("artifact") if isinstance(item.get("artifact"), dict) else {}
                errors.extend(validate_envelope(record, f"upstream record/{artifact_id}", source_artifact.get("owner_skill")))
                if source_artifact.get("owner_skill") in REGISTERED_ASSET_OWNERS:
                    errors.extend(
                        f"upstream record/{artifact_id}: {item}"
                        for item in validate_owner_asset_export(record, root)
                    )
                for field in (
                    "contract_version", "artifact_id", "owner_skill", "version", "sha256",
                    "dependencies", "affected_shot_uids",
                ):
                    if record.get(field) != source_artifact.get(field):
                        errors.append(f"upstream record/{artifact_id}: {field} differs from Canon inventory")
                status_matches = (
                    record.get("approval_status") == source_artifact.get("approval_status")
                    and record.get("stale_reason") == source_artifact.get("stale_reason")
                )
                if not status_matches:
                    overlay_allowed = (
                        record.get("approval_status") in {"assistant_validated", "user_approved"}
                        and record.get("stale_reason") is None
                        and source_artifact.get("approval_status") in {"stale", "blocked"}
                        and item.get("eligible_for_downstream") is False
                        and isinstance(source_artifact.get("stale_reason"), str)
                        and bool(source_artifact["stale_reason"].strip())
                    )
                    matching_events = [
                        event for event in canon_snapshot.get("stale_events", [])
                        if isinstance(event, dict)
                        and artifact_id in event.get("stale_artifact_ids", [])
                        and event.get("affected_shot_uids") == source_artifact.get("affected_shot_uids")
                        and event.get("reason") == source_artifact.get("stale_reason")
                    ]
                    if not overlay_allowed or len(matching_events) != 1:
                        errors.append(
                            f"upstream record/{artifact_id}: status differs without one exact event-bound Canon stale overlay"
                        )

    shot_source, shot_errors = load_original_authority(
        root, inventory, "professional_shot_contract", "ai-video-shot-script-director", "ai-video-shot-contract.v1"
    )
    errors.extend(shot_errors)
    shot_projection: dict[str, dict[str, Any]] = {}
    if shot_source is not None:
        source_shots, source_claim_boundary = shot_contract_projection(shot_source)
        source_uids = [item.get("shot_uid") for item in source_shots]
        shot_projection = {item.get("shot_uid"): item for item in source_shots if isinstance(item.get("shot_uid"), str)}
        if source_uids != ir.get("ordered_shot_uids") or len(shot_projection) != len(source_shots):
            errors.append("IR semantic lock: shot order differs from Shot Contract file")
        timeline = shot_source.get("timeline") if isinstance(shot_source.get("timeline"), dict) else {}
        if timeline.get("shot_count") != len(source_shots) or not close(timeline.get("total_duration_seconds"), source_shots[-1].get("target_end_seconds") if source_shots else None):
            errors.append("upstream authority/professional_shot_contract: timeline does not close projected shot windows")
        if shot_source.get("global_directing_prompt_full") != ir.get("global_directing_prompt_full"):
            errors.append("IR semantic lock: Global Directing differs from Shot Contract file")
        if source_claim_boundary != ir.get("claim_boundary"):
            errors.append("IR semantic lock: claim boundary differs from Shot Contract file")
        for shot in ir.get("shots", []) if isinstance(ir.get("shots"), list) else []:
            if not isinstance(shot, dict):
                continue
            uid = shot.get("shot_uid")
            source = shot_projection.get(uid)
            expected = {field: shot.get(field) for field in source} if isinstance(source, dict) else None
            if source is None or source != expected:
                errors.append(f"IR semantic lock/{uid}: action/camera/timing/copy/claim facts differ from Shot Contract file")

    look_source, look_errors = load_original_authority(
        root, inventory, "global_look_contract", "ai-video-global-look-lock", "ai-video-global-look.v1"
    )
    errors.extend(look_errors)
    look_by_shot: dict[str, dict[str, Any]] = {}
    if look_source is not None:
        look_states = {
            item.get("state_id"): item for item in look_source.get("look_states", []) if isinstance(item, dict)
        }
        reference_id_to_artifact_id: dict[str, str] = {}
        references: list[str] = []
        for reference in look_source.get("look_reference_set", []) if isinstance(look_source.get("look_reference_set"), list) else []:
            if not isinstance(reference, dict):
                continue
            nested = reference.get("artifact") if isinstance(reference.get("artifact"), dict) else {}
            errors.extend(validate_envelope(nested, f"Global Look reference/{reference.get('reference_id')}", "ai-video-global-look-lock"))
            artifact_id = nested.get("artifact_id")
            if isinstance(reference.get("reference_id"), str) and isinstance(artifact_id, str):
                reference_id_to_artifact_id[reference["reference_id"]] = artifact_id
                references.append(artifact_id)
            canon_item = inventory.get(artifact_id, {})
            if canon_item.get("artifact") != nested or canon_item.get("file_path") != reference.get("locator") or canon_item.get("file_sha256") != reference.get("file_sha256"):
                errors.append(f"IR semantic lock: Global Look nested reference differs from active Canon asset: {reference.get('reference_id')}")
        expected_global_look = {
            "artifact_id": look_source.get("artifact_id"),
            "exact_prompt_block": look_source.get("global_look_prompt_full"),
            "reference_asset_ids": references,
            "look_state_matrix_id": look_source.get("look_state_matrix_id"),
        }
        if expected_global_look != ir.get("global_look"):
            errors.append("IR semantic lock: Global Look Core/reference/matrix differs from Global Look file")
        for assignment in look_source.get("shot_look_assignments", []) if isinstance(look_source.get("shot_look_assignments"), list) else []:
            if not isinstance(assignment, dict):
                continue
            state = look_states.get(assignment.get("state_id"), {})
            delta = assignment.get("shot_look_delta") if isinstance(assignment.get("shot_look_delta"), dict) else {}
            look_by_shot[assignment.get("shot_uid")] = {
                "look_state_id": assignment.get("state_id"),
                "look_state_prompt_full": state.get("state_prompt_full"),
                "look_state_reference_asset_ids": [reference_id_to_artifact_id.get(value) for value in state.get("reference_ids", [])],
                "shot_look_delta": {
                    "active": delta.get("active"), "scope": delta.get("scope"),
                    "description": delta.get("description"), "reason": delta.get("reason"),
                    "preserves_look_core": delta.get("preserves_look_core"),
                    "prompt_full": assignment.get("shot_look_delta_prompt_full"),
                },
            }
        for shot in ir.get("shots", []) if isinstance(ir.get("shots"), list) else []:
            if not isinstance(shot, dict):
                continue
            expected = {
                "look_state_id": shot.get("look_state_id"),
                "look_state_prompt_full": shot.get("look_state_prompt_full"),
                "look_state_reference_asset_ids": shot.get("look_state_reference_asset_ids"),
                "shot_look_delta": shot.get("shot_look_delta"),
            }
            if look_by_shot.get(shot.get("shot_uid")) != expected:
                errors.append(f"IR semantic lock/{shot.get('shot_uid')}: State/Delta differs from Global Look file")

    storyboard_source, storyboard_errors = load_original_authority(
        root, inventory, "storyboard_manifest", "ai-video-modular-storyboard", "ai-video-modular-storyboard.v1"
    )
    errors.extend(storyboard_errors)
    if storyboard_source is not None:
        frames = storyboard_source.get("frames")
        frame_by_uid = {item.get("shot_uid"): item for item in frames if isinstance(item, dict)} if isinstance(frames, list) else {}
        for shot in ir.get("shots", []) if isinstance(ir.get("shots"), list) else []:
            if not isinstance(shot, dict):
                continue
            source_frame = frame_by_uid.get(shot.get("shot_uid"))
            expected = {
                "artifact_id": shot.get("storyboard_artifact_id"), "stage": shot.get("storyboard_stage"),
                "is_model_input_eligible": shot.get("storyboard_model_input_eligible"),
                "global_directing_prompt_full": ir.get("global_directing_prompt_full"),
                "global_look_prompt_full": ir.get("global_look", {}).get("exact_prompt_block"),
                "look_state_id": shot.get("look_state_id"), "look_state_prompt_full": shot.get("look_state_prompt_full"),
                "shot_look_delta_prompt_full": shot.get("shot_look_delta", {}).get("prompt_full"),
                "look_reference_asset_ids": shot.get("look_state_reference_asset_ids"),
            }
            actual = {field: source_frame.get(field) for field in expected} if isinstance(source_frame, dict) else None
            if actual != expected:
                errors.append(f"IR semantic lock/{shot.get('shot_uid')}: storyboard fact differs from Storyboard file")
            if isinstance(source_frame, dict):
                errors.extend(validate_envelope(source_frame, f"Storyboard frame/{shot.get('shot_uid')}", "ai-video-modular-storyboard"))
                frame_item = inventory.get(source_frame.get("artifact_id"), {})
                if frame_item.get("artifact") != {field: source_frame.get(field) for field in (
                    "contract_version", "artifact_id", "owner_skill", "version", "sha256", "approval_status",
                    "dependencies", "affected_shot_uids", "stale_reason",
                )} or frame_item.get("file_path") != source_frame.get("file_path") or frame_item.get("file_sha256") != source_frame.get("file_sha256"):
                    errors.append(f"IR semantic lock/{shot.get('shot_uid')}: Storyboard nested frame differs from active Canon frame")

    keyframe_source, keyframe_errors = load_original_authority(
        root, inventory, "keyframe_continuity_manifest", "ai-video-keyframe-continuity-pack", "ai-video-keyframe-continuity-pack.v1"
    )
    errors.extend(keyframe_errors)
    k1_ids_by_shot: dict[str, list[str]] = {}
    if keyframe_source is not None:
        records = keyframe_source.get("shot_records")
        by_uid = {item.get("shot_uid"): item for item in records if isinstance(item, dict)} if isinstance(records, list) else {}
        for shot in ir.get("shots", []) if isinstance(ir.get("shots"), list) else []:
            uid = shot.get("shot_uid")
            source_record = by_uid.get(uid, {})
            keyframes = source_record.get("keyframes") if isinstance(source_record, dict) else []
            k1_ids = [item.get("artifact", {}).get("artifact_id") for item in keyframes if isinstance(item, dict)]
            k1_ids_by_shot[uid] = k1_ids
            expected_semantics = {
                "storyboard_artifact_id": shot.get("storyboard_artifact_id"),
                "global_directing_prompt_full": ir.get("global_directing_prompt_full"),
                "global_look_artifact_id": ir.get("global_look", {}).get("artifact_id"),
                "global_look_prompt_full": ir.get("global_look", {}).get("exact_prompt_block"),
                "look_state_id": shot.get("look_state_id"), "look_state_prompt_full": shot.get("look_state_prompt_full"),
                "shot_look_delta_prompt_full": shot.get("shot_look_delta", {}).get("prompt_full"),
                "look_reference_asset_ids": shot.get("look_state_reference_asset_ids"),
            }
            actual_semantics = {field: source_record.get(field) for field in expected_semantics} if isinstance(source_record, dict) else None
            if actual_semantics != expected_semantics:
                errors.append(f"IR semantic lock/{uid}: Keyframe continuity semantics differ from K1 file")
            material_projection = compact_semantic_json({
                "product_state_ledger": source_record.get("product_state_ledger"),
                "material_state_trajectory": source_record.get("material_state_trajectory"),
                "dynamic_state_ladder": source_record.get("dynamic_state_ladder"),
            }) if isinstance(source_record, dict) else None
            if shot.get("product_material_change") != material_projection:
                errors.append(f"IR semantic lock/{uid}: product/material trajectory differs from K1 file")
            for keyframe in keyframes if isinstance(keyframes, list) else []:
                nested = keyframe.get("artifact") if isinstance(keyframe, dict) and isinstance(keyframe.get("artifact"), dict) else {}
                errors.extend(validate_envelope(nested, f"K1 keyframe/{uid}", "ai-video-keyframe-continuity-pack"))
                canon_item = inventory.get(nested.get("artifact_id"), {})
                if canon_item.get("artifact") != nested or canon_item.get("file_path") != keyframe.get("file_path") or canon_item.get("file_sha256") != keyframe.get("file_sha256"):
                    errors.append(f"IR semantic lock/{uid}: K1 nested keyframe differs from active Canon keyframe")

    boundary_source, boundary_errors = load_original_authority(
        root, inventory, "keyframe_boundary_supplement", "ai-video-keyframe-continuity-pack", "ai-video-keyframe-boundary-supplement.v1"
    )
    errors.extend(boundary_errors)
    k2_ids_by_shot: dict[str, list[str]] = {uid: [] for uid in ir.get("ordered_shot_uids", [])}
    if boundary_source is not None:
        expected_units = [
            {"generation_unit_id": unit.get("generation_unit_id"), "ordered_shot_uids": unit.get("ordered_shot_uids")}
            for unit in ir.get("generation_units", []) if isinstance(unit, dict)
        ]
        if boundary_source.get("prompt_preflight") != artifact_ref(plan) or boundary_source.get("generation_units") != expected_units or boundary_source.get("scripted_shot_uids") != ir.get("ordered_shot_uids"):
            errors.append("IR semantic lock: K2 boundary supplement differs from P1 or uses a within-shot split")
        if any("within_shot" in compact_semantic_json(item).lower() for item in boundary_source.get("cross_generation_unit_boundaries", []) if isinstance(item, dict)):
            errors.append("IR semantic lock: K2 contains a forbidden within-shot boundary")
        for keyframe in boundary_source.get("supplemental_keyframes", []) if isinstance(boundary_source.get("supplemental_keyframes"), list) else []:
            if not isinstance(keyframe, dict):
                continue
            nested = keyframe.get("artifact") if isinstance(keyframe.get("artifact"), dict) else {}
            uid = keyframe.get("shot_uid")
            k2_ids_by_shot.setdefault(uid, []).append(nested.get("artifact_id"))
            errors.extend(validate_envelope(nested, f"K2 keyframe/{uid}", "ai-video-keyframe-continuity-pack"))
            canon_item = inventory.get(nested.get("artifact_id"), {})
            if canon_item.get("artifact") != nested or canon_item.get("file_path") != keyframe.get("file_path") or canon_item.get("file_sha256") != keyframe.get("file_sha256"):
                errors.append(f"IR semantic lock/{uid}: K2 nested keyframe differs from active Canon keyframe")
        for shot in ir.get("shots", []) if isinstance(ir.get("shots"), list) else []:
            uid = shot.get("shot_uid")
            if shot.get("keyframe_artifact_ids") != k1_ids_by_shot.get(uid, []) + k2_ids_by_shot.get(uid, []):
                errors.append(f"IR semantic lock/{uid}: keyframe IDs differ from K1/K2 originals")

    plan_source, plan_source_errors = load_original_authority(
        root, inventory, "generation_unit_preflight_plan", OWNER, "ai-video-generation-unit-preflight.v1"
    )
    errors.extend(plan_source_errors)
    if plan_source is not None and plan_source != plan:
        errors.append("IR semantic lock: P1 file differs from the plan object validated by Prompt")

    v1_source, v1_errors = load_original_authority(
        root, manifest_entries_as_inventory(preflight_active), "previs_manifest", "ai-video-timed-animatic-previs-director", "ai-video-timed-animatic-previs.v1"
    )
    errors.extend(v1_errors)
    if v1_source is not None:
        timing = v1_source.get("timing_animatic_v1") if isinstance(v1_source.get("timing_animatic_v1"), dict) else {}
        errors.extend(validate_envelope(timing, "V1 timing artifact", "ai-video-timed-animatic-previs-director"))
        timing_item = inventory.get(timing.get("artifact_id"), {})
        if timing_item.get("artifact") != {field: timing.get(field) for field in (
            "contract_version", "artifact_id", "owner_skill", "version", "sha256", "approval_status",
            "dependencies", "affected_shot_uids", "stale_reason",
        )} or timing_item.get("file_path") != timing.get("file_path") or timing_item.get("file_sha256") != timing.get("file_sha256"):
            errors.append("IR semantic lock: V1 nested media differs from active Canon media artifact")
        timeline = timing.get("timeline") if isinstance(timing.get("timeline"), list) else []
        expected_timeline = [{
            "shot_uid": shot.get("shot_uid"), "start_seconds": shot.get("target_start_seconds"),
            "end_seconds": shot.get("target_end_seconds"),
        } for shot in ir.get("shots", []) if isinstance(shot, dict)]
        actual_timeline = [{field: item.get(field) for field in ("shot_uid", "start_seconds", "end_seconds")} for item in timeline if isinstance(item, dict)]
        if actual_timeline != expected_timeline or not close(timing.get("actual_duration_seconds"), expected_timeline[-1]["end_seconds"] if expected_timeline else None):
            errors.append("IR semantic lock: V1 timeline differs from Shot Contract windows")

    v2_source, v2_errors = load_original_authority(
        root, inventory, "previs_manifest", "ai-video-timed-animatic-previs-director", "ai-video-timed-animatic-previs.v1"
    )
    errors.extend(v2_errors)
    v2_units = {
        item.get("generation_unit_id"): item for item in v2_source.get("control_previs_v2_units", []) if isinstance(item, dict)
    } if isinstance(v2_source, dict) else {}

    for unit in ir.get("generation_units", []) if isinstance(ir.get("generation_units"), list) else []:
        if not isinstance(unit, dict) or unit.get("control_previs_requirement") != "required":
            continue
        v2_id = unit.get("control_previs_artifact_id")
        v2_item = inventory.get(v2_id, {})
        source_unit = v2_units.get(unit.get("generation_unit_id"), {})
        errors.extend(validate_envelope(source_unit, f"V2 unit/{unit.get('generation_unit_id')}", "ai-video-timed-animatic-previs-director"))
        if source_unit.get("artifact_id") != v2_id or v2_item.get("artifact_slot") != f"control_previs_v2:{unit.get('generation_unit_id')}":
            errors.append(f"IR semantic lock/{unit.get('generation_unit_id')}: V2 slot does not bind the unit")
        if v2_item.get("artifact") != {field: source_unit.get(field) for field in (
            "contract_version", "artifact_id", "owner_skill", "version", "sha256", "approval_status",
            "dependencies", "affected_shot_uids", "stale_reason",
        )} or v2_item.get("file_path") != source_unit.get("file_path") or v2_item.get("file_sha256") != source_unit.get("file_sha256"):
            errors.append(f"IR semantic lock/{unit.get('generation_unit_id')}: V2 nested unit differs from active Canon media artifact")
        artifact_scope = v2_item.get("artifact", {}).get("affected_shot_uids") if isinstance(v2_item.get("artifact"), dict) else None
        if artifact_scope != unit.get("ordered_shot_uids") or source_unit.get("shot_uids") != unit.get("ordered_shot_uids") or not close(source_unit.get("target_duration_seconds"), unit.get("target_duration_seconds")):
            errors.append(f"IR semantic lock/{unit.get('generation_unit_id')}: V2 shot scope differs from unit")
        first_start = next((shot.get("target_start_seconds") for shot in ir.get("shots", []) if isinstance(shot, dict) and shot.get("shot_uid") in unit.get("ordered_shot_uids", [])), 0.0)
        expected_local = [{
            "shot_uid": shot.get("shot_uid"),
            "start_seconds": float(shot.get("target_start_seconds", 0)) - float(first_start or 0),
            "end_seconds": float(shot.get("target_end_seconds", 0)) - float(first_start or 0),
        } for shot in ir.get("shots", []) if isinstance(shot, dict) and shot.get("shot_uid") in unit.get("ordered_shot_uids", [])]
        actual_local = [{field: item.get(field) for field in ("shot_uid", "start_seconds", "end_seconds")} for item in source_unit.get("local_timeline", []) if isinstance(item, dict)]
        if actual_local != expected_local:
            errors.append(f"IR semantic lock/{unit.get('generation_unit_id')}: V2 local timeline differs from Shot Contract windows")
        expected_dependencies = {plan.get("artifact_id"), ir.get("boundary_supplement_ref", {}).get("artifact_id")}
        actual_dependencies = {
            dep.get("artifact_id") for dep in v2_item.get("artifact", {}).get("dependencies", []) if isinstance(dep, dict)
        }
        if not expected_dependencies <= actual_dependencies:
            errors.append(f"IR semantic lock/{unit.get('generation_unit_id')}: V2 lacks P1/K2 dependency locks")
    return errors


def validate_ir(
    root: Path,
    ir: dict[str, Any],
    snapshot: dict[str, Any],
    active: dict[str, dict[str, Any]],
    plan: dict[str, Any],
) -> tuple[list[str], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    errors = validate_envelope(ir, "IR", OWNER)
    if ir.get("schema_version") != "ai-video-canonical-ir.v2":
        errors.append("IR: wrong schema_version")
    if ir.get("ir_stage") not in {"final_compile", "revision_compile"}:
        errors.append("IR: final compile stage required")
    if ir.get("package_mode") not in {"compile", "revise"}:
        errors.append("IR: invalid package_mode")
    if ir.get("generation_mode") != "omni_reference_to_video":
        errors.append("IR: generation_mode must be omni_reference_to_video")
    if ir.get("generation_unit_boundary_policy") != "whole_shot_uids_only" or ir.get("generation_unit_boundary_policy") != plan.get("generation_unit_boundary_policy"):
        errors.append("IR: generation units must preserve the approved whole-Shot-UID boundary policy")
    if ir.get("target_profile_id") != "seedance_2_5_forward_compatible":
        errors.append("IR: wrong target profile")
    if set(ir.get("forbidden_fallbacks", [])) != {"text_only_generation", "endpoint_frame_generation"}:
        errors.append("IR: both lower-control fallbacks must be forbidden")
    errors.extend(validate_manifest_receipt(root, ir.get("project_canon_read_receipt"), snapshot, COMPILE_SNAPSHOT, "IR"))

    expected_plan_ref = artifact_ref(plan)
    if ir.get("preflight_plan_ref") != expected_plan_ref:
        errors.append("IR: preflight_plan_ref mismatch")
    boundary_ref = ir.get("boundary_supplement_ref")
    if not isinstance(boundary_ref, dict) or boundary_ref.get("artifact_id") not in active:
        errors.append("IR: boundary_supplement_ref must resolve in compile manifest")
    elif artifact_ref(active[boundary_ref["artifact_id"]]) != boundary_ref:
        errors.append("IR: boundary_supplement_ref lock mismatch")

    ordered = ir.get("ordered_shot_uids")
    if ordered != snapshot.get("canonical_shot_uids"):
        errors.append("IR: ordered shots must equal compile manifest canonical order")
        ordered = snapshot.get("canonical_shot_uids", [])
    shots = ir.get("shots")
    if not isinstance(shots, list):
        errors.append("IR: shots must be an array")
        shots = []
    shot_ids = [item.get("shot_uid") for item in shots if isinstance(item, dict)]
    if shot_ids != ordered or len(shot_ids) != len(shots):
        errors.append("IR: shot records must exactly match approved order")
    by_shot = {item.get("shot_uid"): item for item in shots if isinstance(item, dict)}

    inventory = ir.get("source_artifact_inventory")
    if not isinstance(inventory, list):
        errors.append("IR: source_artifact_inventory must be an array")
        inventory = []
    inventory_by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(inventory):
        label = f"IR.source_artifact_inventory[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: must be an object")
            continue
        artifact = item.get("artifact")
        errors.extend(validate_consumed_envelope(artifact, f"{label}.artifact"))
        if not isinstance(artifact, dict):
            continue
        artifact_id = artifact.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id or artifact_id in inventory_by_id:
            errors.append(f"{label}: artifact_id must be unique")
            continue
        inventory_by_id[artifact_id] = item
        entry = active.get(artifact_id)
        if entry is None:
            errors.append(f"{label}: artifact absent from compile manifest")
            continue
        if source_inventory_tuple(item) != manifest_entry_tuple(entry):
            errors.append(f"{label}: exact identity/file lock differs from compile manifest")
        for field in ("artifact_slot", "artifact_type", "approval_status", "eligible_for_downstream"):
            if item.get(field) != entry.get(field):
                errors.append(f"{label}: {field} differs from compile manifest")
        roles = item.get("control_roles")
        if (
            not isinstance(roles, list) or not roles or len(roles) != len(set(roles))
            or any(not isinstance(role, str) or not role for role in roles)
            or item.get("control_role") not in roles
        ):
            errors.append(f"{label}: control_roles must be non-empty unique and contain primary control_role")
        expected_artifact = {
            "contract_version": "ai-video-artifact-v1",
            "artifact_id": entry.get("artifact_id"), "owner_skill": entry.get("owner_skill"),
            "version": entry.get("version"), "sha256": entry.get("sha256"),
            "approval_status": entry.get("approval_status"), "dependencies": entry.get("dependencies"),
            "affected_shot_uids": entry.get("affected_shot_uids"), "stale_reason": entry.get("stale_reason"),
        }
        if artifact != expected_artifact:
            errors.append(f"{label}: artifact envelope differs from manifest entry")
    if set(inventory_by_id) != set(active):
        missing = sorted(set(active) - set(inventory_by_id))
        extra = sorted(set(inventory_by_id) - set(active))
        errors.append(f"IR: inventory must equal full compile manifest active set; missing={missing}, extra={extra}")

    required_slots = {
        "professional_shot_contract", "global_look_contract", "storyboard_manifest",
        "previs_manifest", "timing_animatic_v1", "keyframe_continuity_manifest", "generation_unit_preflight_plan",
        "keyframe_boundary_supplement",
    }
    slots = {entry.get("artifact_slot") for entry in active.values()}
    missing_slots = required_slots - slots
    if missing_slots:
        errors.append(f"IR: compile manifest missing required slots {sorted(missing_slots)}")

    grammar = ir.get("global_directing_prompt_full")
    look = ir.get("global_look") if isinstance(ir.get("global_look"), dict) else {}
    if not isinstance(grammar, str) or len(grammar) < 40:
        errors.append("IR: exact global directing prompt required")
    if not isinstance(look.get("exact_prompt_block"), str) or len(look["exact_prompt_block"]) < 200:
        errors.append("IR: exact Global Look block required")
    if look.get("artifact_id") not in inventory_by_id:
        errors.append("IR: Global Look artifact not in inventory")
    for ref_id in look.get("reference_asset_ids", []) if isinstance(look.get("reference_asset_ids"), list) else []:
        if ref_id not in inventory_by_id:
            errors.append(f"IR: unknown Global Look reference {ref_id}")

    cursor = 0.0
    claim_ids = {
        item.get("claim_id") for item in ir.get("claim_boundary", {}).get("claims", [])
        if isinstance(item, dict)
    }
    for index, shot in enumerate(shots):
        label = f"IR.shots[{index}]"
        if not isinstance(shot, dict):
            errors.append(f"{label}: must be an object")
            continue
        start, end = shot.get("target_start_seconds"), shot.get("target_end_seconds")
        if not close(start, cursor) or not is_number(end) or float(end) <= float(start or 0):
            errors.append(f"{label}: invalid or non-contiguous target time window")
        if is_number(end):
            cursor = float(end)
        for field in (
            "advertising_function", "scene_initial_state", "visible_action_expression", "camera_composition",
            "blocking_spatial_change", "product_material_change", "ending_continuity_state",
            "look_state_id", "look_state_prompt_full", "storyboard_artifact_id",
        ):
            if not isinstance(shot.get(field), str) or not shot[field]:
                errors.append(f"{label}: {field} required")
        if not str(shot.get("look_state_id", "")).startswith("LOOK_STATE_") or len(str(shot.get("look_state_prompt_full", ""))) < 80:
            errors.append(f"{label}: exact legal Look State required")
        delta = shot.get("shot_look_delta")
        if not isinstance(delta, dict) or delta.get("preserves_look_core") is not True or not isinstance(delta.get("prompt_full"), str) or not delta["prompt_full"]:
            errors.append(f"{label}: complete legal Shot Look Delta required")
        if shot.get("storyboard_stage") != "look_applied_final" or shot.get("storyboard_model_input_eligible") is not True:
            errors.append(f"{label}: only look_applied_final storyboard is model-input eligible")
        referenced = [shot.get("storyboard_artifact_id"), *shot.get("keyframe_artifact_ids", [])]
        referenced.extend(shot.get("look_state_reference_asset_ids", []))
        if shot.get("control_previs_artifact_id") is not None:
            referenced.append(shot.get("control_previs_artifact_id"))
        for artifact_id in referenced:
            if artifact_id not in inventory_by_id:
                errors.append(f"{label}: referenced artifact absent from inventory: {artifact_id}")
        spoken = shot.get("spoken_content")
        if not isinstance(spoken, dict):
            errors.append(f"{label}: spoken_content required")
        elif spoken.get("delivery_mode") not in {"model_spoken", "prohibited_model_text"}:
            errors.append(f"{label}: spoken_content delivery mode invalid")
        copy_items = shot.get("on_screen_copy")
        if not isinstance(copy_items, list):
            errors.append(f"{label}: on_screen_copy must be an array")
            copy_items = []
        for copy_index, copy_item in enumerate(copy_items):
            if not isinstance(copy_item, dict) or copy_item.get("delivery_mode") not in {"external_overlay_handoff", "prohibited_model_text"}:
                errors.append(f"{label}.on_screen_copy[{copy_index}]: model-rendered text is not permitted")
        for copy_item in [spoken, *copy_items]:
            if isinstance(copy_item, dict):
                unknown_claims = set(copy_item.get("claim_ids", [])) - claim_ids
                if unknown_claims:
                    errors.append(f"{label}: copy references unknown claims {sorted(unknown_claims)}")

    units = ir.get("generation_units")
    if not isinstance(units, list) or not units:
        errors.append("IR: generation_units must be non-empty")
        units = []
    plan_units = {
        item.get("generation_unit_id"): item for item in plan.get("generation_units", []) if isinstance(item, dict)
    }
    flattened: list[str] = []
    for index, unit in enumerate(units):
        label = f"IR.units[{index}]"
        if not isinstance(unit, dict):
            errors.append(f"{label}: must be an object")
            continue
        unit_id = unit.get("generation_unit_id")
        shots_in_unit = unit.get("ordered_shot_uids")
        if not isinstance(shots_in_unit, list) or not shots_in_unit:
            errors.append(f"{label}: ordered_shot_uids required")
            shots_in_unit = []
        flattened.extend(shots_in_unit)
        preflight_unit = plan_units.get(unit_id)
        if preflight_unit is None:
            errors.append(f"{label}: missing from approved preflight plan")
        else:
            for field in (
                "ordered_shot_uids", "target_duration_seconds", "timing_sensitive",
                "control_previs_requirement", "required_modalities", "preflight_status",
            ):
                if unit.get(field) != preflight_unit.get(field):
                    errors.append(f"{label}: {field} differs from preflight plan")
        expected_duration = sum(
            float(by_shot[uid]["target_end_seconds"]) - float(by_shot[uid]["target_start_seconds"])
            for uid in shots_in_unit if uid in by_shot and is_number(by_shot[uid].get("target_start_seconds")) and is_number(by_shot[uid].get("target_end_seconds"))
        )
        if not close(unit.get("target_duration_seconds"), expected_duration):
            errors.append(f"{label}: target duration differs from shot windows")
        requirement = unit.get("control_previs_requirement")
        v2_id = unit.get("control_previs_artifact_id")
        if requirement == "required":
            if not isinstance(v2_id, str) or not v2_id or v2_id not in inventory_by_id:
                errors.append(f"{label}: required V2 Control Previs artifact missing")
            if "video" not in unit.get("required_modalities", []):
                errors.append(f"{label}: required V2 must make video a required modality")
            for uid in shots_in_unit:
                if by_shot.get(uid, {}).get("control_previs_artifact_id") != v2_id:
                    errors.append(f"{label}: shot {uid} does not bind unit V2")
        elif requirement == "exempt_single_static_shot":
            if len(ordered) != 1 or len(units) != 1 or len(shots_in_unit) != 1 or v2_id is not None:
                errors.append(f"{label}: invalid V2 exemption")
        else:
            errors.append(f"{label}: invalid control_previs_requirement")
        boundary_id = unit.get("boundary_supplement_artifact_id")
        if not isinstance(boundary_ref, dict) or boundary_id != boundary_ref.get("artifact_id"):
            errors.append(f"{label}: boundary supplement mismatch")
    if flattened != ordered:
        errors.append("IR: units must preserve exact shot order")
    if set(plan_units) != {item.get("generation_unit_id") for item in units if isinstance(item, dict)}:
        errors.append("IR: unit IDs must exactly equal preflight plan")
    if ir.get("affected_shot_uids") != ordered:
        errors.append("IR: affected_shot_uids must equal canonical shots")
    return errors, inventory_by_id, units


def effective_provider_profile(provider_doc: dict[str, Any]) -> dict[str, Any] | None:
    profiles = provider_doc.get("profiles")
    if not isinstance(profiles, list):
        return None
    return next((item for item in profiles if isinstance(item, dict) and item.get("profile_type") == "provider_runtime"), None)


def validate_capabilities(root: Path, model_doc: dict[str, Any], provider_doc: dict[str, Any]) -> tuple[list[str], dict[str, Any] | None, dict[str, Any]]:
    errors = validate_envelope(model_doc, "model_capabilities", OWNER)
    errors.extend(validate_envelope(provider_doc, "provider_capabilities", OWNER))
    if model_doc.get("schema_version") != "ai-video-capability-profile.v1" or provider_doc.get("schema_version") != "ai-video-capability-profile.v1":
        errors.append("capabilities: wrong schema_version")
    model_profiles = model_doc.get("profiles")
    if not isinstance(model_profiles, list):
        return errors + ["model capabilities: profiles must be an array"], None, {}
    by_id = {item.get("profile_id"): item for item in model_profiles if isinstance(item, dict)}
    target = by_id.get("seedance_2_5_forward_compatible")
    documented = by_id.get("seedance_2_0_documented_omni")
    if not target or target.get("surface_status") != "forward_target_only":
        errors.append("model capabilities: missing 2.5 forward target")
    if not documented or documented.get("surface_status") != "first_party_documented":
        errors.append("model capabilities: missing documented Seedance 2.0")
    else:
        expected = {"max_duration_seconds": 15, "max_image_inputs": 9, "max_video_inputs": 3, "max_audio_inputs": 3}
        limits = documented.get("effective_limits") if isinstance(documented.get("effective_limits"), dict) else {}
        for key, value in expected.items():
            if limits.get(key) != value:
                errors.append(f"model capabilities: Seedance 2.0 {key} must be {value}")
        if not {"text", "image", "video", "audio"} <= set(documented.get("supported_modalities", [])):
            errors.append("model capabilities: Seedance 2.0 modalities incomplete")
        evidence = documented.get("evidence")
        if not isinstance(evidence, list) or not any(item.get("evidence_tier") == "first_party_documented" and str(item.get("locator", "")).startswith("https://seed.bytedance.com/") for item in evidence if isinstance(item, dict)):
            errors.append("model capabilities: Seedance 2.0 requires first-party evidence locator")
    for profile in model_profiles:
        for evidence_item in profile.get("evidence", []) if isinstance(profile, dict) else []:
            if isinstance(evidence_item, dict) and evidence_item.get("evidence_tier") != "provider_schema_verified":
                if evidence_item.get("snapshot_path") is not None or evidence_item.get("snapshot_file_sha256") is not None:
                    errors.append("model capabilities: non-provider evidence must not masquerade as local provider schema")
        for claim in profile.get("capability_claims", []) if isinstance(profile, dict) else []:
            if claim.get("evidence_tier") in {"preview_or_user_supplied_claim", "third_party_marketing_claim", "unknown"} and (claim.get("runtime_verified") or claim.get("usable_for_payload_budget")):
                errors.append("model capabilities: unverified claim cannot be executable")
    provider = effective_provider_profile(provider_doc)
    effective: dict[str, Any] = {}
    if provider is None:
        errors.append("provider capabilities: provider_runtime profile missing")
    else:
        if provider.get("surface_status") != "provider_schema_verified" or provider.get("generation_mode") != "omni_reference_to_video":
            errors.append("provider capabilities: verified Omni runtime required")
        input_constraints = provider.get("input_constraints") if isinstance(provider.get("input_constraints"), dict) else {}
        for modality in set(provider.get("supported_modalities", [])) - {"text"}:
            if not isinstance(input_constraints.get(modality), dict):
                errors.append(f"provider capabilities: schema-verified {modality} support requires explicit upload constraints")
        range_pairs = {
            "image": (("min_width_px", "max_width_px"), ("min_height_px", "max_height_px"), ("min_aspect_ratio", "max_aspect_ratio")),
            "video": (("min_duration_seconds", "max_duration_seconds"), ("min_width_px", "max_width_px"), ("min_height_px", "max_height_px"), ("min_aspect_ratio", "max_aspect_ratio"), ("min_fps", "max_fps")),
            "audio": (("min_channels", "max_channels"), ("min_sample_rate_hz", "max_sample_rate_hz")),
        }
        for modality, pairs in range_pairs.items():
            constraint = input_constraints.get(modality)
            if not isinstance(constraint, dict):
                continue
            for minimum_key, maximum_key in pairs:
                minimum, maximum = constraint.get(minimum_key), constraint.get(maximum_key)
                if not is_number(minimum) or not is_number(maximum) or float(minimum) > float(maximum):
                    errors.append(f"provider capabilities: {modality} constraint range {minimum_key}/{maximum_key} is invalid")
        evidence = provider.get("evidence")
        verified_evidence = [
            item for item in evidence if isinstance(item, dict) and item.get("evidence_tier") == "provider_schema_verified"
        ] if isinstance(evidence, list) else []
        if len(verified_evidence) != 1:
            errors.append("provider capabilities: exactly one hash-locked provider schema snapshot required")
        else:
            evidence_item = verified_evidence[0]
            snapshot, snapshot_errors = read_hash_locked_json(
                root, evidence_item.get("snapshot_path"), evidence_item.get("snapshot_file_sha256"),
                "provider capabilities/schema snapshot",
            )
            errors.extend(snapshot_errors)
            if snapshot is not None:
                expected_snapshot = {
                    "schema_version": "ai-video-provider-runtime-capability-snapshot.v1",
                    "profile_id": provider.get("profile_id"), "provider": provider.get("provider"),
                    "model_family": provider.get("model_family"), "model_id": provider.get("model_id"),
                    "surface": provider.get("surface"),
                    "documented_backend_profile_id": provider.get("documented_backend_profile_id"),
                    "generation_mode": provider.get("generation_mode"),
                    "surface_status": provider.get("surface_status"),
                    "supported_modalities": provider.get("supported_modalities"),
                    "effective_limits": provider.get("effective_limits"),
                    "input_constraints": provider.get("input_constraints"),
                }
                if snapshot != expected_snapshot:
                    errors.append("provider capabilities: declared runtime fields differ from local provider schema snapshot")
        backend_id = provider.get("documented_backend_profile_id")
        if not isinstance(backend_id, str) or backend_id not in by_id:
            errors.append("provider capabilities: documented_backend_profile_id must resolve")
        else:
            backend = by_id[backend_id]
            provider_limits = provider.get("effective_limits") if isinstance(provider.get("effective_limits"), dict) else {}
            documented_limits = backend.get("effective_limits") if isinstance(backend.get("effective_limits"), dict) else {}
            for key in ("max_duration_seconds", "max_image_inputs", "max_video_inputs", "max_audio_inputs", "max_total_multimodal_inputs"):
                p_value, d_value = provider_limits.get(key), documented_limits.get(key)
                if is_number(p_value) and is_number(d_value):
                    if float(p_value) > float(d_value):
                        errors.append(f"provider capabilities: {key} exceeds documented backend ceiling")
                    effective[key] = min(p_value, d_value)
                elif is_number(d_value):
                    effective[key] = d_value
                else:
                    effective[key] = p_value
    return errors, provider, effective


def validate_bindings(
    root: Path,
    bindings: dict[str, Any],
    inventory: dict[str, dict[str, Any]],
    units: list[dict[str, Any]],
    shots: list[dict[str, Any]],
    provider: dict[str, Any] | None,
    limits: dict[str, Any],
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    errors = validate_envelope(bindings, "bindings", OWNER)
    if bindings.get("schema_version") != "ai-video-binding-manifest.v2" or bindings.get("generation_mode") != "omni_reference_to_video":
        errors.append("bindings: contract mismatch")
    unit_ids = [item.get("generation_unit_id") for item in units if isinstance(item, dict)]
    asset_inventory = bindings.get("asset_inventory")
    if not isinstance(asset_inventory, list):
        return errors + ["bindings: asset_inventory must be an array"], {}
    binding_inventory: dict[str, dict[str, Any]] = {}
    expected_selected: dict[str, set[str]] = {unit_id: set() for unit_id in unit_ids}
    for index, item in enumerate(asset_inventory):
        label = f"bindings.asset_inventory[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: must be an object")
            continue
        artifact = item.get("artifact") if isinstance(item.get("artifact"), dict) else {}
        artifact_id = artifact.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id or artifact_id in binding_inventory:
            errors.append(f"{label}: artifact_id must be unique")
            continue
        binding_inventory[artifact_id] = item
        source = inventory.get(artifact_id)
        if source is None:
            errors.append(f"{label}: artifact absent from IR inventory")
            continue
        source_artifact = source.get("artifact", {})
        expected_ref = {
            "artifact_id": source_artifact.get("artifact_id"), "owner_skill": source_artifact.get("owner_skill"),
            "version": source_artifact.get("version"), "sha256": source_artifact.get("sha256"),
            "file_path": source.get("file_path"), "file_sha256": source.get("file_sha256"),
            "artifact_record_locator": source.get("artifact_record_locator"),
            "artifact_record_file_sha256": source.get("artifact_record_file_sha256"),
        }
        if artifact != expected_ref:
            errors.append(f"{label}: exact identity/file lock differs from IR")
        for field in ("artifact_slot", "artifact_type", "control_roles", "control_role", "approval_status", "eligible_for_downstream"):
            if item.get(field) != source.get(field):
                errors.append(f"{label}: {field} differs from IR")
        source_owner = source_artifact.get("owner_skill")
        control_roles = item.get("control_roles")
        if (
            not isinstance(control_roles, list) or not control_roles
            or len(control_roles) != len(set(control_roles))
            or any(not isinstance(role, str) or not role for role in control_roles)
            or item.get("control_role") not in control_roles
        ):
            errors.append(f"{label}: control_roles must be non-empty unique and contain primary control_role")
            control_roles = []
        owner_asset_record: dict[str, Any] | None = None
        if source_owner in REGISTERED_ASSET_OWNERS:
            owner_asset_record, owner_record_errors = read_hash_locked_json(
                root,
                source.get("artifact_record_locator"),
                source.get("artifact_record_file_sha256"),
                f"{label}/fixed-owner asset record",
            )
            errors.extend(owner_record_errors)
            if owner_asset_record is not None:
                if owner_asset_record.get("schema_version") != "ai-video-owner-asset-export.v1":
                    errors.append(f"{label}: registered asset owner must supply ai-video-owner-asset-export.v1")
                if owner_asset_record.get("artifact_type") != item.get("artifact_type"):
                    errors.append(f"{label}: artifact_type differs from the fixed-owner asset record")
                authorized_roles = owner_asset_record.get("control_roles_authorized")
                if not isinstance(authorized_roles, list) or control_roles != authorized_roles:
                    errors.append(f"{label}: control_roles must exactly equal the fixed-owner asset record authorization")
                if item.get("control_role") not in control_roles:
                    errors.append(f"{label}: primary control_role is not authorized by the fixed-owner asset record")
        classifications = item.get("unit_classification")
        if not isinstance(classifications, list):
            errors.append(f"{label}: unit_classification must be an array")
            continue
        class_ids = [entry.get("generation_unit_id") for entry in classifications if isinstance(entry, dict)]
        if class_ids != unit_ids:
            errors.append(f"{label}: must classify every unit in exact order")
        for classification in classifications:
            if not isinstance(classification, dict):
                continue
            if classification.get("status") in {"relevant_selected", "transported_via_atlas"} and item.get("control_role") == "storyboard" and (item.get("storyboard_stage") != "look_applied_final" or item.get("storyboard_model_input_eligible") is not True):
                errors.append(f"{label}: structure-draft storyboard cannot enter model transport")
            if (
                (source_owner == "packaging-product-identity-label-lock-board" or "label_copy" in control_roles)
                and classification.get("status") == "transported_via_atlas"
            ):
                errors.append(f"{label}: label_copy or packaging evidence must remain a direct image binding, never an atlas panel")
            if classification.get("status") == "relevant_selected":
                if item.get("eligible_for_downstream") is not True or item.get("approval_status") != "user_approved":
                    errors.append(f"{label}: relevant final input must be user-approved and eligible")
                expected_selected.setdefault(classification.get("generation_unit_id"), set()).add(artifact_id)
        if item.get("modality") == "audio" and not set(control_roles) <= {"dialogue_voice", "synchronous_sfx"}:
            errors.append(f"{label}: only source-approved dialogue/voice/synchronous SFX audio is allowed")
    if set(binding_inventory) != set(inventory):
        errors.append("bindings: asset inventory must equal full IR inventory")

    records = bindings.get("generation_unit_bindings")
    if not isinstance(records, list):
        return errors + ["bindings: generation_unit_bindings must be an array"], {}
    by_unit = {item.get("generation_unit_id"): item for item in records if isinstance(item, dict)}
    if set(by_unit) != set(unit_ids) or len(by_unit) != len(records):
        errors.append("bindings: unit records must exactly match IR")
    supported = set(provider.get("supported_modalities", [])) if provider else set()
    provider_input_constraints = provider.get("input_constraints") if provider and isinstance(provider.get("input_constraints"), dict) else {}
    shots_by_uid = {item.get("shot_uid"): item for item in shots if isinstance(item, dict)}
    selected_ids_by_unit: dict[str, set[str]] = {}
    for unit in units:
        unit_id = unit.get("generation_unit_id")
        record = by_unit.get(unit_id, {})
        selected = record.get("bindings") if isinstance(record.get("bindings"), list) else []
        selected_ids = [item.get("artifact_id") for item in selected if isinstance(item, dict)]
        selected_ids_by_unit[unit_id] = set(selected_ids)
        if set(selected_ids) != expected_selected.get(unit_id, set()) or len(selected_ids) != len(set(selected_ids)):
            errors.append(f"bindings/{unit_id}: selected artifacts must equal all relevant_selected exactly")
        aliases = [item.get("provider_alias") for item in selected if isinstance(item, dict)]
        if len(aliases) != len(set(aliases)):
            errors.append(f"bindings/{unit_id}: provider aliases must be unique")
        counts = {"image": 0, "video": 0, "audio": 0}
        for selected_item in selected:
            if not isinstance(selected_item, dict):
                errors.append(f"bindings/{unit_id}: binding must be an object")
                continue
            artifact_id = selected_item.get("artifact_id")
            source = binding_inventory.get(artifact_id, {})
            for field in ("modality", "control_roles", "control_role", "scope", "controlled_shot_uids", "expected_influence", "priority"):
                if selected_item.get(field) != source.get(field):
                    errors.append(f"bindings/{unit_id}/{artifact_id}: {field} differs from inventory")
            modality = selected_item.get("modality")
            if modality in counts:
                counts[modality] += 1
            if modality not in supported:
                errors.append(f"bindings/{unit_id}: selected unsupported modality {modality}")
            if modality == "image":
                source_artifact = source.get("artifact") if isinstance(source.get("artifact"), dict) else {}
                errors.extend(validate_image_file_for_provider(
                    root, source_artifact.get("file_path"), source_artifact.get("file_sha256"),
                    provider_input_constraints.get("image"), f"bindings/{unit_id}/{artifact_id}",
                ))
            elif modality == "video":
                errors.extend(validate_video_item_for_provider(
                    root, source, provider_input_constraints.get("video"),
                    f"bindings/{unit_id}/{artifact_id}",
                ))
            elif modality == "audio":
                source_artifact = source.get("artifact") if isinstance(source.get("artifact"), dict) else {}
                errors.extend(validate_audio_file_for_provider(
                    root, source_artifact.get("file_path"), source_artifact.get("file_sha256"),
                    provider_input_constraints.get("audio"), f"bindings/{unit_id}/{artifact_id}",
                ))
        declared = record.get("selected_counts") if isinstance(record, dict) else {}
        if any(declared.get(key) != value for key, value in counts.items()) or declared.get("total_multimodal") != sum(counts.values()):
            errors.append(f"bindings/{unit_id}: selected_counts mismatch")
        for modality, limit_key in (("image", "max_image_inputs"), ("video", "max_video_inputs"), ("audio", "max_audio_inputs")):
            limit = limits.get(limit_key)
            if limit is None and counts[modality] > 0:
                errors.append(f"bindings/{unit_id}: unknown {modality} capacity")
            elif is_number(limit) and counts[modality] > float(limit):
                errors.append(f"bindings/{unit_id}: {modality} capacity exceeded")
        total_limit = limits.get("max_total_multimodal_inputs")
        if is_number(total_limit) and sum(counts.values()) > float(total_limit):
            errors.append(f"bindings/{unit_id}: total multimodal capacity exceeded")
        required = set(unit.get("required_modalities", []))
        missing = required - supported
        if missing and record.get("binding_status") != "blocked_unsupported_required_modality":
            errors.append(f"bindings/{unit_id}: missing modalities {sorted(missing)} must fail closed")
        if unit.get("control_previs_requirement") == "required":
            v2_id = unit.get("control_previs_artifact_id")
            if not any(item.get("artifact_id") == v2_id and item.get("modality") == "video" and item.get("control_role") == "control_previs" for item in selected if isinstance(item, dict)):
                errors.append(f"bindings/{unit_id}: required V2 control video binding missing")
        for modality in required - {"text"}:
            if counts.get(modality, 0) < 1:
                errors.append(f"bindings/{unit_id}: required modality {modality} has no selected input")
    atlas_records = bindings.get("atlas_records")
    if not isinstance(atlas_records, list):
        errors.append("bindings: atlas_records must be an array")
        atlas_records = []
    atlas_by_unit: dict[str, list[dict[str, Any]]] = {}
    for index, atlas in enumerate(atlas_records):
        label = f"bindings.atlas_records[{index}]"
        if not isinstance(atlas, dict):
            errors.append(f"{label}: must be an object")
            continue
        if atlas.get("deterministic_composition") is not True or atlas.get("generative_recomposition") is not False:
            errors.append(f"{label}: atlas must be deterministic and non-generative")
        sources = atlas.get("source_artifact_ids")
        if not isinstance(sources, list) or not sources or not set(sources).issubset(binding_inventory):
            errors.append(f"{label}: source artifacts invalid")
        atlas_id = atlas.get("atlas_id")
        unit_id = atlas.get("generation_unit_id")
        if atlas_id not in binding_inventory:
            errors.append(f"{label}: atlas artifact absent from inventory")
        elif atlas_id not in selected_ids_by_unit.get(unit_id, set()):
            errors.append(f"{label}: atlas transport artifact must itself be selected")
        atlas_path, atlas_bytes, atlas_file_errors = read_hash_locked_file(
            root, atlas.get("file_path"), atlas.get("file_sha256"), f"{label}/atlas"
        )
        errors.extend(atlas_file_errors)
        if atlas_bytes is not None and atlas.get("file_bytes") != len(atlas_bytes):
            errors.append(f"{label}: declared file_bytes differs from the locked atlas file")
        spec, spec_errors = read_hash_locked_json(
            root, atlas.get("composition_spec_path"), atlas.get("composition_spec_file_sha256"), f"{label}/composition spec"
        )
        errors.extend(spec_errors)
        receipt, receipt_errors = read_hash_locked_json(
            root, atlas.get("composition_receipt_path"), atlas.get("composition_receipt_file_sha256"), f"{label}/composition receipt"
        )
        errors.extend(receipt_errors)
        if atlas_id in binding_inventory:
            atlas_source = binding_inventory[atlas_id].get("artifact", {})
            if atlas_source.get("file_path") != atlas.get("file_path") or atlas_source.get("file_sha256") != atlas.get("file_sha256"):
                errors.append(f"{label}: atlas file lock differs from selected inventory artifact")
        if spec is not None and receipt is not None and atlas_bytes is not None:
            try:
                rebuilt_bytes, rebuilt_receipt = build_from_spec(root, spec)
            except (OSError, ValueError, TypeError) as exc:
                errors.append(f"{label}: deterministic atlas rebuild failed closed: {exc}")
            else:
                if rebuilt_bytes != atlas_bytes:
                    errors.append(f"{label}: atlas pixels are not the deterministic composition result")
                if rebuilt_receipt != receipt:
                    errors.append(f"{label}: composition receipt differs from deterministic rebuild")
                if receipt.get("atlas_id") != atlas_id or receipt.get("generation_unit_id") != unit_id:
                    errors.append(f"{label}: composition receipt atlas/unit mismatch")
                if (
                    atlas.get("codec") != receipt.get("codec")
                    or atlas.get("media_type") != receipt.get("media_type")
                    or atlas.get("width") != receipt.get("width")
                    or atlas.get("height") != receipt.get("height")
                ):
                    errors.append(f"{label}: declared codec/media type/dimensions differ from receipt")
                if (
                    atlas.get("minimum_panel_width_pixels") != receipt.get("minimum_panel_width_pixels")
                    or atlas.get("minimum_panel_height_pixels") != receipt.get("minimum_panel_height_pixels")
                    or atlas.get("legibility_policy") != receipt.get("legibility_policy")
                    or atlas.get("layout_policy") != receipt.get("layout_policy")
                    or atlas.get("decoder_runtime") != receipt.get("decoder_runtime")
                    or atlas.get("encoder_runtime") != receipt.get("encoder_runtime")
                    or atlas.get("minimum_panel_width_pixels", 0) < MINIMUM_ATLAS_PANEL_WIDTH_PIXELS
                    or atlas.get("minimum_panel_height_pixels", 0) < MINIMUM_ATLAS_PANEL_HEIGHT_PIXELS
                    or atlas.get("legibility_policy") != ATLAS_LEGIBILITY_POLICY
                ):
                    errors.append(f"{label}: declared panel legibility policy differs from the frozen builder receipt")
                spec_sources = spec.get("sources") if isinstance(spec.get("sources"), list) else []
                spec_source_ids = [item.get("artifact_id") for item in spec_sources if isinstance(item, dict)]
                if spec_source_ids != sources:
                    errors.append(f"{label}: source_artifact_ids must equal ordered compositor sources")
                for source_spec in spec_sources:
                    if not isinstance(source_spec, dict):
                        continue
                    source = binding_inventory.get(source_spec.get("artifact_id"), {}).get("artifact", {})
                    if source_spec.get("file_path") != source.get("file_path") or source_spec.get("file_sha256") != source.get("file_sha256"):
                        errors.append(f"{label}: compositor source file lock differs from inventory")
                    source_item = binding_inventory.get(source_spec.get("artifact_id"), {})
                    if (
                        source_spec.get("control_roles") != source_item.get("control_roles")
                        or source_spec.get("control_role") != source_item.get("control_role")
                        or not set(source_spec.get("control_roles", [])) <= ALLOWED_ATLAS_CONTROL_ROLES
                        or "label_copy" in source_spec.get("control_roles", [])
                    ):
                        errors.append(f"{label}: atlas control roles differ from inventory or include text-sensitive authority")
        atlas_by_unit.setdefault(unit_id, []).append(atlas)
    for artifact_id, item in binding_inventory.items():
        for classification in item.get("unit_classification", []) if isinstance(item.get("unit_classification"), list) else []:
            if classification.get("status") != "transported_via_atlas":
                continue
            unit_id = classification.get("generation_unit_id")
            if not any(artifact_id in atlas.get("source_artifact_ids", []) for atlas in atlas_by_unit.get(unit_id, [])):
                errors.append(f"bindings/{artifact_id}: transported_via_atlas lacks source mapping for {unit_id}")
    expected_roles = {
        "GLOBAL_LOOK_REFERENCE": {"global_look"},
        "CHARACTER_ASSET": {"identity", "wardrobe"},
        "PRODUCT_ASSET": {"product_geometry", "material_behavior", "label_copy"},
        "SCENE_ASSET": {"scene_canon"},
        "STORYBOARD_FRAME_LOOK_APPLIED_FINAL": {"storyboard"},
        "KEYFRAME_ANCHOR": {"keyframe_state", "keyframe_boundary"},
        "CONTROL_PREVIS_V2": {"control_previs", "camera_path", "blocking", "physical_motion"},
    }
    for unit in units:
        unit_id = unit.get("generation_unit_id")
        required_by_shot: dict[str, set[str]] = {}
        for shot_uid in unit.get("ordered_shot_uids", []):
            shot = shots_by_uid.get(shot_uid, {})
            ids = shot.get("required_control_artifact_ids")
            if not isinstance(ids, list) or not ids:
                errors.append(f"bindings/{unit_id}/{shot_uid}: required_control_artifact_ids must be non-empty")
                continue
            required_by_shot[shot_uid] = set(ids)
        selected_atlas_sources = {
            source_id
            for atlas in atlas_by_unit.get(unit_id, [])
            if atlas.get("atlas_id") in selected_ids_by_unit.get(unit_id, set())
            for source_id in atlas.get("source_artifact_ids", [])
        }
        delivered = selected_ids_by_unit.get(unit_id, set()) | selected_atlas_sources
        for shot_uid, required_ids in required_by_shot.items():
            missing_controls = required_ids - delivered
            if missing_controls:
                errors.append(f"bindings/{unit_id}/{shot_uid}: required controls not delivered {sorted(missing_controls)}")
            for artifact_id in required_ids:
                item = binding_inventory.get(artifact_id)
                if item is None:
                    errors.append(f"bindings/{unit_id}/{shot_uid}: unknown required control {artifact_id}")
                    continue
                classification = next((
                    value for value in item.get("unit_classification", [])
                    if isinstance(value, dict) and value.get("generation_unit_id") == unit_id
                ), {})
                if classification.get("status") not in {"relevant_selected", "transported_via_atlas"}:
                    errors.append(f"bindings/{unit_id}/{shot_uid}: required control {artifact_id} classified as {classification.get('status')}")
                allowed_roles = expected_roles.get(item.get("artifact_type"))
                actual_roles = set(item.get("control_roles", []))
                if allowed_roles is not None and (not actual_roles or not actual_roles <= allowed_roles):
                    errors.append(f"bindings/{unit_id}/{shot_uid}: required control {artifact_id} has wrong roles {sorted(actual_roles)}")
                affected = inventory.get(artifact_id, {}).get("artifact", {}).get("affected_shot_uids", [])
                if shot_uid not in affected:
                    errors.append(f"bindings/{unit_id}/{shot_uid}: required control {artifact_id} does not govern the shot")
    return errors, by_unit


PREFLIGHT_TO_COMPILE_CLASSIFICATION = {
    "selected_direct": "relevant_selected",
    "transported_via_atlas_planned": "transported_via_atlas",
    "inline_text": "relevant_selected",
    "irrelevant": "irrelevant_to_unit",
    "conflict_blocked": "conflicting_blocked",
    "superseded": "superseded_version",
}


def validate_preflight_compile_identity(
    plan: dict[str, Any],
    bindings: dict[str, Any],
    ir: dict[str, Any],
    inventory: dict[str, dict[str, Any]],
    compile_snapshot: dict[str, Any],
) -> list[str]:
    """Prove that P2 executed each P1 artifact decision, not merely the same counts."""
    errors: list[str] = []
    binding_items = {
        item.get("artifact", {}).get("artifact_id"): item
        for item in bindings.get("asset_inventory", [])
        if isinstance(item, dict) and isinstance(item.get("artifact"), dict)
    }
    selected_by_unit = {
        record.get("generation_unit_id"): {
            item.get("artifact_id") for item in record.get("bindings", []) if isinstance(item, dict)
        }
        for record in bindings.get("generation_unit_bindings", []) if isinstance(record, dict)
    }
    atlases = [item for item in bindings.get("atlas_records", []) if isinstance(item, dict)]
    ir_units = {
        unit.get("generation_unit_id"): unit
        for unit in ir.get("generation_units", []) if isinstance(unit, dict)
    }
    boundary_ref = ir.get("boundary_supplement_ref") if isinstance(ir.get("boundary_supplement_ref"), dict) else {}
    superseded = {
        item.get("artifact_id"): item
        for item in compile_snapshot.get("superseded_artifacts", []) if isinstance(item, dict)
    }
    planned_group_keys: set[tuple[str, str]] = set()

    def unit_classification(item: dict[str, Any], unit_id: Any) -> dict[str, Any]:
        return next((
            value for value in item.get("unit_classification", [])
            if isinstance(value, dict) and value.get("generation_unit_id") == unit_id
        ), {})

    for unit_index, unit in enumerate(plan.get("generation_units", []) if isinstance(plan.get("generation_units"), list) else []):
        if not isinstance(unit, dict):
            continue
        unit_id = unit.get("generation_unit_id")
        label = f"P1→P2/{unit_id or unit_index}"
        selected_ids = selected_by_unit.get(unit_id, set())
        expected_groups: dict[str, list[str]] = {}

        for decision_index, decision in enumerate(unit.get("artifact_decisions", []) if isinstance(unit.get("artifact_decisions"), list) else []):
            if not isinstance(decision, dict):
                continue
            ref = decision.get("artifact") if isinstance(decision.get("artifact"), dict) else {}
            artifact_id = ref.get("artifact_id")
            item_label = f"{label}.artifact_decisions[{decision_index}]/{artifact_id}"
            item = binding_items.get(artifact_id)
            effective_artifact_id = artifact_id
            if not isinstance(item, dict):
                old_entry = superseded.get(artifact_id)
                replacement_id = old_entry.get("superseded_by_artifact_id") if isinstance(old_entry, dict) else None
                replacement = binding_items.get(replacement_id)
                if (
                    decision.get("artifact_slot") == "previs_manifest"
                    and decision.get("decision") == "inline_text"
                    and isinstance(old_entry, dict)
                    and isinstance(replacement, dict)
                    and replacement.get("artifact_slot") == "previs_manifest"
                    and replacement.get("artifact", {}).get("owner_skill") == "ai-video-timed-animatic-previs-director"
                ):
                    item = replacement
                    effective_artifact_id = replacement_id
                else:
                    errors.append(f"{item_label}: P1 artifact missing from P2 binding inventory without the legal V1→V2 root supersession")
                    continue
            classification = unit_classification(item, unit_id)
            expected_status = PREFLIGHT_TO_COMPILE_CLASSIFICATION.get(decision.get("decision"))
            if classification.get("status") != expected_status:
                errors.append(f"{item_label}: P2 classification differs from the exact P1 decision")
            if classification.get("controlled_shot_uids") != decision.get("controlled_shot_uids"):
                errors.append(f"{item_label}: P2 unit scope differs from the exact P1 decision scope")
            if classification.get("preflight_planned_input_id") is not None:
                errors.append(f"{item_label}: existing P1 artifact must not impersonate a planned future input")
            if decision.get("decision") in PREFLIGHT_USED_DECISIONS and item.get("modality") != decision.get("transport_modality"):
                errors.append(f"{item_label}: P2 transport modality differs from P1")
            if item.get("control_roles") != decision.get("control_roles") or item.get("control_role") != decision.get("control_role"):
                errors.append(f"{item_label}: P2 control role set/primary role differs from P1")
            if decision.get("decision") in {"selected_direct", "inline_text"}:
                if effective_artifact_id not in selected_ids:
                    errors.append(f"{item_label}: P1 direct/inline artifact is not an actual selected P2 binding")
            elif decision.get("decision") == "transported_via_atlas_planned":
                if effective_artifact_id in selected_ids:
                    errors.append(f"{item_label}: P1 atlas source was silently changed to a direct P2 binding")
                group_id = decision.get("transport_group_id")
                if isinstance(group_id, str) and group_id:
                    expected_groups.setdefault(group_id, []).append(artifact_id)
                    planned_group_keys.add((str(unit_id), group_id))
            elif effective_artifact_id in selected_ids:
                errors.append(f"{item_label}: blocked/irrelevant/superseded P1 artifact became a selected P2 binding")

        for group_id, expected_source_ids in expected_groups.items():
            planned_group = next((
                group for group in unit.get("planned_atlas_groups", [])
                if isinstance(group, dict) and group.get("transport_group_id") == group_id
            ), {})
            records = [
                atlas for atlas in atlases
                if atlas.get("generation_unit_id") == unit_id
                and atlas.get("preflight_transport_group_id") == group_id
            ]
            if len(records) != 1:
                errors.append(f"{label}: preflight atlas group {group_id} must map to exactly one P2 atlas")
                continue
            atlas = records[0]
            if atlas.get("atlas_id") != planned_group.get("planned_atlas_id"):
                errors.append(f"{label}: P2 atlas identity differs from preflight group {group_id}")
            if atlas.get("source_artifact_ids") != expected_source_ids:
                errors.append(f"{label}: P2 atlas source identity/order differs from preflight group {group_id}")
            if atlas.get("atlas_id") not in selected_ids:
                errors.append(f"{label}: P2 atlas for preflight group {group_id} is not selected")
            preflight_build = planned_group.get("preflight_build") if isinstance(planned_group.get("preflight_build"), dict) else {}
            actual_build = {
                "file_sha256": atlas.get("file_sha256"),
                "file_bytes": atlas.get("file_bytes"),
                "width": atlas.get("width"), "height": atlas.get("height"),
                "codec": atlas.get("codec"), "media_type": atlas.get("media_type"),
                "decoder_runtime": atlas.get("decoder_runtime"),
                "encoder_runtime": atlas.get("encoder_runtime"),
            }
            if actual_build != preflight_build:
                errors.append(f"{label}: P2 atlas output/runtime differs from the P1 deterministic dry-build")

        future_inputs = unit.get("planned_future_inputs") if isinstance(unit.get("planned_future_inputs"), list) else []
        seen_future_bindings: set[str] = set()
        for future_index, future in enumerate(future_inputs):
            if not isinstance(future, dict):
                continue
            planned_input_id = future.get("planned_input_id")
            future_label = f"{label}.planned_future_inputs[{future_index}]/{planned_input_id}"
            matches: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
            for artifact_id, item in binding_items.items():
                classification = unit_classification(item, unit_id)
                if classification.get("preflight_planned_input_id") == planned_input_id:
                    matches.append((artifact_id, item, classification))
            if len(matches) != 1:
                errors.append(f"{future_label}: planned future input must map to exactly one actual P2 artifact")
                continue
            artifact_id, item, classification = matches[0]
            seen_future_bindings.add(artifact_id)
            if classification.get("status") != "relevant_selected" or artifact_id not in selected_ids:
                errors.append(f"{future_label}: future input must be an actual selected direct P2 binding")
            if classification.get("controlled_shot_uids") != future.get("controlled_shot_uids"):
                errors.append(f"{future_label}: actual P2 future-input scope differs from P1")
            if item.get("modality") != future.get("transport_modality"):
                errors.append(f"{future_label}: actual P2 future-input modality differs from P1")
            owner = item.get("artifact", {}).get("owner_skill") if isinstance(item.get("artifact"), dict) else None
            if owner != future.get("producer_skill"):
                errors.append(f"{future_label}: actual P2 future-input owner differs from P1")
            role = future.get("control_role")
            if role == "control_previs_v2":
                actual_v2 = ir_units.get(unit_id, {}).get("control_previs_artifact_id")
                if artifact_id != actual_v2 or item.get("control_role") != "control_previs":
                    errors.append(f"{future_label}: actual artifact is not the IR-bound V2 Control Previs")
            elif role == "keyframe_boundary_supplement":
                if artifact_id != boundary_ref.get("artifact_id") or item.get("control_role") != "keyframe_boundary":
                    errors.append(f"{future_label}: actual artifact is not the IR-bound K2 Boundary Supplement")
            elif role == "keyframe_boundary_anchor":
                if item.get("control_role") != "keyframe_boundary":
                    errors.append(f"{future_label}: actual artifact is not a K2 boundary anchor")

        mapped_future_ids = {
            classification.get("preflight_planned_input_id")
            for item in binding_items.values()
            for classification in item.get("unit_classification", []) if isinstance(classification, dict)
            if classification.get("generation_unit_id") == unit_id
            and classification.get("preflight_planned_input_id") is not None
        }
        expected_future_ids = {
            item.get("planned_input_id") for item in future_inputs if isinstance(item, dict)
        }
        if mapped_future_ids != expected_future_ids:
            errors.append(f"{label}: P2 future-input mappings must equal the complete P1 planned future set")

    actual_group_keys = {
        (str(atlas.get("generation_unit_id")), str(atlas.get("preflight_transport_group_id")))
        for atlas in atlases
    }
    if actual_group_keys != planned_group_keys:
        errors.append("P1→P2: atlas transport groups must exactly equal the P1 planned group set")
    return errors


def shot_block_expected(shot: dict[str, Any]) -> dict[str, Any]:
    return {
        "shot_uid": shot.get("shot_uid"),
        "target_time_window": f"{float(shot.get('target_start_seconds', 0)):.3f}-{float(shot.get('target_end_seconds', 0)):.3f}",
        "advertising_function": shot.get("advertising_function"),
        "visible_action_expression": shot.get("visible_action_expression"),
        "camera_composition": shot.get("camera_composition"),
        "blocking_spatial_change": shot.get("blocking_spatial_change"),
        "product_material_change": shot.get("product_material_change"),
        "ending_continuity_state": shot.get("ending_continuity_state"),
        "look_state_id": shot.get("look_state_id"),
        "look_state_prompt_full": shot.get("look_state_prompt_full"),
        "look_state_reference_asset_ids": shot.get("look_state_reference_asset_ids"),
        "shot_look_delta_prompt_full": shot.get("shot_look_delta", {}).get("prompt_full") if isinstance(shot.get("shot_look_delta"), dict) else None,
        "spoken_content": shot.get("spoken_content"),
        "on_screen_copy": shot.get("on_screen_copy"),
        "claim_provenance": shot.get("claim_provenance"),
        "storyboard_artifact_id": shot.get("storyboard_artifact_id"),
        "keyframe_artifact_ids": shot.get("keyframe_artifact_ids"),
        "control_previs_artifact_id": shot.get("control_previs_artifact_id"),
        "must_preserve": shot.get("must_preserve"),
        "must_avoid": shot.get("must_avoid"),
    }


def render_prompt_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return str(value)


def validate_rendered_block(block: dict[str, Any], expected: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    for field, value in expected.items():
        if block.get(field) != value:
            errors.append(f"{label}: {field} differs from IR")
    rendered = block.get("rendered_block")
    if not isinstance(rendered, str) or not rendered:
        return errors + [f"{label}: rendered_block required"]
    for field, value in expected.items():
        if value is not None and render_prompt_value(value) not in rendered:
            errors.append(f"{label}: rendered_block missing exact {field}")
    return errors


def validate_prompts(
    root: Path,
    ir: dict[str, Any],
    unit_doc: dict[str, Any],
    repair_doc: dict[str, Any],
    binding_units: dict[str, dict[str, Any]],
) -> list[str]:
    errors = validate_envelope(unit_doc, "unit_prompts", OWNER)
    errors.extend(validate_envelope(repair_doc, "repair_prompts", OWNER))
    grammar = ir.get("global_directing_prompt_full", "")
    look = ir.get("global_look", {}).get("exact_prompt_block", "") if isinstance(ir.get("global_look"), dict) else ""
    shots = {item.get("shot_uid"): item for item in ir.get("shots", []) if isinstance(item, dict)}
    units = ir.get("generation_units", [])
    prompts = unit_doc.get("generation_unit_prompts")
    if not isinstance(prompts, list):
        return errors + ["unit prompts: generation_unit_prompts must be an array"]
    by_unit = {item.get("generation_unit_id"): item for item in prompts if isinstance(item, dict)}
    if set(by_unit) != {item.get("generation_unit_id") for item in units if isinstance(item, dict)} or len(by_unit) != len(prompts):
        errors.append("unit prompts: IDs must exactly match IR units")
    for unit in units:
        unit_id = unit.get("generation_unit_id")
        item = by_unit.get(unit_id, {})
        prompt = item.get("prompt_text")
        if not isinstance(prompt, str):
            errors.append(f"unit prompts/{unit_id}: prompt_text required")
            prompt = ""
        if grammar not in prompt or look not in prompt:
            errors.append(f"unit prompts/{unit_id}: exact global blocks missing")
        for section in REQUIRED_PROMPT_SECTIONS:
            if section not in prompt:
                errors.append(f"unit prompts/{unit_id}: required section missing: {section}")
        if item.get("generation_mode") != "omni_reference_to_video":
            errors.append(f"unit prompts/{unit_id}: wrong generation mode")
        selected_bindings = [
            binding for binding in binding_units.get(unit_id, {}).get("bindings", []) if isinstance(binding, dict)
        ]
        selected_artifacts = {binding.get("artifact_id") for binding in selected_bindings}
        if set(item.get("bound_artifact_ids", [])) != selected_artifacts:
            errors.append(f"unit prompts/{unit_id}: bound_artifact_ids must equal selected bindings")
        expected_role_map = [{
            "artifact_id": binding.get("artifact_id"),
            "provider_alias": binding.get("provider_alias"),
            "control_roles": binding.get("control_roles"),
        } for binding in selected_bindings]
        if item.get("bound_artifact_roles") != expected_role_map:
            errors.append(f"unit prompts/{unit_id}: bound_artifact_roles must serialize every selected binding role exactly")
        for role_map in expected_role_map:
            role_text = json.dumps(role_map["control_roles"], ensure_ascii=False, separators=(",", ":"))
            if role_map["artifact_id"] not in prompt or role_map["provider_alias"] not in prompt or role_text not in prompt:
                errors.append(f"unit prompts/{unit_id}: prompt mapping omits alias or complete control_roles for {role_map['artifact_id']}")
        blocks = item.get("shot_blocks")
        if not isinstance(blocks, list):
            errors.append(f"unit prompts/{unit_id}: shot_blocks must be an array")
            blocks = []
        block_ids = [block.get("shot_uid") for block in blocks if isinstance(block, dict)]
        if block_ids != unit.get("ordered_shot_uids") or len(block_ids) != len(blocks):
            errors.append(f"unit prompts/{unit_id}: shot_blocks must cover exact unit shots in order")
        last_position = -1
        for block in blocks:
            shot_uid = block.get("shot_uid") if isinstance(block, dict) else None
            expected = shot_block_expected(shots.get(shot_uid, {}))
            if isinstance(block, dict):
                errors.extend(validate_rendered_block(block, expected, f"unit prompts/{unit_id}/{shot_uid}"))
                rendered = block.get("rendered_block", "")
                position = prompt.find(rendered) if isinstance(rendered, str) else -1
                if position < 0 or position <= last_position:
                    errors.append(f"unit prompts/{unit_id}: rendered shot blocks missing or out of order")
                last_position = position

    repairs = repair_doc.get("shot_repair_prompts")
    if not isinstance(repairs, list):
        return errors + ["repair prompts: shot_repair_prompts must be an array"]
    by_shot = {item.get("shot_uid"): item for item in repairs if isinstance(item, dict)}
    if set(by_shot) != set(shots) or len(by_shot) != len(repairs):
        errors.append("repair prompts: exactly one repair prompt per canonical shot required")
    for shot_uid, shot in shots.items():
        item = by_shot.get(shot_uid, {})
        prompt = item.get("prompt_text")
        if not isinstance(prompt, str):
            errors.append(f"repair prompts/{shot_uid}: prompt_text required")
            prompt = ""
        if grammar not in prompt or look not in prompt or shot.get("look_state_prompt_full", "") not in prompt or shot.get("shot_look_delta", {}).get("prompt_full", "") not in prompt:
            errors.append(f"repair prompts/{shot_uid}: complete global/State/Delta blocks missing")
        block = item.get("shot_block")
        if not isinstance(block, dict):
            errors.append(f"repair prompts/{shot_uid}: shot_block required")
        else:
            errors.extend(validate_rendered_block(block, shot_block_expected(shot), f"repair prompts/{shot_uid}"))
            if block.get("rendered_block") not in prompt:
                errors.append(f"repair prompts/{shot_uid}: rendered shot block missing from prompt")
        unit = next((value for value in units if shot_uid in value.get("ordered_shot_uids", [])), None)
        selected_bindings = [
            binding for binding in binding_units.get(unit.get("generation_unit_id"), {}).get("bindings", [])
            if unit and isinstance(binding, dict) and (not binding.get("controlled_shot_uids") or shot_uid in binding.get("controlled_shot_uids", []))
        ]
        selected = {binding.get("artifact_id") for binding in selected_bindings}
        if set(item.get("bound_artifact_ids", [])) != selected:
            errors.append(f"repair prompts/{shot_uid}: bound artifacts must be self-contained and exact")
        expected_role_map = [{
            "artifact_id": binding.get("artifact_id"),
            "provider_alias": binding.get("provider_alias"),
            "control_roles": binding.get("control_roles"),
        } for binding in selected_bindings]
        if item.get("bound_artifact_roles") != expected_role_map:
            errors.append(f"repair prompts/{shot_uid}: bound_artifact_roles must serialize every selected binding role exactly")
        for role_map in expected_role_map:
            role_text = json.dumps(role_map["control_roles"], ensure_ascii=False, separators=(",", ":"))
            if role_map["artifact_id"] not in prompt or role_map["provider_alias"] not in prompt or role_text not in prompt:
                errors.append(f"repair prompts/{shot_uid}: prompt missing alias or complete control_roles for {role_map['artifact_id']}")
        if item.get("generation_mode") != "omni_reference_to_video":
            errors.append(f"repair prompts/{shot_uid}: wrong generation mode")

    for rel in (
        "02_prompts/PROJECT_GLOBAL_BLOCK.md", "02_prompts/SEEDANCE_2_5_MASTER_PROMPT.md",
        "02_prompts/SEEDANCE_2_0_COMPATIBLE_RENDER.md",
    ):
        text = (root / rel).read_text(encoding="utf-8", errors="ignore")
        if grammar not in text or look not in text:
            errors.append(f"{rel}: exact global blocks missing")
    for rel in ("02_prompts/SEEDANCE_2_5_MASTER_PROMPT.md", "02_prompts/SEEDANCE_2_0_COMPATIBLE_RENDER.md"):
        master_text = (root / rel).read_text(encoding="utf-8", errors="ignore")
        for item in prompts:
            if isinstance(item, dict) and isinstance(item.get("prompt_text"), str) and item["prompt_text"] not in master_text:
                errors.append(f"{rel}: missing complete generation-unit prompt {item.get('generation_unit_id')}")
    target = (root / "02_prompts/SEEDANCE_2_5_MASTER_PROMPT.md").read_text(encoding="utf-8", errors="ignore").lower()
    if "forward-compatible" not in target and "前向兼容" not in target:
        errors.append("2.5 master prompt must disclose forward-compatible status")
    return errors


def scan_forbidden_payload(value: Any, path: str = "payload") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).lower()
            if any(token in normalized_key for token in FORBIDDEN_PAYLOAD_TOKENS):
                errors.append(f"{path}.{key}: forbidden endpoint-generation key")
            normalized_semantic_key = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(key)).lower()
            normalized_semantic_key = re.sub(r"[^a-z0-9]+", "_", normalized_semantic_key).strip("_")
            if any(token in normalized_semantic_key for token in FORBIDDEN_NORMALIZED_PAYLOAD_TOKENS):
                errors.append(f"{path}.{key}: forbidden normalized endpoint-generation key")
            errors.extend(scan_forbidden_payload(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(scan_forbidden_payload(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        lowered = value.lower()
        if any(token in lowered for token in FORBIDDEN_PAYLOAD_TOKENS):
            errors.append(f"{path}: forbidden endpoint/T2V generation value")
        normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value).lower()
        normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
        if any(token in normalized for token in FORBIDDEN_NORMALIZED_PAYLOAD_TOKENS):
            errors.append(f"{path}: forbidden normalized endpoint-generation value")
    return errors


def validate_payload(
    payload: dict[str, Any],
    ir: dict[str, Any],
    provider: dict[str, Any] | None,
    binding_units: dict[str, dict[str, Any]],
) -> list[str]:
    errors = validate_envelope(payload, "payload", OWNER)
    errors.extend(scan_forbidden_payload(payload, "payload"))
    if payload.get("schema_version") != "ai-video-provider-payload.v1" or payload.get("generation_mode") != "omni_reference_to_video":
        errors.append("payload: contract mismatch")
    status = payload.get("payload_status")
    allowed = {"executable", "blocked_unverified_provider", "blocked_unsupported_required_modality", "blocked_capacity", "blocked_conflict"}
    if status not in allowed:
        errors.append("payload: invalid payload_status")
    if provider:
        if payload.get("provider_profile_id") != provider.get("profile_id"):
            errors.append("payload: provider profile mismatch")
        if payload.get("documented_backend_profile_id") != provider.get("documented_backend_profile_id"):
            errors.append("payload: documented backend mismatch")
        if payload.get("provider_surface") != provider.get("surface"):
            errors.append("payload: provider surface mismatch")
    units = ir.get("generation_units", [])
    payload_units = payload.get("unit_payloads")
    if not isinstance(payload_units, list):
        errors.append("payload: unit_payloads must be an array")
        payload_units = []
    by_unit = {item.get("generation_unit_id"): item for item in payload_units if isinstance(item, dict)}
    if set(by_unit) != {item.get("generation_unit_id") for item in units if isinstance(item, dict)} or len(by_unit) != len(payload_units):
        errors.append("payload: units must exactly match IR")
    for unit in units:
        unit_id = unit.get("generation_unit_id")
        item = by_unit.get(unit_id, {})
        if item.get("generation_mode") != "omni_reference_to_video":
            errors.append(f"payload/{unit_id}: wrong generation mode")
        if item.get("target_duration_seconds") != unit.get("target_duration_seconds"):
            errors.append(f"payload/{unit_id}: target duration mismatch")
        expected_bindings = {
            binding.get("binding_id") for binding in binding_units.get(unit_id, {}).get("bindings", []) if isinstance(binding, dict)
        }
        if set(item.get("binding_ids", [])) != expected_bindings:
            errors.append(f"payload/{unit_id}: binding IDs mismatch")
    if status == "executable":
        if not provider or provider.get("surface_status") != "provider_schema_verified":
            errors.append("payload: executable requires schema-verified provider")
        if any(item.get("preflight_status") != "ready" for item in units if isinstance(item, dict)):
            errors.append("payload: executable requires ready units")
        if any(item.get("binding_status") != "ready" for item in binding_units.values() if isinstance(item, dict)):
            errors.append("payload: executable requires ready bindings")
    return errors


def input_lock_tuple(value: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(value.get(field) for field in (
        "artifact_id", "owner_skill", "version", "sha256", "file_path", "file_sha256",
        "artifact_record_locator", "artifact_record_file_sha256",
    ))


def validate_lockfile(package_root: Path, project_root: Path, lockfile: dict[str, Any], inventory: dict[str, dict[str, Any]]) -> list[str]:
    errors = validate_envelope(lockfile, "lockfile", OWNER)
    if lockfile.get("schema_version") != "ai-video-dependency-lockfile.v1":
        errors.append("lockfile: wrong schema_version")
    expected_inputs = {
        source_inventory_tuple(item) for item in inventory.values()
    }
    input_locks = lockfile.get("input_locks")
    if not isinstance(input_locks, list):
        return errors + ["lockfile: input_locks must be an array"]
    actual_inputs = {input_lock_tuple(item) for item in input_locks if isinstance(item, dict)}
    if actual_inputs != expected_inputs or len(actual_inputs) != len(input_locks):
        errors.append("lockfile: input locks must exactly equal IR identity/version/artifact/file inventory")
    for item in input_locks:
        if not isinstance(item, dict):
            continue
        if item.get("file_path") is not None:
            path, _, path_errors = read_hash_locked_file(
                project_root, item.get("file_path"), item.get("file_sha256"), f"lockfile/input/{item.get('artifact_id')}"
            )
            errors.extend(path_errors)
            if path_errors or path is None:
                errors.append(f"lockfile/input/{item.get('artifact_id')}: binary lock mismatch")
        _, _, record_errors = read_hash_locked_file(
            project_root, item.get("artifact_record_locator"), item.get("artifact_record_file_sha256"),
            f"lockfile/input/{item.get('artifact_id')}/record",
        )
        errors.extend(record_errors)
        if record_errors:
            errors.append(f"lockfile/input/{item.get('artifact_id')}: artifact record lock mismatch")
    output_locks = lockfile.get("output_locks")
    if not isinstance(output_locks, list):
        return errors + ["lockfile: output_locks must be an array"]
    output_paths = [item.get("file_path") for item in output_locks if isinstance(item, dict)]
    if set(output_paths) != EXPECTED_OUTPUT_LOCK_PATHS or len(output_paths) != len(set(output_paths)):
        errors.append("lockfile: output locks must exactly cover every required non-self output")
    source_ids = set(inventory)
    for item in output_locks:
        if not isinstance(item, dict):
            errors.append("lockfile: output lock must be an object")
            continue
        path, _, path_errors = read_hash_locked_file(
            package_root, item.get("file_path"), item.get("file_sha256"), f"lockfile/output/{item.get('artifact_id')}"
        )
        errors.extend(path_errors)
        if path_errors or path is None:
            errors.append(f"lockfile/output/{item.get('artifact_id')}: file lock mismatch")
        if not set(item.get("depends_on_artifact_ids", [])).issubset(source_ids):
            errors.append(f"lockfile/output/{item.get('artifact_id')}: unknown dependency ID")
    return errors


ROUTE_OWNERS = {
    "prompt_binding_or_serialization": OWNER,
    "canon_camera_intent_change": SHOT_OWNER,
    "storyboard_static_realization_mismatch": STORYBOARD_OWNER,
    "global_look": LOOK_OWNER,
    "keyframe_visual_state": KEYFRAME_OWNER,
    "dynamic_camera_blocking_physics": PREVIS_OWNER,
    "shot_story_timing_function": SHOT_OWNER,
    "stochastic_model_failure": OWNER,
}
WORKFLOW_OWNERS = {
    SHOT_OWNER, LOOK_OWNER, STORYBOARD_OWNER, PREVIS_OWNER, KEYFRAME_OWNER,
    OWNER,
}
ASSET_ARTIFACT_TYPE_TOKENS = {"CHARACTER", "PRODUCT", "PACKAGING", "MATERIAL", "SCENE"}
REGISTERED_ASSET_OWNERS = {
    CASTING_OWNER, CHARACTER_FINAL_OWNER, SINGLE_FACE_OWNER, MULTI_ANGLE_OWNER,
    PACKAGING_OWNER, MATERIAL_OWNER, SCENE_OWNER,
}


def validate_feedback(
    feedback: dict[str, Any],
    ir: dict[str, Any],
    inventory: dict[str, dict[str, Any]],
) -> list[str]:
    errors = validate_envelope(feedback, "feedback", OWNER)
    if feedback.get("schema_version") != "ai-video-feedback-route.v1":
        errors.append("feedback: wrong schema_version")
    if feedback.get("package_mode") != ir.get("package_mode"):
        errors.append("feedback: package_mode differs from IR")
    if feedback.get("revision_anchor") != ir.get("revision_anchor"):
        errors.append("feedback: revision anchor differs from IR")
    if feedback.get("independent_output_qc") is not False or feedback.get("edit_action") != "none" or feedback.get("music_action") != "none":
        errors.append("feedback: independent QC, editing, and music actions are forbidden")
    routes = feedback.get("feedback_routes")
    if not isinstance(routes, list):
        errors.append("feedback: feedback_routes must be an array")
        routes = []
    if ir.get("package_mode") == "compile" and routes:
        errors.append("feedback: initial compile must not fabricate review feedback")
    if ir.get("package_mode") == "revise" and not routes:
        errors.append("feedback: revise mode requires feedback routes")
    canonical_shots = set(ir.get("ordered_shot_uids", []))
    boundary_id = ir.get("boundary_supplement_ref", {}).get("artifact_id") if isinstance(ir.get("boundary_supplement_ref"), dict) else None
    v2_ids = {
        item.get("control_previs_artifact_id") for item in ir.get("generation_units", [])
        if isinstance(item, dict) and item.get("control_previs_artifact_id")
    }
    existing_asset_owners = {
        item.get("artifact", {}).get("owner_skill")
        for item in inventory.values()
        if isinstance(item, dict)
        and isinstance(item.get("artifact"), dict)
        and isinstance(item.get("artifact_type"), str)
        and any(token in item["artifact_type"].upper() for token in ASSET_ARTIFACT_TYPE_TOKENS)
        and item.get("artifact", {}).get("owner_skill") in REGISTERED_ASSET_OWNERS
    }
    existing_asset_owners = {
        owner for owner in existing_asset_owners if isinstance(owner, str) and owner
    }
    route_requests: list[dict[str, Any]] = []
    for index, route in enumerate(routes):
        label = f"feedback.routes[{index}]"
        if not isinstance(route, dict):
            errors.append(f"{label}: must be an object")
            continue
        scope = route.get("diagnosis_scope")
        owner = route.get("owner_skill")
        if scope in ROUTE_OWNERS and owner != ROUTE_OWNERS[scope]:
            errors.append(f"{label}: wrong sole owner for {scope}")
        if scope == "identity_product_material_scene_canon" and owner not in existing_asset_owners:
            errors.append(f"{label}: identity/product/material/scene issue must route to an existing asset owner")
        shots = route.get("affected_shot_uids")
        if not isinstance(shots, list) or not shots or not set(shots).issubset(canonical_shots):
            errors.append(f"{label}: affected shots invalid")
        affected_artifact_ids = route.get("affected_artifact_ids")
        if (
            not isinstance(affected_artifact_ids, list)
            or not all(isinstance(artifact_id, str) and artifact_id in inventory for artifact_id in affected_artifact_ids)
            or len(affected_artifact_ids) != len(set(affected_artifact_ids))
        ):
            errors.append(f"{label}: affected_artifact_ids must be unique existing Canon inventory IDs")
            affected_artifact_ids = []
        affected_control_roles = route.get("affected_control_roles")
        if (
            not isinstance(affected_control_roles, list)
            or not all(isinstance(role, str) and role for role in affected_control_roles)
            or len(affected_control_roles) != len(set(affected_control_roles))
        ):
            errors.append(f"{label}: affected_control_roles must be unique non-empty strings")
            affected_control_roles = []
        authorized_role_union = {
            role
            for artifact_id in affected_artifact_ids
            for role in inventory.get(artifact_id, {}).get("control_roles", [])
            if isinstance(role, str)
        }
        if not isinstance(route.get("evidence_comparison"), list) or not route["evidence_comparison"]:
            errors.append(f"{label}: evidence comparison required")
        action = route.get("action")
        upstream = route.get("upstream_change_request")
        owned_diff = route.get("owned_diff")
        upstream_scope = scope not in {"prompt_binding_or_serialization", "stochastic_model_failure"}
        if upstream_scope:
            if not affected_artifact_ids:
                errors.append(f"{label}: upstream-owned defect requires at least one affected artifact")
            for artifact_id in affected_artifact_ids:
                artifact = inventory.get(artifact_id, {}).get("artifact", {})
                if artifact.get("owner_skill") != owner:
                    errors.append(f"{label}: affected artifact {artifact_id} is not owned by the routed sole owner")
            if not affected_control_roles:
                errors.append(f"{label}: upstream-owned defect requires at least one affected control role")
            elif not set(affected_control_roles) <= authorized_role_union:
                errors.append(f"{label}: affected_control_roles exceed the affected artifacts' authorized role union")
            if scope == "identity_product_material_scene_canon":
                for artifact_id in affected_artifact_ids:
                    artifact_type = inventory.get(artifact_id, {}).get("artifact_type")
                    if not isinstance(artifact_type, str) or not any(
                        token in artifact_type.upper() for token in ASSET_ARTIFACT_TYPE_TOKENS
                    ):
                        errors.append(f"{label}: affected asset {artifact_id} is not a character/product/material/scene Canon artifact")
            if action != "issue_upstream_change_request" or not isinstance(upstream, dict) or owned_diff is not None:
                errors.append(f"{label}: upstream-owned defect requires one upstream request and no prompt diff")
            else:
                route_requests.append(upstream)
                if upstream.get("target_owner_skill") != owner:
                    errors.append(f"{label}: upstream request target differs from owner")
                if upstream.get("affected_shot_uids") != shots:
                    errors.append(f"{label}: upstream request Shot scope differs from route")
                if upstream.get("affected_artifact_ids") != affected_artifact_ids:
                    errors.append(f"{label}: upstream request artifact scope differs from route")
                if upstream.get("affected_control_roles") != affected_control_roles:
                    errors.append(f"{label}: upstream request control-role scope differs from route")
        elif scope == "prompt_binding_or_serialization":
            if affected_artifact_ids:
                errors.append(f"{label}: prompt-owned diagnosis must not claim upstream artifact ownership")
            if affected_control_roles:
                errors.append(f"{label}: prompt-owned diagnosis must have empty affected_control_roles")
            if action not in {"revise_prompt_owned_surface", "shorten_generation_unit_after_preflight_revision"}:
                errors.append(f"{label}: prompt-owned defect action invalid")
            if not isinstance(owned_diff, dict) or not owned_diff:
                errors.append(f"{label}: prompt-owned revision requires non-empty owned_diff")
            if upstream is not None:
                errors.append(f"{label}: prompt-owned revision must not issue an upstream request")
        elif scope == "stochastic_model_failure":
            if affected_artifact_ids:
                errors.append(f"{label}: stochastic retry must not claim an affected artifact")
            if affected_control_roles:
                errors.append(f"{label}: stochastic retry must have empty affected_control_roles")
            if action != "retry_exact_package" or owned_diff is not None or upstream is not None:
                errors.append(f"{label}: stochastic failure requires exact-package retry with no diff or request")
            if route.get("invalidated_artifact_ids") != []:
                errors.append(f"{label}: stochastic retry must not invalidate artifacts")
        if action == "shorten_generation_unit_after_preflight_revision":
            required_invalidations = {boundary_id, *v2_ids}
            if not required_invalidations <= set(route.get("invalidated_artifact_ids", [])):
                errors.append(f"{label}: unit-plan change must invalidate K2 and all V2 controls")
        hashes = route.get("unaffected_artifact_hashes")
        if not isinstance(hashes, dict) or any(not is_hash(value) for value in hashes.values()):
            errors.append(f"{label}: unaffected artifact hashes invalid")
    root_requests = feedback.get("upstream_change_requests")
    if not isinstance(root_requests, list):
        errors.append("feedback: upstream_change_requests must be an array")
    else:
        def request_map(values: list[Any], label: str) -> dict[str, dict[str, Any]]:
            result: dict[str, dict[str, Any]] = {}
            for index, value in enumerate(values):
                if not isinstance(value, dict):
                    errors.append(f"{label}[{index}]: change request must be an object")
                    continue
                request_id = value.get("request_id")
                if not isinstance(request_id, str) or not request_id:
                    errors.append(f"{label}[{index}]: non-empty request_id required")
                    continue
                if request_id in result:
                    errors.append(f"{label}: duplicate request_id {request_id}")
                result[request_id] = value
            return result
        root_by_id = request_map(root_requests, "feedback.upstream_change_requests")
        route_by_id = request_map(route_requests, "feedback.route_change_requests")
        if root_by_id != route_by_id:
            errors.append("feedback: upstream_change_requests must exactly equal all route requests with no missing or orphan entries")
    return errors


def validate_revision_anchor(root: Path, ir: dict[str, Any], feedback: dict[str, Any], lockfile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    anchor = ir.get("revision_anchor")
    if ir.get("package_mode") == "compile":
        if anchor is not None or feedback.get("revision_anchor") is not None:
            errors.append("revision: initial compile must have null revision anchors")
        return errors
    if not isinstance(anchor, dict):
        return ["revision: revise mode requires an immutable previous-package anchor"]
    previous_ir, previous_ir_errors = read_hash_locked_json(
        root, anchor.get("previous_ir_path"), anchor.get("previous_ir_file_sha256"), "revision/previous IR"
    )
    errors.extend(previous_ir_errors)
    previous_lock, previous_lock_errors = read_hash_locked_json(
        root, anchor.get("previous_lockfile_path"), anchor.get("previous_lockfile_file_sha256"), "revision/previous lockfile"
    )
    errors.extend(previous_lock_errors)
    _, _, diff_errors = read_hash_locked_file(
        root, anchor.get("revision_diff_path"), anchor.get("revision_diff_file_sha256"), "revision/diff"
    )
    errors.extend(diff_errors)
    if previous_ir is not None and anchor.get("previous_package_ref") != artifact_ref(previous_ir):
        errors.append("revision: previous_package_ref differs from hash-locked previous IR")
    if previous_ir is not None:
        previous_version = semver_tuple(previous_ir.get("version"))
        current_version = semver_tuple(ir.get("version"))
        if previous_version is None or current_version is None or current_version <= previous_version:
            errors.append("revision: current IR version must exceed previous IR version")
    changed = anchor.get("changed_output_paths")
    unchanged = anchor.get("unchanged_output_paths")
    if not isinstance(changed, list) or not isinstance(unchanged, list):
        return errors + ["revision: changed/unchanged output paths must be arrays"]
    changed_set, unchanged_set = set(changed), set(unchanged)
    if changed_set & unchanged_set or changed_set | unchanged_set != EXPECTED_OUTPUT_LOCK_PATHS:
        errors.append("revision: changed and unchanged paths must form an exact disjoint output partition")
    if anchor.get("revision_diff_path") not in changed_set or IR_PATH not in changed_set or FEEDBACK not in changed_set:
        errors.append("revision: IR, feedback route, and machine-readable diff must be declared changed")
    current_outputs = {
        item.get("file_path"): item.get("file_sha256")
        for item in lockfile.get("output_locks", []) if isinstance(item, dict)
    }
    previous_outputs = {
        item.get("file_path"): item.get("file_sha256")
        for item in previous_lock.get("output_locks", []) if isinstance(item, dict)
    } if isinstance(previous_lock, dict) else {}
    if set(previous_outputs) != EXPECTED_OUTPUT_LOCK_PATHS:
        errors.append("revision: previous lockfile does not cover the complete prior package")
    for path in unchanged_set:
        if current_outputs.get(path) != previous_outputs.get(path):
            errors.append(f"revision: unchanged output drifted from previous lock: {path}")
    for path in changed_set:
        if current_outputs.get(path) == previous_outputs.get(path):
            errors.append(f"revision: declared changed output has no byte-level diff: {path}")
    expected_unaffected = {path: previous_outputs.get(path) for path in sorted(unchanged_set)}
    for index, route in enumerate(feedback.get("feedback_routes", []) if isinstance(feedback.get("feedback_routes"), list) else []):
        if isinstance(route, dict) and route.get("unaffected_artifact_hashes") != expected_unaffected:
            errors.append(f"revision: feedback route {index} unaffected hashes do not equal prior output locks")
    return errors


def _validate_package(root: Path, project_root: Path, project_canon_manifest: Path | None) -> list[str]:
    errors: list[str] = []
    required_json_files = [
        rel for rel in JSON_FILES
        if rel != MANIFEST_RECEIPT or project_canon_manifest is not None or (root / rel).is_file()
    ]
    for rel in required_json_files + TEXT_FILES:
        if not (root / rel).is_file():
            errors.append(f"missing required file: {rel}")
    if errors:
        return errors

    documents: dict[str, dict[str, Any]] = {}
    for rel in required_json_files:
        try:
            value = load_json(root / rel)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{rel}: JSON read failed: {exc}")
            continue
        if not isinstance(value, dict):
            errors.append(f"{rel}: top-level JSON must be an object")
            continue
        documents[rel] = value
    if errors:
        return errors

    reference_root = Path(__file__).resolve().parents[1] / "references"
    for rel, schema_name in RUNTIME_SCHEMA_BY_FILE.items():
        try:
            schema = load_json(reference_root / schema_name)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{rel}: runtime schema unreadable: {exc}")
            continue
        for schema_error in validate_instance(documents[rel], schema, schema):
            errors.append(f"{rel}: schema: {schema_error}")
    if errors:
        return errors

    pre_snapshot = documents[PREFLIGHT_SNAPSHOT]
    compile_snapshot = documents[COMPILE_SNAPSHOT]
    pre_snapshot_errors, pre_active = validate_manifest_snapshot(pre_snapshot, "preflight_manifest_snapshot")
    compile_snapshot_errors, compile_active = validate_manifest_snapshot(compile_snapshot, "compile_manifest_snapshot")
    errors.extend(pre_snapshot_errors)
    errors.extend(compile_snapshot_errors)
    superseded_ids = {
        item.get("artifact_id") for item in compile_snapshot.get("superseded_artifacts", []) if isinstance(item, dict)
    }
    silently_removed = set(pre_active) - set(compile_active) - superseded_ids
    if silently_removed:
        errors.append(f"compile manifest silently removed preflight assets without supersession: {sorted(silently_removed)}")

    plan = documents[PREFLIGHT_PLAN]
    plan_errors, _ = validate_preflight_plan(root, plan, pre_snapshot, pre_active)
    errors.extend(plan_errors)
    ir = documents[IR_PATH]
    ir_errors, inventory, units = validate_ir(root, ir, compile_snapshot, compile_active, plan)
    errors.extend(ir_errors)
    errors.extend(validate_upstream_semantics(project_root, ir, inventory, plan, pre_active, compile_snapshot))

    owned_docs = {
        PREFLIGHT_PLAN: plan, IR_PATH: ir, MODEL_CAPS: documents[MODEL_CAPS],
        PROVIDER_CAPS: documents[PROVIDER_CAPS], LOCKFILE: documents[LOCKFILE],
        BINDINGS: documents[BINDINGS], UNIT_PROMPTS: documents[UNIT_PROMPTS],
        REPAIR_PROMPTS: documents[REPAIR_PROMPTS], PAYLOAD: documents[PAYLOAD], FEEDBACK: documents[FEEDBACK],
    }
    for rel, value in owned_docs.items():
        errors.extend(validate_envelope(value, rel, OWNER))
        if value.get("approval_status") not in {"assistant_validated", "user_approved", "blocked"}:
            errors.append(f"{rel}: final package artifact must be validated, approved, or blocked")
    owned_doc_ids = {value.get("artifact_id") for value in owned_docs.values()}
    additional_owned_ids = {
        artifact_id for artifact_id, item in inventory.items()
        if item.get("artifact", {}).get("owner_skill") == OWNER and artifact_id not in owned_doc_ids
    }
    allowed_additional = {
        artifact_id for artifact_id in additional_owned_ids
        if inventory.get(artifact_id, {}).get("artifact_type") == "DETERMINISTIC_REFERENCE_ATLAS"
    }
    if additional_owned_ids != allowed_additional:
        errors.append(f"Prompt-owned compile artifacts lack an explicit output contract: {sorted(additional_owned_ids - allowed_additional)}")
    if project_canon_manifest is not None:
        receipt = documents.get(MANIFEST_RECEIPT)
        if receipt is None:
            errors.append("optional Project Canon integration requires MANIFEST_UPDATE_RECEIPT.json")
        else:
            errors.extend(validate_manifest_update_receipt(receipt, compile_snapshot, owned_docs, allowed_additional))
            errors.extend(validate_actual_post_canon(
                root, project_root, project_canon_manifest, pre_snapshot, compile_snapshot,
                receipt, owned_docs, allowed_additional,
            ))

    capability_errors, provider, effective_limits = validate_capabilities(root, documents[MODEL_CAPS], documents[PROVIDER_CAPS])
    errors.extend(capability_errors)
    errors.extend(validate_preflight_decision_matrix(
        plan, pre_active, provider, effective_limits, project_root=project_root
    ))
    if provider:
        if plan.get("provider_profile_id") != provider.get("profile_id") or plan.get("documented_backend_profile_id") != provider.get("documented_backend_profile_id"):
            errors.append("preflight_plan: provider/backend profile differs from verified capability artifact")
    max_duration = effective_limits.get("max_duration_seconds")
    planned_by_unit = {
        item.get("generation_unit_id"): item.get("planned_reference_counts")
        for item in plan.get("generation_units", []) if isinstance(item, dict)
    }
    supported_modalities = set(provider.get("supported_modalities", [])) if isinstance(provider, dict) else set()
    for planned_unit in plan.get("generation_units", []) if isinstance(plan.get("generation_units"), list) else []:
        if not isinstance(planned_unit, dict):
            continue
        unit_id = planned_unit.get("generation_unit_id")
        counts = planned_unit.get("planned_reference_counts") if isinstance(planned_unit.get("planned_reference_counts"), dict) else {}
        for modality, limit_key in (("image", "max_image_inputs"), ("video", "max_video_inputs"), ("audio", "max_audio_inputs")):
            count = counts.get(modality)
            limit = effective_limits.get(limit_key)
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                errors.append(f"preflight_plan/{unit_id}: invalid planned {modality} count")
            elif modality not in supported_modalities and count > 0:
                errors.append(f"preflight_plan/{unit_id}: planned unsupported modality {modality}")
            elif not is_number(limit) or count > float(limit):
                errors.append(f"preflight_plan/{unit_id}: planned {modality} count exceeds effective capacity")
            if modality in set(planned_unit.get("required_modalities", [])) and count < 1:
                errors.append(f"preflight_plan/{unit_id}: required modality {modality} has zero planned inputs")
        total_limit = effective_limits.get("max_total_multimodal_inputs")
        if not is_number(total_limit) or counts.get("total_multimodal", -1) > float(total_limit):
            errors.append(f"preflight_plan/{unit_id}: planned total count exceeds effective capacity")
    for unit in units:
        if max_duration is None:
            errors.append(f"IR/{unit.get('generation_unit_id')}: unknown duration capacity")
        elif is_number(unit.get("target_duration_seconds")) and float(unit["target_duration_seconds"]) > float(max_duration) + TIME_TOLERANCE:
            errors.append(f"IR/{unit.get('generation_unit_id')}: duration exceeds effective backend capacity")

    binding_errors, binding_units = validate_bindings(project_root, documents[BINDINGS], inventory, units, ir.get("shots", []), provider, effective_limits)
    errors.extend(binding_errors)
    errors.extend(validate_preflight_compile_identity(plan, documents[BINDINGS], ir, inventory, compile_snapshot))
    for unit_id, planned_counts in planned_by_unit.items():
        binding_record = binding_units.get(unit_id, {})
        if binding_record.get("selected_counts") != planned_counts:
            errors.append(f"bindings/{unit_id}: selected counts must exactly close the P1 planned reference budget")
    errors.extend(validate_prompts(root, ir, documents[UNIT_PROMPTS], documents[REPAIR_PROMPTS], binding_units))
    errors.extend(validate_payload(documents[PAYLOAD], ir, provider, binding_units))
    errors.extend(validate_lockfile(root, project_root, documents[LOCKFILE], inventory))
    errors.extend(validate_feedback(documents[FEEDBACK], ir, inventory))
    errors.extend(validate_revision_anchor(root, ir, documents[FEEDBACK], documents[LOCKFILE]))

    if ir.get("package_status") == "compiled":
        if ir.get("approval_status") not in {"assistant_validated", "user_approved"}:
            errors.append("compiled IR must be validated or approved")
        if documents[PAYLOAD].get("payload_status") != "executable":
            errors.append("compiled IR requires executable payload")
    return errors


def validate_package(root: Path, project_root: Path | None = None, project_canon_manifest: Path | None = None) -> list[str]:
    effective_project_root = project_root.resolve() if project_root is not None else root.resolve()
    try:
        root.resolve().relative_to(effective_project_root)
    except ValueError:
        return ["package root must be inside --project-root"]
    try:
        return _validate_package(root, effective_project_root, project_canon_manifest)
    except (TypeError, KeyError, AttributeError, ValueError, OverflowError) as exc:
        return [f"malformed prompt package rejected safely: {type(exc).__name__}: {exc}"]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_root", type=Path)
    parser.add_argument("--input-root", "--project-root", dest="input_root", required=True, type=Path)
    parser.add_argument(
        "--project-canon-manifest", type=Path,
        help="optional actual post-write registry used only for Project Canon integration proof",
    )
    args = parser.parse_args(argv[1:])
    errors = validate_package(
        args.package_root.resolve(), args.input_root.resolve(),
        args.project_canon_manifest.resolve() if args.project_canon_manifest is not None else None,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"FAILED: {len(errors)} error(s)")
        return 1
    print("PASS: Omni-reference prompt package contract is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
