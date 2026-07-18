#!/usr/bin/env python3
"""Validate only the explicitly selected High-Control aggregate compatibility profile."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable

from suite_common import SuiteConfigurationError, load_distribution, managed_inventory


AI_VIDEO_MEMBERS = (
    "ai-video-shot-script-director",
    "ai-video-global-look-lock",
    "ai-video-modular-storyboard",
    "ai-video-timed-animatic-previs-director",
    "ai-video-keyframe-continuity-pack",
    "ai-video-omni-reference-prompt-director",
)
CANON_OWNERS = (
    "character-casting-lock-board",
    "character-final-lock-board",
    "single-face-character-lock-board",
    "multi-angle-product-identity-lock-board",
    "packaging-product-identity-label-lock-board",
    "material-sensitive-product-master-asset-board",
    "scene-canon-asset-pack",
)
OPTIONAL_EXPLORERS = (
    "cinematic_shot_image_explorer",
    "cinematic_world_builder",
)
AGGREGATE_MEMBERS = AI_VIDEO_MEMBERS + CANON_OWNERS + OPTIONAL_EXPLORERS
DISCOVERY_COPY_MARKER = ".high-control-ai-tvc-owner.json"
SHARED_APPROVALS = ["draft", "assistant_validated", "user_approved", "stale", "blocked"]

PRIMARY_SCHEMAS = {
    "ai-video-shot-script-director": "references/shot_contract.schema.json",
    "ai-video-global-look-lock": "references/global_look_contract.schema.json",
    "ai-video-modular-storyboard": "references/storyboard_manifest.schema.json",
    "ai-video-timed-animatic-previs-director": "references/previs_manifest.schema.json",
    "ai-video-keyframe-continuity-pack": "references/keyframe_manifest.schema.json",
    "ai-video-omni-reference-prompt-director": "references/canonical_ir.schema.json",
}

COMPATIBILITY_MARKERS = {
    "ai-video-shot-script-director": (
        ("references/project_canon_manifest_contract.md", "Apply a delta atomically"),
    ),
    "ai-video-global-look-lock": (
        ("references/global_look_contract.schema.json", "look_state_matrix_id"),
    ),
    "ai-video-modular-storyboard": (
        ("references/storyboard_manifest.schema.json", "is_model_input_eligible"),
    ),
    "ai-video-timed-animatic-previs-director": (
        ("references/provider_runtime_capability_evidence.schema.json", "video_input_constraints"),
    ),
    "ai-video-keyframe-continuity-pack": (
        ("references/keyframe_manifest.schema.json", "forbidden_video_generation_modes"),
    ),
    "ai-video-omni-reference-prompt-director": (
        ("references/canonical_ir.schema.json", "look_state_prompt_full"),
    ),
}

TEST_COMMANDS = (
    ("shot contract", "ai-video-shot-script-director", "scripts/test_contract.py"),
    ("global look", "ai-video-global-look-lock", "scripts/test_contract.py"),
    ("storyboard", "ai-video-modular-storyboard", "scripts/test_contract.py"),
    ("previs", "ai-video-timed-animatic-previs-director", "scripts/test_contract.py"),
    ("keyframe", "ai-video-keyframe-continuity-pack", "scripts/test_contract.py"),
    ("prompt", "ai-video-omni-reference-prompt-director", "scripts/test_contract.py"),
    ("scene canon", "scene-canon-asset-pack", "scripts/test_contract.py"),
    ("schema parity", "high-control-ai-tvc", "tools/validate_schema_parity.py"),
    ("asset Canon bridge", "high-control-ai-tvc", "tools/test_asset_canon_bridge.py"),
    ("global Canon write gate", "high-control-ai-tvc", "tools/test_global_canon_write_gate.py"),
    ("aggregate contract", "high-control-ai-tvc", "tools/test_aggregate_contract.py"),
)


def _walk_json(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda value: value.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if relative == DISCOVERY_COPY_MARKER:
            continue
        if path.is_symlink():
            digest.update(b"L\0" + relative.encode("utf-8") + b"\0" + os.readlink(path).encode("utf-8"))
        elif path.is_file():
            digest.update(b"F\0" + relative.encode("utf-8") + b"\0" + path.read_bytes())
    return digest.hexdigest()


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def _run_test(command: list[str], cwd: Path, timeout_seconds: float = 180) -> tuple[int, str, float]:
    environment = dict(os.environ)
    environment.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    })
    options: dict[str, Any] = {}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="backslashreplace",
        **options,
    )
    try:
        output, _stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        _terminate_process_tree(process)
        output = exc.output or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="backslashreplace")
        raise subprocess.TimeoutExpired(command, timeout_seconds, output=output) from exc
    return process.returncode, output, time.monotonic() - started


def _validate_schema(skill: str, schema_path: Path, errors: list[str]) -> None:
    if not schema_path.is_file():
        errors.append(f"{skill}: aggregate compatibility schema missing: {schema_path.name}")
        return
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"{skill}: aggregate compatibility schema is invalid: {exc}")
        return
    properties = schema.get("properties", {})
    if properties.get("contract_version", {}).get("const") != "ai-video-artifact-v1":
        errors.append(f"{skill}: aggregate contract_version compatibility drift")
    if properties.get("approval_status", {}).get("enum") != SHARED_APPROVALS:
        errors.append(f"{skill}: aggregate approval_status compatibility drift")
    for node in _walk_json(schema):
        required = node.get("required")
        if isinstance(required, list) and set(required) == {"artifact_id", "owner_skill", "version", "sha256"}:
            if node.get("additionalProperties") is not False:
                errors.append(f"{skill}: dependency/artifactRef compatibility permits extra properties")


def validate_aggregate(
    root: Path,
    *,
    run_tests: bool = True,
    require_discovery: bool = False,
    discovery_root: Path | None = None,
) -> list[str]:
    """Return aggregate-only compatibility failures without judging standalone availability."""
    root = root.resolve()
    errors: list[str] = []
    try:
        manifest, _requirements, skills, distribution_errors = load_distribution(root)
    except SuiteConfigurationError as exc:
        return [str(exc)]
    skills, inventory_errors = managed_inventory(manifest, skills, root)
    errors.extend(distribution_errors)
    errors.extend(inventory_errors)
    managed_names = tuple(item["name"] for item in skills)
    if set(managed_names) != set(AGGREGATE_MEMBERS) or len(managed_names) != len(AGGREGATE_MEMBERS):
        errors.append(
            "aggregate member compatibility set differs; "
            f"missing={sorted(set(AGGREGATE_MEMBERS) - set(managed_names))}; "
            f"extra={sorted(set(managed_names) - set(AGGREGATE_MEMBERS))}"
        )
    excluded = set(manifest.get("excluded_from_aggregate_profile", []))
    if excluded & set(managed_names):
        errors.append("aggregate-excluded catalog entries leaked into aggregate managed inventory")

    bridge_tools = root / "high-control-ai-tvc" / "tools"
    for relative in (
        "build_asset_canon_export.py",
        "validate_asset_canon_export.py",
        "test_asset_canon_bridge.py",
        "test_global_canon_write_gate.py",
        "canon_runner_ai_video_shot_script_director.py",
        "canon_runner_ai_video_global_look_lock.py",
        "canon_runner_ai_video_modular_storyboard.py",
        "canon_runner_ai_video_timed_animatic_previs_director.py",
        "canon_runner_ai_video_keyframe_continuity_pack.py",
        "canon_runner_ai_video_omni_reference_prompt_director.py",
    ):
        if not (bridge_tools / relative).is_file():
            errors.append(f"aggregate Canon bridge closure is missing: high-control-ai-tvc/tools/{relative}")

    for name in managed_names:
        package = root / name
        if not package.is_dir() or not (package / "SKILL.md").is_file():
            errors.append(f"{name}: aggregate member package is missing")

    for skill in AI_VIDEO_MEMBERS:
        _validate_schema(skill, root / skill / PRIMARY_SCHEMAS[skill], errors)
        for relative, marker in COMPATIBILITY_MARKERS[skill]:
            path = root / skill / relative
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                errors.append(f"{skill}: cannot read aggregate compatibility marker file {relative}: {exc}")
                continue
            if marker not in text:
                errors.append(f"{skill}: aggregate compatibility marker missing in {relative}: {marker}")

    manifest_schema = root / "ai-video-shot-script-director" / "references" / "project_canon_manifest.schema.json"
    if manifest_schema.is_file():
        try:
            project_schema = json.loads(manifest_schema.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"aggregate Project Canon schema is invalid: {exc}")
        else:
            if project_schema.get("properties", {}).get("dependencies", {}).get("maxItems") != 0:
                errors.append("aggregate PROJECT_CANON_MANIFEST must have zero envelope dependencies")
    else:
        errors.append("aggregate PROJECT_CANON_MANIFEST schema is missing")

    pins: dict[str, str] = {}
    for label, path in (
        ("Shot Director", root / "ai-video-shot-script-director" / "requirements.txt"),
        ("Prompt Director", root / "ai-video-omni-reference-prompt-director" / "requirements.txt"),
        ("Packaging owner", root / "packaging-product-identity-label-lock-board" / "requirements.txt"),
    ):
        if not path.is_file():
            errors.append(f"{label}: aggregate compatibility requirements.txt missing")
            continue
        matches = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip().lower().startswith("pillow") and not line.lstrip().startswith("#")
        ]
        if len(matches) != 1 or not re.fullmatch(r"Pillow==\d+\.\d+\.\d+", matches[0]):
            errors.append(f"{label}: aggregate Pillow compatibility pin must be exact")
        else:
            pins[label] = matches[0]
    if len(pins) == 3 and len(set(pins.values())) != 1:
        errors.append("aggregate Pillow compatibility pins differ")

    if run_tests:
        for label, cwd_relative, script_relative in TEST_COMMANDS:
            cwd = root / cwd_relative
            script = cwd / script_relative
            if not script.is_file():
                errors.append(f"{label}: aggregate regression entrypoint missing: {script.relative_to(root)}")
                continue
            print(f"RUN: {label} aggregate regression", flush=True)
            try:
                code, output, elapsed = _run_test([sys.executable, str(script)], cwd)
            except subprocess.TimeoutExpired as exc:
                timeout_output = exc.output if isinstance(exc.output, str) else ""
                errors.append(f"{label}: aggregate regression timed out: {timeout_output[-1500:].strip()}")
                continue
            if code != 0:
                errors.append(f"{label}: aggregate regression failed (exit {code}): {output[-1500:].strip()}")
            else:
                print(f"PASS: {label} aggregate regression ({elapsed:.3f}s)", flush=True)

    if require_discovery:
        discovery = (discovery_root or (Path.home() / ".agents" / "skills")).expanduser().absolute()
        for name in managed_names:
            entry = discovery / name
            expected = (root / name).resolve()
            if not os.path.lexists(str(entry)):
                errors.append(f"{name}: aggregate discovery entry missing under {discovery}")
            elif entry.resolve() == expected:
                continue
            elif entry.is_dir():
                marker_path = entry / DISCOVERY_COPY_MARKER
                try:
                    marker = json.loads(marker_path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    marker = None
                if not isinstance(marker, dict) or marker.get("skill_name") != name:
                    errors.append(f"{name}: aggregate discovery copy lacks ownership marker")
                elif _tree_digest(entry) != _tree_digest(expected):
                    errors.append(f"{name}: aggregate discovery copy differs from selected source")
            else:
                errors.append(f"{name}: unsupported aggregate discovery entry at {entry}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--require-discovery", action="store_true")
    parser.add_argument("--discovery-root", type=Path)
    args = parser.parse_args()
    try:
        errors = validate_aggregate(
            args.suite_root,
            run_tests=not args.skip_tests,
            require_discovery=args.require_discovery,
            discovery_root=args.discovery_root,
        )
    except Exception as exc:
        print(f"ERROR: aggregate validation could not complete safely: {type(exc).__name__}: {exc}")
        return 2
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        "OK: optional 15-Skill aggregate compatibility profile validated; "
        "standalone package availability was not decided"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
