#!/usr/bin/env python3
"""Regression tests for product identity fidelity in shot plans."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL_DIR / "scripts" / "validate_shot_plan.py"


def base_shot(idx: int) -> dict:
    shot_sizes = [
        "wide establishing shot",
        "extreme close-up macro insert",
        "medium close-up",
        "close-up insert",
        "overhead product insert",
        "low-angle hero product shot",
        "macro label detail close-up",
        "medium shot",
        "final packshot close-up",
    ]
    angles = [
        "eye-level wide angle",
        "top overhead angle",
        "low angle from table height",
        "high angle looking down",
        "ground-level angle",
        "low three-quarter angle",
        "straight-on macro angle",
        "side angle",
        "front eye-level packshot angle",
    ]
    movements = [
        "locked-off",
        "slow dolly-in",
        "tilt-down reveal",
        "locked-off",
        "slow lateral slide",
        "push-in",
        "locked-off macro hold",
        "handheld follow",
        "slow push-in",
    ]
    return {
        "shot_id": f"SH_{idx:03d}",
        "aspect_ratio": "16:9",
        "scene": "blue-gray product world with white serum bottle on reflective tray",
        "duration": "1.5s",
        "shot_purpose": "show the user-provided serum bottle as the commercial identity anchor",
        "shot_size": shot_sizes[idx - 1],
        "camera_angle": angles[idx - 1],
        "lens_feel": "slightly wide product-table spatial feel",
        "camera_movement": movements[idx - 1],
        "cut_logic": "advance from product world to package proof and final payoff",
        "attention_order": "first product silhouette, second label panel, third reflective tray",
        "eye_trace": "viewer enters on bottle shoulder, drops to label panel, exits toward tray edge",
        "depth_strategy": "foreground tray rim, midground product bottle, background soft glass forms",
        "reference_parity": "preserve product bottle proportion and front label placement from the user reference",
        "main_subject": "user-provided serum bottle product",
        "main_action": "product remains upright while light sweeps across the front label area",
        "body_pose": "not applicable for product-only shot",
        "composition": "product sits on right third with label area facing camera and negative space left",
        "foreground": "blurred reflective tray rim",
        "midground": "single serum bottle with front label panel",
        "background": "soft vertical glass blocks",
        "scale_reference": "hand-sized bottle beside fingertip-height tray edge",
        "continuity_lock": "same user-provided bottle shape, cap, label panel, and front-facing orientation",
        "must_preserve": "same product silhouette and white bottle body",
        "avoid": "avoid extra bottles, fake logos, blank generic cosmetics, or changed packaging",
    }


def make_plan(include_identity_lock: bool) -> dict:
    plan = {
        "project_title": "Serum product ad",
        "project_type": "premium_product_ad",
        "duration_seconds": 12,
        "storyboard_sheet_count": 1,
        "panel_count": 9,
        "video_segment_count": 2,
        "continuity_locks": ["same user-provided serum bottle throughout"],
        "reference_roles": [
            {
                "image": "serum-reference.jpg",
                "role": "product_identity",
                "must_preserve": ["bottle shape", "cap", "front label"],
            }
        ],
        "sheets": [
            {
                "sheet_id": "sheet_01",
                "time_range": "0s-12s",
                "beat": "product identity and label proof",
                "shots": [base_shot(i) for i in range(1, 10)],
            }
        ],
    }
    if include_identity_lock:
        plan["product_identity_lock"] = {
            "source_reference": "serum-reference.jpg",
            "product_name_text": "LUMA",
            "primary_label_text": ["LUMA", "HYDRATING SERUM", "30 ml"],
            "surface_text_inventory": ["front wordmark LUMA", "center text HYDRATING SERUM", "lower text 30 ml"],
            "embossed_or_relief_marks": ["none_visible"],
            "label_layout": "white front label rectangle centered on the bottle face",
            "packaging_shape": "tall cylindrical white bottle with rounded black cap",
            "physical_component_inventory": ["white cylindrical bottle", "rounded black cap", "front label rectangle"],
            "color_material_marks": "white bottle, black cap, pale blue label stripe",
            "required_visible_marks": ["LUMA wordmark", "HYDRATING SERUM line", "30 ml line"],
            "forbidden_changes": ["blank bottle", "fake brand", "new label layout", "extra claims"],
            "forbidden_visual_additions": ["gold metal plate", "metal badge", "front plaque", "extra emblem"],
            "full_view_fidelity_rule": (
                "full product views must show the exact LUMA / HYDRATING SERUM / 30 ml text, "
                "same white bottle, same black cap, same label geometry, and no extra hardware"
            ),
        }
        for shot in plan["sheets"][0]["shots"]:
            shot["product_visibility"] = "full_visible"
            shot["product_identity_action"] = (
                "draw the locked bottle shape with the front label panel and exact supplied label text blocks"
            )
            shot["visible_product_text_or_marks"] = ["LUMA", "HYDRATING SERUM", "30 ml"]
            shot["product_visual_facts"] = (
                "same white cylindrical bottle, rounded black cap, centered front label rectangle, "
                "LUMA wordmark, HYDRATING SERUM line, 30 ml line, pale blue stripe, no gold metal plate"
            )
            shot["forbidden_visual_additions"] = "No gold metal plate, no metal badge, no front plaque, no extra emblem."
            shot["must_preserve"] = (
                "same product silhouette, white bottle body, black cap, front label layout, "
                "LUMA wordmark, HYDRATING SERUM text, and 30 ml line"
            )
    return plan


def run_validator(plan: dict) -> tuple[int, dict]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "shot_plan.json"
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), str(path)],
            text=True,
            capture_output=True,
            check=False,
        )
    return proc.returncode, json.loads(proc.stdout)


class ProductIdentityLockTests(unittest.TestCase):
    def test_product_ads_require_top_level_product_identity_lock(self) -> None:
        code, result = run_validator(make_plan(include_identity_lock=False))

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("product_identity_lock" in error for error in result["errors"]),
            result["errors"],
        )

    def test_product_ads_pass_when_product_identity_lock_and_shot_actions_exist(self) -> None:
        code, result = run_validator(make_plan(include_identity_lock=True))

        self.assertEqual(code, 0, result)
        self.assertTrue(result["ok"], result)

    def test_product_ads_require_visual_fact_inventory_in_identity_lock(self) -> None:
        plan = make_plan(include_identity_lock=True)
        del plan["product_identity_lock"]["surface_text_inventory"]

        code, result = run_validator(plan)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("surface_text_inventory" in error for error in result["errors"]),
            result["errors"],
        )

    def test_storyboard_rejects_wrong_visible_text_and_invented_product_parts(self) -> None:
        plan = make_plan(include_identity_lock=True)
        shot = plan["sheets"][0]["shots"][-1]
        shot["visible_product_text_or_marks"] = ["LUMA"]
        shot["product_visual_facts"] = (
            "white bottle with a centered gold metal plate and simplified front branding"
        )
        shot["composition"] = "front packshot shows a gold metal plate as the main label area"
        shot["must_preserve"] = "same bottle silhouette with LUMA visible"

        code, result = run_validator(plan)

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


if __name__ == "__main__":
    raise SystemExit(unittest.main())
