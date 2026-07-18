#!/usr/bin/env python3
"""Freeze fully decoded material references as material_reference_bundle.v2."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from material_contract import (
    ALIAS_RE,
    MaterialContractError,
    canonical_json_bytes,
    create_only_bytes,
    inspect_image_bytes,
    normalized_path,
    pretty_json_bytes,
    require_exact_path,
    require_inside,
    sha256_bytes,
)


def parse_reference(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise MaterialContractError(
            "blocked_reference_bundle_argument",
            f"reference must use alias=path syntax: {value!r}",
        )
    alias, raw_path = value.split("=", 1)
    if not ALIAS_RE.fullmatch(alias):
        raise MaterialContractError(
            "blocked_reference_bundle_alias", f"invalid reference alias: {alias!r}"
        )
    source = Path(raw_path).expanduser().resolve(strict=False)
    if not source.is_file():
        raise MaterialContractError(
            "blocked_reference_materialization", f"reference file not found: {source}"
        )
    return alias, source.resolve(strict=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument(
        "--reference",
        action="append",
        required=True,
        help="Ordered alias=path entry; repeat once per unique source image",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_dir = args.run_dir.expanduser().resolve(strict=False)
    manifest_path = require_exact_path(
        args.manifest,
        run_dir / "sources" / "reference-manifest.json",
        "blocked_reference_bundle_location",
        "reference manifest",
    )
    reference_dir = (run_dir / "sources" / "references").resolve(strict=False)
    require_inside(
        run_dir,
        reference_dir,
        "blocked_reference_bundle_location",
        "reference directory",
    )

    parsed = [parse_reference(item) for item in args.reference]
    aliases = [alias for alias, _ in parsed]
    realpaths = [normalized_path(path) for _, path in parsed]
    if len(set(aliases)) != len(aliases):
        raise MaterialContractError(
            "blocked_reference_bundle_alias", "reference aliases must be unique"
        )
    if len(set(realpaths)) != len(realpaths):
        raise MaterialContractError(
            "blocked_reference_bundle_duplicate_source",
            "each source realpath may appear only once",
        )

    # Decode and validate every input before creating any run-scoped path.
    prepared: list[dict[str, Any]] = []
    source_hashes: list[str] = []
    for index, (alias, source) in enumerate(parsed, 1):
        data = source.read_bytes()
        metadata = inspect_image_bytes(
            data,
            code="blocked_reference_image_invalid",
            label=f"reference {alias}",
        )
        source_sha = sha256_bytes(data)
        destination = reference_dir / (
            f"{index:02d}_{alias}{metadata['canonical_suffix']}"
        )
        destination = require_exact_path(
            destination,
            reference_dir / f"{index:02d}_{alias}{metadata['canonical_suffix']}",
            "blocked_reference_bundle_location",
            f"frozen reference destination {alias}",
        )
        entry = {
            "index": index,
            "alias": alias,
            "source_realpath": str(source),
            "frozen_path": str(destination),
            "size_bytes": len(data),
            "sha256": source_sha,
            **metadata,
        }
        prepared.append({"data": data, "destination": destination, "entry": entry})
        source_hashes.append(source_sha)
    if len(set(source_hashes)) != len(source_hashes):
        raise MaterialContractError(
            "blocked_reference_bundle_duplicate_source",
            "byte-identical duplicate sources are forbidden; bind multiple roles to one alias",
        )

    entries = [item["entry"] for item in prepared]
    manifest = {
        "schema_version": "material_reference_bundle.v2",
        "immutability_contract": "create_only_idempotent;resolver_and_builder_rehash_required",
        "run_dir_realpath": str(run_dir),
        "reference_root_realpath": str(reference_dir),
        "ordered_references": entries,
        "ordered_bundle_sha256": sha256_bytes(canonical_json_bytes(entries)),
    }
    manifest_bytes = pretty_json_bytes(manifest)

    # Preflight conflicts before the first write. Exact bytes are an idempotent rerun.
    if manifest_path.exists() and (
        not manifest_path.is_file() or manifest_path.read_bytes() != manifest_bytes
    ):
        raise MaterialContractError(
            "blocked_reference_bundle_manifest_conflict",
            f"create-only manifest exists with different bytes: {manifest_path}",
        )
    for item in prepared:
        destination = item["destination"]
        if destination.exists() and (
            not destination.is_file() or destination.read_bytes() != item["data"]
        ):
            raise MaterialContractError(
                "blocked_reference_bundle_destination_conflict",
                f"create-only frozen destination exists with different bytes: {destination}",
            )

    reference_dir.mkdir(parents=True, exist_ok=True)
    reference_dir = require_inside(
        run_dir,
        reference_dir.resolve(strict=True),
        "blocked_reference_bundle_location",
        "reference directory realpath",
    )
    if reference_dir != Path(manifest["reference_root_realpath"]):
        raise MaterialContractError(
            "blocked_reference_bundle_location",
            "reference directory realpath changed during creation",
        )

    created: list[Path] = []
    try:
        for item in prepared:
            if create_only_bytes(
                item["destination"],
                item["data"],
                code="blocked_reference_bundle_destination_conflict",
                idempotent=True,
            ):
                created.append(item["destination"])
        if create_only_bytes(
            manifest_path,
            manifest_bytes,
            code="blocked_reference_bundle_manifest_conflict",
            idempotent=True,
        ):
            created.append(manifest_path)
    except BaseException:
        # Roll back only files this invocation created; pre-existing idempotent bytes remain.
        for path in reversed(created):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise

    # Full readback proves the persisted bytes, not only the prepared in-memory values.
    if manifest_path.read_bytes() != manifest_bytes:
        raise MaterialContractError(
            "blocked_reference_bundle_copy_mismatch", "manifest readback mismatch"
        )
    for item in prepared:
        frozen = item["destination"].read_bytes()
        if frozen != item["data"]:
            raise MaterialContractError(
                "blocked_reference_bundle_copy_mismatch",
                f"frozen reference readback mismatch: {item['destination']}",
            )
        inspect_image_bytes(
            frozen,
            code="blocked_reference_bundle_copy_mismatch",
            label=f"frozen reference {item['entry']['alias']}",
        )

    print(
        json.dumps(
            {
                "ok": True,
                "schema_version": manifest["schema_version"],
                "manifest_path": str(manifest_path),
                "manifest_sha256": sha256_bytes(manifest_bytes),
                "ordered_bundle_sha256": manifest["ordered_bundle_sha256"],
                "reference_count": len(entries),
                "frozen_paths": [entry["frozen_path"] for entry in entries],
                "idempotent": not created,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MaterialContractError as exc:
        print(
            json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}),
            file=sys.stderr,
        )
        raise SystemExit(2)
    except OSError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_code": "blocked_reference_bundle_filesystem",
                    "detail": str(exc),
                }
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)
