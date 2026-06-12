#!/usr/bin/env python3
"""Regression tests for product identity locks in Google Omni video prompts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL_DIR / "scripts" / "validate_video_segments.py"


def make_bad_video_prompt() -> dict:
    return {
        "segments": [
            {
                "segment_id": "SEG_01_0s_10s",
                "time_range": "0s-10s",
                "purpose": "Create a high-end purple perfume mood reveal.",
                "source_shots": ["SH_001", "SH_002", "SH_003"],
                "first_frame": "Purple mist and petals in darkness.",
                "last_frame": "A luxurious purple perfume object appears in a hero frame.",
                "camera_plan": "The bottle rises from mist, rotates slowly, and becomes the central object.",
                "subject_motion": "The cap separates slightly and the perfume bottle forms from light.",
                "environment_motion": "Violet petals and reflections swirl around the product.",
                "continuity_lock": "Keep a high-end purple perfume atmosphere.",
                "visual_style": "Luxury purple fragrance ad.",
                "negative_constraints": "No cheap look.",
            }
        ]
    }


def make_locked_video_prompt() -> dict:
    return {
        "required_reference_setup": {
            "product_identity_reference": "Belle-purple-product-sheet.jpeg",
            "product_identity_role": "highest_priority_product_identity",
            "non_identity_references": [
                "style references may control lighting, petals, reflections, and atmosphere only"
            ],
        },
        "product_identity_lock": {
            "source_reference": "Belle-purple-product-sheet.jpeg",
            "product_name_text": "ANDREA SECRET",
            "primary_label_text": ["GLISS LUMIERE", "AURORA SERIES", "ANDREA SECRET", "EAU DE TOILETTE", "100 mL"],
            "label_layout": "small top block, larger center block, vertical side text, small lower block",
            "packaging_shape": "tall slim rectangular transparent lavender-purple bottle with thick base and squared shoulders",
            "color_material_marks": "transparent lavender-purple glass body, champagne-gold rounded cap, visible internal spray tube",
            "required_visible_marks": ["rectangular body", "champagne-gold cap", "internal spray tube", "original label layout"],
            "forbidden_changes": ["generic purple bottle", "round bottle", "blank label", "fake label", "changed cap"],
            "rigid_body_rule": "product remains a rigid physical bottle; camera, mist, petals, reflections, and light carry motion",
            "allowed_angles_or_views": ["front", "front 3/4", "side", "back", "top", "bottom"],
            "forbidden_product_motion": ["morphing", "generating from mist", "cap separation", "product spin", "label movement"],
        },
        "global_negative_constraints": (
            "No generic bottle, no blank label, no fake text, no new brand, no cap removal, no product morphing, "
            "no product spin, no duplicate bottle."
        ),
        "segments": [
            {
                "segment_id": "SEG_01_0s_10s",
                "time_range": "0s-10s",
                "purpose": "Reveal the locked real product without rebuilding it.",
                "source_shots": ["SH_001", "SH_002", "SH_003"],
                "product_visibility": "full_visible",
                "product_identity_reference": "Belle-purple-product-sheet.jpeg",
                "product_motion_rule": "product remains a rigid still bottle; camera slide and foreground glass reveal it",
                "first_frame": "Lavender petal macro; product is not visible yet.",
                "last_frame": (
                    "The same real rectangular transparent lavender-purple bottle is visible front 3/4, "
                    "champagne-gold cap on, internal spray tube visible, original label layout in place."
                ),
                "camera_plan": (
                    "Camera slides past foreground glass to reveal the product already standing in the scene; "
                    "no product generation or product rotation."
                ),
                "subject_motion": (
                    "Product remains rigid, still, cap attached, label fixed, shape unchanged. "
                    "Only light travels across glass and metal."
                ),
                "environment_motion": "Mist, petals, reflections, and glass ribbons move around the locked product.",
                "continuity_lock": (
                    "Hard-lock to Belle-purple-product-sheet.jpeg: tall slim rectangular purple transparent body, "
                    "thick base, squared shoulders, champagne-gold cap, internal spray tube, original label layout."
                ),
                "visual_style": "Restrained violet fragrance TVC; product identity outranks style references.",
                "negative_constraints": (
                    "No generic purple bottle, no blank label, no fake text, no new brand, no changed cap, "
                    "no cap removal, no product morphing, no product spin, no duplicate bottle."
                ),
            }
        ],
    }


def run_validator(payload: dict) -> tuple[int, dict]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "video_segments.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), str(path)],
            text=True,
            capture_output=True,
            check=False,
        )
    return proc.returncode, json.loads(proc.stdout)


class VideoProductLockTests(unittest.TestCase):
    def test_video_prompts_reject_reconstructive_product_language_without_lock(self) -> None:
        code, result = run_validator(make_bad_video_prompt())

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("product_identity_lock" in error for error in result["errors"]),
            result["errors"],
        )
        self.assertTrue(
            any("unsafe product rebuild language" in error for error in result["errors"]),
            result["errors"],
        )

    def test_video_prompts_pass_when_product_reference_and_rigid_motion_rules_are_locked(self) -> None:
        code, result = run_validator(make_locked_video_prompt())

        self.assertEqual(code, 0, result)
        self.assertTrue(result["ok"], result)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
