#!/usr/bin/env python3
"""Validate the codex-skills TVC subsystem and its sibling Skill surface."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

from suite_common import REPO_ROOT, SUBSYSTEM_ROOT, SuiteConfigurationError, load_distribution


EXPECTED_ORIGINS = {
    "new_sop": 6,
    "original_asset_owner": 7,
    "original_exploration": 2,
}
OWNER_SKILLS = {
    "character-casting-lock-board",
    "character-final-lock-board",
    "single-face-character-lock-board",
    "multi-angle-product-identity-lock-board",
    "packaging-product-identity-label-lock-board",
    "material-sensitive-product-master-asset-board",
    "scene-canon-asset-pack",
}
REQUIRED_SUBSYSTEM_FILES = (
    "README.md",
    "assets/high-control-ai-tvc-sop.svg",
    "config/runtime-requirements.json",
    "docs/SOP.md",
    "docs/CODEX_PROMPTS.md",
    "docs/INSTALLATION.md",
    "docs/WINDOWS.md",
    "docs/MACOS.md",
    "docs/PROJECT_STRUCTURE.md",
    "docs/REVISION_AND_APPROVAL.md",
    "docs/SECURITY_AND_DATA.md",
    "docs/SOURCE_PROVENANCE.md",
    "docs/TOOLS_INPUTS_OUTPUTS.md",
    "tools/manage_skills.py",
    "tools/preflight.py",
    "tools/new_project.py",
    "tools/install.sh",
    "tools/install.ps1",
)


def _frontmatter_name(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    match = re.search(r"(?m)^name:\s*([a-z0-9_-]+)\s*$", text[4:end])
    return match.group(1) if match else None


def validate() -> List[str]:
    errors: List[str] = []
    try:
        manifest, _requirements, skills, common_errors = load_distribution(REPO_ROOT)
    except SuiteConfigurationError as exc:
        return [str(exc)]
    errors.extend(common_errors)
    names = {item["name"] for item in skills}

    actual = {
        path.parent.name
        for path in REPO_ROOT.glob("*/SKILL.md")
        if path.parent.name != "high-control-ai-tvc"
    }
    if actual != names:
        errors.append(
            "top-level SKILL.md set differs from manifest; "
            f"missing={sorted(names - actual)}; extra={sorted(actual - names)}"
        )

    for item in skills:
        name = item["name"]
        skill_md = REPO_ROOT / name / "SKILL.md"
        if skill_md.is_file():
            try:
                frontmatter = _frontmatter_name(skill_md)
            except (OSError, UnicodeDecodeError) as exc:
                errors.append(f"{name}: cannot read UTF-8 SKILL.md: {exc}")
            else:
                if frontmatter != name:
                    errors.append(f"{name}: frontmatter name is {frontmatter!r}")

    raw_skills = manifest.get("skills", [])
    origin_counts: Dict[str, int] = {}
    for item in raw_skills if isinstance(raw_skills, list) else []:
        if not isinstance(item, dict):
            continue
        origin = item.get("origin_group")
        if isinstance(origin, str):
            origin_counts[origin] = origin_counts.get(origin, 0) + 1
        else:
            errors.append(f"{item.get('name', '<unknown>')}: origin_group is missing")
    if origin_counts != EXPECTED_ORIGINS:
        errors.append(f"origin counts are {origin_counts}, expected {EXPECTED_ORIGINS}")

    manifest_owners = {
        item.get("name") for item in raw_skills
        if isinstance(item, dict) and item.get("origin_group") == "original_asset_owner"
    }
    if manifest_owners != OWNER_SKILLS:
        errors.append("original_asset_owner membership differs from the seven Canon owners")
    bridge = REPO_ROOT / "ai-video-shot-script-director" / "scripts" / "build_asset_canon_export.py"
    if not bridge.is_file():
        errors.append("shared sibling dependency is missing: Shot Director asset Canon bridge")
    for owner in sorted(OWNER_SKILLS):
        wrapper = REPO_ROOT / owner / "scripts" / "export_ai_video_canon.py"
        if not wrapper.is_file():
            errors.append(f"{owner}: sibling Canon export wrapper is missing")

    pillow_pins = []
    for skill in ("ai-video-shot-script-director", "ai-video-omni-reference-prompt-director"):
        requirements = REPO_ROOT / skill / "requirements.txt"
        if not requirements.is_file():
            errors.append(f"{skill}: requirements.txt is missing")
            continue
        pins = [
            line.strip() for line in requirements.read_text(encoding="utf-8").splitlines()
            if line.strip().lower().startswith("pillow") and not line.lstrip().startswith("#")
        ]
        if len(pins) != 1 or not re.fullmatch(r"Pillow==\d+\.\d+\.\d+", pins[0]):
            errors.append(f"{skill}: requires one exact Pillow pin")
        else:
            pillow_pins.append(pins[0])
    if len(pillow_pins) == 2 and len(set(pillow_pins)) != 1:
        errors.append("Shot Director and Prompt Director Pillow pins differ")
    if pillow_pins and pillow_pins[0] != "Pillow==11.3.0":
        errors.append(f"suite runtime expects Pillow==11.3.0, found {pillow_pins[0]}")

    for relative in REQUIRED_SUBSYSTEM_FILES:
        if not (SUBSYSTEM_ROOT / relative).is_file():
            errors.append(f"required subsystem file is missing: high-control-ai-tvc/{relative}")
    svg = SUBSYSTEM_ROOT / "assets" / "high-control-ai-tvc-sop.svg"
    if svg.is_file():
        try:
            root = ET.parse(svg).getroot()
            if not root.tag.endswith("svg"):
                errors.append("workflow asset root element is not SVG")
        except (ET.ParseError, OSError) as exc:
            errors.append(f"workflow SVG is not valid XML: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-suite-tests", action="store_true")
    args = parser.parse_args()
    errors = validate()
    if not errors and args.run_suite_tests:
        validator = REPO_ROOT / "ai-video-omni-reference-prompt-director" / "scripts" / "validate_ai_video_suite.py"
        result = subprocess.run(
            [sys.executable, str(validator), "--suite-root", str(REPO_ROOT)],
            text=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(f"six-Skill suite validator failed with exit {result.returncode}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: 15-Skill high-control AI TVC subsystem distribution validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
