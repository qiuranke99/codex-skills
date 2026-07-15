#!/usr/bin/env python3
"""Validate ledger-to-prompt coverage and post-generation packaging-copy QA."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from compile_copy_prompt import CopyContractError, compile_block, load_ledger


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path, code: str) -> tuple[dict[str, Any], bytes]:
    if not path.is_file():
        raise CopyContractError(code, f"missing JSON artifact: {path}")
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise CopyContractError(code, f"JSON must be UTF-8/LF without BOM: {path}")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CopyContractError(code, str(exc)) from exc
    if not isinstance(value, dict):
        raise CopyContractError(code, f"JSON must be an object: {path}")
    return value, data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--block", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--qa", required=True, type=Path)
    parser.add_argument("--copy-authority", required=True, choices=["video_reference", "exact_copy_evidence"])
    args = parser.parse_args()

    ledger, ledger_bytes = load_ledger(args.ledger.expanduser().resolve())
    expected_block, expected_receipt = compile_block(ledger, ledger_bytes)
    block_bytes = args.block.expanduser().resolve().read_bytes()
    if block_bytes != expected_block.encode("utf-8"):
        raise CopyContractError("blocked_copy_block_mismatch", "copy block is not the deterministic ledger compilation")
    receipt, _ = load_json(args.receipt.expanduser().resolve(), "blocked_copy_receipt_invalid")
    if receipt != expected_receipt:
        raise CopyContractError("blocked_copy_receipt_invalid", "copy receipt does not bind ledger and block")
    prompt_bytes = args.prompt.expanduser().resolve().read_bytes()
    try:
        prompt_text = prompt_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CopyContractError("blocked_copy_prompt_invalid", str(exc)) from exc
    if expected_block.rstrip("\n") not in prompt_text:
        raise CopyContractError("blocked_copy_prompt_coverage", "final prompt must embed the complete copy block verbatim")

    qa, _ = load_json(args.qa.expanduser().resolve(), "blocked_copy_qa_invalid")
    if qa.get("schema_version") != "packaging_copy_qa.v1":
        raise CopyContractError("blocked_copy_qa_invalid", "unexpected copy-QA schema")
    if qa.get("copy_ledger_sha256") != sha256_bytes(ledger_bytes) or qa.get("copy_prompt_block_sha256") != sha256_bytes(block_bytes):
        raise CopyContractError("blocked_copy_qa_binding", "copy QA does not bind ledger and block")
    if qa.get("overall_status") != "passed" or qa.get("board_wide_invented_or_corrupted_visible_copy") is not False:
        raise CopyContractError("blocked_visible_copy_corruption", "accepted board contains or may contain invented/corrupted visible copy")
    board_regions = qa.get("board_regions")
    if not isinstance(board_regions, list) or not board_regions:
        raise CopyContractError("blocked_copy_qa_invalid", "board_regions must be a non-empty array")
    covered: set[str] = set()
    source_backed_covered: set[str] = set()
    for row in board_regions:
        if not isinstance(row, dict):
            raise CopyContractError("blocked_copy_qa_invalid", "board region QA entry is invalid")
        if row.get("visual_status") not in {"exact_match", "source_reprojected", "no_readable_copy_present"}:
            raise CopyContractError("blocked_visible_copy_corruption", f"unacceptable copy status in {row.get('board_region_id')}")
        if row.get("order_match") not in {"pass", "not_applicable"} or row.get("mismatch_line_ids") != []:
            raise CopyContractError("blocked_copy_qa_mismatch", f"copy mismatch in {row.get('board_region_id')}")
        region_ids = row.get("covered_copy_region_ids")
        if not isinstance(region_ids, list):
            raise CopyContractError("blocked_copy_qa_invalid", "covered_copy_region_ids must be an array")
        if region_ids and row.get("visual_status") not in {"exact_match", "source_reprojected"}:
            raise CopyContractError("blocked_copy_qa_mismatch", "covered copy must be exact or source-reprojected")
        if row.get("visual_status") == "source_reprojected" and row.get("source_backed_pixels") is not True:
            raise CopyContractError("blocked_copy_qa_binding", "source_reprojected status requires source_backed_pixels=true")
        covered.update(region_ids)
        if row.get("source_backed_pixels") is True and row.get("visual_status") in {"exact_match", "source_reprojected"}:
            source_backed_covered.update(region_ids)

    approved_regions = {
        region["region_id"]
        for region in ledger["regions"]
        if any(line.get("status") == "approved_exact" for line in region.get("lines", []))
    }
    if not approved_regions.issubset(covered):
        missing = sorted(approved_regions - covered)
        raise CopyContractError("blocked_copy_qa_coverage", f"approved copy regions lack accepted pixel evidence: {missing}")
    if args.copy_authority == "exact_copy_evidence":
        all_lines = [line for region in ledger["regions"] for line in region.get("lines", [])]
        if ledger.get("ocr_status") != "reviewed" or any(line.get("status") != "approved_exact" for line in all_lines):
            raise CopyContractError("blocked_exact_copy_authority", "exact authority requires reviewed OCR and no uncertain lines")
        if not approved_regions.issubset(source_backed_covered):
            missing = sorted(approved_regions - source_backed_covered)
            raise CopyContractError(
                "blocked_exact_copy_authority",
                f"exact authority requires source/artwork-backed final pixels for every approved region: {missing}",
            )

    result = {
        "ok": True,
        "contract": "packaging_copy_contract_validation.v1",
        "approved_region_count": len(approved_regions),
        "covered_approved_region_count": len(approved_regions),
        "prompt_coverage": "complete",
        "visible_copy_corruption": False,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CopyContractError, OSError) as exc:
        code = exc.code if isinstance(exc, CopyContractError) else "blocked_copy_artifact_io"
        print(json.dumps({"ok": False, "error_code": code, "detail": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
