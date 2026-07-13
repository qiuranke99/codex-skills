#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SCHEMA_VERSION = "complex_product_identity_asset_package.v1"

BOARD_DEFINITIONS = (
    ("geometry_lock", "02_Geometry_Lock_Board", "required"),
    ("material_surface_lock", "03_Material_Surface_Lock", "conditional"),
    ("component_detail_lock", "04_Component_Detail_Lock", "conditional"),
    ("state_transition_lock", "05_State_Transition_Lock", "conditional"),
    ("marking_identity_lock", "06_Marking_Identity_Lock", "conditional"),
)

FINAL_DIRECTORY = "07_Final_Product_Identity_Lock_Board"
SPECIFICATION_FILE = "01_Product_Identity_Specification.md"
PROMPT_FILE = "08_4K_Upscale_Prompts.md"
MANIFEST_FILE = "asset_package_manifest.json"


def board_record(board_id: str, directory: str, relevance: str) -> dict:
    return {
        "board_id": board_id,
        "directory": directory,
        "relevance": relevance,
        "source_gate": "blocked" if board_id == "geometry_lock" else "not_applicable",
        "source_gate_reasons": ["Stage 1 analysis not complete"],
        "evidence_ids": [],
        "status": "planned",
        "attempt_count": 0,
        "terminal_generation_call": "not_started",
        "asset_file": None,
        "actual_dimensions": None,
        "generation_prompt_sha256": None,
        "native_4k_claimed": False,
        "native_4k_evidence": None,
        "qa": {
            "geometry_consistency": "not_applicable",
            "material_consistency": "not_applicable",
            "identity_consistency": "not_applicable",
            "failure_flags": [],
        },
    }


def initial_manifest(asset_id: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "asset_id": asset_id,
        "package_status": "initialized",
        "identity_specification": SPECIFICATION_FILE,
        "identity_specification_sha256": None,
        "source_bundle_sha256": None,
        "unresolved_hard_conflicts": [],
        "boards": [board_record(*definition) for definition in BOARD_DEFINITIONS],
        "final_board": {
            "board_id": "final_product_identity_lock_board",
            "directory": FINAL_DIRECTORY,
            "status": "blocked",
            "source_gate_reasons": ["Complete-package gate not evaluated"],
            "source_board_ids": [],
            "attempt_count": 0,
            "terminal_generation_call": "not_started",
            "asset_file": None,
            "actual_dimensions": None,
            "generation_prompt_sha256": None,
            "native_4k_claimed": False,
            "native_4k_evidence": None,
            "qa": {
                "geometry_consistency": "not_applicable",
                "material_consistency": "not_applicable",
                "identity_consistency": "not_applicable",
                "failure_flags": [],
            },
        },
        "four_k_prompt_file": PROMPT_FILE,
        "four_k_prompts": [],
        "approved_asset_count": 0,
        "four_k_mapping_count": 0,
        "production_approval_status": "not_granted",
    }


def specification_template(asset_id: str) -> str:
    return f"""# Product Identity Specification

Asset ID: `{asset_id}`
Status: analysis_pending

## Source Ledger

| Source ID | Source | Role | View / State | Variant Notes | Limits / Conflicts |
|---|---|---|---|---|---|

## Product Identity Summary

## Overall Geometry And Proportions

## Product Part Tree

| Part ID | Name | Parent | Count | Side | Attachment | Material | Identity Risk | Evidence Status | Source IDs |
|---|---|---|---|---|---|---|---|---|---|

## Material And Surface Model

## Marking Identity

## State Graph

## Evidence Ledger

### Observed

### Cross Validated

### Inferred

### Unknown

### Conflicting

## Board Source Decisions

| Board | Relevance | Source Gate | Evidence IDs | Unsupported Zones / Reason |
|---|---|---|---|---|
| Geometry Lock | required | blocked | | Stage 1 analysis not complete |
| Material & Surface Lock | conditional | not_applicable | | Stage 1 analysis not complete |
| Component Detail Lock | conditional | not_applicable | | Stage 1 analysis not complete |
| State Transition Lock | conditional | not_applicable | | Stage 1 analysis not complete |
| Marking Identity Lock | conditional | not_applicable | | Stage 1 analysis not complete |

## Unresolved Hard Conflicts

## Frozen Hashes

- Source bundle SHA-256:
- Specification SHA-256:
"""


def prompt_template() -> str:
    return """# 4K Upscale Prompts

Add exactly one asset-specific section after each generated asset passes visual QA. Preserve the accepted Codex asset and original sources; do not use this file as proof that external 4K generation occurred.
"""


def validate_asset_id(asset_id: str) -> None:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", asset_id):
        raise ValueError("asset-id must use 1-64 lowercase letters, digits, hyphens, or underscores")


def create_package(output: Path, asset_id: str) -> None:
    validate_asset_id(asset_id)
    output = output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty package: {output}")

    output.mkdir(parents=True, exist_ok=True)
    for _, directory, _ in BOARD_DEFINITIONS:
        (output / directory).mkdir(exist_ok=True)
    (output / FINAL_DIRECTORY).mkdir(exist_ok=True)

    (output / SPECIFICATION_FILE).write_text(
        specification_template(asset_id), encoding="utf-8", newline="\n"
    )
    (output / PROMPT_FILE).write_text(prompt_template(), encoding="utf-8", newline="\n")
    (output / MANIFEST_FILE).write_text(
        json.dumps(initial_manifest(asset_id), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a complex product identity asset package.")
    parser.add_argument("--output", required=True, type=Path, help="Exact package directory to create")
    parser.add_argument("--asset-id", required=True, help="Stable lowercase asset identifier")
    args = parser.parse_args()

    try:
        create_package(args.output, args.asset_id)
    except (ValueError, FileExistsError, OSError) as exc:
        print(f"initialization: FAILED\n  - {exc}", file=sys.stderr)
        return 1

    print(f"asset package initialized: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
