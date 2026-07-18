#!/usr/bin/env python3
"""Render the exact QA-scoped material 4K enhancement prompt create-only."""

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
    render_4k_enhancement_prompt_bytes,
    require_exact_keys,
    require_exact_path,
    sha256_bytes,
)
from material_decision_records import QA_KEYS, board_gate_keys, validate_observed_defects


def same_path(value: object, expected: Path) -> bool:
    return isinstance(value, str) and normalized_path(Path(value)) == normalized_path(expected)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--attempt-dir", required=True, type=Path)
    parser.add_argument("--board", required=True, type=Path)
    parser.add_argument("--inspection", required=True, type=Path)
    parser.add_argument("--reference-manifest", required=True, type=Path)
    parser.add_argument("--source-contract", required=True, type=Path)
    parser.add_argument("--enhancement-prompt", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_dir = args.run_dir.expanduser().resolve(strict=False)
    attempt_dir = args.attempt_dir.expanduser().resolve(strict=False)
    attempt_id = attempt_dir.name
    if (
        not run_dir.is_dir()
        or not ATTEMPT_RE.fullmatch(attempt_id)
        or attempt_dir.parent != run_dir / "attempts"
    ):
        raise MaterialContractError(
            "blocked_4k_prompt_contract_invalid", "invalid run or attempt directory"
        )
    board = require_exact_path(
        args.board,
        attempt_dir / "board.png",
        "blocked_4k_prompt_contract_invalid",
        "accepted board",
    )
    inspection_path = require_exact_path(
        args.inspection,
        attempt_dir / "qa.json",
        "blocked_4k_prompt_contract_invalid",
        "board inspection",
    )
    manifest_path = require_exact_path(
        args.reference_manifest,
        run_dir / "sources" / "reference-manifest.json",
        "blocked_4k_prompt_contract_invalid",
        "reference manifest",
    )
    contract_path = require_exact_path(
        args.source_contract,
        run_dir / "sources" / "material-source-contract.json",
        "blocked_4k_prompt_contract_invalid",
        "source contract",
    )
    manifest_record = load_reference_manifest(manifest_path, run_dir)
    contract_record = load_source_contract(contract_path, run_dir, manifest_record)
    expected_prompt_path = (
        attempt_dir
        / f"{contract_record['value']['asset_id']}_{attempt_id}_4k_enhancement_prompt.md"
    )
    prompt_path = require_exact_path(
        args.enhancement_prompt,
        expected_prompt_path,
        "blocked_4k_prompt_contract_invalid",
        "4K enhancement prompt",
    )
    if not board.is_file():
        raise MaterialContractError(
            "blocked_4k_prompt_contract_invalid", "accepted board is missing"
        )
    board_bytes = board.read_bytes()
    inspect_image_bytes(
        board_bytes,
        code="blocked_4k_prompt_contract_invalid",
        label="accepted board",
        required_format="PNG",
    )
    board_sha = sha256_bytes(board_bytes)
    inspection, _ = load_json_file(
        inspection_path, "blocked_board_inspection_invalid", "board inspection"
    )
    require_exact_keys(inspection, QA_KEYS, "blocked_board_inspection_invalid", "board inspection")
    expected_qa_schema = (
        "material_board_qa.v4"
        if contract_record["value"].get("schema_version") == "material_source_contract.v2"
        else "material_board_qa.v3"
    )
    if (
        inspection["schema_version"] != expected_qa_schema
        or inspection["attempt_id"] != attempt_id
        or inspection["inspected"] is not True
        or not same_path(inspection["board_path"], board)
        or inspection["image_sha256"] != board_sha
        or inspection["assistant_qa_status"] != "passed"
        or inspection["repair_required"] is not False
        or inspection["repair_reasons"] != []
    ):
        raise MaterialContractError(
            "blocked_board_inspection_invalid", "inspection is not an accepted board binding"
        )
    gates = inspection["board_gates"]
    if not isinstance(gates, dict):
        raise MaterialContractError("blocked_board_inspection_invalid", "board_gates must be object")
    require_exact_keys(
        gates,
        board_gate_keys(contract_record["value"]),
        "blocked_board_inspection_invalid",
        "board gates",
    )
    if any(
        value != "pass"
        for key, value in gates.items()
        if key != "state_window_source_supported"
    ) or gates["state_window_source_supported"] not in {"pass", "not_used"}:
        raise MaterialContractError(
            "blocked_board_inspection_invalid", "not every required board gate passed"
        )
    panels = contract_record["value"]["panel_plan"]
    invariants = contract_record["value"]["critical_invariants"]
    if [item.get("panel_id") for item in inspection["panel_results"]] != [
        item["panel_id"] for item in panels
    ] or any(item.get("status") != "pass" for item in inspection["panel_results"]):
        raise MaterialContractError(
            "blocked_board_inspection_invalid", "panel QA is incomplete or failed"
        )
    if [item.get("invariant_id") for item in inspection["invariant_results"]] != [
        item["invariant_id"] for item in invariants
    ] or any(item.get("status") != "pass" for item in inspection["invariant_results"]):
        raise MaterialContractError(
            "blocked_board_inspection_invalid", "invariant QA is incomplete or failed"
        )
    defects = validate_observed_defects(
        inspection["observed_defects"],
        panel_ids={item["panel_id"] for item in panels},
        invariant_ids={item["invariant_id"] for item in invariants},
        source_aliases=set(manifest_record["aliases"]),
    )
    if any(not item["cleanup_eligible"] for item in defects):
        raise MaterialContractError(
            "blocked_4k_cleanup_scope_invalid",
            "4K prompt cannot be rendered while any repair-only defect remains",
        )
    source_refs = [
        {"alias": entry["alias"], "path": entry["frozen_path"], "sha256": entry["sha256"]}
        for entry in manifest_record["entries"]
    ]
    prompt_bytes = render_4k_enhancement_prompt_bytes(
        board_path=board,
        board_sha256=board_sha,
        source_references=source_refs,
        source_contract_path=contract_path,
        source_contract_sha256=contract_record["sha256"],
        cleanup_defects=defects,
    )
    created = create_only_bytes(
        prompt_path,
        prompt_bytes,
        code="blocked_4k_prompt_output_conflict",
        idempotent=True,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "schema_version": "material_4k_enhancement_prompt.v2",
                "enhancement_prompt_path": str(prompt_path),
                "enhancement_prompt_sha256": sha256_bytes(prompt_bytes),
                "cleanup_defect_count": len(defects),
                "idempotent": not created,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MaterialContractError as exc:
        print(
            json.dumps(
                {"ok": False, "error_code": exc.code, "detail": exc.detail},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)
    except OSError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_code": "blocked_4k_prompt_filesystem",
                    "detail": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)
