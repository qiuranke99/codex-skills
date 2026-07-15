#!/usr/bin/env python3
"""Compile a source-cited packaging copy ledger into a deterministic prompt block."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


SHA_RE = re.compile(r"[0-9a-f]{64}")
STATUSES = {"approved_exact", "candidate", "unresolved"}
EVIDENCE = {"source_visual", "approved_artwork", "ocr_only", "not_readable"}


class CopyContractError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_ledger(path: Path) -> tuple[dict[str, Any], bytes]:
    if not path.is_file():
        raise CopyContractError("blocked_copy_ledger_missing", f"copy ledger missing: {path}")
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise CopyContractError("blocked_copy_ledger_invalid", "ledger must be UTF-8/LF without BOM")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CopyContractError("blocked_copy_ledger_invalid", str(exc)) from exc
    if not isinstance(value, dict) or value.get("schema_version") != "packaging_copy_ledger.v1":
        raise CopyContractError("blocked_copy_ledger_invalid", "unexpected copy-ledger schema")
    return value, data


def validate_and_normalize(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    if ledger.get("ocr_status") not in {"not_run", "candidates_only", "reviewed"}:
        raise CopyContractError("blocked_copy_ledger_invalid", "invalid ocr_status")
    regions = ledger.get("regions")
    if not isinstance(regions, list) or not regions:
        raise CopyContractError("blocked_copy_ledger_invalid", "regions must be a non-empty array")
    normalized: list[dict[str, Any]] = []
    region_ids: set[str] = set()
    line_ids: set[str] = set()
    for r_index, region in enumerate(regions, 1):
        if not isinstance(region, dict):
            raise CopyContractError("blocked_copy_ledger_invalid", f"region {r_index} must be an object")
        region_id = region.get("region_id")
        if not isinstance(region_id, str) or not region_id or region_id in region_ids:
            raise CopyContractError("blocked_copy_ledger_invalid", "region_id values must be unique")
        region_ids.add(region_id)
        source_alias = region.get("source_alias")
        source_sha = region.get("source_sha256")
        if not isinstance(source_alias, str) or not source_alias or not isinstance(source_sha, str) or not SHA_RE.fullmatch(source_sha):
            raise CopyContractError("blocked_copy_ledger_source", f"{region_id} lacks a source alias and SHA-256")
        layout = region.get("layout")
        required_layout = {"orientation", "reading_order", "alignment", "column_order"}
        if not isinstance(layout, dict) or any(not isinstance(layout.get(k), str) or not layout.get(k) for k in required_layout):
            raise CopyContractError("blocked_copy_ledger_layout", f"{region_id} lacks explicit layout/order fields")
        lines = region.get("lines")
        if not isinstance(lines, list) or not lines:
            raise CopyContractError("blocked_copy_ledger_invalid", f"{region_id} has no copy lines")
        observed_orders: list[int] = []
        normalized_lines: list[dict[str, Any]] = []
        for l_index, line in enumerate(lines, 1):
            if not isinstance(line, dict):
                raise CopyContractError("blocked_copy_ledger_invalid", f"{region_id} line {l_index} is invalid")
            line_id = line.get("line_id")
            order = line.get("order")
            text = line.get("text")
            status = line.get("status")
            evidence = line.get("evidence")
            language = line.get("language")
            if not isinstance(line_id, str) or not line_id or line_id in line_ids:
                raise CopyContractError("blocked_copy_ledger_invalid", "line_id values must be globally unique")
            if not isinstance(order, int) or order < 1 or not isinstance(text, str) or not text.strip() or "\r" in text or "\n" in text:
                raise CopyContractError("blocked_copy_ledger_invalid", f"{line_id} must be one non-empty ordered line")
            if status not in STATUSES or evidence not in EVIDENCE or not isinstance(language, str) or not language:
                raise CopyContractError("blocked_copy_ledger_invalid", f"{line_id} has invalid status/evidence/language")
            if status == "approved_exact" and evidence not in {"source_visual", "approved_artwork"}:
                raise CopyContractError(
                    "blocked_copy_ledger_unverified_exact",
                    f"{line_id} cannot be approved_exact from OCR-only or unreadable evidence",
                )
            line_ids.add(line_id)
            observed_orders.append(order)
            normalized_lines.append(line)
        if sorted(observed_orders) != list(range(1, len(lines) + 1)):
            raise CopyContractError("blocked_copy_ledger_order", f"{region_id} line order must be contiguous from 1")
        normalized.append({**region, "lines": sorted(normalized_lines, key=lambda row: row["order"])})
    return normalized


def compile_block(ledger: dict[str, Any], ledger_bytes: bytes) -> tuple[str, dict[str, Any]]:
    regions = validate_and_normalize(ledger)
    ledger_sha = sha256_bytes(ledger_bytes)
    exact_count = sum(line["status"] == "approved_exact" for region in regions for line in region["lines"])
    candidate_count = sum(line["status"] != "approved_exact" for region in regions for line in region["lines"])
    lines = [
        "BEGIN PACKAGING COPY CONTRACT",
        f"Ledger SHA-256: {ledger_sha}",
        "Render only APPROVED EXACT strings as readable product copy. Preserve spelling, case, punctuation, units, line order, column order, orientation, and alignment exactly.",
        "CANDIDATE/UNRESOLVED entries are audit evidence only: do not typeset, autocomplete, translate, paraphrase, or invent them.",
    ]
    for region in regions:
        layout = region["layout"]
        lines.extend(
            [
                "",
                f"REGION {region['region_id']}",
                f"SOURCE {region['source_alias']} sha256={region['source_sha256']}",
                (
                    "FORMAT "
                    f"orientation={layout['orientation']}; reading_order={layout['reading_order']}; "
                    f"column_order={layout['column_order']}; alignment={layout['alignment']}"
                ),
                "APPROVED EXACT — render in this order:",
            ]
        )
        approved = [line for line in region["lines"] if line["status"] == "approved_exact"]
        if approved:
            lines.extend(f"[{line['line_id']}] {json.dumps(line['text'], ensure_ascii=False)}" for line in approved)
        else:
            lines.append("[none]")
        lines.append("CANDIDATE/UNRESOLVED — do not render as exact:")
        uncertain = [line for line in region["lines"] if line["status"] != "approved_exact"]
        if uncertain:
            lines.extend(
                f"[{line['line_id']}] status={line['status']} candidate={json.dumps(line['text'], ensure_ascii=False)}"
                for line in uncertain
            )
        else:
            lines.append("[none]")
    lines.extend(
        [
            "",
            "PIXEL AUTHORITY",
            "Prompt inclusion is not proof of correct pixels. Any region claimed readable/exact in the accepted board must be verified against the ledger and source-backed by an approved source crop or artwork reprojection.",
            "No invented characters, pseudo-Chinese, pseudo-Latin, fake barcode digits, fake QR modules, or substituted punctuation anywhere on the product.",
            "END PACKAGING COPY CONTRACT",
        ]
    )
    block = "\n".join(lines) + "\n"
    receipt = {
        "schema_version": "packaging_copy_prompt_receipt.v1",
        "ledger_sha256": ledger_sha,
        "copy_block_sha256": sha256_bytes(block.encode("utf-8")),
        "region_count": len(regions),
        "line_count": exact_count + candidate_count,
        "approved_exact_count": exact_count,
        "candidate_or_unresolved_count": candidate_count,
        "all_lines_emitted": True,
        "order_preserved": True,
    }
    return block, receipt


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    ledger, ledger_bytes = load_ledger(args.ledger.expanduser().resolve())
    block, receipt = compile_block(ledger, ledger_bytes)
    write_text(args.output.expanduser().resolve(), block)
    write_text(args.receipt.expanduser().resolve(), json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"ok": True, **receipt}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CopyContractError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
