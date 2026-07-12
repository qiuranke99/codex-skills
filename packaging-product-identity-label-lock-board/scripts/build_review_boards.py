#!/usr/bin/env python3
"""Deterministically compile approved packaging masters into split 16:9 review boards."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps


SEMANTIC_ROLES = {
    "neutral_rotation", "elevation", "framing_bridge",
    "copy", "code", "structure", "material",
}


def semantic_role(entry: dict[str, Any]) -> str | None:
    family = entry.get("family")
    if family == "neutral_ring":
        return "neutral_rotation"
    if family in {"high_angle", "low_angle", "top_bottom"}:
        return "elevation"
    if family in {"upper_half_close", "lower_half_close"}:
        return "framing_bridge"
    return {
        "detail_copy": "copy", "detail_code": "code",
        "detail_structure": "structure", "detail_material": "material",
    }.get(str(family))


def ordered_key(entry: dict[str, Any]) -> tuple[int, float, str]:
    family = str(entry.get("family", ""))
    view_id = str(entry.get("view_id", ""))
    try:
        azimuth = float(entry.get("azimuth_deg", 0.0))
    except (TypeError, ValueError):
        azimuth = 0.0
    if family == "neutral_ring":
        return (0, azimuth, view_id)
    if family in {"high_angle", "low_angle", "top_bottom"}:
        return ({"high_angle": 0, "low_angle": 1, "top_bottom": 2}[family], azimuth, view_id)
    if family in {"upper_half_close", "lower_half_close"}:
        return ({"upper_half_close": 0, "lower_half_close": 1}[family], azimuth, view_id)
    return (0, 0.0, view_id)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def resolve_asset(run_root: Path, locator: str) -> Path:
    path = Path(locator)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("asset locator must be run-relative and cannot contain '..'")
    resolved = (run_root.resolve() / path).resolve()
    resolved.relative_to(run_root.resolve())
    return resolved


def board_layout(count: int, max_cells: int) -> tuple[int, int]:
    if max_cells <= 4:
        return 2, 2
    if count <= 3:
        return 3, 1
    return 3, 2


def build_board(
    entries: list[dict[str, Any]], output: Path, width: int, height: int,
    background: tuple[int, int, int], role: str, semantic_board_role: str,
    run_root: Path,
) -> dict[str, Any]:
    max_cells = 4 if all(str(item.get("family", "")).startswith("detail") for item in entries) else 6
    columns, rows = board_layout(len(entries), max_cells)
    margin = max(24, width // 120)
    gutter = max(18, width // 160)
    caption_height = max(72, height // 24)
    cell_width = (width - margin * 2 - gutter * (columns - 1)) // columns
    cell_height = (height - margin * 2 - gutter * (rows - 1)) // rows
    canvas = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    input_records: list[dict[str, Any]] = []

    for index, entry in enumerate(entries):
        row, column = divmod(index, columns)
        x0 = margin + column * (cell_width + gutter)
        y0 = margin + row * (cell_height + gutter)
        image_area = (x0, y0, x0 + cell_width, y0 + cell_height - caption_height)
        source = Path(entry["resolved_path"])
        with Image.open(source) as opened:
            image = opened.convert("RGB")
        fitted = ImageOps.contain(image, (image_area[2] - image_area[0], image_area[3] - image_area[1]), Image.Resampling.LANCZOS)
        paste_x = image_area[0] + (image_area[2] - image_area[0] - fitted.width) // 2
        paste_y = image_area[1] + (image_area[3] - image_area[1] - fitted.height) // 2
        canvas.paste(fitted, (paste_x, paste_y))
        label = str(entry.get("view_id") or entry.get("asset_id"))
        draw.rectangle((x0, y0 + cell_height - caption_height, x0 + cell_width, y0 + cell_height), fill=(245, 245, 245))
        draw.text((x0 + 14, y0 + cell_height - caption_height + 14), label, fill=(20, 20, 20), font=font)
        input_records.append({
            "asset_id": entry.get("asset_id"),
            "view_id": entry.get("view_id"),
            "file_path": entry.get("file_path"),
            "file_sha256": entry.get("file_sha256"),
        })

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=False)
    output_locator = output.resolve().relative_to(run_root.resolve()).as_posix()
    return {
        "file_path": output_locator,
        "file_sha256": sha256_file(output),
        "pixel_dimensions": {"width": width, "height": height},
        "aspect_ratio_profile": "16:9",
        "role": role,
        "semantic_board_role": semantic_board_role,
        "ordered_view_ids": [item["view_id"] for item in input_records],
        "derivation_mode": "deterministic_composite",
        "inputs": input_records,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-qa", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--family", action="append", default=[], help="Only include this family; repeat as needed")
    parser.add_argument("--semantic-role", choices=sorted(SEMANTIC_ROLES), help="Build exactly one semantic review-board family")
    parser.add_argument("--width", type=int, default=3840)
    parser.add_argument("--height", type=int, default=2160)
    parser.add_argument("--prefix", default="packaging_review")
    parser.add_argument("--dense-index", action="store_true", help="Role-label output as review_only_no_qa_authority")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.width * 9 != args.height * 16 or args.width < 3840 or args.height < 2160:
        print("ERROR: review-board output must be exact 16:9 at no less than 3840x2160")
        return 2
    qa = load_json(args.asset_qa)
    run_root = args.asset_qa.resolve().parents[1]
    assets = qa.get("assets")
    if not isinstance(assets, list):
        print("ERROR: asset_qa assets must be an array")
        return 2
    selected: list[dict[str, Any]] = []
    allowed_families = set(args.family)
    for entry in assets:
        if (
            not isinstance(entry, dict)
            or entry.get("assistant_qa_status") != "passed"
            or entry.get("text_pollution_status") != "passed"
            or entry.get("copy_composition_status") != "passed"
            or entry.get("post_verification_status") != "passed"
        ):
            continue
        if allowed_families and entry.get("family") not in allowed_families:
            continue
        entry_semantic_role = semantic_role(entry)
        if entry_semantic_role not in SEMANTIC_ROLES:
            print(f"ERROR: unknown review-board semantic role for {entry.get('view_id')}")
            return 2
        if args.semantic_role and entry_semantic_role != args.semantic_role:
            continue
        try:
            path = resolve_asset(run_root, str(entry.get("file_path", "")))
        except (ValueError, OSError) as exc:
            print(f"ERROR: unsafe approved asset path for {entry.get('view_id')}: {exc}")
            return 2
        if not path.is_file() or entry.get("file_sha256") != sha256_file(path):
            print(f"ERROR: approved asset file/hash invalid for {entry.get('view_id')}")
            return 2
        copy = dict(entry)
        copy["resolved_path"] = str(path)
        selected.append(copy)
    if not selected:
        print("ERROR: no approved assets matched the requested family filter")
        return 2
    selected_semantic_roles = {semantic_role(item) for item in selected}
    if len(selected_semantic_roles) != 1:
        print("ERROR: one review-board build must contain exactly one semantic board role")
        return 2
    selected_semantic_role = str(next(iter(selected_semantic_roles)))
    selected.sort(key=ordered_key)

    max_cells = 4 if all(str(item.get("family", "")).startswith("detail") for item in selected) else 6
    chunks = [selected[index : index + max_cells] for index in range(0, len(selected), max_cells)]
    role = "review_only_no_qa_authority" if args.dense_index else "human_review_qa_board"
    try:
        args.output_dir.resolve().relative_to(run_root.resolve())
    except ValueError:
        print("ERROR: output-dir must stay inside the packaging run root")
        return 2
    args.output_dir.mkdir(parents=True, exist_ok=True)
    boards: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks, start=1):
        output = args.output_dir / f"{args.prefix}_{index:02d}.png"
        boards.append(build_board(
            chunk, output, args.width, args.height, (250, 250, 250), role,
            selected_semantic_role, run_root,
        ))
    manifest = {
        "schema_version": "packaging-review-board-manifest.v1",
        "source_asset_qa_sha256": sha256_file(args.asset_qa),
        "semantic_board_role": selected_semantic_role,
        "ordered_view_ids": [item["view_id"] for item in selected],
        "board_count": len(boards),
        "boards": boards,
    }
    manifest_path = args.output_dir / f"{args.prefix}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS",
        "board_count": len(boards),
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
