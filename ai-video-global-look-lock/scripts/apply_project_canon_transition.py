#!/usr/bin/env python3
"""Optionally hand a validated Project Canon transition to an explicit runner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


OWNER = "ai-video-global-look-lock"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"Apply an optional {OWNER} Project Canon handoff without locating sibling packages"
    )
    parser.add_argument(
        "--transition-runner", type=Path,
        help="explicit compatible transition runner; optional unless Canon integration is requested",
    )
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--package-root", required=True, type=Path)
    parser.add_argument("--transaction-id", required=True)
    parser.add_argument("--expected-registered-artifact-id", action="append", required=True)
    parser.add_argument("--preserved-artifact-id", action="append", default=[])
    args = parser.parse_args()
    if args.transition_runner is None:
        print(json.dumps({
            "status": "blocked_missing_project_canon_transition_input",
            "owner_skill": OWNER,
            "missing_input": "transition_runner",
            "required_input_contract": (
                "an explicit Python runner accepting the same project-root, package-root, "
                "transaction-id, expected artifact and preserved artifact arguments"
            ),
            "package_artifact_remains_valid": True,
        }, ensure_ascii=False, sort_keys=True))
        return 3
    runner = args.transition_runner.resolve()
    if not runner.is_file():
        print(json.dumps({
            "status": "blocked_invalid_project_canon_transition_input",
            "owner_skill": OWNER,
            "transition_runner": str(runner),
            "reason": "runner file is missing",
            "package_artifact_remains_valid": True,
        }, ensure_ascii=False, sort_keys=True))
        return 3
    command = [
        sys.executable, str(runner),
        "--project-root", str(args.project_root),
        "--package-root", str(args.package_root),
        "--transaction-id", args.transaction_id,
    ]
    for artifact_id in args.expected_registered_artifact_id:
        command.extend(["--expected-registered-artifact-id", artifact_id])
    for artifact_id in args.preserved_artifact_id:
        command.extend(["--preserved-artifact-id", artifact_id])
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
