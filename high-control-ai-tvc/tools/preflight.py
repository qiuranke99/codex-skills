#!/usr/bin/env python3
"""Fail-closed runtime and installation preflight for the TVC production suite."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from manage_skills import inspect_installation
from release_control import ReleaseControlError, production_check, resolve_target
from suite_common import REPO_ROOT, SuiteConfigurationError, load_distribution, select_skills


def _check(checks: List[Dict[str, Any]], check_id: str, status: str, detail: str, kind: str = "automatic") -> None:
    checks.append({"id": check_id, "kind": kind, "status": status, "detail": detail})


def _command_output(command: List[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 2, str(exc)
    return result.returncode, result.stdout


def evaluate(
    target: Path | None,
    profile: str,
    confirmations: List[str],
    repository_only: bool,
    automatic_only: bool,
) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    active_repo_root = REPO_ROOT
    resolved_target = target
    if not repository_only:
        release_state = production_check(target, profile=profile)
        _check(
            checks,
            "github_latest_release",
            "pass" if release_state["ready_latest"] else "fail",
            f"GitHub main release {release_state.get('release_commit')} is active"
            if release_state["ready_latest"]
            else "; ".join(release_state.get("errors", ["release authority check failed"])),
        )
        if release_state["ready_latest"]:
            active_system_root = Path(release_state["active_system_root"])
            active_repo_root = active_system_root.parent
            resolved_target = Path(release_state["target_root"])
        else:
            resolved_target = resolve_target(target)
    try:
        manifest, requirements, skills, errors = load_distribution(active_repo_root)
    except SuiteConfigurationError as exc:
        manifest, requirements, skills, errors = {}, {}, [], [str(exc)]

    if errors:
        for index, error in enumerate(errors):
            _check(checks, f"distribution_{index + 1}", "fail", error)
    else:
        _check(checks, "distribution", "pass", f"manifest and all {len(skills)} skill directories are coherent")

    if not repository_only:
        installation = inspect_installation(active_repo_root, resolved_target, profile)
        _check(
            checks,
            "skill_installation",
            "pass" if installation["ready"] else "fail",
            "all selected skills have one suite-owned discovery entry"
            if installation["ready"]
            else "; ".join(installation["errors"] or [
                f"{item['name']}={item['state']}" for item in installation["skills"] if item["state"] != "installed"
            ]),
        )

        python_config = requirements.get("python", {})
        tested = python_config.get("tested_major_minor", []) if isinstance(python_config, dict) else []
        current = f"{sys.version_info.major}.{sys.version_info.minor}"
        _check(
            checks,
            "python_version",
            "pass" if current in tested else "fail",
            f"running Python {current}; production-tested versions: {', '.join(tested)}",
        )

        packages = python_config.get("packages", {}) if isinstance(python_config, dict) else {}
        expected_pillow = packages.get("Pillow") if isinstance(packages, dict) else None
        try:
            import PIL  # type: ignore

            actual_pillow = PIL.__version__
        except (ImportError, AttributeError):
            actual_pillow = None
        _check(
            checks,
            "pillow_version",
            "pass" if actual_pillow == expected_pillow else "fail",
            f"Pillow={actual_pillow or 'missing'}; required exact version={expected_pillow}",
        )

        for executable in requirements.get("executables", []):
            if not isinstance(executable, dict) or not isinstance(executable.get("name"), str):
                _check(checks, "executable_config", "fail", "runtime executable configuration is invalid")
                continue
            name = executable["name"]
            path = shutil.which(name)
            _check(
                checks,
                f"executable_{name}",
                "pass" if path else "fail",
                f"{name}={path or 'not found in PATH'}",
            )

        ffmpeg_path = shutil.which("ffmpeg")
        required_encoders = requirements.get("ffmpeg_required_encoders", [])
        if ffmpeg_path and isinstance(required_encoders, list):
            code, output = _command_output([ffmpeg_path, "-hide_banner", "-encoders"])
            missing = [encoder for encoder in required_encoders if encoder not in output]
            _check(
                checks,
                "ffmpeg_encoders",
                "pass" if code == 0 and not missing else "fail",
                "required encoders available" if code == 0 and not missing else "missing: " + ", ".join(missing),
            )

        if platform.system() == "Windows":
            _check(
                checks,
                "legacy_doc_windows",
                "warn",
                "legacy .doc/.rtf is not portable here; save it as .docx before ingestion",
            )

        if not automatic_only:
            confirmed = set(confirmations)
            manual_gates = requirements.get("manual_gates", [])
            for gate in manual_gates if isinstance(manual_gates, list) else []:
                if not isinstance(gate, dict) or not isinstance(gate.get("id"), str):
                    _check(checks, "manual_gate_config", "fail", "manual gate configuration is invalid")
                    continue
                gate_id = gate["id"]
                _check(
                    checks,
                    gate_id,
                    "pass" if gate_id in confirmed else "needs_confirmation",
                    str(gate.get("description", gate_id)),
                    kind="manual",
                )

    failures = [item for item in checks if item["status"] == "fail"]
    pending = [item for item in checks if item["status"] == "needs_confirmation"]
    ready = not failures and not pending and not repository_only
    return {
        "schema_version": "1.0.0",
        "suite_id": manifest.get("suite_id", "high-control-ai-tvc-production-system"),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "target_root": str(resolved_target.expanduser().absolute()) if resolved_target is not None else None,
        "profile": profile,
        "repository_only": repository_only,
        "automatic_only": automatic_only,
        "ready": ready,
        "production_ready": ready,
        "result": "ready_latest" if ready else (
            "repository_valid" if repository_only and not failures else (
                "needs_manual_confirmation" if not failures else "not_ready"
            )
        ),
        "checks": checks,
    }


def _print_text(result: Dict[str, Any]) -> None:
    for item in result["checks"]:
        symbols = {"pass": "OK", "warn": "WARN", "fail": "FAIL", "needs_confirmation": "CONFIRM"}
        print(f"[{symbols[item['status']]}] {item['id']}: {item['detail']}")
    print(result["result"].upper())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path)
    parser.add_argument("--profile", choices=("all", "core"), default="all")
    parser.add_argument("--confirm", action="append", default=[], metavar="GATE_ID")
    parser.add_argument("--automatic-only", action="store_true")
    parser.add_argument("--repository-only", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()

    try:
        result = evaluate(
            args.target,
            args.profile,
            args.confirm,
            args.repository_only,
            args.automatic_only,
        )
    except (ReleaseControlError, SuiteConfigurationError, OSError) as exc:
        if args.format == "json":
            print(json.dumps({"ready": False, "result": "not_ready", "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_text(result)
    return 0 if result["ready"] or result["result"] == "repository_valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
