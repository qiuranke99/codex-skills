#!/usr/bin/env python3
"""Compile deterministic, hash-bound prompts for every required packaging view."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from validate_packaging_run import validate_run


SKILL_DIR = Path(__file__).resolve().parents[1]
SHA256 = re.compile(r"^[a-f0-9]{64}$")
READY_STAGES = {
    "READY_FOR_GENERATION", "GENERATING", "INSPECTING",
    "COMPOSITING_EXACT_COPY", "POST_COMPOSITE_VERIFYING",
    "BUILDING_REVIEW_BOARDS", "QA_PASSED", "COMPLETE",
}


class CompileError(ValueError):
    """Raised when frozen dependencies cannot support prompt compilation."""


def final_runtime_capability_errors(
    *, platform_name: str, swift_path: str | None,
    vision_script_exists: bool, adapter_script_exists: bool,
    pillow_version: str | None, expected_pillow_version: str,
    live_smoke_status: str | None = None,
) -> list[str]:
    """Evaluate the non-negotiable final exact-copy verification runtime."""
    errors: list[str] = []
    if platform_name != "darwin":
        errors.append("final post-composite Vision verification requires Darwin")
    if not swift_path:
        errors.append("Swift runtime is unavailable")
    if not vision_script_exists:
        errors.append("bundled macOS Vision script is missing")
    if not adapter_script_exists:
        errors.append("bundled post-composite verification adapter is missing")
    if pillow_version is None:
        errors.append("Pillow runtime is unavailable")
    elif pillow_version != expected_pillow_version:
        errors.append(
            f"Pillow runtime {pillow_version} differs from required {expected_pillow_version}"
        )
    if live_smoke_status is not None and live_smoke_status != "PASS":
        errors.append("bundled Vision live OCR/EAN/QR smoke did not pass")
    return errors


def required_pillow_version() -> str:
    requirements = SKILL_DIR / "requirements.txt"
    try:
        matches = [
            line.split("==", 1)[1].strip()
            for line in requirements.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("Pillow==")
        ]
    except OSError as exc:
        raise CompileError(f"cannot read pinned runtime dependencies: {exc}") from exc
    require(len(matches) == 1 and bool(matches[0]), "requirements.txt must contain one exact Pillow pin")
    return matches[0]


def assert_final_post_composite_runtime_callable(manifest: dict[str, Any]) -> None:
    """Fail before prompt creation when exact-copy final verification cannot run."""
    if manifest.get("exact_copy_mode") == "geometry_only_preview":
        return
    expected_pillow = required_pillow_version()
    try:
        import PIL  # type: ignore[import-not-found]
        pillow_version: str | None = str(PIL.__version__)
    except ImportError:
        pillow_version = None
    vision_script = SKILL_DIR / "scripts/macos_vision_ocr.swift"
    adapter_script = SKILL_DIR / "scripts/run_post_composite_verification.py"
    swift_path = shutil.which("swift")
    base_errors = final_runtime_capability_errors(
        platform_name=sys.platform,
        swift_path=swift_path,
        vision_script_exists=vision_script.is_file(),
        adapter_script_exists=adapter_script.is_file(),
        pillow_version=pillow_version,
        expected_pillow_version=expected_pillow,
    )
    if base_errors:
        raise CompileError(
            "final post-composite runtime preflight blocked prompt compilation: "
            + " | ".join(base_errors)
        )
    smoke_script = SKILL_DIR / "scripts/test_macos_vision_runtime.py"
    require(smoke_script.is_file(), "bundled Vision live-smoke script is missing")
    environment = dict(os.environ)
    environment.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"})
    try:
        result = subprocess.run(
            [sys.executable, "-B", str(smoke_script), "--require-live"],
            cwd=str(SKILL_DIR), env=environment, capture_output=True, text=True,
            encoding="utf-8", errors="backslashreplace", timeout=45, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CompileError(f"final post-composite runtime live smoke could not run: {exc}") from exc
    smoke_status: str | None = None
    if result.returncode == 0:
        for line in reversed(result.stdout.splitlines()):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                smoke_status = str(payload.get("status"))
                break
    live_errors = final_runtime_capability_errors(
        platform_name=sys.platform,
        swift_path=swift_path,
        vision_script_exists=vision_script.is_file(),
        adapter_script_exists=adapter_script.is_file(),
        pillow_version=pillow_version,
        expected_pillow_version=expected_pillow,
        live_smoke_status=smoke_status,
    )
    if result.returncode != 0 or live_errors:
        detail = (result.stderr or result.stdout).strip()[-1000:]
        raise CompileError(
            "final post-composite runtime live smoke blocked prompt compilation: "
            + " | ".join(live_errors or [detail or f"exit {result.returncode}"])
        )


def strict_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise CompileError(f"cannot read strict JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CompileError(f"JSON root must be an object: {path}")
    return value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_hash(value: dict[str, Any], omit: str | None = None) -> str:
    payload = dict(value)
    if omit:
        payload.pop(omit, None)
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256_bytes(encoded)


def stable_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CompileError(message)


def run_path(root: Path, locator: Any, label: str, *, must_exist: bool = True) -> Path:
    require(isinstance(locator, str) and bool(locator), f"{label}: locator must be non-empty")
    relative = Path(locator)
    require(not relative.is_absolute() and ".." not in relative.parts, f"{label}: locator must be run-relative")
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise CompileError(f"{label}: locator escapes run root") from exc
    if must_exist:
        require(path.is_file(), f"{label}: missing file {locator}")
    return path


def locked_json(
    root: Path, manifest: dict[str, Any], path_key: str, hash_key: str,
) -> tuple[Path, dict[str, Any]]:
    paths = manifest.get("paths")
    hashes = manifest.get("hashes")
    require(isinstance(paths, dict) and isinstance(hashes, dict), "run manifest paths/hashes must be objects")
    path = run_path(root, paths.get(path_key), path_key)
    expected = hashes.get(hash_key)
    require(isinstance(expected, str) and SHA256.fullmatch(expected) is not None, f"{hash_key}: invalid SHA-256")
    actual = sha256_file(path)
    require(actual == expected, f"{path_key}: file hash {actual} does not match {hash_key} {expected}")
    return path, strict_json(path)


def nonempty_list(record: dict[str, Any], key: str, label: str) -> list[Any]:
    value = record.get(key)
    require(isinstance(value, list) and bool(value), f"{label}.{key} must be a non-empty array")
    return value


def list_value(record: dict[str, Any], key: str, label: str) -> list[Any]:
    value = record.get(key)
    require(isinstance(value, list), f"{label}.{key} must be an array")
    return value


def text_value(record: dict[str, Any], key: str, label: str) -> str:
    value = record.get(key)
    require(isinstance(value, str) and bool(value.strip()), f"{label}.{key} must be non-empty text")
    return value


def format_optional(value: Any) -> str:
    return "none" if value is None else str(value)


def ranked_references(view: dict[str, Any]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for role, values in (
        ("authoritative_source", view["source_refs"]),
        ("parent_anchor", view["parent_anchor_view_ids"]),
        ("previous_neighbor", [view.get("previous_view_id")] if view.get("previous_view_id") else []),
        ("next_neighbor", [view.get("next_view_id")] if view.get("next_view_id") else []),
    ):
        for value in values:
            require(isinstance(value, str) and bool(value), f"view {view['view_id']}: invalid {role} reference")
            key = (role, value)
            if key not in seen:
                seen.add(key)
                ranked.append({"rank": len(ranked) + 1, "role": role, "reference_id": value})
    return ranked


def prompt_bytes(
    *, manifest: dict[str, Any], coverage: dict[str, Any], view: dict[str, Any],
    composition: dict[str, Any], composition_view: dict[str, Any],
    dependencies: dict[str, str], extended_dependencies: dict[str, str],
    asset_id: str, ranked: list[dict[str, Any]],
) -> bytes:
    identity_lock = coverage["identity_lock"]
    coordinate_frame = coverage["product_coordinate_frame"]
    detail_job = view.get("detail_job") or "not_applicable_full_product"
    lines = [
        "Create exactly one horizontal 16:9 full-frame packaging product reference asset.",
        f"This is generation unit {asset_id}, view {view['view_id']}, for product state {manifest['product_state_id']}.",
        f"Show exactly one {view['shot_scale']} view of the single frozen product identity.",
        "No contact sheet, collage, second product, title, legend, caption, UI, watermark, poster, scene, prop, person, or non-product-native text.",
        "Return exact horizontal 16:9 pixels at no less than 1280x720; do not satisfy this request by resizing a smaller generated image after generation.",
        "",
        "CAMERA LOCK",
        f"- Frozen view family: {view['family']}.",
        f"- Review-board semantic role: {view['review_board_role']}.",
        f"- Product coordinate frame: {stable_json(coordinate_frame)}",
        f"- Camera pose: azimuth {view['azimuth_deg']} degrees; elevation {view['elevation_deg']} degrees; roll {view['roll_deg']} degrees.",
        f"- Lens profile: {view['lens_profile']}.",
        f"- Camera-distance profile: {view['camera_distance_profile']}.",
        f"- Product occupancy and center lock: {identity_lock['occupancy_lock']}.",
        f"- Previous calibrated neighbor: {format_optional(view.get('previous_view_id'))}.",
        f"- Next calibrated neighbor: {format_optional(view.get('next_view_id'))}.",
        f"- Parent anchor views: {stable_json(view['parent_anchor_view_ids'])}.",
        f"- Frozen framing contract: {view.get('framing_contract', 'complete uncropped full-product master')}.",
        "",
        "IDENTITY, GEOMETRY, AND STATE LOCK",
        f"- Product state ID: {manifest['product_state_id']}.",
        f"- Global identity core SHA-256: {canonical_hash(identity_lock)}.",
        f"- Geometry landmark contract: {stable_json(identity_lock['geometry_landmark_contract'])}.",
        f"- View geometry landmark IDs: {stable_json(view['geometry_landmark_ids'])}.",
        f"- Visible component IDs: {stable_json(view['visible_component_ids'])}.",
        f"- Visible surface IDs: {stable_json(view['visible_surface_ids'])}.",
        f"- Occluded surface IDs: {stable_json(view['occluded_surface_ids'])}.",
        "- Preserve component count, topology, silhouette, width/depth ratio, shoulder, side walls, seams, base, closure, pump/nozzle vector, fill level, internal-component topology, embossing registration, and immutable product state exactly as frozen.",
        "- Do not invent an unseen surface, seam, mechanism, label continuation, code, or internal component.",
        "",
        "MATERIAL LOCK",
        f"- Global material contract: {stable_json(identity_lock['material_contract'])}.",
        f"- View material feature IDs: {stable_json(view['material_feature_ids'])}.",
        "- Closure/nozzle orientation is fixed in product space, never screen space.",
        "- For upright rotation, liquid volume and fill level remain constant and world-horizontal.",
        "- Transparent opposite-side copy is a mirrored/refracted physical layer, never newly typeset direct front copy.",
        "",
        "MACHINE-READABLE UNIT LOCKS",
        f"azimuth_deg: {float(view['azimuth_deg'])}",
        f"elevation_deg: {float(view['elevation_deg'])}",
        f"roll_deg: {float(view['roll_deg'])}",
        f"shot_scale: {view['shot_scale']}",
        f"view_family: {view['family']}",
        f"review_board_role: {view['review_board_role']}",
        "minimum_returned_pixel_dimensions: {\"height\":720,\"width\":1280}",
        "post_generation_resize_allowed_to_meet_minimum: false",
        f"dynamic_region_contract: {stable_json(view.get('dynamic_region_contract'))}",
        f"lens_profile: {view['lens_profile']}",
        f"camera_distance_profile: {view['camera_distance_profile']}",
        f"visible_surface_ids: {stable_json(view['visible_surface_ids'])}",
        f"visible_component_ids: {stable_json(view['visible_component_ids'])}",
        f"source_reference_ids: {stable_json(view['source_refs'])}",
        f"parent_anchor_view_ids: {stable_json(view['parent_anchor_view_ids'])}",
        f"previous_anchor_id: {stable_json(view.get('previous_view_id'))}",
        f"next_anchor_id: {stable_json(view.get('next_view_id'))}",
        f"protected_copy_region_ids: {stable_json(composition_view['protected_region_ids'])}",
        f"deterministic_composition_plan_id: {composition['plan_id']}",
        "material_lock: preserve source-bound material response",
        "geometry_lock: preserve source-bound topology and proportions",
        f"exact_copy_bundle_sha256: {dependencies['exact_copy_bundle_sha256']}",
        f"exact_copy_bundle_file_sha256: {dependencies['exact_copy_bundle_file_sha256']}",
        f"coverage_matrix_sha256: {dependencies['coverage_matrix_sha256']}",
        f"surface_texture_atlas_sha256: {dependencies['surface_texture_atlas_sha256']}",
        "",
        "FOUR REQUIRED DEPENDENCY HASHES",
        f"- Exact-copy bundle SHA-256: {dependencies['exact_copy_bundle_sha256']}",
        f"- Exact-copy bundle file SHA-256: {dependencies['exact_copy_bundle_file_sha256']}",
        f"- Coverage matrix SHA-256: {dependencies['coverage_matrix_sha256']}",
        f"- Surface texture atlas SHA-256: {dependencies['surface_texture_atlas_sha256']}",
        "",
        "EXTENDED FROZEN LOCKS",
        f"- Source manifest SHA-256: {extended_dependencies['source_manifest_sha256']}",
        f"- Protected-region masks SHA-256: {extended_dependencies['protected_region_masks_sha256']}",
        f"- Deterministic composition plan SHA-256: {extended_dependencies['composition_plan_sha256']}",
        f"- Deterministic composition plan ID: {composition['plan_id']}.",
        f"- Projection status/model: {composition_view['status']} / {composition_view.get('projection_model', 'not_required_no_visible_copy')}.",
        f"- Source layer IDs: {stable_json(composition_view.get('source_layer_ids', []))}.",
        f"- Protected copy region IDs: {stable_json(composition_view['protected_region_ids'])}.",
        f"- Visible OCR field IDs: {stable_json(composition_view['ocr_field_ids_visible'])}.",
        f"- Visible code IDs: {stable_json(composition_view['code_ids_visible'])}.",
        f"- Visible graphic IDs: {stable_json(composition_view['graphic_ids_visible'])}.",
        f"- Unit detail job: {stable_json(detail_job)}.",
        f"- Dynamic exact-copy region contract: {stable_json(view.get('dynamic_region_contract'))}.",
        "",
        "REFERENCE PRIORITY",
        stable_json(ranked),
        "Use only the bound reference IDs for this unit. Source IDs govern observed product evidence; anchor view IDs govern calibrated pose continuity.",
        "",
        "EXACT-COPY BOUNDARY",
        "generation_text_policy: no_model_generated_product_copy",
        "Do not generate, typeset, rewrite, translate, autocorrect, approximate, or hallucinate any packaging word, letter, number, punctuation, unit, logo, certification mark, barcode, QR code, batch code, or date.",
        "Render only the source-bound package substrate and protected blank or masked copy surfaces required by the deterministic composition plan. Frozen product copy is applied later by deterministic composition.",
        "raw_generated_asset_publishable: false",
        "raw_generated_asset_registry_eligible: false",
        "",
        "FORBIDDEN INVENTIONS",
        stable_json(identity_lock["forbidden_inventions"]),
        "",
        f"Return one complete, uncropped, neutral studio reference asset for {asset_id} only. Product correctness, calibrated camera continuity, material identity, and protected exact-copy regions outrank advertising polish.",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def write_frozen(path: Path, payload: bytes, *, replace: bool) -> None:
    if path.exists():
        existing = path.read_bytes()
        if existing == payload:
            return
        require(replace, f"refusing to overwrite different frozen bytes: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def compile_run(root: Path, *, replace: bool = False) -> dict[str, Any]:
    root = root.resolve()
    preflight_errors = validate_run(root)
    require(
        not preflight_errors,
        "full READY preflight failed before prompt compilation: " + " | ".join(preflight_errors),
    )
    manifest_path = root / "00_manifest/run_manifest.json"
    require(manifest_path.is_file(), "missing 00_manifest/run_manifest.json")
    manifest = strict_json(manifest_path)
    require(manifest.get("schema_version") == "packaging-asset-pack-run.v3", "unsupported run manifest schema")
    require(manifest.get("contract_version") == "whole_product_ocr_rotation_pack_v3", "unsupported contract version")
    require(manifest.get("stage") in READY_STAGES, "run has not reached READY_FOR_GENERATION")
    assert_final_post_composite_runtime_callable(manifest)
    gates = manifest.get("gates")
    require(isinstance(gates, dict), "run manifest gates must be an object")
    require(gates.get("prompt_compilation_allowed") is True, "prompt compilation hard gate is closed")
    require(gates.get("image_generation_allowed") is True, "image generation hard gate is closed")
    require(isinstance(manifest.get("product_state_id"), str) and bool(manifest["product_state_id"]), "missing product_state_id")

    _, source_manifest = locked_json(root, manifest, "source_manifest", "source_manifest_sha256")
    coverage_path, coverage = locked_json(root, manifest, "coverage_matrix", "coverage_matrix_sha256")
    composition_path, composition = locked_json(root, manifest, "composition_plan", "composition_plan_sha256")
    _, atlas = locked_json(root, manifest, "surface_texture_atlas", "surface_texture_atlas_sha256")
    _, masks = locked_json(root, manifest, "protected_region_masks", "protected_region_masks_sha256")
    require(source_manifest.get("schema_version") == "packaging-source-manifest.v1", "source manifest schema mismatch")
    require(coverage.get("schema_version") == "packaging-view-coverage.v1" and coverage.get("freeze_status") == "frozen", "coverage matrix is not frozen v1")
    require(composition.get("schema_version") == "packaging-deterministic-composition-plan.v1" and composition.get("status") == "ready", "composition plan is not ready v1")
    require(atlas.get("schema_version") == "packaging-surface-texture-atlas.v1" and atlas.get("freeze_status") == "frozen", "surface atlas is not frozen v1")
    require(masks.get("schema_version") == "packaging-protected-region-masks.v1" and masks.get("freeze_status") == "frozen", "protected masks are not frozen v1")

    exact_path = run_path(root, manifest["paths"].get("exact_copy_bundle"), "exact_copy_bundle")
    exact_file_sha = sha256_file(exact_path)
    require(exact_file_sha == manifest["hashes"].get("exact_copy_bundle_file_sha256"), "exact-copy bundle file hash mismatch")
    exact_bundle = strict_json(exact_path)
    semantic_sha = canonical_hash(exact_bundle, "exact_copy_bundle_sha256")
    require(exact_bundle.get("freeze_status") == "frozen", "exact-copy bundle is not frozen")
    require(exact_bundle.get("exact_copy_bundle_sha256") == semantic_sha, "exact-copy bundle self hash mismatch")
    require(manifest["hashes"].get("exact_copy_bundle_sha256") == semantic_sha, "run manifest exact-copy bundle semantic hash mismatch")

    coordinate_frame = coverage.get("product_coordinate_frame")
    identity_lock = coverage.get("identity_lock")
    require(isinstance(coordinate_frame, dict) and bool(coordinate_frame), "coverage matrix requires product_coordinate_frame")
    require(isinstance(identity_lock, dict), "coverage matrix requires identity_lock")
    for key in ("geometry_landmark_contract", "material_contract", "occupancy_lock", "forbidden_inventions"):
        require(key in identity_lock, f"coverage identity_lock missing {key}")
    require(isinstance(identity_lock["forbidden_inventions"], list) and bool(identity_lock["forbidden_inventions"]), "identity_lock.forbidden_inventions must be non-empty")
    require(isinstance(identity_lock["occupancy_lock"], str) and bool(identity_lock["occupancy_lock"]), "identity_lock.occupancy_lock must be non-empty")

    sources = source_manifest.get("sources")
    require(isinstance(sources, list) and bool(sources), "source manifest requires sources")
    known_sources = {item.get("source_id") for item in sources if isinstance(item, dict)}
    views = coverage.get("views")
    require(isinstance(views, list) and bool(views), "coverage matrix requires views")
    required_views = [item for item in views if isinstance(item, dict) and item.get("required") is True]
    require(bool(required_views), "coverage matrix has no required views")
    view_ids = [item.get("view_id") for item in required_views]
    require(all(isinstance(value, str) and bool(value) for value in view_ids), "required views need non-empty view_id")
    require(len(view_ids) == len(set(view_ids)), "required view IDs must be unique")

    statuses = composition.get("view_statuses")
    require(isinstance(statuses, list), "composition plan view_statuses must be an array")
    composition_by_view = {
        item.get("view_id"): item for item in statuses
        if isinstance(item, dict) and isinstance(item.get("view_id"), str)
    }
    require(set(composition_by_view) == set(view_ids), "composition plan must exactly cover required views")

    dependencies = {
        "exact_copy_bundle_sha256": semantic_sha,
        "exact_copy_bundle_file_sha256": exact_file_sha,
        "coverage_matrix_sha256": sha256_file(coverage_path),
        "surface_texture_atlas_sha256": manifest["hashes"]["surface_texture_atlas_sha256"],
    }
    extended_dependencies = {
        "source_manifest_sha256": manifest["hashes"]["source_manifest_sha256"],
        "protected_region_masks_sha256": manifest["hashes"]["protected_region_masks_sha256"],
        "composition_plan_sha256": sha256_file(composition_path),
    }
    index_path = run_path(
        root, manifest["paths"].get("generation_prompt_index"),
        "generation_prompt_index", must_exist=False,
    )
    records: list[dict[str, Any]] = []
    unit_outputs: list[tuple[Path, bytes]] = []
    compiler_sha = sha256_file(Path(__file__).resolve())

    for view in sorted(required_views, key=lambda item: str(item["view_id"])):
        view_id = str(view["view_id"])
        label = f"coverage view {view_id}"
        for key in ("azimuth_deg", "elevation_deg", "roll_deg"):
            require(isinstance(view.get(key), (int, float)) and not isinstance(view.get(key), bool), f"{label}.{key} must be numeric")
        for key in ("family", "review_board_role", "shot_scale", "lens_profile", "camera_distance_profile"):
            text_value(view, key, label)
        for key in (
            "visible_surface_ids", "visible_component_ids", "occluded_surface_ids", "geometry_landmark_ids",
            "material_feature_ids", "source_refs", "parent_anchor_view_ids",
            "label_region_ids", "ocr_field_ids_visible", "code_ids_visible", "graphic_ids_visible",
        ):
            list_value(view, key, label)
        nonempty_list(view, "visible_surface_ids", label)
        nonempty_list(view, "geometry_landmark_ids", label)
        nonempty_list(view, "source_refs", label)
        require(set(view["source_refs"]).issubset(known_sources), f"{label}.source_refs contains unknown source IDs")
        require(view.get("product_state_id") == manifest["product_state_id"], f"{label}.product_state_id drift")
        composition_view = composition_by_view[view_id]
        for key in ("protected_region_ids", "ocr_field_ids_visible", "code_ids_visible", "graphic_ids_visible"):
            list_value(composition_view, key, f"composition view {view_id}")
        require(composition_view["protected_region_ids"] == view["label_region_ids"], f"composition {view_id}: protected regions mismatch")
        for key in ("ocr_field_ids_visible", "code_ids_visible", "graphic_ids_visible"):
            require(composition_view[key] == view[key], f"composition {view_id}: {key} mismatch")
        require(composition_view.get("status") in {"ready", "not_required_no_visible_copy"}, f"composition {view_id}: unresolved status")
        if composition_view.get("status") == "ready":
            nonempty_list(composition_view, "source_layer_ids", f"composition view {view_id}")
            text_value(composition_view, "projection_model", f"composition view {view_id}")

        asset_id = view.get("asset_id") or f"ASSET_{view_id}"
        require(isinstance(asset_id, str) and re.fullmatch(r"[A-Za-z0-9_.-]+", asset_id) is not None, f"view {view_id}: unsafe asset_id")
        ranked = ranked_references(view)
        payload = prompt_bytes(
            manifest=manifest, coverage=coverage, view=view, composition=composition,
            composition_view=composition_view, dependencies=dependencies,
            extended_dependencies=extended_dependencies, asset_id=asset_id, ranked=ranked,
        )
        prompt_locator = f"{index_path.parent.relative_to(root).as_posix()}/generation_units/{asset_id}_generation_prompt.md"
        prompt_path = run_path(root, prompt_locator, f"prompt {view_id}", must_exist=False)
        unit_outputs.append((prompt_path, payload))
        records.append({
            "asset_id": asset_id,
            "view_id": view_id,
            "prompt_path": prompt_locator,
            "prompt_sha256": sha256_bytes(payload),
            "dependency_hashes": dependencies,
            "extended_dependency_hashes": extended_dependencies,
            "compiler_sha256": compiler_sha,
            "product_state_id": manifest["product_state_id"],
            "reference_ids": view["source_refs"],
            "ranked_reference_bindings": ranked,
            "previous_anchor_id": view.get("previous_view_id"),
            "next_anchor_id": view.get("next_view_id"),
            "parent_anchor_view_ids": view["parent_anchor_view_ids"],
            "protected_copy_region_ids": view["label_region_ids"],
            "deterministic_composition_plan_id": composition["plan_id"],
            "generation_text_policy": "no_model_generated_product_copy",
            "minimum_returned_pixel_dimensions": {"width": 1280, "height": 720},
            "post_generation_resize_allowed_to_meet_minimum": False,
        })

    index = {
        "schema_version": "packaging-generation-prompt-index.v1",
        "contract_version": "whole_product_ocr_rotation_pack_v3",
        "compiler_path": "scripts/compile_generation_prompts.py",
        "compiler_sha256": compiler_sha,
        "dependency_hashes": dependencies,
        "extended_dependency_hashes": extended_dependencies,
        "global_identity_core_sha256": canonical_hash(identity_lock),
        "prompts": records,
    }
    index_payload = (json.dumps(index, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if replace:
        require(
            manifest.get("stage") == "READY_FOR_GENERATION",
            "--replace requires resetting the run to READY_FOR_GENERATION and invalidating downstream assets first",
        )
    for output_path, output_payload in [*unit_outputs, (index_path, index_payload)]:
        if output_path.exists() and output_path.read_bytes() != output_payload:
            require(replace, f"refusing to overwrite different frozen bytes: {output_path}")
    for output_path, output_payload in unit_outputs:
        write_frozen(output_path, output_payload, replace=replace)
    write_frozen(index_path, index_payload, replace=replace)
    return {
        "status": "compiled",
        "run_root": str(root),
        "prompt_count": len(records),
        "generation_prompt_index": str(index_path.relative_to(root)),
        "generation_prompt_index_sha256": sha256_bytes(index_payload),
        "dependency_hashes": dependencies,
        "manifest_update_required": {
            "hashes.generation_prompt_index_sha256": sha256_bytes(index_payload),
            "stage": "GENERATING only after each prompt has been frozen before its terminal image call",
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    parser.add_argument(
        "--replace", action="store_true",
        help="replace prompt/index bytes only when intentionally invalidating prior frozen prompts",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = compile_run(args.run_root, replace=args.replace)
    except CompileError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
