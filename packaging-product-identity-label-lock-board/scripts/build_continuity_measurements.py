#!/usr/bin/env python3
"""Recompute hash-bound packaging continuity metrics from image bytes and raw annotations."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from statistics import median
from typing import Any

import PIL
from PIL import Image, ImageDraw


TOOL_SCRIPT_PATH = "scripts/build_continuity_measurements.py"
SCHEMA_VERSION = "packaging-continuity-measurements.v2"
SEMANTIC_EVIDENCE_SCHEMA = "packaging-continuity-semantic-evidence.v2"
ANNOTATION_SCHEMA = "packaging-continuity-annotation.v2"
SAMPLE_LONG_EDGE = 512
PAIR_SAMPLE_SIZE = (256, 144)
REGION_SAMPLE_SIZE = (256, 144)
FOREGROUND_DISTANCE_THRESHOLD = 24
GRAPH_ENDPOINT_SNAP_TOLERANCE = 0.05
COMPARATORS = {"eq", "lte", "gte", "between", "manual"}
RAW_ANNOTATION_KEYS = {"landmarks", "polylines", "polygons", "mask_rle_or_polygon"}

UNIVERSAL_CONTINUITY_GATES = {
    "product_frame_gate", "topology_gate", "silhouette_gate",
    "label_surface_binding_gate", "material_gate", "camera_calibration_gate",
    "adjacent_edge_gate", "loop_closure_gate", "copy_render_gate",
    "board_derivation_gate",
}
FEATURE_CONDITIONED_CONTINUITY_GATES: dict[str, set[str]] = {
    "visible_fill_line_or_liquid_boundary": {"fill_volume_gate"},
    "pump_or_spray": {"nozzle_frame_binding_gate"},
    "visible_dip_tube": {"dip_tube_topology_gate"},
    "embossing_or_debossing": {"embossing_registration_gate"},
    "transparent_or_translucent": {"transparent_showthrough_gate"},
}


GATE_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "adjacent_edge_gate": {
        "algorithm_id": "presence_fraction", "comparator": "gte", "hard_tolerance": 1.0,
        "unit": "fraction", "view_policy": "all_ring", "structure_type": "landmarks",
        "structure_ids": ["ADJACENT_EDGE_ANCHOR_A", "ADJACENT_EDGE_ANCHOR_B"],
    },
    "board_derivation_gate": {
        "algorithm_id": "board_input_binding", "comparator": "lte", "hard_tolerance": 0.0,
        "unit": "error_fraction", "view_policy": "all_assets", "required_role": "human_review_qa_board",
    },
    "camera_calibration_gate": {
        "algorithm_id": "landmark_coordinate_spread", "comparator": "lte", "hard_tolerance": 0.02,
        "unit": "normalized", "view_policy": "all_ring", "landmark_ids": ["CAMERA_PRODUCT_CENTER"],
        "axis": "euclidean",
    },
    "copy_render_gate": {
        "algorithm_id": "post_copy_verification_lock", "comparator": "lte", "hard_tolerance": 0.0,
        "unit": "error_fraction", "view_policy": "all_assets",
    },
    "dip_tube_topology_gate": {
        "algorithm_id": "component_graph_signature_match", "comparator": "lte", "hard_tolerance": 0.0,
        "unit": "mismatch_fraction", "view_policy": "minimum_two",
        "node_landmark_ids": ["DIP_TUBE_START", "DIP_TUBE_MIDDLE", "DIP_TUBE_END"],
        "edges": [
            {"polyline_id": "DIP_TUBE_START_TO_MIDDLE", "from_landmark_id": "DIP_TUBE_START", "to_landmark_id": "DIP_TUBE_MIDDLE"},
            {"polyline_id": "DIP_TUBE_MIDDLE_TO_END", "from_landmark_id": "DIP_TUBE_MIDDLE", "to_landmark_id": "DIP_TUBE_END"},
        ],
    },
    "embossing_registration_gate": {
        "algorithm_id": "mask_iou_error", "comparator": "lte", "hard_tolerance": 0.05,
        "unit": "iou_error", "view_policy": "minimum_two", "mask_ids": ["EMBOSSING_REGION_MASK"],
    },
    "fill_volume_gate": {
        "algorithm_id": "horizontal_line_angle_error", "comparator": "lte", "hard_tolerance": 2.0,
        "unit": "degrees", "view_policy": "minimum_two", "polyline_ids": ["LIQUID_FILL_LINE"],
    },
    "label_surface_binding_gate": {
        "algorithm_id": "local_frame_polygon_centroid_spread", "comparator": "lte", "hard_tolerance": 0.03,
        "unit": "local_frame_normalized", "view_policy": "minimum_two",
        "polygon_ids": ["LABEL_SURFACE_REGION"],
        "frame_landmark_ids": ["LABEL_FRAME_ORIGIN", "LABEL_FRAME_X", "LABEL_FRAME_Y"],
    },
    "loop_closure_gate": {
        "algorithm_id": "loop_pose_conditioned_landmark_vector_error", "comparator": "lte", "hard_tolerance": 0.02,
        "unit": "normalized_vector_error", "view_policy": "all_ring",
        "landmark_ids": ["EDGE_CONTINUITY_ANCHOR_A", "EDGE_CONTINUITY_ANCHOR_B"],
        "calibration_id": "loop_closure_pose_baseline_v1",
    },
    "material_gate": {
        "algorithm_id": "pose_conditioned_region_stat_baseline_error", "comparator": "lte", "hard_tolerance": 0.05,
        "unit": "normalized_error", "view_policy": "all_ring", "region_structure_type": "polygons",
        "structure_ids": ["MATERIAL_REFERENCE_REGION"], "statistic": "luma_mean",
        "calibration_id": "material_source_pose_baseline_v1",
    },
    "nozzle_frame_binding_gate": {
        "algorithm_id": "local_frame_vector_spread", "comparator": "lte", "hard_tolerance": 0.02,
        "unit": "local_frame_normalized", "view_policy": "minimum_two",
        "landmark_pairs": [["NOZZLE_BASE", "NOZZLE_TIP"]],
        "frame_landmark_ids": ["NOZZLE_FRAME_ORIGIN", "NOZZLE_FRAME_X", "NOZZLE_FRAME_Y"],
    },
    "product_frame_gate": {
        "algorithm_id": "landmark_coordinate_spread", "comparator": "lte", "hard_tolerance": 0.02,
        "unit": "normalized", "view_policy": "all_ring", "landmark_ids": ["PRODUCT_ROTATION_CENTER"],
        "axis": "euclidean",
    },
    "silhouette_gate": {
        "algorithm_id": "pose_conditioned_polygon_baseline_error", "comparator": "lte", "hard_tolerance": 0.05,
        "unit": "relative_error", "view_policy": "all_ring", "polygon_ids": ["PRODUCT_SILHOUETTE"],
        "calibration_id": "silhouette_source_pose_baseline_v1",
    },
    "topology_gate": {
        "algorithm_id": "component_graph_signature_match", "comparator": "lte", "hard_tolerance": 0.0,
        "unit": "mismatch_fraction", "view_policy": "minimum_two",
        "node_landmark_ids": ["COMPONENT_BODY", "COMPONENT_CLOSURE"],
        "edges": [
            {"polyline_id": "BODY_TO_CLOSURE", "from_landmark_id": "COMPONENT_BODY", "to_landmark_id": "COMPONENT_CLOSURE"},
        ],
    },
    "transparent_showthrough_gate": {
        "algorithm_id": "pose_conditioned_region_stat_baseline_error", "comparator": "lte", "hard_tolerance": 0.05,
        "unit": "normalized_error", "view_policy": "all_ring", "region_structure_type": "polygons",
        "structure_ids": ["SHOWTHROUGH_REFERENCE_REGION"], "statistic": "luma_std",
        "calibration_id": "showthrough_source_pose_baseline_v1",
    },
}

ALL_CONTINUITY_GATES = set(GATE_REQUIREMENTS)
CANONICAL_PRODUCT_FEATURES = {
    "box_or_carton", "complex_reflection", "continuous_wrap_copy",
    "embossing_or_debossing", "flat_or_rectangular_body",
    "foil_or_reflective_print", "high_material_risk", "liquid_or_gel",
    "low_copy_risk", "macro_rotation", "non_symmetric_closure",
    "ordinary_label_heavy_packaging", "pouch_or_bag", "pump_or_spray",
    "simple_near_rotational_symmetry", "transparent_or_translucent", "tube",
    "wrap_label",
    "visible_dip_tube", "visible_fill_line_or_liquid_boundary",
}


def derive_required_continuity_gates(product_features: list[str] | set[str]) -> set[str]:
    """Return the sole legal gate set for an observed-present product feature set."""
    required = set(UNIVERSAL_CONTINUITY_GATES)
    for feature_id in set(product_features):
        required.update(FEATURE_CONDITIONED_CONTINUITY_GATES.get(feature_id, set()))
    return required


def observed_product_features(source_manifest: dict[str, Any]) -> list[str]:
    if source_manifest.get("schema_version") != "packaging-source-manifest.v1":
        raise ValueError("source manifest must be packaging-source-manifest.v1")
    classification = source_manifest.get("product_feature_classification")
    if not isinstance(classification, list):
        raise ValueError("source manifest product_feature_classification must be an array")
    observed: list[str] = []
    audited: set[str] = set()
    for index, item in enumerate(classification):
        if not isinstance(item, dict):
            raise ValueError(f"product_feature_classification[{index}] must be an object")
        feature_id = item.get("feature_id")
        if not isinstance(feature_id, str) or not feature_id or feature_id in audited:
            raise ValueError("source manifest feature IDs must be unique non-empty strings")
        audited.add(feature_id)
        if item.get("status") == "present":
            observed.append(feature_id)
        elif item.get("status") != "reviewed_absent":
            raise ValueError("source manifest feature status must be present or reviewed_absent")
        if item.get("review_status") != "reviewed" or not item.get("reviewer_id") or not item.get("evidence_note"):
            raise ValueError("source manifest feature audit requires named review and evidence note")
    if audited != CANONICAL_PRODUCT_FEATURES:
        raise ValueError("source manifest feature audit must cover the complete canonical taxonomy")
    return sorted(observed)

EDGE_REQUIREMENT = {
    "algorithm_id": "edge_pose_conditioned_landmark_vector_error", "comparator": "lte",
    "hard_tolerance": 0.02, "unit": "normalized_vector_error",
    "landmark_ids": ["EDGE_CONTINUITY_ANCHOR_A", "EDGE_CONTINUITY_ANCHOR_B"],
    "aggregation": "max", "calibration_id": "edge_motion_pose_baseline_v1",
    "calibration_key": "edge_measurements",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_receipt_hash(receipt: dict[str, Any]) -> str:
    payload = copy.deepcopy(receipt)
    payload.pop("receipt_sha256", None)
    return sha256_bytes(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8"))


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def reject_fixture_flags(value: Any, trail: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if ("fixture" in lowered or "synthetic" in lowered) and child not in (None, False, "", 0):
                raise ValueError(f"{trail}.{key}: fixture/synthetic flags are prohibited")
            reject_fixture_flags(child, f"{trail}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_fixture_flags(child, f"{trail}[{index}]")


def reject_raw_authority_fields(value: Any, trail: str = "annotation") -> None:
    forbidden = {"measurements", "measurement", "value", "status", "tolerance", "comparator", "algorithm_id"}
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in forbidden:
                raise ValueError(f"{trail}.{key}: raw annotation cannot contain computed values or authority")
            reject_raw_authority_fields(child, f"{trail}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_raw_authority_fields(child, f"{trail}[{index}]")


def resolve_run_file(run_root: Path, locator: Any, label: str) -> Path:
    if not isinstance(locator, str) or not locator:
        raise ValueError(f"{label}: locator must be a non-empty run-relative string")
    relative = Path(locator)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{label}: locator must be run-relative and cannot contain '..'")
    path = (run_root / relative).resolve()
    path.relative_to(run_root)
    if not path.is_file():
        raise ValueError(f"{label}: file is missing")
    return path


def resolve_output(run_root: Path, locator: Any) -> Path:
    relative = Path(str(locator))
    if not str(locator) or relative.is_absolute() or ".." in relative.parts:
        raise ValueError("output must be a non-empty safe run-relative locator")
    output = (run_root / relative).resolve()
    output.relative_to(run_root)
    return output


def rounded(value: float) -> float:
    if not math.isfinite(float(value)):
        raise ValueError("non-finite value is prohibited")
    return round(float(value), 12)


def point(value: Any, label: str) -> tuple[float, float]:
    if (
        not isinstance(value, list) or len(value) != 2
        or any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value)
        or any(not math.isfinite(float(item)) or not 0 <= float(item) <= 1 for item in value)
    ):
        raise ValueError(f"{label}: expected normalized [x,y]")
    return float(value[0]), float(value[1])


def distance(left: tuple[float, float], right: tuple[float, float]) -> float:
    return math.hypot(left[0] - right[0], left[1] - right[1])


def polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(distance(points[index], points[index + 1]) for index in range(len(points) - 1))


def polygon_area(points: list[tuple[float, float]]) -> float:
    return abs(sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )) / 2.0


def polygon_centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    area_twice = sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )
    if abs(area_twice) <= 1e-12:
        raise ValueError("polygon is degenerate")
    cx = sum(
        (points[index][0] + points[(index + 1) % len(points)][0])
        * (points[index][0] * points[(index + 1) % len(points)][1] - points[(index + 1) % len(points)][0] * points[index][1])
        for index in range(len(points))
    ) / (3 * area_twice)
    cy = sum(
        (points[index][1] + points[(index + 1) % len(points)][1])
        * (points[index][0] * points[(index + 1) % len(points)][1] - points[(index + 1) % len(points)][0] * points[index][1])
        for index in range(len(points))
    ) / (3 * area_twice)
    return cx, cy


def point_in_local_frame(
    value: tuple[float, float], origin: tuple[float, float],
    x_axis_point: tuple[float, float], y_axis_point: tuple[float, float],
) -> tuple[float, float] | None:
    x_axis = (x_axis_point[0] - origin[0], x_axis_point[1] - origin[1])
    y_axis = (y_axis_point[0] - origin[0], y_axis_point[1] - origin[1])
    determinant = x_axis[0] * y_axis[1] - x_axis[1] * y_axis[0]
    if abs(determinant) <= 1e-8:
        return None
    delta = (value[0] - origin[0], value[1] - origin[1])
    return (
        (delta[0] * y_axis[1] - delta[1] * y_axis[0]) / determinant,
        (x_axis[0] * delta[1] - x_axis[1] * delta[0]) / determinant,
    )


def finite_positive(value: Any) -> bool:
    return (
        not isinstance(value, bool) and isinstance(value, (int, float))
        and math.isfinite(float(value)) and float(value) > 0
    )


def derive_metric_status(value: Any, tolerance: Any, comparator: str) -> str:
    if comparator not in COMPARATORS:
        raise ValueError(f"unsupported comparator {comparator}")
    if comparator == "manual":
        if value is not None or tolerance is not None:
            raise ValueError("manual metrics require null value/tolerance")
        return "blocked"
    if value is None or tolerance is None:
        return "blocked"
    if comparator == "eq":
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("eq value must be finite")
        if isinstance(tolerance, float) and not math.isfinite(tolerance):
            raise ValueError("eq tolerance must be finite")
        return "passed" if value == tolerance else "failed"
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError("ordered metric value must be finite numeric")
    if comparator in {"lte", "gte"}:
        if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or not math.isfinite(float(tolerance)):
            raise ValueError("ordered metric tolerance must be finite numeric")
        passed = float(value) <= float(tolerance) if comparator == "lte" else float(value) >= float(tolerance)
        return "passed" if passed else "failed"
    if (
        not isinstance(tolerance, list) or len(tolerance) != 2
        or any(isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(float(item)) for item in tolerance)
        or float(tolerance[0]) > float(tolerance[1])
    ):
        raise ValueError("between tolerance must be finite ordered [min,max]")
    return "passed" if float(tolerance[0]) <= float(value) <= float(tolerance[1]) else "failed"


def metric(
    metric_id: str, value: Any, tolerance: Any, comparator: str, asset_hashes: list[str],
    *, unit: str, scope_type: str = "whole_product", region_ids: list[str] | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    if not asset_hashes or len(asset_hashes) != len(set(asset_hashes)):
        raise ValueError(f"{metric_id}: asset hashes must be non-empty and unique")
    if scope_type not in {"whole_product", "region"}:
        raise ValueError(f"{metric_id}: invalid scope")
    output = {
        "metric_id": metric_id, "value": value, "tolerance": tolerance,
        "comparator": comparator, "status": derive_metric_status(value, tolerance, comparator),
        "asset_file_sha256s": asset_hashes,
        "measurement_scope": {"scope_type": scope_type, "region_ids": sorted(set(region_ids or []))},
        "unit": unit,
    }
    if note:
        output["note"] = note
    return output


def derived_status(records: list[dict[str, Any]]) -> str:
    if not records:
        raise ValueError("metric records cannot be empty")
    statuses = [record.get("status") for record in records]
    if "failed" in statuses:
        return "failed"
    if "blocked" in statuses:
        return "blocked"
    if all(status == "passed" for status in statuses):
        return "passed"
    raise ValueError("metric record has invalid status")


def grayscale(image: Image.Image) -> list[int]:
    return [(299 * r + 587 * g + 114 * b + 500) // 1000 for r, g, b in image.getdata()]


def image_statistics(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    with Image.open(path) as probe:
        probe.verify()
    with Image.open(path) as decoded:
        decoded.load()
        image_format = str(decoded.format or "unknown")
        image = decoded.convert("RGB")
    width, height = image.size
    scale = min(1.0, SAMPLE_LONG_EDGE / max(width, height))
    sample = image.resize((max(1, round(width * scale)), max(1, round(height * scale))), Image.Resampling.NEAREST)
    pixels = list(sample.getdata())
    values = grayscale(sample)
    count = len(values)
    mean = sum(values) / count
    variance = sum((item - mean) ** 2 for item in values) / count
    histogram = [0] * 256
    for item in values:
        histogram[item] += 1
    entropy = -sum((bucket / count) * math.log2(bucket / count) for bucket in histogram if bucket)
    sw, sh = sample.size
    border = [pixels[x] for x in range(sw)] + [pixels[(sh - 1) * sw + x] for x in range(sw)]
    border += [pixels[y * sw] for y in range(sh)] + [pixels[y * sw + sw - 1] for y in range(sh)]
    background = tuple(int(median([pixel[channel] for pixel in border])) for channel in range(3))
    foreground = [
        index for index, pixel_value in enumerate(pixels)
        if max(abs(pixel_value[channel] - background[channel]) for channel in range(3)) >= FOREGROUND_DISTANCE_THRESHOLD
    ]
    bbox = None
    if foreground:
        xs, ys = [index % sw for index in foreground], [index // sw for index in foreground]
        left, top, right, bottom = min(xs), min(ys), max(xs) + 1, max(ys) + 1
        bbox = {
            "left": rounded(left / sw), "top": rounded(top / sh), "right": rounded(right / sw),
            "bottom": rounded(bottom / sh), "width": rounded((right - left) / sw),
            "height": rounded((bottom - top) / sh), "center_x": rounded((left + right) / 2 / sw),
            "center_y": rounded((top + bottom) / 2 / sh),
            "area": rounded((right - left) * (bottom - top) / (sw * sh)),
        }
    horizontal = [abs(values[y * sw + x + 1] - values[y * sw + x]) for y in range(sh) for x in range(sw - 1)]
    vertical = [abs(values[(y + 1) * sw + x] - values[y * sw + x]) for y in range(sh - 1) for x in range(sw)]
    edge_mean = (sum(horizontal) / max(1, len(horizontal)) + sum(vertical) / max(1, len(vertical))) / 510
    comparison = image.resize(PAIR_SAMPLE_SIZE, Image.Resampling.NEAREST)
    comparison_gray = grayscale(comparison)
    record = {
        "decoded_format": image_format,
        "pixel_dimensions": {"width": width, "height": height},
        "aspect_ratio": rounded(width / height),
        "exact_horizontal_16_9": width * 9 == height * 16 and width > height,
        "sample_dimensions": {"width": sw, "height": sh},
        "background_rgb_median": list(background),
        "gray_mean_normalized": rounded(mean / 255),
        "gray_standard_deviation_normalized": rounded(math.sqrt(variance) / 255),
        "entropy_bits": rounded(entropy),
        "non_uniformity_normalized": rounded(math.sqrt(variance) / 255),
        "edge_difference_mean_normalized": rounded(edge_mean),
        "foreground_fraction": rounded(len(foreground) / count),
        "content_bbox_normalized": bbox,
    }
    return record, {"comparison_gray": comparison_gray}


def validate_input_relationships(
    asset_qa: dict[str, Any], coverage: dict[str, Any], continuity: dict[str, Any],
    source_manifest: dict[str, Any], product_features: list[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    if asset_qa.get("schema_version") != "packaging-asset-qa.v1":
        raise ValueError("asset_qa must be packaging-asset-qa.v1")
    if coverage.get("schema_version") != "packaging-view-coverage.v1" or coverage.get("freeze_status") != "frozen":
        raise ValueError("coverage must be frozen packaging-view-coverage.v1")
    if continuity.get("schema_version") != "packaging-continuity-contract.v1" or continuity.get("freeze_status") != "frozen":
        raise ValueError("continuity contract must be frozen packaging-continuity-contract.v1")
    if coverage.get("product_state_id") != continuity.get("product_state_id"):
        raise ValueError("product_state_id mismatch")
    if source_manifest.get("product_state_id") != continuity.get("product_state_id"):
        raise ValueError("source manifest/continuity product_state_id mismatch")
    views = coverage.get("views")
    if not isinstance(views, list) or not views:
        raise ValueError("coverage views must be non-empty")
    by_view: dict[str, dict[str, Any]] = {}
    for item in views:
        view_id = item.get("view_id") if isinstance(item, dict) else None
        if not isinstance(view_id, str) or not view_id or view_id in by_view:
            raise ValueError("coverage view IDs must be unique/non-empty")
        by_view[view_id] = item
    required = {view_id for view_id, item in by_view.items() if item.get("required") is True}
    assets = asset_qa.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("asset_qa assets must be non-empty")
    asset_views = [item.get("view_id") for item in assets if isinstance(item, dict)]
    if len(asset_views) != len(assets) or len(asset_views) != len(set(asset_views)) or set(asset_views) != required:
        raise ValueError("asset_qa must exactly cover required views")
    gates = continuity.get("required_gates")
    expected_gates = derive_required_continuity_gates(product_features)
    if not isinstance(gates, list) or set(gates) != expected_gates or len(gates) != len(set(gates)):
        raise ValueError(
            "continuity required_gates must exactly match the source-feature-derived v2 gate set "
            f"{sorted(expected_gates)}"
        )
    return assets, by_view, gates


def required_edge_pairs(coverage_views: dict[str, dict[str, Any]]) -> list[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for view_id, view in coverage_views.items():
        family = str(view.get("family") or "")
        target_id = view.get("next_view_id")
        target = coverage_views.get(target_id)
        if (
            view.get("required") is True and view.get("shot_scale") == "full_product"
            and (family in {"neutral_ring", "high_angle", "low_angle", "elevation_ring"} or "ring" in family)
            and isinstance(target_id, str) and target is not None and target.get("required") is True
            and target.get("shot_scale") == "full_product" and target.get("family") == family
        ):
            pairs.add((view_id, target_id))
    return sorted(pairs)


def base_gate_measurements(required_gates: list[str], assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hashes = [item["file_sha256"] for item in assets]
    exact_fraction = sum(bool(item["image_metrics"]["exact_horizontal_16_9"]) for item in assets) / len(assets)
    output = []
    for gate_id in required_gates:
        records = [
            metric(f"{gate_id}:approved_master_hash_binding_count", len(hashes), len(hashes), "eq", hashes, unit="count"),
            metric(f"{gate_id}:decoded_master_fraction", 1.0, 1.0, "eq", hashes, unit="fraction"),
            metric(f"{gate_id}:exact_horizontal_16_9_fraction", rounded(exact_fraction), 1.0, "eq", hashes, unit="fraction"),
            metric(
                f"{gate_id}:blocked_gate_specific_raw_evidence", None, None, "manual", hashes,
                unit="not_applicable", note="gate-specific raw structures and deterministic algorithm output are required",
            ),
        ]
        output.append({
            "gate_id": gate_id, "status": derived_status(records),
            "status_derivation": "failed_if_any_metric_failed_else_blocked_if_any_metric_blocked_else_passed",
            "semantic_claim_status": "not_established_without_gate_specific_raw_evidence",
            "semantic_evidence_applied": False, "metric_records": records,
        })
    return output


def base_edge_measurements(
    pairs: list[tuple[str, str]], assets_by_view: dict[str, dict[str, Any]], internals: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    output = []
    for from_view, to_view in pairs:
        left, right = assets_by_view[from_view], assets_by_view[to_view]
        hashes = [left["file_sha256"], right["file_sha256"]]
        lm, rm = left["image_metrics"], right["image_metrics"]
        luma_a, luma_b = internals[from_view]["comparison_gray"], internals[to_view]["comparison_gray"]
        luma_mae = sum(abs(a - b) for a, b in zip(luma_a, luma_b)) / len(luma_a) / 255
        bbox_a, bbox_b = lm["content_bbox_normalized"], rm["content_bbox_normalized"]
        bbox_delta = 1.0 if bbox_a is None or bbox_b is None else distance(
            (bbox_a["center_x"], bbox_a["center_y"]), (bbox_b["center_x"], bbox_b["center_y"]),
        )
        edge_id = f"{from_view}__TO__{to_view}"
        records = [
            metric(f"{edge_id}:width_delta_px", abs(lm["pixel_dimensions"]["width"] - rm["pixel_dimensions"]["width"]), 0, "eq", hashes, unit="pixels"),
            metric(f"{edge_id}:height_delta_px", abs(lm["pixel_dimensions"]["height"] - rm["pixel_dimensions"]["height"]), 0, "eq", hashes, unit="pixels"),
            metric(f"{edge_id}:brightness_difference_observed", rounded(luma_mae), 1.0, "lte", hashes, unit="normalized", note="observation only"),
            metric(f"{edge_id}:content_bbox_center_difference_observed", rounded(bbox_delta), 2.0, "lte", hashes, unit="normalized", note="observation only"),
            metric(
                f"{edge_id}:blocked_shared_named_edge_geometry", None, None, "manual", hashes,
                unit="not_applicable", note="shared named edge landmarks are required",
            ),
        ]
        output.append({
            "edge_id": edge_id, "from_view_id": from_view, "to_view_id": to_view,
            "from_file_path": left["file_path"], "to_file_path": right["file_path"],
            "from_file_sha256": left["file_sha256"], "to_file_sha256": right["file_sha256"],
            "status": derived_status(records),
            "status_derivation": "failed_if_any_metric_failed_else_blocked_if_any_metric_blocked_else_passed",
            "semantic_continuity_status": "not_established_without_shared_named_raw_geometry",
            "semantic_evidence_applied": False, "metric_records": records,
        })
    return output


def parse_points(value: Any, label: str, minimum: int) -> list[tuple[float, float]]:
    if not isinstance(value, list) or len(value) < minimum:
        raise ValueError(f"{label}: needs at least {minimum} points")
    return [point(item, f"{label}[{index}]") for index, item in enumerate(value)]


def parse_mask_record(item: dict[str, Any], label: str) -> dict[str, Any]:
    encoding = item.get("encoding")
    if encoding == "polygon_normalized":
        points = parse_points(item.get("polygon_normalized"), label, 3)
        if polygon_area(points) <= 1e-8:
            raise ValueError(f"{label}: polygon is degenerate")
        return {"encoding": encoding, "points": points}
    if encoding == "rle_row_major":
        width, height, counts = item.get("width"), item.get("height"), item.get("counts")
        if (
            isinstance(width, bool) or not isinstance(width, int) or width <= 0
            or isinstance(height, bool) or not isinstance(height, int) or height <= 0
            or not isinstance(counts, list) or not counts
            or any(isinstance(run, bool) or not isinstance(run, int) or run < 0 for run in counts)
            or sum(counts) != width * height
        ):
            raise ValueError(f"{label}: invalid row-major RLE")
        return {"encoding": encoding, "width": width, "height": height, "counts": counts}
    raise ValueError(f"{label}: encoding must be polygon_normalized or rle_row_major")


def load_raw_annotation(
    run_root: Path, declaration: dict[str, Any], assets_by_view: dict[str, dict[str, Any]],
    valid_regions: set[str], valid_landmarks: set[str],
) -> tuple[dict[str, Any], dict[str, dict[tuple[str, str], dict[str, Any]]]]:
    annotation_id = declaration.get("annotation_id")
    if not isinstance(annotation_id, str) or not annotation_id:
        raise ValueError("annotation_id must be non-empty")
    if declaration.get("annotation_type") != "raw_geometry_json":
        raise ValueError(f"annotation {annotation_id}: annotation_type must be raw_geometry_json")
    path = resolve_run_file(run_root, declaration.get("annotation_path"), f"annotation {annotation_id}")
    if path.suffix.lower() != ".json" or declaration.get("annotation_sha256") != sha256_file(path):
        raise ValueError(f"annotation {annotation_id}: JSON path/hash binding failed")
    content = load_json(path)
    reject_fixture_flags(content, f"annotation.{annotation_id}")
    reject_raw_authority_fields(content, f"annotation.{annotation_id}")
    if content.get("schema_version") != ANNOTATION_SCHEMA or content.get("annotation_id") != annotation_id or content.get("annotation_type") != "raw_geometry_json":
        raise ValueError(f"annotation {annotation_id}: schema/id/type mismatch")
    declared_views, declared_hashes, declared_regions = (
        declaration.get("view_ids"), declaration.get("asset_file_sha256s"), declaration.get("region_ids")
    )
    if any(not isinstance(value, list) or len(value) != len(set(value)) for value in (declared_views, declared_hashes, declared_regions)):
        raise ValueError(f"annotation {annotation_id}: view/hash/region locks must be unique arrays")
    if not declared_views or set(declared_views) - set(assets_by_view):
        raise ValueError(f"annotation {annotation_id}: invalid view locks")
    expected_hashes = [assets_by_view[view_id]["file_sha256"] for view_id in declared_views]
    if set(declared_hashes) != set(expected_hashes) or not set(declared_regions).issubset(valid_regions):
        raise ValueError(f"annotation {annotation_id}: asset/region locks are invalid")
    if any(content.get(key) != declaration.get(key) for key in ("view_ids", "asset_file_sha256s", "region_ids")):
        raise ValueError(f"annotation {annotation_id}: content locks differ from declaration")
    if set(content) - ({"schema_version", "annotation_id", "annotation_type", "view_ids", "asset_file_sha256s", "region_ids"} | RAW_ANNOTATION_KEYS):
        raise ValueError(f"annotation {annotation_id}: only raw geometry keys are allowed")
    indexes: dict[str, dict[tuple[str, str], dict[str, Any]]] = {key: {} for key in RAW_ANNOTATION_KEYS}
    specs = {
        "landmarks": ("landmark_id", "point_normalized", 1),
        "polylines": ("polyline_id", "points_normalized", 2),
        "polygons": ("polygon_id", "points_normalized", 3),
    }
    structure_count = 0
    for structure_type, (id_key, geometry_key, minimum) in specs.items():
        values = content.get(structure_type)
        if not isinstance(values, list):
            raise ValueError(f"annotation {annotation_id}: {structure_type} must be an array")
        for index, item in enumerate(values):
            if not isinstance(item, dict):
                raise ValueError(f"annotation {annotation_id}/{structure_type}[{index}]: invalid record")
            structure_id, view_id, asset_hash, region_id = item.get(id_key), item.get("view_id"), item.get("asset_file_sha256"), item.get("region_id")
            if not isinstance(structure_id, str) or not structure_id or view_id not in declared_views or asset_hash != assets_by_view[view_id]["file_sha256"]:
                raise ValueError(f"annotation {annotation_id}/{structure_type}[{index}]: ID/view/asset binding failed")
            if region_id is not None and region_id not in declared_regions:
                raise ValueError(f"annotation {annotation_id}/{structure_type}[{index}]: region binding failed")
            if structure_type == "landmarks" and structure_id not in valid_landmarks:
                raise ValueError(f"annotation {annotation_id}: landmark {structure_id} is absent from coverage")
            geometry = point(item.get(geometry_key), f"annotation {annotation_id}/{structure_type}[{index}]") if minimum == 1 else parse_points(item.get(geometry_key), f"annotation {annotation_id}/{structure_type}[{index}]", minimum)
            if structure_type == "polygons" and polygon_area(geometry) <= 1e-8:
                raise ValueError(f"annotation {annotation_id}/{structure_type}[{index}]: degenerate polygon")
            key = (view_id, structure_id)
            if key in indexes[structure_type]:
                raise ValueError(f"annotation {annotation_id}: duplicate {structure_type} key {key}")
            indexes[structure_type][key] = {"geometry": geometry, "asset_file_sha256": asset_hash, "region_id": region_id}
            structure_count += 1
    masks = content.get("mask_rle_or_polygon")
    if not isinstance(masks, list):
        raise ValueError(f"annotation {annotation_id}: mask_rle_or_polygon must be an array")
    for index, item in enumerate(masks):
        if not isinstance(item, dict):
            raise ValueError(f"annotation {annotation_id}/mask[{index}]: invalid record")
        mask_id, view_id, asset_hash, region_id = item.get("mask_id"), item.get("view_id"), item.get("asset_file_sha256"), item.get("region_id")
        if not isinstance(mask_id, str) or not mask_id or view_id not in declared_views or asset_hash != assets_by_view[view_id]["file_sha256"]:
            raise ValueError(f"annotation {annotation_id}/mask[{index}]: ID/view/asset binding failed")
        if region_id is not None and region_id not in declared_regions:
            raise ValueError(f"annotation {annotation_id}/mask[{index}]: region binding failed")
        key = (view_id, mask_id)
        if key in indexes["mask_rle_or_polygon"]:
            raise ValueError(f"annotation {annotation_id}: duplicate mask key {key}")
        indexes["mask_rle_or_polygon"][key] = {**parse_mask_record(item, f"annotation {annotation_id}/mask[{index}]"), "asset_file_sha256": asset_hash, "region_id": region_id}
        structure_count += 1
    if structure_count == 0:
        raise ValueError(f"annotation {annotation_id}: at least one raw structure is required")
    binding = {
        "annotation_id": annotation_id, "annotation_type": "raw_geometry_json",
        "annotation_path": declaration["annotation_path"], "annotation_sha256": sha256_file(path),
        "view_ids": declared_views, "asset_file_sha256s": declared_hashes,
        "region_ids": declared_regions, "raw_structure_count": structure_count,
    }
    return binding, indexes


def merge_indexes(annotation_ids: list[str], raw_by_annotation: dict[str, dict[str, dict[tuple[str, str], dict[str, Any]]]]) -> dict[str, dict[tuple[str, str], dict[str, Any]]]:
    merged: dict[str, dict[tuple[str, str], dict[str, Any]]] = {key: {} for key in RAW_ANNOTATION_KEYS}
    for annotation_id in annotation_ids:
        for structure_type, values in raw_by_annotation[annotation_id].items():
            overlap = set(merged[structure_type]).intersection(values)
            if overlap:
                raise ValueError(f"selected annotations conflict on {structure_type}: {sorted(overlap)}")
            merged[structure_type].update(values)
    return merged


def mask_image(record: dict[str, Any], size: tuple[int, int] = REGION_SAMPLE_SIZE) -> Image.Image:
    if record["encoding"] == "polygon_normalized":
        image = Image.new("1", size, 0)
        ImageDraw.Draw(image).polygon([(round(x * (size[0] - 1)), round(y * (size[1] - 1))) for x, y in record["points"]], fill=1)
        return image
    width, height, counts = record["width"], record["height"], record["counts"]
    pixels: list[int] = []
    bit = 0
    for run in counts:
        pixels.extend([bit] * run)
        bit = 1 - bit
    image = Image.new("1", (width, height), 0)
    image.putdata(pixels)
    return image.resize(size, Image.Resampling.NEAREST)


def polygon_mask(points: list[tuple[float, float]], size: tuple[int, int] = REGION_SAMPLE_SIZE) -> Image.Image:
    image = Image.new("1", size, 0)
    ImageDraw.Draw(image).polygon([(round(x * (size[0] - 1)), round(y * (size[1] - 1))) for x, y in points], fill=1)
    return image


def required_views(parameters: dict[str, Any], policy: str, ring_views: list[str], all_views: set[str]) -> list[str]:
    view_ids = parameters.get("view_ids")
    if not isinstance(view_ids, list) or len(view_ids) != len(set(view_ids)) or set(view_ids) - all_views:
        raise ValueError("algorithm parameters require unique valid view_ids")
    if policy == "all_ring" and set(view_ids) != set(ring_views):
        raise ValueError("gate requires exactly every neutral-ring view")
    if policy == "minimum_two" and len(view_ids) < 2:
        raise ValueError("gate requires at least two annotated views")
    return view_ids


def validate_tolerance(comparator: str, tolerance: Any, requirement: dict[str, Any]) -> None:
    if comparator != requirement["comparator"]:
        raise ValueError("semantic comparator does not match gate-specific contract")
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or not math.isfinite(float(tolerance)):
        raise ValueError("semantic tolerance must be finite numeric")
    hard = float(requirement["hard_tolerance"])
    if comparator == "lte" and not 0 <= float(tolerance) <= hard:
        raise ValueError(f"semantic tolerance exceeds hard maximum {hard}")
    if comparator == "gte" and not hard <= float(tolerance) <= 1.0:
        raise ValueError(f"semantic tolerance is weaker than hard minimum {hard}")


def exact_parameters(parameters: dict[str, Any], requirement: dict[str, Any], keys: list[str]) -> None:
    for key in keys:
        if parameters.get(key) != requirement.get(key):
            raise ValueError(f"algorithm parameter {key} violates gate-specific requirement")


def validated_gate_calibration(
    owner_id: str, requirement: dict[str, Any], calibrations: dict[str, Any],
    view_ids: list[str], source_manifest_sha256: str,
    edge_pair: tuple[str, str] | None = None,
) -> dict[str, Any] | None:
    calibration_id = requirement.get("calibration_id")
    if calibration_id is None:
        return None
    calibration = calibrations.get(requirement.get("calibration_key", owner_id))
    if calibration is None:
        return None
    if not isinstance(calibration, dict):
        raise ValueError(f"{owner_id}: calibration must be an object")
    if (
        calibration.get("calibration_id") != calibration_id
        or calibration.get("basis") != "source_pose_locked_before_generation"
        or calibration.get("source_manifest_sha256") != source_manifest_sha256
    ):
        raise ValueError(f"{owner_id}: calibration identity/source lock is invalid")
    if edge_pair is not None:
        edge_id = f"{edge_pair[0]}__TO__{edge_pair[1]}"
        by_edge = calibration.get("by_edge")
        edge = by_edge.get(edge_id) if isinstance(by_edge, dict) else None
        if (
            not isinstance(edge, dict)
            or edge.get("from_view_id") != edge_pair[0]
            or edge.get("to_view_id") != edge_pair[1]
        ):
            raise ValueError(f"{owner_id}: calibrated edge binding is missing or invalid")
    else:
        by_view = calibration.get("by_view")
        if not isinstance(by_view, dict) or set(by_view) != set(view_ids):
            raise ValueError(f"{owner_id}: calibration must exactly cover algorithm views")
    return calibration


def calculate_geometry_algorithm(
    algorithm_id: str, parameters: dict[str, Any], indexes: dict[str, dict[tuple[str, str], dict[str, Any]]],
    *, run_root: Path, assets_by_view: dict[str, dict[str, Any]], review_boards: list[dict[str, Any]],
    gate_calibration: dict[str, Any] | None = None,
) -> float | None:
    view_ids = parameters.get("view_ids") or []
    if algorithm_id == "presence_fraction":
        mapping = indexes[parameters["structure_type"]]
        expected = [(view_id, structure_id) for view_id in view_ids for structure_id in parameters["structure_ids"]]
        return sum(key in mapping for key in expected) / len(expected) if expected else None
    if algorithm_id == "landmark_coordinate_spread":
        values: list[tuple[float, float]] = []
        for view_id in view_ids:
            for landmark_id in parameters["landmark_ids"]:
                record = indexes["landmarks"].get((view_id, landmark_id))
                if record is None:
                    return None
                values.append(record["geometry"])
        axis = parameters["axis"]
        if axis == "x":
            return max(item[0] for item in values) - min(item[0] for item in values)
        if axis == "y":
            return max(item[1] for item in values) - min(item[1] for item in values)
        return max((distance(left, right) for left in values for right in values), default=0.0)
    if algorithm_id == "pair_length_spread":
        spreads = []
        for left_id, right_id in parameters["landmark_pairs"]:
            lengths = []
            for view_id in view_ids:
                left, right = indexes["landmarks"].get((view_id, left_id)), indexes["landmarks"].get((view_id, right_id))
                if left is None or right is None:
                    return None
                lengths.append(distance(left["geometry"], right["geometry"]))
            spreads.append(max(lengths) - min(lengths))
        return max(spreads, default=None)
    if algorithm_id in {"local_frame_polygon_centroid_spread", "local_frame_vector_spread"}:
        origin_id, x_axis_id, y_axis_id = parameters["frame_landmark_ids"]
        local_values: list[tuple[float, float]] = []
        for view_id in view_ids:
            origin_record = indexes["landmarks"].get((view_id, origin_id))
            x_record = indexes["landmarks"].get((view_id, x_axis_id))
            y_record = indexes["landmarks"].get((view_id, y_axis_id))
            if origin_record is None or x_record is None or y_record is None:
                return None
            origin, x_axis, y_axis = (
                origin_record["geometry"], x_record["geometry"], y_record["geometry"]
            )
            if algorithm_id == "local_frame_polygon_centroid_spread":
                polygon_record = indexes["polygons"].get((view_id, parameters["polygon_ids"][0]))
                if polygon_record is None:
                    return None
                local = point_in_local_frame(
                    polygon_centroid(polygon_record["geometry"]), origin, x_axis, y_axis,
                )
            else:
                left_id, right_id = parameters["landmark_pairs"][0]
                left = indexes["landmarks"].get((view_id, left_id))
                right = indexes["landmarks"].get((view_id, right_id))
                if left is None or right is None:
                    return None
                local_left = point_in_local_frame(left["geometry"], origin, x_axis, y_axis)
                local_right = point_in_local_frame(right["geometry"], origin, x_axis, y_axis)
                local = None if local_left is None or local_right is None else (
                    local_right[0] - local_left[0], local_right[1] - local_left[1],
                )
            if local is None:
                return None
            local_values.append(local)
        return max(
            (distance(left, right) for left in local_values for right in local_values),
            default=0.0,
        )
    if algorithm_id == "polyline_length_spread":
        spreads = []
        for structure_id in parameters["polyline_ids"]:
            lengths = []
            for view_id in view_ids:
                record = indexes["polylines"].get((view_id, structure_id))
                if record is None:
                    return None
                lengths.append(polyline_length(record["geometry"]))
            spreads.append(max(lengths) - min(lengths))
        return max(spreads, default=None)
    if algorithm_id in {"polygon_area_spread", "polygon_centroid_spread"}:
        spreads = []
        for polygon_id in parameters["polygon_ids"]:
            geometries = []
            for view_id in view_ids:
                record = indexes["polygons"].get((view_id, polygon_id))
                if record is None:
                    return None
                geometries.append(record["geometry"])
            if algorithm_id == "polygon_area_spread":
                values = [polygon_area(item) for item in geometries]
                spreads.append(max(values) - min(values))
            else:
                centers = [polygon_centroid(item) for item in geometries]
                spreads.append(max((distance(left, right) for left in centers for right in centers), default=0.0))
        return max(spreads, default=None)
    if algorithm_id == "pose_conditioned_polygon_baseline_error":
        if gate_calibration is None:
            return None
        errors: list[float] = []
        by_view = gate_calibration["by_view"]
        polygon_id = parameters["polygon_ids"][0]
        for view_id in view_ids:
            record = indexes["polygons"].get((view_id, polygon_id))
            baseline = by_view.get(view_id)
            if record is None or not isinstance(baseline, dict):
                return None
            expected_area = baseline.get("area_normalized")
            expected_aspect = baseline.get("bbox_aspect_ratio")
            if not finite_positive(expected_area) or not finite_positive(expected_aspect):
                raise ValueError("silhouette calibration values must be finite and positive")
            geometry = record["geometry"]
            actual_area = polygon_area(geometry)
            xs, ys = [item[0] for item in geometry], [item[1] for item in geometry]
            height = max(ys) - min(ys)
            if height <= 1e-8:
                return None
            actual_aspect = (max(xs) - min(xs)) / height
            errors.extend([
                abs(actual_area - float(expected_area)) / float(expected_area),
                abs(actual_aspect - float(expected_aspect)) / float(expected_aspect),
            ])
        return max(errors, default=None)
    if algorithm_id == "mask_iou_error":
        errors = []
        for mask_id in parameters["mask_ids"]:
            masks = []
            for view_id in view_ids:
                record = indexes["mask_rle_or_polygon"].get((view_id, mask_id))
                if record is None:
                    return None
                masks.append(list(mask_image(record).getdata()))
            for index, left in enumerate(masks):
                for right in masks[index + 1:]:
                    intersection = sum(bool(a) and bool(b) for a, b in zip(left, right))
                    union = sum(bool(a) or bool(b) for a, b in zip(left, right))
                    errors.append(1.0 if union == 0 else 1.0 - intersection / union)
        return max(errors, default=None)
    if algorithm_id in {"horizontal_line_angle_error", "horizontal_line_angle_range"}:
        angles = []
        for polyline_id in parameters["polyline_ids"]:
            for view_id in view_ids:
                record = indexes["polylines"].get((view_id, polyline_id))
                if record is None:
                    return None
                points = record["geometry"]
                angle = math.degrees(math.atan2(points[-1][1] - points[0][1], points[-1][0] - points[0][0]))
                while angle > 90:
                    angle -= 180
                while angle < -90:
                    angle += 180
                angles.append(angle)
        return max(abs(item) for item in angles) if algorithm_id.endswith("error") else max(angles) - min(angles)
    if algorithm_id == "component_graph_signature_match":
        total, mismatch = 0, 0
        for view_id in view_ids:
            for landmark_id in parameters["node_landmark_ids"]:
                total += 1
                mismatch += (view_id, landmark_id) not in indexes["landmarks"]
            for edge in parameters["edges"]:
                total += 1
                line = indexes["polylines"].get((view_id, edge["polyline_id"]))
                left = indexes["landmarks"].get((view_id, edge["from_landmark_id"]))
                right = indexes["landmarks"].get((view_id, edge["to_landmark_id"]))
                if line is None or left is None or right is None:
                    mismatch += 1
                    continue
                points = line["geometry"]
                forward = distance(points[0], left["geometry"]) + distance(points[-1], right["geometry"])
                reverse = distance(points[-1], left["geometry"]) + distance(points[0], right["geometry"])
                mismatch += min(forward, reverse) > GRAPH_ENDPOINT_SNAP_TOLERANCE * 2
        return mismatch / total if total else None
    if algorithm_id in {"region_pixel_stat_spread", "pose_conditioned_region_stat_baseline_error"}:
        statistics = []
        statistic_by_view: dict[str, float] = {}
        structure_type = parameters["region_structure_type"]
        mapping_key = "polygons" if structure_type == "polygons" else "mask_rle_or_polygon"
        for view_id in view_ids:
            path = run_root / assets_by_view[view_id]["file_path"]
            with Image.open(path) as opened:
                image = opened.convert("RGB").resize(REGION_SAMPLE_SIZE, Image.Resampling.NEAREST)
            image_gray = grayscale(image)
            for structure_id in parameters["structure_ids"]:
                record = indexes[mapping_key].get((view_id, structure_id))
                if record is None:
                    return None
                mask = polygon_mask(record["geometry"]) if mapping_key == "polygons" else mask_image(record)
                selected = [pixel for pixel, include in zip(image_gray, mask.getdata()) if include]
                if not selected:
                    return None
                mean = sum(selected) / len(selected) / 255
                if parameters["statistic"] == "luma_mean":
                    statistic_value = mean
                elif parameters["statistic"] == "luma_std":
                    statistic_value = math.sqrt(sum((item / 255 - mean) ** 2 for item in selected) / len(selected))
                elif parameters["statistic"] == "entropy":
                    histogram = [0] * 256
                    for item in selected:
                        histogram[item] += 1
                    statistic_value = -sum((bucket / len(selected)) * math.log2(bucket / len(selected)) for bucket in histogram if bucket) / 8
                else:
                    raise ValueError("unsupported region pixel statistic")
                statistics.append(statistic_value)
                statistic_by_view[view_id] = statistic_value
        if algorithm_id == "region_pixel_stat_spread":
            return max(statistics) - min(statistics) if statistics else None
        if gate_calibration is None:
            return None
        errors = []
        for view_id in view_ids:
            baseline = gate_calibration["by_view"].get(view_id)
            expected = baseline.get("statistic_value") if isinstance(baseline, dict) else None
            if not isinstance(expected, (int, float)) or isinstance(expected, bool) or not math.isfinite(float(expected)):
                raise ValueError("region-stat calibration values must be finite numeric")
            errors.append(abs(statistic_by_view[view_id] - float(expected)))
        return max(errors, default=None)
    if algorithm_id == "edge_named_landmark_displacement":
        from_view, to_view = parameters["from_view_id"], parameters["to_view_id"]
        values = []
        for landmark_id in parameters["landmark_ids"]:
            left, right = indexes["landmarks"].get((from_view, landmark_id)), indexes["landmarks"].get((to_view, landmark_id))
            if left is None or right is None:
                return None
            values.append(distance(left["geometry"], right["geometry"]))
        return max(values) if parameters["aggregation"] == "max" else sum(values) / len(values)
    if algorithm_id in {
        "edge_pose_conditioned_landmark_vector_error",
        "loop_pose_conditioned_landmark_vector_error",
    }:
        if gate_calibration is None:
            return None
        from_view, to_view = parameters["from_view_id"], parameters["to_view_id"]
        edge_id = f"{from_view}__TO__{to_view}"
        edge = gate_calibration["by_edge"].get(edge_id)
        expected_vectors = edge.get("landmark_vectors") if isinstance(edge, dict) else None
        if not isinstance(expected_vectors, dict) or set(expected_vectors) != set(parameters["landmark_ids"]):
            raise ValueError("edge calibration landmark-vector coverage is invalid")
        errors = []
        for landmark_id in parameters["landmark_ids"]:
            left = indexes["landmarks"].get((from_view, landmark_id))
            right = indexes["landmarks"].get((to_view, landmark_id))
            expected = expected_vectors[landmark_id]
            if left is None or right is None:
                return None
            if (
                not isinstance(expected, list) or len(expected) != 2
                or any(isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(float(item)) for item in expected)
            ):
                raise ValueError("edge calibration vectors must be finite [dx,dy]")
            actual = (
                right["geometry"][0] - left["geometry"][0],
                right["geometry"][1] - left["geometry"][1],
            )
            errors.append(distance(actual, (float(expected[0]), float(expected[1]))))
        return max(errors) if parameters["aggregation"] == "max" else sum(errors) / len(errors)
    if algorithm_id == "board_input_binding":
        expected = {item["file_sha256"] for item in assets_by_view.values()}
        inputs = [item["file_sha256"] for board in review_boards if board.get("role") == parameters["required_role"] for item in board.get("inputs") or []]
        mismatch = len(expected.symmetric_difference(inputs)) + max(0, len(inputs) - len(set(inputs)))
        mismatch += sum(board.get("derivation_mode") != "deterministic_composite" for board in review_boards if board.get("role") == parameters["required_role"])
        return mismatch / max(1, len(expected))
    raise ValueError(f"unsupported deterministic algorithm {algorithm_id}")


def calculate_post_copy_lock(
    run_root: Path, parameters: dict[str, Any], assets_by_view: dict[str, dict[str, Any]],
) -> tuple[float, dict[str, Any]]:
    locator, expected_hash = parameters.get("post_composite_verification_path"), parameters.get("post_composite_verification_sha256")
    if locator != "07_qa/post_composite_verification.json":
        raise ValueError("copy_render_gate must bind the canonical post-composite verification path")
    path = resolve_run_file(run_root, locator, "post-composite verification")
    if expected_hash != sha256_file(path):
        raise ValueError("post-composite verification hash mismatch")
    post = load_json(path)
    if post.get("schema_version") != "packaging-post-composite-verification.v1":
        raise ValueError("invalid post-composite verification schema")
    results = post.get("asset_results")
    by_view = {item.get("view_id"): item for item in results if isinstance(item, dict)} if isinstance(results, list) else {}
    total, failures = 0, 0
    if set(by_view) != set(assets_by_view) or not isinstance(results, list) or len(results) != len(by_view):
        total += 1; failures += 1
    for view_id, asset in assets_by_view.items():
        total += 1
        result = by_view.get(view_id, {})
        if result.get("asset_id") != asset.get("asset_id") or result.get("asset_file_sha256") != asset.get("file_sha256"):
            failures += 1
        for path_key, hash_key in (
            ("composition_receipt_path", "composition_receipt_sha256"),
            ("post_ocr_evidence_path", "post_ocr_evidence_sha256"),
        ):
            total += 1
            try:
                evidence_path = resolve_run_file(run_root, result.get(path_key), f"post {view_id} {path_key}")
                if result.get(hash_key) != sha256_file(evidence_path):
                    failures += 1
            except (OSError, ValueError):
                failures += 1
        for field in result.get("field_results") or []:
            total += 1
            failures += not (
                field.get("match") is True
                and isinstance(field.get("expected_text_sha256"), str)
                and field.get("expected_text_sha256") == field.get("observed_text_sha256")
            )
        for code in result.get("code_results") or []:
            total += 1
            failures += not (
                code.get("payload_match") is True and code.get("checksum_result") == "passed"
                and code.get("symbol_geometry_status") == "matched"
                and code.get("expected_payload_sha256") == code.get("observed_payload_sha256")
            )
        for graphic in result.get("graphic_results") or []:
            total += 1
            failures += graphic.get("comparison_status") != "matched"
    for key in (
        "copy_content_lock_status", "label_artwork_lock_status", "code_payload_lock_status",
        "code_symbol_lock_status", "logo_graphic_lock_status", "exact_copy_lock_status",
    ):
        total += 1; failures += post.get(key) != "approved"
    return failures / max(1, total), {"path": locator, "sha256": expected_hash}


def semantic_metric(
    owner_id: str, source: dict[str, Any], requirement: dict[str, Any],
    *, annotation_bindings: dict[str, dict[str, Any]], raw_by_annotation: dict[str, Any],
    assets_by_view: dict[str, dict[str, Any]], coverage_views: dict[str, dict[str, Any]],
    ring_views: list[str], valid_regions: set[str], run_root: Path, review_boards: list[dict[str, Any]],
    edge_pair: tuple[str, str] | None = None, continuity_calibrations: dict[str, Any] | None = None,
    source_manifest_sha256: str | None = None,
) -> tuple[dict[str, Any], set[str]]:
    if "value" in source or "status" in source:
        raise ValueError(f"{owner_id}: semantic evidence cannot submit value/status")
    metric_id, algorithm_id, parameters = source.get("metric_id"), source.get("algorithm_id"), source.get("parameters")
    if not isinstance(metric_id, str) or not metric_id.startswith(owner_id + ":") or algorithm_id != requirement["algorithm_id"] or not isinstance(parameters, dict):
        raise ValueError(f"{owner_id}: metric ID/algorithm/parameters violate gate-specific contract")
    reject_raw_authority_fields(parameters, f"semantic.{owner_id}.parameters")
    validate_tolerance(source.get("comparator"), source.get("tolerance"), requirement)
    if source.get("unit") != requirement["unit"]:
        raise ValueError(f"{owner_id}: unit violates gate-specific contract")
    annotation_ids = source.get("annotation_ids")
    no_annotation_algorithm = algorithm_id in {"board_input_binding", "post_copy_verification_lock"}
    if (
        not isinstance(annotation_ids, list) or len(annotation_ids) != len(set(annotation_ids))
        or any(item not in annotation_bindings for item in annotation_ids)
        or (no_annotation_algorithm and annotation_ids)
        or (not no_annotation_algorithm and not annotation_ids)
    ):
        raise ValueError(f"{owner_id}: annotation IDs violate algorithm contract")
    indexes = merge_indexes(annotation_ids, raw_by_annotation) if annotation_ids else {key: {} for key in RAW_ANNOTATION_KEYS}
    all_view_ids = set(assets_by_view)
    expected_hashes: list[str]
    if edge_pair:
        exact_parameters(parameters, requirement, ["landmark_ids", "aggregation", "calibration_id"])
        if parameters.get("from_view_id") != edge_pair[0] or parameters.get("to_view_id") != edge_pair[1]:
            raise ValueError(f"{owner_id}: edge parameters do not match edge owner")
        expected_hashes = [assets_by_view[edge_pair[0]]["file_sha256"], assets_by_view[edge_pair[1]]["file_sha256"]]
    elif requirement["view_policy"] == "all_assets":
        expected_hashes = [assets_by_view[view_id]["file_sha256"] for view_id in sorted(assets_by_view)]
        if algorithm_id == "board_input_binding":
            exact_parameters(parameters, requirement, ["required_role"])
        elif set(parameters) != {"post_composite_verification_path", "post_composite_verification_sha256"}:
            raise ValueError("copy_render_gate parameters must only bind canonical post evidence")
    else:
        view_ids = required_views(parameters, requirement["view_policy"], ring_views, all_view_ids)
        expected_hashes = [assets_by_view[view_id]["file_sha256"] for view_id in view_ids]
        if algorithm_id == "presence_fraction":
            exact_parameters(parameters, requirement, ["structure_type", "structure_ids"])
        elif algorithm_id == "landmark_coordinate_spread":
            exact_parameters(parameters, requirement, ["landmark_ids", "axis"])
        elif algorithm_id == "pair_length_spread":
            exact_parameters(parameters, requirement, ["landmark_pairs"])
        elif algorithm_id == "local_frame_polygon_centroid_spread":
            exact_parameters(parameters, requirement, ["polygon_ids", "frame_landmark_ids"])
        elif algorithm_id == "local_frame_vector_spread":
            exact_parameters(parameters, requirement, ["landmark_pairs", "frame_landmark_ids"])
        elif algorithm_id == "loop_pose_conditioned_landmark_vector_error":
            exact_parameters(parameters, requirement, ["landmark_ids", "calibration_id"])
            expected_loop = (ring_views[-1], ring_views[0])
            if (
                parameters.get("from_view_id") != expected_loop[0]
                or parameters.get("to_view_id") != expected_loop[1]
                or parameters.get("aggregation") != "max"
            ):
                raise ValueError("loop closure must bind the calibrated final-to-first ring edge")
        elif algorithm_id == "polyline_length_spread":
            exact_parameters(parameters, requirement, ["polyline_ids"])
        elif algorithm_id in {"polygon_area_spread", "polygon_centroid_spread"}:
            exact_parameters(parameters, requirement, ["polygon_ids"])
        elif algorithm_id == "pose_conditioned_polygon_baseline_error":
            exact_parameters(parameters, requirement, ["polygon_ids", "calibration_id"])
        elif algorithm_id == "mask_iou_error":
            exact_parameters(parameters, requirement, ["mask_ids"])
        elif algorithm_id in {"horizontal_line_angle_error", "horizontal_line_angle_range"}:
            exact_parameters(parameters, requirement, ["polyline_ids"])
        elif algorithm_id == "component_graph_signature_match":
            exact_parameters(parameters, requirement, ["node_landmark_ids", "edges"])
        elif algorithm_id == "region_pixel_stat_spread":
            exact_parameters(parameters, requirement, ["region_structure_type", "structure_ids", "statistic"])
        elif algorithm_id == "pose_conditioned_region_stat_baseline_error":
            exact_parameters(
                parameters, requirement,
                ["region_structure_type", "structure_ids", "statistic", "calibration_id"],
            )
    if source.get("asset_file_sha256s") != expected_hashes:
        raise ValueError(f"{owner_id}: metric asset hashes must exactly match algorithm views")
    scope = source.get("measurement_scope")
    if not isinstance(scope, dict) or scope.get("scope_type") not in {"whole_product", "region"}:
        raise ValueError(f"{owner_id}: invalid measurement scope")
    region_ids = scope.get("region_ids")
    if not isinstance(region_ids, list) or len(region_ids) != len(set(region_ids)) or not set(region_ids).issubset(valid_regions):
        raise ValueError(f"{owner_id}: invalid region IDs")
    bound_regions = set().union(*(set(annotation_bindings[item]["region_ids"]) for item in annotation_ids)) if annotation_ids else set()
    if scope["scope_type"] == "whole_product" and region_ids or not set(region_ids).issubset(bound_regions):
        raise ValueError(f"{owner_id}: region scope is not annotation-bound")
    if algorithm_id == "post_copy_verification_lock":
        value, external_lock = calculate_post_copy_lock(run_root, parameters, assets_by_view)
    else:
        calibration_edge_pair = edge_pair
        if algorithm_id == "loop_pose_conditioned_landmark_vector_error":
            calibration_edge_pair = (parameters["from_view_id"], parameters["to_view_id"])
        gate_calibration = validated_gate_calibration(
            owner_id, requirement, continuity_calibrations or {},
            list(parameters.get("view_ids") or []), source_manifest_sha256 or "",
            calibration_edge_pair,
        )
        value = calculate_geometry_algorithm(
            algorithm_id, parameters, indexes, run_root=run_root,
            assets_by_view=assets_by_view, review_boards=review_boards,
            gate_calibration=gate_calibration,
        )
        external_lock = None
    if value is None:
        output = metric(
            metric_id, None, None, "manual", expected_hashes, unit=requirement["unit"],
            scope_type=scope["scope_type"], region_ids=region_ids,
            note="required named raw structures are missing; gate remains blocked",
        )
        output["requested_comparator"] = source["comparator"]
        output["requested_tolerance"] = source["tolerance"]
    else:
        output = metric(
            metric_id, rounded(value), source["tolerance"], source["comparator"], expected_hashes,
            unit=requirement["unit"], scope_type=scope["scope_type"], region_ids=region_ids,
            note="value recomputed by bundled algorithm from locked raw geometry and/or image/evidence bytes",
        )
    output["algorithm_id"] = algorithm_id
    output["algorithm_parameters"] = parameters
    output["annotation_ids"] = annotation_ids
    output["annotation_file_sha256s"] = [annotation_bindings[item]["annotation_sha256"] for item in annotation_ids]
    if requirement.get("calibration_id") is not None:
        output["calibration_lock"] = {
            "calibration_id": requirement["calibration_id"],
            "basis": "source_pose_locked_before_generation",
            "source_manifest_sha256": source_manifest_sha256,
        }
    if external_lock:
        output["external_evidence_lock"] = external_lock
    return output, set(annotation_ids)


def load_semantic_evidence(
    run_root: Path, evidence_path: Path, expected_input_locks: dict[str, Any],
    required_gates: list[str], edge_records: list[dict[str, Any]], assets: list[dict[str, Any]],
    coverage_views: dict[str, dict[str, Any]], review_boards: list[dict[str, Any]],
    continuity_calibrations: dict[str, Any], source_manifest_sha256: str,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    evidence = load_json(evidence_path)
    reject_fixture_flags(evidence, "semantic_evidence")
    if evidence.get("schema_version") != SEMANTIC_EVIDENCE_SCHEMA or evidence.get("input_locks") != expected_input_locks:
        raise ValueError("semantic evidence schema/input locks are invalid")
    assets_by_view = {item["view_id"]: item for item in assets}
    valid_regions = {str(region_id) for view in coverage_views.values() for region_id in view.get("label_region_ids") or []}
    valid_landmarks = {str(landmark_id) for view in coverage_views.values() for landmark_id in view.get("geometry_landmark_ids") or []}
    declarations = evidence.get("annotations")
    if not isinstance(declarations, list):
        raise ValueError("semantic annotations must be an array")
    bindings: dict[str, dict[str, Any]] = {}
    raw: dict[str, Any] = {}
    for declaration in declarations:
        if not isinstance(declaration, dict):
            raise ValueError("semantic annotation declaration must be an object")
        annotation_id = declaration.get("annotation_id")
        if annotation_id in bindings:
            raise ValueError(f"duplicate annotation ID {annotation_id}")
        binding, indexes = load_raw_annotation(run_root, declaration, assets_by_view, valid_regions, valid_landmarks)
        bindings[binding["annotation_id"]], raw[binding["annotation_id"]] = binding, indexes
    ring_views = sorted(
        view_id for view_id, item in coverage_views.items()
        if item.get("required") is True and item.get("family") == "neutral_ring" and item.get("shot_scale") == "full_product"
    )
    if len(ring_views) < 2:
        raise ValueError("semantic continuity requires at least two neutral-ring views")
    used_annotations: set[str] = set()
    gate_map: dict[str, list[dict[str, Any]]] = {}
    gate_entries = evidence.get("gate_measurements")
    if not isinstance(gate_entries, list):
        raise ValueError("semantic gate_measurements must be an array")
    for item in gate_entries:
        gate_id = item.get("gate_id") if isinstance(item, dict) else None
        records = item.get("metric_records") if isinstance(item, dict) else None
        if gate_id not in required_gates or gate_id in gate_map or "status" in item or not isinstance(records, list) or len(records) != 1:
            raise ValueError("every semantic gate requires exactly one unique gate-specific metric")
        compiled, used = semantic_metric(
            gate_id, records[0], GATE_REQUIREMENTS[gate_id], annotation_bindings=bindings,
            raw_by_annotation=raw, assets_by_view=assets_by_view, coverage_views=coverage_views,
            ring_views=ring_views, valid_regions=valid_regions, run_root=run_root, review_boards=review_boards,
            continuity_calibrations=continuity_calibrations,
            source_manifest_sha256=source_manifest_sha256,
        )
        gate_map[gate_id] = [compiled]; used_annotations.update(used)
    expected_edges = {item["edge_id"]: (item["from_view_id"], item["to_view_id"]) for item in edge_records}
    edge_map: dict[str, list[dict[str, Any]]] = {}
    edge_entries = evidence.get("edge_measurements")
    if not isinstance(edge_entries, list):
        raise ValueError("semantic edge_measurements must be an array")
    for item in edge_entries:
        edge_id = item.get("edge_id") if isinstance(item, dict) else None
        records = item.get("metric_records") if isinstance(item, dict) else None
        if edge_id not in expected_edges or edge_id in edge_map or "status" in item or not isinstance(records, list) or len(records) != 1:
            raise ValueError("every semantic edge requires exactly one deterministic shared-geometry metric")
        if item.get("from_view_id") != expected_edges[edge_id][0] or item.get("to_view_id") != expected_edges[edge_id][1]:
            raise ValueError(f"semantic edge {edge_id}: view binding mismatch")
        compiled, used = semantic_metric(
            edge_id, records[0], EDGE_REQUIREMENT, annotation_bindings=bindings,
            raw_by_annotation=raw, assets_by_view=assets_by_view, coverage_views=coverage_views,
            ring_views=ring_views, valid_regions=valid_regions, run_root=run_root,
            review_boards=review_boards, edge_pair=expected_edges[edge_id],
            continuity_calibrations=continuity_calibrations,
            source_manifest_sha256=source_manifest_sha256,
        )
        edge_map[edge_id] = [compiled]; used_annotations.update(used)
    if used_annotations != set(bindings):
        raise ValueError("semantic evidence contains unused raw annotation files")
    return gate_map, edge_map, [bindings[key] for key in sorted(bindings)]


def merge_semantic(
    gates: list[dict[str, Any]], edges: list[dict[str, Any]], gate_map: dict[str, list[dict[str, Any]]], edge_map: dict[str, list[dict[str, Any]]],
) -> None:
    for group in gates:
        records = gate_map.get(group["gate_id"])
        if records:
            group["metric_records"] = [item for item in group["metric_records"] if item["comparator"] != "manual"] + records
            group["semantic_evidence_applied"] = True
            group["semantic_claim_status"] = "gate_specific_raw_algorithm_applied"
        group["status"] = derived_status(group["metric_records"])
    for group in edges:
        records = edge_map.get(group["edge_id"])
        if records:
            group["metric_records"] = [item for item in group["metric_records"] if item["comparator"] != "manual"] + records
            group["semantic_evidence_applied"] = True
            group["semantic_continuity_status"] = "shared_named_raw_edge_algorithm_applied"
        group["status"] = derived_status(group["metric_records"])


def build_receipt(
    run_root: Path, asset_qa_path: Path, coverage_path: Path, continuity_path: Path,
    semantic_evidence_path: Path | None, source_manifest_path: Path | None = None,
) -> dict[str, Any]:
    if source_manifest_path is None:
        source_manifest_path = resolve_run_file(
            run_root, "00_source/source_manifest.json", "source manifest",
        )
    asset_qa = load_json(asset_qa_path)
    coverage = load_json(coverage_path)
    continuity = load_json(continuity_path)
    source_manifest = load_json(source_manifest_path)
    for label, value in (
        ("asset_qa", asset_qa), ("coverage", coverage), ("continuity", continuity),
        ("source_manifest", source_manifest),
    ):
        reject_fixture_flags(value, label)
    product_features = observed_product_features(source_manifest)
    source_assets, coverage_views, required_gates = validate_input_relationships(
        asset_qa, coverage, continuity, source_manifest, product_features,
    )
    assets: list[dict[str, Any]] = []
    internals: dict[str, dict[str, Any]] = {}
    seen_paths, seen_hashes = set(), set()
    for source in sorted(source_assets, key=lambda item: item["view_id"]):
        view_id = source["view_id"]
        if not isinstance(source.get("asset_id"), str) or not source["asset_id"] or source.get("assistant_qa_status") != "passed":
            raise ValueError(f"{view_id}: approved asset ID/status invalid")
        path = resolve_run_file(run_root, source.get("file_path"), f"asset {view_id}")
        actual_hash = sha256_file(path)
        if source.get("file_sha256") != actual_hash or source["file_path"] in seen_paths or actual_hash in seen_hashes:
            raise ValueError(f"{view_id}: master path/hash must be valid and unique")
        if source.get("family") != coverage_views[view_id].get("family"):
            raise ValueError(f"{view_id}: family mismatch")
        seen_paths.add(source["file_path"]); seen_hashes.add(actual_hash)
        image_metrics, internal = image_statistics(path)
        assets.append({
            "asset_id": source["asset_id"], "view_id": view_id, "family": source["family"],
            "shot_scale": coverage_views[view_id].get("shot_scale"), "file_path": source["file_path"],
            "file_sha256": actual_hash, "image_metrics": image_metrics,
        })
        internals[view_id] = internal
    assets_by_view = {item["view_id"]: item for item in assets}
    review_boards: list[dict[str, Any]] = []
    boards = asset_qa.get("review_boards")
    if boards is not None and not isinstance(boards, list):
        raise ValueError("review_boards must be an array")
    for index, board in enumerate(boards or []):
        if not isinstance(board, dict):
            raise ValueError("review board must be an object")
        path = resolve_run_file(run_root, board.get("file_path"), f"review board {index}")
        if board.get("file_sha256") != sha256_file(path):
            raise ValueError(f"review board {index}: hash mismatch")
        board_metrics, _ = image_statistics(path)
        inputs = board.get("inputs")
        if not isinstance(inputs, list) or not inputs:
            raise ValueError(f"review board {index}: inputs missing")
        bound_inputs = []
        for item in inputs:
            asset = assets_by_view.get(item.get("view_id")) if isinstance(item, dict) else None
            if asset is None or any(item.get(key) != asset.get(key) for key in ("asset_id", "file_path", "file_sha256")):
                raise ValueError(f"review board {index}: input binding invalid")
            bound_inputs.append({key: asset[key] for key in ("asset_id", "view_id", "file_path", "file_sha256")})
        review_boards.append({
            "file_path": board["file_path"], "file_sha256": board["file_sha256"],
            "role": board.get("role"), "derivation_mode": board.get("derivation_mode"),
            "pixel_dimensions": board_metrics["pixel_dimensions"],
            "exact_horizontal_16_9": board_metrics["exact_horizontal_16_9"], "inputs": bound_inputs,
        })
    gates = base_gate_measurements(required_gates, assets)
    edges = base_edge_measurements(required_edge_pairs(coverage_views), assets_by_view, internals)
    annotation_bindings: list[dict[str, Any]] = []
    if semantic_evidence_path is not None:
        expected_locks = {
            "source_manifest_path": source_manifest_path.relative_to(run_root).as_posix(),
            "source_manifest_sha256": sha256_file(source_manifest_path),
            "asset_qa_path": asset_qa_path.relative_to(run_root).as_posix(), "asset_qa_sha256": sha256_file(asset_qa_path),
            "coverage_matrix_path": coverage_path.relative_to(run_root).as_posix(), "coverage_matrix_sha256": sha256_file(coverage_path),
            "continuity_contract_path": continuity_path.relative_to(run_root).as_posix(), "continuity_contract_sha256": sha256_file(continuity_path),
        }
        gate_map, edge_map, annotation_bindings = load_semantic_evidence(
            run_root, semantic_evidence_path, expected_locks, required_gates, edges, assets,
            coverage_views, review_boards,
            continuity.get("calibration_baselines")
            if isinstance(continuity.get("calibration_baselines"), dict) else {},
            sha256_file(source_manifest_path),
        )
        merge_semantic(gates, edges, gate_map, edge_map)
    receipt = {
        "schema_version": SCHEMA_VERSION, "tool_script_path": TOOL_SCRIPT_PATH,
        "tool_script_sha256": sha256_file(Path(__file__).resolve()), "receipt_sha256": None,
        "canonicalization": "utf8_sorted_keys_compact_no_nan_receipt_sha256_omitted",
        "authority_boundary": "deterministic_recomputation_from_locked_image_and_raw_annotation_bytes_not_standalone_product_truth",
        "runtime": {"python_version": sys.version.split()[0], "pillow_version": PIL.__version__},
        "input_locks": {
            "source_manifest_path": source_manifest_path.relative_to(run_root).as_posix(),
            "source_manifest_sha256": sha256_file(source_manifest_path),
            "asset_qa_path": asset_qa_path.relative_to(run_root).as_posix(), "asset_qa_sha256": sha256_file(asset_qa_path),
            "coverage_matrix_path": coverage_path.relative_to(run_root).as_posix(), "coverage_matrix_sha256": sha256_file(coverage_path),
            "continuity_contract_path": continuity_path.relative_to(run_root).as_posix(), "continuity_contract_sha256": sha256_file(continuity_path),
            "semantic_evidence_path": semantic_evidence_path.relative_to(run_root).as_posix() if semantic_evidence_path else None,
            "semantic_evidence_sha256": sha256_file(semantic_evidence_path) if semantic_evidence_path else None,
        },
        "measurement_configuration": {
            "sample_long_edge_px": SAMPLE_LONG_EDGE,
            "pair_sample_dimensions": {"width": PAIR_SAMPLE_SIZE[0], "height": PAIR_SAMPLE_SIZE[1]},
            "region_sample_dimensions": {"width": REGION_SAMPLE_SIZE[0], "height": REGION_SAMPLE_SIZE[1]},
            "resampling": "nearest_neighbor", "foreground_distance_threshold_rgb": FOREGROUND_DISTANCE_THRESHOLD,
            "component_graph_endpoint_snap_tolerance_normalized": GRAPH_ENDPOINT_SNAP_TOLERANCE,
            "gate_requirement_contract": "source_feature_derived_gate_specific_requirements_v2",
        },
        "observed_product_features": product_features,
        "derived_required_gates": sorted(derive_required_continuity_gates(product_features)),
        "assets": assets, "review_board_bindings": review_boards,
        "semantic_annotation_bindings": annotation_bindings,
        "gate_measurements": gates, "edge_measurements": edges,
    }
    receipt["receipt_sha256"] = canonical_receipt_hash(receipt)
    return receipt


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--asset-qa", default="07_qa/asset_qa.json")
    parser.add_argument("--source-manifest", default="00_source/source_manifest.json")
    parser.add_argument("--coverage", default="02_coverage/coverage_matrix.json")
    parser.add_argument("--continuity-contract", default="02_coverage/continuity_contract.json")
    parser.add_argument("--semantic-evidence", default=None)
    parser.add_argument("--output", default="07_qa/continuity_measurements.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        root = args.run_root.resolve()
        if not root.is_dir():
            raise ValueError("run root is not a directory")
        asset_qa = resolve_run_file(root, args.asset_qa, "asset_qa")
        source_manifest = resolve_run_file(root, args.source_manifest, "source manifest")
        coverage = resolve_run_file(root, args.coverage, "coverage")
        continuity = resolve_run_file(root, args.continuity_contract, "continuity contract")
        semantic = resolve_run_file(root, args.semantic_evidence, "semantic evidence") if args.semantic_evidence else None
        output = resolve_output(root, args.output)
        protected = {source_manifest, asset_qa, coverage, continuity, Path(__file__).resolve()}
        if semantic:
            protected.add(semantic)
        if output in protected:
            raise ValueError("output cannot overwrite an input/tool")
        receipt = build_receipt(root, asset_qa, coverage, continuity, semantic, source_manifest)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        os.replace(temporary, output)
        reread = load_json(output)
        if reread.get("receipt_sha256") != canonical_receipt_hash(reread):
            raise ValueError("written receipt self-hash replay failed")
        print(json.dumps({
            "status": "PASS", "output": output.relative_to(root).as_posix(),
            "receipt_sha256": reread["receipt_sha256"], "asset_count": len(reread["assets"]),
            "gate_count": len(reread["gate_measurements"]), "edge_count": len(reread["edge_measurements"]),
            "blocked_gate_ids": [item["gate_id"] for item in reread["gate_measurements"] if item["status"] == "blocked"],
            "failed_gate_ids": [item["gate_id"] for item in reread["gate_measurements"] if item["status"] == "failed"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
