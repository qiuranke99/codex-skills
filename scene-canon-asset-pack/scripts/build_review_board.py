#!/usr/bin/env python3
"""Compose a human-only review board from approved independent scene assets."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a review board without cropping machine assets.")
    parser.add_argument("manifest", type=Path, help="Path to ASSET_MANIFEST.json")
    parser.add_argument("output", type=Path, help="Output PNG path")
    parser.add_argument("--columns", type=int, default=3)
    args = parser.parse_args()

    try:
        from PIL import Image, ImageDraw, ImageOps
    except ImportError:
        print("Pillow is required to compose the human review board.", file=sys.stderr)
        return 2

    manifest_path = args.manifest.resolve()
    package_root = manifest_path.parents[1]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected = [
        asset
        for asset in manifest.get("assets", [])
        if asset.get("is_machine_asset")
        and asset.get("assistant_qa_status") == "approved"
        and asset.get("independently_generated") is True
        and asset.get("derived_from_multipanel") is False
    ]
    if not selected:
        print("No approved independent machine assets are available.", file=sys.stderr)
        return 1

    columns = max(1, args.columns)
    rows = math.ceil(len(selected) / columns)
    cell_w, cell_h, label_h, gap = 640, 360, 34, 16
    board = Image.new("RGB", (columns * cell_w + (columns + 1) * gap, rows * (cell_h + label_h) + (rows + 1) * gap), "#17191b")
    draw = ImageDraw.Draw(board)

    for index, asset in enumerate(selected):
        image_path = package_root / asset["file_path"]
        with Image.open(image_path) as source:
            tile = ImageOps.contain(source.convert("RGB"), (cell_w, cell_h))
        column = index % columns
        row = index // columns
        x = gap + column * (cell_w + gap)
        y = gap + row * (cell_h + label_h + gap)
        board.paste(tile, (x + (cell_w - tile.width) // 2, y + (cell_h - tile.height) // 2))
        draw.text((x, y + cell_h + 7), f"{asset['asset_id']} · {asset['asset_name']}", fill="#f3f3f3")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    board.save(args.output, format="PNG")
    print(f"wrote human review board: {args.output}")
    print(f"approved source asset count: {len(selected)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
