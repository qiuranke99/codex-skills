#!/usr/bin/env python3
"""Deterministic research-evidence contract for material-sensitive products.

This module deliberately separates research prose from generation authority.  Web
observations remain prompt-ineligible evidence.  Only normalized structure tokens
and explicitly graded surface coverage may be consumed by a later source contract.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse


DRAFT_SCHEMA = "material_research_draft.v1"
FROZEN_SCHEMA = "material_research.v1"


class ResearchContractError(ValueError):
    """A fail-closed, machine-readable research contract violation."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


EVIDENCE_CLASSES = {
    "user_source_exact_visible",
    "exact_variant",
    "same_package_family",
    "packaging_archetype",
    "rejected_lead",
}
SOURCE_TYPES = {
    "user_source",
    "official_regulator",
    "official_brand",
    "authorized_retailer",
    "component_manufacturer",
    "technical_standard",
    "packaging_supplier",
    "marketplace_listing",
    "search_result_lead",
    "other",
}
RIGHTS_STATUSES = {
    "user_provided",
    "licensed",
    "official_public_product_media_research_reference",
    "research_reference_only",
    "unknown",
    "restricted",
}
GENERATION_REFERENCE_RIGHTS = {
    "user_provided",
    "licensed",
}
LANES = {"exact_variant", "same_package_family", "packaging_archetype"}
EXECUTION_SURFACES = {"in_app_browser", "web_search_fallback", "user_supplied"}
RUNTIME_STATUSES = {"completed", "unavailable", "failed"}
QUERY_OUTCOMES = {"results_found", "no_results", "blocked"}
SURFACES = {
    "front",
    "rear",
    "left_side",
    "right_side",
    "top",
    "bottom",
    "open_cap",
    "interior",
    "through_body",
    "not_applicable",
}
CLAIM_KINDS = {
    "identity",
    "visible_copy",
    "hidden_copy",
    "surface_geometry",
    "family_topology",
    "structure_mechanism",
    "manufacturing_archetype",
    "material",
    "color",
    "exact_dimension",
    "dimensional_range",
    "conflict",
}
SUPPORT_MODES = {
    "direct_visual",
    "official_record",
    "technical_documentation",
    "marketing_copy",
    "search_snippet",
    "user_statement",
}
AUTHORITIES = {"direct_exact", "exact_official_record", "reconstruction", "rejected"}

RECONSTRUCTION_CLAIMS_SAME_FAMILY = {
    "surface_geometry",
    "family_topology",
    "structure_mechanism",
    "manufacturing_archetype",
    "dimensional_range",
}
RECONSTRUCTION_CLAIMS_ARCHETYPE = {
    "structure_mechanism",
    "manufacturing_archetype",
    "dimensional_range",
}

COVERAGE_AUTHORITIES = {
    "direct_exact_source",
    "exact_variant_hidden_surface",
    "same_family_reconstruction",
    "packaging_archetype_reconstruction",
    "unresolved",
}
COVERAGE_USES = {"exact_render", "reconstruction_only", "not_renderable"}
HIDDEN_SURFACES = {"rear", "left_side", "right_side", "top", "bottom", "open_cap", "interior"}

STRUCTURE_COMPONENTS = {
    "outer_body",
    "cavity",
    "heel_base",
    "cap_shell",
    "cap_retention",
    "actuator",
    "ferrule_collar",
    "neck_finish",
    "pump_housing",
    "valve",
    "gasket",
    "dip_tube",
    "print_layer",
}
STRUCTURE_PROPERTIES = {
    "presence",
    "geometry",
    "mechanism",
    "material",
    "dimensional_range",
    "assembly_order",
}
STRUCTURE_SCOPES = {
    "source_visible_exact",
    "exact_variant_verified",
    "evidence_supported_reconstruction",
    "unknown",
}
FORBIDDEN_EXACT_CLAIMS = {
    "exact_dimensions",
    "exact_material",
    "exact_supplier",
    "exact_hidden_copy",
    "exact_color",
    "exact_component_geometry",
}

FORBIDDEN_CONTENT_KEYS = {
    "prompt",
    "prompt_text",
    "prompt_block",
    "prompt_fragment",
    "provider_prompt",
    "generation_instruction",
    "raw_page_text",
    "page_text",
    "raw_html",
    "page_html",
    "html",
}

ID_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,95}$")
TOKEN_RE = re.compile(r"^[a-z][a-z0-9_]{0,95}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _fail(code: str, detail: str) -> None:
    raise ResearchContractError(code, detail)


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("blocked_material_research_invalid", f"{field} must be an object")
    return value


def _require_list(value: Any, field: str, *, nonempty: bool = False) -> list[Any]:
    if not isinstance(value, list) or (nonempty and not value):
        suffix = "a non-empty array" if nonempty else "an array"
        _fail("blocked_material_research_invalid", f"{field} must be {suffix}")
    return value


def _require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        _fail("blocked_material_research_invalid", f"{field} must be boolean")
    return value


def _require_text(
    value: Any,
    field: str,
    *,
    max_length: int = 600,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        _fail("blocked_material_research_invalid", f"{field} must be text")
    if not allow_empty and not value.strip():
        _fail("blocked_material_research_invalid", f"{field} must not be empty")
    if len(value) > max_length or "\r" in value or "\n" in value or "\x00" in value:
        _fail(
            "blocked_material_research_invalid",
            f"{field} must be one line and at most {max_length} characters",
        )
    return value


def _require_id(value: Any, field: str) -> str:
    text = _require_text(value, field, max_length=96)
    if not ID_RE.fullmatch(text):
        _fail("blocked_material_research_invalid", f"{field} is not a stable lowercase id")
    return text


def _require_token(value: Any, field: str) -> str:
    text = _require_text(value, field, max_length=96)
    if not TOKEN_RE.fullmatch(text):
        _fail("blocked_material_research_prompt_contamination", f"{field} is not a normalized token")
    return text


def _require_sha256(value: Any, field: str) -> str:
    text = _require_text(value, field, max_length=64)
    if not SHA256_RE.fullmatch(text):
        _fail("blocked_material_research_invalid", f"{field} must be lowercase SHA-256")
    return text


def _require_timestamp(value: Any, field: str) -> str:
    text = _require_text(value, field, max_length=40)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        _fail("blocked_material_research_invalid", f"{field} must be RFC 3339")
    if parsed.tzinfo is None:
        _fail("blocked_material_research_invalid", f"{field} must include a timezone")
    return text


def _exact_keys(value: Mapping[str, Any], expected: set[str], field: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        _fail(
            "blocked_material_research_invalid",
            f"{field} key mismatch; missing={missing}, extra={extra}",
        )


def _unique_ids(items: Iterable[Mapping[str, Any]], key: str, field: str) -> set[str]:
    seen: set[str] = set()
    for index, item in enumerate(items):
        item_id = _require_id(item.get(key), f"{field}[{index}].{key}")
        if item_id in seen:
            _fail("blocked_material_research_invalid", f"duplicate {field} id {item_id}")
        seen.add(item_id)
    return seen


def _reject_prompt_material(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.casefold() in FORBIDDEN_CONTENT_KEYS:
                _fail(
                    "blocked_material_research_prompt_contamination",
                    f"raw research or prompt-bearing key is forbidden at {path}.{key}",
                )
            _reject_prompt_material(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_prompt_material(child, f"{path}[{index}]")


def _validate_browser_runtime(items: Any) -> dict[str, dict[str, Any]]:
    runtime = _require_list(items, "browser_runtime", nonempty=True)
    attempts: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(runtime):
        item = _require_mapping(raw, f"browser_runtime[{index}]")
        _exact_keys(
            item,
            {"attempt_id", "requested_tool", "status", "attempted_at", "failure_code", "detail"},
            f"browser_runtime[{index}]",
        )
        attempt_id = _require_id(item["attempt_id"], f"browser_runtime[{index}].attempt_id")
        if attempt_id in attempts:
            _fail("blocked_material_research_invalid", f"duplicate runtime attempt {attempt_id}")
        if item["requested_tool"] != "in_app_browser":
            _fail(
                "blocked_material_research_runtime_provenance",
                "browser-first runtime must name in_app_browser exactly",
            )
        status = item["status"]
        if status not in RUNTIME_STATUSES:
            _fail("blocked_material_research_invalid", f"unsupported runtime status {status!r}")
        _require_timestamp(item["attempted_at"], f"browser_runtime[{index}].attempted_at")
        failure_code = item["failure_code"]
        detail = item["detail"]
        if status == "completed":
            if failure_code is not None or detail is not None:
                _fail(
                    "blocked_material_research_runtime_provenance",
                    "completed browser attempt must not carry failure fields",
                )
        else:
            _require_token(failure_code, f"browser_runtime[{index}].failure_code")
            _require_text(detail, f"browser_runtime[{index}].detail")
        attempts[attempt_id] = item
    return attempts


def _validate_queries(items: Any, attempts: Mapping[str, Mapping[str, Any]]) -> tuple[set[str], dict[str, Any]]:
    queries = _require_list(items, "queries", nonempty=True)
    query_ids = _unique_ids(queries, "query_id", "queries")
    lanes_seen: set[str] = set()
    searched_lanes: set[str] = set()
    by_id: dict[str, Any] = {}
    for index, raw in enumerate(queries):
        item = _require_mapping(raw, f"queries[{index}]")
        _exact_keys(
            item,
            {
                "query_id",
                "lane",
                "query_text",
                "execution_surface",
                "runtime_attempt_id",
                "executed_at",
                "outcome",
                "fallback_reason",
                "evidence_ids",
            },
            f"queries[{index}]",
        )
        query_id = _require_id(item["query_id"], f"queries[{index}].query_id")
        lane = item["lane"]
        if lane not in LANES:
            _fail("blocked_material_research_invalid", f"unsupported research lane {lane!r}")
        lanes_seen.add(lane)
        _require_text(item["query_text"], f"queries[{index}].query_text", max_length=300)
        surface = item["execution_surface"]
        if surface not in EXECUTION_SURFACES:
            _fail("blocked_material_research_runtime_provenance", f"unsupported execution surface {surface!r}")
        attempt_id = item["runtime_attempt_id"]
        fallback_reason = item["fallback_reason"]
        if surface == "user_supplied":
            if attempt_id is not None or fallback_reason is not None:
                _fail(
                    "blocked_material_research_runtime_provenance",
                    "user-supplied evidence cannot claim a browser runtime",
                )
        else:
            searched_lanes.add(lane)
            attempt_id = _require_id(attempt_id, f"queries[{index}].runtime_attempt_id")
            if attempt_id not in attempts:
                _fail("blocked_material_research_runtime_provenance", f"unknown runtime attempt {attempt_id}")
            status = attempts[attempt_id]["status"]
            if surface == "in_app_browser":
                if status != "completed" or fallback_reason is not None:
                    _fail(
                        "blocked_material_research_runtime_provenance",
                        "an in-app-browser query requires a completed in-app-browser attempt",
                    )
            else:
                if status not in {"unavailable", "failed"}:
                    _fail(
                        "blocked_material_research_runtime_provenance",
                        "web fallback is allowed only after a recorded unavailable or failed browser attempt",
                    )
                _require_text(fallback_reason, f"queries[{index}].fallback_reason")
        _require_timestamp(item["executed_at"], f"queries[{index}].executed_at")
        if item["outcome"] not in QUERY_OUTCOMES:
            _fail("blocked_material_research_invalid", f"unsupported query outcome {item['outcome']!r}")
        result_ids = _require_list(item["evidence_ids"], f"queries[{index}].evidence_ids")
        if len(result_ids) != len(set(result_ids)):
            _fail("blocked_material_research_invalid", f"duplicate evidence id in query {query_id}")
        for evidence_id in result_ids:
            _require_id(evidence_id, f"queries[{index}].evidence_ids")
        by_id[query_id] = item
    if lanes_seen != LANES:
        _fail(
            "blocked_material_research_lane_incomplete",
            f"all bounded research lanes are required; missing={sorted(LANES - lanes_seen)}",
        )
    if searched_lanes != LANES:
        _fail(
            "blocked_material_research_lane_incomplete",
            f"each lane requires an in-app-browser or audited fallback query; missing={sorted(LANES - searched_lanes)}",
        )
    return query_ids, by_id


def _validate_capture(
    capture: Any,
    *,
    field: str,
    draft_dir: Path,
) -> dict[str, Any] | None:
    if capture is None:
        return None
    raw = _require_mapping(capture, field)
    _exact_keys(raw, {"path", "sha256", "media_type", "captured_at"}, field)
    path_text = _require_text(raw["path"], f"{field}.path", max_length=2048)
    source_path = Path(path_text)
    if not source_path.is_absolute():
        source_path = draft_dir / source_path
    try:
        resolved = source_path.resolve(strict=True)
    except (OSError, RuntimeError):
        _fail("blocked_research_materialization", f"capture does not exist: {source_path}")
    if not resolved.is_file():
        _fail("blocked_research_materialization", f"capture is not a file: {resolved}")
    expected_hash = _require_sha256(raw["sha256"], f"{field}.sha256")
    actual_hash = sha256_file(resolved)
    if actual_hash != expected_hash:
        _fail(
            "blocked_research_capture_hash_mismatch",
            f"capture {resolved} expected {expected_hash}, got {actual_hash}",
        )
    media_type = _require_text(raw["media_type"], f"{field}.media_type", max_length=100)
    if "/" not in media_type:
        _fail("blocked_material_research_invalid", f"{field}.media_type must be a MIME type")
    _require_timestamp(raw["captured_at"], f"{field}.captured_at")
    return {
        "local_path": str(resolved),
        "sha256": actual_hash,
        "byte_count": resolved.stat().st_size,
        "media_type": media_type,
        "captured_at": raw["captured_at"],
    }


def _validate_url(value: Any, field: str, source_type: str) -> str:
    url = _require_text(value, field, max_length=2048)
    parsed = urlparse(url)
    if source_type == "user_source":
        if parsed.scheme not in {"file", "local"}:
            _fail("blocked_material_research_invalid", f"{field} for user_source must be file:// or local://")
    elif parsed.scheme not in {"http", "https"} or not parsed.netloc:
        _fail("blocked_material_research_invalid", f"{field} must be an absolute http(s) URL")
    return url


def _validate_observation(
    raw: Any,
    *,
    field: str,
    evidence_class: str,
) -> dict[str, Any]:
    item = _require_mapping(raw, field)
    _exact_keys(
        item,
        {"observation_id", "surface", "claim_kind", "support_mode", "statement", "authority", "prompt_eligible"},
        field,
    )
    _require_id(item["observation_id"], f"{field}.observation_id")
    surface = item["surface"]
    claim_kind = item["claim_kind"]
    support_mode = item["support_mode"]
    authority = item["authority"]
    if surface not in SURFACES:
        _fail("blocked_material_research_invalid", f"{field}.surface is unsupported")
    if claim_kind not in CLAIM_KINDS:
        _fail("blocked_material_research_invalid", f"{field}.claim_kind is unsupported")
    if support_mode not in SUPPORT_MODES:
        _fail("blocked_material_research_invalid", f"{field}.support_mode is unsupported")
    if authority not in AUTHORITIES:
        _fail("blocked_material_research_invalid", f"{field}.authority is unsupported")
    _require_text(item["statement"], f"{field}.statement")
    if _require_bool(item["prompt_eligible"], f"{field}.prompt_eligible"):
        _fail(
            "blocked_material_research_prompt_contamination",
            f"{field} research prose must never be prompt-eligible",
        )

    if evidence_class == "user_source_exact_visible":
        if authority != "direct_exact" or support_mode != "direct_visual":
            _fail("blocked_research_fact_authority", f"{field} user source must be direct visual exact evidence")
        if surface not in {"front", "through_body"}:
            _fail("blocked_research_fact_authority", f"{field} user front source cannot authorize {surface}")
    elif evidence_class == "exact_variant":
        if authority not in {"direct_exact", "exact_official_record"}:
            _fail("blocked_research_fact_authority", f"{field} exact evidence has invalid authority")
        if authority == "exact_official_record" and support_mode != "official_record":
            _fail("blocked_research_fact_authority", f"{field} official authority requires an official record")
        if claim_kind == "hidden_copy" or surface in HIDDEN_SURFACES:
            if authority != "direct_exact" or support_mode != "direct_visual":
                _fail(
                    "blocked_exact_hidden_surface_authority",
                    f"{field} hidden exact fact requires direct exact visual evidence",
                )
    elif evidence_class == "same_package_family":
        if authority != "reconstruction" or claim_kind not in RECONSTRUCTION_CLAIMS_SAME_FAMILY:
            _fail(
                "blocked_research_fact_authority",
                f"{field} same-family evidence may support reconstruction topology/mechanism only",
            )
    elif evidence_class == "packaging_archetype":
        if authority != "reconstruction" or claim_kind not in RECONSTRUCTION_CLAIMS_ARCHETYPE:
            _fail(
                "blocked_research_fact_authority",
                f"{field} archetype evidence may support generic mechanisms only",
            )
    else:
        if authority != "rejected":
            _fail("blocked_research_fact_authority", f"{field} rejected lead must remain rejected")
    return item


def _validate_evidence(
    items: Any,
    *,
    draft_dir: Path,
    query_ids: set[str],
    query_by_id: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    evidence = _require_list(items, "evidence", nonempty=True)
    _unique_ids(evidence, "evidence_id", "evidence")
    by_id: dict[str, dict[str, Any]] = {}
    frozen: list[dict[str, Any]] = []
    observation_ids: set[str] = set()
    aliases: set[str] = set()
    for index, raw in enumerate(evidence):
        item = _require_mapping(raw, f"evidence[{index}]")
        _exact_keys(
            item,
            {
                "evidence_id",
                "query_ids",
                "evidence_class",
                "source_type",
                "title",
                "publisher",
                "resolved_url",
                "retrieved_at",
                "rights_status",
                "selected_generation_reference",
                "reference_alias",
                "capture",
                "observations",
            },
            f"evidence[{index}]",
        )
        evidence_id = _require_id(item["evidence_id"], f"evidence[{index}].evidence_id")
        evidence_class = item["evidence_class"]
        source_type = item["source_type"]
        if evidence_class not in EVIDENCE_CLASSES or source_type not in SOURCE_TYPES:
            _fail("blocked_material_research_invalid", f"unsupported evidence class or source type for {evidence_id}")
        linked_queries = _require_list(item["query_ids"], f"evidence[{index}].query_ids", nonempty=True)
        if len(linked_queries) != len(set(linked_queries)):
            _fail("blocked_material_research_invalid", f"duplicate query link for {evidence_id}")
        for query_id in linked_queries:
            _require_id(query_id, f"evidence[{index}].query_ids")
            if query_id not in query_ids:
                _fail("blocked_material_research_invalid", f"evidence {evidence_id} links unknown query {query_id}")
        if evidence_class == "exact_variant" and not any(query_by_id[q]["lane"] == "exact_variant" for q in linked_queries):
            _fail("blocked_research_fact_authority", f"exact evidence {evidence_id} lacks exact-variant query provenance")
        if evidence_class == "same_package_family" and not any(
            query_by_id[q]["lane"] == "same_package_family" for q in linked_queries
        ):
            _fail("blocked_research_fact_authority", f"same-family evidence {evidence_id} lacks family query provenance")
        if evidence_class == "packaging_archetype" and not any(
            query_by_id[q]["lane"] == "packaging_archetype" for q in linked_queries
        ):
            _fail("blocked_research_fact_authority", f"archetype evidence {evidence_id} lacks archetype query provenance")
        _require_text(item["title"], f"evidence[{index}].title")
        _require_text(item["publisher"], f"evidence[{index}].publisher")
        _validate_url(item["resolved_url"], f"evidence[{index}].resolved_url", source_type)
        _require_timestamp(item["retrieved_at"], f"evidence[{index}].retrieved_at")
        rights = item["rights_status"]
        if rights not in RIGHTS_STATUSES:
            _fail("blocked_material_research_invalid", f"unsupported rights status {rights!r}")
        selected = _require_bool(
            item["selected_generation_reference"],
            f"evidence[{index}].selected_generation_reference",
        )
        alias = item["reference_alias"]
        capture = _validate_capture(item["capture"], field=f"evidence[{index}].capture", draft_dir=draft_dir)
        if selected:
            if evidence_class in {"same_package_family", "packaging_archetype", "rejected_lead"}:
                _fail(
                    "blocked_archetype_identity_contamination",
                    f"{evidence_id} cannot enter image-generation references",
                )
            if rights not in GENERATION_REFERENCE_RIGHTS:
                _fail("blocked_reference_generation_rights", f"{evidence_id} has no recorded generation-reference right")
            if capture is None:
                _fail("blocked_selected_reference_capture_missing", f"{evidence_id} selected without verified capture")
            alias = _require_id(alias, f"evidence[{index}].reference_alias")
            if alias in aliases:
                _fail("blocked_material_research_invalid", f"duplicate generation reference alias {alias}")
            aliases.add(alias)
        elif alias is not None:
            _fail("blocked_material_research_invalid", f"unselected evidence {evidence_id} must not have reference_alias")

        observations = _require_list(item["observations"], f"evidence[{index}].observations", nonempty=True)
        validated_observations: list[dict[str, Any]] = []
        for obs_index, observation in enumerate(observations):
            validated = _validate_observation(
                observation,
                field=f"evidence[{index}].observations[{obs_index}]",
                evidence_class=evidence_class,
            )
            observation_id = validated["observation_id"]
            if observation_id in observation_ids:
                _fail("blocked_material_research_invalid", f"duplicate observation id {observation_id}")
            observation_ids.add(observation_id)
            validated_observations.append(copy.deepcopy(validated))
        if capture is None and any(obs["support_mode"] == "direct_visual" for obs in validated_observations):
            _fail(
                "blocked_research_provenance_incomplete",
                f"direct-visual evidence {evidence_id} requires a retained capture and media hash",
            )
        frozen_item = copy.deepcopy(item)
        frozen_item["capture"] = capture
        frozen_item["observations"] = validated_observations
        by_id[evidence_id] = frozen_item
        frozen.append(frozen_item)

    # Query-to-evidence links must be reciprocal, so search results cannot be attached out of band.
    for query_id, query in query_by_id.items():
        for evidence_id in query["evidence_ids"]:
            if evidence_id not in by_id:
                _fail("blocked_material_research_invalid", f"query {query_id} links unknown evidence {evidence_id}")
            if query_id not in by_id[evidence_id]["query_ids"]:
                _fail("blocked_material_research_invalid", f"query/evidence link is not reciprocal for {query_id}/{evidence_id}")
    for evidence_id, item in by_id.items():
        for query_id in item["query_ids"]:
            if evidence_id not in query_by_id[query_id]["evidence_ids"]:
                _fail("blocked_material_research_invalid", f"evidence/query link is not reciprocal for {evidence_id}/{query_id}")
    return by_id, frozen


def _evidence_supports(
    evidence: Mapping[str, Any],
    *,
    surface: str | None = None,
    claim_kind: str | None = None,
    authority: str | None = None,
) -> bool:
    for observation in evidence["observations"]:
        if surface is not None and observation["surface"] != surface:
            continue
        if claim_kind is not None and observation["claim_kind"] != claim_kind:
            continue
        if authority is not None and observation["authority"] != authority:
            continue
        return True
    return False


def _validate_identity(value: Any, evidence_by_id: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    identity = _require_mapping(value, "identity_resolution")
    _exact_keys(
        identity,
        {"target_fingerprint", "candidates", "selected_candidate_id", "selection_basis", "conflicts"},
        "identity_resolution",
    )
    fingerprint = _require_mapping(identity["target_fingerprint"], "identity_resolution.target_fingerprint")
    _exact_keys(
        fingerprint,
        {"visible_strings", "claimed_filename_identity", "capacity_marking", "color_family", "source_sha256"},
        "identity_resolution.target_fingerprint",
    )
    visible_strings = _require_list(fingerprint["visible_strings"], "identity_resolution.target_fingerprint.visible_strings", nonempty=True)
    for index, text in enumerate(visible_strings):
        _require_text(text, f"identity_resolution.target_fingerprint.visible_strings[{index}]")
    if fingerprint["claimed_filename_identity"] is not None:
        _require_text(fingerprint["claimed_filename_identity"], "identity_resolution.target_fingerprint.claimed_filename_identity")
    _require_text(fingerprint["capacity_marking"], "identity_resolution.target_fingerprint.capacity_marking")
    _require_token(fingerprint["color_family"], "identity_resolution.target_fingerprint.color_family")
    _require_sha256(fingerprint["source_sha256"], "identity_resolution.target_fingerprint.source_sha256")

    candidates = _require_list(identity["candidates"], "identity_resolution.candidates", nonempty=True)
    candidate_ids = _unique_ids(candidates, "candidate_id", "identity_resolution.candidates")
    selected_id = _require_id(identity["selected_candidate_id"], "identity_resolution.selected_candidate_id")
    if selected_id not in candidate_ids:
        _fail("blocked_identity_resolution_invalid", "selected identity candidate is missing")
    selected_count = 0
    selected_exact_identity = False
    selected_user_visible_identity = False
    exact_identity_evidence = {
        evidence_id
        for evidence_id, evidence in evidence_by_id.items()
        if evidence["evidence_class"] == "exact_variant"
        and any(
            obs["claim_kind"] == "identity"
            and obs["authority"] in {"direct_exact", "exact_official_record"}
            for obs in evidence["observations"]
        )
    }
    for index, raw in enumerate(candidates):
        item = _require_mapping(raw, f"identity_resolution.candidates[{index}]")
        _exact_keys(item, {"candidate_id", "product_name", "variant_code", "evidence_ids", "state", "reason"}, f"identity_resolution.candidates[{index}]")
        _require_text(item["product_name"], f"identity_resolution.candidates[{index}].product_name")
        if item["variant_code"] is not None:
            _require_text(item["variant_code"], f"identity_resolution.candidates[{index}].variant_code", max_length=100)
        linked = _require_list(item["evidence_ids"], f"identity_resolution.candidates[{index}].evidence_ids", nonempty=True)
        for evidence_id in linked:
            if evidence_id not in evidence_by_id:
                _fail("blocked_identity_resolution_invalid", f"identity candidate links unknown evidence {evidence_id}")
        if item["state"] not in {"selected", "rejected"}:
            _fail("blocked_identity_resolution_invalid", "identity candidate state must be selected or rejected")
        _require_text(item["reason"], f"identity_resolution.candidates[{index}].reason")
        if item["state"] == "selected":
            selected_count += 1
            if item["candidate_id"] != selected_id:
                _fail("blocked_identity_resolution_invalid", "selected candidate marker disagrees with selected_candidate_id")
            selected_exact_identity = any(
                evidence_by_id[evidence_id]["evidence_class"] == "exact_variant"
                and _evidence_supports(evidence_by_id[evidence_id], claim_kind="identity")
                and any(
                    obs["claim_kind"] == "identity"
                    and obs["authority"] in {"direct_exact", "exact_official_record"}
                    for obs in evidence_by_id[evidence_id]["observations"]
                )
                for evidence_id in linked
            )
            selected_user_visible_identity = any(
                evidence_by_id[evidence_id]["evidence_class"] == "user_source_exact_visible"
                and _evidence_supports(evidence_by_id[evidence_id], claim_kind="identity", authority="direct_exact")
                for evidence_id in linked
            )
    _require_token(identity["selection_basis"], "identity_resolution.selection_basis")
    conflicts = _require_list(identity["conflicts"], "identity_resolution.conflicts")
    for index, raw in enumerate(conflicts):
        item = _require_mapping(raw, f"identity_resolution.conflicts[{index}]")
        _exact_keys(item, {"conflict_id", "left_claim", "right_claim", "resolution", "evidence_ids"}, f"identity_resolution.conflicts[{index}]")
        _require_id(item["conflict_id"], f"identity_resolution.conflicts[{index}].conflict_id")
        for key in ("left_claim", "right_claim", "resolution"):
            _require_text(item[key], f"identity_resolution.conflicts[{index}].{key}")
        linked = _require_list(item["evidence_ids"], f"identity_resolution.conflicts[{index}].evidence_ids", nonempty=True)
        for evidence_id in linked:
            if evidence_id not in evidence_by_id:
                _fail("blocked_identity_resolution_invalid", f"identity conflict links unknown evidence {evidence_id}")
    if selected_count != 1:
        _fail("blocked_identity_resolution_invalid", "identity resolution requires exactly one selected candidate")
    if exact_identity_evidence and not selected_exact_identity:
        _fail(
            "blocked_identity_resolution_invalid",
            "available exact-variant identity evidence must take precedence over source-only identity",
        )
    if not exact_identity_evidence and (not selected_user_visible_identity or conflicts):
        _fail(
            "blocked_identity_resolution_invalid",
            "source-only identity is allowed only when directly visible and conflict-free",
        )
    return copy.deepcopy(identity)


def _validate_structure_claims(items: Any, evidence_by_id: Mapping[str, Mapping[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    claims = _require_list(items, "structure_claims")
    _unique_ids(claims, "claim_id", "structure_claims")
    by_id: dict[str, dict[str, Any]] = {}
    frozen: list[dict[str, Any]] = []
    for index, raw in enumerate(claims):
        item = _require_mapping(raw, f"structure_claims[{index}]")
        _exact_keys(
            item,
            {"claim_id", "component", "property", "normalized_value", "scope", "evidence_ids", "allowed_surfaces", "forbidden_exact_claims"},
            f"structure_claims[{index}]",
        )
        claim_id = _require_id(item["claim_id"], f"structure_claims[{index}].claim_id")
        if item["component"] not in STRUCTURE_COMPONENTS or item["property"] not in STRUCTURE_PROPERTIES:
            _fail("blocked_material_research_invalid", f"unsupported structure component/property in {claim_id}")
        _require_token(item["normalized_value"], f"structure_claims[{index}].normalized_value")
        scope = item["scope"]
        if scope not in STRUCTURE_SCOPES:
            _fail("blocked_material_research_invalid", f"unsupported structure scope {scope!r}")
        linked = _require_list(item["evidence_ids"], f"structure_claims[{index}].evidence_ids", nonempty=scope != "unknown")
        for evidence_id in linked:
            if evidence_id not in evidence_by_id:
                _fail("blocked_material_research_invalid", f"structure claim {claim_id} links unknown evidence {evidence_id}")
        surfaces = _require_list(item["allowed_surfaces"], f"structure_claims[{index}].allowed_surfaces", nonempty=scope != "unknown")
        for surface in surfaces:
            if surface not in SURFACES - {"not_applicable"}:
                _fail("blocked_material_research_invalid", f"structure claim {claim_id} has unsupported surface")
        forbidden = _require_list(item["forbidden_exact_claims"], f"structure_claims[{index}].forbidden_exact_claims")
        if any(value not in FORBIDDEN_EXACT_CLAIMS for value in forbidden):
            _fail("blocked_material_research_invalid", f"structure claim {claim_id} has invalid forbidden exact claim")
        if scope == "source_visible_exact":
            if not linked or any(evidence_by_id[e]["evidence_class"] != "user_source_exact_visible" for e in linked):
                _fail("blocked_research_fact_authority", f"source-visible claim {claim_id} requires user source evidence")
        elif scope == "exact_variant_verified":
            if not linked or any(evidence_by_id[e]["evidence_class"] != "exact_variant" for e in linked):
                _fail("blocked_research_fact_authority", f"exact claim {claim_id} requires exact-variant evidence")
        elif scope == "evidence_supported_reconstruction":
            if not linked or any(
                evidence_by_id[e]["evidence_class"] not in {"same_package_family", "packaging_archetype"}
                for e in linked
            ):
                _fail("blocked_research_fact_authority", f"reconstruction {claim_id} has invalid evidence class")
            if not forbidden:
                _fail(
                    "blocked_research_fact_authority",
                    f"reconstruction {claim_id} must explicitly deny exact claims",
                )
        else:
            if linked or surfaces or forbidden:
                _fail("blocked_material_research_invalid", f"unknown claim {claim_id} must not carry authority")
        frozen_item = copy.deepcopy(item)
        by_id[claim_id] = frozen_item
        frozen.append(frozen_item)
    return by_id, frozen


def _validate_surface_coverage(
    items: Any,
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    structure_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    coverage = _require_list(items, "surface_coverage", nonempty=True)
    _unique_ids(coverage, "coverage_id", "surface_coverage")
    surfaces_seen: set[str] = set()
    frozen: list[dict[str, Any]] = []
    for index, raw in enumerate(coverage):
        item = _require_mapping(raw, f"surface_coverage[{index}]")
        _exact_keys(item, {"coverage_id", "surface", "authority", "usable_for", "evidence_ids", "structure_claim_ids"}, f"surface_coverage[{index}]")
        surface = item["surface"]
        authority = item["authority"]
        usable_for = item["usable_for"]
        if surface not in SURFACES - {"not_applicable"} or surface in surfaces_seen:
            _fail("blocked_material_research_invalid", f"duplicate or unsupported surface coverage {surface!r}")
        surfaces_seen.add(surface)
        if authority not in COVERAGE_AUTHORITIES or usable_for not in COVERAGE_USES:
            _fail("blocked_material_research_invalid", f"invalid coverage authority/use for {surface}")
        evidence_ids = _require_list(item["evidence_ids"], f"surface_coverage[{index}].evidence_ids")
        claim_ids = _require_list(item["structure_claim_ids"], f"surface_coverage[{index}].structure_claim_ids")
        for evidence_id in evidence_ids:
            if evidence_id not in evidence_by_id:
                _fail("blocked_material_research_invalid", f"coverage {surface} links unknown evidence {evidence_id}")
        for claim_id in claim_ids:
            if claim_id not in structure_by_id:
                _fail("blocked_material_research_invalid", f"coverage {surface} links unknown structure claim {claim_id}")
            if surface not in structure_by_id[claim_id]["allowed_surfaces"]:
                _fail("blocked_research_surface_authority", f"structure claim {claim_id} does not authorize {surface}")

        if authority == "direct_exact_source":
            if usable_for != "exact_render" or claim_ids:
                _fail("blocked_research_surface_authority", f"direct source coverage for {surface} has invalid use")
            if not evidence_ids or any(
                evidence_by_id[e]["evidence_class"] not in {"user_source_exact_visible", "exact_variant"}
                or not _evidence_supports(evidence_by_id[e], surface=surface, authority="direct_exact")
                for e in evidence_ids
            ):
                _fail("blocked_research_surface_authority", f"direct source coverage for {surface} lacks exact visual evidence")
        elif authority == "exact_variant_hidden_surface":
            if surface not in HIDDEN_SURFACES or usable_for != "exact_render" or claim_ids:
                _fail("blocked_research_surface_authority", f"exact hidden coverage has invalid surface/use for {surface}")
            if not evidence_ids or any(
                evidence_by_id[e]["evidence_class"] != "exact_variant"
                or not _evidence_supports(evidence_by_id[e], surface=surface, authority="direct_exact")
                for e in evidence_ids
            ):
                _fail("blocked_research_surface_authority", f"exact hidden coverage for {surface} lacks direct exact capture")
        elif authority == "same_family_reconstruction":
            if usable_for != "reconstruction_only" or not evidence_ids or not claim_ids:
                _fail("blocked_research_surface_authority", f"same-family coverage for {surface} is incomplete")
            if any(evidence_by_id[e]["evidence_class"] != "same_package_family" for e in evidence_ids):
                _fail("blocked_research_surface_authority", f"same-family coverage for {surface} launders another class")
            if any(structure_by_id[c]["scope"] != "evidence_supported_reconstruction" for c in claim_ids):
                _fail("blocked_research_surface_authority", f"same-family coverage for {surface} links an exact claim")
        elif authority == "packaging_archetype_reconstruction":
            if usable_for != "reconstruction_only" or not evidence_ids or not claim_ids:
                _fail("blocked_research_surface_authority", f"archetype coverage for {surface} is incomplete")
            if any(evidence_by_id[e]["evidence_class"] != "packaging_archetype" for e in evidence_ids):
                _fail("blocked_research_surface_authority", f"archetype coverage for {surface} launders another class")
            if any(structure_by_id[c]["scope"] != "evidence_supported_reconstruction" for c in claim_ids):
                _fail("blocked_research_surface_authority", f"archetype coverage for {surface} links an exact claim")
        else:
            if usable_for != "not_renderable" or evidence_ids or claim_ids:
                _fail("blocked_research_surface_authority", f"unresolved surface {surface} must carry no authority")
        frozen.append(copy.deepcopy(item))
    if "front" not in surfaces_seen:
        _fail("blocked_material_research_invalid", "surface coverage must include front")
    return frozen


def _decision_policy() -> dict[str, Any]:
    return {
        "browser_first_required": True,
        "fallback_must_record_browser_failure": True,
        "raw_research_text_prompt_eligible": False,
        "research_artifact_is_prompt_source": False,
        "same_family_exact_fact_upgrade_allowed": False,
        "archetype_exact_fact_upgrade_allowed": False,
        "hidden_copy_requires_exact_variant_direct_capture": True,
        "selected_reference_requires_verified_capture": True,
        "selected_reference_requires_rights_record": True,
    }


def freeze_research_document(draft: Mapping[str, Any], *, draft_dir: Path) -> dict[str, Any]:
    """Validate a draft and return a canonical, self-hashed frozen document."""

    draft_copy = copy.deepcopy(_require_mapping(draft, "draft"))
    _reject_prompt_material(draft_copy)
    _exact_keys(
        draft_copy,
        {
            "schema",
            "subject_id",
            "research_epoch",
            "target_source_sha256",
            "browser_runtime",
            "queries",
            "evidence",
            "identity_resolution",
            "surface_coverage",
            "structure_claims",
        },
        "draft",
    )
    if draft_copy["schema"] != DRAFT_SCHEMA:
        _fail("blocked_material_research_invalid", f"draft schema must be {DRAFT_SCHEMA}")
    subject_id = _require_id(draft_copy["subject_id"], "subject_id")
    research_epoch = _require_id(draft_copy["research_epoch"], "research_epoch")
    target_source_sha256 = _require_sha256(draft_copy["target_source_sha256"], "target_source_sha256")
    attempts = _validate_browser_runtime(draft_copy["browser_runtime"])
    query_ids, query_by_id = _validate_queries(draft_copy["queries"], attempts)
    evidence_by_id, evidence = _validate_evidence(
        draft_copy["evidence"],
        draft_dir=draft_dir,
        query_ids=query_ids,
        query_by_id=query_by_id,
    )
    identity = _validate_identity(draft_copy["identity_resolution"], evidence_by_id)
    structure_by_id, structure = _validate_structure_claims(draft_copy["structure_claims"], evidence_by_id)
    coverage = _validate_surface_coverage(draft_copy["surface_coverage"], evidence_by_id, structure_by_id)

    frozen: dict[str, Any] = {
        "schema": FROZEN_SCHEMA,
        "subject_id": subject_id,
        "research_epoch": research_epoch,
        "target_source_sha256": target_source_sha256,
        "browser_runtime": copy.deepcopy(draft_copy["browser_runtime"]),
        "queries": copy.deepcopy(draft_copy["queries"]),
        "evidence": evidence,
        "identity_resolution": identity,
        "surface_coverage": coverage,
        "structure_claims": structure,
        "decision_policy": _decision_policy(),
    }
    frozen["artifact_sha256"] = sha256_bytes(canonical_json_bytes(frozen))
    return frozen


def validate_frozen_research_document(value: Mapping[str, Any]) -> dict[str, Any]:
    """Verify self-hash, immutable policy, and the complete frozen research semantics."""

    document = copy.deepcopy(_require_mapping(value, "material-research"))
    _exact_keys(
        document,
        {
            "schema",
            "subject_id",
            "research_epoch",
            "target_source_sha256",
            "browser_runtime",
            "queries",
            "evidence",
            "identity_resolution",
            "surface_coverage",
            "structure_claims",
            "decision_policy",
            "artifact_sha256",
        },
        "material-research",
    )
    if document["schema"] != FROZEN_SCHEMA:
        _fail("blocked_material_research_invalid", f"frozen schema must be {FROZEN_SCHEMA}")
    recorded = _require_sha256(document.pop("artifact_sha256"), "artifact_sha256")
    actual = sha256_bytes(canonical_json_bytes(document))
    if recorded != actual:
        _fail("blocked_material_research_hash_mismatch", f"expected {recorded}, got {actual}")
    if document["decision_policy"] != _decision_policy():
        _fail("blocked_material_research_policy_mismatch", "decision policy is not the frozen fail-closed policy")
    replay_evidence = copy.deepcopy(document["evidence"])
    for evidence in replay_evidence:
        capture = evidence["capture"]
        if capture is not None:
            evidence["capture"] = {
                "path": capture["local_path"],
                "sha256": capture["sha256"],
                "media_type": capture["media_type"],
                "captured_at": capture["captured_at"],
            }
    replay_draft = {
        "schema": DRAFT_SCHEMA,
        "subject_id": document["subject_id"],
        "research_epoch": document["research_epoch"],
        "target_source_sha256": document["target_source_sha256"],
        "browser_runtime": document["browser_runtime"],
        "queries": document["queries"],
        "evidence": replay_evidence,
        "identity_resolution": document["identity_resolution"],
        "surface_coverage": document["surface_coverage"],
        "structure_claims": document["structure_claims"],
    }
    replayed = freeze_research_document(replay_draft, draft_dir=Path.cwd())
    replayed_recorded = replayed.pop("artifact_sha256")
    if replayed != document or replayed_recorded != recorded:
        _fail(
            "blocked_material_research_semantic_mismatch",
            "frozen research is not the deterministic rendering of its validated semantics",
        )
    for index, evidence in enumerate(document["evidence"]):
        capture = evidence.get("capture") if isinstance(evidence, dict) else None
        if capture is None:
            continue
        capture = _require_mapping(capture, f"evidence[{index}].capture")
        _exact_keys(
            capture,
            {"local_path", "sha256", "byte_count", "media_type", "captured_at"},
            f"evidence[{index}].capture",
        )
        path = Path(_require_text(capture["local_path"], f"evidence[{index}].capture.local_path", max_length=2048))
        try:
            resolved = path.resolve(strict=True)
        except (OSError, RuntimeError):
            _fail("blocked_research_materialization", f"frozen capture is missing: {path}")
        if not resolved.is_file():
            _fail("blocked_research_materialization", f"frozen capture is not a file: {resolved}")
        expected_hash = _require_sha256(capture["sha256"], f"evidence[{index}].capture.sha256")
        actual_hash = sha256_file(resolved)
        if actual_hash != expected_hash or resolved.stat().st_size != capture["byte_count"]:
            _fail(
                "blocked_research_capture_hash_mismatch",
                f"frozen capture changed after freeze: {resolved}",
            )
    document["artifact_sha256"] = recorded
    return document


def load_frozen_research(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail("blocked_material_research_invalid", f"cannot load frozen research: {exc}")
    return validate_frozen_research_document(value)
