#!/usr/bin/env python3
"""Compile a frozen-moment input specification into an auditable prompt package."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError


INPUT_SCHEMA = "frozen_moment_coverage_input.v1"
MANIFEST_SCHEMA = "frozen_moment_coverage_manifest.v1"
EVIDENCE_CLASSES = (
    "observed",
    "source_corroborated",
    "inferred",
    "unknown",
    "approved_canon",
)
PROFILES = {"targeted_views", "minimum_ring", "robust_ring", "custom"}
MODES = {"prompt_only", "generate_and_package"}
INPUT_MODES = {"image_anchor", "text_anchor"}
UNCERTAINTY_POLICIES = {"source_bounded", "conservative_hypothesis", "design_expansion"}
DEFAULT_BINS = {
    "minimum_ring": [0.0, 90.0, 180.0, 270.0],
    "robust_ring": [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0],
}
ROLE_BY_ANGLE = {
    0: "front",
    45: "right_front_three_quarter",
    90: "right_profile",
    135: "right_rear_three_quarter",
    180: "rear",
    225: "left_rear_three_quarter",
    270: "left_profile",
    315: "left_front_three_quarter",
}
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
    "moment_anchor",
    "identity_anchor",
    "wardrobe_anchor",
    "scene_topology_anchor",
    "look_anchor",
}
PROMPT_CONTEXT_CONTRACT = {
    "task_definition": "Recreate the same frozen instant while moving only the camera.",
    "identity_pose_contact_lock": "Keep identity, age, body, pose, balance, head, expression, gaze, wardrobe, asymmetry, hands, props, and contacts unchanged.",
    "scene_time_light_lock": "Keep scene topology, object positions, temporal state, and all light sources fixed in world space.",
    "look_contract": "Match the source camera character, depth, palette, texture, and grain without cosmetic retouching.",
    "negative_contract": "No mirroring, subject rotation, new action, new gaze, crop or zoom substitute, scene relayout, camera-following beauty light, added person, text, logo, or unsupported salient detail.",
}
CANON_LIST_FIELDS = ("subjects", "scene_topology", "temporal_state", "lighting", "look", "prohibited_changes")


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


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_bytes_atomic(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(value)
    os.replace(temporary, path)


def write_text_atomic(path: Path, value: str) -> None:
    write_bytes_atomic(path, value.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8"))


def write_json_atomic(path: Path, value: Any) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    write_text_atomic(path, text)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("blocked_input_invalid", f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError("blocked_input_invalid", "input specification must be a JSON object")
    return value


def ensure_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError("blocked_input_invalid", f"{field} must be a non-empty string")
    return value.strip()


def normalize_angle(value: float) -> float:
    result = (float(value) % 360.0 + 360.0) % 360.0
    return 0.0 if math.isclose(result, 360.0, abs_tol=1e-9) else result


def circular_diff(left: float, right: float) -> float:
    return abs(((normalize_angle(left) - normalize_angle(right) + 180.0) % 360.0) - 180.0)


def validate_evidence_ledger(value: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(value, dict) or set(value) != set(EVIDENCE_CLASSES):
        raise ContractError(
            "blocked_input_invalid",
            "evidence_ledger must contain exactly observed, source_corroborated, inferred, unknown, approved_canon",
        )
    seen: set[str] = set()
    result: dict[str, list[dict[str, Any]]] = {}
    for evidence_class in EVIDENCE_CLASSES:
        entries = value[evidence_class]
        if not isinstance(entries, list):
            raise ContractError("blocked_input_invalid", f"evidence_ledger.{evidence_class} must be a list")
        normalized: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise ContractError("blocked_input_invalid", "evidence entries must be objects")
            evidence_id = ensure_nonempty_string(entry.get("evidence_id"), "evidence_id")
            if evidence_id in seen:
                raise ContractError("blocked_input_invalid", f"duplicate evidence_id: {evidence_id}")
            seen.add(evidence_id)
            for field in ("scope", "claim", "confidence", "conflict_state"):
                ensure_nonempty_string(entry.get(field), f"{evidence_id}.{field}")
            if entry["confidence"] not in {"low", "medium", "high"}:
                raise ContractError("blocked_input_invalid", f"invalid confidence for {evidence_id}")
            if entry["conflict_state"] not in {"none", "resolved", "unresolved"}:
                raise ContractError("blocked_input_invalid", f"invalid conflict_state for {evidence_id}")
            if entry["conflict_state"] == "unresolved":
                raise ContractError("blocked_conflicting_authority", f"unresolved evidence conflict: {evidence_id}")
            source_ids = entry.get("source_ids")
            if not isinstance(source_ids, list) or not all(isinstance(item, str) and item for item in source_ids):
                raise ContractError("blocked_input_invalid", f"{evidence_id}.source_ids must be a string list")
            normalized.append(deepcopy(entry))
        result[evidence_class] = normalized
    if not any(result[evidence_class] for evidence_class in EVIDENCE_CLASSES):
        raise ContractError("blocked_missing_input", "evidence_ledger cannot be empty for a claimed frozen moment")
    return result


def validate_evidence_authority(
    ledger: dict[str, list[dict[str, Any]]],
    *,
    input_mode: str,
    source_evidence: dict[str, Any],
    canon_status: str,
) -> None:
    reference_ids = source_evidence.get("reference_ids", [])
    if not isinstance(reference_ids, list) or not all(isinstance(item, str) and item for item in reference_ids):
        raise ContractError("blocked_evidence_authority_invalid", "source reference IDs are invalid")
    reference_set = set(reference_ids)
    for evidence_class, entries in ledger.items():
        for entry in entries:
            ordered_source_ids = entry["source_ids"]
            source_ids = set(ordered_source_ids)
            if not source_ids or len(source_ids) != len(ordered_source_ids):
                raise ContractError(
                    "blocked_evidence_authority_invalid",
                    f"{entry['evidence_id']} must cite a non-empty set of unique authority IDs",
                )
            if evidence_class == "observed" and not source_ids <= reference_set:
                raise ContractError(
                    "blocked_evidence_authority_invalid",
                    f"{entry['evidence_id']} claims source observation without frozen source bytes",
                )
            if evidence_class == "source_corroborated" and (len(source_ids) < 2 or not source_ids <= reference_set):
                raise ContractError(
                    "blocked_evidence_authority_invalid",
                    f"{entry['evidence_id']} requires at least two distinct frozen source references",
                )
            if evidence_class == "inferred" and not source_ids <= reference_set | {"model_inference", "text_brief"}:
                raise ContractError(
                    "blocked_evidence_authority_invalid",
                    f"{entry['evidence_id']} cites an authority that cannot support an inference",
                )
            if evidence_class == "unknown" and ordered_source_ids != ["unobserved"]:
                raise ContractError(
                    "blocked_evidence_authority_invalid",
                    f"{entry['evidence_id']} unknown claims must cite exactly unobserved",
                )
            if evidence_class == "approved_canon" and not source_ids <= {"user_approval", "main_inspection"}:
                raise ContractError(
                    "blocked_evidence_authority_invalid",
                    f"{entry['evidence_id']} approved canon must cite only user_approval or main_inspection",
                )
            if evidence_class == "approved_canon" and "main_inspection" in source_ids and not source_evidence.get("anchor_inspection_sha256"):
                raise ContractError(
                    "blocked_evidence_authority_invalid",
                    f"{entry['evidence_id']} cites main_inspection without a bound anchor inspection",
                )
    if input_mode == "text_anchor" and not reference_set and (ledger["observed"] or ledger["source_corroborated"]):
        raise ContractError(
            "blocked_evidence_authority_invalid",
            "unrendered text input cannot claim observed or source-corroborated image evidence",
        )
    if canon_status == "approved_canon" and not ledger["approved_canon"]:
        raise ContractError(
            "blocked_evidence_authority_invalid",
            "approved_canon status requires an explicit approved_canon evidence entry",
        )


def reject_prompt_control_text(value: Any, field_path: str) -> None:
    if isinstance(value, str):
        if PROMPT_CONTROL_OVERRIDE_RE.search(value):
            raise ContractError(
                "blocked_prompt_contract_override",
                f"{field_path} contains instruction-like text that attempts to override the camera-only contract",
            )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            reject_prompt_control_text(item, f"{field_path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            reject_prompt_control_text(item, f"{field_path}.{key}")


def validate_moment_canon(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("blocked_missing_input", "moment_canon must be an object")
    moment = deepcopy(value)
    reject_prompt_control_text(moment, "moment_canon")
    ensure_nonempty_string(moment.get("moment_id"), "moment_canon.moment_id")
    for field in CANON_LIST_FIELDS:
        entries = moment.get(field)
        if not isinstance(entries, list) or not entries:
            raise ContractError("blocked_missing_input", f"moment_canon.{field} must be a non-empty list")
    for index, subject in enumerate(moment["subjects"]):
        if not isinstance(subject, dict):
            raise ContractError("blocked_missing_input", f"moment_canon.subjects[{index}] must be an object")
        for field in ("subject_id", "identity", "pose", "head_expression_gaze", "wardrobe"):
            ensure_nonempty_string(subject.get(field), f"moment_canon.subjects[{index}].{field}")
        contacts = subject.get("contacts")
        if not isinstance(contacts, list) or not contacts or not all(isinstance(item, str) and item.strip() for item in contacts):
            raise ContractError("blocked_missing_input", f"moment_canon.subjects[{index}].contacts must be a non-empty string list")
        for vector_field in ("head_direction", "gaze_direction"):
            vector = subject.get(vector_field)
            if vector is None:
                continue
            if (
                not isinstance(vector, dict)
                or not isinstance(vector.get("yaw_deg"), (int, float))
                or not isinstance(vector.get("pitch_deg"), (int, float))
            ):
                raise ContractError("blocked_input_invalid", f"{subject['subject_id']}.{vector_field} requires numeric yaw_deg/pitch_deg")
    for field in CANON_LIST_FIELDS[1:]:
        if not all(isinstance(item, str) and item.strip() for item in moment[field]):
            raise ContractError("blocked_missing_input", f"moment_canon.{field} must contain non-empty strings")
    return moment


def inspect_reference_image(path: Path) -> str:
    try:
        with Image.open(path) as image:
            image.verify()
            image_format = image.format
    except (OSError, UnidentifiedImageError) as exc:
        raise ContractError("blocked_reference_materialization", f"reference is not a decodable image: {path}: {exc}") from exc
    if image_format not in {"PNG", "JPEG", "WEBP"}:
        raise ContractError("blocked_reference_materialization", f"unsupported reference image format {image_format}: {path}")
    return image_format


def validate_anchor_acceptance(source: dict[str, Any], output_root: Path) -> dict[str, str]:
    fields = (
        "accepted_anchor_image_path",
        "accepted_anchor_image_sha256",
        "anchor_inspection_path",
        "anchor_inspection_sha256",
    )
    if any(not isinstance(source.get(field), str) or not source[field] for field in fields):
        raise ContractError("blocked_prompt_publication", "text coverage requires anchor image and inspection paths plus SHA-256")
    image = Path(source["accepted_anchor_image_path"])
    inspection_path = Path(source["anchor_inspection_path"])
    for path, label in ((image, "anchor image"), (inspection_path, "anchor inspection")):
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            raise ContractError("blocked_prompt_publication", f"{label} path is invalid: {path}")
        try:
            path.resolve().relative_to(output_root)
        except ValueError as exc:
            raise ContractError("blocked_prompt_publication", f"{label} must remain inside the run root") from exc
    if not SHA_RE.fullmatch(source["accepted_anchor_image_sha256"]) or sha256_file(image) != source["accepted_anchor_image_sha256"]:
        raise ContractError("blocked_prompt_publication", "accepted anchor image hash is missing or changed")
    inspect_reference_image(image)
    if not SHA_RE.fullmatch(source["anchor_inspection_sha256"]) or sha256_file(inspection_path) != source["anchor_inspection_sha256"]:
        raise ContractError("blocked_prompt_publication", "anchor inspection hash is missing or changed")
    inspection = read_json(inspection_path)
    if (
        inspection.get("schema_version") != "frozen_moment_main_inspection.v1"
        or inspection.get("decision") != "approved"
        or inspection.get("view_id") != "V00"
        or inspection.get("image_sha256") != source["accepted_anchor_image_sha256"]
        or inspection.get("superseded") is True
    ):
        raise ContractError("blocked_prompt_publication", "anchor inspection is not a current approved V00 image inspection")
    previous_manifest_path = output_root / "00_manifest" / "COVERAGE_MANIFEST.json"
    if not previous_manifest_path.is_file() or previous_manifest_path.is_symlink():
        raise ContractError("blocked_prompt_publication", "text coverage requires a validated prior V00 anchor run")
    try:
        import validate_coverage_package as package_validator
    except ImportError as exc:
        raise ContractError("blocked_prompt_publication", f"anchor validator unavailable: {exc}") from exc
    try:
        package_validator.validate_package(output_root, "stage", "V00")
    except package_validator.ContractError as exc:
        detail = getattr(exc, "detail", str(exc))
        raise ContractError("blocked_prompt_publication", f"prior V00 anchor package is invalid: {detail}") from exc
    previous_manifest = read_json(previous_manifest_path)
    if (
        previous_manifest.get("job", {}).get("input_mode") != "text_anchor"
        or previous_manifest.get("job", {}).get("generation_phase") != "moment_anchor"
    ):
        raise ContractError("blocked_prompt_publication", "prior package is not the text V00 anchor phase")
    approved = [
        attempt for attempt in previous_manifest.get("attempts", [])
        if attempt.get("view_id") == "V00" and attempt.get("decision") == "approved"
    ]
    if len(approved) != 1:
        raise ContractError("blocked_prompt_publication", "prior V00 anchor phase lacks exactly one approved attempt")
    attempt = approved[0]
    if (
        (output_root / str(attempt.get("image_path", ""))).resolve() != image.resolve()
        or attempt.get("image_sha256") != source["accepted_anchor_image_sha256"]
        or (output_root / str(attempt.get("inspection_path", ""))).resolve() != inspection_path.resolve()
        or attempt.get("inspection_sha256") != source["anchor_inspection_sha256"]
    ):
        raise ContractError("blocked_prompt_publication", "accepted anchor fields do not bind the validated V00 attempt")
    previous_publication_path = output_root / "00_manifest" / "PROMPT_PUBLICATION.json"
    if not previous_publication_path.is_file() or previous_publication_path.is_symlink():
        raise ContractError("blocked_prompt_publication", "text coverage requires the validated prior V00 publication receipt")
    previous_prompt_document_path = output_root / "00_manifest" / "GENERATION_PROMPTS.md"
    if not previous_prompt_document_path.is_file() or previous_prompt_document_path.is_symlink():
        raise ContractError("blocked_prompt_publication", "text coverage requires the validated prior V00 prompt document")
    manifest_snapshot = output_root / "00_manifest" / "ANCHOR_PHASE_MANIFEST.json"
    publication_snapshot = output_root / "00_manifest" / "ANCHOR_PHASE_PROMPT_PUBLICATION.json"
    prompt_document_snapshot = output_root / "00_manifest" / "ANCHOR_PHASE_GENERATION_PROMPTS.md"
    for snapshot, source_path in (
        (manifest_snapshot, previous_manifest_path),
        (publication_snapshot, previous_publication_path),
        (prompt_document_snapshot, previous_prompt_document_path),
    ):
        source_bytes = source_path.read_bytes()
        if snapshot.exists() and (snapshot.is_symlink() or not snapshot.is_file() or snapshot.read_bytes() != source_bytes):
            raise ContractError("blocked_prompt_publication", f"anchor phase snapshot conflicts with validated evidence: {snapshot}")
        write_bytes_atomic(snapshot, source_bytes)
    return {
        "anchor_phase_manifest_path": manifest_snapshot.relative_to(output_root).as_posix(),
        "anchor_phase_manifest_sha256": sha256_file(manifest_snapshot),
        "anchor_phase_publication_path": publication_snapshot.relative_to(output_root).as_posix(),
        "anchor_phase_publication_sha256": sha256_file(publication_snapshot),
        "anchor_phase_prompt_document_path": prompt_document_snapshot.relative_to(output_root).as_posix(),
        "anchor_phase_prompt_document_sha256": sha256_file(prompt_document_snapshot),
    }


def validate_family(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("blocked_input_invalid", "camera family must be an object")
    required = (
        "family_id",
        "family_kind",
        "coordinate_frame_id",
        "projection",
        "azimuth_basis",
        "varying_fields",
        "orbit_radius_ratio",
        "orbit_elevation_deg",
        "roll_deg",
        "look_at_target",
        "focus_target",
        "focal_policy",
        "shot_scale",
        "framing_policy",
        "crop_policy",
        "subject_scale_policy",
    )
    for field in required:
        if field not in value:
            raise ContractError("blocked_input_invalid", f"camera family missing {field}")
    family = deepcopy(value)
    ensure_nonempty_string(family["family_id"], "family_id")
    if family["family_kind"] not in {"master", "portrait"}:
        raise ContractError("E_FAMILY_MIX", f"unsupported family_kind: {family['family_kind']}")
    if family["azimuth_basis"] not in {"subject_forward", "source_camera_relative"}:
        raise ContractError("E_COORDINATE_BASIS_UNKNOWN", "azimuth_basis must be subject_forward or source_camera_relative")
    if family["varying_fields"] != ["azimuth_deg"]:
        raise ContractError("E_FAMILY_INVARIANT_DRIFT", "a camera family may vary only azimuth_deg")
    if not isinstance(family["orbit_radius_ratio"], (int, float)) or family["orbit_radius_ratio"] <= 0:
        raise ContractError("blocked_input_invalid", "orbit_radius_ratio must be positive")
    for field in ("orbit_elevation_deg", "roll_deg"):
        if not isinstance(family[field], (int, float)):
            raise ContractError("blocked_input_invalid", f"{field} must be numeric")
    focal_range = family.get("focal_length_equiv_mm")
    if focal_range is not None:
        if (
            not isinstance(focal_range, list)
            or len(focal_range) != 2
            or not all(isinstance(item, (int, float)) and item > 0 for item in focal_range)
            or focal_range[0] > focal_range[1]
        ):
            raise ContractError("E_OPTICS_INCONSISTENT", "focal_length_equiv_mm must be an ascending positive range")
    family["family_contract_sha256"] = sha256_bytes(canonical_json({k: v for k, v in family.items() if k != "family_contract_sha256"}))
    return family


def default_views(profile: str, family_id: str) -> list[dict[str, Any]]:
    if profile not in DEFAULT_BINS:
        return []
    return [
        {
            "view_id": f"V{int(angle):03d}",
            "family_id": family_id,
            "coverage_role": ROLE_BY_ANGLE[int(angle)],
            "required": True,
            "azimuth_deg": angle,
            "elevation_deg": 0.0,
            "visibility": {
                "must_remain_visible": [],
                "expected_visible": [],
                "expected_occluded": [],
                "newly_revealed": [],
                "persistent_occluders": [],
                "forbidden_reveals": [],
                "face_visibility_goal": "natural_from_frozen_pose",
                "common_anchor_ids": [],
            },
            "evidence_risk": "hypothesis_heavy" if angle in {135.0, 180.0, 225.0} else "medium",
        }
        for angle in DEFAULT_BINS[profile]
    ]


def validate_views(
    profile: str,
    raw_views: Any,
    families: dict[str, dict[str, Any]],
    full_coverage_claim: bool,
    moment: dict[str, Any],
) -> list[dict[str, Any]]:
    if not isinstance(raw_views, list):
        raise ContractError("blocked_input_invalid", "views must be a list")
    if not raw_views:
        master_ids = [key for key, family in families.items() if family["family_kind"] == "master"]
        if profile in DEFAULT_BINS and master_ids:
            raw_views = default_views(profile, master_ids[0])
        else:
            raise ContractError("blocked_input_invalid", f"{profile} requires explicit views")
    views: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw in raw_views:
        if not isinstance(raw, dict):
            raise ContractError("blocked_input_invalid", "view must be an object")
        view_id = ensure_nonempty_string(raw.get("view_id"), "view_id").upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9_-]{1,31}", view_id):
            raise ContractError("blocked_input_invalid", f"invalid view_id: {view_id}")
        if view_id in seen_ids:
            raise ContractError("E_TUPLE_DUPLICATE", f"duplicate view_id: {view_id}")
        seen_ids.add(view_id)
        family_id = ensure_nonempty_string(raw.get("family_id"), f"{view_id}.family_id")
        if family_id not in families:
            raise ContractError("E_FAMILY_MIX", f"unknown family for {view_id}: {family_id}")
        angle = raw.get("azimuth_deg")
        if not isinstance(angle, (int, float)):
            raise ContractError("blocked_input_invalid", f"{view_id}.azimuth_deg must be numeric")
        elevation = raw.get("elevation_deg", families[family_id]["orbit_elevation_deg"])
        if not isinstance(elevation, (int, float)):
            raise ContractError("blocked_input_invalid", f"{view_id}.elevation_deg must be numeric")
        if not math.isclose(float(elevation), float(families[family_id]["orbit_elevation_deg"]), abs_tol=0.001):
            raise ContractError("E_FAMILY_INVARIANT_DRIFT", f"{view_id} elevation differs from family")
        view = deepcopy(raw)
        view.update(
            {
                "view_id": view_id,
                "family_id": family_id,
                "coverage_role": ensure_nonempty_string(raw.get("coverage_role", f"azimuth_{normalize_angle(angle):g}"), f"{view_id}.coverage_role"),
                "required": bool(raw.get("required", True)),
                "azimuth_deg": normalize_angle(angle),
                "elevation_deg": float(elevation),
                "visibility": deepcopy(raw.get("visibility", {})),
                "evidence_risk": raw.get("evidence_risk", "medium"),
                "status": "prompt_ready",
            }
        )
        if view["evidence_risk"] not in {"low", "medium", "high", "hypothesis_heavy"}:
            raise ContractError("blocked_input_invalid", f"invalid evidence_risk for {view_id}")
        visibility = view["visibility"]
        if not isinstance(visibility, dict):
            raise ContractError("blocked_input_invalid", f"{view_id}.visibility must be an object")
        for field in (
            "must_remain_visible",
            "expected_visible",
            "expected_occluded",
            "newly_revealed",
            "persistent_occluders",
            "forbidden_reveals",
            "common_anchor_ids",
        ):
            items = visibility.setdefault(field, [])
            if not isinstance(items, list):
                raise ContractError("blocked_input_invalid", f"{view_id}.visibility.{field} must be a list")
        goal = visibility.setdefault("face_visibility_goal", "natural_from_frozen_pose")
        if goal not in {"natural_from_frozen_pose", "full_face", "eye_contact", "as_text_defined", "not_applicable"}:
            raise ContractError("blocked_input_invalid", f"{view_id}.face_visibility_goal is invalid")
        if goal in {"full_face", "eye_contact"}:
            subject_id = visibility.get("subject_id") or moment["subjects"][0]["subject_id"]
            subject = next((item for item in moment["subjects"] if item["subject_id"] == subject_id), None)
            if subject is None:
                raise ContractError("blocked_physical_conflict", f"{view_id} references unknown face subject {subject_id}")
            vector_field = "head_direction" if goal == "full_face" else "gaze_direction"
            vector = subject.get(vector_field)
            if not isinstance(vector, dict):
                raise ContractError("blocked_physical_conflict", f"{view_id} requests {goal} without an approved {vector_field}")
            yaw_tolerance = 15.0 if goal == "full_face" else 5.0
            pitch_tolerance = 10.0 if goal == "full_face" else 5.0
            if (
                circular_diff(view["azimuth_deg"], float(vector["yaw_deg"])) > yaw_tolerance
                or abs(view["elevation_deg"] - float(vector["pitch_deg"])) > pitch_tolerance
            ):
                raise ContractError("blocked_physical_conflict", f"{view_id} {goal} conflicts with the frozen {vector_field}")
        camera_contract = {
            "family": {k: v for k, v in families[family_id].items() if k != "family_contract_sha256"},
            "view_id": view_id,
            "coverage_role": view["coverage_role"],
            "required": view["required"],
            "azimuth_deg": view["azimuth_deg"],
            "elevation_deg": view["elevation_deg"],
            "visibility": view["visibility"],
            "micro_coverage": bool(view.get("micro_coverage", False)),
            "expected_parallax_region_ids": view.get("expected_parallax_region_ids", []),
        }
        view["camera_contract_sha256"] = sha256_bytes(canonical_json(camera_contract))
        views.append(view)

    required = [view for view in views if view["required"]]
    if profile == "targeted_views":
        if not 1 <= len(required) <= 3:
            raise ContractError("E_RING_WRONG_COUNT", "targeted_views requires one to three required views")
        if full_coverage_claim:
            raise ContractError("E_TARGETED_OVERCLAIM", "targeted views cannot claim full coverage")
    elif profile == "custom" and full_coverage_claim:
        raise ContractError("E_CUSTOM_OVERCLAIM", "custom coverage cannot claim full coverage; use a validated ring profile")
    elif profile in DEFAULT_BINS:
        expected = DEFAULT_BINS[profile]
        if len(required) != len(expected):
            raise ContractError("E_RING_WRONG_COUNT", f"{profile} requires exactly {len(expected)} required views")
        family_ids = {view["family_id"] for view in required}
        if len(family_ids) != 1:
            raise ContractError("E_FAMILY_MIX", f"{profile} required views must use one family")
        if families[next(iter(family_ids))]["family_kind"] != "master":
            raise ContractError("E_MASTER_PORTRAIT_AGGREGATION", "master coverage cannot be completed by a portrait family")
        assigned: dict[float, str] = {}
        for view in required:
            matches = [target for target in expected if circular_diff(view["azimuth_deg"], target) <= 3.0]
            if len(matches) != 1:
                raise ContractError("E_RING_MISSING_BIN", f"{view['view_id']} does not map to exactly one {profile} bin")
            target = matches[0]
            if target in assigned:
                raise ContractError("E_RING_DUPLICATE_BIN", f"{view['view_id']} duplicates bin {target:g}")
            assigned[target] = view["view_id"]
        missing = [target for target in expected if target not in assigned]
        if missing:
            raise ContractError("E_RING_MISSING_BIN", f"missing bins: {missing}")

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
    return views


def load_reference_evidence(
    spec: dict[str, Any], output_root: Path, job_id: str, generation_phase: str
) -> tuple[dict[str, Any], str, list[str]]:
    source = deepcopy(spec.get("source_evidence"))
    if not isinstance(source, dict):
        raise ContractError("blocked_input_invalid", "source_evidence must be an object")
    input_mode = spec["job"]["input_mode"]
    path_value = source.get("reference_manifest_path")
    reference_labels: list[str] = []
    if path_value:
        reference_path = Path(path_value).expanduser()
        if not reference_path.is_absolute():
            raise ContractError("blocked_reference_materialization", "reference_manifest_path must be absolute")
        destination = output_root / "00_manifest" / "REFERENCE_BINDINGS.json"
        if reference_path.resolve() != destination.resolve():
            raise ContractError(
                "blocked_reference_manifest_location",
                "freeze the reference bundle directly at <run-root>/00_manifest/REFERENCE_BINDINGS.json before compilation",
            )
        reference_manifest = read_json(reference_path)
        required_manifest_keys = {
            "schema_version", "run_id", "view_id", "attempt_id", "source_evidence_sha256",
            "moment_canon_sha256", "reference_plan_sha256", "ordered_references",
            "ordered_bundle_sha256", "immutability_contract", "provider_reference_count",
        }
        if set(reference_manifest) != required_manifest_keys or reference_manifest.get("schema_version") != "frozen_moment_reference_bundle.v1":
            raise ContractError("blocked_reference_manifest_hash_mismatch", "reference manifest fields or schema are invalid")
        if reference_manifest.get("run_id") != job_id or reference_manifest.get("attempt_id") != "PLAN":
            raise ContractError("blocked_reference_manifest_hash_mismatch", "reference manifest does not bind this job PLAN")
        entries = reference_manifest.get("ordered_references")
        if not isinstance(entries, list) or not 1 <= len(entries) <= 5 or reference_manifest.get("provider_reference_count") != len(entries):
            raise ContractError("blocked_reference_materialization", "reference manifest has no references")
        if entries[0].get("role") != "moment_anchor":
            raise ContractError("blocked_reference_materialization", "image input requires moment_anchor first")
        reference_root = destination.parent / "references"
        if not reference_root.is_dir() or reference_root.is_symlink():
            raise ContractError("blocked_reference_manifest_location", "run-scoped reference directory is missing or linked")
        planned: list[dict[str, Any]] = []
        frozen_paths: list[Path] = []
        ids: set[str] = set()
        aliases: set[str] = set()
        for expected_index, entry in enumerate(entries, 1):
            if not isinstance(entry, dict) or entry.get("index") != expected_index:
                raise ContractError("blocked_reference_manifest_hash_mismatch", "reference entries are not contiguous objects")
            reference_id = entry.get("reference_id")
            alias = entry.get("alias")
            role = entry.get("role")
            frozen_raw = entry.get("frozen_path")
            if (
                not isinstance(reference_id, str) or not reference_id
                or not isinstance(alias, str) or not alias
                or role not in REFERENCE_ROLES
                or not isinstance(frozen_raw, str) or not frozen_raw
                or reference_id in ids or alias in aliases
            ):
                raise ContractError("blocked_reference_manifest_hash_mismatch", "reference identity, role, or uniqueness is invalid")
            ids.add(reference_id)
            aliases.add(alias)
            frozen = Path(frozen_raw)
            if not frozen.is_absolute() or frozen.is_symlink():
                raise ContractError("blocked_reference_manifest_location", f"invalid frozen reference path: {frozen}")
            try:
                frozen.resolve().relative_to(reference_root.resolve())
            except ValueError as exc:
                raise ContractError("blocked_reference_manifest_location", f"reference escapes run bundle: {frozen}") from exc
            if not frozen.is_file() or frozen.stat().st_size != entry.get("size_bytes") or sha256_file(frozen) != entry.get("sha256"):
                raise ContractError("blocked_reference_bytes_changed", f"frozen reference is missing or changed: {frozen}")
            if inspect_reference_image(frozen) != entry.get("media_format"):
                raise ContractError("blocked_reference_bytes_changed", f"reference media format differs: {frozen}")
            if any(entry.get(field) is not None for field in ("origin_view_id", "origin_attempt_id", "origin_inspection_sha256", "origin_inspection_path")):
                raise ContractError("blocked_reference_manifest_hash_mismatch", f"v1 references cannot carry generated bridge origins: {reference_id}")
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
            frozen_paths.append(frozen.resolve())
        actual_files = {path.resolve() for path in reference_root.iterdir() if path.is_file()}
        if any(path.is_dir() for path in reference_root.iterdir()) or actual_files != set(frozen_paths):
            raise ContractError("blocked_reference_manifest_hash_mismatch", "reference directory contains missing, extra, or nested entries")
        expected_plan_sha = sha256_bytes(canonical_json(planned))
        if reference_manifest.get("reference_plan_sha256") != expected_plan_sha:
            raise ContractError("blocked_reference_manifest_hash_mismatch", "reference plan digest mismatch")
        if reference_manifest.get("ordered_bundle_sha256") != sha256_bytes(canonical_json(entries)):
            raise ContractError("blocked_reference_manifest_hash_mismatch", "ordered reference bundle digest mismatch")
        if input_mode == "text_anchor" and generation_phase == "coverage":
            if entries[0].get("sha256") != source.get("accepted_anchor_image_sha256"):
                raise ContractError("blocked_prompt_publication", "coverage moment_anchor bytes do not match the accepted V00 anchor")
        reference_labels = [f"{entry['index']}. {entry['reference_id']} ({entry['role']})" for entry in entries]
        source["reference_ids"] = [entry["reference_id"] for entry in entries]
        reference_sha = reference_manifest["reference_plan_sha256"]
        source["reference_manifest_path"] = str(destination.resolve())
        source["reference_manifest_sha256"] = sha256_file(destination)
        source["ordered_reference_bundle_sha256"] = reference_manifest.get("ordered_bundle_sha256")
    else:
        if input_mode == "image_anchor":
            raise ContractError("blocked_reference_materialization", "image_anchor requires a frozen reference manifest")
        reference_plan = {"schema_version": "frozen_moment_reference_bundle.v1", "ordered_references": [], "input_mode": input_mode}
        reference_sha = sha256_bytes(canonical_json(reference_plan))
        source["reference_manifest_path"] = None
        source["reference_manifest_sha256"] = None
        source["ordered_reference_bundle_sha256"] = sha256_bytes(canonical_json([]))
        source["reference_ids"] = []
    source["reference_plan_sha256"] = reference_sha
    source["source_evidence_sha256"] = sha256_bytes(canonical_json({key: value for key, value in source.items() if key != "source_evidence_sha256"}))
    return source, reference_sha, reference_labels


def compile_prompt(
    context: dict[str, Any],
    moment: dict[str, Any],
    family: dict[str, Any],
    view: dict[str, Any],
    reference_labels: list[str],
    uncertainty_policy: str,
) -> str:
    references = "；".join(reference_labels) if reference_labels else "无图像参考；仅使用 synthetic_unrendered 文字 Canon"
    subjects = json.dumps(moment.get("subjects", []), ensure_ascii=False, separators=(",", ":"))
    scene = "；".join(str(item) for item in moment.get("scene_topology", [])) or "保持已声明场景拓扑"
    temporal = "；".join(str(item) for item in moment.get("temporal_state", [])) or "保持同一冻结时刻"
    lighting = "；".join(str(item) for item in moment.get("lighting", [])) or "光源固定于世界空间"
    look = "；".join(str(item) for item in moment.get("look", [])) or "保持已声明视觉质感"
    visibility = json.dumps(view.get("visibility", {}), ensure_ascii=False, separators=(",", ":"))
    lines = [
        f"任务：{context['task_definition']}",
        f"参考图顺序与职责：{references}。各参考只影响其声明范围，原始 moment_anchor 始终拥有最高权威。",
        f"人物与接触硬锁：{context['identity_pose_contact_lock']} Frozen Moment Canon subjects={subjects}",
        f"场景、时间与光线硬锁：{context['scene_time_light_lock']} 场景={scene}；时间={temporal}；世界空间光线={lighting}",
        (
            f"目标摄影机：family={family['family_id']} kind={family['family_kind']}；"
            f"azimuth={view['azimuth_deg']:g}°；elevation={view['elevation_deg']:g}°；"
            f"radius_ratio={family['orbit_radius_ratio']:g}；roll={family['roll_deg']:g}°；"
            f"look_at={family['look_at_target']}；focus={family['focus_target']}；"
            f"focal_policy={family['focal_policy']}；shot_scale={family['shot_scale']}；"
            f"framing={family['framing_policy']}；crop={family['crop_policy']}。"
        ),
        f"遮挡与揭示：{visibility}。只接受由该机位自然造成的遮挡、显露、透视和视角相关材质变化。",
        f"未见区域：uncertainty_policy={uncertainty_policy}；任何未由来源直接支持的新显露区域必须标记 inferred 或 unknown，不得写成真实恢复。",
        f"光学与观感：{context['look_contract']} look={look}",
        f"禁止项：{context['negative_contract']}",
        "完成要求：画面必须像同一摄影师在同一场景、同一瞬间移动了摄影机；不得让主体为镜头配合而转身、转头、改视线、改接触或改动作。",
    ]
    return "\n".join(lines).strip() + "\n"


def compile_package(spec: dict[str, Any], output_root: Path) -> dict[str, Any]:
    if spec.get("schema_version") != INPUT_SCHEMA:
        raise ContractError("blocked_input_invalid", f"schema_version must be {INPUT_SCHEMA}")
    output_root = output_root.resolve()
    package_root = Path(__file__).resolve().parents[1]
    if output_root == package_root or package_root in output_root.parents:
        raise ContractError("blocked_output_location", "run output must remain outside the public Skill package")
    job = spec.get("job")
    if not isinstance(job, dict):
        raise ContractError("blocked_input_invalid", "job must be an object")
    job_id = ensure_nonempty_string(job.get("job_id"), "job.job_id")
    mode = job.get("mode")
    input_mode = job.get("input_mode")
    profile = job.get("coverage_profile")
    uncertainty = job.get("uncertainty_policy")
    if mode not in MODES or input_mode not in INPUT_MODES or profile not in PROFILES or uncertainty not in UNCERTAINTY_POLICIES:
        raise ContractError("blocked_input_invalid", "job mode/input_mode/coverage_profile/uncertainty_policy is invalid")
    max_attempts = job.get("max_attempts_per_view", 2)
    if not isinstance(max_attempts, int) or not 1 <= max_attempts <= 10:
        raise ContractError("blocked_input_invalid", "max_attempts_per_view must be 1..10")
    full_claim = bool(job.get("full_coverage_claim", profile in DEFAULT_BINS))
    generation_phase = job.get("generation_phase")
    if generation_phase is None:
        if mode == "generate_and_package" and input_mode == "text_anchor":
            generation_phase = "coverage" if spec.get("source_evidence", {}).get("accepted_anchor_image_sha256") else "moment_anchor"
        else:
            generation_phase = "all"
    if generation_phase not in {"all", "moment_anchor", "coverage"}:
        raise ContractError("blocked_input_invalid", "generation_phase must be all, moment_anchor, or coverage")
    if input_mode != "text_anchor" and generation_phase == "moment_anchor":
        raise ContractError("blocked_input_invalid", "moment_anchor generation phase is only for text input")
    if generation_phase == "coverage" and input_mode == "text_anchor":
        anchor_phase_binding = validate_anchor_acceptance(spec.get("source_evidence", {}), output_root)
        spec["source_evidence"].update(anchor_phase_binding)

    evidence_ledger = validate_evidence_ledger(spec.get("evidence_ledger"))
    moment = validate_moment_canon(spec.get("moment_canon"))
    accepted_anchor = bool(spec.get("source_evidence", {}).get("accepted_anchor_image_sha256"))
    if input_mode == "text_anchor" and not accepted_anchor:
        allowed_canon_statuses = {"synthetic_unrendered"}
    else:
        allowed_canon_statuses = {"source_anchored", "approved_canon"}
    if moment.get("canon_status") not in allowed_canon_statuses:
        raise ContractError("blocked_unsupported_claim", "moment_canon.canon_status exceeds available evidence")
    if input_mode == "text_anchor" and generation_phase == "moment_anchor":
        moment["canon_status"] = "synthetic_unrendered"

    raw_families = spec.get("camera_families")
    if not isinstance(raw_families, list) or not raw_families:
        raise ContractError("blocked_input_invalid", "camera_families must be a non-empty list")
    families: dict[str, dict[str, Any]] = {}
    for raw in raw_families:
        family = validate_family(raw)
        family_id = family["family_id"]
        if family_id in families:
            raise ContractError("E_FAMILY_MIX", f"duplicate family_id: {family_id}")
        families[family_id] = family
    source_basis = spec.get("source_evidence", {}).get("azimuth_basis")
    source_basis_evidence = spec.get("source_evidence", {}).get("azimuth_basis_evidence")
    for family in families.values():
        if family["azimuth_basis"] == "subject_forward" and (
            source_basis != "subject_forward" or source_basis_evidence not in {"observed", "source_corroborated", "approved_canon"}
        ):
            raise ContractError("E_COORDINATE_BASIS_UNKNOWN", "subject-forward view labels lack supported coordinate evidence")

    raw_views = spec.get("views", [])
    if generation_phase == "moment_anchor":
        first_family = next(iter(families))
        raw_views = [
            {
                "view_id": "V00",
                "family_id": first_family,
                "coverage_role": "text_moment_anchor",
                "required": True,
                "azimuth_deg": 0.0,
                "elevation_deg": families[first_family]["orbit_elevation_deg"],
                "visibility": {"face_visibility_goal": "as_text_defined"},
                "evidence_risk": "high",
            }
        ]
        validation_profile = "targeted_views"
        validation_claim = False
    else:
        validation_profile = profile
        validation_claim = full_claim
    views = validate_views(validation_profile, raw_views, families, validation_claim, moment)

    output_root.mkdir(parents=True, exist_ok=True)
    source_evidence, reference_plan_sha, reference_labels = load_reference_evidence(
        spec, output_root, job_id, generation_phase
    )
    validate_evidence_authority(
        evidence_ledger,
        input_mode=input_mode,
        source_evidence=source_evidence,
        canon_status=moment["canon_status"],
    )
    context = spec.get("prompt_context")
    if not isinstance(context, dict):
        raise ContractError("blocked_input_invalid", "prompt_context must be an object")
    if context != PROMPT_CONTEXT_CONTRACT:
        raise ContractError(
            "blocked_prompt_contract_override",
            "prompt_context must exactly match the compiler-owned immutable camera-only contract",
        )
    context = PROMPT_CONTEXT_CONTRACT

    prompts: list[dict[str, Any]] = []
    prompt_document: list[str] = [f"# Frozen Moment Camera Coverage Prompts — {job_id}", ""]
    prompt_root = output_root / "00_manifest" / "prompts"
    for view in views:
        family = families[view["family_id"]]
        prompt_text = compile_prompt(context, moment, family, view, reference_labels, uncertainty)
        prompt_path = prompt_root / f"{view['view_id']}.zh.txt"
        write_text_atomic(prompt_path, prompt_text)
        prompt_sha = sha256_file(prompt_path)
        prompts.append(
            {
                "view_id": view["view_id"],
                "language": "zh",
                "prompt_path": prompt_path.relative_to(output_root).as_posix(),
                "prompt_sha256": prompt_sha,
                "reference_plan_sha256": reference_plan_sha,
                "published": True,
            }
        )
        prompt_document.extend(
            [
                f"## {view['view_id']} — {view['coverage_role']}",
                "",
                f"- Prompt SHA-256: `{prompt_sha}`",
                f"- Reference plan SHA-256: `{reference_plan_sha}`",
                f"- Camera contract SHA-256: `{view['camera_contract_sha256']}`",
                "",
                prompt_text.rstrip(),
                "",
            ]
        )

    manifest_job = {
        "job_id": job_id,
        "mode": mode,
        "input_mode": input_mode,
        "coverage_profile": profile,
        "uncertainty_policy": uncertainty,
        "max_attempts_per_view": max_attempts,
        "full_coverage_claim": full_claim and generation_phase != "moment_anchor",
        "generation_phase": generation_phase,
    }
    moment["moment_canon_sha256"] = sha256_bytes(canonical_json({k: v for k, v in moment.items() if k != "moment_canon_sha256"}))
    required_ids = [view["view_id"] for view in views if view["required"]]
    prompt_set_sha = sha256_bytes(canonical_json([{key: item[key] for key in ("view_id", "prompt_sha256", "reference_plan_sha256")} for item in prompts]))
    terminal = "prompt_package_ready" if mode == "prompt_only" else None
    state_current = terminal or "prompts_locked"
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "job": manifest_job,
        "source_evidence": source_evidence,
        "evidence_ledger": evidence_ledger,
        "moment_canon": moment,
        "camera_families": list(families.values()),
        "views": views,
        "prompts": prompts,
        "attempts": [],
        "qa": {
            "required_view_ids": required_ids,
            "approved_required_view_ids": [],
            "all_required_views_approved": False,
            "main_inspection_required": mode == "generate_and_package",
            "runtime_evidence_origin": "none",
        },
        "state": {"current": state_current, "terminal_state": terminal},
        "prompt_set_sha256": prompt_set_sha,
        "coverage_contract_sha256": "",
        "compiled_at_utc": utc_now(),
    }
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
    manifest["coverage_contract_sha256"] = sha256_bytes(canonical_json(coverage_contract))

    write_json_atomic(output_root / "00_manifest" / "SOURCE_EVIDENCE.json", {"source_evidence": source_evidence, "evidence_ledger": evidence_ledger})
    write_json_atomic(output_root / "00_manifest" / "FROZEN_MOMENT.json", moment)
    write_json_atomic(
        output_root / "00_manifest" / "CAMERA_COVERAGE.json",
        {
            "coverage_profile": profile,
            "generation_phase": generation_phase,
            "camera_families": list(families.values()),
            "views": views,
            "required_view_ids": required_ids,
        },
    )
    prompt_document_text = "\n".join(prompt_document).rstrip() + "\n"
    write_text_atomic(output_root / "00_manifest" / "GENERATION_PROMPTS.md", prompt_document_text)
    write_text_atomic(output_root / "40_handoff" / "MASTER_REGENERATION_PROMPTS.md", prompt_document_text)
    write_json_atomic(output_root / "00_manifest" / "COVERAGE_MANIFEST.json", manifest)
    receipt = {
        "schema_version": "frozen_moment_prompt_publication_receipt.v1",
        "phase": "moment_anchor" if generation_phase == "moment_anchor" else "coverage",
        "input_mode": input_mode,
        "publication_status": "prompt_artifacts_frozen",
        "published_at_utc": utc_now(),
        "published_at_unix_ms": int(time.time() * 1000),
        "required_view_ids": required_ids,
        "required_view_set_sha256": sha256_bytes(canonical_json(required_ids)),
        "prompt_document_path": "00_manifest/GENERATION_PROMPTS.md",
        "prompt_document_sha256": sha256_file(output_root / "00_manifest" / "GENERATION_PROMPTS.md"),
        "published_prompt_ids": required_ids,
        "published_prompt_sha256": [item["prompt_sha256"] for item in prompts if item["view_id"] in required_ids],
        "published_reference_plan_sha256": [item["reference_plan_sha256"] for item in prompts if item["view_id"] in required_ids],
        "first_worker_spawn_event_index": None,
        "first_worker_spawn_elapsed_ms": None,
        "accepted_anchor_image_sha256": source_evidence.get("accepted_anchor_image_sha256"),
        "anchor_inspection_sha256": source_evidence.get("anchor_inspection_sha256"),
    }
    write_json_atomic(output_root / "00_manifest" / "PROMPT_PUBLICATION.json", receipt)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_spec", type=Path)
    parser.add_argument("output_root", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        manifest = compile_package(read_json(args.input_spec), args.output_root)
    except ContractError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}, ensure_ascii=False), file=sys.stderr)
        return 2
    except OSError as exc:
        print(json.dumps({"ok": False, "error_code": "blocked_filesystem", "detail": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "ok": True,
                "manifest": str((args.output_root.resolve() / "00_manifest" / "COVERAGE_MANIFEST.json")),
                "state": manifest["state"],
                "required_views": manifest["qa"]["required_view_ids"],
                "prompt_set_sha256": manifest["prompt_set_sha256"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
