#!/usr/bin/env python3
"""Validate opt-in aggregate schema/template parity without judging package availability."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


PAIRS = (
    ("ai-video-shot-script-director/references/shot_contract.schema.json", "ai-video-shot-script-director/references/shot_contract.template.json"),
    ("ai-video-shot-script-director/references/project_canon_manifest.schema.json", "ai-video-shot-script-director/references/project_canon_manifest.template.json"),
    ("ai-video-shot-script-director/references/manifest_update_receipt.schema.json", "ai-video-shot-script-director/references/manifest_update_receipt.template.json"),
    ("ai-video-global-look-lock/references/global_look_contract.schema.json", "ai-video-global-look-lock/references/global_look_contract.template.json"),
    ("ai-video-modular-storyboard/references/storyboard_manifest.schema.json", "ai-video-modular-storyboard/references/storyboard_manifest_template.json"),
    ("ai-video-timed-animatic-previs-director/references/previs_manifest.schema.json", "ai-video-timed-animatic-previs-director/references/previs_manifest_template.json"),
    ("ai-video-keyframe-continuity-pack/references/keyframe_manifest.schema.json", "ai-video-keyframe-continuity-pack/references/keyframe_manifest_template.json"),
    ("ai-video-keyframe-continuity-pack/references/boundary_supplement.schema.json", "ai-video-keyframe-continuity-pack/references/boundary_supplement.template.json"),
    ("ai-video-omni-reference-prompt-director/references/generation_unit_preflight.schema.json", "ai-video-omni-reference-prompt-director/references/generation_unit_preflight.template.json"),
    ("ai-video-omni-reference-prompt-director/references/canonical_ir.schema.json", "ai-video-omni-reference-prompt-director/references/canonical_ir_template.json"),
    ("ai-video-omni-reference-prompt-director/references/acceptance_gap_report.schema.json", "ai-video-omni-reference-prompt-director/references/acceptance_gap_report.template.json"),
    ("ai-video-omni-reference-prompt-director/references/reference_atlas_spec.schema.json", "ai-video-omni-reference-prompt-director/references/reference_atlas_spec.template.json"),
    ("ai-video-omni-reference-prompt-director/references/reference_atlas_receipt.schema.json", "ai-video-omni-reference-prompt-director/references/reference_atlas_receipt.template.json"),
)


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return False


def _resolve(root_schema: dict[str, Any], reference: str) -> Any:
    if not reference.startswith("#/"):
        raise ValueError(f"only local JSON Pointer refs are supported: {reference}")
    current: Any = root_schema
    for token in reference[2:].split("/"):
        key = token.replace("~1", "/").replace("~0", "~")
        current = current[key]
    return current


def validate_instance(instance: Any, schema: Any, root_schema: dict[str, Any], path: str = "$") -> list[str]:
    if schema is True:
        return []
    if schema is False:
        return [f"{path}: forbidden by false schema"]
    if not isinstance(schema, dict):
        return [f"{path}: invalid schema node"]
    if "$ref" in schema:
        try:
            target = _resolve(root_schema, schema["$ref"])
        except (KeyError, TypeError, ValueError) as exc:
            return [f"{path}: unresolved $ref {schema.get('$ref')}: {exc}"]
        return validate_instance(instance, target, root_schema, path)

    errors: list[str] = []
    if "not" in schema and not validate_instance(instance, schema["not"], root_schema, path):
        errors.append(f"{path}: value matched forbidden not schema")
    if "allOf" in schema:
        for branch in schema["allOf"]:
            errors.extend(validate_instance(instance, branch, root_schema, path))
    if "anyOf" in schema:
        branch_errors = [validate_instance(instance, branch, root_schema, path) for branch in schema["anyOf"]]
        if not any(not branch for branch in branch_errors):
            errors.append(f"{path}: no anyOf branch matched")
    if "oneOf" in schema:
        matches = sum(not validate_instance(instance, branch, root_schema, path) for branch in schema["oneOf"])
        if matches != 1:
            errors.append(f"{path}: expected exactly one oneOf match, got {matches}")
    if "if" in schema:
        condition_matches = not validate_instance(instance, schema["if"], root_schema, path)
        selected = schema.get("then") if condition_matches else schema.get("else")
        if selected is not None:
            errors.extend(validate_instance(instance, selected, root_schema, path))

    expected_type = schema.get("type")
    if expected_type is not None:
        allowed = [expected_type] if isinstance(expected_type, str) else expected_type
        if not isinstance(allowed, list) or not any(_type_matches(instance, item) for item in allowed if isinstance(item, str)):
            return errors + [f"{path}: expected type {expected_type}, got {type(instance).__name__}"]
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: value differs from const")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value not in enum")

    if isinstance(instance, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            for key in required:
                if key not in instance:
                    errors.append(f"{path}: missing required property {key}")
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, value in instance.items():
                child_path = f"{path}.{key}"
                if key in properties:
                    errors.extend(validate_instance(value, properties[key], root_schema, child_path))
                elif schema.get("additionalProperties") is False:
                    errors.append(f"{child_path}: additional property forbidden")
                elif isinstance(schema.get("additionalProperties"), dict):
                    errors.extend(validate_instance(value, schema["additionalProperties"], root_schema, child_path))
        if isinstance(schema.get("minProperties"), int) and len(instance) < schema["minProperties"]:
            errors.append(f"{path}: too few properties")
        if isinstance(schema.get("maxProperties"), int) and len(instance) > schema["maxProperties"]:
            errors.append(f"{path}: too many properties")

    if isinstance(instance, list):
        if isinstance(schema.get("minItems"), int) and len(instance) < schema["minItems"]:
            errors.append(f"{path}: too few items")
        if isinstance(schema.get("maxItems"), int) and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: too many items")
        if schema.get("uniqueItems") is True:
            encoded = [json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) for item in instance]
            if len(encoded) != len(set(encoded)):
                errors.append(f"{path}: items are not unique")
        if isinstance(schema.get("items"), dict) or isinstance(schema.get("items"), bool):
            for index, item in enumerate(instance):
                errors.extend(validate_instance(item, schema["items"], root_schema, f"{path}[{index}]"))
        if "contains" in schema and not any(not validate_instance(item, schema["contains"], root_schema, f"{path}[*]") for item in instance):
            errors.append(f"{path}: contains constraint not satisfied")

    if isinstance(instance, str):
        if isinstance(schema.get("minLength"), int) and len(instance) < schema["minLength"]:
            errors.append(f"{path}: string shorter than minLength")
        if isinstance(schema.get("maxLength"), int) and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: string longer than maxLength")
        if isinstance(schema.get("pattern"), str) and re.search(schema["pattern"], instance) is None:
            errors.append(f"{path}: string does not match pattern")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: above maximum")
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: not above exclusiveMinimum")
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            errors.append(f"{path}: not below exclusiveMaximum")
    return errors


def validate_pairs(suite_root: Path) -> list[str]:
    errors: list[str] = []
    for schema_rel, instance_rel in PAIRS:
        schema_path = suite_root / schema_rel
        instance_path = suite_root / instance_rel
        if not schema_path.is_file() or not instance_path.is_file():
            errors.append(f"missing schema/template pair: {schema_rel} | {instance_rel}")
            continue
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            instance = json.loads(instance_path.read_text(encoding="utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"cannot read schema/template pair {schema_rel}: {exc}")
            continue
        pair_errors = validate_instance(instance, schema, schema)
        errors.extend(f"{instance_rel}: {error}" for error in pair_errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite-root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    try:
        errors = validate_pairs(args.suite_root.resolve())
    except Exception as exc:
        print(f"ERROR: schema parity failed safely: {type(exc).__name__}: {exc}")
        return 2
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {len(PAIRS)} aggregate schema/template compatibility pairs conform")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
