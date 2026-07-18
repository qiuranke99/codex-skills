#!/usr/bin/env python3
"""Validate the optional High-Control aggregate profile and its maintenance tooling."""

from __future__ import annotations

import argparse
import json
import os
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
FORBIDDEN_PACKAGE_ENTRYPOINT_MARKERS = (
    ("HIGH_CONTROL_RELEASE_GATE", re.compile(r"\bHIGH_CONTROL_RELEASE_GATE(?:_V\d+)?\b", re.IGNORECASE)),
    ("release-control", re.compile(r"\brelease[-_]control(?:\.(?:ps1|sh|py))?\b", re.IGNORECASE)),
    ("SUITE_MANIFEST", re.compile(r"\bSUITE_MANIFEST(?:\.json)?\b", re.IGNORECASE)),
    ("ready_latest", re.compile(r"\bready_latest\b", re.IGNORECASE)),
    ("unverified global Python", re.compile(r"\bunverified global Python\b", re.IGNORECASE)),
)
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
    "tools/release_control.py",
    "tools/release-control.sh",
    "tools/release-control.ps1",
    "tools/preflight.py",
    "tools/new_project.py",
    "tools/test_install_lifecycle.py",
    "tools/test_release_control.py",
    "tools/validate_ai_video_aggregate.py",
    "tools/test_aggregate_contract.py",
    "tools/validate_schema_parity.py",
    "tools/build_asset_canon_export.py",
    "tools/validate_asset_canon_export.py",
    "tools/test_asset_canon_bridge.py",
    "tools/test_global_canon_write_gate.py",
    "tools/canon_runner_ai_video_shot_script_director.py",
    "tools/canon_runner_ai_video_global_look_lock.py",
    "tools/canon_runner_ai_video_modular_storyboard.py",
    "tools/canon_runner_ai_video_timed_animatic_previs_director.py",
    "tools/canon_runner_ai_video_keyframe_continuity_pack.py",
    "tools/canon_runner_ai_video_omni_reference_prompt_director.py",
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
    authority = manifest.get("source_authority")
    expected_authority = {
        "repository": "qiuranke99/codex-skills",
        "remote_url": "https://github.com/qiuranke99/codex-skills.git",
        "branch": "main",
        "github_repository_id": 1264973746,
        "revision_policy": "github_main_latest_validated_immutable_snapshot",
    }
    if authority != expected_authority:
        errors.append(f"source_authority is {authority!r}, expected {expected_authority!r}")
    if "source_commit" in manifest:
        errors.append("source_commit is self-referential and forbidden; runtime receipts own release commits")
    names = {item["name"] for item in skills}

    raw_excluded = manifest.get("excluded_from_aggregate_profile", [])
    if not isinstance(raw_excluded, list) or any(
        not isinstance(name, str) or not name for name in raw_excluded
    ):
        errors.append("excluded_from_aggregate_profile must be a list of non-empty skill names")
        excluded = set()
    else:
        excluded = set(raw_excluded)
        if len(excluded) != len(raw_excluded):
            errors.append("excluded_from_aggregate_profile contains duplicate names")
        overlap = excluded & names
        if overlap:
            errors.append(f"excluded_from_aggregate_profile overlaps aggregate membership: {sorted(overlap)}")

    actual = {
        path.parent.name
        for path in REPO_ROOT.glob("*/SKILL.md")
        if path.parent.name != "high-control-ai-tvc"
    }
    expected_top_level = names | excluded
    expected_standalone_count = manifest.get("standalone_package_count")
    if len(expected_top_level) != expected_standalone_count:
        errors.append(
            "aggregate compatibility catalog size is "
            f"{len(expected_top_level)}, expected {expected_standalone_count}"
        )
    if len(actual) != expected_standalone_count:
        errors.append(
            f"top-level standalone Skill count is {len(actual)}, expected {expected_standalone_count}"
        )
    missing_catalog_entries = expected_top_level - actual
    if missing_catalog_entries:
        errors.append(
            "aggregate compatibility catalog names missing top-level SKILL.md: "
            + ", ".join(sorted(missing_catalog_entries))
        )
    unexpected_catalog_entries = actual - expected_top_level
    if unexpected_catalog_entries:
        errors.append(
            "top-level standalone Skill directories absent from the aggregate compatibility catalog: "
            + ", ".join(sorted(unexpected_catalog_entries))
        )

    for name in sorted(actual):
        skill_md = REPO_ROOT / name / "SKILL.md"
        if skill_md.is_file():
            try:
                frontmatter = _frontmatter_name(skill_md)
            except (OSError, UnicodeDecodeError) as exc:
                errors.append(f"{name}: cannot read UTF-8 SKILL.md: {exc}")
            else:
                if frontmatter != name:
                    errors.append(f"{name}: frontmatter name is {frontmatter!r}")
                text = skill_md.read_text(encoding="utf-8")
                for marker_name, pattern in FORBIDDEN_PACKAGE_ENTRYPOINT_MARKERS:
                    if pattern.search(text):
                        errors.append(
                            f"{name}: standalone SKILL.md contains forbidden aggregate coupling: {marker_name}"
                        )

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
        errors.append(f"aggregate maintenance runtime expects Pillow==11.3.0, found {pillow_pins[0]}")

    for relative in REQUIRED_SUBSYSTEM_FILES:
        if not (SUBSYSTEM_ROOT / relative).is_file():
            errors.append(f"required subsystem file is missing: high-control-ai-tvc/{relative}")
    bridge_path = SUBSYSTEM_ROOT / "tools/build_asset_canon_export.py"
    if bridge_path.is_file():
        bridge_text = bridge_path.read_text(encoding="utf-8")
        for marker in (
            "OWNER_PROFILES",
            "WORKFLOW_CANON_WRITERS",
            "def recover_or_gate_global_pending_transaction(",
            "def apply_fixed_owner_export(",
            "def apply_workflow_canon_transition(",
            "def run_aggregate_cli(",
            'asset.add_argument("--profile"',
            'workflow.add_argument("--profile"',
            "AI_VIDEO_CANON_TEST_FAULT_AFTER_MANIFEST_REPLACE",
        ):
            if marker not in bridge_text:
                errors.append(f"aggregate Canon bridge is missing contract marker: {marker}")
    workflow_runners = {
        "canon_runner_ai_video_shot_script_director.py": "ai-video-shot-script-director",
        "canon_runner_ai_video_global_look_lock.py": "ai-video-global-look-lock",
        "canon_runner_ai_video_modular_storyboard.py": "ai-video-modular-storyboard",
        "canon_runner_ai_video_timed_animatic_previs_director.py": "ai-video-timed-animatic-previs-director",
        "canon_runner_ai_video_keyframe_continuity_pack.py": "ai-video-keyframe-continuity-pack",
        "canon_runner_ai_video_omni_reference_prompt_director.py": "ai-video-omni-reference-prompt-director",
    }
    for runner_name, owner in workflow_runners.items():
        runner_path = SUBSYSTEM_ROOT / "tools" / runner_name
        if runner_path.is_file():
            runner_text = runner_path.read_text(encoding="utf-8")
            if f'"workflow", "--profile", "{owner}"' not in runner_text:
                errors.append(f"aggregate workflow runner does not bind fixed owner {owner}")
        handoff = REPO_ROOT / owner / "scripts/apply_project_canon_transition.py"
        if not handoff.is_file():
            errors.append(f"{owner}: optional Project Canon handoff entrypoint is missing")
        elif "--transition-runner" not in handoff.read_text(encoding="utf-8"):
            errors.append(f"{owner}: Project Canon handoff does not accept an explicit transition runner")
    if os.name != "nt" and not os.access(SUBSYSTEM_ROOT / "tools/release-control.sh", os.X_OK):
        errors.append("tools/release-control.sh must be executable")
    svg = SUBSYSTEM_ROOT / "assets" / "high-control-ai-tvc-sop.svg"
    if svg.is_file():
        try:
            root = ET.parse(svg).getroot()
            if not root.tag.endswith("svg"):
                errors.append("workflow asset root element is not SVG")
        except (ET.ParseError, OSError) as exc:
            errors.append(f"workflow SVG is not valid XML: {exc}")

    packaging_root = REPO_ROOT / "packaging-product-identity-label-lock-board"
    packaging_required = (
        "SKILL.md",
        "agents/openai.yaml",
        "references/generation_prompt_template.md",
        "references/generation_prompt_values.template.json",
        "references/copy_ledger.template.json",
        "references/copy_qa.template.json",
        "references/raw_board_qa.template.json",
        "references/prompt_dispatch_trace.template.json",
        "references/composition_plan.template.json",
        "references/asset_board_manifest.template.json",
        "scripts/freeze_reference_bundle.py",
        "scripts/build_generation_reference_pack.py",
        "scripts/validate_prompt_dispatch_trace.py",
        "scripts/resolve_worker_image.py",
        "scripts/compose_asset_board.py",
        "scripts/compile_copy_prompt.py",
        "scripts/render_generation_prompt.py",
        "scripts/validate_copy_contract.py",
        "scripts/validate_asset_board_run.py",
        "scripts/test_contract.py",
    )
    for relative in packaging_required:
        if not (packaging_root / relative).is_file():
            errors.append(f"packaging worker-runtime closure is missing: {relative}")
    packaging_skill = packaging_root / "SKILL.md"
    if packaging_skill.is_file():
        text = packaging_skill.read_text(encoding="utf-8")
        for marker in (
            "Return exactly one clean horizontal 16:9 board",
            "exactly seven complete product views",
            "two source-grounded detail regions by default",
            "nine regions by default and never more than ten",
            "borderless_continuous_background",
            "No blank cells, empty rectangles, placeholders, reserved slots",
            "independently usable as a final single-call prompt",
            "OCR remains nonblocking",
            "copy-ledger.json",
            "scripts/compile_copy_prompt.py",
            "scripts/render_generation_prompt.py",
            "scripts/validate_copy_contract.py",
            "raw-board-qa.json",
            "references/raw_board_qa.template.json",
            "USER_SKIPPED_GENERATION",
            "board_wide_invented_or_corrupted_visible_copy",
            "never request a fixed 8/12/16/24-angle capture set",
            "The main agent must not call imagegen directly",
            "scripts/compose_asset_board.py",
            "scripts/validate_asset_board_run.py",
        ):
            if marker not in text:
                errors.append(f"packaging worker-runtime marker is missing: {marker}")
        if len(text.splitlines()) > 500:
            errors.append("packaging SKILL.md exceeds the 500-line progressive-disclosure limit")
    packaging_ui = packaging_root / "agents/openai.yaml"
    if packaging_ui.is_file() and "allow_implicit_invocation: false" not in packaging_ui.read_text(encoding="utf-8"):
        errors.append("packaging worker runtime must disable implicit invocation")
    board_manifest_template = packaging_root / "references/asset_board_manifest.template.json"
    if board_manifest_template.is_file():
        try:
            board_manifest = json.loads(board_manifest_template.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"packaging asset-board manifest template is invalid: {exc}")
        else:
            if board_manifest.get("schema_version") != "packaging_video_asset_board.v2":
                errors.append("packaging asset-board manifest has the wrong schema")
            if len(board_manifest.get("view_regions", [])) != 7:
                errors.append("packaging asset-board manifest must define exactly seven views")
            if not 2 <= len(board_manifest.get("detail_regions", [])) <= 3:
                errors.append("packaging asset-board manifest must define two or three details")
            if board_manifest.get("region_count") not in {9, 10}:
                errors.append("packaging asset-board manifest must define nine or ten total regions")
            if board_manifest.get("layout_style") != "borderless_continuous_background":
                errors.append("packaging asset-board manifest must require a borderless continuous background")
            if board_manifest.get("qa", {}).get("all_regions_populated") != "pass":
                errors.append("packaging asset-board manifest must require all_regions_populated")
            if board_manifest.get("qa", {}).get("no_visible_frames") != "pass":
                errors.append("packaging asset-board manifest must reject visible frames")
            for field in ("raw_board_qa_path", "raw_board_qa_sha256"):
                if field not in board_manifest:
                    errors.append(f"packaging asset-board manifest must bind {field}")
    raw_board_qa_template = packaging_root / "references/raw_board_qa.template.json"
    if raw_board_qa_template.is_file():
        try:
            raw_board_qa = json.loads(raw_board_qa_template.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"packaging raw-board QA template is invalid: {exc}")
        else:
            if raw_board_qa.get("schema_version") != "packaging_raw_board_qa.v1":
                errors.append("packaging raw-board QA template has the wrong schema")
            if raw_board_qa.get("inspected") is not False or raw_board_qa.get("overall_status") != "pending":
                errors.append("packaging raw-board QA template must default to a fail-closed pending state")
            if raw_board_qa.get("complete_view_count") != 7:
                errors.append("packaging raw-board QA must require exactly seven complete views")
            if raw_board_qa.get("detail_region_count") not in {2, 3}:
                errors.append("packaging raw-board QA must require two or three details")
            if raw_board_qa.get("total_region_count") not in {9, 10}:
                errors.append("packaging raw-board QA must require nine or ten regions")
            flags = raw_board_qa.get("failure_flags")
            if not isinstance(flags, dict) or any(value is not False for value in flags.values()):
                errors.append("packaging raw-board QA failure flags must default to false")
    dispatch_validator = packaging_root / "scripts/validate_prompt_dispatch_trace.py"
    if dispatch_validator.is_file():
        dispatch_text = dispatch_validator.read_text(encoding="utf-8")
        for marker in (
            "prompt_elapsed not in updates",
            "validate_update_cadence(trace, 0, terminal_elapsed)",
            "USER_SKIPPED_GENERATION",
            "BLOCKED_PROMPT_READY_TIMEOUT",
        ):
            if marker not in dispatch_text:
                errors.append(f"packaging dispatch validator is missing end-to-end cadence marker: {marker}")
    composition_plan_template = packaging_root / "references/composition_plan.template.json"
    if composition_plan_template.is_file():
        try:
            composition_plan = json.loads(composition_plan_template.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"packaging composition-plan template is invalid: {exc}")
        else:
            if composition_plan.get("schema_version") != "packaging_board_composition_plan.v2":
                errors.append("packaging composition plan has the wrong schema")
            if not 2 <= len(composition_plan.get("detail_layout", [])) <= 3:
                errors.append("packaging composition plan must freeze two or three populated detail regions")
            if composition_plan.get("layout_style") != "borderless_continuous_background":
                errors.append("packaging composition plan must require a borderless continuous background")
            if composition_plan.get("drawn_borders") is not False:
                errors.append("packaging composition plan must forbid drawn borders")
    return errors


def _run_standalone_validator() -> List[str]:
    """Consume the repository-level package authority without importing it."""
    validator = REPO_ROOT / ".github" / "scripts" / "validate_standalone_skills.py"
    if not validator.is_file():
        return ["repository standalone Skill validator is missing"]
    try:
        manifest = json.loads((SUBSYSTEM_ROOT / "SUITE_MANIFEST.json").read_text(encoding="utf-8"))
        expected_count = manifest["standalone_package_count"]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        return [f"cannot resolve standalone package count: {exc}"]
    result = subprocess.run(
        [
            sys.executable,
            str(validator),
            "--repo-root",
            str(REPO_ROOT),
            "--expected-count",
            str(expected_count),
            "--timeout",
            "180",
            "--compact",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        return [
            "repository standalone Skill validator returned invalid JSON"
            + (f": {result.stderr.strip()}" if result.stderr.strip() else "")
        ]
    if result.returncode == 0 and report.get("status") == "pass":
        return []
    summary = report.get("summary", {})
    failed = [
        item.get("name", "<unknown>")
        for item in report.get("packages", [])
        if isinstance(item, dict) and item.get("status") != "pass"
    ]
    detail = (
        f"exit={result.returncode}; status={report.get('status')}; "
        f"packages_failed={summary.get('packages_failed')}; issues_total={summary.get('issues_total')}"
    )
    if failed:
        detail += "; failed=" + ", ".join(failed)
    return ["repository standalone Skill isolation validation failed: " + detail]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-suite-tests", action="store_true")
    args = parser.parse_args()
    errors = validate()
    if not errors and args.run_suite_tests:
        errors.extend(_run_standalone_validator())
    if not errors and args.run_suite_tests:
        validator = SUBSYSTEM_ROOT / "tools" / "validate_ai_video_aggregate.py"
        result = subprocess.run(
            [sys.executable, str(validator), "--suite-root", str(REPO_ROOT)],
            text=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(f"AI-video aggregate compatibility validator failed with exit {result.returncode}")
        for label, script_name in (
            ("install lifecycle", "test_install_lifecycle.py"),
            ("release control", "test_release_control.py"),
        ):
            script = SUBSYSTEM_ROOT / "tools" / script_name
            test_result = subprocess.run([sys.executable, str(script)], text=True, check=False)
            if test_result.returncode != 0:
                errors.append(f"{label} regression test failed with exit {test_result.returncode}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: optional 15-Skill High-Control aggregate compatibility profile validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
