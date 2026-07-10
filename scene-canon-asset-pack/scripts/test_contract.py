#!/usr/bin/env python3
"""Run positive and adversarial fixtures against the scene package validator."""

from __future__ import annotations

import binascii
import copy
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path
from typing import Any, Callable

from validate_scene_package import canonical_json_hash, image_dimensions, sha256_file, validate_package


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)


def write_png(path: Path, width: int = 32, height: int = 18, rgb: tuple[int, int, int] = (110, 120, 130)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    scanline = b"\x00" + bytes(rgb) * width
    payload = b"".join(scanline for _ in range(height))
    data = b"\x89PNG\r\n\x1a\n"
    data += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += png_chunk(b"IDAT", zlib.compress(payload))
    data += png_chunk(b"IEND", b"")
    path.write_bytes(data)


def scene_canon() -> dict[str, Any]:
    completion = {
        "element_id": "COMP_001",
        "description": "Simple rear wall continuation constrained by visible side walls",
        "rationale": "Required for reverse coverage inside the minimum-complete boundary",
        "constraints": ["preserve room width", "introduce no new door or landmark"],
        "status": "approved",
    }
    return {
        "schema_version": "scene-canon.v1",
        "scene_id": "TEST_SCENE",
        "project_name": "Contract Fixture",
        "scene_name": "Neutral Test Room",
        "scene_type": "bounded_rigid_space",
        "secondary_scene_types": [],
        "source_reference_list": [{"reference_id": "SRC_001", "source_locator": "fixture/source.png", "role": "primary_scene_evidence", "dimensions": {"width": 32, "height": 18}}],
        "primary_reference": "SRC_001",
        "source_locked_elements": [{"element_id": "E_001", "description": "rear wall and left doorway", "source_reference_ids": ["SRC_001"], "confidence": "high"}],
        "source_corroborated_elements": [],
        "canonical_completion_elements": [completion],
        "conflicts": [],
        "out_of_scope_unknowns": ["unused room beyond excluded corridor"],
        "minimum_complete_scene_boundary": {"included_regions": ["main room", "doorway connection"], "excluded_regions": ["unused room"], "coverage_rationale": "Enough for main, reverse, and high/low continuity"},
        "fixed_architecture": ["rear wall", "left doorway"],
        "fixed_natural_structures": [],
        "fixed_set_dressing": ["fixed wall shelf"],
        "conditional_scene_elements": ["fixed cyan emissive strip powered on"],
        "temporary_or_unwanted_objects": ["cup"],
        "prohibited_elements": ["people", "products", "new furniture"],
        "fixed_content_exclusion_map": {
            "fixed_architecture_or_natural": ["rear wall", "left doorway"],
            "fixed_set_dressing": ["fixed wall shelf"],
            "conditional_scene_elements": ["fixed cyan emissive strip"],
            "temporary_objects": ["cup"],
            "prohibited_additions": ["new furniture", "people", "products"],
            "prohibited_look_components": ["teal-orange grade", "bloom", "crushed shadows"],
        },
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
        "neutral_appearance_rules": ["neutral white balance", "preserve fixed cyan emissive strip", "retain readable contact shadows"],
        "scale_relationships": ["door height anchors room scale"],
        "topology_relationships": ["left doorway connects to excluded corridor"],
        "entrances_and_exits": ["left doorway"],
        "orientation_system": "primary camera faces north wall; doorway west",
        "horizon_or_vertical_reference": "vertical wall edges",
        "intrinsic_scene_state": [{"state_id": "STATE_001", "description": "fixed cyan emissive strip powered on", "identity_defining": True, "preservation_rule": "preserve physical strip and emission; remove added bloom"}],
        "camera_coverage_plan": [
            {"asset_id": "CDM_001", "view_role": "diagnostic main", "camera_height": "eye", "direction": "north", "information_gain": "identity and neutral appearance"},
            {"asset_id": "SRM_001", "view_role": "elevated spatial", "camera_height": "elevated", "direction": "northwest", "information_gain": "topology and connection"},
        ],
        "inferred_regions": [completion],
        "confidence_level": "high",
        "unresolved_hard_blockers": [],
        "canon_revision": "canon-v1",
        "canon_freeze_status": "frozen",
        "source_asset_dimensions": {"SRC_001": {"width": 32, "height": 18}},
        "target_4k_dimensions": {"width": 3840, "height": 2160},
        "generated_asset_index": ["CDM_001", "SRM_001", "HRB_001"],
        "four_k_prompt_index": ["4K_CDM_001", "4K_SRM_001"],
        "QA_status": "approved",
    }


def appearance() -> dict[str, Any]:
    return {
        "schema_version": "scene-appearance-decomposition.v1",
        "scene_id": "TEST_SCENE",
        "source_reference_ids": ["SRC_001"],
        "heavy_look_detected": True,
        "source_color_cast": ["teal-orange"],
        "source_exposure_state": ["underexposed shadows"],
        "source_contrast_state": ["high contrast"],
        "source_key_light_direction": ["camera right"],
        "shadow_compression": "strong",
        "highlight_clipping": "mild",
        "bloom_flare": ["cyan strip bloom"],
        "depth_of_field": "shallow source, deep diagnostic target",
        "grading_characteristics": ["teal-orange", "crushed blacks"],
        "atmosphere_or_medium_state": ["clear interior air"],
        "intrinsic_scene_appearance": [{"surface_or_feature": "WALL_01", "property": "warm off-white plaster", "source_status": "source_locked", "confidence": "high"}],
        "intrinsic_scene_state": [{"state": "fixed cyan strip powered on", "identity_defining": True, "preserve": True, "reason": "fixed emissive architecture"}],
        "external_illumination": [{"effect": "temporary warm side light", "remove_from_neutral_assets": True, "evidence": "color discontinuity on all materials"}],
        "camera_optical_effects": [{"effect": "shallow depth of field", "remove_from_neutral_assets": True, "evidence": "focus falloff"}],
        "postprocess_effects": [{"effect": "teal-orange grade and bloom", "remove_from_neutral_assets": True, "evidence": "highlight halos and split toning"}],
        "unresolved_appearance": [],
        "material_color_inferences": [{"surface_id": "WALL_01", "observed_rendered_color": "orange", "intrinsic_base_color": "warm off-white", "confidence": "high", "status": "confirmed"}],
        "intrinsic_emissive_structures": [{"feature": "fixed cyan emissive strip", "intrinsic": True, "preservation_rule": "preserve strip and emission; remove post bloom"}],
        "neutral_appearance_canon": {
            "white_balance": "neutral",
            "illumination": "broad soft diagnostic illumination",
            "contrast": "low to medium",
            "shadow_rule": "readable contact shadows",
            "highlight_rule": "no clipping",
            "depth_of_field_rule": "sufficient depth for structure",
            "material_rule": "preserve intrinsic colors and texture",
            "state_rule": "preserve fixed emissive strip without added bloom",
            "forbidden_look_components": ["teal-orange grade", "bloom", "flare", "crushed shadows"],
        },
        "neutralization_strategy": ["remove temporary warm light", "restore neutral wall base color", "preserve cyan emissive structure", "retain readable shadows"],
        "appearance_revision": "appearance-v1",
        "appearance_freeze_status": "frozen",
    }


def long_prompt(asset_name: str) -> str:
    return (
        "Use the provided QA-approved Codex scene asset as the primary and highest-priority visual reference. "
        f"Preserve the exact {asset_name} scene identity, geometry, camera position, camera height, framing, crop, perspective, horizon, topology, landmark placement, scale, fixed content, material identity, intrinsic base colors, canonical completion, intrinsic scene state, and neutral diagnostic appearance. "
        "Only increase effective resolution, edge definition, material micro-detail, distant structural clarity, and texture precision. "
        "Do not redesign, relight, restyle, recolor, expand, remove, move, beautify, or cinematize the scene. "
        "Do not restore the heavy color grade, dramatic lighting, crushed shadows, clipped highlights, bloom, flare, vignette, shallow depth of field, film grain, or other look characteristics from the original source reference."
    )


def create_fixture(root: Path) -> None:
    for rel in [
        "00_manifest/SCENE_CANON.md",
        "00_manifest/SOURCE_APPEARANCE_DECOMPOSITION.md",
        "00_manifest/ASSET_INDEX.md",
        "01_source_analysis/source_evidence_report.md",
        "01_source_analysis/conflict_report.md",
        "01_source_analysis/coverage_assessment.md",
        "09_qa/QA_REPORT.md",
        "09_qa/failed_asset_log.md",
        "09_qa/look_contamination_report.md",
        "09_qa/4k_prompt_mapping_report.md",
    ]:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {path.stem}\n\nFixture evidence.\n", encoding="utf-8")

    canon = scene_canon()
    appearance_record = appearance()
    write_json(root / "00_manifest/SCENE_CANON.json", canon)
    write_json(root / "00_manifest/SOURCE_APPEARANCE_DECOMPOSITION.json", appearance_record)
    canon_hash = sha256_file(root / "00_manifest/SCENE_CANON.json")
    appearance_hash = sha256_file(root / "00_manifest/SOURCE_APPEARANCE_DECOMPOSITION.json")
    completion_hash = canonical_json_hash(canon["canonical_completion_elements"])

    image_specs = [
        ("CDM_001", "Canonical Diagnostic Master", "canonical_diagnostic_master", "02_diagnostic_master/canonical_diagnostic_master.png", (110, 120, 130)),
        ("SRM_001", "Spatial Relational Master", "spatial_relational_master", "03_spatial_relational_master/spatial_or_relational_master.png", (100, 115, 125)),
        ("HRB_001", "Human Review Overview Board", "human_review_overview_board", "07_review_board/scene_asset_overview_board.png", (30, 30, 30)),
    ]
    for _, _, _, rel, rgb in image_specs:
        write_png(root / rel, rgb=rgb)

    assets: list[dict[str, Any]] = []
    for index, (asset_id, name, asset_type, rel, _) in enumerate(image_specs):
        is_review = asset_type == "human_review_overview_board"
        assets.append({
            "asset_id": asset_id,
            "asset_name": name,
            "asset_type": asset_type,
            "asset_revision": 1,
            "file_path": rel,
            "file_sha256": sha256_file(root / rel),
            "is_machine_asset": not is_review,
            "independently_generated": not is_review,
            "derived_from_multipanel": False,
            "generation_mode": "approved_asset_composite" if is_review else "independent_full_frame",
            "terminal_generation_call": "not_applicable_composite" if is_review else "executed",
            "generation_turn": None if is_review else 10 + index * 2,
            "inspection_turn": None if is_review else 11 + index * 2,
            "generation_status": "generated",
            "assistant_qa_status": "approved",
            "production_approval_status": "not_granted",
            "actual_pixel_dimensions": {"width": 32, "height": 18},
            "actual_dimensions_verified": True,
            "target_pixel_dimensions": {"width": 3840, "height": 2160},
            "native_4k_claim": False,
            "native_4k_evidence": None,
            "source_reference_ids": ["SRC_001"],
            "canon_sha256": canon_hash,
            "appearance_sha256": appearance_hash,
            "completion_hash": completion_hash,
            "scene_canon_version": "canon-v1",
            "neutral_appearance_version": "appearance-v1",
            "contamination_flags": {"text_or_layout": False, "person": False, "product": False, "temporary_object": False, "look_contamination": False},
            "four_k_prompt_id": None if is_review else f"4K_{asset_id}",
        })

    prompts: list[dict[str, Any]] = []
    for asset in assets[:2]:
        prompts.append({
            "prompt_id": f"4K_{asset['asset_id']}",
            "asset_id": asset["asset_id"],
            "asset_name": asset["asset_name"],
            "source_image": asset["file_path"],
            "source_dimensions": asset["actual_pixel_dimensions"],
            "target_dimensions": {"width": 3840, "height": 2160},
            "asset_type": asset["asset_type"],
            "required_reference_images": [asset["file_path"], "02_diagnostic_master/canonical_diagnostic_master.png"],
            "reference_priority": ["matching QA-approved neutral Codex asset", "Canonical Diagnostic Master", "optional original structure reference"],
            "primary_reference_asset_id": asset["asset_id"],
            "preservation_checklist": ["camera position", "camera height", "framing", "crop", "perspective", "horizon", "topology", "landmarks", "scale", "materials", "intrinsic base colors", "canonical completion", "intrinsic scene state"],
            "allowed_enhancements": ["effective resolution", "edge definition", "material micro-detail", "distant structural clarity", "texture precision"],
            "forbidden_structural_changes": ["camera change", "framing change", "perspective change", "topology change", "landmark movement", "scale change", "material change"],
            "forbidden_look_changes": ["heavy grade restoration", "dramatic relighting", "crushed shadows", "clipped highlights", "bloom", "flare", "vignette"],
            "regeneration_prompt_en": long_prompt(asset["asset_name"]),
            "negative_constraints": ["no redesign", "no relight", "no recolor", "no reframe", "no new objects", "no look restoration"],
            "post_generation_qa_checklist": ["identity", "camera", "topology", "landmarks", "materials", "neutral look", "pixels verified"],
            "source_asset_revision": 1,
            "source_asset_sha256": asset["file_sha256"],
            "source_canon_sha256": canon_hash,
            "source_appearance_sha256": appearance_hash,
            "source_completion_hash": completion_hash,
            "status": "finalized_post_qa",
        })

    manifest = {
        "schema_version": "scene-canon-asset-manifest.v1",
        "package_id": "TEST_SCENE_ASSET_PACK_V1",
        "scene_id": "TEST_SCENE",
        "canon_revision": "canon-v1",
        "canon_sha256": canon_hash,
        "appearance_revision": "appearance-v1",
        "appearance_sha256": appearance_hash,
        "completion_hash": completion_hash,
        "package_status": "packaged",
        "task_finalization_status": "complete",
        "assistant_qa_status": "passed",
        "production_approval_status": "not_granted",
        "scene_canon_path": "00_manifest/SCENE_CANON.json",
        "appearance_decomposition_path": "00_manifest/SOURCE_APPEARANCE_DECOMPOSITION.json",
        "assets": assets,
        "four_k_prompt_records": prompts,
        "approved_machine_asset_count": 2,
        "four_k_prompt_mapping_count": 2,
        "human_review_overview_board": "07_review_board/scene_asset_overview_board.png",
        "repair_log": [],
        "qa_report_path": "09_qa/QA_REPORT.md",
        "look_contamination_report_path": "09_qa/look_contamination_report.md",
        "four_k_prompt_mapping_report_path": "09_qa/4k_prompt_mapping_report.md",
    }
    write_json(root / "00_manifest/ASSET_MANIFEST.json", manifest)
    write_json(root / "00_manifest/actual_image_dimensions.json", {
        asset["asset_id"]: {"file_path": asset["file_path"], "width": 32, "height": 18, "verified": True}
        for asset in assets[:2]
    })
    prompt_doc = "# 4K Asset Regeneration Prompts\n\n" + "\n\n".join(
        f"## {record['prompt_id']}\n\n{record['regeneration_prompt_en']}" for record in prompts
    ) + "\n"
    prompt_path = root / "08_4k_regeneration/4K_ASSET_REGENERATION_PROMPTS.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt_doc, encoding="utf-8")


def load_manifest(root: Path) -> dict[str, Any]:
    return json.loads((root / "00_manifest/ASSET_MANIFEST.json").read_text(encoding="utf-8"))


def save_manifest(root: Path, manifest: dict[str, Any]) -> None:
    write_json(root / "00_manifest/ASSET_MANIFEST.json", manifest)


def mutate_grid_crop(root: Path) -> None:
    manifest = load_manifest(root)
    manifest["assets"][0]["generation_mode"] = "approved_asset_composite"
    manifest["assets"][0]["derived_from_multipanel"] = True
    save_manifest(root, manifest)


def mutate_false_4k(root: Path) -> None:
    manifest = load_manifest(root)
    manifest["assets"][0]["native_4k_claim"] = True
    manifest["assets"][0]["native_4k_evidence"] = None
    save_manifest(root, manifest)


def mutate_missing_prompt(root: Path) -> None:
    manifest = load_manifest(root)
    manifest["four_k_prompt_records"].pop()
    manifest["four_k_prompt_mapping_count"] = 1
    save_manifest(root, manifest)


def mutate_wrong_primary(root: Path) -> None:
    manifest = load_manifest(root)
    manifest["four_k_prompt_records"][0]["primary_reference_asset_id"] = "ORIGINAL_SOURCE"
    save_manifest(root, manifest)


def mutate_stale_prompt(root: Path) -> None:
    manifest = load_manifest(root)
    manifest["four_k_prompt_records"][0]["source_asset_revision"] = 2
    save_manifest(root, manifest)


def mutate_terminal_overclaim(root: Path) -> None:
    manifest = load_manifest(root)
    manifest["assets"][0]["inspection_turn"] = manifest["assets"][0]["generation_turn"]
    save_manifest(root, manifest)


def mutate_look_contamination(root: Path) -> None:
    manifest = load_manifest(root)
    manifest["assets"][0]["contamination_flags"]["look_contamination"] = True
    save_manifest(root, manifest)


def mutate_unresolved_boundary(root: Path) -> None:
    canon_path = root / "00_manifest/SCENE_CANON.json"
    canon = json.loads(canon_path.read_text(encoding="utf-8"))
    canon["unresolved_hard_blockers"] = ["unresolved rear wall inside included boundary"]
    write_json(canon_path, canon)
    canon_hash = sha256_file(canon_path)
    manifest = load_manifest(root)
    manifest["canon_sha256"] = canon_hash
    for asset in manifest["assets"]:
        asset["canon_sha256"] = canon_hash
    for prompt in manifest["four_k_prompt_records"]:
        prompt["source_canon_sha256"] = canon_hash
    save_manifest(root, manifest)


def run() -> int:
    with tempfile.TemporaryDirectory(prefix="scene-canon-contract-") as temp:
        base = Path(temp) / "valid"
        create_fixture(base)
        valid_errors = validate_package(base)
        if valid_errors:
            print("FAIL valid fixture")
            for error in valid_errors:
                print(f"  - {error}")
            return 1
        print("PASS valid packaged fixture")

        review_output = base / "07_review_board/rebuilt_overview_board.png"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("build_review_board.py")),
                str(base / "00_manifest/ASSET_MANIFEST.json"),
                str(review_output),
                "--columns",
                "2",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0 or not review_output.is_file():
            print("FAIL review-board composition smoke")
            print(result.stdout + result.stderr)
            return 1
        width, height = image_dimensions(review_output)
        if width <= 0 or height <= 0:
            print("FAIL review-board dimensions")
            return 1
        print("PASS review-board composition smoke")

        cases: list[tuple[str, Callable[[Path], None], str]] = [
            ("grid_crop_asset", mutate_grid_crop, "grid/contact-sheet crops are forbidden"),
            ("false_native_4k", mutate_false_4k, "native 4K claim"),
            ("prompt_many_to_one", mutate_missing_prompt, "one-to-one"),
            ("heavy_source_primary", mutate_wrong_primary, "primary reference"),
            ("stale_prompt_revision", mutate_stale_prompt, "stale asset revision"),
            ("terminal_false_complete", mutate_terminal_overclaim, "later-turn visual QA"),
            ("look_contamination", mutate_look_contamination, "contamination flags"),
            ("unresolved_inside_boundary", mutate_unresolved_boundary, "unresolved hard blockers"),
        ]
        for name, mutator, expected in cases:
            root = Path(temp) / name
            shutil.copytree(base, root)
            mutator(root)
            errors = validate_package(root)
            if not errors:
                print(f"FAIL {name}: invalid fixture unexpectedly passed")
                return 1
            if not any(expected.lower() in error.lower() for error in errors):
                print(f"FAIL {name}: expected signal {expected!r} not found")
                for error in errors:
                    print(f"  - {error}")
                return 1
            print(f"PASS expected failure: {name}")

    print("scene canon contract fixtures: 1 valid + 8 expected failures passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
