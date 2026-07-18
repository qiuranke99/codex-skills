#!/usr/bin/env python3
"""Exercise the Scene Canon v2 validator with positive and adversarial fixtures."""

from __future__ import annotations

import copy
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageDraw

from freeze_reference_bundle import freeze_bundle
from resolve_worker_image import ContractError, SCENE_CANON_ASSET_TASK_SLUGS, load_reference_manifest, validate_worker_name_binding

from validate_scene_package import (
    DEPENDENCIES,
    MACHINE_ASSET_IDS,
    ROLE_BY_ASSET,
    STAGES,
    canonical_json_hash,
    sha256_file,
    sha256_text,
    validate_package,
)


HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
TEMPLATE = SKILL_DIR / "references" / "asset_manifest_template.json"
NODE_BY_ASSET = {asset_id: f"NODE_{asset_id}" for asset_id in MACHINE_ASSET_IDS}
ASSET_PATHS = {
    "CDM_001": "02_diagnostic_master/canonical_diagnostic_master.png",
    "SRM_001": "03_spatial_relational_master/spatial_relational_master.png",
    "COV_001": "04_coverage_plates/coverage_001_left_adjacent.png",
    "COV_002": "04_coverage_plates/coverage_002_right_adjacent.png",
    "COV_003": "04_coverage_plates/coverage_003_motion_reveal.png",
    "SCL_001": "05_scale_landmarks/scale_landmark_depth.png",
}
CHECKS = {
    "source_fidelity", "topology", "scale", "landmarks", "materials",
    "fixed_content", "overlap", "reveal", "parallax", "loop_continuity",
    "duplicate", "contamination", "neutral_appearance",
}


def assert_standalone_skill_contract() -> None:
    required = (
        "SKILL.md",
        "requirements.txt",
        "agents/openai.yaml",
        "references/scene_canon.schema.json",
        "references/asset_manifest.schema.json",
        "scripts/freeze_reference_bundle.py",
        "scripts/resolve_worker_image.py",
        "scripts/build_review_board.py",
        "scripts/validate_scene_package.py",
    )
    for relative in required:
        if not (SKILL_DIR / relative).is_file():
            raise AssertionError(f"standalone package is missing {relative}")

    forbidden_text = (
        "HIGH_CONTROL_" + "RELEASE_GATE_V2",
        "high-control-" + "ai-tvc",
        "release-" + "control.ps1",
        "release-" + "control.sh",
        "ready_" + "latest=true",
        "ai-video-" + "shot-script-director",
    )
    text_suffixes = {".md", ".py", ".yaml", ".json", ".txt"}
    for path in SKILL_DIR.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in text_suffixes:
            continue
        text = path.read_text(encoding="utf-8")
        for marker in forbidden_text:
            if marker in text:
                raise AssertionError(f"standalone package retains external runtime marker {marker!r} in {path.relative_to(SKILL_DIR)}")
        if path.suffix.casefold() == ".py":
            if ("sys.path." + "insert") in text or (".parents[" + "2]") in text:
                raise AssertionError(f"standalone package retains a cross-package Python loader in {path.relative_to(SKILL_DIR)}")

    removed_exporter = SKILL_DIR / "scripts" / ("export_ai_video_" + "canon.py")
    if removed_exporter.exists():
        raise AssertionError("suite-specific exporter must not be part of the standalone Scene package")

    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    metadata = (SKILL_DIR / "agents/openai.yaml").read_text(encoding="utf-8")
    if "## Standalone Runtime Contract" not in skill:
        raise AssertionError("SKILL.md is missing the standalone runtime contract")
    if "allow_implicit_invocation: false" not in metadata:
        raise AssertionError("Scene explicit-invocation metadata drifted")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def substantive(label: str) -> str:
    return (
        f"# {label}\n\nThis deterministic contract record binds concrete scene topology, landmark overlap, "
        "camera coverage, neutral appearance, provenance, and delivery evidence. Every required check "
        "has an explicit subject and byte-level receipt, so the package can fail closed when evidence drifts.\n"
    )


def write_jsonl(path: Path, events: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n" for event in events), encoding="utf-8", newline="\n")


def run_resolver_e2e_probe(root: Path) -> dict[str, Any]:
    asset_id = "CDM_001"; attempt_id = "ATTEMPT_CDM_001_E2E"; nonce = "0123456789abcdef0123456789abcdef"
    task_name = f"scene_canon_image_cdm_001_{nonce}"; agent_path = f"/root/{task_name}"
    parent_thread_id = "parent-thread-e2e"; worker_thread_id = "worker-thread-e2e"
    parent_turn_id = "parent-turn-e2e"; worker_turn_id = "worker-turn-e2e"
    spawn_call_id = "spawn-call-e2e"; image_call_id = "image-call-e2e"; delivery_ciphertext = "opaque-ciphertext-e2e"
    not_before_ms = 1000; spawn_ms = 1100
    codex_home = root / "codex-home"; package_root = root / "package"; runtime_dir = package_root / "10_runtime/cdm_001"
    source_path = package_root / "01_source_analysis/source.png"; source_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 18), (10, 20, 30)).save(source_path, format="PNG")
    reference_manifest = runtime_dir / "reference-manifest.json"
    freeze = subprocess.run([
        sys.executable, str(HERE / "freeze_reference_bundle.py"), "--asset-id", asset_id,
        "--source-reference-id", "SRC_001", "--source", str(source_path), "--output", str(reference_manifest),
    ], text=True, capture_output=True)
    if freeze.returncode != 0:
        raise AssertionError(f"freezer failed:\n{freeze.stdout}\n{freeze.stderr}")
    reference_data = read_json(reference_manifest); frozen_reference = Path(reference_data["ordered_references"][0]["frozen_path"])
    prompt = "Generate exactly one independent full-frame CDM_001 test scene raster from the ordered frozen source."
    prompt_path = runtime_dir / "generation-prompt.txt"; prompt_path.parent.mkdir(parents=True, exist_ok=True); prompt_path.write_bytes(prompt.encode("utf-8"))
    generated_path = codex_home / "generated_images" / worker_thread_id / f"{image_call_id}.png"
    generated_path.parent.mkdir(parents=True, exist_ok=True); Image.new("RGB", (64, 36), (40, 50, 60)).save(generated_path, format="PNG")
    parent_rollout = root / "parent-rollout.jsonl"; worker_rollout = root / "worker-rollout.jsonl"
    write_jsonl(parent_rollout, [
        {"type": "session_meta", "payload": {"id": parent_thread_id}},
        {"type": "event_msg", "payload": {"type": "agent_message", "event_id": "pre-spawn-sentinel", "message": "event before worker spawn"}},
        {"type": "response_item", "payload": {"type": "function_call", "name": "spawn_agent", "call_id": spawn_call_id, "arguments": json.dumps({"task_name": task_name, "fork_turns": "none", "message": delivery_ciphertext}, separators=(",", ":")), "internal_chat_message_metadata_passthrough": {"turn_id": parent_turn_id}}},
        {"type": "event_msg", "payload": {"type": "sub_agent_activity", "event_id": spawn_call_id, "kind": "started", "occurred_at_ms": spawn_ms, "agent_thread_id": worker_thread_id, "agent_path": agent_path}},
        {"type": "response_item", "payload": {"type": "function_call_output", "call_id": spawn_call_id, "output": json.dumps({"task_name": agent_path}), "internal_chat_message_metadata_passthrough": {"turn_id": parent_turn_id}}},
    ])
    delivery_header = f"Message Type: NEW_TASK\nTask name: {agent_path}\nSender: /root\nPayload:\n"
    tool_input = "tools.image_gen__imagegen({prompt:" + json.dumps(prompt) + ",referenced_image_paths:" + json.dumps([str(frozen_reference)]) + "})"
    write_jsonl(worker_rollout, [
        {"type": "session_meta", "payload": {"id": worker_thread_id, "agent_path": agent_path, "parent_thread_id": parent_thread_id}},
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": worker_turn_id}},
        {"type": "turn_context", "payload": {"turn_id": worker_turn_id}},
        {"type": "inter_agent_communication_metadata", "payload": {"trigger_turn": True}},
        {"type": "response_item", "payload": {"type": "agent_message", "recipient": agent_path, "author": "/root", "content": [{"type": "input_text", "text": delivery_header}, {"type": "encrypted_content", "encrypted_content": delivery_ciphertext}], "internal_chat_message_metadata_passthrough": {"turn_id": worker_turn_id}}},
        {"type": "response_item", "payload": {"type": "custom_tool_call", "input": tool_input}},
        {"type": "event_msg", "payload": {"type": "image_generation_end", "status": "completed", "call_id": image_call_id, "saved_path": str(generated_path)}},
        {"type": "event_msg", "payload": {"type": "agent_message", "phase": "final_answer", "message": ""}},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant", "phase": "final_answer", "content": []}},
        {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": worker_turn_id, "last_agent_message": ""}},
    ])
    state_db = root / "state_5.sqlite"; connection = sqlite3.connect(state_db)
    connection.execute("CREATE TABLE threads (id TEXT, rollout_path TEXT, created_at INTEGER, created_at_ms INTEGER, source TEXT)")
    connection.execute("INSERT INTO threads VALUES (?, ?, ?, ?, ?)", (parent_thread_id, str(parent_rollout), 1, 900, "{}"))
    connection.execute("INSERT INTO threads VALUES (?, ?, ?, ?, ?)", (worker_thread_id, str(worker_rollout), 1, spawn_ms, json.dumps({"subagent": {"thread_spawn": {"agent_path": agent_path, "parent_thread_id": parent_thread_id}}})))
    connection.commit(); connection.close()
    copy_to = package_root / "02_diagnostic_master/canonical_diagnostic_master.png"; result_json = runtime_dir / "worker-result.json"
    resolve = subprocess.run([
        sys.executable, str(HERE / "resolve_worker_image.py"), "--agent-path", agent_path, "--not-before-ms", str(not_before_ms),
        "--parent-thread-id", parent_thread_id, "--asset-id", asset_id, "--attempt-id", attempt_id, "--worker-run-nonce", nonce,
        "--expected-prompt", str(prompt_path), "--reference-manifest", str(reference_manifest), "--copy-to", str(copy_to),
        "--result-json", str(result_json), "--state-db", str(state_db), "--codex-home", str(codex_home),
    ], text=True, capture_output=True)
    if resolve.returncode != 0:
        raise AssertionError(f"resolver failed:\n{resolve.stdout}\n{resolve.stderr}")
    result = read_json(result_json)
    expected = {
        "ok": True, "contract": "delegated_image_worker_result.v3", "asset_id": asset_id, "attempt_id": attempt_id,
        "worker_task_name": task_name, "worker_thread_id": worker_thread_id, "parent_thread_id": parent_thread_id,
        "parent_spawn_call_id": spawn_call_id, "parent_spawn_event_index": 2, "binding_mode": "parent_spawn_cipher_chain_v1",
        "prompt_sha_match": True, "reference_mode": "frozen_manifest", "reference_count": 1,
        "image_generation_call_id": image_call_id, "width_px": 64, "height_px": 36,
    }
    for key, value in expected.items():
        if result.get(key) != value:
            raise AssertionError(f"resolver result mismatch for {key}: {result.get(key)!r} != {value!r}")
    if result["reference_manifest_sha256"] != sha256_file(reference_manifest) or result["ordered_reference_bundle_sha256"] != reference_data["ordered_bundle_sha256"] or not copy_to.is_file() or sha256_file(copy_to) != result["image_sha256"]:
        raise AssertionError("resolver output/reference/image hash binding failed")
    return result


def make_pattern(path: Path, seed: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 192, 108
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            pixels[x, y] = (
                (x * (seed * 7 + 3) + y * 11 + seed * 29) % 256,
                (x * 5 + y * (seed * 13 + 7) + seed * 41) % 256,
                ((x ^ (y * seed + 17)) * 9 + seed * 23) % 256,
            )
    draw = ImageDraw.Draw(image)
    draw.rectangle((8 + seed * 2, 7, 55 + seed * 3, 36 + seed), outline="white", width=3)
    draw.line((0, (seed * 17) % height, width - 1, (seed * 31 + 19) % height), fill="black", width=4)
    draw.ellipse((110 - seed, 25 + seed, 155 + seed, 70 + seed), outline=(255, 220, 40), width=3)
    image.save(path, format="PNG")


def completion() -> dict[str, Any]:
    return {
        "element_id": "COMP_001",
        "description": "Rear wall continuation constrained by the visible side-wall junctions",
        "rationale": "Required by the approved motion-reveal boundary",
        "constraints": ["preserve room width", "introduce no new door or landmark"],
        "status": "approved",
    }


def node(asset_id: str, pose: dict[str, Any], revealed: list[str], adjacent: list[str]) -> dict[str, Any]:
    return {
        "node_id": NODE_BY_ASSET[asset_id],
        "asset_id": asset_id,
        "role": ROLE_BY_ASSET[asset_id],
        "camera_pose": {
            **pose,
            "roll_degrees": 0,
            "lens_fov_class": "wide" if asset_id != "SCL_001" else "normal",
            "distance_framing_class": "wide_context" if asset_id != "SCL_001" else "mid_context",
        },
        "visible_landmark_ids": ["L_001"],
        "revealed_region_ids": revealed,
        "occluded_region_ids": [],
        "source_evidence_ids": ["E_001"],
        "canonical_completion_ids": ["COMP_001"] if asset_id in {"COV_003", "SCL_001"} else [],
        "adjacent_node_ids": [NODE_BY_ASSET[item] for item in adjacent],
        "overlap_invariant_ids": ["INV_GEOMETRY", "INV_LANDMARK"],
        "mandatory": True,
    }


def edge(edge_id: str, left: str, right: str, movement: str, path_id: str) -> dict[str, Any]:
    translated = movement in {"truck", "crane", "orbit", "approach", "departure"}
    return {
        "edge_id": edge_id,
        "from_node_id": NODE_BY_ASSET[left],
        "to_node_id": NODE_BY_ASSET[right],
        "movement_type": movement,
        "direction": f"{left} to {right}",
        "translation_baseline_normalized": 0.25 if translated else 0,
        "parallax_expected": translated,
        "parallax_evidence_status": "verified" if translated else "not_applicable",
        "reveal_order_region_ids": ["REGION_MAIN", "REGION_REAR"],
        "handedness": "forward" if translated else "left_to_right",
        "overlap_invariant_ids": ["INV_GEOMETRY"],
        "path_ids": [path_id],
    }


def scene_canon() -> dict[str, Any]:
    nodes = [
        node("CDM_001", {"x": 0.0, "y": 0.4, "z": 0.0, "yaw_degrees": 0, "pitch_degrees": 0}, ["REGION_MAIN"], ["COV_001", "COV_002"]),
        node("SRM_001", {"x": 0.0, "y": 0.8, "z": -0.1, "yaw_degrees": -15, "pitch_degrees": -15}, ["REGION_UPPER"], ["COV_001", "COV_002"]),
        node("COV_001", {"x": -0.6, "y": 0.4, "z": 0.0, "yaw_degrees": 30, "pitch_degrees": 0}, ["REGION_LEFT"], ["CDM_001", "SRM_001", "COV_003"]),
        node("COV_002", {"x": 0.6, "y": 0.4, "z": 0.0, "yaw_degrees": -30, "pitch_degrees": 0}, ["REGION_RIGHT"], ["SRM_001", "CDM_001"]),
        node("COV_003", {"x": 0.0, "y": 0.6, "z": 0.5, "yaw_degrees": 60, "pitch_degrees": -10}, ["REGION_REAR"], ["COV_001", "SCL_001"]),
        node("SCL_001", {"x": 0.0, "y": 0.25, "z": -0.7, "yaw_degrees": -60, "pitch_degrees": 5}, ["REGION_DEPTH"], ["COV_003"]),
    ]
    edges = [
        edge("EDGE_01", "CDM_001", "COV_001", "truck", "PATH_LOOP"),
        edge("EDGE_02", "COV_001", "SRM_001", "crane", "PATH_LOOP"),
        edge("EDGE_03", "SRM_001", "COV_002", "orbit", "PATH_LOOP"),
        edge("EDGE_04", "COV_002", "CDM_001", "pan", "PATH_LOOP"),
        edge("EDGE_05", "COV_001", "COV_003", "tilt", "PATH_REVEAL"),
        edge("EDGE_06", "COV_003", "SCL_001", "approach", "PATH_REVEAL"),
    ]
    done = completion()
    return {
        "schema_version": "scene-canon.v2",
        "scene_id": "TEST_SCENE",
        "project_name": "Contract Fixture",
        "scene_name": "Neutral Test Room",
        "scene_type": "bounded_rigid_space",
        "secondary_scene_types": [],
        "source_reference_list": [{"reference_id": "SRC_001", "source_locator": "01_source_analysis/source.png", "role": "primary_scene_evidence", "dimensions": {"width": 192, "height": 108}}],
        "primary_reference": "SRC_001",
        "source_locked_elements": [{"element_id": "E_001", "description": "rear wall and left doorway", "source_reference_ids": ["SRC_001"], "confidence": "high"}],
        "source_corroborated_elements": [],
        "canonical_completion_elements": [done],
        "conflicts": [],
        "out_of_scope_unknowns": ["corridor beyond approved reveal"],
        "minimum_complete_scene_boundary": {"included_regions": ["REGION_MAIN", "REGION_UPPER", "REGION_LEFT", "REGION_RIGHT", "REGION_REAR", "REGION_DEPTH"], "excluded_regions": ["REMOTE_CORRIDOR"], "coverage_rationale": "Six nodes cover the executable camera envelope and the one approved completion."},
        "fixed_architecture": ["rear wall", "left doorway"],
        "fixed_natural_structures": [],
        "fixed_set_dressing": ["fixed wall shelf"],
        "conditional_scene_elements": ["fixed cyan emissive strip powered on"],
        "temporary_or_unwanted_objects": ["cup"],
        "prohibited_elements": ["people", "products", "new furniture"],
        "fixed_content_exclusion_map": {"fixed_architecture_or_natural": ["rear wall", "left doorway"], "fixed_set_dressing": ["fixed wall shelf"], "conditional_scene_elements": ["fixed cyan emissive strip"], "temporary_objects": ["cup"], "prohibited_additions": ["new furniture", "people", "products"], "prohibited_look_components": ["teal-orange grade", "bloom", "crushed shadows"]},
        "landmark_list": [{"landmark_id": "L_001", "description": "left doorway", "orientation": "west wall", "source_state": "source_locked"}],
        "material_identity": [{"surface_id": "WALL_01", "material_class": "warm plaster", "base_color_status": "intrinsic_confirmed", "confidence": "high"}],
        "observed_rendered_colors": [{"surface_id": "WALL_01", "description": "orange under grade", "confidence": "high"}],
        "intrinsic_base_colors": [{"surface_id": "WALL_01", "description": "warm off-white plaster", "confidence": "high"}],
        "estimated_intrinsic_colors": [],
        "appearance_confidence": "high",
        "source_color_cast": ["teal-orange"],
        "source_exposure_characteristics": ["crushed shadows"],
        "source_lighting_characteristics": ["temporary warm side light"],
        "removable_lighting_components": ["temporary warm side light"],
        "removable_camera_effects": ["shallow depth of field"],
        "removable_postprocess_components": ["teal-orange grade", "bloom"],
        "intrinsic_emissive_structures": ["fixed cyan emissive strip"],
        "neutral_appearance_rules": ["neutral white balance", "preserve fixed cyan emission", "retain readable contact shadows"],
        "scale_relationships": ["door height anchors room scale"],
        "topology_relationships": ["left doorway connects to excluded corridor"],
        "entrances_and_exits": ["left doorway"],
        "orientation_system": "primary camera faces north wall; doorway west",
        "horizon_or_vertical_reference": "vertical wall edges",
        "intrinsic_scene_state": [{"state_id": "STATE_001", "description": "fixed cyan emissive strip powered on", "identity_defining": True, "preservation_rule": "preserve physical strip and emission without added bloom"}],
        "supported_camera_motion_envelope": {
            "profile_id": "scene_motion_six.v1",
            "supported_movement_types": ["locked_off", "pan", "tilt", "truck", "crane", "orbit", "approach"],
            "azimuth_degrees": {"min": -90, "max": 90},
            "elevation_degrees": {"min": -30, "max": 30},
            "translation_bounds_normalized": {"x": {"min": -1, "max": 1}, "y": {"min": 0, "max": 1}, "z": {"min": -1, "max": 1}},
            "supported_path_ids": ["PATH_LOOP", "PATH_REVEAL"],
            "included_reveal_region_ids": ["REGION_REAR", "REGION_DEPTH"],
            "backside_truth_status": "canonical_completion",
        },
        "unsupported_camera_motion": ["full 360 orbit beyond the completed rear boundary", "travel into REMOTE_CORRIDOR"],
        "coverage_graph": {
            "graph_id": "GRAPH_TEST_SCENE_V2", "profile_id": "scene_motion_six.v1",
            "required_asset_ids": MACHINE_ASSET_IDS, "nodes": nodes, "edges": edges,
            "paths": [
                {"path_id": "PATH_LOOP", "node_ids": [NODE_BY_ASSET[item] for item in ["CDM_001", "COV_001", "SRM_001", "COV_002"]], "edge_ids": ["EDGE_01", "EDGE_02", "EDGE_03", "EDGE_04"], "supported_movement_types": ["pan", "truck", "crane", "orbit"]},
                {"path_id": "PATH_REVEAL", "node_ids": [NODE_BY_ASSET[item] for item in ["COV_001", "COV_003", "SCL_001"]], "edge_ids": ["EDGE_05", "EDGE_06"], "supported_movement_types": ["tilt", "approach"]},
            ],
            "loops": [{"loop_id": "LOOP_01", "node_ids": [NODE_BY_ASSET[item] for item in ["CDM_001", "COV_001", "SRM_001", "COV_002"]], "edge_ids": ["EDGE_01", "EDGE_02", "EDGE_03", "EDGE_04"], "closure_landmark_ids": ["L_001"], "convergence_status": "verified"}],
            "graph_status": "verified",
        },
        "inferred_regions": [done],
        "confidence_level": "high",
        "unresolved_hard_blockers": [],
        "canon_revision": "canon-v2",
        "canon_freeze_status": "frozen",
        "source_asset_dimensions": {"SRC_001": {"width": 192, "height": 108}},
        "target_4k_dimensions": {"width": 3840, "height": 2160},
        "generated_asset_index": MACHINE_ASSET_IDS + ["HRB_001"],
        "four_k_prompt_index": [f"4K_{asset_id}" for asset_id in MACHINE_ASSET_IDS],
        "QA_status": "approved",
    }


def appearance() -> dict[str, Any]:
    return {
        "schema_version": "scene-appearance-decomposition.v1", "scene_id": "TEST_SCENE",
        "source_reference_ids": ["SRC_001"], "heavy_look_detected": True,
        "source_color_cast": ["teal-orange"], "source_exposure_state": ["underexposed shadows"],
        "source_contrast_state": ["high contrast"], "source_key_light_direction": ["camera right"],
        "shadow_compression": "strong", "highlight_clipping": "mild", "bloom_flare": ["cyan strip bloom"],
        "depth_of_field": "shallow source, deep diagnostic target", "grading_characteristics": ["teal-orange", "crushed blacks"],
        "atmosphere_or_medium_state": ["clear interior air"],
        "intrinsic_scene_appearance": [{"surface_or_feature": "WALL_01", "property": "warm off-white plaster", "source_status": "source_locked", "confidence": "high"}],
        "intrinsic_scene_state": [{"state": "fixed cyan strip powered on", "identity_defining": True, "preserve": True, "reason": "fixed emissive architecture"}],
        "external_illumination": [{"effect": "temporary warm side light", "remove_from_neutral_assets": True, "evidence": "color discontinuity on all materials"}],
        "camera_optical_effects": [{"effect": "shallow depth of field", "remove_from_neutral_assets": True, "evidence": "focus falloff"}],
        "postprocess_effects": [{"effect": "teal-orange grade and bloom", "remove_from_neutral_assets": True, "evidence": "highlight halos and split toning"}],
        "unresolved_appearance": [],
        "material_color_inferences": [{"surface_id": "WALL_01", "observed_rendered_color": "orange", "intrinsic_base_color": "warm off-white", "confidence": "high", "status": "confirmed"}],
        "intrinsic_emissive_structures": [{"feature": "fixed cyan emissive strip", "intrinsic": True, "preservation_rule": "preserve strip and emission; remove post bloom"}],
        "neutral_appearance_canon": {"white_balance": "neutral", "illumination": "broad soft diagnostic illumination", "contrast": "low to medium", "shadow_rule": "readable contact shadows", "highlight_rule": "no clipping", "depth_of_field_rule": "sufficient depth for structure", "material_rule": "preserve intrinsic colors and texture", "state_rule": "preserve fixed emissive strip without added bloom", "forbidden_look_components": ["teal-orange grade", "bloom", "flare", "crushed shadows"]},
        "neutralization_strategy": ["remove temporary warm light", "restore neutral wall base color", "preserve cyan emissive structure"],
        "appearance_revision": "appearance-v1", "appearance_freeze_status": "frozen",
    }


def generation_prompt(asset_id: str) -> str:
    role = ROLE_BY_ASSET[asset_id]
    dependencies = ", ".join(DEPENDENCIES[asset_id]) or "no generated predecessor"
    return (
        f"Generate exactly one independent full-frame scene asset for {asset_id}, role {role}. "
        f"Use the ordered references exactly as supplied; approved generated predecessors are {dependencies}. "
        "Preserve the frozen scene identity, topology, room dimensions, west-wall doorway, fixed shelf, warm off-white plaster, cyan intrinsic emissive strip, landmark handedness, neutral diagnostic appearance, and approved rear-wall canonical completion. "
        "The camera pose, yaw, pitch, translation baseline, visible landmarks, occlusion state, and revealed regions must match the bound coverage node and remain inside the supported motion envelope. "
        "Do not add people, products, furniture, signs, text, grids, borders, watermarks, dramatic grading, bloom, flare, crushed shadows, shallow depth of field, or source-look contamination. "
        "Return only one raster image. Do not make identity choices, do not change the frozen prompt, do not perform QA, do not approve the image, and do not publish a package."
    )


def four_k_prompt(asset_name: str) -> str:
    return (
        "Use the matching QA-approved neutral scene asset as the primary and highest-priority reference. "
        f"Preserve the exact {asset_name} camera, topology, landmarks, scale, completion, materials, intrinsic base colors, and neutral appearance. "
        "Only increase resolution and material micro-detail. Do not redesign, reframe, relight, recolor, add objects, or change geometry. "
        "Do not restore the heavy grade, dramatic lighting, crushed shadows, bloom, flare, vignette, grain, or shallow depth of field."
    )


def reference_plan(asset_id: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    if len(DEPENDENCIES[asset_id]) < 5:
        values.append({"index": 1, "alias": "source-scene", "kind": "source_reference", "source_reference_id": "SRC_001", "predecessor_asset_id": None})
    for dependency in DEPENDENCIES[asset_id]:
        values.append({"index": len(values) + 1, "alias": dependency.lower(), "kind": "approved_predecessor", "source_reference_id": None, "predecessor_asset_id": dependency})
    return values


def make_reference_manifest(root: Path, asset_id: str, asset_paths: dict[str, Path]) -> Path:
    sources: list[tuple[str, str | None, Path]] = [("source_reference", None, root / "01_source_analysis/source.png")]
    sources.extend(("approved_predecessor", dependency, asset_paths[dependency]) for dependency in DEPENDENCIES[asset_id])
    output = root / f"10_runtime/{asset_id.lower()}/reference-manifest.json"
    freeze_bundle(asset_id, "SRC_001", output, sources)
    return output


def create_fixture(root: Path) -> None:
    for rel in [
        "00_manifest/SCENE_CANON.md", "00_manifest/SOURCE_APPEARANCE_DECOMPOSITION.md", "00_manifest/ASSET_INDEX.md",
        "01_source_analysis/source_evidence_report.md", "01_source_analysis/conflict_report.md", "01_source_analysis/coverage_assessment.md",
        "09_qa/QA_REPORT.md", "09_qa/failed_asset_log.md", "09_qa/look_contamination_report.md",
        "09_qa/coverage_graph_report.md", "09_qa/4k_prompt_mapping_report.md",
    ]:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(substantive(path.stem), encoding="utf-8")

    make_pattern(root / "01_source_analysis/source.png", 9)
    canon = scene_canon()
    appearance_record = appearance()
    write_json(root / "00_manifest/SCENE_CANON.json", canon)
    write_json(root / "00_manifest/SOURCE_APPEARANCE_DECOMPOSITION.json", appearance_record)
    canon_hash = sha256_file(root / "00_manifest/SCENE_CANON.json")
    appearance_hash = sha256_file(root / "00_manifest/SOURCE_APPEARANCE_DECOMPOSITION.json")
    completion_hash = canonical_json_hash(canon["canonical_completion_elements"])

    prompts = []
    prompt_parts = ["# Six Frozen Generation Prompts\n\nAll six complete prompt bodies are published together before worker dispatch.\n"]
    for order, asset_id in enumerate(MACHINE_ASSET_IDS, 1):
        body = generation_prompt(asset_id)
        digest = sha256_text(body)
        prompt = {
            "prompt_id": f"GEN_{asset_id}", "asset_id": asset_id, "coverage_node_id": NODE_BY_ASSET[asset_id],
            "generation_order": order, "dependency_stage": STAGES[asset_id], "dependency_asset_ids": DEPENDENCIES[asset_id],
            "reference_plan": reference_plan(asset_id), "prompt_body": body, "prompt_sha256": digest, "status": "published",
        }
        prompts.append(prompt)
        prompt_parts.append(f"## {prompt['prompt_id']}\n\nSHA-256: {digest}\n\n{body}\n")
    prompt_doc = "\n".join(prompt_parts)
    prompt_path = root / "00_manifest/GENERATION_PROMPTS.md"
    prompt_path.write_text(prompt_doc, encoding="utf-8")

    rollout = root / "10_runtime/parent-rollout.jsonl"
    rollout.parent.mkdir(parents=True, exist_ok=True)
    publication_event_id = "event-six-prompts-public"
    rollout_events = [
        {"type": "session_meta", "payload": {"id": "parent-thread-fixture"}},
        {"type": "response_item", "payload": {"type": "message", "event_id": publication_event_id, "elapsed_ms": 100, "assistant_message": prompt_doc}},
    ]
    for order, asset_id in enumerate(MACHINE_ASSET_IDS, 1):
        rollout_events.append({"type": "response_item", "payload": {"type": "function_call", "name": "spawn_agent", "call_id": f"spawn-{order}", "asset_id": asset_id}})
    rollout.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in rollout_events), encoding="utf-8", newline="\n")
    publication = {
        "schema_version": "scene_prompt_publication_receipt.v1", "origin": "deterministic_contract_fixture",
        "parent_thread_id": "parent-thread-fixture", "parent_rollout_path": str(rollout.resolve()), "parent_rollout_sha256": sha256_file(rollout),
        "publication_event_id": publication_event_id, "publication_event_index": 1, "publication_elapsed_ms": 100,
        "prompt_document_sha256": sha256_text(prompt_doc),
        "published_prompt_ids": [item["prompt_id"] for item in prompts],
        "published_prompt_sha256": [item["prompt_sha256"] for item in prompts],
        "first_worker_spawn_event_index": 2, "first_worker_spawn_elapsed_ms": 200,
    }
    publication_path = root / "10_runtime/prompt-publication-receipt.json"
    write_json(publication_path, publication)

    asset_paths: dict[str, Path] = {}
    for seed, asset_id in enumerate(MACHINE_ASSET_IDS, 1):
        asset_paths[asset_id] = root / ASSET_PATHS[asset_id]
        make_pattern(asset_paths[asset_id], seed)
    review_path = root / "07_review_board/scene_asset_overview_board.png"

    manifest = read_json(TEMPLATE)
    manifest.update({
        "package_id": "TEST_SCENE_ASSET_PACK_V2", "scene_id": "TEST_SCENE", "canon_revision": "canon-v2",
        "canon_sha256": canon_hash, "appearance_revision": "appearance-v1", "appearance_sha256": appearance_hash,
        "completion_hash": completion_hash, "package_status": "packaged", "task_finalization_status": "complete",
        "assistant_qa_status": "passed", "runtime_evidence_origin": "deterministic_contract_fixture",
        "generation_prompt_document_sha256": sha256_text(prompt_doc),
        "prompt_publication_receipt_sha256": sha256_file(publication_path),
        "generation_prompt_records": prompts, "approved_machine_asset_count": 6, "four_k_prompt_mapping_count": 6,
        "human_review_overview_board": "07_review_board/scene_asset_overview_board.png",
    })
    manifest["generation_queue"] = {
        "ordered_asset_ids": MACHINE_ASSET_IDS, "status": "complete", "current_asset_id": None, "next_asset_id": None,
        "max_parallel_workers": 1, "user_continuation_required": False,
        "first_worker_spawn_elapsed_ms": 200, "last_worker_complete_elapsed_ms": 1300,
    }

    dimensions_index: dict[str, Any] = {}
    asset_by_id = {item["asset_id"]: item for item in manifest["assets"]}
    for order, asset_id in enumerate(MACHINE_ASSET_IDS, 1):
        image_path = asset_paths[asset_id]
        ref_path = make_reference_manifest(root, asset_id, asset_paths)
        spawn = 200 + (order - 1) * 200
        inspected = spawn + 100
        result_rel = f"10_runtime/{asset_id.lower()}-worker-result.json"
        inspection_rel = f"10_runtime/{asset_id.lower()}-inspection.json"
        result_path = root / result_rel
        result = {
            "contract": "delegated_image_worker_result.v3", "ok": True,
            "asset_id": asset_id, "attempt_id": f"ATTEMPT_{asset_id}_01",
            "binding_mode": "parent_spawn_cipher_chain_v1", "prompt_sha_match": True,
            "generation_prompt_sha256": prompts[order - 1]["prompt_sha256"], "tool_prompt_sha256": prompts[order - 1]["prompt_sha256"],
            "run_image_path": str(image_path.resolve()), "image_sha256": sha256_file(image_path), "width_px": 192, "height_px": 108,
            "reference_manifest_path": str(ref_path.resolve()), "reference_manifest_sha256": sha256_file(ref_path),
            "ordered_reference_bundle_sha256": read_json(ref_path)["ordered_bundle_sha256"],
            "reference_count": len(read_json(ref_path)["ordered_references"]),
            "agent_path": f"/root/scene_canon_image_{asset_id.lower()}_{order:032x}", "worker_task_name": f"scene_canon_image_{asset_id.lower()}_{order:032x}", "worker_thread_id": f"worker-thread-{order}",
            "parent_thread_id": "parent-thread-fixture", "worker_run_nonce": f"{order:032x}",
            "image_generation_call_id": f"image-call-{order}", "parent_spawn_activity_ms": spawn, "parent_spawn_event_index": order + 1,
        }
        write_json(result_path, result)
        inspection = {
            "schema_version": "scene_inspection_receipt.v1", "origin": "deterministic_contract_fixture",
            "inspector_task_id": "parent-thread-fixture",
            "receipt_id": f"INSPECT_{asset_id}", "asset_id": asset_id, "coverage_node_id": NODE_BY_ASSET[asset_id],
            "worker_result_path": result_rel, "worker_result_sha256": sha256_file(result_path),
            "image_path": ASSET_PATHS[asset_id], "image_sha256": sha256_file(image_path),
            "inspected_elapsed_ms": inspected, "decision": "approved",
            "evidence_summary": "Main-agent inspection confirms distinct pose, required overlap, reveal, topology, material identity, and neutral appearance.",
            "checks": {key: True for key in CHECKS},
            "observed_landmark_ids": ["L_001"],
            "observed_revealed_region_ids": next(item for item in canon["coverage_graph"]["nodes"] if item["asset_id"] == asset_id)["revealed_region_ids"],
        }
        inspection_path = root / inspection_rel
        write_json(inspection_path, inspection)
        asset = asset_by_id[asset_id]
        asset.update({
            "file_sha256": sha256_file(image_path), "generation_status": "generated", "accepted_attempt_id": f"ATTEMPT_{asset_id}_01",
            "assistant_qa_status": "approved", "actual_pixel_dimensions": {"width": 192, "height": 108}, "actual_dimensions_verified": True,
            "canon_sha256": canon_hash, "appearance_sha256": appearance_hash, "completion_hash": completion_hash,
            "worker_result_path": result_rel, "worker_result_sha256": sha256_file(result_path),
            "inspection_receipt_path": inspection_rel, "inspection_receipt_sha256": sha256_file(inspection_path),
            "four_k_prompt_id": f"4K_{asset_id}",
        })
        dimensions_index[asset_id] = {"file_path": ASSET_PATHS[asset_id], "width": 192, "height": 108, "verified": True}

    write_json(root / "00_manifest/ASSET_MANIFEST.json", manifest)
    build_result = subprocess.run([sys.executable, str(HERE / "build_review_board.py"), str(root / "00_manifest/ASSET_MANIFEST.json"), str(review_path)], text=True, capture_output=True)
    if build_result.returncode != 0:
        raise RuntimeError(build_result.stdout + build_result.stderr)
    review = asset_by_id["HRB_001"]
    with Image.open(review_path) as review_image:
        review_width, review_height = review_image.size
    review.update({
        "file_sha256": sha256_file(review_path), "generation_status": "generated", "accepted_attempt_id": "DERIVED_FROM_SIX_APPROVED_ASSETS",
        "assistant_qa_status": "approved", "actual_pixel_dimensions": {"width": review_width, "height": review_height}, "actual_dimensions_verified": True,
        "canon_sha256": canon_hash, "appearance_sha256": appearance_hash, "completion_hash": completion_hash,
    })
    write_json(root / "00_manifest/actual_image_dimensions.json", dimensions_index)

    four_k = []
    four_k_parts = ["# Finalized 4K Regeneration Prompts\n"]
    for asset_id in MACHINE_ASSET_IDS:
        asset = asset_by_id[asset_id]
        body = four_k_prompt(asset["asset_name"])
        record = {
            "prompt_id": f"4K_{asset_id}", "asset_id": asset_id, "asset_name": asset["asset_name"], "source_image": asset["file_path"],
            "source_dimensions": asset["actual_pixel_dimensions"], "target_dimensions": {"width": 3840, "height": 2160}, "asset_type": asset["asset_type"],
            "required_reference_images": [asset["file_path"]], "reference_priority": ["matching QA-approved neutral asset"],
            "primary_reference_asset_id": asset_id,
            "preservation_checklist": ["camera", "height", "framing", "crop", "perspective", "topology", "landmarks", "scale", "materials"],
            "allowed_enhancements": ["resolution", "micro-detail"],
            "forbidden_structural_changes": ["camera", "framing", "perspective", "topology", "landmark movement"],
            "forbidden_look_changes": ["heavy grade", "dramatic light", "crushed shadows", "bloom", "flare"],
            "regeneration_prompt_en": body,
            "negative_constraints": ["no redesign", "no relight", "no recolor", "no reframe", "no new objects"],
            "post_generation_qa_checklist": ["identity", "camera", "topology", "materials", "neutral look"],
            "source_asset_revision": 1, "source_asset_sha256": asset["file_sha256"], "source_canon_sha256": canon_hash,
            "source_appearance_sha256": appearance_hash, "source_completion_hash": completion_hash, "status": "finalized_post_qa",
        }
        four_k.append(record)
        four_k_parts.append(f"## {record['prompt_id']}\n\n{body}\n")
    manifest["four_k_prompt_records"] = four_k
    output_4k = root / "08_4k_regeneration/4K_ASSET_REGENERATION_PROMPTS.md"
    output_4k.parent.mkdir(parents=True, exist_ok=True)
    output_4k.write_text("\n".join(four_k_parts), encoding="utf-8")

    qa = []
    inspection_ids = {asset_id: f"INSPECT_{asset_id}" for asset_id in MACHINE_ASSET_IDS}
    node_asset = {item["node_id"]: item["asset_id"] for item in canon["coverage_graph"]["nodes"]}
    def bind(asset_ids: list[str]) -> tuple[list[str], list[str]]:
        return ([asset_by_id[item]["file_sha256"] for item in asset_ids], [inspection_ids[item] for item in asset_ids])
    for asset_id in MACHINE_ASSET_IDS:
        qa.append({"check_id": f"ASSET_{asset_id}", "scope": "asset", "subject_ids": [asset_id], "status": "passed", "applicability": "required", "evidence_summary": "Bound inspection verifies the complete asset hard-gate checklist.", "bound_asset_sha256": [asset_by_id[asset_id]["file_sha256"]], "inspection_receipt_ids": [f"INSPECT_{asset_id}"]})
    for item in canon["coverage_graph"]["edges"]:
        asset_ids = [node_asset[item["from_node_id"]], node_asset[item["to_node_id"]]]; hashes, receipts = bind(asset_ids)
        qa.append({"check_id": f"QA_{item['edge_id']}", "scope": "edge", "subject_ids": [item["edge_id"]], "status": "passed", "applicability": "required", "evidence_summary": "Shared landmarks, overlap invariants, reveal order, and parallax are verified.", "bound_asset_sha256": hashes, "inspection_receipt_ids": receipts})
    for item in canon["coverage_graph"]["paths"]:
        asset_ids = [node_asset[node_id] for node_id in item["node_ids"]]; hashes, receipts = bind(asset_ids)
        qa.append({"check_id": f"QA_{item['path_id']}", "scope": "path", "subject_ids": [item["path_id"]], "status": "passed", "applicability": "required", "evidence_summary": "Every directed edge and declared movement is executable within the envelope.", "bound_asset_sha256": hashes, "inspection_receipt_ids": receipts})
    for item in canon["coverage_graph"]["loops"]:
        asset_ids = [node_asset[node_id] for node_id in item["node_ids"]]; hashes, receipts = bind(asset_ids)
        qa.append({"check_id": f"QA_{item['loop_id']}", "scope": "loop", "subject_ids": [item["loop_id"]], "status": "passed", "applicability": "required", "evidence_summary": "Loop closure returns to the same landmark identity and handedness.", "bound_asset_sha256": hashes, "inspection_receipt_ids": receipts})
    all_hashes, all_receipts = bind(MACHINE_ASSET_IDS)
    for check_id in ["prompt_publication", "runtime_lineage", "duplicate_detection", "four_k_mapping"]:
        qa.append({"check_id": check_id, "scope": "package", "subject_ids": ["TEST_SCENE_ASSET_PACK_V2"], "status": "passed", "applicability": "required", "evidence_summary": "Package-level receipt and one-to-one reconciliation passed the strict validator.", "bound_asset_sha256": all_hashes, "inspection_receipt_ids": all_receipts})
    manifest["structured_qa_records"] = qa
    write_json(root / "00_manifest/ASSET_MANIFEST.json", manifest)


def load_manifest(root: Path) -> dict[str, Any]:
    return read_json(root / "00_manifest/ASSET_MANIFEST.json")


def save_manifest(root: Path, value: dict[str, Any]) -> None:
    write_json(root / "00_manifest/ASSET_MANIFEST.json", value)


def rebind_canon(root: Path) -> None:
    canon_hash = sha256_file(root / "00_manifest/SCENE_CANON.json")
    manifest = load_manifest(root)
    manifest["canon_sha256"] = canon_hash
    for asset in manifest["assets"]:
        asset["canon_sha256"] = canon_hash
    for record in manifest["four_k_prompt_records"]:
        record["source_canon_sha256"] = canon_hash
    save_manifest(root, manifest)


def rebind_canon_hash_only(root: Path) -> None:
    canon_hash = sha256_file(root / "00_manifest/SCENE_CANON.json")
    manifest = load_manifest(root)
    manifest["canon_sha256"] = canon_hash
    for asset in manifest["assets"]:
        asset["canon_sha256"] = canon_hash
    for record in manifest["four_k_prompt_records"]:
        record["source_canon_sha256"] = canon_hash
    save_manifest(root, manifest)


def refresh_qa_bindings(manifest: dict[str, Any], canon: dict[str, Any]) -> None:
    asset_by_id = {item["asset_id"]: item for item in manifest["assets"]}
    inspection_ids = {asset_id: f"INSPECT_{asset_id}" for asset_id in MACHINE_ASSET_IDS}
    node_asset = {item["node_id"]: item["asset_id"] for item in canon["coverage_graph"]["nodes"]}
    edge_assets = {item["edge_id"]: [node_asset[item["from_node_id"]], node_asset[item["to_node_id"]]] for item in canon["coverage_graph"]["edges"]}
    path_assets = {item["path_id"]: [node_asset[node_id] for node_id in item["node_ids"]] for item in canon["coverage_graph"]["paths"]}
    loop_assets = {item["loop_id"]: [node_asset[node_id] for node_id in item["node_ids"]] for item in canon["coverage_graph"]["loops"]}
    for record in manifest["structured_qa_records"]:
        if record["scope"] == "package":
            asset_ids = MACHINE_ASSET_IDS
        elif record["scope"] == "asset":
            asset_ids = record["subject_ids"]
        elif record["scope"] == "edge":
            asset_ids = edge_assets.get(record["subject_ids"][0], [])
        elif record["scope"] == "path":
            asset_ids = path_assets.get(record["subject_ids"][0], [])
        else:
            asset_ids = loop_assets.get(record["subject_ids"][0], [])
        record["bound_asset_sha256"] = [asset_by_id[item]["file_sha256"] for item in asset_ids]
        record["inspection_receipt_ids"] = [inspection_ids[item] for item in asset_ids]


def rebind_runtime(root: Path) -> None:
    manifest = load_manifest(root)
    canon = read_json(root / "00_manifest/SCENE_CANON.json")
    assets = {item["asset_id"]: item for item in manifest["assets"]}
    paths = {asset_id: root / ASSET_PATHS[asset_id] for asset_id in MACHINE_ASSET_IDS}
    for asset_id in MACHINE_ASSET_IDS:
        asset = assets[asset_id]
        image_path = paths[asset_id]
        ref_path = make_reference_manifest(root, asset_id, paths)
        result_path = root / asset["worker_result_path"]
        result = read_json(result_path)
        result.update({
            "run_image_path": str(image_path.resolve()), "image_sha256": sha256_file(image_path),
            "reference_manifest_path": str(ref_path.resolve()), "reference_manifest_sha256": sha256_file(ref_path),
            "ordered_reference_bundle_sha256": read_json(ref_path)["ordered_bundle_sha256"],
            "reference_count": len(read_json(ref_path)["ordered_references"]),
        })
        write_json(result_path, result)
        inspection_path = root / asset["inspection_receipt_path"]
        inspection = read_json(inspection_path)
        inspection.update({"worker_result_sha256": sha256_file(result_path), "image_sha256": sha256_file(image_path)})
        write_json(inspection_path, inspection)
        asset.update({
            "file_sha256": sha256_file(image_path), "worker_result_sha256": sha256_file(result_path),
            "inspection_receipt_sha256": sha256_file(inspection_path),
        })
    for record in manifest["four_k_prompt_records"]:
        record["source_asset_sha256"] = assets[record["asset_id"]]["file_sha256"]
    refresh_qa_bindings(manifest, canon)
    save_manifest(root, manifest)


def make_stage_fixture(root: Path, through_asset: str) -> None:
    manifest = load_manifest(root)
    template = read_json(TEMPLATE)
    through_index = MACHINE_ASSET_IDS.index(through_asset)
    template_assets = {item["asset_id"]: item for item in template["assets"]}
    for index, asset_id in enumerate(MACHINE_ASSET_IDS):
        if index > through_index:
            replacement = copy.deepcopy(template_assets[asset_id])
            manifest["assets"][index] = replacement
    manifest["assets"][-1] = copy.deepcopy(template_assets["HRB_001"])
    manifest.update({"package_status": "generating", "task_finalization_status": "in_progress", "assistant_qa_status": "not_reviewed", "human_review_overview_board": None})
    next_asset = MACHINE_ASSET_IDS[through_index + 1] if through_index + 1 < len(MACHINE_ASSET_IDS) else None
    last_inspected = 300 + through_index * 200
    manifest["generation_queue"] = {
        "ordered_asset_ids": MACHINE_ASSET_IDS, "status": "running", "current_asset_id": next_asset, "next_asset_id": next_asset,
        "max_parallel_workers": 1, "user_continuation_required": False,
        "first_worker_spawn_elapsed_ms": 200, "last_worker_complete_elapsed_ms": last_inspected,
    }
    dimensions_index = read_json(root / "00_manifest/actual_image_dimensions.json")
    write_json(root / "00_manifest/actual_image_dimensions.json", {asset_id: dimensions_index[asset_id] for asset_id in MACHINE_ASSET_IDS[: through_index + 1]})
    save_manifest(root, manifest)


def mutate_one_machine_plus_review(root: Path) -> None:
    value = load_manifest(root); value["assets"] = [value["assets"][0], value["assets"][-1]]; save_manifest(root, value)


def mutate_missing_role(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["coverage_graph"]["nodes"].pop(); write_json(root / "00_manifest/SCENE_CANON.json", canon)


def mutate_graph_manifest_gap(root: Path) -> None:
    value = load_manifest(root); value["assets"][4]["coverage_node_id"] = "NODE_COV_002"; save_manifest(root, value)


def mutate_same_role(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["coverage_graph"]["nodes"][3]["role"] = "left_adjacent_continuity"; write_json(root / "00_manifest/SCENE_CANON.json", canon)


def mutate_same_direction(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json")
    for item in canon["coverage_graph"]["nodes"]: item["camera_pose"]["yaw_degrees"] = 0; item["camera_pose"]["pitch_degrees"] = 0
    write_json(root / "00_manifest/SCENE_CANON.json", canon)


def mutate_duplicate_tuple(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["coverage_graph"]["nodes"][3]["camera_pose"] = copy.deepcopy(canon["coverage_graph"]["nodes"][2]["camera_pose"]); write_json(root / "00_manifest/SCENE_CANON.json", canon)


def mutate_exact_duplicate(root: Path) -> None:
    left = root / ASSET_PATHS["CDM_001"]; right = root / ASSET_PATHS["COV_002"]; shutil.copyfile(left, right)
    value = load_manifest(root); value["assets"][3]["file_sha256"] = value["assets"][0]["file_sha256"]; save_manifest(root, value)


def mutate_near_duplicate(root: Path) -> None:
    source = Image.open(root / ASSET_PATHS["CDM_001"]).convert("RGB")
    source.save(root / ASSET_PATHS["COV_002"], format="JPEG", quality=94)
    value = load_manifest(root); value["assets"][3]["file_sha256"] = sha256_file(root / ASSET_PATHS["COV_002"]); save_manifest(root, value)
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["coverage_graph"]["nodes"][3]["revealed_region_ids"] = canon["coverage_graph"]["nodes"][0]["revealed_region_ids"]; write_json(root / "00_manifest/SCENE_CANON.json", canon)


def mutate_missing_loop(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["coverage_graph"]["loops"] = []; write_json(root / "00_manifest/SCENE_CANON.json", canon)


def mutate_awaiting_continuation(root: Path) -> None:
    value = load_manifest(root); value["generation_queue"]["status"] = "running"; value["generation_queue"]["current_asset_id"] = "COV_001"; value["generation_queue"]["next_asset_id"] = "COV_002"; save_manifest(root, value)


def mutate_self_attested_runtime(root: Path) -> None:
    value = load_manifest(root); value["assets"][2]["worker_result_path"] = "10_runtime/missing-self-attested.json"; save_manifest(root, value)


def mutate_prompt_body(root: Path) -> None:
    value = load_manifest(root); value["generation_prompt_records"][0]["prompt_body"] += " unauthorized mutation"; save_manifest(root, value)


def mutate_missing_source_anchor(root: Path) -> None:
    value = load_manifest(root); value["generation_prompt_records"][-1]["reference_plan"].pop(0); save_manifest(root, value)


def mutate_placeholder_qa(root: Path) -> None:
    (root / "09_qa/coverage_graph_report.md").write_text("TODO", encoding="utf-8")


def mutate_live_origin_relabel(root: Path) -> None:
    manifest = load_manifest(root)
    publication_path = root / manifest["prompt_publication_receipt_path"]
    publication = read_json(publication_path)
    publication["origin"] = "live_runtime"
    write_json(publication_path, publication)
    manifest["prompt_publication_receipt_sha256"] = sha256_file(publication_path)
    for asset in manifest["assets"]:
        if not asset["is_machine_asset"]:
            continue
        inspection_path = root / asset["inspection_receipt_path"]
        inspection = read_json(inspection_path)
        inspection["origin"] = "live_runtime"
        write_json(inspection_path, inspection)
        asset["inspection_receipt_sha256"] = sha256_file(inspection_path)
    manifest["runtime_evidence_origin"] = "live_runtime"
    save_manifest(root, manifest)


def mutate_non_executable_path(root: Path) -> None:
    canon_path = root / "00_manifest/SCENE_CANON.json"
    canon = read_json(canon_path)
    reveal_path = next(item for item in canon["coverage_graph"]["paths"] if item["path_id"] == "PATH_REVEAL")
    reveal_path["node_ids"] = [NODE_BY_ASSET[item] for item in ["COV_001", "SCL_001", "COV_003"]]
    write_json(canon_path, canon)
    rebind_canon(root)


def mutate_duplicate_4k_prompt_ids(root: Path) -> None:
    manifest = load_manifest(root)
    for asset in manifest["assets"]:
        if asset["is_machine_asset"]:
            asset["four_k_prompt_id"] = "4K_SHARED"
    for record in manifest["four_k_prompt_records"]:
        record["prompt_id"] = "4K_SHARED"
    save_manifest(root, manifest)
    with (root / "08_4k_regeneration/4K_ASSET_REGENERATION_PROMPTS.md").open("a", encoding="utf-8") as handle:
        handle.write("\n## 4K_SHARED\n\nShared prompt marker used only by the negative fixture.\n")


def mutate_schema_additional_properties(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["source_asset_dimensions"]["SRC_001"] = "not-dimensions"; write_json(root / "00_manifest/SCENE_CANON.json", canon); rebind_canon(root)


def mutate_nan_number(root: Path) -> None:
    path = root / "00_manifest/SCENE_CANON.json"; text = path.read_text(encoding="utf-8"); path.write_text(text.replace('"translation_baseline_normalized": 0.25', '"translation_baseline_normalized": NaN', 1), encoding="utf-8", newline="\n"); rebind_canon_hash_only(root)


def mutate_empty_core_markdown(root: Path) -> None:
    (root / "00_manifest/SCENE_CANON.md").write_text("", encoding="utf-8")


def mutate_hrb_reuses_machine(root: Path) -> None:
    manifest = load_manifest(root); machine = manifest["assets"][0]; review = manifest["assets"][-1]
    review.update({"file_path": machine["file_path"], "file_sha256": machine["file_sha256"], "actual_pixel_dimensions": machine["actual_pixel_dimensions"]})
    manifest["human_review_overview_board"] = machine["file_path"]; save_manifest(root, manifest)


def mutate_primary_reference_ghost(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["primary_reference"] = "SRC_GHOST"; write_json(root / "00_manifest/SCENE_CANON.json", canon); rebind_canon(root)


def mutate_duplicate_source_id(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["source_reference_list"].append(copy.deepcopy(canon["source_reference_list"][0])); write_json(root / "00_manifest/SCENE_CANON.json", canon); rebind_canon(root)


def mutate_source_locator_escape(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["source_reference_list"][0]["source_locator"] = "../../outside-source.png"; write_json(root / "00_manifest/SCENE_CANON.json", canon); rebind_canon(root)


def mutate_loop_edges_unrelated(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["coverage_graph"]["loops"][0]["edge_ids"] = ["EDGE_05", "EDGE_06", "EDGE_01", "EDGE_02"]; write_json(root / "00_manifest/SCENE_CANON.json", canon); rebind_canon(root)


def mutate_ghost_edge_path(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["coverage_graph"]["edges"][0]["path_ids"].append("PATH_GHOST"); write_json(root / "00_manifest/SCENE_CANON.json", canon); rebind_canon(root)


def mutate_negative_publication_time(root: Path) -> None:
    manifest = load_manifest(root); path = root / manifest["prompt_publication_receipt_path"]; receipt = read_json(path); receipt["publication_elapsed_ms"] = -100; write_json(path, receipt); manifest["prompt_publication_receipt_sha256"] = sha256_file(path); save_manifest(root, manifest)


def mutate_foreign_publication_parent(root: Path) -> None:
    manifest = load_manifest(root); receipt_path = root / manifest["prompt_publication_receipt_path"]; receipt = read_json(receipt_path)
    old_rollout = Path(receipt["parent_rollout_path"]); events = old_rollout.read_text(encoding="utf-8").splitlines(); meta = json.loads(events[0]); meta["payload"]["id"] = "foreign-parent-thread"
    foreign = root / "10_runtime/foreign-parent.jsonl"; foreign.write_text(json.dumps(meta) + "\n" + "\n".join(events[1:]) + "\n", encoding="utf-8", newline="\n")
    receipt.update({"parent_thread_id": "foreign-parent-thread", "parent_rollout_path": str(foreign.resolve()), "parent_rollout_sha256": sha256_file(foreign)})
    write_json(receipt_path, receipt); manifest["prompt_publication_receipt_sha256"] = sha256_file(receipt_path); save_manifest(root, manifest)


def mutate_4k_target_tiny(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["target_4k_dimensions"] = {"width": 1, "height": 1}; write_json(root / "00_manifest/SCENE_CANON.json", canon); rebind_canon(root)
    manifest = load_manifest(root)
    for asset in manifest["assets"]: asset["target_pixel_dimensions"] = {"width": 1, "height": 1}
    for record in manifest["four_k_prompt_records"]: record["target_dimensions"] = {"width": 1, "height": 1}
    save_manifest(root, manifest)


def mutate_4k_missing_reference(root: Path) -> None:
    manifest = load_manifest(root); manifest["four_k_prompt_records"][0]["required_reference_images"] = ["missing/reference.png"]; save_manifest(root, manifest)


def mutate_stale_structured_qa(root: Path) -> None:
    manifest = load_manifest(root); record = next(item for item in manifest["structured_qa_records"] if item["scope"] == "asset"); record["bound_asset_sha256"] = ["0" * 64]; record["inspection_receipt_ids"] = ["INSPECT_GHOST"]; save_manifest(root, manifest)


def mutate_closure_landmark_ghost(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["coverage_graph"]["loops"][0]["closure_landmark_ids"] = ["L_GHOST"]; write_json(root / "00_manifest/SCENE_CANON.json", canon); rebind_canon(root)


def mutate_envelope_reveal_ghost(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["supported_camera_motion_envelope"]["included_reveal_region_ids"] = ["REGION_GHOST"]; write_json(root / "00_manifest/SCENE_CANON.json", canon); rebind_canon(root)


def mutate_edge_reveal_ghost(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["coverage_graph"]["edges"][0]["reveal_order_region_ids"] = ["REGION_GHOST"]; write_json(root / "00_manifest/SCENE_CANON.json", canon); rebind_canon(root)


def mutate_node_evidence_ghost(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["coverage_graph"]["nodes"][0]["source_evidence_ids"] = ["E_GHOST"]; write_json(root / "00_manifest/SCENE_CANON.json", canon); rebind_canon(root)


def mutate_node_completion_ghost(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["coverage_graph"]["nodes"][0]["canonical_completion_ids"] = ["COMP_GHOST"]; write_json(root / "00_manifest/SCENE_CANON.json", canon); rebind_canon(root)


def mutate_dangling_adjacency(root: Path) -> None:
    canon = read_json(root / "00_manifest/SCENE_CANON.json"); canon["coverage_graph"]["nodes"][0]["adjacent_node_ids"].append("NODE_GHOST"); write_json(root / "00_manifest/SCENE_CANON.json", canon); rebind_canon(root)


def mutate_wrong_worker_asset(root: Path) -> None:
    manifest = load_manifest(root); asset = manifest["assets"][0]; path = root / asset["worker_result_path"]; result = read_json(path); nonce = result["worker_run_nonce"]; result["agent_path"] = f"/root/scene_canon_image_srm_001_{nonce}"; result["worker_task_name"] = f"scene_canon_image_srm_001_{nonce}"; write_json(path, result); asset["worker_result_sha256"] = sha256_file(path)
    inspection = root / asset["inspection_receipt_path"]; receipt = read_json(inspection); receipt["worker_result_sha256"] = asset["worker_result_sha256"]; write_json(inspection, receipt); asset["inspection_receipt_sha256"] = sha256_file(inspection); save_manifest(root, manifest)


def mutate_attempt_mismatch(root: Path) -> None:
    manifest = load_manifest(root); asset = manifest["assets"][0]; path = root / asset["worker_result_path"]; result = read_json(path); result["attempt_id"] = "ATTEMPT_OTHER_01"; write_json(path, result); asset["worker_result_sha256"] = sha256_file(path)
    inspection = root / asset["inspection_receipt_path"]; receipt = read_json(inspection); receipt["worker_result_sha256"] = asset["worker_result_sha256"]; write_json(inspection, receipt); asset["inspection_receipt_sha256"] = sha256_file(inspection); save_manifest(root, manifest)


def mutate_inspection_owner(root: Path) -> None:
    manifest = load_manifest(root); asset = manifest["assets"][0]; path = root / asset["inspection_receipt_path"]; receipt = read_json(path); receipt["inspector_task_id"] = "foreign-task"; write_json(path, receipt); asset["inspection_receipt_sha256"] = sha256_file(path); save_manifest(root, manifest)


def mutate_reencoded_same_pixels(root: Path) -> None:
    source = Image.open(root / ASSET_PATHS["CDM_001"]).convert("RGB"); source.save(root / ASSET_PATHS["COV_002"], format="PNG", compress_level=9); rebind_runtime(root)


def mutate_unlisted_frozen_reference(root: Path) -> None:
    extra = root / "10_runtime/cdm_001/references/99-unlisted.png"; make_pattern(extra, 15)


def run() -> int:
    assert_standalone_skill_contract()
    print("PASS standalone package contract")
    with tempfile.TemporaryDirectory(prefix="scene-canon-v2-") as temporary:
        base = Path(temporary) / "valid"
        create_fixture(base)
        errors = validate_package(base, mode="delivery", fixture_mode=True)
        if errors:
            print("FAIL valid fixture")
            for error in errors: print(f"  - {error}")
            return 1
        print("PASS valid strict six-asset fixture")

        production_errors = validate_package(base, mode="delivery", fixture_mode=False)
        if not any("deterministic fixture receipts" in error for error in production_errors):
            print("FAIL fixture evidence unexpectedly satisfied production delivery")
            return 1
        print("PASS fixture/live evidence boundary")

        relabeled = Path(temporary) / "live_origin_relabel"
        create_fixture(relabeled)
        mutate_live_origin_relabel(relabeled)
        relabeled_errors = validate_package(relabeled, mode="delivery", fixture_mode=False)
        if not any("live worker result missing audited provenance fields" in error for error in relabeled_errors):
            print("FAIL live_origin_relabel: relabeled fixture receipts satisfied production delivery")
            for error in relabeled_errors: print(f"  - {error}")
            return 1
        print("PASS expected failure: live_origin_relabel")

        state = Path(temporary) / "state"
        create_fixture(state)
        state_manifest = load_manifest(state)
        state_manifest["package_status"] = "repair_required"
        state_manifest["task_finalization_status"] = "in_progress"
        state_manifest["assistant_qa_status"] = "failed"
        save_manifest(state, state_manifest)
        state_errors = validate_package(state, mode="state")
        if state_errors:
            print("FAIL valid repair state")
            for error in state_errors: print(f"  - {error}")
            return 1
        print("PASS state validator remains separate from delivery")

        stage = Path(temporary) / "stage"
        create_fixture(stage)
        make_stage_fixture(stage, "COV_001")
        stage_errors = validate_package(stage, mode="stage", fixture_mode=True, through_asset="COV_001")
        if stage_errors:
            print("FAIL valid strict stage runtime")
            for error in stage_errors: print(f"  - {error}")
            return 1
        print("PASS strict stage runtime prefix")

        stage_attempt = Path(temporary) / "stage_attempt_mismatch"
        create_fixture(stage_attempt); make_stage_fixture(stage_attempt, "COV_001"); mutate_attempt_mismatch(stage_attempt)
        stage_attempt_errors = validate_package(stage_attempt, mode="stage", fixture_mode=True, through_asset="COV_001")
        if not any("does not bind asset and accepted attempt" in error for error in stage_attempt_errors):
            print("FAIL stage accepted an attempt mismatch")
            return 1
        print("PASS expected stage failure: attempt_mismatch")

        stage_owner = Path(temporary) / "stage_inspection_owner"
        create_fixture(stage_owner); make_stage_fixture(stage_owner, "COV_001"); mutate_inspection_owner(stage_owner)
        stage_owner_errors = validate_package(stage_owner, mode="stage", fixture_mode=True, through_asset="COV_001")
        if not any("inspection owner is not" in error for error in stage_owner_errors):
            print("FAIL stage accepted a foreign inspection owner")
            return 1
        print("PASS expected stage failure: inspection_owner")

        review_output = Path(temporary) / "review.png"
        result = subprocess.run([sys.executable, str(HERE / "build_review_board.py"), str(base / "00_manifest/ASSET_MANIFEST.json"), str(review_output)], text=True, capture_output=True)
        if result.returncode != 0 or not review_output.is_file():
            print("FAIL review-board composition")
            print(result.stdout + result.stderr)
            return 1
        print("PASS review-board composition smoke")

        help_result = subprocess.run([sys.executable, str(HERE / "resolve_worker_image.py"), "--help"], text=True, capture_output=True)
        if help_result.returncode != 0 or "delegated" not in (help_result.stdout + help_result.stderr).lower():
            print("FAIL vendored worker resolver smoke")
            return 1
        nonce = "a" * 32
        for asset_slug in SCENE_CANON_ASSET_TASK_SLUGS:
            expected_task = f"scene_canon_image_{asset_slug}_{nonce}"
            if validate_worker_name_binding(f"/root/{expected_task}", nonce) != expected_task:
                print(f"FAIL scene worker name binding: {asset_slug}")
                return 1
        for invalid_task in (
            f"single_face_image_cdm_001_{nonce}",
            f"scene_canon_image_garbage_{nonce}",
            f"scene_canon_image__{nonce}",
        ):
            try:
                validate_worker_name_binding(f"/root/{invalid_task}", nonce)
            except ContractError:
                continue
            print(f"FAIL resolver accepted an invalid worker namespace: {invalid_task}")
            return 1
        reference_probe = load_reference_manifest(base / "10_runtime/cdm_001/reference-manifest.json", "CDM_001")
        if reference_probe["reference_count"] != 1 or reference_probe["source_reference_id"] != "SRC_001":
            print("FAIL vendored resolver could not load the Scene Canon frozen reference bundle")
            return 1
        print("PASS vendored worker resolver smoke")
        resolver_result = run_resolver_e2e_probe(Path(temporary) / "resolver_e2e")
        print(f"PASS resolver full synthetic state/parent/worker rollout: {resolver_result['asset_id']} {resolver_result['attempt_id']}")

        cases: list[tuple[str, Callable[[Path], None], str]] = [
            ("one_machine_plus_review_packaged", mutate_one_machine_plus_review, "at least 7 items"),
            ("missing_required_asset_role", mutate_missing_role, "at least 6 items"),
            ("coverage_graph_manifest_gap", mutate_graph_manifest_gap, "back-pointer mismatch"),
            ("same_asset_multiple_roles", mutate_same_role, "mandatory roles must be unique and complete"),
            ("same_direction_views", mutate_same_direction, "insufficient camera direction diversity"),
            ("duplicate_camera_tuple", mutate_duplicate_tuple, "duplicate camera tuple"),
            ("exact_duplicate_bytes", mutate_exact_duplicate, "exact duplicate image bytes"),
            ("near_duplicate_reencode", mutate_near_duplicate, "near-duplicate or crop/focal-only coverage"),
            ("loop_closure_missing", mutate_missing_loop, "requires at least 1 items"),
            ("awaiting_continuation_delivery", mutate_awaiting_continuation, "generation queue must complete"),
            ("self_attested_without_runtime", mutate_self_attested_runtime, "missing-self-attested.json"),
            ("published_prompt_mutated", mutate_prompt_body, "prompt body hash mismatch"),
            ("missing_primary_source_anchor", mutate_missing_source_anchor, "primary scene source must be reference 1"),
            ("placeholder_qa_report", mutate_placeholder_qa, "report is placeholder"),
            ("non_executable_path", mutate_non_executable_path, "does not execute"),
            ("duplicate_4k_prompt_ids", mutate_duplicate_4k_prompt_ids, "4K prompt IDs must be unique"),
            ("schema_additional_properties", mutate_schema_additional_properties, "expected type"),
            ("non_finite_number", mutate_nan_number, "non-finite JSON number"),
            ("empty_core_markdown", mutate_empty_core_markdown, "core deliverable is placeholder or empty"),
            ("hrb_reuses_machine", mutate_hrb_reuses_machine, "cannot reuse a machine asset"),
            ("primary_reference_ghost", mutate_primary_reference_ghost, "source reference IDs must be unique and include"),
            ("duplicate_source_id", mutate_duplicate_source_id, "source reference IDs must be unique and include"),
            ("source_locator_escape", mutate_source_locator_escape, "path escapes package root"),
            ("loop_edges_unrelated", mutate_loop_edges_unrelated, "loop edge"),
            ("ghost_edge_path", mutate_ghost_edge_path, "edge/path membership must be exact"),
            ("negative_publication_time", mutate_negative_publication_time, "all six prompts must be public"),
            ("foreign_publication_parent", mutate_foreign_publication_parent, "do not share the finalizing parent"),
            ("tiny_4k_target", mutate_4k_target_tiny, "below minimum"),
            ("missing_4k_reference", mutate_4k_missing_reference, "required references must contain only"),
            ("stale_structured_qa", mutate_stale_structured_qa, "bindings are stale or incomplete"),
            ("closure_landmark_ghost", mutate_closure_landmark_ghost, "closure landmarks must exist"),
            ("envelope_reveal_ghost", mutate_envelope_reveal_ghost, "motion envelope reveal region lies outside"),
            ("edge_reveal_ghost", mutate_edge_reveal_ghost, "reveal order lies outside"),
            ("node_evidence_ghost", mutate_node_evidence_ghost, "source evidence reference is unresolved"),
            ("node_completion_ghost", mutate_node_completion_ghost, "canonical completion reference is unresolved"),
            ("dangling_adjacency", mutate_dangling_adjacency, "adjacency list must exactly match"),
            ("wrong_worker_asset", mutate_wrong_worker_asset, "worker namespace does not bind"),
            ("attempt_mismatch", mutate_attempt_mismatch, "does not bind asset and accepted attempt"),
            ("inspection_owner", mutate_inspection_owner, "inspection owner is not"),
            ("same_pixels_reencoded", mutate_reencoded_same_pixels, "near-duplicate or crop/focal-only coverage"),
            ("unlisted_frozen_reference", mutate_unlisted_frozen_reference, "missing or unlisted files"),
        ]
        for name, mutator, expected in cases:
            root = Path(temporary) / name
            create_fixture(root)
            mutator(root)
            case_errors = validate_package(root, mode="delivery", fixture_mode=True)
            if not case_errors or not any(expected.lower() in error.lower() for error in case_errors):
                print(f"FAIL {name}: expected {expected!r}")
                for error in case_errors: print(f"  - {error}")
                return 1
            print(f"PASS expected failure: {name}")

    print("scene canon contract fixtures: strict valid/stage boundaries + 44 expected failures passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
