#!/usr/bin/env python3
"""Build one v4 final result only from a fully reverified material artifact chain."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from material_contract import (
    ATTEMPT_RE,
    MaterialContractError,
    create_only_bytes,
    inspect_image_bytes,
    load_json_file,
    load_reference_manifest,
    load_source_contract,
    normalized_path,
    read_prompt_bytes,
    render_4k_enhancement_prompt_bytes,
    render_worker_exec_bytes,
    require_exact_keys,
    require_exact_path,
    require_inside,
    require_prompt_block_once,
    sha256_bytes,
)
from resolve_worker_image import read_rollout, validate_worker_rollout


ACCEPTED_KEYS = {
    "schema_version",
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
    "inspection_path",
    "inspection_sha256",
    "handoff_path",
    "handoff_sha256",
}
SPAWN_KEYS = {
    "schema_version",
    "attempt_id",
    "agent_path",
    "parent_thread_id",
    "worker_spawn_not_before_ms",
    "worker_run_nonce",
    "generation_prompt_path",
    "generation_prompt_sha256",
    "reference_manifest_path",
    "reference_manifest_sha256",
    "source_contract_path",
    "source_contract_sha256",
    "prompt_block_sha256",
    "worker_exec_source_path",
    "worker_exec_source_sha256",
    "worker_exec_receipt_path",
    "worker_exec_receipt_sha256",
    "pre_spawn_state",
}
EXEC_RECEIPT_KEYS = {
    "schema_version",
    "attempt_id",
    "worker_run_nonce",
    "generation_prompt_path",
    "generation_prompt_sha256",
    "reference_manifest_path",
    "reference_manifest_sha256",
    "ordered_reference_bundle_sha256",
    "ordered_reference_paths",
    "source_contract_path",
    "source_contract_sha256",
    "prompt_block_sha256",
    "exec_source_path",
    "exec_source_sha256",
    "call_contract",
}
RESULT_KEYS = {
    "ok",
    "schema_version",
    "attempt_id",
    "resolved_at_utc",
    "agent_path",
    "worker_thread_id",
    "worker_turn_id",
    "parent_thread_id",
    "worker_rollout_path",
    "image_generation_call_id",
    "worker_saved_path",
    "run_image_path",
    "image_sha256",
    "width_px",
    "height_px",
    "observed_aspect_ratio",
    "exact_16_9",
    "png_validation",
    "generation_prompt_sha256",
    "prompt_sha_match",
    "reference_mode",
    "reference_count",
    "reference_bytes_verified",
    "reference_manifest_path",
    "reference_manifest_sha256",
    "ordered_reference_bundle_sha256",
    "source_contract_path",
    "source_contract_sha256",
    "prompt_block_sha256",
    "worker_spawn_path",
    "worker_spawn_sha256",
    "worker_exec_source_path",
    "worker_exec_source_sha256",
    "worker_exec_receipt_path",
    "worker_exec_receipt_sha256",
    "output_distinct_from_all_sources",
}
QA_KEYS = {
    "schema_version",
    "attempt_id",
    "inspected",
    "inspection_method",
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
    "attempt_id",
    "generation_prompt_path",
    "generation_prompt_sha256",
    "enhancement_prompt_path",
    "enhancement_prompt_sha256",
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
EXTERNAL_STATUSES = {
    "not_ready",
    "handoff_ready",
    "blocked_runtime_controls",
    "pending_external_generation",
    "returned_unverified",
    "verified",
    "rejected",
}
DEFECT_CATEGORIES = {
    "identity",
    "material",
    "topology",
    "structure",
    "label",
    "state",
    "artifact",
}
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


def same_path(value: Any, expected: Path) -> bool:
    return isinstance(value, str) and normalized_path(Path(value)) == normalized_path(expected)


def one_line_list(value: Any, code: str, label: str) -> list[str]:
    if not isinstance(value, list):
        raise MaterialContractError(code, f"{label} must be a list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or any(char in item for char in "\r\n\x00"):
            raise MaterialContractError(code, f"{label} must contain one-line strings")
        result.append(item)
    if len(set(result)) != len(result):
        raise MaterialContractError(code, f"{label} must contain unique values")
    return result


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
    for defect in value:
        if not isinstance(defect, dict):
            raise MaterialContractError(code, "observed defect must be an object")
        require_exact_keys(
            defect,
            {
                "defect_id",
                "category",
                "severity",
                "description",
                "panel_ids",
                "invariant_ids",
                "source_aliases",
                "cleanup_eligible",
                "cleanup_operation",
            },
            code,
            "observed defect",
        )
        defect_id = defect["defect_id"]
        category = defect["category"]
        severity = defect["severity"]
        description = defect["description"]
        panels = defect["panel_ids"]
        invariants = defect["invariant_ids"]
        sources = defect["source_aliases"]
        cleanup_eligible = defect["cleanup_eligible"]
        cleanup_operation = defect["cleanup_operation"]
        if (
            not isinstance(defect_id, str)
            or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", defect_id)
            or defect_id in defect_ids
        ):
            raise MaterialContractError(code, "defect_id is invalid or duplicated")
        if category not in DEFECT_CATEGORIES or severity not in DEFECT_SEVERITIES:
            raise MaterialContractError(code, f"invalid defect category/severity: {category}/{severity}")
        if (
            not isinstance(description, str)
            or not description.strip()
            or any(char in description for char in "\r\n\x00")
        ):
            raise MaterialContractError(code, "defect description must be one non-empty line")
        if (
            not isinstance(panels, list)
            or not panels
            or not all(isinstance(item, str) for item in panels)
            or len(set(panels)) != len(panels)
            or not set(panels) <= panel_ids
        ):
            raise MaterialContractError(code, f"defect {defect_id} has invalid panel_ids")
        if (
            not isinstance(invariants, list)
            or not all(isinstance(item, str) for item in invariants)
            or len(set(invariants)) != len(invariants)
            or not set(invariants) <= invariant_ids
        ):
            raise MaterialContractError(code, f"defect {defect_id} has invalid invariant_ids")
        if (
            not isinstance(sources, list)
            or not sources
            or not all(isinstance(item, str) for item in sources)
            or len(set(sources)) != len(sources)
            or not set(sources) <= source_aliases
        ):
            raise MaterialContractError(code, f"defect {defect_id} has invalid source_aliases")
        if type(cleanup_eligible) is not bool:
            raise MaterialContractError(code, f"defect {defect_id} cleanup_eligible must be boolean")
        if not isinstance(cleanup_operation, str):
            raise MaterialContractError(
                code,
                f"defect {defect_id} cleanup_operation must be a string",
            )
        if cleanup_eligible:
            if (
                category != "artifact"
                or severity not in {"low", "medium"}
                or invariants
                or cleanup_operation not in CLEANUP_OPERATIONS
            ):
                raise MaterialContractError(
                    "blocked_4k_cleanup_scope_invalid",
                    f"defect {defect_id} is not a non-critical raster-only cleanup",
                )
        elif cleanup_operation != "none":
            raise MaterialContractError(
                code,
                f"defect {defect_id} must use cleanup_operation=none when cleanup is ineligible",
            )
        defect_ids.add(defect_id)
        normalized.append(defect)
    return normalized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--accepted-attempt", required=True, type=Path)
    parser.add_argument("--board", required=True, type=Path)
    parser.add_argument("--generation-prompt", required=True, type=Path)
    parser.add_argument("--enhancement-prompt", required=True, type=Path)
    parser.add_argument("--worker-spawn", required=True, type=Path)
    parser.add_argument("--worker-result", required=True, type=Path)
    parser.add_argument("--inspection", required=True, type=Path)
    parser.add_argument("--reference-manifest", required=True, type=Path)
    parser.add_argument("--source-contract", required=True, type=Path)
    parser.add_argument("--handoff", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-output-bytes", type=int)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_dir = args.run_dir.expanduser().resolve(strict=False)
    if not run_dir.is_dir():
        raise MaterialContractError(
            "blocked_publication_run_missing", f"run directory missing: {run_dir}"
        )
    accepted_path = require_exact_path(
        args.accepted_attempt,
        run_dir / "accepted_attempt.json",
        "blocked_accepted_attempt_invalid",
        "accepted attempt",
    )
    accepted_candidates = [path for path in run_dir.glob("accepted_attempt*.json") if path.is_file()]
    if [normalized_path(path) for path in accepted_candidates] != [normalized_path(accepted_path)]:
        raise MaterialContractError(
            "blocked_accepted_attempt_invalid", "run must contain exactly one accepted_attempt.json"
        )
    output = require_inside(
        run_dir, args.output, "blocked_publication_artifact_location", "final output"
    )
    if output.parent != run_dir:
        raise MaterialContractError(
            "blocked_publication_artifact_location", "final output must be directly inside the run"
        )
    if output.exists():
        raise MaterialContractError(
            "blocked_publication_output_conflict", "final main result is create-only"
        )

    accepted, _ = load_json_file(
        accepted_path, "blocked_accepted_attempt_invalid", "accepted attempt"
    )
    if accepted.get("schema_version") == "material_accepted_attempt.v1":
        raise MaterialContractError(
            "blocked_legacy_material_run_v1", "material_accepted_attempt.v1 cannot resume as v4"
        )
    require_exact_keys(accepted, ACCEPTED_KEYS, "blocked_accepted_attempt_invalid", "accepted attempt")
    attempt_id = accepted["attempt_id"]
    if accepted["schema_version"] != "material_accepted_attempt.v2" or not isinstance(
        attempt_id, str
    ) or not ATTEMPT_RE.fullmatch(attempt_id):
        raise MaterialContractError("blocked_accepted_attempt_invalid", "invalid v2 accepted attempt")
    attempt_dir = run_dir / "attempts" / attempt_id
    if not attempt_dir.is_dir():
        raise MaterialContractError("blocked_accepted_attempt_invalid", "accepted attempt directory missing")

    board = require_exact_path(args.board, attempt_dir / "board.png", "blocked_accepted_attempt_mismatch", "board")
    generation_path = require_inside(
        attempt_dir, args.generation_prompt, "blocked_accepted_attempt_mismatch", "generation prompt"
    )
    enhancement_path = require_inside(
        attempt_dir, args.enhancement_prompt, "blocked_accepted_attempt_mismatch", "enhancement prompt"
    )
    spawn_path = require_exact_path(
        args.worker_spawn,
        attempt_dir / "worker_spawn.json",
        "blocked_accepted_attempt_mismatch",
        "worker spawn",
    )
    worker_path = require_exact_path(
        args.worker_result,
        attempt_dir / "worker_result.json",
        "blocked_accepted_attempt_mismatch",
        "worker result",
    )
    inspection_path = require_exact_path(
        args.inspection,
        attempt_dir / "qa.json",
        "blocked_accepted_attempt_mismatch",
        "inspection",
    )
    handoff_path = require_inside(
        attempt_dir, args.handoff, "blocked_accepted_attempt_mismatch", "4K handoff"
    )
    if any(path.parent != attempt_dir for path in (generation_path, enhancement_path, handoff_path)):
        raise MaterialContractError(
            "blocked_accepted_attempt_mismatch", "attempt artifacts must be direct children of accepted attempt"
        )
    manifest_path = require_exact_path(
        args.reference_manifest,
        run_dir / "sources" / "reference-manifest.json",
        "blocked_accepted_attempt_mismatch",
        "reference manifest",
    )
    contract_path = require_exact_path(
        args.source_contract,
        run_dir / "sources" / "material-source-contract.json",
        "blocked_accepted_attempt_mismatch",
        "source contract",
    )

    manifest_record = load_reference_manifest(manifest_path, run_dir)
    contract_record = load_source_contract(contract_path, run_dir, manifest_record)
    prompt_block_path = contract_record["prompt_block_path"]
    generation_bytes = read_prompt_bytes(
        generation_path, "blocked_prompt_pair_integrity", "generation prompt"
    )
    enhancement_bytes = read_prompt_bytes(
        enhancement_path, "blocked_prompt_pair_integrity", "4K enhancement prompt"
    )
    require_prompt_block_once(
        generation_bytes, contract_record["prompt_block_bytes"], "blocked_prompt_pair_integrity"
    )
    generation_sha = sha256_bytes(generation_bytes)
    enhancement_sha = sha256_bytes(enhancement_bytes)
    if not board.is_file():
        raise MaterialContractError("blocked_publication_board_missing", f"board missing: {board}")
    board_bytes = board.read_bytes()
    board_metadata = inspect_image_bytes(
        board_bytes,
        code="blocked_publication_board_invalid",
        label="accepted board",
        required_format="PNG",
    )
    board_sha = sha256_bytes(board_bytes)
    if board_sha in set(manifest_record["hashes"]):
        raise MaterialContractError(
            "blocked_publication_provenance_mismatch", "accepted board equals a frozen source image"
        )

    accepted_path_fields = {
        "reference_manifest_path": manifest_path,
        "source_contract_path": contract_path,
        "prompt_block_path": prompt_block_path,
        "generation_prompt_path": generation_path,
        "enhancement_prompt_path": enhancement_path,
        "worker_spawn_path": spawn_path,
        "worker_result_path": worker_path,
        "board_path": board,
        "inspection_path": inspection_path,
        "handoff_path": handoff_path,
    }
    if any(not same_path(accepted[field], path) for field, path in accepted_path_fields.items()):
        raise MaterialContractError(
            "blocked_accepted_attempt_mismatch", "accepted attempt path locks mismatch"
        )

    spawn, spawn_bytes = load_json_file(
        spawn_path, "blocked_worker_spawn_invalid", "worker spawn"
    )
    worker, worker_bytes = load_json_file(
        worker_path, "blocked_worker_result_invalid", "worker result"
    )
    inspection, inspection_bytes = load_json_file(
        inspection_path, "blocked_board_inspection_invalid", "board inspection"
    )
    handoff, handoff_bytes = load_json_file(
        handoff_path, "blocked_4k_handoff_invalid", "4K handoff"
    )
    hash_locks = {
        "reference_manifest_sha256": manifest_record["sha256"],
        "source_contract_sha256": contract_record["sha256"],
        "prompt_block_sha256": contract_record["prompt_block_sha256"],
        "generation_prompt_sha256": generation_sha,
        "4k_enhancement_prompt_sha256": enhancement_sha,
        "worker_spawn_sha256": sha256_bytes(spawn_bytes),
        "worker_result_sha256": sha256_bytes(worker_bytes),
        "image_sha256": board_sha,
        "inspection_sha256": sha256_bytes(inspection_bytes),
        "handoff_sha256": sha256_bytes(handoff_bytes),
    }
    if any(accepted[field] != value for field, value in hash_locks.items()):
        raise MaterialContractError(
            "blocked_accepted_attempt_mismatch", "accepted attempt hash locks mismatch"
        )

    require_exact_keys(spawn, SPAWN_KEYS, "blocked_worker_spawn_invalid", "worker spawn")
    if spawn["schema_version"] != "material_worker_spawn.v2" or spawn["attempt_id"] != attempt_id:
        raise MaterialContractError("blocked_worker_spawn_invalid", "worker spawn schema/attempt mismatch")
    exec_path = require_exact_path(
        Path(spawn["worker_exec_source_path"]),
        attempt_dir / "worker_exec.js",
        "blocked_worker_spawn_invalid",
        "worker exec source",
    )
    receipt_path = require_exact_path(
        Path(spawn["worker_exec_receipt_path"]),
        attempt_dir / "worker_exec.json",
        "blocked_worker_spawn_invalid",
        "worker exec receipt",
    )
    if not exec_path.is_file():
        raise MaterialContractError("blocked_worker_spawn_invalid", "worker exec source missing")
    exec_bytes = exec_path.read_bytes()
    expected_exec = render_worker_exec_bytes(
        spawn["worker_run_nonce"], generation_bytes.decode("utf-8"), manifest_record["paths"]
    )
    if exec_bytes != expected_exec:
        raise MaterialContractError(
            "blocked_worker_exec_source_mismatch", "worker exec bytes are not the deterministic render"
        )
    receipt, receipt_bytes = load_json_file(
        receipt_path, "blocked_worker_exec_receipt_invalid", "worker exec receipt"
    )
    require_exact_keys(receipt, EXEC_RECEIPT_KEYS, "blocked_worker_exec_receipt_invalid", "worker exec receipt")
    expected_receipt = {
        "schema_version": "material_render_worker_exec.v1",
        "attempt_id": attempt_id,
        "worker_run_nonce": spawn["worker_run_nonce"],
        "generation_prompt_path": str(generation_path),
        "generation_prompt_sha256": generation_sha,
        "reference_manifest_path": str(manifest_path),
        "reference_manifest_sha256": manifest_record["sha256"],
        "ordered_reference_bundle_sha256": manifest_record["ordered_bundle_sha256"],
        "ordered_reference_paths": [str(path) for path in manifest_record["paths"]],
        "source_contract_path": str(contract_path),
        "source_contract_sha256": contract_record["sha256"],
        "prompt_block_sha256": contract_record["prompt_block_sha256"],
        "exec_source_path": str(exec_path),
        "exec_source_sha256": sha256_bytes(exec_bytes),
        "call_contract": "exactly_one_imagegen;no_decision;empty_worker_final",
    }
    if receipt != expected_receipt:
        raise MaterialContractError(
            "blocked_worker_exec_receipt_invalid", "worker exec receipt mismatch"
        )
    accepted_exec_locks = {
        "worker_exec_source_path": exec_path,
        "worker_exec_receipt_path": receipt_path,
    }
    if any(not same_path(accepted[field], path) for field, path in accepted_exec_locks.items()):
        raise MaterialContractError(
            "blocked_accepted_attempt_mismatch",
            "accepted attempt does not directly bind worker exec source/receipt paths",
        )
    if (
        accepted["worker_exec_source_sha256"] != sha256_bytes(exec_bytes)
        or accepted["worker_exec_receipt_sha256"] != sha256_bytes(receipt_bytes)
    ):
        raise MaterialContractError(
            "blocked_accepted_attempt_mismatch",
            "accepted attempt does not directly bind worker exec source/receipt hashes",
        )
    expected_spawn_values = {
        "generation_prompt_path": str(generation_path),
        "generation_prompt_sha256": generation_sha,
        "reference_manifest_path": str(manifest_path),
        "reference_manifest_sha256": manifest_record["sha256"],
        "source_contract_path": str(contract_path),
        "source_contract_sha256": contract_record["sha256"],
        "prompt_block_sha256": contract_record["prompt_block_sha256"],
        "worker_exec_source_sha256": sha256_bytes(exec_bytes),
        "worker_exec_receipt_sha256": sha256_bytes(receipt_bytes),
        "pre_spawn_state": "one_non_decision_worker_spawned_unresolved",
    }
    if any(spawn[field] != value for field, value in expected_spawn_values.items()):
        raise MaterialContractError("blocked_worker_spawn_invalid", "worker spawn artifact locks mismatch")

    require_exact_keys(worker, RESULT_KEYS, "blocked_worker_result_invalid", "worker result")
    expected_worker_values = {
        "ok": True,
        "schema_version": "delegated_product_image_worker_result.v2",
        "attempt_id": attempt_id,
        "run_image_path": str(board),
        "image_sha256": board_sha,
        "width_px": board_metadata["width_px"],
        "height_px": board_metadata["height_px"],
        "png_validation": "pillow_verify_and_full_load",
        "generation_prompt_sha256": generation_sha,
        "prompt_sha_match": True,
        "reference_mode": "frozen_manifest_v2",
        "reference_count": len(manifest_record["paths"]),
        "reference_bytes_verified": True,
        "reference_manifest_path": str(manifest_path),
        "reference_manifest_sha256": manifest_record["sha256"],
        "ordered_reference_bundle_sha256": manifest_record["ordered_bundle_sha256"],
        "source_contract_path": str(contract_path),
        "source_contract_sha256": contract_record["sha256"],
        "prompt_block_sha256": contract_record["prompt_block_sha256"],
        "worker_spawn_path": str(spawn_path),
        "worker_spawn_sha256": sha256_bytes(spawn_bytes),
        "worker_exec_source_path": str(exec_path),
        "worker_exec_source_sha256": sha256_bytes(exec_bytes),
        "worker_exec_receipt_path": str(receipt_path),
        "worker_exec_receipt_sha256": sha256_bytes(receipt_bytes),
        "output_distinct_from_all_sources": True,
    }
    if any(worker[field] != value for field, value in expected_worker_values.items()):
        raise MaterialContractError(
            "blocked_publication_provenance_mismatch", "worker result does not bind the full v4 chain"
        )
    if worker["agent_path"] != spawn["agent_path"] or worker["parent_thread_id"] != spawn["parent_thread_id"]:
        raise MaterialContractError(
            "blocked_publication_provenance_mismatch", "worker identity differs from frozen spawn"
        )
    try:
        resolved_at = datetime.fromisoformat(worker["resolved_at_utc"])
    except (TypeError, ValueError) as exc:
        raise MaterialContractError(
            "blocked_worker_result_invalid", "worker resolved_at_utc is invalid"
        ) from exc
    if resolved_at.tzinfo is None:
        raise MaterialContractError(
            "blocked_worker_result_invalid", "worker resolved_at_utc must be timezone-aware"
        )
    expected_ratio = board_metadata["width_px"] / board_metadata["height_px"]
    if (
        type(worker["observed_aspect_ratio"]) not in {int, float}
        or abs(float(worker["observed_aspect_ratio"]) - expected_ratio) > 1e-12
        or worker["exact_16_9"]
        is not (board_metadata["width_px"] * 9 == board_metadata["height_px"] * 16)
    ):
        raise MaterialContractError(
            "blocked_worker_result_invalid", "worker aspect-ratio evidence is falsified"
        )
    rollout_raw = worker["worker_rollout_path"]
    if not isinstance(rollout_raw, str) or not Path(rollout_raw).is_absolute():
        raise MaterialContractError(
            "blocked_worker_result_invalid", "worker rollout path must be absolute"
        )
    rollout_path = Path(rollout_raw)
    if rollout_path.is_symlink() or not rollout_path.is_file():
        raise MaterialContractError(
            "blocked_worker_result_invalid", "bound worker rollout is missing or symlinked"
        )
    rollout_evidence = validate_worker_rollout(
        read_rollout(rollout_path),
        thread_id=worker["worker_thread_id"],
        agent_path=spawn["agent_path"],
        parent_thread_id=spawn["parent_thread_id"],
        expected_exec_bytes=exec_bytes,
    )
    saved_raw = worker["worker_saved_path"]
    if not isinstance(saved_raw, str) or not Path(saved_raw).is_absolute():
        raise MaterialContractError(
            "blocked_worker_result_invalid", "worker saved image path must be absolute"
        )
    saved_path = Path(saved_raw)
    if saved_path.is_symlink() or not saved_path.is_file():
        raise MaterialContractError(
            "blocked_worker_result_invalid", "worker saved image is missing or symlinked"
        )
    if (
        saved_path.name != f"{worker['image_generation_call_id']}.png"
        or saved_path.parent.name != worker["worker_thread_id"]
        or saved_path.parent.parent.name != "generated_images"
    ):
        raise MaterialContractError(
            "blocked_publication_provenance_mismatch",
            "worker saved image path is not derived from thread plus image call",
        )
    saved_bytes = saved_path.read_bytes()
    saved_metadata = inspect_image_bytes(
        saved_bytes,
        code="blocked_worker_result_invalid",
        label="worker saved image",
        required_format="PNG",
    )
    if (
        saved_bytes != board_bytes
        or saved_metadata["width_px"] != board_metadata["width_px"]
        or saved_metadata["height_px"] != board_metadata["height_px"]
        or rollout_evidence["worker_turn_id"] != worker["worker_turn_id"]
        or rollout_evidence["image_generation_call_id"] != worker["image_generation_call_id"]
        or normalized_path(Path(rollout_evidence["saved_path"])) != normalized_path(saved_path)
        or rollout_evidence["exec_source_sha256"] != worker["worker_exec_source_sha256"]
    ):
        raise MaterialContractError(
            "blocked_publication_provenance_mismatch",
            "worker result no longer matches its live rollout or saved PNG",
        )

    require_exact_keys(inspection, QA_KEYS, "blocked_board_inspection_invalid", "board inspection")
    if (
        inspection["schema_version"] != "material_board_qa.v2"
        or inspection["attempt_id"] != attempt_id
        or inspection["inspected"] is not True
        or inspection["inspection_method"] != "main_agent_visual_inspection"
        or not same_path(inspection["board_path"], board)
        or inspection["image_sha256"] != board_sha
        or inspection["worker_thread_id"] != worker["worker_thread_id"]
        or inspection["image_generation_call_id"] != worker["image_generation_call_id"]
    ):
        raise MaterialContractError(
            "blocked_board_inspection_invalid", "board inspection identity/binding mismatch"
        )
    dimensions = inspection["observed_pixel_dimensions"]
    if dimensions != {
        "width_px": board_metadata["width_px"],
        "height_px": board_metadata["height_px"],
    }:
        raise MaterialContractError(
            "blocked_board_inspection_invalid", "observed dimensions do not match decoded PNG"
        )
    board_gates = inspection["board_gates"]
    if not isinstance(board_gates, dict):
        raise MaterialContractError("blocked_board_inspection_invalid", "board_gates must be an object")
    require_exact_keys(board_gates, BOARD_GATE_KEYS, "blocked_board_inspection_invalid", "board gates")
    if any(board_gates[field] != "pass" for field in ("identity_fidelity", "topology_fidelity", "structure_fidelity")):
        raise MaterialContractError(
            "blocked_repair_required_identity_topology_structure",
            "identity, topology, or structure drift requires a new generation attempt",
        )

    invariant_results = inspection["invariant_results"]
    if not isinstance(invariant_results, list):
        raise MaterialContractError("blocked_board_inspection_invalid", "invariant_results must be a list")
    contract_invariants = contract_record["value"]["critical_invariants"]
    if [item.get("invariant_id") for item in invariant_results if isinstance(item, dict)] != [
        item["invariant_id"] for item in contract_invariants
    ]:
        raise MaterialContractError(
            "blocked_board_inspection_invalid", "invariant results must match contract order exactly"
        )
    for expected, actual in zip(contract_invariants, invariant_results, strict=True):
        if expected["evidence_classification"] != "verified":
            if expected["category"] in {"identity", "topology", "structure"}:
                raise MaterialContractError(
                    "blocked_repair_required_identity_topology_structure",
                    f"critical {expected['category']} invariant is not source-verified",
                )
            raise MaterialContractError(
                "blocked_unverified_critical_invariant",
                f"critical invariant is not source-verified: {expected['invariant_id']}",
            )
        if not isinstance(actual, dict):
            raise MaterialContractError("blocked_board_inspection_invalid", "invariant result must be object")
        require_exact_keys(
            actual,
            {"invariant_id", "category", "status", "source_fidelity", "observed_content"},
            "blocked_board_inspection_invalid",
            "invariant result",
        )
        if (
            actual["category"] != expected["category"]
            or actual["status"] != "pass"
            or actual["source_fidelity"] != "pass"
            or not isinstance(actual["observed_content"], str)
            or not actual["observed_content"].strip()
        ):
            if expected["category"] in {"identity", "topology", "structure"}:
                raise MaterialContractError(
                    "blocked_repair_required_identity_topology_structure",
                    f"critical {expected['category']} invariant failed and cannot be delegated to 4K",
                )
            raise MaterialContractError(
                "blocked_board_inspection_invalid", f"invariant failed: {expected['invariant_id']}"
            )

    panel_results = inspection["panel_results"]
    contract_panels = contract_record["value"]["panel_plan"]
    if not isinstance(panel_results, list) or [
        item.get("panel_id") for item in panel_results if isinstance(item, dict)
    ] != [item["panel_id"] for item in contract_panels]:
        raise MaterialContractError(
            "blocked_board_inspection_invalid", "panel results must match panel plan order exactly"
        )
    for expected, actual in zip(contract_panels, panel_results, strict=True):
        if not isinstance(actual, dict):
            raise MaterialContractError("blocked_board_inspection_invalid", "panel result must be object")
        require_exact_keys(
            actual,
            {"panel_id", "status", "source_fidelity", "observed_content", "invariant_ids"},
            "blocked_board_inspection_invalid",
            "panel result",
        )
        if (
            actual["status"] != "pass"
            or actual["source_fidelity"] != "pass"
            or actual["invariant_ids"] != expected["invariant_ids"]
            or not isinstance(actual["observed_content"], str)
            or not actual["observed_content"].strip()
        ):
            raise MaterialContractError(
                "blocked_board_inspection_invalid", f"panel failed: {expected['panel_id']}"
            )
    non_state_gate_fields = BOARD_GATE_KEYS - {"state_window_source_supported"}
    if any(board_gates[field] != "pass" for field in non_state_gate_fields) or board_gates[
        "state_window_source_supported"
    ] not in {"pass", "not_used"}:
        raise MaterialContractError("blocked_board_inspection_invalid", "not every board gate passed")
    observed_defects = validate_observed_defects(
        inspection["observed_defects"],
        panel_ids={item["panel_id"] for item in contract_panels},
        invariant_ids={item["invariant_id"] for item in contract_invariants},
        source_aliases=set(manifest_record["aliases"]),
    )
    unrepairable_defects = [item for item in observed_defects if not item["cleanup_eligible"]]
    identity_structure_defects = [
        item
        for item in unrepairable_defects
        if item["category"] in {"identity", "topology", "structure"}
    ]
    if identity_structure_defects:
        raise MaterialContractError(
            "blocked_repair_required_identity_topology_structure",
            "identity/topology/structure defects require regeneration, never 4K cleanup",
        )
    if unrepairable_defects:
        raise MaterialContractError(
            "blocked_repair_required_source_fidelity",
            "accepted QA contains a label/state/critical defect that is not 4K-cleanup eligible",
        )
    cleanup_defects = [item for item in observed_defects if item["cleanup_eligible"]]
    expected_source_refs = [
        {"alias": entry["alias"], "path": entry["frozen_path"], "sha256": entry["sha256"]}
        for entry in manifest_record["entries"]
    ]
    expected_enhancement_bytes = render_4k_enhancement_prompt_bytes(
        board_path=board,
        board_sha256=board_sha,
        source_references=expected_source_refs,
        source_contract_path=contract_path,
        source_contract_sha256=contract_record["sha256"],
        cleanup_defects=cleanup_defects,
    )
    if enhancement_bytes != expected_enhancement_bytes:
        raise MaterialContractError(
            "blocked_4k_prompt_contract_invalid",
            "4K enhancement prompt is not the deterministic QA-scoped cleanup prompt",
        )
    repair_reasons = one_line_list(
        inspection["repair_reasons"], "blocked_board_inspection_invalid", "repair_reasons"
    )
    if (
        inspection["assistant_qa_status"] != "passed"
        or inspection["repair_required"] is not False
        or repair_reasons
    ):
        raise MaterialContractError(
            "blocked_board_inspection_invalid", "accepted attempt still requires repair or lacks passed QA"
        )
    production_approval = inspection["production_approval_status"]
    if production_approval not in {"not_granted", "user_granted", "external_pipeline_granted"}:
        raise MaterialContractError("blocked_board_inspection_invalid", "invalid production approval status")

    require_exact_keys(handoff, HANDOFF_KEYS, "blocked_4k_handoff_invalid", "4K handoff")
    if handoff["schema_version"] != "material_4k_handoff.v2" or handoff["attempt_id"] != attempt_id:
        raise MaterialContractError("blocked_4k_handoff_invalid", "handoff schema/attempt mismatch")
    board_ref = handoff["codex_asset_board"]
    if not isinstance(board_ref, dict):
        raise MaterialContractError("blocked_4k_handoff_invalid", "codex_asset_board must be object")
    require_exact_keys(board_ref, {"path", "sha256"}, "blocked_4k_handoff_invalid", "codex board")
    source_refs = handoff["original_source_references"]
    runtime_request = handoff["external_runtime_request"]
    if not isinstance(runtime_request, dict):
        raise MaterialContractError("blocked_4k_handoff_invalid", "external_runtime_request must be object")
    require_exact_keys(
        runtime_request,
        {"aspect_ratio", "image_size", "alternate_aspect_ratios_allowed"},
        "blocked_4k_handoff_invalid",
        "external runtime request",
    )
    external_status = handoff["external_4k_status"]
    external_qa_status = handoff["external_4k_qa_status"]
    external_production_status = handoff["external_4k_production_approval_status"]
    if (
        not same_path(handoff["generation_prompt_path"], generation_path)
        or handoff["generation_prompt_sha256"] != generation_sha
        or not same_path(handoff["enhancement_prompt_path"], enhancement_path)
        or handoff["enhancement_prompt_sha256"] != enhancement_sha
        or not same_path(board_ref["path"], board)
        or board_ref["sha256"] != board_sha
        or source_refs != expected_source_refs
        or not same_path(handoff["source_contract_path"], contract_path)
        or handoff["source_contract_sha256"] != contract_record["sha256"]
        or handoff["source_fidelity_status"] != "passed"
        or runtime_request
        != {"aspect_ratio": "16:9", "image_size": "4K", "alternate_aspect_ratios_allowed": False}
        or external_status not in EXTERNAL_STATUSES
        or external_qa_status not in {"not_started", "pending", "passed", "failed"}
        or external_production_status
        not in {"not_requested", "pending", "granted", "rejected"}
        or handoff["observed_defects"] != cleanup_defects
    ):
        raise MaterialContractError("blocked_4k_handoff_invalid", "handoff is incomplete or stale")
    if (external_qa_status, external_production_status) not in EXTERNAL_STATE_MATRIX[external_status]:
        raise MaterialContractError(
            "blocked_4k_handoff_invalid",
            "external 4K status, QA state, and production-approval state are contradictory",
        )

    expected_output = run_dir / f"{contract_record['value']['asset_id']}_final_main_result.md"
    require_exact_path(output, expected_output, "blocked_publication_artifact_location", "final output")
    generation_text = generation_bytes.decode("utf-8")
    enhancement_text = enhancement_bytes.decode("utf-8")
    payload = (
        f"![Material-Sensitive Product Master Asset Board](<{board.as_posix()}>)\n\n"
        f"final_generation_prompt:\n{generation_text}\n\n"
        f"generation_prompt_sha256: {generation_sha}\n\n"
        f"final_4k_enhancement_prompt:\n{enhancement_text}\n\n"
        f"4k_enhancement_prompt_sha256: {enhancement_sha}\n\n"
        "assistant_qa_status: passed\n"
        f"observed_pixel_dimensions: {board_metadata['width_px']}x{board_metadata['height_px']}\n"
        f"worker_thread_id: {worker['worker_thread_id']}\n"
        f"image_generation_call_id: {worker['image_generation_call_id']}\n"
        f"external_4k_status: {external_status}\n"
        f"external_4k_qa_status: {external_qa_status}\n"
        f"external_4k_production_approval_status: {external_production_status}\n"
        f"production_approval_status: {production_approval}\n\n"
        "main_result_prompt_pair_status: published\n"
        "task_finalization_status: final_main_result_published"
    )
    payload_bytes = payload.encode("utf-8")
    if args.max_output_bytes is not None and len(payload_bytes) > args.max_output_bytes:
        raise MaterialContractError(
            "blocked_final_output_capacity",
            f"final payload is {len(payload_bytes)} bytes, above {args.max_output_bytes}",
        )
    create_only_bytes(
        output,
        payload_bytes,
        code="blocked_publication_output_conflict",
        idempotent=False,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "schema_version": "material_sensitive_final_main_result.v2",
                "attempt_id": attempt_id,
                "output_path": str(output),
                "output_sha256": sha256_bytes(payload_bytes),
                "generation_prompt_sha256": generation_sha,
                "4k_enhancement_prompt_sha256": enhancement_sha,
                "image_sha256": board_sha,
                "external_4k_status": external_status,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MaterialContractError as exc:
        print(
            json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}),
            file=sys.stderr,
        )
        raise SystemExit(2)
    except OSError as exc:
        print(
            json.dumps(
                {"ok": False, "error_code": "blocked_publication_filesystem", "detail": str(exc)}
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)
