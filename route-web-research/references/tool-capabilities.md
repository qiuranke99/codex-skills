# Tool Capabilities

This reference captures what each installed tool is good for, what it is not, and when to route to it.

## Firecrawl

- Best for hosted web search, scrape, crawl, map, batch scrape, extraction, links, screenshots, and LLM-ready Markdown/HTML/JSON outputs.
- Use when `FIRECRAWL_API_KEY` is present, or when a self-hosted `FIRECRAWL_API_URL` is configured.
- Self-hosting is a service deployment, normally Docker/Redis/Playwright; it is not equivalent to installing a Python package.
- Do not assume cloud-only features are present in self-hosted mode.
- Official sources: https://github.com/firecrawl/firecrawl and https://docs.firecrawl.dev/

## Crawl4AI

- Best local first choice for public page-to-Markdown extraction, LLM-oriented crawling, deep crawl, sessions, browser hooks, and extraction strategies.
- Use for one-off public pages, docs-site ingestion, and local browser-backed extraction.
- Run `crawl4ai-setup` after package install and `crawl4ai-doctor` for health checks.
- Needs browser runtime for JS-heavy pages; LLM extraction needs model/provider configuration.
- Official sources: https://github.com/unclecode/crawl4ai and https://docs.crawl4ai.com/

## browser-use

- Best for LLM-directed browser action loops: forms, multi-step UI tasks, visual state, dynamic apps, and workflows where the next action depends on page observation.
- Not a crawler framework. Do not route ordinary source discovery or bulk extraction here first.
- Local browser inspection can run without Browser Use Cloud, but `run`/agent behavior needs an LLM/API route; remote/cloud mode needs a Browser Use API key.
- On Windows, run with UTF-8 env vars if CLI output hits GBK encoding errors.
- Official sources: https://github.com/browser-use/browser-use and https://docs.browser-use.com/

## Crawlee

- Best Node/TypeScript framework for repeatable crawlers, request queues, datasets, proxies, and choosing HTTP/DOM/browser crawling.
- Use CheerioCrawler for fast static pages and PlaywrightCrawler/PuppeteerCrawler for JS-rendered pages.
- No API key required locally; Apify cloud deployment, proxies, and storage are optional.
- Official sources: https://github.com/apify/crawlee and https://crawlee.dev/js/docs/

## Scrapy

- Best mature Python framework for long-lived structured crawlers: spiders, selectors, item pipelines, feed exports, middlewares, scheduling, retries, and broad crawls.
- Use for stable static sites and repeatable data collection.
- It does not render JavaScript by default; pair with scrapy-playwright or route to Playwright/Crawlee when rendering is mandatory.
- Official sources: https://github.com/scrapy/scrapy and https://docs.scrapy.org/

## MarkItDown

- Best for converting files and documents to Markdown: PDF, Office, spreadsheets, HTML, images, audio metadata/transcripts where supported, CSV/JSON/XML, ZIP, EPUB, and URLs supported by the converter.
- Use for document conversion before web crawling.
- Some advanced OCR/Azure/vision behavior needs external services. It reads inputs with current process privileges; do not feed untrusted files casually.
- Official source: https://github.com/microsoft/markitdown

## Scrapling

- Best for adaptive scraping, self-healing element matching, stealthier fetchers, and pages where selectors drift.
- `Fetcher` gives fast HTTP fetching; stealth/browser modes need installed browser/fingerprint resources.
- Do not default to stealth. Use it only when public access is legitimate and simpler fetchers fail.
- Official sources: https://github.com/D4Vinci/Scrapling and https://scrapling.readthedocs.io/

## AutoScraper

- Best for simple rule learning from example desired values over similar static pages.
- Requires representative examples; weak for JS-heavy pages, complex anti-bot sites, and highly variable layouts.
- PyPI/GitHub project is older and should be treated as a narrow extractor, not a full crawling platform. On this machine it imports, but generic minimal learning checks returned empty results, so require target-specific proof before relying on it.
- Official source: https://github.com/alirezamika/autoscraper

## curl-impersonate and curl_cffi

- `curl-impersonate` is a patched curl/libcurl that mimics browser TLS/HTTP2 fingerprints. On this Windows machine it is installed in WSL via Linux release wrappers such as `curl_chrome110`.
- `curl_cffi` is the Windows-friendly Python route that wraps curl-impersonate-style browser impersonation.
- Use only for public resources where plain HTTP clients fail due to TLS/HTTP fingerprint mismatch.
- It is a transport primitive, not a parser, crawler, or permission bypass.
- Official source: https://github.com/lwthiker/curl-impersonate
- Complementary source: https://github.com/lexiforest/curl_cffi

## Direct Playwright

- Best deterministic browser control: navigation, screenshots, DOM inspection, file downloads, JS evaluation, and local debugging.
- Use before browser-use when the task is deterministic and does not need an LLM action loop.
- Official source: https://playwright.dev/
