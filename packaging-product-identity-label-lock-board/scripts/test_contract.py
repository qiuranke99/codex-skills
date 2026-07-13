#!/usr/bin/env python3
"""Production-shaped positive and adversarial tests for packaging contract v3."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageDraw

from validate_packaging_run import (
    ALL_CONTINUITY_GATES,
    CANONICAL_FEATURES,
    canonical_hash,
    derive_dynamic_region_detail_specs,
    dynamic_region_detail_view_id,
    derive_required_continuity_gates,
    derive_minimum_rotation_profile,
    sha256_file,
    validate_continuity,
    validate_code_decode_receipt,
    validate_codes,
    validate_graphics,
    validate_dynamic_region_pixel_contract,
    validate_ocr,
    validate_region_authority_modalities,
    validate_sources,
    validate_run,
)
import run_post_composite_verification as post_adapter
import build_continuity_measurements as continuity_builder
import validate_template_contract as template_contract


SKILL_DIR = Path(__file__).resolve().parents[1]
PROFILES = json.loads(
    (SKILL_DIR / "references/view_coverage_profiles.json").read_text(encoding="utf-8")
)
STATE_ID = "STATE_CLOSED_001"
PRODUCT_ID = "PRODUCT_CONTRACT_ACCEPTANCE"
EXACT_TEXT_LINES = [
    "EXAMPLE LAB 7Q4",
    "TEST BOTANICAL OIL",
    "测试净含量:500ml",
]
EXACT_TEXT = "\n".join(EXACT_TEXT_LINES)
FIELD_ID = "FIELD_FRONT_HERO"
GRAPHIC_ID = "LOGO_EXAMPLE_LAB_7Q4"
REGION_ID = "REGION_FRONT_LABEL"
BACK_FIELD_ID = "FIELD_BACK_COMPLIANCE"
BACK_REGION_ID = "REGION_BACK_LABEL"
EAN_CODE_ID = "CODE_BACK_EAN13"
QR_CODE_ID = "CODE_BACK_QR"
EAN_REGION_ID = "REGION_BACK_EAN13"
QR_REGION_ID = "REGION_BACK_QR"
EAN_PAYLOAD = "2901234567896"
QR_PAYLOAD = "https://product.example.invalid/example-lab-7q4/test-oil"
BACK_EXACT_TEXT_LINES = [
    "EXAMPLE LAB 7Q4 TEST OIL",
    "Demonstration ingredients",
    "Test net content: 500ml",
]
BACK_EXACT_TEXT = "\n".join(BACK_EXACT_TEXT_LINES)
DEFAULT_PRODUCT_FEATURES: list[str] = ["simple_near_rotational_symmetry", "low_copy_risk"]
BATH_OIL_PRODUCT_FEATURES = {
    "transparent_or_translucent", "liquid_or_gel", "pump_or_spray",
    "embossing_or_debossing", "visible_fill_line_or_liquid_boundary",
    "visible_dip_tube", "flat_or_rectangular_body", "non_symmetric_closure",
    "high_material_risk", "ordinary_label_heavy_packaging",
}
MATERIAL_REFERENCE_POLYGON = [
    [0.40, 0.22], [0.46, 0.22], [0.46, 0.28], [0.40, 0.28],
]
SOURCE_SIZE = (512, 288)
MASTER_SIZE = (1280, 720)


def scale_master_box(box: list[int]) -> list[int]:
    """Map a 512x288 fixture box onto the HD machine-master canvas."""
    return [
        round(box[0] * MASTER_SIZE[0] / SOURCE_SIZE[0]),
        round(box[1] * MASTER_SIZE[1] / SOURCE_SIZE[1]),
        round(box[2] * MASTER_SIZE[0] / SOURCE_SIZE[0]),
        round(box[3] * MASTER_SIZE[1] / SOURCE_SIZE[1]),
    ]


def silhouette_polygon_for_ring_index(index: int, ring_size: int = 8) -> list[list[float]]:
    # Front/back are wider than side views; this intentionally proves that
    # correct pose-conditioned projection is not a cross-view area constant.
    angle = 2 * math.pi * index / ring_size
    width = 0.18 + 0.12 * abs(math.cos(angle))
    left, right = 0.5 - width / 2, 0.5 + width / 2
    return [[left, 0.15], [right, 0.15], [right, 0.85], [left, 0.85]]


def edge_anchor_points_for_ring_index(index: int, ring_size: int = 8) -> dict[str, list[float]]:
    angle = 2 * math.pi * index / ring_size
    return {
        "EDGE_CONTINUITY_ANCHOR_A": [
            round(0.50 + 0.10 * math.cos(angle), 12),
            round(0.38 + 0.05 * math.sin(angle), 12),
        ],
        "EDGE_CONTINUITY_ANCHOR_B": [
            round(0.50 + 0.08 * math.cos(angle), 12),
            round(0.62 + 0.04 * math.sin(angle), 12),
        ],
    }


def edge_calibration_by_edge(ring_views: list[str]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for index, from_view in enumerate(ring_views):
        to_index = (index + 1) % len(ring_views)
        to_view = ring_views[to_index]
        left = edge_anchor_points_for_ring_index(index, len(ring_views))
        right = edge_anchor_points_for_ring_index(to_index, len(ring_views))
        output[f"{from_view}__TO__{to_view}"] = {
            "from_view_id": from_view,
            "to_view_id": to_view,
            "landmark_vectors": {
                landmark_id: [
                    round(right[landmark_id][0] - coordinates[0], 12),
                    round(right[landmark_id][1] - coordinates[1], 12),
                ]
                for landmark_id, coordinates in left.items()
            },
        }
    return output


def label_surface_frame(view_id: str) -> dict[str, list[float]]:
    if view_id == "ROT_0000":
        return {
            "LABEL_FRAME_ORIGIN": [0.25, 0.35],
            "LABEL_FRAME_X": [0.75, 0.35],
            "LABEL_FRAME_Y": [0.25, 0.85],
        }
    return {
        "LABEL_FRAME_ORIGIN": [0.35, 0.30],
        "LABEL_FRAME_X": [0.65, 0.30],
        "LABEL_FRAME_Y": [0.35, 0.80],
    }


def frame_point(frame: dict[str, list[float]], local: tuple[float, float]) -> list[float]:
    origin, x_axis, y_axis = (
        frame["LABEL_FRAME_ORIGIN"], frame["LABEL_FRAME_X"], frame["LABEL_FRAME_Y"]
    )
    return [
        origin[0] + local[0] * (x_axis[0] - origin[0]) + local[1] * (y_axis[0] - origin[0]),
        origin[1] + local[0] * (x_axis[1] - origin[1]) + local[1] * (y_axis[1] - origin[1]),
    ]


def label_polygon_for_view(view_id: str) -> list[list[float]]:
    frame = label_surface_frame(view_id)
    return [frame_point(frame, point) for point in ((0.20, 0.40), (0.80, 0.40), (0.80, 0.80), (0.20, 0.80))]


def nozzle_frame_and_vector_points(view_id: str) -> dict[str, list[float]]:
    if view_id == "ROT_0000":
        origin, x_axis, y_axis = [0.40, 0.14], [0.60, 0.14], [0.40, 0.34]
    else:
        origin, x_axis, y_axis = [0.44, 0.13], [0.57, 0.17], [0.41, 0.33]
    def local(a: float, b: float) -> list[float]:
        return [
            origin[0] + a * (x_axis[0] - origin[0]) + b * (y_axis[0] - origin[0]),
            origin[1] + a * (x_axis[1] - origin[1]) + b * (y_axis[1] - origin[1]),
        ]
    return {
        "NOZZLE_FRAME_ORIGIN": origin,
        "NOZZLE_FRAME_X": x_axis,
        "NOZZLE_FRAME_Y": y_axis,
        "NOZZLE_BASE": local(0.45, 0.50),
        "NOZZLE_TIP": local(0.95, 0.50),
    }


def reviewed_feature_classification(present_features: list[str] | set[str]) -> list[dict[str, Any]]:
    present = set(present_features)
    return [{
        "feature_id": feature_id,
        "status": "present" if feature_id in present else "reviewed_absent",
        "evidence_source_ids": [SOURCE_BY_ROLE["front"]],
        "review_status": "reviewed",
        "reviewer_id": "QA_REVIEWER_01",
        "evidence_note": (
            "Feature is directly visible in the reviewed authoritative source set."
            if feature_id in present
            else "Feature was checked across the authoritative source set and is absent from this product state."
        ),
    } for feature_id in sorted(CANONICAL_FEATURES)]
SURFACE_BY_ROLE = {
    "front": "SURFACE_FRONT",
    "right": "SURFACE_RIGHT",
    "back": "SURFACE_BACK",
    "left": "SURFACE_LEFT",
    "top": "SURFACE_TOP",
    "bottom": "SURFACE_BOTTOM",
}
SOURCE_BY_ROLE = {
    "front": "SRC_FRONT",
    "right": "SRC_RIGHT",
    "back": "SRC_BACK",
    "left": "SRC_LEFT",
    "top": "SRC_TOP",
    "bottom": "SRC_BOTTOM",
}
SOURCE_BY_VIEW_ID = {
    "ROT_0000": SOURCE_BY_ROLE["front"],
    "ROT_0900": SOURCE_BY_ROLE["right"],
    "ROT_1800": SOURCE_BY_ROLE["back"],
    "ROT_2700": SOURCE_BY_ROLE["left"],
    "TOP_0000": SOURCE_BY_ROLE["top"],
    "BOTTOM_0000": SOURCE_BY_ROLE["bottom"],
}
def continuity_raw_landmark_ids(product_features: list[str] | set[str]) -> list[str]:
    return sorted({
        landmark_id
        for requirement in [
            *(continuity_builder.GATE_REQUIREMENTS[gate_id]
              for gate_id in sorted(derive_required_continuity_gates(product_features))),
            continuity_builder.EDGE_REQUIREMENT,
        ]
        for landmark_id in (
            requirement.get("landmark_ids", [])
            + requirement.get("frame_landmark_ids", [])
            + requirement.get("node_landmark_ids", [])
            + [item for pair in requirement.get("landmark_pairs", []) for item in pair]
            + (requirement.get("structure_ids", []) if requirement.get("structure_type") == "landmarks" else [])
        )
    })


CONTINUITY_RAW_LANDMARK_IDS = continuity_raw_landmark_ids(DEFAULT_PRODUCT_FEATURES)
_PROMPT_COMPILER_TEST_MODULE: Any | None = None


def prompt_compiler_for_test() -> Any:
    global _PROMPT_COMPILER_TEST_MODULE
    if _PROMPT_COMPILER_TEST_MODULE is not None:
        return _PROMPT_COMPILER_TEST_MODULE
    path = SKILL_DIR / "scripts/compile_generation_prompts.py"
    spec = importlib.util.spec_from_file_location("_packaging_prompt_compiler_test", path)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load packaging prompt compiler for contract test")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _PROMPT_COMPILER_TEST_MODULE = module
    return module


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_image(
    path: Path,
    color: tuple[int, int, int],
    size: tuple[int, int] = (512, 288),
    *,
    label_patch: bool = False,
    back_code_patch: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", size, color)
    if label_patch:
        draw = ImageDraw.Draw(image)
        draw.rectangle((128, 72, 255, 143), fill=(238, 118, 58))
        draw.rectangle((136, 80, 247, 135), outline=(255, 242, 220), width=3)
        draw.line((142, 94, 240, 94), fill=(255, 255, 255), width=2)
        draw.line((142, 108, 232, 108), fill=(255, 255, 255), width=2)
        draw.line((142, 122, 210, 122), fill=(255, 255, 255), width=2)
    if back_code_patch:
        draw = ImageDraw.Draw(image)
        draw.rectangle((128, 72, 383, 223), fill=(244, 236, 220), outline=(80, 60, 45), width=2)
        draw.line((144, 88, 350, 88), fill=(45, 35, 30), width=3)
        draw.line((144, 104, 332, 104), fill=(45, 35, 30), width=2)
        draw.line((144, 120, 306, 120), fill=(45, 35, 30), width=2)
        draw.rectangle((250, 150, 359, 189), fill=(255, 255, 255), outline=(0, 0, 0), width=1)
        for offset in range(0, 104, 4):
            width = 1 if offset % 12 else 2
            draw.rectangle((253 + offset, 153, 253 + offset + width, 186), fill=(0, 0, 0))
        draw.rectangle((140, 150, 209, 219), fill=(255, 255, 255), outline=(0, 0, 0), width=1)
        for row in range(11):
            for column in range(11):
                if (row * 3 + column * 5 + row * column) % 7 < 3:
                    left = 143 + column * 6
                    top = 153 + row * 6
                    draw.rectangle((left, top, left + 4, top + 4), fill=(0, 0, 0))
    image.save(path, format="PNG", optimize=False)


def make_master_image(seed: int) -> Image.Image:
    """Build the deterministic product-like image used by frozen test baselines."""
    background = (
        (seed * 37) % 180 + 30,
        (seed * 53) % 180 + 30,
        (seed * 71) % 180 + 30,
    )
    image = Image.new("RGB", SOURCE_SIZE, background)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (176, 34, 336, 262), radius=28,
        fill=((seed * 19) % 155 + 70, (seed * 29) % 155 + 70, (seed * 43) % 155 + 70),
        outline=(245, 245, 245), width=4,
    )
    draw.rectangle((218, 18, 294, 52), fill=(225, 225, 220), outline=(55, 55, 55), width=2)
    draw.ellipse((236, 4, 278, 30), fill=(250, 250, 245), outline=(70, 70, 70), width=2)
    for band in range(8):
        x0 = 188 + band * 17
        draw.rectangle(
            (x0, 78, x0 + 12, 230),
            fill=((seed * 11 + band * 23) % 256, (seed * 17 + band * 31) % 256, (seed * 23 + band * 41) % 256),
        )
    draw.line((176, 194, 336, 194), fill=(255, 255, 255), width=3)
    return image.resize(MASTER_SIZE, Image.Resampling.NEAREST)


def expected_material_luma(seed: int) -> float:
    image = make_master_image(seed).resize(
        continuity_builder.REGION_SAMPLE_SIZE, Image.Resampling.NEAREST,
    )
    gray = continuity_builder.grayscale(image)
    mask = continuity_builder.polygon_mask(
        [(float(x), float(y)) for x, y in MATERIAL_REFERENCE_POLYGON]
    )
    selected = [pixel for pixel, include in zip(gray, mask.getdata()) if include]
    return round(sum(selected) / len(selected) / 255, 12)


def expected_showthrough_luma_std(seed: int) -> float:
    image = make_master_image(seed).resize(
        continuity_builder.REGION_SAMPLE_SIZE, Image.Resampling.NEAREST,
    )
    gray = continuity_builder.grayscale(image)
    mask = continuity_builder.polygon_mask(
        [(float(x), float(y)) for x, y in MATERIAL_REFERENCE_POLYGON]
    )
    selected = [pixel / 255 for pixel, include in zip(gray, mask.getdata()) if include]
    mean = sum(selected) / len(selected)
    return round(math.sqrt(sum((item - mean) ** 2 for item in selected) / len(selected)), 12)


def write_master_image(path: Path, seed: int) -> None:
    """Write a unique, non-uniform 16:9 product-like evidence image."""
    path.parent.mkdir(parents=True, exist_ok=True)
    image = make_master_image(seed)
    image.save(path, format="PNG", optimize=False)


def crop_source(source: Path, crop: Path, box: tuple[int, int, int, int]) -> None:
    crop.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image.convert("RGB").crop(box).save(crop, format="PNG", optimize=False)


def run_command(command: list[str], label: str) -> dict[str, Any]:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(f"{label} failed:\n{result.stdout}\n{result.stderr}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{label} returned invalid JSON: {result.stdout}") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"{label} returned a non-object JSON payload")
    return payload


def required_view_ids(
    rotation_profile: str = "R8",
    product_features: list[str] | set[str] = DEFAULT_PRODUCT_FEATURES,
    *,
    include_codes: bool = False,
    elevation_rings: list[dict[str, Any]] | None = None,
) -> list[str]:
    view_ids = list(PROFILES["rotation_profiles"][rotation_profile]["view_ids"])
    view_ids.extend(item["view_id"] for item in PROFILES["base_elevation_views"])
    view_ids.extend(item["view_id"] for item in PROFILES["base_close_views"])
    view_ids.extend(PROFILES["base_detail_views"])
    for feature_id in sorted(set(product_features)):
        view_ids.extend(PROFILES["feature_detail_requirements"].get(feature_id, []))
    dynamic_specs = fixture_dynamic_region_specs(include_codes)
    view_ids.extend(dynamic_specs)
    for ring in elevation_rings or []:
        view_ids.extend(ring.get("view_ids") or [])
    return list(dict.fromkeys(view_ids))


def fixture_dynamic_region_specs(include_codes: bool) -> dict[str, dict[str, Any]]:
    text_fields = {
        FIELD_ID: {"region_id": REGION_ID, "surface_id": SURFACE_BY_ROLE["front"]},
    }
    code_records: dict[str, dict[str, Any]] = {}
    graphic_records = {
        GRAPHIC_ID: {"region_id": REGION_ID, "surface_id": SURFACE_BY_ROLE["front"]},
    }
    if include_codes:
        text_fields[BACK_FIELD_ID] = {
            "region_id": BACK_REGION_ID, "surface_id": SURFACE_BY_ROLE["back"],
        }
        code_records = {
            EAN_CODE_ID: {"region_id": EAN_REGION_ID, "surface_id": SURFACE_BY_ROLE["back"]},
            QR_CODE_ID: {"region_id": QR_REGION_ID, "surface_id": SURFACE_BY_ROLE["back"]},
        }
    return derive_dynamic_region_detail_specs(
        text_fields, code_records, graphic_records, [],
    )


def full_elevation_ring(
    prefix: str, rotation_profile: str, elevation_deg: float,
) -> dict[str, Any]:
    return {
        "ring_id": f"{prefix}_{rotation_profile}_FULL_RING",
        "view_prefix": prefix,
        "elevation_deg": elevation_deg,
        "view_ids": [
            view_id.replace("ROT_", f"{prefix}_")
            for view_id in PROFILES["rotation_profiles"][rotation_profile]["view_ids"]
        ],
        "loop_closure_required": True,
    }


def horizontal_roles(azimuth: float) -> list[str]:
    angle = azimuth % 360.0
    if angle == 0:
        return ["front"]
    if angle == 90:
        return ["right"]
    if angle == 180:
        return ["back"]
    if angle == 270:
        return ["left"]
    if 0 < angle < 90:
        return ["front", "right"]
    if 90 < angle < 180:
        return ["right", "back"]
    if 180 < angle < 270:
        return ["back", "left"]
    return ["left", "front"]


def detail_role(view_id: str) -> str:
    frozen_spec = PROFILES.get("fixed_detail_specs", {}).get(view_id)
    if isinstance(frozen_spec, dict) and frozen_spec.get("target_surface_role") in SURFACE_BY_ROLE:
        return str(frozen_spec["target_surface_role"])
    if any(token in view_id for token in ("TRUE_BOTTOM", "BASE_EDGE", "BOTTOM_FLAP", "BOTTOM_GUSSET", "TAIL_CRIMP")):
        return "bottom"
    if any(token in view_id for token in ("CLOSURE_FRONT", "CLOSURE_TOP", "NOZZLE_APERTURE", "ACTUATOR_STEM", "NECK_COLLAR", "TOP_FLAP", "CAP_AND_NOZZLE")):
        return "top"
    if any(token in view_id for token in ("BACK", "BARCODE_QR_CERTIFICATION", "GLUE_SEAM", "REAR_SHOWTHROUGH")):
        return "back"
    if any(token in view_id for token in ("LEFT", "LEFT_GUSSET")):
        return "left"
    if any(token in view_id for token in ("RIGHT", "SIDE", "RIGHT_GUSSET", "WRAP_CONTINUITY")):
        return "right"
    return "front"


def component_ids_for_role(
    role: str, product_features: list[str] | set[str] = DEFAULT_PRODUCT_FEATURES,
) -> list[str]:
    values = ["BODY"]
    values.extend(
        view_id.removeprefix("DETAIL_")
        for view_id in PROFILES["base_detail_views"]
        if detail_role(view_id) == role
    )
    for feature_id in sorted(set(product_features)):
        values.extend(
            view_id.removeprefix("DETAIL_")
            for view_id in PROFILES["feature_detail_requirements"].get(feature_id, [])
            if detail_role(view_id) == role
        )
    return list(dict.fromkeys(values))


def all_component_ids(
    product_features: list[str] | set[str] = DEFAULT_PRODUCT_FEATURES,
) -> list[str]:
    values = ["BODY"]
    values.extend(view_id.removeprefix("DETAIL_") for view_id in PROFILES["base_detail_views"])
    for feature_id in sorted(set(product_features)):
        values.extend(
            view_id.removeprefix("DETAIL_")
            for view_id in PROFILES["feature_detail_requirements"].get(feature_id, [])
        )
    return list(dict.fromkeys(values))


def material_feature_ids(
    product_features: list[str] | set[str] = DEFAULT_PRODUCT_FEATURES,
) -> list[str]:
    features = set(product_features)
    values = ["MATERIAL_LABEL_STOCK"]
    values.append(
        "MATERIAL_TRANSPARENT_BODY"
        if "transparent_or_translucent" in features
        else "MATERIAL_OPAQUE_POLYMER"
    )
    if "liquid_or_gel" in features:
        values.append("MATERIAL_LIQUID_CONTENT")
    if "pump_or_spray" in features:
        values.append("MATERIAL_PUMP_COLLAR")
    if "foil_or_reflective_print" in features:
        values.append("MATERIAL_REFLECTIVE_PRINT")
    return values


def is_copy_detail(view_id: str) -> bool:
    return any(
        token in view_id
        for token in ("LABEL", "LOGO", "CAPACITY", "BATCH", "BARCODE", "CERTIFICATION")
    )


def make_view(
    view_id: str,
    rotation_profile: str = "R8",
    product_features: list[str] | set[str] = DEFAULT_PRODUCT_FEATURES,
    *,
    include_codes: bool = False,
    elevation_rings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    neutral_ring = PROFILES["rotation_profiles"][rotation_profile]["view_ids"]
    base_elevations = {item["view_id"]: item for item in PROFILES["base_elevation_views"]}
    base_close = {item["view_id"]: item for item in PROFILES["base_close_views"]}
    fixed_detail_specs = PROFILES["fixed_detail_specs"]
    dynamic_detail_specs = fixture_dynamic_region_specs(include_codes)
    ring_by_view: dict[str, dict[str, Any]] = {}
    for ring in elevation_rings or []:
        for ring_view_id in ring.get("view_ids") or []:
            ring_by_view[ring_view_id] = ring

    def direct_cardinal_parents(azimuth_value: float) -> list[str]:
        normalized = azimuth_value % 360.0
        cardinal_id = f"ROT_{int(normalized * 10):04d}"
        if cardinal_id in {"ROT_0000", "ROT_0900", "ROT_1800", "ROT_2700"}:
            return [cardinal_id]
        pairs = [
            (0.0, 90.0, ["ROT_0000", "ROT_0900"]),
            (90.0, 180.0, ["ROT_0900", "ROT_1800"]),
            (180.0, 270.0, ["ROT_1800", "ROT_2700"]),
            (270.0, 360.0, ["ROT_2700", "ROT_0000"]),
        ]
        return next(pair for lower, upper, pair in pairs if lower < normalized < upper)

    detail_parents = {
        "front": ["ROT_0000", "ROT_0900"],
        "right": ["ROT_0900", "ROT_0000"],
        "back": ["ROT_1800", "ROT_0900"],
        "left": ["ROT_2700", "ROT_1800"],
        "top": ["TOP_0000", "ROT_0000"],
        "bottom": ["BOTTOM_0000", "ROT_1800"],
    }
    parents: list[str] = []
    previous: str | None = None
    next_view: str | None = None
    derivation = "source"
    framing_contract: str | None = None
    focus_contract: str | None = None
    dynamic_region_contract: dict[str, Any] | None = None
    if view_id.startswith("ROT_"):
        azimuth = int(view_id.split("_")[1]) / 10.0
        elevation = 0.0
        family = "neutral_ring"
        shot_scale = "full_product"
        ring_index = neutral_ring.index(view_id)
        previous = neutral_ring[ring_index - 1]
        next_view = neutral_ring[(ring_index + 1) % len(neutral_ring)]
        roles = horizontal_roles(azimuth)
        if view_id not in {"ROT_0000", "ROT_0900", "ROT_1800", "ROT_2700"}:
            derivation = "generated"
            parents = direct_cardinal_parents(azimuth)
        review_board_role = "neutral_rotation"
    elif view_id in base_elevations or view_id in ring_by_view:
        if view_id in ring_by_view:
            azimuth = int(view_id.split("_")[1]) / 10.0
            elevation = float(ring_by_view[view_id]["elevation_deg"])
        else:
            spec = base_elevations[view_id]
            azimuth = float(spec["azimuth_deg"])
            elevation = float(spec["elevation_deg"])
        shot_scale = "full_product"
        if view_id.startswith("HIGH_"):
            family = "high_angle"
            roles = horizontal_roles(azimuth) + ["top"]
            derivation = "generated"
            parents = [*direct_cardinal_parents(azimuth), "TOP_0000"]
        elif view_id.startswith("LOW_"):
            family = "low_angle"
            roles = horizontal_roles(azimuth) + ["bottom"]
            derivation = "generated"
            parents = [*direct_cardinal_parents(azimuth), "BOTTOM_0000"]
        elif view_id == "TOP_0000":
            family = "top_bottom"
            roles = ["top"]
        else:
            family = "top_bottom"
            roles = ["bottom"]
        if view_id in ring_by_view:
            ring_ids = ring_by_view[view_id]["view_ids"]
            ring_index = ring_ids.index(view_id)
            previous = ring_ids[ring_index - 1]
            next_view = ring_ids[(ring_index + 1) % len(ring_ids)]
        review_board_role = "elevation"
    elif view_id in base_close:
        spec = base_close[view_id]
        azimuth = float(spec["azimuth_deg"])
        elevation = float(spec["elevation_deg"])
        family = spec["family"]
        shot_scale = spec["shot_scale"]
        roles = [spec["target_surface_role"]]
        derivation = "generated"
        parents = detail_parents[roles[0]]
        framing_contract = spec["framing_contract"]
        review_board_role = spec["review_board_role"]
    else:
        spec = fixed_detail_specs.get(view_id) or dynamic_detail_specs[view_id]
        if view_id in dynamic_detail_specs:
            surface_role_by_id = {value: key for key, value in SURFACE_BY_ROLE.items()}
            detail_surface_role = surface_role_by_id[spec["surface_id"]]
            pose_by_role = {
                "front": (0.0, 0.0), "right": (90.0, 0.0),
                "back": (180.0, 0.0), "left": (270.0, 0.0),
                "top": (0.0, 90.0), "bottom": (0.0, -90.0),
            }
            azimuth, elevation = pose_by_role[detail_surface_role]
            dynamic_region_contract = {
                key: spec[key] for key in (
                    "region_id", "surface_id", "field_ids", "code_ids", "graphic_ids",
                    "native_region_pixel_contract",
                )
            }
        else:
            detail_surface_role = spec["target_surface_role"]
            azimuth = float(spec["azimuth_deg"])
            elevation = float(spec["elevation_deg"])
        family = spec["family"]
        shot_scale = spec["shot_scale"]
        roles = [detail_surface_role]
        derivation = "generated"
        parents = detail_parents[detail_surface_role]
        framing_contract = spec["framing_contract"]
        focus_contract = spec["focus_contract"]
        review_board_role = spec["review_board_role"]

    visible_surfaces = [SURFACE_BY_ROLE[role] for role in dict.fromkeys(roles)]
    if shot_scale in {"full_product", "upper_half_close", "lower_half_close"}:
        visible_component_ids = list(dict.fromkeys(
            component_id for role in dict.fromkeys(roles)
            for component_id in component_ids_for_role(role, product_features)
        ))
    elif view_id in fixed_detail_specs:
        visible_component_ids = [view_id.removeprefix("DETAIL_")]
    else:
        visible_component_ids = component_ids_for_role(roles[0], product_features)
    source_refs = [SOURCE_BY_ROLE[role] for role in dict.fromkeys(roles)]
    if derivation == "generated":
        source_refs = list(dict.fromkeys(SOURCE_BY_VIEW_ID[parent_id] for parent_id in parents))
    surface_view = shot_scale in {"full_product", "upper_half_close", "lower_half_close"}
    front_copy_detail_ids = {
        "DETAIL_FRONT_LABEL", "DETAIL_LOGO_HERO_COPY", "DETAIL_CAPACITY_AND_SPEC",
    }
    has_front_copy = (surface_view and "front" in roles) or view_id in front_copy_detail_ids
    has_back_label = include_codes and (
        (surface_view and "back" in roles)
        or view_id == "DETAIL_BACK_LABEL"
    )
    has_back_codes = include_codes and (
        (surface_view and "back" in roles)
        or view_id == "DETAIL_BARCODE_QR_CERTIFICATION"
    )
    has_exact_content = has_front_copy or has_back_label or has_back_codes
    label_region_ids = []
    ocr_field_ids_visible = []
    code_ids_visible = []
    graphic_ids_visible = []
    if has_front_copy:
        label_region_ids.append(REGION_ID)
        ocr_field_ids_visible.append(FIELD_ID)
        graphic_ids_visible.append(GRAPHIC_ID)
    if has_back_label:
        label_region_ids.append(BACK_REGION_ID)
        ocr_field_ids_visible.append(BACK_FIELD_ID)
    if has_back_codes:
        label_region_ids.extend([EAN_REGION_ID, QR_REGION_ID])
        code_ids_visible.extend([EAN_CODE_ID, QR_CODE_ID])
    dynamic_spec = dynamic_detail_specs.get(view_id)
    if dynamic_spec is not None:
        label_region_ids = [dynamic_spec["region_id"]]
        ocr_field_ids_visible = dynamic_spec["field_ids"]
        code_ids_visible = dynamic_spec["code_ids"]
        graphic_ids_visible = dynamic_spec["graphic_ids"]
        has_exact_content = True
    else:
        has_exact_content = bool(ocr_field_ids_visible or code_ids_visible or graphic_ids_visible)
    generated = derivation == "generated"
    view: dict[str, Any] = {
        "asset_id": f"ASSET_{view_id}",
        "view_id": view_id,
        "family": family,
        "review_board_role": review_board_role,
        "azimuth_deg": azimuth,
        "elevation_deg": elevation,
        "roll_deg": 0.0,
        "shot_scale": shot_scale,
        "lens_profile": "CALIBRATED_70MM_EQUIVALENT",
        "camera_distance_profile": "LOCKED_OCCUPANCY_72_PERCENT",
        "product_state_id": STATE_ID,
        "visible_surface_ids": visible_surfaces,
        "visible_component_ids": visible_component_ids,
        "occluded_surface_ids": [
            surface for surface in SURFACE_BY_ROLE.values() if surface not in visible_surfaces
        ],
        "geometry_landmark_ids": [
            "LANDMARK_BODY_OUTLINE", "LANDMARK_VERTICAL_AXIS",
            *continuity_raw_landmark_ids(product_features),
        ],
        "label_region_ids": label_region_ids,
        "ocr_field_ids_visible": ocr_field_ids_visible,
        "code_ids_visible": code_ids_visible,
        "graphic_ids_visible": graphic_ids_visible,
        "material_feature_ids": material_feature_ids(product_features),
        "pose_source_status": "inferred_from_sources" if generated else "source_verified",
        "surface_source_status": "inferred_from_sources" if generated else "source_verified",
        "copy_source_status": (
            "inferred_from_sources"
            if generated and has_exact_content
            else "source_verified"
            if has_exact_content
            else "not_applicable_no_visible_content"
        ),
        "material_source_status": "inferred_from_sources" if generated else "source_verified",
        "derivation_status": derivation,
        "source_refs": source_refs,
        "parent_anchor_view_ids": parents,
        "previous_view_id": previous,
        "next_view_id": next_view,
        "required": True,
        "production_authority": "validator_derived",
    }
    if framing_contract is not None:
        view["framing_contract"] = framing_contract
    if dynamic_region_contract is not None:
        view["dynamic_region_contract"] = dynamic_region_contract
    if view_id in fixed_detail_specs or view_id in dynamic_detail_specs:
        target_components = (
            [view_id.removeprefix("DETAIL_")]
            if view_id in fixed_detail_specs else visible_component_ids
        )
        required_evidence_ids = [
            *ocr_field_ids_visible, *code_ids_visible, *graphic_ids_visible,
        ]
        if view_id in fixed_detail_specs:
            required_evidence_ids.insert(0, view_id.removeprefix("DETAIL_"))
        view["detail_job"] = {
            "detail_id": view_id,
            "target_surface_ids": visible_surfaces,
            "target_component_ids": target_components,
            "required_evidence_ids": required_evidence_ids,
            "framing_contract": framing_contract,
            "focus_contract": focus_contract,
        }
    return view


def exact_text_field(authority_path: str, authority_sha: str) -> dict[str, Any]:
    return {
        "field_id": FIELD_ID,
        "region_id": REGION_ID,
        "surface_id": SURFACE_BY_ROLE["front"],
        "field_class": "A_exact",
        "semantic_role": "hero_copy",
        "volatility": "static",
        "expected_raw_text": EXACT_TEXT,
        "expected_text_sha256": hashlib.sha256(EXACT_TEXT.encode("utf-8")).hexdigest(),
        "ocr_match_policy": "ordered_line_aggregation_exact",
        "line_joiner": "newline",
        "authority_source_ids": [SOURCE_BY_ROLE["front"]],
        "ocr_observation_ids": ["SRC_FRONT_REGION_TEXT_0001"],
        "engine_consensus_status": "exact_match",
        "human_review_status": "approved",
        "verification_basis": "ocr_exact_match",
        "authority_asset_path": authority_path,
        "authority_asset_sha256": authority_sha,
        "field_status": "verified",
        "visibility_mode": "direct",
        "showthrough_of_region_id": None,
        "render_policy": "deterministic_projected_artwork",
        "required_view_ids": [
            "ROT_0000", "DETAIL_FRONT_LABEL",
            dynamic_region_detail_view_id(REGION_ID),
        ],
    }


def back_exact_text_field(authority_path: str, authority_sha: str) -> dict[str, Any]:
    return {
        "field_id": BACK_FIELD_ID,
        "region_id": BACK_REGION_ID,
        "surface_id": SURFACE_BY_ROLE["back"],
        "field_class": "A_exact",
        "semantic_role": "compliance_copy",
        "volatility": "static",
        "expected_raw_text": BACK_EXACT_TEXT,
        "expected_text_sha256": hashlib.sha256(BACK_EXACT_TEXT.encode("utf-8")).hexdigest(),
        "ocr_match_policy": "ordered_line_aggregation_exact",
        "line_joiner": "newline",
        "authority_source_ids": [SOURCE_BY_ROLE["back"]],
        "ocr_observation_ids": ["SRC_BACK_REGION_TEXT_0001"],
        "engine_consensus_status": "exact_match",
        "human_review_status": "approved",
        "verification_basis": "ocr_exact_match",
        "authority_asset_path": authority_path,
        "authority_asset_sha256": authority_sha,
        "field_status": "verified",
        "visibility_mode": "direct",
        "showthrough_of_region_id": None,
        "render_policy": "deterministic_projected_artwork",
        "required_view_ids": [
            "ROT_1800", "DETAIL_BACK_LABEL",
            dynamic_region_detail_view_id(BACK_REGION_ID),
        ],
    }


def exact_source_layer_ids(view: dict[str, Any]) -> list[str]:
    layer_ids: list[str] = []
    if FIELD_ID in set(view.get("ocr_field_ids_visible") or []):
        layer_ids.append("LAYER_FRONT_EXACT")
    if BACK_FIELD_ID in set(view.get("ocr_field_ids_visible") or []):
        layer_ids.append("LAYER_BACK_TEXT_EXACT")
    if EAN_CODE_ID in set(view.get("code_ids_visible") or []):
        layer_ids.append("LAYER_BACK_EAN13_EXACT")
    if QR_CODE_ID in set(view.get("code_ids_visible") or []):
        layer_ids.append("LAYER_BACK_QR_EXACT")
    return layer_ids or ["LAYER_NEUTRAL_PATCH"]


def manifest_paths() -> dict[str, str]:
    return {
        "source_manifest": "00_source/source_manifest.json",
        "surface_inventory": "00_source/surface_inventory.json",
        "ocr_observations": "01_ocr/ocr_observations.json",
        "text_ssot": "01_ocr/exact_copy_text_ssot.json",
        "code_manifest": "01_ocr/code_manifest.json",
        "logo_graphic_manifest": "01_ocr/logo_graphic_manifest.json",
        "exact_copy_bundle": "01_ocr/exact_copy_bundle_manifest.json",
        "coverage_matrix": "02_coverage/coverage_matrix.json",
        "motion_envelope": "02_coverage/motion_envelope.json",
        "continuity_contract": "02_coverage/continuity_contract.json",
        "composition_plan": "03_composition/deterministic_composition_plan.json",
        "surface_texture_atlas": "03_composition/surface_texture_atlas.json",
        "protected_region_masks": "03_composition/protected_region_masks.json",
        "generation_prompt_index": "04_prompts/generation_prompt_index.json",
        "asset_qa": "07_qa/asset_qa.json",
        "continuity_qa": "07_qa/continuity_qa.json",
        "post_composite_verification": "07_qa/post_composite_verification.json",
    }


def relock(root: Path) -> None:
    manifest_path = root / "00_manifest/run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bundle_path = root / manifest["paths"]["exact_copy_bundle"]
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle_mapping = {
        "text_ssot_sha256": "text_ssot",
        "code_manifest_sha256": "code_manifest",
        "logo_graphic_manifest_sha256": "logo_graphic_manifest",
        "surface_texture_atlas_sha256": "surface_texture_atlas",
        "protected_region_masks_sha256": "protected_region_masks",
        "deterministic_composition_plan_sha256": "composition_plan",
    }
    for hash_key, path_key in bundle_mapping.items():
        bundle[hash_key] = sha256_file(root / manifest["paths"][path_key])
    bundle["exact_copy_bundle_sha256"] = canonical_hash(bundle, "exact_copy_bundle_sha256")
    write_json(bundle_path, bundle)

    file_hash_mapping = {
        "source_manifest_sha256": "source_manifest",
        "surface_inventory_sha256": "surface_inventory",
        "ocr_observations_sha256": "ocr_observations",
        "text_ssot_sha256": "text_ssot",
        "code_manifest_sha256": "code_manifest",
        "logo_graphic_manifest_sha256": "logo_graphic_manifest",
        "coverage_matrix_sha256": "coverage_matrix",
        "motion_envelope_sha256": "motion_envelope",
        "continuity_contract_sha256": "continuity_contract",
        "composition_plan_sha256": "composition_plan",
        "surface_texture_atlas_sha256": "surface_texture_atlas",
        "protected_region_masks_sha256": "protected_region_masks",
    }
    for hash_key, path_key in file_hash_mapping.items():
        manifest["hashes"][hash_key] = sha256_file(root / manifest["paths"][path_key])
    manifest["hashes"]["exact_copy_bundle_sha256"] = bundle["exact_copy_bundle_sha256"]
    manifest["hashes"]["exact_copy_bundle_file_sha256"] = sha256_file(bundle_path)
    for hash_key, path_key in (
        ("generation_prompt_index_sha256", "generation_prompt_index"),
        ("asset_qa_sha256", "asset_qa"),
        ("continuity_qa_sha256", "continuity_qa"),
        ("post_composite_verification_sha256", "post_composite_verification"),
    ):
        path = root / manifest["paths"][path_key]
        manifest["hashes"][hash_key] = sha256_file(path) if path.is_file() else None
    write_json(manifest_path, manifest)


def compile_prompts(root: Path) -> None:
    if sys.platform == "darwin":
        summary = run_command(
            [sys.executable, str(SKILL_DIR / "scripts/compile_generation_prompts.py"), str(root)],
            "generation prompt compiler",
        )
    else:
        # Cross-platform contract tests must exercise downstream validators with
        # a COMPLETE fixture, while the installed production CLI must remain
        # fail-closed without Darwin Vision. The override exists only inside
        # this test module and is never exposed by the production compiler.
        compiler = prompt_compiler_for_test()
        original = compiler.assert_final_post_composite_runtime_callable
        compiler.assert_final_post_composite_runtime_callable = lambda manifest: None
        try:
            summary = compiler.compile_run(root)
        finally:
            compiler.assert_final_post_composite_runtime_callable = original
    index_path = root / "04_prompts/generation_prompt_index.json"
    if summary.get("status") != "compiled" or not index_path.is_file():
        raise AssertionError("generation compiler did not publish its frozen index")
    manifest_path = root / "00_manifest/run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["hashes"]["generation_prompt_index_sha256"] = sha256_file(index_path)
    write_json(manifest_path, manifest)


def create_ready_run(
    root: Path,
    *,
    rotation_profile: str = "R8",
    product_features: list[str] | set[str] = DEFAULT_PRODUCT_FEATURES,
    include_codes: bool = False,
    motion_type: str = "neutral_height_full_spin",
    motion_scope: str = "neutral_height_full_360_rotation",
    elevation_rings: list[dict[str, Any]] | None = None,
) -> None:
    product_features = sorted(set(product_features))
    elevation_rings = list(elevation_rings or [])
    source_pose_by_role = {
        "front": ("ROT_0000", 0.0, 0.0),
        "right": ("ROT_0900", 90.0, 0.0),
        "back": ("ROT_1800", 180.0, 0.0),
        "left": ("ROT_2700", 270.0, 0.0),
        "top": ("TOP_0000", 0.0, 90.0),
        "bottom": ("BOTTOM_0000", 0.0, -90.0),
    }
    source_specs = [
        ("front", (220, 145, 70), True),
        ("right", (205, 130, 64), False),
        ("back", (190, 118, 58), False),
        ("left", (198, 124, 61), False),
        ("top", (230, 155, 78), False),
        ("bottom", (175, 105, 52), False),
    ]
    sources: list[dict[str, Any]] = []
    for role, color, label_patch in source_specs:
        source_id = SOURCE_BY_ROLE[role]
        surface_id = SURFACE_BY_ROLE[role]
        source_view_id, source_azimuth, source_elevation = source_pose_by_role[role]
        locator = f"00_source/{role}.png"
        path = root / locator
        write_image(
            path, color, label_patch=label_patch,
            back_code_patch=include_codes and role == "back",
        )
        sources.append({
            "source_id": source_id,
            "product_id": PRODUCT_ID,
            "product_state_id": STATE_ID,
            "file_path": locator,
            "file_sha256": sha256_file(path),
            "pixel_dimensions": {"width": 512, "height": 288},
            "source_kind": "direct_product_photograph",
            "source_authority": "authoritative",
            "required_for_run": True,
            "view_id": source_view_id,
            "azimuth_deg": source_azimuth,
            "elevation_deg": source_elevation,
            "visible_surfaces": [surface_id],
            "visible_component_ids": component_ids_for_role(role, product_features),
        })
    write_json(root / "00_source/source_manifest.json", {
        "schema_version": "packaging-source-manifest.v1",
        "product_id": PRODUCT_ID,
        "product_state_id": STATE_ID,
        "variant_resolution_status": "resolved_single_sku_and_instance",
        "product_feature_classification": reviewed_feature_classification(product_features),
        "sources": sources,
    })

    surface_records: list[dict[str, Any]] = []
    for role, surface_id in SURFACE_BY_ROLE.items():
        front = role == "front"
        back_exact = include_codes and role == "back"
        accounted = front or back_exact
        physical_layers = (
            ["front_label_opaque"] if front
            else ["back_wall", "back_label_opaque", "back_print_outer"] if back_exact
            else [f"{role}_wall"]
        )
        record: dict[str, Any] = {
            "surface_id": surface_id,
            "semantic_role": role,
            "physical_layer_ids": physical_layers,
            "coverage_status": "accounted" if accounted else "verified_no_copy",
            "text_detection_status": "text_detected" if accounted else "verified_no_copy",
            "source_refs": [SOURCE_BY_ROLE[role]],
            "region_ids": (
                [REGION_ID] if front
                else [BACK_REGION_ID, EAN_REGION_ID, QR_REGION_ID] if back_exact
                else []
            ),
            "required_copy_field_ids": (
                [FIELD_ID] if front else [BACK_FIELD_ID] if back_exact else []
            ),
            "required_code_ids": [EAN_CODE_ID, QR_CODE_ID] if back_exact else [],
            "required_graphic_ids": [GRAPHIC_ID] if front else [],
        }
        if not accounted:
            record.update({
                "no_copy_review_status": "reviewed",
                "no_copy_reviewer_id": "QA_REVIEWER_01",
                "no_copy_evidence_note": f"Direct {role} source reviewed after whole-product OCR; no native copy is present.",
            })
        surface_records.append(record)
    write_json(root / "00_source/surface_inventory.json", {
        "schema_version": "packaging-surface-inventory.v1",
        "required_surface_ids": list(SURFACE_BY_ROLE.values()),
        "surfaces": surface_records,
    })

    crop_box_normalized = {"x": 0.25, "y": 0.25, "width": 0.25, "height": 0.25}
    crop_locator = "00_source/front_label_rectified.png"
    crop_path = root / crop_locator
    crop_source(root / "00_source/front.png", crop_path, (128, 72, 256, 144))
    region_spec_locator = "01_ocr/front_region_spec.json"
    write_json(root / region_spec_locator, {
        "schema_version": "packaging-region-ocr-spec.v2",
        "source_id": SOURCE_BY_ROLE["front"],
        "regions": [{
            "region_id": REGION_ID,
            "surface_id": SURFACE_BY_ROLE["front"],
            "physical_layer_id": "front_label_opaque",
            "coordinate_origin": "top_left",
            "bounding_box_normalized": crop_box_normalized,
            "visibility_mode": "direct",
            "region_purpose": "mixed",
        }],
    })
    region_spec_sha = sha256_file(root / region_spec_locator)
    crop_receipt_locator = "01_ocr/front_region_crop_receipt.json"
    crop_receipt: dict[str, Any] = {
        "schema_version": "packaging-region-crop-receipt.v2",
        "source_id": SOURCE_BY_ROLE["front"],
        "source_path": "00_source/front.png",
        "source_file_sha256": sha256_file(root / "00_source/front.png"),
        "source_pixel_dimensions": {"width": 512, "height": 288},
        "region_id": REGION_ID,
        "surface_id": SURFACE_BY_ROLE["front"],
        "physical_layer_id": "front_label_opaque",
        "visibility_mode": "direct",
        "region_purpose": "mixed",
        "region_spec_path": region_spec_locator,
        "region_spec_sha256": region_spec_sha,
        "coordinate_origin": "top_left",
        "bounding_box_normalized": crop_box_normalized,
        "crop_box_px": [128, 72, 256, 144],
        "crop_method": "axis_aligned_normalized_bbox_v1",
        "rectifier_script_sha256": sha256_file(SKILL_DIR / "scripts/run_region_ocr.py"),
        "rectified_crop_path": crop_locator,
        "rectified_crop_sha256": sha256_file(crop_path),
        "receipt_sha256": None,
    }
    crop_receipt["receipt_sha256"] = canonical_hash(crop_receipt, "receipt_sha256")
    write_json(root / crop_receipt_locator, crop_receipt)

    back_region_spec_locator: str | None = None
    back_region_spec_sha: str | None = None
    back_crop_locators: dict[str, str] = {}
    back_crop_receipts: dict[str, tuple[str, dict[str, Any]]] = {}
    if include_codes:
        back_region_definitions = [
            {
                "region_id": BACK_REGION_ID,
                "surface_id": SURFACE_BY_ROLE["back"],
                "physical_layer_id": "back_label_opaque",
                "visibility_mode": "direct",
                "region_purpose": "text",
                "coordinate_origin": "top_left",
                "bounding_box_normalized": {
                    "x": 128 / 512, "y": 72 / 288,
                    "width": 256 / 512, "height": 72 / 288,
                },
                "crop_box_px": [128, 72, 384, 144],
                "crop_locator": "00_source/back_label_rectified.png",
            },
            {
                "region_id": EAN_REGION_ID,
                "surface_id": SURFACE_BY_ROLE["back"],
                "physical_layer_id": "back_print_outer",
                "visibility_mode": "direct",
                "region_purpose": "code",
                "coordinate_origin": "top_left",
                "bounding_box_normalized": {
                    "x": 250 / 512, "y": 150 / 288,
                    "width": 110 / 512, "height": 40 / 288,
                },
                "crop_box_px": [250, 150, 360, 190],
                "crop_locator": "00_source/back_ean13.png",
            },
            {
                "region_id": QR_REGION_ID,
                "surface_id": SURFACE_BY_ROLE["back"],
                "physical_layer_id": "back_print_outer",
                "visibility_mode": "direct",
                "region_purpose": "code",
                "coordinate_origin": "top_left",
                "bounding_box_normalized": {
                    "x": 140 / 512, "y": 150 / 288,
                    "width": 70 / 512, "height": 70 / 288,
                },
                "crop_box_px": [140, 150, 210, 220],
                "crop_locator": "00_source/back_qr.png",
            },
        ]
        back_region_spec_locator = "01_ocr/back_region_spec.json"
        write_json(root / back_region_spec_locator, {
            "schema_version": "packaging-region-ocr-spec.v2",
            "source_id": SOURCE_BY_ROLE["back"],
            "regions": [{
                key: value for key, value in definition.items()
                if key not in {"crop_box_px", "crop_locator"}
            } for definition in back_region_definitions],
        })
        back_region_spec_sha = sha256_file(root / back_region_spec_locator)
        for definition in back_region_definitions:
            region_id = definition["region_id"]
            crop_locator_value = definition["crop_locator"]
            crop_box_px = tuple(definition["crop_box_px"])
            crop_source(root / "00_source/back.png", root / crop_locator_value, crop_box_px)
            back_crop_locators[region_id] = crop_locator_value
            receipt_locator = f"01_ocr/back_regions/{region_id}.crop_receipt.json"
            receipt_value: dict[str, Any] = {
                "schema_version": "packaging-region-crop-receipt.v2",
                "source_id": SOURCE_BY_ROLE["back"],
                "source_path": "00_source/back.png",
                "source_file_sha256": sha256_file(root / "00_source/back.png"),
                "source_pixel_dimensions": {"width": 512, "height": 288},
                "region_id": region_id,
                "surface_id": definition["surface_id"],
                "physical_layer_id": definition["physical_layer_id"],
                "visibility_mode": definition["visibility_mode"],
                "region_purpose": definition["region_purpose"],
                "region_spec_path": back_region_spec_locator,
                "region_spec_sha256": back_region_spec_sha,
                "coordinate_origin": definition["coordinate_origin"],
                "bounding_box_normalized": definition["bounding_box_normalized"],
                "crop_box_px": list(crop_box_px),
                "crop_method": "axis_aligned_normalized_bbox_v1",
                "rectifier_script_sha256": sha256_file(SKILL_DIR / "scripts/run_region_ocr.py"),
                "rectified_crop_path": crop_locator_value,
                "rectified_crop_sha256": sha256_file(root / crop_locator_value),
                "receipt_sha256": None,
            }
            receipt_value["receipt_sha256"] = canonical_hash(
                receipt_value, "receipt_sha256"
            )
            write_json(root / receipt_locator, receipt_value)
            back_crop_receipts[region_id] = (receipt_locator, receipt_value)

    source_records: list[dict[str, Any]] = []
    for source in sources:
        source_id = source["source_id"]
        front = source_id == SOURCE_BY_ROLE["front"]
        back_exact = include_codes and source_id == SOURCE_BY_ROLE["back"]
        whole_observations = ([{
            "observation_id": "SRC_FRONT_WHOLE_TEXT_0001",
            "text": "EXAMPLE LAB 7Q4",
            "confidence": 0.98,
            "bounding_box_normalized": {"x": 0.25, "y": 0.25, "width": 0.12, "height": 0.04},
            "scope": "whole_product",
            "region_id": None,
            "visibility_mode": "direct",
            "disposition": {
                "status": "duplicate_showthrough",
                "review_status": "reviewed",
                "reviewer_id": "QA_REVIEWER_01",
                "evidence_note": "Discovery detection is superseded by the direct rectified region observation.",
            },
        }] if front else [])
        if back_exact:
            whole_observations = [{
                "observation_id": "SRC_BACK_WHOLE_TEXT_0001",
                "text": "EXAMPLE LAB 7Q4 TEST OIL",
                "confidence": 0.97,
                "bounding_box_normalized": {
                    "x": 0.25, "y": 0.25, "width": 0.50, "height": 0.25,
                },
                "scope": "whole_product",
                "region_id": None,
                "visibility_mode": "direct",
                "disposition": {
                    "status": "duplicate_showthrough",
                    "review_status": "reviewed",
                    "reviewer_id": "QA_REVIEWER_01",
                    "field_id": None,
                    "evidence_note": "Whole-product discovery is superseded by the exact direct back-label region observation.",
                },
            }]
        region_observations = ([{
            "observation_id": "SRC_FRONT_REGION_TEXT_0001",
            "text": EXACT_TEXT,
            "confidence": 0.99,
            "bounding_box_normalized": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
            "scope": "region",
            "region_id": REGION_ID,
            "region_pass_id": "SRC_FRONT_REGION_01",
            "surface_id": SURFACE_BY_ROLE["front"],
            "physical_layer_id": "front_label_opaque",
            "visibility_mode": "direct",
            "region_purpose": "mixed",
            "disposition": {
                "status": "mapped_to_field",
                "field_id": FIELD_ID,
                "review_status": "reviewed",
                "reviewer_id": "QA_REVIEWER_01",
                "evidence_note": "Exact NFC string confirmed against the locked source-derived crop.",
            },
        }] if front else [])
        if back_exact:
            region_observations = [{
                "observation_id": "SRC_BACK_REGION_TEXT_0001",
                "text": BACK_EXACT_TEXT,
                "confidence": 0.99,
                "bounding_box_normalized": {
                    "x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0,
                },
                "scope": "region",
                "region_id": BACK_REGION_ID,
                "region_pass_id": "SRC_BACK_BACK_LABEL_REGION_01",
                "surface_id": SURFACE_BY_ROLE["back"],
                "physical_layer_id": "back_label_opaque",
                "visibility_mode": "direct",
                "region_purpose": "text",
                "disposition": {
                    "status": "mapped_to_field",
                    "field_id": BACK_FIELD_ID,
                    "review_status": "reviewed",
                    "reviewer_id": "QA_REVIEWER_01",
                    "evidence_note": "Exact back compliance text confirmed against the replayed direct crop.",
                },
            }]
        code_observations = ([
            {
                "code_id": "SRC_BACK_EAN13_OBS_001",
                "symbology": "EAN-13",
                "payload": EAN_PAYLOAD,
                "bounding_box_normalized": {
                    "x": 250 / 512, "y": 150 / 288,
                    "width": 110 / 512, "height": 40 / 288,
                },
                "disposition": {
                    "status": "mapped_to_code",
                    "review_status": "reviewed",
                    "reviewer_id": "QA_REVIEWER_01",
                    "manifest_code_id": EAN_CODE_ID,
                    "evidence_note": "EAN-13 payload and checksum were decoded from the direct back source.",
                },
            },
            {
                "code_id": "SRC_BACK_QR_OBS_001",
                "symbology": "QR",
                "payload": QR_PAYLOAD,
                "bounding_box_normalized": {
                    "x": 140 / 512, "y": 150 / 288,
                    "width": 70 / 512, "height": 70 / 288,
                },
                "disposition": {
                    "status": "mapped_to_code",
                    "review_status": "reviewed",
                    "reviewer_id": "QA_REVIEWER_01",
                    "manifest_code_id": QR_CODE_ID,
                    "evidence_note": "QR payload bytes were decoded from the direct back source.",
                },
            },
        ] if back_exact else [])
        record: dict[str, Any] = {
            "source_id": source_id,
            "file_path": source["file_path"],
            "file_sha256": source["file_sha256"],
            "pixel_dimensions": source["pixel_dimensions"],
            "whole_product_ocr_passes": [{
                "pass_id": f"{source_id}_FULL_01",
                "scope": "whole_product",
                "engine_id": "macos_vision",
                "engine_version": "VNRecognizeTextRequest-runtime",
                "preflight_adapter_path": "scripts/run_ocr_preflight.py",
                "preflight_adapter_sha256": sha256_file(SKILL_DIR / "scripts/run_ocr_preflight.py"),
                "engine_adapter_path": "scripts/macos_vision_ocr.swift",
                "engine_adapter_sha256": sha256_file(SKILL_DIR / "scripts/macos_vision_ocr.swift"),
                "language_set": ["zh-Hans", "en-US"],
                "uses_language_correction": False,
                "source_sha256": source["file_sha256"],
                "observation_count": len(whole_observations),
            }],
            "region_ocr_passes": [],
            "text_observations": whole_observations + region_observations,
            "code_observations": code_observations,
            "ocr_review_status": "reviewed",
        }
        if not front and not back_exact:
            record["zero_detection_review_status"] = "reviewed_no_copy_detected"
        elif front:
            record["region_ocr_passes"] = [{
                "pass_id": "SRC_FRONT_REGION_01",
                "region_id": REGION_ID,
                "surface_id": SURFACE_BY_ROLE["front"],
                "physical_layer_id": "front_label_opaque",
                "visibility_mode": "direct",
                "region_purpose": "mixed",
                "engine_id": "bundled_macos_vision_ocr",
                "engine_version": "VNRecognizeTextRequest-runtime",
                "language_set": ["zh-Hans", "en-US"],
                "uses_language_correction": False,
                "source_id": source_id,
                "source_file_sha256": source["file_sha256"],
                "crop_method": "axis_aligned_normalized_bbox_v1",
                "rectifier_script_sha256": sha256_file(SKILL_DIR / "scripts/run_region_ocr.py"),
                "region_spec_path": region_spec_locator,
                "region_spec_sha256": region_spec_sha,
                "coordinate_origin": "top_left",
                "bounding_box_normalized": crop_box_normalized,
                "crop_receipt_path": crop_receipt_locator,
                "crop_receipt_sha256": sha256_file(root / crop_receipt_locator),
                "crop_receipt_semantic_sha256": crop_receipt["receipt_sha256"],
                "rectified_crop_path": crop_locator,
                "rectified_crop_sha256": sha256_file(crop_path),
                "observation_count": 1,
                "zero_detection_review_status": "not_applicable",
            }]
        elif back_exact:
            back_definitions_by_region = {
                item["region_id"]: item for item in back_region_definitions
            }
            record["region_ocr_passes"] = []
            for region_id in (BACK_REGION_ID, EAN_REGION_ID, QR_REGION_ID):
                definition = back_definitions_by_region[region_id]
                receipt_locator, receipt_value = back_crop_receipts[region_id]
                is_text = definition["region_purpose"] == "text"
                record["region_ocr_passes"].append({
                    "pass_id": f"SRC_BACK_{region_id.removeprefix('REGION_')}_REGION_01",
                    "region_id": region_id,
                    "surface_id": SURFACE_BY_ROLE["back"],
                    "physical_layer_id": definition["physical_layer_id"],
                    "visibility_mode": "direct",
                    "region_purpose": definition["region_purpose"],
                    "engine_id": "bundled_macos_vision_ocr",
                    "engine_version": "VNRecognizeTextRequest-runtime",
                    "language_set": ["zh-Hans", "en-US"],
                    "uses_language_correction": False,
                    "source_id": source_id,
                    "source_file_sha256": source["file_sha256"],
                    "crop_method": "axis_aligned_normalized_bbox_v1",
                    "rectifier_script_sha256": sha256_file(SKILL_DIR / "scripts/run_region_ocr.py"),
                    "region_spec_path": back_region_spec_locator,
                    "region_spec_sha256": back_region_spec_sha,
                    "coordinate_origin": "top_left",
                    "bounding_box_normalized": definition["bounding_box_normalized"],
                    "crop_receipt_path": receipt_locator,
                    "crop_receipt_sha256": sha256_file(root / receipt_locator),
                    "crop_receipt_semantic_sha256": receipt_value["receipt_sha256"],
                    "rectified_crop_path": back_crop_locators[region_id],
                    "rectified_crop_sha256": sha256_file(root / back_crop_locators[region_id]),
                    "observation_count": 1 if is_text else 0,
                    "zero_detection_review_status": (
                        "not_applicable" if is_text else "not_applicable_non_text_region"
                    ),
                })
        source_records.append(record)
    ocr_ledger: dict[str, Any] = {
        "schema_version": "packaging-ocr-observations.v1",
        "engine": "macos_vision",
        "engine_version": "VNRecognizeTextRequest-runtime",
        "preflight_adapter_path": "scripts/run_ocr_preflight.py",
        "preflight_adapter_sha256": sha256_file(SKILL_DIR / "scripts/run_ocr_preflight.py"),
        "engine_adapter_path": "scripts/macos_vision_ocr.swift",
        "engine_adapter_sha256": sha256_file(SKILL_DIR / "scripts/macos_vision_ocr.swift"),
        "language_set": ["zh-Hans", "en-US"],
        "uses_language_correction": False,
        "created_at": "2026-07-13T00:00:00Z",
        "source_records": source_records,
        "preflight_status": "observations_ready",
        "ledger_semantic_sha256": None,
    }
    ocr_ledger["ledger_semantic_sha256"] = canonical_hash(ocr_ledger, "ledger_semantic_sha256")
    write_json(root / "01_ocr/ocr_observations.json", ocr_ledger)
    authority_sha = sha256_file(crop_path)
    text_fields = [exact_text_field(crop_locator, authority_sha)]
    if include_codes:
        back_label_locator = back_crop_locators[BACK_REGION_ID]
        text_fields.append(back_exact_text_field(
            back_label_locator, sha256_file(root / back_label_locator),
        ))
    write_json(root / "01_ocr/exact_copy_text_ssot.json", {
        "schema_version": "packaging-exact-copy-text-ssot.v1",
        "exact_copy_mode": "all_visible_product_native_copy",
        "freeze_status": "frozen",
        "normalization_policy": {
            "unicode": "NFC", "autocorrect": "forbidden", "letters": "preserve",
            "numbers": "preserve", "punctuation": "preserve", "units": "preserve",
        },
        "fields": text_fields,
        "unresolved_required_field_ids": [],
    })
    code_records = []
    if include_codes:
        code_records = [
            {
                "code_id": EAN_CODE_ID,
                "surface_id": SURFACE_BY_ROLE["back"],
                "region_id": EAN_REGION_ID,
                "required": True,
                "symbology": "EAN-13",
                "expected_payload": EAN_PAYLOAD,
                "decoded_payload": EAN_PAYLOAD,
                "payload_match": True,
                "checksum_result": "passed",
                "authority_source_ids": [SOURCE_BY_ROLE["back"]],
                "ocr_code_observation_ids": ["SRC_BACK_EAN13_OBS_001"],
                "printed_symbol_asset_path": back_crop_locators[EAN_REGION_ID],
                "printed_symbol_asset_sha256": sha256_file(
                    root / back_crop_locators[EAN_REGION_ID]
                ),
                "status": "verified",
                "required_view_ids": [
                    "ROT_1800", "DETAIL_BARCODE_QR_CERTIFICATION",
                    dynamic_region_detail_view_id(EAN_REGION_ID),
                ],
            },
            {
                "code_id": QR_CODE_ID,
                "surface_id": SURFACE_BY_ROLE["back"],
                "region_id": QR_REGION_ID,
                "required": True,
                "symbology": "QR",
                "expected_payload": QR_PAYLOAD,
                "decoded_payload": QR_PAYLOAD,
                "payload_match": True,
                "checksum_result": "passed",
                "authority_source_ids": [SOURCE_BY_ROLE["back"]],
                "ocr_code_observation_ids": ["SRC_BACK_QR_OBS_001"],
                "printed_symbol_asset_path": back_crop_locators[QR_REGION_ID],
                "printed_symbol_asset_sha256": sha256_file(
                    root / back_crop_locators[QR_REGION_ID]
                ),
                "status": "verified",
                "required_view_ids": [
                    "ROT_1800", "DETAIL_BARCODE_QR_CERTIFICATION",
                    dynamic_region_detail_view_id(QR_REGION_ID),
                ],
            },
        ]
    write_json(root / "01_ocr/code_manifest.json", {
        "schema_version": "packaging-code-manifest.v1",
        "codes": code_records,
        "required_codes_present": include_codes,
    })
    write_json(root / "01_ocr/logo_graphic_manifest.json", {
        "schema_version": "packaging-logo-graphic-manifest.v1",
        "graphics": [{
            "graphic_id": GRAPHIC_ID,
            "graphic_role": "brand_logo",
            "required": True,
            "surface_id": SURFACE_BY_ROLE["front"],
            "region_id": REGION_ID,
            "authority_source_ids": [SOURCE_BY_ROLE["front"]],
            "asset_path": crop_locator,
            "asset_sha256": authority_sha,
            "status": "verified",
            "disposition": {
                "status": "mapped_to_graphic",
                "review_status": "reviewed",
                "reviewer_id": "QA_REVIEWER_01",
                "manifest_graphic_id": GRAPHIC_ID,
                "evidence_note": "Named reviewer matched the source-derived brand mark to this manifest graphic.",
            },
            "render_policy": "deterministic_source_projection",
            "required_view_ids": [
                "ROT_0000", "DETAIL_LOGO_HERO_COPY",
                dynamic_region_detail_view_id(REGION_ID),
            ],
        }],
    })
    textures = [{
        "surface_id": SURFACE_BY_ROLE["front"],
        "asset_path": "00_source/front.png",
        "asset_sha256": sha256_file(root / "00_source/front.png"),
    }]
    if include_codes:
        textures.append({
            "surface_id": SURFACE_BY_ROLE["back"],
            "asset_path": "00_source/back.png",
            "asset_sha256": sha256_file(root / "00_source/back.png"),
        })
    write_json(root / "03_composition/surface_texture_atlas.json", {
        "schema_version": "packaging-surface-texture-atlas.v1",
        "freeze_status": "frozen",
        "textures": textures,
    })
    mask_locator = "03_composition/masks/REGION_FRONT_LABEL.png"
    write_image(root / mask_locator, (255, 255, 255), (128, 72))
    neutral_locator = "03_composition/layers/neutral_patch.png"
    write_image(root / neutral_locator, (12, 34, 56), (16, 16))
    neutral_mask_locator = "03_composition/masks/NEUTRAL_PATCH.png"
    write_image(root / neutral_mask_locator, (255, 255, 255), (16, 16))
    mask_records = [{
        "region_id": REGION_ID,
        "asset_path": mask_locator,
        "asset_sha256": sha256_file(root / mask_locator),
    }]
    if include_codes:
        for region_id, size in (
            (BACK_REGION_ID, (256, 72)),
            (EAN_REGION_ID, (110, 40)),
            (QR_REGION_ID, (70, 70)),
        ):
            locator = f"03_composition/masks/{region_id}.png"
            write_image(root / locator, (255, 255, 255), size)
            mask_records.append({
                "region_id": region_id,
                "asset_path": locator,
                "asset_sha256": sha256_file(root / locator),
            })
    write_json(root / "03_composition/protected_region_masks.json", {
        "schema_version": "packaging-protected-region-masks.v1",
        "freeze_status": "frozen",
        "masks": mask_records,
    })

    views = [
        make_view(
            view_id, rotation_profile, product_features,
            include_codes=include_codes, elevation_rings=elevation_rings,
        )
        for view_id in required_view_ids(
            rotation_profile, product_features, include_codes=include_codes,
            elevation_rings=elevation_rings,
        )
    ]
    write_json(root / "02_coverage/coverage_matrix.json", {
        "schema_version": "packaging-view-coverage.v1",
        "rotation_profile": rotation_profile,
        "product_state_id": STATE_ID,
        "freeze_status": "frozen",
        "production_coverage_status": "passed",
        "product_coordinate_frame": {
            "z_axis": "product_vertical_positive_up",
            "front_axis": "outward_normal_of_authoritative_front",
            "right_axis": "product_right_when_viewed_from_front",
            "azimuth_0": "front",
            "azimuth_90": "right",
            "azimuth_180": "back",
            "azimuth_270": "left",
            "positive_azimuth": "camera_clockwise_when_viewed_from_above",
            "elevation_positive": "camera_above_product",
        },
        "identity_lock": {
            "occupancy_lock": "product occupies 72 percent of frame height at a fixed optical center",
            "geometry_landmark_contract": {
                "required_landmark_ids": [
                    "LANDMARK_BODY_OUTLINE", "LANDMARK_VERTICAL_AXIS",
                    *continuity_raw_landmark_ids(product_features),
                ],
                "component_ids": all_component_ids(product_features),
                "component_count_lock": "exact frozen component inventory",
                "width_depth_height_ratio_lock": "source-calibrated product ratio",
                "closure_vector_lock": "fixed in product coordinates",
                "internal_component_topology_lock": "source-calibrated graph",
            },
            "material_contract": {
                "material_feature_ids": material_feature_ids(product_features),
                "body_material": (
                    "source-verified transparent polymer"
                    if "transparent_or_translucent" in product_features
                    else "source-verified opaque polymer"
                ),
                "closure_material": "source-verified polymer",
                "content_material": (
                    "source-verified liquid"
                    if "liquid_or_gel" in product_features else "not_applicable"
                ),
                "fill_level_lock": (
                    "source-calibrated world-horizontal liquid boundary"
                    if "visible_fill_line_or_liquid_boundary" in product_features else "not_applicable"
                ),
                "transparency_layer_order": (
                    ["front_wall", "internal_content", "internal_components", "rear_wall"]
                    if "transparent_or_translucent" in product_features else []
                ),
            },
            "forbidden_inventions": ["new seams", "new labels", "new mechanisms", "new copy"],
        },
        "views": views,
    })
    view_ids = [view["view_id"] for view in views]
    ring_sequences = [list(PROFILES["rotation_profiles"][rotation_profile]["view_ids"])]
    ring_sequences.extend(list(ring["view_ids"]) for ring in elevation_rings)
    required_edge_ids = [
        f"{ring[index]}__TO__{ring[(index + 1) % len(ring)]}"
        for ring in ring_sequences for index in range(len(ring))
    ]
    write_json(root / "02_coverage/motion_envelope.json", {
        "schema_version": "packaging-motion-envelope.v1",
        "motion_type": motion_type,
        "motion_scope": motion_scope,
        "product_state_id": STATE_ID,
        "required_view_ids": view_ids,
        "required_edge_ids": required_edge_ids,
        "loop_closure_required": True,
        "elevation_rings": elevation_rings,
        "coverage_status": "passed",
        "blocked_motion_segments": [],
    })
    neutral_ring = list(PROFILES["rotation_profiles"][rotation_profile]["view_ids"])
    source_manifest_sha = sha256_file(root / "00_source/source_manifest.json")
    write_json(root / "02_coverage/continuity_contract.json", {
        "schema_version": "packaging-continuity-contract.v1",
        "freeze_status": "frozen",
        "product_state_id": STATE_ID,
        "required_gates": sorted(derive_required_continuity_gates(product_features)),
        "geometry_tolerance_normalized": 0.25,
        "object_occupancy_tolerance_normalized": 0.25,
        "text_code_topology_zero_tolerance": True,
        "calibration_baselines": {
            "silhouette_gate": {
                "calibration_id": "silhouette_source_pose_baseline_v1",
                "basis": "source_pose_locked_before_generation",
                "source_manifest_sha256": source_manifest_sha,
                "by_view": {
                    view_id: {
                        "area_normalized": round(
                            continuity_builder.polygon_area([
                                (float(x), float(y))
                                for x, y in silhouette_polygon_for_ring_index(index, len(neutral_ring))
                            ]), 12,
                        ),
                        "bbox_aspect_ratio": round(
                            ([point[0] for point in silhouette_polygon_for_ring_index(index, len(neutral_ring))][1]
                             - [point[0] for point in silhouette_polygon_for_ring_index(index, len(neutral_ring))][0])
                            / 0.70,
                            12,
                        ),
                    }
                    for index, view_id in enumerate(neutral_ring)
                },
            },
            "material_gate": {
                "calibration_id": "material_source_pose_baseline_v1",
                "basis": "source_pose_locked_before_generation",
                "source_manifest_sha256": source_manifest_sha,
                "by_view": {
                    view_id: {"statistic_value": expected_material_luma(index + 1)}
                    for index, view_id in enumerate(neutral_ring)
                },
            },
            "transparent_showthrough_gate": {
                "calibration_id": "showthrough_source_pose_baseline_v1",
                "basis": "source_pose_locked_before_generation",
                "source_manifest_sha256": source_manifest_sha,
                "by_view": {
                    view_id: {"statistic_value": expected_material_luma(index + 1)}
                    for index, view_id in enumerate(neutral_ring)
                },
            },
            **({
                "transparent_showthrough_gate": {
                    "calibration_id": "showthrough_source_pose_baseline_v1",
                    "basis": "source_pose_locked_before_generation",
                    "source_manifest_sha256": source_manifest_sha,
                    "by_view": {
                        view_id: {"statistic_value": expected_showthrough_luma_std(index + 1)}
                        for index, view_id in enumerate(neutral_ring)
                    },
                },
            } if "transparent_or_translucent" in product_features else {}),
            "edge_measurements": {
                "calibration_id": "edge_motion_pose_baseline_v1",
                "basis": "source_pose_locked_before_generation",
                "source_manifest_sha256": source_manifest_sha,
                "by_edge": edge_calibration_by_edge(neutral_ring),
            },
            "loop_closure_gate": {
                "calibration_id": "loop_closure_pose_baseline_v1",
                "basis": "source_pose_locked_before_generation",
                "source_manifest_sha256": source_manifest_sha,
                "by_edge": {
                    edge_id: edge
                    for edge_id, edge in edge_calibration_by_edge(neutral_ring).items()
                    if edge["from_view_id"] == neutral_ring[-1]
                    and edge["to_view_id"] == neutral_ring[0]
                },
            },
        },
    })
    write_json(root / "03_composition/deterministic_composition_plan.json", {
        "schema_version": "packaging-deterministic-composition-plan.v1",
        "plan_id": "COMPOSITION_PLAN_ACCEPTANCE_V1",
        "status": "ready",
        "view_statuses": [{
            "view_id": view["view_id"],
            "status": "ready",
            "projection_model": (
                "planar_rectangle" if view.get("dynamic_region_contract")
                else "source_pixel_preservation"
            ),
            "source_layer_ids": exact_source_layer_ids(view),
            "protected_region_ids": view["label_region_ids"],
            "ocr_field_ids_visible": view["ocr_field_ids_visible"],
            "code_ids_visible": view["code_ids_visible"],
            "graphic_ids_visible": view["graphic_ids_visible"],
            "binding_receipt_required": True,
        } for view in views],
    })

    bundle: dict[str, Any] = {
        "schema_version": "packaging-exact-copy-bundle.v1",
        "exact_copy_mode": "all_visible_product_native_copy",
        "text_ssot_sha256": sha256_file(root / "01_ocr/exact_copy_text_ssot.json"),
        "code_manifest_sha256": sha256_file(root / "01_ocr/code_manifest.json"),
        "logo_graphic_manifest_sha256": sha256_file(root / "01_ocr/logo_graphic_manifest.json"),
        "surface_texture_atlas_sha256": sha256_file(root / "03_composition/surface_texture_atlas.json"),
        "protected_region_masks_sha256": sha256_file(root / "03_composition/protected_region_masks.json"),
        "deterministic_composition_plan_sha256": sha256_file(root / "03_composition/deterministic_composition_plan.json"),
        "freeze_status": "frozen",
        "exact_copy_bundle_sha256": None,
    }
    bundle["exact_copy_bundle_sha256"] = canonical_hash(bundle, "exact_copy_bundle_sha256")
    write_json(root / "01_ocr/exact_copy_bundle_manifest.json", bundle)

    manifest = {
        "schema_version": "packaging-asset-pack-run.v3",
        "contract_version": "whole_product_ocr_rotation_pack_v3",
        "run_id": "RUN_CONTRACT_ACCEPTANCE",
        "product_id": PRODUCT_ID,
        "product_state_id": STATE_ID,
        "stage": "READY_FOR_GENERATION",
        "exact_copy_mode": "all_visible_product_native_copy",
        "allow_geometry_only_preview": False,
        "rotation_profile": rotation_profile,
        "master_resolution_contract": {
            "aspect_ratio": "16:9",
            "minimum_native_width_px": 1280,
            "minimum_native_height_px": 720,
            "post_generation_resize_allowed_to_meet_minimum": False,
            "external_4k_is_separate_delivery_state": True,
        },
        "product_features": product_features,
        "paths": manifest_paths(),
        "hashes": {},
        "gates": {
            "variant_conflict_status": "passed",
            "whole_product_ocr_status": "passed",
            "region_ocr_status": "passed",
            "copy_preflight_status": "passed_ssot_frozen",
            "exact_copy_bundle_hash_verified": True,
            "unresolved_required_field_count": 0,
            "source_conflict_count": 0,
            "required_code_decodes_pass": True,
            "logo_graphic_binding_pass": True,
            "deterministic_composition_plan_status": "ready",
            "required_view_surface_coverage_status": "passed",
            "prompt_compilation_allowed": True,
            "image_generation_allowed": True,
        },
        "production_approval_status": "not_granted",
        "blocked_reason": None,
    }
    write_json(root / "00_manifest/run_manifest.json", manifest)
    relock(root)
    compile_prompts(root)


def composition_layers(root: Path, view: dict[str, Any]) -> list[dict[str, Any]]:
    view_id = view["view_id"]
    dynamic_region_id = (view.get("dynamic_region_contract") or {}).get("region_id")
    layers: list[dict[str, Any]] = []

    def add_layer(
        *, layer_suffix: str, source_layer_id: str, source_path: str,
        source_size: tuple[int, int], destination_box: list[int], mask_path: str,
        region_ids: list[str], field_ids: list[str], code_ids: list[str],
        graphic_ids: list[str],
    ) -> None:
        layers.append({
            "layer_id": f"LAYER_{layer_suffix}_{view_id}",
            "source_layer_id": source_layer_id,
            "projection_model": (
                "planar_rectangle" if dynamic_region_id else "source_pixel_preservation"
            ),
            "source_path": source_path,
            "source_sha256": sha256_file(root / source_path),
            "source_crop_box_px": [0, 0, source_size[0], source_size[1]],
            "destination_box_px": destination_box,
            "mask_path": mask_path,
            "mask_sha256": sha256_file(root / mask_path),
            "region_ids": region_ids,
            "field_ids": field_ids,
            "graphic_ids": graphic_ids,
            "code_ids": code_ids,
        })

    if FIELD_ID in set(view.get("ocr_field_ids_visible") or []):
        add_layer(
            layer_suffix="FRONT_EXACT", source_layer_id="LAYER_FRONT_EXACT",
            source_path="00_source/front_label_rectified.png", source_size=(128, 72),
            destination_box=(
                scale_master_box([64, 36, 448, 252]) if dynamic_region_id == REGION_ID
                else [192, 108, 320, 180]
            ),
            mask_path="03_composition/masks/REGION_FRONT_LABEL.png",
            region_ids=[REGION_ID], field_ids=[FIELD_ID], code_ids=[],
            graphic_ids=[GRAPHIC_ID],
        )
    if BACK_FIELD_ID in set(view.get("ocr_field_ids_visible") or []):
        add_layer(
            layer_suffix="BACK_TEXT", source_layer_id="LAYER_BACK_TEXT_EXACT",
            source_path="00_source/back_label_rectified.png", source_size=(256, 72),
            destination_box=(
                scale_master_box([32, 81, 480, 207]) if dynamic_region_id == BACK_REGION_ID
                else [128, 80, 384, 152]
            ),
            mask_path=f"03_composition/masks/{BACK_REGION_ID}.png",
            region_ids=[BACK_REGION_ID], field_ids=[BACK_FIELD_ID], code_ids=[],
            graphic_ids=[],
        )
    if EAN_CODE_ID in set(view.get("code_ids_visible") or []):
        add_layer(
            layer_suffix="BACK_EAN13", source_layer_id="LAYER_BACK_EAN13_EXACT",
            source_path="00_source/back_ean13.png", source_size=(110, 40),
            destination_box=(
                scale_master_box([64, 72, 448, 216]) if dynamic_region_id == EAN_REGION_ID
                else [260, 170, 370, 210]
            ),
            mask_path=f"03_composition/masks/{EAN_REGION_ID}.png",
            region_ids=[EAN_REGION_ID], field_ids=[], code_ids=[EAN_CODE_ID],
            graphic_ids=[],
        )
    if QR_CODE_ID in set(view.get("code_ids_visible") or []):
        add_layer(
            layer_suffix="BACK_QR", source_layer_id="LAYER_BACK_QR_EXACT",
            source_path="00_source/back_qr.png", source_size=(70, 70),
            destination_box=(
                scale_master_box([144, 32, 400, 288]) if dynamic_region_id == QR_REGION_ID
                else [150, 165, 220, 235]
            ),
            mask_path=f"03_composition/masks/{QR_REGION_ID}.png",
            region_ids=[QR_REGION_ID], field_ids=[], code_ids=[QR_CODE_ID],
            graphic_ids=[],
        )
    if not layers:
        add_layer(
            layer_suffix="NEUTRAL", source_layer_id="LAYER_NEUTRAL_PATCH",
            source_path="03_composition/layers/neutral_patch.png", source_size=(16, 16),
            destination_box=[8, 8, 24, 24],
            mask_path="03_composition/masks/NEUTRAL_PATCH.png",
            region_ids=[], field_ids=[], code_ids=[], graphic_ids=[],
        )
    return layers


def write_post_ocr_evidence(
    root: Path, view: dict[str, Any], asset_id: str,
    final_locator: str, final_sha: str, job: dict[str, Any],
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    view_id = view["view_id"]
    scans = [
        {
            "scan_id": f"{view_id}_FINAL_MASTER",
            "scope": "final_master",
            "image_path": final_locator,
            "image_sha256": final_sha,
            "pixel_dimensions": {"width": MASTER_SIZE[0], "height": MASTER_SIZE[1]},
            "crop_box_px_on_final_master": None,
            "region_ids": [], "field_ids": [], "code_ids": [],
            "graphic_ids": [], "layer_ids": [],
        },
    ]
    scan_specs: list[post_adapter.ScanSpec] = []
    for index, layer in enumerate(job["layers"], start=1):
        destination = tuple(layer["destination_box_px"])
        crop_locator = f"07_qa/post_ocr/crops/{view_id}/REGION_{index:03d}.png"
        crop_source(root / final_locator, root / crop_locator, destination)
        crop_path = root / crop_locator
        with Image.open(crop_path) as crop_image:
            crop_width, crop_height = crop_image.size
        scan = post_adapter.ScanSpec(
            scan_id=f"{view_id}_PROJECTED_REGION_{index:03d}",
            scope="projected_region_crop",
            image_path=crop_path,
            image_locator=crop_locator,
            crop_box_px=destination,
            region_ids=tuple(layer["region_ids"]),
            field_ids=tuple(layer["field_ids"]),
            code_ids=tuple(layer["code_ids"]),
            graphic_ids=tuple(layer["graphic_ids"]),
            layer_ids=(layer["layer_id"],),
        )
        scan_specs.append(scan)
        scans.append({
            "scan_id": scan.scan_id,
            "scope": scan.scope,
            "image_path": crop_locator,
            "image_sha256": sha256_file(crop_path),
            "pixel_dimensions": {"width": crop_width, "height": crop_height},
            "crop_box_px_on_final_master": list(destination),
            "region_ids": list(scan.region_ids), "field_ids": list(scan.field_ids),
            "code_ids": list(scan.code_ids), "graphic_ids": list(scan.graphic_ids),
            "layer_ids": list(scan.layer_ids),
        })

    field_records = {
        FIELD_ID: exact_text_field(
            "00_source/front_label_rectified.png",
            sha256_file(root / "00_source/front_label_rectified.png"),
        ),
    }
    if (root / "00_source/back_label_rectified.png").is_file():
        field_records[BACK_FIELD_ID] = back_exact_text_field(
            "00_source/back_label_rectified.png",
            sha256_file(root / "00_source/back_label_rectified.png"),
        )
    text_lines_by_field = {
        FIELD_ID: EXACT_TEXT_LINES,
        BACK_FIELD_ID: BACK_EXACT_TEXT_LINES,
    }
    raw_text: list[dict[str, Any]] = []
    for scan in scan_specs:
        for field_id in scan.field_ids:
            lines = text_lines_by_field[field_id]
            y_values = [0.78, 0.45, 0.12][:len(lines)]
            scan_size = (
                scan.crop_box_px[2] - scan.crop_box_px[0],
                scan.crop_box_px[3] - scan.crop_box_px[1],
            )
            for line_index, (line_text, y) in enumerate(zip(lines, y_values), start=1):
                crop_box = {"x": 0.05, "y": y, "width": 0.90, "height": 0.10}
                raw_text.append({
                    "raw_observation_id": f"RAW_{scan.scan_id}_TEXT_{line_index:04d}",
                    "scan_id": scan.scan_id,
                    "scan_scope": "projected_region_crop",
                    "text": line_text,
                    "observed_hash": hashlib.sha256(line_text.encode("utf-8")).hexdigest(),
                    "confidence": 0.99,
                    "scan_bounding_box_normalized": crop_box,
                    "full_master_bounding_box_normalized": post_adapter.full_master_box(
                        crop_box, scan, MASTER_SIZE, scan_size,
                    ),
                    "candidate_ids": [],
                    "region_ids": list(scan.region_ids),
                })
    expected_fields = {
        field_id: field_records[field_id]
        for field_id in view["ocr_field_ids_visible"]
    }
    _, aggregates = post_adapter.build_exact_aggregate_observations(
        raw_text, scan_specs, expected_fields,
    )
    observations: list[dict[str, Any]] = []
    field_results: list[dict[str, Any]] = []
    aggregates_by_field = {
        aggregate["candidate_ids"][0]: aggregate for aggregate in aggregates
    }
    if set(aggregates_by_field) != set(expected_fields):
        raise AssertionError(f"ordered aggregation did not cover visible fields for {view_id}")
    for field_id in sorted(expected_fields):
        aggregate = aggregates_by_field[field_id]
        field = expected_fields[field_id]
        observation_id = f"POST_{view_id}_{field_id}"
        observations.append({
            "observation_id": observation_id,
            "field_id": field_id,
            "text": field["expected_raw_text"],
            "text_sha256": field["expected_text_sha256"],
            "confidence": aggregate["confidence"],
            "region_id": field["region_id"],
            "full_master_bounding_box_normalized": aggregate["full_master_bounding_box_normalized"],
            "source_scan_id": aggregate["scan_id"],
            "raw_observation_ids": [aggregate["raw_observation_id"]],
            "disposition": "mapped_to_expected_field",
            "product_native": True,
            "review_status": "reviewed",
            "ocr_match_policy": "ordered_line_aggregation_exact",
            "mapping_basis": "ordered_bbox_line_aggregation_exact_utf8_hash_one_to_one",
            "aggregation": aggregate["aggregation"],
        })
        field_results.append({
            "field_id": field_id,
            "observation_id": observation_id,
            "expected_text_sha256": field["expected_text_sha256"],
            "observed_text_sha256": field["expected_text_sha256"],
            "match": True,
            "ocr_match_policy": "ordered_line_aggregation_exact",
            "line_joiner": "newline",
        })

    code_records = {
        EAN_CODE_ID: {
            "symbology": "EAN-13", "expected_payload": EAN_PAYLOAD,
            "region_id": EAN_REGION_ID,
        },
        QR_CODE_ID: {
            "symbology": "QR", "expected_payload": QR_PAYLOAD,
            "region_id": QR_REGION_ID,
        },
    }
    raw_codes: list[dict[str, Any]] = []
    code_observations: list[dict[str, Any]] = []
    code_results: list[dict[str, Any]] = []
    for scan in scan_specs:
        for code_id in scan.code_ids:
            code = code_records[code_id]
            payload = code["expected_payload"]
            raw_symbology = (
                "VNBarcodeSymbologyEAN13" if code_id == EAN_CODE_ID
                else "VNBarcodeSymbologyQR"
            )
            crop_box = {"x": 0.10, "y": 0.10, "width": 0.80, "height": 0.80}
            scan_size = (
                scan.crop_box_px[2] - scan.crop_box_px[0],
                scan.crop_box_px[3] - scan.crop_box_px[1],
            )
            full_box = post_adapter.full_master_box(
                crop_box, scan, MASTER_SIZE, scan_size,
            )
            raw_id = f"RAW_{scan.scan_id}_{code_id}"
            raw_codes.append({
                "raw_observation_id": raw_id,
                "scan_id": scan.scan_id,
                "scan_scope": "projected_region_crop",
                "payload": payload,
                "observed_hash": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                "raw_symbology": raw_symbology,
                "canonical_symbology": code["symbology"],
                "scan_bounding_box_normalized": crop_box,
                "full_master_bounding_box_normalized": full_box,
                "candidate_ids": [code_id],
                "region_ids": list(scan.region_ids),
            })
            integrity, integrity_method = post_adapter.decoded_payload_integrity(
                code["symbology"], payload,
            )
            if not integrity:
                raise AssertionError(f"test code payload integrity failed for {code_id}")
            observation_id = f"POST_{view_id}_{code_id}"
            observation = {
                "observation_id": observation_id,
                "code_id": code_id,
                "symbology": code["symbology"],
                "observed_symbology_raw": raw_symbology,
                "symbology_mapping_id": "explicit_vision_aliases_v1",
                "payload": payload,
                "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                "region_id": code["region_id"],
                "full_master_bounding_box_normalized": full_box,
                "source_scan_id": scan.scan_id,
                "raw_observation_ids": [raw_id],
                "decode_integrity_status": "passed",
                "decode_integrity_method": integrity_method,
                "disposition": "mapped_to_expected_code",
                "review_status": "reviewed",
            }
            code_observations.append(observation)
            receipt_locator = (
                f"07_qa/post_ocr/code_decode_receipts/{view_id}/{code_id}.json"
            )
            receipt_value: dict[str, Any] = {
                "schema_version": "packaging-post-code-decode-receipt.v1",
                "asset_id": asset_id,
                "view_id": view_id,
                "asset_file_sha256": final_sha,
                "code_id": code_id,
                "engine_id": "bundled_macos_vision_ocr",
                "engine_script_path": "scripts/macos_vision_ocr.swift",
                "engine_script_sha256": sha256_file(
                    SKILL_DIR / "scripts/macos_vision_ocr.swift"
                ),
                "observation_id": observation_id,
                "observed_symbology_raw": raw_symbology,
                "canonical_symbology": code["symbology"],
                "payload": payload,
                "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                "decode_integrity_status": "passed",
                "decode_integrity_method": integrity_method,
                "symbol_geometry_status": "matched",
                "receipt_sha256": None,
            }
            receipt_value["receipt_sha256"] = canonical_hash(
                receipt_value, "receipt_sha256"
            )
            write_json(root / receipt_locator, receipt_value)
            code_results.append({
                "code_id": code_id,
                "observation_id": observation_id,
                "symbology": code["symbology"],
                "expected_payload_sha256": receipt_value["payload_sha256"],
                "observed_payload_sha256": receipt_value["payload_sha256"],
                "payload_match": True,
                "checksum_result": "passed",
                "symbol_geometry_status": "matched",
                "decode_receipt_path": receipt_locator,
                "decode_receipt_sha256": sha256_file(root / receipt_locator),
            })
    post_ocr_locator = f"07_qa/post_ocr/{view_id}.json"
    write_json(root / post_ocr_locator, {
        "schema_version": "packaging-post-ocr-evidence.v1",
        "asset_id": asset_id, "view_id": view_id,
        "asset_file_path": final_locator, "asset_file_sha256": final_sha,
        "engine_id": "bundled_macos_vision_ocr",
        "engine_version": "VNRecognizeTextRequest-runtime",
        "engine_script_path": "scripts/macos_vision_ocr.swift",
        "engine_script_sha256": sha256_file(SKILL_DIR / "scripts/macos_vision_ocr.swift"),
        "language_set": ["zh-Hans", "en-US"],
        "uses_language_correction": False,
        "review_status": "reviewed",
        "mapping_policy": "exact_utf8_single_or_fixed_bbox_line_aggregation_one_to_one_v2",
        "aggregation_order_contract": {
            "reading_order": "top_to_bottom_then_same_line_left_to_right",
            "same_line_min_center_delta": post_adapter.SAME_LINE_MIN_CENTER_DELTA,
            "same_line_height_ratio": post_adapter.SAME_LINE_HEIGHT_RATIO,
            "intra_line_joiner": "U+0020",
            "language_model_correction": "forbidden",
        },
        "scans": scans,
        "observations": observations,
        "code_observations": code_observations,
        "raw_scan_observations": {"text": raw_text, "codes": raw_codes},
        "aggregate_observations": aggregates,
        "unresolved_observation_ids": [],
        "missing_field_ids": [],
        "missing_code_ids": [],
    })
    return post_ocr_locator, field_results, code_results


def build_review_boards(root: Path, asset_qa_path: Path) -> list[dict[str, Any]]:
    board_records: list[dict[str, Any]] = []
    qa = json.loads(asset_qa_path.read_text(encoding="utf-8"))
    role_by_family = {
        "neutral_ring": "neutral_rotation",
        "high_angle": "elevation", "low_angle": "elevation", "top_bottom": "elevation",
        "upper_half_close": "framing_bridge", "lower_half_close": "framing_bridge",
        "detail_copy": "copy", "detail_code": "code",
        "detail_structure": "structure", "detail_material": "material",
    }
    present_roles = {
        role_by_family.get(str(asset.get("family")))
        for asset in qa.get("assets") or [] if isinstance(asset, dict)
    }
    ordered_roles = [
        "neutral_rotation", "elevation", "framing_bridge",
        "copy", "code", "structure", "material",
    ]
    for semantic_role in ordered_roles:
        if semantic_role not in present_roles:
            continue
        command = [
            sys.executable,
            str(SKILL_DIR / "scripts/build_review_boards.py"),
            "--asset-qa", str(asset_qa_path),
            "--output-dir", str(root / f"06_review_boards/{semantic_role}"),
            "--width", "3840", "--height", "2160", "--prefix", semantic_role,
            "--semantic-role", semantic_role,
        ]
        summary = run_command(command, f"{semantic_role} review-board builder")
        manifest_path = Path(str(summary["manifest"]))
        board_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        board_records.extend(board_manifest["boards"])
    return board_records


def continuity_edge_pairs(rotation_profile: str = "R8") -> list[tuple[str, str]]:
    ring = PROFILES["rotation_profiles"][rotation_profile]["view_ids"]
    return [(view_id, ring[(index + 1) % len(ring)]) for index, view_id in enumerate(ring)]


def write_continuity_qa_from_receipt(root: Path, receipt_locator: str) -> None:
    receipt_path = root / receipt_locator
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    evidence_sha = sha256_file(receipt_path)
    asset_qa = json.loads((root / "07_qa/asset_qa.json").read_text(encoding="utf-8"))
    all_final_hashes = sorted(asset["file_sha256"] for asset in asset_qa["assets"])
    gate_results = [{
        "gate_id": group["gate_id"],
        "status": group["status"],
        "asset_file_sha256s": all_final_hashes,
        "evidence_path": receipt_locator,
        "evidence_sha256": evidence_sha,
    } for group in receipt["gate_measurements"]]
    edge_results = [{
        "edge_id": group["edge_id"],
        "from_view_id": group["from_view_id"],
        "to_view_id": group["to_view_id"],
        "from_file_sha256": group["from_file_sha256"],
        "to_file_sha256": group["to_file_sha256"],
        "status": group["status"],
        "evidence_path": receipt_locator,
        "evidence_sha256": evidence_sha,
    } for group in receipt["edge_measurements"]]
    all_passed = (
        all(item["status"] == "passed" for item in gate_results)
        and all(item["status"] == "passed" for item in edge_results)
    )
    write_json(root / "07_qa/continuity_qa.json", {
        "schema_version": "packaging-continuity-qa.v1",
        "all_gates_passed": all_passed,
        "loop_closure_status": "passed" if all_passed else "failed",
        "failed_edge_ids": sorted(
            item["edge_id"] for item in edge_results if item["status"] != "passed"
        ),
        "gate_results": gate_results,
        "edge_results": edge_results,
    })


def run_continuity_builder(root: Path) -> None:
    receipt_locator = "07_qa/continuity_measurements.json"
    summary = run_command([
        sys.executable,
        str(SKILL_DIR / "scripts/build_continuity_measurements.py"),
        str(root),
        "--source-manifest", "00_source/source_manifest.json",
        "--asset-qa", "07_qa/asset_qa.json",
        "--coverage", "02_coverage/coverage_matrix.json",
        "--continuity-contract", "02_coverage/continuity_contract.json",
        "--semantic-evidence", "07_qa/continuity_semantic_evidence.json",
        "--output", receipt_locator,
    ], "continuity measurement v2 builder")
    if summary.get("status") != "PASS":
        raise AssertionError("continuity measurement builder did not return PASS")
    write_continuity_qa_from_receipt(root, receipt_locator)


def build_continuity_artifacts(root: Path, asset_records: list[dict[str, Any]]) -> None:
    asset_by_view = {asset["view_id"]: asset for asset in asset_records}
    source_manifest = json.loads(
        (root / "00_source/source_manifest.json").read_text(encoding="utf-8")
    )
    product_features = {
        item["feature_id"] for item in source_manifest["product_feature_classification"]
        if item.get("status") == "present"
    }
    required_gates = continuity_builder.derive_required_continuity_gates(product_features)
    if required_gates != derive_required_continuity_gates(product_features):
        raise AssertionError("builder and validator continuity gate derivation diverged")
    continuity_contract = json.loads(
        (root / "02_coverage/continuity_contract.json").read_text(encoding="utf-8")
    )
    if set(continuity_contract.get("required_gates") or []) != required_gates:
        raise AssertionError("continuity fixture contract is not source-feature-derived")
    coverage = json.loads(
        (root / "02_coverage/coverage_matrix.json").read_text(encoding="utf-8")
    )
    ring_views = list(PROFILES["rotation_profiles"][coverage["rotation_profile"]]["view_ids"])
    minimum_views = ring_views[:2]
    ring_hashes = [asset_by_view[view_id]["file_sha256"] for view_id in ring_views]
    all_final_hashes = [asset_by_view[view_id]["file_sha256"] for view_id in sorted(asset_by_view)]
    annotation_locator = "07_qa/continuity_annotations/raw_continuity_geometry.json"
    annotation_id = "ANNOTATION_RAW_CONTINUITY_GEOMETRY"
    active_requirements = [
        continuity_builder.GATE_REQUIREMENTS[gate_id] for gate_id in sorted(required_gates)
    ]
    needed_landmark_ids = {
        landmark_id
        for requirement in [*active_requirements, continuity_builder.EDGE_REQUIREMENT]
        for landmark_id in (
            requirement.get("landmark_ids", [])
            + requirement.get("frame_landmark_ids", [])
            + requirement.get("node_landmark_ids", [])
            + [item for pair in requirement.get("landmark_pairs", []) for item in pair]
            + (requirement.get("structure_ids", []) if requirement.get("structure_type") == "landmarks" else [])
        )
    }
    landmark_points = {
        "ADJACENT_EDGE_ANCHOR_A": [0.30, 0.30],
        "ADJACENT_EDGE_ANCHOR_B": [0.70, 0.30],
        "CAMERA_PRODUCT_CENTER": [0.50, 0.50],
        "DIP_TUBE_START": [0.50, 0.25],
        "DIP_TUBE_MIDDLE": [0.50, 0.50],
        "DIP_TUBE_END": [0.50, 0.75],
        "LOOP_ANCHOR_LEFT": [0.30, 0.50],
        "LOOP_ANCHOR_RIGHT": [0.70, 0.50],
        "PRODUCT_ROTATION_CENTER": [0.50, 0.50],
        "COMPONENT_BODY": [0.50, 0.60],
        "COMPONENT_CLOSURE": [0.50, 0.25],
    }
    landmark_points = {
        key: value for key, value in landmark_points.items() if key in needed_landmark_ids
    }
    landmarks = [{
        "landmark_id": landmark_id, "view_id": view_id,
        "asset_file_sha256": asset_by_view[view_id]["file_sha256"],
        "region_id": None, "point_normalized": coordinates,
    } for view_id in ring_views for landmark_id, coordinates in landmark_points.items()]
    landmarks.extend({
        "landmark_id": landmark_id, "view_id": view_id,
        "asset_file_sha256": asset_by_view[view_id]["file_sha256"],
        "region_id": None, "point_normalized": coordinates,
    } for index, view_id in enumerate(ring_views)
      for landmark_id, coordinates in edge_anchor_points_for_ring_index(index, len(ring_views)).items())
    if "label_surface_binding_gate" in required_gates:
        landmarks.extend({
            "landmark_id": landmark_id, "view_id": view_id,
            "asset_file_sha256": asset_by_view[view_id]["file_sha256"],
            "region_id": REGION_ID, "point_normalized": coordinates,
        } for view_id in minimum_views for landmark_id, coordinates in label_surface_frame(view_id).items())
    if "nozzle_frame_binding_gate" in required_gates:
        landmarks.extend({
            "landmark_id": landmark_id, "view_id": view_id,
            "asset_file_sha256": asset_by_view[view_id]["file_sha256"],
            "region_id": None, "point_normalized": coordinates,
        } for view_id in minimum_views
          for landmark_id, coordinates in nozzle_frame_and_vector_points(view_id).items())
    line_geometry = {
        "DIP_TUBE_START_TO_MIDDLE": [[0.50, 0.25], [0.50, 0.50]],
        "DIP_TUBE_MIDDLE_TO_END": [[0.50, 0.50], [0.50, 0.75]],
        "LIQUID_FILL_LINE": [[0.30, 0.45], [0.70, 0.45]],
        "BODY_TO_CLOSURE": [[0.50, 0.60], [0.50, 0.25]],
    }
    needed_polyline_ids = {
        polyline_id
        for requirement in active_requirements
        for polyline_id in (
            requirement.get("polyline_ids", [])
            + [edge["polyline_id"] for edge in requirement.get("edges", [])]
        )
    }
    line_geometry = {
        key: value for key, value in line_geometry.items() if key in needed_polyline_ids
    }
    polylines = [{
        "polyline_id": polyline_id, "view_id": view_id,
        "asset_file_sha256": asset_by_view[view_id]["file_sha256"],
        "region_id": None, "points_normalized": coordinates,
    } for view_id in minimum_views for polyline_id, coordinates in line_geometry.items()]
    needed_polygon_ids = {
        polygon_id
        for requirement in active_requirements
        for polygon_id in (
            requirement.get("polygon_ids", [])
            + (requirement.get("structure_ids", []) if requirement.get("region_structure_type") == "polygons" else [])
        )
    }
    polygons: list[dict[str, Any]] = []
    for index, view_id in enumerate(ring_views):
        geometry_by_id = {
            "MATERIAL_REFERENCE_REGION": MATERIAL_REFERENCE_POLYGON,
            "PRODUCT_SILHOUETTE": silhouette_polygon_for_ring_index(index, len(ring_views)),
            "SHOWTHROUGH_REFERENCE_REGION": MATERIAL_REFERENCE_POLYGON,
        }
        polygons.extend({
            "polygon_id": polygon_id, "view_id": view_id,
            "asset_file_sha256": asset_by_view[view_id]["file_sha256"],
            "region_id": None, "points_normalized": geometry_by_id[polygon_id],
        } for polygon_id in sorted(needed_polygon_ids.intersection(geometry_by_id)))
    if "LABEL_SURFACE_REGION" in needed_polygon_ids:
        polygons.extend({
            "polygon_id": "LABEL_SURFACE_REGION", "view_id": view_id,
            "asset_file_sha256": asset_by_view[view_id]["file_sha256"], "region_id": REGION_ID,
            "points_normalized": label_polygon_for_view(view_id),
        } for view_id in minimum_views)
    needed_mask_ids = {
        mask_id
        for requirement in active_requirements
        for mask_id in requirement.get("mask_ids", [])
    }
    masks = [{
        "mask_id": "EMBOSSING_REGION_MASK", "view_id": view_id,
        "asset_file_sha256": asset_by_view[view_id]["file_sha256"], "region_id": None,
        "encoding": "polygon_normalized",
        "polygon_normalized": [[0.40, 0.30], [0.60, 0.30], [0.60, 0.50], [0.40, 0.50]],
    } for view_id in minimum_views if "EMBOSSING_REGION_MASK" in needed_mask_ids]
    write_json(root / annotation_locator, {
        "schema_version": "packaging-continuity-annotation.v2",
        "annotation_id": annotation_id, "annotation_type": "raw_geometry_json",
        "view_ids": ring_views, "asset_file_sha256s": ring_hashes, "region_ids": [REGION_ID],
        "landmarks": landmarks, "polylines": polylines, "polygons": polygons,
        "mask_rle_or_polygon": masks,
    })
    semantic_locator = "07_qa/continuity_semantic_evidence.json"
    annotation_declaration = {
        "annotation_id": annotation_id, "annotation_type": "raw_geometry_json",
        "annotation_path": annotation_locator, "annotation_sha256": sha256_file(root / annotation_locator),
        "view_ids": ring_views, "asset_file_sha256s": ring_hashes, "region_ids": [REGION_ID],
    }
    gate_measurements = []
    metadata_keys = {"algorithm_id", "comparator", "hard_tolerance", "unit", "view_policy"}
    for gate_id in sorted(required_gates):
        requirement = continuity_builder.GATE_REQUIREMENTS[gate_id]
        algorithm_id = requirement["algorithm_id"]
        parameters = {
            key: json.loads(json.dumps(value))
            for key, value in requirement.items() if key not in metadata_keys
        }
        if requirement["view_policy"] == "all_ring":
            parameters["view_ids"] = ring_views
            hashes = ring_hashes
        elif requirement["view_policy"] == "minimum_two":
            parameters["view_ids"] = minimum_views
            hashes = [asset_by_view[view_id]["file_sha256"] for view_id in minimum_views]
        else:
            hashes = all_final_hashes
            if algorithm_id == "post_copy_verification_lock":
                parameters = {
                    "post_composite_verification_path": "07_qa/post_composite_verification.json",
                    "post_composite_verification_sha256": sha256_file(root / "07_qa/post_composite_verification.json"),
                }
        if algorithm_id == "loop_pose_conditioned_landmark_vector_error":
            parameters.update({
                "from_view_id": ring_views[-1],
                "to_view_id": ring_views[0],
                "aggregation": "max",
            })
        region_scope = gate_id == "label_surface_binding_gate"
        gate_measurements.append({
            "gate_id": gate_id,
            "metric_records": [{
                "metric_id": f"{gate_id}:deterministic_{algorithm_id}",
                "algorithm_id": algorithm_id,
                "parameters": parameters,
                "annotation_ids": [] if algorithm_id in {"board_input_binding", "post_copy_verification_lock"} else [annotation_id],
                "tolerance": requirement["hard_tolerance"],
                "comparator": requirement["comparator"],
                "asset_file_sha256s": hashes,
                "measurement_scope": {
                    "scope_type": "region" if region_scope else "whole_product",
                    "region_ids": [REGION_ID] if region_scope else [],
                },
                "unit": requirement["unit"],
            }],
        })
    edge_measurements = []
    for from_view, to_view in continuity_edge_pairs(coverage["rotation_profile"]):
        edge_id = f"{from_view}__TO__{to_view}"
        from_hash = asset_by_view[from_view]["file_sha256"]
        to_hash = asset_by_view[to_view]["file_sha256"]
        edge_measurements.append({
            "edge_id": edge_id,
            "from_view_id": from_view,
            "to_view_id": to_view,
            "metric_records": [{
                "metric_id": f"{edge_id}:deterministic_edge_displacement",
                "algorithm_id": continuity_builder.EDGE_REQUIREMENT["algorithm_id"],
                "parameters": {
                    "from_view_id": from_view,
                    "to_view_id": to_view,
                    "landmark_ids": continuity_builder.EDGE_REQUIREMENT["landmark_ids"],
                    "aggregation": continuity_builder.EDGE_REQUIREMENT["aggregation"],
                    "calibration_id": continuity_builder.EDGE_REQUIREMENT["calibration_id"],
                },
                "annotation_ids": [annotation_id],
                "tolerance": continuity_builder.EDGE_REQUIREMENT["hard_tolerance"],
                "comparator": continuity_builder.EDGE_REQUIREMENT["comparator"],
                "asset_file_sha256s": [from_hash, to_hash],
                "measurement_scope": {"scope_type": "whole_product", "region_ids": []},
                "unit": continuity_builder.EDGE_REQUIREMENT["unit"],
            }],
        })
    write_json(root / semantic_locator, {
        "schema_version": "packaging-continuity-semantic-evidence.v2",
        "input_locks": {
            "source_manifest_path": "00_source/source_manifest.json",
            "source_manifest_sha256": sha256_file(root / "00_source/source_manifest.json"),
            "asset_qa_path": "07_qa/asset_qa.json",
            "asset_qa_sha256": sha256_file(root / "07_qa/asset_qa.json"),
            "coverage_matrix_path": "02_coverage/coverage_matrix.json",
            "coverage_matrix_sha256": sha256_file(root / "02_coverage/coverage_matrix.json"),
            "continuity_contract_path": "02_coverage/continuity_contract.json",
            "continuity_contract_sha256": sha256_file(root / "02_coverage/continuity_contract.json"),
        },
        "annotations": [annotation_declaration],
        "gate_measurements": gate_measurements,
        "edge_measurements": edge_measurements,
    })
    run_continuity_builder(root)


def create_complete_run(root: Path) -> None:
    create_ready_run(root, include_codes=True)
    manifest_path = root / "00_manifest/run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    coverage = json.loads((root / manifest["paths"]["coverage_matrix"]).read_text(encoding="utf-8"))
    source_manifest = json.loads((root / manifest["paths"]["source_manifest"]).read_text(encoding="utf-8"))
    sources_by_id = {item["source_id"]: item for item in source_manifest["sources"]}
    prompt_index = json.loads((root / manifest["paths"]["generation_prompt_index"]).read_text(encoding="utf-8"))
    prompts = {item["view_id"]: item for item in prompt_index["prompts"]}
    composition_plan = json.loads((root / manifest["paths"]["composition_plan"]).read_text(encoding="utf-8"))
    bundle = json.loads((root / manifest["paths"]["exact_copy_bundle"]).read_text(encoding="utf-8"))
    asset_records: list[dict[str, Any]] = []
    post_results: list[dict[str, Any]] = []

    for index, view in enumerate(coverage["views"]):
        view_id = view["view_id"]
        asset_id = view["asset_id"]
        prompt = prompts[view_id]
        raw_locator = f"05_masters_raw/{view['family']}/{view_id}.png"
        raw_path = root / raw_locator
        write_master_image(raw_path, index + 1)
        generation_receipt_locator = f"07_qa/generation_receipts/{view_id}.json"
        submitted_bindings = []
        for source_id in view["source_refs"]:
            source = sources_by_id[source_id]
            submitted_bindings.append({
                "role": "source_reference", "reference_id": source_id, "source_id": source_id,
                "locator": source["file_path"], "file_sha256": source["file_sha256"],
            })
        for parent_view_id in view["parent_anchor_view_ids"]:
            source_id = next(
                source_id for source_id in view["source_refs"]
                if sources_by_id[source_id]["view_id"] == parent_view_id
            )
            source = sources_by_id[source_id]
            submitted_bindings.append({
                "role": "parent_anchor", "reference_id": parent_view_id, "source_id": source_id,
                "locator": source["file_path"], "file_sha256": source["file_sha256"],
            })
        submitted_bindings.sort(key=lambda item: (item["role"], item["reference_id"], item["source_id"]))
        binding_payload = json.dumps(
            submitted_bindings, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
        )
        attempt_root = root / f"07_qa/worker_attempts/{view_id}/A01"
        frozen_entries: list[dict[str, Any]] = []
        submitted_frozen: list[dict[str, Any]] = []
        for rank, source_id in enumerate(view["source_refs"], 1):
            source = sources_by_id[source_id]
            source_path = root / source["file_path"]
            frozen_path = attempt_root / "references" / f"{rank:02d}_{source_id.lower()}{source_path.suffix}"
            frozen_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, frozen_path)
            frozen_sha = sha256_file(frozen_path)
            frozen_entries.append({
                "index": rank,
                "alias": source_id,
                "frozen_path": str(frozen_path),
                "size_bytes": frozen_path.stat().st_size,
                "sha256": frozen_sha,
            })
            submitted_frozen.append({
                "rank": rank,
                "reference_id": source_id,
                "frozen_path": str(frozen_path.relative_to(root)).replace("\\", "/"),
                "file_sha256": frozen_sha,
            })
        frozen_payload = json.dumps(
            frozen_entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
        )
        reference_manifest_locator = f"07_qa/worker_attempts/{view_id}/A01/reference_manifest.json"
        reference_manifest = {
            "schema_version": "packaging_reference_bundle.v1",
            "immutability_contract": "no_writes_after_freeze; resolver_rehash_required",
            "ordered_references": frozen_entries,
            "ordered_bundle_sha256": hashlib.sha256(frozen_payload.encode("utf-8")).hexdigest(),
        }
        write_json(root / reference_manifest_locator, reference_manifest)
        worker_result_locator = f"07_qa/worker_attempts/{view_id}/A01/worker_result.json"
        nonce = f"{index + 1:032x}"
        worker_result = {
            "ok": True,
            "contract": "delegated_image_worker_result.v1",
            "resolved_at_utc": "2026-07-13T00:00:00+00:00",
            "agent_path": f"/root/packaging_{view_id}_A01_{nonce}",
            "worker_thread_id": f"worker-thread-{view_id}",
            "worker_turn_id": f"worker-turn-{view_id}",
            "parent_thread_id": "contract-parent-thread",
            "worker_rollout_path": str(attempt_root / "worker-rollout.jsonl"),
            "image_generation_call_id": f"image-call-{view_id}",
            "worker_saved_path": str(attempt_root / "generated.png"),
            "run_image_path": str(raw_path),
            "image_sha256": sha256_file(raw_path),
            "width_px": MASTER_SIZE[0],
            "height_px": MASTER_SIZE[1],
            "observed_aspect_ratio": MASTER_SIZE[0] / MASTER_SIZE[1],
            "exact_16_9": True,
            "generation_prompt_sha256": prompt["prompt_sha256"],
            "tool_prompt_sha256": prompt["prompt_sha256"],
            "prompt_sha_match": True,
            "prompt_binding_mode": "image_event_revised_prompt",
            "image_wrapper_candidate_count": 1,
            "reference_mode": "frozen_manifest",
            "reference_manifest_path": str(root / reference_manifest_locator),
            "reference_manifest_sha256": sha256_file(root / reference_manifest_locator),
            "ordered_reference_bundle_sha256": reference_manifest["ordered_bundle_sha256"],
            "reference_count": len(frozen_entries),
        }
        write_json(root / worker_result_locator, worker_result)
        submitted_payload = json.dumps(
            submitted_frozen, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
        )
        write_json(root / generation_receipt_locator, {
            "schema_version": "packaging-generation-receipt.v2",
            "asset_id": asset_id,
            "view_id": view_id,
            "prompt_sha256": prompt["prompt_sha256"],
            "output_path": raw_locator,
            "output_file_sha256": sha256_file(raw_path),
            "generation_mode": "independent_full_frame",
            "worker_transport_mode": "delegated_single_image_worker",
            "output_pixel_dimensions": {"width": MASTER_SIZE[0], "height": MASTER_SIZE[1]},
            "post_generation_resize_applied": False,
            "reference_ids": view["source_refs"],
            "source_reference_bindings": submitted_bindings,
            "submitted_reference_bindings": submitted_frozen,
            "submitted_reference_set_sha256": hashlib.sha256(submitted_payload.encode("utf-8")).hexdigest(),
            "worker_provenance": {
                "contract": worker_result["contract"],
                "result_path": worker_result_locator,
                "result_sha256": sha256_file(root / worker_result_locator),
                "agent_path": worker_result["agent_path"],
                "worker_thread_id": worker_result["worker_thread_id"],
                "worker_turn_id": worker_result["worker_turn_id"],
                "parent_thread_id": worker_result["parent_thread_id"],
                "image_generation_call_id": worker_result["image_generation_call_id"],
                "prompt_binding_mode": worker_result["prompt_binding_mode"],
                "reference_manifest_path": reference_manifest_locator,
                "reference_manifest_sha256": sha256_file(root / reference_manifest_locator),
                "ordered_reference_bundle_sha256": reference_manifest["ordered_bundle_sha256"],
            },
        })

        final_locator = f"05_masters/{view['family']}/{view_id}.png"
        receipt_locator = f"07_qa/composition_receipts/{view_id}.json"
        job_locator = f"07_qa/composition_jobs/{view_id}.json"
        job: dict[str, Any] = {
            "schema_version": "packaging-exact-copy-composition-job.v1",
            "asset_id": asset_id,
            "view_id": view_id,
            "prompt_sha256": prompt["prompt_sha256"],
            "composition_plan_id": composition_plan["plan_id"],
            "composition_plan_sha256": manifest["hashes"]["composition_plan_sha256"],
            "exact_copy_bundle_sha256": bundle["exact_copy_bundle_sha256"],
            "base_asset": {"path": raw_locator, "file_sha256": sha256_file(raw_path)},
            "layers": composition_layers(root, view),
            "output_path": final_locator,
            "receipt_path": receipt_locator,
            "job_sha256": None,
        }
        job["job_sha256"] = canonical_hash(job, "job_sha256")
        write_json(root / job_locator, job)
        summary = run_command([
            sys.executable,
            str(SKILL_DIR / "scripts/compose_exact_copy.py"),
            "--run-root", str(root),
            "--job", str(root / job_locator),
        ], f"exact-copy compositor {view_id}")
        if summary.get("status") != "PASS":
            raise AssertionError(f"exact-copy compositor did not pass for {view_id}")
        final_path = root / final_locator
        final_sha = sha256_file(final_path)
        post_ocr_locator, field_results, code_results = write_post_ocr_evidence(
            root, view, asset_id, final_locator, final_sha, job,
        )

        graphic_results: list[dict[str, Any]] = []
        if view["graphic_ids_visible"]:
            composition_receipt = json.loads((root / receipt_locator).read_text(encoding="utf-8"))
            comparison_locator, comparison_sha, comparison_passed, comparison_reasons = (
                post_adapter.build_graphic_comparison_receipt(
                    root, view_id, GRAPHIC_ID,
                    {"asset_id": asset_id, "file_sha256": final_sha},
                    job, root / receipt_locator, composition_receipt,
                    {"asset_sha256": sha256_file(root / "00_source/front_label_rectified.png")},
                    MASTER_SIZE, True, False,
                )
            )
            if not comparison_passed or not comparison_locator or not comparison_sha:
                raise AssertionError(
                    f"bundled graphic comparison did not pass for {view_id}: {comparison_reasons}"
                )
            graphic_results.append({
                "graphic_id": GRAPHIC_ID,
                "source_graphic_sha256": sha256_file(root / "00_source/front_label_rectified.png"),
                "comparison_status": "matched",
                "comparison_receipt_path": comparison_locator,
                "comparison_receipt_sha256": comparison_sha,
            })
        post_results.append({
            "result_id": f"POST_{asset_id}",
            "asset_id": asset_id,
            "view_id": view_id,
            "asset_file_sha256": final_sha,
            "composition_receipt_path": receipt_locator,
            "composition_receipt_sha256": sha256_file(root / receipt_locator),
            "post_ocr_evidence_path": post_ocr_locator,
            "post_ocr_evidence_sha256": sha256_file(root / post_ocr_locator),
            "field_results": field_results,
            "code_results": code_results,
            "graphic_results": graphic_results,
        })
        asset_records.append({
            "asset_id": asset_id,
            "view_id": view_id,
            "family": view["family"],
            "raw_file_path": raw_locator,
            "raw_file_sha256": sha256_file(raw_path),
            "file_path": final_locator,
            "file_sha256": final_sha,
            "generation_prompt_sha256": prompt["prompt_sha256"],
            "generation_receipt_path": generation_receipt_locator,
            "generation_receipt_sha256": sha256_file(root / generation_receipt_locator),
            "independently_generated": True,
            "derived_from_multipanel": False,
            "assistant_qa_status": "passed",
            "text_pollution_status": "passed",
            "copy_composition_status": "passed",
            "post_verification_status": "passed",
        })

    asset_qa_path = root / "07_qa/asset_qa.json"
    write_json(asset_qa_path, {
        "schema_version": "packaging-asset-qa.v1",
        "assets": asset_records,
        "review_boards": [],
    })
    review_boards = build_review_boards(root, asset_qa_path)
    write_json(asset_qa_path, {
        "schema_version": "packaging-asset-qa.v1",
        "assets": asset_records,
        "review_boards": review_boards,
    })

    write_json(root / "07_qa/post_composite_verification.json", {
        "schema_version": "packaging-post-composite-verification.v1",
        "candidate_provenance": {
            "adapter_path": "scripts/run_post_composite_verification.py",
            "adapter_sha256": sha256_file(SKILL_DIR / "scripts/run_post_composite_verification.py"),
            "run_manifest_path": "00_manifest/run_manifest.json",
            "run_manifest_sha256": sha256_file(manifest_path),
            "engine_id": "bundled_macos_vision_ocr",
            "engine_script_path": "scripts/macos_vision_ocr.swift",
            "engine_script_sha256": sha256_file(SKILL_DIR / "scripts/macos_vision_ocr.swift"),
            "uses_language_correction": False,
        },
        "asset_results": post_results,
        "copy_content_lock_status": "approved",
        "label_artwork_lock_status": "approved",
        "code_payload_lock_status": "approved",
        "code_symbol_lock_status": "approved",
        "logo_graphic_lock_status": "approved",
        "exact_copy_lock_status": "approved",
    })
    build_continuity_artifacts(root, asset_records)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["stage"] = "COMPLETE"
    manifest["production_approval_status"] = "user_granted"
    write_json(manifest_path, manifest)
    relock(root)


def mutate_json(root: Path, locator: str, mutator: Callable[[dict[str, Any]], None]) -> None:
    path = root / locator
    value = json.loads(path.read_text(encoding="utf-8"))
    mutator(value)
    write_json(path, value)


def rewrite_region_as_zero_text_non_text(root: Path, purpose: str) -> None:
    spec_path = root / "01_ocr/front_region_spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["regions"][0]["region_purpose"] = purpose
    write_json(spec_path, spec)
    spec_sha = sha256_file(spec_path)

    receipt_path = root / "01_ocr/front_region_crop_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["region_purpose"] = purpose
    receipt["region_spec_sha256"] = spec_sha
    receipt["receipt_sha256"] = canonical_hash(receipt, "receipt_sha256")
    write_json(receipt_path, receipt)

    ledger_path = root / "01_ocr/ocr_observations.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    front = next(
        item for item in ledger["source_records"]
        if item["source_id"] == SOURCE_BY_ROLE["front"]
    )
    front["text_observations"] = [
        item for item in front["text_observations"] if item.get("scope") != "region"
    ]
    region_pass = front["region_ocr_passes"][0]
    region_pass["region_purpose"] = purpose
    region_pass["region_spec_sha256"] = spec_sha
    region_pass["crop_receipt_sha256"] = sha256_file(receipt_path)
    region_pass["crop_receipt_semantic_sha256"] = receipt["receipt_sha256"]
    region_pass["observation_count"] = 0
    region_pass["zero_detection_review_status"] = "not_applicable_non_text_region"
    if purpose == "code":
        front["code_observations"] = [{
            "code_id": "SRC_FRONT_CODE_001",
            "symbology": "EAN-13",
            "payload": "2901234567896",
            "bounding_box_normalized": {
                "x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0,
            },
            "disposition": {
                "status": "mapped_to_code",
                "review_status": "reviewed",
                "reviewer_id": "QA_REVIEWER_01",
                "manifest_code_id": "CODE_REGION_ONLY",
                "evidence_note": "Named reviewer confirmed the decoded source symbol in the replayed crop.",
            },
        }]
    ledger["ledger_semantic_sha256"] = canonical_hash(ledger, "ledger_semantic_sha256")
    write_json(ledger_path, ledger)


def assert_zero_text_non_text_region_contract(ready: Path) -> None:
    for purpose in ("code", "graphic"):
        root = ready.parent / f"zero_text_{purpose}_region_provenance"
        shutil.copytree(ready, root)
        rewrite_region_as_zero_text_non_text(root, purpose)
        source_manifest = json.loads(
            (root / "00_source/source_manifest.json").read_text(encoding="utf-8")
        )
        errors: list[str] = []
        sources = validate_sources(root, source_manifest, PRODUCT_ID, STATE_ID, errors)
        ledger = json.loads((root / "01_ocr/ocr_observations.json").read_text(encoding="utf-8"))
        _, _, code_observations, region_authorities = validate_ocr(
            root, ledger, sources, errors,
        )
        if errors:
            raise AssertionError(
                f"zero-text {purpose}-only replayed crop failed provenance validation:\n"
                + "\n".join(errors)
            )

        inventory = json.loads(
            (root / "00_source/surface_inventory.json").read_text(encoding="utf-8")
        )
        front_surface = next(
            item for item in inventory["surfaces"]
            if item["surface_id"] == SURFACE_BY_ROLE["front"]
        )
        front_surface["required_copy_field_ids"] = []
        front_surface["text_detection_status"] = "decorative_graphic"
        surface_ids = set(SURFACE_BY_ROLE.values())
        crop_only_errors: list[str] = []
        validate_region_authority_modalities(
            inventory, region_authorities, {}, {}, {}, crop_only_errors,
        )
        if not any("differs from bound manifest modalities" in item for item in crop_only_errors):
            raise AssertionError(
                f"zero-text {purpose}-only crop provenance self-authorized without downstream evidence"
            )
        code_records: dict[str, dict[str, Any]] = {}
        graphic_records: dict[str, dict[str, Any]] = {}
        if purpose == "code":
            code_manifest = {
                "schema_version": "packaging-code-manifest.v1",
                "required_codes_present": True,
                "codes": [{
                    "code_id": "CODE_REGION_ONLY",
                    "surface_id": SURFACE_BY_ROLE["front"],
                    "region_id": REGION_ID,
                    "required": True,
                    "symbology": "EAN-13",
                    "expected_payload": "2901234567896",
                    "decoded_payload": "2901234567896",
                    "payload_match": True,
                    "checksum_result": "passed",
                    "authority_source_ids": [SOURCE_BY_ROLE["front"]],
                    "ocr_code_observation_ids": ["SRC_FRONT_CODE_001"],
                    "printed_symbol_asset_path": "00_source/front_label_rectified.png",
                    "printed_symbol_asset_sha256": sha256_file(
                        root / "00_source/front_label_rectified.png"
                    ),
                    "status": "verified",
                }],
            }
            code_records = validate_codes(
                code_manifest, root, {"CODE_REGION_ONLY"}, surface_ids, sources,
                code_observations, region_authorities, errors,
            )
        else:
            graphic_manifest = {
                "schema_version": "packaging-logo-graphic-manifest.v1",
                "graphics": [{
                    "graphic_id": "GRAPHIC_REGION_ONLY",
                    "graphic_role": "brand_logo",
                    "surface_id": SURFACE_BY_ROLE["front"],
                    "region_id": REGION_ID,
                    "required": True,
                    "authority_source_ids": [SOURCE_BY_ROLE["front"]],
                    "asset_path": "00_source/front_label_rectified.png",
                    "asset_sha256": sha256_file(root / "00_source/front_label_rectified.png"),
                    "status": "verified",
                    "disposition": {
                        "status": "mapped_to_graphic",
                        "review_status": "reviewed",
                        "reviewer_id": "QA_REVIEWER_01",
                        "manifest_graphic_id": "GRAPHIC_REGION_ONLY",
                        "evidence_note": "Named reviewer matched the replayed source crop to the graphic record.",
                    },
                }],
            }
            graphic_records = validate_graphics(
                graphic_manifest, root, {"GRAPHIC_REGION_ONLY"}, surface_ids,
                sources, region_authorities, errors,
            )
        validate_region_authority_modalities(
            inventory, region_authorities, {}, code_records, graphic_records, errors,
        )
        if errors:
            raise AssertionError(
                f"zero-text {purpose}-only region failed downstream disposition closure:\n"
                + "\n".join(errors)
            )

        if purpose == "code":
            bad_ledger = json.loads(json.dumps(ledger))
            bad_front = next(
                item for item in bad_ledger["source_records"]
                if item["source_id"] == SOURCE_BY_ROLE["front"]
            )
            bad_front["code_observations"][0]["disposition"]["reviewer_id"] = None
            bad_ledger["ledger_semantic_sha256"] = canonical_hash(
                bad_ledger, "ledger_semantic_sha256"
            )
            negative_errors: list[str] = []
            validate_ocr(root, bad_ledger, sources, negative_errors)
            if not any("decoded-code disposition requires named human review" in item for item in negative_errors):
                raise AssertionError("code-only zero-text region passed without a named decode reviewer")
    print("PASS zero-text code/graphic region crop provenance plus downstream disposition gates")


def assert_invalid(
    base: Path,
    name: str,
    mutation: Callable[[Path], None],
    expected: str,
    *,
    do_relock: bool = True,
) -> None:
    target = base.parent / name
    shutil.copytree(base, target)
    mutation(target)
    if do_relock:
        relock(target)
    errors = validate_run(target)
    if not errors:
        raise AssertionError(f"{name}: invalid run unexpectedly passed")
    joined = "\n".join(errors)
    if expected not in joined:
        raise AssertionError(f"{name}: expected {expected!r}; got:\n{joined}")
    print(f"PASS expected failure: {name}")


def mutate_four_dimensional_needs_source(root: Path) -> None:
    def apply(data: dict[str, Any]) -> None:
        view = next(item for item in data["views"] if item["view_id"] == "ROT_0450")
        for key in ("pose_source_status", "surface_source_status", "copy_source_status", "material_source_status"):
            view[key] = "needs_source"
    mutate_json(root, "02_coverage/coverage_matrix.json", apply)


def mutate_all_angles_front(root: Path) -> None:
    def apply(data: dict[str, Any]) -> None:
        for view in data["views"]:
            if view["shot_scale"] == "full_product":
                view["visible_surface_ids"] = [SURFACE_BY_ROLE["front"]]
                view["source_refs"] = [SOURCE_BY_ROLE["front"]]
    mutate_json(root, "02_coverage/coverage_matrix.json", apply)


def mutate_spatial_source_to_artwork_anchor(root: Path) -> None:
    def apply(data: dict[str, Any]) -> None:
        source = next(item for item in data["sources"] if item["source_id"] == SOURCE_BY_ROLE["front"])
        source["source_kind"] = "approved_artwork"
        source["applies_to_surface_ids"] = [SURFACE_BY_ROLE["front"]]
    mutate_json(root, "00_source/source_manifest.json", apply)


def mutate_missing_feature_audit_row(root: Path) -> None:
    mutate_json(
        root, "00_source/source_manifest.json",
        lambda data: data["product_feature_classification"].pop(),
    )


def mutate_impossible_extra_surface(root: Path) -> None:
    def apply(data: dict[str, Any]) -> None:
        view = next(item for item in data["views"] if item["view_id"] == "ROT_0000")
        view["visible_surface_ids"].append(SURFACE_BY_ROLE["back"])
        view["source_refs"].append(SOURCE_BY_ROLE["back"])
    mutate_json(root, "02_coverage/coverage_matrix.json", apply)


def mutate_inferred_high_claims_direct_source(root: Path) -> None:
    def apply(data: dict[str, Any]) -> None:
        view = next(item for item in data["views"] if item["view_id"] == "HIGH_0000")
        view.update({
            "derivation_status": "source",
            "pose_source_status": "source_verified",
            "surface_source_status": "source_verified",
            "copy_source_status": "source_verified",
            "material_source_status": "source_verified",
            "parent_anchor_view_ids": [],
        })
    mutate_json(root, "02_coverage/coverage_matrix.json", apply)


def mutate_generated_detail_claims_direct_source(root: Path) -> None:
    def apply(data: dict[str, Any]) -> None:
        view = next(item for item in data["views"] if item["view_id"] == "DETAIL_CLOSURE_TOP")
        view.update({
            "derivation_status": "source",
            "pose_source_status": "source_verified",
            "surface_source_status": "source_verified",
            "copy_source_status": "not_applicable_no_visible_content",
            "material_source_status": "source_verified",
            "parent_anchor_view_ids": [],
        })
    mutate_json(root, "02_coverage/coverage_matrix.json", apply)


def mutate_black_region_crop(root: Path) -> None:
    crop_path = root / "00_source/front_label_rectified.png"
    write_image(crop_path, (0, 0, 0), (128, 72))
    crop_sha = sha256_file(crop_path)
    receipt_path = root / "01_ocr/front_region_crop_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["rectified_crop_sha256"] = crop_sha
    receipt["receipt_sha256"] = canonical_hash(receipt, "receipt_sha256")
    write_json(receipt_path, receipt)
    ocr_path = root / "01_ocr/ocr_observations.json"
    ocr = json.loads(ocr_path.read_text(encoding="utf-8"))
    front = next(item for item in ocr["source_records"] if item["source_id"] == SOURCE_BY_ROLE["front"])
    region_pass = front["region_ocr_passes"][0]
    region_pass["rectified_crop_sha256"] = crop_sha
    region_pass["crop_receipt_semantic_sha256"] = receipt["receipt_sha256"]
    region_pass["crop_receipt_sha256"] = sha256_file(receipt_path)
    write_json(ocr_path, ocr)
    mutate_json(root, "01_ocr/exact_copy_text_ssot.json", lambda data: data["fields"][0].update({"authority_asset_sha256": crop_sha}))
    mutate_json(root, "01_ocr/logo_graphic_manifest.json", lambda data: data["graphics"][0].update({"asset_sha256": crop_sha}))


def mutate_text_region_to_zero_detections(root: Path) -> None:
    path = root / "01_ocr/ocr_observations.json"
    ledger = json.loads(path.read_text(encoding="utf-8"))
    front = next(
        item for item in ledger["source_records"]
        if item["source_id"] == SOURCE_BY_ROLE["front"]
    )
    front["text_observations"] = [
        item for item in front["text_observations"] if item.get("scope") != "region"
    ]
    region_pass = front["region_ocr_passes"][0]
    region_pass["observation_count"] = 0
    region_pass["zero_detection_review_status"] = "review_required"
    ledger["ledger_semantic_sha256"] = canonical_hash(ledger, "ledger_semantic_sha256")
    write_json(path, ledger)


def mutate_region_pass_authority_binding(root: Path, key: str, value: str) -> None:
    path = root / "01_ocr/ocr_observations.json"
    ledger = json.loads(path.read_text(encoding="utf-8"))
    front = next(
        item for item in ledger["source_records"]
        if item["source_id"] == SOURCE_BY_ROLE["front"]
    )
    front["region_ocr_passes"][0][key] = value
    for observation in front["text_observations"]:
        if observation.get("scope") == "region":
            observation[key] = value
    ledger["ledger_semantic_sha256"] = canonical_hash(ledger, "ledger_semantic_sha256")
    write_json(path, ledger)


def mutate_region_receipt_authority_binding(root: Path) -> None:
    receipt_path = root / "01_ocr/front_region_crop_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["physical_layer_id"] = "tampered_unowned_layer"
    receipt["receipt_sha256"] = canonical_hash(receipt, "receipt_sha256")
    write_json(receipt_path, receipt)
    ledger_path = root / "01_ocr/ocr_observations.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    front = next(
        item for item in ledger["source_records"]
        if item["source_id"] == SOURCE_BY_ROLE["front"]
    )
    region_pass = front["region_ocr_passes"][0]
    region_pass["crop_receipt_sha256"] = sha256_file(receipt_path)
    region_pass["crop_receipt_semantic_sha256"] = receipt["receipt_sha256"]
    ledger["ledger_semantic_sha256"] = canonical_hash(ledger, "ledger_semantic_sha256")
    write_json(ledger_path, ledger)


def mutate_fake_whole_ocr_engine(root: Path) -> None:
    path = root / "01_ocr/ocr_observations.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["engine"] = "fake_ocr"
    for record in data["source_records"]:
        for ocr_pass in record["whole_product_ocr_passes"]:
            ocr_pass["engine_id"] = "fake_ocr"
    data["ledger_semantic_sha256"] = canonical_hash(data, "ledger_semantic_sha256")
    write_json(path, data)


def mutate_text_authority_to_unrelated_image(root: Path) -> None:
    unrelated = "03_composition/layers/neutral_patch.png"
    mutate_json(
        root, "01_ocr/exact_copy_text_ssot.json",
        lambda data: data["fields"][0].update({
            "authority_asset_path": unrelated,
            "authority_asset_sha256": sha256_file(root / unrelated),
        }),
    )


def mutate_graphic_authority_to_unrelated_image(root: Path) -> None:
    unrelated = "03_composition/layers/neutral_patch.png"
    mutate_json(
        root, "01_ocr/logo_graphic_manifest.json",
        lambda data: data["graphics"][0].update({
            "asset_path": unrelated,
            "asset_sha256": sha256_file(root / unrelated),
        }),
    )


def mutate_unknown_feature(root: Path) -> None:
    mutate_json(root, "00_source/source_manifest.json", lambda data: data["product_feature_classification"].append({
        "feature_id": "unknown_feature_typo",
        "status": "present",
        "evidence_source_ids": [SOURCE_BY_ROLE["front"]],
    }))
    mutate_json(root, "00_manifest/run_manifest.json", lambda data: data.update({"product_features": ["unknown_feature_typo"]}))


def mutate_present_feature_without_profile_upgrade(root: Path, feature_id: str) -> None:
    def source_apply(data: dict[str, Any]) -> None:
        item = next(record for record in data["product_feature_classification"] if record["feature_id"] == feature_id)
        item["status"] = "present"
        item["evidence_note"] = "Feature is directly visible but the malicious fixture keeps the lower rotation profile."
    mutate_json(root, "00_source/source_manifest.json", source_apply)
    mutate_json(
        root, "00_manifest/run_manifest.json",
        lambda data: data.update({"product_features": sorted(set(DEFAULT_PRODUCT_FEATURES) | {feature_id})}),
    )


def mutate_double_high_ring(root: Path) -> None:
    ring_ids = [view_id.replace("ROT_", "HIGH_") for view_id in PROFILES["rotation_profiles"]["R8"]["view_ids"]]
    def apply(data: dict[str, Any]) -> None:
        data["elevation_rings"] = [
            {"ring_id": "HIGH_RING_A", "view_prefix": "HIGH", "elevation_deg": 30.0, "view_ids": ring_ids, "loop_closure_required": True},
            {"ring_id": "HIGH_RING_B", "view_prefix": "HIGH", "elevation_deg": 45.0, "view_ids": ring_ids, "loop_closure_required": True},
        ]
    mutate_json(root, "02_coverage/motion_envelope.json", apply)


def mutate_fixed_detail_pose_semantics(root: Path) -> None:
    mutate_json(
        root, "02_coverage/coverage_matrix.json",
        lambda data: next(
            item for item in data["views"] if item["view_id"] == "DETAIL_CLOSURE_TOP"
        ).update({"elevation_deg": 0.0}),
    )


def mutate_remove_upper_bridge(root: Path) -> None:
    def apply(data: dict[str, Any]) -> None:
        data["views"] = [item for item in data["views"] if item["view_id"] != "UPPER_0900"]
    mutate_json(root, "02_coverage/coverage_matrix.json", apply)


def mutate_coalesce_dynamic_regions(root: Path) -> None:
    coverage_path = root / "02_coverage/coverage_matrix.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    ean_view_id = dynamic_region_detail_view_id(EAN_REGION_ID)
    qr_view_id = dynamic_region_detail_view_id(QR_REGION_ID)
    ean_view = next(item for item in coverage["views"] if item["view_id"] == ean_view_id)
    ean_view["label_region_ids"].append(QR_REGION_ID)
    ean_view["code_ids_visible"].append(QR_CODE_ID)
    ean_view["dynamic_region_contract"]["code_ids"].append(QR_CODE_ID)
    coverage["views"] = [item for item in coverage["views"] if item["view_id"] != qr_view_id]
    write_json(coverage_path, coverage)


def mutate_review_board_order(root: Path) -> None:
    def apply(data: dict[str, Any]) -> None:
        board = next(
            item for item in data["review_boards"]
            if item.get("semantic_board_role") == "neutral_rotation" and len(item.get("inputs") or []) >= 2
        )
        board["inputs"][0], board["inputs"][1] = board["inputs"][1], board["inputs"][0]
        board["ordered_view_ids"] = [item["view_id"] for item in board["inputs"]]
    mutate_json(root, "07_qa/asset_qa.json", apply)


def mutate_pitched_ring_missing(root: Path) -> None:
    def apply(data: dict[str, Any]) -> None:
        data["motion_type"] = "pitched_full_rotation"
        data["motion_scope"] = "high_full_360_rotation"
        data["elevation_rings"] = []
    mutate_json(root, "02_coverage/motion_envelope.json", apply)


def mutate_required_detail_content_omission(root: Path) -> None:
    def strip_coverage(data: dict[str, Any]) -> None:
        for view in data["views"]:
            if str(view.get("family", "")).startswith("detail"):
                view["label_region_ids"] = []
                view["ocr_field_ids_visible"] = []
                view["graphic_ids_visible"] = []
    def strip_plan(data: dict[str, Any]) -> None:
        for view in data["view_statuses"]:
            if view["view_id"].startswith("DETAIL_"):
                view["protected_region_ids"] = []
                view["ocr_field_ids_visible"] = []
                view["graphic_ids_visible"] = []
    mutate_json(root, "02_coverage/coverage_matrix.json", strip_coverage)
    mutate_json(root, "03_composition/deterministic_composition_plan.json", strip_plan)


def mutate_test_marker_job(root: Path) -> None:
    post_path = root / "07_qa/post_composite_verification.json"
    post = json.loads(post_path.read_text(encoding="utf-8"))
    result = next(item for item in post["asset_results"] if item["view_id"] == "ROT_0000")
    receipt_path = root / result["composition_receipt_path"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    job_path = root / receipt["composition_job_path"]
    job = json.loads(job_path.read_text(encoding="utf-8"))
    job["evidence_mode"] = "fixture_synthetic_job"
    job["job_sha256"] = canonical_hash(job, "job_sha256")
    write_json(job_path, job)
    receipt["composition_job_sha256"] = sha256_file(job_path)
    receipt["receipt_sha256"] = canonical_hash(receipt, "receipt_sha256")
    write_json(receipt_path, receipt)
    result["composition_receipt_sha256"] = sha256_file(receipt_path)
    write_json(post_path, post)


def mutate_extra_post_ocr(root: Path) -> None:
    post_path = root / "07_qa/post_composite_verification.json"
    post = json.loads(post_path.read_text(encoding="utf-8"))
    result = next(item for item in post["asset_results"] if item["view_id"] == "ROT_0000")
    ocr_path = root / result["post_ocr_evidence_path"]
    evidence = json.loads(ocr_path.read_text(encoding="utf-8"))
    evidence["observations"].append({
        "observation_id": "POST_ROT_0000_UNEXPECTED_TEXT",
        "field_id": FIELD_ID,
        "region_id": REGION_ID,
        "text": "UNEXPECTED",
        "text_sha256": hashlib.sha256(b"UNEXPECTED").hexdigest(),
        "product_native": True,
        "disposition": "mapped_to_expected_field",
    })
    write_json(ocr_path, evidence)
    result["post_ocr_evidence_sha256"] = sha256_file(ocr_path)
    write_json(post_path, post)


def mutate_contradictory_aggregate_raw(root: Path) -> None:
    post_path = root / "07_qa/post_composite_verification.json"
    post = json.loads(post_path.read_text(encoding="utf-8"))
    result = next(item for item in post["asset_results"] if item["field_results"])
    ocr_path = root / result["post_ocr_evidence_path"]
    evidence = json.loads(ocr_path.read_text(encoding="utf-8"))
    raw = evidence["raw_scan_observations"]["text"][0]
    raw["text"] = "CONTRADICTORY RAW BYTES"
    raw["observed_hash"] = hashlib.sha256(raw["text"].encode("utf-8")).hexdigest()
    write_json(ocr_path, evidence)
    result["post_ocr_evidence_sha256"] = sha256_file(ocr_path)
    write_json(post_path, post)


def mutate_forged_graphic_receipt(root: Path) -> None:
    post_path = root / "07_qa/post_composite_verification.json"
    post = json.loads(post_path.read_text(encoding="utf-8"))
    result = next(item for item in post["asset_results"] if item["graphic_results"])
    graphic_result = result["graphic_results"][0]
    receipt_path = root / graphic_result["comparison_receipt_path"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["comparison_adapter_sha256"] = "0" * 64
    receipt["deterministic_similarity"] = 1.0
    receipt["receipt_sha256"] = canonical_hash(receipt, "receipt_sha256")
    write_json(receipt_path, receipt)
    graphic_result["comparison_receipt_sha256"] = sha256_file(receipt_path)
    write_json(post_path, post)


def mutate_integrated_final_code_receipt_payload(root: Path) -> None:
    post_path = root / "07_qa/post_composite_verification.json"
    post = json.loads(post_path.read_text(encoding="utf-8"))
    result = next(item for item in post["asset_results"] if item["view_id"] == "ROT_1800")
    code_result = next(
        item for item in result["code_results"] if item["code_id"] == EAN_CODE_ID
    )
    receipt_path = root / code_result["decode_receipt_path"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["payload"] = "0000000000000"
    receipt["payload_sha256"] = hashlib.sha256(
        receipt["payload"].encode("utf-8")
    ).hexdigest()
    receipt["receipt_sha256"] = canonical_hash(receipt, "receipt_sha256")
    write_json(receipt_path, receipt)
    code_result["decode_receipt_sha256"] = sha256_file(receipt_path)
    write_json(post_path, post)


def assert_integrated_code_bearing_complete(root: Path) -> None:
    text_ssot = json.loads(
        (root / "01_ocr/exact_copy_text_ssot.json").read_text(encoding="utf-8")
    )
    if {item["field_id"] for item in text_ssot["fields"]} != {FIELD_ID, BACK_FIELD_ID}:
        raise AssertionError("integrated COMPLETE does not contain front and back exact Text SSOT fields")
    code_manifest = json.loads(
        (root / "01_ocr/code_manifest.json").read_text(encoding="utf-8")
    )
    if {item["code_id"] for item in code_manifest["codes"]} != {EAN_CODE_ID, QR_CODE_ID}:
        raise AssertionError("integrated COMPLETE does not contain both EAN-13 and QR source records")
    coverage = json.loads(
        (root / "02_coverage/coverage_matrix.json").read_text(encoding="utf-8")
    )
    coverage_by_view = {item["view_id"]: item for item in coverage["views"]}
    for view_id in ("ROT_1800", "DETAIL_BARCODE_QR_CERTIFICATION"):
        if set(coverage_by_view[view_id]["code_ids_visible"]) != {EAN_CODE_ID, QR_CODE_ID}:
            raise AssertionError(f"{view_id} does not expose both required codes")
    post = json.loads(
        (root / "07_qa/post_composite_verification.json").read_text(encoding="utf-8")
    )
    post_by_view = {item["view_id"]: item for item in post["asset_results"]}
    for view_id in ("ROT_1800", "DETAIL_BARCODE_QR_CERTIFICATION"):
        result = post_by_view[view_id]
        if {item["code_id"] for item in result["code_results"]} != {EAN_CODE_ID, QR_CODE_ID}:
            raise AssertionError(f"{view_id} post verification lacks both code results")
        for code_result in result["code_results"]:
            receipt_path = root / code_result["decode_receipt_path"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if (
                receipt.get("receipt_sha256") != canonical_hash(receipt, "receipt_sha256")
                or receipt.get("symbol_geometry_status") != "matched"
                or receipt.get("payload") not in {EAN_PAYLOAD, QR_PAYLOAD}
            ):
                raise AssertionError(f"{view_id}/{code_result['code_id']} semantic receipt is invalid")
        post_ocr = json.loads(
            (root / result["post_ocr_evidence_path"]).read_text(encoding="utf-8")
        )
        if (
            {item["code_id"] for item in post_ocr["code_observations"]}
            != {EAN_CODE_ID, QR_CODE_ID}
            or {item["candidate_ids"][0] for item in post_ocr["raw_scan_observations"]["codes"]}
            != {EAN_CODE_ID, QR_CODE_ID}
        ):
            raise AssertionError(f"{view_id} raw/canonical final code observations are incomplete")
    if any(
        post.get(key) != "approved"
        for key in (
            "copy_content_lock_status", "label_artwork_lock_status",
            "code_payload_lock_status", "code_symbol_lock_status",
            "logo_graphic_lock_status", "exact_copy_lock_status",
        )
    ):
        raise AssertionError("integrated COMPLETE top-level exact-copy approvals are not closed")
    print("PASS integrated code-bearing COMPLETE with back Text, EAN-13, QR, and semantic receipts")


def mutate_raw_equals_final(root: Path) -> None:
    qa_path = root / "07_qa/asset_qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    asset = next(item for item in qa["assets"] if item["view_id"] == "ROT_0000")
    asset["raw_file_path"] = asset["file_path"]
    asset["raw_file_sha256"] = asset["file_sha256"]
    receipt_path = root / asset["generation_receipt_path"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["output_path"] = asset["file_path"]
    receipt["output_file_sha256"] = asset["file_sha256"]
    write_json(receipt_path, receipt)
    asset["generation_receipt_sha256"] = sha256_file(receipt_path)
    write_json(qa_path, qa)


def mutate_one_master_reuse(root: Path) -> None:
    qa_path = root / "07_qa/asset_qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    first = qa["assets"][0]
    qa["assets"][1]["file_path"] = first["file_path"]
    qa["assets"][1]["file_sha256"] = first["file_sha256"]
    write_json(qa_path, qa)


def mutate_one_character_prompts(root: Path) -> None:
    index_path = root / "04_prompts/generation_prompt_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    for record in index["prompts"]:
        prompt_path = root / record["prompt_path"]
        prompt_path.write_text("x\n", encoding="utf-8")
        record["prompt_sha256"] = sha256_file(prompt_path)
    write_json(index_path, index)


def mutate_missing_review_board(root: Path) -> None:
    mutate_json(root, "07_qa/asset_qa.json", lambda data: data["review_boards"][0].update({
        "file_path": "06_review_boards/DOES_NOT_EXIST.png",
        "file_sha256": "0" * 64,
    }))


def rebind_continuity_qa_receipt(root: Path) -> None:
    receipt_locator = "07_qa/continuity_measurements.json"
    receipt_sha = sha256_file(root / receipt_locator)
    qa_path = root / "07_qa/continuity_qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    for result in [*qa["gate_results"], *qa["edge_results"]]:
        result["evidence_path"] = receipt_locator
        result["evidence_sha256"] = receipt_sha
    write_json(qa_path, qa)


def rewrite_continuity_receipt(
    root: Path, mutator: Callable[[dict[str, Any]], None], *, recompute_self_hash: bool = True,
) -> None:
    receipt_path = root / "07_qa/continuity_measurements.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    mutator(receipt)
    if recompute_self_hash:
        receipt["receipt_sha256"] = canonical_hash(receipt, "receipt_sha256")
    write_json(receipt_path, receipt)
    rebind_continuity_qa_receipt(root)


def retarget_receipt_to_changed_semantic_evidence(root: Path) -> None:
    semantic_sha = sha256_file(root / "07_qa/continuity_semantic_evidence.json")
    rewrite_continuity_receipt(
        root,
        lambda receipt: receipt["input_locks"].update({"semantic_evidence_sha256": semantic_sha}),
    )


def mutate_legacy_v1_continuity_receipt(root: Path) -> None:
    write_json(root / "07_qa/continuity_measurements.json", {
        "schema_version": "packaging-continuity-measurements.v1",
        "measurement_method": "legacy_status_only",
    })
    rebind_continuity_qa_receipt(root)


def mutate_empty_semantic_metrics(root: Path) -> None:
    mutate_json(
        root,
        "07_qa/continuity_semantic_evidence.json",
        lambda evidence: evidence["gate_measurements"][0].update({"metric_records": []}),
    )
    retarget_receipt_to_changed_semantic_evidence(root)


def mutate_manual_semantic_gate(root: Path) -> None:
    def apply(evidence: dict[str, Any]) -> None:
        metric = evidence["gate_measurements"][0]["metric_records"][0]
        metric["comparator"] = "manual"
        metric["tolerance"] = None
    mutate_json(root, "07_qa/continuity_semantic_evidence.json", apply)
    retarget_receipt_to_changed_semantic_evidence(root)


def mutate_blocked_semantic_gate(root: Path) -> None:
    mutate_json(
        root,
        "07_qa/continuity_semantic_evidence.json",
        lambda evidence: evidence["gate_measurements"].pop(0),
    )
    run_continuity_builder(root)


def mutate_fake_continuity_tool_hash(root: Path) -> None:
    rewrite_continuity_receipt(
        root,
        lambda receipt: receipt.update({"tool_script_sha256": "0" * 64}),
    )


def mutate_receipt_metric_and_self_hash(root: Path) -> None:
    def apply(receipt: dict[str, Any]) -> None:
        metric = receipt["gate_measurements"][0]["metric_records"][0]
        metric["value"] = -1
        metric["status"] = "failed"
        receipt["gate_measurements"][0]["status"] = "failed"
    rewrite_continuity_receipt(root, apply)


def mutate_annotation_bytes(root: Path) -> None:
    mutate_json(
        root,
        "07_qa/continuity_annotations/raw_continuity_geometry.json",
        lambda annotation: annotation.update({"post_receipt_edit_note": "annotation bytes changed"}),
    )


def mutate_wrong_raw_geometry(root: Path) -> None:
    annotation_path = root / "07_qa/continuity_annotations/raw_continuity_geometry.json"
    annotation = json.loads(annotation_path.read_text(encoding="utf-8"))
    target = next(
        item for item in annotation["landmarks"]
        if item["landmark_id"] == "PRODUCT_ROTATION_CENTER" and item["view_id"] == "ROT_0450"
    )
    target["point_normalized"] = [0.9, 0.5]
    write_json(annotation_path, annotation)
    semantic_path = root / "07_qa/continuity_semantic_evidence.json"
    semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
    semantic["annotations"][0]["annotation_sha256"] = sha256_file(annotation_path)
    write_json(semantic_path, semantic)
    run_continuity_builder(root)


def mutate_screen_locked_label_during_rotation(root: Path) -> None:
    annotation_path = root / "07_qa/continuity_annotations/raw_continuity_geometry.json"
    annotation = json.loads(annotation_path.read_text(encoding="utf-8"))
    front = next(
        item for item in annotation["polygons"]
        if item["polygon_id"] == "LABEL_SURFACE_REGION" and item["view_id"] == "ROT_0000"
    )
    rotated = next(
        item for item in annotation["polygons"]
        if item["polygon_id"] == "LABEL_SURFACE_REGION" and item["view_id"] == "ROT_0450"
    )
    rotated["points_normalized"] = json.loads(json.dumps(front["points_normalized"]))
    write_json(annotation_path, annotation)
    semantic_path = root / "07_qa/continuity_semantic_evidence.json"
    semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
    semantic["annotations"][0]["annotation_sha256"] = sha256_file(annotation_path)
    write_json(semantic_path, semantic)
    run_continuity_builder(root)


def mutate_screen_stationary_edge_anchors(root: Path) -> None:
    annotation_path = root / "07_qa/continuity_annotations/raw_continuity_geometry.json"
    annotation = json.loads(annotation_path.read_text(encoding="utf-8"))
    first_points = {
        item["landmark_id"]: item["point_normalized"]
        for item in annotation["landmarks"]
        if item["view_id"] == "ROT_0000"
        and item["landmark_id"] in {"EDGE_CONTINUITY_ANCHOR_A", "EDGE_CONTINUITY_ANCHOR_B"}
    }
    for item in annotation["landmarks"]:
        if item["landmark_id"] in first_points:
            item["point_normalized"] = json.loads(json.dumps(first_points[item["landmark_id"]]))
    write_json(annotation_path, annotation)
    semantic_path = root / "07_qa/continuity_semantic_evidence.json"
    semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
    semantic["annotations"][0]["annotation_sha256"] = sha256_file(annotation_path)
    write_json(semantic_path, semantic)
    run_continuity_builder(root)


def mutate_loose_semantic_tolerance(root: Path) -> None:
    def apply(evidence: dict[str, Any]) -> None:
        gate = next(item for item in evidence["gate_measurements"] if item["gate_id"] == "product_frame_gate")
        gate["metric_records"][0]["tolerance"] = 1.0
    mutate_json(root, "07_qa/continuity_semantic_evidence.json", apply)
    retarget_receipt_to_changed_semantic_evidence(root)


def mutate_one_generic_landmark_for_all_gates(root: Path) -> None:
    annotation_path = root / "07_qa/continuity_annotations/raw_continuity_geometry.json"
    annotation = json.loads(annotation_path.read_text(encoding="utf-8"))
    annotation["landmarks"] = [next(
        item for item in annotation["landmarks"]
        if item["landmark_id"] == "CAMERA_PRODUCT_CENTER" and item["view_id"] == "ROT_0000"
    )]
    annotation["polylines"] = []
    annotation["polygons"] = []
    annotation["mask_rle_or_polygon"] = []
    write_json(annotation_path, annotation)
    semantic_path = root / "07_qa/continuity_semantic_evidence.json"
    semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
    semantic["annotations"][0]["annotation_sha256"] = sha256_file(annotation_path)
    write_json(semantic_path, semantic)
    run_continuity_builder(root)


def mutate_edge_missing_semantic_evidence(root: Path) -> None:
    mutate_json(
        root,
        "07_qa/continuity_semantic_evidence.json",
        lambda evidence: evidence["edge_measurements"].pop(0),
    )
    run_continuity_builder(root)


def mutate_missing_submitted_reference_binding(root: Path) -> None:
    qa_path = root / "07_qa/asset_qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    asset = next(item for item in qa["assets"] if item["view_id"] == "ROT_0450")
    receipt_path = root / asset["generation_receipt_path"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["submitted_reference_bindings"] = []
    receipt["submitted_reference_set_sha256"] = hashlib.sha256(b"[]").hexdigest()
    write_json(receipt_path, receipt)
    asset["generation_receipt_sha256"] = sha256_file(receipt_path)
    write_json(qa_path, qa)


def mutate_legacy_v1_generation_receipt(root: Path) -> None:
    qa_path = root / "07_qa/asset_qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    asset = next(item for item in qa["assets"] if item["view_id"] == "ROT_0000")
    receipt_path = root / asset["generation_receipt_path"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["schema_version"] = "packaging-generation-receipt.v1"
    write_json(receipt_path, receipt)
    asset["generation_receipt_sha256"] = sha256_file(receipt_path)
    write_json(qa_path, qa)


def mutate_reused_worker_call(root: Path) -> None:
    qa_path = root / "07_qa/asset_qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    first = next(item for item in qa["assets"] if item["view_id"] == "ROT_0000")
    second = next(item for item in qa["assets"] if item["view_id"] == "ROT_0450")
    first_receipt = json.loads((root / first["generation_receipt_path"]).read_text(encoding="utf-8"))
    second_path = root / second["generation_receipt_path"]
    second_receipt = json.loads(second_path.read_text(encoding="utf-8"))
    second_receipt["worker_provenance"]["image_generation_call_id"] = (
        first_receipt["worker_provenance"]["image_generation_call_id"]
    )
    write_json(second_path, second_receipt)
    second["generation_receipt_sha256"] = sha256_file(second_path)
    write_json(qa_path, qa)


def mutate_worker_prompt_binding(root: Path) -> None:
    qa_path = root / "07_qa/asset_qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    asset = next(item for item in qa["assets"] if item["view_id"] == "ROT_0000")
    receipt_path = root / asset["generation_receipt_path"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    worker_path = root / receipt["worker_provenance"]["result_path"]
    worker = json.loads(worker_path.read_text(encoding="utf-8"))
    worker["tool_prompt_sha256"] = "f" * 64
    write_json(worker_path, worker)
    receipt["worker_provenance"]["result_sha256"] = sha256_file(worker_path)
    write_json(receipt_path, receipt)
    asset["generation_receipt_sha256"] = sha256_file(receipt_path)
    write_json(qa_path, qa)


def mutate_worker_raw_master_locator(root: Path) -> None:
    qa_path = root / "07_qa/asset_qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    asset = next(item for item in qa["assets"] if item["view_id"] == "ROT_0000")
    receipt_path = root / asset["generation_receipt_path"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    worker_path = root / receipt["worker_provenance"]["result_path"]
    worker = json.loads(worker_path.read_text(encoding="utf-8"))
    worker["run_image_path"] = str(root / "05_masters_raw/rotation/WRONG.png")
    write_json(worker_path, worker)
    receipt["worker_provenance"]["result_sha256"] = sha256_file(worker_path)
    write_json(receipt_path, receipt)
    asset["generation_receipt_sha256"] = sha256_file(receipt_path)
    write_json(qa_path, qa)


def mutate_low_resolution_final_master(root: Path) -> None:
    """Downsample one approved master while leaving its locked metadata intact."""
    qa = json.loads((root / "07_qa/asset_qa.json").read_text(encoding="utf-8"))
    path = root / qa["assets"][0]["file_path"]
    with Image.open(path) as opened:
        resized = opened.convert("RGB").resize(SOURCE_SIZE, Image.Resampling.LANCZOS)
    resized.save(path, format="PNG", optimize=False)


def mutate_prompt_drops_extended_lock(root: Path) -> None:
    index_path = root / "04_prompts/generation_prompt_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    record = next(item for item in index["prompts"] if item["view_id"] == "ROT_0000")
    prompt_path = root / record["prompt_path"]
    prompt_text = prompt_path.read_text(encoding="utf-8")
    marker = f"- Source manifest SHA-256: {index['extended_dependency_hashes']['source_manifest_sha256']}\n"
    if marker not in prompt_text:
        raise AssertionError("canonical extended lock marker is absent before mutation")
    prompt_path.write_text(prompt_text.replace(marker, "", 1), encoding="utf-8")
    record["prompt_sha256"] = sha256_file(prompt_path)
    write_json(index_path, index)


def mutate_detached_projected_ocr_crop(root: Path) -> None:
    post_path = root / "07_qa/post_composite_verification.json"
    post = json.loads(post_path.read_text(encoding="utf-8"))
    result = next(item for item in post["asset_results"] if item["view_id"] == "ROT_0000")
    evidence_path = root / result["post_ocr_evidence_path"]
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    scan = next(item for item in evidence["scans"] if item["scope"] == "projected_region_crop")
    crop_path = root / scan["image_path"]
    dimensions = scan["pixel_dimensions"]
    write_image(crop_path, (1, 2, 3), (dimensions["width"], dimensions["height"]))
    scan["image_sha256"] = sha256_file(crop_path)
    write_json(evidence_path, evidence)
    result["post_ocr_evidence_sha256"] = sha256_file(evidence_path)
    write_json(post_path, post)


def assert_no_forbidden_markers(root: Path) -> None:
    for path in root.rglob("*.json"):
        text = path.read_text(encoding="utf-8").lower()
        if "fixture" in text or "synthetic" in text:
            raise AssertionError(f"positive production evidence contains a forbidden test marker: {path}")


def assert_code_decode_receipt_contract() -> None:
    asset = {"asset_id": "ASSET_CODE_RECEIPT", "file_sha256": "a" * 64}
    code = {"symbology": "EAN-13", "expected_payload": "2901234567896"}
    observation = {
        "observation_id": "POST_CODE_001",
        "observed_symbology_raw": "VNBarcodeSymbologyEAN13",
        "decode_integrity_status": "passed",
        "decode_integrity_method": "ean13_mod10",
    }
    receipt: dict[str, Any] = {
        "schema_version": "packaging-post-code-decode-receipt.v1",
        "asset_id": asset["asset_id"], "view_id": "ROT_1800",
        "asset_file_sha256": asset["file_sha256"], "code_id": "CODE_EAN13",
        "engine_id": "bundled_macos_vision_ocr",
        "engine_script_path": "scripts/macos_vision_ocr.swift",
        "engine_script_sha256": sha256_file(SKILL_DIR / "scripts/macos_vision_ocr.swift"),
        "observation_id": observation["observation_id"],
        "observed_symbology_raw": observation["observed_symbology_raw"],
        "canonical_symbology": code["symbology"],
        "payload": code["expected_payload"],
        "payload_sha256": hashlib.sha256(code["expected_payload"].encode("utf-8")).hexdigest(),
        "decode_integrity_status": "passed",
        "decode_integrity_method": observation["decode_integrity_method"],
        "symbol_geometry_status": "matched",
        "receipt_sha256": None,
    }
    receipt["receipt_sha256"] = canonical_hash(receipt, "receipt_sha256")
    errors = validate_code_decode_receipt(
        receipt, asset=asset, view_id="ROT_1800", code_id="CODE_EAN13",
        code_record=code, code_observation=observation,
    )
    if errors:
        raise AssertionError(f"valid code decode receipt failed: {errors}")
    forged = dict(receipt)
    forged["symbol_geometry_status"] = "matched"
    forged["payload"] = "0000000000000"
    forged["payload_sha256"] = hashlib.sha256(forged["payload"].encode("utf-8")).hexdigest()
    forged["receipt_sha256"] = canonical_hash(forged, "receipt_sha256")
    if not validate_code_decode_receipt(
        forged, asset=asset, view_id="ROT_1800", code_id="CODE_EAN13",
        code_record=code, code_observation=observation,
    ):
        raise AssertionError("forged self-hashed code decode receipt unexpectedly passed")
    if not validate_code_decode_receipt(
        {}, asset=asset, view_id="ROT_1800", code_id="CODE_EAN13",
        code_record=code, code_observation=observation,
    ):
        raise AssertionError("empty code decode receipt unexpectedly passed")
    print("PASS semantic code decode receipt positive and forged/empty negatives")


def assert_macos_var_alias_path_contract() -> None:
    alias_parent = Path("/var/tmp")
    if not alias_parent.is_dir() or alias_parent.resolve() == alias_parent:
        print("PASS canonical run-relative locator (macOS /var alias not present on this host)")
        return
    with tempfile.TemporaryDirectory(prefix="packaging-var-alias-", dir=str(alias_parent)) as temporary:
        alias_root = Path(temporary)
        canonical_root = alias_root.resolve()
        alias_file = alias_root / "07_qa/composition_receipts/ROT_0000.json"
        write_json(alias_file, {"receipt": "alias-path-regression"})
        canonical_file = alias_file.resolve()
        expected = "07_qa/composition_receipts/ROT_0000.json"
        if post_adapter.run_relative_locator(canonical_root, alias_file, "alias child") != expected:
            raise AssertionError("/var child was not canonicalized against /private/var root")
        if post_adapter.run_relative_locator(alias_root, canonical_file, "canonical child") != expected:
            raise AssertionError("/private/var child was not canonicalized against /var root")
        outside = canonical_root.parent / f"{canonical_root.name}-outside.json"
        write_json(outside, {"receipt": "must-not-enter-run"})
        try:
            post_adapter.run_relative_locator(alias_root, outside, "outside child")
        except post_adapter.VerificationError:
            pass
        else:
            raise AssertionError("canonical locator accepted a path outside the run root")
        outside.unlink()
    print("PASS macOS /var and /private/var canonical path alias regression")


def assert_feature_derived_continuity_gate_contract() -> None:
    universal = derive_required_continuity_gates(set())
    if universal != continuity_builder.derive_required_continuity_gates(set()):
        raise AssertionError("builder/validator universal gate derivation differs")
    if derive_required_continuity_gates({"box_or_carton"}) != universal:
        raise AssertionError("box/carton incorrectly inherits liquid, pump, embossing, or showthrough gates")
    bath_oil = derive_required_continuity_gates(BATH_OIL_PRODUCT_FEATURES)
    if bath_oil != ALL_CONTINUITY_GATES or bath_oil != continuity_builder.ALL_CONTINUITY_GATES:
        raise AssertionError("transparent embossed pump bath oil does not derive every applicable gate")
    pump_only = derive_required_continuity_gates({"pump_or_spray"})
    if "nozzle_frame_binding_gate" not in pump_only or "dip_tube_topology_gate" in pump_only:
        raise AssertionError("pump derives nozzle gate while hidden dip-tube remains feature-conditioned")
    if {"fill_volume_gate", "embossing_registration_gate", "transparent_showthrough_gate"}.intersection(pump_only):
        raise AssertionError("pump-only product inherits unrelated feature gates")
    contract = {
        "schema_version": "packaging-continuity-contract.v1",
        "freeze_status": "frozen",
        "required_gates": sorted(universal),
        "text_code_topology_zero_tolerance": True,
    }
    errors: list[str] = []
    validate_continuity(contract, sorted(BATH_OIL_PRODUCT_FEATURES), errors)
    if not any("source-feature-derived" in error for error in errors):
        raise AssertionError("missing bath-oil conditional gates were not rejected")


def assert_pose_conditioned_continuity_positive(root: Path) -> None:
    annotation = json.loads(
        (root / "07_qa/continuity_annotations/raw_continuity_geometry.json").read_text(encoding="utf-8")
    )
    areas = [
        continuity_builder.polygon_area([(float(x), float(y)) for x, y in item["points_normalized"]])
        for item in annotation["polygons"] if item["polygon_id"] == "PRODUCT_SILHOUETTE"
    ]
    if max(areas) - min(areas) <= 0.05:
        raise AssertionError("positive silhouette evidence does not exercise legal front/side projection change")
    receipt = json.loads(
        (root / "07_qa/continuity_measurements.json").read_text(encoding="utf-8")
    )
    silhouette = next(
        item for item in receipt["gate_measurements"] if item["gate_id"] == "silhouette_gate"
    )
    if silhouette["status"] != "passed" or silhouette["metric_records"][-1].get("algorithm_id") != "pose_conditioned_polygon_baseline_error":
        raise AssertionError("pose-conditioned silhouette baseline did not accept calibrated front/side variation")


def assert_dynamic_region_readability_contract(base: Path) -> None:
    root = base / "dynamic_region_readability"
    master_locator = "05_masters/details_copy/dynamic_front.png"
    write_image(root / master_locator, (120, 80, 40), (512, 288))
    spec = next(iter(fixture_dynamic_region_specs(False).values()))
    view = {
        "dynamic_region_contract": {
            key: spec[key] for key in (
                "region_id", "surface_id", "field_ids", "code_ids", "graphic_ids",
                "native_region_pixel_contract",
            )
        }
    }
    asset = {"file_path": master_locator}
    evidence = {
        "scans": [{
            "scan_id": "REGION_SCAN",
            "scope": "projected_region_crop",
            "crop_box_px_on_final_master": [64, 36, 448, 252],
            "pixel_dimensions": {"width": 384, "height": 216},
            "region_ids": [REGION_ID], "field_ids": [FIELD_ID],
            "code_ids": [], "graphic_ids": [GRAPHIC_ID],
        }],
        "raw_scan_observations": {"text": [{
            "raw_observation_id": "RAW_DYNAMIC_LINE",
            "scan_id": "REGION_SCAN",
            "scan_bounding_box_normalized": {
                "x": 0.05, "y": 0.45, "width": 0.9, "height": 0.08,
            },
        }], "codes": []},
    }
    positive_errors: list[str] = []
    if not validate_dynamic_region_pixel_contract(
        root, dynamic_region_detail_view_id(REGION_ID), view, asset, evidence,
        positive_errors,
    ) or positive_errors:
        raise AssertionError(f"valid dynamic-region readability evidence failed: {positive_errors}")
    tiny = json.loads(json.dumps(evidence))
    tiny["scans"][0]["crop_box_px_on_final_master"] = [8, 8, 28, 18]
    tiny["scans"][0]["pixel_dimensions"] = {"width": 20, "height": 10}
    negative_errors: list[str] = []
    if validate_dynamic_region_pixel_contract(
        root, dynamic_region_detail_view_id(REGION_ID), view, asset, tiny,
        negative_errors,
    ) or not any("below the 4K-equivalent" in item for item in negative_errors):
        raise AssertionError("tiny final-master region bbox unexpectedly passed readability authority")
    unsafe_id = dynamic_region_detail_view_id("../危险 region/../../label")
    if re.fullmatch(r"DETAIL_REGION_[A-Z0-9_]+_[A-F0-9]{8}", unsafe_id) is None or "/" in unsafe_id or ".." in unsafe_id:
        raise AssertionError("dynamic region stable ID did not sanitize unsafe path characters")
    print("PASS dynamic region stable ID plus final-pixel 4K readability positive/tiny negative")


def assert_bath_oil_r16_continuity_builder(base: Path) -> None:
    root = base / "bath_oil_r16_continuity"
    root.mkdir(parents=True, exist_ok=True)
    ring_views = list(PROFILES["rotation_profiles"]["R16"]["view_ids"])
    source_locator = "00_source/front.png"
    write_image(root / source_locator, (220, 145, 70))
    write_json(root / "00_source/source_manifest.json", {
        "schema_version": "packaging-source-manifest.v1",
        "product_id": "PRODUCT_BATH_OIL_R16_CONTINUITY",
        "product_state_id": STATE_ID,
        "variant_resolution_status": "resolved_single_sku_and_instance",
        "product_feature_classification": reviewed_feature_classification(BATH_OIL_PRODUCT_FEATURES),
        "sources": [{"source_id": SOURCE_BY_ROLE["front"], "file_path": source_locator}],
    })
    source_sha = sha256_file(root / "00_source/source_manifest.json")
    landmark_ids = continuity_raw_landmark_ids(BATH_OIL_PRODUCT_FEATURES)
    coverage_views = [{
        "asset_id": f"ASSET_{view_id}", "view_id": view_id,
        "family": "neutral_ring", "shot_scale": "full_product", "required": True,
        "product_state_id": STATE_ID,
        "geometry_landmark_ids": landmark_ids,
        "label_region_ids": [REGION_ID],
        "next_view_id": ring_views[(index + 1) % len(ring_views)],
    } for index, view_id in enumerate(ring_views)]
    write_json(root / "02_coverage/coverage_matrix.json", {
        "schema_version": "packaging-view-coverage.v1", "rotation_profile": "R16",
        "product_state_id": STATE_ID, "freeze_status": "frozen", "views": coverage_views,
    })
    silhouette_by_view = {}
    for index, view_id in enumerate(ring_views):
        geometry = silhouette_polygon_for_ring_index(index, len(ring_views))
        width = max(point[0] for point in geometry) - min(point[0] for point in geometry)
        height = max(point[1] for point in geometry) - min(point[1] for point in geometry)
        silhouette_by_view[view_id] = {
            "area_normalized": round(continuity_builder.polygon_area([
                (float(x), float(y)) for x, y in geometry
            ]), 12),
            "bbox_aspect_ratio": round(width / height, 12),
        }
    all_calibrations = {
        "silhouette_gate": {
            "calibration_id": "silhouette_source_pose_baseline_v1",
            "basis": "source_pose_locked_before_generation", "source_manifest_sha256": source_sha,
            "by_view": silhouette_by_view,
        },
        "material_gate": {
            "calibration_id": "material_source_pose_baseline_v1",
            "basis": "source_pose_locked_before_generation", "source_manifest_sha256": source_sha,
            "by_view": {
                view_id: {"statistic_value": expected_material_luma(index + 1)}
                for index, view_id in enumerate(ring_views)
            },
        },
        "transparent_showthrough_gate": {
            "calibration_id": "showthrough_source_pose_baseline_v1",
            "basis": "source_pose_locked_before_generation", "source_manifest_sha256": source_sha,
            "by_view": {
                view_id: {"statistic_value": expected_showthrough_luma_std(index + 1)}
                for index, view_id in enumerate(ring_views)
            },
        },
        "edge_measurements": {
            "calibration_id": "edge_motion_pose_baseline_v1",
            "basis": "source_pose_locked_before_generation", "source_manifest_sha256": source_sha,
            "by_edge": edge_calibration_by_edge(ring_views),
        },
        "loop_closure_gate": {
            "calibration_id": "loop_closure_pose_baseline_v1",
            "basis": "source_pose_locked_before_generation", "source_manifest_sha256": source_sha,
            "by_edge": {
                edge_id: edge for edge_id, edge in edge_calibration_by_edge(ring_views).items()
                if edge["from_view_id"] == ring_views[-1] and edge["to_view_id"] == ring_views[0]
            },
        },
    }
    write_json(root / "02_coverage/continuity_contract.json", {
        "schema_version": "packaging-continuity-contract.v1", "freeze_status": "frozen",
        "product_state_id": STATE_ID,
        "required_gates": sorted(derive_required_continuity_gates(BATH_OIL_PRODUCT_FEATURES)),
        "text_code_topology_zero_tolerance": True,
        "calibration_baselines": all_calibrations,
    })
    asset_records = []
    for index, view_id in enumerate(ring_views):
        locator = f"05_masters/neutral_ring/{view_id}.png"
        write_master_image(root / locator, index + 1)
        asset_records.append({
            "asset_id": f"ASSET_{view_id}", "view_id": view_id, "family": "neutral_ring",
            "file_path": locator, "file_sha256": sha256_file(root / locator),
            "assistant_qa_status": "passed",
        })
    board_locator = "06_review_boards/r16_continuity.png"
    write_image(root / board_locator, (80, 90, 100), (512, 288))
    board_inputs = [{
        key: asset[key] for key in ("asset_id", "view_id", "file_path", "file_sha256")
    } for asset in asset_records]
    write_json(root / "07_qa/asset_qa.json", {
        "schema_version": "packaging-asset-qa.v1", "assets": asset_records,
        "review_boards": [{
            "file_path": board_locator, "file_sha256": sha256_file(root / board_locator),
            "role": "human_review_qa_board", "derivation_mode": "deterministic_composite",
            "inputs": board_inputs,
        }],
    })
    stub_locator = "07_qa/post_stub.json"
    write_json(root / stub_locator, {"locked": True})
    stub_sha = sha256_file(root / stub_locator)
    post_results = [{
        "asset_id": asset["asset_id"], "view_id": asset["view_id"],
        "asset_file_sha256": asset["file_sha256"],
        "composition_receipt_path": stub_locator, "composition_receipt_sha256": stub_sha,
        "post_ocr_evidence_path": stub_locator, "post_ocr_evidence_sha256": stub_sha,
        "field_results": [], "code_results": [], "graphic_results": [],
    } for asset in asset_records]
    write_json(root / "07_qa/post_composite_verification.json", {
        "schema_version": "packaging-post-composite-verification.v1",
        "asset_results": post_results,
        "copy_content_lock_status": "approved", "label_artwork_lock_status": "approved",
        "code_payload_lock_status": "approved", "code_symbol_lock_status": "approved",
        "logo_graphic_lock_status": "approved", "exact_copy_lock_status": "approved",
    })
    build_continuity_artifacts(root, asset_records)
    receipt = json.loads((root / "07_qa/continuity_measurements.json").read_text(encoding="utf-8"))
    if (
        set(item["gate_id"] for item in receipt["gate_measurements"]) != ALL_CONTINUITY_GATES
        or len(receipt["edge_measurements"]) != 16
        or any(item["status"] != "passed" for item in [*receipt["gate_measurements"], *receipt["edge_measurements"]])
    ):
        raise AssertionError("bath-oil R16 continuity builder did not pass all derived gates and ring edges")
    negative = base / "bath_oil_r16_stationary_edge_negative"
    shutil.copytree(root, negative)
    mutate_screen_stationary_edge_anchors(negative)
    failed_receipt = json.loads(
        (negative / "07_qa/continuity_measurements.json").read_text(encoding="utf-8")
    )
    if not any(item["status"] == "failed" for item in failed_receipt["edge_measurements"]):
        raise AssertionError("R16 stationary screen anchors unexpectedly passed calibrated edge motion")


def mutate_extra_feature_gate_without_feature(root: Path) -> None:
    mutate_json(
        root, "02_coverage/continuity_contract.json",
        lambda contract: contract["required_gates"].append("fill_volume_gate"),
    )


def mutate_missing_universal_gate(root: Path) -> None:
    mutate_json(
        root, "02_coverage/continuity_contract.json",
        lambda contract: contract["required_gates"].remove("product_frame_gate"),
    )


def assert_final_runtime_gate_contract() -> None:
    compiler = prompt_compiler_for_test()
    expected_pillow = compiler.required_pillow_version()
    valid = compiler.final_runtime_capability_errors(
        platform_name="darwin", swift_path="/usr/bin/swift",
        vision_script_exists=True, adapter_script_exists=True,
        pillow_version=expected_pillow, expected_pillow_version=expected_pillow,
        live_smoke_status="PASS",
    )
    if valid:
        raise AssertionError(f"valid final Vision runtime capability failed: {valid}")
    mutations = {
        "non_darwin": {"platform_name": "linux"},
        "missing_swift": {"swift_path": None},
        "missing_vision": {"vision_script_exists": False},
        "missing_adapter": {"adapter_script_exists": False},
        "missing_pillow": {"pillow_version": None},
        "pillow_drift": {"pillow_version": "0.0.0"},
        "live_smoke_failure": {"live_smoke_status": "FAILED"},
    }
    base = {
        "platform_name": "darwin", "swift_path": "/usr/bin/swift",
        "vision_script_exists": True, "adapter_script_exists": True,
        "pillow_version": expected_pillow, "expected_pillow_version": expected_pillow,
        "live_smoke_status": "PASS",
    }
    for label, change in mutations.items():
        candidate = dict(base); candidate.update(change)
        if not compiler.final_runtime_capability_errors(**candidate):
            raise AssertionError(f"final runtime mutation {label} unexpectedly passed")
    compiler.assert_final_post_composite_runtime_callable({"exact_copy_mode": "geometry_only_preview"})
    if sys.platform != "darwin":
        try:
            compiler.assert_final_post_composite_runtime_callable(
                {"exact_copy_mode": "all_visible_product_native_copy"}
            )
        except compiler.CompileError:
            pass
        else:
            raise AssertionError("non-Darwin exact-copy compiler runtime unexpectedly passed")
    print("PASS final Vision runtime pre-generation gate and capability negatives")


def main() -> int:
    runtime_command = [
        sys.executable, str(SKILL_DIR / "scripts/test_macos_vision_runtime.py"),
    ]
    if sys.platform == "darwin":
        runtime_command.append("--require-live")
    runtime_result = run_command(runtime_command, "bundled macOS Vision runtime smoke")
    expected_runtime_status = "PASS" if sys.platform == "darwin" else "SKIP_NON_DARWIN"
    if runtime_result.get("status") != expected_runtime_status:
        raise AssertionError(f"unexpected bundled Vision runtime status: {runtime_result}")
    print(f"PASS bundled Vision runtime boundary: {expected_runtime_status}")
    template_result = run_command([
        sys.executable, str(SKILL_DIR / "scripts/validate_template_contract.py"),
    ], "cross-template contract validator")
    if template_result.get("status") != "PASS":
        raise AssertionError(f"cross-template contract validator did not pass: {template_result}")
    print("PASS cross-template starter closure")
    canonical_enum = sorted(CANONICAL_FEATURES)
    if template_contract.validate_canonical_feature_enum(canonical_enum) != CANONICAL_FEATURES:
        raise AssertionError("canonical schema feature enum positive did not preserve the taxonomy")
    enum_mutations = {
        "duplicate": canonical_enum + [canonical_enum[0]],
        "missing": canonical_enum[:-1],
        "non_string": canonical_enum + [7],
    }
    for label, mutation in enum_mutations.items():
        try:
            template_contract.validate_canonical_feature_enum(mutation)
        except template_contract.TemplateContractError:
            continue
        raise AssertionError(f"schema feature enum {label} mutation unexpectedly passed")
    print("PASS schema feature taxonomy duplicate/missing/type mutations fail closed")
    assert_macos_var_alias_path_contract()
    assert_code_decode_receipt_contract()
    assert_feature_derived_continuity_gate_contract()
    print("PASS source-feature-derived continuity gate contract")
    assert_final_runtime_gate_contract()
    with tempfile.TemporaryDirectory(prefix="packaging-contract-") as temporary:
        base = Path(temporary)
        ready = base / "ready"
        create_ready_run(ready)
        ready_errors = validate_run(ready)
        if ready_errors:
            raise AssertionError("READY positive run failed:\n" + "\n".join(ready_errors))
        print("PASS production-shaped R8 READY run")
        assert_dynamic_region_readability_contract(base)

        bath_oil_ready = base / "bath_oil_r16_ready"
        create_ready_run(
            bath_oil_ready,
            rotation_profile="R16",
            product_features=BATH_OIL_PRODUCT_FEATURES,
            include_codes=True,
        )
        bath_oil_errors = validate_run(bath_oil_ready)
        if bath_oil_errors:
            raise AssertionError(
                "bath-oil R16 READY positive run failed:\n" + "\n".join(bath_oil_errors)
            )
        bath_manifest = json.loads(
            (bath_oil_ready / "00_manifest/run_manifest.json").read_text(encoding="utf-8")
        )
        bath_coverage = json.loads(
            (bath_oil_ready / "02_coverage/coverage_matrix.json").read_text(encoding="utf-8")
        )
        required_bath_views = required_view_ids(
            "R16", BATH_OIL_PRODUCT_FEATURES, include_codes=True,
        )
        bath_role_counts: dict[str, int] = {}
        for view in bath_coverage.get("views") or []:
            role = str(view.get("review_board_role"))
            bath_role_counts[role] = bath_role_counts.get(role, 0) + 1
        role_capacities = {
            "neutral_rotation": 6, "elevation": 6, "framing_bridge": 6,
            "copy": 4, "code": 4, "structure": 4, "material": 4,
        }
        minimum_bath_boards = sum(
            (count + role_capacities[role] - 1) // role_capacities[role]
            for role, count in bath_role_counts.items()
        )
        if (
            bath_manifest.get("rotation_profile") != "R16"
            or set(bath_manifest.get("product_features") or []) != BATH_OIL_PRODUCT_FEATURES
            or {item.get("view_id") for item in bath_coverage.get("views") or []}
            != set(required_bath_views)
            or len(required_bath_views) != 61
            or bath_role_counts != {
                "neutral_rotation": 16, "elevation": 10, "framing_bridge": 8,
                "copy": 7, "code": 3, "structure": 11, "material": 6,
            }
            or minimum_bath_boards != 15
        ):
            raise AssertionError("bath-oil R16 READY fixture did not bind its full feature-derived view pack")
        print("PASS transparent liquid pump bath-oil R16 READY: 61 masters / minimum 15 semantic QA boards")
        pitched_ready = base / "pitched_high_r8_ready"
        high_ring = full_elevation_ring("HIGH", "R8", 30.0)
        create_ready_run(
            pitched_ready,
            motion_type="pitched_full_rotation",
            motion_scope="high_full_360_rotation",
            elevation_rings=[high_ring],
        )
        pitched_errors = validate_run(pitched_ready)
        if pitched_errors:
            raise AssertionError("pitched HIGH full-ring positive failed:\n" + "\n".join(pitched_errors))
        pitched_coverage = json.loads(
            (pitched_ready / "02_coverage/coverage_matrix.json").read_text(encoding="utf-8")
        )
        if not set(high_ring["view_ids"]).issubset({item["view_id"] for item in pitched_coverage["views"]}):
            raise AssertionError("pitched HIGH positive omitted profile-matched ring views")
        print("PASS pitched HIGH full rotation requires and validates one complete profile-matched ring")
        assert_bath_oil_r16_continuity_builder(base)
        print("PASS bath-oil R16 continuity builder all gates/edges plus stationary-edge negative")
        print("PASS production-shaped READY_FOR_GENERATION run")
        assert_zero_text_non_text_region_contract(ready)

        assert_invalid(
            ready, "text_region_zero_ocr", mutate_text_region_to_zero_detections,
            "text/mixed region requires at least one text OCR detection",
        )
        assert_invalid(
            ready, "region_surface_id_tamper",
            lambda root: mutate_region_pass_authority_binding(
                root, "surface_id", SURFACE_BY_ROLE["back"]
            ),
            "region authority metadata differs from region spec",
        )
        assert_invalid(
            ready, "region_physical_layer_tamper",
            lambda root: mutate_region_pass_authority_binding(
                root, "physical_layer_id", "tampered_unowned_layer"
            ),
            "region authority metadata differs from region spec",
        )
        assert_invalid(
            ready, "region_visibility_tamper",
            lambda root: mutate_region_pass_authority_binding(
                root, "visibility_mode", "oblique"
            ),
            "region authority metadata differs from region spec",
        )
        assert_invalid(
            ready, "region_purpose_tamper",
            lambda root: mutate_region_pass_authority_binding(
                root, "region_purpose", "graphic"
            ),
            "region authority metadata differs from region spec",
        )
        assert_invalid(
            ready, "region_receipt_authority_tamper",
            mutate_region_receipt_authority_binding,
            "crop derivation receipt failed",
        )
        assert_invalid(
            ready, "graphic_missing_named_disposition",
            lambda root: mutate_json(
                root, "01_ocr/logo_graphic_manifest.json",
                lambda data: data["graphics"][0].pop("disposition"),
            ),
            "required graphic needs a reviewed source disposition",
        )
        assert_invalid(
            ready, "graphic_disposition_unnamed_reviewer",
            lambda root: mutate_json(
                root, "01_ocr/logo_graphic_manifest.json",
                lambda data: data["graphics"][0]["disposition"].update({"reviewer_id": None}),
            ),
            "graphic disposition requires named human review",
        )

        assert_invalid(
            ready, "extra_feature_gate_without_feature", mutate_extra_feature_gate_without_feature,
            "source-feature-derived v3 gate set",
        )
        assert_invalid(
            ready, "missing_universal_continuity_gate", mutate_missing_universal_gate,
            "source-feature-derived v3 gate set",
        )

        assert_invalid(
            ready, "four_dimensional_needs_source", mutate_four_dimensional_needs_source,
            "required production view cannot pass with needs_source",
        )
        assert_invalid(
            ready, "generated_empty_parents",
            lambda root: mutate_json(root, "02_coverage/coverage_matrix.json", lambda data: next(
                item for item in data["views"] if item["view_id"] == "ROT_0450"
            ).update({"parent_anchor_view_ids": []})),
            "generated view requires at least two unique direct anchors",
        )
        assert_invalid(
            ready, "all_angles_claim_front", mutate_all_angles_front,
            "visible surfaces violate canonical camera/surface topology",
        )
        assert_invalid(
            ready, "front_claims_impossible_back_surface", mutate_impossible_extra_surface,
            "visible surfaces violate canonical camera/surface topology",
        )
        assert_invalid(
            ready, "source_missing_camera_pose_binding",
            lambda root: mutate_json(root, "00_source/source_manifest.json", lambda data: data["sources"][0].pop("view_id")),
            "view_id must bind the spatial source to one canonical camera pose",
        )
        assert_invalid(
            ready, "inferred_high_claims_direct_source", mutate_inferred_high_claims_direct_source,
            "source-derived full-product view requires an attached direct source",
        )
        assert_invalid(
            ready, "generated_detail_claims_direct_source", mutate_generated_detail_claims_direct_source,
            "V3 detail masters must be generated/inferred from direct full-product anchors",
        )
        assert_invalid(
            ready, "undisposed_source_ocr",
            lambda root: mutate_json(root, "01_ocr/ocr_observations.json", lambda data: next(
                item for item in data["source_records"] if item["source_id"] == SOURCE_BY_ROLE["front"]
            )["text_observations"][1].pop("disposition")),
            "every OCR detection requires a disposition",
        )
        assert_invalid(
            ready, "unreconciled_extra_code_observation",
            lambda root: mutate_json(root, "01_ocr/ocr_observations.json", lambda data: data["source_records"][0]["code_observations"].append({
                "code_id": "SRC_FRONT_CODE_EXTRA_001",
                "symbology": "QR",
                "payload": "https://unexpected.invalid/",
                "bounding_box_normalized": {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2},
                "disposition": {
                    "status": "unresolved", "review_status": "review_required",
                    "reviewer_id": None, "manifest_code_id": None,
                    "evidence_note": "Discovery candidate not yet reconciled."
                }
            })),
            "unresolved decoded-code disposition blocks exact-copy generation",
        )
        assert_invalid(
            ready, "black_region_crop_with_coordinated_hashes", mutate_black_region_crop,
            "crop pixels are not derived from locked source geometry",
        )
        assert_invalid(
            ready, "fake_whole_product_ocr_engine", mutate_fake_whole_ocr_engine,
            "engine must be trusted macos_vision or tesseract",
        )
        assert_invalid(
            ready, "text_authority_unrelated_image", mutate_text_authority_to_unrelated_image,
            "authority asset is not the replayed source-region crop",
        )
        assert_invalid(
            ready, "graphic_authority_unrelated_image", mutate_graphic_authority_to_unrelated_image,
            "graphic asset lacks source-crop or approved-master provenance",
        )
        assert_invalid(
            ready, "unknown_feature_typo", mutate_unknown_feature,
            "unknown feature_id",
        )
        assert_invalid(
            ready, "evidence_only_artwork_masquerades_as_camera_anchor",
            mutate_spatial_source_to_artwork_anchor,
            "artwork/text/dieline sources cannot claim a product camera pose",
        )
        assert_invalid(
            ready, "incomplete_feature_taxonomy", mutate_missing_feature_audit_row,
            "product_feature_classification must audit the complete canonical taxonomy",
        )
        assert_invalid(
            ready, "ordinary_label_heavy_illegal_r8",
            lambda root: mutate_present_feature_without_profile_upgrade(root, "ordinary_label_heavy_packaging"),
            "feature-derived minimum rotation profile is R12",
        )
        assert_invalid(
            ready, "macro_rotation_illegal_r8",
            lambda root: mutate_present_feature_without_profile_upgrade(root, "macro_rotation"),
            "feature-derived minimum rotation profile is R24",
        )
        assert_invalid(
            ready, "double_high_ring", mutate_double_high_ring,
            "only one dynamic HIGH ring is allowed",
        )
        assert_invalid(
            ready, "fixed_detail_pose_semantic_drift", mutate_fixed_detail_pose_semantics,
            "elevation_deg differs from frozen view semantics",
        )
        assert_invalid(
            ready, "missing_upper_half_bridge", mutate_remove_upper_bridge,
            "missing required views: UPPER_0900",
        )
        assert_invalid(
            bath_oil_ready, "dynamic_region_coalescing_forbidden",
            mutate_coalesce_dynamic_regions,
            "dynamic region contract differs from exact-copy evidence",
        )
        assert_invalid(
            ready, "pitched_full_rotation_missing_ring", mutate_pitched_ring_missing,
            "elevation_rings must exactly match the motion scope",
        )
        assert_invalid(
            ready, "required_detail_content_omission", mutate_required_detail_content_omission,
            "lacks its own region-derived exact-copy detail master",
        )
        assert_invalid(
            ready, "empty_detail_job",
            lambda root: mutate_json(root, "02_coverage/coverage_matrix.json", lambda data: next(
                item for item in data["views"] if item["view_id"] == "DETAIL_CLOSURE_TOP"
            ).update({"detail_job": {}})),
            "detail_job.detail_id must equal view_id",
        )
        assert_invalid(
            ready, "incompatible_projection",
            lambda root: mutate_json(root, "03_composition/deterministic_composition_plan.json", lambda data: data["view_statuses"][0].update({"projection_model": "cylindrical_uv"})),
            "projection_model is not executable",
        )

        complete = base / "complete"
        create_complete_run(complete)
        complete_asset_qa = json.loads((complete / "07_qa/asset_qa.json").read_text(encoding="utf-8"))
        builder_asset = next(item for item in complete_asset_qa["assets"] if item["view_id"] == "ROT_0000")
        builder_receipt = json.loads(
            (complete / builder_asset["generation_receipt_path"]).read_text(encoding="utf-8")
        )
        builder_output = complete / "07_qa/generation_receipts/ROT_0000.builder-smoke.json"
        builder_summary = run_command([
            sys.executable,
            str(SKILL_DIR / "scripts/build_generation_receipt.py"),
            "--run-root", str(complete),
            "--view-id", "ROT_0000",
            "--worker-result", str(complete / builder_receipt["worker_provenance"]["result_path"]),
            "--reference-manifest", str(
                complete / builder_receipt["worker_provenance"]["reference_manifest_path"]
            ),
            "--output", str(builder_output),
        ], "delegated per-master generation receipt builder")
        if builder_summary.get("status") != "PASS" or not builder_output.is_file():
            raise AssertionError("generation receipt builder did not publish v2 evidence")
        print("PASS delegated per-master generation receipt builder")
        assert_integrated_code_bearing_complete(complete)
        assert_pose_conditioned_continuity_positive(complete)
        print("PASS pose-conditioned silhouette variation and local-frame continuity")
        assert_no_forbidden_markers(complete)
        complete_errors = validate_run(complete)
        if complete_errors:
            raise AssertionError("COMPLETE positive run failed:\n" + "\n".join(complete_errors))
        print("PASS production-shaped COMPLETE run")
        print("PASS ordered-line aggregation COMPLETE positive")
        relocated = base / "complete_relocated"
        shutil.copytree(complete, relocated)
        relocated_errors = validate_run(relocated)
        if relocated_errors:
            raise AssertionError("relocated COMPLETE run failed:\n" + "\n".join(relocated_errors))
        print("PASS COMPLETE run remains valid after relocation")
        assert_invalid(
            complete, "low_resolution_master_cannot_be_promoted",
            mutate_low_resolution_final_master,
            "master is below the minimum native delivery resolution 1280x720",
        )
        assert_invalid(
            complete, "review_board_noncanonical_order", mutate_review_board_order,
            "semantic board inputs are not in canonical order",
        )

        assert_invalid(
            complete, "fixture_synthetic_job_marker", mutate_test_marker_job,
            "deterministic composition receipt failed",
        )
        assert_invalid(
            complete, "extra_post_ocr_product_text", mutate_extra_post_ocr,
            "missing, duplicate, or unexpected product text",
        )
        assert_invalid(
            complete, "detached_projected_ocr_crop", mutate_detached_projected_ocr_crop,
            "pixels are detached from the approved final master",
        )
        assert_invalid(
            complete, "contradictory_aggregate_raw", mutate_contradictory_aggregate_raw,
            "replay/hash contradicts raw fragments",
        )
        assert_invalid(
            complete, "forged_graphic_receipt", mutate_forged_graphic_receipt,
            "graphic LOGO_EXAMPLE_LAB_7Q4 failed",
        )
        assert_invalid(
            complete, "integrated_final_code_receipt_payload_tamper",
            mutate_integrated_final_code_receipt_payload,
            "semantic payload/engine/integrity/geometry binding failed",
        )
        assert_invalid(
            complete, "raw_equals_final", mutate_raw_equals_final,
            "exact-copy final must differ from raw generated bytes",
        )
        assert_invalid(
            complete, "one_master_reuse", mutate_one_master_reuse,
            "master file_path must be unique",
        )
        assert_invalid(
            complete, "one_character_prompts", mutate_one_character_prompts,
            "prompt is incomplete or not dependency-bound",
        )
        assert_invalid(
            complete, "prompt_drops_extended_frozen_lock", mutate_prompt_drops_extended_lock,
            "prompt bytes differ from canonical compiler replay",
        )
        assert_invalid(
            complete, "missing_review_board", mutate_missing_review_board,
            "missing file",
        )
        assert_invalid(
            complete, "missing_submitted_reference_binding", mutate_missing_submitted_reference_binding,
            "submitted frozen references do not match manifest bytes",
        )
        assert_invalid(
            complete, "legacy_v1_generation_receipt", mutate_legacy_v1_generation_receipt,
            "invalid generation receipt schema",
        )
        assert_invalid(
            complete, "reused_worker_image_call", mutate_reused_worker_call,
            "worker provenance reuses image_generation_call_id",
        )
        assert_invalid(
            complete, "worker_prompt_binding_drift", mutate_worker_prompt_binding,
            "worker result does not bind provenance/prompt/image",
        )
        assert_invalid(
            complete, "worker_raw_master_locator_drift", mutate_worker_raw_master_locator,
            "worker result raw-master locator mismatch",
        )
        assert_invalid(
            complete, "legacy_v1_continuity_receipt", mutate_legacy_v1_continuity_receipt,
            "v2 measurement receipt identity/self-hash failed",
        )
        assert_invalid(
            complete, "empty_semantic_metrics", mutate_empty_semantic_metrics,
            "measurement builder replay failed",
        )
        assert_invalid(
            complete, "manual_semantic_gate", mutate_manual_semantic_gate,
            "measurement builder replay failed",
        )
        assert_invalid(
            complete, "blocked_semantic_gate", mutate_blocked_semantic_gate,
            "semantic measurement/result did not pass",
        )
        assert_invalid(
            complete, "fake_continuity_tool_hash", mutate_fake_continuity_tool_hash,
            "v2 measurement receipt identity/self-hash failed",
        )
        assert_invalid(
            complete, "edited_metric_recomputed_self_hash", mutate_receipt_metric_and_self_hash,
            "installed measurement builder replay differs",
        )
        assert_invalid(
            complete, "tampered_annotation_bytes", mutate_annotation_bytes,
            "semantic annotation 0 hash binding failed",
        )
        assert_invalid(
            complete, "wrong_raw_geometry_recomputed", mutate_wrong_raw_geometry,
            "semantic measurement/result did not pass",
        )
        assert_invalid(
            complete, "screen_locked_label_during_rotation",
            mutate_screen_locked_label_during_rotation,
            "label_surface_binding_gate: semantic measurement/result did not pass",
        )
        assert_invalid(
            complete, "screen_stationary_edge_anchors",
            mutate_screen_stationary_edge_anchors,
            "semantic edge measurement/result did not pass",
        )
        assert_invalid(
            complete, "loose_semantic_tolerance", mutate_loose_semantic_tolerance,
            "measurement builder replay failed",
        )
        assert_invalid(
            complete, "one_generic_landmark_for_all_gates", mutate_one_generic_landmark_for_all_gates,
            "semantic measurement/result did not pass",
        )
        assert_invalid(
            complete, "edge_missing_semantic_evidence", mutate_edge_missing_semantic_evidence,
            "semantic edge measurement/result did not pass",
        )

        canon_output = complete / "08_validation/packaging_exact_copy_canon_evidence.json"
        canon_summary = run_command([
            sys.executable,
            str(SKILL_DIR / "scripts/build_exact_copy_canon_evidence.py"),
            "--project-root", str(base),
            "--run-root", str(complete),
            "--asset-key", "contract-acceptance-product",
            "--primary-view-id", "ROT_0000",
            "--output", str(canon_output),
        ], "COMPLETE-run Canon v2 evidence builder")
        if canon_summary.get("status") != "PASS" or not canon_output.is_file():
            raise AssertionError("Canon v2 evidence builder did not publish a locked sidecar")
        print("PASS COMPLETE-run-bound Canon v2 evidence builder")

    print("PASS packaging asset-pack contract suite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
