#!/usr/bin/env python3
"""Small local validator for the JSON-Schema keywords used by this package.

This avoids a runtime dependency on ``jsonschema`` while still validating the
checked-in contract files themselves. Unsupported keywords are annotations;
all structural and conditional keywords used by the package are implemented.
"""

from __future__ import annotations

import json
import math
import re
from datetime import date, datetime
from typing import Any
from urllib.parse import urlsplit


class SchemaViolation(ValueError):
    pass


SUPPORTED_KEYWORDS = {
    "$schema",
    "$id",
    "$ref",
    "$defs",
    "title",
    "description",
    "default",
    "type",
    "const",
    "enum",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "minItems",
    "maxItems",
    "uniqueItems",
    "contains",
    "minContains",
    "maxContains",
    "minLength",
    "maxLength",
    "pattern",
    "format",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "allOf",
    "anyOf",
    "oneOf",
    "not",
    "if",
    "then",
    "else",
}


def _assert_supported(schema: dict[str, Any], path: str) -> None:
    unsupported = sorted(set(schema) - SUPPORTED_KEYWORDS)
    if unsupported:
        raise SchemaViolation(f"{path}: unsupported JSON-Schema keywords {unsupported}")


def assert_schema_supported(schema: dict[str, Any] | bool, path: str = "$") -> None:
    """Recursively reject unsupported keywords, even in an untaken branch."""

    if isinstance(schema, bool):
        return
    if not isinstance(schema, dict):
        raise SchemaViolation(f"{path}: schema must be an object or boolean")
    _assert_supported(schema, path)
    for container_key in ("properties", "$defs"):
        container = schema.get(container_key, {})
        if isinstance(container, dict):
            for key, subschema in container.items():
                assert_schema_supported(subschema, f"{path}.{container_key}.{key}")
    for child_key in ("items", "contains", "not", "if", "then", "else", "additionalProperties"):
        subschema = schema.get(child_key)
        if isinstance(subschema, (dict, bool)):
            assert_schema_supported(subschema, f"{path}.{child_key}")
    for child_key in ("allOf", "anyOf", "oneOf"):
        children = schema.get(child_key, [])
        if isinstance(children, list):
            for index, subschema in enumerate(children):
                assert_schema_supported(subschema, f"{path}.{child_key}[{index}]")


def _resolve(root: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise SchemaViolation(f"external $ref is unsupported: {reference}")
    cursor: Any = root
    for raw in reference[2:].split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        if not isinstance(cursor, dict) or key not in cursor:
            raise SchemaViolation(f"unresolvable $ref: {reference}")
        cursor = cursor[key]
    if not isinstance(cursor, dict):
        raise SchemaViolation(f"$ref does not resolve to a schema: {reference}")
    return cursor


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (
            isinstance(value, int) and not isinstance(value, bool)
        ) or (
            isinstance(value, float) and math.isfinite(value)
        )
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _format_ok(value: str, format_name: str) -> bool:
    try:
        if format_name == "date-time":
            raw = value[:-1] + "+00:00" if value.endswith("Z") else value
            return datetime.fromisoformat(raw).tzinfo is not None
        if format_name == "date":
            date.fromisoformat(value)
            return True
        if format_name == "uri":
            parts = urlsplit(value)
            return bool(parts.scheme and (parts.netloc or parts.scheme == "file"))
    except (ValueError, TypeError):
        return False
    return True


def _is_unique(values: list[Any]) -> bool:
    try:
        rendered = [
            json.dumps(item, sort_keys=True, ensure_ascii=False, allow_nan=False)
            for item in values
        ]
    except (TypeError, ValueError, OverflowError):
        return False
    return len(rendered) == len(set(rendered))


def validate(instance: Any, schema: dict[str, Any] | bool, *, root: dict[str, Any] | None = None, path: str = "$") -> list[str]:
    if schema is True:
        return []
    if schema is False:
        return [f"{path}: boolean false schema rejects the instance"]
    if not isinstance(schema, dict):
        raise SchemaViolation(f"{path}: schema must be an object or boolean")
    root_schema = root or schema
    _assert_supported(schema, path)
    errors: list[str] = []
    if "$ref" in schema:
        return validate(instance, _resolve(root_schema, schema["$ref"]), root=root_schema, path=path)

    expected = schema.get("type")
    if expected is not None:
        expected_types = expected if isinstance(expected, list) else [expected]
        if not any(_type_ok(instance, item) for item in expected_types):
            return [f"{path}: expected type {expected_types}, got {type(instance).__name__}"]

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value {instance!r} is not in enum")

    if isinstance(instance, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                errors.append(f"{path}: missing required property {key!r}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(instance) - set(properties))
            for key in extra:
                errors.append(f"{path}: additional property {key!r} is forbidden")
        for key, subschema in properties.items():
            if key in instance:
                errors.extend(validate(instance[key], subschema, root=root_schema, path=f"{path}.{key}"))

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: needs at least {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: allows at most {schema['maxItems']} items")
        if schema.get("uniqueItems") and not _is_unique(instance):
            errors.append(f"{path}: items must be unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, (dict, bool)):
            for index, item in enumerate(instance):
                errors.extend(validate(item, item_schema, root=root_schema, path=f"{path}[{index}]"))
        contains_schema = schema.get("contains")
        if isinstance(contains_schema, (dict, bool)):
            matches = sum(
                1 for index, item in enumerate(instance)
                if not validate(item, contains_schema, root=root_schema, path=f"{path}[{index}]")
            )
            minimum = schema.get("minContains", 1)
            maximum = schema.get("maxContains")
            if matches < minimum:
                errors.append(f"{path}: contains matched {matches}, below minContains {minimum}")
            if maximum is not None and matches > maximum:
                errors.append(f"{path}: contains matched {matches}, above maxContains {maximum}")

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: string shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: string longer than {schema['maxLength']}")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append(f"{path}: string does not match {schema['pattern']!r}")
        if "format" in schema and not _format_ok(instance, schema["format"]):
            errors.append(f"{path}: invalid {schema['format']} format")

    if (
        isinstance(instance, int) and not isinstance(instance, bool)
    ) or (
        isinstance(instance, float) and math.isfinite(instance)
    ):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: value is below minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: value is above maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: value must exceed {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            errors.append(f"{path}: value must be below {schema['exclusiveMaximum']}")

    for subschema in schema.get("allOf", []):
        errors.extend(validate(instance, subschema, root=root_schema, path=path))
    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        matches = sum(1 for subschema in any_of if not validate(instance, subschema, root=root_schema, path=path))
        if matches < 1:
            errors.append(f"{path}: no anyOf branch matched")
    one_of = schema.get("oneOf")
    if isinstance(one_of, list):
        matches = sum(1 for subschema in one_of if not validate(instance, subschema, root=root_schema, path=path))
        if matches != 1:
            errors.append(f"{path}: oneOf matched {matches} branches, expected exactly 1")
    negated = schema.get("not")
    if isinstance(negated, (dict, bool)) and not validate(instance, negated, root=root_schema, path=path):
        errors.append(f"{path}: instance matches forbidden not schema")
    condition = schema.get("if")
    if isinstance(condition, dict):
        if not validate(instance, condition, root=root_schema, path=path):
            then_schema = schema.get("then")
            if isinstance(then_schema, dict):
                errors.extend(validate(instance, then_schema, root=root_schema, path=path))
        else:
            else_schema = schema.get("else")
            if isinstance(else_schema, dict):
                errors.extend(validate(instance, else_schema, root=root_schema, path=path))
    return errors
