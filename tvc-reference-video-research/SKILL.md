---
name: tvc-reference-video-research
description: "Use when finding precise TVC-grade reference videos, commercial reference films, 广告参考片, 竞品广告片, cankaopian, Vimeo/YouTube/新片场 references, director/production-company source links, or model-led product film examples from a product, service, brand, or campaign brief."
---

# TVC Reference Video Research

## Overview

Find source-backed, TVC-grade reference videos from a commercial brief. Work as a hybrid TVC Reference Creative Director: brand strategist for fit, agency creative director for advertising logic, commercial film director for craft, and producer for source/production realism.

The output is not a list of attractive links. It is a ranked evidence set that explains which references are direct competitors, adjacent category references, or craft analogies; what to borrow; what not to copy; and what remains unverified.

## Boundaries

- Use this skill when the center of gravity is finding precise reference films before ideation, pitching, scripting, storyboard work, or shooting.
- If the user already provides one specific reference video and asks to adapt it, use `reference-video-product-adapter`.
- If the task is broad visual source research with image packs, use `source-url-reference-research`.
- If the task is a whole local project folder, brief, budget, selling points, and production handoff, use `commercial-video-project-planning`.
- Do not download videos. Return source pages and verification notes.
- Do not bypass login, private accounts, paywalls, DRM, region blocks, or hotlink restrictions. Label access limits.
- Do not call a reference `verified` unless the source page was opened or browser-verified and the video relevance was actually checked.
- Use `probable` only when the source and relevance are plausible but a key fact remains incomplete, such as partial viewing, duration uncertainty, or JS-heavy platform access. State the missing proof.

## Resource Map

Read only what is needed:

- Source priority and platform caveats: `references/tvc-source-tiers.md`.
- Query lanes, platform grammar, and anti-noise filters: `references/tvc-query-lanes.md`.
- TVC-grade scoring, role taxonomy, and failure modes: `references/tvc-fit-rubric.md`.
- Required report fields and final template: `references/tvc-output-schema.md`.
- Report validator: `scripts/validate_tvc_reference_report.py`.

## Workflow

1. Parse the brief into observable search requirements.
   - Extract product/category, competitor set, brand tier, geography/language, target duration, platform, scene, talent/model requirements, product action, texture/material needs, lighting mood, and hard exclusions.
   - Translate vague words like premium, lifestyle, cinematic, high-end, natural, intimate, or TVC into observable filters: source credibility, single-work page, model performance, product role, shot structure, lighting, art direction, edit rhythm, and source tier.
   - For underspecified but workable briefs, proceed with explicit assumptions. Ask only when missing product identity, geography, target duration, or mandatory/forbidden style would materially change the search.

2. Build a reference target matrix before searching.
   - `direct_competitor`: same product category, similar scene/use case, similar commercial task.
   - `adjacent_category`: neighboring category that supplies missing model, ritual, product-use, or brand-world evidence.
   - `craft_analogy`: not the same category; useful for one mechanism such as oil texture, skin highlight, macro liquid, hand gesture, camera movement, light, edit rhythm, or sound.
   - `rejected_noise`: tutorials, reviews, UGC, shopping pages, stock footage, AI renders, ad compilations, showreels, case films, and weak reposts.

3. Run at least five query lanes unless the brief explicitly narrows the task.
   - Direct category lane.
   - Competitor brand lane.
   - Creator/director/production-company lane.
   - Visual-mechanism lane.
   - Original-source recovery lane from weak clues.
   - Add Chinese/English/local-language variants when useful.
   - Read `references/tvc-query-lanes.md` for grammar and negative filters.

4. Verify source-first.
   - Prefer single-work pages from brand, director, production company, agency, DOP/editor/colour house, official Vimeo/YouTube, 新片场 creator pages, LBB/shots/Ads of the World, or similar accountable sources.
   - Treat YouTube reposts, Vimeo compilations, 新片场 blocked pages, ad archives without embedded playable video, social posts, and award/case pages as clues until the actual single-work source is confirmed.
   - For 新片场 pages that return blocked, blank, 406, or script-heavy responses, try browser verification; otherwise keep them as `unconfirmed_lead` or clearly limited `probable` and recover the creator/brand source elsewhere.
   - Record `source_url`, `final_url`, `source_type`, `source_tier`, `video_kind`, `duration_sec`, `duration_basis`, `access_status`, `verification_method`, and `checked_at`.

5. Triage like a commercial director.
   - Identify why each candidate is useful: product role, model performance, application gesture, texture proof, lighting, set/props, camera movement, edit rhythm, packshot, sound, or end-frame authority.
   - Reject beautiful but strategically wrong references. A fashion film with no product causality is not a body-oil TVC reference; a liquid macro render is only craft analogy; a hair-oil ad is not direct body-oil evidence.
   - Score candidates with `references/tvc-fit-rubric.md`; rank by fit and source confidence, not by search order.

6. Return two layers of evidence.
   - User-facing table: 5-12 strong references, compact enough to scan.
   - Complete evidence record: JSON/CSV-ready fields from `references/tvc-output-schema.md` when the task warrants durable output.
   - Include `unconfirmed_leads` and `rejected_candidates` separately. Never mix them into the final ranked reference table.
   - End with high-yield next searches, not generic "more research needed".

## Final Ranking Gates

Final ranked references may include only:

- `candidate_status`: `verified`, `browser_verified`, `browser_verified_partial`, `browser_verified_login_context`, or carefully labeled `probable`.
- `video_kind`: usually `single_work` or `official_cut`.
- `brief_fit`: `direct_category`, `adjacent_category`, or `craft_analogy`.

Final ranked references must not include:

- `candidate_status`: `unconfirmed_lead`, `rejected`, `inaccessible`, or `out_of_scope`.
- `video_kind`: `showreel`, `reel`, `compilation`, `bts`, `making_of`, `tutorial`, `review`, or `case_study`.
- Search result URLs, thumbnails, raw CDN URLs, video files, product pages with no confirmed video, or "seen in snippet" guesses.

## Body Oil Example

For a premium indoor model-led body-oil TVC brief, do not stop at `body oil commercial`. Build lanes such as:

- direct: `body oil`, `dry oil`, `skin oil`, `bath & body oil`, `vitamin E body oil`;
- competitors: NUXE, Bio-Oil, Palmer's, L'Occitane Almond, OSEA, Clarins, Neutrogena, NIVEA;
- adjacent: body lotion, body serum, sunscreen oil, hair oil, spa/wellness, fragrance ritual;
- mechanisms: oil texture, skin glow, hand application, body macro, liquid droplet, bathroom/window light, towel/linen skin contact;
- creators: director, production company, DOP, beauty film, product film, TVC, campaign film.

Label hair-oil, fragrance, or fashion references as analogies unless their product role and body-care logic truly match the brief.

## Validation

When saving a Markdown or JSON report, validate before claiming it is ready:

```bash
python scripts/validate_tvc_reference_report.py <report.md-or-json>
```

For skill maintenance:

```bash
python -m unittest discover -s tests -v
python -m py_compile scripts/validate_tvc_reference_report.py
python C:/Users/Administrator/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

## Delegation Template

Use this for parallel research lanes:

```text
/goal: Find verified TVC-grade source_url video references for <brief slice>.
Role: TVC reference researcher with source-first verification.
Lane: <direct_category | competitor_brand | creator_source | visual_mechanism | original_source_recovery>.
Target: <product/category/scene/model/craft requirement>.
Sources: <Vimeo, YouTube, 新片场, LBB, shots, Ads of the World, brand, agency, director, production-company sites>.
Queries: <specific queries with negative terms>.
Hard exclusions: reviews, tutorials, UGC, shopping pages, stock, AI renders, showreels, compilations, BTS, case films unless explicitly requested.
Verification: open or browser-verify every final source_url; unverified leads stay separate.
Output: ranked candidates using tvc-output-schema fields plus search audit; include rejected patterns and next searches.
Stop after: <count/time bound>.
```
