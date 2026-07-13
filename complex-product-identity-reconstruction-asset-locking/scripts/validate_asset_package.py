#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "complex_product_identity_asset_package.v1"
SPECIFICATION_FILE = "01_Product_Identity_Specification.md"
PROMPT_FILE = "08_4K_Upscale_Prompts.md"
MANIFEST_FILE = "asset_package_manifest.json"

BOARD_DIRECTORIES = {
    "geometry_lock": "02_Geometry_Lock_Board",
    "material_surface_lock": "03_Material_Surface_Lock",
    "component_detail_lock": "04_Component_Detail_Lock",
    "state_transition_lock": "05_State_Transition_Lock",
    "marking_identity_lock": "06_Marking_Identity_Lock",
}
FINAL_BOARD_ID = "final_product_identity_lock_board"
FINAL_DIRECTORY = "07_Final_Product_Identity_Lock_Board"

PACKAGE_STATUSES = {
    "initialized",
    "analysis_complete",
    "generation_in_progress",
    "partial_approved",
    "complete",
    "blocked_source_insufficient",
    "blocked_identity_conflict",
    "blocked_generation_runtime",
    "four_k_mapping_failed",
}
BOARD_STATUSES = {
    "planned",
    "generation_pending",
    "awaiting_post_generation_continuation",
    "qa_pending",
    "repair_required",
    "approved",
    "blocked",
    "blocked_generation_quality",
    "not_applicable",
}
RELEVANCE = {"required", "conditional", "not_applicable"}
SOURCE_GATES = {"approved", "blocked", "not_applicable"}
QA_VALUES = {"pass", "fail", "not_applicable"}
TERMINAL_VALUES = {"not_started", "pending", "executed", "failed"}
PRODUCTION_APPROVAL = {"not_granted", "user_granted", "external_pipeline_granted"}
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

REQUIRED_SPEC_HEADINGS = (
    "## Product Part Tree",
    "## State Graph",
    "### Observed",
    "### Cross Validated",
    "### Inferred",
    "### Unknown",
    "### Conflicting",
    "## Board Source Decisions",
)
REQUIRED_PRESERVES = {"geometry", "part_count", "proportions", "markings", "materials"}
ALLOWED_4K_CHANGES = {
    "resolution",
    "edge_definition",
    "realistic_microtexture",
    "source_supported_fine_detail",
}
REQUIRED_PROMPT_PHRASES = (
    "preserve original product geometry",
    "preserve part count",
    "preserve proportions",
    "preserve any source-supported logo and markings exactly",
    "preserve materials and colors",
    "enhance only clarity and realistic micro-texture",
    "do not redesign the product",
)


class ValidationFailure(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationFailure(f"invalid UTF-8 JSON in {path}: {exc}") from exc
    require(isinstance(data, dict), f"JSON root must be an object: {path}")
    return data


def require_hash(value: Any, field: str, *, allow_none: bool = False) -> None:
    if value is None and allow_none:
        return
    require(isinstance(value, str) and HASH_RE.fullmatch(value) is not None, f"{field} must be SHA-256 lowercase hex")


def require_asset(root: Path, value: Any, field: str) -> Path:
    require(isinstance(value, str) and value.strip(), f"{field} must name an asset file")
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts, f"{field} must be package-relative")
    path = root / relative
    require(path.is_file() and path.stat().st_size > 8, f"{field} is missing or empty: {value}")
    require(path.suffix.lower() == ".png", f"{field} must be a PNG: {value}")
    require(path.read_bytes()[:8] == PNG_SIGNATURE, f"{field} is not a valid PNG signature: {value}")
    return path


def require_dimensions(value: Any, field: str) -> None:
    require(isinstance(value, dict), f"{field} must contain width and height")
    require(isinstance(value.get("width"), int) and value["width"] > 0, f"{field}.width must be positive")
    require(isinstance(value.get("height"), int) and value["height"] > 0, f"{field}.height must be positive")


def validate_native_4k(record: dict[str, Any], field: str) -> None:
    claimed = record.get("native_4k_claimed")
    require(isinstance(claimed, bool), f"{field}.native_4k_claimed must be boolean")
    require(claimed is False, f"{field}.native_4k_claimed must remain false for Codex package assets")
    require(record.get("native_4k_evidence") is None, f"{field}.native_4k_evidence must remain null for Codex package assets")


def validate_qa(record: dict[str, Any], field: str, approved: bool) -> None:
    qa = record.get("qa")
    require(isinstance(qa, dict), f"{field}.qa must be an object")
    for key in ("geometry_consistency", "material_consistency", "identity_consistency"):
        value = qa.get(key)
        require(value in QA_VALUES, f"{field}.qa.{key} has invalid value: {value}")
    flags = qa.get("failure_flags")
    require(isinstance(flags, list) and all(isinstance(item, str) for item in flags), f"{field}.qa.failure_flags must be a string list")
    if approved:
        require(not flags, f"{field} cannot be approved with failure flags")
        require(qa["geometry_consistency"] == "pass", f"{field} approved asset requires geometry_consistency: pass")
        require(qa["identity_consistency"] == "pass", f"{field} approved asset requires identity_consistency: pass")
        if record.get("board_id") in {"material_surface_lock", FINAL_BOARD_ID}:
            require(qa["material_consistency"] == "pass", f"{field} approved asset requires material_consistency: pass")
        else:
            require(qa["material_consistency"] in {"pass", "not_applicable"}, f"{field} material QA cannot fail when approved")


def validate_generated_record(root: Path, record: dict[str, Any], field: str, approved: bool) -> str | None:
    status = record.get("status")
    require(status in BOARD_STATUSES, f"{field}.status has invalid value: {status}")
    attempts = record.get("attempt_count")
    require(isinstance(attempts, int) and 0 <= attempts <= 3, f"{field}.attempt_count must be 0..3")
    terminal = record.get("terminal_generation_call")
    require(terminal in TERMINAL_VALUES, f"{field}.terminal_generation_call has invalid value: {terminal}")
    validate_native_4k(record, field)
    validate_qa(record, field, approved)

    generated_states = {
        "awaiting_post_generation_continuation",
        "qa_pending",
        "repair_required",
        "approved",
        "blocked_generation_quality",
    }
    asset_file = record.get("asset_file")
    if status in generated_states:
        require_asset(root, asset_file, f"{field}.asset_file")
        require_dimensions(record.get("actual_dimensions"), f"{field}.actual_dimensions")
        require_hash(record.get("generation_prompt_sha256"), f"{field}.generation_prompt_sha256")
    elif asset_file is not None:
        require_asset(root, asset_file, f"{field}.asset_file")
    return asset_file if isinstance(asset_file, str) else None


def validate_board(root: Path, record: Any, expected_id: str, expected_directory: str) -> str | None:
    field = f"boards[{expected_id}]"
    require(isinstance(record, dict), f"{field} must be an object")
    require(record.get("board_id") == expected_id, f"{field}.board_id mismatch")
    require(record.get("directory") == expected_directory, f"{field}.directory mismatch")
    relevance = record.get("relevance")
    source_gate = record.get("source_gate")
    status = record.get("status")
    require(relevance in RELEVANCE, f"{field}.relevance has invalid value: {relevance}")
    require(source_gate in SOURCE_GATES, f"{field}.source_gate has invalid value: {source_gate}")
    require(isinstance(record.get("source_gate_reasons"), list), f"{field}.source_gate_reasons must be a list")
    require(isinstance(record.get("evidence_ids"), list), f"{field}.evidence_ids must be a list")
    if status == "approved":
        require(source_gate == "approved", f"{field} approved board requires source_gate: approved")
        require(relevance != "not_applicable", f"{field} approved board cannot be not_applicable")
    if source_gate == "blocked":
        require(status not in {"generation_pending", "awaiting_post_generation_continuation", "qa_pending", "repair_required", "approved"}, f"{field} cannot generate or approve while source_gate is blocked")
    if relevance == "not_applicable":
        require(source_gate == "not_applicable" and status in {"planned", "not_applicable"}, f"{field} not_applicable relevance must remain non-generated")
    return validate_generated_record(root, record, field, status == "approved")


def prompt_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^## Asset: (.+?)\s*$", text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        asset = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        require(asset not in sections, f"duplicate 4K prompt section for {asset}")
        sections[asset] = text[start:end].strip()
    return sections


def validate_prompt_mappings(manifest: dict[str, Any], prompt_text: str, approved_assets: set[str]) -> None:
    mappings = manifest.get("four_k_prompts")
    require(isinstance(mappings, list), "four_k_prompts must be a list")
    sections = prompt_sections(prompt_text)
    mapped_assets: list[str] = []

    for index, mapping in enumerate(mappings):
        field = f"four_k_prompts[{index}]"
        require(isinstance(mapping, dict), f"{field} must be an object")
        asset = mapping.get("asset_file")
        require(isinstance(asset, str) and asset, f"{field}.asset_file is required")
        mapped_assets.append(asset)
        require(mapping.get("section_anchor") == f"Asset: {asset}", f"{field}.section_anchor mismatch")
        require(set(mapping.get("preserves", [])) == REQUIRED_PRESERVES, f"{field}.preserves must match the required identity set")
        allowed = set(mapping.get("allowed_changes", []))
        require(allowed and allowed <= ALLOWED_4K_CHANGES, f"{field}.allowed_changes contains an unsupported change")
        require(mapping.get("redesign_forbidden") is True, f"{field}.redesign_forbidden must be true")
        require(asset in sections, f"missing 4K prompt section for {asset}")
        section = sections[asset].casefold()
        for phrase in REQUIRED_PROMPT_PHRASES:
            require(phrase in section, f"4K prompt for {asset} is missing phrase: {phrase}")

    require(len(mapped_assets) == len(set(mapped_assets)), "four_k_prompts contains duplicate asset mappings")
    require(set(mapped_assets) == approved_assets, "approved assets and 4K prompt mappings are not one-to-one")
    require(set(sections) == approved_assets, "08_4K_Upscale_Prompts.md contains unmapped or missing asset sections")
    require(manifest.get("approved_asset_count") == len(approved_assets), "approved_asset_count mismatch")
    require(manifest.get("four_k_mapping_count") == len(mappings), "four_k_mapping_count mismatch")


def validate_package(root: Path) -> None:
    root = root.resolve()
    require(root.is_dir(), f"package directory does not exist: {root}")
    for directory in (*BOARD_DIRECTORIES.values(), FINAL_DIRECTORY):
        require((root / directory).is_dir(), f"missing required directory: {directory}")

    specification_path = root / SPECIFICATION_FILE
    require(specification_path.is_file(), f"missing {SPECIFICATION_FILE}")
    specification = specification_path.read_text(encoding="utf-8")
    for heading in REQUIRED_SPEC_HEADINGS:
        require(heading in specification, f"specification missing heading: {heading}")

    manifest = load_json(root / MANIFEST_FILE)
    require(manifest.get("schema_version") == SCHEMA_VERSION, "schema_version mismatch")
    require(manifest.get("identity_specification") == SPECIFICATION_FILE, "identity_specification path mismatch")
    package_status = manifest.get("package_status")
    require(package_status in PACKAGE_STATUSES, f"invalid package_status: {package_status}")
    require(manifest.get("production_approval_status") in PRODUCTION_APPROVAL, "invalid production_approval_status")
    require(isinstance(manifest.get("unresolved_hard_conflicts"), list), "unresolved_hard_conflicts must be a list")
    frozen_status = package_status not in {"initialized"}
    require_hash(manifest.get("identity_specification_sha256"), "identity_specification_sha256", allow_none=not frozen_status)
    require_hash(manifest.get("source_bundle_sha256"), "source_bundle_sha256", allow_none=not frozen_status)

    boards = manifest.get("boards")
    require(isinstance(boards, list) and len(boards) == len(BOARD_DIRECTORIES), "boards must contain exactly five records")
    by_id = {record.get("board_id"): record for record in boards if isinstance(record, dict)}
    require(set(by_id) == set(BOARD_DIRECTORIES), "boards must contain the five canonical board IDs exactly once")

    approved_assets: set[str] = set()
    approved_board_ids: set[str] = set()
    active_states: list[str] = []
    for board_id, directory in BOARD_DIRECTORIES.items():
        record = by_id[board_id]
        asset = validate_board(root, record, board_id, directory)
        if record.get("status") == "approved":
            require(asset is not None, f"approved {board_id} lacks asset_file")
            approved_assets.add(asset)
            approved_board_ids.add(board_id)
        if record.get("status") in {"generation_pending", "awaiting_post_generation_continuation", "qa_pending", "repair_required"}:
            active_states.append(board_id)

    final = manifest.get("final_board")
    require(isinstance(final, dict), "final_board must be an object")
    require(final.get("board_id") == FINAL_BOARD_ID, "final_board.board_id mismatch")
    require(final.get("directory") == FINAL_DIRECTORY, "final_board.directory mismatch")
    final_status = final.get("status")
    final_asset = validate_generated_record(root, final, "final_board", final_status == "approved")
    source_board_ids = final.get("source_board_ids")
    require(isinstance(source_board_ids, list), "final_board.source_board_ids must be a list")
    require(set(source_board_ids) <= approved_board_ids, "final_board references a non-approved source board")
    if final_status == "approved":
        require("geometry_lock" in approved_board_ids, "approved final board requires approved Geometry Lock")
        for record in boards:
            if record["relevance"] == "required":
                require(record["status"] == "approved", f"approved final board requires approved required board: {record['board_id']}")
        require(not manifest["unresolved_hard_conflicts"], "approved final board cannot retain hard identity conflicts")
        require(final_asset is not None, "approved final board lacks asset_file")
        approved_assets.add(final_asset)
    if final_status in {"generation_pending", "awaiting_post_generation_continuation", "qa_pending", "repair_required"}:
        active_states.append(FINAL_BOARD_ID)

    require(manifest.get("four_k_prompt_file") == PROMPT_FILE, "four_k_prompt_file path mismatch")
    prompt_path = root / PROMPT_FILE
    require(prompt_path.is_file(), f"missing {PROMPT_FILE}")
    prompt_text = prompt_path.read_text(encoding="utf-8")
    validate_prompt_mappings(manifest, prompt_text, approved_assets)

    if package_status == "complete":
        require(not active_states, f"complete package has unfinished generation states: {', '.join(active_states)}")
        require(final_status == "approved", "complete package requires an approved final board")
        require("geometry_lock" in approved_board_ids, "complete package requires approved Geometry Lock")
        require(not manifest["unresolved_hard_conflicts"], "complete package cannot retain hard identity conflicts")
    if package_status == "partial_approved":
        require(bool(approved_assets), "partial_approved requires at least one approved asset")
        require(final_status != "approved", "partial_approved cannot include an approved final board")
    if package_status in {"blocked_source_insufficient", "blocked_identity_conflict", "blocked_generation_runtime"}:
        require(final_status != "approved", f"{package_status} cannot include an approved final board")
    if package_status == "four_k_mapping_failed":
        require(set(mapping.get("asset_file") for mapping in manifest.get("four_k_prompts", []) if isinstance(mapping, dict)) != approved_assets, "four_k_mapping_failed must reflect a mapping mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a complex product identity asset package.")
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    try:
        validate_package(args.package)
    except (ValidationFailure, OSError, UnicodeDecodeError) as exc:
        print(f"asset package validation: FAILED\n  - {exc}", file=sys.stderr)
        return 1
    print(f"asset package validation: OK ({args.package.resolve()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
