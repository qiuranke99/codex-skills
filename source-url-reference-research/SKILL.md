---
name: source-url-reference-research
description: "Use when finding visual reference images or videos and returning source_url evidence without downloading media: Vimeo, 新片场, brand sites, official campaign pages, creator or production-company pages, high-end product visuals, 参考片, 参考图, visual mechanisms, link lists, or source-aware research tables."
---

# Source URL Reference Research

## Overview

Use this skill to find and triage visual references as source links, not media files. The output is a compact evidence set that can feed project planning, visual-direction research, or later reference adaptation.

This is for ad hoc discovery. If the work is the scheduled `D:\Agent\visual-art-director-agent` daily/weekly/monthly/quarterly loop, use the existing automations and repo validators. If the user already has a specific reference video to adapt, use `reference-video-product-adapter`.

## Workflow

1. Define the research target.
   - Extract product/category, desired visual level, style words, platforms, target duration, geography/language, must-have traits, and hard exclusions.
   - Convert fuzzy words like "高级", "轻奢", "not low-end", or "实拍静物" into observable filters: brand tier, lighting quality, production value, product role, camera language, and reference suitability.
   - Set an explicit count target. If none is given, aim for 10 strong candidates plus rejected-pattern notes.

2. Choose source tiers.
   - Tier 1: brand official sites, campaign pages, official YouTube/Vimeo/Instagram, director/photographer/studio/agency/production-company pages.
   - Tier 2: Vimeo search, 新片场 search, Behance, portfolio sites, press/media pages, curated visual databases.
   - Tier 3: Pinterest, 小红书, generic reposts, social compilations, or image search clues. Use only for discovery until an original or more authoritative `source_url` is found.

3. Search without collecting media files.
   - Use Browser or Chrome when the user asks for logged-in sites or specific browser context.
   - Do not download original images/videos, bypass login/paywalls/DRM, scrape private content, or present inaccessible links as verified.
   - Parallelize independent search lanes only when the task is large enough: platform A, platform B, category C, exclusion-controlled variants.

4. Triage each candidate.
   - Prefer original/official pages over reposts.
   - Reject low-end e-commerce content, tutorials, vlogs, conference videos, low-resolution reposts, unrelated category drift, car-brand false positives, and exact-copy risks.
   - For video, confirm or estimate duration and whether it fits the user's production target.
   - Identify the visual mechanism, not just style adjectives.

5. Return an evidence table.
   - Required fields: `rank`, `title`, `source_url`, `source_type`, `brand_or_creator`, `category`, `static_or_moving`, `duration_if_video`, `why_selected`, `visual_mechanism`, `fit_for_project`, `risks_or_limits`, `confidence`.
   - Include a short rejection summary: what search terms or source types were tried and why they failed.
   - If a repo has `references_index/source_url_index.csv` or a Markdown source-card convention, update it only when the user asks for file changes.

6. State next searches.
   - End with the highest-yield follow-up search directions, not generic "more research needed".
   - If evidence is weak, say so directly and name the missing source tier.

## Delegation Template

Use this shape when dispatching a bounded research subtask:

```text
Role: source-url visual reference researcher.
Target: <category/style/project>.
Sources: <platforms/sites>.
Queries: <query list>.
Hard exclusions: <exclude categories, brands, durations, quality types>.
Output: return only source_url evidence, no downloads. Use rank/title/source_url/source_type/brand_or_creator/category/static_or_moving/duration_if_video/why_selected/visual_mechanism/risks/confidence.
Stop after: <count or time bound>.
```

## Validation

Before presenting the final list:

- open or otherwise confirm each important `source_url` when possible,
- label unverified leads as `unconfirmed_lead`,
- prefer fewer strong references over a long weak list,
- keep source provenance visible enough that a later agent can re-check it.
