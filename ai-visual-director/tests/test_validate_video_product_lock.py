#!/usr/bin/env python3
"""Regression tests for product visual-fidelity locks in Google Omni video prompts."""

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


def make_bad_visual_identity_prompt() -> dict:
    return {
        "required_reference_setup": {
            "product_identity_reference": "Belle-purple-product-sheet.jpeg",
            "product_identity_role": "highest_priority_product_identity",
        },
        "product_identity_lock": {
            "source_reference": "Belle-purple-product-sheet.jpeg",
            "product_name_text": "BELLE",
            "primary_label_text": ["BELLE", "EAU DE PARFUM", "100 mL"],
            "surface_text_inventory": ["front wordmark BELLE", "lower text EAU DE PARFUM", "small volume text 100 mL"],
            "embossed_or_relief_marks": ["raised BELLE wordmark on front face"],
            "label_layout": "minimal centered front wordmark with lower small product text, no metal plate",
            "packaging_shape": "tall transparent purple rectangular bottle, smooth front face, squared shoulders",
            "physical_component_inventory": ["transparent purple glass bottle", "smooth glass front", "matching cap"],
            "color_material_marks": "transparent purple glass and matching cap; no applied metal hardware on bottle face",
            "required_visible_marks": ["BELLE wordmark", "EAU DE PARFUM text", "100 mL text", "smooth front glass"],
            "forbidden_changes": ["blank label", "wrong text", "changed label layout", "extra emblem"],
            "forbidden_visual_additions": ["gold metal plate", "metal badge", "front plaque", "extra emblem"],
            "full_view_fidelity_rule": "full product views must show the exact BELLE / EAU DE PARFUM / 100 mL text inventory and smooth no-plate front face",
        },
        "global_negative_constraints": (
            "No blank label, no wrong text, no fake logo, no gold metal plate, no front plaque, no extra emblem."
        ),
        "segments": [
            {
                "segment_id": "SEG_01_0s_10s",
                "time_range": "0s-10s",
                "purpose": "Hero full-product reveal with a camera orbit.",
                "source_shots": ["SH_001", "SH_002", "SH_003"],
                "product_visibility": "full_visible",
                "product_identity_reference": "Belle-purple-product-sheet.jpeg",
                "product_motion_rule": "Camera orbit rotates around the product to show the front face clearly.",
                "visible_product_text_or_marks": ["LUXE VIOLET"],
                "product_visual_facts": "Adds a gold metal plate on the front face and omits the BELLE wordmark.",
                "forbidden_visual_additions": "No cheap details.",
                "first_frame": "Purple bottle silhouette in mist.",
                "last_frame": "Full front hero view with LUXE VIOLET text on a gold metal plate.",
                "camera_plan": "The camera orbits as the product rotates into a full front packshot.",
                "subject_motion": "Product turns smoothly for a full reveal.",
                "environment_motion": "Violet reflections and petals move around the bottle.",
                "continuity_lock": "Keep a premium purple perfume look.",
                "visual_style": "Luxury purple fragrance TVC.",
                "negative_constraints": "No cheap look.",
            }
        ],
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
            "surface_text_inventory": [
                "GLISS LUMIERE",
                "AURORA SERIES",
                "ANDREA SECRET",
                "EAU DE TOILETTE",
                "100 mL",
            ],
            "embossed_or_relief_marks": ["no separate embossed emblem visible beyond supplied label marks"],
            "label_layout": "small top block, larger center block, vertical side text, small lower block",
            "packaging_shape": "tall slim rectangular transparent lavender-purple bottle with thick base and squared shoulders",
            "physical_component_inventory": [
                "transparent lavender-purple glass body",
                "thick rectangular base",
                "squared shoulders",
                "champagne-gold rounded cap",
                "visible internal spray tube",
                "printed front label only",
            ],
            "color_material_marks": "transparent lavender-purple glass body, champagne-gold rounded cap, visible internal spray tube",
            "required_visible_marks": ["rectangular body", "champagne-gold cap", "internal spray tube", "original label layout"],
            "forbidden_changes": ["generic purple bottle", "round bottle", "blank label", "fake label", "changed cap"],
            "forbidden_visual_additions": ["metal plate", "front plaque", "extra badge", "extra emblem", "new label panel"],
            "full_view_fidelity_rule": (
                "full product views must repeat the supplied bottle shape, label layout, visible text inventory, "
                "cap, spray tube, and no-extra-hardware surface exactly"
            ),
            "rigid_body_rule": "product visual facts remain the same; camera, mist, petals, reflections, and light carry motion",
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
                "product_motion_rule": "camera orbit and foreground glass reveal the product while preserving exact visual facts",
                "visible_product_text_or_marks": [
                    "GLISS LUMIERE",
                    "AURORA SERIES",
                    "ANDREA SECRET",
                    "EAU DE TOILETTE",
                    "100 mL",
                ],
                "product_visual_facts": (
                    "Tall slim rectangular transparent lavender-purple body, thick base, squared shoulders, "
                    "champagne-gold rounded cap, visible internal spray tube, original printed label layout, no metal plate."
                ),
                "forbidden_visual_additions": "No metal plate, no front plaque, no extra badge, no extra emblem, no new label panel.",
                "first_frame": "Lavender petal macro; product is not visible yet.",
                "last_frame": (
                    "The same real rectangular transparent lavender-purple bottle is visible front 3/4, "
                    "champagne-gold cap on, internal spray tube visible, original label layout in place."
                ),
                "camera_plan": (
                    "Camera slides past foreground glass, then makes a controlled orbit that shows the full bottle front."
                ),
                "subject_motion": (
                    "Product turns only as a photographed packshot object; label text, cap, spray tube, body shape, and surface components stay exact."
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
    def test_video_prompts_reject_product_segments_without_identity_lock(self) -> None:
        code, result = run_validator(make_bad_video_prompt())

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("product_identity_lock" in error for error in result["errors"]),
            result["errors"],
        )
        self.assertFalse(any("unsafe product rebuild language" in error for error in result["errors"]), result["errors"])

    def test_video_prompts_reject_wrong_text_and_invented_product_parts_on_full_view(self) -> None:
        code, result = run_validator(make_bad_visual_identity_prompt())

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("exact visible product text" in error for error in result["errors"]),
            result["errors"],
        )
        self.assertTrue(
            any("forbidden visual addition" in error for error in result["errors"]),
            result["errors"],
        )

    def test_video_prompts_pass_when_product_reference_and_rigid_motion_rules_are_locked(self) -> None:
        code, result = run_validator(make_locked_video_prompt())

        self.assertEqual(code, 0, result)
        self.assertTrue(result["ok"], result)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
