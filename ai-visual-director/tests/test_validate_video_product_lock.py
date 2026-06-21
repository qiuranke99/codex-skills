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


def make_video_story() -> dict:
    return {
        "logline": "A locked product identity emerges from a tactile material world and becomes the final authority frame.",
        "story_arc": ["material omen", "earned product reveal", "settled identity payoff"],
        "world_rule": "Reflections and foreground glass reveal the product; the package never builds itself from mist.",
        "emotional_turn": "The viewer moves from curiosity to confidence when the exact package resolves.",
        "duration_strategy": "One 10-second segment can carry multiple controlled source shots when time spans and transitions are explicit.",
        "anti_plastic_strategy": "Use real glass thickness, contact shadows, imperfect specular edges, lens softness, and restrained film grain to avoid waxy plastic CGI.",
    }


def video_agent_ledger() -> list[dict]:
    return [
        {
            "agent_role": "director_agent",
            "stage": "video_prompt_approval",
            "started_at": "2026-06-21T00:04:00Z",
            "input_evidence": [
                "02_shot_plan.json#/sheets",
                "02_shot_plan.json#/storyboard_layout_decision",
            ],
            "output_evidence": [
                "08_google_omni_video_prompts.json#/segments",
                "08_google_omni_video_prompts.json#/segments/0/source_shots",
            ],
            "decision_summary": "Approved the segment source-shot ranges and video prompt direction.",
            "status": "completed",
            "blocks_next_stage_until": "director-approved source_shots and segments exist",
        },
        {
            "agent_role": "google_omni_prompt_expert_agent",
            "stage": "omni_prompt_translation",
            "started_at": "2026-06-21T00:05:00Z",
            "input_evidence": [
                "02_shot_plan.json#/sheets",
                "08_google_omni_video_prompts.json#/required_reference_setup",
            ],
            "output_evidence": [
                "08_google_omni_video_prompts.json#/segments",
                "08_google_omni_video_prompts.json#/segments/0/omni_prompt",
            ],
            "decision_summary": "Translated director-approved storyboard packets into Google Omni segment prompts.",
            "status": "completed",
            "blocks_next_stage_until": "paste-ready segment prompts exist",
        },
    ]


def make_bad_video_prompt() -> dict:
    return {
        "video_story": make_video_story(),
        "segments": [
            {
                "segment_id": "SEG_01_0s_10s",
                "time_range": "0s-10s",
                "purpose": "Create a high-end purple perfume mood reveal.",
                "source_shots": ["SH_001", "SH_002", "SH_003"],
                "first_frame": "Purple mist and petals in darkness.",
                "last_frame": "A luxurious purple perfume object appears in a hero frame.",
                "story_beats": ["mist omen", "bottle appears", "hero hold"],
                "camera_plan": "The bottle rises from mist, rotates slowly, and becomes the central object.",
                "cut_strategy": "single reveal move, no hard cuts",
                "subject_motion": "The cap separates slightly and the perfume bottle forms from light.",
                "environment_motion": "Violet petals and reflections swirl around the product.",
                "motion_continuity": "Mist moves into the reveal, then settles.",
                "continuity_lock": "Keep a high-end purple perfume atmosphere.",
                "visual_style": "Luxury purple fragrance ad.",
                "anti_plastic_constraints": "Real glass surface, contact shadows, lens softness, and subtle grain; avoid waxy plastic CGI.",
                "omni_prompt": "A purple perfume object rises from mist as the camera pushes in; petals move around real glass with subtle grain.",
                "negative_constraints": "No cheap look, no waxy plastic CGI.",
            }
        ]
    }


def make_bad_visual_identity_prompt() -> dict:
    return {
        "video_story": make_video_story(),
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
                "story_beats": ["silhouette", "orbit reveal", "front hero view"],
                "camera_plan": "The camera orbits as the product rotates into a full front packshot.",
                "cut_strategy": "single orbit reveal",
                "subject_motion": "Product turns smoothly for a full reveal.",
                "environment_motion": "Violet reflections and petals move around the bottle.",
                "motion_continuity": "The orbit continues from silhouette to front view without a jump.",
                "continuity_lock": "Keep a premium purple perfume look.",
                "visual_style": "Luxury purple fragrance TVC.",
                "anti_plastic_constraints": "Real glass thickness, contact shadows, lens softness, and restrained grain; avoid waxy plastic CGI.",
                "omni_prompt": "The camera orbits a purple bottle from silhouette to front hero view while reflections and petals move around real glass.",
                "negative_constraints": "No cheap look, no waxy plastic CGI.",
            }
        ],
    }


def make_locked_video_prompt() -> dict:
    return {
        "requested_video_aspect_ratio": "9:16",
        "video_story": make_video_story(),
        "agent_activation_ledger": video_agent_ledger(),
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
                "aspect_ratio": "9:16",
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
                "first_frame": "9:16 vertical lavender petal macro; product is not visible yet.",
                "last_frame": (
                    "The same real rectangular transparent lavender-purple bottle is visible front 3/4 in a 9:16 vertical frame, "
                    "champagne-gold cap on, internal spray tube visible, original label layout in place."
                ),
                "story_beats": [
                    "foreground petal macro with no product",
                    "glass slide reveals the locked bottle silhouette",
                    "front 3/4 product identity settles into the authority frame",
                ],
                "internal_shots": [
                    {
                        "shot_id": "SH_001",
                        "time_span": "0s-3s",
                        "camera_state": "macro slide across lavender petal and foreground glass",
                        "transition": "glass refraction carries the motion into the next source shot",
                        "purpose": "open with material atmosphere before product visibility",
                    },
                    {
                        "shot_id": "SH_002",
                        "time_span": "3s-7s",
                        "camera_state": "controlled slide past foreground glass toward the locked bottle silhouette",
                        "transition": "same lateral camera energy becomes a restrained orbit",
                        "purpose": "reveal product form without changing package facts",
                    },
                    {
                        "shot_id": "SH_003",
                        "time_span": "7s-10s",
                        "camera_state": "slow orbit settles into a readable front three-quarter authority frame",
                        "transition": "motion settles into a final product hold",
                        "purpose": "lock final visible product identity and label layout",
                    },
                ],
                "camera_plan": (
                    "Camera slides past foreground glass, then makes a controlled orbit that shows the full bottle front."
                ),
                "cut_strategy": "one continuous reveal with three internal beats; no full contact-sheet dump",
                "subject_motion": (
                    "Product turns only as a photographed packshot object; label text, cap, spray tube, body shape, and surface components stay exact."
                ),
                "environment_motion": "Mist, petals, reflections, and glass ribbons move around the locked product.",
                "motion_continuity": "The foreground glass slide motivates the orbit, and the orbit settles into the final readable packshot.",
                "continuity_lock": (
                    "Hard-lock to Belle-purple-product-sheet.jpeg: tall slim rectangular purple transparent body, "
                    "thick base, squared shoulders, champagne-gold cap, internal spray tube, original label layout."
                ),
                "visual_style": "Restrained violet fragrance TVC; product identity outranks style references.",
                "anti_plastic_constraints": (
                    "Real glass thickness, contact shadows under the bottle, imperfect specular edges, restrained lens softness, "
                    "subtle film grain, and physical mist depth; avoid waxy plastic CGI and over-smoothed reflections."
                ),
                "omni_prompt": (
                    "A lavender petal macro opens the shot with no product visible. The camera slides past foreground glass, "
                    "then makes a controlled orbit revealing the same real rectangular transparent lavender-purple bottle; mist, "
                    "petals, and reflections move around it while label layout, champagne-gold cap, internal spray tube, and body "
                    "proportions stay locked. The shot settles on a readable front 3/4 authority frame with real glass thickness, "
                    "contact shadows, subtle grain, and no waxy plastic CGI."
                ),
                "negative_constraints": (
                    "No generic purple bottle, no blank label, no fake text, no new brand, no changed cap, "
                    "no cap removal, no product morphing, no product spin, no duplicate bottle, no waxy plastic CGI."
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

    def test_video_prompts_reject_segment_aspect_ratio_mismatch(self) -> None:
        payload = make_locked_video_prompt()
        payload["segments"][0]["aspect_ratio"] = "16:9"

        code, result = run_validator(payload)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("aspect_ratio" in error for error in result["errors"]),
            result["errors"],
        )

    def test_video_prompts_require_prompt_expert_and_director_activation(self) -> None:
        payload = make_locked_video_prompt()
        payload["agent_activation_ledger"] = [
            entry
            for entry in payload["agent_activation_ledger"]
            if entry["agent_role"] != "google_omni_prompt_expert_agent"
        ]

        code, result = run_validator(payload)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("google_omni_prompt_expert_agent" in error for error in result["errors"]),
            result["errors"],
        )

    def test_video_prompts_reject_simulated_prompt_expert(self) -> None:
        payload = make_locked_video_prompt()
        payload["agent_activation_ledger"][1]["status"] = "simulated"

        code, result = run_validator(payload)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("status must be completed" in error for error in result["errors"]),
            result["errors"],
        )

    def test_video_prompts_reject_dense_panel_dump_without_internal_shot_timing(self) -> None:
        payload = make_locked_video_prompt()
        segment = payload["segments"][0]
        segment["source_shots"] = [f"SH_{idx:03d}" for idx in range(1, 10)]
        segment["story_beats"] = [f"panel {idx} cut" for idx in range(1, 10)]
        segment.pop("internal_shots", None)

        code, result = run_validator(payload)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("multi-shot segment requires internal_shots" in error or "dense storyboard-panel list" in error for error in result["errors"]),
            result["errors"],
        )

    def test_video_prompts_allow_controlled_multi_shot_ten_second_segment(self) -> None:
        payload = make_locked_video_prompt()
        segment = payload["segments"][0]
        segment["source_shots"] = [f"SH_{idx:03d}" for idx in range(1, 8)]
        segment["story_beats"] = [
            "petal macro wipes left to right",
            "glass ridge catches lavender refraction",
            "partial bottle edge enters through foreground blur",
            "label-side silhouette crosses a specular streak",
            "cap highlight resolves as the camera arcs",
            "full 3/4 bottle locks into readable identity",
            "final authority hold with mist settling behind the product",
        ]
        segment["internal_shots"] = [
            {
                "shot_id": f"SH_{idx:03d}",
                "time_span": f"{idx - 1}.0s-{idx}.2s",
                "camera_state": "controlled slide/orbit with physical lens motion",
                "transition": "match movement through glass reflection",
                "purpose": "advance the reveal while preserving product identity",
            }
            for idx in range(1, 8)
        ]
        segment["cut_strategy"] = "seven controlled internal shots with time spans, reflection-motivated transitions, and a final readable product hold"

        code, result = run_validator(payload)

        self.assertEqual(code, 0, result)
        self.assertTrue(result["ok"], result)

    def test_video_prompts_reject_static_first_last_frame(self) -> None:
        payload = make_locked_video_prompt()
        segment = payload["segments"][0]
        segment["last_frame"] = segment["first_frame"]

        code, result = run_validator(payload)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("first_frame and last_frame cannot be identical" in error for error in result["errors"]),
            result["errors"],
        )


if __name__ == "__main__":
    raise SystemExit(unittest.main())
