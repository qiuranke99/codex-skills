#!/usr/bin/env python3
"""Atomically preflight and freeze the 4K prompt, handoff, and accepted-attempt commit."""

from __future__ import annotations

import argparse
import json
import sys
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
    require_exact_path,
    require_prompt_block_once,
    sha256_bytes,
)
from material_decision_records import (
    build_accepted_record,
    build_handoff_record,
    build_qa_record,
    normalize_decision,
    render_record_bytes,
)
from resolve_worker_image import read_rollout, validate_worker_rollout


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--attempt-dir", required=True, type=Path)
    parser.add_argument("--board", required=True, type=Path)
    parser.add_argument("--generation-prompt", required=True, type=Path)
    parser.add_argument("--worker-spawn", required=True, type=Path)
    parser.add_argument("--worker-result", required=True, type=Path)
    parser.add_argument("--inspection-decision", required=True, type=Path)
    parser.add_argument("--inspection", required=True, type=Path)
    parser.add_argument("--reference-manifest", required=True, type=Path)
    parser.add_argument("--source-contract", required=True, type=Path)
    parser.add_argument("--enhancement-prompt", required=True, type=Path)
    parser.add_argument("--handoff", required=True, type=Path)
    parser.add_argument("--accepted-attempt", required=True, type=Path)
    parser.add_argument("--external-4k-status", required=True)
    parser.add_argument("--external-4k-qa-status", required=True)
    parser.add_argument("--external-4k-production-approval-status", required=True)
    return parser


def _preflight(path: Path, data: bytes, code: str) -> None:
    if path.exists() and path.read_bytes() != data:
        raise MaterialContractError(code, f"create-only destination has different bytes: {path}")


def _hash(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def main() -> int:
    args = build_parser().parse_args()
    run_dir = args.run_dir.expanduser().resolve(strict=False)
    attempt_dir = require_exact_path(args.attempt_dir, run_dir / "attempts" / args.attempt_dir.name, "blocked_post_generation_records_invalid", "attempt directory")
    attempt_id = attempt_dir.name
    if not attempt_dir.is_dir() or not ATTEMPT_RE.fullmatch(attempt_id):
        raise MaterialContractError("blocked_post_generation_records_invalid", "invalid attempt directory")
    board = require_exact_path(args.board, attempt_dir / "board.png", "blocked_post_generation_records_invalid", "board")
    generation = require_exact_path(args.generation_prompt, attempt_dir / args.generation_prompt.name, "blocked_post_generation_records_invalid", "generation prompt")
    spawn_path = require_exact_path(args.worker_spawn, attempt_dir / "worker_spawn.json", "blocked_post_generation_records_invalid", "worker spawn")
    worker_path = require_exact_path(args.worker_result, attempt_dir / "worker_result.json", "blocked_post_generation_records_invalid", "worker result")
    decision_path = require_exact_path(args.inspection_decision, attempt_dir / "qa_decision.json", "blocked_post_generation_records_invalid", "inspection decision")
    inspection_path = require_exact_path(args.inspection, attempt_dir / "qa.json", "blocked_post_generation_records_invalid", "inspection")
    enhancement_path = require_exact_path(args.enhancement_prompt, attempt_dir / args.enhancement_prompt.name, "blocked_post_generation_records_invalid", "enhancement prompt")
    handoff_path = require_exact_path(args.handoff, attempt_dir / args.handoff.name, "blocked_post_generation_records_invalid", "handoff")
    accepted_path = require_exact_path(args.accepted_attempt, run_dir / "accepted_attempt.json", "blocked_post_generation_records_invalid", "accepted attempt")

    manifest = load_reference_manifest(args.reference_manifest, run_dir)
    contract_record = load_source_contract(args.source_contract, run_dir, manifest)
    contract = contract_record["value"]
    expected_generation = attempt_dir / f"{contract['asset_id']}_{attempt_id}_generation_prompt.md"
    expected_enhancement = attempt_dir / f"{contract['asset_id']}_{attempt_id}_4k_enhancement_prompt.md"
    expected_handoff = attempt_dir / f"{contract['asset_id']}_{attempt_id}_4k_handoff.json"
    if any(
        normalized_path(actual) != normalized_path(expected)
        for actual, expected in (
            (generation, expected_generation),
            (enhancement_path, expected_enhancement),
            (handoff_path, expected_handoff),
        )
    ):
        raise MaterialContractError(
            "blocked_post_generation_records_invalid",
            "generation, enhancement, and handoff names must match the asset/attempt contract",
        )
    generation_bytes = read_prompt_bytes(generation, "blocked_post_generation_records_invalid", "generation prompt")
    require_prompt_block_once(generation_bytes, contract_record["prompt_block_bytes"], "blocked_post_generation_records_invalid")
    board_bytes = board.read_bytes()
    board_meta = inspect_image_bytes(board_bytes, code="blocked_post_generation_records_invalid", label="board", required_format="PNG")
    board_sha = sha256_bytes(board_bytes)
    worker, _ = load_json_file(worker_path, "blocked_post_generation_records_invalid", "worker result")
    spawn, _ = load_json_file(spawn_path, "blocked_post_generation_records_invalid", "worker spawn")
    decision, decision_bytes = load_json_file(decision_path, "blocked_post_generation_records_invalid", "inspection decision")
    inspection, inspection_bytes = load_json_file(inspection_path, "blocked_post_generation_records_invalid", "inspection")
    if (
        spawn.get("schema_version") != "material_worker_spawn.v2"
        or worker.get("schema_version") != "delegated_product_image_worker_result.v2"
        or spawn.get("attempt_id") != attempt_id
        or worker.get("attempt_id") != attempt_id
        or normalized_path(Path(worker.get("run_image_path", ""))) != normalized_path(board)
        or worker.get("image_sha256") != board_sha
        or worker.get("width_px") != board_meta["width_px"]
        or worker.get("height_px") != board_meta["height_px"]
        or worker.get("generation_prompt_sha256") != sha256_bytes(generation_bytes)
        or worker.get("reference_manifest_sha256") != manifest["sha256"]
        or worker.get("source_contract_sha256") != contract_record["sha256"]
        or normalized_path(Path(worker.get("worker_spawn_path", ""))) != normalized_path(spawn_path)
        or worker.get("worker_spawn_sha256") != _hash(spawn_path)
    ):
        raise MaterialContractError(
            "blocked_post_generation_records_invalid",
            "worker/spawn chain does not bind the selected board and frozen sources",
        )
    exec_source_path = require_exact_path(
        Path(spawn.get("worker_exec_source_path", "")),
        attempt_dir / "worker_exec.js",
        "blocked_post_generation_records_invalid",
        "worker exec source",
    )
    exec_receipt_path = require_exact_path(
        Path(spawn.get("worker_exec_receipt_path", "")),
        attempt_dir / "worker_exec.json",
        "blocked_post_generation_records_invalid",
        "worker exec receipt",
    )
    if not exec_source_path.is_file() or not exec_receipt_path.is_file():
        raise MaterialContractError("blocked_post_generation_records_invalid", "worker exec artifacts are missing")
    exec_bytes = exec_source_path.read_bytes()
    exec_receipt_bytes = exec_receipt_path.read_bytes()
    if (
        spawn.get("worker_exec_source_sha256") != sha256_bytes(exec_bytes)
        or worker.get("worker_exec_source_sha256") != sha256_bytes(exec_bytes)
        or spawn.get("worker_exec_receipt_sha256") != sha256_bytes(exec_receipt_bytes)
        or worker.get("worker_exec_receipt_sha256") != sha256_bytes(exec_receipt_bytes)
    ):
        raise MaterialContractError(
            "blocked_post_generation_records_invalid",
            "worker spawn/result no longer bind the exact exec artifacts",
        )
    rollout_path = Path(worker.get("worker_rollout_path", "")).resolve(strict=False)
    rollout_evidence = validate_worker_rollout(
        read_rollout(rollout_path),
        thread_id=worker["worker_thread_id"],
        agent_path=worker["agent_path"],
        parent_thread_id=worker["parent_thread_id"],
        expected_exec_bytes=exec_bytes,
    )
    saved_path = Path(worker.get("worker_saved_path", "")).resolve(strict=False)
    if (
        rollout_evidence["image_generation_call_id"] != worker["image_generation_call_id"]
        or normalized_path(Path(rollout_evidence["saved_path"])) != normalized_path(saved_path)
        or not saved_path.is_file()
        or saved_path.read_bytes() != board_bytes
    ):
        raise MaterialContractError(
            "blocked_post_generation_records_invalid",
            "worker rollout and saved PNG no longer match the selected board",
        )
    normalize_decision(decision, contract=contract, manifest=manifest)
    expected_inspection = build_qa_record(
        decision=decision,
        decision_path=decision_path,
        decision_sha256=sha256_bytes(decision_bytes),
        board_path=board,
        board_sha256=board_sha,
        width_px=board_meta["width_px"],
        height_px=board_meta["height_px"],
        worker_thread_id=worker["worker_thread_id"],
        image_generation_call_id=worker["image_generation_call_id"],
        contract=contract,
        manifest=manifest,
    )
    if inspection != expected_inspection or inspection_bytes != render_record_bytes(expected_inspection):
        raise MaterialContractError("blocked_board_inspection_invalid", "inspection is not the deterministic decision rendering")
    if inspection["assistant_qa_status"] != "passed":
        raise MaterialContractError("blocked_board_inspection_invalid", "only passed QA can create accepted records")
    cleanup_defects = [item for item in inspection["observed_defects"] if item["cleanup_eligible"]]
    source_refs = [{"alias": item["alias"], "path": item["frozen_path"], "sha256": item["sha256"]} for item in manifest["entries"]]
    enhancement_bytes = render_4k_enhancement_prompt_bytes(
        board_path=board,
        board_sha256=board_sha,
        source_references=source_refs,
        source_contract_path=args.source_contract.resolve(strict=False),
        source_contract_sha256=contract_record["sha256"],
        cleanup_defects=cleanup_defects,
    )
    handoff = build_handoff_record(
        attempt_id=attempt_id,
        generation_prompt_path=generation,
        generation_prompt_sha256=sha256_bytes(generation_bytes),
        enhancement_prompt_path=enhancement_path,
        enhancement_prompt_sha256=sha256_bytes(enhancement_bytes),
        inspection_path=inspection_path,
        inspection_sha256=sha256_bytes(inspection_bytes),
        board_path=board,
        board_sha256=board_sha,
        source_references=source_refs,
        source_contract_path=args.source_contract.resolve(strict=False),
        source_contract_sha256=contract_record["sha256"],
        observed_defects=cleanup_defects,
        external_status=args.external_4k_status,
        external_qa_status=args.external_4k_qa_status,
        external_production_status=args.external_4k_production_approval_status,
    )
    handoff_bytes = render_record_bytes(handoff)
    exec_source = exec_source_path
    exec_receipt = exec_receipt_path
    paths_and_hashes: dict[str, Any] = {
        "reference_manifest_path": str(args.reference_manifest.resolve(strict=False)),
        "reference_manifest_sha256": manifest["sha256"],
        "source_contract_path": str(args.source_contract.resolve(strict=False)),
        "source_contract_sha256": contract_record["sha256"],
        "prompt_block_path": str(contract_record["prompt_block_path"]),
        "prompt_block_sha256": contract_record["prompt_block_sha256"],
        "generation_prompt_path": str(generation),
        "generation_prompt_sha256": sha256_bytes(generation_bytes),
        "enhancement_prompt_path": str(enhancement_path),
        "4k_enhancement_prompt_sha256": sha256_bytes(enhancement_bytes),
        "worker_spawn_path": str(spawn_path),
        "worker_spawn_sha256": _hash(spawn_path),
        "worker_exec_source_path": str(exec_source),
        "worker_exec_source_sha256": _hash(exec_source),
        "worker_exec_receipt_path": str(exec_receipt),
        "worker_exec_receipt_sha256": _hash(exec_receipt),
        "worker_result_path": str(worker_path),
        "worker_result_sha256": _hash(worker_path),
        "board_path": str(board),
        "image_sha256": board_sha,
        "inspection_decision_path": str(decision_path),
        "inspection_decision_sha256": sha256_bytes(decision_bytes),
        "inspection_path": str(inspection_path),
        "inspection_sha256": sha256_bytes(inspection_bytes),
        "handoff_path": str(handoff_path),
        "handoff_sha256": sha256_bytes(handoff_bytes),
    }
    accepted = build_accepted_record(attempt_id=attempt_id, paths_and_hashes=paths_and_hashes)
    accepted_bytes = render_record_bytes(accepted)

    # Preflight every destination before the first write. accepted_attempt.json is written last and is the commit marker.
    _preflight(enhancement_path, enhancement_bytes, "blocked_post_generation_output_conflict")
    _preflight(handoff_path, handoff_bytes, "blocked_post_generation_output_conflict")
    _preflight(accepted_path, accepted_bytes, "blocked_post_generation_output_conflict")
    created = {
        "enhancement_prompt": create_only_bytes(enhancement_path, enhancement_bytes, code="blocked_post_generation_output_conflict", idempotent=True),
        "handoff": create_only_bytes(handoff_path, handoff_bytes, code="blocked_post_generation_output_conflict", idempotent=True),
        "accepted_attempt": create_only_bytes(accepted_path, accepted_bytes, code="blocked_post_generation_output_conflict", idempotent=True),
    }
    print(json.dumps({"ok": True, "created": created, "accepted_attempt": str(accepted_path), "accepted_sha256": sha256_bytes(accepted_bytes)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MaterialContractError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}), file=sys.stderr)
        raise SystemExit(2)
    except OSError as exc:
        print(json.dumps({"ok": False, "error_code": "blocked_post_generation_filesystem", "detail": str(exc)}), file=sys.stderr)
        raise SystemExit(2)
