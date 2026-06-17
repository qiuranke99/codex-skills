"""Download public image references and write provenance sidecars.

The downloader is for image-reference review packs. It does not bypass logins,
private pages, paywalls, DRM, or hotlink protections.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import mimetypes
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
    r"<meta\s+[^>]*(?:property|name)=[\"'](?:og:image|twitter:image)[\"'][^>]*>",
    re.IGNORECASE,
)
CONTENT_RE = re.compile(r"content=[\"']([^\"']+)[\"']", re.IGNORECASE)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _slug(value: str, fallback: str = "reference") -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value, flags=re.IGNORECASE)
    value = value.strip("-")
    return (value or fallback)[:80]


def _request(url: str, timeout: float):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        },
    )
    return urllib.request.urlopen(request, timeout=timeout)


def _extension_for(url: str, content_type: str) -> str:
    media_type = (content_type or "").split(";", 1)[0].strip().lower()
    extension = mimetypes.guess_extension(media_type) if media_type else ""
    if extension == ".jpe":
        extension = ".jpg"
    if extension:
        return extension
    suffix = Path(urllib.parse.urlsplit(url).path).suffix
    return suffix if suffix else ".img"


def extract_og_image(page_url: str, timeout: float = 10) -> str:
    """Return the first og:image/twitter:image URL from a public HTML page."""

    request = urllib.request.Request(
        page_url,
        headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "text/html,*/*;q=0.8"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type.lower():
            return ""
        body = response.read(1_000_000).decode("utf-8", errors="ignore")
    for meta_tag in META_IMAGE_RE.findall(body):
        match = CONTENT_RE.search(meta_tag)
        if match:
            return urllib.parse.urljoin(page_url, html.unescape(match.group(1)))
    return ""


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


def _write_manifest(output_dir: Path, manifest: list[dict]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "manifest.json"
    csv_path = output_dir / "manifest.csv"
    json_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fieldnames = [
        "rank",
        "title",
        "source_url",
        "image_url",
        "download_status",
        "download_error",
        "download_path",
        "sidecar_path",
        "sha256",
        "bytes",
        "content_type",
        "dimensions_px",
        "duplicate_of",
        "capture_method",
        "source_page_verified",
        "license_status",
        "rights_or_usage_note",
        "is_thumbnail_or_full_res",
        "visual_mechanism",
        "error",
        "checked_at",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(manifest)


def download_records(
    records: Iterable[dict],
    output_dir: str | Path,
    timeout: float = 10,
    max_bytes: int = 25_000_000,
    dry_run: bool = False,
) -> list[dict]:
    """Download image URLs from records and write manifest files."""

    output = Path(output_dir)
    image_dir = output / "assets" / "images" / "original"
    metadata_dir = output / "sidecars"
    image_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    seen_hashes: dict[str, str] = {}
    for index, record in enumerate(records, start=1):
        source_url = (record.get("source_url") or record.get("page_url") or "").strip()
        image_url = (record.get("image_url") or record.get("asset_url") or "").strip()
        title = (record.get("title") or f"reference-{index}").strip()
        rank = str(record.get("rank") or index)
        checked_at = _now_iso()
        base_record = {
            "rank": rank,
            "title": title,
            "source_url": source_url,
            "image_url": image_url,
            "visual_mechanism": record.get("visual_mechanism", ""),
            "checked_at": checked_at,
        }

        try:
            if not image_url and source_url:
                image_url = extract_og_image(source_url, timeout=timeout)
                base_record["image_url"] = image_url
            if not image_url:
                raise ValueError("skipped_no_direct_image_url: missing image_url and no extractable page preview image")
            if dry_run:
                raise ValueError("pending_manual_review: dry_run enabled")

            with _request(image_url, timeout=timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                content_length = response.headers.get("Content-Length", "")
                if content_length:
                    try:
                        if int(content_length) > max_bytes:
                            raise ValueError(f"failed_too_large: content length {content_length} exceeds {max_bytes}")
                    except ValueError as exc:
                        if str(exc).startswith("failed_too_large"):
                            raise
                data = response.read()
            if not data:
                raise ValueError("empty response")
            if len(data) > max_bytes:
                raise ValueError(f"failed_too_large: file size {len(data)} exceeds {max_bytes}")
            media_type = content_type.lower()
            if content_type and not media_type.startswith("image/"):
                raise ValueError(f"failed_bad_content_type: response is not an image: {content_type}")

            digest = hashlib.sha256(data).hexdigest()
            extension = _extension_for(image_url, content_type)
            stem = f"{rank.zfill(2)}-{_slug(title)}-{digest[:10]}"
            image_path = image_dir / f"{stem}{extension}"
            sidecar_path = metadata_dir / f"{stem}.json"
            status = "duplicate_exact" if digest in seen_hashes else "downloaded"
            duplicate_of = seen_hashes.get(digest, "")
            if status == "downloaded":
                image_path.write_bytes(data)
                seen_hashes[digest] = str(image_path.relative_to(output))
            else:
                image_path = output / seen_hashes[digest]

            item = {
                **base_record,
                "download_status": status,
                "download_error": "",
                "download_path": str(image_path.relative_to(output)),
                "sidecar_path": str(sidecar_path.relative_to(output)),
                "sha256": digest,
                "bytes": len(data),
                "content_type": content_type,
                "dimensions_px": record.get("dimensions_px", ""),
                "duplicate_of": duplicate_of,
                "capture_method": record.get("capture_method", ""),
                "source_page_verified": record.get("source_page_verified", ""),
                "license_status": record.get("license_status", "unknown"),
                "rights_or_usage_note": record.get("rights_or_usage_note", "research reference only; verify rights before reuse"),
                "is_thumbnail_or_full_res": record.get("is_thumbnail_or_full_res", ""),
                "error": "",
            }
            sidecar_path.write_text(
                json.dumps({**record, **item}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except (urllib.error.URLError, TimeoutError, socket.timeout, ValueError) as exc:
            error = str(exc)
            if error.startswith("skipped_no_direct_image_url"):
                status = "skipped_no_direct_image_url"
            elif error.startswith("pending_manual_review"):
                status = "pending_manual_review"
            elif error.startswith("failed_bad_content_type"):
                status = "failed_bad_content_type"
            elif error.startswith("failed_too_large"):
                status = "failed_too_large"
            else:
                status = "failed_unreachable"
            item = {
                **base_record,
                "download_status": status,
                "download_error": error,
                "download_path": "",
                "sidecar_path": "",
                "sha256": "",
                "bytes": "",
                "content_type": "",
                "dimensions_px": record.get("dimensions_px", ""),
                "duplicate_of": "",
                "capture_method": record.get("capture_method", ""),
                "source_page_verified": record.get("source_page_verified", ""),
                "license_status": record.get("license_status", "unknown"),
                "rights_or_usage_note": record.get("rights_or_usage_note", "not downloaded; verify rights before reuse"),
                "is_thumbnail_or_full_res": record.get("is_thumbnail_or_full_res", ""),
                "error": error,
            }
        manifest.append(item)

    _write_manifest(output, manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download public image references with provenance.")
    parser.add_argument("--input", required=True, help="CSV, JSON, or JSONL records with image_url and source_url.")
    parser.add_argument("--output-dir", required=True, help="Directory for images, sidecars, and manifests.")
    parser.add_argument("--timeout", type=float, default=10, help="Per-request timeout in seconds.")
    parser.add_argument("--max-bytes", type=int, default=25_000_000, help="Maximum bytes per image.")
    parser.add_argument("--allow-download", action="store_true", help="Legacy no-op; downloads run by default.")
    parser.add_argument("--dry-run", action="store_true", help="Write manifest statuses without downloading.")
    args = parser.parse_args(argv)

    manifest = download_records(
        _read_records(Path(args.input)),
        args.output_dir,
        timeout=args.timeout,
        max_bytes=args.max_bytes,
        dry_run=args.dry_run,
    )
    failed = [item for item in manifest if item["download_status"].startswith("failed")]
    json.dump(manifest, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
