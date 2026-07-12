#!/usr/bin/env python3
"""Rectify declared evidence regions and append purpose-aware no-autocorrect OCR evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image

from run_ocr_preflight import (
    PreflightError,
    canonical_ledger_hash,
    image_dimensions,
    run_macos_vision,
    run_tesseract,
    select_engine,
    sha256_file,
)


REGION_PURPOSES = {"text", "code", "graphic", "mixed"}
REGION_VISIBILITY_MODES = {
    "direct", "oblique", "mirrored_showthrough", "refracted", "reflected", "occluded",
}
TEXT_REQUIRED_REGION_PURPOSES = {"text", "mixed"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--region-spec", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--crop-dir", type=Path)
    parser.add_argument("--engine", choices=["auto", "macos_vision", "tesseract"], default="auto")
    parser.add_argument("--language", action="append", default=[])
    parser.add_argument("--tesseract-languages", default="chi_sim+eng")
    return parser.parse_args(argv)


def load_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PreflightError(f"{label} root must be an object", 3)
    return value


def canonical_hash(value: dict[str, Any]) -> str:
    payload = copy.deepcopy(value)
    payload.pop("receipt_sha256", None)
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def portable_locator(path: Path, run_root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(run_root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def normalized_crop_box(
    box: dict[str, Any], width: int, height: int, origin: str
) -> tuple[int, int, int, int]:
    try:
        x = float(box["x"])
        y = float(box["y"])
        w = float(box["width"])
        h = float(box["height"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PreflightError(f"invalid normalized region box: {exc}", 3) from exc
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > 1 or y + h > 1:
        raise PreflightError("normalized region box must be positive and stay inside the source", 3)
    left = int(round(x * width))
    right = int(round((x + w) * width))
    if origin == "bottom_left":
        top = int(round((1.0 - (y + h)) * height))
        bottom = int(round((1.0 - y) * height))
    elif origin == "top_left":
        top = int(round(y * height))
        bottom = int(round((y + h) * height))
    else:
        raise PreflightError("coordinate_origin must be top_left or bottom_left", 3)
    if right <= left or bottom <= top:
        raise PreflightError("region rounds to an empty pixel crop", 3)
    return left, top, right, bottom


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        ledger = load_object(args.ledger.resolve(), "OCR ledger")
        spec = load_object(args.region_spec.resolve(), "region spec")
        if spec.get("schema_version") != "packaging-region-ocr-spec.v2":
            raise PreflightError("region spec schema_version is invalid", 3)
        if spec.get("source_id") != args.source_id:
            raise PreflightError("region spec source_id must match --source-id", 3)
        records = ledger.get("source_records")
        if not isinstance(records, list):
            raise PreflightError("OCR ledger source_records must be an array", 3)
        matches = [item for item in records if isinstance(item, dict) and item.get("source_id") == args.source_id]
        if len(matches) != 1:
            raise PreflightError("source-id must match exactly one OCR ledger record", 3)
        source_record = matches[0]
        whole_passes = source_record.get("whole_product_ocr_passes")
        if not isinstance(whole_passes, list) or not whole_passes or not any(
            isinstance(item, dict) and item.get("scope") == "whole_product" for item in whole_passes
        ):
            raise PreflightError("whole-product OCR must exist before region OCR", 4)
        run_root = args.ledger.resolve().parents[1]
        source_locator = Path(str(source_record.get("file_path")))
        source_path = (
            source_locator.resolve()
            if source_locator.is_absolute()
            else (run_root / source_locator).resolve()
        )
        if not source_path.is_file() or sha256_file(source_path) != source_record.get("file_sha256"):
            raise PreflightError("source image is missing or differs from the whole-product OCR lock", 3)
        width, height = image_dimensions(source_path)
        if source_record.get("pixel_dimensions") != {"width": width, "height": height}:
            raise PreflightError("source pixel dimensions differ from the whole-product OCR lock", 3)
        regions = spec.get("regions")
        if not isinstance(regions, list) or not regions:
            raise PreflightError("region spec requires a non-empty regions array", 3)
        crop_dir = (args.crop_dir or (args.output.parent / "rectified_regions" / args.source_id)).resolve()
        crop_dir.mkdir(parents=True, exist_ok=True)
        crop_paths: list[Path] = []
        region_by_crop: dict[str, dict[str, Any]] = {}
        receipt_by_region: dict[str, tuple[Path, dict[str, Any]]] = {}
        seen_regions: set[str] = set()
        with Image.open(source_path) as opened:
            source_image = opened.convert("RGB")
            for index, region in enumerate(regions):
                if not isinstance(region, dict):
                    raise PreflightError(f"regions[{index}] must be an object", 3)
                region_id = region.get("region_id")
                if not isinstance(region_id, str) or not region_id or region_id in seen_regions:
                    raise PreflightError(f"regions[{index}].region_id must be unique", 3)
                seen_regions.add(region_id)
                for key in ("surface_id", "physical_layer_id"):
                    if not isinstance(region.get(key), str) or not region.get(key):
                        raise PreflightError(f"regions[{index}].{key} must be non-empty", 3)
                if region.get("visibility_mode") not in REGION_VISIBILITY_MODES:
                    raise PreflightError(f"regions[{index}].visibility_mode is invalid", 3)
                if region.get("region_purpose") not in REGION_PURPOSES:
                    raise PreflightError(
                        f"regions[{index}].region_purpose must be text, code, graphic, or mixed", 3
                    )
                box = normalized_crop_box(
                    region.get("bounding_box_normalized"), width, height,
                    str(region.get("coordinate_origin")),
                )
                crop_path = crop_dir / f"{region_id}.png"
                source_image.crop(box).save(crop_path, format="PNG", optimize=False)
                receipt_path = crop_dir / f"{region_id}.crop_receipt.json"
                receipt: dict[str, Any] = {
                    "schema_version": "packaging-region-crop-receipt.v2",
                    "source_id": args.source_id,
                    "source_path": portable_locator(source_path, run_root),
                    "source_file_sha256": source_record.get("file_sha256"),
                    "source_pixel_dimensions": {"width": width, "height": height},
                    "region_id": region_id,
                    "surface_id": region.get("surface_id"),
                    "physical_layer_id": region.get("physical_layer_id"),
                    "visibility_mode": region.get("visibility_mode"),
                    "region_purpose": region.get("region_purpose"),
                    "region_spec_path": portable_locator(args.region_spec, run_root),
                    "region_spec_sha256": sha256_file(args.region_spec.resolve()),
                    "coordinate_origin": region.get("coordinate_origin"),
                    "bounding_box_normalized": region.get("bounding_box_normalized"),
                    "crop_box_px": list(box),
                    "crop_method": "axis_aligned_normalized_bbox_v1",
                    "rectifier_script_sha256": sha256_file(Path(__file__).resolve()),
                    "rectified_crop_path": portable_locator(crop_path, run_root),
                    "rectified_crop_sha256": sha256_file(crop_path),
                    "receipt_sha256": None,
                }
                receipt["receipt_sha256"] = canonical_hash(receipt)
                receipt_path.write_text(
                    json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8",
                )
                crop_paths.append(crop_path)
                region_by_crop[str(crop_path.resolve())] = region
                receipt_by_region[region_id] = (receipt_path, receipt)
        languages = args.language or list(ledger.get("language_set") or ["zh-Hans", "en-US"])
        engine = select_engine(args.engine)
        if engine == "macos_vision":
            raw, engine_version = run_macos_vision(crop_paths, languages)
        else:
            raw, engine_version = run_tesseract(crop_paths, args.tesseract_languages)
        raw_by_path = {str(Path(item["file_path"]).resolve()): item for item in raw}
        updated = copy.deepcopy(ledger)
        target = next(item for item in updated["source_records"] if item["source_id"] == args.source_id)
        existing_region_ids = set(seen_regions)
        target["region_ocr_passes"] = [
            item for item in target.get("region_ocr_passes", [])
            if item.get("region_id") not in existing_region_ids
        ]
        target["text_observations"] = [
            item for item in target.get("text_observations", [])
            if item.get("region_id") not in existing_region_ids
        ]
        blocked_zero_text_regions: list[str] = []
        zero_text_non_text_regions: list[str] = []
        for crop_path in crop_paths:
            region = region_by_crop[str(crop_path.resolve())]
            region_id = region["region_id"]
            raw_record = raw_by_path.get(str(crop_path.resolve()))
            if raw_record is None:
                raise PreflightError(f"OCR engine omitted region crop {region_id}", 4)
            observations = raw_record.get("text_observations")
            if not isinstance(observations, list):
                raise PreflightError(f"region OCR returned malformed observations for {region_id}", 4)
            pass_id = f"{args.source_id}_{region_id}_REGION_01"
            receipt_path, crop_receipt = receipt_by_region[region_id]
            region_purpose = str(region.get("region_purpose"))
            if observations:
                zero_detection_review_status = "not_applicable"
            elif region_purpose in TEXT_REQUIRED_REGION_PURPOSES:
                zero_detection_review_status = "review_required"
                blocked_zero_text_regions.append(region_id)
            else:
                zero_detection_review_status = "not_applicable_non_text_region"
                zero_text_non_text_regions.append(region_id)
            target["region_ocr_passes"].append({
                "pass_id": pass_id, "region_id": region_id,
                "surface_id": region.get("surface_id"),
                "physical_layer_id": region.get("physical_layer_id"),
                "visibility_mode": region.get("visibility_mode"),
                "region_purpose": region_purpose,
                "source_id": args.source_id,
                "source_file_sha256": source_record.get("file_sha256"),
                "engine_id": engine, "engine_version": engine_version,
                "language_set": languages, "uses_language_correction": False,
                "observation_count": len(observations),
                "zero_detection_review_status": zero_detection_review_status,
                "region_spec_path": portable_locator(args.region_spec, run_root),
                "region_spec_sha256": sha256_file(args.region_spec.resolve()),
                "coordinate_origin": region.get("coordinate_origin"),
                "bounding_box_normalized": region.get("bounding_box_normalized"),
                "crop_method": "axis_aligned_normalized_bbox_v1",
                "rectifier_script_sha256": sha256_file(Path(__file__).resolve()),
                "crop_receipt_path": portable_locator(receipt_path, run_root),
                "crop_receipt_sha256": sha256_file(receipt_path),
                "crop_receipt_semantic_sha256": crop_receipt["receipt_sha256"],
                "rectified_crop_path": portable_locator(crop_path, run_root),
                "rectified_crop_sha256": sha256_file(crop_path),
            })
            if not observations:
                continue
            for index, observation in enumerate(observations, start=1):
                target["text_observations"].append({
                    "observation_id": f"{args.source_id}_{region_id}_TEXT_{index:04d}",
                    "text": str(observation.get("text", "")),
                    "confidence": float(observation.get("confidence", 0.0)),
                    "bounding_box_normalized": observation.get("bounding_box_normalized"),
                    "scope": "region", "region_id": region_id,
                    "region_pass_id": pass_id,
                    "surface_id": region.get("surface_id"),
                    "physical_layer_id": region.get("physical_layer_id"),
                    "visibility_mode": region.get("visibility_mode"),
                    "region_purpose": region_purpose,
                    "disposition": {
                        "status": "unresolved",
                        "review_status": "review_required",
                        "reviewer_id": None,
                        "field_id": None,
                        "evidence_note": "Region OCR discovery must be reconciled against the exact-copy SSOT.",
                    },
                })
        target["ocr_review_status"] = "review_required"
        updated["ledger_semantic_sha256"] = canonical_ledger_hash(updated)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(updated, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "status": (
                "blocked_zero_text_detection_review_required"
                if blocked_zero_text_regions else "review_required"
            ),
            "source_id": args.source_id,
            "region_count": len(crop_paths), "engine": engine,
            "zero_text_required_region_ids": blocked_zero_text_regions,
            "zero_text_non_text_region_ids": zero_text_non_text_regions,
            "output": str(args.output.resolve()), "sha256": sha256_file(args.output),
        }, ensure_ascii=False, sort_keys=True))
        return 4 if blocked_zero_text_regions else 0
    except (PreflightError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return exc.exit_code if isinstance(exc, PreflightError) else 3


if __name__ == "__main__":
    raise SystemExit(main())
