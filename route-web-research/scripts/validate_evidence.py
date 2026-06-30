#!/usr/bin/env python3
"""Validate route-web-research evidence JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


VALID_SOURCE_TYPES = {
    "official",
    "primary",
    "creator",
    "manufacturer",
    "paper",
    "repo",
    "standards",
    "press",
    "docs",
    "repost",
    "search_result",
    "unknown",
}
VALID_STATUS = {
    "verified",
    "partially_verified",
    "unconfirmed_lead",
    "access_restricted",
    "contradicted",
    "failed_fetch",
}


def is_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    return parsed.scheme in {"http", "https", "file"} and bool(parsed.netloc or parsed.scheme == "file")


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root must be a JSON object"]

    run = data.get("run")
    if not isinstance(run, dict):
        errors.append("run object is required")
    elif not run.get("task"):
        errors.append("run.task is required")

    route = data.get("route")
    if not isinstance(route, dict):
        errors.append("route object is required")
    else:
        if not route.get("selected_tools"):
            errors.append("route.selected_tools must not be empty")

    sources = data.get("sources")
    if not isinstance(sources, list):
        errors.append("sources must be a list")
        return errors

    seen_ids = set()
    seen_urls = set()
    for index, source in enumerate(sources):
        prefix = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be an object")
            continue

        sid = source.get("source_id")
        if not sid:
            errors.append(f"{prefix}.source_id is required")
        elif sid in seen_ids:
            errors.append(f"{prefix}.source_id is duplicated: {sid}")
        else:
            seen_ids.add(sid)

        url = source.get("source_url")
        if not url or not is_url(url):
            errors.append(f"{prefix}.source_url must be an http(s) or file URL")
        elif url in seen_urls:
            errors.append(f"{prefix}.source_url is duplicated: {url}")
        else:
            seen_urls.add(url)

        stype = source.get("source_type")
        if stype not in VALID_SOURCE_TYPES:
            errors.append(f"{prefix}.source_type must be one of {sorted(VALID_SOURCE_TYPES)}")

        status = source.get("verification_status")
        if status not in VALID_STATUS:
            errors.append(f"{prefix}.verification_status must be one of {sorted(VALID_STATUS)}")

        if stype in {"repost", "search_result", "unknown"} and status == "verified":
            errors.append(f"{prefix} weak source_type must not be marked as verified")

        if not source.get("discovered_via"):
            errors.append(f"{prefix}.discovered_via is required")
        if not source.get("fetched_via"):
            errors.append(f"{prefix}.fetched_via is required")

        claims = source.get("claims", [])
        if claims is None:
            claims = []
        if not isinstance(claims, list):
            errors.append(f"{prefix}.claims must be a list")
            continue
        for cindex, claim in enumerate(claims):
            cp = f"{prefix}.claims[{cindex}]"
            if not isinstance(claim, dict):
                errors.append(f"{cp} must be an object")
                continue
            if not claim.get("claim"):
                errors.append(f"{cp}.claim is required")
            if not claim.get("evidence_snippet"):
                errors.append(f"{cp}.evidence_snippet is required")
            if claim.get("confidence") not in {"high", "medium", "low"}:
                errors.append(f"{cp}.confidence must be high, medium, or low")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate route-web-research evidence JSON")
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        data = load_json(args.path)
    except Exception as exc:
        print(f"Failed to load JSON: {exc}", file=sys.stderr)
        return 2

    errors = validate(data)
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors}, indent=2, ensure_ascii=False))
    elif errors:
        print("Evidence validation failed:")
        for error in errors:
            print(f"- {error}")
    else:
        print("Evidence is valid.")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
