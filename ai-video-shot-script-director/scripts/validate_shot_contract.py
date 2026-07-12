#!/usr/bin/env python3
"""Validate an AI Video Professional Shot Contract using only the standard library."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from revision_evidence import keyed_changes, revision_semantic_view, validate_predecessor_evidence


SHOT_UID_RE = re.compile(r"^[A-Z][A-Z0-9_-]*[0-9][A-Z0-9_-]*$")
HASH_RE = re.compile(r"^[a-f0-9]{64}$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")

SOURCE_FIELDS = {"source_id", "locator", "source_type", "file_sha256", "integrity_status", "authority_scope", "extraction_status"}
CLASSIFICATION_FIELDS = {"source_type", "creative_mode", "primary_mode", "narrative_logic", "product_expression", "literal_usage_demo", "source_intent_preserved"}
PRODUCTION_FIELDS = {"aspect_ratio", "distribution_context", "source_language", "copy_policy"}
GRAMMAR_FIELDS = {
    "lens_and_scale_tendencies", "camera_movement_principles", "composition_rules", "cutting_motivations",
    "performance_restraint", "product_reveal_strategy", "motion_rhythm", "immutable_core",
}
TIMELINE_FIELDS = {"total_duration_seconds", "numerical_tolerance_seconds", "shot_count"}
SHOT_FIELDS = {
    "shot_uid", "display_no", "target_duration_seconds", "submode", "narrative_function", "advertising_function",
    "subjects", "product_or_prop", "scene", "initial_state", "action_path", "ending_state", "shot_size", "camera_height",
    "camera_angle", "lens_intent", "composition", "subject_placement", "primary_camera_movement", "focus_behavior", "blocking",
    "screen_direction", "continuity_in", "continuity_out", "cut_motivation", "transition_intent", "visible_emotional_expression",
    "spoken_content", "on_screen_copy", "must_preserve", "must_avoid", "required_assets", "storyboard_requirement",
    "keyframe_requirement", "previs_requirement",
}
SPOKEN_FIELDS = {"mode", "text", "copy_status", "source_reference_ids", "claim_ids"}
COPY_FIELDS = {"text", "copy_status", "source_reference_ids", "claim_ids", "timing_intent"}
CONTINUITY_FIELDS = {"from_shot_uid", "to_shot_uid", "continuity_type", "preserved_state", "cut_reason"}
ASSET_MAP_FIELDS = {"shot_uid", "requirements", "risk_note"}
REQUIREMENT_MAP_FIELDS = {"shot_uid", "requirement", "reason"}
INFERENCE_FIELDS = {"field_path", "decision", "rationale", "confidence", "source_basis", "reversible"}
CLAIM_FIELDS = {"supplied_claims", "used_claim_ids", "prohibited_unsourced_claims", "compliance_unknowns", "claim_generation_status"}
SUPPLIED_CLAIM_FIELDS = {"claim_id", "text", "source_reference_ids"}
REVISION_FIELDS = {
    "mode", "requested_shot_uids", "actually_changed_shot_uids", "global_fields_changed",
    "expanded_dependency_reasons", "invalidated_artifact_ids", "preserved_artifact_ids",
    "predecessor_artifact", "changed_json_pointers",
}
BLOCKER_FIELDS = {"blocker_id", "blocker_type", "required_fact", "reason", "affected_shot_uids", "unaffected_work_completed"}
HARD_BLOCKER_TYPES = {
    "mutually_exclusive_brand_direction", "exact_legally_material_claim",
    "unavailable_exact_supplied_copy", "target_product_source_conflict",
}


def canonical_sha256(record: dict[str, Any]) -> str:
    """Hash canonical JSON after excluding only the envelope's top-level sha256."""
    payload = dict(record)
    payload.pop("sha256", None)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def verify_declared_file_hashes(record: dict[str, Any], file_root: Path) -> list[str]:
    errors: list[str] = []
    resolved_root = file_root.resolve()
    for index, source in enumerate(record.get("source_inputs", []) if isinstance(record.get("source_inputs"), list) else []):
        if not isinstance(source, dict) or source.get("integrity_status") != "verified_bytes":
            continue
        locator = source.get("locator")
        if not isinstance(locator, str) or not locator:
            errors.append(f"source_inputs[{index}] verified locator missing")
            continue
        path = Path(locator)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"source_inputs[{index}] verified locator must be project-root-relative without traversal: {locator}")
            continue
        candidate = (resolved_root / path).resolve()
        try:
            candidate.relative_to(resolved_root)
        except ValueError:
            errors.append(f"source_inputs[{index}] verified locator escapes file root: {locator}")
            continue
        if not candidate.is_file():
            errors.append(f"source_inputs[{index}] verified file missing: {locator}")
            continue
        actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if actual != source.get("file_sha256"):
            errors.append(f"source_inputs[{index}] file_sha256 mismatch")
    return errors


def _required_object(record: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = record.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key}: required object")
        return {}
    return value


def _required_list(record: dict[str, Any], key: str, errors: list[str]) -> list[Any]:
    value = record.get(key)
    if not isinstance(value, list):
        errors.append(f"{key}: required array")
        return []
    return value


def _exact_fields(value: Any, expected: set[str], label: str, errors: list[str]) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return False
    if set(value) != expected:
        errors.append(f"{label} must contain exact fields: {sorted(expected)}")
        return False
    return True


def _validate_contract(record: dict[str, Any], previous_record: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version", "contract_version", "artifact_id", "owner_skill", "version", "sha256",
        "approval_status", "dependencies", "affected_shot_uids", "stale_reason", "project_id",
        "source_inputs", "source_classification", "director_intent", "production_spec", "global_directing_grammar", "global_directing_prompt_full", "timeline", "shots",
        "continuity_map", "asset_requirement_map", "keyframe_requirement_map", "previs_requirement_map",
        "inferred_directing_decisions", "claim_boundary", "isolated_blockers", "revision_scope",
    }
    missing = sorted(required - record.keys())
    if missing:
        errors.append("missing root fields: " + ", ".join(missing))
    extra = sorted(set(record) - required)
    if extra:
        errors.append("unexpected root fields: " + ", ".join(extra))

    if record.get("schema_version") != "ai-video-shot-contract.v1":
        errors.append("schema_version must be ai-video-shot-contract.v1")
    if record.get("contract_version") != "ai-video-artifact-v1":
        errors.append("contract_version must be ai-video-artifact-v1")
    if record.get("owner_skill") != "ai-video-shot-script-director":
        errors.append("owner_skill must be ai-video-shot-script-director")
    if not _nonempty(record.get("artifact_id")):
        errors.append("artifact_id must be non-empty")
    if not isinstance(record.get("version"), str) or not VERSION_RE.fullmatch(record["version"]):
        errors.append("version must use semantic x.y.z form")
    if not _nonempty(record.get("project_id")):
        errors.append("project_id must be non-empty")
    if not _nonempty(record.get("director_intent")):
        errors.append("director_intent must be non-empty")

    source_inputs = _required_list(record, "source_inputs", errors)
    source_ids: list[str] = []
    for index, source in enumerate(source_inputs):
        if not isinstance(source, dict):
            errors.append(f"source_inputs[{index}] must be an object")
            continue
        _exact_fields(source, SOURCE_FIELDS, f"source_inputs[{index}]", errors)
        source_id = source.get("source_id")
        if not _nonempty(source_id):
            errors.append(f"source_inputs[{index}].source_id required")
        else:
            source_ids.append(source_id)
        if not _nonempty(source.get("locator")) or not _nonempty(source.get("source_type")):
            errors.append(f"source_inputs[{index}] locator/source_type required")
        if not isinstance(source.get("authority_scope"), list) or not source["authority_scope"] or not all(_nonempty(item) for item in source["authority_scope"]):
            errors.append(f"source_inputs[{index}].authority_scope required")
        if source.get("extraction_status") not in {"complete", "partial"}:
            errors.append(f"source_inputs[{index}].extraction_status invalid")
        integrity = source.get("integrity_status")
        if integrity not in {"verified_bytes", "runtime_reference_bound", "unavailable"}:
            errors.append(f"source_inputs[{index}].integrity_status invalid")
        if integrity == "verified_bytes":
            source_hash = source.get("file_sha256")
            if not isinstance(source_hash, str) or not HASH_RE.fullmatch(source_hash):
                errors.append(f"source_inputs[{index}] verified_bytes requires file_sha256")
    if not source_ids or len(source_ids) != len(set(source_ids)):
        errors.append("source_inputs must have unique source IDs")
    source_id_set = set(source_ids)

    production = _required_object(record, "production_spec", errors)
    _exact_fields(production, PRODUCTION_FIELDS, "production_spec", errors)
    aspect_ratio = production.get("aspect_ratio")
    if not isinstance(aspect_ratio, str) or not re.fullmatch(r"^[0-9]+:[0-9]+$", aspect_ratio):
        errors.append("production_spec.aspect_ratio must use W:H form")
    if not isinstance(production.get("distribution_context"), list) or not production["distribution_context"] or not all(_nonempty(item) for item in production["distribution_context"]):
        errors.append("production_spec.distribution_context must be non-empty")
    if not _nonempty(production.get("source_language")) or not _nonempty(production.get("copy_policy")):
        errors.append("production_spec source_language/copy_policy required")

    approval = record.get("approval_status")
    allowed_approvals = {"draft", "assistant_validated", "user_approved", "stale", "blocked"}
    if approval not in allowed_approvals:
        errors.append(f"approval_status invalid: {approval!r}")
    digest = record.get("sha256")
    if approval == "draft":
        if digest is not None:
            errors.append("draft sha256 must be null")
    else:
        if not isinstance(digest, str) or not HASH_RE.fullmatch(digest):
            errors.append("non-draft sha256 must be 64 lowercase hex characters")
        else:
            expected = canonical_sha256(record)
            if digest != expected:
                errors.append(f"sha256 mismatch: expected {expected}")

    stale_reason = record.get("stale_reason")
    if approval == "stale" and not _nonempty(stale_reason):
        errors.append("stale artifact requires non-empty stale_reason")
    if approval != "stale" and stale_reason is not None:
        errors.append("non-stale artifact must use stale_reason: null")

    dependencies = _required_list(record, "dependencies", errors)
    for index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            errors.append(f"dependencies[{index}] must be an object")
            continue
        if set(dependency) != {"artifact_id", "owner_skill", "version", "sha256"}:
            errors.append(f"dependencies[{index}] must contain exactly artifact_id/owner_skill/version/sha256")
        for field in ("artifact_id", "owner_skill", "version", "sha256"):
            if field not in dependency:
                errors.append(f"dependencies[{index}] missing {field}")
        if not _nonempty(dependency.get("artifact_id")) or not _nonempty(dependency.get("owner_skill")):
            errors.append(f"dependencies[{index}] artifact_id/owner_skill required")
        dep_version = dependency.get("version")
        if not isinstance(dep_version, str) or not VERSION_RE.fullmatch(dep_version):
            errors.append(f"dependencies[{index}].version must be SemVer")
        dep_hash = dependency.get("sha256")
        if not isinstance(dep_hash, str) or not HASH_RE.fullmatch(dep_hash):
            errors.append(f"dependencies[{index}].sha256 invalid")

    classification = _required_object(record, "source_classification", errors)
    _exact_fields(classification, CLASSIFICATION_FIELDS, "source_classification", errors)
    creative_mode = classification.get("creative_mode")
    modes = {"poetic_brand_film", "functional_demonstration", "narrative_advertisement", "mixed_mode"}
    if creative_mode not in modes:
        errors.append("source_classification.creative_mode invalid")
    if classification.get("source_intent_preserved") is not True:
        errors.append("source_classification.source_intent_preserved must be true")
    if classification.get("primary_mode") not in {"poetic_brand_film", "functional_demonstration", "narrative_advertisement"}:
        errors.append("source_classification.primary_mode invalid")
    if not _nonempty(classification.get("narrative_logic")) or not _nonempty(classification.get("product_expression")):
        errors.append("source_classification narrative_logic/product_expression required")
    if creative_mode == "poetic_brand_film" and classification.get("literal_usage_demo") is not False:
        errors.append("poetic_brand_film must not be silently converted into a literal usage demo")

    grammar = _required_object(record, "global_directing_grammar", errors)
    _exact_fields(grammar, GRAMMAR_FIELDS, "global_directing_grammar", errors)
    grammar_fields = (
        "lens_and_scale_tendencies", "camera_movement_principles", "composition_rules", "cutting_motivations",
        "performance_restraint", "product_reveal_strategy", "motion_rhythm", "immutable_core",
    )
    for field in grammar_fields:
        values = grammar.get(field)
        if not isinstance(values, list) or not values or not all(_nonempty(item) for item in values):
            errors.append(f"global_directing_grammar.{field} must be a non-empty string array")
    if isinstance(grammar.get("immutable_core"), list) and len(grammar["immutable_core"]) < 3:
        errors.append("global_directing_grammar.immutable_core requires at least 3 rules")
    prompt_full = record.get("global_directing_prompt_full")
    if not _nonempty(prompt_full) or len(prompt_full.strip()) < 40:
        errors.append("global_directing_prompt_full must be a frozen production-ready block")
    else:
        for field in grammar_fields:
            values = grammar.get(field)
            for rule in values if isinstance(values, list) else []:
                if rule not in prompt_full:
                    errors.append(f"global_directing_prompt_full missing exact rule from {field}: {rule}")

    timeline = _required_object(record, "timeline", errors)
    _exact_fields(timeline, TIMELINE_FIELDS, "timeline", errors)
    shots = _required_list(record, "shots", errors)
    total = timeline.get("total_duration_seconds")
    tolerance = timeline.get("numerical_tolerance_seconds")
    shot_count = timeline.get("shot_count")
    if not isinstance(total, (int, float)) or isinstance(total, bool) or not math.isfinite(total) or total <= 0:
        errors.append("timeline.total_duration_seconds must be a finite positive number")
        total = 0.0
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or not math.isfinite(tolerance) or not 0 <= tolerance <= 0.01:
        errors.append("timeline.numerical_tolerance_seconds must be within 0..0.01")
        tolerance = 0.0
    if shot_count != len(shots):
        errors.append(f"timeline.shot_count {shot_count!r} does not equal shots length {len(shots)}")

    shot_uids: list[str] = []
    display_numbers: list[int] = []
    duration_sum = 0.0
    copy_claim_ids: set[str] = set()
    shot_required_fields = (
        "narrative_function", "advertising_function", "scene", "initial_state", "ending_state", "shot_size",
        "camera_height", "camera_angle", "lens_intent", "composition", "subject_placement",
        "primary_camera_movement", "focus_behavior", "blocking", "screen_direction", "continuity_in",
        "continuity_out", "cut_motivation", "transition_intent", "visible_emotional_expression",
    )
    for index, shot in enumerate(shots):
        if not isinstance(shot, dict):
            errors.append(f"shots[{index}] must be an object")
            continue
        _exact_fields(shot, SHOT_FIELDS, f"shots[{index}]", errors)
        uid = shot.get("shot_uid")
        if not isinstance(uid, str) or not SHOT_UID_RE.fullmatch(uid):
            errors.append(f"shots[{index}].shot_uid invalid")
        else:
            shot_uids.append(uid)
        display_no = shot.get("display_no")
        if not isinstance(display_no, int) or isinstance(display_no, bool) or display_no < 1:
            errors.append(f"shots[{index}].display_no invalid")
        else:
            display_numbers.append(display_no)
        duration = shot.get("target_duration_seconds")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool) or not math.isfinite(duration) or duration <= 0:
            errors.append(f"shots[{index}].target_duration_seconds invalid")
        else:
            duration_sum += float(duration)
        for field in shot_required_fields:
            if not _nonempty(shot.get(field)):
                errors.append(f"shots[{index}].{field} must be non-empty")
        action_path = shot.get("action_path")
        if not isinstance(action_path, list) or not action_path or not all(_nonempty(item) for item in action_path):
            errors.append(f"shots[{index}].action_path must contain observable actions")
        for field in ("subjects", "must_preserve", "must_avoid"):
            values = shot.get(field)
            if not isinstance(values, list) or not values or not all(_nonempty(item) for item in values):
                errors.append(f"shots[{index}].{field} must be a non-empty string array")
        for field in ("product_or_prop", "required_assets"):
            values = shot.get(field)
            if not isinstance(values, list) or not all(_nonempty(item) for item in values) or len(values) != len(set(values)):
                errors.append(f"shots[{index}].{field} must be a unique string array")
        if shot.get("submode") not in {"poetic_brand_film", "functional_demonstration", "narrative_advertisement"}:
            errors.append(f"shots[{index}].submode invalid")
        if shot.get("storyboard_requirement") not in {"required", "not_required"}:
            errors.append(f"shots[{index}].storyboard_requirement invalid")
        if shot.get("keyframe_requirement") not in {"required_single_anchor", "required_state_ladder", "recommended", "not_required"}:
            errors.append(f"shots[{index}].keyframe_requirement invalid")
        if shot.get("previs_requirement") not in {"required", "recommended", "not_required"}:
            errors.append(f"shots[{index}].previs_requirement invalid")
        spoken = shot.get("spoken_content")
        if not isinstance(spoken, dict):
            errors.append(f"shots[{index}].spoken_content required")
        else:
            _exact_fields(spoken, SPOKEN_FIELDS, f"shots[{index}].spoken_content", errors)
            mode = spoken.get("mode")
            status = spoken.get("copy_status")
            text_value = spoken.get("text")
            copy_source_ids = spoken.get("source_reference_ids")
            claim_ids = spoken.get("claim_ids")
            if mode not in {"none", "voiceover", "dialogue"}:
                errors.append(f"shots[{index}].spoken_content.mode invalid")
            if not isinstance(copy_source_ids, list) or not isinstance(claim_ids, list):
                errors.append(f"shots[{index}].spoken_content source/claim IDs must be arrays")
                copy_source_ids, claim_ids = [], []
            copy_claim_ids.update(item for item in claim_ids if isinstance(item, str))
            if mode == "none":
                if text_value != "" or status != "not_used" or copy_source_ids or claim_ids:
                    errors.append(f"shots[{index}].spoken_content none mode must be empty and not_used")
            else:
                if not _nonempty(text_value) or status not in {"supplied_exact", "provisional_nonclaim", "source_supported_claim"}:
                    errors.append(f"shots[{index}].spoken_content active mode requires text and copy status")
                if status in {"supplied_exact", "source_supported_claim"} and not copy_source_ids:
                    errors.append(f"shots[{index}].spoken_content source-backed copy requires source IDs")
                if set(copy_source_ids) - source_id_set:
                    errors.append(f"shots[{index}].spoken_content references unknown sources")
                if status == "source_supported_claim" and not claim_ids:
                    errors.append(f"shots[{index}].spoken_content claim copy requires claim IDs")
                if status == "provisional_nonclaim" and claim_ids:
                    errors.append(f"shots[{index}].spoken_content provisional copy cannot carry claims")
        on_screen = shot.get("on_screen_copy")
        if not isinstance(on_screen, list):
            errors.append(f"shots[{index}].on_screen_copy must be an array")
        else:
            for copy_index, copy_record in enumerate(on_screen):
                if not isinstance(copy_record, dict):
                    errors.append(f"shots[{index}].on_screen_copy[{copy_index}] must be an object")
                    continue
                _exact_fields(copy_record, COPY_FIELDS, f"shots[{index}].on_screen_copy[{copy_index}]", errors)
                status = copy_record.get("copy_status")
                copy_source_ids = copy_record.get("source_reference_ids")
                claim_ids = copy_record.get("claim_ids")
                if not _nonempty(copy_record.get("text")) or not _nonempty(copy_record.get("timing_intent")):
                    errors.append(f"shots[{index}].on_screen_copy[{copy_index}] text/timing required")
                if status not in {"supplied_exact", "provisional_nonclaim", "source_supported_claim"}:
                    errors.append(f"shots[{index}].on_screen_copy[{copy_index}].copy_status invalid")
                if not isinstance(copy_source_ids, list) or not isinstance(claim_ids, list):
                    errors.append(f"shots[{index}].on_screen_copy[{copy_index}] source/claim IDs must be arrays")
                    copy_source_ids, claim_ids = [], []
                copy_claim_ids.update(item for item in claim_ids if isinstance(item, str))
                if status in {"supplied_exact", "source_supported_claim"} and not copy_source_ids:
                    errors.append(f"shots[{index}].on_screen_copy[{copy_index}] source-backed copy requires source IDs")
                if set(copy_source_ids) - source_id_set:
                    errors.append(f"shots[{index}].on_screen_copy[{copy_index}] references unknown sources")
                if status == "source_supported_claim" and not claim_ids:
                    errors.append(f"shots[{index}].on_screen_copy[{copy_index}] claim copy requires claim IDs")
                if status == "provisional_nonclaim" and claim_ids:
                    errors.append(f"shots[{index}].on_screen_copy[{copy_index}] provisional copy cannot carry claims")

    uid_set = set(shot_uids)
    if len(uid_set) != len(shot_uids):
        errors.append("shot_uid values must be unique")
    if len(set(display_numbers)) != len(display_numbers):
        errors.append("display_no values must be unique")
    if display_numbers != list(range(1, len(shots) + 1)):
        errors.append("shots array must follow contiguous display_no order 1..shot_count exactly")
    if abs(duration_sum - float(total)) > float(tolerance) + 1e-12:
        errors.append(f"timeline mismatch: shots sum to {duration_sum:g}, total is {float(total):g}")

    affected = _required_list(record, "affected_shot_uids", errors)
    if len(set(affected)) != len(affected):
        errors.append("affected_shot_uids must be unique")
    unknown_affected = sorted(set(affected) - uid_set)
    if unknown_affected:
        errors.append("affected_shot_uids reference unknown shots: " + ", ".join(unknown_affected))

    continuity = _required_list(record, "continuity_map", errors)
    for index, edge in enumerate(continuity):
        if not isinstance(edge, dict):
            errors.append(f"continuity_map[{index}] must be an object")
            continue
        _exact_fields(edge, CONTINUITY_FIELDS, f"continuity_map[{index}]", errors)
        origin, target = edge.get("from_shot_uid"), edge.get("to_shot_uid")
        if origin not in uid_set or target not in uid_set:
            errors.append(f"continuity_map[{index}] references unknown shot")
        if origin == target:
            errors.append(f"continuity_map[{index}] cannot self-reference")
        if not _nonempty(edge.get("cut_reason")):
            errors.append(f"continuity_map[{index}].cut_reason must be non-empty")
        if edge.get("continuity_type") not in {"physical", "action_match", "screen_direction", "conceptual", "color_rhyme", "shape_rhyme", "texture_rhyme", "motion_rhyme", "intentional_discontinuity"}:
            errors.append(f"continuity_map[{index}].continuity_type invalid")
        if not isinstance(edge.get("preserved_state"), list) or not all(_nonempty(item) for item in edge.get("preserved_state", [])):
            errors.append(f"continuity_map[{index}].preserved_state must be a string array")

    for map_name in ("asset_requirement_map", "keyframe_requirement_map", "previs_requirement_map"):
        entries = _required_list(record, map_name, errors)
        expected_fields = ASSET_MAP_FIELDS if map_name == "asset_requirement_map" else REQUIREMENT_MAP_FIELDS
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                errors.append(f"{map_name}[{index}] must be an object")
                continue
            _exact_fields(entry, expected_fields, f"{map_name}[{index}]", errors)
            if map_name == "asset_requirement_map":
                if not isinstance(entry.get("requirements"), list) or not all(_nonempty(item) for item in entry.get("requirements", [])) or not _nonempty(entry.get("risk_note")):
                    errors.append(f"{map_name}[{index}] requirements/risk_note invalid")
            else:
                allowed = {"required_single_anchor", "required_state_ladder", "recommended", "not_required"} if map_name == "keyframe_requirement_map" else {"required", "recommended", "not_required"}
                if entry.get("requirement") not in allowed or not _nonempty(entry.get("reason")):
                    errors.append(f"{map_name}[{index}] requirement/reason invalid")
        mapped = [entry.get("shot_uid") for entry in entries if isinstance(entry, dict)]
        if len(mapped) != len(set(mapped)):
            errors.append(f"{map_name} must map each shot exactly once")
        if set(mapped) != uid_set:
            errors.append(f"{map_name} coverage must equal the shot UID set")

    inferences = _required_list(record, "inferred_directing_decisions", errors)
    for index, inference in enumerate(inferences):
        if not isinstance(inference, dict):
            errors.append(f"inferred_directing_decisions[{index}] must be an object")
            continue
        _exact_fields(inference, INFERENCE_FIELDS, f"inferred_directing_decisions[{index}]", errors)
        for field in ("field_path", "decision", "rationale", "source_basis"):
            if not _nonempty(inference.get(field)):
                errors.append(f"inferred_directing_decisions[{index}].{field} must be non-empty")
        if inference.get("confidence") not in {"high", "medium", "low"}:
            errors.append(f"inferred_directing_decisions[{index}].confidence invalid")
        if not isinstance(inference.get("reversible"), bool):
            errors.append(f"inferred_directing_decisions[{index}].reversible must be boolean")
    if classification.get("source_type") in {"rough_idea", "partial_shot_list", "structured_creative_shot_draft"} and not inferences:
        errors.append("rough/partial/structured creative input requires a non-empty inference ledger")

    claims = _required_object(record, "claim_boundary", errors)
    _exact_fields(claims, CLAIM_FIELDS, "claim_boundary", errors)
    supplied = claims.get("supplied_claims")
    used_ids = claims.get("used_claim_ids")
    if not isinstance(supplied, list):
        errors.append("claim_boundary.supplied_claims must be an array")
        supplied = []
    supplied_ids: list[str] = []
    for index, claim in enumerate(supplied):
        if not isinstance(claim, dict):
            errors.append(f"claim_boundary.supplied_claims[{index}] must be an object")
            continue
        _exact_fields(claim, SUPPLIED_CLAIM_FIELDS, f"claim_boundary.supplied_claims[{index}]", errors)
        claim_id = claim.get("claim_id")
        if not _nonempty(claim_id):
            errors.append(f"claim_boundary.supplied_claims[{index}].claim_id missing")
        else:
            supplied_ids.append(claim_id)
        if not _nonempty(claim.get("text")):
            errors.append(f"claim_boundary.supplied_claims[{index}].text missing")
        sources = claim.get("source_reference_ids")
        if not isinstance(sources, list) or not sources or not all(_nonempty(item) for item in sources):
            errors.append(f"claim_boundary.supplied_claims[{index}].source_reference_ids required")
        elif set(sources) - source_id_set:
            errors.append(f"claim_boundary.supplied_claims[{index}] references unknown sources")
    if len(set(supplied_ids)) != len(supplied_ids):
        errors.append("claim IDs must be unique")
    if not isinstance(used_ids, list):
        errors.append("claim_boundary.used_claim_ids must be an array")
        used_ids = []
    unsupported = sorted(set(used_ids) - set(supplied_ids))
    if unsupported:
        errors.append("used claims lack supplied evidence: " + ", ".join(unsupported))
    copy_unregistered = sorted(copy_claim_ids - set(used_ids))
    if copy_unregistered:
        errors.append("copy claim IDs are not registered as used claims: " + ", ".join(copy_unregistered))
    prohibited = claims.get("prohibited_unsourced_claims")
    if not isinstance(prohibited, list) or not prohibited or not all(_nonempty(item) for item in prohibited):
        errors.append("claim_boundary.prohibited_unsourced_claims must be non-empty")
    if claims.get("claim_generation_status") not in {"no_new_claims_added", "source_supported_claims_only", "blocked_unresolved_claim"}:
        errors.append("claim_boundary.claim_generation_status invalid")
    if used_ids and claims.get("claim_generation_status") == "no_new_claims_added":
        errors.append("used claims require source_supported_claims_only status")

    blockers = _required_list(record, "isolated_blockers", errors)
    blocker_ids: list[str] = []
    for index, blocker in enumerate(blockers):
        label = f"isolated_blockers[{index}]"
        if not _exact_fields(blocker, BLOCKER_FIELDS, label, errors):
            continue
        if not _nonempty(blocker.get("blocker_id")):
            errors.append(f"{label}.blocker_id required")
        else:
            blocker_ids.append(blocker["blocker_id"])
        if blocker.get("blocker_type") not in HARD_BLOCKER_TYPES:
            errors.append(f"{label}.blocker_type is not a genuine commercial hard fact")
        for field in ("required_fact", "reason"):
            if not _nonempty(blocker.get(field)):
                errors.append(f"{label}.{field} required")
        scope = blocker.get("affected_shot_uids")
        if not isinstance(scope, list) or not set(scope).issubset(uid_set):
            errors.append(f"{label}.affected_shot_uids must be canonical shots")
        if blocker.get("unaffected_work_completed") is not True:
            errors.append(f"{label}.unaffected_work_completed must be true")
    if len(blocker_ids) != len(set(blocker_ids)):
        errors.append("isolated blocker IDs must be unique")
    if approval == "blocked" and not blockers:
        errors.append("blocked approval requires at least one isolated genuine hard-fact blocker")
    if approval != "blocked" and blockers:
        errors.append("isolated blockers require approval_status blocked")
    if claims.get("claim_generation_status") == "blocked_unresolved_claim" and not any(
        isinstance(item, dict) and item.get("blocker_type") in {"exact_legally_material_claim", "unavailable_exact_supplied_copy"}
        for item in blockers
    ):
        errors.append("blocked_unresolved_claim requires a matching isolated claim/copy blocker")

    revision = _required_object(record, "revision_scope", errors)
    _exact_fields(revision, REVISION_FIELDS, "revision_scope", errors)
    mode = revision.get("mode")
    if mode not in {"initial", "selective_revision", "global_revision", "reorder"}:
        errors.append("revision_scope.mode invalid")
    requested = revision.get("requested_shot_uids")
    changed = revision.get("actually_changed_shot_uids")
    expanded = revision.get("expanded_dependency_reasons")
    if not isinstance(requested, list) or not isinstance(changed, list) or not isinstance(expanded, list):
        errors.append("revision_scope shot and expansion fields must be arrays")
        requested, changed, expanded = [], [], []
    unknown_revision = sorted((set(requested) | set(changed)) - uid_set)
    if unknown_revision:
        errors.append("revision_scope references unknown shots: " + ", ".join(unknown_revision))
    if mode == "initial" and set(changed) != uid_set:
        errors.append("initial revision must mark every shot as changed")
    if mode == "selective_revision":
        if not requested:
            errors.append("selective_revision requires requested_shot_uids")
        if revision.get("global_fields_changed") is not False:
            errors.append("selective_revision cannot set global_fields_changed")
        if set(changed) - set(requested) and not expanded:
            errors.append("expanded selective revision requires a dependency reason")
    if not set(changed).issubset(set(affected)):
        errors.append("affected_shot_uids must include every actually changed shot")
    if set(revision.get("invalidated_artifact_ids", [])) & set(revision.get("preserved_artifact_ids", [])):
        errors.append("revision_scope invalidated_artifact_ids and preserved_artifact_ids must be disjoint")

    predecessor_errors, _ = validate_predecessor_evidence(record, previous_record, revision)
    errors.extend(predecessor_errors)
    if mode != "initial" and previous_record is not None:
        actual_changed: set[str] = set()
        for collection in ("shots", "asset_requirement_map", "keyframe_requirement_map", "previs_requirement_map"):
            collection_changed, malformed = keyed_changes(previous_record.get(collection), record.get(collection), "shot_uid")
            if malformed:
                errors.append(f"cannot prove stable-ID revision diff for {collection}")
            actual_changed.update(collection_changed)
        before_edges = previous_record.get("continuity_map")
        after_edges = record.get("continuity_map")
        if before_edges != after_edges:
            for edge in [*(before_edges if isinstance(before_edges, list) else []), *(after_edges if isinstance(after_edges, list) else [])]:
                if isinstance(edge, dict):
                    for field in ("from_shot_uid", "to_shot_uid"):
                        if isinstance(edge.get(field), str):
                            actual_changed.add(edge[field])
        if set(changed) != actual_changed:
            errors.append(
                "revision_scope.actually_changed_shot_uids must exactly equal the real stable-ID diff: "
                + ", ".join(sorted(actual_changed))
            )

        local_roots = {
            "shots", "continuity_map", "asset_requirement_map", "keyframe_requirement_map", "previs_requirement_map",
            "affected_shot_uids",
        }
        before_global = {key: value for key, value in revision_semantic_view(previous_record).items() if key not in local_roots}
        after_global = {key: value for key, value in revision_semantic_view(record).items() if key not in local_roots}
        actual_global_change = before_global != after_global
        if revision.get("global_fields_changed") is not actual_global_change:
            errors.append("revision_scope.global_fields_changed does not match the real predecessor diff")

        previous_uids = {
            shot.get("shot_uid") for shot in previous_record.get("shots", [])
            if isinstance(shot, dict) and isinstance(shot.get("shot_uid"), str)
        }
        if mode in {"selective_revision", "reorder"} and previous_uids != uid_set:
            errors.append(f"{mode} must preserve the complete stable Shot UID set")

    return errors


def validate_contract(record: dict[str, Any], previous_record: dict[str, Any] | None = None) -> list[str]:
    try:
        return _validate_contract(record, previous_record)
    except (TypeError, KeyError, AttributeError, ValueError, OverflowError) as exc:
        return [f"malformed contract rejected safely: {type(exc).__name__}: {exc}"]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("root JSON value must be an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--print-hash", action="store_true", help="print the canonical envelope hash")
    parser.add_argument("--verify-files-root", type=Path, help="resolve and re-hash verified_bytes locators")
    parser.add_argument("--previous-contract", type=Path, help="required immutable predecessor bytes for every non-initial revision")
    args = parser.parse_args()
    try:
        record = load_json(args.contract)
        previous_record = load_json(args.previous_contract) if args.previous_contract is not None else None
        errors = validate_contract(record, previous_record)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    verified_sources = [source for source in record.get("source_inputs", []) if isinstance(source, dict) and source.get("integrity_status") == "verified_bytes"] if isinstance(record.get("source_inputs"), list) else []
    if record.get("approval_status") != "draft" and verified_sources and args.verify_files_root is None:
        errors.append("non-draft verified_bytes sources require --verify-files-root")
    if args.verify_files_root is not None:
        errors.extend(verify_declared_file_hashes(record, args.verify_files_root.resolve()))
    if args.print_hash:
        print(canonical_sha256(record))
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"OK: {args.contract}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
