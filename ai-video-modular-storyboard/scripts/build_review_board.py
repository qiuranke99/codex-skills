#!/usr/bin/env python3
"""Build a deterministic human-only storyboard review board from independent frames."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

try:
    from PIL import __version__ as PILLOW_VERSION
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required: install with `python3 -m pip install Pillow`") from exc

TOOL_VERSION = "build-review-board.v1"


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def default_columns(count: int) -> int:
    return min(5, max(1, math.ceil(math.sqrt(count * 16 / 9))))


def safe_file(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    path.relative_to(root.resolve())
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_root", type=Path)
    parser.add_argument("--output", type=Path, default=Path("02_review_board/storyboard_review_board.png"))
    parser.add_argument("--metadata", type=Path, default=Path("02_review_board/storyboard_review_board.metadata.json"))
    parser.add_argument("--columns", type=int)
    parser.add_argument("--cell-width", type=int, default=640)
    parser.add_argument("--image-height", type=int, default=360)
    parser.add_argument("--label-height", type=int, default=44)
    parser.add_argument("--padding", type=int, default=16)
    args = parser.parse_args()

    root = args.package_root.resolve()
    data = json.loads((root / "00_manifest" / "STORYBOARD_MANIFEST.json").read_text(encoding="utf-8"))
    frames = sorted(data["frames"], key=lambda item: item["display_order"])
    count = data["script_shot_count"]
    if count != len(frames) or count < 1:
        raise SystemExit("manifest cardinality must be valid before board composition")
    columns = args.columns or default_columns(count)
    if columns < 1:
        raise SystemExit("columns must be positive")
    rows = math.ceil(count / columns)
    for value in (args.cell_width, args.image_height, args.label_height):
        if value < 1:
            raise SystemExit("cell and label dimensions must be positive")
    if args.padding < 0:
        raise SystemExit("padding must be nonnegative")

    board_width = args.padding + columns * (args.cell_width + args.padding)
    board_height = args.padding + rows * (args.image_height + args.label_height + args.padding)
    board = Image.new("RGB", (board_width, board_height), (22, 22, 22))
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default()
    source_hashes: dict[str, str] = {}

    for index, frame in enumerate(frames):
        source = safe_file(root, frame["file_path"])
        actual_hash = file_sha(source)
        if actual_hash != frame["file_sha256"]:
            raise SystemExit(f"source hash mismatch for {frame['shot_uid']}")
        source_hashes[frame["shot_uid"]] = actual_hash
        row, column = divmod(index, columns)
        x = args.padding + column * (args.cell_width + args.padding)
        y = args.padding + row * (args.image_height + args.label_height + args.padding)
        with Image.open(source) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
            contained = ImageOps.contain(image, (args.cell_width, args.image_height), Image.Resampling.LANCZOS)
        image_area = Image.new("RGB", (args.cell_width, args.image_height), (0, 0, 0))
        image_area.paste(contained, ((args.cell_width - contained.width) // 2, (args.image_height - contained.height) // 2))
        board.paste(image_area, (x, y))
        label = f"{frame['display_order']:02d}  {frame['shot_uid']}  {frame['target_duration_seconds']:g}s  v{frame['version']}"
        draw.rectangle((x, y + args.image_height, x + args.cell_width, y + args.image_height + args.label_height), fill=(38, 38, 38))
        draw.text((x + 10, y + args.image_height + 12), label, fill=(238, 238, 238), font=font)

    output = (root / args.output).resolve()
    output.relative_to(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    board.save(output, format="PNG", optimize=False, compress_level=9)
    metadata = {
        "tool_version": TOOL_VERSION,
        "pillow_version": PILLOW_VERSION,
        "board_type": "deterministic_human_review_composite",
        "is_model_input": False,
        "deterministic": True,
        "valid_cell_count": count,
        "cell_shot_uids": [frame["shot_uid"] for frame in frames],
        "source_frame_hashes": source_hashes,
        "layout": {
            "columns": columns,
            "rows": rows,
            "cell_width": args.cell_width,
            "image_height": args.image_height,
            "label_height": args.label_height,
            "padding": args.padding,
        },
        "file_path": str(output.relative_to(root)),
        "file_sha256": file_sha(output),
    }
    metadata_path = (root / args.metadata).resolve()
    metadata_path.relative_to(root)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
