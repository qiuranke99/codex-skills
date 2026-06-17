"""Check reference source URLs for reachability and redirect state.

This script is intentionally dependency-free so the skill can use it in fresh
Codex workspaces without setup.
"""

from __future__ import annotations

import argparse
import csv
import json
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
SOFT_404_PATTERNS = (
    "not found",
    "no longer available",
    "content unavailable",
    "page unavailable",
    "removed",
    "doesn't exist",
    "does not exist",
    "404",
)
LOGIN_PATTERNS = (
    "log in to continue",
    "login to continue",
    "sign in to continue",
    "please log in",
    "please sign in",
    "create an account",
    "join to view",
)


class _HeadRequest(urllib.request.Request):
    def get_method(self) -> str:
        return "HEAD"


class _TrackingRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self) -> None:
        self.redirect_chain: list[str] = []
        super().__init__()

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirect_chain.append(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    return urllib.parse.urlunsplit((scheme, netloc, path, parsed.query, ""))


def _state_for_status(status_code: int, redirected: bool) -> str:
    if 200 <= status_code < 400:
        return "redirected" if redirected else "ok"
    if status_code in (404, 410):
        return "not_found"
    if status_code in (401, 403):
        return "forbidden"
    if status_code == 429:
        return "rate_limited"
    if 400 <= status_code < 500:
        return "client_error"
    if 500 <= status_code < 600:
        return "server_error"
    return "unknown_status"


def _open_once(url: str, method: str, timeout: float, user_agent: str):
    headers = {
        "User-Agent": user_agent,
        "Accept": "*/*",
    }
    if method == "GET":
        headers["Range"] = "bytes=0-4095"
    request_cls = _HeadRequest if method == "HEAD" else urllib.request.Request
    request = request_cls(url, headers=headers)
    redirect_handler = _TrackingRedirectHandler()
    opener = urllib.request.build_opener(redirect_handler)
    response = opener.open(request, timeout=timeout)
    return response, redirect_handler.redirect_chain


def _sniff_html_state(body: bytes) -> str:
    text = body[:250_000].decode("utf-8", errors="ignore").lower()
    compact = " ".join(text.split())
    if any(pattern in compact for pattern in LOGIN_PATTERNS):
        return "login_required"
    if any(pattern in compact for pattern in SOFT_404_PATTERNS):
        return "soft_404"
    return ""


def _redirect_target_mismatch(original_url: str, final_url: str) -> bool:
    original = urllib.parse.urlsplit(original_url)
    final = urllib.parse.urlsplit(final_url)
    if not final.netloc:
        return False
    if original.netloc.lower() != final.netloc.lower():
        return True
    original_path = (original.path or "/").strip("/")
    final_path = (final.path or "/").strip("/")
    return bool(original_path and not final_path)


def check_url(url: str, timeout: float = 10, user_agent: str = DEFAULT_USER_AGENT) -> dict:
    """Return a normalized reachability record for one URL."""

    original_url = (url or "").strip()
    checked_at = _now_iso()
    if not original_url:
        return {
            "url": original_url,
            "final_url": "",
            "state": "invalid_url",
            "status_code": "",
            "content_type": "",
            "error": "empty URL",
            "checked_at": checked_at,
        }
    if not urllib.parse.urlsplit(original_url).scheme:
        original_url = "https://" + original_url

    last_error = ""
    for method in ("HEAD", "GET"):
        try:
            response, redirect_chain = _open_once(original_url, method, timeout, user_agent)
            with response:
                final_url = response.geturl()
                status_code = response.getcode() or 0
                redirected = _normalize_url(final_url) != _normalize_url(original_url)
                content_type = response.headers.get("Content-Type", "")
                state = _state_for_status(status_code, redirected)
                if method == "HEAD" and "html" in content_type.lower() and 200 <= status_code < 400:
                    continue
                if method == "GET" and "html" in content_type.lower() and 200 <= status_code < 400:
                    sniffed_state = _sniff_html_state(response.read(250_000))
                    if sniffed_state:
                        state = sniffed_state
                if state == "redirected" and _redirect_target_mismatch(original_url, final_url):
                    state = "redirect_target_mismatch"
                return {
                    "url": original_url,
                    "final_url": final_url,
                    "state": state,
                    "status_code": status_code,
                    "content_type": content_type,
                    "error": "",
                    "checked_at": checked_at,
                    "method": method,
                    "redirect_chain": redirect_chain,
                }
        except urllib.error.HTTPError as exc:
            final_url = exc.geturl() or original_url
            status_code = exc.code
            redirected = _normalize_url(final_url) != _normalize_url(original_url)
            record = {
                "url": original_url,
                "final_url": final_url,
                "state": _state_for_status(status_code, redirected),
                "status_code": status_code,
                "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
                "error": str(exc),
                "checked_at": checked_at,
                "method": method,
                "redirect_chain": [],
            }
            if method == "HEAD" and status_code in (401, 403, 405, 429, 500, 501):
                last_error = str(exc)
                continue
            return record
        except (urllib.error.URLError, TimeoutError, socket.timeout, ValueError) as exc:
            last_error = str(exc)
            if method == "HEAD":
                continue

    return {
        "url": original_url,
        "final_url": "",
        "state": "unreachable",
        "status_code": "",
        "content_type": "",
        "error": last_error,
        "checked_at": checked_at,
        "method": "GET",
        "redirect_chain": [],
    }


def _read_csv(path: Path, url_column: str) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return []
        column = url_column if url_column in reader.fieldnames else reader.fieldnames[0]
        return [row.get(column, "").strip() for row in reader if row.get(column, "").strip()]


def _read_json(path: Path, url_column: str) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        urls = []
        for item in payload:
            if isinstance(item, str):
                urls.append(item)
            elif isinstance(item, dict) and item.get(url_column):
                urls.append(str(item[url_column]))
        return urls
    if isinstance(payload, dict):
        value = payload.get(url_column)
        if isinstance(value, str):
            return [value]
    return []


def load_urls(input_path: str | None, url_column: str, positional_urls: Iterable[str]) -> list[str]:
    urls = [url for url in positional_urls if url]
    if not input_path:
        return urls
    path = Path(input_path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        urls.extend(_read_csv(path, url_column))
    elif suffix == ".json":
        urls.extend(_read_json(path, url_column))
    else:
        urls.extend(
            line.strip()
            for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    return urls


def write_records(records: list[dict], output_path: str | None, output_format: str) -> None:
    if output_format == "csv":
        fieldnames = [
            "url",
            "final_url",
            "state",
            "status_code",
            "content_type",
            "error",
            "checked_at",
            "method",
            "redirect_chain",
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check source URLs before using them as evidence.")
    parser.add_argument("urls", nargs="*", help="URLs to check.")
    parser.add_argument("--input", help="CSV, JSON, or TXT file containing URLs.")
    parser.add_argument("--url-column", default="source_url", help="URL field for CSV/JSON inputs.")
    parser.add_argument("--timeout", type=float, default=10, help="Per-request timeout in seconds.")
    parser.add_argument("--format", choices=("json", "csv"), default="json")
    parser.add_argument("--output", help="Write results to this path instead of stdout.")
    args = parser.parse_args(argv)

    urls = load_urls(args.input, args.url_column, args.urls)
    records = [check_url(url, timeout=args.timeout) for url in urls]
    write_records(records, args.output, args.format)
    return 0 if all(record["state"] in ("ok", "redirected") for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
