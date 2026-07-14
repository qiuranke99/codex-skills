#!/usr/bin/env python3
"""Compile a frozen source ledger into at most five imagegen-bound references."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


PROVIDER_MAX_REFERENCES = 5
DIRECT_ANCHOR_COUNT = 3
SHEET_SIZE = 2048
GUTTER = 24


class PackError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackError("blocked_generation_reference_manifest", f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PackError("blocked_generation_reference_manifest", f"expected one JSON object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def verified_entries(manifest_path: Path) -> list[dict[str, Any]]:
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != "packaging_reference_bundle.v1":
        raise PackError("blocked_generation_reference_manifest", "unsupported source reference manifest schema")
    entries = manifest.get("ordered_references")
    if not isinstance(entries, list) or not entries:
        raise PackError("blocked_generation_reference_count", "source reference manifest must contain at least one entry")
    verified: list[dict[str, Any]] = []
    aliases: set[str] = set()
    for expected_index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            raise PackError("blocked_generation_reference_manifest", "source reference entry is not an object")
        alias = entry.get("alias")
        if not isinstance(alias, str) or not alias or alias in aliases:
            raise PackError("blocked_generation_reference_manifest", "source reference aliases must be unique strings")
        aliases.add(alias)
        if entry.get("index") != expected_index:
            raise PackError("blocked_generation_reference_order", "source references must keep contiguous one-based order")
        path = Path(str(entry.get("frozen_path", ""))).expanduser().resolve()
        if not path.is_file():
            raise PackError("blocked_reference_materialization", f"frozen source is missing: {path}")
        data = path.read_bytes()
        digest = sha256_bytes(data)
        if digest != entry.get("sha256"):
            raise PackError("blocked_reference_hash_mismatch", f"frozen source hash mismatch: {path}")
        verified.append({"index": expected_index, "alias": alias, "path": path, "sha256": digest})
    return verified


def split_balanced(entries: list[dict[str, Any]], group_count: int) -> list[list[dict[str, Any]]]:
    quotient, remainder = divmod(len(entries), group_count)
    groups: list[list[dict[str, Any]]] = []
    cursor = 0
    for index in range(group_count):
        size = quotient + (1 if index < remainder else 0)
        groups.append(entries[cursor : cursor + size])
        cursor += size
    return [group for group in groups if group]


def fit_image(source: Image.Image, width: int, height: int) -> Image.Image:
    image = ImageOps.exif_transpose(source).convert("RGB")
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    tile = Image.new("RGB", (width, height), (248, 248, 248))
    x = (width - image.width) // 2
    y = (height - image.height) // 2
    tile.paste(image, (x, y))
    return tile


def build_sheet(group: list[dict[str, Any]], destination: Path) -> list[dict[str, Any]]:
    count = len(group)
    columns = 1 if count == 1 else min(2, math.ceil(math.sqrt(count)))
    rows = math.ceil(count / columns)
    cell_width = (SHEET_SIZE - GUTTER * (columns + 1)) // columns
    cell_height = (SHEET_SIZE - GUTTER * (rows + 1)) // rows
    if cell_width < 128 or cell_height < 128:
        raise PackError(
            "blocked_generation_reference_sheet_capacity",
            f"too many detail references for a useful two-sheet provider pack: {count}",
        )
    canvas = Image.new("RGB", (SHEET_SIZE, SHEET_SIZE), (248, 248, 248))
    cells: list[dict[str, Any]] = []
    for index, entry in enumerate(group):
        row, column = divmod(index, columns)
        left = GUTTER + column * (cell_width + GUTTER)
        top = GUTTER + row * (cell_height + GUTTER)
        box = [left, top, left + cell_width, top + cell_height]
        with Image.open(entry["path"]) as source:
            tile = fit_image(source, cell_width, cell_height)
        canvas.paste(tile, (left, top))
        cells.append(
            {
                "source_alias": entry["alias"],
                "source_sha256": entry["sha256"],
                "target_box": box,
            }
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    canvas.save(temporary, format="PNG", optimize=False, compress_level=6)
    os.replace(temporary, destination)
    return cells


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source_manifest = args.reference_manifest.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    manifest_path = args.manifest.expanduser().resolve()
    run_dir = source_manifest.parent
    if not output_dir.is_relative_to(run_dir) or manifest_path.parent != output_dir:
        raise PackError(
            "blocked_generation_reference_location",
            "provider pack output and manifest must live inside the frozen run directory",
        )
    entries = verified_entries(source_manifest)
    provider_entries: list[dict[str, Any]] = []
    if len(entries) <= PROVIDER_MAX_REFERENCES:
        for provider_index, entry in enumerate(entries, 1):
            provider_entries.append(
                {
                    "provider_index": provider_index,
                    "role": "direct_source",
                    "provider_path": str(entry["path"]),
                    "provider_sha256": entry["sha256"],
                    "source_aliases": [entry["alias"]],
                    "cells": [],
                }
            )
    else:
        anchors = entries[:DIRECT_ANCHOR_COUNT]
        details = entries[DIRECT_ANCHOR_COUNT:]
        sheet_slots = PROVIDER_MAX_REFERENCES - len(anchors)
        for provider_index, entry in enumerate(anchors, 1):
            provider_entries.append(
                {
                    "provider_index": provider_index,
                    "role": "direct_anchor",
                    "provider_path": str(entry["path"]),
                    "provider_sha256": entry["sha256"],
                    "source_aliases": [entry["alias"]],
                    "cells": [],
                }
            )
        for sheet_index, group in enumerate(split_balanced(details, sheet_slots), 1):
            destination = output_dir / f"provider-detail-sheet-{sheet_index:02d}.png"
            cells = build_sheet(group, destination)
            provider_entries.append(
                {
                    "provider_index": len(provider_entries) + 1,
                    "role": "detail_sheet",
                    "provider_path": str(destination),
                    "provider_sha256": sha256_bytes(destination.read_bytes()),
                    "source_aliases": [entry["alias"] for entry in group],
                    "cells": cells,
                }
            )
    if not 1 <= len(provider_entries) <= PROVIDER_MAX_REFERENCES:
        raise PackError(
            "blocked_generation_reference_count",
            f"provider submission requires 1-{PROVIDER_MAX_REFERENCES} references, got {len(provider_entries)}",
        )
    provider_digest = sha256_bytes(
        json.dumps(provider_entries, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    manifest = {
        "schema_version": "packaging_generation_reference_pack.v1",
        "source_reference_manifest_path": str(source_manifest),
        "source_reference_manifest_sha256": sha256_bytes(source_manifest.read_bytes()),
        "source_reference_count": len(entries),
        "provider_reference_limit": PROVIDER_MAX_REFERENCES,
        "provider_reference_count": len(provider_entries),
        "provider_bundle_sha256": provider_digest,
        "provider_order_contract": "pass provider_path values exactly in provider_index order",
        "provider_references": provider_entries,
    }
    write_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                "ok": True,
                "manifest_path": str(manifest_path),
                "source_reference_count": len(entries),
                "provider_reference_count": len(provider_entries),
                "provider_paths": [entry["provider_path"] for entry in provider_entries],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PackError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}), file=sys.stderr)
        raise SystemExit(2)
    except OSError as exc:
        print(
            json.dumps({"ok": False, "error_code": "blocked_generation_reference_filesystem", "detail": str(exc)}),
            file=sys.stderr,
        )
        raise SystemExit(2)
