#!/usr/bin/env python3
"""Freeze one Scene Canon worker's ordered references into a run-scoped bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path


ASSET_IDS = {"CDM_001", "SRM_001", "COV_001", "COV_002", "COV_003", "SCL_001"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def freeze_bundle(asset_id: str, source_reference_id: str, output: Path, references: list[tuple[str, str | None, Path]]) -> dict:
    if asset_id not in ASSET_IDS:
        raise ValueError(f"unsupported Scene Canon asset id: {asset_id}")
    if not source_reference_id:
        raise ValueError("source reference id is required")
    if not 1 <= len(references) <= 5 or references[0][0] != "source_reference":
        raise ValueError("bundle requires one to five references with source_reference first")
    output = output.resolve()
    reference_root = output.parent / "references"
    if reference_root.is_symlink():
        raise ValueError("run-scoped references directory cannot be a symlink")
    reference_root.mkdir(parents=True, exist_ok=True)
    if any(source.resolve().is_relative_to(reference_root) for _, _, source in references):
        raise ValueError("reference sources must remain outside the destination references directory")
    for stale in reference_root.iterdir():
        if stale.is_dir() and not stale.is_symlink():
            raise ValueError(f"unexpected nested directory in run-scoped references: {stale}")
        stale.unlink()
    entries = []
    for index, (kind, predecessor_id, source) in enumerate(references, 1):
        source = source.resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        if kind == "source_reference":
            if index != 1 or predecessor_id is not None:
                raise ValueError("the only source reference must be index 1")
            alias = "source-scene"
        elif kind == "approved_predecessor":
            if predecessor_id not in ASSET_IDS:
                raise ValueError(f"invalid predecessor asset id: {predecessor_id}")
            alias = predecessor_id.lower()
        else:
            raise ValueError(f"invalid reference kind: {kind}")
        suffix = source.suffix.lower() or ".bin"
        frozen = reference_root / f"{index:02d}-{alias}{suffix}"
        shutil.copyfile(source, frozen)
        entries.append({
            "index": index,
            "alias": alias,
            "kind": kind,
            "source_reference_id": source_reference_id if kind == "source_reference" else None,
            "asset_id": predecessor_id,
            "source_path": str(source),
            "frozen_path": str(frozen.resolve()),
            "size_bytes": frozen.stat().st_size,
            "sha256": sha256_file(frozen),
        })
    digest = hashlib.sha256(json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    manifest = {
        "schema_version": "scene_canon_reference_bundle.v1",
        "asset_id": asset_id,
        "source_reference_id": source_reference_id,
        "ordered_references": entries,
        "ordered_bundle_sha256": digest,
    }
    write_json(output, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--source-reference-id", required=True)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--predecessor", action="append", default=[], metavar="ASSET_ID=PATH")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    references: list[tuple[str, str | None, Path]] = [("source_reference", None, args.source)]
    for raw in args.predecessor:
        asset_id, separator, path = raw.partition("=")
        if not separator:
            parser.error("--predecessor must use ASSET_ID=PATH")
        references.append(("approved_predecessor", asset_id, Path(path)))
    manifest = freeze_bundle(args.asset_id, args.source_reference_id, args.output, references)
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
