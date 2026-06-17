"""Build an image reference pack from verified source page records.

This is the one-command path for image_reference routes. It writes source
records, extracts public image candidates, downloads what is reachable, and
keeps failed/skipped rows in the manifest instead of silently dropping them.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Iterable

try:
    from .download_reference_images import download_records
    from .extract_image_candidates import extract_records
except ImportError:  # Allows `python scripts/build_image_reference_pack.py`.
    from download_reference_images import download_records
    from extract_image_candidates import extract_records


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _write_jsonl(path: Path, records: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, ensure_ascii=False) for record in records]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _direct_image_candidates(records: Iterable[dict]) -> list[dict]:
    candidates = []
    for record in records:
        image_url = (record.get("image_url") or record.get("asset_url") or "").strip()
        if not image_url:
            continue
        candidates.append(
            {
                **record,
                "image_url": image_url,
                "capture_method": record.get("capture_method", "direct_url"),
                "source_page_verified": record.get("source_page_verified", "partial"),
            }
        )
    return candidates


def _dedupe_by_image_url(records: Iterable[dict]) -> list[dict]:
    deduped = []
    seen = set()
    for record in records:
        image_url = record.get("image_url", "")
        if image_url and image_url not in seen:
            seen.add(image_url)
            deduped.append(record)
    return deduped


def _append_missing_source_placeholders(source_records: Iterable[dict], candidates: list[dict]) -> list[dict]:
    covered_sources = {candidate.get("source_url", "") for candidate in candidates if candidate.get("source_url")}
    with_placeholders = list(candidates)
    for record in source_records:
        source_url = record.get("source_url", "") or record.get("final_url", "")
        if source_url and source_url not in covered_sources:
            with_placeholders.append(
                {
                    **record,
                    "source_url": source_url,
                    "image_url": "",
                    "capture_method": "manual_review",
                    "source_page_verified": record.get("source_page_verified", "partial"),
                }
            )
    return with_placeholders


def build_pack(
    records: Iterable[dict],
    output_dir: str | Path,
    timeout: float = 10,
    min_width: int = 800,
    max_bytes: int = 25_000_000,
    dry_run: bool = False,
) -> dict:
    """Create a reference pack directory and return a summary."""

    source_records = list(records)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    logs_dir = output / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    _write_jsonl(output / "sources.jsonl", source_records)

    extracted = extract_records(source_records, timeout=timeout, min_width=min_width)
    candidates = _dedupe_by_image_url([*_direct_image_candidates(source_records), *extracted])
    candidates = _append_missing_source_placeholders(source_records, candidates)
    _write_jsonl(output / "image_candidates.jsonl", candidates)

    manifest = download_records(
        candidates,
        output,
        timeout=timeout,
        max_bytes=max_bytes,
        dry_run=dry_run,
    )
    downloaded_count = sum(1 for item in manifest if item.get("download_status") == "downloaded")
    failed_count = sum(1 for item in manifest if item.get("download_status", "").startswith("failed"))
    skipped_count = sum(1 for item in manifest if item.get("download_status", "").startswith("skipped"))
    summary = {
        "output_dir": str(output),
        "source_count": len(source_records),
        "candidate_count": len(candidates),
        "downloaded_count": downloaded_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "built_at": _now_iso(),
        "manifest": manifest,
    }
    (output / "pack_summary.json").write_text(
        json.dumps({k: v for k, v in summary.items() if k != "manifest"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an image reference pack from source records.")
    parser.add_argument("--input", required=True, help="CSV, JSON, or JSONL source records.")
    parser.add_argument("--output-dir", required=True, help="Reference pack output directory.")
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--min-width", type=int, default=800)
    parser.add_argument("--max-bytes", type=int, default=25_000_000)
    parser.add_argument("--dry-run", action="store_true", help="Create manifests without downloading image bytes.")
    args = parser.parse_args(argv)

    summary = build_pack(
        _read_records(Path(args.input)),
        args.output_dir,
        timeout=args.timeout,
        min_width=args.min_width,
        max_bytes=args.max_bytes,
        dry_run=args.dry_run,
    )
    json.dump({k: v for k, v in summary.items() if k != "manifest"}, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
