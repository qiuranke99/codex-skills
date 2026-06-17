# Evidence Schema

Use this schema for Markdown tables, CSV rows, or JSON records. Keep it as the single source of truth for output fields; do not duplicate a different field list in `SKILL.md`.

## Evidence Row

Required for every ranked final reference:

- `rank`
- `route_mode`: `image_reference`, `video_reference`, or `mixed_reference`
- `title`
- `source_url`: evidence page, not a downloaded file
- `final_url`: URL after redirects, or blank with a stated reason
- `source_type`: brand, photographer, director, studio, agency, production_company, editorial, Behance, Instagram, Vimeo, YouTube, Xinpianchang, archive, repost_clue, other
- `source_tier`: `tier_1_original`, `tier_2_professional_platform`, or `tier_3_discovery_clue`
- `brand_or_creator`
- `category`
- `static_or_moving`: `static`, `moving`, or `mixed`
- `duration_if_video`
- `duration_basis`: observed, platform_metadata, estimated, unknown, or not_applicable
- `access_status`: see labels below
- `verification_method`: browser, chrome_logged_in, script_head_get, platform_api, manual_open, search_snippet_only
- `checked_at`: ISO timestamp or exact local date/time
- `why_selected`
- `visual_mechanism`
- `reference_role`: direct_category, product_still_life, macro_detail, material_texture, lighting_mood, set_design, application_gesture, edit_motion, analogy_form_factor, analogy_material, other
- `adaptation_takeaway`
- `do_not_copy`
- `fit_for_project`
- `risks_or_limits`
- `confidence`: see labels below

## Image Download Manifest

Required when an image pack is created:

- `rank`
- `title`
- `source_url`
- `image_url`: direct image or preview asset URL, if available
- `download_path`: local path relative to the pack directory
- `sidecar_path`
- `download_status`: downloaded, duplicate_exact, duplicate_near, skipped_not_allowed, skipped_no_direct_image_url, skipped_login_gated, skipped_hotlink_blocked, skipped_license_unknown, failed_unreachable, failed_bad_content_type, failed_corrupt_image, failed_too_large, pending_manual_review
- `download_error`
- `content_type`
- `dimensions_px`
- `bytes`
- `sha256`
- `duplicate_of`
- `capture_method`: direct_url, og_image, twitter_image, html_img, browser_save, manual_review
- `source_page_verified`: true, false, or partial
- `license_status`: explicitly_allowed, editorial_reference_only, unknown, prohibited, platform_restricted, or requires_permission
- `rights_or_usage_note`
- `is_thumbnail_or_full_res`
- `checked_at`
- `error`

## Search Audit

Include this after the evidence table:

- `route_decision`
- `image_pack_path`: required for `image_reference`, unless user explicitly requested links-only/no-download
- `image_pack_summary`: source_count, candidate_count, downloaded_count, failed_count, skipped_count
- `query_lanes`
- `queries_tried`
- `hard_exclusions`
- `rejected_patterns`
- `unconfirmed_leads`
- `missing_source_tiers`
- `next_searches`

## Access Status Labels

- `ok`: source page opened and is usable.
- `redirected`: source page redirects but final page is usable.
- `redirect_target_mismatch`: redirect leads to a home page, login page, unrelated project, or unrelated domain.
- `soft_404`: HTTP 200 page that says content is missing, removed, or unavailable.
- `browser_verified`: verified in a real browser, often needed for JavaScript-heavy pages.
- `browser_verified_login_context`: visible in a logged-in browser session; public unauthenticated access is not confirmed.
- `forbidden`: 401/403 or blocked access.
- `login_required`: login required to confirm the content.
- `paywalled`: meaningful reference is behind a paywall.
- `not_found`: 404/410 or removed page.
- `unreachable`: timeout, DNS, TLS, or network failure.
- `server_error`: 5xx response.
- `rate_limited`: 429 or similar platform throttling.
- `dynamic_unverified`: page likely requires browser rendering and script verification was inconclusive.
- `blocked_asset`: page exists but image/media asset cannot be retrieved.
- `unverified`: not checked; cannot appear as a verified final row.

## Confidence Labels

- `verified`: original/professional source page is reachable and visual relevance was checked.
- `browser_verified_partial`: visible in browser but public/script verification is limited.
- `probable`: plausible source, but originality, access, or fit is not fully proven.
- `unconfirmed_lead`: discovery clue only; needs original source confirmation.
- `rejected`: kept only as a negative example or search-path note.

## Source Rules

- Use the original brand, creator, studio, agency, production company, photographer, director, editorial, or platform project page when available.
- Keep reposts only as clues unless the original source cannot be found.
- Never treat downloaded media files as the evidence source. The evidence is the page URL plus verification metadata.
- Include access limitations instead of hiding them: login required, region blocked, removed, private, paywalled, low resolution, thumbnail only, or duration unknown.
