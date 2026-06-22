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
DIRECTOR_KERNEL = SKILL_DIR / "references" / "director_kernel.md"


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


def assert_no_route_panel_fields(testcase: unittest.TestCase, routed: dict) -> None:
    for forbidden in [
        "tempo_profile",
        "average_seconds_per_shot",
        "panel_count",
        "panel_count_source",
        "panels_per_sheet",
        "grid_layouts",
        "shots_per_video_segment",
        "max_panels_per_sheet",
    ]:
        testcase.assertNotIn(forbidden, routed)


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
                "brief": "高端护肤产品广告，40s，Google Omni 10s/段，一张产品图，一张视觉风格参考图",
                "reference_images": [{"path": "product.jpg"}, {"path": "style.jpg"}],
            }
        )

        self.assertEqual(routed["duration_seconds"], 40)
        self.assertEqual(routed["duration_source"], "brief.duration_context")
        self.assertEqual(routed["video_segment_seconds"], 10)
        self.assertEqual(routed["video_segment_seconds_source"], "brief.segment_seconds")
        self.assertEqual(routed["video_segment_count"], 4)
        self.assertEqual(routed["storyboard_sheet_count"], 4)
        self.assertEqual(routed["storyboard_artifact_policy"], "per_segment_dynamic_n_panel_storyboard")
        self.assertEqual(routed["storyboard_grid_mode"], "director_decided_dynamic_n_panel_per_segment")
        self.assertEqual(routed["director_concept_board_count"], 4)
        self.assertEqual(routed["segment_keyframe_packet_count"], 4)
        self.assertEqual(routed["panel_count_status"], "deferred_to_director_after_script")
        self.assertTrue(routed["director_decision_contract"]["route_must_not_estimate_panel_count"])
        assert_no_route_panel_fields(self, routed)

    def test_ten_second_ad_uses_dynamic_panels_without_extra_generations(self) -> None:
        routed = run_router(
            {
                "brief": "10s product ad, one product photo, one visual reference, cinematic but concise",
                "reference_images": [{"path": "product.jpg"}, {"path": "style.jpg"}],
            }
        )

        self.assertEqual(routed["duration_seconds"], 10)
        self.assertEqual(routed["video_segment_count"], 1)
        self.assertEqual(routed["storyboard_sheet_count"], 1)
        self.assertEqual(routed["storyboard_grid_mode"], "director_decided_dynamic_n_panel_per_segment")
        self.assertEqual(routed["segment_keyframe_packet_count"], 1)
        self.assertEqual(routed["panel_count_status"], "deferred_to_director_after_script")
        self.assertLessEqual(routed["recommended_story_beat_count"], 3)
        self.assertIn("route_project must not infer", routed["notes"][0])
        self.assertIn("not a single-shot generation plan", routed["video_generation_handoff"]["storyboard_sheet_role"])
        self.assertIn("Product Identity Lock", routed["video_generation_handoff"]["executable_segment_rule"])
        assert_no_route_panel_fields(self, routed)

    def test_thirty_second_standard_ad_uses_three_segment_storyboard_slots_without_panel_defaults(self) -> None:
        routed = run_router(
            {
                "brief": "30s high-end lipstick product ad, 9:16, one product image",
                "reference_images": [{"path": "product.jpg"}],
            }
        )

        self.assertEqual(routed["duration_seconds"], 30)
        self.assertEqual(routed["requested_video_aspect_ratio"], "9:16")
        self.assertEqual(routed["aspect_ratio_source"], "brief.aspect_ratio")
        self.assertEqual(routed["aspect_contract"], "panel_must_match_video_sheet_canvas_may_differ")
        self.assertEqual(routed["video_segment_count"], 3)
        self.assertEqual(routed["storyboard_sheet_count"], 3)
        self.assertEqual(routed["director_concept_board_count"], 3)
        self.assertEqual(routed["segment_keyframe_packet_count"], 3)
        self.assertEqual(routed["storyboard_density_strategy"], "script_first_director_decided")
        self.assertIn("create 3 storyboard sheet", routed["video_generation_handoff"]["duration_mapping"])
        self.assertIn("N panels are decided only after", routed["video_generation_handoff"]["duration_mapping"])
        self.assertIn("not an equal-seconds-per-panel rule", routed["video_generation_handoff"]["storyboard_sheet_role"])
        assert_no_route_panel_fields(self, routed)

    def test_route_normalizes_structured_video_aspect_ratio(self) -> None:
        routed = run_router(
            {
                "brief": "30s high-end lipstick product ad for mobile vertical delivery",
                "requested_video_aspect_ratio": "1080x1920",
                "reference_images": [{"path": "product.jpg"}],
            }
        )

        self.assertEqual(routed["requested_video_aspect_ratio"], "9:16")
        self.assertEqual(routed["aspect_ratio_source"], "intake.requested_video_aspect_ratio")
        self.assertEqual(routed["brief_detected_video_aspect_ratio"], "9:16")
        self.assertEqual(routed["aspect_contract"], "panel_must_match_video_sheet_canvas_may_differ")

    def test_route_flags_aspect_ratio_conflict_with_structured_intake_precedence(self) -> None:
        routed = run_router(
            {
                "brief": "30s high-end lipstick product ad, 9:16",
                "requested_video_aspect_ratio": "16:9",
                "reference_images": [{"path": "product.jpg"}],
            }
        )

        self.assertEqual(routed["requested_video_aspect_ratio"], "16:9")
        self.assertEqual(routed["aspect_ratio_source"], "intake.requested_video_aspect_ratio")
        self.assertEqual(routed["brief_detected_video_aspect_ratio"], "9:16")
        self.assertIn("aspect_ratio_conflict_intake_overrides_brief", routed["escalation_triggers"])

    def test_production_handoff_uses_segment_aligned_keyframe_boards(self) -> None:
        routed = run_router(
            {
                "brief": (
                    "30s high-end lipstick AI film workflow: creative concept, approved keyframes, "
                    "multi-backend bidding, edit/sound/color, QC/failure log"
                ),
                "reference_images": [{"path": "product.jpg"}],
            }
        )

        self.assertEqual(routed["production_mode"], "production_handoff")
        self.assertEqual(routed["video_segment_count"], 3)
        self.assertEqual(routed["storyboard_sheet_count"], 3)
        self.assertEqual(routed["director_concept_board_count"], 3)
        self.assertEqual(routed["segment_keyframe_packet_count"], 3)
        self.assertEqual(routed["storyboard_density_strategy"], "script_first_director_decided")
        self.assertEqual(routed["panel_to_segment_map_status"], "deferred_to_shot_plan_after_timecoded_script_map")
        self.assertTrue(any("multi-backend bidding" in note for note in routed["notes"]))
        assert_no_route_panel_fields(self, routed)

    def test_longer_ads_scale_segments_without_route_owned_panel_counts(self) -> None:
        cases = [
            (40, 4),
            (50, 5),
            (60, 6),
        ]
        for duration, segments in cases:
            with self.subTest(duration=duration):
                routed = run_router(
                    {
                        "brief": f"{duration}s premium fragrance product ad, Google Omni 10s/段",
                        "reference_images": [{"path": "product.jpg"}],
                    }
                )

                self.assertEqual(routed["duration_seconds"], duration)
                self.assertEqual(routed["video_segment_count"], segments)
                self.assertEqual(routed["storyboard_sheet_count"], segments)
                self.assertEqual(routed["director_concept_board_count"], segments)
                self.assertEqual(routed["segment_keyframe_packet_count"], segments)
                self.assertEqual(routed["storyboard_density_strategy"], "script_first_director_decided")
                assert_no_route_panel_fields(self, routed)

    def test_intake_script_shot_count_is_rejected_by_schema_and_ignored_by_router_contract(self) -> None:
        routed = run_router(
            {
                "brief": "30s high-end lipstick product ad, Google Omni speed route",
                "script_shot_count": 18,
                "reference_images": [{"path": "product.jpg"}],
            }
        )

        self.assertEqual(routed["duration_seconds"], 30)
        self.assertEqual(routed["video_segment_count"], 3)
        self.assertEqual(routed["storyboard_sheet_count"], 3)
        self.assertEqual(routed["panel_count_status"], "deferred_to_director_after_script")
        assert_no_route_panel_fields(self, routed)

    def test_requested_short_segments_are_normalized_to_ten_second_omni_generation_units(self) -> None:
        routed = run_router(
            {
                "brief": "30s premium lipstick ad, Google Omni 5s/段",
                "reference_images": [{"path": "product.jpg"}],
            }
        )

        self.assertEqual(routed["requested_video_segment_seconds"], 5)
        self.assertEqual(routed["video_segment_seconds"], 10)
        self.assertIn("normalized_to_10s_omni_generation_unit", routed["video_segment_seconds_source"])
        self.assertEqual(routed["video_segment_count"], 3)
        self.assertEqual(routed["storyboard_sheet_count"], 3)
        assert_no_route_panel_fields(self, routed)

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

    def test_director_kernel_no_longer_hardcodes_segment_sheet_count(self) -> None:
        kernel_text = DIRECTOR_KERNEL.read_text(encoding="utf-8")

        self.assertNotIn("one segment storyboard sheet per temporal video prompt after 15s", kernel_text)
        self.assertNotIn("30s, use 3 sheets", kernel_text)
        self.assertNotIn("40s, use 4", kernel_text)
        self.assertNotIn("50s standard concept pass", kernel_text)
        self.assertIn("dynamic N-panel", kernel_text)
        self.assertNotIn("script_shot_count", kernel_text)
        self.assertNotIn("tempo_estimate", kernel_text)
        self.assertNotIn("default 15", kernel_text)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
