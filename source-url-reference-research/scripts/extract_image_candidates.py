"""Extract public image candidate URLs from verified source pages.

This tool does not download images. It produces candidate records for manual
review or for `download_reference_images.py`.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36"
)
META_IMAGE_RE = re.compile(
    r"<meta\s+[^>]*(?:property|name)=[\"'](?P<kind>og:image|twitter:image|twitter:image:src)[\"'][^>]*>",
    re.IGNORECASE,
)
CONTENT_RE = re.compile(r"content=[\"']([^\"']+)[\"']", re.IGNORECASE)
IMG_RE = re.compile(r"<img\s+[^>]*(?:src|data-src)=[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)
WIDTH_RE = re.compile(r"\bwidth=[\"']?(\d{2,5})", re.IGNORECASE)
HEIGHT_RE = re.compile(r"\bheight=[\"']?(\d{2,5})", re.IGNORECASE)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _request_html(url: str, timeout: float) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "text/html,*/*;q=0.8"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type.lower():
            return ""
        return response.read(2_000_000).decode("utf-8", errors="ignore")


def _dimension(tag: str, pattern: re.Pattern) -> int:
    match = pattern.search(tag)
    return int(match.group(1)) if match else 0


def _append_unique(records: list[dict], seen: set[str], record: dict) -> None:
    image_url = record.get("image_url", "")
    if image_url and image_url not in seen:
        seen.add(image_url)
        records.append(record)


def extract_page_image_candidates(
    record: dict,
    timeout: float = 10,
    min_width: int = 0,
) -> list[dict]:
    """Return image candidate records extracted from one public HTML source page."""

    source_url = (record.get("source_url") or record.get("final_url") or "").strip()
    if not source_url:
        return []

    try:
        body = _request_html(source_url, timeout=timeout)
    except (urllib.error.URLError, TimeoutError, socket.timeout, ValueError):
        return []
    if not body:
        return []

    checked_at = _now_iso()
    candidates: list[dict] = []
    seen: set[str] = set()
    rank = str(record.get("rank") or "")
    title = record.get("title", "")
    visual_mechanism = record.get("visual_mechanism", "")

    for meta_tag in META_IMAGE_RE.finditer(body):
        tag = meta_tag.group(0)
        match = CONTENT_RE.search(tag)
        if not match:
            continue
        image_url = urllib.parse.urljoin(source_url, html.unescape(match.group(1)))
        _append_unique(
            candidates,
            seen,
            {
                "rank": rank,
                "title": title,
                "source_url": source_url,
                "image_url": image_url,
                "visual_mechanism": visual_mechanism,
                "capture_method": "og_image" if "og:image" in tag.lower() else "twitter_image",
                "width": "",
                "height": "",
                "checked_at": checked_at,
            },
        )

    for match in IMG_RE.finditer(body):
        tag = match.group(0)
        width = _dimension(tag, WIDTH_RE)
        height = _dimension(tag, HEIGHT_RE)
        if min_width and width and width < min_width:
            continue
        image_url = urllib.parse.urljoin(source_url, html.unescape(match.group(1)))
        _append_unique(
            candidates,
            seen,
            {
                "rank": rank,
                "title": title,
                "source_url": source_url,
                "image_url": image_url,
                "visual_mechanism": visual_mechanism,
                "capture_method": "html_img",
                "width": width or "",
                "height": height or "",
                "checked_at": checked_at,
            },
        )
    return candidates


def _read_records(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        raise ValueError("JSON input must be a list of records.")
    if suffix == ".jsonl":
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                if isinstance(item, dict):
                    records.append(item)
        return records
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _write_records(records: list[dict], output_path: str | None, output_format: str) -> None:
    if output_format == "jsonl":
        lines = [json.dumps(record, ensure_ascii=False) for record in records]
        payload = "\n".join(lines) + ("\n" if lines else "")
        if output_path:
            Path(output_path).write_text(payload, encoding="utf-8")
        else:
            sys.stdout.write(payload)
        return

    if output_format == "csv":
        fieldnames = [
            "rank",
            "title",
            "source_url",
            "image_url",
            "visual_mechanism",
            "capture_method",
            "width",
            "height",
            "checked_at",
        ]
        handle = open(output_path, "w", newline="", encoding="utf-8") if output_path else sys.stdout
        try:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)
        finally:
            if output_path:
                handle.close()
        return

    payload = json.dumps(records, ensure_ascii=False, indent=2)
    if output_path:
        Path(output_path).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


def extract_records(records: Iterable[dict], timeout: float = 10, min_width: int = 0) -> list[dict]:
    candidates: list[dict] = []
    for record in records:
        candidates.extend(extract_page_image_candidates(record, timeout=timeout, min_width=min_width))
    return candidates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract image candidate URLs from source pages.")
    parser.add_argument("--input", required=True, help="CSV, JSON, or JSONL verified source records.")
    parser.add_argument("--output", help="Write candidate records to this path.")
    parser.add_argument("--format", choices=("json", "jsonl", "csv"), default="jsonl")
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--min-width", type=int, default=0)
    parser.add_argument("--no-download", action="store_true", help="Documented safety flag; this tool never downloads.")
    args = parser.parse_args(argv)

    candidates = extract_records(_read_records(Path(args.input)), timeout=args.timeout, min_width=args.min_width)
    _write_records(candidates, args.output, args.format)
    return 0 if candidates else 1


if __name__ == "__main__":
    raise SystemExit(main())
