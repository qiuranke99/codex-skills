---
name: route-web-research
description: Route and execute web search, source discovery, page extraction, document-to-Markdown conversion, site crawling, browser automation, and scraping tasks by selecting among Firecrawl, Crawl4AI, browser-use, Crawlee, Scrapy, MarkItDown, Scrapling, AutoScraper, curl-impersonate, curl_cffi, and Playwright. Use when Codex must search the web, find primary/source URLs, cite sources, crawl a site, scrape structured data, convert files or pages to Markdown, handle JavaScript-rendered pages, investigate fetch failures, or design repeatable web-data workflows with evidence and fallbacks.
---

# Route Web Research

Use this skill as a router, not as a menu. Start from the user's research or extraction intent, classify the access problem, choose the smallest sufficient tool chain, record rejected tools, and validate evidence before reporting.

## First Moves

1. Run `scripts/probe_tools.py --json` when the current machine/toolchain state matters, or when a requested route depends on API keys, Node modules, browser runtimes, WSL, or `curl-impersonate`.
2. Read `references/route-matrix.md` before choosing tools for a non-trivial task.
3. Read `references/tool-capabilities.md` when tool-specific behavior, prerequisites, or caveats matter.
4. Read `references/access-safety.md` before using browser automation, stealth fetchers, `curl-impersonate`, `curl_cffi`, proxies, logged-in sessions, paywalled content, or any site that may object to automated access.
5. Use `references/evidence-schema.md` as the output contract for source discovery, citations, crawling, and scraping deliverables.

## Routing Rules

- Prefer primary, official, creator, manufacturer, standards, repo, paper, or first-party sources. Label reposts, mirrors, and weak inferences as `unconfirmed_lead`.
- For quick search plus LLM-ready web extraction, use Firecrawl when `FIRECRAWL_API_KEY` or a configured self-hosted Firecrawl URL is available.
- For local LLM-friendly Markdown extraction from public web pages, use Crawl4AI first.
- For deterministic browser inspection, screenshots, JS-rendered pages, sessions, and UI interaction, use Playwright directly; use browser-use when an LLM-driven browser action loop is required and an LLM/API route is available.
- For repeatable Node crawlers, queues, datasets, or a JavaScript stack, use Crawlee.
- For long-lived Python crawler projects with spiders, selectors, exports, middlewares, and pipelines, use Scrapy.
- For PDFs, Office files, spreadsheets, HTML files, media metadata, and mixed documents, use MarkItDown.
- For selector drift or adaptive scraping, use Scrapling; for sample-value rule learning over similar pages, use AutoScraper.
- For public pages blocked by TLS/HTTP fingerprint mismatch, try `curl_cffi` on Windows or WSL `curl_chrome*`/`curl-impersonate-*`. Do not use impersonation to bypass login, paywall, CAPTCHA, rate limits, or explicit access controls.

## Execution Helpers

- `scripts/route_web_research.py`: local router for simple search, URL fetch, and document conversion. It emits evidence JSON and records tools tried. Use it as a first pass, then escalate manually when the task needs scale or custom selectors.
- `scripts/crawlee_fetch.js`: one-page Crawlee fetch helper used by the router or for Node route validation.
- `scripts/probe_tools.py`: environment probe for Python packages, Node modules, CLIs, browsers, API-key presence, and WSL `curl-impersonate` wrappers.
- `scripts/validate_evidence.py`: validates evidence JSON before final answers or durable handoffs.

Default local toolchain on this machine:

```text
D:\AI\toolchains\global-search\.venv\Scripts\python.exe
D:\AI\toolchains\global-search\node
WSL: ~/.local/share/global-search/curl-impersonate-v0.6.1
```

Override with `GLOBAL_SEARCH_TOOLCHAIN_ROOT`, `GLOBAL_SEARCH_PYTHON`, or `GLOBAL_SEARCH_NODE_ROOT`.

## Evidence Contract

Every research/crawl/scrape answer must include enough provenance to re-check claims:

- `source_url` and canonical URL when available.
- `source_type` and `verification_status`.
- `discovered_via`, `fetched_via`, HTTP status, access time, and content hash where applicable.
- Claim-to-source mapping. Do not treat a search-result snippet as final evidence.
- Route rationale: selected tools, rejected tools, fallbacks used, and failures that changed the route.

Run:

```powershell
D:\AI\toolchains\global-search\.venv\Scripts\python.exe D:\AI\skill\route-web-research\scripts\validate_evidence.py output.json
```

## Stop Conditions

Stop or ask before proceeding when the only remaining path requires credentials, account approval, paid API budget, solving CAPTCHA, bypassing a paywall/login, ignoring robots/ToS constraints, collecting sensitive personal data, or installing system-level services such as Docker Desktop.

When a route fails, record the exact failure and move up the ladder: search diversification, clean HTTP fetch, Crawl4AI/MarkItDown extraction, Playwright/browser-use, Scrapling/AutoScraper, Crawlee/Scrapy projectization. Do not report success from a weaker artifact if the user's claim requires stronger evidence.
