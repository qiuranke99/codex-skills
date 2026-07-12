#!/usr/bin/env python3
"""Validate one owner-produced ai-video asset sidecar and optional Canon binding."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from build_asset_canon_export import validate_export_record
from validate_project_canon_manifest import validate_manifest, verify_artifact_files


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )
    if not isinstance(value, dict):
        raise ValueError(f"{path} root must be an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--canonical-manifest", type=Path)
    args = parser.parse_args()
    try:
        record = _load(args.record)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: asset export record unreadable: {exc}")
        return 2
    errors = validate_export_record(record, args.project_root)
    if args.canonical_manifest is not None:
        try:
            manifest = _load(args.canonical_manifest)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            print(f"ERROR: canonical manifest unreadable: {exc}")
            return 2
        errors.extend(validate_manifest(manifest))
        errors.extend(verify_artifact_files(manifest, args.project_root))
        active = manifest.get("active_artifacts")
        entries = [
            item for item in active if isinstance(item, dict) and item.get("artifact_id") == record.get("artifact_id")
        ] if isinstance(active, list) else []
        if len(entries) != 1:
            errors.append("record must have exactly one active Canon entry")
        else:
            entry = entries[0]
            for field in (
                "artifact_id", "owner_skill", "version", "sha256", "approval_status",
                "dependencies", "affected_shot_uids", "stale_reason",
            ):
                if entry.get(field) != record.get(field):
                    errors.append(f"Canon entry {field} differs from owner artifact record")
            if entry.get("locator") != record.get("primary_asset", {}).get("locator"):
                errors.append("Canon entry locator differs from owner primary asset")
            if entry.get("file_sha256") != record.get("primary_asset", {}).get("file_sha256"):
                errors.append("Canon entry file_sha256 differs from owner primary asset")
            try:
                expected_record_file_hash = hashlib.sha256(args.record.read_bytes()).hexdigest()
                record_locator = str(args.record.resolve().relative_to(args.project_root.resolve()))
            except (OSError, ValueError) as exc:
                errors.append(f"record path is outside project root or unreadable: {exc}")
            else:
                if entry.get("artifact_record_locator") != record_locator:
                    errors.append("Canon entry artifact_record_locator differs from validated record path")
                if entry.get("artifact_record_file_sha256") != expected_record_file_hash:
                    errors.append("Canon entry artifact_record_file_sha256 differs from validated record bytes")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: fixed-owner AI-video asset export is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
