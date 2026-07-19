#!/usr/bin/env python3
"""Build a non-authoritative comparison board from accepted independent views."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from validate_coverage_package import ContractError, read_json, resolve_artifact, validate_package


def build_board(run_root: Path, columns: int = 2):
    from PIL import Image, ImageDraw, ImageOps

    run_root = run_root.resolve()
    validate_package(run_root, "state")
    manifest = read_json(run_root / "00_manifest" / "COVERAGE_MANIFEST.json")
    approved: list[tuple[str, Path, str]] = []
    for attempt in manifest["attempts"]:
        if attempt.get("decision") != "approved":
            continue
        inspection = read_json(resolve_artifact(run_root, attempt["inspection_path"], "inspection_missing"))
        if inspection.get("decision") != "approved":
            raise ContractError("review_board_source_invalid", f"attempt inspection is not approved: {attempt['attempt_id']}")
        image_path = resolve_artifact(run_root, attempt["image_path"], "image_missing")
        approved.append((attempt["view_id"], image_path, attempt["attempt_id"]))
    if not approved:
        raise ContractError("review_board_source_invalid", "no approved independent views")
    if len({view_id for view_id, _path, _attempt in approved}) != len(approved):
        raise ContractError("review_board_source_invalid", "more than one approved image exists for a view")

    columns = max(1, int(columns))
    rows = math.ceil(len(approved) / columns)
    cell_w, cell_h, label_h, gap = 640, 360, 42, 16
    width = columns * cell_w + (columns + 1) * gap
    height = rows * (cell_h + label_h) + (rows + 1) * gap
    board = Image.new("RGB", (width, height), "#15181c")
    draw = ImageDraw.Draw(board)
    for index, (view_id, image_path, attempt_id) in enumerate(approved):
        with Image.open(image_path) as source:
            tile = ImageOps.contain(ImageOps.exif_transpose(source).convert("RGB"), (cell_w, cell_h))
        column = index % columns
        row = index // columns
        x = gap + column * (cell_w + gap)
        y = gap + row * (cell_h + label_h + gap)
        board.paste(tile, (x + (cell_w - tile.width) // 2, y + (cell_h - tile.height) // 2))
        draw.text((x, y + cell_h + 8), f"{view_id} · {attempt_id} · approved", fill="#f3f4f6")
    return board, approved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--columns", type=int, default=2)
    args = parser.parse_args()
    try:
        board, approved = build_board(args.run_root, args.columns)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        board.save(args.output, format="PNG")
    except ImportError:
        print("Pillow is required to build the review board.", file=sys.stderr)
        return 2
    except (ContractError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "output": str(args.output.resolve()), "approved_views": [item[0] for item in approved], "machine_authority": False}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
