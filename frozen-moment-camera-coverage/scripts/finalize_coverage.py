#!/usr/bin/env python3
"""Atomically finalize a complete or honest partial frozen-coverage delivery."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from validate_coverage_package import ContractError, read_json, validate_package


def write_bytes_atomic(path: Path, value: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_bytes(value)
    os.replace(temporary, path)


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    write_bytes_atomic(path, (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def finalize(run_root: Path, terminal: str) -> dict[str, Any]:
    root = run_root.resolve()
    manifest_path = root / "00_manifest" / "COVERAGE_MANIFEST.json"
    original = manifest_path.read_bytes()
    manifest = read_json(manifest_path, "package_manifest_invalid")
    validate_package(root, "state")
    required = [view["view_id"] for view in manifest["views"] if view.get("required")]
    approved = list(manifest["qa"].get("approved_required_view_ids", []))
    transitions: list[str] = [str(manifest.get("state", {}).get("current"))]
    if terminal == "package_ready":
        if approved != required:
            raise ContractError("premature_package_ready", "every required view must be approved before package_ready")
        allowed_starts = ("all_required_views_approved", "coverage_approved", "handoff_finalized")
        current = manifest.get("state", {}).get("current")
        if current not in allowed_starts:
            raise ContractError("state_transition_invalid", "package finalization must start from the approved coverage sequence")
    elif terminal == "partial_handoff_ready":
        if not approved or approved == required:
            raise ContractError("partial_state_invalid", "partial delivery requires some but not all required views")
        if manifest.get("state", {}).get("current") != "blocked_attempt_budget":
            raise ContractError("state_transition_invalid", "partial finalization must start from blocked_attempt_budget")
        remaining = [view_id for view_id in required if view_id not in approved]
        exhausted: dict[str, list[str]] = {}
        for view_id in remaining:
            attempts = [item for item in manifest["attempts"] if item.get("view_id") == view_id]
            if len(attempts) < manifest["job"]["max_attempts_per_view"]:
                raise ContractError("partial_state_invalid", f"required view has unspent attempt budget: {view_id}")
            exhausted[view_id] = ["blocked_attempt_budget"]
        manifest["qa"]["blocked_view_reasons"] = exhausted
    else:
        raise ContractError("delivery_terminal_invalid", f"unsupported terminal: {terminal}")
    try:
        if terminal == "package_ready":
            phase_order = ["all_required_views_approved", "coverage_approved", "handoff_finalized"]
            start_index = phase_order.index(manifest["state"]["current"])
            for phase in phase_order[start_index + 1 :]:
                manifest["state"] = {"current": phase, "terminal_state": None}
                write_json_atomic(manifest_path, manifest)
                validate_package(root, "state")
                transitions.append(phase)
        manifest["state"] = {"current": terminal, "terminal_state": terminal}
        write_json_atomic(manifest_path, manifest)
        evidence = validate_package(root, "delivery")
        transitions.append(terminal)
    except Exception:
        write_bytes_atomic(manifest_path, original)
        raise
    return {**evidence, "transitions": transitions}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--terminal", choices=("package_ready", "partial_handoff_ready"), required=True)
    args = parser.parse_args()
    try:
        result = finalize(args.run_root, args.terminal)
    except (ContractError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        code = exc.code if isinstance(exc, ContractError) else "delivery_finalize_failed"
        print(json.dumps({"ok": False, "error_code": code, "detail": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
