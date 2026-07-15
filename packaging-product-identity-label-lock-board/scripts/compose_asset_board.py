#!/usr/bin/env python3
"""Compose frozen source anchors/details onto one generated packaging asset board."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageOps


class CompositionError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> tuple[dict[str, Any], bytes]:
    if not path.is_file():
        raise CompositionError("blocked_composition_plan_missing", f"plan missing: {path}")
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise CompositionError("blocked_composition_plan_invalid", "plan must be UTF-8/LF without BOM")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CompositionError("blocked_composition_plan_invalid", str(exc)) from exc
    if not isinstance(value, dict):
        raise CompositionError("blocked_composition_plan_invalid", "plan must be a JSON object")
    return value, data


def normalized(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def run_path(run_dir: Path, value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise CompositionError("blocked_composition_plan_invalid", f"{field} must be a path string")
    path = (run_dir / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    try:
        common = os.path.commonpath([normalized(run_dir), normalized(path)])
    except ValueError as exc:
        raise CompositionError("blocked_composition_path_escape", str(exc)) from exc
    if common != normalized(run_dir):
        raise CompositionError("blocked_composition_path_escape", f"{field} escapes run directory: {path}")
    return path


def require_sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise CompositionError("blocked_composition_plan_invalid", f"{field} must be lowercase SHA-256")
    return value


def require_box(value: Any, field: str, width: int, height: int) -> tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != 4 or not all(isinstance(item, int) for item in value):
        raise CompositionError("blocked_composition_plan_invalid", f"{field} must contain four integers")
    left, top, right, bottom = value
    if left < 0 or top < 0 or right <= left or bottom <= top or right > width or bottom > height:
        raise CompositionError("blocked_composition_box_invalid", f"{field} is outside {width}x{height}: {value}")
    return left, top, right, bottom


def fit_image(image: Image.Image, size: tuple[int, int], mode: str, background: tuple[int, int, int]) -> Image.Image:
    rgb = ImageOps.exif_transpose(image).convert("RGB")
    if mode == "cover":
        return ImageOps.fit(rgb, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    if mode != "contain":
        raise CompositionError("blocked_composition_plan_invalid", f"unsupported fit mode: {mode}")
    contained = ImageOps.contain(rgb, size, method=Image.Resampling.LANCZOS)
    panel = Image.new("RGB", size, background)
    panel.paste(contained, ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2))
    return panel


def boxes_overlap(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> bool:
    return not (
        first[2] <= second[0]
        or second[2] <= first[0]
        or first[3] <= second[1]
        or second[3] <= first[1]
    )


def non_background_fraction(panel: Image.Image, background: tuple[int, int, int]) -> float:
    background_image = Image.new("RGB", panel.size, background)
    difference = ImageChops.difference(panel.convert("RGB"), background_image).convert("L")
    histogram = difference.histogram()
    changed = sum(histogram[9:])
    return changed / max(1, panel.width * panel.height)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    if not run_dir.is_dir():
        raise CompositionError("blocked_composition_run_missing", f"run directory missing: {run_dir}")
    plan_path = args.plan.expanduser().resolve()
    receipt_path = args.receipt.expanduser().resolve()
    for path, name in [(plan_path, "plan"), (receipt_path, "receipt")]:
        try:
            common = os.path.commonpath([normalized(run_dir), normalized(path)])
        except ValueError as exc:
            raise CompositionError("blocked_composition_path_escape", str(exc)) from exc
        if common != normalized(run_dir):
            raise CompositionError("blocked_composition_path_escape", f"{name} escapes run directory: {path}")

    plan, plan_bytes = load_json(plan_path)
    if plan.get("schema_version") != "packaging_board_composition_plan.v2":
        raise CompositionError("blocked_composition_plan_invalid", "unexpected plan schema")
    if plan.get("layout_style") != "borderless_continuous_background" or plan.get("drawn_borders") is not False:
        raise CompositionError(
            "blocked_composition_borderless_contract",
            "composition must declare a borderless continuous background and drawn_borders=false",
        )
    canvas = plan.get("canvas_size")
    if not isinstance(canvas, list) or len(canvas) != 2 or not all(isinstance(item, int) for item in canvas):
        raise CompositionError("blocked_composition_plan_invalid", "canvas_size must be [width, height]")
    canvas_width, canvas_height = canvas
    if canvas_width <= 0 or canvas_height <= 0 or canvas_width * 9 != canvas_height * 16:
        raise CompositionError("blocked_composition_canvas_invalid", "canvas must be exact horizontal 16:9")

    raw_path = run_path(run_dir, plan.get("raw_board_path"), "raw_board_path")
    output_path = run_path(run_dir, plan.get("output_board_path"), "output_board_path")
    if output_path == raw_path or output_path == plan_path or output_path == receipt_path:
        raise CompositionError("blocked_composition_output_invalid", "output path must be a distinct PNG")
    if output_path.suffix.lower() != ".png":
        raise CompositionError("blocked_composition_output_invalid", "output board must be PNG")
    if not raw_path.is_file():
        raise CompositionError("blocked_composition_raw_missing", f"raw board missing: {raw_path}")
    raw_bytes = raw_path.read_bytes()
    expected_raw_sha = require_sha(plan.get("raw_board_sha256"), "raw_board_sha256")
    if sha256_bytes(raw_bytes) != expected_raw_sha:
        raise CompositionError("blocked_composition_raw_mismatch", "raw board hash mismatch")

    with Image.open(raw_path) as raw:
        board = fit_image(
            raw,
            (canvas_width, canvas_height),
            str(plan.get("base_fit", "cover")),
            (248, 248, 248),
        )

    overlays = plan.get("overlays")
    if not isinstance(overlays, list) or not overlays:
        raise CompositionError("blocked_composition_plan_invalid", "overlays must be a non-empty array")
    detail_layout = plan.get("detail_layout")
    if not isinstance(detail_layout, list) or not 2 <= len(detail_layout) <= 3:
        raise CompositionError(
            "blocked_composition_detail_layout_invalid",
            "detail_layout must contain exactly two or three populated detail regions",
        )
    detail_targets: dict[str, tuple[int, int, int, int]] = {}
    for index, cell in enumerate(detail_layout, 1):
        if not isinstance(cell, dict):
            raise CompositionError("blocked_composition_detail_layout_invalid", f"detail cell {index} is not an object")
        region_id = cell.get("region_id")
        if not isinstance(region_id, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", region_id):
            raise CompositionError("blocked_composition_detail_layout_invalid", f"detail cell {index} has invalid region_id")
        if region_id in detail_targets:
            raise CompositionError("blocked_composition_detail_layout_invalid", f"duplicate detail region_id: {region_id}")
        target_box = require_box(cell.get("target_box"), f"detail_layout[{index}].target_box", canvas_width, canvas_height)
        if any(boxes_overlap(target_box, existing) for existing in detail_targets.values()):
            raise CompositionError("blocked_composition_detail_layout_overlap", f"detail target overlaps another cell: {region_id}")
        detail_targets[region_id] = target_box
    records: list[dict[str, Any]] = []
    ids: set[str] = set()
    populated_detail_ids: set[str] = set()
    placed_targets: list[tuple[str, tuple[int, int, int, int]]] = []
    role_counts = {"anchor": 0, "detail": 0}
    for index, overlay in enumerate(overlays, 1):
        if not isinstance(overlay, dict):
            raise CompositionError("blocked_composition_plan_invalid", f"overlay {index} is not an object")
        region_id = overlay.get("region_id")
        if not isinstance(region_id, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", region_id):
            raise CompositionError("blocked_composition_plan_invalid", f"overlay {index} has invalid region_id")
        if region_id in ids:
            raise CompositionError("blocked_composition_plan_invalid", f"duplicate region_id: {region_id}")
        ids.add(region_id)
        role = overlay.get("role")
        if role not in role_counts:
            raise CompositionError("blocked_composition_plan_invalid", f"invalid overlay role: {role}")
        role_counts[role] += 1
        if overlay.get("border_px", 0) != 0:
            raise CompositionError("blocked_composition_visible_frame", f"{region_id} requests a drawn border")
        if overlay.get("seamless_background_match") is not True:
            raise CompositionError(
                "blocked_composition_borderless_contract",
                f"{region_id} must declare seamless_background_match=true",
            )
        fit_mode = str(overlay.get("fit", "contain"))
        if role == "detail" and fit_mode != "cover":
            raise CompositionError(
                "blocked_composition_visible_frame",
                f"detail region {region_id} must use cover so no contain-padding box is created",
            )
        source_path = run_path(run_dir, overlay.get("source_path"), f"overlays[{index}].source_path")
        if not source_path.is_file():
            raise CompositionError("blocked_composition_source_missing", f"source missing: {source_path}")
        source_bytes = source_path.read_bytes()
        expected_source_sha = require_sha(overlay.get("source_sha256"), f"overlays[{index}].source_sha256")
        if sha256_bytes(source_bytes) != expected_source_sha:
            raise CompositionError("blocked_composition_source_mismatch", f"source hash mismatch: {region_id}")
        try:
            with Image.open(source_path) as source:
                source = ImageOps.exif_transpose(source).convert("RGB")
                crop_box = require_box(overlay.get("crop_box"), f"{region_id}.crop_box", source.width, source.height)
                crop = source.crop(crop_box)
        except OSError as exc:
            raise CompositionError("blocked_composition_source_decode", f"{region_id}: {exc}") from exc
        target_box = require_box(
            overlay.get("target_box"), f"{region_id}.target_box", canvas_width, canvas_height
        )
        for placed_region, placed_box in placed_targets:
            if boxes_overlap(target_box, placed_box):
                raise CompositionError(
                    "blocked_composition_target_overlap",
                    f"overlay target {region_id} overlaps {placed_region}",
                )
        placed_targets.append((region_id, target_box))
        if role == "detail":
            if region_id not in detail_targets:
                raise CompositionError(
                    "blocked_composition_detail_mapping",
                    f"detail overlay is not declared in detail_layout: {region_id}",
                )
            if target_box != detail_targets[region_id]:
                raise CompositionError(
                    "blocked_composition_detail_mapping",
                    f"detail overlay target differs from detail_layout: {region_id}",
                )
            populated_detail_ids.add(region_id)
        elif any(boxes_overlap(target_box, detail_box) for detail_box in detail_targets.values()):
            raise CompositionError(
                "blocked_composition_target_overlap",
                f"anchor overlay {region_id} overlaps the frozen detail layout",
            )
        background_value = overlay.get("background_rgb", [248, 248, 248])
        if (
            not isinstance(background_value, list)
            or len(background_value) != 3
            or not all(isinstance(item, int) and 0 <= item <= 255 for item in background_value)
        ):
            raise CompositionError("blocked_composition_plan_invalid", f"{region_id} has invalid background_rgb")
        target_size = (target_box[2] - target_box[0], target_box[3] - target_box[1])
        background = tuple(background_value)
        panel = fit_image(crop, target_size, fit_mode, background)
        occupancy = non_background_fraction(panel, background)
        if role == "detail" and occupancy < 0.02:
            raise CompositionError(
                "blocked_composition_detail_blank",
                f"detail overlay contains too little non-background evidence: {region_id} ({occupancy:.6f})",
            )
        board.paste(panel, (target_box[0], target_box[1]))
        records.append(
            {
                "index": index,
                "region_id": region_id,
                "role": role,
                "source_path": str(source_path),
                "source_sha256": expected_source_sha,
                "crop_box": list(crop_box),
                "target_box": list(target_box),
                "fit": fit_mode,
                "border_px": 0,
                "seamless_background_match": True,
                "evidence_status": "deterministic_reprojection",
                "non_background_fraction": round(occupancy, 6),
            }
        )

    if populated_detail_ids != set(detail_targets):
        missing = sorted(set(detail_targets) - populated_detail_ids)
        extra = sorted(populated_detail_ids - set(detail_targets))
        raise CompositionError(
            "blocked_composition_detail_mapping",
            f"every detail region must be filled exactly once; missing={missing}, extra={extra}",
        )
    if role_counts["detail"] != len(detail_targets) or not 2 <= role_counts["detail"] <= 3:
        raise CompositionError("blocked_composition_detail_mapping", "detail overlay count must equal detail_layout")
    if not 0 <= role_counts["anchor"] <= 3:
        raise CompositionError("blocked_composition_plan_invalid", "zero to three anchor overlays are legal")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(".tmp.png")
    board.save(temporary, format="PNG", optimize=False)
    os.replace(temporary, output_path)
    output_bytes = output_path.read_bytes()
    receipt = {
        "schema_version": "packaging_board_composition_receipt.v2",
        "plan_path": str(plan_path),
        "plan_sha256": sha256_bytes(plan_bytes),
        "raw_board_path": str(raw_path),
        "raw_board_sha256": expected_raw_sha,
        "output_board_path": str(output_path),
        "output_board_sha256": sha256_bytes(output_bytes),
        "width_px": canvas_width,
        "height_px": canvas_height,
        "exact_16_9": True,
        "anchor_overlay_count": role_counts["anchor"],
        "detail_overlay_count": role_counts["detail"],
        "layout_style": "borderless_continuous_background",
        "drawn_borders": False,
        "detail_regions_populated": True,
        "detail_layout": [
            {"region_id": region_id, "target_box": list(target_box)}
            for region_id, target_box in detail_targets.items()
        ],
        "overlays": records,
    }
    write_json(receipt_path, receipt)
    print(json.dumps({"ok": True, **receipt}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CompositionError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}), file=sys.stderr)
        raise SystemExit(2)
    except OSError as exc:
        print(
            json.dumps({"ok": False, "error_code": "blocked_composition_filesystem", "detail": str(exc)}),
            file=sys.stderr,
        )
        raise SystemExit(2)
