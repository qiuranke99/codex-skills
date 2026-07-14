#!/usr/bin/env python3
"""Validate one sparse-reference packaging video asset board and its evidence bindings."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import sys
from pathlib import Path
from typing import Any


EXPECTED_VIEWS = {
    "front",
    "back",
    "left_side",
    "right_side",
    "front_three_quarter",
    "rear_three_quarter",
    "high_angle",
    "low_angle",
}
EVIDENCE = {"source_observed", "source_crop", "deterministic_reprojection", "bounded_inferred", "unknown"}
SOURCE_DERIVED = {"source_observed", "source_crop", "deterministic_reprojection"}
SHA_RE = re.compile(r"[0-9a-f]{64}")
STAGING_PROMPT_PATTERNS = [
    re.compile(r"\bwill be replaced\b", re.IGNORECASE),
    re.compile(r"\breserv(?:e|ed)\b[^\n]{0,100}\b(?:detail|evidence)\b[^\n]{0,100}\b(?:window|cell|panel)s?\b", re.IGNORECASE),
    re.compile(r"\bkeep\b[^\n]{0,120}\b(?:window|cell|panel)s?\b[^\n]{0,80}\b(?:empty|blank)\b", re.IGNORECASE),
    re.compile(r"\bdo not place\b[^\n]{0,100}\b(?:close-up|detail)\b[^\n]{0,100}\b(?:window|cell|panel)s?\b", re.IGNORECASE),
]


class ValidationError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def load_json(path: Path, code: str) -> tuple[dict[str, Any], bytes]:
    if not path.is_file():
        raise ValidationError(code, f"missing JSON artifact: {path}")
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise ValidationError(code, f"JSON must be UTF-8/LF without BOM: {path}")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(code, str(exc)) from exc
    if not isinstance(value, dict):
        raise ValidationError(code, f"JSON artifact must be an object: {path}")
    return value, data


def inside(root: Path, value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValidationError("blocked_manifest_path_invalid", f"{field} must be a path string")
    path = (root / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    try:
        common = os.path.commonpath([normalized(root), normalized(path)])
    except ValueError as exc:
        raise ValidationError("blocked_manifest_path_escape", str(exc)) from exc
    if common != normalized(root):
        raise ValidationError("blocked_manifest_path_escape", f"{field} escapes run directory: {path}")
    return path


def require_file_hash(root: Path, manifest: dict[str, Any], path_field: str, hash_field: str) -> tuple[Path, bytes]:
    path = inside(root, manifest.get(path_field), path_field)
    if not path.is_file():
        raise ValidationError("blocked_manifest_artifact_missing", f"missing {path_field}: {path}")
    expected = manifest.get(hash_field)
    if not isinstance(expected, str) or not SHA_RE.fullmatch(expected):
        raise ValidationError("blocked_manifest_hash_invalid", f"{hash_field} must be lowercase SHA-256")
    data = path.read_bytes()
    if sha256_bytes(data) != expected:
        raise ValidationError("blocked_manifest_hash_mismatch", f"hash mismatch for {path_field}")
    return path, data


def same_path(value: Any, expected: Path) -> bool:
    return isinstance(value, str) and normalized(Path(value)) == normalized(expected)


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValidationError("blocked_final_board_invalid", "final board is not a valid PNG")
    return struct.unpack(">II", data[16:24])


def validated_box(value: Any, field: str, width: int, height: int) -> tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != 4 or not all(isinstance(item, int) for item in value):
        raise ValidationError("blocked_composition_detail_layout_invalid", f"{field} must contain four integers")
    left, top, right, bottom = value
    if left < 0 or top < 0 or right <= left or bottom <= top or right > width or bottom > height:
        raise ValidationError("blocked_composition_detail_layout_invalid", f"{field} is outside the final canvas")
    return left, top, right, bottom


def boxes_overlap(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> bool:
    return not (
        first[2] <= second[0]
        or second[2] <= first[0]
        or first[3] <= second[1]
        or second[3] <= first[1]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    manifest_path = args.manifest.expanduser().resolve()
    manifest, _ = load_json(manifest_path, "blocked_asset_board_manifest_invalid")
    root = manifest_path.parent
    if manifest.get("schema_version") != "packaging_video_asset_board.v1":
        raise ValidationError("blocked_asset_board_manifest_invalid", "unexpected asset-board schema")
    if manifest.get("run_status") != "COMPLETE":
        raise ValidationError("blocked_asset_board_incomplete", "run_status must be COMPLETE")

    reference_path = inside(root, manifest.get("reference_manifest_path"), "reference_manifest_path")
    references, reference_bytes = load_json(reference_path, "blocked_reference_manifest_invalid")
    if references.get("schema_version") != "packaging_reference_bundle.v1":
        raise ValidationError("blocked_reference_manifest_invalid", "unexpected reference-bundle schema")
    reference_entries = references.get("ordered_references")
    if not isinstance(reference_entries, list) or not 1 <= len(reference_entries) <= 8:
        raise ValidationError("blocked_reference_count_invalid", "one to eight frozen references are legal")
    aliases = {entry.get("alias") for entry in reference_entries if isinstance(entry, dict)}
    profile = manifest.get("input_profile")
    if profile == "one_to_three_reference" and len(reference_entries) > 3:
        raise ValidationError("blocked_input_profile_mismatch", "one_to_three_reference contains more than three files")
    if profile not in {"one_to_three_reference", "extended_reference"}:
        raise ValidationError("blocked_input_profile_mismatch", "unsupported input profile")

    prompt_path, prompt_bytes = require_file_hash(
        root, manifest, "generation_prompt_path", "generation_prompt_sha256"
    )
    try:
        prompt_text = prompt_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError("blocked_generation_prompt_invalid", str(exc)) from exc
    staging_hits = [pattern.pattern for pattern in STAGING_PROMPT_PATTERNS if pattern.search(prompt_text)]
    if staging_hits:
        raise ValidationError(
            "blocked_staging_prompt_leakage",
            "generation prompt requests an empty or later-filled intermediate board",
        )
    if "No blank cells" not in prompt_text or "fully populated" not in prompt_text:
        raise ValidationError(
            "blocked_generation_prompt_population_contract",
            "generation prompt must require a fully populated board and explicitly ban blank cells",
        )
    worker_path, worker_bytes = require_file_hash(root, manifest, "worker_result_path", "worker_result_sha256")
    plan_path, plan_bytes = require_file_hash(root, manifest, "composition_plan_path", "composition_plan_sha256")
    receipt_path, receipt_bytes = require_file_hash(
        root, manifest, "composition_receipt_path", "composition_receipt_sha256"
    )
    final_path, final_bytes = require_file_hash(root, manifest, "final_board_path", "final_board_sha256")

    worker = json.loads(worker_bytes.decode("utf-8"))
    if not all(
        [
            worker.get("ok") is True,
            worker.get("contract") == "delegated_image_worker_result.v1",
            worker.get("prompt_sha_match") is True,
            worker.get("reference_bytes_verified") is True,
            worker.get("generation_prompt_sha256") == sha256_bytes(prompt_bytes),
            worker.get("tool_prompt_sha256") == sha256_bytes(prompt_bytes),
            worker.get("reference_manifest_sha256") == sha256_bytes(reference_bytes),
            worker.get("reference_count") == len(reference_entries),
        ]
    ):
        raise ValidationError("blocked_worker_provenance_invalid", "worker result does not bind prompt and references")

    plan = json.loads(plan_bytes.decode("utf-8"))
    receipt = json.loads(receipt_bytes.decode("utf-8"))
    if plan.get("schema_version") != "packaging_board_composition_plan.v1":
        raise ValidationError("blocked_composition_plan_invalid", "unexpected composition-plan schema")
    if receipt.get("schema_version") != "packaging_board_composition_receipt.v1":
        raise ValidationError("blocked_composition_receipt_invalid", "unexpected composition-receipt schema")
    raw_path = inside(root, plan.get("raw_board_path"), "raw_board_path")
    if not raw_path.is_file() or worker.get("image_sha256") != sha256_bytes(raw_path.read_bytes()):
        raise ValidationError("blocked_worker_raw_board_mismatch", "worker image does not bind composition raw board")
    if not same_path(worker.get("run_image_path"), raw_path):
        raise ValidationError("blocked_worker_raw_board_mismatch", "worker run_image_path differs from raw board")
    if not all(
        [
            receipt.get("plan_sha256") == sha256_bytes(plan_bytes),
            receipt.get("raw_board_sha256") == sha256_bytes(raw_path.read_bytes()),
            receipt.get("output_board_sha256") == sha256_bytes(final_bytes),
            same_path(receipt.get("plan_path"), plan_path),
            same_path(receipt.get("raw_board_path"), raw_path),
            same_path(receipt.get("output_board_path"), final_path),
            receipt.get("detail_overlay_count") in {4, 5, 6},
            receipt.get("detail_cells_populated") is True,
            isinstance(receipt.get("anchor_overlay_count"), int),
            0 <= receipt.get("anchor_overlay_count") <= 3,
        ]
    ):
        raise ValidationError("blocked_composition_receipt_invalid", "composition receipt does not bind final board")

    width, height = png_size(final_path)
    if (width, height) != (3840, 2160):
        raise ValidationError("blocked_final_board_dimensions", f"final board must be 3840x2160, got {width}x{height}")

    plan_layout = plan.get("detail_layout")
    receipt_layout = receipt.get("detail_layout")
    if not isinstance(plan_layout, list) or not 4 <= len(plan_layout) <= 6 or receipt_layout != plan_layout:
        raise ValidationError("blocked_composition_detail_layout_invalid", "plan and receipt detail_layout must match")
    layout_ids: set[str] = set()
    layout_boxes: dict[str, tuple[int, int, int, int]] = {}
    for index, cell in enumerate(plan_layout, 1):
        if not isinstance(cell, dict):
            raise ValidationError("blocked_composition_detail_layout_invalid", f"detail cell {index} is not an object")
        region_id = cell.get("region_id")
        if not isinstance(region_id, str) or not region_id or region_id in layout_ids:
            raise ValidationError("blocked_composition_detail_layout_invalid", "detail layout IDs must be unique")
        target_box = validated_box(cell.get("target_box"), f"detail_layout[{index}].target_box", width, height)
        if any(boxes_overlap(target_box, other) for other in layout_boxes.values()):
            raise ValidationError("blocked_composition_detail_layout_overlap", f"detail target overlaps: {region_id}")
        layout_ids.add(region_id)
        layout_boxes[region_id] = target_box

    receipt_overlays = receipt.get("overlays")
    if not isinstance(receipt_overlays, list):
        raise ValidationError("blocked_composition_receipt_invalid", "receipt overlays must be an array")
    receipt_details: dict[str, dict[str, Any]] = {}
    for overlay in receipt_overlays:
        if not isinstance(overlay, dict) or overlay.get("role") != "detail":
            continue
        region_id = overlay.get("region_id")
        if not isinstance(region_id, str) or region_id in receipt_details:
            raise ValidationError("blocked_composition_detail_mapping", "receipt detail IDs must be unique")
        target_box = validated_box(overlay.get("target_box"), f"receipt.{region_id}.target_box", width, height)
        occupancy = overlay.get("non_background_fraction")
        if region_id not in layout_boxes or target_box != layout_boxes[region_id]:
            raise ValidationError("blocked_composition_detail_mapping", f"receipt detail does not match layout: {region_id}")
        if not isinstance(occupancy, (int, float)) or occupancy < 0.02:
            raise ValidationError("blocked_composition_detail_blank", f"detail is blank or near-blank: {region_id}")
        receipt_details[region_id] = overlay
    if set(receipt_details) != layout_ids or receipt.get("detail_overlay_count") != len(layout_ids):
        raise ValidationError("blocked_composition_detail_mapping", "every detail cell must be populated exactly once")

    views = manifest.get("view_cells")
    if not isinstance(views, list) or len(views) != 8:
        raise ValidationError("blocked_view_coverage", "exactly eight view cells are required")
    view_ids = [view.get("view_id") for view in views if isinstance(view, dict)]
    if len(view_ids) != 8 or set(view_ids) != EXPECTED_VIEWS:
        raise ValidationError("blocked_view_coverage", "view IDs must match the eight-view board contract")
    for view in views:
        status = view.get("evidence_status")
        if status not in EVIDENCE or status == "unknown":
            raise ValidationError("blocked_view_evidence", f"COMPLETE view has invalid evidence status: {status}")

    details = manifest.get("detail_cells")
    if not isinstance(details, list) or not 4 <= len(details) <= 6:
        raise ValidationError("blocked_detail_coverage", "four to six detail cells are required")
    region_ids: set[str] = set()
    for detail in details:
        if not isinstance(detail, dict):
            raise ValidationError("blocked_detail_coverage", "detail cell is not an object")
        region_id = detail.get("region_id")
        if not isinstance(region_id, str) or not region_id or region_id in region_ids:
            raise ValidationError("blocked_detail_coverage", "detail region IDs must be non-empty and unique")
        region_ids.add(region_id)
        if detail.get("evidence_status") not in SOURCE_DERIVED:
            raise ValidationError("blocked_detail_evidence", f"detail {region_id} is not source-derived")
        if detail.get("source_alias") not in aliases:
            raise ValidationError("blocked_detail_evidence", f"detail {region_id} has unknown source_alias")
    if region_ids != layout_ids:
        raise ValidationError(
            "blocked_composition_detail_mapping",
            "manifest detail cells must match the populated composition layout one-to-one",
        )

    ocr = manifest.get("ocr")
    if not isinstance(ocr, dict) or ocr.get("status") not in {"not_run", "candidates_only", "reviewed"}:
        raise ValidationError("blocked_ocr_state_invalid", "invalid OCR state")
    if ocr.get("blocking") is not False:
        raise ValidationError("blocked_ocr_global_gate", "OCR may not be a global board gate")
    authority = manifest.get("copy_authority")
    if authority not in {"video_reference", "exact_copy_evidence"}:
        raise ValidationError("blocked_copy_authority_invalid", "invalid copy authority")
    unresolved = manifest.get("unresolved_regions")
    if not isinstance(unresolved, list):
        raise ValidationError("blocked_copy_authority_invalid", "unresolved_regions must be an array")
    if authority == "exact_copy_evidence" and (ocr.get("status") != "reviewed" or unresolved):
        raise ValidationError(
            "blocked_exact_copy_authority",
            "exact_copy_evidence requires reviewed OCR and zero unresolved regions",
        )

    qa = manifest.get("qa")
    required_qa = {
        "eight_complete_views",
        "four_to_six_details",
        "identity_consistency",
        "label_fidelity",
        "source_anchor_match",
        "non_product_text_pollution",
        "all_cells_populated",
    }
    if not isinstance(qa, dict) or qa.get("inspected") is not True:
        raise ValidationError("blocked_visual_inspection", "main-agent inspection is required")
    failed = sorted(field for field in required_qa if qa.get(field) != "pass")
    if failed:
        raise ValidationError("blocked_visual_inspection", f"failed QA fields: {', '.join(failed)}")
    if qa.get("assistant_qa_status") not in {"passed", "conditional"}:
        raise ValidationError("blocked_visual_inspection", "assistant_qa_status must be passed or conditional")

    result = {
        "ok": True,
        "contract": "packaging_video_asset_board_validation.v1",
        "reference_count": len(reference_entries),
        "view_count": len(views),
        "detail_count": len(details),
        "copy_authority": authority,
        "assistant_qa_status": qa.get("assistant_qa_status"),
        "final_board_path": str(final_path),
        "final_board_sha256": sha256_bytes(final_bytes),
        "width_px": width,
        "height_px": height,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}), file=sys.stderr)
        raise SystemExit(2)
    except OSError as exc:
        print(
            json.dumps({"ok": False, "error_code": "blocked_validation_filesystem", "detail": str(exc)}),
            file=sys.stderr,
        )
        raise SystemExit(2)
