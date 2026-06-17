---
name: source-url-reference-research
description: "Use when finding visual reference images or videos, source_url evidence, downloadable image reference packs, verified links, Instagram/Behance/Vimeo/portfolio research, high-end beauty/skincare/luxury/product photography, reference images, reference videos, cankaotu, or cankaopian."
---

# Source URL Reference Research

## Overview

Use this skill for source-aware visual reference research. The default is still `source_url` first: every selected reference must remain traceable to a reachable source page. source_url-first does not mean source_url-only. For every `image_reference` task, source evidence and a local image reference pack are both required. Only skip downloads when the user explicitly says `links-only`, `no-download`, or "不要下载"; never infer that from "source_url-first". Downloaded files are working copies, not provenance. For video-reference tasks, return verified source links and do not download video unless the user separately authorizes a different workflow.

This is for ad hoc discovery. If the work is the scheduled `D:\Agent\visual-art-director-agent` loop, use that repo's automations and validators. If the user already has a specific reference video to adapt, use `reference-video-product-adapter`.

## Non-Negotiables

- Run the first-pass research autonomously. Do not pause for broad direction confirmation when the brief is workable.
- Verify every final ranked `source_url`. A link that was not opened, checked with `scripts/verify_urls.py`, or browser-verified cannot be called `verified`.
- Prefer fewer strong references over a long weak list. Move weak clues to `unconfirmed_leads` or `rejected_patterns`.
- Keep source provenance separate from media files: `source_url`/`final_url` identify evidence; `download_path` identifies a local working copy.
- For `image_reference`, MUST create a local image reference pack. Do not finish an `image_reference` route with only Markdown links unless the user explicitly requested links-only/no-download.
- A report that says "未下载媒体", "未下载图片", "未建本地参考包", "no media downloads", or equivalent is a failed `image_reference` run, not a completed result.
- Do not bypass login, private accounts, paywalls, DRM, robots-style blocks, or hotlink protections. Label access limits directly.
- Do not promote Pinterest, Xiaohongshu, generic repost pages, stock sites, AI renders, or social compilations to original sources unless no better source exists and the row is clearly labeled as a clue.

## Route First

Choose one route before searching. If the user mixes needs, use `mixed_reference` and keep outputs separated.

| Route | Use When | Output |
| --- | --- | --- |
| `image_reference` | Reference images, mood board, still life, product photo, material, lighting, set design, downloadable image pack, cankaotu | Verified evidence table plus a local image pack; links-only is allowed only when the user explicitly asks for no downloads |
| `video_reference` | Reference films, ads, camera movement, edit rhythm, duration, Vimeo/YouTube/Xinpianchang, cankaopian | Verified evidence table; no video downloads |
| `mixed_reference` | User asks for both images and videos, or a campaign needs still and moving references | Separate image and video sections with separate validation notes |

For image routes, create a pack under `reference-packs/<brief-slug>-<YYYYMMDD-HHMM>/`. If no image can be downloaded, still create the pack directory and manifest with failed/skipped rows and explain why. Use this layout:

- `assets/images/original/` downloaded public image files,
- `sidecars/` one JSON sidecar per image,
- `manifest.csv` and `manifest.json`,
- `sources.jsonl`, `image_candidates.jsonl`, and `pack_summary.json`,
- optional `logs/url-check.csv` from URL verification.

## Workflow

1. Define the research target.
   - Extract product/category, route, brand tier, geography/language, desired count, visual level, platforms, must-have traits, and hard exclusions.
   - Translate fuzzy words like "premium", "luxury", "high-end", "clean", "editorial", or "not e-commerce" into observable filters: production value, lighting, set design, retouching, product role, camera language, and source credibility.
   - Build a visual-director matrix before searching: direct product match, adjacent category analogies, material/lens/lighting/set references, and what must not be copied.

2. Design search lanes.
   - Read `references/search-playbook.md` for source tiers, platform caveats, and query grammar.
   - For product precision, run at least three lanes: direct category, professional creator/source, and visual-mechanism/analogy.
   - Use negative terms aggressively to remove tutorials, reviews, shopping pages, stock, AI renders, packs, and low-end e-commerce.

3. Search source-first.
   - Prefer original pages: brand/campaign, photographer, director, studio, agency, production company, editorial feature, Behance project, Instagram creator post, Vimeo/YouTube official upload.
   - Use reposts and visual bookmarking sites only as discovery clues until an original or more authoritative source is found.
   - For Instagram or other login-sensitive sites, use Browser/Chrome only when the task needs that platform or the user has relevant browser state. Label `browser_verified_login_context` if public unauthenticated access is not confirmed. Do not return a list of profile links as final evidence; prefer a specific post, creator portfolio, agency page, brand/editorial credit page, or Behance project.

4. Triage like a visual director.
   - For each candidate, identify observable mechanisms: composition, crop, lens/framing, lighting ratio, shadows/reflections, material treatment, color, set/props, retouching, camera movement, edit rhythm, product role, and adaptation takeaway.
   - For eyeliner/eye-pencil-like briefs, do not stop at packshots. Cover product still life, macro tip/detail, texture/swatch/material, shadow/mood, set design, similar-form-factor cosmetics, and application/gesture if relevant.
   - Label analogies as analogies. A luxury pen, mascara wand, lip liner, or brow pencil can inform form/material/crop, but it is not an eyeliner reference.

5. Verify links before final output.
   - Use `scripts/verify_urls.py` for candidate lists:

```bash
python scripts/verify_urls.py --input candidates.csv --format csv --output url-check.csv
```

   - Accept final rows only when `access_status` is `ok`, `redirected`, `browser_verified`, or `browser_verified_login_context`.
   - If a useful candidate is `not_found`, `soft_404`, `unreachable`, `forbidden`, `login_required`, `paywalled`, `rate_limited`, `redirect_target_mismatch`, or uncertain, move it to `unconfirmed_leads` or `rejected_patterns` unless the user explicitly wants blocked leads documented.

6. Build the image reference pack for every image route.
   - Run `scripts/build_image_reference_pack.py` after selecting verified source pages. This is the default path; do not replace it with a Markdown-only link list.

```bash
python scripts/build_image_reference_pack.py --input verified-sources.csv --output-dir reference-packs/<brief-slug>-<YYYYMMDD-HHMM>
```

   - If a page has no extractable image URL, the pack builder still writes `sources.jsonl`, `image_candidates.jsonl`, `manifest.json`, and `manifest.csv`; report the failure status instead of silently skipping it.
   - If you already know direct image URLs, include `image_url` in the source records so the builder downloads them without a separate extraction step.
   - Use lower-level tools only when debugging or manually recovering a blocked case:

```bash
python scripts/extract_image_candidates.py --input verified-sources.csv --output image-candidates.jsonl --format jsonl --min-width 800 --no-download
python scripts/download_reference_images.py --input selected-images.jsonl --output-dir reference-packs/<brief-slug>-<YYYYMMDD-HHMM>
```

   - If the tool can only retrieve a thumbnail, social preview, or blocked asset, label it in the manifest and search for a better source. Do not claim a pack is complete when most images failed.

7. Apply route-specific gates.
   - Static image gate: final set should cover direct category plus useful visual mechanisms, not just product-detail pages.
   - Video gate: prefer single-work pages; reject showreels, compilations, tutorials, making-of videos, reviews, and case-study pages unless explicitly requested. For "near 30 seconds", use a default acceptance window of 20-45 seconds and include `duration_basis`.
   - Instagram gate: use Instagram for discovery and specific creator-owned posts only; if not publicly opened or browser-verified, keep it as `unconfirmed_lead` and look for the creator's website, agency, brand, editorial, or Behance source.

8. Return the evidence.
   - Follow `references/evidence-schema.md` for required fields.
   - Include a short search audit: `route_decision`, `query_lanes`, `queries_tried`, `hard_exclusions`, `rejected_patterns`, `missing_source_tiers`, and `next_searches`.
   - State the local image-pack path for every image route, plus downloaded/failed/skipped counts from `pack_summary.json`.
   - Run `scripts/validate_reference_report.py` before the final answer for any Markdown report. If it fails, fix the report or build the missing image pack before responding.
   - End with high-yield next searches, not generic "more research needed".

## Delegation Template

Use this shape when dispatching a bounded research subtask:

```text
/goal: Find verified source_url visual references for <target>.
Role: source-url visual reference researcher.
Route: <image_reference | video_reference | mixed_reference>.
Download images: <yes by default for image_reference; no only if user explicitly requests links-only/no-download>.
Target: <category/style/project>.
Sources: <platforms/sites/source tiers>.
Queries: <query list with negative terms>.
Hard exclusions: <exclude categories, brands, durations, quality types>.
Reachability: verify every final source_url; unverified leads stay separate.
Output: use references/evidence-schema.md fields plus search audit.
Image pack: run scripts/build_image_reference_pack.py and report pack path plus manifest counts.
Completion gate: run scripts/validate_reference_report.py before final answer.
Stop after: <count or time bound>.
```

## Common Failure Modes

- Listing search-result URLs or snippets without opening the page.
- Treating reposts, Pinterest boards, Xiaohongshu saves, or ad compilations as original evidence.
- Returning product pages only when the user needs visual mechanisms, not SKU documentation.
- Downloading thumbnails, CDN previews, or expiring social hotlinks and calling them usable references.
- Letting ambiguous product names drift into unrelated categories.
- Calling a link `verified` when it is actually login-gated, blocked, or only visible in the current browser session.
- Mixing direct references and analogy references without labeling the difference.
