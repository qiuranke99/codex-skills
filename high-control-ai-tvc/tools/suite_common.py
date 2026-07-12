#!/usr/bin/env python3
"""Shared, dependency-free distribution helpers for the TVC skill suite."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


SUBSYSTEM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SUBSYSTEM_ROOT.parent
MANIFEST_PATH = SUBSYSTEM_ROOT / "SUITE_MANIFEST.json"
RUNTIME_REQUIREMENTS_PATH = SUBSYSTEM_ROOT / "config" / "runtime-requirements.json"
DEFAULT_SUITE_ID = "high-control-ai-tvc-production-system"
VALID_TIERS = {"core", "optional"}


class SuiteConfigurationError(RuntimeError):
    """Raised when the checked-out distribution is not internally coherent."""


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SuiteConfigurationError(f"required file is missing: {path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SuiteConfigurationError(f"cannot read valid UTF-8 JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SuiteConfigurationError(f"JSON root must be an object: {path}")
    return value


def suite_id_from_manifest(manifest: Dict[str, Any]) -> str:
    raw = manifest.get("suite_id", DEFAULT_SUITE_ID)
    if not isinstance(raw, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,79}", raw):
        raise SuiteConfigurationError("SUITE_MANIFEST.json suite_id must be a lowercase slug")
    return raw


def load_distribution(
    repo_root: Path = REPO_ROOT,
) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, str]], List[str]]:
    """Load the two SSOT files and return normalized skills plus validation errors."""
    subsystem_root = repo_root / "high-control-ai-tvc"
    manifest_path = subsystem_root / "SUITE_MANIFEST.json"
    requirements_path = subsystem_root / "config" / "runtime-requirements.json"
    manifest = read_json(manifest_path)
    requirements = read_json(requirements_path)
    errors: List[str] = []

    raw_skills = manifest.get("skills")
    skills: List[Dict[str, str]] = []
    seen = set()
    if not isinstance(raw_skills, list):
        errors.append("SUITE_MANIFEST.json skills must be an array")
        raw_skills = []
    for index, item in enumerate(raw_skills):
        if not isinstance(item, dict):
            errors.append(f"skills[{index}] must be an object")
            continue
        name = item.get("name")
        tier = item.get("tier")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name):
            errors.append(f"skills[{index}].name is not a valid skill directory name")
            continue
        if name in seen:
            errors.append(f"duplicate skill name in manifest: {name}")
            continue
        seen.add(name)
        if tier not in VALID_TIERS:
            errors.append(f"{name}: tier must be core or optional")
            continue
        skills.append({"name": name, "tier": tier})

        skill_root = repo_root / name
        if not skill_root.is_dir():
            errors.append(f"{name}: skill directory is missing")
        elif not (skill_root / "SKILL.md").is_file():
            errors.append(f"{name}: SKILL.md is missing")

    expected = requirements.get("expected_distribution")
    if not isinstance(expected, dict):
        errors.append("runtime requirements expected_distribution must be an object")
    else:
        counts = {
            "skill_count": len(skills),
            "core_skill_count": sum(skill["tier"] == "core" for skill in skills),
            "optional_skill_count": sum(skill["tier"] == "optional" for skill in skills),
        }
        for key, actual in counts.items():
            wanted = expected.get(key)
            if wanted != actual:
                errors.append(f"distribution {key} is {actual}, expected {wanted}")

    try:
        suite_id_from_manifest(manifest)
    except SuiteConfigurationError as exc:
        errors.append(str(exc))

    return manifest, requirements, skills, errors


def select_skills(skills: List[Dict[str, str]], profile: str) -> List[Dict[str, str]]:
    if profile == "all":
        return list(skills)
    if profile == "core":
        return [skill for skill in skills if skill["tier"] == "core"]
    raise SuiteConfigurationError(f"unsupported install profile: {profile}")


def discovery_roots() -> Tuple[Path, Path]:
    """Return the official user root followed by the legacy Codex root."""
    return Path.home() / ".agents" / "skills", Path.home() / ".codex" / "skills"


def other_known_discovery_root(target: Path) -> Path | None:
    official, legacy = discovery_roots()
    normalized = os.path.normcase(str(target.expanduser().resolve(strict=False)))
    official_identity = os.path.normcase(str(official.expanduser().resolve(strict=False)))
    legacy_identity = os.path.normcase(str(legacy.expanduser().resolve(strict=False)))
    if normalized == official_identity:
        return legacy
    if normalized == legacy_identity:
        return official
    return None
