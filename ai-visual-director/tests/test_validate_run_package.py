#!/usr/bin/env python3
"""Regression tests for completed run-package validation."""

from __future__ import annotations

import importlib.util
import copy
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


def three_segment_video_prompt() -> dict:
    payload = video_helper.make_locked_video_prompt()
    base_segment = payload["segments"][0]
    segment_specs = [
        ("SEG_01", "0s-10s", ["SH_001", "SH_002", "SH_003", "SH_004"]),
        ("SEG_02", "10s-20s", ["SH_005", "SH_006", "SH_007"]),
        ("SEG_03", "20s-30s", ["SH_008", "SH_009"]),
    ]
    segments = []
    for segment_id, time_range, shot_ids in segment_specs:
        segment = copy.deepcopy(base_segment)
        segment["segment_id"] = segment_id
        segment["time_range"] = time_range
        segment["source_shots"] = shot_ids
        segment["story_beats"] = [f"{shot_id} executes its approved script beat" for shot_id in shot_ids]
        segment["internal_shots"] = [
            {
                "shot_id": shot_id,
                "time_span": f"{idx * 2}s-{idx * 2 + 2}s",
                "camera_state": "director-approved physical camera move for this source shot",
                "transition": "match movement through water, glass reflection, or product silhouette",
                "purpose": "execute the mapped storyboard panel while preserving product identity",
            }
            for idx, shot_id in enumerate(shot_ids)
        ]
        segment["first_frame"] = f"9:16 vertical frame: {shot_ids[0]} first approved storyboard state."
        segment["last_frame"] = f"9:16 vertical frame: {shot_ids[-1]} final approved storyboard state with temporal change."
        segment["visual_style"] = "Restrained vertical 9:16 product TVC; product identity outranks style references."
        segment["omni_prompt"] = (
            "Generate a 9:16 vertical Google Omni segment. "
            + segment["omni_prompt"]
        )
        segment["cut_strategy"] = "multi-shot segment with explicit internal_shots and time spans"
        segments.append(segment)
    payload["segments"] = segments
    return payload


def agent_orchestration_payload() -> dict:
    return {
        "schema_version": "1.0",
        "run_id": "test-run",
        "required_agents": [
            "creative_director_agent",
            "director_agent",
            "screenwriter_agent",
            "art_director_agent",
            "google_omni_prompt_expert_agent",
        ],
        "invocations": [
            {
                "agent": "creative_director_agent",
                "stage": "creative_concept",
                "status": "completed",
                "blocking": True,
                "started_after": ["product_identity_lock", "story_engine"],
                "input_refs": [
                    "00_route_decision.json",
                    "01_reference_roles.md",
                    "02_shot_plan.json#/story_engine",
                ],
                "output_refs": [
                    "02_shot_plan.json#/creative_concept_candidates",
                    "02_shot_plan.json#/creative_concept",
                ],
                "vetoes": [],
                "decision": "approved",
                "decision_summary": "Selected the droplet-reflection concept after comparing two routes.",
                "handoff_to": ["director_agent", "screenwriter_agent", "art_director_agent"],
                "consumed_by": [
                    "02_shot_plan.json#/concept_council",
                    "02_shot_plan.json#/timecoded_script_map",
                ],
            },
            {
                "agent": "director_agent",
                "stage": "director_resolution_and_video_approval",
                "status": "completed",
                "blocking": True,
                "started_after": ["creative_director_agent"],
                "input_refs": [
                    "02_shot_plan.json#/creative_concept",
                    "02_shot_plan.json#/timecoded_script_map",
                    "08_google_omni_video_prompts.json#/segments",
                ],
                "output_refs": [
                    "02_shot_plan.json#/concept_council",
                    "02_shot_plan.json#/director_script_approval",
                    "02_shot_plan.json#/storyboard_layout_decision",
                    "08_google_omni_video_prompts.json#/segments",
                ],
                "vetoes": [],
                "decision": "approved",
                "decision_summary": "Approved the script map, segment boards, and video prompt source-shot ranges.",
                "handoff_to": ["screenwriter_agent", "google_omni_prompt_expert_agent"],
                "consumed_by": [
                    "03_director_qc.json#/director_agent_evidence",
                    "08_google_omni_video_prompts.json#/agent_activation_ledger",
                ],
            },
            {
                "agent": "screenwriter_agent",
                "stage": "timecoded_script_map",
                "status": "completed",
                "blocking": True,
                "started_after": ["director_agent"],
                "input_refs": [
                    "02_shot_plan.json#/creative_concept",
                    "02_shot_plan.json#/story_engine",
                ],
                "output_refs": ["02_shot_plan.json#/timecoded_script_map"],
                "vetoes": [],
                "decision": "approved",
                "decision_summary": "Mapped the requested duration into three timecoded script beats.",
                "handoff_to": ["director_agent", "art_director_agent"],
                "consumed_by": [
                    "02_shot_plan.json#/director_script_approval",
                    "02_shot_plan.json#/sheets",
                ],
            },
            {
                "agent": "art_director_agent",
                "stage": "art_direction_veto",
                "status": "completed",
                "blocking": True,
                "started_after": ["creative_director_agent"],
                "input_refs": [
                    "01_reference_roles.md",
                    "02_shot_plan.json#/product_identity_lock",
                    "02_shot_plan.json#/creative_concept",
                ],
                "output_refs": [
                    "02_shot_plan.json#/concept_council",
                    "02_shot_plan.json#/product_identity_lock",
                ],
                "vetoes": [],
                "decision": "approved",
                "decision_summary": "Approved material, color, product-fidelity, and anti-plastic constraints.",
                "handoff_to": ["director_agent"],
                "consumed_by": [
                    "02_shot_plan.json#/storyboard_layout_decision",
                    "04_storyboard_image_prompts.md",
                ],
            },
            {
                "agent": "google_omni_prompt_expert_agent",
                "stage": "omni_prompt_translation",
                "status": "completed",
                "blocking": True,
                "started_after": ["director_agent", "validated_shot_plan"],
                "input_refs": [
                    "02_shot_plan.json#/sheets",
                    "08_google_omni_video_prompts.json#/required_reference_setup",
                ],
                "output_refs": [
                    "08_google_omni_video_prompts.json#/segments",
                    "08_google_omni_video_prompts.json#/segments/0/omni_prompt",
                ],
                "vetoes": [],
                "decision": "approved",
                "decision_summary": "Translated approved storyboard packets into Google Omni segment prompts.",
                "handoff_to": ["director_agent"],
                "consumed_by": [
                    "08_google_omni_video_prompts.md",
                    "11_video_generation_handoff.md",
                ],
            },
        ],
        "stage_gates": [
            {
                "gate": "before_concept_council",
                "requires_completed": ["creative_director_agent"],
                "next_step": "write_concept_council",
                "next_allowed": True,
                "blockers": [],
            },
            {
                "gate": "before_shot_plan",
                "requires_completed": [
                    "creative_director_agent",
                    "director_agent",
                    "screenwriter_agent",
                    "art_director_agent",
                ],
                "next_step": "write_02_shot_plan",
                "next_allowed": True,
                "blockers": [],
            },
            {
                "gate": "before_video_prompts",
                "requires_completed": ["director_agent", "google_omni_prompt_expert_agent"],
                "next_step": "write_08_google_omni_video_prompts",
                "next_allowed": True,
                "blockers": [],
            },
        ],
    }


def populate_run_dir(run_dir: Path, storyboard_prompt: str) -> None:
    shot_plan = shot_helper.make_plan(include_identity_lock=True)
    write_json(
        run_dir / "00_route_decision.json",
        {
            "project_type": "premium_product_ad",
            "production_mode": "standard_fast",
            "video_backend": "google_omni",
            "duration_seconds": 30,
            "requested_video_aspect_ratio": "9:16",
            "aspect_ratio_source": "brief.aspect_ratio",
            "aspect_contract": "panel_must_match_video_sheet_canvas_may_differ",
            "video_segment_seconds": 10,
            "storyboard_sheet_count": 3,
            "video_segment_count": 3,
            "storyboard_artifact_policy": "per_segment_dynamic_n_panel_storyboard",
            "panel_count_status": "deferred_to_director_after_script",
        },
    )
    write_text(run_dir / "01_reference_roles.md", "product_identity: serum-reference.jpg\n")
    write_json(run_dir / "02_shot_plan.json", shot_plan)
    write_json(
        run_dir / "03_director_qc.json",
        {
            "ok": True,
            "director_agent_evidence": {
                "agent_role": "director_agent",
                "evidence_refs": [
                    "05_agent_orchestration.json#/invocations/1",
                    "02_shot_plan.json#/director_script_approval",
                ],
            },
        },
    )
    write_text(run_dir / "04_storyboard_image_prompts.md", storyboard_prompt)
    write_json(run_dir / "05_agent_orchestration.json", agent_orchestration_payload())
    write_text(run_dir / "08_google_omni_video_prompts.md", "See structured JSON sidecar.\n")
    write_json(run_dir / "08_google_omni_video_prompts.json", three_segment_video_prompt())
    write_text(run_dir / "09_final_qc_report.md", "All required artifacts validated.\n")
    write_text(
        run_dir / "11_video_generation_handoff.md",
        """
# Video Generation Handoff

Use the original product image as the product identity reference. Paste the
Required Reference Setup and Product Identity Lock with exactly one segment
prompt at a time. The storyboard sheet is not the primary video-model input,
not the sole input, not a clip count, and not equal seconds per panel. Generate
or evaluate multi-segment runs separately before editing.
""",
    )


def valid_storyboard_prompt() -> str:
    return """
# Storyboard Sheet 01 Prompt

Panel Aspect Ratio: 9:16 for every storyboard cell. Sheet Canvas Aspect Ratio:
16:9 is allowed only as the outer contact-sheet canvas; do not mix horizontal
and vertical panel frames inside the sheet.

Story Engine: A clinical droplet teaches a reflective world to reveal the serum
only after its hydration logic is proven.
Creative Concept: A single clinical droplet teaches the world to behave like
the bottle's pale blue stripe.
World Rule: every reveal is caused by water, reflection, fingertip pressure, or
glass refraction, never by a random beauty pose.
Beat Map: origin droplet -> reflected cap clue -> withheld shoulder -> earned
full reveal -> label proof -> fingertip use -> hydration metaphor -> return
bridge -> final product authority.
Scene Ladder: clinical droplet world -> reflective tray threshold -> fingertip
interaction table -> hydration ripple world -> clean packshot memory space.
Visual Mechanism: droplet, tray reflection, label stripe, fingertip ripple, and
final packshot form one cause-and-effect chain.
Anti-plastic: real glass reflection, contact shadow, tactile tray edges,
physical water behavior, subtle paper grain, and restrained blue-gray graphite.

Product Lock Evidence: surface text inventory includes front wordmark LUMA,
center text HYDRATING SERUM, lower text 30 ml, centered front label rectangle,
and pale blue stripe; embossed or relief marks: none_visible.

Product Visibility Rhythm: SH_001 not_visible -> SH_002 detail_only -> SH_003
partial_visible -> SH_004 full_visible -> SH_005 detail_only -> SH_006
partial_visible -> SH_007 not_visible -> SH_008 partial_visible -> SH_009
full_visible.

Product Lock Evidence: surface text inventory includes front wordmark LUMA,
center text HYDRATING SERUM, lower text 30 ml, centered front label rectangle,
and pale blue stripe; embossed or relief marks: none_visible.

Panel plan:
- SH_001 [aspect_ratio: 9:16] [product_visibility: not_visible] [scene_arena: clinical droplet world]
  [scene_role: origin world] [dramatic_event: a suspended droplet trembles and
  establishes the water logic before any package appears] [visual_mechanism:
  droplet highlight foreshadows the pale blue label stripe]. No product, no
  bottle, no package, no label, and no product text in this panel.
- SH_002 [aspect_ratio: 9:16] [product_visibility: detail_only] [scene_arena: reflective tray
  threshold] [scene_role: material clue] [dramatic_event: the black cap edge
  arrives as a reflected clue before the full package is shown]
  [visual_mechanism: tray reflection turns the droplet highlight into a
  product-component reveal]. Draw only the rounded black cap edge and pale blue
  stripe reflection, not the full bottle.
- SH_003 [aspect_ratio: 9:16] [product_visibility: partial_visible] [scene_arena: reflective tray
  threshold] [scene_role: partial reveal] [dramatic_event: a cropped shoulder
  slides behind the tray rim and withholds the full bottle] [visual_mechanism:
  foreground tray occlusion turns the package into a withheld silhouette].
- SH_004 [aspect_ratio: 9:16] [product_visibility: full_visible] [scene_arena: reflective tray
  threshold] [scene_role: first full reveal] [dramatic_event: the tray
  reflection completes the silhouette and lets the first readable product view
  arrive] [visual_mechanism: the reflection opens like a stage slit]. Draw the
  exact LUMA / HYDRATING SERUM / 30 ml product with white cylindrical bottle,
  rounded black cap, front label rectangle, pale blue stripe, and no gold metal
  plate, no metal badge, no front plaque, no extra emblem.
- SH_005 [aspect_ratio: 9:16] [product_visibility: detail_only] [scene_arena: label stripe
  inspection] [scene_role: typography proof] [dramatic_event: macro focus tests
  the pale blue stripe and label rectangle as proof of product identity]
  [visual_mechanism: a moving specular line connects the stripe to the earlier
  droplet path].
- SH_006 [aspect_ratio: 9:16] [product_visibility: partial_visible] [scene_arena: fingertip
  interaction table] [scene_role: use action] [dramatic_event: a fingertip
  nudges only the cropped base so the object becomes tactile rather than
  worshipped] [visual_mechanism: fingertip pressure starts a rotation].
- SH_007 [aspect_ratio: 9:16] [product_visibility: not_visible] [scene_arena: hydration ripple world]
  [scene_role: benefit metaphor] [dramatic_event: the fingertip action resolves
  as a smooth water ripple with no package in frame] [visual_mechanism: the
  rotation energy transfers into a skin-like hydration ripple]. No product, no
  bottle, no package, no label, and no product text in this panel.
- SH_008 [aspect_ratio: 9:16] [product_visibility: partial_visible] [scene_arena: hydration ripple
  world] [scene_role: return bridge] [dramatic_event: the ripple reflection
  catches a cropped bottle silhouette and pulls the eye back to identity]
  [visual_mechanism: the circular ripple deforms into the product reflection].
- SH_009 [aspect_ratio: 9:16] [product_visibility: full_visible] [scene_arena: clean packshot memory
  space] [scene_role: final authority] [dramatic_event: the ripple energy stops
  and the product holds as the final memory image] [visual_mechanism: the
  reflected ripple becomes the stable base highlight]. Final front packshot of
  the exact LUMA / HYDRATING SERUM / 30 ml bottle, preserving the same white
  cylindrical bottle, rounded black cap, front label rectangle, pale blue stripe,
  and no gold metal plate, no metal badge, no front plaque, no extra emblem.
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

    def test_run_package_rejects_missing_agent_orchestration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            populate_run_dir(run_dir, valid_storyboard_prompt())
            (run_dir / "05_agent_orchestration.json").unlink()

            code, result = run_validator(run_dir)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("05_agent_orchestration.json" in error for error in result["errors"]),
            result["errors"],
        )

    def test_run_package_rejects_incomplete_agent_orchestration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            populate_run_dir(run_dir, valid_storyboard_prompt())
            orchestration = json.loads((run_dir / "05_agent_orchestration.json").read_text(encoding="utf-8"))
            orchestration["invocations"] = [
                invocation
                for invocation in orchestration["invocations"]
                if invocation["agent"] != "google_omni_prompt_expert_agent"
            ]
            write_json(run_dir / "05_agent_orchestration.json", orchestration)

            code, result = run_validator(run_dir)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("google_omni_prompt_expert_agent" in error for error in result["errors"]),
            result["errors"],
        )

    def test_run_package_rejects_director_qc_without_director_agent_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            populate_run_dir(run_dir, valid_storyboard_prompt())
            write_json(run_dir / "03_director_qc.json", {"ok": True})

            code, result = run_validator(run_dir)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("director_agent_evidence" in error for error in result["errors"]),
            result["errors"],
        )

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

    def test_run_package_rejects_storyboard_prompt_without_panel_aspect_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            prompt = valid_storyboard_prompt().replace("Panel Aspect Ratio: 9:16", "Panel Shape: mixed")
            prompt = prompt.replace("[aspect_ratio: 9:16] ", "")
            populate_run_dir(run_dir, prompt)

            code, result = run_validator(run_dir)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("Panel Aspect Ratio" in error or "aspect_ratio: 9:16" in error for error in result["errors"]),
            result["errors"],
        )

    def test_run_package_rejects_storyboard_prompt_without_creative_scene_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            populate_run_dir(
                run_dir,
                """
# Storyboard Sheet 01 Prompt

Product Visibility Rhythm: SH_001 not_visible -> SH_002 detail_only -> SH_003
partial_visible -> SH_004 full_visible -> SH_005 detail_only -> SH_006
partial_visible -> SH_007 not_visible -> SH_008 partial_visible -> SH_009
full_visible.

Product Lock Evidence: surface text inventory includes front wordmark LUMA,
center text HYDRATING SERUM, lower text 30 ml, centered front label rectangle,
and pale blue stripe; embossed or relief marks: none_visible.

Panel plan:
- SH_001 [product_visibility: not_visible]: no product, no bottle, no package.
- SH_002 [product_visibility: detail_only]: cap detail.
- SH_003 [product_visibility: partial_visible]: bottle crop.
- SH_004 [product_visibility: full_visible]: exact LUMA / HYDRATING SERUM / 30 ml bottle, white cylindrical bottle, rounded black cap, front label rectangle, pale blue stripe, no gold metal plate, no metal badge, no front plaque, no extra emblem.
- SH_005 [product_visibility: detail_only]: label detail.
- SH_006 [product_visibility: partial_visible]: base crop.
- SH_007 [product_visibility: not_visible]: no product, no bottle, no package.
- SH_008 [product_visibility: partial_visible]: reflected bottle crop.
- SH_009 [product_visibility: full_visible]: exact LUMA / HYDRATING SERUM / 30 ml bottle, white cylindrical bottle, rounded black cap, front label rectangle, pale blue stripe, no gold metal plate, no metal badge, no front plaque, no extra emblem.
""",
            )

            code, result = run_validator(run_dir)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("Creative Concept" in error or "scene_arena" in error for error in result["errors"]),
            result["errors"],
        )

    def test_run_package_rejects_markdown_only_video_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            populate_run_dir(run_dir, valid_storyboard_prompt())
            (run_dir / "08_google_omni_video_prompts.json").unlink()

            code, result = run_validator(run_dir)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("structured video prompt JSON" in error for error in result["errors"]),
            result["errors"],
        )

    def test_run_package_rejects_missing_video_generation_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            populate_run_dir(run_dir, valid_storyboard_prompt())
            (run_dir / "11_video_generation_handoff.md").unlink()

            code, result = run_validator(run_dir)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("11_video_generation_handoff.md" in error for error in result["errors"]),
            result["errors"],
        )

    def test_run_package_rejects_handoff_that_uses_storyboard_as_video_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            populate_run_dir(run_dir, valid_storyboard_prompt())
            write_text(
                run_dir / "11_video_generation_handoff.md",
                """
# Video Generation Handoff

Upload the fixed-grid storyboard sheet and ask the video model to make the whole
30-second film from the grid.
""",
            )

            code, result = run_validator(run_dir)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("primary/sole video-model input" in error for error in result["errors"]),
            result["errors"],
        )

    def test_run_package_rejects_three_segment_route_with_one_storyboard_sheet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            populate_run_dir(run_dir, valid_storyboard_prompt())
            write_json(
                run_dir / "00_route_decision.json",
                {
                    "project_type": "premium_product_ad",
                    "production_mode": "standard_fast",
                    "video_backend": "google_omni",
                    "duration_seconds": 30,
                    "video_segment_seconds": 10,
                    "storyboard_sheet_count": 1,
                    "video_segment_count": 3,
                },
            )

            code, result = run_validator(run_dir)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("storyboard_sheet_count must equal video_segment_count" in error for error in result["errors"]),
            result["errors"],
        )

    def test_run_package_rejects_route_owned_tempo_panel_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            populate_run_dir(run_dir, valid_storyboard_prompt())
            write_json(
                run_dir / "00_route_decision.json",
                {
                    "project_type": "premium_product_ad",
                    "production_mode": "standard_fast",
                    "video_backend": "google_omni",
                    "duration_seconds": 30,
                    "video_segment_seconds": 10,
                    "storyboard_sheet_count": 3,
                    "video_segment_count": 3,
                    "tempo_profile": "medium",
                    "panel_count": 17,
                    "panel_count_source": "legacy_duration_tempo_estimate",
                    "panels_per_sheet": [17],
                    "grid_layouts": ["legacy_fixed_grid"],
                    "shots_per_video_segment": [5, 5, 5],
                },
            )

            code, result = run_validator(run_dir)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("director/shot-plan owned" in error for error in result["errors"]),
            result["errors"],
        )

    def test_run_package_rejects_route_and_shot_plan_aspect_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            populate_run_dir(run_dir, valid_storyboard_prompt())
            shot_plan_path = run_dir / "02_shot_plan.json"
            shot_plan = json.loads(shot_plan_path.read_text(encoding="utf-8"))
            shot_plan["requested_video_aspect_ratio"] = "16:9"
            for sheet in shot_plan["sheets"]:
                sheet["panel_aspect_ratio"] = "16:9"
                for shot in sheet["shots"]:
                    shot["aspect_ratio"] = "16:9"
            write_json(shot_plan_path, shot_plan)

            code, result = run_validator(run_dir)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("requested_video_aspect_ratio" in error for error in result["errors"]),
            result["errors"],
        )


if __name__ == "__main__":
    raise SystemExit(unittest.main())
