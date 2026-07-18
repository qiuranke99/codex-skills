#!/usr/bin/env python3
"""Small stdlib JSON-Schema subset used by this package's bundled schemas."""

from __future__ import annotations

import json
import math
import re
from typing import Any


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
        current = current[token.replace("~1", "/").replace("~0", "~")]
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
            return validate_instance(instance, _resolve(root_schema, schema["$ref"]), root_schema, path)
        except (KeyError, TypeError, ValueError) as exc:
            return [f"{path}: unresolved $ref {schema.get('$ref')}: {exc}"]

    errors: list[str] = []
    if "not" in schema and not validate_instance(instance, schema["not"], root_schema, path):
        errors.append(f"{path}: value matched forbidden not schema")
    for branch in schema.get("allOf", []):
        errors.extend(validate_instance(instance, branch, root_schema, path))
    if "anyOf" in schema and not any(
        not validate_instance(instance, branch, root_schema, path) for branch in schema["anyOf"]
    ):
        errors.append(f"{path}: no anyOf branch matched")
    if "oneOf" in schema:
        matches = sum(not validate_instance(instance, branch, root_schema, path) for branch in schema["oneOf"])
        if matches != 1:
            errors.append(f"{path}: expected exactly one oneOf match, got {matches}")
    if "if" in schema:
        selected = schema.get("then") if not validate_instance(instance, schema["if"], root_schema, path) else schema.get("else")
        if selected is not None:
            errors.extend(validate_instance(instance, selected, root_schema, path))

    expected_type = schema.get("type")
    if expected_type is not None:
        allowed = [expected_type] if isinstance(expected_type, str) else expected_type
        if not isinstance(allowed, list) or not any(
            _type_matches(instance, item) for item in allowed if isinstance(item, str)
        ):
            return errors + [f"{path}: expected type {expected_type}, got {type(instance).__name__}"]
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: value differs from const")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value not in enum")

    if isinstance(instance, dict):
        for key in schema.get("required", []) if isinstance(schema.get("required", []), list) else []:
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
        if isinstance(schema.get("items"), (dict, bool)):
            for index, item in enumerate(instance):
                errors.extend(validate_instance(item, schema["items"], root_schema, f"{path}[{index}]"))
        if "contains" in schema and not any(
            not validate_instance(item, schema["contains"], root_schema, f"{path}[*]") for item in instance
        ):
            errors.append(f"{path}: contains constraint not satisfied")

    if isinstance(instance, str):
        if isinstance(schema.get("minLength"), int) and len(instance) < schema["minLength"]:
            errors.append(f"{path}: string shorter than minLength")
        if isinstance(schema.get("maxLength"), int) and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: string longer than maxLength")
        if isinstance(schema.get("pattern"), str) and re.search(schema["pattern"], instance) is None:
            errors.append(f"{path}: string does not match pattern")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        for keyword, failed, message in (
            ("minimum", lambda limit: instance < limit, "below minimum"),
            ("maximum", lambda limit: instance > limit, "above maximum"),
            ("exclusiveMinimum", lambda limit: instance <= limit, "not above exclusiveMinimum"),
            ("exclusiveMaximum", lambda limit: instance >= limit, "not below exclusiveMaximum"),
        ):
            if keyword in schema and failed(schema[keyword]):
                errors.append(f"{path}: {message}")
    return errors


__all__ = ["validate_instance"]
