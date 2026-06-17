#!/usr/bin/env python3
"""Validate TVC reference-video research reports.

The validator is intentionally narrow. It catches the failures that make TVC
reference research misleading: unverified leads in the final ranked list,
showreels/compilations presented as single-work references, missing source URLs,
and missing search audit evidence.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ALLOWED_FINAL_STATUSES = {
    "verified",
    "browser_verified",
    "browser_verified_partial",
    "browser_verified_login_context",
    "probable",
}
FORBIDDEN_FINAL_STATUSES = {
    "unconfirmed_lead",
    "rejected",
    "inaccessible",
    "out_of_scope",
}
FORBIDDEN_FINAL_VIDEO_KINDS = {
    "showreel",
    "reel",
    "compilation",
    "bts",
    "making_of",
    "tutorial",
    "review",
    "case_study",
}
REQUIRED_JSON_AUDIT_FIELDS = {
    "route_decision",
    "query_lanes",
    "queries_tried",
    "platforms_checked",
    "hard_exclusions",
    "verification_methods_used",
    "counts",
    "next_searches",
}
REQUIRED_REFERENCE_FIELDS = {
    "rank",
    "candidate_status",
    "title",
    "source_url",
    "video_kind",
    "brief_fit",
    "reference_role",
    "visual_mechanism",
    "temporal_mechanism",
    "shoot_takeaway",
    "do_not_copy",
    "risks_or_limits",
    "confidence",
}


def normalize(value: Any) -> str:
    return str(value or "").strip().lower()


def is_url(value: Any) -> bool:
    return str(value or "").strip().startswith(("http://", "https://"))


def validate_json_report(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    audit = data.get("audit")
    references = data.get("references")

    if not isinstance(audit, dict):
        errors.append("JSON report must include an audit object.")
    else:
        missing_audit = sorted(REQUIRED_JSON_AUDIT_FIELDS - set(audit))
        if missing_audit:
            errors.append(f"Audit is missing required fields: {', '.join(missing_audit)}.")
        for field in ("query_lanes", "queries_tried", "platforms_checked", "hard_exclusions", "next_searches"):
            value = audit.get(field)
            if isinstance(value, list) and not value:
                errors.append(f"Audit field '{field}' must not be empty.")

    if not isinstance(references, list) or not references:
        errors.append("JSON report must include at least one ranked reference.")
        return errors

    for index, row in enumerate(references, start=1):
        if not isinstance(row, dict):
            errors.append(f"Reference row {index} must be an object.")
            continue

        missing = sorted(REQUIRED_REFERENCE_FIELDS - set(row))
        if missing:
            errors.append(f"Reference row {index} is missing fields: {', '.join(missing)}.")

        status = normalize(row.get("candidate_status") or row.get("confidence"))
        if status in FORBIDDEN_FINAL_STATUSES:
            errors.append(f"Reference row {index} has forbidden final status '{status}'.")
        elif status not in ALLOWED_FINAL_STATUSES:
            errors.append(f"Reference row {index} has unsupported final status '{status}'.")

        video_kind = normalize(row.get("video_kind"))
        if video_kind in FORBIDDEN_FINAL_VIDEO_KINDS:
            errors.append(f"Reference row {index} uses forbidden final video_kind '{video_kind}'.")

        source_url = row.get("source_url")
        if not is_url(source_url):
            errors.append(f"Reference row {index} must include an http(s) source_url.")

        for field in ("reference_role", "visual_mechanism", "temporal_mechanism", "shoot_takeaway", "do_not_copy"):
            if not str(row.get(field, "")).strip():
                errors.append(f"Reference row {index} field '{field}' must not be empty.")

    return errors


def section_exists(markdown: str, name: str) -> bool:
    pattern = rf"(?im)^#+\s*{re.escape(name)}\s*$"
    return bool(re.search(pattern, markdown))


def extract_ranked_table(markdown: str) -> tuple[list[str], list[list[str]]]:
    lines = markdown.splitlines()
    in_section = False
    table_lines: list[str] = []

    for line in lines:
        if re.match(r"(?i)^#+\s*ranked\s+(tvc\s+)?references", line.strip()):
            in_section = True
            continue
        if in_section and line.startswith("#"):
            break
        if in_section and line.strip().startswith("|"):
            table_lines.append(line.strip())

    if len(table_lines) < 3:
        return [], []

    header = [cell.strip().lower().replace(" ", "_") for cell in table_lines[0].strip("|").split("|")]
    rows: list[list[str]] = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if any(cells):
            rows.append(cells)
    return header, rows


def find_column(header: list[str], *candidates: str) -> int | None:
    normalized_candidates = {candidate.lower().replace(" ", "_") for candidate in candidates}
    for index, name in enumerate(header):
        if name in normalized_candidates:
            return index
    return None


def validate_markdown_report(markdown: str) -> list[str]:
    errors: list[str] = []

    if not section_exists(markdown, "Search Audit"):
        errors.append("Markdown report must include a 'Search Audit' section.")

    header, rows = extract_ranked_table(markdown)
    if not header or not rows:
        errors.append("Markdown report must include a non-empty 'Ranked TVC References' table.")
        return errors

    status_col = find_column(header, "status", "candidate_status", "confidence")
    source_col = find_column(header, "source_url", "source")
    role_col = find_column(header, "reference_role", "role")
    borrow_col = find_column(header, "what_to_borrow", "shoot_takeaway")
    avoid_col = find_column(header, "do_not_copy", "avoid")
    risk_col = find_column(header, "risk", "risks_or_limits")

    required_columns = {
        "status": status_col,
        "source_url/source": source_col,
        "reference_role/role": role_col,
        "what_to_borrow/shoot_takeaway": borrow_col,
        "do_not_copy/avoid": avoid_col,
        "risk/risks_or_limits": risk_col,
    }
    for label, index in required_columns.items():
        if index is None:
            errors.append(f"Ranked table is missing column '{label}'.")

    for row_index, row in enumerate(rows, start=1):
        if status_col is not None and status_col < len(row):
            status = normalize(row[status_col])
            if status in FORBIDDEN_FINAL_STATUSES:
                errors.append(f"Ranked table row {row_index} has forbidden final status '{status}'.")
        if source_col is not None and source_col < len(row) and not is_url(row[source_col]):
            errors.append(f"Ranked table row {row_index} must include an http(s) source URL.")

    return errors


def detect_format(path: Path, forced: str) -> str:
    if forced != "auto":
        return forced
    if path.suffix.lower() == ".json":
        return "json"
    return "markdown"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a TVC reference-video research report.")
    parser.add_argument("report_path", help="Path to a Markdown or JSON report.")
    parser.add_argument("--format", choices=("auto", "json", "markdown"), default="auto")
    args = parser.parse_args()

    path = Path(args.report_path)
    if not path.exists():
        print(f"ERROR: Report not found: {path}")
        return 1

    fmt = detect_format(path, args.format)
    content = path.read_text(encoding="utf-8")

    try:
        if fmt == "json":
            errors = validate_json_report(json.loads(content))
        else:
            errors = validate_markdown_report(content)
    except json.JSONDecodeError as exc:
        errors = [f"Invalid JSON: {exc}"]

    if errors:
        print("FAILED: TVC reference report validation found issues:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("OK: TVC reference report validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
