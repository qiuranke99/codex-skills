#!/usr/bin/env python3
"""Validate a prompt-only reference-guided reconstruction JSON contract.

The validator checks deterministic contract consistency. It does not inspect
pixels, verify claimed provenance, grant human approval, generate or edit
images, or operate an external platform.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


class DuplicateJsonKeyError(ValueError):
    """Raised before a JSON object with duplicate keys can become a dict."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Duplicate JSON object key {key!r} is forbidden.")


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKeyError(key)
        result[key] = value
    return result


DEFAULT_PROTECTED_STRUCTURE = {
    "frame.composition",
    "frame.camera_intent",
    "frame.crop",
    "frame.aspect_ratio",
    "frame.perspective",
    "frame.perspective_system",
    "structure.spatial_layout",
    "structure.layout",
    "structure.object_count",
    "structure.position",
    "structure.relative_scale",
    "structure.scale",
    "structure.topology",
    "structure.occlusion",
}

ATTRIBUTE_ALIASES = {
    "composition": "frame.composition",
    "camera": "frame.camera_intent",
    "camera_intent": "frame.camera_intent",
    "crop": "frame.crop",
    "aspect_ratio": "frame.aspect_ratio",
    "perspective": "frame.perspective",
    "perspective_system": "frame.perspective_system",
    "spatial_layout": "structure.spatial_layout",
    "layout": "structure.layout",
    "object_count": "structure.object_count",
    "position": "structure.position",
    "relative_scale": "structure.relative_scale",
    "scale": "structure.scale",
    "topology": "structure.topology",
    "occlusion": "structure.occlusion",
}

REQUIRED_REMOVAL_CLEANUP = (
    "cast_shadows",
    "reflections",
    "contact_traces",
    "occlusion_residue",
    "revealed_background",
    "reference_reintroduction",
)

VALID_ASSET_KINDS = {
    "target",
    "reference",
    "structure_master",
    "candidate_result",
    "exact_asset",
    "mask",
}

VALID_STAGE_KINDS = {
    "pixel",
    "local",
    "isomorphic",
    "structure",
    "realism",
    "composite",
    "blocked",
}

VALID_ROLE_STATES = {"known", "inferred", "chosen", "unknown"}
VALID_CONTAMINATION_RISKS = {"low", "medium", "high"}
PROMPT_ONLY_EXECUTION_BOUNDARY = "manual_external_prompt_only"
VALID_DELIVERY_STATES = {"prompt_plan", "imported_external_candidate"}
VALID_EXTERNAL_RESULT_ORIGINS = {"user_manual_external_generation"}
VALID_RESOLUTION_FACT_STATES = {"known", "observed", "user_reported", "unknown"}
VALID_DIMENSION_EVIDENCE_TYPES = {
    "none",
    "authoritative_record",
    "inspected_file_metadata",
    "user_report",
}
DIMENSION_EVIDENCE_TYPE_BY_FACT_STATE = {
    "unknown": "none",
    "known": "authoritative_record",
    "observed": "inspected_file_metadata",
    "user_reported": "user_report",
}
VALID_STATUSES = {
    "prompt_package_ready",
    "blocked_missing_evidence",
    "bounded_proxy_only",
    "structure_master_candidate",
    "candidate_unapproved",
    "qa_failed_directional_retry_ready",
}
BLOCKED_STATUSES = {"blocked_missing_evidence", "bounded_proxy_only"}
IMPORTED_CANDIDATE_STATUSES = {
    "structure_master_candidate",
    "candidate_unapproved",
    "qa_failed_directional_retry_ready",
}

TOP_LEVEL_KEYS = {
    "version",
    "target_id",
    "execution_boundary",
    "delivery_state",
    "external_result_provenance",
    "platform_parameter_guidance",
    "direct_copy_prompts",
    "assets",
    "intent",
    "authority",
    "reference_permissions",
    "stages",
    "truth_sensitive",
    "status",
    "protected_structure",
    "user_request",
    "notes",
}
ASSET_KEYS = {
    "id",
    "kind",
    "approved",
    "contamination_risk",
    "exact_attributes",
}
PROVENANCE_KEYS = {"result_id", "origin", "imported_by_user", "provenance"}
PLATFORM_PARAMETER_GUIDANCE_KEYS = {
    "semantic_target",
    "prompt_guarantees_dimensions",
    "dimensions_fact_state",
    "dimensions_evidence_type",
    "actual_pixel_dimensions",
    "settings_evidence",
}
PIXEL_DIMENSION_KEYS = {"width", "height"}
INTENT_KEYS = {"preserve_all", "remove", "explicit_exceptions"}
EXCEPTION_KEYS = {"entity", "cleanup"}
AUTHORITY_KEYS = {
    "attribute",
    "primary",
    "allow",
    "deny",
    "role_state",
    "evidence",
    "confidence",
    "conflicts",
    "missingness",
    "unresolved",
    "reason",
}
REFERENCE_PERMISSION_KEYS = {
    "asset_id",
    "role_state",
    "role_evidence",
    "allow_attributes",
    "deny_attributes",
    "allow_entities",
    "deny_entities",
}
STAGE_KEYS = {"id", "kind", "inputs", "target_reuse", "base_stage_id", "reason"}
TARGET_REUSE_KEYS = {
    "justification",
    "allowed_attributes",
    "deny_protected_structure",
}
TRUTH_SENSITIVE_KEYS = {"attribute", "required_exact", "evidence_ids"}
UNBOUNDED_ATTRIBUTE_ROOTS = {
    "*",
    "all",
    "any",
    "everything",
    "unrestricted",
    "reference",
    "style",
    "attribute",
    "attributes",
    "content",
    "image",
    "global",
    "whole",
    "whole_image",
    "entire",
    "entire_image",
    "full",
    "full_image",
    "universal",
    "unlimited",
}
BOUNDED_WILDCARD_ROOTS = {
    "appearance",
    "construction",
    "geometry",
    "graphics",
    "identity",
}
ATTRIBUTE_FAMILY_ROOTS = BOUNDED_WILDCARD_ROOTS | {
    "frame",
    "structure",
    "protected_structure",
}

REQUIRED_AUTHORITY_BY_STAGE = {
    "pixel": {"frame.composition"},
    "local": {"frame.composition"},
    "isomorphic": {"frame.composition"},
    "structure": {"frame.composition"},
    "realism": {"frame.composition"},
}

EVIDENCE_STAGE_KINDS_BY_ASSET_KIND = {
    "target": {"pixel", "local", "isomorphic", "realism", "composite"},
    "reference": {"local", "isomorphic", "realism", "composite"},
    "structure_master": {"realism", "composite"},
    "exact_asset": {"composite"},
    "mask": set(),
}

ALLOWED_ASSET_KINDS_BY_STAGE = {
    "pixel": {"target", "mask"},
    "local": {"target", "reference", "mask"},
    "isomorphic": {"target", "reference", "mask"},
    "structure": {"target", "mask"},
    "realism": {"structure_master", "reference", "target", "mask"},
    "composite": {"target", "structure_master", "reference", "exact_asset", "mask"},
}

_DIMENSION_CLAIM = (
    r"(?:native[-\s]+4k|true[-\s]+4k|4k(?:[-\s]+(?:pixels?|resolution|output))?|"
    r"exact[-\s]+pixel[-\s]+dimensions?|exact[-\s]+dimensions?|"
    r"\d{3,5}\s*(?:x|×)\s*\d{3,5}(?:\s*(?:px|pixels?))?|"
    r"\d{3,5}\s*(?:px|pixels?))"
)
DIMENSION_CLAIM_RE = re.compile(_DIMENSION_CLAIM, re.IGNORECASE)
DIMENSION_CLAUSE_SPLIT_RE = re.compile(
    r"(?:[\r\n.!?;。！？；]+|\b(?:but|however|yet|whereas|although|though)\b|(?:但是|然而|不过|但))",
    re.IGNORECASE,
)
NEGATED_DIMENSION_COMMITMENT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bno\s+(?:(?:known|available|documented)\s+)?(?:prompt|setting|platform|instruction|wording|text|parameter|configuration|control)\b.{0,40}?\b(?:guarantee(?:s|d)?|ensure(?:s|d)?|promise(?:s|d)?|certif(?:y|ies|ied))\b",
        r"\b(?:there\s+is\s+)?no\s+(?:absolute\s+)?(?:guarantee|assurance|promise)\b",
        r"\b(?:(?:absolutely|definitely|certainly)\s+)?(?:do(?:es)?|did|can|could|will|would|shall|should|may|might)\s+not\s+(?:always\s+)?(?:be\s+)?(?:guarantee(?:s|d)?|ensure(?:s|d)?|promise(?:s|d)?|certif(?:y|ies|ied)|yields?|produces?|delivers?|returns?|renders?|provides?|receives?)\b",
        r"\b(?:(?:absolutely|definitely|certainly)\s+)?(?:cannot|can't|never)\s+(?:be\s+)?(?:guarantee(?:s|d)?|ensure(?:s|d)?|promise(?:s|d)?|certif(?:y|ies|ied)|yields?|produces?|delivers?|returns?|renders?|provides?|receives?)\b",
        r"\b(?:is|are|was|were|be|being)\s+(?:not|never)\s+(?:guaranteed|ensured|promised|certified)\b",
        r"\bnot\s+necessarily\s+(?:guarantee(?:d)?|ensure(?:d)?|promise(?:d)?|certif(?:y|ied)|yield|produce|deliver|return|render|provide|receive)\b",
        r"\bwithout\s+(?:an?\s+)?(?:guarantee|assurance|promise)\b",
        r"\bnon[-\s]+guaranteed\b",
        r"没有任何[^，。！？；\r\n]{0,32}?(?:保证|确保|承诺|认证)",
        r"(?:没有|无)(?:任何)?(?:保证|确保|承诺|认证)",
        r"(?:绝对|肯定)?(?:无法|不能|不会|未能|不一定|不)(?:(?:再|总是|总|始终|每次|一定|必然|真正|直接|自动|稳定|可靠|都|能|会|可以)\s*){0,4}(?:保证|确保|承诺|认证|产出|输出|生成|达到|提供|得到|为|是)",
    )
)
EXPLICIT_AFFIRMATIVE_DIMENSION_COMMITMENT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:guarantee(?:s|d|ing)?|ensure(?:s|d|ing)?|promise(?:s|d|ing)?|certif(?:y|ies|ied|ying))\b",
        r"\b(?:will|shall)\s+(?:always\s+)?(?:receive|be|output|produce|yield|return|render|deliver|provide)\b",
        r"\b(?:prompt|setting|instruction|wording|text|result|output|platform)\s+(?:always\s+)?(?:yields?|produces?|delivers?|returns?|renders?|provides?|certifies?)\b",
        r"\bmust\s+(?:be|output|produce|yield|return|render|deliver|provide|receive)\b",
        r"(?:保证|确保|承诺|认证|必为|必定|(?<!不)一定(?:会)?|绝对)",
    )
)
DETERMINISTIC_DIMENSION_CUE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:always|every\s+time|without\s+(?:any\s+)?exception|certainly|definitely|inevitably)\b",
        r"\bregardless\s+of\s+(?:the\s+)?(?:platform(?:\s+settings?)?|settings?|controls?|process)\b",
        r"\birrespective\s+of\s+(?:the\s+)?(?:platform(?:\s+(?:settings?|controls?))?|settings?|controls?|process)\b",
        r"\bindependent\s+of\s+(?:the\s+)?(?:platform(?:\s+(?:settings?|controls?))?|settings?|controls?|process)\b",
        r"\bin\s+all\s+cases\b",
        r"\bno\s+matter\s+(?:(?:what|how|which)\s+)?(?:the\s+)?(?:platform(?:\s+(?:settings?|controls?))?|settings?|controls?|process)\b",
        r"(?:每次|无一例外|毫无例外|始终|总是|无论(?:平台)?(?:设置|控制|流程)(?:如何|怎样|怎么)?|不受(?:平台)?(?:设置|控制|流程)(?:的)?影响|在所有情况下)",
    )
)
UNVERIFIED_DECLARATIVE_OUTPUT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        (
            r"\b(?:the\s+)?(?:exact\s+)?(?:output|result)"
            r"(?:\s+(?:pixel\s+)?dimensions?)?\s+(?:is|are)\s+"
            r"(?:exact\s+)?" + _DIMENSION_CLAIM
        ),
        r"(?:输出|结果)(?:为|是)(?:原生|真正)?\s*4K",
        r"(?:精确)?(?:输出|结果)(?:像素)?尺寸(?:为|是)\s*\d{3,5}\s*(?:x|×)\s*\d{3,5}(?:\s*(?:px|像素))?",
    )
)
CATEGORICAL_DECLARATIVE_OUTPUT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:the\s+)?(?:output|result)\s+(?:is|are)\s+(?:native[-\s]+|true[-\s]+)?4k\b",
        r"(?:输出|结果)(?:为|是)(?:原生|真正)?\s*4K",
    )
)
DECLARATIVE_OUTPUT_DIMENSION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        (
            r"\b(?:the\s+)?(?:exact\s+)?(?:output|result)(?:\s+pixel)?\s+"
            r"dimensions?\s+(?:is|are)\s+"
            r"(\d{3,5})\s*(?:x|×)\s*(\d{3,5})(?:\s*(?:px|pixels?))?\b"
        ),
        (
            r"(?:输出|结果)(?:像素)?尺寸(?:为|是)\s*"
            r"(\d{3,5})\s*(?:x|×)\s*(\d{3,5})(?:\s*(?:px|像素))?"
        ),
    )
)
INSPECTED_FILE_DIMENSION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        (
            r"\b(?:the\s+)?inspected\s+(?:file|image|picture)(?:'s)?\s+"
            r"(?:pixel\s+)?dimensions?\s+(?:is|are|was|were)\s+"
            r"(\d{3,5})\s*(?:x|×)\s*(\d{3,5})(?:\s*(?:px|pixels?))?\b"
        ),
        (
            r"(?:(?:经检查|已检查|经检视|检查所得|检查到)[，,\s]*|"
            r"(?:经检查的|已检查的|检查的))"
            r"(?:文件|图像|图片)(?:的)?(?:像素)?尺寸(?:为|是|：|:)\s*"
            r"(\d{3,5})\s*(?:x|×)\s*(\d{3,5})(?:\s*(?:px|像素))?"
        ),
    )
)
AUTHORITATIVE_INTERNAL_DIRECTION_RE = re.compile(
    r"(?<![a-z0-9_])(?:image_gen__imagegen|image2gen|imagegen)(?![a-z0-9_])|"
    r"\bcodex\b|\b(?:this|the)\s+skill\b|"
    r"\bskill\b\s*(?::|,|\b(?:must|should|shall|will|can|cannot|to)\b)|"
    r"\$?reference-guided-image-reconstruction-director\b",
    re.IGNORECASE,
)
DIMENSION_MISSINGNESS_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bno\s+(?:actual\s+)?(?:pixel\s+)?dimensions?\s+(?:are\s+)?(?:known|evidenced|observed|reported|available|established)\b",
        r"\b(?:actual\s+)?(?:pixel\s+)?dimensions?\s+(?:are|remain|is)\s+(?:unknown|unevidenced|unobserved|unreported|unavailable|missing|not\s+known|not\s+evidenced)\b",
        r"\b(?:dimensions?|pixel\s+size)\s+(?:have|has)\s+not\s+been\s+(?:observed|reported|established|verified|evidenced)\b",
        r"(?:像素)?尺寸(?:未知|不详|未观察|未报告|未确认|尚未确定|没有证据|无证据)",
        r"(?:没有|无)(?:任何)?(?:像素)?尺寸(?:证据|记录)",
    )
)


def _issue(bucket: list[dict[str, str]], code: str, message: str, path: str) -> None:
    bucket.append({"code": code, "message": message, "path": path})


def _reject_unknown_fields(
    value: dict[str, Any],
    allowed: set[str],
    path: str,
    errors: list[dict[str, str]],
) -> None:
    for key in sorted(set(value) - allowed):
        _issue(
            errors,
            "E_UNKNOWN_FIELD",
            f"Field {key!r} is not allowed in this structured object.",
            f"{path}.{key}",
        )


def _actual_dimension_pair(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, dict):
        return None
    width = value.get("width")
    height = value.get("height")
    if (
        not isinstance(width, int)
        or isinstance(width, bool)
        or width <= 0
        or not isinstance(height, int)
        or isinstance(height, bool)
        or height <= 0
    ):
        return None
    return width, height


def _dimension_text_violations(
    text: str,
    *,
    fact_state: str,
    evidence_type: str,
    actual_dimensions: Any,
) -> set[str]:
    violations: set[str] = set()
    actual_pair = _actual_dimension_pair(actual_dimensions)
    for clause in DIMENSION_CLAUSE_SPLIT_RE.split(text):
        if not DIMENSION_CLAIM_RE.search(clause):
            continue
        inspected_pairs = {
            (int(match.group(1)), int(match.group(2)))
            for pattern in INSPECTED_FILE_DIMENSION_PATTERNS
            for match in pattern.finditer(clause)
        }
        declarative_output_pairs = {
            (int(match.group(1)), int(match.group(2)))
            for pattern in DECLARATIVE_OUTPUT_DIMENSION_PATTERNS
            for match in pattern.finditer(clause)
        }
        if inspected_pairs and (
            fact_state != "observed"
            or evidence_type != "inspected_file_metadata"
            or actual_pair is None
            or inspected_pairs != {actual_pair}
        ):
            violations.add("inspected_file_binding")
        if declarative_output_pairs and fact_state != "unknown" and (
            actual_pair is None or declarative_output_pairs != {actual_pair}
        ):
            violations.add("declarative_output_binding")
        remaining = clause
        has_explicit_negation = False
        for pattern in NEGATED_DIMENSION_COMMITMENT_PATTERNS:
            if pattern.search(clause):
                has_explicit_negation = True
            remaining = pattern.sub(" ", remaining)
        if any(
            pattern.search(remaining)
            for pattern in EXPLICIT_AFFIRMATIVE_DIMENSION_COMMITMENT_PATTERNS
        ):
            violations.add("commitment")
            continue
        if not has_explicit_negation and any(
            pattern.search(remaining)
            for pattern in DETERMINISTIC_DIMENSION_CUE_PATTERNS
        ):
            violations.add("commitment")
            continue
        if any(
            pattern.search(remaining)
            for pattern in CATEGORICAL_DECLARATIVE_OUTPUT_PATTERNS
        ):
            violations.add("commitment")
            continue
        if fact_state == "unknown" and (
            declarative_output_pairs
            or any(
                pattern.search(remaining)
                for pattern in UNVERIFIED_DECLARATIVE_OUTPUT_PATTERNS
            )
        ):
            violations.add("commitment")
    return violations


def _has_authoritative_internal_direction(text: str) -> bool:
    return bool(AUTHORITATIVE_INTERNAL_DIRECTION_RE.search(text))


def _has_dimension_missingness_claim(text: str) -> bool:
    return any(pattern.search(text) for pattern in DIMENSION_MISSINGNESS_PATTERNS)


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicate: set[str] = set()
    for value in values:
        if value in seen:
            duplicate.add(value)
        seen.add(value)
    return duplicate


def _canonical_attribute(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip().lower().replace("/", ".").replace(":", ".")
    parts: list[str] = []
    for raw_part in text.split("."):
        if raw_part == "*":
            parts.append("*")
            continue
        part = re.sub(r"[^a-z0-9*]+", "_", raw_part).strip("_")
        if part:
            parts.append(part)
    canonical = ".".join(parts)
    return ATTRIBUTE_ALIASES.get(canonical, canonical)


def _string_list(
    value: Any,
    path: str,
    errors: list[dict[str, str]],
    *,
    required_key: bool = False,
    strip_values: bool = True,
) -> list[str]:
    if value is None and not required_key:
        return []
    if not isinstance(value, list):
        _issue(errors, "E_EXPECTED_ARRAY", "Expected an array of strings.", path)
        return []
    output: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            _issue(
                errors,
                "E_EXPECTED_STRING",
                "Expected a non-empty string.",
                f"{path}[{index}]",
            )
        else:
            output.append(item.strip() if strip_values else item)
    return output


def _required_string_list(
    owner: dict[str, Any],
    key: str,
    path: str,
    errors: list[dict[str, str]],
) -> list[str]:
    if key not in owner:
        _issue(errors, "E_REQUIRED_FIELD", f"Required field {key!r} is missing.", f"{path}.{key}")
        return []
    return _string_list(owner.get(key), f"{path}.{key}", errors, required_key=True)


def _attribute_list(
    owner: dict[str, Any],
    key: str,
    path: str,
    errors: list[dict[str, str]],
    *,
    required_key: bool = False,
    allow_global_umbrella: bool = False,
) -> list[str]:
    if required_key and key not in owner:
        _issue(errors, "E_REQUIRED_FIELD", f"Required field {key!r} is missing.", f"{path}.{key}")
        return []
    raw_values = _string_list(
        owner.get(key, []),
        f"{path}.{key}",
        errors,
        required_key=required_key,
        strip_values=False,
    )
    output: list[str] = []
    for index, raw_value in enumerate(raw_values):
        canonical = _validated_attribute_scope(
            raw_value,
            f"{path}.{key}[{index}]",
            errors,
            allow_global_umbrella=allow_global_umbrella,
        )
        if canonical:
            output.append(canonical)
    return output


def _raw_scope_grammar_valid(
    raw_scope: str, *, allow_global_umbrella: bool = False
) -> bool:
    if raw_scope == "*":
        return allow_global_umbrella
    if raw_scope != raw_scope.strip() or raw_scope != raw_scope.lower():
        return False
    if raw_scope.count("*") > 1 or (
        "*" in raw_scope and not raw_scope.endswith(".*")
    ):
        return False
    base = raw_scope[:-2] if raw_scope.endswith(".*") else raw_scope
    segments = base.split(".") if base else []
    snake_segment = r"[a-z0-9]+(?:_[a-z0-9]+)*"
    if not segments or any(
        not re.fullmatch(snake_segment, segment, flags=re.ASCII)
        for segment in segments
    ):
        return False
    return (
        len(segments) >= 2
        or segments[0] in ATTRIBUTE_FAMILY_ROOTS
        or raw_scope in ATTRIBUTE_ALIASES
        or raw_scope.endswith(".*")
    )


def _validated_attribute_scope(
    value: Any,
    path: str,
    errors: list[dict[str, str]],
    *,
    allow_global_umbrella: bool = False,
) -> str:
    if not isinstance(value, str) or not value:
        _issue(
            errors,
            "E_INVALID_ATTRIBUTE_TOKEN",
            f"Attribute token {value!r} has no semantic content.",
            path,
        )
        return ""
    if not _raw_scope_grammar_valid(
        value, allow_global_umbrella=allow_global_umbrella
    ):
        _issue(
            errors,
            "E_ATTRIBUTE_SCOPE_GRAMMAR",
            (
                "Raw attribute scope must use lowercase ASCII dotted snake_case as a "
                "recognized family root, documented alias, or qualified path, with at "
                "most one trailing '.*'; global '*' is deny-only."
            ),
            path,
        )
        # Preserve the historical unlimited-allow diagnostic for the exact
        # global token, but never canonicalize a malformed scope.
        return "*" if value == "*" else ""
    return ATTRIBUTE_ALIASES.get(value, value)


def _normalize_enum(
    value: Any,
    allowed: set[str],
    path: str,
    errors: list[dict[str, str]],
    code: str,
) -> str:
    if not isinstance(value, str):
        _issue(errors, code, f"Expected one of {sorted(allowed)}.", path)
        return ""
    normalized = value.strip().lower()
    if normalized not in allowed:
        _issue(errors, code, f"Expected one of {sorted(allowed)}; got {value!r}.", path)
        return normalized
    return normalized


def _is_protected(attribute: str, protected_patterns: set[str]) -> bool:
    attribute = _canonical_attribute(attribute)
    if not attribute:
        return False
    if attribute in {"protected_structure", "protected_structure.*"}:
        return True
    if attribute == "frame" or attribute.startswith("frame."):
        return True
    if attribute == "structure" or attribute.startswith("structure."):
        return True
    for protected in protected_patterns:
        if _patterns_overlap(attribute, protected, protected_patterns, allow_umbrella=False):
            return True
    return False


def _patterns_overlap(
    first: str,
    second: str,
    protected_patterns: set[str],
    *,
    allow_umbrella: bool = True,
) -> bool:
    first = _canonical_attribute(first)
    second = _canonical_attribute(second)
    if not first or not second:
        return False
    if allow_umbrella and first in {"protected_structure", "protected_structure.*"}:
        return _is_protected(second, protected_patterns)
    if allow_umbrella and second in {"protected_structure", "protected_structure.*"}:
        return _is_protected(first, protected_patterns)
    return _basic_pattern_covers(first, second) or _basic_pattern_covers(second, first)


def _scope_base(scope: str) -> str:
    return scope[:-2] if scope.endswith(".*") else scope


def _basic_pattern_covers(cover: str, item: str) -> bool:
    if cover == "*" or cover == item:
        return True
    cover_base = _scope_base(cover)
    item_base = _scope_base(item)
    cover_is_family = cover.endswith(".*") or cover in ATTRIBUTE_FAMILY_ROOTS
    return cover_is_family and (
        item_base == cover_base or item_base.startswith(cover_base + ".")
    )


def _pattern_covers(
    cover: str,
    item: str,
    protected_patterns: set[str],
) -> bool:
    cover = _canonical_attribute(cover)
    item = _canonical_attribute(item)
    if not cover or not item:
        return False
    if cover in {"protected_structure", "protected_structure.*"}:
        return _is_protected(item, protected_patterns)
    return _basic_pattern_covers(cover, item)


def _permission_matches(
    patterns: Iterable[str],
    attribute: str,
    protected_patterns: set[str],
) -> bool:
    return any(_pattern_covers(pattern, attribute, protected_patterns) for pattern in patterns)


def _attribute_root(attribute: str) -> str:
    canonical = _canonical_attribute(attribute)
    return canonical.split(".", 1)[0] if canonical else ""


def _is_unbounded_attribute_scope(attribute: str) -> bool:
    """Return whether a scope names a generic, effectively unlimited root."""

    canonical = _canonical_attribute(attribute)
    if not canonical:
        return False
    root = _attribute_root(canonical)
    if root in UNBOUNDED_ATTRIBUTE_ROOTS:
        return True
    return "*" in canonical and root not in BOUNDED_WILDCARD_ROOTS


def _is_concrete_attribute_scope(attribute: str) -> bool:
    """Target reuse must name a concrete leaf-like scope, never a wildcard/root grant."""

    canonical = _canonical_attribute(attribute)
    return (
        bool(canonical)
        and "." in canonical
        and "*" not in canonical
        and not _is_unbounded_attribute_scope(canonical)
    )


def validate_contract(contract: Any) -> dict[str, Any]:
    """Return a machine-readable validation result for an in-memory contract."""

    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    normalized_exceptions: list[dict[str, Any]] = []

    if not isinstance(contract, dict):
        _issue(errors, "E_CONTRACT_TYPE", "The contract root must be an object.", "$")
        return _result(errors, warnings, normalized_exceptions, 0, 0, 0, 0, "")

    _reject_unknown_fields(contract, TOP_LEVEL_KEYS, "$", errors)

    required_top_level = (
        "execution_boundary",
        "delivery_state",
        "external_result_provenance",
        "platform_parameter_guidance",
        "assets",
        "intent",
        "authority",
        "reference_permissions",
        "stages",
        "truth_sensitive",
        "status",
    )
    for key in required_top_level:
        if key not in contract:
            _issue(errors, "E_REQUIRED_TOP_LEVEL", f"Required top-level field {key!r} is missing.", f"$.{key}")

    if "version" in contract and (
        not isinstance(contract.get("version"), str) or not contract["version"].strip()
    ):
        _issue(errors, "E_VERSION_TYPE", "version must be a non-empty string when present.", "$.version")
    for descriptive_key in ("user_request", "notes"):
        if descriptive_key in contract and not isinstance(contract.get(descriptive_key), str):
            _issue(
                errors,
                "E_NON_AUTHORITATIVE_TEXT_TYPE",
                f"{descriptive_key} must be a string and never grants execution authority.",
                f"$.{descriptive_key}",
            )

    platform_guidance_hint = contract.get("platform_parameter_guidance")
    raw_dimension_fact_state = (
        platform_guidance_hint.get("dimensions_fact_state")
        if isinstance(platform_guidance_hint, dict)
        else None
    )
    raw_dimension_evidence_type = (
        platform_guidance_hint.get("dimensions_evidence_type")
        if isinstance(platform_guidance_hint, dict)
        else None
    )
    dimension_fact_state_hint = (
        raw_dimension_fact_state.strip().lower()
        if isinstance(raw_dimension_fact_state, str)
        else ""
    )
    dimension_evidence_type_hint = (
        raw_dimension_evidence_type.strip().lower()
        if isinstance(raw_dimension_evidence_type, str)
        else ""
    )
    actual_dimensions_hint = (
        platform_guidance_hint.get("actual_pixel_dimensions")
        if isinstance(platform_guidance_hint, dict)
        else None
    )

    direct_copy_prompts_value = contract.get("direct_copy_prompts", [])
    if not isinstance(direct_copy_prompts_value, list):
        _issue(
            errors,
            "E_DIRECT_COPY_PROMPTS_TYPE",
            "direct_copy_prompts must be an array of prompt strings when present.",
            "$.direct_copy_prompts",
        )
        direct_copy_prompts: list[Any] = []
    else:
        direct_copy_prompts = direct_copy_prompts_value
    for index, prompt in enumerate(direct_copy_prompts):
        path = f"$.direct_copy_prompts[{index}]"
        if not isinstance(prompt, str) or not prompt.strip():
            _issue(
                errors,
                "E_DIRECT_COPY_PROMPT_TYPE",
                "Each direct-copy prompt must be a non-empty string.",
                path,
            )
        else:
            if _has_authoritative_internal_direction(prompt):
                _issue(
                    errors,
                    "E_AUTHORITATIVE_OUTPUT_INTERNAL_DIRECTION",
                    (
                        "Authoritative output text cannot name internal image tools or "
                        "direct Codex or this Skill to act."
                    ),
                    path,
                )
            dimension_text_violations = _dimension_text_violations(
                prompt,
                fact_state=dimension_fact_state_hint,
                evidence_type=dimension_evidence_type_hint,
                actual_dimensions=actual_dimensions_hint,
            )
            if "commitment" in dimension_text_violations:
                _issue(
                    errors,
                    "E_PROMPT_DIMENSION_GUARANTEE",
                    (
                        "A direct-copy prompt cannot promise native 4K or exact pixel "
                        "dimensions, or present an unevidenced output size as fact."
                    ),
                    path,
                )
            if "inspected_file_binding" in dimension_text_violations:
                _issue(
                    errors,
                    "E_INSPECTED_FILE_DIMENSION_BINDING",
                    (
                        "An inspected-file dimension fact requires observed + "
                        "inspected_file_metadata and exact agreement with "
                        "actual_pixel_dimensions."
                    ),
                    path,
                )
            if "declarative_output_binding" in dimension_text_violations:
                _issue(
                    errors,
                    "E_DECLARATIVE_OUTPUT_DIMENSION_BINDING",
                    (
                        "A declarative output/result dimension fact must exactly "
                        "match actual_pixel_dimensions for a non-unknown fact state."
                    ),
                    path,
                )

    platform_guidance_value = contract.get("platform_parameter_guidance")
    resolution_fact_state = ""
    if not isinstance(platform_guidance_value, dict):
        _issue(
            errors,
            "E_PLATFORM_PARAMETER_GUIDANCE_TYPE",
            "platform_parameter_guidance must be an object.",
            "$.platform_parameter_guidance",
        )
        platform_guidance: dict[str, Any] = {}
    else:
        platform_guidance = platform_guidance_value
        _reject_unknown_fields(
            platform_guidance,
            PLATFORM_PARAMETER_GUIDANCE_KEYS,
            "$.platform_parameter_guidance",
            errors,
        )
    for key in PLATFORM_PARAMETER_GUIDANCE_KEYS:
        if key not in platform_guidance:
            _issue(
                errors,
                "E_REQUIRED_FIELD",
                f"platform_parameter_guidance.{key} is required.",
                f"$.platform_parameter_guidance.{key}",
            )
    semantic_target = platform_guidance.get("semantic_target")
    if not isinstance(semantic_target, str) or not semantic_target.strip():
        _issue(
            errors,
            "E_RESOLUTION_SEMANTIC_TARGET",
            "semantic_target must be a non-empty resolution intent string.",
            "$.platform_parameter_guidance.semantic_target",
        )
    else:
        if _has_authoritative_internal_direction(semantic_target):
            _issue(
                errors,
                "E_AUTHORITATIVE_OUTPUT_INTERNAL_DIRECTION",
                (
                    "semantic_target cannot name internal image tools or direct Codex "
                    "or this Skill to act."
                ),
                "$.platform_parameter_guidance.semantic_target",
            )
        dimension_text_violations = _dimension_text_violations(
            semantic_target,
            fact_state=dimension_fact_state_hint,
            evidence_type=dimension_evidence_type_hint,
            actual_dimensions=actual_dimensions_hint,
        )
        if "commitment" in dimension_text_violations:
            _issue(
                errors,
                "E_RESOLUTION_TEXT_GUARANTEE",
                (
                    "semantic_target cannot promise native 4K or exact pixel dimensions, "
                    "or present an unevidenced output size as fact."
                ),
                "$.platform_parameter_guidance.semantic_target",
            )
        if "inspected_file_binding" in dimension_text_violations:
            _issue(
                errors,
                "E_INSPECTED_FILE_DIMENSION_BINDING",
                (
                    "An inspected-file dimension fact requires observed + "
                    "inspected_file_metadata and exact agreement with "
                    "actual_pixel_dimensions."
                ),
                "$.platform_parameter_guidance.semantic_target",
            )
        if "declarative_output_binding" in dimension_text_violations:
            _issue(
                errors,
                "E_DECLARATIVE_OUTPUT_DIMENSION_BINDING",
                (
                    "A declarative output/result dimension fact must exactly match "
                    "actual_pixel_dimensions for a non-unknown fact state."
                ),
                "$.platform_parameter_guidance.semantic_target",
            )
    prompt_guarantees_dimensions = platform_guidance.get("prompt_guarantees_dimensions")
    if not isinstance(prompt_guarantees_dimensions, bool):
        _issue(
            errors,
            "E_PROMPT_GUARANTEES_DIMENSIONS_TYPE",
            "prompt_guarantees_dimensions must be a boolean.",
            "$.platform_parameter_guidance.prompt_guarantees_dimensions",
        )
    elif prompt_guarantees_dimensions is not False:
        _issue(
            errors,
            "E_PROMPT_GUARANTEES_DIMENSIONS",
            "prompt_guarantees_dimensions must be false.",
            "$.platform_parameter_guidance.prompt_guarantees_dimensions",
        )
    resolution_fact_state = _normalize_enum(
        platform_guidance.get("dimensions_fact_state"),
        VALID_RESOLUTION_FACT_STATES,
        "$.platform_parameter_guidance.dimensions_fact_state",
        errors,
        "E_DIMENSIONS_FACT_STATE",
    )
    dimensions_evidence_type = _normalize_enum(
        platform_guidance.get("dimensions_evidence_type"),
        VALID_DIMENSION_EVIDENCE_TYPES,
        "$.platform_parameter_guidance.dimensions_evidence_type",
        errors,
        "E_DIMENSIONS_EVIDENCE_TYPE",
    )
    expected_evidence_type = DIMENSION_EVIDENCE_TYPE_BY_FACT_STATE.get(
        resolution_fact_state
    )
    if (
        expected_evidence_type is not None
        and dimensions_evidence_type
        and dimensions_evidence_type != expected_evidence_type
    ):
        _issue(
            errors,
            "E_DIMENSIONS_EVIDENCE_TYPE_MISMATCH",
            (
                f"dimensions_fact_state {resolution_fact_state!r} requires "
                f"dimensions_evidence_type {expected_evidence_type!r}."
            ),
            "$.platform_parameter_guidance.dimensions_evidence_type",
        )
    settings_evidence = platform_guidance.get("settings_evidence")
    if not isinstance(settings_evidence, str) or not settings_evidence.strip():
        _issue(
            errors,
            "E_SETTINGS_EVIDENCE",
            "settings_evidence must be a non-empty evidence or missingness statement.",
            "$.platform_parameter_guidance.settings_evidence",
        )
    else:
        if _has_authoritative_internal_direction(settings_evidence):
            _issue(
                errors,
                "E_AUTHORITATIVE_OUTPUT_INTERNAL_DIRECTION",
                (
                    "settings_evidence cannot name internal image tools or direct Codex "
                    "or this Skill to act."
                ),
                "$.platform_parameter_guidance.settings_evidence",
            )
        dimension_text_violations = _dimension_text_violations(
            settings_evidence,
            fact_state=dimension_fact_state_hint,
            evidence_type=dimension_evidence_type_hint,
            actual_dimensions=actual_dimensions_hint,
        )
        if "commitment" in dimension_text_violations:
            _issue(
                errors,
                "E_RESOLUTION_TEXT_GUARANTEE",
                (
                    "settings_evidence cannot promise native 4K or exact pixel dimensions, "
                    "or present an unevidenced output size as fact."
                ),
                "$.platform_parameter_guidance.settings_evidence",
            )
        if "inspected_file_binding" in dimension_text_violations:
            _issue(
                errors,
                "E_INSPECTED_FILE_DIMENSION_BINDING",
                (
                    "An inspected-file dimension fact requires observed + "
                    "inspected_file_metadata and exact agreement with "
                    "actual_pixel_dimensions."
                ),
                "$.platform_parameter_guidance.settings_evidence",
            )
        if "declarative_output_binding" in dimension_text_violations:
            _issue(
                errors,
                "E_DECLARATIVE_OUTPUT_DIMENSION_BINDING",
                (
                    "A declarative output/result dimension fact must exactly match "
                    "actual_pixel_dimensions for a non-unknown fact state."
                ),
                "$.platform_parameter_guidance.settings_evidence",
            )
        if (
            resolution_fact_state in {"known", "observed", "user_reported"}
            and _has_dimension_missingness_claim(settings_evidence)
        ):
            _issue(
                errors,
                "E_DIMENSIONS_EVIDENCE_CONTRADICTION",
                (
                    "A non-unknown dimensions fact state cannot use settings_evidence "
                    "that explicitly says dimensions are unknown or unevidenced."
                ),
                "$.platform_parameter_guidance.settings_evidence",
            )
    actual_dimensions = platform_guidance.get("actual_pixel_dimensions")
    if actual_dimensions is not None:
        if not isinstance(actual_dimensions, dict):
            _issue(
                errors,
                "E_ACTUAL_PIXEL_DIMENSIONS_TYPE",
                "actual_pixel_dimensions must be null or an object with width and height.",
                "$.platform_parameter_guidance.actual_pixel_dimensions",
            )
        else:
            _reject_unknown_fields(
                actual_dimensions,
                PIXEL_DIMENSION_KEYS,
                "$.platform_parameter_guidance.actual_pixel_dimensions",
                errors,
            )
            for dimension_name in PIXEL_DIMENSION_KEYS:
                dimension_value = actual_dimensions.get(dimension_name)
                if (
                    not isinstance(dimension_value, int)
                    or isinstance(dimension_value, bool)
                    or dimension_value <= 0
                ):
                    _issue(
                        errors,
                        "E_ACTUAL_PIXEL_DIMENSION_VALUE",
                        f"{dimension_name} must be a positive integer.",
                        f"$.platform_parameter_guidance.actual_pixel_dimensions.{dimension_name}",
                    )
            if resolution_fact_state == "unknown":
                _issue(
                    errors,
                    "E_UNKNOWN_DIMENSIONS_CLAIM",
                    "An unknown dimensions fact state cannot assert actual pixel dimensions.",
                    "$.platform_parameter_guidance.actual_pixel_dimensions",
                )
    if resolution_fact_state in {"known", "observed", "user_reported"} and not isinstance(
        actual_dimensions, dict
    ):
        _issue(
            errors,
            "E_DIMENSIONS_EVIDENCE_REQUIRED",
            (
                "known, observed, and user_reported dimension states require a valid "
                "actual_pixel_dimensions object."
            ),
            "$.platform_parameter_guidance.actual_pixel_dimensions",
        )

    raw_execution_boundary = contract.get("execution_boundary")
    execution_boundary = (
        raw_execution_boundary if isinstance(raw_execution_boundary, str) else ""
    )
    if execution_boundary != PROMPT_ONLY_EXECUTION_BOUNDARY:
        _issue(
            errors,
            "E_EXECUTION_BOUNDARY",
            (
                "execution_boundary must be exactly "
                f"{PROMPT_ONLY_EXECUTION_BOUNDARY!r}; this contract cannot authorize "
                "Codex or the Skill to generate or edit pixels."
            ),
            "$.execution_boundary",
        )

    delivery_state = _normalize_enum(
        contract.get("delivery_state"),
        VALID_DELIVERY_STATES,
        "$.delivery_state",
        errors,
        "E_DELIVERY_STATE",
    )

    provenance_value = contract.get("external_result_provenance")
    valid_provenance_count = 0
    provenance_result_ids: list[str] = []
    valid_provenance_result_ids: set[str] = set()
    if not isinstance(provenance_value, list):
        _issue(
            errors,
            "E_EXTERNAL_RESULT_PROVENANCE_TYPE",
            "external_result_provenance must be an array.",
            "$.external_result_provenance",
        )
        provenance_records: list[Any] = []
    else:
        provenance_records = provenance_value

    for index, record in enumerate(provenance_records):
        path = f"$.external_result_provenance[{index}]"
        record_valid = True
        if not isinstance(record, dict):
            _issue(
                errors,
                "E_EXTERNAL_RESULT_PROVENANCE_RECORD",
                "Each external result provenance record must be an object.",
                path,
            )
            continue

        _reject_unknown_fields(record, PROVENANCE_KEYS, path, errors)

        result_id = record.get("result_id")
        if not isinstance(result_id, str) or not result_id.strip():
            _issue(
                errors,
                "E_EXTERNAL_RESULT_ID",
                "result_id must be a non-empty string.",
                f"{path}.result_id",
            )
            record_valid = False
        else:
            provenance_result_ids.append(result_id.strip())

        origin = record.get("origin")
        if not isinstance(origin, str) or origin not in VALID_EXTERNAL_RESULT_ORIGINS:
            _issue(
                errors,
                "E_EXTERNAL_RESULT_ORIGIN",
                (
                    "origin must be exactly 'user_manual_external_generation'; "
                    "the Skill cannot be the origin of pixels."
                ),
                f"{path}.origin",
            )
            record_valid = False

        imported_by_user = record.get("imported_by_user")
        if imported_by_user is not True:
            _issue(
                errors,
                "E_EXTERNAL_RESULT_IMPORT",
                "imported_by_user must be the boolean true.",
                f"{path}.imported_by_user",
            )
            record_valid = False

        provenance = record.get("provenance")
        if not isinstance(provenance, str) or not provenance.strip():
            _issue(
                errors,
                "E_EXTERNAL_RESULT_PROVENANCE_REQUIRED",
                "provenance must be a non-empty user-supplied import record.",
                f"{path}.provenance",
            )
            record_valid = False

        if record_valid:
            valid_provenance_count += 1
            valid_provenance_result_ids.add(result_id.strip())

    for duplicate_result_id in sorted(_duplicates(provenance_result_ids)):
        _issue(
            errors,
            "E_DUPLICATE_EXTERNAL_RESULT_ID",
            f"External result ID {duplicate_result_id!r} is duplicated.",
            "$.external_result_provenance",
        )

    status = _normalize_enum(
        contract.get("status"), VALID_STATUSES, "$.status", errors, "E_STATUS"
    )

    if delivery_state == "prompt_plan" and provenance_records:
        _issue(
            errors,
            "E_PROMPT_PLAN_HAS_EXTERNAL_RESULT",
            "A prompt_plan must not claim imported external result provenance.",
            "$.external_result_provenance",
        )
    if delivery_state == "imported_external_candidate" and valid_provenance_count == 0:
        _issue(
            errors,
            "E_IMPORTED_RESULT_PROVENANCE_REQUIRED",
            (
                "An imported_external_candidate requires at least one complete "
                "user-manual external result provenance record."
            ),
            "$.external_result_provenance",
        )
    if status in IMPORTED_CANDIDATE_STATUSES:
        if delivery_state != "imported_external_candidate" or valid_provenance_count == 0:
            _issue(
                errors,
                "E_CANDIDATE_REQUIRES_IMPORTED_RESULT",
                (
                    f"Status {status!r} is legal only after the user manually generates "
                    "the external result and imports it with complete provenance."
                ),
                "$.status",
            )
    elif status in VALID_STATUSES and delivery_state != "prompt_plan":
        _issue(
            errors,
            "E_PROMPT_STATUS_DELIVERY_STATE",
            (
                f"Status {status!r} describes a prompt or blocked plan and therefore "
                "requires delivery_state 'prompt_plan'."
            ),
            "$.delivery_state",
        )

    protected_patterns = set(DEFAULT_PROTECTED_STRUCTURE)
    if "protected_structure" in contract:
        if not isinstance(contract.get("protected_structure"), list):
            _issue(
                errors,
                "E_PROTECTED_STRUCTURE_TYPE",
                "protected_structure must be an array of attribute paths.",
                "$.protected_structure",
            )
        else:
            for index, raw_value in enumerate(contract["protected_structure"]):
                canonical = _validated_attribute_scope(
                    raw_value,
                    f"$.protected_structure[{index}]",
                    errors,
                )
                if canonical:
                    protected_patterns.add(canonical)

    assets_value = contract.get("assets")
    if not isinstance(assets_value, list):
        _issue(errors, "E_ASSETS_REQUIRED", "assets must be an array.", "$.assets")
        assets: list[Any] = []
    else:
        assets = assets_value
        if not assets:
            _issue(errors, "E_ASSETS_EMPTY", "assets must not be empty.", "$.assets")

    asset_ids: list[str] = []
    asset_by_id: dict[str, dict[str, Any]] = {}
    asset_kind: dict[str, str] = {}
    asset_approved: dict[str, bool | None] = {}
    contamination_risk: dict[str, str] = {}
    exact_attributes_by_id: dict[str, set[str]] = {}

    for index, raw_asset in enumerate(assets):
        path = f"$.assets[{index}]"
        if not isinstance(raw_asset, dict):
            _issue(errors, "E_ASSET_TYPE", "Each asset must be an object.", path)
            continue
        _reject_unknown_fields(raw_asset, ASSET_KEYS, path, errors)
        raw_id = raw_asset.get("id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            _issue(errors, "E_ASSET_ID", "Asset id must be a non-empty string.", f"{path}.id")
            continue
        asset_id = raw_id.strip()
        asset_ids.append(asset_id)
        kind = _normalize_enum(
            raw_asset.get("kind"), VALID_ASSET_KINDS, f"{path}.kind", errors, "E_ASSET_KIND"
        )
        if "approved" in raw_asset and not isinstance(raw_asset.get("approved"), bool):
            _issue(errors, "E_ASSET_APPROVED_TYPE", "approved must be a boolean when present.", f"{path}.approved")
            approved: bool | None = None
        else:
            approved = raw_asset.get("approved") if "approved" in raw_asset else None
        if kind == "candidate_result" and approved is True:
            _issue(
                errors,
                "E_CANDIDATE_RESULT_APPROVED",
                "candidate_result assets can never carry approved: true.",
                f"{path}.approved",
            )
        if "contamination_risk" in raw_asset:
            risk = _normalize_enum(
                raw_asset.get("contamination_risk"),
                VALID_CONTAMINATION_RISKS,
                f"{path}.contamination_risk",
                errors,
                "E_CONTAMINATION_RISK",
            )
        else:
            risk = ""
        exact_attributes = set(
            _attribute_list(raw_asset, "exact_attributes", path, errors)
        ) if "exact_attributes" in raw_asset else set()
        if asset_id not in asset_by_id:
            asset_by_id[asset_id] = raw_asset
            asset_kind[asset_id] = kind
            asset_approved[asset_id] = approved
            contamination_risk[asset_id] = risk
            exact_attributes_by_id[asset_id] = exact_attributes

    for duplicate_id in sorted(_duplicates(asset_ids)):
        _issue(errors, "E_DUPLICATE_ASSET_ID", f"Asset id {duplicate_id!r} is duplicated.", "$.assets")

    target_ids = [asset_id for asset_id in asset_ids if asset_kind.get(asset_id) == "target"]
    reference_ids = {asset_id for asset_id in asset_ids if asset_kind.get(asset_id) == "reference"}
    candidate_result_ids = {
        asset_id for asset_id in asset_ids if asset_kind.get(asset_id) == "candidate_result"
    }
    if len(target_ids) != 1:
        _issue(errors, "E_TARGET_COUNT", f"Exactly one target is required; found {len(target_ids)}.", "$.assets")
    target_id = target_ids[0] if len(target_ids) == 1 else None
    if "target_id" in contract and contract.get("target_id") != target_id:
        _issue(errors, "E_TARGET_ID_MISMATCH", "target_id does not match the sole target asset.", "$.target_id")

    if delivery_state == "prompt_plan" and candidate_result_ids:
        _issue(
            errors,
            "E_PROMPT_PLAN_CANDIDATE_RESULT",
            (
                "A prompt_plan cannot declare candidate_result assets: "
                f"{sorted(candidate_result_ids)}."
            ),
            "$.assets",
        )
    if delivery_state == "imported_external_candidate":
        unbound_candidate_results = candidate_result_ids - valid_provenance_result_ids
        if unbound_candidate_results:
            _issue(
                errors,
                "E_UNBOUND_CANDIDATE_RESULT",
                (
                    "Every candidate_result must be bound by a complete external result "
                    f"provenance record: {sorted(unbound_candidate_results)}."
                ),
                "$.assets",
            )

    expected_result_kind = ""
    if status == "structure_master_candidate":
        expected_result_kind = "structure_master"
    elif status in {"candidate_unapproved", "qa_failed_directional_retry_ready"}:
        expected_result_kind = "candidate_result"
    if status in IMPORTED_CANDIDATE_STATUSES:
        for index, record in enumerate(provenance_records):
            if not isinstance(record, dict):
                continue
            raw_result_id = record.get("result_id")
            if not isinstance(raw_result_id, str) or not raw_result_id.strip():
                continue
            result_id = raw_result_id.strip()
            result_path = f"$.external_result_provenance[{index}].result_id"
            if result_id not in asset_by_id:
                _issue(
                    errors,
                    "E_EXTERNAL_RESULT_ASSET_MISSING",
                    (
                        f"Imported external result {result_id!r} must bind to a "
                        "declared asset."
                    ),
                    result_path,
                )
                continue
            if asset_kind.get(result_id) != expected_result_kind:
                _issue(
                    errors,
                    "E_EXTERNAL_RESULT_KIND",
                    (
                        f"Status {status!r} requires imported result {result_id!r} "
                        f"to have asset kind {expected_result_kind!r}."
                    ),
                    result_path,
                )
            if asset_approved.get(result_id) is True:
                _issue(
                    errors,
                    "E_CANDIDATE_RESULT_ALREADY_APPROVED",
                    (
                        f"Imported result {result_id!r} is still a candidate and "
                        "cannot carry approved: true."
                    ),
                    result_path,
                )

    intent_value = contract.get("intent")
    if not isinstance(intent_value, dict):
        _issue(errors, "E_INTENT_TYPE", "intent must be an object.", "$.intent")
        intent: dict[str, Any] = {}
    else:
        intent = intent_value
        _reject_unknown_fields(intent, INTENT_KEYS, "$.intent", errors)
    if "preserve_all" not in intent:
        _issue(errors, "E_REQUIRED_FIELD", "intent.preserve_all is required.", "$.intent.preserve_all")
    preserve_all = intent.get("preserve_all")
    if not isinstance(preserve_all, bool):
        _issue(errors, "E_PRESERVE_ALL_TYPE", "preserve_all must be a boolean.", "$.intent.preserve_all")
        preserve_all = False
    removed_entities = _required_string_list(intent, "remove", "$.intent", errors)
    for duplicate_entity in sorted(_duplicates(removed_entities)):
        _issue(warnings, "W_DUPLICATE_REMOVAL", f"Removed entity {duplicate_entity!r} is duplicated.", "$.intent.remove")
    removed_set = set(removed_entities)
    if "explicit_exceptions" not in intent:
        _issue(errors, "E_REQUIRED_FIELD", "intent.explicit_exceptions is required.", "$.intent.explicit_exceptions")
        exceptions: list[Any] = []
    elif not isinstance(intent.get("explicit_exceptions"), list):
        _issue(errors, "E_EXCEPTIONS_TYPE", "explicit_exceptions must be an array.", "$.intent.explicit_exceptions")
        exceptions = []
    else:
        exceptions = intent["explicit_exceptions"]
    exception_by_entity: dict[str, dict[str, Any]] = {}
    for index, raw_exception in enumerate(exceptions):
        path = f"$.intent.explicit_exceptions[{index}]"
        if not isinstance(raw_exception, dict):
            _issue(errors, "E_EXCEPTION_TYPE", "Exception must be an object.", path)
            continue
        _reject_unknown_fields(raw_exception, EXCEPTION_KEYS, path, errors)
        entity = raw_exception.get("entity")
        if not isinstance(entity, str) or not entity.strip():
            _issue(errors, "E_EXCEPTION_ENTITY", "Exception entity is required.", f"{path}.entity")
            continue
        entity = entity.strip()
        if entity in exception_by_entity:
            _issue(errors, "E_DUPLICATE_EXCEPTION", f"Entity {entity!r} has multiple exceptions.", path)
        else:
            exception_by_entity[entity] = raw_exception
    for entity in removed_entities:
        normalized_exceptions.append(
            {
                "entity": entity,
                "exception_to": "preserve_all" if preserve_all else "preserve_scope",
                "cleanup": list(REQUIRED_REMOVAL_CLEANUP),
            }
        )
        raw_exception = exception_by_entity.get(entity)
        if raw_exception is None:
            _issue(errors, "E_REMOVE_EXCEPTION_MISSING", f"Removal of {entity!r} requires an explicit exception.", "$.intent.explicit_exceptions")
            continue
        cleanup = {
            _canonical_attribute(item)
            for item in _required_string_list(raw_exception, "cleanup", "$.intent.explicit_exceptions", errors)
        }
        missing_cleanup = [item for item in REQUIRED_REMOVAL_CLEANUP if item not in cleanup]
        if missing_cleanup:
            _issue(errors, "E_REMOVE_CLEANUP_INCOMPLETE", f"Removal of {entity!r} lacks cleanup items: {missing_cleanup}.", "$.intent.explicit_exceptions")

    authority_value = contract.get("authority")
    if not isinstance(authority_value, list):
        _issue(errors, "E_AUTHORITY_TYPE", "authority must be an array.", "$.authority")
        authority: list[Any] = []
    else:
        authority = authority_value
        if not authority:
            _issue(errors, "E_AUTHORITY_EMPTY", "authority must contain at least one substantive row.", "$.authority")
    authority_rows: list[dict[str, Any]] = []
    authority_attributes: list[str] = []
    for index, raw_row in enumerate(authority):
        path = f"$.authority[{index}]"
        if not isinstance(raw_row, dict):
            _issue(errors, "E_AUTHORITY_ROW", "Authority row must be an object.", path)
            continue
        _reject_unknown_fields(raw_row, AUTHORITY_KEYS, path, errors)
        raw_attribute = raw_row.get("attribute")
        attribute = _validated_attribute_scope(
            raw_attribute, f"{path}.attribute", errors
        )
        if not attribute:
            _issue(errors, "E_AUTHORITY_ATTRIBUTE", "attribute must be a meaningful string.", f"{path}.attribute")
            continue
        authority_attributes.append(attribute)
        primary = _required_string_list(raw_row, "primary", path, errors)
        allow = _required_string_list(raw_row, "allow", path, errors)
        deny = _required_string_list(raw_row, "deny", path, errors)
        for field_name, values in (("primary", primary), ("allow", allow), ("deny", deny)):
            duplicates = _duplicates(values)
            if duplicates:
                _issue(errors, "E_DUPLICATE_AUTHORITY_SOURCE", f"Duplicate sources in {field_name}: {sorted(duplicates)}.", f"{path}.{field_name}")
        if len(set(primary)) > 1:
            _issue(errors, "E_MULTIPLE_PRIMARY_AUTHORITIES", f"Attribute {raw_attribute!r} has multiple primary authorities: {sorted(set(primary))}.", f"{path}.primary")
        overlap = (set(primary) | set(allow)) & set(deny)
        if overlap:
            _issue(errors, "E_ALLOW_DENY_CONFLICT", f"Sources are both permitted and denied: {sorted(overlap)}.", path)
        unresolved = raw_row.get("unresolved", False)
        if "unresolved" in raw_row and not isinstance(unresolved, bool):
            _issue(errors, "E_UNRESOLVED_TYPE", "unresolved must be a boolean.", f"{path}.unresolved")
            unresolved = False
        reason = raw_row.get("reason")
        if unresolved:
            if primary or allow:
                _issue(
                    errors,
                    "E_UNRESOLVED_AUTHORITY_ASSIGNED",
                    "An unresolved authority row cannot grant primary or allow authority.",
                    path,
                )
            if not isinstance(reason, str) or not reason.strip():
                _issue(
                    errors,
                    "E_UNRESOLVED_REASON",
                    "An unresolved authority row requires a non-empty reason.",
                    f"{path}.reason",
                )
        else:
            if "reason" in raw_row:
                _issue(
                    errors,
                    "E_AUTHORITY_REASON_WITH_RESOLVED",
                    "reason is valid only when unresolved is true.",
                    f"{path}.reason",
                )
            if len(set(primary)) != 1:
                _issue(
                    errors,
                    "E_RESOLVED_AUTHORITY_PRIMARY_COUNT",
                    "Every resolved authority row requires exactly one primary source.",
                    f"{path}.primary",
                )
            if not primary and not allow and not deny:
                _issue(
                    errors,
                    "E_AUTHORITY_ROW_EMPTY",
                    "An unassigned authority row requires unresolved=true and a non-empty reason.",
                    path,
                )
        if "role_state" in raw_row:
            _normalize_enum(raw_row.get("role_state"), VALID_ROLE_STATES, f"{path}.role_state", errors, "E_AUTHORITY_ROLE_STATE")
        if "evidence" in raw_row and (not isinstance(raw_row.get("evidence"), str) or not raw_row.get("evidence").strip()):
            _issue(errors, "E_AUTHORITY_EVIDENCE", "evidence must be a non-empty string when present.", f"{path}.evidence")
        if "confidence" in raw_row:
            confidence = raw_row.get("confidence")
            if (
                not isinstance(confidence, (int, float))
                or isinstance(confidence, bool)
                or not 0 <= confidence <= 1
            ):
                _issue(
                    errors,
                    "E_AUTHORITY_CONFIDENCE",
                    "confidence must be a number from 0 through 1.",
                    f"{path}.confidence",
                )
        for descriptive_field in ("conflicts", "missingness"):
            if descriptive_field in raw_row:
                _string_list(
                    raw_row.get(descriptive_field),
                    f"{path}.{descriptive_field}",
                    errors,
                    required_key=True,
                )
        for source_id in set(primary + allow + deny):
            if source_id not in asset_by_id:
                _issue(errors, "E_UNKNOWN_AUTHORITY_SOURCE", f"Unknown authority source {source_id!r}.", path)
        authority_rows.append(
            {
                "attribute": attribute,
                "primary": set(primary),
                "allow": set(allow),
                "deny": set(deny),
                "unresolved": unresolved,
                "path": path,
            }
        )
    for duplicate_attribute in sorted(_duplicates(authority_attributes)):
        _issue(errors, "E_DUPLICATE_AUTHORITY_ATTRIBUTE", f"Attribute {duplicate_attribute!r} has multiple authority rows.", "$.authority")
    for first_index, first_row in enumerate(authority_rows):
        if first_row["unresolved"]:
            continue
        for second_row in authority_rows[first_index + 1 :]:
            if second_row["unresolved"] or not _patterns_overlap(
                first_row["attribute"], second_row["attribute"], protected_patterns
            ):
                continue
            first_sources = (first_row["primary"], first_row["allow"])
            second_sources = (second_row["primary"], second_row["allow"])
            if first_sources != second_sources:
                _issue(
                    errors,
                    "E_OVERLAPPING_AUTHORITY_SCOPES",
                    (
                        f"Overlapping authority scopes {first_row['attribute']!r} and "
                        f"{second_row['attribute']!r} resolve to different primary/allow sources."
                    ),
                    second_row["path"],
                )

    permissions_value = contract.get("reference_permissions")
    if not isinstance(permissions_value, list):
        _issue(errors, "E_REFERENCE_PERMISSIONS_TYPE", "reference_permissions must be an array.", "$.reference_permissions")
        permissions: list[Any] = []
    else:
        permissions = permissions_value
    permission_ids: list[str] = []
    permission_by_ref: dict[str, dict[str, Any]] = {}
    for index, raw_permission in enumerate(permissions):
        path = f"$.reference_permissions[{index}]"
        if not isinstance(raw_permission, dict):
            _issue(errors, "E_REFERENCE_PERMISSION", "Permission must be an object.", path)
            continue
        _reject_unknown_fields(raw_permission, REFERENCE_PERMISSION_KEYS, path, errors)
        raw_ref_id = raw_permission.get("asset_id")
        if not isinstance(raw_ref_id, str) or not raw_ref_id.strip():
            _issue(errors, "E_REFERENCE_PERMISSION_ID", "asset_id is required.", f"{path}.asset_id")
            continue
        ref_id = raw_ref_id.strip()
        permission_ids.append(ref_id)
        if ref_id not in asset_by_id:
            _issue(errors, "E_UNKNOWN_REFERENCE", f"Unknown reference {ref_id!r}.", path)
        elif asset_kind.get(ref_id) != "reference":
            _issue(errors, "E_NOT_REFERENCE", f"Asset {ref_id!r} is not a reference.", path)
        role_state = _normalize_enum(raw_permission.get("role_state"), VALID_ROLE_STATES, f"{path}.role_state", errors, "E_REFERENCE_ROLE_STATE")
        role_evidence = raw_permission.get("role_evidence")
        if not isinstance(role_evidence, str) or not role_evidence.strip():
            _issue(errors, "E_REFERENCE_ROLE_EVIDENCE", "role_evidence must be a non-empty string.", f"{path}.role_evidence")
        allow_attributes = _attribute_list(raw_permission, "allow_attributes", path, errors, required_key=True)
        deny_attributes = _attribute_list(
            raw_permission,
            "deny_attributes",
            path,
            errors,
            required_key=True,
            allow_global_umbrella=True,
        )
        allow_entities = _required_string_list(raw_permission, "allow_entities", path, errors)
        deny_entities = _required_string_list(raw_permission, "deny_entities", path, errors)
        for field_name, values in (("allow_attributes", allow_attributes), ("deny_attributes", deny_attributes), ("allow_entities", allow_entities), ("deny_entities", deny_entities)):
            duplicates = _duplicates(values)
            if duplicates:
                _issue(errors, "E_DUPLICATE_PERMISSION_VALUE", f"Duplicate values in {field_name}: {sorted(duplicates)}.", f"{path}.{field_name}")
        if not deny_attributes:
            _issue(errors, "E_REFERENCE_DENY_EMPTY", "Every reference requires a non-empty deny_attributes/must-not-inherit scope.", f"{path}.deny_attributes")
        unlimited = {
            attribute
            for attribute in allow_attributes
            if _is_unbounded_attribute_scope(attribute)
        }
        if unlimited:
            _issue(errors, "E_REFERENCE_UNLIMITED_AUTHORITY", f"Reference has unlimited authority patterns: {sorted(unlimited)}.", f"{path}.allow_attributes")
        attribute_conflicts = [
            allowed
            for allowed in allow_attributes
            if any(_patterns_overlap(allowed, denied, protected_patterns) for denied in deny_attributes)
        ]
        if attribute_conflicts:
            _issue(errors, "E_REFERENCE_ATTRIBUTE_CONFLICT", f"Reference allow and deny scopes overlap: {sorted(set(attribute_conflicts))}.", path)
        protected_allow = [attribute for attribute in allow_attributes if _is_protected(attribute, protected_patterns)]
        if protected_allow:
            _issue(errors, "E_REFERENCE_PROTECTED_PERMISSION", f"Reference is allowed protected structure: {sorted(set(protected_allow))}.", f"{path}.allow_attributes")
        uncovered_protected = [
            protected
            for protected in sorted(protected_patterns)
            if not any(_pattern_covers(denied, protected, protected_patterns) for denied in deny_attributes)
        ]
        if uncovered_protected:
            _issue(errors, "E_REFERENCE_PROTECTED_DENY_INCOMPLETE", f"Reference deny scope does not cover protected structure: {uncovered_protected}.", f"{path}.deny_attributes")
        entity_overlap = set(allow_entities) & set(deny_entities)
        if entity_overlap:
            _issue(errors, "E_REFERENCE_ENTITY_CONFLICT", f"Reference allows and denies the same entities: {sorted(entity_overlap)}.", path)
        reallowed = set(allow_entities) & removed_set
        if reallowed:
            _issue(errors, "E_REMOVED_ENTITY_REALLOWED", f"Reference explicitly re-allows removed entities: {sorted(reallowed)}.", f"{path}.allow_entities")
        missing_removed_denials = removed_set - set(deny_entities)
        if missing_removed_denials:
            _issue(errors, "E_REMOVED_ENTITY_NOT_DENIED", f"Reference must deny all removed entities: {sorted(missing_removed_denials)}.", f"{path}.deny_entities")
        if ref_id not in permission_by_ref:
            permission_by_ref[ref_id] = {
                "role_state": role_state,
                "allow_attributes": allow_attributes,
                "deny_attributes": deny_attributes,
                "allow_entities": set(allow_entities),
                "deny_entities": set(deny_entities),
                "path": path,
            }
    for duplicate_permission in sorted(_duplicates(permission_ids)):
        _issue(errors, "E_DUPLICATE_REFERENCE_PERMISSION", f"Reference {duplicate_permission!r} has multiple permission records.", "$.reference_permissions")
    missing_permissions = reference_ids - set(permission_ids)
    if missing_permissions:
        _issue(errors, "E_REFERENCE_PERMISSION_MISSING", f"References lack permission records: {sorted(missing_permissions)}.", "$.reference_permissions")

    stages_value = contract.get("stages")
    if not isinstance(stages_value, list):
        _issue(errors, "E_STAGES_TYPE", "stages must be an array.", "$.stages")
        stages: list[Any] = []
    else:
        stages = stages_value
        if not stages:
            _issue(errors, "E_STAGES_EMPTY", "stages must contain an actionable manual external plan or a blocked plan.", "$.stages")
    stage_ids: list[str] = []
    parsed_stage_kinds: list[str] = []
    parsed_stages: list[dict[str, Any]] = []
    prior_stage_by_id: dict[str, dict[str, Any]] = {}
    used_reference_ids: set[str] = set()
    action_stage_kinds_by_input: dict[str, set[str]] = {}
    for index, raw_stage in enumerate(stages):
        path = f"$.stages[{index}]"
        if not isinstance(raw_stage, dict):
            _issue(errors, "E_STAGE_TYPE", "Stage must be an object.", path)
            continue
        _reject_unknown_fields(raw_stage, STAGE_KEYS, path, errors)
        raw_stage_id = raw_stage.get("id")
        if not isinstance(raw_stage_id, str) or not raw_stage_id.strip():
            _issue(errors, "E_STAGE_ID", "Stage id is required.", f"{path}.id")
            stage_id = ""
        else:
            stage_id = raw_stage_id.strip()
            stage_ids.append(stage_id)
        kind = _normalize_enum(raw_stage.get("kind"), VALID_STAGE_KINDS, f"{path}.kind", errors, "E_STAGE_KIND")
        parsed_stage_kinds.append(kind)
        if "target_reuse" in raw_stage:
            reuse_value = raw_stage.get("target_reuse")
            if not isinstance(reuse_value, dict):
                _issue(
                    errors,
                    "E_TARGET_REUSE_TYPE",
                    "target_reuse must be an object.",
                    f"{path}.target_reuse",
                )
            else:
                _reject_unknown_fields(
                    reuse_value,
                    TARGET_REUSE_KEYS,
                    f"{path}.target_reuse",
                    errors,
                )
            if kind != "realism":
                _issue(
                    errors,
                    "E_STAGE_FIELD_INCOMPATIBLE",
                    "target_reuse is valid only on a realism stage.",
                    f"{path}.target_reuse",
                )
        if "base_stage_id" in raw_stage and kind != "composite":
            _issue(
                errors,
                "E_STAGE_FIELD_INCOMPATIBLE",
                "base_stage_id is valid only on a composite stage.",
                f"{path}.base_stage_id",
            )
        if "reason" in raw_stage and kind != "blocked":
            _issue(
                errors,
                "E_STAGE_FIELD_INCOMPATIBLE",
                "reason is valid only on a blocked stage.",
                f"{path}.reason",
            )
        inputs = _required_string_list(raw_stage, "inputs", path, errors)
        duplicate_inputs = _duplicates(inputs)
        if duplicate_inputs:
            _issue(errors, "E_DUPLICATE_STAGE_INPUT", f"Stage contains duplicate inputs: {sorted(duplicate_inputs)}.", f"{path}.inputs")
        if not inputs:
            _issue(errors, "E_STAGE_INPUTS_EMPTY", "Stage inputs must not be empty.", f"{path}.inputs")
        for source_id in inputs:
            if source_id not in asset_by_id:
                _issue(errors, "E_UNKNOWN_STAGE_INPUT", f"Unknown stage input {source_id!r}.", f"{path}.inputs")
        parsed_stage = {
            "id": stage_id,
            "kind": kind,
            "inputs": set(inputs),
            "path": path,
        }
        parsed_stages.append(parsed_stage)
        stage_refs = {source_id for source_id in inputs if source_id in reference_ids}
        used_reference_ids.update(stage_refs)
        if kind != "blocked":
            for source_id in inputs:
                if source_id in asset_by_id:
                    action_stage_kinds_by_input.setdefault(source_id, set()).add(kind)
        allowed_kinds = ALLOWED_ASSET_KINDS_BY_STAGE.get(kind)
        if allowed_kinds is not None:
            incompatible_inputs = [
                source_id
                for source_id in inputs
                if source_id in asset_by_id and asset_kind.get(source_id) not in allowed_kinds
            ]
            if incompatible_inputs:
                _issue(
                    errors,
                    "E_STAGE_ASSET_ROLE_INCOMPATIBLE",
                    (
                        f"Stage kind {kind!r} cannot ingest these asset roles: "
                        f"{sorted(incompatible_inputs)}."
                    ),
                    f"{path}.inputs",
                )
        if (
            kind in {"pixel", "local", "isomorphic", "structure"}
            and target_id is not None
            and target_id in inputs
            and inputs[0] != target_id
        ):
            _issue(
                errors,
                "E_TARGET_MUST_BE_FIRST",
                f"The target must be the first input for stage kind {kind!r}.",
                f"{path}.inputs",
            )
        if kind == "structure":
            if target_id is not None and target_id not in inputs:
                _issue(errors, "E_STRUCTURE_TARGET_REQUIRED", "Structure stage must include the target.", f"{path}.inputs")
            if stage_refs:
                _issue(errors, "E_STRUCTURE_STAGE_REFERENCE", f"Structure stage cannot ingest references: {sorted(stage_refs)}.", f"{path}.inputs")
        elif kind == "pixel":
            if target_id is not None and target_id not in inputs:
                _issue(errors, "E_PIXEL_TARGET_REQUIRED", "Pixel stage must include the target.", f"{path}.inputs")
            semantic_inputs = [source_id for source_id in inputs if asset_kind.get(source_id) not in {"target", "mask"}]
            if semantic_inputs:
                _issue(errors, "E_PIXEL_SEMANTIC_INPUT", f"Pixel stage accepts only target and optional mask assets: {sorted(semantic_inputs)}.", f"{path}.inputs")
        elif kind == "local":
            if target_id is not None and target_id not in inputs:
                _issue(errors, "E_LOCAL_TARGET_REQUIRED", "Local stage must include the target.", f"{path}.inputs")
        elif kind == "isomorphic":
            if target_id is not None and target_id not in inputs:
                _issue(errors, "E_ISOMORPHIC_TARGET_REQUIRED", "Isomorphic stage must include the target.", f"{path}.inputs")
        elif kind == "realism":
            masters = [source_id for source_id in inputs if asset_kind.get(source_id) == "structure_master"]
            if len(masters) != 1:
                _issue(errors, "E_REALISM_MASTER_COUNT", f"Realism stage requires exactly one structure master; found {len(masters)}.", f"{path}.inputs")
            else:
                if inputs and inputs[0] != masters[0]:
                    _issue(
                        errors,
                        "E_REALISM_MASTER_FIRST",
                        "The sole approved structure master must be the first realism input.",
                        f"{path}.inputs",
                    )
                if asset_approved.get(masters[0]) is not True:
                    _issue(errors, "E_UNAPPROVED_MASTER_IN_REALISM", f"Structure master {masters[0]!r} is not approved for realism.", f"{path}.inputs")
            if target_id is not None and target_id in inputs:
                reuse = raw_stage.get("target_reuse")
                if not isinstance(reuse, dict):
                    _issue(errors, "E_TARGET_REUSE_SCOPE_REQUIRED", "Any original-target reuse in realism requires a scoped justification.", f"{path}.target_reuse")
                else:
                    justification = reuse.get("justification")
                    if not isinstance(justification, str) or not justification.strip():
                        _issue(errors, "E_TARGET_REUSE_JUSTIFICATION", "target_reuse.justification must be non-empty.", f"{path}.target_reuse.justification")
                    allowed_attributes = _attribute_list(reuse, "allowed_attributes", f"{path}.target_reuse", errors, required_key=True)
                    if not allowed_attributes:
                        _issue(errors, "E_TARGET_REUSE_ATTRIBUTES_EMPTY", "target_reuse.allowed_attributes must contain meaningful non-structural attributes.", f"{path}.target_reuse.allowed_attributes")
                    broad_reuse = [
                        attribute
                        for attribute in allowed_attributes
                        if not _is_concrete_attribute_scope(attribute)
                    ]
                    if broad_reuse:
                        _issue(
                            errors,
                            "E_TARGET_REUSE_ATTRIBUTE_NOT_SCOPED",
                            (
                                "Original-target reuse must name concrete attributes; "
                                f"broad roots and wildcards are forbidden: {sorted(set(broad_reuse))}."
                            ),
                            f"{path}.target_reuse.allowed_attributes",
                        )
                    protected_reuse = [attribute for attribute in allowed_attributes if _is_protected(attribute, protected_patterns)]
                    if protected_reuse:
                        _issue(errors, "E_TARGET_REUSE_PROTECTED_STRUCTURE", f"Original target reuse allows protected structure: {sorted(set(protected_reuse))}.", f"{path}.target_reuse.allowed_attributes")
                    if reuse.get("deny_protected_structure") is not True:
                        _issue(errors, "E_TARGET_REUSE_STRUCTURE_NOT_DENIED", "target_reuse.deny_protected_structure must be true.", f"{path}.target_reuse.deny_protected_structure")
            elif "target_reuse" in raw_stage:
                _issue(
                    errors,
                    "E_TARGET_REUSE_WITHOUT_TARGET",
                    "target_reuse is invalid when the target is not an input.",
                    f"{path}.target_reuse",
                )
        elif kind == "composite":
            exact_inputs = [
                source_id
                for source_id in inputs
                if asset_kind.get(source_id) == "exact_asset"
            ]
            if not exact_inputs:
                _issue(
                    errors,
                    "E_COMPOSITE_EXACT_ASSET_REQUIRED",
                    "A composite stage requires at least one exact_asset input.",
                    f"{path}.inputs",
                )
            base_asset_inputs = [
                source_id
                for source_id in inputs
                if asset_kind.get(source_id) in {"target", "structure_master"}
            ]
            base_stage_id_value = raw_stage.get("base_stage_id")
            valid_base_stage = False
            if "base_stage_id" in raw_stage:
                if (
                    not isinstance(base_stage_id_value, str)
                    or not base_stage_id_value.strip()
                ):
                    _issue(
                        errors,
                        "E_COMPOSITE_BASE_STAGE_ID",
                        "base_stage_id must be a non-empty prior stage ID.",
                        f"{path}.base_stage_id",
                    )
                else:
                    base_stage_id = base_stage_id_value.strip()
                    base_stage = prior_stage_by_id.get(base_stage_id)
                    if base_stage is None or base_stage["kind"] not in (
                        VALID_STAGE_KINDS - {"blocked"}
                    ):
                        _issue(
                            errors,
                            "E_COMPOSITE_BASE_STAGE_INVALID",
                            "base_stage_id must name an earlier actionable external stage.",
                            f"{path}.base_stage_id",
                        )
                    else:
                        valid_base_stage = True
            if not base_asset_inputs and not valid_base_stage:
                _issue(
                    errors,
                    "E_COMPOSITE_BASE_REQUIRED",
                    (
                        "A composite stage requires a target/structure_master base input "
                        "or base_stage_id naming an earlier actionable external stage."
                    ),
                    path,
                )
        elif kind == "blocked":
            reason = raw_stage.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                _issue(errors, "E_BLOCKED_REASON", "Blocked stage requires a non-empty reason.", f"{path}.reason")
            if target_id is not None and target_id not in inputs:
                _issue(errors, "E_BLOCKED_TARGET_REQUIRED", "Blocked plan must identify the target input.", f"{path}.inputs")
        if stage_id:
            prior_stage_by_id.setdefault(stage_id, parsed_stage)

    for duplicate_stage in sorted(_duplicates(stage_ids)):
        _issue(errors, "E_DUPLICATE_STAGE_ID", f"Stage id {duplicate_stage!r} is duplicated.", "$.stages")
    has_blocked_stage = "blocked" in parsed_stage_kinds
    actionable_stage_kinds = {
        kind for kind in parsed_stage_kinds if kind in VALID_STAGE_KINDS and kind != "blocked"
    }
    if has_blocked_stage and actionable_stage_kinds:
        _issue(
            errors,
            "E_BLOCKED_STAGE_EXCLUSIVE",
            "A blocked plan is terminal and cannot coexist with actionable external stages.",
            "$.stages",
        )
    if status in BLOCKED_STATUSES and not has_blocked_stage:
        _issue(errors, "E_BLOCKED_STATUS_PLAN", "A blocked status requires an explicit blocked stage.", "$.status")
    if status in BLOCKED_STATUSES and actionable_stage_kinds:
        _issue(
            errors,
            "E_BLOCKED_STATUS_EXECUTION",
            "A blocked status cannot contain actionable external stages.",
            "$.stages",
        )
    if has_blocked_stage and status not in BLOCKED_STATUSES:
        _issue(errors, "E_BLOCKED_STAGE_STATUS", "A blocked stage requires a blocked or bounded-proxy status.", "$.status")
    if status == "structure_master_candidate":
        if "structure" not in parsed_stage_kinds:
            _issue(errors, "E_STRUCTURE_STATUS_STAGE", "structure_master_candidate requires a structure stage.", "$.status")
        if set(parsed_stage_kinds) != {"structure"}:
            _issue(
                errors,
                "E_STRUCTURE_CANDIDATE_STAGE_SET",
                "structure_master_candidate permits structure stages only.",
                "$.stages",
            )
    if status == "candidate_unapproved" and set(parsed_stage_kinds) == {"structure"}:
        _issue(
            errors,
            "E_CANDIDATE_UNAPPROVED_STRUCTURE_ONLY",
            (
                "A structure-only plan must use structure_master_candidate, "
                "prompt_package_ready, or qa_failed_directional_retry_ready rather than "
                "candidate_unapproved."
            ),
            "$.status",
        )

    unresolved_rows = [row for row in authority_rows if row["unresolved"]]
    if unresolved_rows and (
        status not in BLOCKED_STATUSES or not has_blocked_stage or actionable_stage_kinds
    ):
        for row in unresolved_rows:
            _issue(
                errors,
                "E_UNRESOLVED_AUTHORITY_EXECUTABLE",
                "Unresolved authority is permitted only in a blocked-only contract.",
                row["path"],
            )

    for stage in parsed_stages:
        kind = stage["kind"]
        if kind not in actionable_stage_kinds:
            continue
        for required_attribute in sorted(REQUIRED_AUTHORITY_BY_STAGE.get(kind, set())):
            covering_rows = [
                row
                for row in authority_rows
                if _pattern_covers(row["attribute"], required_attribute, protected_patterns)
            ]
            resolved_rows = [
                row for row in covering_rows if not row["unresolved"] and row["primary"]
            ]
            if not covering_rows:
                _issue(
                    errors,
                    "E_STAGE_REQUIRED_AUTHORITY_MISSING",
                    f"Stage kind {kind!r} requires authority for {required_attribute!r}.",
                    "$.authority",
                )
            elif not resolved_rows:
                _issue(
                    errors,
                    "E_STAGE_REQUIRED_AUTHORITY_UNRESOLVED",
                    (
                        f"Stage kind {kind!r} requires a resolved primary authority for "
                        f"{required_attribute!r}."
                    ),
                    "$.authority",
                )
            elif not any(
                (row["primary"] | row["allow"]) & stage["inputs"]
                for row in resolved_rows
            ):
                _issue(
                    errors,
                    "E_STAGE_REQUIRED_AUTHORITY_INPUT",
                    (
                        f"Stage {stage['id']!r} does not ingest any primary/allow source "
                        f"authorized for {required_attribute!r}."
                    ),
                    f"{stage['path']}.inputs",
                )

    for ref_id in used_reference_ids:
        permission = permission_by_ref.get(ref_id)
        if permission is not None:
            if permission["role_state"] == "unknown":
                _issue(errors, "E_UNKNOWN_REFERENCE_UPLOADED", f"Reference {ref_id!r} has unknown role_state but is uploaded to a stage.", permission["path"])
            if not permission["allow_attributes"]:
                _issue(errors, "E_INCLUDED_REFERENCE_NO_ALLOW", f"Uploaded reference {ref_id!r} has no allowed attribute role.", permission["path"])

    for row in authority_rows:
        attribute = row["attribute"]
        permitted_refs = reference_ids & (row["primary"] | row["allow"])
        denied_refs = reference_ids & row["deny"]
        if permitted_refs and _is_protected(attribute, protected_patterns):
            _issue(errors, "E_REFERENCE_PROTECTED_STRUCTURE", f"References cannot control protected attribute {attribute!r}: {sorted(permitted_refs)}.", row["path"])
        for ref_id in permitted_refs:
            permission = permission_by_ref.get(ref_id)
            if permission is None:
                continue
            if permission["role_state"] == "unknown":
                _issue(
                    errors,
                    "E_UNKNOWN_REFERENCE_AUTHORITY",
                    f"Unknown-role reference {ref_id!r} cannot receive resolved primary/allow authority.",
                    row["path"],
                )
            if not _permission_matches(permission["allow_attributes"], attribute, protected_patterns):
                _issue(errors, "E_AUTHORITY_PERMISSION_ALLOW_MISSING", f"Authority permits reference {ref_id!r} for {attribute!r}, but its permission does not allow it.", row["path"])
            if _permission_matches(permission["deny_attributes"], attribute, protected_patterns):
                _issue(errors, "E_AUTHORITY_PERMISSION_DENY_CONFLICT", f"Authority permits reference {ref_id!r} for {attribute!r}, but its permission denies it.", row["path"])
        for ref_id in denied_refs:
            permission = permission_by_ref.get(ref_id)
            if permission is None:
                continue
            if _permission_matches(permission["allow_attributes"], attribute, protected_patterns):
                _issue(errors, "E_AUTHORITY_DENY_PERMISSION_ALLOW_CONFLICT", f"Authority denies reference {ref_id!r} for {attribute!r}, but its permission allows it.", row["path"])
            if not _permission_matches(permission["deny_attributes"], attribute, protected_patterns):
                _issue(errors, "E_AUTHORITY_DENY_PERMISSION_MISSING", f"Authority denies reference {ref_id!r} for {attribute!r}, but its permission lacks the matching deny scope.", row["path"])

    for ref_id, permission in permission_by_ref.items():
        for allowed_pattern in permission["allow_attributes"]:
            assigned = any(
                ref_id in (row["primary"] | row["allow"])
                and _pattern_covers(row["attribute"], allowed_pattern, protected_patterns)
                for row in authority_rows
            )
            if not assigned:
                _issue(errors, "E_PERMISSION_ALLOW_WITHOUT_AUTHORITY", f"Reference {ref_id!r} allows {allowed_pattern!r} without a matching authority assignment.", permission["path"])

    truth_value = contract.get("truth_sensitive")
    if not isinstance(truth_value, list):
        _issue(errors, "E_TRUTH_SENSITIVE_TYPE", "truth_sensitive must be an array.", "$.truth_sensitive")
        truth_sensitive: list[Any] = []
    else:
        truth_sensitive = truth_value
    truth_attributes: list[str] = []
    for index, raw_truth in enumerate(truth_sensitive):
        path = f"$.truth_sensitive[{index}]"
        if not isinstance(raw_truth, dict):
            _issue(errors, "E_TRUTH_ROW", "Truth-sensitive row must be an object.", path)
            continue
        _reject_unknown_fields(raw_truth, TRUTH_SENSITIVE_KEYS, path, errors)
        raw_attribute = raw_truth.get("attribute")
        attribute = _validated_attribute_scope(
            raw_attribute, f"{path}.attribute", errors
        )
        if not attribute:
            _issue(errors, "E_TRUTH_ATTRIBUTE", "attribute must be a meaningful string.", f"{path}.attribute")
            continue
        truth_attributes.append(attribute)
        if "required_exact" not in raw_truth or not isinstance(raw_truth.get("required_exact"), bool):
            _issue(errors, "E_REQUIRED_EXACT_TYPE", "required_exact must be a boolean.", f"{path}.required_exact")
            required_exact = False
        else:
            required_exact = raw_truth["required_exact"]
        evidence_ids = _required_string_list(raw_truth, "evidence_ids", path, errors)
        valid_exact_evidence: set[str] = set()
        for evidence_id in evidence_ids:
            if evidence_id not in asset_by_id:
                _issue(errors, "E_UNKNOWN_EXACT_EVIDENCE", f"Unknown exact-evidence asset {evidence_id!r}.", f"{path}.evidence_ids")
            elif any(
                _pattern_covers(exact_scope, attribute, protected_patterns)
                for exact_scope in exact_attributes_by_id.get(evidence_id, set())
            ):
                valid_exact_evidence.add(evidence_id)
        if required_exact and not valid_exact_evidence:
            _issue(errors, "E_EXACT_EVIDENCE_REQUIRED", f"Truth-sensitive attribute {raw_attribute!r} lacks declared exact evidence.", path)
        if required_exact and valid_exact_evidence:
            relevant_evidence = {
                evidence_id
                for evidence_id in valid_exact_evidence
                if action_stage_kinds_by_input.get(evidence_id, set())
                & EVIDENCE_STAGE_KINDS_BY_ASSET_KIND.get(
                    asset_kind.get(evidence_id, ""), set()
                )
            }
            if not relevant_evidence:
                _issue(
                    errors,
                    "E_EXACT_EVIDENCE_UNUSED",
                    (
                        f"Exact evidence for {raw_attribute!r} is declared but is not used "
                        "by a stage compatible with its asset role."
                    ),
                    path,
                )
        if required_exact:
            exact_authority_rows = [
                row
                for row in authority_rows
                if not row["unresolved"]
                and _pattern_covers(row["attribute"], attribute, protected_patterns)
            ]
            if not exact_authority_rows:
                _issue(
                    errors,
                    "E_EXACT_AUTHORITY_MISSING",
                    f"Required exact attribute {raw_attribute!r} lacks resolved authority.",
                    path,
                )
            else:
                primary_exact_evidence = set().union(
                    *(row["primary"] for row in exact_authority_rows)
                ) & valid_exact_evidence
                if not primary_exact_evidence:
                    _issue(
                        errors,
                        "E_EXACT_AUTHORITY_PRIMARY_EVIDENCE",
                        (
                            f"The resolved primary for exact attribute {raw_attribute!r} "
                            "must be one of its valid exact-evidence assets."
                        ),
                        path,
                    )
                else:
                    unused_primary_evidence = {
                        evidence_id
                        for evidence_id in primary_exact_evidence
                        if not (
                            action_stage_kinds_by_input.get(evidence_id, set())
                            & EVIDENCE_STAGE_KINDS_BY_ASSET_KIND.get(
                                asset_kind.get(evidence_id, ""), set()
                            )
                        )
                    }
                    if unused_primary_evidence:
                        _issue(
                            errors,
                            "E_EXACT_AUTHORITY_PRIMARY_UNUSED",
                            (
                                "Resolved primary exact evidence must itself enter a "
                                "compatible manual external stage; unused primary assets: "
                                f"{sorted(unused_primary_evidence)}."
                            ),
                            path,
                        )
    for duplicate_truth in sorted(_duplicates(truth_attributes)):
        _issue(errors, "E_DUPLICATE_TRUTH_ATTRIBUTE", f"Truth-sensitive attribute {duplicate_truth!r} is duplicated.", "$.truth_sensitive")

    return _result(
        errors,
        warnings,
        normalized_exceptions,
        len(target_ids),
        len(reference_ids),
        len(assets),
        len(stages),
        status,
        execution_boundary,
        delivery_state,
        valid_provenance_count,
    )


def _result(
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
    normalized_exceptions: list[dict[str, Any]],
    targets: int,
    references: int,
    assets: int,
    stages: int,
    status: str,
    execution_boundary: str = "",
    delivery_state: str = "",
    imported_results: int = 0,
) -> dict[str, Any]:
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "normalized_exceptions": normalized_exceptions,
        "summary": {
            "targets": targets,
            "references": references,
            "assets": assets,
            "stages": stages,
            "status": status,
            "execution_boundary": execution_boundary,
            "delivery_state": delivery_state,
            "imported_results": imported_results,
        },
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a prompt-only reference-guided reconstruction JSON contract."
    )
    parser.add_argument("contract", help="UTF-8 JSON file path, or - for standard input")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        raw = sys.stdin.read() if args.contract == "-" else Path(args.contract).read_text(encoding="utf-8")
        contract = json.loads(raw, object_pairs_hook=_unique_json_object)
    except DuplicateJsonKeyError as exc:
        result = _result(
            [
                {
                    "code": "E_DUPLICATE_JSON_KEY",
                    "message": str(exc),
                    "path": "$",
                }
            ],
            [],
            [],
            0,
            0,
            0,
            0,
            "",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 2
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        result = _result(
            [{"code": "E_INPUT_JSON", "message": str(exc), "path": "$"}],
            [],
            [],
            0,
            0,
            0,
            0,
            "",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 2
    result = validate_contract(contract)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
