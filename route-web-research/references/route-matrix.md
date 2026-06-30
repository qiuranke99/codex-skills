# Route Matrix

Use this as the routing ladder for search, extraction, crawl, and scraping tasks.

## Intent Routes

| User intent | First route | Escalate when | Stronger route |
| --- | --- | --- | --- |
| Find source URLs or primary sources | Firecrawl Search if keyed; otherwise web search / DuckDuckGo lead pass | Leads are weak, repost-heavy, or not primary | Query-lane expansion plus direct official/repo/docs searches |
| Convert a known public URL to Markdown | Crawl4AI | JS rendering, blocked static fetch, screenshots, or interactions required | Playwright, then browser-use if LLM action loop is needed |
| Convert PDF/Office/HTML/local files | MarkItDown | Tables/OCR/reading order are poor | Add Docling/Azure/vision OCR manually if warranted |
| Crawl many pages in Python | Scrapy | JS rendering or browser state is required | Scrapy + scrapy-playwright, or Crawlee Playwright |
| Crawl many pages in Node/TS | Crawlee CheerioCrawler | JS rendering required | Crawlee PlaywrightCrawler/PuppeteerCrawler |
| Extract values from pages with examples | AutoScraper only after a target-specific learning test passes | Selectors drift, pages differ materially, or AutoScraper returns empty rules | Scrapling adaptive matching or a custom crawler |
| Selectors keep breaking | Scrapling | Browser behavior required | Scrapling stealth/dynamic fetchers or Playwright |
| TLS/HTTP fingerprint blocks public content | curl_cffi on Windows | Need exact curl-impersonate profiles | WSL curl_chrome* wrappers |
| Dynamic UI, form flow, visual state | Playwright | Goal requires autonomous LLM decisions | browser-use |
| Firecrawl cloud extraction/crawl requested | Firecrawl SDK | No API key or service unavailable | Crawl4AI/Crawlee/Scrapy local route |

## Default Fallback Ladder

1. Discover candidate sources.
2. Rank source quality before extraction: official/primary beats mirrors/reposts.
3. Fetch clean content: Firecrawl if keyed, otherwise Crawl4AI.
4. If content is a document or local file, use MarkItDown.
5. If static fetch fails: try Scrapling Fetcher, then `curl_cffi` for public TLS fingerprint mismatch.
6. If the page is JavaScript-rendered or requires interaction: use Playwright.
7. If repeated or large-scale: promote to Crawlee or Scrapy project shape.
8. Validate evidence JSON before reporting or promoting durable findings.

## Negative Routing

- Do not use browser-use for ordinary crawling. It is for browser action loops.
- Do not use curl-impersonate/curl_cffi to bypass logins, paywalls, CAPTCHA, explicit blocks, or rate limits.
- Do not treat Firecrawl/Search snippets, DuckDuckGo snippets, or SERP summaries as verified evidence.
- Do not run a broad crawler until the source set, scope, robots/ToS posture, rate limits, and output schema are clear.
- Do not hide failed tools. Record failures because they explain why the route escalated.
