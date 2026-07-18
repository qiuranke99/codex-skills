#!/usr/bin/env python3
"""Freeze one source-bound v3/v4 material board QA record."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from material_contract import (
    ATTEMPT_RE,
    MaterialContractError,
    create_only_bytes,
    inspect_image_bytes,
    load_json_file,
    load_reference_manifest,
    load_source_contract,
    normalized_path,
    pretty_json_bytes,
    require_exact_path,
    sha256_bytes,
)
from material_decision_records import build_qa_record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--attempt-dir", required=True, type=Path)
    parser.add_argument("--board", required=True, type=Path)
    parser.add_argument("--worker-result", required=True, type=Path)
    parser.add_argument("--reference-manifest", required=True, type=Path)
    parser.add_argument("--source-contract", required=True, type=Path)
    parser.add_argument("--decision-draft", required=True, type=Path)
    parser.add_argument("--inspection", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_dir = args.run_dir.expanduser().resolve(strict=False)
    attempt_dir = require_exact_path(args.attempt_dir, run_dir / "attempts" / args.attempt_dir.name, "blocked_board_inspection_invalid", "attempt directory")
    if not attempt_dir.is_dir() or not ATTEMPT_RE.fullmatch(attempt_dir.name):
        raise MaterialContractError("blocked_board_inspection_invalid", "invalid attempt directory")
    board = require_exact_path(args.board, attempt_dir / "board.png", "blocked_board_inspection_invalid", "board")
    worker_path = require_exact_path(args.worker_result, attempt_dir / "worker_result.json", "blocked_board_inspection_invalid", "worker result")
    decision_path = require_exact_path(args.decision_draft, attempt_dir / "qa_decision.json", "blocked_board_inspection_invalid", "QA decision draft")
    inspection_path = require_exact_path(args.inspection, attempt_dir / "qa.json", "blocked_board_inspection_invalid", "inspection")
    manifest = load_reference_manifest(args.reference_manifest, run_dir)
    contract_record = load_source_contract(args.source_contract, run_dir, manifest)
    worker, _ = load_json_file(worker_path, "blocked_board_inspection_invalid", "worker result")
    decision, decision_bytes = load_json_file(decision_path, "blocked_board_inspection_invalid", "QA decision draft")
    if worker.get("schema_version") != "delegated_product_image_worker_result.v2" or worker.get("attempt_id") != attempt_dir.name:
        raise MaterialContractError("blocked_board_inspection_invalid", "worker result schema/attempt mismatch")
    if normalized_path(Path(worker.get("run_image_path", ""))) != normalized_path(board):
        raise MaterialContractError("blocked_board_inspection_invalid", "worker result does not bind board")
    board_bytes = board.read_bytes()
    metadata = inspect_image_bytes(board_bytes, code="blocked_board_inspection_invalid", label="board", required_format="PNG")
    board_sha = sha256_bytes(board_bytes)
    if worker.get("image_sha256") != board_sha or worker.get("width_px") != metadata["width_px"] or worker.get("height_px") != metadata["height_px"]:
        raise MaterialContractError("blocked_board_inspection_invalid", "worker result board evidence mismatch")
    record = build_qa_record(
        decision=decision,
        decision_path=decision_path,
        decision_sha256=sha256_bytes(decision_bytes),
        board_path=board,
        board_sha256=board_sha,
        width_px=metadata["width_px"],
        height_px=metadata["height_px"],
        worker_thread_id=worker["worker_thread_id"],
        image_generation_call_id=worker["image_generation_call_id"],
        contract=contract_record["value"],
        manifest=manifest,
    )
    created = create_only_bytes(
        inspection_path,
        pretty_json_bytes(record),
        code="blocked_board_inspection_output_conflict",
        idempotent=True,
    )
    print(json.dumps({"ok": True, "created": created, "inspection_path": str(inspection_path), "inspection_sha256": sha256_bytes(pretty_json_bytes(record))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MaterialContractError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}), file=sys.stderr)
        raise SystemExit(2)
    except OSError as exc:
        print(json.dumps({"ok": False, "error_code": "blocked_board_inspection_filesystem", "detail": str(exc)}), file=sys.stderr)
        raise SystemExit(2)
