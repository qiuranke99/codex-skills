#!/usr/bin/env python3
"""Regression tests for the optional aggregate compatibility boundary."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from build_asset_canon_export import OWNER_PROFILES, WORKFLOW_CANON_WRITERS
from suite_common import load_distribution, managed_inventory
from validate_ai_video_aggregate import AGGREGATE_MEMBERS, validate_aggregate


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ASSET_PROFILES = {
    "character_casting": "character-casting-lock-board",
    "character_final": "character-final-lock-board",
    "single_face_character": "single-face-character-lock-board",
    "multi_angle_product": "multi-angle-product-identity-lock-board",
    "packaging_product": "packaging-product-identity-label-lock-board",
    "material_sensitive_product": "material-sensitive-product-master-asset-board",
    "scene_canon": "scene-canon-asset-pack",
}
EXPECTED_WORKFLOW_PROFILES = {
    "ai-video-shot-script-director",
    "ai-video-global-look-lock",
    "ai-video-modular-storyboard",
    "ai-video-timed-animatic-previs-director",
    "ai-video-keyframe-continuity-pack",
    "ai-video-omni-reference-prompt-director",
}
EXPECTED_AGGREGATE_EXCLUSIONS = {
    "complex-product-identity-reconstruction-asset-locking",
}


def main() -> int:
    manifest, _requirements, suite_skills, errors = load_distribution(ROOT)
    managed, inventory_errors = managed_inventory(manifest, suite_skills, ROOT)
    errors.extend(inventory_errors)
    if errors:
        raise AssertionError(errors)

    managed_names = [item["name"] for item in managed]
    excluded_names = list(manifest.get("excluded_from_aggregate_profile", []))
    if len(managed_names) != 15 or set(managed_names) != set(AGGREGATE_MEMBERS):
        raise AssertionError(f"unexpected aggregate managed inventory: {managed_names}")
    if manifest.get("standalone_package_count") != 16:
        raise AssertionError("repository standalone_package_count must remain exactly 16")
    if set(excluded_names) != EXPECTED_AGGREGATE_EXCLUSIONS:
        raise AssertionError(f"unexpected aggregate exclusions: {excluded_names}")
    if set(excluded_names) & set(managed_names):
        raise AssertionError("aggregate-excluded catalog entry leaked into aggregate managed inventory")

    actual_asset_profiles = {
        profile_id: profile.owner_skill for profile_id, profile in OWNER_PROFILES.items()
    }
    if actual_asset_profiles != EXPECTED_ASSET_PROFILES:
        raise AssertionError(f"aggregate asset profiles drifted: {actual_asset_profiles}")
    if set(WORKFLOW_CANON_WRITERS) != EXPECTED_WORKFLOW_PROFILES:
        raise AssertionError(f"aggregate workflow profiles drifted: {WORKFLOW_CANON_WRITERS}")

    tools = ROOT / "high-control-ai-tvc" / "tools"
    bridge = tools / "build_asset_canon_export.py"
    validator = tools / "validate_asset_canon_export.py"
    for path in (bridge, validator, tools / "test_asset_canon_bridge.py", tools / "test_global_canon_write_gate.py"):
        if not path.is_file():
            raise AssertionError(f"aggregate Canon bridge closure is missing: {path}")
    for owner in sorted(EXPECTED_WORKFLOW_PROFILES):
        runner = tools / ("canon_runner_" + owner.replace("-", "_") + ".py")
        if not runner.is_file():
            raise AssertionError(f"fixed workflow runner is missing: {runner}")
        text = runner.read_text(encoding="utf-8")
        if f'"workflow", "--profile", "{owner}"' not in text:
            raise AssertionError(f"fixed workflow runner does not bind {owner}")

    invalid_profile = subprocess.run(
        [sys.executable, str(bridge), "asset", "--profile", "not-a-canon-owner"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if invalid_profile.returncode != 2 or "invalid choice" not in invalid_profile.stdout:
        raise AssertionError("aggregate asset CLI did not fail closed on an unknown explicit profile")

    compatibility_errors = validate_aggregate(ROOT, run_tests=False)
    if compatibility_errors:
        raise AssertionError("aggregate compatibility validation failed: " + "; ".join(compatibility_errors))

    print(
        "PASS: optional aggregate manages exactly 15 members; "
        "excluded catalog entries remain outside aggregate receipts; all 16 packages remain standalone"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
