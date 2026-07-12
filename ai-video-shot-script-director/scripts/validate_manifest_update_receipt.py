#!/usr/bin/env python3
"""Validate the shared Project Canon manifest update receipt."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SHA = re.compile(r"^[a-f0-9]{64}$")
FIELDS = {
    "schema_version", "canonical_manifest_locator", "updated_by_skill", "base_manifest_sha256",
    "resulting_manifest_sha256", "registered_artifact_ids", "delta_status",
}


def validate_receipt(
    value: Any,
    expected_skill: str | None = None,
    expected_ids: set[str] | None = None,
    canonical_manifest: Any | None = None,
) -> list[str]:
    if not isinstance(value, dict):
        return ["receipt root must be an object"]
    errors: list[str] = []
    if set(value) != FIELDS:
        errors.append("receipt must contain exact shared fields")
    if value.get("schema_version") != "ai-video-manifest-update-receipt.v1":
        errors.append("invalid receipt schema_version")
    if value.get("canonical_manifest_locator") != "00_project_canon/PROJECT_CANON_MANIFEST.json":
        errors.append("invalid canonical manifest locator")
    owner = value.get("updated_by_skill")
    if not isinstance(owner, str) or not owner:
        errors.append("updated_by_skill must be non-empty")
    if expected_skill is not None and owner != expected_skill:
        errors.append(f"updated_by_skill must equal {expected_skill}")
    for field in ("base_manifest_sha256", "resulting_manifest_sha256"):
        if not isinstance(value.get(field), str) or not SHA.fullmatch(value[field]):
            errors.append(f"{field} must be lowercase SHA-256")
    if value.get("delta_status") != "applied":
        errors.append("delta_status must be applied")
    registered = value.get("registered_artifact_ids")
    if not isinstance(registered, list) or not registered or not all(isinstance(item, str) and item for item in registered):
        errors.append("registered_artifact_ids must be a non-empty string array")
        registered = []
    elif len(registered) != len(set(registered)):
        errors.append("registered_artifact_ids must be unique")
    if expected_ids is not None and set(registered) != expected_ids:
        errors.append("registered_artifact_ids do not match expected owned artifacts")
    if canonical_manifest is not None:
        if not isinstance(canonical_manifest, dict):
            errors.append("canonical manifest must be an object")
        else:
            if value.get("resulting_manifest_sha256") != canonical_manifest.get("sha256"):
                errors.append("resulting_manifest_sha256 must equal canonical manifest sha256")
            if value.get("base_manifest_sha256") != canonical_manifest.get("base_manifest_sha256"):
                errors.append("base_manifest_sha256 must equal canonical manifest base_manifest_sha256")
            if owner != canonical_manifest.get("updated_by_skill"):
                errors.append("updated_by_skill must equal canonical manifest updated_by_skill")
            active = canonical_manifest.get("active_artifacts")
            active_by_id = {
                item.get("artifact_id"): item for item in active if isinstance(item, dict) and isinstance(item.get("artifact_id"), str)
            } if isinstance(active, list) else {}
            for artifact_id in registered:
                entry = active_by_id.get(artifact_id)
                if entry is None:
                    errors.append(f"registered artifact is not active in canonical manifest: {artifact_id}")
                elif entry.get("owner_skill") != owner:
                    errors.append(f"registered artifact owner mismatch in canonical manifest: {artifact_id}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--expected-skill")
    parser.add_argument("--expected-artifact-id", action="append", default=[])
    parser.add_argument("--canonical-manifest", type=Path, help="bind before/after hashes and registered artifacts to the actual canonical registry")
    args = parser.parse_args()
    try:
        value = json.loads(args.receipt.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: receipt unreadable: {exc}")
        return 2
    expected_ids = set(args.expected_artifact_id) if args.expected_artifact_id else None
    canonical_manifest = None
    if args.canonical_manifest is not None:
        try:
            canonical_manifest = json.loads(args.canonical_manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"ERROR: canonical manifest unreadable: {exc}")
            return 2
    errors = validate_receipt(value, args.expected_skill, expected_ids, canonical_manifest)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: manifest update receipt is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
