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
        "aspect_ratio": "9:16",
        "scene": "cool pearl product world with white serum bottle on reflective tray",
        "arc_position": [
            "origin",
            "material clue",
            "withheld reveal",
            "first identity reveal",
            "identity proof",
            "use action",
            "benefit metaphor",
            "return bridge",
            "final authority",
        ][idx - 1],
        "story_beat": [
            "water establishes the world rule before the product appears",
            "the cap edge appears only as a reflected clue",
            "the product shoulder is withheld by foreground tray geometry",
            "the first readable full product view is earned by reflection",
            "label stripe and text become tactile material proof",
            "a fingertip makes the product feel usable rather than worshipped",
            "the use action becomes a hydration ripple with no product in frame",
            "the ripple reflection pulls the eye back toward the package",
            "the exact product resolves into the final memory image",
        ][idx - 1],
        "duration": "1.5s",
        "shot_purpose": "show the user-provided serum bottle as the commercial identity anchor",
        "shot_size": shot_sizes[idx - 1],
        "camera_angle": angles[idx - 1],
        "lens_feel": "slightly wide product-table spatial feel",
        "lens_progression_role": [
            "open from product absence with wide spatial pressure before any pack recognition",
            "compress into macro component proof so the cap clue earns attention",
            "shift to low occluded partial view to withhold full identity",
            "expand into first readable product authority after the reflection cue",
            "return to macro inspection for typography and material proof",
            "drop into tactile use proximity so the product becomes handled, not worshipped",
            "remove product coverage and let benefit metaphor carry the rhythm",
            "bridge from metaphor back into cropped product memory",
            "settle into final front authority after the prior proof beats",
        ][idx - 1],
        "camera_movement": movements[idx - 1],
        "camera_motivation": "camera movement follows the water/reflection rule instead of circling the product arbitrarily",
        "motivated_camera_path": "camera reveals, withholds, or follows the water/reflection rule that causes this exact beat",
        "coverage_strategy": "withhold full product coverage until proof and ritual beats earn each readable view",
        "motion_continuity": "each motion inherits energy from the prior droplet, tray, fingertip, or ripple beat",
        "material_truth": "real glass reflections, contact shadows, tactile tray edges, and restrained graphite storyboard texture avoid waxy CGI",
        "transition_in": "enter through a matched droplet, reflection, cap edge, or ripple direction from the prior shot",
        "transition_out": "exit by handing the eye to the next water, glass, product, or fingertip motion cue",
        "edit_bridge": "material highlight and motion direction bridge this cut to the next proof beat",
        "shot_to_shot_causality": "this shot changes what the next shot is allowed to reveal about product, ritual, or benefit",
        "cut_logic": "advance from product world to package proof and final payoff",
        "attention_order": "first product silhouette, second label panel, third reflective tray",
        "eye_trace": "viewer enters on bottle shoulder, drops to label panel, exits toward tray edge",
        "depth_strategy": "foreground tray rim, midground product bottle, background soft glass forms",
        "reference_parity": "preserve product bottle proportion and front label placement from the user reference",
        "reference_transform": [
            "translate the reference's hard diagonal platform into a water-reflection threshold, not the same white plinth",
            "turn the reference's red field into a pale clinical stripe of light that controls the reveal",
            "convert the product-on-corner isolation into a withheld reflection sequence",
            "use the reference's metallic/specular tension as tactile label proof instead of another lipstick-on-step angle",
            "move from reference geometry into fingertip interaction so the shot adds story information",
            "transform product solitude into a use-action proof, not another centered object portrait",
            "convert the reference's empty red negative space into a product-absent hydration metaphor",
            "bend the reference's diagonal ledge into a circular ripple return path",
            "resolve the reference's hero isolation as a final earned vertical packshot",
        ][idx - 1],
        "reference_to_world_transformation": "turn reference geometry into a clinical skincare counter world governed by water, tray reflection, and touch",
        "invented_scene_architecture": "reflective tester counter, tray threshold, fingertip table, ripple surface, and clean packshot memory space",
        "prop_logic": "tray, tester surface, droplet, fingertip, and reflection each prove a purchase or use ritual beat",
        "material_system": "etched glass, pearl-white bottle, black cap edge, pale blue stripe, water meniscus, contact shadow, and soft clinical bounce",
        "category_coded_restraint": "no flowers, no fake lab screen, no miracle claim typography, no extra badges, no influencer mirror clutter",
        "set_piece_invention": "the tray reflection and ripple repeatedly reshape into the bottle silhouette before the final authority frame",
        "shot_function_signature": {
            "information_delta": [
                "introduce the water rule before the viewer sees any product",
                "reveal one real component clue: black cap edge and pale blue stripe reflection",
                "show that the product exists but withhold the readable package",
                "answer the first identity question with a readable full product view",
                "prove label geometry and stripe material at inspection distance",
                "change product role from display object to touched usable object",
                "remove the product to show the benefit metaphor caused by the use action",
                "return the viewer from benefit metaphor to product identity through reflection",
                "resolve all prior clues into the final exact front-facing product memory",
            ][idx - 1],
            "desire_delta": [
                "create curiosity through absence and controlled negative space",
                "raise desire by showing a precise component without satisfying the full reveal",
                "increase anticipation through occlusion and cropped product presence",
                "satisfy identity curiosity while opening the need for proof",
                "shift desire from appearance to tactile product credibility",
                "make the product feel usable and close to skin",
                "turn desire into imagined hydration benefit",
                "pull benefit desire back toward purchase object",
                "convert desire into final product authority and recall",
            ][idx - 1],
            "purchase_ritual_delta": [
                "introduce the silent counter before the tester object appears",
                "show a component clue like a tester inspection moment",
                "withhold full package as the viewer scans for identity",
                "complete the first product recognition moment",
                "turn label inspection into counter-level proof",
                "move from looking to handled use",
                "pause purchase object so benefit can be imagined",
                "return benefit memory toward the object",
                "resolve into the product the viewer would recognize on shelf",
            ][idx - 1],
            "shelf_memory_delta": [
                "seed pearl-white and pale-blue vertical memory without showing the bottle",
                "attach the black cap edge to the pale-blue stripe clue",
                "make the cropped cylinder silhouette memorable",
                "connect silhouette, stripe, and label into first recognition",
                "reinforce the label rectangle and stripe as mnemonic marks",
                "associate touch with the cylindrical base",
                "replace object with a circular hydration memory",
                "pull the memory back into bottle reflection",
                "lock the front product view as final recall",
            ][idx - 1],
            "ritual_proof_delta": [
                "water behavior sets up credible skincare ritual proof",
                "component clue proves physical packaging material",
                "occlusion keeps proof incomplete until reveal",
                "full reveal proves package identity before use proof",
                "macro label and stripe prove inspection-grade identity",
                "fingertip pressure proves use proximity",
                "ripple proves sensorial benefit without a medical claim",
                "reflection proves benefit memory returns to product",
                "final hold proves purchase authority without overclaim",
            ][idx - 1],
            "claim_safety": "show hydration ritual and tactile proof visually without making medical or quantified skin claims",
            "product_role_delta": [
                "product absent as a withheld promise",
                "product appears only as component evidence",
                "product becomes partial silhouette evidence",
                "product becomes first readable identity",
                "product becomes typography and material proof",
                "product becomes touched-use proof",
                "product absent so benefit can occupy the frame",
                "product returns as reflected memory",
                "product becomes final purchase authority",
            ][idx - 1],
            "event_type": [
                "origin_rule",
                "component_clue",
                "withheld_reveal",
                "identity_reveal",
                "material_proof",
                "use_action",
                "benefit_metaphor",
                "return_bridge",
                "final_authority",
            ][idx - 1],
            "camera_relation_key": [
                "vertical_negative_space_wide",
                "top_macro_component_insert",
                "low_occluded_partial",
                "three_quarter_first_read",
                "overhead_label_macro",
                "low_touch_partial",
                "abstract_surface_close",
                "side_reflection_crop",
                "front_vertical_packshot",
            ][idx - 1],
            "reference_transform_id": f"RT_{idx:03d}",
            "redundancy_risk": [
                "could become empty mood if the water rule is not legible",
                "could become another macro beauty detail unless it reveals only one component clue",
                "could repeat plinth geometry unless foreground occlusion changes the story information",
                "could become early packshot wall unless followed by proof and use beats",
                "could repeat typography glamour unless it tests exact label facts",
                "could become generic hand beauty unless contact changes product role",
                "could feel unrelated unless motion continuity carries the fingertip energy",
                "could repeat product silhouette unless reflection explicitly bridges benefit back to identity",
                "could repeat the first reveal unless it resolves all prior clues as final authority",
            ][idx - 1],
        },
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


def shot_plan_agent_ledger() -> list[dict]:
    return [
        {
            "agent_role": "creative_director_agent",
            "stage": "creative_concept",
            "started_at": "2026-06-21T00:00:00Z",
            "input_evidence": [
                "00_route_decision.json",
                "01_reference_roles.md",
                "02_shot_plan.json#/story_engine",
            ],
            "output_evidence": [
                "02_shot_plan.json#/creative_concept_candidates",
                "02_shot_plan.json#/creative_concept",
                "02_shot_plan.json#/reference_deconstruction",
            ],
            "decision_summary": "Generated two concept candidates and selected the droplet-reflection concept.",
            "status": "completed",
            "blocks_next_stage_until": "creative_concept_candidates and creative_concept exist",
        },
        {
            "agent_role": "director_agent",
            "stage": "director_resolution",
            "started_at": "2026-06-21T00:01:00Z",
            "input_evidence": [
                "02_shot_plan.json#/creative_concept_candidates",
                "02_shot_plan.json#/timecoded_script_map",
            ],
            "output_evidence": [
                "02_shot_plan.json#/concept_council",
                "02_shot_plan.json#/director_script_approval",
                "02_shot_plan.json#/storyboard_layout_decision",
            ],
            "decision_summary": "Approved the script map and the 4/3/2 segment panel rhythm.",
            "status": "completed",
            "blocks_next_stage_until": "director approval and layout decision exist",
        },
        {
            "agent_role": "screenwriter_agent",
            "stage": "timecoded_script_map",
            "started_at": "2026-06-21T00:02:00Z",
            "input_evidence": [
                "02_shot_plan.json#/creative_concept",
                "02_shot_plan.json#/story_engine",
            ],
            "output_evidence": ["02_shot_plan.json#/timecoded_script_map"],
            "decision_summary": "Mapped the 30-second film into three executable timecoded script beats.",
            "status": "completed",
            "blocks_next_stage_until": "timecoded_script_map exists",
        },
        {
            "agent_role": "art_director_agent",
            "stage": "art_direction_veto",
            "started_at": "2026-06-21T00:03:00Z",
            "input_evidence": [
                "01_reference_roles.md",
                "02_shot_plan.json#/product_identity_lock",
                "02_shot_plan.json#/creative_concept",
            ],
            "output_evidence": [
                "02_shot_plan.json#/concept_council",
                "02_shot_plan.json#/product_identity_lock",
                "02_shot_plan.json#/reference_deconstruction",
            ],
            "decision_summary": "Approved material, color, product-fidelity, and anti-plastic constraints.",
            "status": "completed",
            "blocks_next_stage_until": "art-direction veto is resolved",
        },
    ]


def make_plan(include_identity_lock: bool) -> dict:
    shots = [base_shot(i) for i in range(1, 10)]
    plan = {
        "project_title": "Serum product ad",
        "project_type": "premium_product_ad",
        "duration_seconds": 30,
        "requested_video_aspect_ratio": "9:16",
        "storyboard_sheet_count": 3,
        "panel_count": 9,
        "panels_per_sheet": [4, 3, 2],
        "grid_layouts": ["2x2", "1x3", "1x2"],
        "shots_per_video_segment": [4, 3, 2],
        "video_segment_count": 3,
        "agent_activation_ledger": shot_plan_agent_ledger(),
        "category_strategy": {
            "category_truth": "premium skincare sells credible ritual proof, tactile control, and repeatable shelf memory rather than fantasy cure",
            "purchase_ritual": "the counter tester moment moves from silent shelf scan to one-pump tactile proof and final pack recognition",
            "shelf_memory": "white cylindrical bottle, black cap edge, pale blue stripe, and vertical label rectangle return as a repeated memory system",
            "ritual_proof": "water meniscus, fingertip pressure, label inspection, and reflection behavior prove hydration through visible ritual",
            "brand_altitude": "prestige clinical skincare: restrained, precise, cool, sensorial, and never loud or miracle-claim driven",
            "claim_restraint": "the film implies hydration through texture and ritual; it does not promise medical repair or quantified efficacy",
            "rejected_category_cliches": [
                "petals drifting behind a serum packshot",
                "fake laboratory screens and floating molecule icons",
                "endless macro droplets without purchase or use ritual",
            ],
        },
        "director_language": {
            "lens_progression": "wide absence to macro component clue, low occluded partial reveal, first readable product, tactile use, product-absent benefit, and final front authority",
            "transition_grammar": "match cuts, reflection wipes, foreground tray occlusion, ripple motion carry, and label-stripe eye-trace handoffs",
            "edit_bridge": "each cut uses water direction, cap geometry, label stripe, fingertip pressure, or reflected silhouette as the bridge",
            "motivated_camera_path": "camera moves only to reveal, withhold, compare, follow, or transform the water/reflection ritual proof",
            "shot_to_shot_causality": "each shot earns the next information state: absence, clue, partial identity, full identity, proof, use, benefit, return, memory",
            "coverage_strategy": "withhold full product views, use detail and partial shots as proof, and reserve final front coverage for recall",
        },
        "art_direction_invention": {
            "reference_to_world_transformation": "reference edge tension becomes a skincare counter world where water and reflection control product recognition",
            "invented_scene_architecture": "reflective tray threshold, tester counter, fingertip interaction table, ripple surface, and packshot memory space",
            "prop_logic": "tray, droplet, tester surface, fingertip, and reflection are allowed only when they advance purchase ritual or proof",
            "material_system": "etched glass, pearl bottle, black cap, pale blue stripe, water meniscus, soft clinical bounce, and contact shadows",
            "category_coded_restraint": "remove flowers, fake lab UI, miracle-claim typography, excessive chrome, and influencer mirror clutter",
            "set_piece_invention": "the counter reflection repeatedly reshapes into the bottle silhouette, then settles into final pack recognition",
        },
        "creative_concept_candidates": [
            {
                "concept_id": "concept_a",
                "logline": "A clinical droplet earns the serum reveal through water, tray reflection, and tactile use proof.",
                "visual_world": "cool pearlescent reflective tray world with precise glass and water behavior",
                "reason_to_select_or_reject": "selected because it gives product identity a clear causal reveal instead of static packshots",
            },
            {
                "concept_id": "concept_b",
                "logline": "A colder laboratory grid turns the serum into a clinical specimen before the final reveal.",
                "visual_world": "harder laboratory grid, colder white light, stricter geometry",
                "reason_to_select_or_reject": "rejected because it feels too diagnostic and leaves less room for tactile beauty use",
            },
        ],
        "reference_deconstruction": {
            "references": [
                {
                    "reference_id": "REF_001",
                    "role": "product_identity_and_style_reference",
                    "observed_visual_facts": [
                        "lipstick stands isolated against a deep red negative field",
                        "white platform edge creates a strong diagonal path into the product",
                        "metallic lipstick tube and clear base create crisp specular contact shadows",
                    ],
                    "transferable_principles": [
                        "use hard geometry to control when the product becomes readable",
                        "let red or color pressure shape desire before the product fills the frame",
                        "preserve material contrast between pigment, metal, acrylic, and white architectural support",
                    ],
                    "must_not_copy_surface_elements": [
                        "do not repeat the same lipstick-on-step corner composition",
                        "do not make every panel a red-background product closeup",
                        "do not use the white platform as an unchanged staircase motif",
                    ],
                    "assigned_agent_owner": "art_director_agent",
                }
            ],
            "source_image_dna": {
                "composition_principles": [
                    "the reference uses a product isolated against an architectural edge instead of filling the whole frame",
                    "diagonal white geometry creates a hard path for the eye before the red object is read",
                    "large negative space makes the product feel controlled and expensive",
                ],
                "light_material_logic": [
                    "red pigment reads through glossy highlights rather than flat color fill",
                    "white platform and transparent package surfaces create cold specular contrast",
                    "metal and acrylic edges need crisp contact shadows to avoid CGI softness",
                ],
                "negative_space_strategy": [
                    "empty red field should create withheld desire rather than become repeated background wallpaper",
                    "white geometric voids should guide reveal timing rather than appear as the same staircase in every shot",
                ],
                "motion_implications": [
                    "the diagonal ledge implies a gliding reveal path across the vertical frame",
                    "the lipstick angle suggests rotation and edge reveal rather than static repeated packshots",
                ],
            },
            "creative_translation": {
                "borrow": [
                    "borrow the reference's red/white edge tension and isolated product authority",
                    "borrow the hard shadow and polished material contrast between product and architectural support",
                ],
                "transform": [
                    "turn the diagonal ledge into a water-reflection threshold that changes across shots",
                    "turn the red field into a moving color pressure that appears only when the product earns attention",
                    "turn product isolation into a script arc: withheld component, tactile proof, benefit metaphor, final authority",
                ],
                "reject": [
                    "do not repeat the same product-on-white-step composition",
                    "do not reuse the red background as a wallpaper in every panel",
                    "do not make multiple macro lipstick angles without a new story event",
                ],
                "creative_leap": "A clinical droplet converts the reference's hard diagonal product stage into a cause-and-effect hydration world that reveals the serum through reflection, touch, and final authority.",
                "new_mechanism": {
                    "borrowed_dna_ids": ["REF_001.diagonal_edge", "REF_001.red_negative_space", "REF_001.specular_material_contrast"],
                    "transformed_into": "a water-reflection threshold, pale clinical color pressure, and tactile label-proof chain",
                    "new_story_world_rule": "only water, reflection, refraction, and touch may reveal the product or return it to final authority",
                    "rejects_surface_copy_ids": ["REF_001.white_step", "REF_001.red_wallpaper", "REF_001.repeated_lipstick_angle"],
                },
                "reference_to_world_transformation": "the reference's hard edge tension becomes a skincare counter ritual governed by water, reflection, and touch",
                "invented_scene_architecture": "a reflective tester counter opens into tray threshold, fingertip table, ripple surface, and final packshot memory space",
                "prop_logic": "droplet, tray, fingertip, and reflection each exist to prove purchase ritual or product identity rather than decorate the frame",
                "material_system": "pearl bottle, black cap, pale blue stripe, etched glass, water meniscus, contact shadow, and soft clinical bounce",
                "set_piece_invention": "the counter reflection deforms into the bottle silhouette before the final exact product authority frame",
            },
            "literal_copy_risks": [
                "repeating white step geometry until every shot feels like the same plinth",
                "using red background and product closeups as surface decoration without story change",
                "turning every panel into a product angle instead of moving through world, proof, use, benefit, and payoff",
            ],
            "agent_responsibility": {
                "creative_director_agent": "owns the creative leap from reference DNA to a new advertising mechanism; must veto surface extraction masquerading as concept",
                "art_director_agent": "owns material, color, negative-space, and literal-copy vetoes so the reference becomes visual grammar, not repeated props",
                "screenwriter_agent": "owns timecoded progression so each beat changes desire, information, or product role instead of repeating beauty coverage",
                "director_agent": "owns shot-to-shot difference, panel aspect, camera motivation, and final rejection of repetitive composition",
            },
        },
        "concept_council": {
            "creative_director": "select concept_a for stronger first-read material logic and cleaner product-reference hierarchy",
            "director": "approve concept_a because each reveal can become a segment-mapped shot with clear motion motivation",
            "screenwriter": "approve concept_a because the droplet, tray, fingertip, and ripple make a complete 30-second arc",
            "art_director": "approve concept_a because the world can preserve the white bottle, black cap, and pale blue stripe without added hardware",
            "final_concept_decision": "concept_a is final; concept_b is rejected for sterile emotional range",
            "unresolved_vetos": [],
        },
        "timecoded_script_map": [
            {
                "time_range": "0s-10s",
                "beat": "origin and withheld reveal",
                "visual_event": "a droplet and tray reflection introduce product clues before the first readable reveal",
                "product_role": "product is withheld until water/reflection earns visibility",
                "director_intent": "use four planned shots to establish world rule, component clue, partial reveal, and first full view",
            },
            {
                "time_range": "10s-20s",
                "beat": "proof and use action",
                "visual_event": "label stripe macro and fingertip pressure convert the packshot into tactile use proof",
                "product_role": "product alternates detail proof and partial tactile interaction",
                "director_intent": "use three planned shots to keep identity legible while avoiding a packshot wall",
            },
            {
                "time_range": "20s-30s",
                "beat": "benefit metaphor and final authority",
                "visual_event": "hydration ripple returns as a cropped reflection, then settles into the final exact product image",
                "product_role": "product leaves frame for the benefit metaphor, then returns as final identity",
                "director_intent": "use two planned shots for the final turn and packshot authority",
            },
        ],
        "director_script_approval": {
            "approved": True,
            "rationale": "The 30-second script has three executable 10-second segments and a director-owned 4/3/2 panel rhythm.",
        },
        "storyboard_layout_decision": {
            "policy": "per_segment_dynamic_n_panel_storyboard",
            "rationale": "Create one storyboard sheet per Google Omni segment; each sheet uses only the shots required by its script beat.",
            "panel_count_source": "approved timecoded script map and director shot plan",
            "segment_mapping_source": "director-approved segment-to-shot map",
        },
        "story_engine": {
            "advertising_logline": "A clinical droplet teaches a reflective world to reveal the serum only when its hydration logic is proven.",
            "world_rule": "Water, tray reflection, fingertip pressure, and glass refraction are the only forces allowed to reveal the product.",
            "dramatic_question": "Can the product earn visibility through tactile proof before becoming a final packshot?",
            "dramatic_arc": [
                "an empty droplet world establishes the rule",
                "partial product clues and fingertip pressure test the material promise",
                "a hydration ripple resolves into the final exact product identity",
            ],
            "product_role": "the serum is the proof object that becomes inevitable after the world demonstrates its hydration behavior",
            "reference_synthesis": "product reference controls package identity; visual references control cool pearlescent lighting, tray depth, and restrained atmosphere only",
            "duration_design": "30 seconds use three segment-aligned dynamic N-panel storyboards; panels are director-planned shots, not a preset grid",
            "motion_language": "slow dolly, tray slide, fingertip pressure, ripple transfer, and final locked push-in",
            "anti_plastic_rules": "real glass reflection, contact shadow, micro texture, physical water behavior, lens softness, and restrained grain",
        },
        "continuity_locks": ["same user-provided serum bottle throughout"],
        "creative_concept": {
            "big_idea": "A single clinical droplet teaches the world to behave like the bottle's pale blue stripe.",
            "audience_desire": "make the serum feel precise, cool, tactile, and desirable before the final packshot",
            "story_tension": "the skin-world is dry and still until small controlled water events pull the product into view",
            "world_rule": "every reveal is caused by water, reflection, fingertip pressure, or glass refraction, never by a random beauty pose",
            "visual_mechanism": "droplet, tray reflection, label stripe, fingertip ripple, and final packshot form one cause-and-effect chain",
            "scene_ladder": [
                "clinical droplet world",
                "reflective tray threshold",
                "fingertip interaction table",
                "hydration ripple world",
                "clean packshot memory space",
            ],
            "signature_images": [
                "a blue-white droplet suspended over an empty tray",
                "the black cap edge arriving as a reflection before the bottle appears",
                "a fingertip ripple becoming the final packshot base highlight",
            ],
        },
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
                "segment_id": "SEG_01",
                "time_range": "0s-10s",
                "beat": "origin, withheld reveal, and first readable view",
                "sheet_canvas_aspect_ratio": "16:9",
                "panel_aspect_ratio": "9:16",
                "shots": shots[:4],
            },
            {
                "sheet_id": "sheet_02",
                "segment_id": "SEG_02",
                "time_range": "10s-20s",
                "beat": "identity proof and tactile use action",
                "sheet_canvas_aspect_ratio": "16:9",
                "panel_aspect_ratio": "9:16",
                "shots": shots[4:7],
            },
            {
                "sheet_id": "sheet_03",
                "segment_id": "SEG_03",
                "time_range": "20s-30s",
                "beat": "return bridge and final authority",
                "sheet_canvas_aspect_ratio": "16:9",
                "panel_aspect_ratio": "9:16",
                "shots": shots[7:],
            },
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
        visibility_plan = {
            1: {
                "product_visibility": "not_visible",
                "scene": "blue-white clinical droplet world with no object visible yet",
                "scene_arena": "clinical droplet world",
                "scene_role": "origin world",
                "dramatic_event": "a suspended droplet trembles and establishes the water logic before any package appears",
                "visual_mechanism": "droplet highlight foreshadows the pale blue label stripe and later tray reflection",
                "shot_purpose": "establish a cool clinical morning world before the object reveal",
                "main_subject": "blue-white water droplet suspended above a reflective tray",
                "main_action": "droplet trembles and catches a pale blue stripe of light",
                "composition": "droplet sits high left while the empty tray curve opens space on the right",
                "foreground": "soft tray rim blur",
                "midground": "single suspended droplet",
                "background": "white-blue laboratory glass blocks",
                "must_preserve": "cool white and pale blue material world with no bottle visible",
            },
            2: {
                "product_visibility": "detail_only",
                "scene_arena": "reflective tray threshold",
                "scene_role": "material clue",
                "dramatic_event": "the black cap edge arrives as a reflected clue before the full package is shown",
                "visual_mechanism": "tray reflection turns the droplet highlight into a product-component reveal",
                "main_subject": "rounded black cap edge and pale blue label stripe reflection",
                "main_action": "light rolls across the cap edge without showing the full bottle",
                "shot_size": "extreme close-up cap-and-label material insert",
                "product_identity_action": "show only the real black cap edge and pale blue label stripe reflection from the locked LUMA bottle",
            },
            3: {
                "product_visibility": "partial_visible",
                "scene_arena": "reflective tray threshold",
                "scene_role": "partial reveal",
                "dramatic_event": "a cropped shoulder slides behind the tray rim and withholds the full bottle",
                "visual_mechanism": "foreground tray occlusion turns the package into a withheld silhouette",
                "main_subject": "cropped white bottle shoulder entering behind a tray rim",
                "main_action": "shoulder edge slides into view while most of the package stays hidden",
                "product_identity_action": "crop the locked white cylindrical bottle so only the shoulder curve and black cap base are visible",
            },
            4: {
                "product_visibility": "full_visible",
                "scene_arena": "first readable product stage",
                "scene_role": "first full reveal",
                "dramatic_event": "the tray reflection completes the silhouette and lets the first readable product view arrive",
                "visual_mechanism": "the reflection opens like a stage slit to motivate the full product reveal",
                "main_subject": "first full LUMA bottle reveal in three-quarter view",
                "main_action": "front label turns into readable view",
            },
            5: {
                "product_visibility": "detail_only",
                "scene_arena": "label stripe inspection",
                "scene_role": "typography proof",
                "dramatic_event": "macro focus tests the pale blue stripe and label rectangle as proof of product identity",
                "visual_mechanism": "a moving specular line connects the stripe to the earlier droplet path",
                "main_subject": "front label rectangle and pale blue stripe detail",
                "main_action": "macro focus moves across the label stripe and white bottle surface",
                "product_identity_action": "draw only the real centered front label rectangle, pale blue stripe, and white bottle material",
            },
            6: {
                "product_visibility": "partial_visible",
                "scene_arena": "fingertip interaction table",
                "scene_role": "use action",
                "dramatic_event": "a fingertip nudges only the cropped base so the object becomes tactile rather than worshipped",
                "visual_mechanism": "fingertip pressure starts a rotation that will become the final reflection",
                "main_subject": "clean fingertip nudging the cropped bottle base",
                "main_action": "fingertip starts a small rotation from the base edge",
                "product_identity_action": "show the locked white cylindrical base partially, keeping the black cap and label geometry consistent where visible",
            },
            7: {
                "product_visibility": "not_visible",
                "scene": "abstract blue-white hydration surface with no object visible",
                "scene_arena": "hydration ripple world",
                "scene_role": "benefit metaphor",
                "dramatic_event": "the fingertip action resolves as a smooth water ripple with no package in frame",
                "visual_mechanism": "the rotation energy transfers into a skin-like hydration ripple",
                "shot_purpose": "show the benefit metaphor before returning to the final identity",
                "shot_size": "benefit metaphor close shot",
                "main_subject": "skin-like water surface forming a smooth hydration ripple",
                "main_action": "ripple expands into a clean circular highlight",
                "composition": "ripple fills the lower half while the upper right stays empty for the next reveal",
                "foreground": "soft wet surface edge",
                "midground": "single smooth ripple highlight",
                "background": "pale blue-white negative space",
                "must_preserve": "benefit metaphor with no bottle, label, logo, or package visible",
            },
            8: {
                "product_visibility": "partial_visible",
                "scene_arena": "hydration ripple world",
                "scene_role": "return bridge",
                "dramatic_event": "the ripple reflection catches a cropped bottle silhouette and pulls the eye back to identity",
                "visual_mechanism": "the circular ripple deforms into the product's cylindrical reflection",
                "main_subject": "cropped bottle silhouette re-entering through a glass reflection",
                "main_action": "reflection pulls the eye back toward the final packshot",
                "product_identity_action": "show only the locked white cylindrical silhouette and black cap outline as a reflection-cropped transition",
            },
            9: {
                "product_visibility": "full_visible",
                "scene_arena": "clean packshot memory space",
                "scene_role": "final authority",
                "dramatic_event": "the ripple energy stops and the product holds as the final memory image",
                "visual_mechanism": "the reflected ripple becomes the stable base highlight under the front packshot",
                "main_subject": "final front-facing LUMA bottle packshot",
                "main_action": "product holds still while the label finishes readable",
            },
        }
        all_shots = [shot for sheet in plan["sheets"] for shot in sheet["shots"]]
        for index, shot in enumerate(all_shots, start=1):
            shot.update(visibility_plan[index])
            if shot["product_visibility"] != "not_visible":
                shot.setdefault(
                    "product_identity_action",
                    "preserve the locked bottle shape, label layout, black cap, and visible real product marks",
                )
            if shot["product_visibility"] == "full_visible":
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

    def test_shot_plan_requires_reference_deconstruction_before_storyboard(self) -> None:
        plan = make_plan(include_identity_lock=True)
        del plan["reference_deconstruction"]

        code, result = run_validator(plan)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("reference_deconstruction" in error for error in result["errors"]),
            result["errors"],
        )

    def test_shot_plan_rejects_literal_reference_copy_as_creative_leap(self) -> None:
        plan = make_plan(include_identity_lock=True)
        plan["reference_deconstruction"]["creative_translation"]["creative_leap"] = (
            "Copy the same stairs, same red background, and same product-on-white-plinth composition from the reference."
        )
        plan["sheets"][0]["shots"][0]["reference_transform"] = (
            "copy the same white plinth and same red background from the reference"
        )

        code, result = run_validator(plan)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("creative_leap" in error or "reference_transform" in error for error in result["errors"]),
            result["errors"],
        )

    def test_storyboard_panels_must_match_requested_video_aspect_ratio(self) -> None:
        plan = make_plan(include_identity_lock=True)
        plan["sheets"][0]["panel_aspect_ratio"] = "16:9"
        plan["sheets"][0]["shots"][0]["aspect_ratio"] = "16:9"

        code, result = run_validator(plan)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("requested_video_aspect_ratio" in error or "panel_aspect_ratio" in error for error in result["errors"]),
            result["errors"],
        )

    def test_shot_plan_requires_agent_activation_ledger(self) -> None:
        plan = make_plan(include_identity_lock=True)
        del plan["agent_activation_ledger"]

        code, result = run_validator(plan)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("agent_activation_ledger" in error for error in result["errors"]),
            result["errors"],
        )

    def test_shot_plan_rejects_missing_mandatory_concept_agent(self) -> None:
        plan = make_plan(include_identity_lock=True)
        plan["agent_activation_ledger"] = [
            entry
            for entry in plan["agent_activation_ledger"]
            if entry["agent_role"] != "screenwriter_agent"
        ]

        code, result = run_validator(plan)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("screenwriter_agent" in error for error in result["errors"]),
            result["errors"],
        )

    def test_shot_plan_rejects_skipped_or_simulated_agent_activation(self) -> None:
        plan = make_plan(include_identity_lock=True)
        plan["agent_activation_ledger"][0]["status"] = "simulated"

        code, result = run_validator(plan)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("status must be completed" in error for error in result["errors"]),
            result["errors"],
        )

    def test_storyboard_rejects_packshot_wall_visibility_rhythm(self) -> None:
        plan = make_plan(include_identity_lock=True)
        for shot in plan["sheets"][0]["shots"]:
            shot["product_visibility"] = "full_visible"
            shot["shot_purpose"] = "repeat a full product beauty view with only minor angle variation"
            shot["main_subject"] = "full front-facing LUMA bottle product packshot"
            shot["main_action"] = "product holds while a light sweep crosses the front label"
            shot["composition"] = "full bottle remains dominant in the center with only small lighting changes"
            shot["midground"] = "full product bottle with front label"
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

        code, result = run_validator(plan)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("too many full-visible" in error or "packshot wall" in error for error in result["errors"]),
            result["errors"],
        )

    def test_product_ads_require_creative_concept_and_scene_mechanics(self) -> None:
        plan = make_plan(include_identity_lock=True)
        del plan["creative_concept"]
        for shot in plan["sheets"][0]["shots"]:
            shot.pop("scene_arena", None)
            shot.pop("scene_role", None)
            shot.pop("dramatic_event", None)
            shot.pop("visual_mechanism", None)

        code, result = run_validator(plan)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("creative_concept" in error or "scene_arena" in error for error in result["errors"]),
            result["errors"],
        )

    def test_product_ads_require_story_engine_before_shot_planning(self) -> None:
        plan = make_plan(include_identity_lock=True)
        del plan["story_engine"]

        code, result = run_validator(plan)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("story_engine" in error for error in result["errors"]),
            result["errors"],
        )

    def test_product_ads_require_category_strategy_before_concept(self) -> None:
        plan = make_plan(include_identity_lock=True)
        del plan["category_strategy"]

        code, result = run_validator(plan)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("category_strategy" in error for error in result["errors"]),
            result["errors"],
        )

    def test_product_ads_require_director_and_art_direction_contracts(self) -> None:
        plan = make_plan(include_identity_lock=True)
        del plan["director_language"]["transition_grammar"]
        del plan["art_direction_invention"]["invented_scene_architecture"]

        code, result = run_validator(plan)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("director_language" in error for error in result["errors"]),
            result["errors"],
        )
        self.assertTrue(
            any("art_direction_invention" in error for error in result["errors"]),
            result["errors"],
        )

    def test_shot_plan_rejects_panel_count_that_disagrees_with_actual_shots(self) -> None:
        plan = make_plan(include_identity_lock=True)
        plan["panel_count"] = 999

        code, result = run_validator(plan)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("panel_count=999" in error for error in result["errors"]),
            result["errors"],
        )

    def test_product_ads_reject_weak_repeated_macro_detail_mechanics(self) -> None:
        plan = make_plan(include_identity_lock=True)
        plan["creative_concept"]["scene_ladder"] = ["macro lavender surface"]
        plan["creative_concept"]["visual_mechanism"] = "light sweeps across premium product details"
        for shot in plan["sheets"][0]["shots"]:
            shot["scene_arena"] = "macro lavender product detail table"
            shot["scene_role"] = "product beauty detail"
            shot["dramatic_event"] = "light sweeps across the product detail"
            shot["visual_mechanism"] = "soft lavender reflection makes it look premium"

        code, result = run_validator(plan)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("distinct scene_arena" in error or "weak dramatic_event" in error for error in result["errors"]),
            result["errors"],
        )

    def test_product_ads_reject_semantic_repetition_even_when_surface_words_vary(self) -> None:
        plan = make_plan(include_identity_lock=True)
        for index, shot in enumerate([shot for sheet in plan["sheets"] for shot in sheet["shots"]], start=1):
            shot["scene_arena"] = f"distinct red pressure chamber {index}"
            shot["visual_mechanism"] = f"distinct glamour color pressure variant {index} reveals a polished surface"
            shot["dramatic_event"] = f"a different polished red highlight crosses the product surface variant {index}"
            shot["reference_transform"] = f"transform reference color into a named glamour pressure variant {index}"
            shot["shot_function_signature"] = {
                "information_delta": "same desire pressure variation",
                "desire_delta": f"slightly intensify the same glamour desire variant {index}",
                "purchase_ritual_delta": f"repeat the same cosmetic inspection gesture variant {index}",
                "shelf_memory_delta": f"repeat the same red glamour shelf-memory cue variant {index}",
                "ritual_proof_delta": f"repeat the same polished surface proof variant {index}",
                "claim_safety": "visual glamour only; no quantified or medical product claims",
                "product_role_delta": "same product glamour object variation",
                "event_type": "glamour_surface_reveal",
                "camera_relation_key": "macro_product_glamour_relation",
                "reference_transform_id": f"RT_REPEAT_{index:03d}",
                "redundancy_risk": "risk of repeated glamour surface coverage disguised with new words",
            }

        code, result = run_validator(plan)

        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("semantic redundancy" in error or "information_delta" in error for error in result["errors"]),
            result["errors"],
        )

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
