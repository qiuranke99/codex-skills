#!/usr/bin/env python3
"""Validate an OCR-first, rotation-ready packaging asset-pack run."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import re
import shutil
import sys
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore[assignment]


SKILL_DIR = Path(__file__).resolve().parents[1]
PROFILES_PATH = SKILL_DIR / "references/view_coverage_profiles.json"
PROFILES = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
SHA = re.compile(r"^[a-f0-9]{64}$")
CANONICAL_FEATURES = set(PROFILES.get("feature_detail_requirements", {})) | {
    "simple_near_rotational_symmetry", "low_copy_risk", "ordinary_label_heavy_packaging",
    "flat_or_rectangular_body", "non_symmetric_closure", "high_material_risk",
    "complex_reflection", "continuous_wrap_copy", "macro_rotation",
}
PROFILE_RANK = {"R8": 8, "R12": 12, "R16": 16, "R24": 24}
R16_FEATURES = {
    "transparent_or_translucent", "liquid_or_gel", "pump_or_spray",
    "visible_fill_line_or_liquid_boundary", "visible_dip_tube",
    "foil_or_reflective_print", "wrap_label", "flat_or_rectangular_body",
    "non_symmetric_closure", "high_material_risk",
}
R24_FEATURES = {"complex_reflection", "continuous_wrap_copy", "macro_rotation"}
REGION_PURPOSES = {"text", "code", "graphic", "mixed"}
REGION_VISIBILITY_MODES = {
    "direct", "oblique", "mirrored_showthrough", "refracted", "reflected", "occluded",
}
TEXT_REQUIRED_REGION_PURPOSES = {"text", "mixed"}
BASE_CLOSE_SPECS = {
    item["view_id"]: item for item in PROFILES.get("base_close_views", [])
    if isinstance(item, dict) and isinstance(item.get("view_id"), str)
}
FIXED_DETAIL_SPECS = {
    key: value for key, value in PROFILES.get("fixed_detail_specs", {}).items()
    if isinstance(key, str) and isinstance(value, dict)
}
DYNAMIC_REGION_DETAIL_CONTRACT = PROFILES.get("dynamic_region_detail_contract", {})
MOTION_SCOPE_BY_TYPE: dict[str, set[str]] = {
    "bounded_orbit": {"bounded_neutral_orbit", "bounded_high_orbit", "bounded_low_orbit"},
    "neutral_height_full_spin": {"neutral_height_full_360_rotation"},
    "pitched_full_rotation": {
        "high_full_360_rotation", "low_full_360_rotation",
        "high_and_low_full_360_rotation",
    },
    "macro_rotation": {"macro_full_360_rotation"},
    "mechanism_state_change": {"mechanism_state_change_no_orbit"},
}
PITCHED_SCOPE_PREFIXES: dict[str, set[str]] = {
    "high_full_360_rotation": {"HIGH"},
    "low_full_360_rotation": {"LOW"},
    "high_and_low_full_360_rotation": {"HIGH", "LOW"},
}
REVIEW_BOARD_ROLES = {
    "neutral_rotation", "elevation", "framing_bridge",
    "copy", "code", "structure", "material",
}
MIN_MACHINE_MASTER_WIDTH_PX = 1280
MIN_MACHINE_MASTER_HEIGHT_PX = 720
MASTER_RESOLUTION_CONTRACT = {
    "aspect_ratio": "16:9",
    "minimum_native_width_px": MIN_MACHINE_MASTER_WIDTH_PX,
    "minimum_native_height_px": MIN_MACHINE_MASTER_HEIGHT_PX,
    "post_generation_resize_allowed_to_meet_minimum": False,
    "external_4k_is_separate_delivery_state": True,
}


def derive_minimum_rotation_profile(product_features: list[str] | set[str]) -> str:
    features = set(product_features)
    if features.intersection(R24_FEATURES):
        return "R24"
    if features.intersection(R16_FEATURES):
        return "R16"
    if {"simple_near_rotational_symmetry", "low_copy_risk"}.issubset(features) and "ordinary_label_heavy_packaging" not in features:
        return "R8"
    return "R12"


def dynamic_region_detail_view_id(region_id: str) -> str:
    """Return a readable, collision-resistant stable view ID for one exact-copy region."""
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", region_id).strip("_").upper()
    if normalized.startswith("REGION_"):
        normalized = normalized[len("REGION_"):]
    normalized = (normalized or "UNNAMED")[:48]
    digest = hashlib.sha256(region_id.encode("utf-8")).hexdigest()[:8].upper()
    return f"DETAIL_REGION_{normalized}_{digest}"


def derive_dynamic_region_detail_specs(
    text_fields: dict[str, dict[str, Any]],
    code_records: dict[str, dict[str, Any]],
    graphic_records: dict[str, dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Compile one mandatory exact-copy detail master per physical region."""
    by_region: dict[str, dict[str, Any]] = {}
    for record_id, record, evidence_key in [
        *[(key, value, "field_ids") for key, value in text_fields.items()],
        *[(key, value, "code_ids") for key, value in code_records.items()],
        *[(key, value, "graphic_ids") for key, value in graphic_records.items()],
    ]:
        region_id = record.get("region_id")
        surface_id = record.get("surface_id")
        if not isinstance(region_id, str) or not region_id:
            if errors is not None:
                errors.append(f"exact-copy evidence {record_id}: region_id is required for dynamic detail derivation")
            continue
        if not isinstance(surface_id, str) or not surface_id:
            if errors is not None:
                errors.append(f"exact-copy evidence {record_id}: surface_id is required for dynamic detail derivation")
            continue
        entry = by_region.setdefault(region_id, {
            "region_id": region_id, "surface_id": surface_id,
            "field_ids": [], "code_ids": [], "graphic_ids": [],
        })
        if entry["surface_id"] != surface_id:
            if errors is not None:
                errors.append(f"exact-copy region {region_id}: records disagree on physical surface")
            continue
        entry[evidence_key].append(record_id)
    output: dict[str, dict[str, Any]] = {}
    for region_id, entry in sorted(by_region.items()):
        for key in ("field_ids", "code_ids", "graphic_ids"):
            entry[key] = sorted(set(entry[key]))
        has_code = bool(entry["code_ids"])
        view_id = dynamic_region_detail_view_id(region_id)
        entry.update({
            "view_id": view_id,
            "family": DYNAMIC_REGION_DETAIL_CONTRACT.get(
                "family_for_any_code" if has_code else "family_for_text_or_graphic"
            ),
            "shot_scale": DYNAMIC_REGION_DETAIL_CONTRACT.get("shot_scale"),
            "review_board_role": DYNAMIC_REGION_DETAIL_CONTRACT.get(
                "review_board_role_for_any_code" if has_code
                else "review_board_role_for_text_or_graphic"
            ),
            "framing_contract": DYNAMIC_REGION_DETAIL_CONTRACT.get("framing_contract"),
            "focus_contract": DYNAMIC_REGION_DETAIL_CONTRACT.get("focus_contract"),
            "native_region_pixel_contract": {
                key: DYNAMIC_REGION_DETAIL_CONTRACT.get(key)
                for key in (
                    "reference_canvas_px", "min_region_width_px_at_reference",
                    "min_region_height_px_at_reference",
                    "min_text_line_height_px_at_reference",
                    "min_code_short_edge_px_at_reference",
                    "min_graphic_short_edge_px_at_reference",
                )
            },
        })
        if view_id in output and output[view_id]["region_id"] != region_id:
            if errors is not None:
                errors.append(
                    f"exact-copy regions {output[view_id]['region_id']} and {region_id}: dynamic detail view ID collision"
                )
            continue
        output[view_id] = entry
    return output


def required_pitched_prefixes(
    motion_envelope: dict[str, Any] | None, errors: list[str],
) -> set[str]:
    if not isinstance(motion_envelope, dict):
        errors.append("motion_envelope: object is required")
        return set()
    motion_type = motion_envelope.get("motion_type")
    motion_scope = motion_envelope.get("motion_scope")
    allowed_scopes = MOTION_SCOPE_BY_TYPE.get(motion_type)
    if allowed_scopes is None:
        errors.append("motion_envelope: motion_type is not a canonical enum value")
        return set()
    if motion_scope not in allowed_scopes:
        errors.append("motion_envelope: motion_scope is incompatible with motion_type")
        return set()
    return set(PITCHED_SCOPE_PREFIXES.get(str(motion_scope), set()))


def board_semantic_role_for_view(view_id: str, view: dict[str, Any]) -> str | None:
    family = view.get("family")
    if family == "neutral_ring":
        return "neutral_rotation"
    if family in {"high_angle", "low_angle", "top_bottom"}:
        return "elevation"
    if family in {"upper_half_close", "lower_half_close"}:
        return "framing_bridge"
    return {
        "detail_copy": "copy", "detail_code": "code",
        "detail_structure": "structure", "detail_material": "material",
    }.get(str(family))


def semantic_board_order_key(view_id: str, view: dict[str, Any]) -> tuple[int, float, str]:
    family = str(view.get("family", ""))
    if family == "neutral_ring":
        return (0, float(view.get("azimuth_deg", 0.0)), view_id)
    elevation_order = {"high_angle": 0, "low_angle": 1, "top_bottom": 2}
    if family in elevation_order:
        return (elevation_order[family], float(view.get("azimuth_deg", 0.0)), view_id)
    bridge_order = {"upper_half_close": 0, "lower_half_close": 1}
    if family in bridge_order:
        return (bridge_order[family], float(view.get("azimuth_deg", 0.0)), view_id)
    return (0, 0.0, view_id)
EXECUTABLE_PROJECTION_MODELS = {
    "source_pixel_preservation", "planar_rectangle", "planar_homography",
}
SOURCE_STATUS_KEYS = (
    "pose_source_status", "surface_source_status", "copy_source_status", "material_source_status",
)
DIRECT_SOURCE_STATUSES = {"source_verified", "not_applicable_no_visible_content"}
CONTINUITY_MEASUREMENT_METHODS = {
    "deterministic_landmark_mask_metric_v1", "calibrated_feature_track_metric_v1",
}
STAGES = [
    "SOURCE_INGESTED", "OCR_DISCOVERY_COMPLETE", "COPY_REVIEW_REQUIRED",
    "COPY_SSOT_FROZEN", "COVERAGE_PLAN_FROZEN", "READY_FOR_GENERATION",
    "GENERATING", "INSPECTING", "COMPOSITING_EXACT_COPY",
    "POST_COMPOSITE_VERIFYING", "BUILDING_REVIEW_BOARDS", "QA_PASSED", "COMPLETE",
]
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
ALL_CONTINUITY_GATES = UNIVERSAL_CONTINUITY_GATES | set().union(
    *FEATURE_CONDITIONED_CONTINUITY_GATES.values()
)
# Compatibility export: this is the registry of all legal gates, not the gate
# set required for every product. Use derive_required_continuity_gates().
REQUIRED_CONTINUITY_GATES = ALL_CONTINUITY_GATES
_PROMPT_COMPILER_MODULE: Any | None = None


def derive_required_continuity_gates(product_features: list[str] | set[str]) -> set[str]:
    required = set(UNIVERSAL_CONTINUITY_GATES)
    for feature_id in set(product_features):
        required.update(FEATURE_CONDITIONED_CONTINUITY_GATES.get(feature_id, set()))
    return required


def prompt_compiler_module() -> Any:
    """Load the canonical prompt compiler so validation can replay exact bytes."""
    global _PROMPT_COMPILER_MODULE
    if _PROMPT_COMPILER_MODULE is not None:
        return _PROMPT_COMPILER_MODULE
    path = SKILL_DIR / "scripts/compile_generation_prompts.py"
    spec = importlib.util.spec_from_file_location("_packaging_prompt_compiler_replay", path)
    if spec is None or spec.loader is None:
        raise ImportError("canonical packaging prompt compiler is unavailable")
    scripts_dir = str(path.parent)
    inserted = scripts_dir not in sys.path
    if inserted:
        sys.path.insert(0, scripts_dir)
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if inserted and scripts_dir in sys.path:
            sys.path.remove(scripts_dir)
    _PROMPT_COMPILER_MODULE = module
    return module


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_hash(value: dict[str, Any], omit: str | None = None) -> str:
    payload = dict(value)
    if omit:
        payload.pop(omit, None)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def safe_run_path(root: Path, locator: Any, label: str) -> tuple[Path | None, list[str]]:
    if not isinstance(locator, str) or not locator:
        return None, [f"{label}: locator must be non-empty"]
    path = Path(locator)
    if path.is_absolute() or ".." in path.parts:
        return None, [f"{label}: locator must be run-relative and cannot contain '..'"]
    resolved_root = root.resolve()
    candidate = (resolved_root / path).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError:
        return None, [f"{label}: locator escapes the run root"]
    if not candidate.is_file():
        return None, [f"{label}: missing file {locator}"]
    return candidate, []


def resolve_source_path(root: Path, locator: Any) -> Path | None:
    if not isinstance(locator, str) or not locator:
        return None
    path = Path(locator)
    return path if path.is_absolute() else (root / path).resolve()


def path_ends_with_run_locator(value: Any, locator: Any) -> bool:
    """Bind historical worker evidence to a relocatable run-relative artifact.

    The receipt builder verifies the exact absolute worker output path while the
    run is being assembled.  COMPLETE packages may later be copied or archived,
    so steady-state validation compares the immutable historical path's suffix
    to the receipt-bound run locator instead of requiring the old absolute root.
    Both Windows and POSIX separators are accepted for cross-machine review.
    """
    if not isinstance(value, str) or not value or not isinstance(locator, str) or not locator:
        return False
    value_parts = [part.casefold() for part in re.split(r"[\\/]+", value) if part not in ("", ".")]
    locator_parts = [part.casefold() for part in re.split(r"[\\/]+", locator) if part not in ("", ".")]
    return (
        bool(locator_parts)
        and ".." not in locator_parts
        and len(value_parts) >= len(locator_parts)
        and value_parts[-len(locator_parts):] == locator_parts
    )


def verify_image(path: Path) -> tuple[int, int]:
    if Image is None:
        raise ValueError("Pillow is required for image verification")
    with Image.open(path) as probe:
        size = probe.size
        probe.verify()
    with Image.open(path) as decoded:
        decoded.load()
    return size


def verify_nontrivial_image(path: Path) -> bool:
    if Image is None:
        return False
    with Image.open(path) as opened:
        rgb = opened.convert("RGB")
        extrema = rgb.getextrema()
        if all(low == high for low, high in extrema):
            return False
        colors = rgb.getcolors(maxcolors=16)
        return colors is None or len(colors) >= 8


def normalized_crop_box(
    box: Any, width: int, height: int, origin: Any,
) -> tuple[int, int, int, int] | None:
    if not isinstance(box, dict):
        return None
    try:
        x = float(box["x"]); y = float(box["y"])
        box_width = float(box["width"]); box_height = float(box["height"])
    except (KeyError, TypeError, ValueError):
        return None
    if x < 0 or y < 0 or box_width <= 0 or box_height <= 0 or x + box_width > 1 or y + box_height > 1:
        return None
    left = int(round(x * width)); right = int(round((x + box_width) * width))
    if origin == "bottom_left":
        top = int(round((1.0 - (y + box_height)) * height))
        bottom = int(round((1.0 - y) * height))
    elif origin == "top_left":
        top = int(round(y * height)); bottom = int(round((y + box_height) * height))
    else:
        return None
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def load_bundled_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load bundled module {path}")
    module = importlib.util.module_from_spec(spec)
    # Dataclasses and other runtime type resolvers require the executing module
    # to be present in sys.modules, matching normal import semantics.
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def contains_forbidden_test_marker(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered_key = str(key).lower()
            if ("fixture" in lowered_key or "synthetic" in lowered_key) and item not in (None, False, "", 0):
                return True
            if contains_forbidden_test_marker(item):
                return True
        return False
    if isinstance(value, list):
        return any(contains_forbidden_test_marker(item) for item in value)
    if isinstance(value, str):
        lowered = value.lower()
        return lowered in {"fixture", "synthetic_contract_fixture", "synthetic_contract_evidence"} or lowered.startswith("fixture_")
    return False


def require_sha(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        errors.append(f"{label}: expected lowercase SHA-256")


def load_locked_json(root: Path, manifest: dict[str, Any], path_key: str, hash_key: str, errors: list[str]) -> dict[str, Any] | None:
    locator = manifest.get("paths", {}).get(path_key)
    path, path_errors = safe_run_path(root, locator, path_key)
    errors.extend(path_errors)
    if path is None:
        return None
    try:
        value = read_json(path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"{path_key}: invalid strict JSON: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{path_key}: JSON root must be an object")
        return None
    expected = manifest.get("hashes", {}).get(hash_key)
    require_sha(expected, f"hashes.{hash_key}", errors)
    if isinstance(expected, str) and SHA.fullmatch(expected) and sha256_file(path) != expected:
        errors.append(f"{path_key}: file SHA-256 does not match hashes.{hash_key}")
    return value


def load_evidence_json(
    root: Path,
    locator: Any,
    expected_sha256: Any,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    path, path_errors = safe_run_path(root, locator, label)
    errors.extend(path_errors)
    if path is None:
        return None
    require_sha(expected_sha256, f"{label}.file_sha256", errors)
    if isinstance(expected_sha256, str) and SHA.fullmatch(expected_sha256) and sha256_file(path) != expected_sha256:
        errors.append(f"{label}: file SHA-256 mismatch")
    try:
        value = read_json(path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"{label}: invalid strict JSON: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label}: JSON root must be an object")
        return None
    return value


def stage_at_least(stage: str, target: str) -> bool:
    if stage == "BLOCKED":
        return False
    return STAGES.index(stage) >= STAGES.index(target)


def validate_sources(
    root: Path,
    source_manifest: dict[str, Any],
    product_id: Any,
    product_state_id: Any,
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    if source_manifest.get("schema_version") != "packaging-source-manifest.v1":
        errors.append("source_manifest: schema_version must be packaging-source-manifest.v1")
    if source_manifest.get("product_id") != product_id or source_manifest.get("product_state_id") != product_state_id:
        errors.append("source_manifest: product/physical-state identity differs from run manifest")
    if source_manifest.get("variant_resolution_status") != "resolved_single_sku_and_instance":
        errors.append("source_manifest: variant/SKU/instance conflict is unresolved")
    sources = source_manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("source_manifest: sources must be a non-empty array")
        return {}
    by_id: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(sources):
        label = f"source_manifest.sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{label}: must be an object")
            continue
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            errors.append(f"{label}: source_id must be non-empty")
            continue
        if source_id in by_id:
            errors.append(f"{label}: duplicate source_id {source_id}")
        by_id[source_id] = source
        if source.get("product_id") != product_id or source.get("product_state_id") != product_state_id:
            errors.append(f"{label}: source belongs to a different product or physical state")
        source_kind = source.get("source_kind")
        if source_kind not in {
            "direct_product_photograph", "approved_artwork", "dieline",
            "authoritative_text_master", "cad_render", "turntable_frame",
        }:
            errors.append(f"{label}: source_kind must identify the frozen authority type")
        spatial_source = source_kind in {"direct_product_photograph", "turntable_frame", "cad_render"}
        view_id = source.get("view_id")
        if spatial_source:
            if not isinstance(view_id, str) or not re.fullmatch(
                r"(?:ROT|HIGH|LOW)_\d{4}|TOP_0000|BOTTOM_0000", view_id
            ):
                errors.append(f"{label}: view_id must bind the spatial source to one canonical camera pose")
            for pose_key in ("azimuth_deg", "elevation_deg"):
                pose_value = source.get(pose_key)
                if isinstance(pose_value, bool) or not isinstance(pose_value, (int, float)) or not math.isfinite(float(pose_value)):
                    errors.append(f"{label}: {pose_key} must be a finite numeric camera pose")
        else:
            if any(source.get(key) is not None for key in ("view_id", "azimuth_deg", "elevation_deg")):
                errors.append(f"{label}: artwork/text/dieline sources cannot claim a product camera pose")
            applies = [
                item for key in ("applies_to_surface_ids", "applies_to_region_ids", "applies_to_field_ids")
                for item in (source.get(key) or []) if isinstance(item, str) and item
            ]
            if not applies:
                errors.append(f"{label}: evidence-only source requires applies_to surface/region/field IDs")
        visible_surfaces = source.get("visible_surfaces")
        if spatial_source:
            if not isinstance(visible_surfaces, list) or not visible_surfaces or not all(
                isinstance(item, str) and item for item in visible_surfaces
            ):
                errors.append(f"{label}: visible_surfaces must be a non-empty canonical surface ID array")
            elif len(visible_surfaces) != len(set(visible_surfaces)):
                errors.append(f"{label}: visible_surfaces contains duplicates")
        elif visible_surfaces not in (None, []):
            errors.append(f"{label}: evidence-only source cannot claim visible product surfaces")
        visible_components = source.get("visible_component_ids")
        if spatial_source:
            if not isinstance(visible_components, list) or not visible_components or not all(
                isinstance(item, str) and item for item in visible_components
            ):
                errors.append(f"{label}: visible_component_ids must be a non-empty canonical component array")
            elif len(visible_components) != len(set(visible_components)):
                errors.append(f"{label}: visible_component_ids contains duplicates")
        elif visible_components not in (None, []):
            errors.append(f"{label}: evidence-only source cannot claim visible product components")
        if source.get("source_authority") != "authoritative" or source.get("required_for_run") is not True:
            errors.append(f"{label}: production source must be authoritative and required_for_run")
        path = resolve_source_path(root, source.get("file_path"))
        if path is None or not path.is_file():
            errors.append(f"{label}: source file does not exist")
            continue
        expected = source.get("file_sha256")
        require_sha(expected, f"{label}.file_sha256", errors)
        if isinstance(expected, str) and SHA.fullmatch(expected) and sha256_file(path) != expected:
            errors.append(f"{label}: source file hash mismatch")
        try:
            width, height = verify_image(path)
        except Exception as exc:
            errors.append(f"{label}: image verification failed: {exc}")
            continue
        if source.get("pixel_dimensions") != {"width": width, "height": height}:
            errors.append(f"{label}: pixel_dimensions do not match decoded file")
    return by_id


def validate_feature_classification(
    source_manifest: dict[str, Any],
    manifest_features: list[str],
    sources: dict[str, dict[str, Any]],
    rotation_profile: str,
    errors: list[str],
) -> None:
    classification = source_manifest.get("product_feature_classification")
    if not isinstance(classification, list):
        errors.append("source_manifest: product_feature_classification must be an array")
        return
    present: set[str] = set()
    seen: set[str] = set()
    for index, item in enumerate(classification):
        label = f"source_manifest.product_feature_classification[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: must be an object")
            continue
        feature_id = item.get("feature_id")
        if not isinstance(feature_id, str) or not feature_id or feature_id in seen:
            errors.append(f"{label}: feature_id must be unique and non-empty")
            continue
        seen.add(feature_id)
        if feature_id not in CANONICAL_FEATURES:
            errors.append(f"{label}: unknown feature_id {feature_id!r}; feature typos fail closed")
            continue
        status = item.get("status")
        if status == "present":
            present.add(feature_id)
        elif status != "reviewed_absent":
            errors.append(f"{label}: status must be present or reviewed_absent")
        refs = item.get("evidence_source_ids")
        if not isinstance(refs, list) or not refs or not set(refs).issubset(sources):
            errors.append(f"{label}: evidence_source_ids must be a non-empty source subset")
        elif any(sources[ref].get("source_kind") not in {"direct_product_photograph", "turntable_frame", "cad_render"} for ref in refs):
            errors.append(f"{label}: product feature audit requires spatial source evidence, not artwork/text masters")
        if item.get("review_status") != "reviewed" or not isinstance(item.get("reviewer_id"), str) or not item.get("reviewer_id"):
            errors.append(f"{label}: feature presence/absence requires named review")
        if not isinstance(item.get("evidence_note"), str) or not item.get("evidence_note"):
            errors.append(f"{label}: feature presence/absence requires an evidence note")
    if seen != CANONICAL_FEATURES:
        missing = sorted(CANONICAL_FEATURES - seen)
        extra = sorted(seen - CANONICAL_FEATURES)
        errors.append(
            "source_manifest: product_feature_classification must audit the complete canonical taxonomy; "
            f"missing={missing}, extra={extra}"
        )
    if present != set(manifest_features):
        errors.append("source_manifest: observed features must exactly equal run_manifest product_features")
    minimum_profile = derive_minimum_rotation_profile(present)
    if PROFILE_RANK.get(rotation_profile, 0) < PROFILE_RANK[minimum_profile]:
        errors.append(
            f"run manifest: feature-derived minimum rotation profile is {minimum_profile}; selected {rotation_profile} is insufficient"
        )


def validate_ocr(
    root: Path,
    ocr: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[
    dict[str, dict[str, Any]], set[str], dict[str, dict[str, Any]],
    dict[tuple[str, str], dict[str, Any]],
]:
    if ocr.get("schema_version") != "packaging-ocr-observations.v1":
        errors.append("ocr_observations: invalid schema_version")
    expected_preflight_path = "scripts/run_ocr_preflight.py"
    expected_preflight = SKILL_DIR / expected_preflight_path
    if (
        ocr.get("preflight_adapter_path") != expected_preflight_path
        or not expected_preflight.is_file()
        or ocr.get("preflight_adapter_sha256") != sha256_file(expected_preflight)
    ):
        errors.append("ocr_observations: whole-product OCR must bind the installed run_ocr_preflight.py adapter")
    engine = ocr.get("engine")
    engine_adapter_path = ocr.get("engine_adapter_path")
    engine_adapter_sha = ocr.get("engine_adapter_sha256")
    if engine == "macos_vision":
        expected_engine_path = SKILL_DIR / "scripts/macos_vision_ocr.swift"
        if (
            engine_adapter_path != "scripts/macos_vision_ocr.swift"
            or not expected_engine_path.is_file()
            or engine_adapter_sha != sha256_file(expected_engine_path)
        ):
            errors.append("ocr_observations: macOS Vision engine adapter path/hash is not the installed bundled adapter")
    elif engine == "tesseract":
        executable = shutil.which("tesseract")
        if not executable:
            errors.append("ocr_observations: recorded Tesseract engine is unavailable for verification")
        else:
            expected_engine_path = Path(executable).resolve()
            if engine_adapter_path != str(expected_engine_path) or engine_adapter_sha != sha256_file(expected_engine_path):
                errors.append("ocr_observations: Tesseract executable path/hash differs from the recorded adapter")
    else:
        errors.append("ocr_observations: engine must be trusted macos_vision or tesseract")
    if not isinstance(ocr.get("engine_version"), str) or not ocr.get("engine_version"):
        errors.append("ocr_observations: observed engine_version is required")
    languages = ocr.get("language_set")
    if (
        not isinstance(languages, list) or not languages
        or len(languages) != len(set(languages))
        or any(not isinstance(item, str) or not item for item in languages)
    ):
        errors.append("ocr_observations: language_set must be a non-empty unique string array")
        languages = []
    if ocr.get("ledger_semantic_sha256") != canonical_hash(ocr, "ledger_semantic_sha256"):
        errors.append("ocr_observations: candidate ledger semantic self-hash mismatch")
    if ocr.get("uses_language_correction") is not False:
        errors.append("ocr_observations: language correction must be false")
    if ocr.get("preflight_status") != "observations_ready":
        errors.append("ocr_observations: preflight_status must be observations_ready")
    records = ocr.get("source_records")
    if not isinstance(records, list):
        errors.append("ocr_observations: source_records must be an array")
        return {}, set(), {}, {}
    seen: set[str] = set()
    pass_ids: set[str] = set()
    observations: dict[str, dict[str, Any]] = {}
    code_observations: dict[str, dict[str, Any]] = {}
    region_authorities: dict[tuple[str, str], dict[str, Any]] = {}
    region_ids: set[str] = set()
    for index, record in enumerate(records):
        label = f"ocr_observations.source_records[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{label}: must be an object")
            continue
        source_id = record.get("source_id")
        if source_id in seen:
            errors.append(f"{label}: duplicate source_id")
        if isinstance(source_id, str):
            seen.add(source_id)
        source = sources.get(source_id) if isinstance(source_id, str) else None
        if source is None:
            errors.append(f"{label}: source_id does not exist in source_manifest")
        else:
            if record.get("file_path") != source.get("file_path"):
                source_path = resolve_source_path(root, source.get("file_path"))
                record_path = resolve_source_path(root, record.get("file_path"))
                if source_path is None or record_path is None or source_path.resolve() != record_path.resolve():
                    errors.append(f"{label}: file_path does not match source_manifest")
            if record.get("file_sha256") != source.get("file_sha256"):
                errors.append(f"{label}: file_sha256 does not match source_manifest")
            if record.get("pixel_dimensions") != source.get("pixel_dimensions"):
                errors.append(f"{label}: pixel_dimensions do not match source_manifest")
        if record.get("ocr_review_status") != "reviewed":
            errors.append(f"{label}: ocr_review_status must be reviewed before exact-copy generation")
        passes = record.get("whole_product_ocr_passes")
        if not isinstance(passes, list) or not passes:
            errors.append(f"{label}: every source requires a whole-product OCR pass")
            continue
        if not any(item.get("scope") == "whole_product" for item in passes if isinstance(item, dict)):
            errors.append(f"{label}: no whole_product OCR scope")
        if any(item.get("uses_language_correction") is not False for item in passes if isinstance(item, dict)):
            errors.append(f"{label}: OCR passes must disable language correction")
        text_observations = record.get("text_observations")
        if not isinstance(text_observations, list):
            errors.append(f"{label}: text_observations must be an array")
            text_observations = []
        whole_count = sum(
            1 for item in text_observations
            if isinstance(item, dict) and item.get("scope") == "whole_product"
        )
        declared_count = sum(
            int(item.get("observation_count", -1))
            for item in passes if isinstance(item, dict) and item.get("scope") == "whole_product"
        )
        if declared_count != whole_count:
            errors.append(f"{label}: whole-product observation_count does not match observations")
        if whole_count == 0 and record.get("zero_detection_review_status") != "reviewed_no_copy_detected":
            errors.append(f"{label}: zero OCR detections require reviewed_no_copy_detected evidence")
        for pass_index, pass_record in enumerate(passes):
            if not isinstance(pass_record, dict):
                errors.append(f"{label}.whole_product_ocr_passes[{pass_index}]: must be an object")
                continue
            pass_id = pass_record.get("pass_id")
            if not isinstance(pass_id, str) or not pass_id or pass_id in pass_ids:
                errors.append(f"{label}.whole_product_ocr_passes[{pass_index}]: pass_id must be globally unique")
            else:
                pass_ids.add(pass_id)
            if not isinstance(pass_record.get("engine_version"), str) or not pass_record.get("engine_version"):
                errors.append(f"{label}.whole_product_ocr_passes[{pass_index}]: engine_version is required")
            if (
                pass_record.get("engine_id") != engine
                or pass_record.get("engine_version") != ocr.get("engine_version")
                or pass_record.get("language_set") != languages
                or pass_record.get("preflight_adapter_path") != expected_preflight_path
                or pass_record.get("preflight_adapter_sha256") != ocr.get("preflight_adapter_sha256")
                or pass_record.get("engine_adapter_path") != engine_adapter_path
                or pass_record.get("engine_adapter_sha256") != engine_adapter_sha
            ):
                errors.append(f"{label}.whole_product_ocr_passes[{pass_index}]: engine/language/adapter receipt differs from the trusted whole-product preflight")
            if pass_record.get("source_sha256") != record.get("file_sha256"):
                errors.append(f"{label}.whole_product_ocr_passes[{pass_index}]: source_sha256 must bind source bytes")

        region_passes = record.get("region_ocr_passes")
        if not isinstance(region_passes, list):
            errors.append(f"{label}: region_ocr_passes must be an array")
            region_passes = []
        region_pass_by_id: dict[str, dict[str, Any]] = {}
        for region_index, region_pass in enumerate(region_passes):
            region_label = f"{label}.region_ocr_passes[{region_index}]"
            if not isinstance(region_pass, dict):
                errors.append(f"{region_label}: must be an object")
                continue
            pass_id = region_pass.get("pass_id")
            region_id = region_pass.get("region_id")
            if not isinstance(pass_id, str) or not pass_id or pass_id in pass_ids:
                errors.append(f"{region_label}: pass_id must be globally unique")
            else:
                pass_ids.add(pass_id)
                region_pass_by_id[pass_id] = region_pass
            if not isinstance(region_id, str) or not region_id:
                errors.append(f"{region_label}: region_id must be non-empty")
            else:
                region_ids.add(region_id)
            surface_id = region_pass.get("surface_id")
            physical_layer_id = region_pass.get("physical_layer_id")
            visibility_mode = region_pass.get("visibility_mode")
            region_purpose = region_pass.get("region_purpose")
            if not isinstance(surface_id, str) or not surface_id:
                errors.append(f"{region_label}: surface_id must be non-empty")
            if not isinstance(physical_layer_id, str) or not physical_layer_id:
                errors.append(f"{region_label}: physical_layer_id must be non-empty")
            if visibility_mode not in REGION_VISIBILITY_MODES:
                errors.append(f"{region_label}: visibility_mode is invalid")
            if region_purpose not in REGION_PURPOSES:
                errors.append(f"{region_label}: region_purpose must be text, code, graphic, or mixed")
            if region_pass.get("uses_language_correction") is not False:
                errors.append(f"{region_label}: language correction must be false")
            observation_count = region_pass.get("observation_count")
            if observation_count == 0:
                if region_purpose in TEXT_REQUIRED_REGION_PURPOSES:
                    errors.append(
                        f"{region_label}: text/mixed region requires at least one text OCR detection"
                    )
                    if region_pass.get("zero_detection_review_status") != "review_required":
                        errors.append(
                            f"{region_label}: zero-text text/mixed region must remain review_required"
                        )
                elif region_purpose in {"code", "graphic"}:
                    if region_pass.get("zero_detection_review_status") != "not_applicable_non_text_region":
                        errors.append(
                            f"{region_label}: zero-text code/graphic region must declare not_applicable_non_text_region"
                        )
            elif region_pass.get("zero_detection_review_status") != "not_applicable":
                errors.append(f"{region_label}: non-empty region pass must set zero_detection_review_status=not_applicable")
            if region_pass.get("source_id") != source_id or region_pass.get("source_file_sha256") != record.get("file_sha256"):
                errors.append(f"{region_label}: source identity/hash binding failed")
            expected_rectifier = SKILL_DIR / "scripts/run_region_ocr.py"
            if region_pass.get("crop_method") != "axis_aligned_normalized_bbox_v1":
                errors.append(f"{region_label}: unsupported crop_method")
            if region_pass.get("rectifier_script_sha256") != sha256_file(expected_rectifier):
                errors.append(f"{region_label}: rectifier must bind the installed run_region_ocr.py")
            region_spec = load_evidence_json(
                root, region_pass.get("region_spec_path"), region_pass.get("region_spec_sha256"),
                f"{region_label}.region_spec", errors,
            )
            matching_spec = None
            if region_spec:
                if region_spec.get("schema_version") != "packaging-region-ocr-spec.v2":
                    errors.append(f"{region_label}: invalid region spec schema")
                if region_spec.get("source_id") != source_id:
                    errors.append(f"{region_label}: region spec source_id differs from its OCR source")
                matches = [
                    item for item in region_spec.get("regions", [])
                    if isinstance(item, dict) and item.get("region_id") == region_id
                ] if isinstance(region_spec.get("regions"), list) else []
                if len(matches) != 1:
                    errors.append(f"{region_label}: region spec must contain exactly one matching region")
                else:
                    matching_spec = matches[0]
                    if (
                        matching_spec.get("coordinate_origin") != region_pass.get("coordinate_origin")
                        or matching_spec.get("bounding_box_normalized") != region_pass.get("bounding_box_normalized")
                        or matching_spec.get("surface_id") != surface_id
                        or matching_spec.get("physical_layer_id") != physical_layer_id
                        or matching_spec.get("visibility_mode") != visibility_mode
                        or matching_spec.get("region_purpose") != region_purpose
                    ):
                        errors.append(f"{region_label}: crop geometry or region authority metadata differs from region spec")
            source_dimensions = record.get("pixel_dimensions") or {}
            expected_crop_box = normalized_crop_box(
                region_pass.get("bounding_box_normalized"),
                int(source_dimensions.get("width", 0)),
                int(source_dimensions.get("height", 0)),
                region_pass.get("coordinate_origin"),
            )
            source_path_from_record = resolve_source_path(root, record.get("file_path"))
            crop_receipt = load_evidence_json(
                root, region_pass.get("crop_receipt_path"), region_pass.get("crop_receipt_sha256"),
                f"{region_label}.crop_receipt", errors,
            )
            if not crop_receipt or (
                crop_receipt.get("schema_version") != "packaging-region-crop-receipt.v2"
                or crop_receipt.get("receipt_sha256") != canonical_hash(crop_receipt, "receipt_sha256")
                or crop_receipt.get("receipt_sha256") != region_pass.get("crop_receipt_semantic_sha256")
                or crop_receipt.get("source_id") != source_id
                or resolve_source_path(root, crop_receipt.get("source_path")) != source_path_from_record
                or crop_receipt.get("source_file_sha256") != record.get("file_sha256")
                or crop_receipt.get("source_pixel_dimensions") != record.get("pixel_dimensions")
                or crop_receipt.get("region_id") != region_id
                or crop_receipt.get("surface_id") != surface_id
                or crop_receipt.get("physical_layer_id") != physical_layer_id
                or crop_receipt.get("visibility_mode") != visibility_mode
                or crop_receipt.get("region_purpose") != region_purpose
                or crop_receipt.get("region_spec_path") != region_pass.get("region_spec_path")
                or crop_receipt.get("region_spec_sha256") != region_pass.get("region_spec_sha256")
                or crop_receipt.get("coordinate_origin") != region_pass.get("coordinate_origin")
                or crop_receipt.get("bounding_box_normalized") != region_pass.get("bounding_box_normalized")
                or crop_receipt.get("crop_box_px") != (
                    list(expected_crop_box) if expected_crop_box is not None else None
                )
                or crop_receipt.get("crop_method") != "axis_aligned_normalized_bbox_v1"
                or crop_receipt.get("rectifier_script_sha256") != sha256_file(expected_rectifier)
                or crop_receipt.get("rectified_crop_path") != region_pass.get("rectified_crop_path")
                or crop_receipt.get("rectified_crop_sha256") != region_pass.get("rectified_crop_sha256")
            ):
                errors.append(f"{region_label}: crop derivation receipt failed")
            crop_path = resolve_source_path(root, region_pass.get("rectified_crop_path"))
            expected_crop_hash = region_pass.get("rectified_crop_sha256")
            if crop_path is None or not crop_path.is_file():
                errors.append(f"{region_label}: rectified crop is missing")
            elif expected_crop_hash != sha256_file(crop_path):
                errors.append(f"{region_label}: rectified crop hash mismatch")
            elif source is not None and Image is not None:
                source_path = resolve_source_path(root, source.get("file_path"))
                dimensions = source.get("pixel_dimensions") or {}
                crop_box = normalized_crop_box(
                    region_pass.get("bounding_box_normalized"),
                    int(dimensions.get("width", 0)), int(dimensions.get("height", 0)),
                    region_pass.get("coordinate_origin"),
                )
                if source_path is None or crop_box is None:
                    errors.append(f"{region_label}: source crop geometry is invalid")
                else:
                    try:
                        with Image.open(source_path) as source_image, Image.open(crop_path) as crop_image:
                            expected_pixels = source_image.convert("RGB").crop(crop_box)
                            actual_pixels = crop_image.convert("RGB")
                            if expected_pixels.size != actual_pixels.size or expected_pixels.tobytes() != actual_pixels.tobytes():
                                errors.append(f"{region_label}: crop pixels are not derived from locked source geometry")
                    except Exception as exc:
                        errors.append(f"{region_label}: source crop replay failed: {exc}")
            if isinstance(source_id, str) and isinstance(region_id, str):
                authority_key = (source_id, region_id)
                if authority_key in region_authorities:
                    errors.append(f"{region_label}: duplicate source/region authority")
                else:
                    region_authorities[authority_key] = {
                        "source_id": source_id,
                        "region_id": region_id,
                        "surface_id": surface_id,
                        "physical_layer_id": physical_layer_id,
                        "visibility_mode": visibility_mode,
                        "region_purpose": region_purpose,
                        "observation_count": observation_count,
                        "rectified_crop_path": region_pass.get("rectified_crop_path"),
                        "rectified_crop_sha256": region_pass.get("rectified_crop_sha256"),
                        "crop_receipt_path": region_pass.get("crop_receipt_path"),
                        "crop_receipt_sha256": region_pass.get("crop_receipt_sha256"),
                        "crop_receipt_semantic_sha256": region_pass.get("crop_receipt_semantic_sha256"),
                    }

        observed_region_counts: dict[str, int] = {}
        for observation_index, observation in enumerate(text_observations):
            observation_label = f"{label}.text_observations[{observation_index}]"
            if not isinstance(observation, dict):
                errors.append(f"{observation_label}: must be an object")
                continue
            observation_id = observation.get("observation_id")
            if not isinstance(observation_id, str) or not observation_id or observation_id in observations:
                errors.append(f"{observation_label}: observation_id must be globally unique")
                continue
            if not isinstance(observation.get("text"), str) or not observation.get("text"):
                errors.append(f"{observation_label}: text must be non-empty")
            copy_record = dict(observation)
            copy_record["source_id"] = source_id
            observations[observation_id] = copy_record
            disposition = observation.get("disposition")
            if not isinstance(disposition, dict):
                errors.append(f"{observation_label}: every OCR detection requires a disposition")
            else:
                disposition_status = disposition.get("status")
                if disposition_status not in {
                    "mapped_to_field", "duplicate_showthrough", "decorative_non_product_copy", "false_positive"
                }:
                    errors.append(f"{observation_label}: unresolved OCR disposition blocks exact-copy generation")
                if disposition.get("review_status") != "reviewed" or not isinstance(disposition.get("reviewer_id"), str) or not disposition.get("reviewer_id"):
                    errors.append(f"{observation_label}: OCR disposition requires named human review")
                if not isinstance(disposition.get("evidence_note"), str) or not disposition.get("evidence_note"):
                    errors.append(f"{observation_label}: OCR disposition requires evidence_note")
                if disposition_status == "mapped_to_field" and not isinstance(disposition.get("field_id"), str):
                    errors.append(f"{observation_label}: mapped OCR disposition requires field_id")
            if observation.get("scope") == "region":
                region_id = observation.get("region_id")
                region_pass_id = observation.get("region_pass_id")
                if not isinstance(region_id, str) or not region_id:
                    errors.append(f"{observation_label}: region observation requires region_id")
                if region_pass_id not in region_pass_by_id:
                    errors.append(f"{observation_label}: region_pass_id does not bind a source region pass")
                else:
                    region_pass = region_pass_by_id[region_pass_id]
                    if region_pass.get("region_id") != region_id:
                        errors.append(f"{observation_label}: region_id differs from its region pass")
                    for key in ("surface_id", "physical_layer_id", "visibility_mode", "region_purpose"):
                        if observation.get(key) != region_pass.get(key):
                            errors.append(f"{observation_label}: {key} differs from its region authority pass")
                    observed_region_counts[region_pass_id] = observed_region_counts.get(region_pass_id, 0) + 1
        for pass_id, region_pass in region_pass_by_id.items():
            if region_pass.get("observation_count") != observed_region_counts.get(pass_id, 0):
                errors.append(f"{label}: region OCR observation_count mismatch for {pass_id}")
            if (
                observed_region_counts.get(pass_id, 0) == 0
                and region_pass.get("region_purpose") in TEXT_REQUIRED_REGION_PURPOSES
            ):
                errors.append(f"{label}: text-bearing exact-copy region OCR pass cannot be empty")
        source_code_observations = record.get("code_observations")
        if not isinstance(source_code_observations, list):
            errors.append(f"{label}: code_observations must be an array")
            source_code_observations = []
        for code_index, code in enumerate(source_code_observations):
            code_label = f"{label}.code_observations[{code_index}]"
            if not isinstance(code, dict):
                errors.append(f"{code_label}: must be an object")
                continue
            code_id = code.get("code_id")
            if not isinstance(code_id, str) or not code_id or code_id in code_observations:
                errors.append(f"{code_label}: code_id must be globally unique")
                continue
            disposition = code.get("disposition")
            if not isinstance(disposition, dict):
                errors.append(f"{code_label}: every decoded code requires a disposition")
            else:
                status = disposition.get("status")
                if status not in {
                    "mapped_to_code", "duplicate_code_observation", "decorative_non_product_code", "false_positive"
                }:
                    errors.append(f"{code_label}: unresolved decoded-code disposition blocks exact-copy generation")
                if disposition.get("review_status") != "reviewed" or not isinstance(disposition.get("reviewer_id"), str) or not disposition.get("reviewer_id"):
                    errors.append(f"{code_label}: decoded-code disposition requires named human review")
                if not isinstance(disposition.get("evidence_note"), str) or not disposition.get("evidence_note"):
                    errors.append(f"{code_label}: decoded-code disposition requires evidence_note")
                if status == "mapped_to_code" and not isinstance(disposition.get("manifest_code_id"), str):
                    errors.append(f"{code_label}: mapped decoded code requires manifest_code_id")
            copy_code = dict(code)
            copy_code["source_id"] = source_id
            code_observations[code_id] = copy_code
    if seen != set(sources):
        errors.append("ocr_observations: source IDs must exactly cover source_manifest sources")
    return observations, region_ids, code_observations, region_authorities


def validate_surface_inventory(
    inventory: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[set[str], set[str], set[str], set[str], set[str], dict[str, str]]:
    if inventory.get("schema_version") != "packaging-surface-inventory.v1":
        errors.append("surface_inventory: invalid schema_version")
    surfaces = inventory.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        errors.append("surface_inventory: surfaces must be a non-empty array")
        return set(), set(), set(), set(), set(), {}
    required_surface_ids = inventory.get("required_surface_ids")
    if not isinstance(required_surface_ids, list) or not required_surface_ids:
        errors.append("surface_inventory: required_surface_ids must be non-empty")
        required_surface_ids = []
    surface_ids: set[str] = set()
    region_ids: set[str] = set()
    copy_field_ids: set[str] = set()
    code_ids: set[str] = set()
    graphic_ids: set[str] = set()
    surface_by_role: dict[str, str] = {}
    for index, surface in enumerate(surfaces):
        label = f"surface_inventory.surfaces[{index}]"
        if not isinstance(surface, dict):
            errors.append(f"{label}: must be an object")
            continue
        surface_id = surface.get("surface_id")
        if not isinstance(surface_id, str) or not surface_id or surface_id in surface_ids:
            errors.append(f"{label}: surface_id must be unique and non-empty")
            continue
        surface_ids.add(surface_id)
        semantic_role = surface.get("semantic_role")
        if semantic_role not in {"front", "back", "left", "right", "top", "bottom", "auxiliary"}:
            errors.append(f"{label}: semantic_role must use the canonical product coordinate frame")
        elif semantic_role != "auxiliary":
            if semantic_role in surface_by_role:
                errors.append(f"{label}: duplicate canonical semantic_role {semantic_role}")
            else:
                surface_by_role[semantic_role] = surface_id
        physical_layer_ids = surface.get("physical_layer_ids")
        if not isinstance(physical_layer_ids, list) or not physical_layer_ids:
            errors.append(f"{label}: physical_layer_ids must be a non-empty unique string array")
        elif any(not isinstance(item, str) or not item for item in physical_layer_ids):
            errors.append(f"{label}: physical_layer_ids must be a non-empty unique string array")
        elif len(physical_layer_ids) != len(set(physical_layer_ids)):
            errors.append(f"{label}: physical_layer_ids must be a non-empty unique string array")
        if surface.get("coverage_status") not in {"accounted", "verified_no_copy"}:
            errors.append(f"{label}: coverage_status must be accounted or verified_no_copy")
        text_detection_status = surface.get("text_detection_status")
        if text_detection_status not in {
            "text_detected", "verified_no_copy", "decorative_graphic", "occluded", "needs_source",
        }:
            errors.append(
                f"{label}: text_detection_status must be text_detected, verified_no_copy, "
                "decorative_graphic, occluded, or needs_source"
            )
        if text_detection_status in {"occluded", "needs_source"}:
            errors.append(f"{label}: unresolved surface copy status blocks a production-ready exact-copy inventory")
        if surface.get("coverage_status") == "verified_no_copy" or surface.get("text_detection_status") == "verified_no_copy":
            if surface.get("no_copy_review_status") != "reviewed" or not isinstance(surface.get("no_copy_reviewer_id"), str) or not surface.get("no_copy_reviewer_id"):
                errors.append(f"{label}: verified_no_copy requires named review evidence")
            if not isinstance(surface.get("no_copy_evidence_note"), str) or not surface.get("no_copy_evidence_note"):
                errors.append(f"{label}: verified_no_copy requires evidence_note")
        refs = surface.get("source_refs")
        if not isinstance(refs, list) or not refs or not set(refs).issubset(sources):
            errors.append(f"{label}: source_refs must be a non-empty subset of source_manifest")
        detected = text_detection_status == "text_detected"
        if text_detection_status == "decorative_graphic" and not surface.get("required_graphic_ids"):
            errors.append(f"{label}: decorative_graphic requires required_graphic_ids")
        field_ids = surface.get("required_copy_field_ids")
        if not isinstance(field_ids, list):
            errors.append(f"{label}: required_copy_field_ids must be an array")
            field_ids = []
        if detected and not field_ids:
            errors.append(f"{label}: detected/expected copy requires required_copy_field_ids")
        copy_field_ids.update(item for item in field_ids if isinstance(item, str) and item)
        surface_region_ids = surface.get("region_ids")
        if not isinstance(surface_region_ids, list):
            errors.append(f"{label}: region_ids must be an array")
            surface_region_ids = []
        if detected and not surface_region_ids:
            errors.append(f"{label}: detected/expected copy requires region_ids")
        region_ids.update(item for item in surface_region_ids if isinstance(item, str) and item)
        for key, target in (("required_code_ids", code_ids), ("required_graphic_ids", graphic_ids)):
            values = surface.get(key)
            if not isinstance(values, list):
                errors.append(f"{label}: {key} must be an array")
                continue
            target.update(item for item in values if isinstance(item, str) and item)
    if surface_ids != set(required_surface_ids):
        errors.append("surface_inventory: required_surface_ids must exactly equal surface records")
    source_visible = {
        item for source in sources.values()
        for item in source.get("visible_surfaces", []) if isinstance(item, str)
    }
    if not surface_ids.issubset(source_visible):
        errors.append("surface_inventory: every required surface needs source evidence")
    missing_roles = {"front", "back", "left", "right", "top", "bottom"} - set(surface_by_role)
    if missing_roles:
        errors.append("surface_inventory: missing canonical coordinate surfaces: " + ", ".join(sorted(missing_roles)))
    return surface_ids, region_ids, copy_field_ids, code_ids, graphic_ids, surface_by_role


def authority_asset_has_source_provenance(
    root: Path,
    asset_locator: Any,
    asset_sha256: Any,
    authority_source_ids: list[str],
    region_id: Any,
    sources: dict[str, dict[str, Any]],
    region_authorities: dict[tuple[str, str], dict[str, Any]],
    *,
    allowed_basis: str,
) -> bool:
    """Prove authority bytes are either a replayed source crop or a source master."""
    asset_path = resolve_source_path(root, asset_locator)
    if asset_path is None or not asset_path.is_file() or asset_sha256 != sha256_file(asset_path):
        return False
    for source_id in authority_source_ids:
        source = sources.get(source_id)
        if not isinstance(source, dict):
            continue
        if allowed_basis in {"source_crop", "either"} and isinstance(region_id, str):
            region = region_authorities.get((source_id, region_id))
            if isinstance(region, dict):
                crop_path = resolve_source_path(root, region.get("rectified_crop_path"))
                if (
                    crop_path is not None and crop_path.is_file()
                    and crop_path.resolve() == asset_path.resolve()
                    and region.get("rectified_crop_sha256") == asset_sha256
                    and region.get("visibility_mode") in {"direct", "oblique"}
                ):
                    return True
        if allowed_basis in {"artwork_master", "either"} and source.get("source_kind") in {
            "approved_artwork", "dieline", "authoritative_text_master",
        }:
            source_path = resolve_source_path(root, source.get("file_path"))
            if (
                source_path is not None and source_path.is_file()
                and source_path.resolve() == asset_path.resolve()
                and source.get("file_sha256") == asset_sha256
            ):
                return True
    return False


def validate_text_ssot(
    root: Path,
    text_ssot: dict[str, Any],
    exact_mode: str,
    sources: dict[str, dict[str, Any]],
    surface_ids: set[str],
    inventory_region_ids: set[str],
    ocr_region_ids: set[str],
    required_field_ids: set[str],
    observations: dict[str, dict[str, Any]],
    region_authorities: dict[tuple[str, str], dict[str, Any]],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    if text_ssot.get("schema_version") != "packaging-exact-copy-text-ssot.v1":
        errors.append("text_ssot: invalid schema_version")
    if text_ssot.get("freeze_status") != "frozen":
        errors.append("text_ssot: freeze_status must be frozen")
    policy = text_ssot.get("normalization_policy")
    if not isinstance(policy, dict) or policy.get("unicode") != "NFC" or policy.get("autocorrect") != "forbidden":
        errors.append("text_ssot: normalization must use NFC and forbid autocorrect")
    unresolved = text_ssot.get("unresolved_required_field_ids")
    if unresolved != []:
        errors.append("text_ssot: unresolved_required_field_ids must be empty before generation")
    fields = text_ssot.get("fields")
    if not isinstance(fields, list) or (exact_mode == "all_visible_product_native_copy" and not fields):
        errors.append("text_ssot: exact mode requires non-empty fields")
        return {}
    by_id: dict[str, dict[str, Any]] = {}
    for index, field in enumerate(fields):
        label = f"text_ssot.fields[{index}]"
        if not isinstance(field, dict):
            errors.append(f"{label}: must be an object")
            continue
        field_id = field.get("field_id")
        if not isinstance(field_id, str) or not field_id or field_id in by_id:
            errors.append(f"{label}: field_id must be unique and non-empty")
        else:
            by_id[field_id] = field
        if field.get("surface_id") not in surface_ids:
            errors.append(f"{label}: surface_id is not in surface_inventory")
        region_id = field.get("region_id")
        if region_id not in inventory_region_ids or region_id not in ocr_region_ids:
            errors.append(f"{label}: region_id must exist in inventory and region OCR evidence")
        if exact_mode == "all_visible_product_native_copy" and field.get("field_class") != "A_exact":
            errors.append(f"{label}: all visible copy must be A_exact")
        text = field.get("expected_raw_text")
        if not isinstance(text, str):
            errors.append(f"{label}: expected_raw_text must be a string")
        elif field.get("expected_text_sha256") != sha256_text(text):
            errors.append(f"{label}: expected_text_sha256 mismatch")
        match_policy = field.get("ocr_match_policy")
        line_joiner = field.get("line_joiner")
        if match_policy not in {"single_observation_exact", "ordered_line_aggregation_exact"}:
            errors.append(f"{label}: ocr_match_policy is invalid")
        if line_joiner not in {"newline", "space", "none"}:
            errors.append(f"{label}: line_joiner is invalid")
        if match_policy == "single_observation_exact" and line_joiner != "none":
            errors.append(f"{label}: single_observation_exact requires line_joiner=none")
        if field.get("field_status") != "verified":
            errors.append(f"{label}: field_status must be verified")
        authority_sources = field.get("authority_source_ids")
        if (
            not isinstance(authority_sources, list)
            or not authority_sources
            or not set(authority_sources).issubset(sources)
        ):
            errors.append(f"{label}: authority_source_ids must be a non-empty source subset")
            authority_sources = []
        observation_ids = field.get("ocr_observation_ids")
        if not isinstance(observation_ids, list) or not observation_ids:
            errors.append(f"{label}: ocr_observation_ids must be non-empty")
            observation_ids = []
        cited_observations: list[dict[str, Any]] = []
        for observation_id in observation_ids:
            observation = observations.get(observation_id)
            if observation is None:
                errors.append(f"{label}: OCR observation {observation_id!r} does not exist")
                continue
            cited_observations.append(observation)
            if observation.get("source_id") not in authority_sources:
                errors.append(f"{label}: OCR observation source is not an authority source")
            if observation.get("scope") != "region" or observation.get("region_id") != region_id:
                errors.append(f"{label}: OCR observations must bind the same region OCR pass")
            if observation.get("visibility_mode") not in {"direct", "oblique"}:
                errors.append(f"{label}: exact authority requires direct or reviewed oblique OCR")
            disposition = observation.get("disposition")
            if not isinstance(disposition, dict) or disposition.get("status") != "mapped_to_field" or disposition.get("field_id") != field_id:
                errors.append(f"{label}: cited OCR observation must be reviewed and disposed to this exact field")
        if field.get("human_review_status") != "approved":
            errors.append(f"{label}: human_review_status must be approved")
        if field.get("engine_consensus_status") not in {"exact_match", "reviewed_source_override"}:
            errors.append(f"{label}: engine_consensus_status is not approved")
        authority_path = resolve_source_path(root, field.get("authority_asset_path"))
        if authority_path is None or not authority_path.is_file():
            errors.append(f"{label}: deterministic text authority asset is missing")
        elif field.get("authority_asset_sha256") != sha256_file(authority_path):
            errors.append(f"{label}: deterministic text authority asset hash mismatch")
        basis = field.get("verification_basis")
        if basis == "ocr_exact_match":
            if not any(item.get("text") == text for item in cited_observations):
                errors.append(f"{label}: OCR exact-match basis lacks an exact observed string")
            if not authority_asset_has_source_provenance(
                root, field.get("authority_asset_path"), field.get("authority_asset_sha256"),
                authority_sources, region_id, sources, region_authorities, allowed_basis="source_crop",
            ):
                errors.append(f"{label}: OCR exact-match authority asset is not the replayed source-region crop")
        elif basis == "authoritative_source_crop_reviewed":
            if not authority_asset_has_source_provenance(
                root, field.get("authority_asset_path"), field.get("authority_asset_sha256"),
                authority_sources, region_id, sources, region_authorities, allowed_basis="source_crop",
            ):
                errors.append(f"{label}: source-crop authority is not bound to the OCR crop receipt")
        elif basis == "approved_artwork_text_master":
            if not authority_asset_has_source_provenance(
                root, field.get("authority_asset_path"), field.get("authority_asset_sha256"),
                authority_sources, region_id, sources, region_authorities, allowed_basis="artwork_master",
            ):
                errors.append(f"{label}: artwork authority is not an approved source-manifest master")
        else:
            errors.append(f"{label}: verification_basis is invalid")
        if field.get("visibility_mode") == "mirrored_showthrough" and not field.get("showthrough_of_region_id"):
            errors.append(f"{label}: mirrored show-through must bind a direct source region")
    if set(by_id) != required_field_ids:
        errors.append("text_ssot: fields must exactly equal surface_inventory required copy fields")
    return by_id


def validate_codes(
    codes: dict[str, Any],
    root: Path,
    required_code_ids: set[str],
    surface_ids: set[str],
    sources: dict[str, dict[str, Any]],
    code_observations: dict[str, dict[str, Any]],
    region_authorities: dict[tuple[str, str], dict[str, Any]],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    if codes.get("schema_version") != "packaging-code-manifest.v1":
        errors.append("code_manifest: invalid schema_version")
    records = codes.get("codes")
    if not isinstance(records, list):
        errors.append("code_manifest: codes must be an array")
        return {}
    by_id: dict[str, dict[str, Any]] = {}
    for index, code in enumerate(records):
        label = f"code_manifest.codes[{index}]"
        if not isinstance(code, dict):
            errors.append(f"{label}: must be an object")
            continue
        code_id = code.get("code_id")
        if not isinstance(code_id, str) or not code_id or code_id in by_id:
            errors.append(f"{label}: code_id must be unique and non-empty")
            continue
        by_id[code_id] = code
        if code.get("surface_id") not in surface_ids:
            errors.append(f"{label}: surface_id is not in surface_inventory")
        if code.get("required"):
            if code.get("status") != "verified" or code.get("payload_match") is not True:
                errors.append(f"{label}: required code payload must be verified and matched")
            if not code.get("symbology") or code.get("decoded_payload") != code.get("expected_payload"):
                errors.append(f"{label}: required code symbology/payload mismatch")
            authority_sources = code.get("authority_source_ids")
            if not isinstance(authority_sources, list) or not authority_sources or not set(authority_sources).issubset(sources):
                errors.append(f"{label}: authority_source_ids must be a non-empty source subset")
            observation_ids = code.get("ocr_code_observation_ids")
            if not isinstance(observation_ids, list) or not observation_ids:
                errors.append(f"{label}: required code needs decoded source observation IDs")
            else:
                for observation_id in observation_ids:
                    observation = code_observations.get(observation_id)
                    if observation is None:
                        errors.append(f"{label}: code observation {observation_id!r} does not exist")
                    elif observation.get("source_id") not in set(authority_sources or []):
                        errors.append(f"{label}: source code observation is not from an authority source")
                    elif observation.get("payload") != code.get("expected_payload"):
                        errors.append(f"{label}: source code observation payload mismatch")
                    else:
                        disposition = observation.get("disposition")
                        if not isinstance(disposition, dict) or disposition.get("status") != "mapped_to_code" or disposition.get("manifest_code_id") != code_id:
                            errors.append(f"{label}: source code observation must be reciprocally disposed to this code")
            authority_path = resolve_source_path(root, code.get("printed_symbol_asset_path"))
            if authority_path is None or not authority_path.is_file():
                errors.append(f"{label}: deterministic code authority asset is missing")
            elif code.get("printed_symbol_asset_sha256") != sha256_file(authority_path):
                errors.append(f"{label}: deterministic code authority asset hash mismatch")
            elif not authority_asset_has_source_provenance(
                root, code.get("printed_symbol_asset_path"), code.get("printed_symbol_asset_sha256"),
                authority_sources if isinstance(authority_sources, list) else [], code.get("region_id"),
                sources, region_authorities, allowed_basis="either",
            ):
                errors.append(f"{label}: printed code asset lacks source-crop or approved-master provenance")
    if set(by_id) != required_code_ids:
        errors.append("code_manifest: codes must exactly equal surface_inventory required codes")
    if codes.get("required_codes_present") is not bool(required_code_ids):
        errors.append("code_manifest: required_codes_present does not match inventory")
    for observation_id, observation in code_observations.items():
        disposition = observation.get("disposition")
        if isinstance(disposition, dict) and disposition.get("status") == "mapped_to_code":
            manifest_code_id = disposition.get("manifest_code_id")
            record = by_id.get(manifest_code_id) if isinstance(manifest_code_id, str) else None
            if record is None or observation_id not in set(record.get("ocr_code_observation_ids") or []):
                errors.append(f"code_observation {observation_id}: mapped disposition is not reciprocally bound by code_manifest")
    return by_id


def validate_graphics(
    graphics: dict[str, Any],
    root: Path,
    required_graphic_ids: set[str],
    surface_ids: set[str],
    sources: dict[str, dict[str, Any]],
    region_authorities: dict[tuple[str, str], dict[str, Any]],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    if graphics.get("schema_version") != "packaging-logo-graphic-manifest.v1":
        errors.append("logo_graphic_manifest: invalid schema_version")
    records = graphics.get("graphics")
    if not isinstance(records, list):
        errors.append("logo_graphic_manifest: graphics must be an array")
        return {}
    by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(records):
        label = f"logo_graphic_manifest.graphics[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: must be an object")
            continue
        graphic_id = item.get("graphic_id")
        if not isinstance(graphic_id, str) or not graphic_id or graphic_id in by_id:
            errors.append(f"{label}: graphic_id must be unique and non-empty")
            continue
        by_id[graphic_id] = item
        if item.get("surface_id") not in surface_ids:
            errors.append(f"{label}: surface_id is not in surface_inventory")
        if item.get("required"):
            if item.get("status") != "verified":
                errors.append(f"{label}: required graphic must be verified")
            disposition = item.get("disposition")
            if not isinstance(disposition, dict):
                errors.append(f"{label}: required graphic needs a reviewed source disposition")
            else:
                if (
                    disposition.get("status") != "mapped_to_graphic"
                    or disposition.get("manifest_graphic_id") != graphic_id
                ):
                    errors.append(f"{label}: graphic disposition must map to this manifest graphic")
                if (
                    disposition.get("review_status") != "reviewed"
                    or not isinstance(disposition.get("reviewer_id"), str)
                    or not disposition.get("reviewer_id")
                ):
                    errors.append(f"{label}: graphic disposition requires named human review")
                if not isinstance(disposition.get("evidence_note"), str) or not disposition.get("evidence_note"):
                    errors.append(f"{label}: graphic disposition requires evidence_note")
            path = resolve_source_path(root, item.get("asset_path"))
            if path is None or not path.is_file():
                errors.append(f"{label}: graphic asset is missing")
            elif item.get("asset_sha256") != sha256_file(path):
                errors.append(f"{label}: graphic asset hash mismatch")
            else:
                try:
                    verify_image(path)
                except Exception as exc:
                    errors.append(f"{label}: graphic asset is not a decodable image: {exc}")
            authority_sources = item.get("authority_source_ids")
            if not isinstance(authority_sources, list) or not authority_sources or not set(authority_sources).issubset(sources):
                errors.append(f"{label}: authority_source_ids must be a non-empty source subset")
            elif not authority_asset_has_source_provenance(
                root, item.get("asset_path"), item.get("asset_sha256"), authority_sources,
                item.get("region_id"), sources, region_authorities, allowed_basis="either",
            ):
                errors.append(f"{label}: graphic asset lacks source-crop or approved-master provenance")
    if set(by_id) != required_graphic_ids:
        errors.append("logo_graphic_manifest: graphics must exactly equal inventory requirements")
    return by_id


def validate_region_authority_modalities(
    inventory: dict[str, Any],
    region_authorities: dict[tuple[str, str], dict[str, Any]],
    text_fields: dict[str, dict[str, Any]],
    code_records: dict[str, dict[str, Any]],
    graphic_records: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    """Bind each replayed crop to its physical layer and declared evidence modality."""
    region_surface: dict[str, tuple[str, set[str]]] = {}
    surfaces = inventory.get("surfaces") if isinstance(inventory, dict) else None
    if not isinstance(surfaces, list):
        return
    for surface_index, surface in enumerate(surfaces):
        if not isinstance(surface, dict):
            continue
        surface_id = surface.get("surface_id")
        physical_layers = {
            item for item in (surface.get("physical_layer_ids") or [])
            if isinstance(item, str) and item
        }
        for region_id in surface.get("region_ids") or []:
            if not isinstance(region_id, str) or not region_id:
                continue
            if region_id in region_surface:
                errors.append(
                    f"surface_inventory: region_id {region_id} is assigned to multiple physical surfaces"
                )
            elif isinstance(surface_id, str):
                region_surface[region_id] = (surface_id, physical_layers)

    authorities_by_region: dict[str, list[dict[str, Any]]] = {}
    for authority in region_authorities.values():
        region_id = authority.get("region_id")
        if isinstance(region_id, str):
            authorities_by_region.setdefault(region_id, []).append(authority)
    missing = set(region_surface) - set(authorities_by_region)
    extra = set(authorities_by_region) - set(region_surface)
    if missing or extra:
        errors.append(
            "region authority coverage must exactly match surface_inventory region_ids; "
            f"missing={sorted(missing)}, extra={sorted(extra)}"
        )

    modalities_by_region: dict[str, set[str]] = {}
    for modality, records in (
        ("text", text_fields), ("code", code_records), ("graphic", graphic_records),
    ):
        for record in records.values():
            region_id = record.get("region_id")
            if isinstance(region_id, str) and region_id:
                modalities_by_region.setdefault(region_id, set()).add(modality)

    expected_for_purpose = {
        "text": {"text"},
        "code": {"code"},
        "graphic": {"graphic"},
    }
    for region_id, authorities in authorities_by_region.items():
        inventory_binding = region_surface.get(region_id)
        if inventory_binding is None:
            continue
        expected_surface, physical_layers = inventory_binding
        purposes = {item.get("region_purpose") for item in authorities}
        authority_surface_layers = {
            (item.get("surface_id"), item.get("physical_layer_id")) for item in authorities
        }
        if len(purposes) != 1 or not purposes.issubset(REGION_PURPOSES):
            errors.append(f"region {region_id}: source authorities disagree on region_purpose")
            continue
        purpose = next(iter(purposes))
        for surface_id, physical_layer_id in authority_surface_layers:
            if surface_id != expected_surface:
                errors.append(f"region {region_id}: surface_id is not the owning inventory surface")
            if physical_layer_id not in physical_layers:
                errors.append(f"region {region_id}: physical_layer_id is not owned by its surface")
        if len(authority_surface_layers) != 1:
            errors.append(f"region {region_id}: source authorities disagree on surface/layer binding")
        actual_modalities = modalities_by_region.get(region_id, set())
        if purpose == "mixed":
            if len(actual_modalities) < 2:
                errors.append(
                    f"region {region_id}: mixed purpose requires at least two of text/code/graphic manifests"
                )
        elif actual_modalities != expected_for_purpose.get(str(purpose), set()):
            errors.append(
                f"region {region_id}: region_purpose={purpose} differs from bound manifest modalities "
                f"{sorted(actual_modalities)}"
            )

        if purpose in {"code", "mixed"} and "code" in actual_modalities:
            for code in code_records.values():
                if code.get("region_id") != region_id:
                    continue
                if (
                    code.get("status") != "verified"
                    or code.get("payload_match") is not True
                    or not code.get("ocr_code_observation_ids")
                ):
                    errors.append(
                        f"region {region_id}: code purpose requires verified decode evidence and reviewed disposition"
                    )
        if purpose in {"graphic", "mixed"} and "graphic" in actual_modalities:
            for graphic in graphic_records.values():
                if graphic.get("region_id") != region_id:
                    continue
                disposition = graphic.get("disposition")
                if (
                    not isinstance(disposition, dict)
                    or disposition.get("status") != "mapped_to_graphic"
                    or disposition.get("manifest_graphic_id") != graphic.get("graphic_id")
                    or disposition.get("review_status") != "reviewed"
                    or not isinstance(disposition.get("reviewer_id"), str)
                    or not disposition.get("reviewer_id")
                ):
                    errors.append(
                        f"region {region_id}: graphic purpose requires reviewed graphic disposition and named reviewer"
                    )


def validate_texture_atlas(
    atlas: dict[str, Any], root: Path, required_surface_ids: set[str], errors: list[str]
) -> None:
    if atlas.get("schema_version") != "packaging-surface-texture-atlas.v1" or atlas.get("freeze_status") != "frozen":
        errors.append("surface_texture_atlas: invalid schema/freeze status")
    textures = atlas.get("textures")
    if not isinstance(textures, list) or not textures:
        errors.append("surface_texture_atlas: textures must be non-empty")
        return
    by_surface: dict[str, dict[str, Any]] = {}
    for index, texture in enumerate(textures):
        label = f"surface_texture_atlas.textures[{index}]"
        if not isinstance(texture, dict) or not isinstance(texture.get("surface_id"), str):
            errors.append(f"{label}: invalid texture record")
            continue
        surface_id = texture["surface_id"]
        if surface_id in by_surface:
            errors.append(f"{label}: duplicate surface_id")
        by_surface[surface_id] = texture
        path = resolve_source_path(root, texture.get("asset_path"))
        if path is None or not path.is_file() or texture.get("asset_sha256") != sha256_file(path):
            errors.append(f"{label}: texture asset/hash invalid")
        else:
            try:
                verify_image(path)
            except Exception as exc:
                errors.append(f"{label}: texture image invalid: {exc}")
    if not required_surface_ids.issubset(by_surface):
        errors.append("surface_texture_atlas: missing a required exact-copy surface texture")


def validate_protected_masks(
    masks_manifest: dict[str, Any], root: Path, required_region_ids: set[str], errors: list[str]
) -> None:
    if masks_manifest.get("schema_version") != "packaging-protected-region-masks.v1" or masks_manifest.get("freeze_status") != "frozen":
        errors.append("protected_region_masks: invalid schema/freeze status")
    masks = masks_manifest.get("masks")
    if not isinstance(masks, list):
        errors.append("protected_region_masks: masks must be an array")
        return
    by_region: dict[str, dict[str, Any]] = {}
    for index, mask in enumerate(masks):
        label = f"protected_region_masks.masks[{index}]"
        if not isinstance(mask, dict) or not isinstance(mask.get("region_id"), str):
            errors.append(f"{label}: invalid mask record")
            continue
        region_id = mask["region_id"]
        if region_id in by_region:
            errors.append(f"{label}: duplicate region_id")
        by_region[region_id] = mask
        path = resolve_source_path(root, mask.get("asset_path"))
        if path is None or not path.is_file() or mask.get("asset_sha256") != sha256_file(path):
            errors.append(f"{label}: mask asset/hash invalid")
        else:
            try:
                verify_image(path)
            except Exception as exc:
                errors.append(f"{label}: mask image invalid: {exc}")
    if set(by_region) != required_region_ids:
        errors.append("protected_region_masks: masks must exactly cover exact-copy regions")


def expected_view_ids(
    profile_name: str,
    features: list[str],
    motion_envelope: dict[str, Any] | None,
    text_fields: dict[str, dict[str, Any]],
    code_records: dict[str, dict[str, Any]],
    graphic_records: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[list[str], dict[str, dict[str, Any]], list[list[str]]]:
    profiles = read_json(PROFILES_PATH)
    profile = profiles.get("rotation_profiles", {}).get(profile_name)
    if not isinstance(profile, dict):
        errors.append("coverage_matrix: unknown rotation profile")
        return [], {}, []
    view_ids = list(profile["view_ids"])
    motion_type = (motion_envelope or {}).get("motion_type")
    if motion_type == "macro_rotation" and profile_name != "R24":
        errors.append("motion_envelope: macro_rotation requires R24")
    expected_pitched_prefixes = required_pitched_prefixes(motion_envelope, errors)
    ring_sequences: list[list[str]] = [list(profile["view_ids"])]
    elevation_map = {item["view_id"]: item for item in profiles["base_elevation_views"]}
    view_ids.extend(elevation_map)
    close_map = {
        item["view_id"]: item for item in profiles.get("base_close_views", [])
        if isinstance(item, dict) and isinstance(item.get("view_id"), str)
    }
    view_ids.extend(close_map)
    view_ids.extend(profiles["base_detail_views"])
    for feature in features:
        view_ids.extend(profiles["feature_detail_requirements"].get(feature, []))
    dynamic_region_specs = derive_dynamic_region_detail_specs(
        text_fields, code_records, graphic_records, errors,
    )
    view_ids.extend(dynamic_region_specs)
    elevation_rings = (motion_envelope or {}).get("elevation_rings", [])
    if not isinstance(elevation_rings, list):
        errors.append("motion_envelope: elevation_rings must be an array")
        elevation_rings = []
    neutral_tokens = [view_id.removeprefix("ROT_") for view_id in profile["view_ids"]]
    seen_ring_ids: set[str] = set()
    seen_prefixes: set[str] = set()
    for index, ring in enumerate(elevation_rings):
        label = f"motion_envelope.elevation_rings[{index}]"
        if not isinstance(ring, dict):
            errors.append(f"{label}: must be an object")
            continue
        ring_id = ring.get("ring_id")
        prefix = ring.get("view_prefix")
        elevation = ring.get("elevation_deg")
        declared = ring.get("view_ids")
        if not isinstance(ring_id, str) or not ring_id or ring_id in seen_ring_ids:
            errors.append(f"{label}: ring_id must be unique and non-empty")
        else:
            seen_ring_ids.add(ring_id)
        if prefix not in {"HIGH", "LOW"}:
            errors.append(f"{label}: view_prefix must be HIGH or LOW")
            continue
        if prefix in seen_prefixes:
            errors.append(f"{label}: only one dynamic {prefix} ring is allowed by v3 view IDs")
            continue
        seen_prefixes.add(prefix)
        if not isinstance(elevation, (int, float)) or (prefix == "HIGH" and elevation <= 0) or (prefix == "LOW" and elevation >= 0):
            errors.append(f"{label}: elevation sign does not match ring prefix")
        expected = [f"{prefix}_{token}" for token in neutral_tokens]
        if declared != expected:
            errors.append(f"{label}: full elevation ring must exactly follow selected rotation profile")
            continue
        if ring.get("loop_closure_required") is not True:
            errors.append(f"{label}: loop_closure_required must be true")
        ring_sequences.append(expected)
        view_ids.extend(expected)
        for view_id, token in zip(expected, neutral_tokens):
            elevation_map[view_id] = {
                "view_id": view_id,
                "azimuth_deg": int(token) / 10.0,
                "elevation_deg": float(elevation),
                "shot_scale": "full_product",
            }
    if seen_prefixes != expected_pitched_prefixes:
        missing = sorted(expected_pitched_prefixes - seen_prefixes)
        extra = sorted(seen_prefixes - expected_pitched_prefixes)
        errors.append(
            "motion_envelope: elevation_rings must exactly match the motion scope; "
            f"missing={missing}, extra={extra}"
        )
    return list(dict.fromkeys(view_ids)), elevation_map, ring_sequences


def horizontal_surface_roles(azimuth_deg: float) -> set[str]:
    angle = azimuth_deg % 360.0
    cardinals = [(0.0, "front"), (90.0, "right"), (180.0, "back"), (270.0, "left"), (360.0, "front")]
    for degree, role in cardinals[:-1]:
        if math.isclose(angle, degree, abs_tol=0.01):
            return {role}
    for index in range(len(cardinals) - 1):
        start_degree, start_role = cardinals[index]
        end_degree, end_role = cardinals[index + 1]
        if start_degree < angle < end_degree:
            return {start_role, end_role}
    return {"front"}


def expected_surface_roles_for_view(view_id: str, view: dict[str, Any]) -> set[str]:
    try:
        azimuth = float(view.get("azimuth_deg", 0.0))
    except (TypeError, ValueError):
        azimuth = 0.0
    if view_id == "TOP_0000":
        return {"top"}
    if view_id == "BOTTOM_0000":
        return {"bottom"}
    if view_id.startswith("ROT_"):
        return horizontal_surface_roles(azimuth)
    if view_id.startswith("UPPER_") or view_id.startswith("LOWER_"):
        return horizontal_surface_roles(azimuth)
    if view_id.startswith("HIGH_"):
        return horizontal_surface_roles(azimuth) | {"top"}
    if view_id.startswith("LOW_"):
        return horizontal_surface_roles(azimuth) | {"bottom"}
    detail_role_tokens = [
        (("TRUE_BOTTOM", "BASE_EDGE", "BOTTOM_FLAP", "BOTTOM_GUSSET", "TAIL_CRIMP"), {"bottom"}),
        (("CLOSURE_FRONT", "CLOSURE_TOP", "NOZZLE_APERTURE", "ACTUATOR_STEM", "NECK_COLLAR", "TOP_FLAP", "CAP_AND_NOZZLE"), {"top"}),
        (("BACK", "GLUE_SEAM", "REAR_SHOWTHROUGH"), {"back"}),
        (("LEFT", "LEFT_GUSSET"), {"left"}),
        (("RIGHT", "SIDE", "RIGHT_GUSSET", "WRAP_CONTINUITY"), {"right"}),
    ]
    for tokens, roles in detail_role_tokens:
        if any(token in view_id for token in tokens):
            return roles
    return {"front"}


def validate_coverage(
    coverage: dict[str, Any],
    profile_name: str,
    features: list[str],
    product_state_id: str,
    motion_envelope: dict[str, Any] | None,
    sources: dict[str, dict[str, Any]],
    surface_ids: set[str],
    surface_by_role: dict[str, str],
    text_fields: dict[str, dict[str, Any]],
    code_records: dict[str, dict[str, Any]],
    graphic_records: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[set[str], list[list[str]], dict[str, dict[str, Any]]]:
    if coverage.get("schema_version") != "packaging-view-coverage.v1":
        errors.append("coverage_matrix: invalid schema_version")
    if coverage.get("rotation_profile") != profile_name:
        errors.append("coverage_matrix: rotation_profile mismatch")
    if coverage.get("product_state_id") != product_state_id:
        errors.append("coverage_matrix: product_state_id mismatch")
    if coverage.get("freeze_status") != "frozen":
        errors.append("coverage_matrix: freeze_status must be frozen")
    for source_id, source in sources.items():
        if source.get("source_kind") not in {"direct_product_photograph", "turntable_frame", "cad_render"}:
            continue
        source_view_id = source.get("view_id")
        if not isinstance(source_view_id, str):
            continue
        source_roles = expected_surface_roles_for_view(source_view_id, source)
        expected_source_surfaces = {
            surface_by_role[role] for role in source_roles if role in surface_by_role
        }
        actual_source_surfaces = set(source.get("visible_surfaces") or [])
        if actual_source_surfaces != expected_source_surfaces:
            errors.append(
                f"source_manifest {source_id}: visible surfaces contradict its bound camera pose; "
                f"requires exactly roles {sorted(source_roles)}"
            )
        try:
            source_azimuth = float(source.get("azimuth_deg"))
            source_elevation = float(source.get("elevation_deg"))
            if source_view_id.startswith("ROT_"):
                expected_azimuth = int(source_view_id.split("_")[1]) / 10.0
                if not math.isclose(source_azimuth, expected_azimuth, abs_tol=0.01) or not math.isclose(source_elevation, 0.0, abs_tol=0.01):
                    errors.append(f"source_manifest {source_id}: ROT view_id and numeric camera pose disagree")
            elif source_view_id == "TOP_0000" and (
                not math.isclose(source_azimuth, 0.0, abs_tol=0.01)
                or not math.isclose(source_elevation, 90.0, abs_tol=0.01)
            ):
                errors.append(f"source_manifest {source_id}: TOP_0000 must bind azimuth 0/elevation +90")
            elif source_view_id == "BOTTOM_0000" and (
                not math.isclose(source_azimuth, 0.0, abs_tol=0.01)
                or not math.isclose(source_elevation, -90.0, abs_tol=0.01)
            ):
                errors.append(f"source_manifest {source_id}: BOTTOM_0000 must bind azimuth 0/elevation -90")
            elif source_view_id.startswith("HIGH_") and source_elevation <= 0:
                errors.append(f"source_manifest {source_id}: HIGH source elevation must be positive")
            elif source_view_id.startswith("LOW_") and source_elevation >= 0:
                errors.append(f"source_manifest {source_id}: LOW source elevation must be negative")
        except (TypeError, ValueError):
            pass
    coordinate_frame = coverage.get("product_coordinate_frame")
    if not isinstance(coordinate_frame, dict) or coordinate_frame.get("azimuth_0") != "front" or coordinate_frame.get("azimuth_90") != "right" or coordinate_frame.get("azimuth_180") != "back" or coordinate_frame.get("azimuth_270") != "left" or coordinate_frame.get("elevation_positive") != "camera_above_product":
        errors.append("coverage_matrix: product_coordinate_frame must freeze front/right/back/left and elevation sign")
    identity_lock = coverage.get("identity_lock")
    landmark_inventory: set[str] = set()
    component_inventory: set[str] = set()
    material_inventory: set[str] = set()
    if not isinstance(identity_lock, dict):
        errors.append("coverage_matrix: identity_lock is required")
    else:
        for key in ("occupancy_lock", "geometry_landmark_contract", "material_contract", "forbidden_inventions"):
            value = identity_lock.get(key)
            if value in (None, "", [], {}):
                errors.append(f"coverage_matrix.identity_lock: {key} must be non-empty")
        geometry_contract = identity_lock.get("geometry_landmark_contract")
        material_contract = identity_lock.get("material_contract")
        if not isinstance(geometry_contract, dict):
            errors.append("coverage_matrix.identity_lock: geometry_landmark_contract must be an object inventory")
        else:
            for key, target in (("required_landmark_ids", landmark_inventory), ("component_ids", component_inventory)):
                values = geometry_contract.get(key)
                if not isinstance(values, list) or not values or len(values) != len(set(values)) or any(not isinstance(item, str) or not item for item in values):
                    errors.append(f"coverage_matrix.identity_lock.geometry_landmark_contract: {key} must be a non-empty unique ID array")
                else:
                    target.update(values)
        if not isinstance(material_contract, dict):
            errors.append("coverage_matrix.identity_lock: material_contract must be an object inventory")
        else:
            values = material_contract.get("material_feature_ids")
            if not isinstance(values, list) or not values or len(values) != len(set(values)) or any(not isinstance(item, str) or not item for item in values):
                errors.append("coverage_matrix.identity_lock.material_contract: material_feature_ids must be a non-empty unique ID array")
            else:
                material_inventory.update(values)
    for source_id, source in sources.items():
        if source.get("source_kind") not in {"direct_product_photograph", "turntable_frame", "cad_render"}:
            continue
        source_components = source.get("visible_component_ids")
        if isinstance(source_components, list) and not set(source_components).issubset(component_inventory):
            errors.append(f"source_manifest {source_id}: visible_component_ids contain IDs absent from the frozen component inventory")
    dynamic_detail_specs = derive_dynamic_region_detail_specs(
        text_fields, code_records, graphic_records, errors,
    )
    detail_ids = set(FIXED_DETAIL_SPECS) | set(dynamic_detail_specs)
    close_ids = set(BASE_CLOSE_SPECS)
    role_by_surface = {surface_id: role for role, surface_id in surface_by_role.items()}
    views = coverage.get("views")
    if not isinstance(views, list):
        errors.append("coverage_matrix: views must be an array")
        return set(), [], {}
    by_id: dict[str, dict[str, Any]] = {}
    for index, view in enumerate(views):
        if not isinstance(view, dict) or not isinstance(view.get("view_id"), str):
            errors.append(f"coverage_matrix.views[{index}]: invalid view record")
            continue
        view_id = view["view_id"]
        if view_id in by_id:
            errors.append(f"coverage_matrix: duplicate view_id {view_id}")
        by_id[view_id] = view
        if view.get("product_state_id") != product_state_id:
            errors.append(f"coverage_matrix {view_id}: product_state_id drift")
        if view.get("shot_scale") not in {"full_product", "upper_half_close", "lower_half_close", "macro_component", "rectified_surface_evidence"}:
            errors.append(f"coverage_matrix {view_id}: invalid shot_scale")
        expected_semantic_role = board_semantic_role_for_view(view_id, view)
        if expected_semantic_role not in REVIEW_BOARD_ROLES or view.get("review_board_role") != expected_semantic_role:
            errors.append(f"coverage_matrix {view_id}: review_board_role/family semantic mismatch")
        if view_id.startswith("ROT_") and view.get("family") != "neutral_ring":
            errors.append(f"coverage_matrix {view_id}: neutral ring family mismatch")
        elif view_id.startswith("HIGH_") and view.get("family") != "high_angle":
            errors.append(f"coverage_matrix {view_id}: high-angle family mismatch")
        elif view_id.startswith("LOW_") and view.get("family") != "low_angle":
            errors.append(f"coverage_matrix {view_id}: low-angle family mismatch")
        elif view_id in {"TOP_0000", "BOTTOM_0000"} and view.get("family") != "top_bottom":
            errors.append(f"coverage_matrix {view_id}: top/bottom family mismatch")
        semantic_spec = BASE_CLOSE_SPECS.get(view_id) or FIXED_DETAIL_SPECS.get(view_id)
        if semantic_spec is not None:
            for key in ("family", "shot_scale", "framing_contract"):
                if view.get(key) != semantic_spec.get(key):
                    errors.append(f"coverage_matrix {view_id}: {key} differs from frozen view semantics")
            for key in ("azimuth_deg", "elevation_deg"):
                try:
                    if not math.isclose(float(view.get(key)), float(semantic_spec.get(key)), abs_tol=0.01):
                        errors.append(f"coverage_matrix {view_id}: {key} differs from frozen view semantics")
                except (TypeError, ValueError):
                    errors.append(f"coverage_matrix {view_id}: {key} must be numeric")
            target_role = semantic_spec.get("target_surface_role")
            target_surface_id = surface_by_role.get(str(target_role))
            if target_surface_id is None or set(view.get("visible_surface_ids") or []) != {target_surface_id}:
                errors.append(f"coverage_matrix {view_id}: visible surface differs from frozen target surface")
        dynamic_spec = dynamic_detail_specs.get(view_id)
        if dynamic_spec is not None:
            dynamic_contract = view.get("dynamic_region_contract")
            expected_dynamic_contract = {
                key: dynamic_spec[key] for key in (
                    "region_id", "surface_id", "field_ids", "code_ids", "graphic_ids",
                    "native_region_pixel_contract",
                )
            }
            if dynamic_contract != expected_dynamic_contract:
                errors.append(f"coverage_matrix {view_id}: dynamic region contract differs from exact-copy evidence")
            for key in ("family", "shot_scale", "framing_contract"):
                if view.get(key) != dynamic_spec.get(key):
                    errors.append(f"coverage_matrix {view_id}: {key} differs from dynamic region semantics")
            surface_role = role_by_surface.get(dynamic_spec["surface_id"])
            expected_pose_by_role = {
                "front": (0.0, 0.0), "right": (90.0, 0.0),
                "back": (180.0, 0.0), "left": (270.0, 0.0),
                "top": (0.0, 90.0), "bottom": (0.0, -90.0),
            }
            expected_pose = expected_pose_by_role.get(str(surface_role))
            if expected_pose is None:
                errors.append(f"coverage_matrix {view_id}: dynamic region surface is not canonical")
            else:
                try:
                    if not math.isclose(float(view.get("azimuth_deg")), expected_pose[0], abs_tol=0.01) or not math.isclose(float(view.get("elevation_deg")), expected_pose[1], abs_tol=0.01):
                        errors.append(f"coverage_matrix {view_id}: dynamic region camera pose differs from its physical surface")
                except (TypeError, ValueError):
                    errors.append(f"coverage_matrix {view_id}: dynamic region camera pose must be numeric")
            if set(view.get("visible_surface_ids") or []) != {dynamic_spec["surface_id"]}:
                errors.append(f"coverage_matrix {view_id}: dynamic region master must expose exactly its bound surface")
            for key, view_key in (
                ("field_ids", "ocr_field_ids_visible"),
                ("code_ids", "code_ids_visible"),
                ("graphic_ids", "graphic_ids_visible"),
            ):
                if view.get(view_key) != dynamic_spec[key]:
                    errors.append(f"coverage_matrix {view_id}: {view_key} must exactly match its region-owned evidence")
            if view.get("label_region_ids") != [dynamic_spec["region_id"]]:
                errors.append(f"coverage_matrix {view_id}: dynamic region master must bind exactly one region")
        for key in ("geometry_landmark_ids", "material_feature_ids", "visible_component_ids", "occluded_surface_ids"):
            if not isinstance(view.get(key), list):
                errors.append(f"coverage_matrix {view_id}: {key} must be an array")
        if not set(view.get("geometry_landmark_ids") or []).issubset(landmark_inventory):
            errors.append(f"coverage_matrix {view_id}: geometry_landmark_ids contain IDs absent from the frozen landmark inventory")
        if not set(view.get("material_feature_ids") or []).issubset(material_inventory):
            errors.append(f"coverage_matrix {view_id}: material_feature_ids contain IDs absent from the frozen material inventory")
        if not isinstance(view.get("visible_component_ids"), list) or not view.get("visible_component_ids") or not set(view.get("visible_component_ids") or []).issubset(component_inventory):
            errors.append(f"coverage_matrix {view_id}: visible_component_ids must be a non-empty frozen component subset")
        if view_id in detail_ids:
            detail_job = view.get("detail_job")
            if not isinstance(detail_job, dict):
                errors.append(f"coverage_matrix {view_id}: detail views require a machine-readable detail_job")
            else:
                if detail_job.get("detail_id") != view_id:
                    errors.append(f"coverage_matrix {view_id}: detail_job.detail_id must equal view_id")
                target_surfaces = detail_job.get("target_surface_ids")
                if not isinstance(target_surfaces, list) or not target_surfaces or not set(target_surfaces).issubset(set(view.get("visible_surface_ids") or [])):
                    errors.append(f"coverage_matrix {view_id}: detail_job target surfaces must be a visible non-empty subset")
                components = detail_job.get("target_component_ids")
                if view_id in FIXED_DETAIL_SPECS:
                    expected_component = view_id.removeprefix("DETAIL_")
                    if (
                        not isinstance(components, list) or expected_component not in components
                        or not set(components).issubset(set(view.get("visible_component_ids") or []))
                        or not set(components).issubset(component_inventory)
                        or any(not isinstance(item, str) or not item for item in components)
                    ):
                        errors.append(f"coverage_matrix {view_id}: detail_job must bind its canonical target component")
                elif (
                    not isinstance(components, list) or not components
                    or not set(components).issubset(set(view.get("visible_component_ids") or []))
                    or not set(components).issubset(component_inventory)
                ):
                    errors.append(f"coverage_matrix {view_id}: dynamic detail_job must bind source-visible frozen components")
                evidence_ids = detail_job.get("required_evidence_ids")
                expected_evidence = set(view.get("ocr_field_ids_visible") or []) | set(view.get("code_ids_visible") or []) | set(view.get("graphic_ids_visible") or [])
                allowed_evidence = set(text_fields) | set(code_records) | set(graphic_records) | component_inventory | landmark_inventory | material_inventory
                if (
                    not isinstance(evidence_ids, list) or not evidence_ids
                    or not expected_evidence.issubset(set(evidence_ids))
                    or not set(evidence_ids).issubset(allowed_evidence)
                ):
                    errors.append(f"coverage_matrix {view_id}: detail_job required evidence is incomplete")
                for key in ("framing_contract", "focus_contract"):
                    if not isinstance(detail_job.get(key), str) or not detail_job.get(key):
                        errors.append(f"coverage_matrix {view_id}: detail_job {key} must be non-empty")
                expected_detail_spec = FIXED_DETAIL_SPECS.get(view_id) or dynamic_detail_specs.get(view_id)
                if expected_detail_spec and (
                    detail_job.get("framing_contract") != expected_detail_spec.get("framing_contract")
                    or detail_job.get("focus_contract") != expected_detail_spec.get("focus_contract")
                ):
                    errors.append(f"coverage_matrix {view_id}: detail_job framing/focus differs from frozen semantics")
        elif view.get("detail_job") not in (None, {}):
            errors.append(f"coverage_matrix {view_id}: non-detail view cannot carry a detail_job")
        if view.get("derivation_status") == "generated" and view.get("pose_source_status") == "source_verified":
            errors.append(f"coverage_matrix {view_id}: generated view cannot self-upgrade to source_verified")
        refs = view.get("source_refs")
        if not isinstance(refs, list) or not refs or not set(refs).issubset(sources):
            errors.append(f"coverage_matrix {view_id}: source_refs must be a non-empty source subset")
            refs = []
        elif any(sources[ref].get("source_kind") not in {"direct_product_photograph", "turntable_frame", "cad_render"} for ref in refs):
            errors.append(f"coverage_matrix {view_id}: camera/surface anchors must be spatial sources, never artwork/text/dieline")
        visible_surfaces = view.get("visible_surface_ids")
        if not isinstance(visible_surfaces, list) or not visible_surfaces or not set(visible_surfaces).issubset(surface_ids):
            errors.append(f"coverage_matrix {view_id}: visible_surface_ids must be a non-empty inventory subset")
            visible_surfaces = []
        for key, known in (
            ("ocr_field_ids_visible", set(text_fields)),
            ("code_ids_visible", set(code_records)),
            ("graphic_ids_visible", set(graphic_records)),
        ):
            values = view.get(key)
            if not isinstance(values, list) or not set(values).issubset(known):
                errors.append(f"coverage_matrix {view_id}: {key} must be an array subset of locked evidence")
        allowed_statuses = {"source_verified", "inferred_from_sources", "not_applicable_no_visible_content", "needs_source"}
        for key in SOURCE_STATUS_KEYS:
            if view.get(key) not in allowed_statuses:
                errors.append(f"coverage_matrix {view_id}: invalid {key}")
        if view.get("pose_source_status") == "not_applicable_no_visible_content" or view.get("surface_source_status") == "not_applicable_no_visible_content" or view.get("material_source_status") == "not_applicable_no_visible_content":
            errors.append(f"coverage_matrix {view_id}: pose/surface/material evidence is always applicable")
        if any(view.get(key) == "needs_source" for key in SOURCE_STATUS_KEYS):
            errors.append(f"coverage_matrix {view_id}: required production view cannot pass with needs_source")
        has_visible_copy = bool(
            view.get("ocr_field_ids_visible") or view.get("code_ids_visible") or view.get("graphic_ids_visible")
        )
        if has_visible_copy and view.get("copy_source_status") == "not_applicable_no_visible_content":
            errors.append(f"coverage_matrix {view_id}: visible copy/graphic/code cannot be not_applicable")
        if not has_visible_copy and view.get("copy_source_status") not in {
            "not_applicable_no_visible_content", "source_verified", "inferred_from_sources"
        }:
            errors.append(f"coverage_matrix {view_id}: invalid no-copy authority status")
        if view.get("surface_source_status") == "source_verified" and refs:
            supported_surfaces = {
                item for ref in refs for item in sources[ref].get("visible_surfaces", [])
                if isinstance(item, str)
            }
            if not set(visible_surfaces).issubset(supported_surfaces):
                errors.append(f"coverage_matrix {view_id}: source refs do not verify every visible surface")
            supported_components = {
                item for ref in refs for item in sources[ref].get("visible_component_ids", [])
                if isinstance(item, str)
            }
            if not set(view.get("visible_component_ids") or []).issubset(supported_components):
                errors.append(f"coverage_matrix {view_id}: source refs do not verify every visible component")
        visible_field_ids = set(view.get("ocr_field_ids_visible") or [])
        if view.get("copy_source_status") == "source_verified":
            for field_id in visible_field_ids:
                field = text_fields.get(field_id)
                if field is not None and not set(field.get("authority_source_ids") or []).intersection(refs):
                    errors.append(f"coverage_matrix {view_id}: copy source refs do not authorize {field_id}")
        if view.get("production_authority") != "validator_derived":
            errors.append(f"coverage_matrix {view_id}: production authority must be validator-derived, never self-authorized")
    required_ids, elevation_map, ring_sequences = expected_view_ids(
        profile_name, features, motion_envelope,
        text_fields, code_records, graphic_records, errors,
    )
    missing = [view_id for view_id in required_ids if view_id not in by_id]
    if missing:
        errors.append("coverage_matrix: missing required views: " + ", ".join(missing))
    extra = sorted(set(by_id) - set(required_ids))
    if extra:
        errors.append("coverage_matrix: unbound extra views are forbidden: " + ", ".join(extra))
    for view_id in required_ids:
        view = by_id.get(view_id)
        if not view:
            continue
        if view.get("required") is not True:
            errors.append(f"coverage_matrix {view_id}: required flag must be true")
        if any(view.get(key) == "needs_source" for key in SOURCE_STATUS_KEYS) and coverage.get("production_coverage_status") == "passed":
            errors.append(f"coverage_matrix {view_id}: production coverage cannot pass with needs_source")
        expected_roles = expected_surface_roles_for_view(view_id, view)
        expected_surfaces = {surface_by_role[role] for role in expected_roles if role in surface_by_role}
        actual_surfaces = set(view.get("visible_surface_ids") or [])
        if (
            view.get("shot_scale") == "full_product"
            or view_id.startswith("UPPER_")
            or view_id.startswith("LOWER_")
        ) and actual_surfaces != expected_surfaces:
            errors.append(
                f"coverage_matrix {view_id}: visible surfaces violate canonical camera/surface topology; "
                f"requires exactly roles {sorted(expected_roles)}"
            )
        try:
            if view_id.startswith("ROT_"):
                expected_azimuth = int(view_id.split("_")[1]) / 10.0
                if not math.isclose(float(view.get("azimuth_deg", -999)), expected_azimuth, abs_tol=0.01):
                    errors.append(f"coverage_matrix {view_id}: azimuth mismatch")
                if not math.isclose(float(view.get("elevation_deg", -999)), 0.0, abs_tol=0.01):
                    errors.append(f"coverage_matrix {view_id}: neutral ring elevation must be 0")
            elif view_id in elevation_map:
                spec = elevation_map[view_id]
                if not math.isclose(float(view.get("azimuth_deg", -999)), float(spec["azimuth_deg"]), abs_tol=0.01):
                    errors.append(f"coverage_matrix {view_id}: azimuth mismatch")
                if not math.isclose(float(view.get("elevation_deg", -999)), float(spec["elevation_deg"]), abs_tol=0.01):
                    errors.append(f"coverage_matrix {view_id}: elevation mismatch")
        except (TypeError, ValueError):
            errors.append(f"coverage_matrix {view_id}: camera pose values must be numeric")
    full_product_poses: dict[tuple[float, float, float], str] = {}
    for view_id in required_ids:
        view = by_id.get(view_id)
        if not view or view.get("shot_scale") != "full_product":
            continue
        try:
            pose = (float(view.get("azimuth_deg", 0)), float(view.get("elevation_deg", 0)), float(view.get("roll_deg", 0)))
        except (TypeError, ValueError):
            continue
        if pose in full_product_poses and full_product_poses[pose] != view_id:
            errors.append(f"coverage_matrix: duplicate full-product numeric pose {view_id}/{full_product_poses[pose]}")
        full_product_poses[pose] = view_id
    for ring_ids in ring_sequences:
        for index, view_id in enumerate(ring_ids):
            view = by_id.get(view_id)
            if not view:
                continue
            previous_id = ring_ids[index - 1]
            next_id = ring_ids[(index + 1) % len(ring_ids)]
            if view.get("previous_view_id") != previous_id or view.get("next_view_id") != next_id:
                errors.append(f"coverage_matrix {view_id}: ring adjacency/loop closure mismatch")
    known_ids = set(by_id)
    for view_id, view in by_id.items():
        parents = view.get("parent_anchor_view_ids")
        if not isinstance(parents, list) or not set(parents).issubset(known_ids - {view_id}):
            errors.append(f"coverage_matrix {view_id}: parent_anchor_view_ids are invalid")
            parents = []
        derivation = view.get("derivation_status")
        if derivation not in {"source", "generated"}:
            errors.append(f"coverage_matrix {view_id}: derivation_status must be source or generated")
        if derivation == "source":
            if parents:
                errors.append(f"coverage_matrix {view_id}: source-derived view cannot cite generated parents")
            if any(view.get(key) != "source_verified" for key in ("pose_source_status", "surface_source_status", "material_source_status")):
                errors.append(f"coverage_matrix {view_id}: source-derived view requires direct pose/surface/material evidence")
            if view.get("copy_source_status") not in {"source_verified", "not_applicable_no_visible_content"}:
                errors.append(f"coverage_matrix {view_id}: source-derived view has invalid copy evidence")
            if view.get("shot_scale") != "full_product":
                errors.append(
                    f"coverage_matrix {view_id}: V3 detail masters must be generated/inferred from direct full-product anchors; a source claim requires a future replayable detail-crop contract"
                )
            if view.get("shot_scale") == "full_product":
                direct_pose_sources = []
                for source_id in view.get("source_refs") or []:
                    source = sources.get(source_id)
                    if (
                        not isinstance(source, dict)
                        or source.get("source_kind") not in {"direct_product_photograph", "turntable_frame", "cad_render"}
                        or source.get("view_id") != view_id
                    ):
                        continue
                    try:
                        pose_matches = (
                            math.isclose(float(source.get("azimuth_deg")), float(view.get("azimuth_deg")), abs_tol=0.01)
                            and math.isclose(float(source.get("elevation_deg")), float(view.get("elevation_deg")), abs_tol=0.01)
                        )
                    except (TypeError, ValueError):
                        pose_matches = False
                    if (
                        pose_matches
                        and set(source.get("visible_surfaces") or []) == set(view.get("visible_surface_ids") or [])
                        and set(view.get("visible_component_ids") or []).issubset(set(source.get("visible_component_ids") or []))
                    ):
                        direct_pose_sources.append(source_id)
                if not direct_pose_sources:
                    errors.append(
                        f"coverage_matrix {view_id}: source-derived full-product view requires an attached direct source with identical view_id, pose, and visible surfaces"
                    )
        if derivation == "generated":
            if any(view.get(key) == "source_verified" for key in ("pose_source_status", "surface_source_status", "material_source_status")):
                errors.append(f"coverage_matrix {view_id}: generated view cannot self-upgrade to direct evidence")
            if any(view.get(key) != "inferred_from_sources" for key in ("pose_source_status", "surface_source_status", "material_source_status")):
                errors.append(f"coverage_matrix {view_id}: generated view requires inferred pose/surface/material evidence")
            if view.get("copy_source_status") not in {"inferred_from_sources", "not_applicable_no_visible_content"}:
                errors.append(f"coverage_matrix {view_id}: generated view has invalid copy inference")
            if len(parents) < 2 or len(parents) != len(set(parents)):
                errors.append(f"coverage_matrix {view_id}: generated view requires at least two unique direct anchors")
            parent_views = [by_id[parent_id] for parent_id in parents if parent_id in by_id]
            if any(
                parent.get("derivation_status") != "source"
                or parent.get("pose_source_status") != "source_verified"
                or parent.get("surface_source_status") != "source_verified"
                or parent.get("material_source_status") != "source_verified"
                for parent in parent_views
            ):
                errors.append(f"coverage_matrix {view_id}: every parent anchor must be source-verified")
            for key in (
                "visible_surface_ids", "visible_component_ids", "geometry_landmark_ids",
                "material_feature_ids", "ocr_field_ids_visible", "code_ids_visible", "graphic_ids_visible",
            ):
                parent_union = {
                    item for parent in parent_views for item in (parent.get(key) or []) if isinstance(item, str)
                }
                if not set(view.get(key) or []).issubset(parent_union):
                    errors.append(f"coverage_matrix {view_id}: generated view first-exposes unsupported {key}")
            parent_refs = {
                item for parent in parent_views for item in (parent.get("source_refs") or []) if isinstance(item, str)
            }
            if not set(view.get("source_refs") or []).issubset(parent_refs):
                errors.append(f"coverage_matrix {view_id}: generated view source_refs are not inherited from anchors")

    full_product_views = [view for view_id, view in by_id.items() if view_id in required_ids and view.get("shot_scale") == "full_product"]
    copy_detail_views = [
        view for view_id, view in by_id.items()
        if view_id in required_ids and (
            view.get("shot_scale") == "rectified_surface_evidence"
            or str(view.get("family", "")).startswith("detail_copy")
        )
    ]
    for record_id, record, key, label in [
        *[(field_id, field, "ocr_field_ids_visible", "field") for field_id, field in text_fields.items()],
        *[(code_id, code, "code_ids_visible", "code") for code_id, code in code_records.items()],
        *[(graphic_id, graphic, "graphic_ids_visible", "graphic") for graphic_id, graphic in graphic_records.items()],
    ]:
        surface_id = record.get("surface_id")
        applicable_full = [view for view in full_product_views if surface_id in set(view.get("visible_surface_ids") or [])]
        if applicable_full and not all(record_id in set(view.get(key) or []) for view in applicable_full):
            errors.append(f"coverage_matrix: required {label} {record_id} is omitted from a visible full-product view")
        region_id = record.get("region_id")
        dynamic_view_id = (
            dynamic_region_detail_view_id(region_id)
            if isinstance(region_id, str) and region_id else None
        )
        dynamic_view = by_id.get(dynamic_view_id or "", {})
        if dynamic_view_id not in set(record.get("required_view_ids") or []):
            errors.append(
                f"coverage_matrix: required {label} {record_id} manifest does not bind its region-derived detail view"
            )
        if record_id not in set(dynamic_view.get(key) or []):
            errors.append(
                f"coverage_matrix: required {label} {record_id} lacks its own region-derived exact-copy detail master"
            )
    if coverage.get("production_coverage_status") != "passed":
        errors.append("coverage_matrix: production_coverage_status must be passed before generation")
    return set(required_ids), ring_sequences, by_id


def validate_continuity(
    contract: dict[str, Any], product_features: list[str], errors: list[str],
    *, source_manifest_sha256: str | None = None,
    neutral_ring_views: list[str] | None = None,
) -> None:
    if contract.get("schema_version") != "packaging-continuity-contract.v1":
        errors.append("continuity_contract: invalid schema_version")
    if contract.get("freeze_status") != "frozen":
        errors.append("continuity_contract: freeze_status must be frozen")
    gates = contract.get("required_gates")
    expected_gates = derive_required_continuity_gates(product_features)
    if (
        not isinstance(gates, list)
        or len(gates) != len(set(gates))
        or set(gates) != expected_gates
    ):
        errors.append(
            "continuity_contract: required_gates must exactly match the source-feature-derived "
            f"v3 gate set {sorted(expected_gates)}"
        )
    if contract.get("text_code_topology_zero_tolerance") is not True:
        errors.append("continuity_contract: text/code/topology must be zero-tolerance")
    if source_manifest_sha256 is not None and neutral_ring_views:
        calibrations = contract.get("calibration_baselines")
        if not isinstance(calibrations, dict):
            errors.append("continuity_contract: pose-conditioned calibration_baselines are required before generation")
            return
        calibrated_gate_ids = {"silhouette_gate", "material_gate", "loop_closure_gate"}
        if "transparent_showthrough_gate" in expected_gates:
            calibrated_gate_ids.add("transparent_showthrough_gate")
        expected_ids = {
            "silhouette_gate": "silhouette_source_pose_baseline_v1",
            "material_gate": "material_source_pose_baseline_v1",
            "transparent_showthrough_gate": "showthrough_source_pose_baseline_v1",
            "loop_closure_gate": "loop_closure_pose_baseline_v1",
            "edge_measurements": "edge_motion_pose_baseline_v1",
        }
        for key in sorted(calibrated_gate_ids | {"edge_measurements"}):
            calibration = calibrations.get(key)
            if not isinstance(calibration, dict) or (
                calibration.get("calibration_id") != expected_ids[key]
                or calibration.get("basis") != "source_pose_locked_before_generation"
                or calibration.get("source_manifest_sha256") != source_manifest_sha256
            ):
                errors.append(f"continuity_contract: {key} source/pose calibration identity is invalid")
                continue
            if key in {"silhouette_gate", "material_gate", "transparent_showthrough_gate"}:
                if set(calibration.get("by_view") or {}) != set(neutral_ring_views):
                    errors.append(f"continuity_contract: {key} calibration must exactly cover the neutral ring")
            else:
                expected_edges = {
                    f"{neutral_ring_views[index]}__TO__{neutral_ring_views[(index + 1) % len(neutral_ring_views)]}"
                    for index in range(len(neutral_ring_views))
                }
                if key == "loop_closure_gate":
                    expected_edges = {
                        f"{neutral_ring_views[-1]}__TO__{neutral_ring_views[0]}"
                    }
                if set(calibration.get("by_edge") or {}) != expected_edges:
                    errors.append(f"continuity_contract: {key} calibration edge coverage is invalid")


def validate_composition(
    plan: dict[str, Any],
    required_views: set[str],
    coverage_views: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    if plan.get("schema_version") != "packaging-deterministic-composition-plan.v1":
        errors.append("composition_plan: invalid schema_version")
    if plan.get("status") != "ready":
        errors.append("composition_plan: status must be ready")
    if not isinstance(plan.get("plan_id"), str) or not plan.get("plan_id"):
        errors.append("composition_plan: plan_id must be non-empty")
    statuses = plan.get("view_statuses")
    if not isinstance(statuses, list):
        errors.append("composition_plan: view_statuses must be an array")
        return
    by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(statuses):
        if not isinstance(item, dict) or not isinstance(item.get("view_id"), str):
            errors.append(f"composition_plan.view_statuses[{index}]: invalid record")
            continue
        if item["view_id"] in by_id:
            errors.append(f"composition_plan: duplicate view_id {item['view_id']}")
        by_id[item["view_id"]] = item
    if set(by_id) != required_views:
        errors.append("composition_plan: view_statuses must exactly cover required views")
    allowed = {"ready", "not_required_no_visible_copy"}
    for view_id, item in by_id.items():
        if item.get("status") not in allowed:
            errors.append(f"composition_plan {view_id}: unresolved deterministic projection")
        if item.get("status") == "ready" and item.get("projection_model") not in EXECUTABLE_PROJECTION_MODELS:
            errors.append(f"composition_plan {view_id}: projection_model is not executable by the bundled compositor")
        coverage_view = coverage_views.get(view_id, {})
        expected_regions = coverage_view.get("label_region_ids") or []
        if item.get("protected_region_ids") != expected_regions:
            errors.append(f"composition_plan {view_id}: protected_region_ids mismatch coverage")
        for key in ("ocr_field_ids_visible", "code_ids_visible", "graphic_ids_visible"):
            if item.get(key) != (coverage_view.get(key) or []):
                errors.append(f"composition_plan {view_id}: {key} mismatch coverage")
        has_protected_content = bool(
            coverage_view.get("ocr_field_ids_visible")
            or coverage_view.get("code_ids_visible")
            or coverage_view.get("graphic_ids_visible")
        )
        if has_protected_content and item.get("status") != "ready":
            errors.append(f"composition_plan {view_id}: visible exact content requires an executable composition job")
        if not has_protected_content and item.get("status") == "not_required_no_visible_copy" and item.get("projection_model") not in {None, "none"}:
            errors.append(f"composition_plan {view_id}: no-copy view must not claim an unused projection model")
        if item.get("status") == "ready":
            source_layers = item.get("source_layer_ids")
            if not isinstance(source_layers, list) or not source_layers:
                errors.append(f"composition_plan {view_id}: ready projection requires source_layer_ids")
            if item.get("binding_receipt_required") is not True:
                errors.append(f"composition_plan {view_id}: binding_receipt_required must be true")


def validate_bundle(bundle: dict[str, Any], root: Path, manifest: dict[str, Any], errors: list[str]) -> None:
    if bundle.get("schema_version") != "packaging-exact-copy-bundle.v1":
        errors.append("exact_copy_bundle: invalid schema_version")
    if bundle.get("freeze_status") != "frozen":
        errors.append("exact_copy_bundle: freeze_status must be frozen")
    mapping = {
        "text_ssot_sha256": "text_ssot",
        "code_manifest_sha256": "code_manifest",
        "logo_graphic_manifest_sha256": "logo_graphic_manifest",
        "surface_texture_atlas_sha256": "surface_texture_atlas",
        "protected_region_masks_sha256": "protected_region_masks",
        "deterministic_composition_plan_sha256": "composition_plan",
    }
    for bundle_key, path_key in mapping.items():
        path, path_errors = safe_run_path(root, manifest["paths"].get(path_key), path_key)
        errors.extend(path_errors)
        if path and bundle.get(bundle_key) != sha256_file(path):
            errors.append(f"exact_copy_bundle: {bundle_key} does not match {path_key}")
    bundle_hash = canonical_hash(bundle, "exact_copy_bundle_sha256")
    if bundle.get("exact_copy_bundle_sha256") != bundle_hash:
        errors.append("exact_copy_bundle: self hash mismatch")
    if manifest["hashes"].get("exact_copy_bundle_sha256") != bundle_hash:
        errors.append("run_manifest exact_copy_bundle_sha256 mismatch")


def validate_prompt_index(
    root: Path,
    prompt_index: dict[str, Any],
    manifest: dict[str, Any],
    coverage: dict[str, Any],
    required_views: set[str],
    coverage_views: dict[str, dict[str, Any]],
    composition_plan: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    if prompt_index.get("schema_version") != "packaging-generation-prompt-index.v1":
        errors.append("generation_prompt_index: invalid schema_version")
    expected_dependencies = {
        "exact_copy_bundle_sha256": manifest["hashes"].get("exact_copy_bundle_sha256"),
        "exact_copy_bundle_file_sha256": manifest["hashes"].get("exact_copy_bundle_file_sha256"),
        "coverage_matrix_sha256": manifest["hashes"].get("coverage_matrix_sha256"),
        "surface_texture_atlas_sha256": manifest["hashes"].get("surface_texture_atlas_sha256"),
    }
    expected_extended_dependencies = {
        "source_manifest_sha256": manifest["hashes"].get("source_manifest_sha256"),
        "protected_region_masks_sha256": manifest["hashes"].get("protected_region_masks_sha256"),
        "composition_plan_sha256": manifest["hashes"].get("composition_plan_sha256"),
    }
    compiler_path = SKILL_DIR / "scripts/compile_generation_prompts.py"
    compiler_sha = sha256_file(compiler_path) if compiler_path.is_file() else None
    if prompt_index.get("compiler_path") != "scripts/compile_generation_prompts.py" or prompt_index.get("compiler_sha256") != compiler_sha:
        errors.append("generation_prompt_index: canonical compiler path/hash mismatch")
    if prompt_index.get("dependency_hashes") != expected_dependencies:
        errors.append("generation_prompt_index: dependency_hashes must exactly match the frozen run")
    if prompt_index.get("extended_dependency_hashes") != expected_extended_dependencies:
        errors.append("generation_prompt_index: extended dependency hashes must exactly match the frozen run")
    identity_lock = coverage.get("identity_lock") if isinstance(coverage, dict) else None
    if not isinstance(identity_lock, dict) or prompt_index.get("global_identity_core_sha256") != canonical_hash(identity_lock):
        errors.append("generation_prompt_index: global identity core hash mismatch")
    try:
        compiler = prompt_compiler_module()
    except Exception as exc:
        errors.append(f"generation_prompt_index: canonical compiler replay unavailable: {exc}")
        compiler = None
    prompts = prompt_index.get("prompts")
    if not isinstance(prompts, list):
        errors.append("generation_prompt_index: prompts must be an array")
        return {}
    by_view: dict[str, dict[str, Any]] = {}
    asset_ids: set[str] = set()
    prompt_paths: set[str] = set()
    for index, item in enumerate(prompts):
        if not isinstance(item, dict):
            errors.append(f"generation_prompt_index.prompts[{index}]: must be an object")
            continue
        view_id = item.get("view_id")
        if not isinstance(view_id, str) or view_id in by_view:
            errors.append(f"generation_prompt_index.prompts[{index}]: view_id must be unique")
            continue
        by_view[view_id] = item
        coverage_view = coverage_views.get(view_id, {})
        asset_id = item.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id or asset_id in asset_ids:
            errors.append(f"generation_prompt_index {view_id}: asset_id must be unique and non-empty")
        else:
            asset_ids.add(asset_id)
        if item.get("generation_text_policy") != "no_model_generated_product_copy":
            errors.append(f"generation_prompt_index {view_id}: invalid generation_text_policy")
        path, path_errors = safe_run_path(root, item.get("prompt_path"), f"prompt {view_id}")
        errors.extend(path_errors)
        prompt_locator = item.get("prompt_path")
        if isinstance(prompt_locator, str) and prompt_locator in prompt_paths:
            errors.append(f"generation_prompt_index {view_id}: prompt_path must be unique")
        elif isinstance(prompt_locator, str):
            prompt_paths.add(prompt_locator)
        if path:
            if item.get("prompt_sha256") != sha256_file(path):
                errors.append(f"generation_prompt_index {view_id}: prompt hash mismatch")
            try:
                prompt_text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                errors.append(f"generation_prompt_index {view_id}: prompt is not UTF-8: {exc}")
                prompt_text = ""
            required_markers = [
                "Create exactly one horizontal 16:9 full-frame packaging product reference asset.",
                f"view {view_id}",
                str(manifest["hashes"].get("exact_copy_bundle_sha256")),
                str(manifest["hashes"].get("exact_copy_bundle_file_sha256")),
                str(manifest["hashes"].get("coverage_matrix_sha256")),
                str(manifest["hashes"].get("surface_texture_atlas_sha256")),
                str(manifest.get("product_state_id")),
                "generation_text_policy: no_model_generated_product_copy",
                "raw_generated_asset_publishable: false",
                "raw_generated_asset_registry_eligible: false",
                f"azimuth_deg: {float(coverage_view.get('azimuth_deg')) if isinstance(coverage_view.get('azimuth_deg'), (int, float)) else '<invalid>'}",
                f"elevation_deg: {float(coverage_view.get('elevation_deg')) if isinstance(coverage_view.get('elevation_deg'), (int, float)) else '<invalid>'}",
                f"roll_deg: {float(coverage_view.get('roll_deg')) if isinstance(coverage_view.get('roll_deg'), (int, float)) else '<invalid>'}",
                f"shot_scale: {coverage_view.get('shot_scale')}",
                f"view_family: {coverage_view.get('family')}",
                f"review_board_role: {coverage_view.get('review_board_role')}",
                "dynamic_region_contract: " + json.dumps(coverage_view.get("dynamic_region_contract"), ensure_ascii=False, separators=(",", ":"), sort_keys=True),
                f"lens_profile: {coverage_view.get('lens_profile')}",
                f"camera_distance_profile: {coverage_view.get('camera_distance_profile')}",
                "visible_surface_ids: " + json.dumps(coverage_view.get("visible_surface_ids") or [], ensure_ascii=False, separators=(",", ":")),
                "visible_component_ids: " + json.dumps(coverage_view.get("visible_component_ids") or [], ensure_ascii=False, separators=(",", ":")),
                "source_reference_ids: " + json.dumps(coverage_view.get("source_refs") or [], ensure_ascii=False, separators=(",", ":")),
                "parent_anchor_view_ids: " + json.dumps(coverage_view.get("parent_anchor_view_ids") or [], ensure_ascii=False, separators=(",", ":")),
                "previous_anchor_id: " + json.dumps(coverage_view.get("previous_view_id"), ensure_ascii=False, separators=(",", ":")),
                "next_anchor_id: " + json.dumps(coverage_view.get("next_view_id"), ensure_ascii=False, separators=(",", ":")),
                "protected_copy_region_ids: " + json.dumps(coverage_view.get("label_region_ids") or [], ensure_ascii=False, separators=(",", ":")),
                f"deterministic_composition_plan_id: {composition_plan.get('plan_id')}",
                "material_lock: preserve source-bound material response",
                "geometry_lock: preserve source-bound topology and proportions",
            ]
            if len(prompt_text) < 300 or any(marker not in prompt_text for marker in required_markers):
                errors.append(f"generation_prompt_index {view_id}: prompt is incomplete or not dependency-bound")
            if compiler is not None and isinstance(identity_lock, dict):
                composition_view = next(
                    (record for record in composition_plan.get("view_statuses", []) if isinstance(record, dict) and record.get("view_id") == view_id),
                    None,
                )
                if not isinstance(composition_view, dict):
                    errors.append(f"generation_prompt_index {view_id}: composition replay row is missing")
                else:
                    try:
                        ranked = compiler.ranked_references(coverage_view)
                        expected_payload = compiler.prompt_bytes(
                            manifest=manifest,
                            coverage=coverage,
                            view=coverage_view,
                            composition=composition_plan,
                            composition_view=composition_view,
                            dependencies=expected_dependencies,
                            extended_dependencies=expected_extended_dependencies,
                            asset_id=asset_id,
                            ranked=ranked,
                        )
                    except Exception as exc:
                        errors.append(f"generation_prompt_index {view_id}: canonical prompt replay failed: {exc}")
                    else:
                        if path.read_bytes() != expected_payload:
                            errors.append(f"generation_prompt_index {view_id}: prompt bytes differ from canonical compiler replay")
                        expected_prompt_locator = (
                            Path(str(manifest.get("paths", {}).get("generation_prompt_index"))).parent
                            / "generation_units" / f"{asset_id}_generation_prompt.md"
                        ).as_posix()
                        expected_record_fields = {
                            "prompt_path": expected_prompt_locator,
                            "prompt_sha256": hashlib.sha256(expected_payload).hexdigest(),
                            "dependency_hashes": expected_dependencies,
                            "extended_dependency_hashes": expected_extended_dependencies,
                            "compiler_sha256": compiler_sha,
                            "ranked_reference_bindings": ranked,
                            "parent_anchor_view_ids": coverage_view.get("parent_anchor_view_ids"),
                        }
                        for replay_key, replay_value in expected_record_fields.items():
                            if item.get(replay_key) != replay_value:
                                errors.append(f"generation_prompt_index {view_id}: {replay_key} differs from canonical compiler replay")
        if item.get("dependency_hashes") != expected_dependencies:
            errors.append(f"generation_prompt_index {view_id}: unit dependency_hashes mismatch")
        if item.get("product_state_id") != manifest.get("product_state_id"):
            errors.append(f"generation_prompt_index {view_id}: product_state_id mismatch")
        references = item.get("reference_ids")
        if not isinstance(references, list) or set(references) != set(coverage_view.get("source_refs") or []) or not set(references).issubset(sources):
            errors.append(f"generation_prompt_index {view_id}: reference_ids must exactly match coverage source_refs")
        if item.get("previous_anchor_id") != coverage_view.get("previous_view_id"):
            errors.append(f"generation_prompt_index {view_id}: previous anchor mismatch")
        if item.get("next_anchor_id") != coverage_view.get("next_view_id"):
            errors.append(f"generation_prompt_index {view_id}: next anchor mismatch")
        if item.get("protected_copy_region_ids") != coverage_view.get("label_region_ids"):
            errors.append(f"generation_prompt_index {view_id}: protected copy regions mismatch")
        if item.get("deterministic_composition_plan_id") != composition_plan.get("plan_id"):
            errors.append(f"generation_prompt_index {view_id}: composition plan ID mismatch")
    missing = sorted(required_views - set(by_view))
    if missing:
        errors.append("generation_prompt_index: missing required prompts: " + ", ".join(missing))
    extra = sorted(set(by_view) - required_views)
    if extra:
        errors.append("generation_prompt_index: unexpected prompts: " + ", ".join(extra))
    return by_view


def derive_continuity_metric_status(record: dict[str, Any]) -> str | None:
    comparator = record.get("comparator")
    value = record.get("value")
    tolerance = record.get("tolerance")
    if comparator == "manual":
        return "blocked"
    if comparator == "eq":
        return "passed" if value == tolerance else "failed"
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        return None
    if comparator in {"lte", "gte"}:
        if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or not math.isfinite(float(tolerance)):
            return None
        return "passed" if (
            float(value) <= float(tolerance) if comparator == "lte" else float(value) >= float(tolerance)
        ) else "failed"
    if comparator == "between" and isinstance(tolerance, list) and len(tolerance) == 2 and all(
        not isinstance(item, bool) and isinstance(item, (int, float)) and math.isfinite(float(item))
        for item in tolerance
    ):
        return "passed" if float(tolerance[0]) <= float(value) <= float(tolerance[1]) else "failed"
    return None


def validate_continuity_qa_v2(
    root: Path,
    manifest: dict[str, Any],
    continuity_qa: dict[str, Any],
    asset_by_view: dict[str, dict[str, Any]],
    coverage_views: dict[str, dict[str, Any]],
    ring_sequences: list[list[str]],
    errors: list[str],
) -> None:
    if continuity_qa.get("schema_version") != "packaging-continuity-qa.v1":
        errors.append("continuity_qa: invalid schema_version")
        return
    gate_results = continuity_qa.get("gate_results")
    edge_results = continuity_qa.get("edge_results")
    gate_by_id = {
        item.get("gate_id"): item for item in gate_results
        if isinstance(item, dict) and isinstance(item.get("gate_id"), str)
    } if isinstance(gate_results, list) else {}
    edge_by_id = {
        item.get("edge_id"): item for item in edge_results
        if isinstance(item, dict) and isinstance(item.get("edge_id"), str)
    } if isinstance(edge_results, list) else {}
    expected_gates = derive_required_continuity_gates(
        list(manifest.get("product_features") or [])
    )
    if set(gate_by_id) != expected_gates or not isinstance(gate_results, list) or len(gate_results) != len(gate_by_id):
        errors.append("continuity_qa: gate_results must exactly cover source-feature-derived continuity gates")
        return
    expected_edges = {
        f"{ring[index]}__TO__{ring[(index + 1) % len(ring)]}": (
            ring[index], ring[(index + 1) % len(ring)]
        )
        for ring in ring_sequences for index in range(len(ring))
    }
    if set(edge_by_id) != set(expected_edges) or not isinstance(edge_results, list) or len(edge_results) != len(edge_by_id):
        errors.append("continuity_qa: edge_results must exactly cover every ring and loop edge")
        return
    evidence_locks = {
        (item.get("evidence_path"), item.get("evidence_sha256"))
        for item in [*gate_by_id.values(), *edge_by_id.values()]
    }
    if len(evidence_locks) != 1:
        errors.append("continuity_qa: v2 requires one canonical measurement receipt for all gates and edges")
        return
    evidence_locator, evidence_file_sha = next(iter(evidence_locks))
    evidence = load_evidence_json(
        root, evidence_locator, evidence_file_sha, "continuity_qa measurement receipt", errors,
    )
    if not evidence:
        return
    tool_path = SKILL_DIR / "scripts/build_continuity_measurements.py"
    if (
        evidence.get("schema_version") != "packaging-continuity-measurements.v2"
        or evidence.get("tool_script_path") != "scripts/build_continuity_measurements.py"
        or evidence.get("tool_script_sha256") != sha256_file(tool_path)
        or evidence.get("receipt_sha256") != canonical_hash(evidence, "receipt_sha256")
        or contains_forbidden_test_marker(evidence)
    ):
        errors.append("continuity_qa: v2 measurement receipt identity/self-hash failed")
        return
    input_locks = evidence.get("input_locks")
    expected_inputs = {
        "source_manifest_path": manifest["paths"].get("source_manifest"),
        "source_manifest_sha256": manifest["hashes"].get("source_manifest_sha256"),
        "asset_qa_path": manifest["paths"].get("asset_qa"),
        "asset_qa_sha256": manifest["hashes"].get("asset_qa_sha256"),
        "coverage_matrix_path": manifest["paths"].get("coverage_matrix"),
        "coverage_matrix_sha256": manifest["hashes"].get("coverage_matrix_sha256"),
        "continuity_contract_path": manifest["paths"].get("continuity_contract"),
        "continuity_contract_sha256": manifest["hashes"].get("continuity_contract_sha256"),
    }
    if not isinstance(input_locks, dict) or any(input_locks.get(key) != value for key, value in expected_inputs.items()):
        errors.append("continuity_qa: measurement input locks do not match current run")
        return
    semantic_path: Path | None = None
    semantic_locator = input_locks.get("semantic_evidence_path")
    semantic_sha = input_locks.get("semantic_evidence_sha256")
    if semantic_locator is not None or semantic_sha is not None:
        semantic_path, semantic_errors = safe_run_path(root, semantic_locator, "continuity semantic evidence")
        errors.extend(semantic_errors)
        if semantic_path is None or semantic_sha != sha256_file(semantic_path):
            errors.append("continuity_qa: semantic evidence file/hash binding failed")
            return
    for index, binding in enumerate(evidence.get("semantic_annotation_bindings") or []):
        if not isinstance(binding, dict):
            errors.append(f"continuity_qa: invalid semantic annotation binding {index}")
            continue
        annotation_path, annotation_errors = safe_run_path(
            root, binding.get("annotation_path"), f"continuity annotation {index}",
        )
        errors.extend(annotation_errors)
        if annotation_path is None or binding.get("annotation_sha256") != sha256_file(annotation_path):
            errors.append(f"continuity_qa: semantic annotation {index} hash binding failed")
    try:
        builder = load_bundled_module(tool_path, "packaging_continuity_measurement_validator")
        replay_root = root.resolve()
        asset_qa_path = replay_root / str(manifest["paths"].get("asset_qa"))
        coverage_path = replay_root / str(manifest["paths"].get("coverage_matrix"))
        continuity_path = replay_root / str(manifest["paths"].get("continuity_contract"))
        source_manifest_path = replay_root / str(manifest["paths"].get("source_manifest"))
        replay = builder.build_receipt(
            replay_root, asset_qa_path, coverage_path, continuity_path, semantic_path,
            source_manifest_path,
        )
        if replay != evidence:
            errors.append("continuity_qa: installed measurement builder replay differs from locked receipt")
            return
    except Exception as exc:
        errors.append(f"continuity_qa: measurement builder replay failed: {exc}")
        return
    evidence_assets = evidence.get("assets")
    evidence_asset_by_view = {
        item.get("view_id"): item for item in evidence_assets
        if isinstance(item, dict) and isinstance(item.get("view_id"), str)
    } if isinstance(evidence_assets, list) else {}
    if set(evidence_asset_by_view) != set(asset_by_view):
        errors.append("continuity_qa: measurement assets do not exactly cover approved masters")
    for view_id, asset in asset_by_view.items():
        measured = evidence_asset_by_view.get(view_id, {})
        if any(measured.get(key) != asset.get(key) for key in ("asset_id", "file_path", "file_sha256")):
            errors.append(f"continuity_qa: measurement asset binding failed for {view_id}")
    evidence_gates = {
        item.get("gate_id"): item for item in evidence.get("gate_measurements", [])
        if isinstance(item, dict) and isinstance(item.get("gate_id"), str)
    }
    evidence_edges = {
        item.get("edge_id"): item for item in evidence.get("edge_measurements", [])
        if isinstance(item, dict) and isinstance(item.get("edge_id"), str)
    }
    if (
        set(evidence_gates) != expected_gates
        or set(evidence_edges) != set(expected_edges)
        or evidence.get("observed_product_features") != sorted(set(manifest.get("product_features") or []))
        or evidence.get("derived_required_gates") != sorted(expected_gates)
    ):
        errors.append("continuity_qa: measurement receipt gate/edge coverage is incomplete")
        return
    valid_hashes = {asset.get("file_sha256") for asset in asset_by_view.values()}
    def verify_measurement_group(owner: str, group: dict[str, Any]) -> bool:
        records = group.get("metric_records")
        if not isinstance(records, list) or not records:
            errors.append(f"continuity_qa {owner}: metric_records must be non-empty")
            return False
        metric_ids: set[str] = set()
        statuses: list[str] = []
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get("metric_id"), str) or record["metric_id"] in metric_ids:
                errors.append(f"continuity_qa {owner}: metric IDs must be unique")
                return False
            metric_ids.add(record["metric_id"])
            derived = derive_continuity_metric_status(record)
            if derived is None or record.get("status") != derived:
                errors.append(f"continuity_qa {owner}: metric status is not comparator-derived")
                return False
            hashes = record.get("asset_file_sha256s")
            if not isinstance(hashes, list) or not hashes or not set(hashes).issubset(valid_hashes):
                errors.append(f"continuity_qa {owner}: metric master binding failed")
                return False
            statuses.append(derived)
        derived_group = "failed" if "failed" in statuses else "blocked" if "blocked" in statuses else "passed"
        if group.get("status") != derived_group:
            errors.append(f"continuity_qa {owner}: group status is not metric-derived")
            return False
        return True
    all_passed = True
    all_hash_list = [asset_by_view[view_id].get("file_sha256") for view_id in sorted(asset_by_view)]
    for gate_id, group in evidence_gates.items():
        okay = verify_measurement_group(gate_id, group)
        result = gate_by_id[gate_id]
        if (
            not okay
            or group.get("semantic_evidence_applied") is not True
            or group.get("status") != "passed"
            or result.get("status") != group.get("status")
            or sorted(result.get("asset_file_sha256s") or []) != sorted(all_hash_list)
        ):
            errors.append(f"continuity_qa {gate_id}: semantic measurement/result did not pass")
            all_passed = False
    for edge_id, group in evidence_edges.items():
        okay = verify_measurement_group(edge_id, group)
        result = edge_by_id[edge_id]
        from_view, to_view = expected_edges[edge_id]
        if (
            not okay
            or group.get("semantic_evidence_applied") is not True
            or group.get("status") != "passed"
            or result.get("status") != group.get("status")
            or result.get("from_view_id") != from_view
            or result.get("to_view_id") != to_view
            or result.get("from_file_sha256") != asset_by_view[from_view].get("file_sha256")
            or result.get("to_file_sha256") != asset_by_view[to_view].get("file_sha256")
        ):
            errors.append(f"continuity_qa {edge_id}: semantic edge measurement/result did not pass")
            all_passed = False
    if continuity_qa.get("all_gates_passed") is not all_passed or continuity_qa.get("loop_closure_status") != ("passed" if all_passed else "failed"):
        errors.append("continuity_qa: top-level status does not match v2 measurements")
    expected_failed = sorted(
        result.get("edge_id") for result in edge_by_id.values() if result.get("status") != "passed"
    )
    if continuity_qa.get("failed_edge_ids") != expected_failed:
        errors.append("continuity_qa: failed_edge_ids does not match v2 edge measurements")


def validate_dynamic_region_pixel_contract(
    root: Path,
    view_id: str,
    view: dict[str, Any],
    asset: dict[str, Any],
    evidence: dict[str, Any],
    errors: list[str],
) -> bool:
    """Verify a region detail's declared 4K-equivalent readability against final pixels."""
    dynamic = view.get("dynamic_region_contract")
    if not isinstance(dynamic, dict):
        return True
    prefix = f"post_composite_verification {view_id} dynamic region"
    passed = True

    def fail(message: str) -> None:
        nonlocal passed
        errors.append(f"{prefix}: {message}")
        passed = False

    region_id = dynamic.get("region_id")
    pixel_contract = dynamic.get("native_region_pixel_contract")
    if not isinstance(region_id, str) or not isinstance(pixel_contract, dict):
        fail("region/pixel contract is malformed")
        return False
    asset_path, path_errors = safe_run_path(root, asset.get("file_path"), f"{prefix} master")
    errors.extend(path_errors)
    if asset_path is None:
        return False
    try:
        with Image.open(asset_path) as opened:
            opened.load()
            master_width, master_height = opened.size
    except Exception as exc:
        fail(f"final master dimensions cannot be decoded: {exc}")
        return False
    reference = pixel_contract.get("reference_canvas_px")
    if not isinstance(reference, dict):
        fail("reference canvas is missing")
        return False
    try:
        reference_width = int(reference["width"])
        reference_height = int(reference["height"])
        scale_x = reference_width / master_width
        scale_y = reference_height / master_height
    except Exception:
        fail("reference/master dimensions are invalid")
        return False
    region_scans = [
        scan for scan in evidence.get("scans", [])
        if isinstance(scan, dict)
        and scan.get("scope") == "projected_region_crop"
        and region_id in (scan.get("region_ids") or [])
    ]
    if not region_scans:
        fail("no final-master projected crop binds this exact region")
        return False
    boxes = [scan.get("crop_box_px_on_final_master") for scan in region_scans]
    if any(not isinstance(box, list) or len(box) != 4 for box in boxes):
        fail("projected region crop boxes are invalid")
        return False
    union_left = min(int(box[0]) for box in boxes)
    union_top = min(int(box[1]) for box in boxes)
    union_right = max(int(box[2]) for box in boxes)
    union_bottom = max(int(box[3]) for box in boxes)
    region_width_at_reference = (union_right - union_left) * scale_x
    region_height_at_reference = (union_bottom - union_top) * scale_y
    if region_width_at_reference < float(pixel_contract.get("min_region_width_px_at_reference", math.inf)):
        fail("final-master region bbox is below the 4K-equivalent minimum width")
    if region_height_at_reference < float(pixel_contract.get("min_region_height_px_at_reference", math.inf)):
        fail("final-master region bbox is below the 4K-equivalent minimum height")

    scan_by_id = {
        scan.get("scan_id"): scan for scan in region_scans
        if isinstance(scan.get("scan_id"), str)
    }
    required_fields = set(dynamic.get("field_ids") or [])
    if required_fields:
        line_heights: list[float] = []
        for raw in (evidence.get("raw_scan_observations") or {}).get("text", []):
            if not isinstance(raw, dict) or raw.get("scan_id") not in scan_by_id:
                continue
            box = raw.get("scan_bounding_box_normalized")
            scan = scan_by_id[raw["scan_id"]]
            dimensions = scan.get("pixel_dimensions") or {}
            if isinstance(box, dict) and isinstance(box.get("height"), (int, float)):
                try:
                    line_heights.append(float(box["height"]) * float(dimensions["height"]) * scale_y)
                except Exception:
                    continue
        if not line_heights or min(line_heights) < float(pixel_contract.get("min_text_line_height_px_at_reference", math.inf)):
            fail("final-master text line height is below the 4K-equivalent readability threshold")

    for content_key, scan_key, threshold_key, label in (
        ("code_ids", "code_ids", "min_code_short_edge_px_at_reference", "code"),
        ("graphic_ids", "graphic_ids", "min_graphic_short_edge_px_at_reference", "graphic"),
    ):
        for content_id in dynamic.get(content_key) or []:
            matching = [scan for scan in region_scans if content_id in (scan.get(scan_key) or [])]
            if not matching:
                fail(f"{label} {content_id} has no bound final-master projected crop")
                continue
            best_short_edge = 0.0
            for scan in matching:
                box = scan["crop_box_px_on_final_master"]
                best_short_edge = max(
                    best_short_edge,
                    min((box[2] - box[0]) * scale_x, (box[3] - box[1]) * scale_y),
                )
            if best_short_edge < float(pixel_contract.get(threshold_key, math.inf)):
                fail(f"{label} {content_id} is below its 4K-equivalent short-edge threshold")
    return passed


def validate_post_ocr_raw_contract(
    root: Path,
    view_id: str,
    asset: dict[str, Any],
    evidence: dict[str, Any],
    expected_field_ids: set[str],
    expected_code_ids: set[str],
    text_fields: dict[str, dict[str, Any]],
    composition_job: dict[str, Any],
    post_adapter: Any,
    errors: list[str],
) -> bool:
    """Validate that every raw OCR observation has one non-contradictory owner."""
    prefix = f"post_composite_verification {view_id}"
    passed = True

    def fail(message: str) -> None:
        nonlocal passed
        errors.append(f"{prefix}: {message}")
        passed = False

    if evidence.get("mapping_policy") != "exact_utf8_single_or_fixed_bbox_line_aggregation_one_to_one_v2":
        fail("post OCR mapping_policy is not the installed v2 exact policy")
    expected_order_contract = {
        "reading_order": "top_to_bottom_then_same_line_left_to_right",
        "same_line_min_center_delta": post_adapter.SAME_LINE_MIN_CENTER_DELTA,
        "same_line_height_ratio": post_adapter.SAME_LINE_HEIGHT_RATIO,
        "intra_line_joiner": "U+0020",
        "language_model_correction": "forbidden",
    }
    if evidence.get("aggregation_order_contract") != expected_order_contract:
        fail("post OCR aggregation order contract differs from installed adapter")

    asset_path, asset_path_errors = safe_run_path(root, asset.get("file_path"), f"{prefix} approved master")
    errors.extend(asset_path_errors)
    if asset_path_errors or asset_path is None:
        passed = False
        canvas_size = (0, 0)
    else:
        try:
            with Image.open(asset_path) as master_probe:
                master_probe.load()
                canvas_size = master_probe.size
        except Exception as exc:
            fail(f"approved master cannot be decoded for projected-crop replay: {exc}")
            canvas_size = (0, 0)
    expected_group_layers: dict[tuple[Any, ...], list[str]] = {}
    layers = composition_job.get("layers") if isinstance(composition_job, dict) else None
    if not isinstance(layers, list) or not layers:
        fail("composition job layers are required for projected-crop replay")
        layers = []
    for layer in layers:
        if not isinstance(layer, dict):
            fail("composition job contains a malformed layer")
            continue
        try:
            box = tuple(post_adapter.parse_destination_box(
                layer, canvas_size, f"{view_id}.{layer.get('layer_id')}.post_crop_replay"
            ))
        except Exception as exc:
            fail(f"composition layer destination geometry cannot be replayed: {exc}")
            continue
        group_key = (
            box,
            tuple(sorted(item for item in layer.get("region_ids", []) if isinstance(item, str))),
            tuple(sorted(item for item in layer.get("field_ids", []) if isinstance(item, str))),
            tuple(sorted(item for item in layer.get("code_ids", []) if isinstance(item, str))),
            tuple(sorted(item for item in layer.get("graphic_ids", []) if isinstance(item, str))),
        )
        expected_group_layers.setdefault(group_key, []).append(str(layer.get("layer_id")))
    expected_scan_groups = {
        (*group_key, tuple(sorted(layer_ids)))
        for group_key, layer_ids in expected_group_layers.items()
    }

    scans = evidence.get("scans")
    scan_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(scans, list) or not scans:
        fail("post OCR scans must be a non-empty array")
        scans = []
    actual_scan_groups: set[tuple[Any, ...]] = set()
    for scan in scans:
        scan_id = scan.get("scan_id") if isinstance(scan, dict) else None
        if not isinstance(scan_id, str) or not scan_id or scan_id in scan_by_id:
            fail("post OCR scan IDs must be unique and non-empty")
            continue
        scan_by_id[scan_id] = scan
        scan_path, scan_errors = safe_run_path(root, scan.get("image_path"), f"{prefix} scan {scan_id}")
        errors.extend(scan_errors)
        if scan_errors:
            passed = False
        if scan_path is None or scan.get("image_sha256") != sha256_file(scan_path):
            fail(f"post OCR scan {scan_id} image/hash binding failed")
        if scan.get("scope") == "final_master":
            if scan.get("image_path") != asset.get("file_path") or scan.get("image_sha256") != asset.get("file_sha256"):
                fail(f"post OCR final-master scan {scan_id} does not bind the approved asset")
            if scan.get("crop_box_px_on_final_master") is not None or scan.get("pixel_dimensions") != {"width": canvas_size[0], "height": canvas_size[1]}:
                fail(f"post OCR final-master scan {scan_id} dimensions/crop contract failed")
        elif scan.get("scope") == "projected_region_crop":
            box_value = scan.get("crop_box_px_on_final_master")
            if (
                not isinstance(box_value, list) or len(box_value) != 4
                or any(isinstance(item, bool) or not isinstance(item, int) for item in box_value)
            ):
                fail(f"post OCR projected scan {scan_id} crop box is invalid")
                continue
            box = tuple(box_value)
            left, top, right, bottom = box
            if left < 0 or top < 0 or right <= left or bottom <= top or right > canvas_size[0] or bottom > canvas_size[1]:
                fail(f"post OCR projected scan {scan_id} crop box is outside the final master")
                continue
            expected_dimensions = {"width": right - left, "height": bottom - top}
            if scan.get("pixel_dimensions") != expected_dimensions:
                fail(f"post OCR projected scan {scan_id} dimensions differ from its crop box")
            if asset_path is not None and scan_path is not None:
                try:
                    with Image.open(asset_path) as master_image, Image.open(scan_path) as crop_image:
                        replay = master_image.convert("RGB").crop(box)
                        actual = crop_image.convert("RGB")
                        if replay.size != actual.size or replay.tobytes() != actual.tobytes():
                            fail(f"post OCR projected scan {scan_id} pixels are detached from the approved final master")
                except Exception as exc:
                    fail(f"post OCR projected scan {scan_id} crop replay failed: {exc}")
            key = (
                box,
                tuple(sorted(item for item in scan.get("region_ids", []) if isinstance(item, str))),
                tuple(sorted(item for item in scan.get("field_ids", []) if isinstance(item, str))),
                tuple(sorted(item for item in scan.get("code_ids", []) if isinstance(item, str))),
                tuple(sorted(item for item in scan.get("graphic_ids", []) if isinstance(item, str))),
                tuple(sorted(item for item in scan.get("layer_ids", []) if isinstance(item, str))),
            )
            if key in actual_scan_groups:
                fail(f"post OCR projected scan {scan_id} duplicates a composition region")
            actual_scan_groups.add(key)
        else:
            fail(f"post OCR scan {scan_id} has invalid scope")
    if sum(1 for item in scan_by_id.values() if item.get("scope") == "final_master") != 1:
        fail("post OCR evidence needs exactly one final-master scan")
    if actual_scan_groups != expected_scan_groups:
        fail("post OCR projected scans do not exactly match composition layer geometry and identifier bindings")

    raw_container = evidence.get("raw_scan_observations")
    raw_text_values = raw_container.get("text") if isinstance(raw_container, dict) else None
    raw_code_values = raw_container.get("codes") if isinstance(raw_container, dict) else None
    if not isinstance(raw_text_values, list) or not isinstance(raw_code_values, list):
        fail("raw_scan_observations must contain text and codes arrays")
        raw_text_values = []
        raw_code_values = []
    raw_text: dict[str, dict[str, Any]] = {}
    for item in raw_text_values:
        raw_id = item.get("raw_observation_id") if isinstance(item, dict) else None
        if not isinstance(raw_id, str) or not raw_id or raw_id in raw_text:
            fail("raw text observation IDs must be unique and non-empty")
            continue
        raw_text[raw_id] = item
        text = item.get("text")
        if (
            not isinstance(text, str) or not text
            or item.get("observed_hash") != sha256_text(text)
            or item.get("scan_id") not in scan_by_id
        ):
            fail(f"raw text observation {raw_id} has invalid bytes/hash/scan binding")
        try:
            post_adapter.normalized_box_metrics(item.get("scan_bounding_box_normalized"), raw_id)
            post_adapter.normalized_box_metrics(item.get("full_master_bounding_box_normalized"), raw_id)
        except Exception:
            fail(f"raw text observation {raw_id} has invalid bounding boxes")

    aggregate_values = evidence.get("aggregate_observations")
    aggregate_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(aggregate_values, list):
        fail("aggregate_observations must be an array")
        aggregate_values = []
    for aggregate in aggregate_values:
        aggregate_id = aggregate.get("raw_observation_id") if isinstance(aggregate, dict) else None
        if not isinstance(aggregate_id, str) or not aggregate_id or aggregate_id in aggregate_by_id:
            fail("aggregate observation IDs must be unique and non-empty")
            continue
        aggregate_by_id[aggregate_id] = aggregate
        candidate_ids = aggregate.get("candidate_ids")
        if (
            not isinstance(candidate_ids, list) or len(candidate_ids) != 1
            or not isinstance(candidate_ids[0], str) or candidate_ids[0] not in expected_field_ids
        ):
            fail(f"aggregate {aggregate_id} must bind exactly one visible field")
            continue
        field_id = candidate_ids[0]
        field = text_fields.get(field_id, {})
        aggregation = aggregate.get("aggregation")
        if (
            field.get("ocr_match_policy") != "ordered_line_aggregation_exact"
            or not isinstance(aggregation, dict)
            or aggregation.get("policy") != "ordered_line_aggregation_exact"
            or aggregation.get("line_joiner") != field.get("line_joiner")
            or aggregation.get("intra_line_joiner") != "U+0020"
            or aggregation.get("reading_order") != "top_to_bottom_then_same_line_left_to_right"
            or aggregation.get("same_line_min_center_delta") != post_adapter.SAME_LINE_MIN_CENTER_DELTA
            or aggregation.get("same_line_height_ratio") != post_adapter.SAME_LINE_HEIGHT_RATIO
            or aggregation.get("uses_language_correction") is not False
        ):
            fail(f"aggregate {aggregate_id} policy/order contract is invalid")
            continue
        lines = aggregation.get("component_raw_observation_ids_by_line")
        if (
            not isinstance(lines, list) or not lines
            or any(
                not isinstance(line, list) or not line
                or any(not isinstance(identifier, str) or not identifier for identifier in line)
                for line in lines
            )
        ):
            fail(f"aggregate {aggregate_id} component lines are invalid")
            continue
        component_ids = [identifier for line in lines for identifier in line]
        if (
            len(component_ids) != len(set(component_ids))
            or any(identifier not in raw_text for identifier in component_ids)
        ):
            fail(f"aggregate {aggregate_id} component IDs are missing or duplicated")
            continue
        components = [raw_text[identifier] for identifier in component_ids]
        scan_ids = {item.get("scan_id") for item in components}
        if len(scan_ids) != 1 or aggregate.get("scan_id") not in scan_ids:
            fail(f"aggregate {aggregate_id} components are not from one scan")
            continue
        source_scan_id = aggregate.get("scan_id")
        source_scan = scan_by_id.get(source_scan_id, {})
        field_region = field.get("region_id")
        if (
            source_scan.get("scope") != "projected_region_crop"
            or field_id not in (source_scan.get("field_ids") or [])
            or field_region not in (source_scan.get("region_ids") or [])
        ):
            fail(f"aggregate {aggregate_id} is not bound to its projected field region")
        all_scan_raw_ids = {
            raw_id for raw_id, item in raw_text.items() if item.get("scan_id") == source_scan_id
        }
        if set(component_ids) != all_scan_raw_ids:
            fail(f"aggregate {aggregate_id} hides or omits raw crop text")
        try:
            replay_text, replay_lines = post_adapter.ordered_line_aggregation(
                components, str(field.get("line_joiner")),
            )
            replay_ids = [
                [str(item["raw_observation_id"]) for item in line]
                for line in replay_lines
            ]
        except Exception as exc:
            fail(f"aggregate {aggregate_id} installed reading-order replay failed: {exc}")
            continue
        if (
            replay_ids != lines
            or aggregate.get("text") != replay_text
            or aggregate.get("observed_hash") != sha256_text(replay_text)
            or aggregate.get("observed_hash") != field.get("expected_text_sha256")
            or aggregation.get("aggregate_text_sha256") != aggregate.get("observed_hash")
        ):
            fail(f"aggregate {aggregate_id} replay/hash contradicts raw fragments")
        if aggregate.get("full_master_bounding_box_normalized") != post_adapter.union_normalized_boxes([
            item.get("full_master_bounding_box_normalized") for item in components
        ]):
            fail(f"aggregate {aggregate_id} full-master bounding box is not component-derived")
        for component in components:
            if component.get("consumed_by_aggregate_raw_observation_id") != aggregate_id:
                fail(f"aggregate {aggregate_id} component lacks reciprocal consumption binding")

    observations = evidence.get("observations")
    observation_by_id: dict[str, dict[str, Any]] = {}
    field_owners: dict[str, str] = {}
    raw_single_owners: dict[str, int] = {}
    aggregate_owners: dict[str, int] = {}
    if not isinstance(observations, list):
        fail("canonical OCR observations must be an array")
        observations = []
    for observation in observations:
        observation_id = observation.get("observation_id") if isinstance(observation, dict) else None
        if not isinstance(observation_id, str) or not observation_id or observation_id in observation_by_id:
            fail("canonical OCR observation IDs must be unique and non-empty")
            continue
        observation_by_id[observation_id] = observation
        field_id = observation.get("field_id")
        if not isinstance(field_id, str) or field_id not in expected_field_ids or field_id in field_owners:
            fail(f"canonical OCR observation {observation_id} has missing/duplicate/unexpected field")
            continue
        field_owners[field_id] = observation_id
        field = text_fields.get(field_id, {})
        if (
            observation.get("text") != field.get("expected_raw_text")
            or observation.get("text_sha256") != field.get("expected_text_sha256")
            or observation.get("ocr_match_policy") != field.get("ocr_match_policy")
            or observation.get("product_native") is not True
            or observation.get("disposition") != "mapped_to_expected_field"
            or observation.get("review_status") != "reviewed"
        ):
            fail(f"canonical OCR observation {observation_id} exact field contract failed")
        raw_ids = observation.get("raw_observation_ids")
        if (
            not isinstance(raw_ids, list) or not raw_ids
            or any(not isinstance(raw_id, str) or not raw_id for raw_id in raw_ids)
            or len(raw_ids) != len(set(raw_ids))
        ):
            fail(f"canonical OCR observation {observation_id} raw IDs are invalid")
            continue
        if field.get("ocr_match_policy") == "ordered_line_aggregation_exact":
            aggregate_ids = [raw_id for raw_id in raw_ids if raw_id in aggregate_by_id]
            if len(aggregate_ids) != 1:
                fail(f"canonical aggregate field {field_id} must consume exactly one aggregate")
                continue
            aggregate_id = aggregate_ids[0]
            aggregate_owners[aggregate_id] = aggregate_owners.get(aggregate_id, 0) + 1
            aggregate = aggregate_by_id[aggregate_id]
            duplicate_raw_ids = [raw_id for raw_id in raw_ids if raw_id != aggregate_id]
            if any(
                raw_id not in raw_text
                or raw_text[raw_id].get("consumed_by_aggregate_raw_observation_id") != aggregate_id
                for raw_id in duplicate_raw_ids
            ):
                fail(f"canonical aggregate field {field_id} names unbound duplicate raw evidence")
            if (
                observation.get("aggregation") != aggregate.get("aggregation")
                or observation.get("text") != aggregate.get("text")
                or observation.get("mapping_basis") != "ordered_bbox_line_aggregation_exact_utf8_hash_one_to_one"
            ):
                fail(f"canonical aggregate field {field_id} differs from raw aggregate evidence")
        elif field.get("ocr_match_policy") == "single_observation_exact":
            if observation.get("aggregation") is not None or observation.get("mapping_basis") != "single_observation_exact_utf8_hash_one_to_one":
                fail(f"canonical single observation field {field_id} uses the wrong mapping policy")
            if any(raw_id not in raw_text for raw_id in raw_ids):
                fail(f"canonical single observation field {field_id} references unknown raw text")
                continue
            representative = raw_text[raw_ids[0]]
            for raw_id in raw_ids:
                raw = raw_text[raw_id]
                raw_single_owners[raw_id] = raw_single_owners.get(raw_id, 0) + 1
                if (
                    raw.get("consumed_by_aggregate_raw_observation_id") is not None
                    or raw.get("observed_hash") != field.get("expected_text_sha256")
                    or field_id not in (raw.get("candidate_ids") or [])
                    or post_adapter.intersection_over_min_area(
                        raw.get("full_master_bounding_box_normalized"),
                        representative.get("full_master_bounding_box_normalized"),
                    ) < 0.60
                ):
                    fail(f"canonical single observation field {field_id} has contradictory raw evidence")
        else:
            fail(f"canonical OCR observation {observation_id} uses unknown Text SSOT policy")

    if set(field_owners) != expected_field_ids:
        fail("canonical OCR fields do not exactly cover visible Text SSOT fields")
    for raw_id, raw in raw_text.items():
        owner = raw.get("consumed_by_aggregate_raw_observation_id")
        if isinstance(owner, str):
            aggregate = aggregate_by_id.get(owner)
            if aggregate is None:
                fail(f"raw text {raw_id} names an unknown aggregate owner")
                continue
            component_ids = {
                identifier for line in aggregate.get("aggregation", {}).get("component_raw_observation_ids_by_line", [])
                if isinstance(line, list) for identifier in line if isinstance(identifier, str)
            }
            if raw_id not in component_ids:
                components = [raw_text[item] for item in component_ids if item in raw_text]
                component_duplicate = any(
                    raw.get("observed_hash") == component.get("observed_hash")
                    and post_adapter.intersection_over_min_area(
                        raw.get("full_master_bounding_box_normalized"),
                        component.get("full_master_bounding_box_normalized"),
                    ) >= 0.60
                    for component in components
                )
                aggregate_duplicate = (
                    raw.get("observed_hash") == aggregate.get("observed_hash")
                    and post_adapter.intersection_over_min_area(
                        raw.get("full_master_bounding_box_normalized"),
                        aggregate.get("full_master_bounding_box_normalized"),
                    ) >= 0.60
                )
                if not component_duplicate and not aggregate_duplicate:
                    fail(f"raw text {raw_id} has a contradictory aggregate consumption claim")
        elif raw_single_owners.get(raw_id) != 1:
            fail(f"raw text {raw_id} is extra, missing, duplicated, or unresolved")
    if any(count != 1 for count in aggregate_owners.values()) or set(aggregate_owners) != set(aggregate_by_id):
        fail("aggregate observations are missing, duplicated, or not canonically consumed")
    if evidence.get("unresolved_observation_ids") != []:
        fail("post OCR evidence still contains unresolved observations")
    if evidence.get("missing_field_ids") != [] or evidence.get("missing_code_ids") != []:
        fail("post OCR evidence still reports missing fields or codes")

    raw_codes: dict[str, dict[str, Any]] = {}
    for item in raw_code_values:
        raw_id = item.get("raw_observation_id") if isinstance(item, dict) else None
        payload = item.get("payload") if isinstance(item, dict) else None
        if not isinstance(raw_id, str) or not raw_id or raw_id in raw_codes:
            fail("raw code observation IDs must be unique and non-empty")
            continue
        raw_codes[raw_id] = item
        if (
            not isinstance(payload, str) or not payload
            or item.get("observed_hash") != sha256_text(payload)
            or item.get("scan_id") not in scan_by_id
        ):
            fail(f"raw code observation {raw_id} has invalid payload/hash/scan binding")
        try:
            post_adapter.normalized_box_metrics(item.get("scan_bounding_box_normalized"), raw_id)
            post_adapter.normalized_box_metrics(item.get("full_master_bounding_box_normalized"), raw_id)
        except Exception:
            fail(f"raw code observation {raw_id} has invalid bounding boxes")
    code_observations = evidence.get("code_observations")
    raw_code_owners: dict[str, int] = {}
    observed_code_ids: set[str] = set()
    if not isinstance(code_observations, list):
        fail("canonical code observations must be an array")
        code_observations = []
    for observation in code_observations:
        if not isinstance(observation, dict):
            fail("canonical code observation is malformed")
            continue
        code_id = observation.get("code_id")
        if not isinstance(code_id, str) or code_id not in expected_code_ids or code_id in observed_code_ids:
            fail("canonical code observations contain missing/duplicate/unexpected codes")
            continue
        observed_code_ids.add(code_id)
        raw_ids = observation.get("raw_observation_ids")
        if (
            not isinstance(raw_ids, list) or not raw_ids
            or any(not isinstance(raw_id, str) or not raw_id for raw_id in raw_ids)
            or len(raw_ids) != len(set(raw_ids))
        ):
            fail(f"canonical code {code_id} raw IDs are invalid")
            continue
        for raw_id in raw_ids:
            if raw_id not in raw_codes:
                fail(f"canonical code {code_id} references unknown raw decode")
                continue
            raw = raw_codes[raw_id]
            if (
                code_id not in (raw.get("candidate_ids") or [])
                or raw.get("payload") != observation.get("payload")
                or raw.get("canonical_symbology") != post_adapter.canonical_symbology(
                    str(observation.get("symbology"))
                )
            ):
                fail(f"canonical code {code_id} contradicts raw decode evidence")
            raw_code_owners[raw_id] = raw_code_owners.get(raw_id, 0) + 1
    if observed_code_ids != expected_code_ids:
        fail("canonical code observations do not exactly cover visible codes")
    if set(raw_code_owners) != set(raw_codes) or any(count != 1 for count in raw_code_owners.values()):
        fail("raw code observations are extra, missing, duplicated, or unresolved")
    return passed


def validate_code_decode_receipt(
    receipt: Any,
    *,
    asset: dict[str, Any],
    view_id: str,
    code_id: str,
    code_record: dict[str, Any],
    code_observation: dict[str, Any],
) -> list[str]:
    """Validate a bundled post-code receipt as semantic evidence, not a file token."""
    label = f"post code decode receipt {view_id}/{code_id}"
    if not isinstance(receipt, dict):
        return [f"{label}: root must be an object"]
    required = {
        "schema_version", "asset_id", "view_id", "asset_file_sha256", "code_id",
        "engine_id", "engine_script_path", "engine_script_sha256", "observation_id",
        "observed_symbology_raw", "canonical_symbology", "payload", "payload_sha256",
        "decode_integrity_status", "decode_integrity_method", "symbol_geometry_status",
        "receipt_sha256",
    }
    errors: list[str] = []
    if set(receipt) != required:
        errors.append(f"{label}: fields differ from packaging-post-code-decode-receipt.v1")
    expected_script = SKILL_DIR / "scripts/macos_vision_ocr.swift"
    expected_payload = str(code_record.get("expected_payload"))
    if (
        receipt.get("schema_version") != "packaging-post-code-decode-receipt.v1"
        or receipt.get("receipt_sha256") != canonical_hash(receipt, "receipt_sha256")
        or receipt.get("asset_id") != asset.get("asset_id")
        or receipt.get("view_id") != view_id
        or receipt.get("asset_file_sha256") != asset.get("file_sha256")
        or receipt.get("code_id") != code_id
        or receipt.get("engine_id") != "bundled_macos_vision_ocr"
        or receipt.get("engine_script_path") != "scripts/macos_vision_ocr.swift"
        or not expected_script.is_file()
        or receipt.get("engine_script_sha256") != sha256_file(expected_script)
        or receipt.get("observation_id") != code_observation.get("observation_id")
        or receipt.get("observed_symbology_raw") != code_observation.get("observed_symbology_raw")
        or receipt.get("canonical_symbology") != code_record.get("symbology")
        or receipt.get("payload") != expected_payload
        or receipt.get("payload_sha256") != sha256_text(expected_payload)
        or receipt.get("decode_integrity_status") != "passed"
        or receipt.get("decode_integrity_status") != code_observation.get("decode_integrity_status")
        or not isinstance(receipt.get("decode_integrity_method"), str)
        or not receipt.get("decode_integrity_method")
        or receipt.get("decode_integrity_method") != code_observation.get("decode_integrity_method")
        or receipt.get("symbol_geometry_status") != "matched"
    ):
        errors.append(f"{label}: semantic payload/engine/integrity/geometry binding failed")
    return errors


def validate_complete(
    root: Path,
    manifest: dict[str, Any],
    required_views: set[str],
    ring_sequences: list[list[str]],
    coverage_views: dict[str, dict[str, Any]],
    prompt_records: dict[str, dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    text_fields: dict[str, dict[str, Any]],
    code_records: dict[str, dict[str, Any]],
    graphic_records: dict[str, dict[str, Any]],
    composition_plan: dict[str, Any],
    errors: list[str],
) -> None:
    asset_qa = load_locked_json(root, manifest, "asset_qa", "asset_qa_sha256", errors)
    continuity_qa = load_locked_json(root, manifest, "continuity_qa", "continuity_qa_sha256", errors)
    post = load_locked_json(root, manifest, "post_composite_verification", "post_composite_verification_sha256", errors)
    asset_by_view: dict[str, dict[str, Any]] = {}
    if asset_qa:
        if asset_qa.get("schema_version") != "packaging-asset-qa.v1":
            errors.append("asset_qa: invalid schema_version")
        assets = asset_qa.get("assets")
        if not isinstance(assets, list):
            errors.append("asset_qa: assets must be an array")
        else:
            asset_ids: set[str] = set()
            asset_paths: set[str] = set()
            asset_hashes: set[str] = set()
            raw_paths: set[str] = set()
            raw_hashes: set[str] = set()
            worker_threads: set[str] = set()
            worker_turns: set[str] = set()
            worker_calls: set[str] = set()
            for index, asset in enumerate(assets):
                label = f"asset_qa.assets[{index}]"
                if not isinstance(asset, dict) or not isinstance(asset.get("view_id"), str):
                    errors.append(f"{label}: invalid asset record")
                    continue
                view_id = asset["view_id"]
                if view_id in asset_by_view:
                    errors.append(f"{label}: duplicate view_id")
                asset_by_view[view_id] = asset
                asset_id = asset.get("asset_id")
                if not isinstance(asset_id, str) or not asset_id or asset_id in asset_ids:
                    errors.append(f"{label}: asset_id must be unique and non-empty")
                else:
                    asset_ids.add(asset_id)
                prompt = prompt_records.get(view_id, {})
                if asset_id != prompt.get("asset_id"):
                    errors.append(f"{label}: asset_id does not match generation prompt")
                if asset.get("family") != coverage_views.get(view_id, {}).get("family"):
                    errors.append(f"{label}: family does not match coverage")
                if asset.get("generation_prompt_sha256") != prompt.get("prompt_sha256"):
                    errors.append(f"{label}: generation prompt hash is not bound")
                if asset.get("independently_generated") is not True or asset.get("derived_from_multipanel") is not False:
                    errors.append(f"asset_qa {view_id}: machine master must be independent, never a panel crop")
                if asset.get("assistant_qa_status") != "passed":
                    errors.append(f"asset_qa {view_id}: assistant QA did not pass")
                if asset.get("text_pollution_status") != "passed" or asset.get("copy_composition_status") != "passed" or asset.get("post_verification_status") != "passed":
                    errors.append(f"asset_qa {view_id}: copy pipeline did not pass")
                locator = asset.get("file_path")
                path, path_errors = safe_run_path(root, locator, f"asset_qa {view_id}")
                errors.extend(path_errors)
                if isinstance(locator, str) and locator in asset_paths:
                    errors.append(f"asset_qa {view_id}: master file_path must be unique")
                elif isinstance(locator, str):
                    asset_paths.add(locator)
                if path:
                    actual_hash = sha256_file(path)
                    if asset.get("file_sha256") != actual_hash:
                        errors.append(f"asset_qa {view_id}: asset file/hash invalid")
                    if actual_hash in asset_hashes:
                        errors.append(f"asset_qa {view_id}: different required views cannot reuse identical master bytes")
                    asset_hashes.add(actual_hash)
                    final_dimensions: tuple[int, int] | None = None
                    try:
                        width, height = verify_image(path)
                        final_dimensions = (width, height)
                        if width * 9 != height * 16 or width <= height:
                            errors.append(f"asset_qa {view_id}: master must be a decoded horizontal exact 16:9 image")
                        if width < MIN_MACHINE_MASTER_WIDTH_PX or height < MIN_MACHINE_MASTER_HEIGHT_PX:
                            errors.append(
                                f"asset_qa {view_id}: master is below the minimum native delivery resolution "
                                f"{MIN_MACHINE_MASTER_WIDTH_PX}x{MIN_MACHINE_MASTER_HEIGHT_PX}"
                            )
                        if not verify_nontrivial_image(path):
                            errors.append(f"asset_qa {view_id}: master is blank/near-uniform and cannot prove product identity")
                    except Exception as exc:
                        errors.append(f"asset_qa {view_id}: master image verification failed: {exc}")
                raw_locator = asset.get("raw_file_path")
                raw_path, raw_path_errors = safe_run_path(root, raw_locator, f"asset_qa {view_id} raw master")
                errors.extend(raw_path_errors)
                if isinstance(raw_locator, str) and raw_locator in raw_paths:
                    errors.append(f"asset_qa {view_id}: raw master file_path must be unique")
                elif isinstance(raw_locator, str):
                    raw_paths.add(raw_locator)
                if raw_path:
                    raw_hash = sha256_file(raw_path)
                    if asset.get("raw_file_sha256") != raw_hash:
                        errors.append(f"asset_qa {view_id}: raw master file/hash invalid")
                    if raw_hash in raw_hashes:
                        errors.append(f"asset_qa {view_id}: different required views cannot reuse identical raw master bytes")
                    raw_hashes.add(raw_hash)
                    raw_dimensions: tuple[int, int] | None = None
                    try:
                        raw_width, raw_height = verify_image(raw_path)
                        raw_dimensions = (raw_width, raw_height)
                        if raw_width * 9 != raw_height * 16 or raw_width <= raw_height:
                            errors.append(f"asset_qa {view_id}: raw master must be decoded horizontal exact 16:9")
                        if raw_width < MIN_MACHINE_MASTER_WIDTH_PX or raw_height < MIN_MACHINE_MASTER_HEIGHT_PX:
                            errors.append(
                                f"asset_qa {view_id}: raw master is below the minimum native delivery resolution "
                                f"{MIN_MACHINE_MASTER_WIDTH_PX}x{MIN_MACHINE_MASTER_HEIGHT_PX}"
                            )
                        if not verify_nontrivial_image(raw_path):
                            errors.append(f"asset_qa {view_id}: raw master is blank/near-uniform")
                    except Exception as exc:
                        errors.append(f"asset_qa {view_id}: raw master image verification failed: {exc}")
                    visible_exact = bool(
                        coverage_views.get(view_id, {}).get("ocr_field_ids_visible")
                        or coverage_views.get(view_id, {}).get("code_ids_visible")
                        or coverage_views.get(view_id, {}).get("graphic_ids_visible")
                    )
                    if visible_exact and raw_hash == asset.get("file_sha256"):
                        errors.append(f"asset_qa {view_id}: exact-copy final must differ from raw generated bytes")
                    if raw_dimensions is not None and final_dimensions is not None and raw_dimensions != final_dimensions:
                        errors.append(f"asset_qa {view_id}: deterministic exact-copy composition must preserve master dimensions")
                receipt = load_evidence_json(
                    root,
                    asset.get("generation_receipt_path"),
                    asset.get("generation_receipt_sha256"),
                    f"asset_qa {view_id} generation receipt",
                    errors,
                )
                if receipt:
                    if receipt.get("schema_version") != "packaging-generation-receipt.v2":
                        errors.append(f"asset_qa {view_id}: invalid generation receipt schema")
                    receipt_dimensions_invalid = (
                        raw_dimensions is None
                        or receipt.get("output_pixel_dimensions") != {
                            "width": raw_dimensions[0], "height": raw_dimensions[1]
                        }
                    )
                    if (
                        receipt.get("asset_id") != asset_id
                        or receipt.get("view_id") != view_id
                        or receipt.get("prompt_sha256") != prompt.get("prompt_sha256")
                        or receipt.get("output_file_sha256") != asset.get("raw_file_sha256")
                        or receipt.get("output_path") != asset.get("raw_file_path")
                        or receipt.get("generation_mode") != "independent_full_frame"
                        or receipt.get("worker_transport_mode") != "delegated_single_image_worker"
                        or receipt_dimensions_invalid
                        or receipt.get("post_generation_resize_applied") is not False
                        or set(receipt.get("reference_ids") or []) != set(coverage_views.get(view_id, {}).get("source_refs") or [])
                    ):
                        errors.append(f"asset_qa {view_id}: generation receipt does not bind prompt/output/references")
                    coverage_view = coverage_views.get(view_id, {})
                    expected_bindings: list[dict[str, Any]] = []
                    for source_id in coverage_view.get("source_refs") or []:
                        source = sources.get(source_id, {})
                        expected_bindings.append({
                            "role": "source_reference",
                            "reference_id": source_id,
                            "source_id": source_id,
                            "locator": source.get("file_path"),
                            "file_sha256": source.get("file_sha256"),
                        })
                    for parent_view_id in coverage_view.get("parent_anchor_view_ids") or []:
                        matches = [
                            (source_id, sources[source_id])
                            for source_id in coverage_view.get("source_refs") or []
                            if source_id in sources and sources[source_id].get("view_id") == parent_view_id
                        ]
                        if len(matches) != 1:
                            errors.append(f"asset_qa {view_id}: parent anchor {parent_view_id} lacks one attached source asset")
                            continue
                        source_id, source = matches[0]
                        expected_bindings.append({
                            "role": "parent_anchor",
                            "reference_id": parent_view_id,
                            "source_id": source_id,
                            "locator": source.get("file_path"),
                            "file_sha256": source.get("file_sha256"),
                        })
                    actual_bindings = receipt.get("source_reference_bindings")
                    binding_sort = lambda item: (
                        str(item.get("role")), str(item.get("reference_id")), str(item.get("source_id"))
                    )
                    expected_bindings = sorted(expected_bindings, key=binding_sort)
                    if not isinstance(actual_bindings, list) or sorted(actual_bindings, key=binding_sort) != expected_bindings:
                        errors.append(f"asset_qa {view_id}: generation receipt does not bind actual submitted reference files")
                    else:
                        binding_payload = json.dumps(
                            expected_bindings, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":"), allow_nan=False,
                        )
                    provenance = receipt.get("worker_provenance")
                    if not isinstance(provenance, dict):
                        errors.append(f"asset_qa {view_id}: generation receipt lacks worker provenance")
                    else:
                        worker_result = load_evidence_json(
                            root,
                            provenance.get("result_path"),
                            provenance.get("result_sha256"),
                            f"asset_qa {view_id} worker result",
                            errors,
                        )
                        required_worker_ids = {
                            "worker_thread_id": worker_threads,
                            "worker_turn_id": worker_turns,
                            "image_generation_call_id": worker_calls,
                        }
                        for key, seen in required_worker_ids.items():
                            value = provenance.get(key)
                            if not isinstance(value, str) or not value:
                                errors.append(f"asset_qa {view_id}: worker provenance missing {key}")
                            elif value in seen:
                                errors.append(f"asset_qa {view_id}: worker provenance reuses {key}")
                            else:
                                seen.add(value)
                        agent_path = provenance.get("agent_path")
                        if not isinstance(agent_path, str) or re.search(r"_[0-9a-f]{32}$", agent_path) is None:
                            errors.append(f"asset_qa {view_id}: worker agent path lacks complete nonce suffix")
                        reference_manifest = load_evidence_json(
                            root,
                            provenance.get("reference_manifest_path"),
                            provenance.get("reference_manifest_sha256"),
                            f"asset_qa {view_id} worker reference manifest",
                            errors,
                        )
                        if worker_result:
                            expected_worker_fields = {
                                "contract": "delegated_image_worker_result.v1",
                                "agent_path": provenance.get("agent_path"),
                                "worker_thread_id": provenance.get("worker_thread_id"),
                                "worker_turn_id": provenance.get("worker_turn_id"),
                                "parent_thread_id": provenance.get("parent_thread_id"),
                                "image_generation_call_id": provenance.get("image_generation_call_id"),
                                "prompt_binding_mode": provenance.get("prompt_binding_mode"),
                                "reference_manifest_sha256": provenance.get("reference_manifest_sha256"),
                                "ordered_reference_bundle_sha256": provenance.get("ordered_reference_bundle_sha256"),
                                "generation_prompt_sha256": prompt.get("prompt_sha256"),
                                "tool_prompt_sha256": prompt.get("prompt_sha256"),
                                "image_sha256": asset.get("raw_file_sha256"),
                            }
                            if worker_result.get("ok") is not True or any(
                                worker_result.get(key) != value for key, value in expected_worker_fields.items()
                            ):
                                errors.append(f"asset_qa {view_id}: worker result does not bind provenance/prompt/image")
                            if worker_result.get("prompt_sha_match") is not True:
                                errors.append(f"asset_qa {view_id}: worker prompt-byte binding did not pass")
                            if not path_ends_with_run_locator(worker_result.get("run_image_path"), raw_locator):
                                errors.append(f"asset_qa {view_id}: worker result raw-master locator mismatch")
                        if reference_manifest:
                            if reference_manifest.get("schema_version") != "packaging_reference_bundle.v1":
                                errors.append(f"asset_qa {view_id}: invalid worker reference manifest schema")
                            entries = reference_manifest.get("ordered_references")
                            if not isinstance(entries, list):
                                errors.append(f"asset_qa {view_id}: worker reference manifest entries invalid")
                            else:
                                submitted = receipt.get("submitted_reference_bindings")
                                expected_submitted: list[dict[str, Any]] = []
                                source_ids = coverage_views.get(view_id, {}).get("source_refs") or []
                                submitted_shape_valid = (
                                    isinstance(submitted, list)
                                    and len(submitted) == len(source_ids)
                                    and all(isinstance(item, dict) for item in submitted)
                                )
                                if not submitted_shape_valid:
                                    errors.append(
                                        f"asset_qa {view_id}: submitted frozen references do not match manifest bytes"
                                    )
                                manifest_payload = json.dumps(
                                    entries,
                                    ensure_ascii=False,
                                    sort_keys=True,
                                    separators=(",", ":"),
                                    allow_nan=False,
                                )
                                if reference_manifest.get("ordered_bundle_sha256") != sha256_text(manifest_payload):
                                    errors.append(f"asset_qa {view_id}: worker reference manifest self-hash mismatch")
                                for rank, (entry, source_id) in enumerate(zip(entries, source_ids), 1):
                                    submitted_item = (
                                        submitted[rank - 1]
                                        if isinstance(submitted, list)
                                        and len(submitted) >= rank
                                        and isinstance(submitted[rank - 1], dict)
                                        else {}
                                    )
                                    frozen_locator = submitted_item.get("frozen_path")
                                    frozen_path, frozen_errors = safe_run_path(
                                        root,
                                        frozen_locator,
                                        f"asset_qa {view_id} frozen worker reference {rank}",
                                    )
                                    errors.extend(frozen_errors)
                                    if not path_ends_with_run_locator(entry.get("frozen_path"), frozen_locator):
                                        errors.append(
                                            f"asset_qa {view_id} frozen worker reference {rank}: historical locator mismatch"
                                        )
                                    if frozen_path is not None:
                                        expected_submitted.append({
                                            "rank": rank,
                                            "reference_id": source_id,
                                            "frozen_path": str(frozen_path.relative_to(root)).replace("\\", "/"),
                                            "file_sha256": sha256_file(frozen_path),
                                        })
                                        if (
                                            entry.get("index") != rank
                                            or entry.get("alias") != source_id
                                            or entry.get("size_bytes") != frozen_path.stat().st_size
                                            or entry.get("sha256") != expected_submitted[-1]["file_sha256"]
                                        ):
                                            errors.append(
                                                f"asset_qa {view_id} frozen worker reference {rank}: bytes/order metadata mismatch"
                                            )
                                if len(entries) != len(source_ids) or [item.get("alias") for item in entries] != source_ids:
                                    errors.append(f"asset_qa {view_id}: frozen references do not preserve coverage order")
                                if submitted_shape_valid and submitted != expected_submitted:
                                    errors.append(f"asset_qa {view_id}: submitted frozen references do not match manifest bytes")
                                binding_payload = json.dumps(
                                    expected_submitted,
                                    ensure_ascii=False,
                                    sort_keys=True,
                                    separators=(",", ":"),
                                    allow_nan=False,
                                )
                                if receipt.get("submitted_reference_set_sha256") != sha256_text(binding_payload):
                                    errors.append(f"asset_qa {view_id}: submitted reference set self-hash mismatch")
            if set(asset_by_view) != required_views:
                errors.append("asset_qa: approved assets must exactly cover required views")
        boards = asset_qa.get("review_boards")
        if not isinstance(boards, list) or not boards:
            errors.append("asset_qa: at least one deterministic review board is required")
        else:
            qa_board_views: set[str] = set()
            ordered_views_by_role: dict[str, list[str]] = {}
            for index, board in enumerate(boards):
                label = f"asset_qa.review_boards[{index}]"
                if not isinstance(board, dict) or board.get("derivation_mode") != "deterministic_composite":
                    errors.append(f"asset_qa.review_boards[{index}]: must be deterministic_composite")
                    continue
                board_path, board_path_errors = safe_run_path(root, board.get("file_path"), label)
                errors.extend(board_path_errors)
                if board_path:
                    if board.get("file_sha256") != sha256_file(board_path):
                        errors.append(f"{label}: file hash mismatch")
                    try:
                        width, height = verify_image(board_path)
                        if width * 9 != height * 16 or width < 3840 or height < 2160:
                            errors.append(f"{label}: review board must be exact 16:9 at no less than 3840x2160")
                    except Exception as exc:
                        errors.append(f"{label}: board image verification failed: {exc}")
                inputs = board.get("inputs")
                if not isinstance(inputs, list) or not inputs:
                    errors.append(f"{label}: inputs must be a non-empty master list")
                    continue
                input_views: list[str] = []
                for input_index, item in enumerate(inputs):
                    if not isinstance(item, dict):
                        errors.append(f"{label}.inputs[{input_index}]: invalid record")
                        continue
                    view_id = item.get("view_id")
                    asset = asset_by_view.get(view_id)
                    if asset is None or any(
                        item.get(key) != asset.get(key) for key in ("asset_id", "file_path", "file_sha256")
                    ):
                        errors.append(f"{label}.inputs[{input_index}]: does not match an approved master")
                        continue
                    input_views.append(view_id)
                if len(input_views) != len(set(input_views)):
                    errors.append(f"{label}: duplicate input view")
                semantic_roles = {
                    board_semantic_role_for_view(view_id, coverage_views.get(view_id, {}))
                    for view_id in input_views
                }
                declared_semantic_role = board.get("semantic_board_role")
                if (
                    len(semantic_roles) != 1
                    or declared_semantic_role not in REVIEW_BOARD_ROLES
                    or semantic_roles != {declared_semantic_role}
                ):
                    errors.append(f"{label}: inputs must share the declared semantic_board_role")
                if board.get("ordered_view_ids") != input_views:
                    errors.append(f"{label}: ordered_view_ids must exactly preserve input order")
                expected_local_order = sorted(
                    input_views,
                    key=lambda item: semantic_board_order_key(item, coverage_views.get(item, {})),
                )
                if input_views != expected_local_order:
                    errors.append(f"{label}: semantic board inputs are not in canonical order")
                capacity = 4 if declared_semantic_role in {"copy", "code", "structure", "material"} else 6
                if len(input_views) > capacity:
                    errors.append(f"{label}: board exceeds family capacity {capacity}")
                if board.get("role") == "human_review_qa_board":
                    duplicate_views = qa_board_views.intersection(input_views)
                    if duplicate_views:
                        errors.append(f"{label}: masters repeat across QA boards")
                    qa_board_views.update(input_views)
                    if declared_semantic_role in REVIEW_BOARD_ROLES:
                        ordered_views_by_role.setdefault(declared_semantic_role, []).extend(input_views)
                elif board.get("role") != "review_only_no_qa_authority":
                    errors.append(f"{label}: invalid board role")
            if qa_board_views != required_views:
                errors.append("asset_qa: human review boards must cover every approved master exactly once")
            required_by_role: dict[str, list[str]] = {}
            for view_id in required_views:
                role = board_semantic_role_for_view(view_id, coverage_views.get(view_id, {}))
                if role in REVIEW_BOARD_ROLES:
                    required_by_role.setdefault(role, []).append(view_id)
            for role, view_ids in required_by_role.items():
                expected_order = sorted(
                    view_ids,
                    key=lambda item: semantic_board_order_key(item, coverage_views.get(item, {})),
                )
                if ordered_views_by_role.get(role) != expected_order:
                    errors.append(f"asset_qa: {role} QA boards must form one complete canonical ordered sequence")
    if continuity_qa:
        validate_continuity_qa_v2(
            root, manifest, continuity_qa, asset_by_view, coverage_views, ring_sequences, errors,
        )
    if post:
        if post.get("schema_version") != "packaging-post-composite-verification.v1":
            errors.append("post_composite_verification: invalid schema_version")
        post_adapter_path = Path(__file__).resolve().with_name("run_post_composite_verification.py")
        post_adapter_sha = sha256_file(post_adapter_path) if post_adapter_path.is_file() else None
        post_adapter = None
        try:
            post_adapter = load_bundled_module(
                post_adapter_path, "packaging_post_composite_validator_adapter",
            )
        except Exception as exc:
            errors.append(f"post_composite_verification: installed adapter failed to load: {exc}")
        provenance = post.get("candidate_provenance")
        if not isinstance(provenance, dict) or (
            provenance.get("adapter_path") != "scripts/run_post_composite_verification.py"
            or provenance.get("adapter_sha256") != post_adapter_sha
            or provenance.get("engine_id") != "bundled_macos_vision_ocr"
            or provenance.get("engine_script_path") != "scripts/macos_vision_ocr.swift"
            or provenance.get("engine_script_sha256") != sha256_file(SKILL_DIR / "scripts/macos_vision_ocr.swift")
            or provenance.get("uses_language_correction") is not False
        ):
            errors.append("post_composite_verification: candidate provenance does not bind the installed adapter")
        results = post.get("asset_results")
        result_by_view = {
            item.get("view_id"): item for item in results
            if isinstance(item, dict) and isinstance(item.get("view_id"), str)
        } if isinstance(results, list) else {}
        if set(result_by_view) != required_views:
            errors.append("post_composite_verification: asset_results must exactly cover required masters")
        post_all_passed = True
        for view_id, result in result_by_view.items():
            asset = asset_by_view.get(view_id, {})
            prompt = prompt_records.get(view_id, {})
            if result.get("asset_id") != asset.get("asset_id") or result.get("asset_file_sha256") != asset.get("file_sha256"):
                errors.append(f"post_composite_verification {view_id}: asset binding mismatch")
                post_all_passed = False
            receipt = load_evidence_json(
                root, result.get("composition_receipt_path"), result.get("composition_receipt_sha256"),
                f"post_composite_verification {view_id} composition receipt", errors,
            )
            compositor_path = Path(__file__).resolve().with_name("compose_exact_copy.py")
            expected_compositor_sha = sha256_file(compositor_path) if compositor_path.is_file() else None
            composition_job = None
            if receipt:
                composition_job = load_evidence_json(
                    root, receipt.get("composition_job_path"), receipt.get("composition_job_sha256"),
                    f"post_composite_verification {view_id} composition job", errors,
                )
            plan_by_view = {
                item.get("view_id"): item for item in composition_plan.get("view_statuses", [])
                if isinstance(item, dict) and isinstance(item.get("view_id"), str)
            }
            plan_record = plan_by_view.get(view_id, {})
            composition_failed = not receipt or (
                receipt.get("schema_version") != "packaging-composition-receipt.v1"
                or receipt.get("receipt_sha256") != canonical_hash(receipt, "receipt_sha256")
                or receipt.get("asset_id") != asset.get("asset_id")
                or receipt.get("view_id") != view_id
                or receipt.get("output_file_sha256") != asset.get("file_sha256")
                or receipt.get("prompt_sha256") != prompt.get("prompt_sha256")
                or receipt.get("composition_plan_id") != composition_plan.get("plan_id")
                or receipt.get("composition_plan_sha256") != manifest["hashes"].get("composition_plan_sha256")
                or receipt.get("exact_copy_bundle_sha256") != manifest["hashes"].get("exact_copy_bundle_sha256")
                or receipt.get("replay_status") != "byte_identical"
                or not isinstance(receipt.get("source_layer_sha256s"), list)
                or not receipt.get("source_layer_sha256s")
                or receipt.get("compositor_script_sha256") != expected_compositor_sha
                or not composition_job
                or composition_job.get("schema_version") != "packaging-exact-copy-composition-job.v1"
                or composition_job.get("job_sha256") != canonical_hash(composition_job, "job_sha256")
                or composition_job.get("asset_id") != asset.get("asset_id")
                or composition_job.get("view_id") != view_id
                or composition_job.get("prompt_sha256") != prompt.get("prompt_sha256")
                or composition_job.get("composition_plan_id") != composition_plan.get("plan_id")
                or composition_job.get("composition_plan_sha256") != manifest["hashes"].get("composition_plan_sha256")
                or composition_job.get("exact_copy_bundle_sha256") != manifest["hashes"].get("exact_copy_bundle_sha256")
                or composition_job.get("output_path") != asset.get("file_path")
                or composition_job.get("receipt_path") != result.get("composition_receipt_path")
                or not isinstance(composition_job.get("base_asset"), dict)
                or composition_job.get("base_asset", {}).get("path") != asset.get("raw_file_path")
                or composition_job.get("base_asset", {}).get("file_sha256") != asset.get("raw_file_sha256")
                or contains_forbidden_test_marker(composition_job)
                or contains_forbidden_test_marker(receipt)
            )
            layers = composition_job.get("layers") if isinstance(composition_job, dict) else None
            expected_fields_for_view = set(coverage_views.get(view_id, {}).get("ocr_field_ids_visible") or [])
            expected_codes_for_view = set(coverage_views.get(view_id, {}).get("code_ids_visible") or [])
            expected_graphics_for_view = set(coverage_views.get(view_id, {}).get("graphic_ids_visible") or [])
            observed_layer_fields: set[str] = set()
            observed_layer_codes: set[str] = set()
            observed_layer_graphics: set[str] = set()
            observed_layer_regions: set[str] = set()
            source_layer_hashes: list[str] = []
            job_layer_ids: set[str] = set()
            job_source_layer_ids: set[str] = set()
            if not isinstance(layers, list) or not layers:
                composition_failed = True
            else:
                layer_ids: set[str] = set()
                for layer_index, layer in enumerate(layers):
                    if not isinstance(layer, dict):
                        composition_failed = True
                        continue
                    layer_id = layer.get("layer_id")
                    if not isinstance(layer_id, str) or not layer_id or layer_id in layer_ids:
                        composition_failed = True
                    else:
                        layer_ids.add(layer_id)
                        job_layer_ids.add(layer_id)
                    source_layer_id = layer.get("source_layer_id")
                    if not isinstance(source_layer_id, str) or not source_layer_id:
                        composition_failed = True
                    else:
                        job_source_layer_ids.add(source_layer_id)
                    if layer.get("projection_model") != plan_record.get("projection_model") or layer.get("projection_model") not in EXECUTABLE_PROJECTION_MODELS:
                        composition_failed = True
                    source_sha = layer.get("source_sha256")
                    if not isinstance(source_sha, str):
                        composition_failed = True
                    else:
                        source_layer_hashes.append(source_sha)
                    layer_fields = set(layer.get("field_ids") or [])
                    layer_codes = set(layer.get("code_ids") or [])
                    layer_graphics = set(layer.get("graphic_ids") or [])
                    layer_regions = set(layer.get("region_ids") or [])
                    observed_layer_fields.update(layer_fields)
                    observed_layer_codes.update(layer_codes)
                    observed_layer_graphics.update(layer_graphics)
                    observed_layer_regions.update(layer_regions)
                    for field_id in layer_fields:
                        field = text_fields.get(field_id, {})
                        if source_sha != field.get("authority_asset_sha256") or field.get("region_id") not in layer_regions:
                            composition_failed = True
                    for code_id in layer_codes:
                        code = code_records.get(code_id, {})
                        if source_sha != code.get("printed_symbol_asset_sha256"):
                            composition_failed = True
                    for graphic_id in layer_graphics:
                        graphic = graphic_records.get(graphic_id, {})
                        if source_sha != graphic.get("asset_sha256"):
                            composition_failed = True
            if (
                observed_layer_fields != expected_fields_for_view
                or observed_layer_codes != expected_codes_for_view
                or observed_layer_graphics != expected_graphics_for_view
                or not set(coverage_views.get(view_id, {}).get("label_region_ids") or []).issubset(observed_layer_regions)
                or len(job_source_layer_ids) != len(layers or [])
                or job_source_layer_ids != set(plan_record.get("source_layer_ids") or [])
                or (receipt and receipt.get("source_layer_sha256s") != source_layer_hashes)
            ):
                composition_failed = True
            if not composition_failed and composition_job:
                try:
                    compositor = load_bundled_module(compositor_path, "packaging_exact_copy_compositor_validator")
                    replay_image, replay_source_hashes = compositor.render_job(root, composition_job)
                    replay_bytes = compositor.png_bytes(replay_image)
                    output_path, output_path_errors = safe_run_path(root, asset.get("file_path"), f"post_composite_verification {view_id} replay output")
                    errors.extend(output_path_errors)
                    if output_path is None or output_path.read_bytes() != replay_bytes or replay_source_hashes != source_layer_hashes:
                        composition_failed = True
                except Exception as exc:
                    errors.append(f"post_composite_verification {view_id}: deterministic compositor replay failed: {exc}")
                    composition_failed = True
            if composition_failed:
                errors.append(f"post_composite_verification {view_id}: deterministic composition receipt failed")
                post_all_passed = False
            ocr_evidence = load_evidence_json(
                root, result.get("post_ocr_evidence_path"), result.get("post_ocr_evidence_sha256"),
                f"post_composite_verification {view_id} OCR evidence", errors,
            )
            ocr_observations: dict[str, dict[str, Any]] = {}
            expected_post_ocr_script = SKILL_DIR / "scripts/macos_vision_ocr.swift"
            if not ocr_evidence or (
                ocr_evidence.get("schema_version") != "packaging-post-ocr-evidence.v1"
                or ocr_evidence.get("asset_id") != asset.get("asset_id")
                or ocr_evidence.get("asset_file_sha256") != asset.get("file_sha256")
                or ocr_evidence.get("uses_language_correction") is not False
                or ocr_evidence.get("review_status") != "reviewed"
                or ocr_evidence.get("engine_id") != "bundled_macos_vision_ocr"
                or not isinstance(ocr_evidence.get("engine_version"), str)
                or not ocr_evidence.get("engine_version")
                or ocr_evidence.get("engine_script_path") != "scripts/macos_vision_ocr.swift"
                or ocr_evidence.get("engine_script_sha256") != sha256_file(expected_post_ocr_script)
                or contains_forbidden_test_marker(ocr_evidence)
            ):
                errors.append(f"post_composite_verification {view_id}: post OCR evidence failed")
                post_all_passed = False
            else:
                observed = ocr_evidence.get("observations")
                if not isinstance(observed, list):
                    errors.append(f"post_composite_verification {view_id}: OCR observations must be an array")
                else:
                    for item in observed:
                        if not isinstance(item, dict) or not isinstance(item.get("observation_id"), str):
                            errors.append(f"post_composite_verification {view_id}: malformed OCR observation")
                            post_all_passed = False
                            continue
                        observation_id = item["observation_id"]
                        if observation_id in ocr_observations:
                            errors.append(f"post_composite_verification {view_id}: duplicate OCR observation_id")
                            post_all_passed = False
                            continue
                        text = item.get("text")
                        if (
                            not isinstance(text, str)
                            or item.get("text_sha256") != sha256_text(text)
                            or item.get("product_native") is not True
                            or item.get("disposition") != "mapped_to_expected_field"
                        ):
                            errors.append(f"post_composite_verification {view_id}: OCR observation is not exact/disposed")
                            post_all_passed = False
                        ocr_observations[observation_id] = item
                if post_adapter is None or not validate_post_ocr_raw_contract(
                    root, view_id, asset, ocr_evidence,
                    expected_fields_for_view, expected_codes_for_view,
                    text_fields, composition_job or {}, post_adapter, errors,
                ):
                    post_all_passed = False
                if not validate_dynamic_region_pixel_contract(
                    root, view_id, coverage_views.get(view_id, {}), asset,
                    ocr_evidence, errors,
                ):
                    post_all_passed = False
            expected_fields = set(coverage_views.get(view_id, {}).get("ocr_field_ids_visible") or [])
            observed_field_ids = [
                item.get("field_id") for item in ocr_observations.values()
                if isinstance(item.get("field_id"), str)
            ]
            if set(observed_field_ids) != expected_fields or len(observed_field_ids) != len(set(observed_field_ids)):
                errors.append(f"post_composite_verification {view_id}: OCR observations contain missing, duplicate, or unexpected product text")
                post_all_passed = False
            field_results = result.get("field_results")
            field_by_id = {
                item.get("field_id"): item for item in field_results
                if isinstance(item, dict) and isinstance(item.get("field_id"), str)
            } if isinstance(field_results, list) else {}
            if set(field_by_id) != expected_fields or not isinstance(field_results, list) or len(field_results) != len(field_by_id):
                errors.append(f"post_composite_verification {view_id}: field results do not match visible fields")
                post_all_passed = False
            for field_id, field_result in field_by_id.items():
                field = text_fields.get(field_id, {})
                observation_id = field_result.get("observation_id")
                observation = ocr_observations.get(observation_id)
                expected_hash = field.get("expected_text_sha256")
                observed_text = observation.get("text") if observation else None
                observed_hash = sha256_text(observed_text) if isinstance(observed_text, str) else None
                if (
                    field_result.get("expected_text_sha256") != expected_hash
                    or field_result.get("observed_text_sha256") != observed_hash
                    or observed_hash != expected_hash
                    or field_result.get("match") is not True
                    or (observation and observation.get("field_id") != field_id)
                    or field_result.get("ocr_match_policy") != field.get("ocr_match_policy")
                    or field_result.get("line_joiner") != field.get("line_joiner")
                ):
                    errors.append(f"post_composite_verification {view_id}: exact field {field_id} failed")
                    post_all_passed = False
            expected_codes = set(coverage_views.get(view_id, {}).get("code_ids_visible") or [])
            post_code_observations = ocr_evidence.get("code_observations") if isinstance(ocr_evidence, dict) else None
            post_code_by_id = {
                item.get("code_id"): item for item in post_code_observations
                if isinstance(item, dict) and isinstance(item.get("code_id"), str)
            } if isinstance(post_code_observations, list) else {}
            if (
                not isinstance(post_code_observations, list)
                or set(post_code_by_id) != expected_codes
                or len(post_code_observations) != len(post_code_by_id)
            ):
                errors.append(f"post_composite_verification {view_id}: decoded code observations contain missing, duplicate, or unexpected symbols")
                post_all_passed = False
            code_results = result.get("code_results")
            code_by_id = {
                item.get("code_id"): item for item in code_results
                if isinstance(item, dict) and isinstance(item.get("code_id"), str)
            } if isinstance(code_results, list) else {}
            if set(code_by_id) != expected_codes or not isinstance(code_results, list) or len(code_results) != len(code_by_id):
                errors.append(f"post_composite_verification {view_id}: code results do not match visible codes")
                post_all_passed = False
            for code_id, code_result in code_by_id.items():
                code = code_records.get(code_id, {})
                code_observation = post_code_by_id.get(code_id, {})
                expected_payload = str(code.get("expected_payload"))
                expected_payload_hash = sha256_text(expected_payload)
                if (
                    code_result.get("symbology") != code.get("symbology")
                    or code_result.get("expected_payload_sha256") != expected_payload_hash
                    or code_result.get("observed_payload_sha256") != expected_payload_hash
                    or code_result.get("payload_match") is not True
                    or code_result.get("checksum_result") != "passed"
                    or code_result.get("symbol_geometry_status") != "matched"
                    or code_result.get("observation_id") != code_observation.get("observation_id")
                    or code_observation.get("payload") != code.get("expected_payload")
                    or code_observation.get("symbology") != code.get("symbology")
                    or code_observation.get("disposition") != "mapped_to_expected_code"
                ):
                    errors.append(f"post_composite_verification {view_id}: code {code_id} failed")
                    post_all_passed = False
                decode_receipt = load_evidence_json(
                    root, code_result.get("decode_receipt_path"), code_result.get("decode_receipt_sha256"),
                    f"post_composite_verification {view_id} code {code_id} receipt", errors,
                )
                decode_errors = validate_code_decode_receipt(
                    decode_receipt,
                    asset=asset, view_id=view_id, code_id=code_id,
                    code_record=code, code_observation=code_observation,
                )
                if decode_errors:
                    errors.extend(decode_errors)
                    post_all_passed = False
            expected_graphics = set(coverage_views.get(view_id, {}).get("graphic_ids_visible") or [])
            graphic_results = result.get("graphic_results")
            graphic_by_id = {
                item.get("graphic_id"): item for item in graphic_results
                if isinstance(item, dict) and isinstance(item.get("graphic_id"), str)
            } if isinstance(graphic_results, list) else {}
            if set(graphic_by_id) != expected_graphics or not isinstance(graphic_results, list) or len(graphic_results) != len(graphic_by_id):
                errors.append(f"post_composite_verification {view_id}: graphic results do not match visible graphics")
                post_all_passed = False
            for graphic_id, graphic_result in graphic_by_id.items():
                graphic = graphic_records.get(graphic_id, {})
                compare = load_evidence_json(
                    root, graphic_result.get("comparison_receipt_path"), graphic_result.get("comparison_receipt_sha256"),
                    f"post_composite_verification {view_id} graphic {graphic_id} receipt", errors,
                )
                graphic_layers = [
                    layer for layer in (layers or []) if isinstance(layer, dict)
                    and graphic_id in (layer.get("graphic_ids") or [])
                ]
                graphic_layer = graphic_layers[0] if len(graphic_layers) == 1 else {}
                if graphic_layer.get("projection_model") == "planar_homography":
                    expected_projection_lock = {
                        "projection_model": "planar_homography",
                        "destination_quad_px": graphic_layer.get("destination_quad_px"),
                    }
                else:
                    expected_projection_lock = {
                        "projection_model": graphic_layer.get("projection_model"),
                        "destination_box_px": graphic_layer.get("destination_box_px"),
                    }
                expected_source_lock = {
                    "path": graphic_layer.get("source_path"),
                    "sha256": graphic_layer.get("source_sha256"),
                    "source_crop_box_px": graphic_layer.get("source_crop_box_px"),
                }
                expected_mask_lock = {
                    "path": graphic_layer.get("mask_path"),
                    "sha256": graphic_layer.get("mask_sha256"),
                }
                expected_replay = {
                    "status": "byte_identical",
                    "output_file_sha256": asset.get("file_sha256"),
                    "compositor_script_sha256": expected_compositor_sha,
                    "composition_receipt_replay_status": receipt.get("replay_status") if receipt else None,
                }
                if (
                    graphic_result.get("source_graphic_sha256") != graphic.get("asset_sha256")
                    or graphic_result.get("comparison_status") != "matched"
                    or len(graphic_layers) != 1
                    or not compare
                    or compare.get("schema_version") != "packaging-graphic-comparison-receipt.v1"
                    or compare.get("asset_id") != asset.get("asset_id")
                    or compare.get("view_id") != view_id
                    or compare.get("asset_file_sha256") != asset.get("file_sha256")
                    or compare.get("graphic_id") != graphic_id
                    or compare.get("source_graphic_sha256") != graphic.get("asset_sha256")
                    or compare.get("comparison_adapter_path") != "scripts/run_post_composite_verification.py"
                    or compare.get("comparison_adapter_sha256") != post_adapter_sha
                    or compare.get("composition_job_path") != (receipt.get("composition_job_path") if receipt else None)
                    or compare.get("composition_job_sha256") != (receipt.get("composition_job_sha256") if receipt else None)
                    or compare.get("composition_receipt_path") != result.get("composition_receipt_path")
                    or compare.get("comparison_status") != "matched"
                    or compare.get("deterministic_similarity") != 1.0
                    or compare.get("receipt_sha256") != canonical_hash(compare, "receipt_sha256")
                    or compare.get("composition_receipt_sha256") != result.get("composition_receipt_sha256")
                    or compare.get("layer_id") != graphic_layer.get("layer_id")
                    or compare.get("layer_source_lock") != expected_source_lock
                    or compare.get("projection_lock") != expected_projection_lock
                    or compare.get("mask_lock") != expected_mask_lock
                    or compare.get("final_compositor_replay") != expected_replay
                    or compare.get("comparison_method") != "bundled_composition_replay_source_projection_binding_v1"
                ):
                    errors.append(f"post_composite_verification {view_id}: graphic {graphic_id} failed")
                    post_all_passed = False
        required = [
            "copy_content_lock_status", "label_artwork_lock_status",
            "code_payload_lock_status", "code_symbol_lock_status",
            "logo_graphic_lock_status", "exact_copy_lock_status",
        ]
        for key in required:
            expected_status = "approved" if post_all_passed and set(result_by_view) == required_views else "failed"
            if post.get(key) != expected_status:
                errors.append(f"post_composite_verification: {key} does not match detailed results")
    if manifest.get("production_approval_status") not in {"user_granted", "external_pipeline_granted"}:
        errors.append("COMPLETE run requires explicit production approval")


def validate_run(root: Path) -> list[str]:
    # Establish one physical-path identity for the entire validator.  Windows
    # runners can expose the same temp tree through an 8.3 alias and a long
    # path; macOS can expose /var through /private/var.  Downstream containment
    # checks must never compare a resolved child to an unresolved root alias.
    root = root.resolve(strict=False)
    errors: list[str] = []
    manifest_path = root / "00_manifest/run_manifest.json"
    if not manifest_path.is_file():
        return ["missing 00_manifest/run_manifest.json"]
    try:
        manifest = read_json(manifest_path)
    except Exception as exc:
        return [f"run manifest read failed: {exc}"]
    if not isinstance(manifest, dict):
        return ["run manifest root must be an object"]
    if manifest.get("schema_version") != "packaging-asset-pack-run.v3":
        errors.append("run manifest schema_version is invalid")
    if manifest.get("contract_version") != "whole_product_ocr_rotation_pack_v3":
        errors.append("run manifest contract_version is invalid")
    if manifest.get("master_resolution_contract") != MASTER_RESOLUTION_CONTRACT:
        errors.append("run manifest master_resolution_contract is missing or differs from the installed delivery floor")
    if not isinstance(manifest.get("paths"), dict) or not isinstance(manifest.get("hashes"), dict):
        errors.append("run manifest paths/hashes must be objects")
        return errors
    if manifest.get("exact_copy_mode") not in {
        "all_visible_product_native_copy", "selected_fields_exact", "geometry_only_preview"
    }:
        errors.append("run manifest exact_copy_mode is invalid")
    stage = manifest.get("stage")
    if stage not in set(STAGES) | {"BLOCKED"}:
        errors.append("run manifest stage is invalid")
        return errors
    exact_mode = manifest.get("exact_copy_mode")
    if exact_mode == "all_visible_product_native_copy" and manifest.get("allow_geometry_only_preview") is not False:
        errors.append("all-visible exact-copy mode forbids geometry-only preview")
    if stage == "BLOCKED":
        if not manifest.get("blocked_reason"):
            errors.append("BLOCKED run requires blocked_reason")
        if manifest.get("gates", {}).get("image_generation_allowed") is True:
            errors.append("BLOCKED run cannot allow image generation")
        return errors

    source_manifest = load_locked_json(root, manifest, "source_manifest", "source_manifest_sha256", errors)
    if source_manifest is None:
        return errors
    sources = validate_sources(
        root, source_manifest, manifest.get("product_id"), manifest.get("product_state_id"), errors,
    )
    validate_feature_classification(
        source_manifest, list(manifest.get("product_features") or []), sources,
        str(manifest.get("rotation_profile")), errors,
    )
    if not stage_at_least(stage, "READY_FOR_GENERATION"):
        return errors

    surface_inventory = load_locked_json(root, manifest, "surface_inventory", "surface_inventory_sha256", errors)
    ocr = load_locked_json(root, manifest, "ocr_observations", "ocr_observations_sha256", errors)
    text_ssot = load_locked_json(root, manifest, "text_ssot", "text_ssot_sha256", errors)
    codes = load_locked_json(root, manifest, "code_manifest", "code_manifest_sha256", errors)
    graphics = load_locked_json(root, manifest, "logo_graphic_manifest", "logo_graphic_manifest_sha256", errors)
    coverage = load_locked_json(root, manifest, "coverage_matrix", "coverage_matrix_sha256", errors)
    motion_envelope = load_locked_json(root, manifest, "motion_envelope", "motion_envelope_sha256", errors)
    continuity = load_locked_json(root, manifest, "continuity_contract", "continuity_contract_sha256", errors)
    composition = load_locked_json(root, manifest, "composition_plan", "composition_plan_sha256", errors)
    texture_atlas = load_locked_json(root, manifest, "surface_texture_atlas", "surface_texture_atlas_sha256", errors)
    protected_masks = load_locked_json(root, manifest, "protected_region_masks", "protected_region_masks_sha256", errors)
    bundle_path, bundle_path_errors = safe_run_path(root, manifest.get("paths", {}).get("exact_copy_bundle"), "exact_copy_bundle")
    errors.extend(bundle_path_errors)
    bundle = None
    if bundle_path:
        try:
            bundle = read_json(bundle_path)
            expected_bundle_file_sha = manifest.get("hashes", {}).get("exact_copy_bundle_file_sha256")
            require_sha(expected_bundle_file_sha, "hashes.exact_copy_bundle_file_sha256", errors)
            if isinstance(expected_bundle_file_sha, str) and SHA.fullmatch(expected_bundle_file_sha) and sha256_file(bundle_path) != expected_bundle_file_sha:
                errors.append("exact_copy_bundle: file SHA-256 mismatch")
        except Exception as exc:
            errors.append(f"exact_copy_bundle: invalid strict JSON: {exc}")

    surface_ids: set[str] = set()
    inventory_region_ids: set[str] = set()
    required_field_ids: set[str] = set()
    required_code_ids: set[str] = set()
    required_graphic_ids: set[str] = set()
    surface_by_role: dict[str, str] = {}
    if surface_inventory:
        (
            surface_ids, inventory_region_ids, required_field_ids,
            required_code_ids, required_graphic_ids, surface_by_role,
        ) = validate_surface_inventory(surface_inventory, sources, errors)
    observations: dict[str, dict[str, Any]] = {}
    ocr_region_ids: set[str] = set()
    code_observations: dict[str, dict[str, Any]] = {}
    region_authorities: dict[tuple[str, str], dict[str, Any]] = {}
    if ocr:
        observations, ocr_region_ids, code_observations, region_authorities = validate_ocr(root, ocr, sources, errors)
    text_fields: dict[str, dict[str, Any]] = {}
    if text_ssot:
        text_fields = validate_text_ssot(
            root, text_ssot, str(exact_mode), sources, surface_ids,
            inventory_region_ids, ocr_region_ids, required_field_ids, observations,
            region_authorities, errors,
        )
    for observation_id, observation in observations.items():
        disposition = observation.get("disposition")
        if not isinstance(disposition, dict):
            continue
        if disposition.get("status") == "mapped_to_field":
            field_id = disposition.get("field_id")
            field = text_fields.get(field_id) if isinstance(field_id, str) else None
            if field is None or observation_id not in set(field.get("ocr_observation_ids") or []):
                errors.append(
                    f"ocr_observations {observation_id}: mapped disposition must be reciprocally bound by text SSOT"
                )
    code_records: dict[str, dict[str, Any]] = {}
    if codes:
        code_records = validate_codes(
            codes, root, required_code_ids, surface_ids, sources, code_observations,
            region_authorities, errors,
        )
    graphic_records: dict[str, dict[str, Any]] = {}
    if graphics:
        graphic_records = validate_graphics(
            graphics, root, required_graphic_ids, surface_ids, sources,
            region_authorities, errors
        )
    if surface_inventory:
        validate_region_authority_modalities(
            surface_inventory, region_authorities, text_fields,
            code_records, graphic_records, errors,
        )
    copy_surfaces = {
        field.get("surface_id") for field in text_fields.values()
        if isinstance(field.get("surface_id"), str)
    }
    if texture_atlas:
        validate_texture_atlas(texture_atlas, root, copy_surfaces, errors)
    if protected_masks:
        validate_protected_masks(protected_masks, root, inventory_region_ids, errors)
    required_views: set[str] = set()
    ring_sequences: list[list[str]] = []
    coverage_views: dict[str, dict[str, Any]] = {}
    if coverage:
        required_views, ring_sequences, coverage_views = validate_coverage(
            coverage, str(manifest.get("rotation_profile")), list(manifest.get("product_features") or []),
            str(manifest.get("product_state_id")), motion_envelope, sources, surface_ids,
            surface_by_role, text_fields, code_records, graphic_records, errors,
        )
    if motion_envelope:
        if motion_envelope.get("schema_version") != "packaging-motion-envelope.v1":
            errors.append("motion_envelope: invalid schema_version")
        required_pitched_prefixes(motion_envelope, errors)
        if motion_envelope.get("product_state_id") != manifest.get("product_state_id"):
            errors.append("motion_envelope: product_state_id mismatch")
        if motion_envelope.get("coverage_status") != "passed":
            errors.append("motion_envelope: coverage_status must be passed")
        if set(motion_envelope.get("required_view_ids") or []) != required_views:
            errors.append("motion_envelope: required_view_ids must exactly match coverage requirements")
        expected_edge_ids = {
            f"{ring[index]}__TO__{ring[(index + 1) % len(ring)]}"
            for ring in ring_sequences for index in range(len(ring))
        }
        actual_edge_ids = motion_envelope.get("required_edge_ids")
        if (
            not isinstance(actual_edge_ids, list)
            or len(actual_edge_ids) != len(set(actual_edge_ids))
            or set(actual_edge_ids) != expected_edge_ids
        ):
            errors.append("motion_envelope: required_edge_ids must exactly match every derived ring edge")
        if motion_envelope.get("loop_closure_required") is not True:
            errors.append("motion_envelope: rotation-ready pack requires loop closure")
        if motion_envelope.get("blocked_motion_segments") != []:
            errors.append("motion_envelope: passed coverage cannot retain blocked motion segments")
    if continuity:
        validate_continuity(
            continuity, list(manifest.get("product_features") or []), errors,
            source_manifest_sha256=manifest.get("hashes", {}).get("source_manifest_sha256"),
            neutral_ring_views=ring_sequences[0] if ring_sequences else None,
        )
    if composition: validate_composition(composition, required_views, coverage_views, errors)
    if bundle: validate_bundle(bundle, root, manifest, errors)

    gates = manifest.get("gates")
    if not isinstance(gates, dict):
        errors.append("run manifest gates must be an object")
    else:
        expected_allowed = (
            gates.get("variant_conflict_status") == "passed"
            and gates.get("whole_product_ocr_status") == "passed"
            and gates.get("region_ocr_status") == "passed"
            and gates.get("copy_preflight_status") == "passed_ssot_frozen"
            and gates.get("exact_copy_bundle_hash_verified") is True
            and gates.get("unresolved_required_field_count") == 0
            and gates.get("source_conflict_count") == 0
            and gates.get("required_code_decodes_pass") is True
            and gates.get("logo_graphic_binding_pass") is True
            and gates.get("deterministic_composition_plan_status") == "ready"
            and gates.get("required_view_surface_coverage_status") == "passed"
            and not errors
        )
        if gates.get("prompt_compilation_allowed") is not expected_allowed:
            errors.append("run manifest prompt_compilation_allowed does not match hard gates")
        if gates.get("image_generation_allowed") is not expected_allowed:
            errors.append("run manifest image_generation_allowed does not match hard gates")
        if stage_at_least(stage, "READY_FOR_GENERATION") and not gates.get("image_generation_allowed"):
            errors.append("run cannot reach READY_FOR_GENERATION while hard gates deny generation")

    prompt_records: dict[str, dict[str, Any]] = {}
    if stage_at_least(stage, "GENERATING"):
        prompt_index = load_locked_json(root, manifest, "generation_prompt_index", "generation_prompt_index_sha256", errors)
        if prompt_index and composition:
            prompt_records = validate_prompt_index(
                root, prompt_index, manifest, coverage, required_views, coverage_views,
                composition, sources, errors,
            )
    if stage == "COMPLETE":
        validate_complete(
            root, manifest, required_views, ring_sequences, coverage_views,
            prompt_records, sources, text_fields, code_records, graphic_records,
            composition or {}, errors,
        )
    return errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    errors = validate_run(args.run_root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(json.dumps({"status": "PASS", "run_root": str(args.run_root.resolve())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
