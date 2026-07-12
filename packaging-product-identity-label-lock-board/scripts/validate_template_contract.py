#!/usr/bin/env python3
"""Fail closed when the shipped packaging starter files contradict each other."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REFERENCES = SKILL_DIR / "references"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_continuity_measurements as continuity  # noqa: E402
from validate_packaging_run import (  # noqa: E402
    CANONICAL_FEATURES, REVIEW_BOARD_ROLES, derive_required_continuity_gates,
    dynamic_region_detail_view_id,
)


class TemplateContractError(RuntimeError):
    pass


def load(name: str) -> dict[str, Any]:
    path = REFERENCES / name
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TemplateContractError(f"{name}: root must be an object")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TemplateContractError(message)


def unique_ids(values: Any, key: str, label: str) -> set[str]:
    require(isinstance(values, list), f"{label}: must be an array")
    identifiers = [item.get(key) for item in values if isinstance(item, dict)]
    require(len(identifiers) == len(values), f"{label}: every row must be an object with {key}")
    require(all(isinstance(item, str) and item for item in identifiers), f"{label}: IDs must be non-empty strings")
    require(len(identifiers) == len(set(identifiers)), f"{label}: duplicate IDs")
    return set(identifiers)


def validate_canonical_feature_enum(values: Any) -> set[str]:
    """Validate the schema taxonomy without allowing set coercion to hide defects."""
    require(isinstance(values, list), "asset-pack schema feature enum must be an array")
    require(
        all(isinstance(item, str) and item for item in values),
        "asset-pack schema feature enum must contain only non-empty strings",
    )
    require(
        len(values) == len(set(values)),
        "asset-pack schema feature enum must not contain duplicates",
    )
    identifiers = set(values)
    require(
        identifiers == CANONICAL_FEATURES,
        "asset-pack schema feature enum must exactly equal the canonical feature taxonomy",
    )
    return identifiers


def layer_group(layer: dict[str, Any]) -> tuple[Any, ...]:
    geometry = (
        tuple(layer.get("destination_quad_px") or [])
        if layer.get("projection_model") == "planar_homography"
        else tuple(layer.get("destination_box_px") or [])
    )
    return (
        geometry,
        tuple(sorted(layer.get("region_ids") or [])),
        tuple(sorted(layer.get("field_ids") or [])),
        tuple(sorted(layer.get("code_ids") or [])),
        tuple(sorted(layer.get("graphic_ids") or [])),
        (str(layer.get("layer_id")),),
    )


def scan_group(scan: dict[str, Any]) -> tuple[Any, ...]:
    return (
        tuple(scan.get("crop_box_px_on_final_master") or []),
        tuple(sorted(scan.get("region_ids") or [])),
        tuple(sorted(scan.get("field_ids") or [])),
        tuple(sorted(scan.get("code_ids") or [])),
        tuple(sorted(scan.get("graphic_ids") or [])),
        tuple(sorted(scan.get("layer_ids") or [])),
    )


def validate() -> dict[str, Any]:
    parsed = []
    for path in sorted(REFERENCES.glob("*.template.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        require(isinstance(value, dict), f"{path.name}: root must be an object")
        parsed.append(path.name)

    run = load("packaging_asset_pack.template.json")
    source = load("source_manifest.template.json")
    surface = load("surface_inventory.template.json")
    coverage = load("coverage_matrix.template.json")
    atlas = load("surface_texture_atlas.template.json")
    plan = load("deterministic_composition_plan.template.json")
    job = load("exact_copy_composition_job.template.json")
    text_ssot = load("exact_copy_text_ssot.template.json")
    code_manifest = load("code_manifest.template.json")
    graphic_manifest = load("logo_graphic_manifest.template.json")
    ocr = load("source_ocr_ledger.template.json")
    region_spec = load("region_ocr_spec.template.json")
    crop_receipt = load("region_crop_receipt.template.json")
    continuity_contract = load("continuity_contract.template.json")
    annotation = load("continuity_annotation.template.json")
    semantic = load("continuity_semantic_evidence.template.json")
    measurements = load("continuity_measurements.template.json")
    post_ocr = load("post_ocr_evidence.template.json")
    graphic_receipt = load("graphic_comparison_receipt.template.json")
    motion = load("motion_envelope.template.json")
    asset_qa = load("asset_qa.template.json")
    asset_pack_schema = json.loads(
        (REFERENCES / "packaging_asset_pack.schema.json").read_text(encoding="utf-8")
    )
    profiles = json.loads((REFERENCES / "view_coverage_profiles.json").read_text(encoding="utf-8"))
    require(
        profiles.get("schema_version") == "packaging-view-coverage-profiles.v2",
        "view coverage profile schema must be v2",
    )

    sources = unique_ids(source.get("sources"), "source_id", "source manifest sources")
    classification = source.get("product_feature_classification")
    feature_ids = unique_ids(classification, "feature_id", "feature classification")
    require(feature_ids == CANONICAL_FEATURES, "source starter must audit the complete canonical feature taxonomy")
    schema_feature_ids = validate_canonical_feature_enum(
        asset_pack_schema.get("properties", {})
        .get("product_features", {})
        .get("items", {})
        .get("enum", [])
    )
    require(schema_feature_ids == feature_ids, "schema/source feature taxonomies disagree")
    present: set[str] = set()
    for row in classification:
        require(row.get("status") in {"present", "reviewed_absent"}, "feature starter has invalid status")
        require(row.get("review_status") == "reviewed" and row.get("reviewer_id") and row.get("evidence_note"), "feature starter requires named review and evidence note")
        require(set(row.get("evidence_source_ids") or []).issubset(sources) and row.get("evidence_source_ids"), "feature starter evidence sources are not closed")
        if row["status"] == "present":
            present.add(row["feature_id"])
    require(set(run.get("product_features") or []) == present, "run starter product_features differ from source present-feature audit")

    identity = coverage.get("identity_lock") or {}
    geometry = identity.get("geometry_landmark_contract") or {}
    landmark_ids = set(geometry.get("required_landmark_ids") or [])
    component_ids = set(geometry.get("component_ids") or [])
    require(landmark_ids and component_ids, "coverage starter needs non-empty landmark and component inventories")
    for row in source["sources"]:
        require(set(row.get("visible_component_ids") or []).issubset(component_ids), f"source {row['source_id']} component IDs escape the frozen inventory")

    close_views = profiles.get("base_close_views") or []
    require(
        {item.get("view_id") for item in close_views}
        == {f"{prefix}_{angle}" for prefix in ("UPPER", "LOWER") for angle in ("0000", "0900", "1800", "2700")},
        "coverage profile must freeze four-way upper/lower close bridges",
    )
    require(
        all(
            item.get("family") in {"upper_half_close", "lower_half_close"}
            and item.get("shot_scale") in {"upper_half_close", "lower_half_close"}
            and item.get("target_surface_role") in {"front", "right", "back", "left"}
            and item.get("review_board_role") == "framing_bridge"
            and item.get("framing_contract")
            for item in close_views
        ),
        "upper/lower close profile semantics are incomplete",
    )
    required_fixed_details = set(profiles.get("base_detail_views") or []) | {
        view_id for values in (profiles.get("feature_detail_requirements") or {}).values()
        for view_id in values
    }
    fixed_specs = profiles.get("fixed_detail_specs") or {}
    require(set(fixed_specs) == required_fixed_details, "every fixed DETAIL ID needs exactly one semantic spec")
    for view_id, spec in fixed_specs.items():
        require(
            spec.get("family") in {"detail_copy", "detail_code", "detail_structure", "detail_material"}
            and spec.get("shot_scale") in {"macro_component", "rectified_surface_evidence"}
            and spec.get("target_surface_role") in {"front", "right", "back", "left", "top", "bottom"}
            and spec.get("review_board_role") in {"copy", "code", "structure", "material"}
            and isinstance(spec.get("azimuth_deg"), (int, float))
            and isinstance(spec.get("elevation_deg"), (int, float))
            and spec.get("framing_contract") and spec.get("focus_contract"),
            f"{view_id}: frozen detail semantics are incomplete",
        )
    dynamic_contract = profiles.get("dynamic_region_detail_contract") or {}
    for key in (
        "view_id_algorithm", "reference_canvas_px", "min_region_width_px_at_reference",
        "min_region_height_px_at_reference", "min_text_line_height_px_at_reference",
        "min_code_short_edge_px_at_reference", "min_graphic_short_edge_px_at_reference",
    ):
        require(dynamic_contract.get(key) not in (None, "", {}), f"dynamic region detail contract missing {key}")
    require(
        dynamic_region_detail_view_id("../unsafe region")
        .startswith("DETAIL_REGION_UNSAFE_REGION_"),
        "dynamic region detail ID is not safely normalized",
    )

    required_surfaces = set(surface.get("required_surface_ids") or [])
    surface_ids = unique_ids(surface.get("surfaces"), "surface_id", "surface inventory")
    require(required_surfaces == surface_ids, "surface starter required IDs differ from rows")
    require(required_surfaces == {"SURFACE_FRONT", "SURFACE_BACK", "SURFACE_LEFT", "SURFACE_RIGHT", "SURFACE_TOP", "SURFACE_BOTTOM"}, "surface starter must use exactly six coordinate surfaces")
    allowed_text_states = {"text_detected", "verified_no_copy", "decorative_graphic", "occluded", "needs_source"}
    for row in surface["surfaces"]:
        require(row.get("text_detection_status") in allowed_text_states, f"surface {row['surface_id']} uses a non-canonical text state")
    texture_ids = unique_ids(atlas.get("textures"), "surface_id", "surface texture atlas")
    require(texture_ids == required_surfaces, "texture-atlas starter must cover every coordinate surface exactly once")
    for row in atlas["textures"]:
        require(set(row.get("registration_landmark_ids") or []).issubset(landmark_ids), f"atlas {row['surface_id']} uses landmarks outside the frozen inventory")

    require(plan.get("plan_id") == job.get("composition_plan_id"), "composition plan/job IDs disagree")
    plan_views = {item.get("view_id"): item for item in plan.get("view_statuses") or [] if isinstance(item, dict)}
    plan_view = plan_views.get(job.get("view_id"))
    require(isinstance(plan_view, dict), "composition job view is absent from the plan")
    layers = job.get("layers") or []
    require(layers, "composition job starter needs layers")
    require(set(plan_view.get("source_layer_ids") or []) == {item.get("source_layer_id") for item in layers}, "composition plan/job source-layer IDs disagree")
    require(all(item.get("projection_model") == plan_view.get("projection_model") for item in layers), "composition plan/job projection models disagree")
    bindings = {
        "protected_region_ids": {item for layer in layers for item in (layer.get("region_ids") or [])},
        "ocr_field_ids_visible": {item for layer in layers for item in (layer.get("field_ids") or [])},
        "code_ids_visible": {item for layer in layers for item in (layer.get("code_ids") or [])},
        "graphic_ids_visible": {item for layer in layers for item in (layer.get("graphic_ids") or [])},
    }
    for key, observed in bindings.items():
        require(set(plan_view.get(key) or []) == observed, f"composition plan/job {key} disagree")

    for field in text_ssot.get("fields") or []:
        authority_sources = field.get("authority_source_ids") or []
        require(len(authority_sources) == 1, f"Text starter {field.get('field_id')} must have one unambiguous crop source")
        expected = f"01_ocr/rectified_regions/{authority_sources[0]}/{field.get('region_id')}.png"
        require(field.get("authority_asset_path") == expected, f"Text starter {field.get('field_id')} path differs from bundled region-crop output")
        require(dynamic_region_detail_view_id(field["region_id"]) in (field.get("required_view_ids") or []), f"Text starter {field.get('field_id')} lacks its dynamic region detail")
    for code in code_manifest.get("codes") or []:
        authority_sources = code.get("authority_source_ids") or []
        require(len(authority_sources) == 1, f"code starter {code.get('code_id')} must have one unambiguous crop source")
        expected = f"01_ocr/rectified_regions/{authority_sources[0]}/{code.get('region_id')}.png"
        require(code.get("printed_symbol_asset_path") == expected, f"code starter {code.get('code_id')} path lacks replayed crop provenance")
        require(dynamic_region_detail_view_id(code["region_id"]) in (code.get("required_view_ids") or []), f"code starter {code.get('code_id')} lacks its dynamic region detail")
    for graphic in graphic_manifest.get("graphics") or []:
        authority_sources = graphic.get("authority_source_ids") or []
        require(len(authority_sources) == 1, f"graphic starter {graphic.get('graphic_id')} must have one unambiguous crop source")
        expected = f"01_ocr/rectified_regions/{authority_sources[0]}/{graphic.get('region_id')}.png"
        require(graphic.get("asset_path") == expected, f"graphic starter {graphic.get('graphic_id')} path lacks replayed crop provenance")
        require(dynamic_region_detail_view_id(graphic["region_id"]) in (graphic.get("required_view_ids") or []), f"graphic starter {graphic.get('graphic_id')} lacks its dynamic region detail")

    text_paths = {item.get("authority_asset_path") for item in text_ssot.get("fields") or []}
    graphic_paths = {item.get("asset_path") for item in graphic_manifest.get("graphics") or []}
    for layer in layers:
        if layer.get("field_ids"):
            require(layer.get("source_path") in text_paths, f"composition field layer {layer.get('layer_id')} is detached from Text authority bytes")
        if layer.get("graphic_ids"):
            require(layer.get("source_path") in graphic_paths, f"composition graphic layer {layer.get('layer_id')} is detached from graphic authority bytes")

    for key in ("preflight_adapter_path", "preflight_adapter_sha256", "engine_adapter_path", "engine_adapter_sha256", "ledger_semantic_sha256"):
        require(key in ocr, f"OCR ledger starter missing {key}")
    for row in ocr.get("source_records") or []:
        for pass_row in row.get("whole_product_ocr_passes") or []:
            for key in ("preflight_adapter_path", "preflight_adapter_sha256", "engine_adapter_path", "engine_adapter_sha256"):
                require(key in pass_row, f"whole-product OCR pass starter missing {key}")

    require(
        motion.get("motion_type") == "neutral_height_full_spin"
        and motion.get("motion_scope") == "neutral_height_full_360_rotation"
        and motion.get("product_state_id") == coverage.get("product_state_id")
        and isinstance(motion.get("required_edge_ids"), list)
        and motion.get("blocked_motion_segments") == [],
        "motion starter must use the canonical motion enum/scope/state/edge contract",
    )
    coverage_sample = (coverage.get("views") or [{}])[0]
    require(
        coverage_sample.get("review_board_role") == "neutral_rotation",
        "coverage starter sample lacks semantic review-board routing",
    )
    board_sample = (asset_qa.get("review_boards") or [{}])[0]
    require(
        board_sample.get("semantic_board_role") in REVIEW_BOARD_ROLES
        and board_sample.get("ordered_view_ids")
        == [item.get("view_id") for item in board_sample.get("inputs") or []],
        "asset-QA starter board lacks semantic role/order closure",
    )

    region = (region_spec.get("regions") or [{}])[0]
    for key in ("surface_id", "physical_layer_id", "visibility_mode", "region_purpose"):
        require(key in region, f"region spec starter missing {key}")
        require(crop_receipt.get(key) == region.get(key), f"region crop receipt does not preserve {key}")

    required_gates = derive_required_continuity_gates(present)
    require(set(continuity_contract.get("required_gates") or []) == required_gates, "continuity starter gates differ from the present-feature-derived gate set")
    require(required_gates == continuity.derive_required_continuity_gates(present), "builder/validator feature-gate derivation differs")
    for value, label in ((semantic, "semantic evidence"), (measurements, "measurement receipt")):
        locks = value.get("input_locks") or {}
        for key in ("source_manifest_path", "source_manifest_sha256", "asset_qa_path", "asset_qa_sha256", "coverage_matrix_path", "coverage_matrix_sha256", "continuity_contract_path", "continuity_contract_sha256"):
            require(key in locks, f"{label} starter missing input lock {key}")
    for key in ("semantic_evidence_path", "semantic_evidence_sha256"):
        require(key in (measurements.get("input_locks") or {}), f"measurement starter missing {key}")
    annotation_landmarks = {item.get("landmark_id") for item in annotation.get("landmarks") or []}
    require(annotation_landmarks.issubset(landmark_ids), "continuity annotation starter uses landmarks outside the frozen inventory")

    require(post_ocr.get("mapping_policy") == "exact_utf8_single_or_fixed_bbox_line_aggregation_one_to_one_v2", "post OCR starter is not v2 exact mapping")
    for key in ("aggregation_order_contract", "scans", "raw_scan_observations", "aggregate_observations"):
        require(key in post_ocr, f"post OCR starter missing {key}")
    expected_groups = {layer_group(layer) for layer in layers}
    actual_groups = {scan_group(scan) for scan in post_ocr.get("scans") or [] if scan.get("scope") == "projected_region_crop"}
    require(expected_groups == actual_groups, "post OCR starter projected scans differ from composition-layer bindings")

    graphic_layer = next((item for item in layers if "GRAPHIC_BRAND_LOGO" in (item.get("graphic_ids") or [])), None)
    require(isinstance(graphic_layer, dict), "composition starter lacks the sample graphic layer")
    require(graphic_receipt.get("layer_id") == graphic_layer.get("layer_id"), "graphic receipt starter layer ID differs from composition job")
    require((graphic_receipt.get("layer_source_lock") or {}).get("path") == graphic_layer.get("source_path"), "graphic receipt starter source path differs from composition job")
    require((graphic_receipt.get("projection_lock") or {}).get("projection_model") == graphic_layer.get("projection_model"), "graphic receipt starter projection differs from composition job")
    require((graphic_receipt.get("mask_lock") or {}).get("path") == graphic_layer.get("mask_path"), "graphic receipt starter mask differs from composition job")

    prompt_template = (REFERENCES / "generation_unit_prompt_template.md").read_text(encoding="utf-8")
    for token in (
        "occluded_surface_ids:", "geometry_landmark_ids:", "material_feature_ids:",
        "source_manifest_sha256:", "protected_region_masks_sha256:", "composition_plan_sha256:",
        "composition_view_status:", "composition_projection_model:",
        "view_family:", "review_board_role:", "dynamic_region_contract:",
    ):
        require(token in prompt_template, f"prompt template missing compiler-parity token {token}")

    contract_text = (REFERENCES / "packaging_asset_pack_contract.md").read_text(encoding="utf-8")
    for token in (
        "Flat/rectangular pump bottle: R16 minimum",
        "`wrap_label` requires R16",
        "`continuous_wrap_copy` requires R24",
    ):
        require(token in contract_text, f"contract/profile prose parity marker missing: {token}")
    require(
        "Flat/rectangular pump bottle: R12 minimum" not in contract_text,
        "contract incorrectly permits an R12 flat/pump branch",
    )

    return {
        "status": "PASS",
        "template_json_count": len(parsed),
        "canonical_feature_count": len(CANONICAL_FEATURES),
        "present_feature_count": len(present),
        "required_continuity_gate_count": len(required_gates),
        "coordinate_surface_count": len(required_surfaces),
        "composition_layer_count": len(layers),
    }


def main() -> int:
    try:
        result = validate()
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
