#!/usr/bin/env python3
"""Canonical v5 schemas and deterministic renderers for post-generation records."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from material_contract import (
    MaterialContractError,
    pretty_json_bytes,
    require_exact_keys,
    sha256_bytes,
)


DECISION_KEYS = {
    "schema_version",
    "attempt_id",
    "comparison_mode",
    "assistant_qa_status",
    "production_approval_status",
    "board_gates",
    "panel_results",
    "invariant_results",
    "observed_defects",
    "repair_required",
    "repair_reasons",
}
QA_KEYS = {
    "schema_version",
    "attempt_id",
    "inspected",
    "inspection_method",
    "comparison_mode",
    "decision_path",
    "decision_sha256",
    "source_images_inspected",
    "board_path",
    "image_sha256",
    "observed_pixel_dimensions",
    "worker_thread_id",
    "image_generation_call_id",
    "assistant_qa_status",
    "production_approval_status",
    "board_gates",
    "panel_results",
    "invariant_results",
    "observed_defects",
    "repair_required",
    "repair_reasons",
}
BOARD_GATE_KEYS = {
    "primary_anchor_clear",
    "multi_angle_complementary",
    "material_evidence_present",
    "material_source_consistent",
    "material_fidelity",
    "critical_structure_fidelity",
    "low_redundancy",
    "panel_legibility",
    "single_board_contract",
    "no_poster_pollution",
    "video_reference_ready",
    "prompt_bound",
    "identity_fidelity",
    "topology_fidelity",
    "structure_fidelity",
    "state_window_source_supported",
}
HANDOFF_KEYS = {
    "schema_version",
    "record_compiler",
    "attempt_id",
    "generation_prompt_path",
    "generation_prompt_sha256",
    "enhancement_prompt_path",
    "enhancement_prompt_sha256",
    "inspection_path",
    "inspection_sha256",
    "codex_asset_board",
    "original_source_references",
    "source_contract_path",
    "source_contract_sha256",
    "source_fidelity_status",
    "external_runtime_request",
    "external_4k_status",
    "external_4k_qa_status",
    "external_4k_production_approval_status",
    "observed_defects",
}
ACCEPTED_KEYS = {
    "schema_version",
    "record_compiler",
    "attempt_id",
    "reference_manifest_path",
    "reference_manifest_sha256",
    "source_contract_path",
    "source_contract_sha256",
    "prompt_block_path",
    "prompt_block_sha256",
    "generation_prompt_path",
    "generation_prompt_sha256",
    "enhancement_prompt_path",
    "4k_enhancement_prompt_sha256",
    "worker_spawn_path",
    "worker_spawn_sha256",
    "worker_exec_source_path",
    "worker_exec_source_sha256",
    "worker_exec_receipt_path",
    "worker_exec_receipt_sha256",
    "worker_result_path",
    "worker_result_sha256",
    "board_path",
    "image_sha256",
    "inspection_decision_path",
    "inspection_decision_sha256",
    "inspection_path",
    "inspection_sha256",
    "handoff_path",
    "handoff_sha256",
}

DEFECT_CATEGORIES = {"identity", "material", "topology", "structure", "label", "state", "artifact"}
DEFECT_SEVERITIES = {"low", "medium", "high", "critical"}
CLEANUP_OPERATIONS = {
    "reduce_raster_aliasing",
    "remove_compression_blocking",
    "remove_background_dust",
    "reduce_edge_halo",
}
EXTERNAL_STATE_MATRIX = {
    "not_ready": {("not_started", "not_requested")},
    "handoff_ready": {("not_started", "not_requested")},
    "blocked_runtime_controls": {("not_started", "not_requested")},
    "pending_external_generation": {("pending", "not_requested")},
    "returned_unverified": {("pending", "not_requested")},
    "verified": {("passed", "pending"), ("passed", "granted")},
    "rejected": {("failed", "rejected")},
}
RECORD_COMPILER = "material_post_generation_records.v1"


def _one_line(value: Any, code: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or any(char in value for char in "\r\n\x00"):
        raise MaterialContractError(code, f"{label} must be one non-empty line")
    return value.strip()


def one_line_list(value: Any, code: str, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise MaterialContractError(code, f"{label} must be a list")
    result = [_one_line(item, code, label) for item in value]
    if len(set(result)) != len(result):
        raise MaterialContractError(code, f"{label} must contain unique values")
    return result


def fact_sources(contract: dict[str, Any]) -> dict[str, list[str]]:
    return {
        fact["fact_id"]: fact["source_aliases"]
        for classification in ("verified", "inferred", "needs_source")
        for fact in contract["fact_registry"][classification]
    }


def validate_observed_defects(
    value: Any,
    *,
    panel_ids: set[str],
    invariant_ids: set[str],
    source_aliases: set[str],
) -> list[dict[str, Any]]:
    code = "blocked_board_inspection_invalid"
    if not isinstance(value, list):
        raise MaterialContractError(code, "observed_defects must be a list")
    normalized: list[dict[str, Any]] = []
    defect_ids: set[str] = set()
    keys = {
        "defect_id", "category", "severity", "description", "panel_ids", "invariant_ids",
        "source_aliases", "cleanup_eligible", "cleanup_operation",
    }
    for defect in value:
        if not isinstance(defect, dict):
            raise MaterialContractError(code, "observed defect must be an object")
        require_exact_keys(defect, keys, code, "observed defect")
        defect_id = defect["defect_id"]
        if not isinstance(defect_id, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", defect_id) or defect_id in defect_ids:
            raise MaterialContractError(code, "defect_id is invalid or duplicated")
        category = defect["category"]
        severity = defect["severity"]
        if category not in DEFECT_CATEGORIES or severity not in DEFECT_SEVERITIES:
            raise MaterialContractError(code, f"invalid defect category/severity: {category}/{severity}")
        _one_line(defect["description"], code, "defect description")
        panels = one_line_list(defect["panel_ids"], code, "defect panel_ids", allow_empty=False)
        invariants = one_line_list(defect["invariant_ids"], code, "defect invariant_ids")
        sources = one_line_list(defect["source_aliases"], code, "defect source_aliases", allow_empty=False)
        if not set(panels) <= panel_ids or not set(invariants) <= invariant_ids or not set(sources) <= source_aliases:
            raise MaterialContractError(code, f"defect {defect_id} references unknown evidence")
        cleanup_eligible = defect["cleanup_eligible"]
        cleanup_operation = defect["cleanup_operation"]
        if type(cleanup_eligible) is not bool or not isinstance(cleanup_operation, str):
            raise MaterialContractError(code, f"defect {defect_id} has invalid cleanup fields")
        if cleanup_eligible:
            if category != "artifact" or severity not in {"low", "medium"} or invariants or cleanup_operation not in CLEANUP_OPERATIONS:
                raise MaterialContractError(
                    "blocked_4k_cleanup_scope_invalid",
                    f"defect {defect_id} is not a non-critical raster-only cleanup",
                )
        elif cleanup_operation != "none":
            raise MaterialContractError(code, f"defect {defect_id} must use cleanup_operation=none")
        defect_ids.add(defect_id)
        normalized.append(defect)
    return normalized


def normalize_decision(
    decision: dict[str, Any],
    *,
    contract: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    code = "blocked_board_inspection_invalid"
    require_exact_keys(decision, DECISION_KEYS, code, "board inspection decision")
    if decision["schema_version"] != "material_board_qa_decision.v1":
        raise MaterialContractError(code, "unexpected board inspection decision schema")
    if decision["attempt_id"] not in {"01", "02", "03"}:
        raise MaterialContractError(code, "invalid attempt_id")
    if decision["comparison_mode"] != "source_to_board_visual_comparison":
        raise MaterialContractError(code, "source-to-board comparison mode is required")

    gates = decision["board_gates"]
    if not isinstance(gates, dict):
        raise MaterialContractError(code, "board_gates must be an object")
    require_exact_keys(gates, BOARD_GATE_KEYS, code, "board gates")
    for key, value in gates.items():
        allowed = {"pass", "fail", "not_used"} if key == "state_window_source_supported" else {"pass", "fail"}
        if value not in allowed:
            raise MaterialContractError(code, f"invalid board gate value: {key}={value}")

    sources_by_fact = fact_sources(contract)
    panels = decision["panel_results"]
    expected_panels = contract["panel_plan"]
    if not isinstance(panels, list) or [item.get("panel_id") for item in panels if isinstance(item, dict)] != [item["panel_id"] for item in expected_panels]:
        raise MaterialContractError(code, "panel results must match panel plan order exactly")
    panel_keys = {
        "panel_id", "source_aliases", "invariant_ids", "status", "source_fidelity",
        "source_observation", "board_observation",
    }
    for expected, actual in zip(expected_panels, panels, strict=True):
        if not isinstance(actual, dict):
            raise MaterialContractError(code, "panel result must be an object")
        require_exact_keys(actual, panel_keys, code, "panel result")
        if actual["source_aliases"] != expected["source_aliases"] or actual["invariant_ids"] != expected["invariant_ids"]:
            raise MaterialContractError(code, f"panel evidence binding mismatch: {expected['panel_id']}")
        if actual["status"] not in {"pass", "fail"} or actual["source_fidelity"] not in {"pass", "fail"}:
            raise MaterialContractError(code, f"panel status invalid: {expected['panel_id']}")
        source_obs = _one_line(actual["source_observation"], code, "panel source observation")
        board_obs = _one_line(actual["board_observation"], code, "panel board observation")
        if source_obs == board_obs:
            raise MaterialContractError(code, "source and board observations must be separately recorded")

    invariants = decision["invariant_results"]
    expected_invariants = contract["critical_invariants"]
    if not isinstance(invariants, list) or [item.get("invariant_id") for item in invariants if isinstance(item, dict)] != [item["invariant_id"] for item in expected_invariants]:
        raise MaterialContractError(code, "invariant results must match contract order exactly")
    invariant_keys = {
        "invariant_id", "category", "source_aliases", "status", "source_fidelity",
        "source_observation", "board_observation",
    }
    for expected, actual in zip(expected_invariants, invariants, strict=True):
        if not isinstance(actual, dict):
            raise MaterialContractError(code, "invariant result must be an object")
        require_exact_keys(actual, invariant_keys, code, "invariant result")
        expected_sources = sources_by_fact[expected["fact_id"]]
        if actual["category"] != expected["category"] or actual["source_aliases"] != expected_sources:
            raise MaterialContractError(code, f"invariant evidence binding mismatch: {expected['invariant_id']}")
        if actual["status"] not in {"pass", "fail"} or actual["source_fidelity"] not in {"pass", "fail"}:
            raise MaterialContractError(code, f"invariant status invalid: {expected['invariant_id']}")
        source_obs = _one_line(actual["source_observation"], code, "invariant source observation")
        board_obs = _one_line(actual["board_observation"], code, "invariant board observation")
        if source_obs == board_obs:
            raise MaterialContractError(code, "source and board observations must be separately recorded")

    defects = validate_observed_defects(
        decision["observed_defects"],
        panel_ids={item["panel_id"] for item in expected_panels},
        invariant_ids={item["invariant_id"] for item in expected_invariants},
        source_aliases=set(manifest["aliases"]),
    )
    reasons = one_line_list(decision["repair_reasons"], code, "repair_reasons")
    if type(decision["repair_required"]) is not bool:
        raise MaterialContractError(code, "repair_required must be boolean")
    qa_status = decision["assistant_qa_status"]
    if qa_status not in {"passed", "conditional", "failed"}:
        raise MaterialContractError(code, "invalid assistant_qa_status")
    approval = decision["production_approval_status"]
    if approval not in {"not_granted", "user_granted", "external_pipeline_granted"}:
        raise MaterialContractError(code, "invalid production_approval_status")

    green = (
        all(value == "pass" for key, value in gates.items() if key != "state_window_source_supported")
        and gates["state_window_source_supported"] in {"pass", "not_used"}
        and all(item["status"] == "pass" and item["source_fidelity"] == "pass" for item in panels)
        and all(item["status"] == "pass" and item["source_fidelity"] == "pass" for item in invariants)
        and all(item["cleanup_eligible"] for item in defects)
    )
    if qa_status == "passed":
        if not green or decision["repair_required"] or reasons:
            raise MaterialContractError(code, "passed QA must be fully green and require no repair")
    elif green or not decision["repair_required"] or not reasons:
        raise MaterialContractError(code, "conditional/failed QA must identify a repair with reasons")
    if approval != "not_granted" and qa_status != "passed":
        raise MaterialContractError(code, "production approval cannot bind a non-passed QA")
    return decision


def build_qa_record(
    *,
    decision: dict[str, Any],
    decision_path: Path,
    decision_sha256: str,
    board_path: Path,
    board_sha256: str,
    width_px: int,
    height_px: int,
    worker_thread_id: str,
    image_generation_call_id: str,
    contract: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    normalized = normalize_decision(decision, contract=contract, manifest=manifest)
    return {
        "schema_version": "material_board_qa.v3",
        "attempt_id": normalized["attempt_id"],
        "inspected": True,
        "inspection_method": "main_agent_source_to_board_visual_inspection",
        "comparison_mode": normalized["comparison_mode"],
        "decision_path": str(decision_path),
        "decision_sha256": decision_sha256,
        "source_images_inspected": [
            {"alias": item["alias"], "path": item["frozen_path"], "sha256": item["sha256"]}
            for item in manifest["entries"]
        ],
        "board_path": str(board_path),
        "image_sha256": board_sha256,
        "observed_pixel_dimensions": {"width_px": width_px, "height_px": height_px},
        "worker_thread_id": worker_thread_id,
        "image_generation_call_id": image_generation_call_id,
        **{key: normalized[key] for key in (
            "assistant_qa_status", "production_approval_status", "board_gates", "panel_results",
            "invariant_results", "observed_defects", "repair_required", "repair_reasons",
        )},
    }


def build_handoff_record(
    *, attempt_id: str, generation_prompt_path: Path, generation_prompt_sha256: str,
    enhancement_prompt_path: Path, enhancement_prompt_sha256: str, inspection_path: Path,
    inspection_sha256: str, board_path: Path, board_sha256: str,
    source_references: list[dict[str, str]], source_contract_path: Path,
    source_contract_sha256: str, observed_defects: list[dict[str, Any]],
    external_status: str, external_qa_status: str, external_production_status: str,
) -> dict[str, Any]:
    if external_status not in EXTERNAL_STATE_MATRIX or (external_qa_status, external_production_status) not in EXTERNAL_STATE_MATRIX[external_status]:
        raise MaterialContractError("blocked_4k_handoff_invalid", "contradictory external 4K state matrix")
    return {
        "schema_version": "material_4k_handoff.v3",
        "record_compiler": RECORD_COMPILER,
        "attempt_id": attempt_id,
        "generation_prompt_path": str(generation_prompt_path),
        "generation_prompt_sha256": generation_prompt_sha256,
        "enhancement_prompt_path": str(enhancement_prompt_path),
        "enhancement_prompt_sha256": enhancement_prompt_sha256,
        "inspection_path": str(inspection_path),
        "inspection_sha256": inspection_sha256,
        "codex_asset_board": {"path": str(board_path), "sha256": board_sha256},
        "original_source_references": source_references,
        "source_contract_path": str(source_contract_path),
        "source_contract_sha256": source_contract_sha256,
        "source_fidelity_status": "passed",
        "external_runtime_request": {"aspect_ratio": "16:9", "image_size": "4K", "alternate_aspect_ratios_allowed": False},
        "external_4k_status": external_status,
        "external_4k_qa_status": external_qa_status,
        "external_4k_production_approval_status": external_production_status,
        "observed_defects": observed_defects,
    }


def build_accepted_record(*, attempt_id: str, paths_and_hashes: dict[str, Any]) -> dict[str, Any]:
    record = {
        "schema_version": "material_accepted_attempt.v3",
        "record_compiler": RECORD_COMPILER,
        "attempt_id": attempt_id,
        **paths_and_hashes,
    }
    require_exact_keys(record, ACCEPTED_KEYS, "blocked_accepted_attempt_invalid", "accepted attempt")
    return record


def render_record_bytes(record: dict[str, Any]) -> bytes:
    return pretty_json_bytes(record)


def record_sha256(record: dict[str, Any]) -> str:
    return sha256_bytes(render_record_bytes(record))
