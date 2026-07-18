#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "complex_product_identity_asset_package.v2"
LEGACY_SCHEMA_VERSION = "complex_product_identity_asset_package.v1"
SPECIFICATION_FILE = "01_Product_Identity_Specification.md"
PROMPT_FILE = "08_4K_Upscale_Prompts.md"
MANIFEST_FILE = "asset_package_manifest.json"
GEOMETRY_DIRECTORY = "02_Geometry_Camera_Coverage"
CAMERA_ASSET_DIRECTORY = f"{GEOMETRY_DIRECTORY}/camera_assets"
CAMERA_REPORT_FILE = f"{GEOMETRY_DIRECTORY}/camera_coverage_report.md"
UPLOAD_DIRECTORY = "07_Primary_Upload_Bundle"

DIAGNOSTIC_DIRECTORIES = {
    "material_surface_lock": "03_Material_Surface_Lock",
    "component_detail_lock": "04_Component_Detail_Lock",
    "state_transition_lock": "05_State_Transition_Lock",
    "marking_identity_lock": "06_Marking_Identity_Lock",
}

PACKAGE_STATUSES = {
    "initialized",
    "analysis_complete",
    "generation_in_progress",
    "partial_approved",
    "complete",
    "blocked_source_insufficient",
    "blocked_identity_conflict",
    "blocked_generation_runtime",
    "blocked_generation_semantic_mismatch",
    "four_k_mapping_failed",
}
ASSET_STATUSES = {
    "planned",
    "generation_pending",
    "awaiting_post_generation_continuation",
    "qa_pending",
    "repair_required",
    "approved",
    "blocked",
    "blocked_generation_quality",
    "blocked_generation_semantic_mismatch",
    "not_applicable",
}
GEOMETRY_STATUSES = {"planned", "partial_approved", "approved", "blocked", "generation_in_progress"}
RELEVANCE = {"required", "conditional", "not_applicable"}
SOURCE_GATES = {"approved", "blocked", "not_applicable"}
EVIDENCE_MODES = {
    "unassigned",
    "source_copy",
    "verified_source_render",
    "source_aligned_generation",
    "bounded_reconstruction",
    "blocked",
}
IDENTITY_AUTHORITIES = {"hard", "auxiliary", "none"}
QA_VALUES = {"pass", "fail", "not_applicable"}
TERMINAL_VALUES = {"not_started", "not_applicable", "pending", "executed", "failed"}
PRODUCTION_APPROVAL = {"not_granted", "user_granted", "external_pipeline_granted"}
CONTACT_SHEET_STATUSES = {"not_created", "approved"}
UPLOAD_STATUSES = {"planned", "approved", "blocked"}
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8"

REQUIRED_SPEC_HEADINGS = (
    "## Product Part Tree",
    "## Critical Node Ledger",
    "## State Graph",
    "### Observed",
    "### Cross Validated",
    "### Inferred",
    "### Unknown",
    "### Conflicting",
    "## View Evidence Matrix",
    "## Camera Coverage Plan",
    "## Coverage Gap Requests",
    "## Diagnostic Board Source Decisions",
)
CAMERA_QA_KEYS = (
    "subject_match",
    "complete_product",
    "pose_match",
    "critical_node_consistency",
    "cross_camera_consistency",
    "text_pollution",
)
BOARD_QA_KEYS = (
    "geometry_consistency",
    "material_consistency",
    "identity_consistency",
    "subject_match",
    "text_pollution",
)
REQUIRED_PRESERVES = {
    "geometry",
    "part_count",
    "proportions",
    "markings",
    "materials",
    "camera_pose",
    "critical_nodes",
}
ALLOWED_4K_CHANGES = {
    "resolution",
    "edge_definition",
    "realistic_microtexture",
    "source_supported_fine_detail",
}
REQUIRED_PROMPT_PHRASES = (
    "preserve original product geometry",
    "preserve part count",
    "preserve proportions",
    "preserve the accepted camera pose",
    "preserve all critical nodes",
    "preserve any source-supported logo and markings exactly",
    "preserve materials and colors",
    "enhance only clarity and realistic micro-texture",
    "do not redesign the product",
)


class ValidationFailure(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationFailure(f"invalid UTF-8 JSON in {path}: {exc}") from exc
    require(isinstance(data, dict), f"JSON root must be an object: {path}")
    return data


def require_hash(value: Any, field: str, *, allow_none: bool = False) -> None:
    if value is None and allow_none:
        return
    require(isinstance(value, str) and HASH_RE.fullmatch(value) is not None, f"{field} must be SHA-256 lowercase hex")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def camera_plan_sha256(geometry: dict[str, Any]) -> str:
    cameras = geometry.get("camera_assets", [])
    payload = {
        "minimum_video_ready_camera_count": geometry.get("minimum_video_ready_camera_count"),
        "target_camera_ids": geometry.get("target_camera_ids"),
        "cameras": [
            {
                "camera_id": item.get("camera_id"),
                "role": item.get("role"),
                "pose_bin": item.get("pose_bin"),
                "coverage_sectors": item.get("coverage_sectors"),
            }
            for item in cameras
            if isinstance(item, dict)
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def png_dimensions(data: bytes, field: str) -> tuple[int, int]:
    require(len(data) >= 24 and data[:8] == PNG_SIGNATURE, f"{field} is not a valid PNG")
    width, height = struct.unpack(">II", data[16:24])
    require(width > 0 and height > 0, f"{field} has invalid PNG dimensions")
    return width, height


def jpeg_dimensions(data: bytes, field: str) -> tuple[int, int]:
    require(data[:2] == JPEG_SIGNATURE, f"{field} is not a valid JPEG")
    index = 2
    sof_markers = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while index + 4 <= len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        while index < len(data) and data[index] == 0xFF:
            index += 1
        require(index < len(data), f"{field} has truncated JPEG markers")
        marker = data[index]
        index += 1
        if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        require(index + 2 <= len(data), f"{field} has truncated JPEG segment")
        length = int.from_bytes(data[index:index + 2], "big")
        require(length >= 2 and index + length <= len(data), f"{field} has invalid JPEG segment length")
        if marker in sof_markers:
            require(length >= 7, f"{field} has invalid JPEG SOF segment")
            height = int.from_bytes(data[index + 3:index + 5], "big")
            width = int.from_bytes(data[index + 5:index + 7], "big")
            require(width > 0 and height > 0, f"{field} has invalid JPEG dimensions")
            return width, height
        index += length
    raise ValidationFailure(f"{field} JPEG dimensions not found")


def image_dimensions(path: Path, field: str) -> tuple[int, int]:
    data = path.read_bytes()
    suffix = path.suffix.casefold()
    if suffix == ".png":
        return png_dimensions(data, field)
    if suffix in {".jpg", ".jpeg"}:
        return jpeg_dimensions(data, field)
    raise ValidationFailure(f"{field} must be PNG or JPEG")


def require_asset(root: Path, value: Any, field: str, *, png_only: bool = False) -> tuple[Path, tuple[int, int]]:
    require(isinstance(value, str) and value.strip(), f"{field} must name an asset file")
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts, f"{field} must be package-relative")
    path = root / relative
    require(path.is_file() and path.stat().st_size > 8, f"{field} is missing or empty: {value}")
    if png_only:
        require(path.suffix.casefold() == ".png", f"{field} must be a PNG: {value}")
    return path, image_dimensions(path, field)


def require_dimensions_match(value: Any, actual: tuple[int, int], field: str) -> None:
    require(isinstance(value, dict), f"{field} must contain width and height")
    require(value.get("width") == actual[0], f"{field}.width does not match observed pixels")
    require(value.get("height") == actual[1], f"{field}.height does not match observed pixels")


def validate_qa(qa: Any, keys: tuple[str, ...], field: str, approved: bool) -> None:
    require(isinstance(qa, dict), f"{field} must be an object")
    for key in keys:
        require(qa.get(key) in QA_VALUES, f"{field}.{key} has invalid value: {qa.get(key)}")
        if approved:
            require(qa.get(key) == "pass", f"{field}.{key} must pass for an approved asset")
    flags = qa.get("failure_flags")
    require(isinstance(flags, list) and all(isinstance(item, str) and item for item in flags), f"{field}.failure_flags must be a non-empty-string list")
    if approved:
        require(not flags, f"{field} cannot be approved with failure flags")


def validate_camera(root: Path, record: Any, index: int) -> tuple[str | None, str | None, tuple[str, str, str] | None, set[str], str | None]:
    field = f"geometry_coverage.camera_assets[{index}]"
    require(isinstance(record, dict), f"{field} must be an object")
    camera_id = record.get("camera_id")
    require(isinstance(camera_id, str) and camera_id, f"{field}.camera_id is required")
    require(isinstance(record.get("role"), str) and record["role"], f"{field}.role is required")
    pose = record.get("pose_bin")
    require(isinstance(pose, dict), f"{field}.pose_bin must be an object")
    for key in ("azimuth", "elevation", "shot_size"):
        require(isinstance(pose.get(key), str) and pose[key], f"{field}.pose_bin.{key} is required")
    pose_key = (pose["azimuth"], pose["elevation"], pose["shot_size"])
    sectors = record.get("coverage_sectors")
    require(isinstance(sectors, list) and sectors and all(isinstance(item, str) and item for item in sectors), f"{field}.coverage_sectors must be a non-empty string list")
    nodes = record.get("critical_node_ids")
    require(isinstance(nodes, list) and all(isinstance(item, str) and item for item in nodes), f"{field}.critical_node_ids must be a string list")
    source_gate = record.get("source_gate")
    require(source_gate in SOURCE_GATES, f"{field}.source_gate has invalid value: {source_gate}")
    reasons = record.get("source_gate_reasons")
    require(isinstance(reasons, list) and all(isinstance(item, str) for item in reasons), f"{field}.source_gate_reasons must be a string list")
    source_ids = record.get("source_ids")
    require(isinstance(source_ids, list) and all(isinstance(item, str) and item for item in source_ids), f"{field}.source_ids must be a string list")
    evidence_mode = record.get("evidence_mode")
    authority = record.get("identity_authority")
    status = record.get("status")
    require(evidence_mode in EVIDENCE_MODES, f"{field}.evidence_mode has invalid value: {evidence_mode}")
    require(authority in IDENTITY_AUTHORITIES, f"{field}.identity_authority has invalid value: {authority}")
    require(status in ASSET_STATUSES, f"{field}.status has invalid value: {status}")
    attempts = record.get("attempt_count")
    require(isinstance(attempts, int) and 0 <= attempts <= 2, f"{field}.attempt_count must be 0..2")
    terminal = record.get("terminal_generation_call")
    require(terminal in TERMINAL_VALUES, f"{field}.terminal_generation_call has invalid value: {terminal}")
    approved = status == "approved"
    validate_qa(record.get("qa"), CAMERA_QA_KEYS, f"{field}.qa", approved)

    if source_gate == "blocked":
        require(status not in {"generation_pending", "awaiting_post_generation_continuation", "qa_pending", "repair_required", "approved"}, f"{field} cannot generate or approve while source_gate is blocked")
    if approved:
        require(source_gate == "approved", f"{field} approved camera requires source_gate: approved")
        require(source_ids, f"{field} approved camera requires source_ids")
        require(nodes, f"{field} approved camera requires critical_node_ids")
        require(evidence_mode not in {"unassigned", "blocked"}, f"{field} approved camera requires a usable evidence_mode")

    if evidence_mode == "source_copy":
        require(authority == "hard", f"{field} source_copy must use hard identity authority")
        require(record.get("generation_prompt_sha256") is None, f"{field} source_copy cannot have a generation prompt")
        require(terminal in {"not_started", "not_applicable"}, f"{field} source_copy cannot claim an image-generation call")
    elif evidence_mode == "verified_source_render":
        require(authority == "hard", f"{field} verified_source_render must use hard identity authority")
        require_hash(record.get("provenance_sha256"), f"{field}.provenance_sha256")
        require(record.get("generation_prompt_sha256") is None, f"{field} verified_source_render cannot have an image-generation prompt")
        require(terminal in {"not_started", "not_applicable", "executed"}, f"{field} verified_source_render has invalid terminal state")
    elif evidence_mode in {"source_aligned_generation", "bounded_reconstruction"}:
        require(authority == "auxiliary", f"{field} generative camera must remain auxiliary identity authority")
        if status in {"generation_pending", "awaiting_post_generation_continuation", "qa_pending", "repair_required", "approved", "blocked_generation_quality", "blocked_generation_semantic_mismatch"}:
            require_hash(record.get("generation_prompt_sha256"), f"{field}.generation_prompt_sha256")
        if approved:
            require(terminal == "executed", f"{field} approved generative camera requires executed terminal call")
    elif evidence_mode in {"unassigned", "blocked"}:
        require(authority == "none", f"{field} unassigned/blocked evidence cannot have identity authority")
        require(not approved, f"{field} unassigned/blocked evidence cannot be approved")

    asset_file = record.get("asset_file")
    asset_hash: str | None = None
    generated_states = {
        "awaiting_post_generation_continuation",
        "qa_pending",
        "repair_required",
        "approved",
        "blocked_generation_quality",
        "blocked_generation_semantic_mismatch",
    }
    if status in generated_states:
        require(isinstance(asset_file, str) and asset_file.startswith(f"{CAMERA_ASSET_DIRECTORY}/"), f"{field}.asset_file must live under camera_assets")
        path, actual = require_asset(root, asset_file, f"{field}.asset_file")
        require_dimensions_match(record.get("actual_dimensions"), actual, f"{field}.actual_dimensions")
        require_hash(record.get("asset_sha256"), f"{field}.asset_sha256")
        asset_hash = file_sha256(path)
        require(record.get("asset_sha256") == asset_hash, f"{field}.asset_sha256 does not match observed bytes")
        require_hash(record.get("source_asset_sha256"), f"{field}.source_asset_sha256")
        if evidence_mode == "source_copy":
            require(record.get("source_asset_sha256") == asset_hash, f"{field} source_copy bytes must equal the frozen source asset")
    else:
        require(asset_file is None, f"{field}.asset_file must be null before an image exists")
        require(record.get("asset_sha256") is None, f"{field}.asset_sha256 must be null before an image exists")
        require(record.get("actual_dimensions") is None, f"{field}.actual_dimensions must be null before an image exists")

    return (asset_file if approved else None, asset_hash if approved else None, pose_key if approved else None, set(sectors) if approved else set(), pose["elevation"] if approved else None)


def validate_geometry(root: Path, geometry: Any, frozen: bool) -> tuple[set[str], set[str], set[str], list[str]]:
    field = "geometry_coverage"
    require(isinstance(geometry, dict), f"{field} must be an object")
    require(geometry.get("coverage_id") == "geometry_camera_coverage", f"{field}.coverage_id mismatch")
    require(geometry.get("directory") == GEOMETRY_DIRECTORY, f"{field}.directory mismatch")
    status = geometry.get("status")
    require(status in GEOMETRY_STATUSES, f"{field}.status has invalid value: {status}")
    require_hash(geometry.get("camera_plan_sha256"), f"{field}.camera_plan_sha256")
    minimum = geometry.get("minimum_video_ready_camera_count")
    require(isinstance(minimum, int) and 4 <= minimum <= 6, f"{field}.minimum_video_ready_camera_count must be 4..6")
    targets = geometry.get("target_camera_ids")
    require(isinstance(targets, list) and len(targets) >= minimum and len(targets) == len(set(targets)), f"{field}.target_camera_ids must be unique and meet the minimum")
    cameras = geometry.get("camera_assets")
    require(isinstance(cameras, list) and len(cameras) == len(targets), f"{field}.camera_assets must match target_camera_ids")
    require({item.get("camera_id") for item in cameras if isinstance(item, dict)} == set(targets), f"{field}.camera_assets and target_camera_ids mismatch")
    require(geometry.get("camera_plan_sha256") == camera_plan_sha256(geometry), f"{field}.camera_plan_sha256 does not bind the frozen camera plan")

    approved_files: set[str] = set()
    approved_camera_ids: set[str] = set()
    hard_files: set[str] = set()
    hashes: list[str] = []
    poses: list[tuple[str, str, str]] = []
    sectors: set[str] = set()
    elevations: set[str] = set()
    active: list[str] = []
    for index, camera in enumerate(cameras):
        asset, asset_hash, pose, camera_sectors, elevation = validate_camera(root, camera, index)
        if camera.get("status") == "approved":
            require(asset is not None and asset_hash is not None and pose is not None and elevation is not None, "approved camera validation did not return bindings")
            approved_files.add(asset)
            approved_camera_ids.add(camera["camera_id"])
            hashes.append(asset_hash)
            poses.append(pose)
            sectors |= camera_sectors
            elevations.add(elevation)
            if camera.get("identity_authority") == "hard":
                hard_files.add(asset)
        if camera.get("status") in {"generation_pending", "awaiting_post_generation_continuation", "qa_pending", "repair_required"}:
            active.append(camera["camera_id"])

    duplicate_hash_count = len(hashes) - len(set(hashes))
    duplicate_pose_count = len(poses) - len(set(poses))
    redundancy = duplicate_hash_count + duplicate_pose_count
    video_ready = (
        len(hard_files) >= minimum
        and len(set(poses)) >= minimum
        and {"front", "rear"} <= sectors
        and bool({"left", "right", "side"} & sectors)
        and redundancy == 0
    )
    full = video_ready and approved_camera_ids == set(targets) and len(hard_files) == len(targets)
    derived_tier = "full" if full else "multi_camera" if video_ready else "source_aligned" if approved_files else "none"

    metrics = geometry.get("coverage_metrics")
    require(isinstance(metrics, dict), f"{field}.coverage_metrics must be an object")
    require(metrics.get("approved_camera_count") == len(approved_files), f"{field}.coverage_metrics.approved_camera_count mismatch")
    require(metrics.get("hard_authority_camera_count") == len(hard_files), f"{field}.coverage_metrics.hard_authority_camera_count mismatch")
    require(metrics.get("unique_pose_bin_count") == len(set(poses)), f"{field}.coverage_metrics.unique_pose_bin_count mismatch")
    require(set(metrics.get("covered_sectors", [])) == sectors, f"{field}.coverage_metrics.covered_sectors mismatch")
    require(set(metrics.get("elevation_bands", [])) == elevations, f"{field}.coverage_metrics.elevation_bands mismatch")
    require(metrics.get("redundancy_count") == redundancy, f"{field}.coverage_metrics.redundancy_count mismatch")
    require(metrics.get("coverage_tier") == derived_tier, f"{field}.coverage_metrics.coverage_tier mismatch; expected {derived_tier}")
    require(redundancy == 0, f"{field} contains duplicate camera bytes or pose bins")

    if status == "approved":
        require(video_ready, f"{field} approved status requires hard-authority multi-camera coverage")
        require(not active, f"{field} approved status cannot retain active camera states")
    if status == "partial_approved":
        require(bool(approved_files) and not video_ready, f"{field} partial_approved requires accepted but non-video-ready coverage")
    if status == "blocked":
        require(not approved_files, f"{field} blocked status cannot contain approved cameras")

    contact = geometry.get("contact_sheet")
    require(isinstance(contact, dict), f"{field}.contact_sheet must be an object")
    contact_status = contact.get("status")
    require(contact_status in CONTACT_SHEET_STATUSES, f"{field}.contact_sheet.status has invalid value")
    derived_ids = contact.get("derived_from_camera_ids")
    require(isinstance(derived_ids, list) and len(derived_ids) == len(set(derived_ids)), f"{field}.contact_sheet.derived_from_camera_ids must be unique")
    if contact_status == "approved":
        require(len(derived_ids) >= 2 and set(derived_ids) <= approved_camera_ids, f"{field}.contact_sheet must derive only from at least two approved cameras")
        require(contact.get("identity_authority") == "none", f"{field}.contact_sheet can never be identity authority")
        path, _ = require_asset(root, contact.get("asset_file"), f"{field}.contact_sheet.asset_file", png_only=True)
        require_hash(contact.get("asset_sha256"), f"{field}.contact_sheet.asset_sha256")
        require(contact.get("asset_sha256") == file_sha256(path), f"{field}.contact_sheet.asset_sha256 mismatch")
    else:
        require(contact.get("asset_file") is None and contact.get("asset_sha256") is None and not derived_ids, f"{field}.contact_sheet not_created must remain empty")
        require(contact.get("identity_authority") == "none", f"{field}.contact_sheet must have no identity authority")

    return approved_files, hard_files, approved_camera_ids, active


def validate_native_4k(record: dict[str, Any], field: str) -> None:
    require(record.get("native_4k_claimed") is False, f"{field}.native_4k_claimed must remain false for Codex package assets")
    require(record.get("native_4k_evidence") is None, f"{field}.native_4k_evidence must remain null for Codex package assets")


def validate_board(root: Path, record: Any, expected_id: str, expected_directory: str) -> tuple[str | None, bool]:
    field = f"diagnostic_boards[{expected_id}]"
    require(isinstance(record, dict), f"{field} must be an object")
    require(record.get("board_id") == expected_id, f"{field}.board_id mismatch")
    require(record.get("directory") == expected_directory, f"{field}.directory mismatch")
    relevance = record.get("relevance")
    source_gate = record.get("source_gate")
    status = record.get("status")
    require(relevance in RELEVANCE, f"{field}.relevance has invalid value: {relevance}")
    require(source_gate in SOURCE_GATES, f"{field}.source_gate has invalid value: {source_gate}")
    require(status in ASSET_STATUSES, f"{field}.status has invalid value: {status}")
    require(isinstance(record.get("source_gate_reasons"), list), f"{field}.source_gate_reasons must be a list")
    require(isinstance(record.get("evidence_ids"), list), f"{field}.evidence_ids must be a list")
    attempts = record.get("attempt_count")
    require(isinstance(attempts, int) and 0 <= attempts <= 3, f"{field}.attempt_count must be 0..3")
    require(record.get("terminal_generation_call") in TERMINAL_VALUES, f"{field}.terminal_generation_call has invalid value")
    approved = status == "approved"
    validate_native_4k(record, field)
    validate_qa(record.get("qa"), BOARD_QA_KEYS, f"{field}.qa", approved)
    if approved:
        require(source_gate == "approved", f"{field} approved board requires source_gate: approved")
        require(relevance != "not_applicable", f"{field} approved board cannot be not_applicable")
    if source_gate == "blocked":
        require(status not in {"generation_pending", "awaiting_post_generation_continuation", "qa_pending", "repair_required", "approved"}, f"{field} cannot generate or approve while source_gate is blocked")
    if relevance == "not_applicable":
        require(source_gate == "not_applicable" and status in {"planned", "not_applicable"}, f"{field} not_applicable relevance must remain non-generated")

    asset_file = record.get("asset_file")
    generated_states = {
        "awaiting_post_generation_continuation",
        "qa_pending",
        "repair_required",
        "approved",
        "blocked_generation_quality",
        "blocked_generation_semantic_mismatch",
    }
    if status in generated_states:
        require(record.get("terminal_generation_call") in {"executed", "failed"}, f"{field} generated state requires an executed or failed terminal call")
        path, actual = require_asset(root, asset_file, f"{field}.asset_file", png_only=True)
        require_dimensions_match(record.get("actual_dimensions"), actual, f"{field}.actual_dimensions")
        require_hash(record.get("asset_sha256"), f"{field}.asset_sha256")
        require(record.get("asset_sha256") == file_sha256(path), f"{field}.asset_sha256 does not match observed bytes")
        require_hash(record.get("generation_prompt_sha256"), f"{field}.generation_prompt_sha256")
    else:
        require(asset_file is None, f"{field}.asset_file must be null before an image exists")
    return (asset_file if approved else None, status in {"generation_pending", "awaiting_post_generation_continuation", "qa_pending", "repair_required"})


def prompt_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^## Asset: (.+?)\s*$", text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        asset = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        require(asset not in sections, f"duplicate 4K prompt section for {asset}")
        sections[asset] = text[start:end].strip()
    return sections


def validate_prompt_mappings(
    manifest: dict[str, Any],
    prompt_text: str,
    approved_assets: set[str],
    *,
    allow_incomplete: bool = False,
) -> None:
    mappings = manifest.get("four_k_prompts")
    require(isinstance(mappings, list), "four_k_prompts must be a list")
    sections = prompt_sections(prompt_text)
    mapped_assets: list[str] = []
    for index, mapping in enumerate(mappings):
        field = f"four_k_prompts[{index}]"
        require(isinstance(mapping, dict), f"{field} must be an object")
        asset = mapping.get("asset_file")
        require(isinstance(asset, str) and asset, f"{field}.asset_file is required")
        mapped_assets.append(asset)
        require(mapping.get("section_anchor") == f"Asset: {asset}", f"{field}.section_anchor mismatch")
        require(set(mapping.get("preserves", [])) == REQUIRED_PRESERVES, f"{field}.preserves must match the required identity set")
        allowed = set(mapping.get("allowed_changes", []))
        require(allowed and allowed <= ALLOWED_4K_CHANGES, f"{field}.allowed_changes contains an unsupported change")
        require(mapping.get("redesign_forbidden") is True, f"{field}.redesign_forbidden must be true")
        require(asset in sections, f"missing 4K prompt section for {asset}")
        section = sections[asset].casefold()
        for phrase in REQUIRED_PROMPT_PHRASES:
            require(phrase in section, f"4K prompt for {asset} is missing phrase: {phrase}")
    require(len(mapped_assets) == len(set(mapped_assets)), "four_k_prompts contains duplicate asset mappings")
    mapped_set = set(mapped_assets)
    require(mapped_set <= approved_assets, "4K prompt mappings reference a non-approved asset")
    require(set(sections) == mapped_set, "08_4K_Upscale_Prompts.md sections and mappings are not one-to-one")
    if allow_incomplete:
        require(mapped_set != approved_assets, "four_k_mapping_failed must retain an actual mapping gap")
    else:
        require(mapped_set == approved_assets, "approved assets and 4K prompt mappings are not one-to-one")
    require(manifest.get("approved_asset_count") == len(approved_assets), "approved_asset_count mismatch")
    require(manifest.get("four_k_mapping_count") == len(mappings), "four_k_mapping_count mismatch")


def validate_upload_bundle(
    bundle: Any,
    accepted_assets: set[str],
    approved_camera_files: set[str],
    hard_camera_files: set[str],
) -> tuple[str, set[str], set[str]]:
    field = "primary_upload_bundle"
    require(isinstance(bundle, dict), f"{field} must be an object")
    require(bundle.get("directory") == UPLOAD_DIRECTORY, f"{field}.directory mismatch")
    status = bundle.get("status")
    require(status in UPLOAD_STATUSES, f"{field}.status has invalid value: {status}")
    require(bundle.get("max_asset_count") == 5, f"{field}.max_asset_count must be 5")
    selections = bundle.get("selections")
    require(isinstance(selections, list) and len(selections) <= 5, f"{field}.selections must contain at most five entries")
    files: list[str] = []
    camera_files: set[str] = set()
    hard_files: set[str] = set()
    for index, selection in enumerate(selections):
        require(isinstance(selection, dict), f"{field}.selections[{index}] must be an object")
        asset = selection.get("asset_file")
        require(isinstance(asset, str) and asset in accepted_assets, f"{field}.selections[{index}] references a non-approved asset")
        require(isinstance(selection.get("role"), str) and selection["role"], f"{field}.selections[{index}].role is required")
        files.append(asset)
        if asset in approved_camera_files:
            camera_files.add(asset)
        if asset in hard_camera_files:
            hard_files.add(asset)
    require(len(files) == len(set(files)), f"{field}.selections contains duplicate assets")
    if status == "approved":
        require(bool(files), f"{field} approved status requires at least one selection")
        require(bool(camera_files), f"{field} approved status requires a camera asset")
        require(isinstance(bundle.get("selection_reason"), str) and bundle["selection_reason"].strip(), f"{field}.selection_reason is required")
    else:
        require(not files, f"{field} planned/blocked status cannot contain selections")
    return status, camera_files, hard_files


def validate_package(root: Path) -> None:
    root = root.resolve()
    require(root.is_dir(), f"package directory does not exist: {root}")
    for directory in (GEOMETRY_DIRECTORY, CAMERA_ASSET_DIRECTORY, *DIAGNOSTIC_DIRECTORIES.values(), UPLOAD_DIRECTORY):
        require((root / directory).is_dir(), f"missing required directory: {directory}")

    specification_path = root / SPECIFICATION_FILE
    require(specification_path.is_file(), f"missing {SPECIFICATION_FILE}")
    specification = specification_path.read_text(encoding="utf-8")
    for heading in REQUIRED_SPEC_HEADINGS:
        require(heading in specification, f"specification missing heading: {heading}")
    report_path = root / CAMERA_REPORT_FILE
    require(report_path.is_file(), f"missing {CAMERA_REPORT_FILE}")

    manifest = load_json(root / MANIFEST_FILE)
    schema = manifest.get("schema_version")
    if schema == LEGACY_SCHEMA_VERSION:
        raise ValidationFailure("v1 monolithic Geometry board cannot prove independent camera coverage; rerun Stage 1 and migrate to v2")
    require(schema == SCHEMA_VERSION, "schema_version mismatch")
    require(manifest.get("identity_specification") == SPECIFICATION_FILE, "identity_specification path mismatch")
    require(manifest.get("camera_coverage_report") == CAMERA_REPORT_FILE, "camera_coverage_report path mismatch")
    package_status = manifest.get("package_status")
    require(package_status in PACKAGE_STATUSES, f"invalid package_status: {package_status}")
    require(manifest.get("production_approval_status") in PRODUCTION_APPROVAL, "invalid production_approval_status")
    require(isinstance(manifest.get("unresolved_hard_conflicts"), list), "unresolved_hard_conflicts must be a list")
    frozen = package_status != "initialized"
    require_hash(manifest.get("identity_specification_sha256"), "identity_specification_sha256", allow_none=not frozen)
    require_hash(manifest.get("source_bundle_sha256"), "source_bundle_sha256", allow_none=not frozen)
    if frozen:
        require(manifest.get("identity_specification_sha256") == file_sha256(specification_path), "identity_specification_sha256 does not match frozen specification bytes")
        require("analysis_pending" not in report_path.read_text(encoding="utf-8"), "camera coverage report remains analysis_pending")

    approved_camera_files, hard_camera_files, _, camera_active = validate_geometry(root, manifest.get("geometry_coverage"), frozen)
    approved_assets = set(approved_camera_files)
    active_states = list(camera_active)

    boards = manifest.get("diagnostic_boards")
    require(isinstance(boards, list) and len(boards) == len(DIAGNOSTIC_DIRECTORIES), "diagnostic_boards must contain exactly four records")
    by_id = {record.get("board_id"): record for record in boards if isinstance(record, dict)}
    require(set(by_id) == set(DIAGNOSTIC_DIRECTORIES), "diagnostic_boards must contain the four canonical IDs exactly once")
    for board_id, directory in DIAGNOSTIC_DIRECTORIES.items():
        asset, active = validate_board(root, by_id[board_id], board_id, directory)
        if asset:
            approved_assets.add(asset)
        if active:
            active_states.append(board_id)

    upload_status, selected_camera_files, selected_hard_camera_files = validate_upload_bundle(
        manifest.get("primary_upload_bundle"), approved_assets, approved_camera_files, hard_camera_files
    )

    require(manifest.get("four_k_prompt_file") == PROMPT_FILE, "four_k_prompt_file path mismatch")
    prompt_path = root / PROMPT_FILE
    require(prompt_path.is_file(), f"missing {PROMPT_FILE}")
    validate_prompt_mappings(
        manifest,
        prompt_path.read_text(encoding="utf-8"),
        approved_assets,
        allow_incomplete=package_status == "four_k_mapping_failed",
    )

    geometry_status = manifest["geometry_coverage"]["status"]
    if package_status == "complete":
        require(not active_states, f"complete package has unfinished generation states: {', '.join(active_states)}")
        require(geometry_status == "approved", "complete package requires approved hard-authority multi-camera coverage")
        for record in boards:
            if record["relevance"] == "required":
                require(record["status"] == "approved", f"complete package requires approved required diagnostic board: {record['board_id']}")
        require(not manifest["unresolved_hard_conflicts"], "complete package cannot retain hard identity conflicts")
        require(upload_status == "approved", "complete package requires an approved primary upload bundle")
        require(len(selected_camera_files) >= 2, "complete package upload bundle requires at least two independent camera assets")
        require(len(selected_hard_camera_files) >= 2, "complete package upload bundle requires at least two hard-authority camera assets")
    if package_status == "partial_approved":
        require(bool(approved_assets), "partial_approved requires at least one approved asset")
        require(geometry_status != "blocked", "partial_approved cannot claim a fully blocked geometry coverage")
    if package_status in {"blocked_source_insufficient", "blocked_identity_conflict", "blocked_generation_runtime", "blocked_generation_semantic_mismatch"}:
        require(geometry_status != "approved", f"{package_status} cannot include approved multi-camera geometry")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a complex product identity asset package v2.")
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    try:
        validate_package(args.package)
    except (ValidationFailure, OSError, UnicodeDecodeError) as exc:
        print(f"asset package validation: FAILED\n  - {exc}", file=sys.stderr)
        return 1
    print(f"asset package validation: OK ({args.package.resolve()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
