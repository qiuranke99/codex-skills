# Local Toolchain

Installed on this machine for `route-web-research`.

## Paths

```text
Python venv: D:\AI\toolchains\global-search\.venv
Python executable: D:\AI\toolchains\global-search\.venv\Scripts\python.exe
Node root: D:\AI\toolchains\global-search\node
WSL curl-impersonate: ~/.local/share/global-search/curl-impersonate-v0.6.1
Codex skill root: D:\AI\skill\route-web-research
Codex discovery junction: C:\Users\Administrator\.codex\skills\route-web-research
```

Override paths with:

```text
GLOBAL_SEARCH_TOOLCHAIN_ROOT
GLOBAL_SEARCH_PYTHON
GLOBAL_SEARCH_NODE_ROOT
```

## Installed Python Packages

```text
firecrawl-py 4.31.0
crawl4ai 0.9.0
browser-use 0.11.13
scrapy 2.16.0
markitdown 0.1.5
scrapling 0.2.99
autoscraper 1.1.14
curl_cffi 0.15.0
duckduckgo-search 8.1.1
ddgs 9.14.4
playwright 1.61.0
```

## Installed Node Packages

```text
crawlee 3.17.0
@mendable/firecrawl-js 4.29.0
playwright installed under D:\AI\toolchains\global-search\node
```

## Verified Runtime Notes

- Crawl4AI setup and doctor passed.
- Python Playwright launched Chromium and read a test page.
- browser-use doctor passed package, browser, and network checks; API key and cloudflared are absent because cloud/remote mode is not configured.
- Scrapling installed Camoufox and its browser databases after a retry.
- AutoScraper 1.1.14 imports successfully, but minimal sample-learning checks returned empty results in this Python 3.12 environment; treat it as installed but not a default trusted route until a target-specific sample is proven.
- WSL `curl_chrome110` and `curl-impersonate-chrome` report curl 8.1.1/libcurl 8.1.1 with BoringSSL.
- Docker is not installed in PATH, so Firecrawl self-host service was not installed. Firecrawl SDKs are installed and ready for API-key or external self-hosted service use.
