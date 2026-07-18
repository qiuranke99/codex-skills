#!/usr/bin/env python3
"""Create one editable source-to-board QA decision scaffold for a resolved attempt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from material_contract import (
    ATTEMPT_RE,
    MaterialContractError,
    create_only_bytes,
    load_reference_manifest,
    load_source_contract,
    pretty_json_bytes,
    require_exact_path,
)
from material_decision_records import BOARD_GATE_KEYS, fact_sources


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--attempt-dir", required=True, type=Path)
    parser.add_argument("--reference-manifest", required=True, type=Path)
    parser.add_argument("--source-contract", required=True, type=Path)
    parser.add_argument("--decision-draft", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_dir = args.run_dir.expanduser().resolve(strict=False)
    attempt_dir = require_exact_path(
        args.attempt_dir,
        run_dir / "attempts" / args.attempt_dir.name,
        "blocked_board_inspection_invalid",
        "attempt directory",
    )
    if not attempt_dir.is_dir() or not ATTEMPT_RE.fullmatch(attempt_dir.name):
        raise MaterialContractError("blocked_board_inspection_invalid", "invalid attempt directory")
    decision_path = require_exact_path(
        args.decision_draft,
        attempt_dir / "qa_decision.json",
        "blocked_board_inspection_invalid",
        "QA decision draft",
    )
    manifest = load_reference_manifest(args.reference_manifest, run_dir)
    contract_record = load_source_contract(args.source_contract, run_dir, manifest)
    contract = contract_record["value"]
    sources_by_fact = fact_sources(contract)
    scaffold = {
        "schema_version": "material_board_qa_decision.v1",
        "attempt_id": attempt_dir.name,
        "comparison_mode": "source_to_board_visual_comparison",
        "assistant_qa_status": "pending",
        "production_approval_status": "not_granted",
        "board_gates": {key: "pending" for key in sorted(BOARD_GATE_KEYS)},
        "panel_results": [
            {
                "panel_id": panel["panel_id"],
                "source_aliases": panel["source_aliases"],
                "invariant_ids": panel["invariant_ids"],
                "status": "pending",
                "source_fidelity": "pending",
                "source_observation": "",
                "board_observation": "",
            }
            for panel in contract["panel_plan"]
        ],
        "invariant_results": [
            {
                "invariant_id": invariant["invariant_id"],
                "category": invariant["category"],
                "source_aliases": sources_by_fact[invariant["fact_id"]],
                "status": "pending",
                "source_fidelity": "pending",
                "source_observation": "",
                "board_observation": "",
            }
            for invariant in contract["critical_invariants"]
        ],
        "observed_defects": [],
        "repair_required": True,
        "repair_reasons": ["complete source-to-board visual comparison before freezing QA"],
    }
    created = create_only_bytes(
        decision_path,
        pretty_json_bytes(scaffold),
        code="blocked_board_inspection_output_conflict",
        idempotent=True,
    )
    print(json.dumps({"ok": True, "created": created, "decision_path": str(decision_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MaterialContractError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}), file=sys.stderr)
        raise SystemExit(2)
