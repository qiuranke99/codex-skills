#!/usr/bin/env python3
"""Regression tests for completed run-package validation."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL_DIR / "scripts" / "validate_run_package.py"


def load_helper(module_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(module_name, SKILL_DIR / rel)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load helper module: {rel}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shot_helper = load_helper("shot_helper", "tests/test_validate_product_identity_lock.py")
video_helper = load_helper("video_helper", "tests/test_validate_video_product_lock.py")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def populate_run_dir(run_dir: Path, storyboard_prompt: str) -> None:
    shot_plan = shot_helper.make_plan(include_identity_lock=True)
    write_json(run_dir / "00_route_decision.json", {"project_type": "premium_product_ad"})
    write_text(run_dir / "01_reference_roles.md", "product_identity: serum-reference.jpg\n")
    write_json(run_dir / "02_shot_plan.json", shot_plan)
    write_json(run_dir / "03_director_qc.json", {"ok": True})
    write_text(run_dir / "04_storyboard_image_prompts.md", storyboard_prompt)
    write_text(run_dir / "08_google_omni_video_prompts.md", "See structured JSON sidecar.\n")
    write_json(run_dir / "08_google_omni_video_prompts.json", video_helper.make_locked_video_prompt())
    write_text(run_dir / "09_final_qc_report.md", "All required artifacts validated.\n")


def valid_storyboard_prompt() -> str:
    return """
# Storyboard Sheet 01 Prompt

Product Visibility Rhythm: SH_001 not_visible -> SH_002 detail_only -> SH_003
partial_visible -> SH_004 full_visible -> SH_005 detail_only -> SH_006
partial_visible -> SH_007 not_visible -> SH_008 partial_visible -> SH_009
full_visible.

Panel plan:
- SH_001 [product_visibility: not_visible]: no product, no bottle, no package,
  no label, and no product text in this panel; draw only the blue-white droplet
  world.
- SH_002 [product_visibility: detail_only]: draw only the rounded black cap edge
  and pale blue stripe reflection, not the full bottle.
- SH_003 [product_visibility: partial_visible]: crop the white bottle shoulder
  behind the tray rim; do not show the full package.
- SH_004 [product_visibility: full_visible]: draw the exact user-provided
  product. Preserve front wordmark LUMA, center text HYDRATING SERUM, lower text
  30 ml, white cylindrical bottle, rounded black cap, front label rectangle,
  pale blue stripe, none_visible embossed marks, no gold metal plate, no metal
  badge, no front plaque, no extra emblem.
- SH_005 [product_visibility: detail_only]: show only the centered front label
  rectangle and pale blue stripe material detail.
- SH_006 [product_visibility: partial_visible]: show the fingertip and cropped
  bottle base, not a centered packshot.
- SH_007 [product_visibility: not_visible]: no product, no bottle, no package,
  no label, and no product text in this panel; draw only the hydration ripple.
- SH_008 [product_visibility: partial_visible]: show only the reflected cropped
  bottle silhouette as a transition.
- SH_009 [product_visibility: full_visible]: final front packshot of the exact
  LUMA / HYDRATING SERUM / 30 ml bottle, preserving the same white cylindrical
  bottle, rounded black cap, front label rectangle, pale blue stripe, and no
  gold metal plate, no metal badge, no front plaque, no extra emblem.
"""


def run_validator(run_dir: Path) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(run_dir)],
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.returncode, json.loads(proc.stdout)


class RunPackageValidationTests(unittest.TestCase):
    def test_complete_run_package_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            populate_run_dir(run_dir, valid_storyboard_prompt())

            code, result = run_validator(run_dir)

        self.assertEqual(code, 0, result)
        self.assertTrue(result["ok"], result)

    def test_run_package_rejects_storyboard_prompt_that_drops_product_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            populate_run_dir(
                run_dir,
                "Draw the exact LUMA bottle with the same white cylindrical bottle and rounded black cap.",
            )

            code, result = run_validator(run_dir)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("HYDRATING SERUM" in error for error in result["errors"]),
            result["errors"],
        )

    def test_run_package_rejects_storyboard_prompt_without_visibility_rhythm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            populate_run_dir(
                run_dir,
                """
# Storyboard Sheet 01 Prompt

Global product lock: draw the exact LUMA / HYDRATING SERUM / 30 ml bottle in
the storyboard sheet with the same white cylindrical bottle, rounded black cap,
front label rectangle, pale blue stripe, no gold metal plate, no metal badge,
no front plaque, no extra emblem.
""",
            )

            code, result = run_validator(run_dir)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("Product Visibility Rhythm" in error or "product_visibility" in error for error in result["errors"]),
            result["errors"],
        )


if __name__ == "__main__":
    raise SystemExit(unittest.main())
