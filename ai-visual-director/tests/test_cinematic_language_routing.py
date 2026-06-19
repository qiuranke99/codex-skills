#!/usr/bin/env python3
"""Regression tests for advanced cinematic-language reference routing."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
ROUTER = SKILL_DIR / "scripts" / "route_project.py"
REFERENCE = SKILL_DIR / "references" / "cinematic_language_decision_matrix.md"
SKILL_MD = SKILL_DIR / "SKILL.md"
WORKFLOW = SKILL_DIR / "references" / "workflow_contract.md"


def run_router(payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, str(ROUTER)],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    return json.loads(proc.stdout)


class CinematicLanguageRoutingTests(unittest.TestCase):
    def test_vfx_sound_and_camera_pipeline_brief_requires_advanced_reference(self) -> None:
        routed = run_router(
            {
                "brief": (
                    "Design a 45s VFX-heavy action storyboard with virtual production, "
                    "lens grid notes, ACES color pipeline, J-cut sound bridge, and camera report handoff."
                ),
                "duration_seconds": 45,
                "video_segment_seconds": 10,
            }
        )

        self.assertTrue(routed["cinematic_language_reference_required"], routed)
        self.assertIn(
            "references/cinematic_language_decision_matrix.md",
            routed["recommended_references"],
        )
        self.assertIn("vfx_or_virtual_production", routed["cinematic_language_triggers"])
        self.assertIn("sound_design_or_sound_editing", routed["cinematic_language_triggers"])
        self.assertIn("production_handoff_or_camera_report", routed["cinematic_language_triggers"])
        self.assertIn("color_pipeline_or_delivery", routed["cinematic_language_triggers"])

    def test_simple_product_ad_does_not_load_advanced_reference_by_default(self) -> None:
        routed = run_router(
            {
                "brief": "premium skincare serum product ad with clean floral glass reflections",
                "duration_seconds": 20,
                "video_segment_seconds": 10,
                "reference_images": [{"path": "product.jpg"}],
            }
        )

        self.assertFalse(routed["cinematic_language_reference_required"], routed)
        self.assertNotIn(
            "references/cinematic_language_decision_matrix.md",
            routed["recommended_references"],
        )

    def test_route_parses_duration_and_segment_seconds_from_brief_text(self) -> None:
        routed = run_router(
            {
                "brief": "高端护肤产品广告，40s，Google Omni 10s/段，一张产品图，一张蓝灰视觉参考图",
                "reference_images": [{"path": "product.jpg"}, {"path": "style.jpg"}],
            }
        )

        self.assertEqual(routed["duration_seconds"], 40)
        self.assertEqual(routed["duration_source"], "brief.duration_context")
        self.assertEqual(routed["video_segment_seconds"], 10)
        self.assertEqual(routed["video_segment_seconds_source"], "brief.segment_seconds")
        self.assertEqual(routed["video_segment_count"], 4)
        self.assertEqual(routed["storyboard_sheet_count"], 2)
        self.assertEqual(routed["panel_count"], 18)

    def test_ten_second_ad_keeps_storyboard_as_keyframes_not_nine_video_cuts(self) -> None:
        routed = run_router(
            {
                "brief": "10s product ad, one product photo, one visual reference, cinematic but concise",
                "reference_images": [{"path": "product.jpg"}, {"path": "style.jpg"}],
            }
        )

        self.assertEqual(routed["duration_seconds"], 10)
        self.assertEqual(routed["video_segment_count"], 1)
        self.assertEqual(routed["storyboard_sheet_count"], 1)
        self.assertEqual(routed["panel_count"], 9)
        self.assertLessEqual(routed["recommended_story_beat_count"], 3)
        self.assertIn("not a one-to-one edit list", routed["notes"][0])

    def test_skill_contains_conditional_refined_reference_not_full_source_import(self) -> None:
        self.assertTrue(REFERENCE.exists(), "missing refined cinematic language reference")
        reference_text = REFERENCE.read_text(encoding="utf-8")
        skill_text = SKILL_MD.read_text(encoding="utf-8")
        workflow_text = WORKFLOW.read_text(encoding="utf-8")

        self.assertLess(len(reference_text.splitlines()), 220, "reference should be refined, not full source import")
        self.assertLess(len(reference_text.split()), 1700, "reference should stay compact enough for on-demand loading")
        self.assertIn("Advanced Cinematic Language Decision Matrix", reference_text)
        self.assertIn("Do not load this reference by default", reference_text)
        self.assertIn("L1 - always required", reference_text)
        self.assertIn("L2 - advanced creative controls", reference_text)
        self.assertIn("L3 - complex delivery and traceability", reference_text)
        self.assertIn("sound_intent", reference_text)
        self.assertIn("camera_report_required", reference_text)
        self.assertIn("cinematic_language_decision_matrix.md", skill_text)
        self.assertIn("cinematic_language_reference_required", workflow_text)
        self.assertNotIn("本文档面向视觉导演", reference_text)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
