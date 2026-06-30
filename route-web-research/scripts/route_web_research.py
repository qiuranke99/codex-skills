#!/usr/bin/env python3
"""Small local router for search, fetch, and document conversion evidence runs."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


TOOLCHAIN_ROOT = Path(os.environ.get("GLOBAL_SEARCH_TOOLCHAIN_ROOT", r"D:\AI\toolchains\global-search"))
NODE_ROOT = Path(os.environ.get("GLOBAL_SEARCH_NODE_ROOT", str(TOOLCHAIN_ROOT / "node")))
SKILL_ROOT = Path(__file__).resolve().parents[1]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def is_probable_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def source_type_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "github.com" in host:
        return "repo"
    if any(host.endswith(domain) for domain in [".gov", ".edu", ".int"]):
        return "primary"
    if any(name in host for name in ["docs.", "developer.", "dev."]):
        return "docs"
    return "unknown"


def firecrawl_search(query: str, limit: int) -> tuple[list[dict], str | None]:
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        return [], "FIRECRAWL_API_KEY not set"
    try:
        from firecrawl import Firecrawl

        client = Firecrawl(api_key=api_key, api_url=os.environ.get("FIRECRAWL_API_URL", "https://api.firecrawl.dev"))
        data = client.search(query, limit=limit)
        raw = data.model_dump() if hasattr(data, "model_dump") else data
        rows = raw.get("data", raw) if isinstance(raw, dict) else raw
        return list(rows or [])[:limit], None
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"


def duckduckgo_search(query: str, limit: int) -> tuple[list[dict], str | None]:
    try:
        try:
            from ddgs import DDGS
            provider = "ddgs"
        except Exception:
            from duckduckgo_search import DDGS
            provider = "duckduckgo_search"

        rows = DDGS().text(query, max_results=limit)
        normalized = []
        for row in rows or []:
            normalized.append(
                {
                    "url": row.get("href") or row.get("url"),
                    "title": row.get("title"),
                    "description": row.get("body") or row.get("snippet"),
                }
            )
        if not normalized:
            return [], f"{provider} returned no results"
        return normalized[:limit], None
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"


async def fetch_crawl4ai(url: str) -> tuple[dict | None, str | None]:
    try:
        from crawl4ai import AsyncWebCrawler

        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
        markdown = getattr(result, "markdown", None) or ""
        html = getattr(result, "html", None) or ""
        status = getattr(result, "status_code", None)
        if not markdown and not html:
            return None, "empty Crawl4AI result"
        return {"tool": "crawl4ai", "text": markdown or html, "http_status": status}, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def fetch_firecrawl(url: str) -> tuple[dict | None, str | None]:
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        return None, "FIRECRAWL_API_KEY not set"
    try:
        from firecrawl import Firecrawl

        client = Firecrawl(api_key=api_key, api_url=os.environ.get("FIRECRAWL_API_URL", "https://api.firecrawl.dev"))
        doc = client.scrape(url, formats=["markdown", "html"])
        raw = doc.model_dump() if hasattr(doc, "model_dump") else doc
        text = ""
        if isinstance(raw, dict):
            text = raw.get("markdown") or raw.get("html") or json.dumps(raw, ensure_ascii=False)
        else:
            text = str(raw)
        return {"tool": "firecrawl", "text": text, "http_status": None}, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def fetch_markitdown(source: str) -> tuple[dict | None, str | None]:
    try:
        from markitdown import MarkItDown

        result = MarkItDown().convert(source)
        text = getattr(result, "text_content", "") or str(result)
        return {"tool": "markitdown", "text": text, "http_status": None}, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def fetch_scrapling(url: str) -> tuple[dict | None, str | None]:
    try:
        from scrapling.fetchers import Fetcher

        response = Fetcher.get(url, timeout=15)
        text = (
            getattr(response, "body", None)
            or getattr(response, "html_content", None)
            or getattr(response, "text", None)
            or str(response)
        )
        status = getattr(response, "status", None) or getattr(response, "status_code", None)
        return {"tool": "scrapling", "text": text, "http_status": status}, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def fetch_curl_cffi(url: str) -> tuple[dict | None, str | None]:
    try:
        from curl_cffi import requests

        response = requests.get(url, impersonate="chrome110", timeout=20)
        return {"tool": "curl_cffi", "text": response.text, "http_status": response.status_code}, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def fetch_crawlee(url: str) -> tuple[dict | None, str | None]:
    script = SKILL_ROOT / "scripts" / "crawlee_fetch.js"
    if not script.exists():
        return None, f"missing {script}"
    try:
        completed = subprocess.run(
            ["node", str(script), url],
            cwd=str(NODE_ROOT),
            text=True,
            capture_output=True,
            timeout=60,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if completed.returncode != 0:
        return None, completed.stderr.strip() or completed.stdout.strip()
    json_line = None
    for line in reversed(completed.stdout.splitlines()):
        if line.strip().startswith("{"):
            json_line = line.strip()
            break
    if not json_line:
        return None, completed.stdout
    try:
        data = json.loads(json_line)
    except json.JSONDecodeError:
        return None, completed.stdout
    if data.get("error"):
        return None, data.get("error")
    return {"tool": "crawlee", "text": data.get("text") or "", "http_status": data.get("status")}, None


def fetch_url(url: str, preferred: str = "auto") -> tuple[dict | None, list[dict]]:
    failures: list[dict] = []
    route = []
    if preferred == "auto":
        route = ["firecrawl", "crawl4ai", "scrapling", "curl_cffi", "crawlee"]
    else:
        route = [preferred]

    for tool in route:
        if tool == "firecrawl":
            data, error = fetch_firecrawl(url)
        elif tool == "crawl4ai":
            data, error = asyncio.run(fetch_crawl4ai(url))
        elif tool == "markitdown":
            data, error = fetch_markitdown(url)
        elif tool == "scrapling":
            data, error = fetch_scrapling(url)
        elif tool == "curl_cffi":
            data, error = fetch_curl_cffi(url)
        elif tool == "crawlee":
            data, error = fetch_crawlee(url)
        else:
            data, error = None, f"unknown tool: {tool}"

        if data and data.get("text"):
            data["failures_before_success"] = failures
            return data, failures
        failures.append({"tool": tool, "error": error or "empty result"})

    return None, failures


def evidence_for_search(task: str, rows: list[dict], discovered_via: str, failures: list[dict]) -> dict:
    sources = []
    for idx, row in enumerate(rows, 1):
        url = row.get("url") or row.get("source_url")
        if not url:
            continue
        sources.append(
            {
                "source_id": f"S{idx}",
                "rank": idx,
                "source_url": url,
                "canonical_url": url,
                "title": row.get("title") or "",
                "source_type": source_type_from_url(url),
                "verification_status": "unconfirmed_lead",
                "discovered_via": discovered_via,
                "fetched_via": "not_fetched",
                "http_status": None,
                "accessed_at": now_iso(),
                "published_at": None,
                "content_type": None,
                "content_hash": None,
                "claims": [
                    {
                        "claim": row.get("description") or row.get("title") or "search result lead",
                        "evidence_snippet": row.get("description") or row.get("title") or url,
                        "confidence": "low",
                    }
                ],
                "risks_or_limits": "Search result lead only; fetch and verify before using as final evidence.",
            }
        )
    return {
        "run": {"task": task, "created_at": now_iso(), "constraints": []},
        "route": {
            "selected_tools": [discovered_via],
            "rejected_tools": [],
            "fallbacks_used": failures,
        },
        "sources": sources,
    }


def evidence_for_fetch(task: str, url: str, result: dict | None, failures: list[dict]) -> dict:
    if result:
        text = result.get("text") or ""
        source = {
            "source_id": "S1",
            "rank": 1,
            "source_url": url,
            "canonical_url": url,
            "title": "",
            "source_type": source_type_from_url(url),
            "verification_status": "partially_verified",
            "discovered_via": "user_url",
            "fetched_via": result.get("tool"),
            "http_status": result.get("http_status"),
            "accessed_at": now_iso(),
            "published_at": None,
            "content_type": None,
            "content_hash": sha256_text(text),
            "claims": [
                {
                    "claim": "Content fetched and converted for inspection.",
                    "evidence_snippet": text[:500].replace("\n", " "),
                    "confidence": "medium",
                }
            ],
            "risks_or_limits": "Automated extraction may omit layout, scripts, or hidden content; inspect raw source for high-stakes claims.",
        }
        selected = [result.get("tool")]
    else:
        source = {
            "source_id": "S1",
            "rank": 1,
            "source_url": url,
            "canonical_url": url,
            "title": "",
            "source_type": source_type_from_url(url),
            "verification_status": "failed_fetch",
            "discovered_via": "user_url",
            "fetched_via": "none",
            "http_status": None,
            "accessed_at": now_iso(),
            "published_at": None,
            "content_type": None,
            "content_hash": None,
            "claims": [],
            "risks_or_limits": "All attempted automated fetch routes failed.",
        }
        selected = []

    return {
        "run": {"task": task, "created_at": now_iso(), "constraints": []},
        "route": {
            "selected_tools": selected or ["none"],
            "rejected_tools": [],
            "fallbacks_used": failures,
        },
        "sources": [source],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Route a simple web research/fetch/conversion task")
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--url", help="URL to fetch")
    parser.add_argument("--file", help="Local file to convert with MarkItDown")
    parser.add_argument("--tool", default="auto", help="auto, firecrawl, crawl4ai, markitdown, scrapling, curl_cffi, crawlee")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    if sum(bool(x) for x in [args.query, args.url, args.file]) != 1:
        parser.error("Provide exactly one of --query, --url, or --file")

    if args.query:
        rows, error = firecrawl_search(args.query, args.limit)
        failures = []
        via = "firecrawl_search"
        if error:
            failures.append({"tool": "firecrawl_search", "error": error})
            rows, error = duckduckgo_search(args.query, args.limit)
            via = "duckduckgo_search"
            if error:
                failures.append({"tool": "duckduckgo_search", "error": error})
        evidence = evidence_for_search(args.query, rows, via, failures)
    elif args.file:
        source = str(Path(args.file).resolve())
        result, error = fetch_markitdown(source)
        failures = [] if result else [{"tool": "markitdown", "error": error}]
        evidence = evidence_for_fetch(f"convert {source}", Path(source).as_uri(), result, failures)
    else:
        result, failures = fetch_url(args.url, args.tool)
        evidence = evidence_for_fetch(f"fetch {args.url}", args.url, result, failures)

    text = json.dumps(evidence, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
