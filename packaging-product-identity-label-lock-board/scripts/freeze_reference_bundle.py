#!/usr/bin/env python3
"""Copy ordered source references into one run-scoped, hash-locked bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any


ALIAS_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class BundleError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_reference(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise BundleError(
            "blocked_reference_bundle_argument",
            f"reference must use alias=path syntax: {value!r}",
        )
    alias, raw_path = value.split("=", 1)
    if not ALIAS_RE.fullmatch(alias):
        raise BundleError(
            "blocked_reference_bundle_alias",
            f"invalid reference alias {alias!r}; use lowercase letters, digits, and underscores",
        )
    path = Path(raw_path).expanduser().resolve()
    if not path.is_file():
        raise BundleError("blocked_reference_materialization", f"reference file not found: {path}")
    return alias, path


def safe_suffix(path: Path) -> str:
    suffix = path.suffix.lower()
    if not suffix or not re.fullmatch(r"\.[a-z0-9]{1,10}", suffix):
        return ".bin"
    return suffix


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument(
        "--reference",
        action="append",
        required=True,
        help="Ordered alias=absolute-or-local-path entry; repeat once per unique source file",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    manifest_path = args.manifest.expanduser().resolve()
    if manifest_path.parent != run_dir:
        raise BundleError(
            "blocked_reference_bundle_location",
            "reference manifest must live directly inside the run directory",
        )

    parsed = [parse_reference(value) for value in args.reference]
    aliases = [alias for alias, _ in parsed]
    normalized_sources = [os.path.normcase(os.path.abspath(path)) for _, path in parsed]
    if len(set(aliases)) != len(aliases):
        raise BundleError("blocked_reference_bundle_alias", "reference aliases must be unique")
    if len(set(normalized_sources)) != len(normalized_sources):
        raise BundleError(
            "blocked_reference_bundle_duplicate_source",
            "list each unique source file once; bind multiple source roles to one alias in the prompt ledger",
        )

    reference_dir = run_dir / "references"
    reference_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    for index, (alias, source) in enumerate(parsed, 1):
        source_bytes = source.read_bytes()
        source_sha = sha256_bytes(source_bytes)
        destination = reference_dir / f"{index:02d}_{alias}{safe_suffix(source)}"
        if destination.exists():
            if sha256_bytes(destination.read_bytes()) != source_sha:
                raise BundleError(
                    "blocked_reference_bundle_destination_conflict",
                    f"frozen destination exists with different bytes: {destination}",
                )
        else:
            shutil.copy2(source, destination)
        frozen_bytes = destination.read_bytes()
        frozen_sha = sha256_bytes(frozen_bytes)
        if frozen_sha != source_sha:
            raise BundleError(
                "blocked_reference_bundle_copy_mismatch",
                f"frozen reference differs from source: {destination}",
            )
        entries.append(
            {
                "index": index,
                "alias": alias,
                "frozen_path": str(destination),
                "size_bytes": len(frozen_bytes),
                "sha256": frozen_sha,
            }
        )

    digest_payload = json.dumps(entries, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )
    manifest = {
        "schema_version": "packaging_reference_bundle.v1",
        "immutability_contract": "no_writes_after_freeze; resolver_rehash_required",
        "ordered_references": entries,
        "ordered_bundle_sha256": sha256_bytes(digest_payload),
    }
    write_json(manifest_path, manifest)
    result = {
        "ok": True,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
        "ordered_bundle_sha256": manifest["ordered_bundle_sha256"],
        "reference_count": len(entries),
        "frozen_paths": [entry["frozen_path"] for entry in entries],
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BundleError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}), file=sys.stderr)
        raise SystemExit(2)
    except OSError as exc:
        print(
            json.dumps({"ok": False, "error_code": "blocked_reference_bundle_filesystem", "detail": str(exc)}),
            file=sys.stderr,
        )
        raise SystemExit(2)
