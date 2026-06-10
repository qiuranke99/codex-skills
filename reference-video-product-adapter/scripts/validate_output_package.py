#!/usr/bin/env python3
"""Validate a reference-video product-adapter output package."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "assets" / "schemas"

PACKAGE_FILES = {
    "02-analysis/reference_breakdown.json": "reference_breakdown.schema.json",
    "02-analysis/product_mapping.json": "product_mapping.schema.json",
    "03-brief/adaptation_brief.json": "adaptation_brief.schema.json",
    "04-shot-list/shot_list.json": "shot_list.schema.json",
    "05-storyboard/storyboard_panel_spec.json": "storyboard_panel_spec.schema.json",
}

OPTIONAL_PACKAGE_FILES = {
    "01-input/local-video/video_metadata.json": "video_metadata.schema.json",
}

REQUIRED_TEXT_FILES = [
    "01-input/reference_video_link.md",
    "01-input/product_pack.md",
    "02-analysis/keep_change_avoid.md",
    "02-analysis/similarity_risk_report.md",
    "04-shot-list/shot_list.md",
    "05-storyboard/storyboard_prompt.md",
    "06-video-platform/video_platform_prompt.md",
    "06-video-platform/asset_checklist.md",
    "07-review/feasibility_report.md",
    "07-review/missing_info_questions.md",
]

REQUIRED_GUIDANCE = "Use the storyboard as sequential shot guidance, not as a static collage"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_schema(data: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    expected = schema.get("type")

    if expected == "object":
        if not isinstance(data, dict):
            return [f"{path}: expected object"]
        for key in schema.get("required", []):
            if key not in data:
                errors.append(f"{path}: missing required key '{key}'")
        properties = schema.get("properties", {})
        for key, subschema in properties.items():
            if key in data:
                errors.extend(validate_schema(data[key], subschema, f"{path}.{key}"))

    elif expected == "array":
        if not isinstance(data, list):
            return [f"{path}: expected array"]
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(data):
                errors.extend(validate_schema(item, item_schema, f"{path}[{index}]"))

    elif expected == "string":
        if not isinstance(data, str):
            errors.append(f"{path}: expected string")
        elif "enum" in schema and data not in schema["enum"]:
            errors.append(f"{path}: value '{data}' not in enum {schema['enum']}")

    elif expected == "number":
        if not isinstance(data, (int, float)) or isinstance(data, bool):
            errors.append(f"{path}: expected number")

    return errors


def validate_package(package_dir: Path) -> list[str]:
    errors: list[str] = []

    if not package_dir.exists() or not package_dir.is_dir():
        return [f"package directory not found: {package_dir}"]

    loaded: dict[str, Any] = {}
    for relative_path, schema_name in PACKAGE_FILES.items():
        data_path = package_dir / relative_path
        schema_path = SCHEMA_DIR / schema_name
        if not data_path.exists():
            errors.append(f"missing {relative_path}")
            continue
        try:
            data = load_json(data_path)
            schema = load_json(schema_path)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid json {relative_path}: {exc}")
            continue
        loaded[relative_path] = data
        errors.extend(validate_schema(data, schema, relative_path))

    for relative_path, schema_name in OPTIONAL_PACKAGE_FILES.items():
        data_path = package_dir / relative_path
        if not data_path.exists():
            continue
        schema_path = SCHEMA_DIR / schema_name
        try:
            data = load_json(data_path)
            schema = load_json(schema_path)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid json {relative_path}: {exc}")
            continue
        loaded[relative_path] = data
        errors.extend(validate_schema(data, schema, relative_path))

    for relative_path in REQUIRED_TEXT_FILES:
        path = package_dir / relative_path
        if not path.exists():
            errors.append(f"missing {relative_path}")
        elif not path.read_text(encoding="utf-8").strip():
            errors.append(f"empty {relative_path}")

    local_metadata = loaded.get("01-input/local-video/video_metadata.json")
    if isinstance(local_metadata, dict):
        local_dir = package_dir / "01-input" / "local-video"
        report = local_dir / "local_video_ingest_report.md"
        if not report.exists() or not report.read_text(encoding="utf-8").strip():
            errors.append("local-video/local_video_ingest_report.md missing or empty")
        for frame in local_metadata.get("extracted_frames", []):
            if not (local_dir / str(frame)).exists():
                errors.append(f"local video extracted frame missing: {frame}")
        contact_sheet = str(local_metadata.get("contact_sheet", ""))
        if contact_sheet and not (local_dir / contact_sheet).exists():
            errors.append(f"local video contact sheet missing: {contact_sheet}")
        audio_path = str(local_metadata.get("audio_path", ""))
        if audio_path and not (local_dir / audio_path).exists():
            errors.append(f"local video audio missing: {audio_path}")

    shot_list = loaded.get("04-shot-list/shot_list.json", {})
    shots = shot_list.get("shots", []) if isinstance(shot_list, dict) else []
    if not (3 <= len(shots) <= 12):
        errors.append(f"shot_list must contain 3 to 12 shots, got {len(shots)}")

    shot_ids = {shot.get("shot_id") for shot in shots if isinstance(shot, dict)}
    for shot in shots:
        if not shot.get("source_refs"):
            errors.append(f"{shot.get('shot_id', '<unknown>')}: source_refs is empty")
        if "unsupported_claim" in shot.get("risk_flags", []) and "needs_confirmation" not in " ".join(shot.get("source_refs", [])):
            errors.append(f"{shot.get('shot_id')}: unsupported claim risk lacks confirmation marker")

    panel_spec = loaded.get("05-storyboard/storyboard_panel_spec.json", {})
    panels = panel_spec.get("panels", []) if isinstance(panel_spec, dict) else []
    for panel in panels:
        shot_id = panel.get("shot_id")
        if shot_id not in shot_ids:
            errors.append(f"{panel.get('panel_id', '<panel>')}: unknown shot_id {shot_id}")

    storyboard_prompt = package_dir / "05-storyboard" / "storyboard_prompt.md"
    video_prompt = package_dir / "06-video-platform" / "video_platform_prompt.md"
    for path in [storyboard_prompt, video_prompt]:
        if path.exists() and REQUIRED_GUIDANCE not in path.read_text(encoding="utf-8"):
            errors.append(f"{path.relative_to(package_dir)} missing sequential guidance instruction")

    if "static collage" not in str(panel_spec.get("sequential_guidance", "")):
        errors.append("storyboard_panel_spec sequential_guidance must mention static collage")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_output_package.py <output-package-dir>")
        return 2

    errors = validate_package(Path(sys.argv[1]))
    if errors:
        print("Output package validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Output package validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
