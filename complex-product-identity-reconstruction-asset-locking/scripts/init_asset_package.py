#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


SCHEMA_VERSION = "complex_product_identity_asset_package.v2"

CAMERA_DEFINITIONS = (
    ("CAM_FRONT_3Q_LEFT", "front-left three-quarter", "front_left_three_quarter", "eye", ["front", "left"]),
    ("CAM_FRONT_3Q_RIGHT", "front-right three-quarter", "front_right_three_quarter", "eye", ["front", "right"]),
    ("CAM_LEFT_PROFILE", "left profile", "left_profile", "eye", ["left", "side"]),
    ("CAM_RIGHT_PROFILE", "right profile", "right_profile", "eye", ["right", "side"]),
    ("CAM_REAR_3Q", "rear three-quarter", "rear_three_quarter", "eye", ["rear", "side"]),
    ("CAM_HIGH_FRONT_3Q", "high front three-quarter", "front_three_quarter", "high", ["front", "high"]),
)

DIAGNOSTIC_BOARD_DEFINITIONS = (
    ("material_surface_lock", "03_Material_Surface_Lock", "conditional"),
    ("component_detail_lock", "04_Component_Detail_Lock", "conditional"),
    ("state_transition_lock", "05_State_Transition_Lock", "conditional"),
    ("marking_identity_lock", "06_Marking_Identity_Lock", "conditional"),
)

GEOMETRY_DIRECTORY = "02_Geometry_Camera_Coverage"
CAMERA_ASSET_DIRECTORY = f"{GEOMETRY_DIRECTORY}/camera_assets"
CAMERA_REPORT_FILE = f"{GEOMETRY_DIRECTORY}/camera_coverage_report.md"
UPLOAD_DIRECTORY = "07_Primary_Upload_Bundle"
SPECIFICATION_FILE = "01_Product_Identity_Specification.md"
PROMPT_FILE = "08_4K_Upscale_Prompts.md"
MANIFEST_FILE = "asset_package_manifest.json"


def camera_record(camera_id: str, role: str, azimuth_bin: str, elevation_bin: str, sectors: list[str]) -> dict:
    return {
        "camera_id": camera_id,
        "role": role,
        "pose_bin": {
            "azimuth": azimuth_bin,
            "elevation": elevation_bin,
            "shot_size": "whole_product",
        },
        "coverage_sectors": sectors,
        "critical_node_ids": [],
        "source_gate": "blocked",
        "source_gate_reasons": ["Stage 1 view-evidence analysis not complete"],
        "source_ids": [],
        "evidence_mode": "unassigned",
        "identity_authority": "none",
        "status": "planned",
        "attempt_count": 0,
        "terminal_generation_call": "not_started",
        "asset_file": None,
        "asset_sha256": None,
        "source_asset_sha256": None,
        "provenance_sha256": None,
        "actual_dimensions": None,
        "generation_prompt_sha256": None,
        "qa": {
            "subject_match": "not_applicable",
            "complete_product": "not_applicable",
            "pose_match": "not_applicable",
            "critical_node_consistency": "not_applicable",
            "cross_camera_consistency": "not_applicable",
            "text_pollution": "not_applicable",
            "failure_flags": [],
        },
    }


def board_record(board_id: str, directory: str, relevance: str) -> dict:
    return {
        "board_id": board_id,
        "directory": directory,
        "relevance": relevance,
        "source_gate": "not_applicable",
        "source_gate_reasons": ["Stage 1 analysis not complete"],
        "evidence_ids": [],
        "status": "planned",
        "attempt_count": 0,
        "terminal_generation_call": "not_started",
        "asset_file": None,
        "asset_sha256": None,
        "actual_dimensions": None,
        "generation_prompt_sha256": None,
        "native_4k_claimed": False,
        "native_4k_evidence": None,
        "qa": {
            "geometry_consistency": "not_applicable",
            "material_consistency": "not_applicable",
            "identity_consistency": "not_applicable",
            "subject_match": "not_applicable",
            "text_pollution": "not_applicable",
            "failure_flags": [],
        },
    }


def camera_plan_sha256(cameras: list[dict], target_camera_ids: list[str], minimum: int) -> str:
    payload = {
        "minimum_video_ready_camera_count": minimum,
        "target_camera_ids": target_camera_ids,
        "cameras": [
            {
                "camera_id": item["camera_id"],
                "role": item["role"],
                "pose_bin": item["pose_bin"],
                "coverage_sectors": item["coverage_sectors"],
            }
            for item in cameras
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def initial_manifest(asset_id: str) -> dict:
    cameras = [camera_record(*definition) for definition in CAMERA_DEFINITIONS]
    target_camera_ids = [record["camera_id"] for record in cameras]
    minimum = 4
    return {
        "schema_version": SCHEMA_VERSION,
        "asset_id": asset_id,
        "package_status": "initialized",
        "identity_specification": SPECIFICATION_FILE,
        "identity_specification_sha256": None,
        "source_bundle_sha256": None,
        "camera_coverage_report": CAMERA_REPORT_FILE,
        "unresolved_hard_conflicts": [],
        "geometry_coverage": {
            "coverage_id": "geometry_camera_coverage",
            "directory": GEOMETRY_DIRECTORY,
            "status": "planned",
            "camera_plan_sha256": camera_plan_sha256(cameras, target_camera_ids, minimum),
            "target_camera_ids": target_camera_ids,
            "minimum_video_ready_camera_count": minimum,
            "camera_assets": cameras,
            "coverage_metrics": {
                "approved_camera_count": 0,
                "hard_authority_camera_count": 0,
                "unique_pose_bin_count": 0,
                "covered_sectors": [],
                "elevation_bands": [],
                "redundancy_count": 0,
                "coverage_tier": "none",
            },
            "contact_sheet": {
                "status": "not_created",
                "asset_file": None,
                "asset_sha256": None,
                "derived_from_camera_ids": [],
                "identity_authority": "none",
            },
        },
        "diagnostic_boards": [board_record(*definition) for definition in DIAGNOSTIC_BOARD_DEFINITIONS],
        "primary_upload_bundle": {
            "directory": UPLOAD_DIRECTORY,
            "status": "planned",
            "max_asset_count": 5,
            "selections": [],
            "selection_reason": "",
        },
        "four_k_prompt_file": PROMPT_FILE,
        "four_k_prompts": [],
        "approved_asset_count": 0,
        "four_k_mapping_count": 0,
        "production_approval_status": "not_granted",
    }


def specification_template(asset_id: str) -> str:
    camera_rows = "\n".join(
        f"| {camera_id} | {role} | {azimuth} | {elevation} | blocked | unassigned | | Stage 1 not complete |"
        for camera_id, role, azimuth, elevation, _ in CAMERA_DEFINITIONS
    )
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

## Critical Node Ledger

| Node ID | Assembly / Relationship | Expected Count | Asymmetry / State | Risk | Evidence Status | Source IDs | Rejection Conditions |
|---|---|---:|---|---|---|---|---|

## Material And Surface Model

## Marking Identity

## State Graph

## Evidence Ledger

### Observed

### Cross Validated

### Inferred

### Unknown

### Conflicting

## View Evidence Matrix

| Source ID | Observed Azimuth | Elevation | Whole Product | Visible Critical Nodes | Occluded / Unknown Zones | Variant Confidence |
|---|---|---|---|---|---|---|

## Camera Coverage Plan

| Camera ID | Role | Azimuth Bin | Elevation Bin | Source Gate | Evidence Mode | Source IDs | Blocker / Unique Coverage Value |
|---|---|---|---|---|---|---|---|
{camera_rows}

## Coverage Gap Requests

List one exact missing capture, verified source render, or evidence requirement for every blocked target camera. Do not ask generically for “more references.”

## Diagnostic Board Source Decisions

| Board | Relevance | Source Gate | Evidence IDs | Unsupported Zones / Reason |
|---|---|---|---|---|
| Material & Surface Lock | conditional | not_applicable | | Stage 1 analysis not complete |
| Component Detail Lock | conditional | not_applicable | | Stage 1 analysis not complete |
| State Transition Lock | conditional | not_applicable | | Stage 1 analysis not complete |
| Marking Identity Lock | conditional | not_applicable | | Stage 1 analysis not complete |

## Unresolved Hard Conflicts

## Frozen Hashes

- Source bundle SHA-256:
- Specification SHA-256:
- Camera plan SHA-256:
"""


def camera_report_template() -> str:
    return """# Camera Coverage Report

Status: analysis_pending

## Accepted Independent Cameras

## Blocked Cameras And Exact Evidence Requests

## Coverage Metrics

- Approved camera count: 0
- Hard-authority camera count: 0
- Unique pose-bin count: 0
- Covered sectors: none
- Elevation bands: none
- Redundancy count: 0
- Coverage tier: none

## Downstream Upload Recommendation

No upload bundle is approved yet.
"""


def prompt_template() -> str:
    return """# 4K Upscale Prompts

Add exactly one asset-specific section after each camera asset or diagnostic board passes visual QA. Preserve the accepted asset and original sources; this file is a handoff, not proof that external 4K generation occurred.
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
    (output / CAMERA_ASSET_DIRECTORY).mkdir(parents=True, exist_ok=True)
    for _, directory, _ in DIAGNOSTIC_BOARD_DEFINITIONS:
        (output / directory).mkdir(exist_ok=True)
    (output / UPLOAD_DIRECTORY).mkdir(exist_ok=True)

    (output / SPECIFICATION_FILE).write_text(
        specification_template(asset_id), encoding="utf-8", newline="\n"
    )
    (output / CAMERA_REPORT_FILE).write_text(camera_report_template(), encoding="utf-8", newline="\n")
    (output / PROMPT_FILE).write_text(prompt_template(), encoding="utf-8", newline="\n")
    (output / MANIFEST_FILE).write_text(
        json.dumps(initial_manifest(asset_id), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a complex product identity asset package v2.")
    parser.add_argument("--output", required=True, type=Path, help="Exact package directory to create")
    parser.add_argument("--asset-id", required=True, help="Stable lowercase asset identifier")
    args = parser.parse_args()

    try:
        create_package(args.output, args.asset_id)
    except (ValueError, FileExistsError, OSError) as exc:
        print(f"initialization: FAILED\n  - {exc}", file=sys.stderr)
        return 1

    print(f"asset package v2 initialized: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
