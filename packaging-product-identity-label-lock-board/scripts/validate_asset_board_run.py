#!/usr/bin/env python3
"""Validate one sparse-reference packaging video asset board and its evidence bindings."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any


EXPECTED_VIEWS = {
    "front",
    "back",
    "side",
    "high_side_45",
    "low_side_45",
    "top_down",
    "low_up",
}
EVIDENCE = {"source_observed", "source_crop", "deterministic_reprojection", "bounded_inferred", "unknown"}
SOURCE_DERIVED = {"source_observed", "source_crop", "deterministic_reprojection"}
RAW_FAILURE_FLAGS = {
    "cropped_full_product",
    "duplicate_merged_or_overlapping_product",
    "lying_down_product",
    "blank_placeholder_or_unused_region",
    "visible_frame_card_grid_divider_or_evidence_strip",
    "identity_closure_fill_label_or_embossing_drift",
    "invented_or_corrupted_visible_copy",
}
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


def worker_prompt_binding_is_valid(worker: dict[str, Any], prompt_bytes: bytes) -> bool:
    contract = worker.get("contract")
    if contract == "delegated_image_worker_result.v1":
        return all(
            [
                worker.get("prompt_sha_match") is True,
                worker.get("generation_prompt_sha256") == sha256_bytes(prompt_bytes),
                worker.get("tool_prompt_sha256") == sha256_bytes(prompt_bytes),
            ]
        )
    if contract != "delegated_image_worker_result.v2":
        return False
    has_one_file_terminator = all(
        [
            prompt_bytes.endswith(b"\n"),
            not prompt_bytes.endswith(b"\n\n"),
            b"\r" not in prompt_bytes,
        ]
    )
    content_bytes = prompt_bytes[:-1] if has_one_file_terminator else prompt_bytes
    mode = worker.get("prompt_transport_mode")
    common = all(
        [
            worker.get("generation_prompt_sha256") == sha256_bytes(prompt_bytes),
            worker.get("frozen_prompt_sha256") == sha256_bytes(prompt_bytes),
            worker.get("prompt_content_sha256") == sha256_bytes(content_bytes),
            worker.get("prompt_content_match") is True,
        ]
    )
    if not common:
        return False
    if mode == "exact_bytes":
        return all(
            [
                worker.get("tool_prompt_sha256") == sha256_bytes(prompt_bytes),
                worker.get("prompt_sha_match") is True,
                worker.get("prompt_transport_normalization_applied") is False,
            ]
        )
    if mode == "single_terminal_lf_omitted":
        return all(
            [
                has_one_file_terminator,
                worker.get("tool_prompt_sha256") == sha256_bytes(content_bytes),
                worker.get("prompt_sha_match") is False,
                worker.get("prompt_transport_normalization_applied") is True,
            ]
        )
    return False


def normalized(path: Path) -> str:
    # Compare filesystem identity after resolving symlinks/junctions and platform
    # aliases (for example macOS /var -> /private/var). Lexical abspath alone
    # rejected valid worker/compositor receipts on non-Linux CI runners.
    return os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(path))))


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


def parse_json_object(data: bytes, code: str, label: str) -> dict[str, Any]:
    """Parse a hash-bound JSON artifact and reject non-object roots deterministically."""
    if data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise ValidationError(code, f"{label} must be UTF-8/LF without BOM")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(code, f"{label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(code, f"{label} must be a JSON object")
    return value


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
    if manifest.get("schema_version") != "packaging_video_asset_board.v2":
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
    reference_sha_by_alias = {
        entry.get("alias"): entry.get("sha256")
        for entry in reference_entries
        if isinstance(entry, dict) and isinstance(entry.get("alias"), str)
    }
    aliases = set(reference_sha_by_alias)
    profile = manifest.get("input_profile")
    if profile == "one_to_three_reference" and len(reference_entries) > 3:
        raise ValidationError("blocked_input_profile_mismatch", "one_to_three_reference contains more than three files")
    if profile not in {"one_to_three_reference", "extended_reference"}:
        raise ValidationError("blocked_input_profile_mismatch", "unsupported input profile")

    prompt_path, prompt_bytes = require_file_hash(
        root, manifest, "generation_prompt_path", "generation_prompt_sha256"
    )
    copy_ledger_path, copy_ledger_bytes = require_file_hash(root, manifest, "copy_ledger_path", "copy_ledger_sha256")
    copy_block_path, _ = require_file_hash(root, manifest, "copy_prompt_block_path", "copy_prompt_block_sha256")
    copy_receipt_path, _ = require_file_hash(
        root, manifest, "copy_prompt_receipt_path", "copy_prompt_receipt_sha256"
    )
    copy_qa_path, _ = require_file_hash(root, manifest, "copy_qa_path", "copy_qa_sha256")
    copy_ledger = parse_json_object(copy_ledger_bytes, "blocked_copy_ledger_invalid", "copy ledger")
    if copy_ledger.get("schema_version") != "packaging_copy_ledger.v1" or not isinstance(copy_ledger.get("regions"), list):
        raise ValidationError("blocked_copy_ledger_invalid", "unexpected copy-ledger schema")
    for region in copy_ledger["regions"]:
        if not isinstance(region, dict):
            raise ValidationError("blocked_copy_ledger_invalid", "copy-ledger region must be an object")
        source_alias = region.get("source_alias")
        if source_alias not in reference_sha_by_alias or region.get("source_sha256") != reference_sha_by_alias[source_alias]:
            raise ValidationError(
                "blocked_copy_ledger_source_binding",
                f"copy region {region.get('region_id')} does not bind one frozen source alias/hash",
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
    raw_qa_path, raw_qa_bytes = require_file_hash(root, manifest, "raw_board_qa_path", "raw_board_qa_sha256")
    plan_path, plan_bytes = require_file_hash(root, manifest, "composition_plan_path", "composition_plan_sha256")
    receipt_path, receipt_bytes = require_file_hash(
        root, manifest, "composition_receipt_path", "composition_receipt_sha256"
    )
    final_path, final_bytes = require_file_hash(root, manifest, "final_board_path", "final_board_sha256")

    worker = parse_json_object(worker_bytes, "blocked_worker_provenance_invalid", "worker result")
    reference_mode = worker.get("reference_mode")
    if reference_mode in {None, "frozen_manifest", "frozen_source_manifest"}:
        worker_reference_binding_valid = all(
            [
                worker.get("reference_manifest_sha256") == sha256_bytes(reference_bytes),
                worker.get("reference_count") == len(reference_entries),
            ]
        )
    elif reference_mode == "generation_provider_pack":
        pack_path, pack_bytes = require_file_hash(
            root,
            manifest,
            "generation_reference_pack_path",
            "generation_reference_pack_sha256",
        )
        pack = parse_json_object(pack_bytes, "blocked_reference_manifest_invalid", "provider reference pack")
        provider_entries = pack.get("provider_references")
        provider_count = pack.get("provider_reference_count")
        source_manifest_path = Path(str(pack.get("source_reference_manifest_path", "")))
        worker_reference_binding_valid = all(
            [
                pack.get("schema_version") == "packaging_generation_reference_pack.v1",
                isinstance(provider_entries, list),
                isinstance(provider_count, int),
                isinstance(provider_entries, list) and len(provider_entries) == provider_count,
                isinstance(provider_count, int) and 1 <= provider_count <= 5,
                same_path(str(source_manifest_path), reference_path),
                pack.get("source_reference_manifest_sha256") == sha256_bytes(reference_bytes),
                worker.get("reference_manifest_sha256") == sha256_bytes(pack_bytes),
                worker.get("ordered_reference_bundle_sha256") == pack.get("provider_bundle_sha256"),
                worker.get("reference_count") == provider_count,
                same_path(worker.get("reference_manifest_path"), pack_path),
            ]
        )
    else:
        worker_reference_binding_valid = False
    if not all(
        [
            worker.get("ok") is True,
            worker_prompt_binding_is_valid(worker, prompt_bytes),
            worker.get("reference_bytes_verified") is True,
            worker_reference_binding_valid,
        ]
    ):
        raise ValidationError("blocked_worker_provenance_invalid", "worker result does not bind prompt and references")

    plan = parse_json_object(plan_bytes, "blocked_composition_plan_invalid", "composition plan")
    receipt = parse_json_object(receipt_bytes, "blocked_composition_receipt_invalid", "composition receipt")
    if plan.get("schema_version") != "packaging_board_composition_plan.v2":
        raise ValidationError("blocked_composition_plan_invalid", "unexpected composition-plan schema")
    if receipt.get("schema_version") != "packaging_board_composition_receipt.v2":
        raise ValidationError("blocked_composition_receipt_invalid", "unexpected composition-receipt schema")
    raw_path = inside(root, plan.get("raw_board_path"), "raw_board_path")
    if not raw_path.is_file() or worker.get("image_sha256") != sha256_bytes(raw_path.read_bytes()):
        raise ValidationError("blocked_worker_raw_board_mismatch", "worker image does not bind composition raw board")
    if not same_path(worker.get("run_image_path"), raw_path):
        raise ValidationError("blocked_worker_raw_board_mismatch", "worker run_image_path differs from raw board")
    raw_qa = parse_json_object(raw_qa_bytes, "blocked_raw_board_qa", "raw-board QA")
    raw_view_ids = raw_qa.get("complete_view_ids")
    raw_detail_count = raw_qa.get("detail_region_count")
    raw_total_count = raw_qa.get("total_region_count")
    failure_flags = raw_qa.get("failure_flags")
    raw_view_ids_valid = (
        isinstance(raw_view_ids, list)
        and len(raw_view_ids) == 7
        and all(isinstance(view_id, str) for view_id in raw_view_ids)
        and set(raw_view_ids) == EXPECTED_VIEWS
    )
    raw_detail_count_valid = isinstance(raw_detail_count, int) and not isinstance(raw_detail_count, bool) and raw_detail_count in (2, 3)
    raw_total_count_valid = isinstance(raw_total_count, int) and not isinstance(raw_total_count, bool) and raw_total_count in (9, 10)
    failure_flags_valid = (
        isinstance(failure_flags, dict)
        and set(failure_flags) == RAW_FAILURE_FLAGS
        and all(failure_flags.get(key) is False for key in RAW_FAILURE_FLAGS)
    )
    if not all(
        [
            raw_qa.get("schema_version") == "packaging_raw_board_qa.v1",
            raw_qa.get("raw_board_sha256") == sha256_bytes(raw_path.read_bytes()),
            raw_qa.get("inspected") is True,
            raw_qa.get("overall_status") == "passed",
            raw_view_ids_valid,
            raw_qa.get("complete_view_count") == 7,
            raw_detail_count_valid,
            raw_total_count_valid,
            raw_detail_count_valid and raw_total_count_valid and raw_total_count == 7 + raw_detail_count,
            failure_flags_valid,
        ]
    ):
        raise ValidationError(
            "blocked_raw_board_qa",
            "raw board must be directly inspected and pass the exact seven-view, two/three-detail, borderless, populated, identity, and copy gates before composition",
        )
    if not all(
        [
            receipt.get("plan_sha256") == sha256_bytes(plan_bytes),
            receipt.get("raw_board_sha256") == sha256_bytes(raw_path.read_bytes()),
            receipt.get("output_board_sha256") == sha256_bytes(final_bytes),
            same_path(receipt.get("plan_path"), plan_path),
            same_path(receipt.get("raw_board_path"), raw_path),
            same_path(receipt.get("output_board_path"), final_path),
            receipt.get("detail_overlay_count") in {2, 3},
            receipt.get("detail_regions_populated") is True,
            receipt.get("layout_style") == "borderless_continuous_background",
            receipt.get("drawn_borders") is False,
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
    if not isinstance(plan_layout, list) or not 2 <= len(plan_layout) <= 3 or receipt_layout != plan_layout:
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
        raise ValidationError("blocked_composition_detail_mapping", "every detail region must be populated exactly once")

    views = manifest.get("view_regions")
    if not isinstance(views, list) or len(views) != 7:
        raise ValidationError("blocked_view_coverage", "exactly seven full-product view regions are required")
    view_ids = [view.get("view_id") for view in views if isinstance(view, dict)]
    if len(view_ids) != 7 or set(view_ids) != EXPECTED_VIEWS:
        raise ValidationError("blocked_view_coverage", "view IDs must match the seven-view board contract")
    for view in views:
        status = view.get("evidence_status")
        if status not in EVIDENCE or status == "unknown":
            raise ValidationError("blocked_view_evidence", f"COMPLETE view has invalid evidence status: {status}")

    details = manifest.get("detail_regions")
    if not isinstance(details, list) or not 2 <= len(details) <= 3:
        raise ValidationError("blocked_detail_coverage", "two to three detail regions are required")
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
    total_regions = len(views) + len(details)
    if total_regions not in {9, 10} or manifest.get("region_count") != total_regions:
        raise ValidationError("blocked_region_count", "the board must contain nine regions by default and never more than ten")
    if raw_detail_count != len(details) or raw_total_count != total_regions:
        raise ValidationError(
            "blocked_raw_board_qa",
            "raw-board QA topology differs from the accepted manifest topology",
        )
    if manifest.get("layout_style") != "borderless_continuous_background":
        raise ValidationError("blocked_visible_frames", "manifest must declare borderless_continuous_background")
    if plan.get("layout_style") != "borderless_continuous_background" or plan.get("drawn_borders") is not False:
        raise ValidationError("blocked_visible_frames", "composition plan violates the borderless layout contract")

    ocr = manifest.get("ocr")
    if not isinstance(ocr, dict) or ocr.get("status") not in {"not_run", "candidates_only", "reviewed"}:
        raise ValidationError("blocked_ocr_state_invalid", "invalid OCR state")
    if ocr.get("blocking") is not False:
        raise ValidationError("blocked_ocr_global_gate", "OCR may not be a global board gate")
    if copy_ledger.get("ocr_status") != ocr.get("status"):
        raise ValidationError("blocked_ocr_state_invalid", "manifest OCR status differs from copy ledger")
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
    copy_validation = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(Path(__file__).resolve().parent / "validate_copy_contract.py"),
            "--ledger",
            str(copy_ledger_path),
            "--block",
            str(copy_block_path),
            "--receipt",
            str(copy_receipt_path),
            "--prompt",
            str(prompt_path),
            "--qa",
            str(copy_qa_path),
            "--copy-authority",
            authority,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if copy_validation.returncode != 0:
        detail = copy_validation.stderr.strip() or copy_validation.stdout.strip()
        raise ValidationError("blocked_copy_contract", detail)

    qa = manifest.get("qa")
    required_qa = {
        "seven_complete_views",
        "two_to_three_details",
        "nine_to_ten_total_regions",
        "borderless_continuous_background",
        "no_visible_frames",
        "identity_consistency",
        "label_fidelity",
        "copy_prompt_coverage",
        "copy_pixel_qa",
        "source_anchor_match",
        "non_product_text_pollution",
        "all_regions_populated",
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
        "region_count": total_regions,
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
