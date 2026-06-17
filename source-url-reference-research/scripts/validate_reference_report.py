"""Validate final source-url reference reports against completion gates.

The main gate this enforces: an image_reference report must include image pack
evidence unless the user explicitly requested a links-only/no-download result.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


IMAGE_ROUTE_RE = re.compile(r"\broute\s*[:：]\s*`?image_reference`?", re.IGNORECASE)
PACK_PATH_RE = re.compile(r"\bimage_pack_path\s*[:：]\s*`?([^`\n]+)`?", re.IGNORECASE)
PACK_SUMMARY_RE = re.compile(r"\bimage_pack_summary\s*[:：]", re.IGNORECASE)
LINKS_ONLY_RE = re.compile(r"\b(links-only|link-only|no-download|no downloads)\b", re.IGNORECASE)
NO_DOWNLOAD_PATTERNS = (
    "未下载媒体",
    "未下载图片",
    "未建本地参考包",
    "未创建本地 image pack",
    "未创建本地参考包",
    "no media downloads",
    "without downloading media",
    "did not download",
    "no image pack",
)


def _normalise(text: str) -> str:
    return " ".join(text.lower().split())


def validate_report(path: str | Path, allow_links_only: bool = False, require_existing_pack: bool = False) -> dict:
    report_path = Path(path)
    text = report_path.read_text(encoding="utf-8")
    normalised = _normalise(text)
    is_image_route = bool(IMAGE_ROUTE_RE.search(text))
    declares_links_only = bool(LINKS_ONLY_RE.search(text))
    declares_no_download = any(pattern.lower() in normalised for pattern in NO_DOWNLOAD_PATTERNS)
    errors: list[str] = []

    if is_image_route:
        pack_path_match = PACK_PATH_RE.search(text)
        has_pack_summary = bool(PACK_SUMMARY_RE.search(text))
        links_only_allowed = allow_links_only and declares_links_only
        if declares_no_download:
            errors.append("declares_no_download")
        if declares_links_only and not links_only_allowed:
            errors.append("declares_links_only_without_explicit_override")
        if not links_only_allowed:
            if not pack_path_match:
                errors.append("missing_image_pack_path")
            if not has_pack_summary:
                errors.append("missing_image_pack_summary")
        if pack_path_match and require_existing_pack and not links_only_allowed:
            raw_pack_path = pack_path_match.group(1).strip()
            pack_path = Path(raw_pack_path)
            if not pack_path.is_absolute():
                pack_path = (report_path.parent / pack_path).resolve()
            required_files = ["manifest.json", "manifest.csv", "pack_summary.json", "sources.jsonl"]
            missing = [name for name in required_files if not (pack_path / name).exists()]
            if missing:
                errors.append("missing_pack_files:" + ",".join(missing))

    return {
        "ok": not errors,
        "route": "image_reference" if is_image_route else "other_or_unknown",
        "errors": errors,
        "report_path": str(report_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a final source-url reference report.")
    parser.add_argument("report", help="Markdown report path.")
    parser.add_argument("--allow-links-only", action="store_true", help="Allow explicit links-only/no-download reports.")
    parser.add_argument("--require-existing-pack", action="store_true", help="Require image_pack_path files to exist.")
    args = parser.parse_args(argv)

    result = validate_report(
        args.report,
        allow_links_only=args.allow_links_only,
        require_existing_pack=args.require_existing_pack,
    )
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
