#!/usr/bin/env python3
"""Shared, dependency-free helpers for the optional TVC aggregate profile."""

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
    """Load aggregate-profile metadata and return normalized members plus errors."""
    subsystem_root = repo_root / "high-control-ai-tvc"
    manifest_path = subsystem_root / "SUITE_MANIFEST.json"
    requirements_path = subsystem_root / "config" / "runtime-requirements.json"
    manifest = read_json(manifest_path)
    requirements = read_json(requirements_path)
    errors: List[str] = []

    required_profile_metadata = {
        "profile_scope": "optional_aggregate_compatibility_and_maintenance",
        "opt_in_required": True,
        "controls_individual_skill_availability": False,
        "managed_inventory_policy": "skills_only",
    }
    for key, expected_value in required_profile_metadata.items():
        if manifest.get(key) != expected_value:
            errors.append(f"SUITE_MANIFEST.json {key} must be {expected_value!r}")
    standalone_package_count = manifest.get("standalone_package_count")
    if not isinstance(standalone_package_count, int) or standalone_package_count < 1:
        errors.append("SUITE_MANIFEST.json standalone_package_count must be a positive integer")
    if requirements.get("scope") != "optional_aggregate_profile":
        errors.append("runtime requirements scope must be optional_aggregate_profile")
    if requirements.get("controls_individual_skill_availability") is not False:
        errors.append("runtime requirements must not control individual Skill availability")

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


def managed_inventory(
    manifest: Dict[str, Any],
    suite_skills: List[Dict[str, str]],
    repo_root: Path = REPO_ROOT,
) -> Tuple[List[Dict[str, str]], List[str]]:
    """Return opt-in aggregate members and validate packages excluded from this profile.

    Every top-level Skill remains independently installable.  The exclusion
    catalog says only that this optional aggregate profile does not manage the
    listed package; it is not an inventory of the repository's standalone
    Skills.
    """
    inventory = list(suite_skills)
    errors: List[str] = []
    names = {item["name"] for item in inventory}
    excluded_seen = set()
    raw_excluded = manifest.get("excluded_from_aggregate_profile", [])
    if not isinstance(raw_excluded, list):
        return inventory, ["SUITE_MANIFEST.json excluded_from_aggregate_profile must be an array"]
    for index, name in enumerate(raw_excluded):
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name):
            errors.append(
                f"excluded_from_aggregate_profile[{index}] is not a valid skill directory name"
            )
            continue
        if name in names:
            errors.append(f"aggregate exclusion catalog overlaps aggregate membership: {name}")
            continue
        if name in excluded_seen:
            errors.append(f"duplicate aggregate exclusion catalog entry: {name}")
            continue
        excluded_seen.add(name)
        skill_root = repo_root / name
        if not skill_root.is_dir() or not (skill_root / "SKILL.md").is_file():
            errors.append(f"{name}: aggregate-excluded standalone Skill package is missing")
            continue
    return inventory, errors


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
