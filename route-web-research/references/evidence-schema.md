# Evidence Schema

The skill's durable output is evidence, not a loose summary. Use this JSON shape for source discovery, crawl, scrape, and conversion results.

```json
{
  "run": {
    "task": "",
    "created_at": "",
    "constraints": []
  },
  "route": {
    "selected_tools": [],
    "rejected_tools": [{"tool": "", "reason": ""}],
    "fallbacks_used": [{"tool": "", "error": ""}]
  },
  "sources": [{
    "source_id": "S1",
    "rank": 1,
    "source_url": "",
    "canonical_url": "",
    "title": "",
    "source_type": "official|primary|creator|manufacturer|paper|repo|standards|press|docs|repost|search_result|unknown",
    "verification_status": "verified|partially_verified|unconfirmed_lead|access_restricted|contradicted|failed_fetch",
    "discovered_via": "",
    "fetched_via": "",
    "http_status": 200,
    "accessed_at": "",
    "published_at": "",
    "content_type": "",
    "content_hash": "",
    "claims": [{
      "claim": "",
      "evidence_snippet": "",
      "confidence": "high|medium|low"
    }],
    "risks_or_limits": ""
  }]
}
```

Validate with:

```powershell
D:\AI\toolchains\global-search\.venv\Scripts\python.exe D:\AI\skill\route-web-research\scripts\validate_evidence.py output.json
```

## Source Type Guidance

- `official`: official product/company/project page.
- `primary`: direct source such as government, standard body, original publication, original dataset, or event owner.
- `creator`: original creator/author channel.
- `manufacturer`: brand/manufacturer product page.
- `paper`: scholarly paper, preprint, or technical report.
- `repo`: source code repository or release page.
- `docs`: official docs.
- `press`: press release or publisher article.
- `repost`: copied, mirrored, syndicated, or reuploaded source.
- `search_result`: a SERP lead, never final evidence.
- `unknown`: use only when classification is not yet justified.

Weak source types (`repost`, `search_result`, `unknown`) must not be marked `verified`.

## Minimal Examples

Search lead:

```json
{
  "source_id": "S1",
  "rank": 1,
  "source_url": "https://example.com/page",
  "source_type": "search_result",
  "verification_status": "unconfirmed_lead",
  "discovered_via": "duckduckgo_search",
  "fetched_via": "not_fetched",
  "claims": [{"claim": "Potential source lead", "evidence_snippet": "Search snippet", "confidence": "low"}]
}
```

Fetched source:

```json
{
  "source_id": "S1",
  "rank": 1,
  "source_url": "https://docs.example.com/spec",
  "source_type": "docs",
  "verification_status": "partially_verified",
  "discovered_via": "user_url",
  "fetched_via": "crawl4ai",
  "content_hash": "sha256...",
  "claims": [{"claim": "The page was fetched and converted", "evidence_snippet": "Extracted text", "confidence": "medium"}]
}
```
