#!/usr/bin/env python3
"""Validate a completed Scene Canon Asset Pack using only the Python standard library."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
REFERENCES_DIR = SKILL_DIR / "references"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_ref(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not ref:
        return schema
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported external schema reference: {ref}")
    current: Any = root
    for token in ref[2:].split("/"):
        current = current[token.replace("~1", "/").replace("~0", "~")]
    return current


def type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def validate_schema_value(
    value: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    path: str = "$",
) -> list[str]:
    errors: list[str] = []
    schema = resolve_ref(schema, root_schema)

    expected = schema.get("type")
    if expected:
        options = expected if isinstance(expected, list) else [expected]
        if not any(type_matches(value, option) for option in options):
            return [f"{path}: expected type {options}, got {type(value).__name__}"]

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is not in enum")

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required key {key!r}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extras = sorted(set(value) - set(properties))
            for key in extras:
                errors.append(f"{path}: unexpected key {key!r}")
        for key, child in value.items():
            if key in properties:
                errors.extend(validate_schema_value(child, properties[key], root_schema, f"{path}.{key}"))

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: requires at least {schema['minItems']} items")
        if schema.get("uniqueItems"):
            normalized = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in value]
            if len(normalized) != len(set(normalized)):
                errors.append(f"{path}: items must be unique")
        item_schema = schema.get("items")
        if item_schema:
            for index, child in enumerate(value):
                errors.extend(validate_schema_value(child, item_schema, root_schema, f"{path}[{index}]"))

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string is shorter than {schema['minLength']}")
        pattern = schema.get("pattern")
        if pattern and not re.search(pattern, value):
            errors.append(f"{path}: string does not match pattern {pattern!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: value is below minimum {schema['minimum']}")

    return errors


def image_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if data.startswith(b"\xff\xd8"):
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            index += 2
            if marker in {0xD8, 0xD9}:
                continue
            if index + 2 > len(data):
                break
            length = struct.unpack(">H", data[index : index + 2])[0]
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                height, width = struct.unpack(">HH", data[index + 3 : index + 7])
                return width, height
            index += length
    raise ValueError(f"unsupported or unreadable image format: {path}")


def require_files(root: Path, rel_paths: list[str]) -> list[str]:
    return [f"missing required package file: {rel}" for rel in rel_paths if not (root / rel).is_file()]


def validate_package(root: Path) -> list[str]:
    errors: list[str] = []
    required = [
        "00_manifest/SCENE_CANON.md",
        "00_manifest/SCENE_CANON.json",
        "00_manifest/SOURCE_APPEARANCE_DECOMPOSITION.md",
        "00_manifest/SOURCE_APPEARANCE_DECOMPOSITION.json",
        "00_manifest/ASSET_INDEX.md",
        "00_manifest/ASSET_MANIFEST.json",
        "00_manifest/actual_image_dimensions.json",
        "01_source_analysis/source_evidence_report.md",
        "01_source_analysis/conflict_report.md",
        "01_source_analysis/coverage_assessment.md",
        "08_4k_regeneration/4K_ASSET_REGENERATION_PROMPTS.md",
        "09_qa/QA_REPORT.md",
        "09_qa/failed_asset_log.md",
        "09_qa/look_contamination_report.md",
        "09_qa/4k_prompt_mapping_report.md",
    ]
    errors.extend(require_files(root, required))
    if errors:
        return errors

    canon_path = root / "00_manifest/SCENE_CANON.json"
    appearance_path = root / "00_manifest/SOURCE_APPEARANCE_DECOMPOSITION.json"
    manifest_path = root / "00_manifest/ASSET_MANIFEST.json"
    dimensions_path = root / "00_manifest/actual_image_dimensions.json"

    try:
        canon = read_json(canon_path)
        appearance = read_json(appearance_path)
        manifest = read_json(manifest_path)
        dimensions_index = read_json(dimensions_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"package JSON read failed: {exc}"]

    for instance, schema_name, label in [
        (canon, "scene_canon.schema.json", "SCENE_CANON.json"),
        (appearance, "appearance_decomposition.schema.json", "SOURCE_APPEARANCE_DECOMPOSITION.json"),
        (manifest, "asset_manifest.schema.json", "ASSET_MANIFEST.json"),
    ]:
        schema = read_json(REFERENCES_DIR / schema_name)
        errors.extend(f"{label}: {item}" for item in validate_schema_value(instance, schema, schema))

    if errors:
        return errors

    if not isinstance(dimensions_index, dict):
        errors.append("actual_image_dimensions.json must be an object keyed by asset_id")
        dimensions_index = {}

    scene_ids = {canon["scene_id"], appearance["scene_id"], manifest["scene_id"]}
    if len(scene_ids) != 1:
        errors.append("scene_id mismatch across canon, appearance, and manifest")

    canon_hash = sha256_file(canon_path)
    appearance_hash = sha256_file(appearance_path)
    completion_hash = canonical_json_hash(canon["canonical_completion_elements"])
    if manifest["canon_sha256"] != canon_hash:
        errors.append("manifest canon_sha256 does not match SCENE_CANON.json")
    if manifest["appearance_sha256"] != appearance_hash:
        errors.append("manifest appearance_sha256 does not match decomposition JSON")
    if manifest["completion_hash"] != completion_hash:
        errors.append("manifest completion_hash does not match canonical completion")
    if manifest["canon_revision"] != canon["canon_revision"]:
        errors.append("manifest canon_revision does not match Scene Canon")
    if manifest["appearance_revision"] != appearance["appearance_revision"]:
        errors.append("manifest appearance_revision does not match appearance decomposition")

    assets = manifest["assets"]
    asset_ids = [asset["asset_id"] for asset in assets]
    file_paths = [asset["file_path"] for asset in assets]
    if len(asset_ids) != len(set(asset_ids)):
        errors.append("asset IDs must be unique")
    if len(file_paths) != len(set(file_paths)):
        errors.append("asset file paths must be unique")

    asset_by_id = {asset["asset_id"]: asset for asset in assets}
    approved_machine: dict[str, dict[str, Any]] = {}
    for asset in assets:
        asset_id = asset["asset_id"]
        is_review = asset["asset_type"] == "human_review_overview_board"
        if is_review:
            if asset["is_machine_asset"]:
                errors.append(f"{asset_id}: human review board cannot be a machine asset")
            if asset["generation_mode"] != "approved_asset_composite":
                errors.append(f"{asset_id}: review board must use approved_asset_composite")
            if asset["four_k_prompt_id"] is not None:
                errors.append(f"{asset_id}: review board must not have a 4K prompt")
            continue

        if not asset["is_machine_asset"]:
            errors.append(f"{asset_id}: non-review asset must be a machine asset")
        if asset["generation_mode"] != "independent_full_frame":
            errors.append(f"{asset_id}: machine asset must be independent_full_frame")
        if not asset["independently_generated"] or asset["derived_from_multipanel"]:
            errors.append(f"{asset_id}: grid/contact-sheet crops are forbidden")
        if asset["assistant_qa_status"] != "approved":
            continue

        approved_machine[asset_id] = asset
        if asset["terminal_generation_call"] != "executed":
            errors.append(f"{asset_id}: terminal_generation_call must be executed before QA approval")
        if asset["generation_status"] not in {"generated", "regenerated"}:
            errors.append(f"{asset_id}: approved asset generation_status is not final")
        if not isinstance(asset["generation_turn"], int) or not isinstance(asset["inspection_turn"], int):
            errors.append(f"{asset_id}: generation and inspection turns must be recorded")
        elif asset["inspection_turn"] <= asset["generation_turn"]:
            errors.append(f"{asset_id}: later-turn visual QA must follow the terminal generation turn")
        if not asset["actual_dimensions_verified"]:
            errors.append(f"{asset_id}: actual dimensions are unverified")
        if any(asset["contamination_flags"].values()):
            errors.append(f"{asset_id}: contamination flags must all be false")
        for field, expected in [
            ("canon_sha256", canon_hash),
            ("appearance_sha256", appearance_hash),
            ("completion_hash", completion_hash),
        ]:
            if asset[field] != expected:
                errors.append(f"{asset_id}: {field} does not match frozen package state")
        if asset["scene_canon_version"] != manifest["canon_revision"]:
            errors.append(f"{asset_id}: stale Scene Canon version")
        if asset["neutral_appearance_version"] != manifest["appearance_revision"]:
            errors.append(f"{asset_id}: stale neutral appearance version")

        asset_path = root / asset["file_path"]
        if not asset_path.is_file():
            errors.append(f"{asset_id}: missing generated asset file {asset['file_path']}")
            continue
        actual_sha = sha256_file(asset_path)
        if asset["file_sha256"] != actual_sha:
            errors.append(f"{asset_id}: file_sha256 does not match the generated file")
        try:
            width, height = image_dimensions(asset_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        declared = asset["actual_pixel_dimensions"]
        if (declared["width"], declared["height"]) != (width, height):
            errors.append(f"{asset_id}: declared actual dimensions do not match file pixels")
        index_record = dimensions_index.get(asset_id)
        if index_record != {"file_path": asset["file_path"], "width": width, "height": height, "verified": True}:
            errors.append(f"{asset_id}: actual_image_dimensions.json is stale or unverified")
        if asset["native_4k_claim"]:
            target = asset["target_pixel_dimensions"]
            if not asset.get("native_4k_evidence"):
                errors.append(f"{asset_id}: native 4K claim lacks provenance evidence")
            if width < target["width"] or height < target["height"]:
                errors.append(f"{asset_id}: native 4K claim conflicts with actual pixels")

    prompt_records = manifest["four_k_prompt_records"]
    finalized = [record for record in prompt_records if record["status"] == "finalized_post_qa"]
    prompt_ids = [record["prompt_id"] for record in finalized]
    mapped_asset_ids = [record["asset_id"] for record in finalized]
    if len(prompt_ids) != len(set(prompt_ids)):
        errors.append("finalized 4K prompt IDs must be unique")
    if len(mapped_asset_ids) != len(set(mapped_asset_ids)):
        errors.append("each approved machine asset may have only one finalized 4K prompt")
    if set(mapped_asset_ids) != set(approved_machine):
        errors.append("approved machine assets and finalized 4K prompt mappings must match one-to-one")

    prompt_doc = (root / "08_4k_regeneration/4K_ASSET_REGENERATION_PROMPTS.md").read_text(encoding="utf-8")
    forbidden_allowed = {"relight", "restyle", "recolor", "recompose", "expand_scene", "redesign"}
    for record in finalized:
        asset_id = record["asset_id"]
        asset = approved_machine.get(asset_id)
        if not asset:
            continue
        if record["prompt_id"] not in prompt_doc:
            errors.append(f"{record['prompt_id']}: finalized prompt is missing from the Markdown deliverable")
        if record["primary_reference_asset_id"] != asset_id:
            errors.append(f"{record['prompt_id']}: heavy source or wrong asset is primary reference")
        if record["source_image"] != asset["file_path"]:
            errors.append(f"{record['prompt_id']}: source image path does not match asset")
        if record["source_dimensions"] != asset["actual_pixel_dimensions"]:
            errors.append(f"{record['prompt_id']}: source dimensions do not match asset")
        if record["source_asset_revision"] != asset["asset_revision"]:
            errors.append(f"{record['prompt_id']}: stale asset revision")
        if record["source_asset_sha256"] != asset["file_sha256"]:
            errors.append(f"{record['prompt_id']}: stale source asset hash")
        if record["source_canon_sha256"] != canon_hash or record["source_appearance_sha256"] != appearance_hash:
            errors.append(f"{record['prompt_id']}: stale canon or appearance hash")
        if record["source_completion_hash"] != completion_hash:
            errors.append(f"{record['prompt_id']}: stale completion hash")
        if asset["four_k_prompt_id"] != record["prompt_id"]:
            errors.append(f"{asset_id}: manifest four_k_prompt_id does not match prompt record")
        if forbidden_allowed & set(record["allowed_enhancements"]):
            errors.append(f"{record['prompt_id']}: allowed enhancements include redesign/look changes")
        prompt_text = record["regeneration_prompt_en"].lower()
        for phrase in ["primary and highest-priority", "do not restore", "do not redesign"]:
            if phrase not in prompt_text:
                errors.append(f"{record['prompt_id']}: prompt missing hard phrase {phrase!r}")

    if manifest["approved_machine_asset_count"] != len(approved_machine):
        errors.append("approved_machine_asset_count is incorrect")
    if manifest["four_k_prompt_mapping_count"] != len(finalized):
        errors.append("four_k_prompt_mapping_count is incorrect")
    if set(canon["generated_asset_index"]) != set(asset_ids):
        errors.append("Scene Canon generated_asset_index does not match manifest")
    if set(canon["four_k_prompt_index"]) != set(prompt_ids):
        errors.append("Scene Canon four_k_prompt_index does not match finalized prompts")

    if manifest["package_status"] == "packaged":
        if manifest["task_finalization_status"] != "complete":
            errors.append("packaged state requires task_finalization_status complete")
        if manifest["assistant_qa_status"] != "passed":
            errors.append("packaged state requires assistant QA passed")
        if canon["canon_freeze_status"] != "frozen" or canon["QA_status"] != "approved":
            errors.append("packaged state requires frozen, QA-approved Scene Canon")
        if appearance["appearance_freeze_status"] != "frozen":
            errors.append("packaged state requires frozen appearance decomposition")
        if canon["unresolved_hard_blockers"]:
            errors.append("packaged state cannot contain unresolved hard blockers")
        if any(item["status"] != "approved" for item in canon["canonical_completion_elements"]):
            errors.append("packaged state requires all Canonical Completion elements approved")
        if any(item["resolution_status"] in {"unresolved", "hard_blocker"} for item in canon["conflicts"]):
            errors.append("packaged state cannot contain unresolved conflicts")
        review_path = manifest["human_review_overview_board"]
        if not review_path or not (root / review_path).is_file():
            errors.append("packaged state requires a Human Review Overview Board file")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Scene Canon Asset Pack output directory.")
    parser.add_argument("package_root", type=Path)
    args = parser.parse_args()
    root = args.package_root.resolve()
    errors = validate_package(root)
    if errors:
        print("scene canon package validation: FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("scene canon package validation: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
