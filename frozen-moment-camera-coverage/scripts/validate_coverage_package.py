#!/usr/bin/env python3
"""Validate frozen-moment prompt, stage, partial, and final delivery evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import struct
import sys
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

import inspection_runtime
import resolve_worker_image as worker_resolver


MANIFEST_SCHEMA = "frozen_moment_coverage_manifest.v1"
TERMINALS = {"prompt_package_ready", "package_ready", "partial_handoff_ready"}
ACTIVE_STATES = {
    "prompts_locked",
    "generation_in_progress",
    "inspection_pending",
    "view_approved",
    "repair_required",
    "blocked_attempt_budget",
    "all_required_views_approved",
    "coverage_approved",
    "handoff_finalized",
}
REQUIRED_HARD_CHECKS = {
    "identity_age",
    "pose_skeleton_balance",
    "head_gaze_expression",
    "contact_topology",
    "wardrobe_props_asymmetry",
    "scene_topology",
    "temporal_state",
    "world_space_lighting",
    "camera_family_distinctness",
    "reveal_occlusion",
    "claim_evidence_honesty",
    "source_anchor_retention",
    "no_mirror_crop_zoom_duplicate",
    "no_unsupported_salient_invention",
}
DEFAULT_BINS = {
    "minimum_ring": [0.0, 90.0, 180.0, 270.0],
    "robust_ring": [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0],
}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
PROMPT_CONTROL_OVERRIDE_RE = re.compile(
    r"\b(?:ignore|disregard|override|bypass|forget)\b|"
    r"\b(?:turn|rotate|repose)\s+(?:the\s+)?(?:subject|person|character)\b|"
    r"\b(?:replace|change|alter)\b.{0,24}\b(?:frozen\s+)?(?:pose|action|gaze)\b|"
    r"\bcamera[- ]only\s+contract\b.{0,24}\b(?:no\s+longer|does\s+not|doesn't|need\s+not)\b.{0,12}\bappl(?:y|ies)\b|"
    r"\b(?:subject|person|character)\b.{0,48}\b(?:face|look)\b.{0,48}\b(?:each|every|all|target)\b.{0,16}\bcamera\b|"
    r"忽略|绕过|(?:覆盖|取消).{0,12}(?:锁|约束|规则)|不(?:要|必)遵守|"
    r"让.{0,8}(?:人物|主体|角色).{0,8}(?:转身|转头|改变|改成)|"
    r"(?:人物|主体|角色).{0,24}(?:正对|面向|看向|注视).{0,20}(?:每个|各个|所有|目标)(?:目标)?.{0,4}(?:机位|相机|镜头)|"
    r"原来.{0,16}(?:无需|不用|不必).{0,12}(?:保留|遵守|适用)|"
    r"改成.{0,8}(?:新的?)?(?:动作|姿态|视线)",
    re.IGNORECASE,
)
REFERENCE_ROLES = {
    "moment_anchor", "identity_anchor", "wardrobe_anchor",
    "scene_topology_anchor", "look_anchor",
}


class ContractError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path, code: str = "package_json_invalid") -> dict[str, Any]:
    if not path.is_file():
        raise ContractError(code, f"missing JSON artifact: {path}")
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ContractError(code, f"JSON must be UTF-8/LF without BOM: {path}")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(code, f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(code, f"JSON root must be an object: {path}")
    return value


def resolve_artifact(root: Path, raw: Any, code: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ContractError(code, "artifact path is missing")
    path = Path(raw)
    candidate = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ContractError(code, f"artifact escapes run root: {raw}") from exc
    if candidate.is_symlink():
        raise ContractError(code, f"artifact cannot be a symlink: {candidate}")
    return candidate


def require_sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise ContractError("package_hash_invalid", f"invalid SHA-256 field: {field}")
    return value


def reject_prompt_control_text(value: Any, field_path: str) -> None:
    if isinstance(value, str):
        if PROMPT_CONTROL_OVERRIDE_RE.search(value):
            raise ContractError("blocked_prompt_contract_override", f"{field_path} attempts to override the camera-only contract")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            reject_prompt_control_text(item, f"{field_path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            reject_prompt_control_text(item, f"{field_path}.{key}")


def validate_evidence_authority(job: dict[str, Any], source: dict[str, Any], moment: dict[str, Any], ledger: Any) -> None:
    classes = {"observed", "source_corroborated", "inferred", "unknown", "approved_canon"}
    if not isinstance(ledger, dict) or set(ledger) != classes:
        raise ContractError("blocked_evidence_authority_invalid", "evidence ledger classes differ")
    reference_ids = source.get("reference_ids", [])
    if not isinstance(reference_ids, list) or not all(isinstance(item, str) and item for item in reference_ids):
        raise ContractError("blocked_evidence_authority_invalid", "source reference IDs are invalid")
    reference_set = set(reference_ids)
    if len(reference_set) != len(reference_ids):
        raise ContractError("blocked_evidence_authority_invalid", "source reference IDs are not unique")
    for evidence_class, entries in ledger.items():
        if not isinstance(entries, list):
            raise ContractError("blocked_evidence_authority_invalid", f"{evidence_class} ledger is not a list")
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("source_ids"), list):
                raise ContractError("blocked_evidence_authority_invalid", f"{evidence_class} entry is invalid")
            ordered = entry["source_ids"]
            source_ids = set(ordered)
            if not source_ids or len(source_ids) != len(ordered) or not all(isinstance(item, str) and item for item in ordered):
                raise ContractError("blocked_evidence_authority_invalid", "evidence authority IDs must be non-empty unique strings")
            if evidence_class == "observed" and not source_ids <= reference_set:
                raise ContractError("blocked_evidence_authority_invalid", "observed evidence lacks frozen source bytes")
            if evidence_class == "source_corroborated" and (len(source_ids) < 2 or not source_ids <= reference_set):
                raise ContractError("blocked_evidence_authority_invalid", "source-corroborated evidence requires two frozen sources")
            if evidence_class == "inferred" and not source_ids <= reference_set | {"model_inference", "text_brief"}:
                raise ContractError("blocked_evidence_authority_invalid", "inferred evidence cites an unauthorized authority")
            if evidence_class == "unknown" and ordered != ["unobserved"]:
                raise ContractError("blocked_evidence_authority_invalid", "unknown evidence must cite exactly unobserved")
            if evidence_class == "approved_canon" and not source_ids <= {"user_approval", "main_inspection"}:
                raise ContractError("blocked_evidence_authority_invalid", "approved Canon cites an unauthorized authority")
            if evidence_class == "approved_canon" and "main_inspection" in source_ids and not source.get("anchor_inspection_sha256"):
                raise ContractError("blocked_evidence_authority_invalid", "main inspection authority is not bound")
    if job.get("input_mode") == "text_anchor" and not reference_set and (ledger["observed"] or ledger["source_corroborated"]):
        raise ContractError("blocked_evidence_authority_invalid", "unrendered text cannot claim image observation")
    if moment.get("canon_status") == "approved_canon" and not ledger["approved_canon"]:
        raise ContractError("blocked_evidence_authority_invalid", "approved Canon status lacks approval evidence")


def normalize_angle(value: float) -> float:
    return (float(value) % 360.0 + 360.0) % 360.0


def circular_diff(left: float, right: float) -> float:
    return abs(((normalize_angle(left) - normalize_angle(right) + 180.0) % 360.0) - 180.0)


def inspect_png(path: Path) -> tuple[int, int, str]:
    if not path.is_file():
        raise ContractError("image_missing", f"image missing: {path}")
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != PNG_SIGNATURE or data[12:16] != b"IHDR":
        raise ContractError("image_invalid", f"invalid PNG: {path}")
    width, height = struct.unpack(">II", data[16:24])
    if width <= 0 or height <= 0:
        raise ContractError("image_invalid", f"invalid PNG dimensions: {width}x{height}")
    return width, height, sha256_bytes(data)


def validate_plan_reference_bundle(root: Path, manifest: dict[str, Any]) -> str:
    source = manifest["source_evidence"]
    raw_path = source.get("reference_manifest_path")
    if raw_path is None:
        if manifest["job"]["input_mode"] != "text_anchor":
            raise ContractError("blocked_reference_manifest_missing", "image anchor requires a plan reference bundle")
        expected = sha256_bytes(
            canonical_json(
                {
                    "schema_version": "frozen_moment_reference_bundle.v1",
                    "ordered_references": [],
                    "input_mode": "text_anchor",
                }
            )
        )
        if (
            source.get("reference_plan_sha256") != expected
            or source.get("ordered_reference_bundle_sha256") != sha256_bytes(canonical_json([]))
        ):
            raise ContractError("blocked_reference_manifest_hash_mismatch", "synthetic reference-plan digest differs")
        return expected
    reference_path = resolve_artifact(root, raw_path, "blocked_reference_manifest_location")
    expected_path = root / "00_manifest" / "REFERENCE_BINDINGS.json"
    if reference_path != expected_path or not reference_path.is_file():
        raise ContractError("blocked_reference_manifest_location", "plan reference manifest is not at the frozen run path")
    if sha256_file(reference_path) != source.get("reference_manifest_sha256"):
        raise ContractError("blocked_reference_manifest_hash_mismatch", "plan reference manifest hash differs")
    bundle = read_json(reference_path, "blocked_reference_manifest_hash_mismatch")
    required = {
        "schema_version", "run_id", "view_id", "attempt_id", "source_evidence_sha256",
        "moment_canon_sha256", "reference_plan_sha256", "ordered_references",
        "ordered_bundle_sha256", "immutability_contract", "provider_reference_count",
    }
    if (
        set(bundle) != required
        or bundle.get("schema_version") != "frozen_moment_reference_bundle.v1"
        or bundle.get("run_id") != manifest["job"]["job_id"]
        or bundle.get("attempt_id") != "PLAN"
    ):
        raise ContractError("blocked_reference_manifest_hash_mismatch", "plan reference manifest identity differs")
    entries = bundle.get("ordered_references")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 5 or bundle.get("provider_reference_count") != len(entries):
        raise ContractError("blocked_reference_manifest_hash_mismatch", "plan reference count differs")
    reference_root = reference_path.parent / "references"
    if not reference_root.is_dir() or reference_root.is_symlink():
        raise ContractError("blocked_reference_manifest_location", "plan reference directory is invalid")
    planned: list[dict[str, Any]] = []
    paths: list[Path] = []
    ids: set[str] = set()
    aliases: set[str] = set()
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or entry.get("index") != index:
            raise ContractError("blocked_reference_manifest_hash_mismatch", "plan reference order differs")
        reference_id = entry.get("reference_id")
        alias = entry.get("alias")
        role = entry.get("role")
        frozen = Path(str(entry.get("frozen_path", "")))
        if (
            not isinstance(reference_id, str) or not reference_id or reference_id in ids
            or not isinstance(alias, str) or not alias or alias in aliases
            or role not in REFERENCE_ROLES
            or (index == 1 and role != "moment_anchor")
            or not frozen.is_absolute() or frozen.is_symlink()
        ):
            raise ContractError("blocked_reference_manifest_hash_mismatch", "plan reference identity or role differs")
        ids.add(reference_id)
        aliases.add(alias)
        try:
            frozen.resolve().relative_to(reference_root.resolve())
        except ValueError as exc:
            raise ContractError("blocked_reference_manifest_location", f"plan reference escapes its bundle: {frozen}") from exc
        if not frozen.is_file() or frozen.stat().st_size != entry.get("size_bytes") or sha256_file(frozen) != entry.get("sha256"):
            raise ContractError("blocked_reference_bytes_changed", f"plan reference is missing or changed: {frozen}")
        try:
            with Image.open(frozen) as image:
                image.verify()
                image_format = image.format
        except (OSError, UnidentifiedImageError) as exc:
            raise ContractError("blocked_reference_bytes_changed", f"plan reference is not a decodable image: {frozen}: {exc}") from exc
        if image_format != entry.get("media_format") or image_format not in {"PNG", "JPEG", "WEBP"}:
            raise ContractError("blocked_reference_bytes_changed", f"plan reference media format differs: {frozen}")
        if any(entry.get(field) is not None for field in ("origin_view_id", "origin_attempt_id", "origin_inspection_sha256", "origin_inspection_path")):
            raise ContractError("blocked_reference_manifest_hash_mismatch", "v1 plan references cannot carry generated bridge origins")
        planned.append(
            {
                "index": index,
                "reference_id": reference_id,
                "role": role,
                "source_path": entry.get("source_path"),
                "rights_state": entry.get("rights_state"),
                "bridge_origin": None,
            }
        )
        paths.append(frozen.resolve())
    if {path.resolve() for path in reference_root.iterdir() if path.is_file()} != set(paths) or any(path.is_dir() for path in reference_root.iterdir()):
        raise ContractError("blocked_reference_manifest_hash_mismatch", "plan reference directory inventory differs")
    plan_sha = sha256_bytes(canonical_json(planned))
    if bundle.get("reference_plan_sha256") != plan_sha or source.get("reference_plan_sha256") != plan_sha:
        raise ContractError("blocked_reference_manifest_hash_mismatch", "plan reference digest differs")
    if bundle.get("ordered_bundle_sha256") != sha256_bytes(canonical_json(entries)) or source.get("ordered_reference_bundle_sha256") != bundle.get("ordered_bundle_sha256"):
        raise ContractError("blocked_reference_manifest_hash_mismatch", "plan ordered bundle digest differs")
    return plan_sha


def camera_contract_sha(family: dict[str, Any], view: dict[str, Any]) -> str:
    record = {
        "family": {key: value for key, value in family.items() if key != "family_contract_sha256"},
        "view_id": view["view_id"],
        "coverage_role": view["coverage_role"],
        "required": view["required"],
        "azimuth_deg": view["azimuth_deg"],
        "elevation_deg": view["elevation_deg"],
        "visibility": view["visibility"],
        "micro_coverage": bool(view.get("micro_coverage", False)),
        "expected_parallax_region_ids": view.get("expected_parallax_region_ids", []),
    }
    return sha256_bytes(canonical_json(record))


def validate_ring(manifest: dict[str, Any]) -> None:
    profile = manifest["job"].get("coverage_profile")
    views = manifest["views"]
    required = [view for view in views if view.get("required")]
    if profile == "targeted_views":
        if not 1 <= len(required) <= 3:
            raise ContractError("E_RING_WRONG_COUNT", "targeted_views requires one to three required views")
        if manifest["job"].get("full_coverage_claim"):
            raise ContractError("E_TARGETED_OVERCLAIM", "targeted views cannot claim full coverage")
        return
    if profile == "custom" and manifest["job"].get("full_coverage_claim"):
        raise ContractError("E_CUSTOM_OVERCLAIM", "custom coverage cannot claim full coverage")
    if profile not in DEFAULT_BINS or manifest["job"].get("generation_phase") == "moment_anchor":
        return
    expected = DEFAULT_BINS[profile]
    if len(required) != len(expected):
        raise ContractError("E_RING_WRONG_COUNT", f"{profile} requires {len(expected)} required views")
    family_ids = {view.get("family_id") for view in required}
    if len(family_ids) != 1:
        raise ContractError("E_FAMILY_MIX", f"{profile} must use one family")
    family_by_id = {family["family_id"]: family for family in manifest["camera_families"]}
    family = family_by_id.get(next(iter(family_ids)))
    if not family or family.get("family_kind") != "master":
        raise ContractError("E_MASTER_PORTRAIT_AGGREGATION", "master ring cannot use portrait views")
    bins: dict[float, str] = {}
    for view in required:
        matches = [target for target in expected if circular_diff(view["azimuth_deg"], target) <= 3.0]
        if len(matches) != 1:
            raise ContractError("E_RING_MISSING_BIN", f"view {view['view_id']} misses {profile} bins")
        if matches[0] in bins:
            raise ContractError("E_RING_DUPLICATE_BIN", f"duplicate ring bin: {matches[0]:g}")
        bins[matches[0]] = view["view_id"]
    if set(bins) != set(expected):
        raise ContractError("E_RING_MISSING_BIN", f"missing bins: {sorted(set(expected) - set(bins))}")


def validate_manifest_structure(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    required_top = {
        "schema_version",
        "job",
        "source_evidence",
        "evidence_ledger",
        "moment_canon",
        "camera_families",
        "views",
        "prompts",
        "attempts",
        "qa",
        "state",
        "prompt_set_sha256",
        "coverage_contract_sha256",
        "compiled_at_utc",
    }
    if set(manifest) != required_top or manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise ContractError("package_manifest_invalid", "manifest fields or schema version are invalid")
    job = manifest["job"]
    if not isinstance(job, dict) or job.get("mode") not in {"prompt_only", "generate_and_package"}:
        raise ContractError("package_manifest_invalid", "manifest mode is invalid")
    if job.get("input_mode") not in {"image_anchor", "text_anchor"}:
        raise ContractError("package_manifest_invalid", "manifest input mode is invalid")
    if (
        job.get("coverage_profile") not in {"targeted_views", "minimum_ring", "robust_ring", "custom"}
        or job.get("generation_phase") not in {"all", "moment_anchor", "coverage"}
        or not isinstance(job.get("max_attempts_per_view"), int)
        or not 1 <= job["max_attempts_per_view"] <= 10
        or not isinstance(job.get("full_coverage_claim"), bool)
    ):
        raise ContractError("package_manifest_invalid", "manifest coverage, phase, attempt, or claim fields are invalid")
    source = manifest.get("source_evidence")
    moment = manifest.get("moment_canon")
    if not isinstance(source, dict) or not isinstance(moment, dict):
        raise ContractError("package_manifest_invalid", "source evidence and Moment Canon must be objects")
    expected_source_sha = sha256_bytes(canonical_json({key: value for key, value in source.items() if key != "source_evidence_sha256"}))
    expected_moment_sha = sha256_bytes(canonical_json({key: value for key, value in moment.items() if key != "moment_canon_sha256"}))
    if source.get("source_evidence_sha256") != expected_source_sha or moment.get("moment_canon_sha256") != expected_moment_sha:
        raise ContractError("package_hash_invalid", "source evidence or Moment Canon digest differs")
    for field in ("subjects", "scene_topology", "temporal_state", "lighting", "look", "prohibited_changes"):
        if not isinstance(moment.get(field), list) or not moment[field]:
            raise ContractError("blocked_missing_input", f"Moment Canon {field} is empty")
    if not isinstance(manifest.get("evidence_ledger"), dict) or not any(manifest["evidence_ledger"].get(key) for key in ("observed", "source_corroborated", "inferred", "unknown", "approved_canon")):
        raise ContractError("blocked_missing_input", "evidence ledger is empty")
    validate_evidence_authority(job, source, moment, manifest["evidence_ledger"])
    reject_prompt_control_text(moment, "moment_canon")
    reference_plan_sha = validate_plan_reference_bundle(root, manifest)
    views = manifest["views"]
    prompts = manifest["prompts"]
    families = manifest["camera_families"]
    if not all(isinstance(item, list) for item in (views, prompts, families)) or not views or not prompts or not families:
        raise ContractError("package_manifest_invalid", "families, views, and prompts must be non-empty lists")
    view_ids = [view.get("view_id") for view in views]
    if not all(isinstance(item, str) and item for item in view_ids) or len(set(view_ids)) != len(view_ids):
        raise ContractError("package_manifest_invalid", "view IDs are invalid or duplicate")
    family_ids = [family.get("family_id") for family in families]
    if len(set(family_ids)) != len(family_ids):
        raise ContractError("E_FAMILY_MIX", "family IDs are duplicate")
    for family in families:
        if family.get("varying_fields") != ["azimuth_deg"]:
            raise ContractError("E_FAMILY_INVARIANT_DRIFT", f"family {family.get('family_id')} varies more than azimuth")
        expected = sha256_bytes(canonical_json({key: value for key, value in family.items() if key != "family_contract_sha256"}))
        if family.get("family_contract_sha256") != expected:
            raise ContractError("E_FAMILY_INVARIANT_DRIFT", f"family hash mismatch: {family.get('family_id')}")
    family_by_id = {family["family_id"]: family for family in families}
    for view in views:
        if view.get("family_id") not in set(family_ids):
            raise ContractError("E_FAMILY_MIX", f"view has unknown family: {view.get('view_id')}")
        if (
            not isinstance(view.get("coverage_role"), str) or not view["coverage_role"]
            or not isinstance(view.get("required"), bool)
            or not isinstance(view.get("azimuth_deg"), (int, float))
            or not isinstance(view.get("elevation_deg"), (int, float))
            or not isinstance(view.get("visibility"), dict)
        ):
            raise ContractError("package_manifest_invalid", f"view contract is incomplete: {view.get('view_id')}")
        actual_camera_sha = require_sha(view.get("camera_contract_sha256"), f"view {view.get('view_id')} camera contract")
        if actual_camera_sha != camera_contract_sha(family_by_id[view["family_id"]], view):
            raise ContractError("E_CAMERA_CONTRACT_DRIFT", f"view camera contract changed: {view['view_id']}")
        goal = view["visibility"].get("face_visibility_goal", "natural_from_frozen_pose")
        if goal in {"full_face", "eye_contact"}:
            subject_id = view["visibility"].get("subject_id") or moment["subjects"][0].get("subject_id")
            subject = next((item for item in moment["subjects"] if item.get("subject_id") == subject_id), None)
            vector_field = "head_direction" if goal == "full_face" else "gaze_direction"
            vector = subject.get(vector_field) if isinstance(subject, dict) else None
            if not isinstance(vector, dict):
                raise ContractError("blocked_physical_conflict", f"{view['view_id']} requests {goal} without approved {vector_field}")
            yaw_tolerance = 15.0 if goal == "full_face" else 5.0
            pitch_tolerance = 10.0 if goal == "full_face" else 5.0
            if (
                circular_diff(view["azimuth_deg"], float(vector["yaw_deg"])) > yaw_tolerance
                or abs(float(view["elevation_deg"]) - float(vector["pitch_deg"])) > pitch_tolerance
            ):
                raise ContractError("blocked_physical_conflict", f"{view['view_id']} {goal} conflicts with frozen direction")
    validate_ring(manifest)
    for index, left in enumerate(views):
        for right in views[index + 1 :]:
            if left["family_id"] != right["family_id"]:
                continue
            delta = circular_diff(left["azimuth_deg"], right["azimuth_deg"])
            if delta <= 0.001:
                raise ContractError("E_TUPLE_DUPLICATE", f"duplicate camera tuple: {left['view_id']}, {right['view_id']}")
            if delta < 12.0:
                micro_ok = bool(left.get("micro_coverage") and right.get("micro_coverage"))
                parallax = set(left.get("expected_parallax_region_ids", [])) | set(right.get("expected_parallax_region_ids", []))
                if not micro_ok or not parallax:
                    raise ContractError("E_TUPLE_NEAR_DUPLICATE", f"near-duplicate camera tuple: {left['view_id']}, {right['view_id']}")

    prompt_by_view: dict[str, dict[str, Any]] = {}
    prompt_set_records: list[dict[str, str]] = []
    for prompt in prompts:
        view_id = prompt.get("view_id")
        if view_id not in view_ids or view_id in prompt_by_view or prompt.get("language") != "zh" or prompt.get("published") is not True:
            raise ContractError("prompt_package_invalid", f"prompt record invalid or duplicate: {view_id}")
        path = resolve_artifact(root, prompt.get("prompt_path"), "prompt_package_invalid")
        if not path.is_file():
            raise ContractError("prompt_package_invalid", f"prompt file missing: {path}")
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.strip():
            raise ContractError("prompt_package_invalid", f"prompt bytes invalid: {path}")
        expected_sha = require_sha(prompt.get("prompt_sha256"), f"prompt {view_id}")
        if sha256_bytes(raw) != expected_sha:
            raise ContractError("prompt_hash_mismatch", f"prompt hash mismatch: {view_id}")
        reference_plan_sha = require_sha(prompt.get("reference_plan_sha256"), f"prompt {view_id} reference plan")
        if reference_plan_sha != source.get("reference_plan_sha256"):
            raise ContractError("blocked_reference_manifest_hash_mismatch", f"prompt reference plan differs: {view_id}")
        prompt_by_view[view_id] = prompt
        prompt_set_records.append({"view_id": view_id, "prompt_sha256": expected_sha, "reference_plan_sha256": reference_plan_sha})
    if set(prompt_by_view) != set(view_ids):
        raise ContractError("prompt_package_invalid", "every view must have one complete Chinese prompt")
    if manifest.get("prompt_set_sha256") != sha256_bytes(canonical_json(prompt_set_records)):
        raise ContractError("prompt_hash_mismatch", "prompt set hash mismatch")
    publication = read_json(root / "00_manifest" / "PROMPT_PUBLICATION.json", "prompt_publication_invalid")
    required_ids = [view["view_id"] for view in views if view.get("required")]
    if publication.get("required_view_ids") != required_ids or publication.get("published_prompt_ids") != required_ids:
        raise ContractError("prompt_publication_invalid", "publication receipt omits or reorders required prompts")
    document = resolve_artifact(root, publication.get("prompt_document_path"), "prompt_publication_invalid")
    if not document.is_file() or sha256_file(document) != publication.get("prompt_document_sha256"):
        raise ContractError("prompt_publication_invalid", "published prompt document is missing or changed")
    expected_prompt_hashes = [prompt_by_view[view_id]["prompt_sha256"] for view_id in required_ids]
    if publication.get("published_prompt_sha256") != expected_prompt_hashes:
        raise ContractError("prompt_publication_invalid", "published prompt hashes differ from required prompts")
    expected_reference_hashes = [prompt_by_view[view_id]["reference_plan_sha256"] for view_id in required_ids]
    if publication.get("published_reference_plan_sha256") != expected_reference_hashes:
        raise ContractError("prompt_publication_invalid", "published reference plans differ from required prompts")
    if (
        publication.get("schema_version") != "frozen_moment_prompt_publication_receipt.v1"
        or publication.get("input_mode") != job["input_mode"]
        or publication.get("publication_status") != "prompt_artifacts_frozen"
        or publication.get("required_view_set_sha256") != sha256_bytes(canonical_json(required_ids))
    ):
        raise ContractError("prompt_publication_invalid", "publication identity or required-view digest differs")
    coverage_contract = {
        key: manifest[key]
        for key in (
            "schema_version", "job", "source_evidence", "evidence_ledger", "moment_canon",
            "camera_families", "prompts", "prompt_set_sha256",
        )
    }
    coverage_contract["views"] = [
        {key: value for key, value in view.items() if key != "status"}
        for view in manifest["views"]
    ]
    if manifest.get("coverage_contract_sha256") != sha256_bytes(canonical_json(coverage_contract)):
        raise ContractError("coverage_contract_hash_mismatch", "coverage contract digest differs")
    return {
        "view_ids": view_ids,
        "required_ids": required_ids,
        "prompt_by_view": prompt_by_view,
        "publication": publication,
        "reference_plan_sha256": reference_plan_sha,
    }


def validate_inspection(
    *,
    root: Path,
    manifest: dict[str, Any],
    view: dict[str, Any],
    attempt: dict[str, Any],
    worker_result: dict[str, Any],
    image_path: Path,
    image_sha: str,
    width: int,
    height: int,
) -> dict[str, Any]:
    inspection_path = resolve_artifact(root, attempt.get("inspection_path"), "inspection_missing")
    inspection = read_json(inspection_path, "inspection_invalid")
    if sha256_file(inspection_path) != attempt.get("inspection_sha256"):
        raise ContractError("inspection_hash_mismatch", f"inspection hash mismatch: {inspection_path}")
    if inspection.get("schema_version") != "frozen_moment_main_inspection.v1":
        raise ContractError("inspection_invalid", "inspection schema mismatch")
    for field, expected in (
        ("run_id", manifest["job"]["job_id"]),
        ("view_id", view["view_id"]),
        ("attempt_id", attempt["attempt_id"]),
        ("worker_result_sha256", attempt["worker_result_sha256"]),
        ("image_sha256", image_sha),
        ("moment_canon_sha256", manifest["moment_canon"]["moment_canon_sha256"]),
        ("camera_contract_sha256", view["camera_contract_sha256"]),
        ("prompt_sha256", attempt["prompt_sha256"]),
        ("reference_bundle_sha256", worker_result["ordered_reference_bundle_sha256"]),
    ):
        if inspection.get(field) != expected:
            raise ContractError("inspection_lineage_mismatch", f"inspection {field} does not match current attempt")
    dimensions = inspection.get("actual_dimensions")
    if dimensions != {"width_px": width, "height_px": height}:
        raise ContractError("inspection_lineage_mismatch", "inspection dimensions differ from actual image")
    decision = inspection.get("decision")
    if decision not in {"approved", "rejected", "repair_required"} or attempt.get("decision") != decision:
        raise ContractError("inspection_invalid", "inspection and attempt decisions are invalid or inconsistent")
    runtime_receipt_path = resolve_artifact(
        root,
        attempt.get("inspection_runtime_receipt_path"),
        "inspection_runtime_receipt_missing",
    )
    runtime_receipt = read_json(runtime_receipt_path, "inspection_runtime_receipt_invalid")
    if sha256_file(runtime_receipt_path) != attempt.get("inspection_runtime_receipt_sha256"):
        raise ContractError("inspection_runtime_receipt_mismatch", "pixel-open receipt hash mismatch")
    for field, expected in (
        ("schema_version", "frozen_moment_pixel_open_receipt.v1"),
        ("run_id", manifest["job"]["job_id"]),
        ("view_id", view["view_id"]),
        ("attempt_id", attempt["attempt_id"]),
        ("inspector_thread_id", inspection.get("inspector_task_id")),
        ("image_sha256", image_sha),
        ("inspected_at_utc", inspection.get("inspected_at_utc")),
    ):
        if runtime_receipt.get(field) != expected:
            raise ContractError("inspection_runtime_receipt_mismatch", f"pixel-open receipt {field} differs")
    runtime_slice_path = resolve_artifact(
        root,
        runtime_receipt.get("rollout_slice_path"),
        "inspection_runtime_receipt_missing",
    )
    try:
        inspection_runtime.replay_receipt(
            root=root,
            receipt=runtime_receipt,
            slice_events=worker_resolver.read_rollout(runtime_slice_path),
            inspector_thread_id=str(inspection.get("inspector_task_id", "")),
            image_path=image_path,
            image_sha256=image_sha,
            inspected_at_utc=str(inspection.get("inspected_at_utc", "")),
        )
    except (inspection_runtime.InspectionRuntimeError, worker_resolver.ContractError) as exc:
        code = getattr(exc, "code", "inspection_runtime_receipt_invalid")
        raise ContractError(code, str(exc)) from exc
    checks = inspection.get("hard_checks")
    if not isinstance(checks, list):
        raise ContractError("inspection_invalid", "hard_checks must be a list")
    by_id: dict[str, dict[str, Any]] = {}
    for check in checks:
        if not isinstance(check, dict) or check.get("check_id") in by_id:
            raise ContractError("inspection_invalid", "hard checks must be unique objects")
        if check.get("status") not in {"pass", "fail", "not_applicable_with_reason"}:
            raise ContractError("inspection_invalid", "hard check status invalid")
        if not isinstance(check.get("evidence_summary"), str) or not check["evidence_summary"].strip():
            raise ContractError("inspection_invalid", "hard check lacks evidence summary")
        by_id[check["check_id"]] = check
    missing = REQUIRED_HARD_CHECKS - set(by_id)
    if missing:
        raise ContractError("inspection_invalid", f"inspection misses hard checks: {sorted(missing)}")
    failed = [check_id for check_id, check in by_id.items() if check["status"] == "fail"]
    if decision == "approved" and (failed or any(by_id[check_id]["status"] != "pass" for check_id in REQUIRED_HARD_CHECKS)):
        raise ContractError("inspection_false_approval", f"approved inspection contains non-pass hard checks: {failed}")
    return inspection


def validate_attempts(root: Path, manifest: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    view_by_id = {view["view_id"]: view for view in manifest["views"]}
    prompt_by_view = context["prompt_by_view"]
    attempts = manifest["attempts"]
    if not isinstance(attempts, list):
        raise ContractError("attempt_ledger_invalid", "attempts must be a list")
    seen_attempts: set[str] = set()
    seen_nonces: set[str] = set()
    seen_threads: set[str] = set()
    seen_calls: set[str] = set()
    seen_images: set[str] = set()
    approved_by_view: dict[str, str] = {}
    attempts_by_view: dict[str, list[dict[str, Any]]] = {view_id: [] for view_id in view_by_id}
    revisions_by_view: dict[str, list[int]] = {view_id: [] for view_id in view_by_id}
    queue_records: list[dict[str, Any]] = []
    queue_parent_thread: str | None = None
    for attempt in attempts:
        if not isinstance(attempt, dict):
            raise ContractError("attempt_ledger_invalid", "attempt must be an object")
        view_id = attempt.get("view_id")
        attempt_id = attempt.get("attempt_id")
        if view_id not in view_by_id or not isinstance(attempt_id, str) or not attempt_id:
            raise ContractError("attempt_ledger_invalid", "attempt lacks a valid view or ID")
        if attempt_id in seen_attempts:
            raise ContractError("attempt_ledger_invalid", f"attempt ID reused: {attempt_id}")
        seen_attempts.add(attempt_id)
        revision = attempt.get("attempt_revision")
        maximum = manifest["job"]["max_attempts_per_view"]
        if (
            not isinstance(revision, int)
            or isinstance(revision, bool)
            or not 1 <= revision <= maximum
            or revision != len(revisions_by_view[view_id]) + 1
        ):
            raise ContractError("attempt_ledger_invalid", f"bound attempt revisions must be contiguous from one: {attempt_id}")
        revisions_by_view[view_id].append(revision)
        attempts_by_view[view_id].append(attempt)
        if len(attempts_by_view[view_id]) > manifest["job"]["max_attempts_per_view"]:
            raise ContractError("blocked_attempt_budget", f"attempt budget exceeded for {view_id}")
        prompt_path = resolve_artifact(root, attempt.get("prompt_path"), "attempt_ledger_invalid")
        if not prompt_path.is_file() or sha256_file(prompt_path) != attempt.get("prompt_sha256"):
            raise ContractError("attempt_prompt_mismatch", f"attempt prompt changed: {attempt_id}")
        reference_path = resolve_artifact(root, attempt.get("reference_manifest_path"), "worker_result_lineage_mismatch")
        if not reference_path.is_file() or sha256_file(reference_path) != attempt.get("reference_manifest_sha256"):
            raise ContractError("worker_result_lineage_mismatch", f"attempt reference manifest is missing or changed: {attempt_id}")
        try:
            references = worker_resolver.load_reference_manifest(
                reference_path,
                manifest["job"]["job_id"],
                view_id,
                attempt_id,
                manifest["source_evidence"]["source_evidence_sha256"],
                manifest["moment_canon"]["moment_canon_sha256"],
                prompt_by_view[view_id]["reference_plan_sha256"],
            )
        except worker_resolver.ContractError as exc:
            raise ContractError("worker_result_lineage_mismatch", f"attempt reference manifest failed: {exc.code}: {exc.detail}") from exc
        worker_path = resolve_artifact(root, attempt.get("worker_result_path"), "worker_result_missing")
        worker = read_json(worker_path, "worker_result_invalid")
        if sha256_file(worker_path) != attempt.get("worker_result_sha256"):
            raise ContractError("worker_result_hash_mismatch", f"worker result changed: {attempt_id}")
        if worker.get("schema_version") != "frozen_moment_view_worker_result.v1" or worker.get("ok") is not True:
            raise ContractError("worker_result_invalid", f"worker result schema/status invalid: {attempt_id}")
        prior_bound = attempts_by_view[view_id][:-1]
        authority_mode = attempt.get("prompt_authority_mode", "base_prompt")
        worker_authority_mode = worker.get("prompt_authority_mode", "base_prompt")
        repair_authority: dict[str, Any] | None = None
        if prior_bound:
            if authority_mode != "repair_prompt" or worker_authority_mode != "repair_prompt":
                raise ContractError("blocked_repair_prompt_required", f"bound retry lacks versioned repair authority: {attempt_id}")
            repair_path = resolve_artifact(
                root, attempt.get("repair_publication_path"), "blocked_repair_prompt_invalid"
            )
            if (
                sha256_file(repair_path) != attempt.get("repair_publication_sha256")
                or Path(str(worker.get("repair_publication_path", ""))).resolve() != repair_path
                or worker.get("repair_publication_sha256") != attempt.get("repair_publication_sha256")
            ):
                raise ContractError("blocked_repair_prompt_invalid", f"repair publication lineage differs: {attempt_id}")
            try:
                repair_authority = worker_resolver.load_repair_publication(
                    run_root=root,
                    manifest=manifest,
                    publication_path=repair_path,
                    expected_prompt=prompt_path,
                    view_id=view_id,
                    attempt_id=attempt_id,
                    attempt_revision=revision,
                )
            except worker_resolver.ContractError as exc:
                raise ContractError("blocked_repair_prompt_invalid", f"repair publication failed: {exc.code}: {exc.detail}") from exc
            if (
                repair_authority["prompt_sha256"] != attempt.get("prompt_sha256")
                or repair_authority["publication_sha256"] != attempt.get("repair_publication_sha256")
                or not isinstance(worker.get("not_before_ms"), int)
                or isinstance(worker.get("not_before_ms"), bool)
                or worker["not_before_ms"] < repair_authority["published_at_unix_ms"]
            ):
                raise ContractError("blocked_repair_prompt_invalid", f"repair prompt or publication checkpoint differs: {attempt_id}")
        else:
            if authority_mode != "base_prompt" or worker_authority_mode != "base_prompt":
                raise ContractError("attempt_prompt_mismatch", f"first bound attempt must use base prompt authority: {attempt_id}")
            if (
                attempt.get("prompt_path") != prompt_by_view[view_id]["prompt_path"]
                or attempt.get("prompt_sha256") != prompt_by_view[view_id]["prompt_sha256"]
                or attempt.get("repair_publication_path") is not None
                or attempt.get("repair_publication_sha256") is not None
                or worker.get("repair_publication_path") is not None
                or worker.get("repair_publication_sha256") is not None
            ):
                raise ContractError("attempt_prompt_mismatch", f"base attempt prompt authority differs: {attempt_id}")
        for field, expected in (
            ("run_id", manifest["job"]["job_id"]),
            ("view_id", view_id),
            ("attempt_id", attempt_id),
            ("attempt_revision", attempt.get("attempt_revision")),
            ("generation_prompt_sha256", attempt["prompt_sha256"]),
            ("tool_prompt_sha256", attempt["prompt_sha256"]),
            ("coverage_contract_sha256", manifest["coverage_contract_sha256"]),
            ("source_evidence_sha256", manifest["source_evidence"]["source_evidence_sha256"]),
            ("moment_canon_sha256", manifest["moment_canon"]["moment_canon_sha256"]),
            ("reference_manifest_sha256", attempt["reference_manifest_sha256"]),
            ("reference_plan_sha256", prompt_by_view[view_id]["reference_plan_sha256"]),
            ("ordered_reference_bundle_sha256", references["ordered_bundle_sha256"]),
            ("reference_count", references["reference_count"]),
        ):
            if worker.get(field) != expected:
                raise ContractError("worker_result_lineage_mismatch", f"worker {field} mismatch: {attempt_id}")
        if worker.get("prompt_binding_mode") != "exact_bytes" or worker.get("prompt_sha_match") is not True or worker.get("reference_bytes_verified") is not True:
            raise ContractError("worker_result_lineage_mismatch", f"worker prompt/reference binding not exact: {attempt_id}")
        nonce = worker.get("worker_run_nonce")
        thread = worker.get("worker_thread_id")
        call = worker.get("image_generation_call_id")
        agent_path = worker.get("agent_path")
        parent_thread = worker.get("parent_thread_id")
        not_before_ms = worker.get("not_before_ms")
        if (
            not isinstance(nonce, str) or not re.fullmatch(r"[0-9a-f]{32}", nonce)
            or not isinstance(thread, str) or not thread
            or not isinstance(call, str) or not call
            or not isinstance(agent_path, str) or not agent_path
            or not isinstance(parent_thread, str) or not parent_thread
            or not isinstance(not_before_ms, int) or not_before_ms < 0
        ):
            raise ContractError("worker_result_lineage_mismatch", f"worker identity fields are invalid: {attempt_id}")
        try:
            task_name = worker_resolver.validate_worker_name_binding(agent_path, view_id, nonce)
        except worker_resolver.ContractError as exc:
            raise ContractError("worker_result_lineage_mismatch", f"worker name binding failed: {exc.detail}") from exc
        if worker.get("worker_task_name") != task_name:
            raise ContractError("worker_result_lineage_mismatch", f"worker task name differs: {attempt_id}")
        if nonce in seen_nonces or thread in seen_threads or call in seen_calls:
            raise ContractError("worker_result_lineage_reuse", f"worker nonce/thread/call reused: {attempt_id}")
        seen_nonces.add(nonce)
        seen_threads.add(thread)
        seen_calls.add(call)
        image_path = resolve_artifact(root, attempt.get("image_path"), "image_missing")
        width, height, image_sha = inspect_png(image_path)
        if image_sha != attempt.get("image_sha256") or image_sha != worker.get("image_sha256"):
            raise ContractError("image_hash_mismatch", f"image hash differs from worker/attempt: {attempt_id}")
        if image_sha in seen_images:
            raise ContractError("E_PIXEL_DUPLICATE", f"duplicate generated pixels: {attempt_id}")
        seen_images.add(image_sha)
        if (
            worker.get("width_px") != width
            or worker.get("height_px") != height
            or worker.get("format") != "PNG"
            or Path(str(worker.get("run_image_path", ""))).resolve() != image_path
            or Path(str(worker.get("generation_prompt_path", ""))).resolve() != prompt_path
            or Path(str(worker.get("reference_manifest_path", ""))).resolve() != reference_path
            or Path(str(worker.get("coverage_manifest_path", ""))).resolve() != root / "00_manifest" / "COVERAGE_MANIFEST.json"
            or not isinstance(worker.get("coverage_manifest_sha256_at_resolution"), str)
            or not SHA_RE.fullmatch(worker["coverage_manifest_sha256_at_resolution"])
        ):
            raise ContractError("worker_result_lineage_mismatch", f"worker paths, dimensions, format, or contract binding differ: {attempt_id}")

        worker_rollout = Path(str(worker.get("worker_rollout_path", "")))
        parent_rollout = Path(str(worker.get("parent_rollout_path", "")))
        coverage_snapshot = Path(str(worker.get("coverage_manifest_snapshot_path", "")))
        if (
            not worker_rollout.is_absolute() or worker_rollout.is_symlink() or not worker_rollout.is_file()
            or not parent_rollout.is_absolute() or parent_rollout.is_symlink() or not parent_rollout.is_file()
            or parent_rollout.resolve() != worker_path.parent / "parent-rollout-at-resolution.jsonl"
            or sha256_file(worker_rollout) != worker.get("worker_rollout_sha256")
            or sha256_file(parent_rollout) != worker.get("parent_rollout_sha256")
            or not coverage_snapshot.is_absolute() or coverage_snapshot.is_symlink() or not coverage_snapshot.is_file()
            or coverage_snapshot.resolve() != worker_path.parent / "coverage-manifest-at-resolution.json"
            or sha256_file(coverage_snapshot) != worker.get("coverage_manifest_sha256_at_resolution")
        ):
            raise ContractError("worker_result_lineage_mismatch", f"worker, parent, or coverage snapshot evidence is unavailable: {attempt_id}")
        coverage_at_resolution = read_json(coverage_snapshot, "worker_result_lineage_mismatch")
        snapshot_prior = [
            item for item in coverage_at_resolution.get("attempts", [])
            if isinstance(item, dict) and item.get("view_id") == view_id
            and isinstance(item.get("attempt_revision"), int) and item["attempt_revision"] < revision
        ]
        snapshot_current_or_later = [
            item for item in coverage_at_resolution.get("attempts", [])
            if isinstance(item, dict) and item.get("view_id") == view_id
            and isinstance(item.get("attempt_revision"), int) and item["attempt_revision"] >= revision
        ]
        if canonical_json(snapshot_prior) != canonical_json(prior_bound) or snapshot_current_or_later:
            raise ContractError(
                "worker_result_lineage_mismatch",
                f"coverage snapshot does not contain the exact predecessor ledger: {attempt_id}",
            )
        if repair_authority is not None:
            repair_snapshot_path = resolve_artifact(
                root, attempt.get("repair_publication_path"), "blocked_repair_prompt_invalid"
            )
            try:
                snapshot_repair_authority = worker_resolver.load_repair_publication(
                    run_root=root,
                    manifest=coverage_at_resolution,
                    publication_path=repair_snapshot_path,
                    expected_prompt=prompt_path,
                    view_id=view_id,
                    attempt_id=attempt_id,
                    attempt_revision=revision,
                )
            except worker_resolver.ContractError as exc:
                raise ContractError(
                    "worker_result_lineage_mismatch",
                    f"coverage snapshot cannot replay repair authority: {exc.code}: {exc.detail}",
                ) from exc
            if snapshot_repair_authority["publication_sha256"] != repair_authority["publication_sha256"]:
                raise ContractError("worker_result_lineage_mismatch", f"snapshot repair receipt differs: {attempt_id}")
        try:
            snapshot_contract = {
                key: coverage_at_resolution[key]
                for key in (
                    "schema_version", "job", "source_evidence", "evidence_ledger", "moment_canon",
                    "camera_families", "prompts", "prompt_set_sha256",
                )
            }
            snapshot_contract["views"] = [
                {key: value for key, value in item.items() if key != "status"}
                for item in coverage_at_resolution["views"]
            ]
        except (KeyError, TypeError) as exc:
            raise ContractError("worker_result_lineage_mismatch", f"coverage snapshot contract is incomplete: {attempt_id}") from exc
        snapshot_prompt = next(
            (item for item in coverage_at_resolution.get("prompts", []) if item.get("view_id") == view_id),
            None,
        )
        if (
            coverage_at_resolution.get("job", {}).get("job_id") != manifest["job"]["job_id"]
            or coverage_at_resolution.get("coverage_contract_sha256") != sha256_bytes(canonical_json(snapshot_contract))
            or coverage_at_resolution.get("coverage_contract_sha256") != manifest["coverage_contract_sha256"]
            or not isinstance(snapshot_prompt, dict)
            or snapshot_prompt.get("prompt_sha256") != prompt_by_view[view_id]["prompt_sha256"]
        ):
            raise ContractError("worker_result_lineage_mismatch", f"coverage snapshot differs from the frozen contract: {attempt_id}")
        try:
            worker_trace = worker_resolver.validate_worker_rollout(
                events=worker_resolver.read_rollout(worker_rollout),
                thread_id=thread,
                agent_path=agent_path,
                parent_thread_id=parent_thread,
                view_id=view_id,
                nonce=nonce,
                expected_prompt_bytes=prompt_path.read_bytes(),
                expected_references=references["paths"],
            )
            parent_trace = worker_resolver.validate_parent_spawn_chain(
                events=worker_resolver.read_rollout(parent_rollout),
                parent_thread_id=parent_thread,
                worker_thread_id=thread,
                agent_path=agent_path,
                view_id=view_id,
                nonce=nonce,
                ciphertext=worker_trace["task_delivery_ciphertext"],
                not_before_ms=not_before_ms,
            )
        except worker_resolver.ContractError as exc:
            raise ContractError("worker_result_lineage_mismatch", f"runtime rollout revalidation failed: {exc.code}: {exc.detail}") from exc
        for field, expected in (
            ("worker_turn_id", worker_trace["worker_turn_id"]),
            ("image_generation_call_id", worker_trace["call_id"]),
            ("worker_saved_path", worker_trace["saved_path"]),
            ("task_delivery_ciphertext_sha256", sha256_bytes(worker_trace["task_delivery_ciphertext"].encode("utf-8"))),
            ("binding_mode", parent_trace["binding_mode"]),
            ("parent_spawn_call_id", parent_trace["parent_spawn_call_id"]),
            ("parent_spawn_turn_id", parent_trace["parent_spawn_turn_id"]),
            ("parent_spawn_event_index", parent_trace["parent_spawn_event_index"]),
            ("parent_spawn_activity_ms", parent_trace["parent_spawn_activity_ms"]),
            ("parent_completion_event_index", parent_trace["parent_completion_event_index"]),
            ("parent_completion_activity_ms", parent_trace["parent_completion_activity_ms"]),
            ("parent_completion_mode", parent_trace["parent_completion_mode"]),
            ("parent_spawn_chain_sha256", parent_trace["parent_spawn_chain_sha256"]),
        ):
            if worker.get(field) != expected:
                raise ContractError("worker_result_lineage_mismatch", f"revalidated worker {field} differs: {attempt_id}")
        if queue_parent_thread is None:
            queue_parent_thread = parent_thread
        elif queue_parent_thread != parent_thread:
            raise ContractError("worker_queue_invalid", "all view workers must use one parent task thread")
        queue_records.append(
            {
                "attempt_id": attempt_id,
                "spawn_index": parent_trace["parent_spawn_event_index"],
                "spawn_activity_ms": parent_trace["parent_spawn_activity_ms"],
                "not_before_ms": not_before_ms,
                "completion_index": parent_trace["parent_completion_event_index"],
            }
        )
        inspection = validate_inspection(
            root=root,
            manifest=manifest,
            view=view_by_id[view_id],
            attempt=attempt,
            worker_result=worker,
            image_path=image_path,
            image_sha=image_sha,
            width=width,
            height=height,
        )
        if inspection["decision"] == "approved":
            if view_id in approved_by_view:
                raise ContractError("attempt_ledger_invalid", f"multiple approved attempts for {view_id}")
            approved_by_view[view_id] = attempt_id
    ordered_queue = sorted(queue_records, key=lambda item: item["spawn_index"])
    if ordered_queue != queue_records:
        raise ContractError("worker_queue_invalid", "attempt ledger order differs from parent spawn order")
    for previous, current in zip(ordered_queue, ordered_queue[1:]):
        if current["spawn_index"] <= previous["completion_index"]:
            raise ContractError("worker_queue_invalid", f"worker attempts overlap: {previous['attempt_id']} -> {current['attempt_id']}")
    return {
        "approved_by_view": approved_by_view,
        "attempts_by_view": attempts_by_view,
        "queue_records": ordered_queue,
    }


def validate_text_anchor_phase_lineage(root: Path, manifest: dict[str, Any]) -> None:
    job = manifest.get("job", {})
    if job.get("input_mode") != "text_anchor" or job.get("generation_phase") != "coverage":
        return
    source = manifest.get("source_evidence", {})
    bindings = {
        "manifest": (
            "anchor_phase_manifest_path",
            "anchor_phase_manifest_sha256",
            root / "00_manifest" / "ANCHOR_PHASE_MANIFEST.json",
        ),
        "publication": (
            "anchor_phase_publication_path",
            "anchor_phase_publication_sha256",
            root / "00_manifest" / "ANCHOR_PHASE_PROMPT_PUBLICATION.json",
        ),
        "prompt_document": (
            "anchor_phase_prompt_document_path",
            "anchor_phase_prompt_document_sha256",
            root / "00_manifest" / "ANCHOR_PHASE_GENERATION_PROMPTS.md",
        ),
    }
    resolved: dict[str, Path] = {}
    for label, (path_field, sha_field, exact_path) in bindings.items():
        path = resolve_artifact(root, source.get(path_field), "anchor_phase_lineage_invalid")
        if path != exact_path.resolve() or path.is_symlink() or not path.is_file():
            raise ContractError("anchor_phase_lineage_invalid", f"anchor {label} snapshot is missing or misplaced")
        expected_sha = source.get(sha_field)
        if not isinstance(expected_sha, str) or not SHA_RE.fullmatch(expected_sha) or sha256_file(path) != expected_sha:
            raise ContractError("anchor_phase_lineage_invalid", f"anchor {label} snapshot hash differs")
        resolved[label] = path

    anchor = read_json(resolved["manifest"], "anchor_phase_lineage_invalid")
    required_top = {
        "schema_version", "job", "source_evidence", "evidence_ledger", "moment_canon",
        "camera_families", "views", "prompts", "attempts", "qa", "state",
        "prompt_set_sha256", "coverage_contract_sha256", "compiled_at_utc",
    }
    anchor_job = anchor.get("job", {})
    if (
        set(anchor) != required_top
        or anchor.get("schema_version") != MANIFEST_SCHEMA
        or anchor_job.get("job_id") != job.get("job_id")
        or anchor_job.get("mode") != "generate_and_package"
        or anchor_job.get("input_mode") != "text_anchor"
        or anchor_job.get("generation_phase") != "moment_anchor"
    ):
        raise ContractError("anchor_phase_lineage_invalid", "anchor manifest identity or schema differs")
    anchor_source = anchor.get("source_evidence", {})
    anchor_moment = anchor.get("moment_canon", {})
    if (
        anchor_source.get("source_evidence_sha256")
        != sha256_bytes(canonical_json({key: value for key, value in anchor_source.items() if key != "source_evidence_sha256"}))
        or anchor_moment.get("moment_canon_sha256")
        != sha256_bytes(canonical_json({key: value for key, value in anchor_moment.items() if key != "moment_canon_sha256"}))
    ):
        raise ContractError("anchor_phase_lineage_invalid", "anchor source or Moment Canon digest differs")
    if (
        not isinstance(anchor.get("views"), list)
        or len(anchor["views"]) != 1
        or anchor["views"][0].get("view_id") != "V00"
        or not isinstance(anchor.get("prompts"), list)
        or len(anchor["prompts"]) != 1
        or anchor["prompts"][0].get("view_id") != "V00"
    ):
        raise ContractError("anchor_phase_lineage_invalid", "anchor phase must contain exactly the V00 view and prompt")
    anchor_contract = {
        key: anchor[key]
        for key in (
            "schema_version", "job", "source_evidence", "evidence_ledger", "moment_canon",
            "camera_families", "prompts", "prompt_set_sha256",
        )
    }
    anchor_contract["views"] = [
        {key: value for key, value in view.items() if key != "status"}
        for view in anchor["views"]
    ]
    if anchor.get("coverage_contract_sha256") != sha256_bytes(canonical_json(anchor_contract)):
        raise ContractError("anchor_phase_lineage_invalid", "anchor coverage contract digest differs")
    anchor_prompt = anchor["prompts"][0]
    prompt_path = resolve_artifact(root, anchor_prompt.get("prompt_path"), "anchor_phase_lineage_invalid")
    if not prompt_path.is_file() or sha256_file(prompt_path) != anchor_prompt.get("prompt_sha256"):
        raise ContractError("anchor_phase_lineage_invalid", "anchor V00 prompt bytes are missing or changed")
    if anchor.get("prompt_set_sha256") != sha256_bytes(
        canonical_json([
            {key: anchor_prompt[key] for key in ("view_id", "prompt_sha256", "reference_plan_sha256")}
        ])
    ):
        raise ContractError("anchor_phase_lineage_invalid", "anchor prompt-set digest differs")

    publication = read_json(resolved["publication"], "anchor_phase_lineage_invalid")
    if (
        publication.get("schema_version") != "frozen_moment_prompt_publication_receipt.v1"
        or publication.get("phase") != "moment_anchor"
        or publication.get("input_mode") != "text_anchor"
        or publication.get("publication_status") != "prompt_artifacts_frozen"
        or publication.get("required_view_ids") != ["V00"]
        or publication.get("required_view_set_sha256") != sha256_bytes(canonical_json(["V00"]))
        or publication.get("published_prompt_ids") != ["V00"]
        or publication.get("published_prompt_sha256") != [anchor_prompt["prompt_sha256"]]
        or publication.get("published_reference_plan_sha256") != [anchor_prompt["reference_plan_sha256"]]
        or publication.get("prompt_document_sha256") != sha256_file(resolved["prompt_document"])
    ):
        raise ContractError("anchor_phase_lineage_invalid", "anchor publication receipt does not bind the V00 prompt package")

    anchor_context = {"prompt_by_view": {"V00": anchor_prompt}}
    try:
        attempt_evidence = validate_attempts(root, anchor, anchor_context)
    except ContractError as exc:
        raise ContractError("anchor_phase_lineage_invalid", f"anchor runtime evidence replay failed: {exc.code}: {exc.detail}") from exc
    approved = attempt_evidence["approved_by_view"]
    if set(approved) != {"V00"} or len(anchor.get("attempts", [])) != 1:
        raise ContractError("anchor_phase_lineage_invalid", "anchor phase lacks exactly one approved V00 attempt")
    queue = attempt_evidence["queue_records"]
    publication_ms = publication.get("published_at_unix_ms")
    if not isinstance(publication_ms, int) or publication_ms <= 0 or len(queue) != 1:
        raise ContractError("anchor_phase_lineage_invalid", "anchor publication or worker queue checkpoint is invalid")
    first = queue[0]
    if (
        first["not_before_ms"] < publication_ms
        or first["spawn_activity_ms"] < first["not_before_ms"]
        or publication.get("first_worker_spawn_event_index") != first["spawn_index"]
        or publication.get("first_worker_spawn_elapsed_ms") != first["spawn_activity_ms"] - publication_ms
    ):
        raise ContractError("anchor_phase_lineage_invalid", "anchor worker did not follow its prompt publication checkpoint")
    attempt = anchor["attempts"][0]
    accepted_image = resolve_artifact(root, source.get("accepted_anchor_image_path"), "anchor_phase_lineage_invalid")
    accepted_inspection = resolve_artifact(root, source.get("anchor_inspection_path"), "anchor_phase_lineage_invalid")
    if (
        resolve_artifact(root, attempt.get("image_path"), "anchor_phase_lineage_invalid") != accepted_image
        or attempt.get("image_sha256") != source.get("accepted_anchor_image_sha256")
        or sha256_file(accepted_image) != source.get("accepted_anchor_image_sha256")
        or resolve_artifact(root, attempt.get("inspection_path"), "anchor_phase_lineage_invalid") != accepted_inspection
        or attempt.get("inspection_sha256") != source.get("anchor_inspection_sha256")
        or sha256_file(accepted_inspection) != source.get("anchor_inspection_sha256")
    ):
        raise ContractError("anchor_phase_lineage_invalid", "coverage accepted-anchor fields differ from the replayed V00 attempt")


def validate_prompt_only(root: Path, manifest: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    if manifest["attempts"]:
        raise ContractError("prompt_only_worker_violation", "prompt-only manifest contains attempts")
    runtime_root = root / "10_runtime"
    image_root = root / "20_images"
    if runtime_root.exists() and any(path.is_file() for path in runtime_root.rglob("*")):
        raise ContractError("prompt_only_worker_violation", "prompt-only run contains runtime artifacts")
    if image_root.exists() and any(path.is_file() for path in image_root.rglob("*")):
        raise ContractError("prompt_only_worker_violation", "prompt-only run contains generated image artifacts")
    publication = context["publication"]
    if publication.get("first_worker_spawn_event_index") is not None or publication.get("first_worker_spawn_elapsed_ms") is not None:
        raise ContractError("prompt_only_worker_violation", "prompt-only publication receipt records worker activity")
    if manifest["state"] != {"current": "prompt_package_ready", "terminal_state": "prompt_package_ready"}:
        raise ContractError("prompt_only_state_invalid", "prompt-only run must end only at prompt_package_ready")
    if manifest["qa"].get("approved_required_view_ids") or manifest["qa"].get("all_required_views_approved"):
        raise ContractError("prompt_only_state_invalid", "prompt-only run cannot claim approved generated views")
    if manifest["qa"].get("runtime_evidence_origin") != "none":
        raise ContractError("prompt_only_worker_violation", "prompt-only runtime evidence origin must be none")
    return {"terminal_state": "prompt_package_ready", "approved_required_view_ids": []}


def accepted_prompt_handoff_payload(
    root: Path,
    manifest: dict[str, Any],
    approved_view_ids: list[str],
    terminal: str,
) -> tuple[dict[str, Any], str]:
    accepted: list[dict[str, Any]] = []
    document: list[str] = [
        f"# Accepted Frozen Moment Regeneration Prompts — {manifest['job']['job_id']}",
        "",
        f"- Terminal: `{terminal}`",
        f"- Base prompt set SHA-256: `{manifest['prompt_set_sha256']}`",
        f"- Coverage contract SHA-256: `{manifest['coverage_contract_sha256']}`",
        "",
    ]
    for view_id in approved_view_ids:
        attempts = [
            item for item in manifest.get("attempts", [])
            if item.get("view_id") == view_id and item.get("decision") == "approved"
        ]
        if len(attempts) != 1:
            raise ContractError("accepted_prompt_handoff_invalid", f"accepted view lacks one approved attempt: {view_id}")
        attempt = attempts[0]
        prompt_path = resolve_artifact(root, attempt.get("prompt_path"), "accepted_prompt_handoff_invalid")
        if not prompt_path.is_file() or sha256_file(prompt_path) != attempt.get("prompt_sha256"):
            raise ContractError("accepted_prompt_handoff_invalid", f"accepted prompt changed: {view_id}")
        authority_mode = attempt.get("prompt_authority_mode", "base_prompt")
        repair_path = attempt.get("repair_publication_path")
        repair_sha = attempt.get("repair_publication_sha256")
        if authority_mode == "repair_prompt":
            resolved_repair = resolve_artifact(root, repair_path, "accepted_prompt_handoff_invalid")
            if not resolved_repair.is_file() or sha256_file(resolved_repair) != repair_sha:
                raise ContractError("accepted_prompt_handoff_invalid", f"accepted repair receipt changed: {view_id}")
        elif authority_mode != "base_prompt" or repair_path is not None or repair_sha is not None:
            raise ContractError("accepted_prompt_handoff_invalid", f"accepted prompt authority is invalid: {view_id}")
        record = {
            "view_id": view_id,
            "attempt_id": attempt["attempt_id"],
            "attempt_revision": attempt["attempt_revision"],
            "prompt_authority_mode": authority_mode,
            "prompt_path": attempt["prompt_path"],
            "prompt_sha256": attempt["prompt_sha256"],
            "repair_publication_path": repair_path,
            "repair_publication_sha256": repair_sha,
            "image_path": attempt["image_path"],
            "image_sha256": attempt["image_sha256"],
            "inspection_path": attempt["inspection_path"],
            "inspection_sha256": attempt["inspection_sha256"],
        }
        accepted.append(record)
        document.extend(
            [
                f"## {view_id} — {attempt['attempt_id']}",
                "",
                f"- Prompt authority: `{authority_mode}`",
                f"- Prompt SHA-256: `{attempt['prompt_sha256']}`",
                f"- Image SHA-256: `{attempt['image_sha256']}`",
                "",
                prompt_path.read_text(encoding="utf-8").rstrip(),
                "",
            ]
        )
    document_text = "\n".join(document).rstrip() + "\n"
    index = {
        "schema_version": "frozen_moment_accepted_prompt_handoff.v1",
        "job_id": manifest["job"]["job_id"],
        "terminal": terminal,
        "coverage_completeness": "full_required_set" if terminal == "package_ready" else "partial_required_set",
        "base_prompt_set_sha256": manifest["prompt_set_sha256"],
        "coverage_contract_sha256": manifest["coverage_contract_sha256"],
        "approved_view_ids": approved_view_ids,
        "accepted_prompts": accepted,
        "prompt_document_path": "40_handoff/ACCEPTED_REGENERATION_PROMPTS.md",
        "prompt_document_sha256": sha256_bytes(document_text.encode("utf-8")),
    }
    return index, document_text


def validate_accepted_prompt_handoff(
    root: Path,
    manifest: dict[str, Any],
    approved_view_ids: list[str],
    terminal: str,
) -> None:
    index, expected_document = accepted_prompt_handoff_payload(root, manifest, approved_view_ids, terminal)
    index_path = root / "40_handoff" / "ACCEPTED_PROMPT_INDEX.json"
    actual = read_json(index_path, "accepted_prompt_handoff_invalid")
    if actual != index:
        raise ContractError("accepted_prompt_handoff_invalid", "accepted prompt index differs from approved attempt evidence")
    document_path = resolve_artifact(root, actual.get("prompt_document_path"), "accepted_prompt_handoff_invalid")
    if (
        not document_path.is_file()
        or document_path.read_bytes() != expected_document.encode("utf-8")
        or sha256_file(document_path) != actual.get("prompt_document_sha256")
    ):
        raise ContractError("accepted_prompt_handoff_invalid", "accepted regeneration prompt document differs")


def validate_generated(root: Path, manifest: dict[str, Any], context: dict[str, Any], mode: str, through_view: str | None) -> dict[str, Any]:
    attempt_evidence = validate_attempts(root, manifest, context)
    required = context["required_ids"]
    approved = [view_id for view_id in required if view_id in attempt_evidence["approved_by_view"]]
    qa = manifest["qa"]
    if qa.get("required_view_ids") != required or qa.get("approved_required_view_ids") != approved:
        raise ContractError("qa_state_mismatch", "QA required/approved view lists differ from actual attempts")
    all_approved = len(approved) == len(required)
    if qa.get("all_required_views_approved") is not all_approved:
        raise ContractError("qa_state_mismatch", "all_required_views_approved does not match actual evidence")
    if qa.get("max_parallel_workers", 1) != 1 or qa.get("unknown_inflight_call_count", 0) != 0:
        raise ContractError("worker_queue_invalid", "delivery requires one-worker queue and zero unknown in-flight calls")
    publication = context["publication"]
    publication_ms = publication.get("published_at_unix_ms")
    queue = attempt_evidence["queue_records"]
    if not isinstance(publication_ms, int) or publication_ms <= 0:
        raise ContractError("prompt_publication_invalid", "publication receipt lacks a Unix millisecond checkpoint")
    if queue:
        first = queue[0]
        if (
            first["not_before_ms"] < publication_ms
            or first["spawn_activity_ms"] < first["not_before_ms"]
            or publication.get("first_worker_spawn_event_index") != first["spawn_index"]
            or publication.get("first_worker_spawn_elapsed_ms") != first["spawn_activity_ms"] - publication_ms
        ):
            raise ContractError("prompt_publication_invalid", "first worker does not follow the frozen prompt publication checkpoint")
    elif publication.get("first_worker_spawn_event_index") is not None or publication.get("first_worker_spawn_elapsed_ms") is not None:
        raise ContractError("prompt_publication_invalid", "publication receipt records a worker that has no attempt evidence")
    if mode == "stage":
        if through_view not in required:
            raise ContractError("stage_view_invalid", f"--through-view is not required: {through_view}")
        prefix = required[: required.index(through_view) + 1]
        if any(view_id not in approved for view_id in prefix):
            raise ContractError("stage_prefix_incomplete", f"required prefix not approved through {through_view}: {prefix}")
        later_approved = [view_id for view_id in required[len(prefix) :] if view_id in approved]
        if later_approved:
            raise ContractError("stage_prefix_out_of_order", f"later views approved before prefix gate: {later_approved}")
        return {"terminal_state": None, "approved_required_view_ids": approved, "stage_through_view": through_view}
    if mode == "state":
        current = manifest["state"].get("current")
        terminal = manifest["state"].get("terminal_state")
        if current not in ACTIVE_STATES | TERMINALS or terminal not in TERMINALS | {None}:
            raise ContractError("state_invalid", "generated run state is unsupported")
        if terminal is not None and current != terminal:
            raise ContractError("state_transition_invalid", "terminal state must equal current state")
        if current == "prompts_locked" and (manifest["attempts"] or approved):
            raise ContractError("state_transition_invalid", "prompts_locked cannot contain attempts or approvals")
        if current == "view_approved" and not approved:
            raise ContractError("state_transition_invalid", "view_approved requires an approved view")
        if current in {"all_required_views_approved", "coverage_approved", "handoff_finalized", "package_ready"} and not all_approved:
            raise ContractError("state_transition_invalid", f"{current} requires all required views approved")
        if current == "blocked_attempt_budget":
            exhausted = [
                view_id for view_id in required
                if view_id not in approved
                and len(attempt_evidence["attempts_by_view"][view_id])
                >= manifest["job"]["max_attempts_per_view"]
            ]
            if not exhausted:
                raise ContractError("state_transition_invalid", "blocked_attempt_budget requires an exhausted required view")
        if current == "partial_handoff_ready" and (all_approved or not approved):
            raise ContractError("state_transition_invalid", "partial_handoff_ready requires some but not all required views approved")
        return {"terminal_state": terminal, "approved_required_view_ids": approved, "all_required_views_approved": all_approved}

    terminal = manifest["state"].get("terminal_state")
    current = manifest["state"].get("current")
    if terminal == "package_ready":
        if not all_approved or current != "package_ready":
            raise ContractError("premature_package_ready", "package_ready requires all required views approved")
        if any(view.get("status") != "view_approved" for view in manifest["views"] if view.get("required")):
            raise ContractError("premature_package_ready", "every required view must currently be view_approved")
    elif terminal == "partial_handoff_ready":
        if all_approved or not approved or current != "partial_handoff_ready":
            raise ContractError("partial_state_invalid", "partial handoff requires some but not all required views approved")
        blockers = qa.get("blocked_view_reasons")
        remaining = [view_id for view_id in required if view_id not in approved]
        if (
            not isinstance(blockers, dict)
            or set(blockers) != set(remaining)
            or any(
                not isinstance(blockers[view_id], list)
                or not blockers[view_id]
                or "blocked_attempt_budget" not in blockers[view_id]
                or len(attempt_evidence["attempts_by_view"][view_id]) < manifest["job"]["max_attempts_per_view"]
                for view_id in remaining
            )
        ):
            raise ContractError("partial_state_invalid", "partial handoff lacks blocker reasons for remaining views")
    else:
        raise ContractError("delivery_terminal_invalid", "generated delivery must end at package_ready or partial_handoff_ready")
    validate_accepted_prompt_handoff(root, manifest, approved, terminal)
    return {"terminal_state": terminal, "approved_required_view_ids": approved, "all_required_views_approved": all_approved}


def validate_package(root: Path, mode: str, through_view: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    manifest_path = root / "00_manifest" / "COVERAGE_MANIFEST.json"
    manifest = read_json(manifest_path, "package_manifest_invalid")
    context = validate_manifest_structure(root, manifest)
    validate_text_anchor_phase_lineage(root, manifest)
    if manifest["job"]["mode"] == "prompt_only":
        if mode == "stage":
            raise ContractError("stage_mode_invalid", "prompt-only runs have no generation stage")
        result = validate_prompt_only(root, manifest, context)
    else:
        result = validate_generated(root, manifest, context, mode, through_view)
    return {
        "ok": True,
        "mode": mode,
        "run_root": str(root),
        "manifest_sha256": sha256_file(manifest_path),
        "job_id": manifest["job"]["job_id"],
        "coverage_profile": manifest["job"]["coverage_profile"],
        **result,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("state", "stage", "delivery"), default="delivery")
    parser.add_argument("--through-view")
    parser.add_argument("run_root", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.mode == "stage" and not args.through_view:
        print(json.dumps({"ok": False, "error_code": "stage_view_missing", "detail": "--through-view is required"}), file=sys.stderr)
        return 2
    try:
        result = validate_package(args.run_root, args.mode, args.through_view)
    except ContractError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}, ensure_ascii=False), file=sys.stderr)
        return 2
    except OSError as exc:
        print(json.dumps({"ok": False, "error_code": "package_filesystem_error", "detail": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
