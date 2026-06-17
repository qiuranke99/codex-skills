# TVC Source Tiers

Use this reference when judging whether a video source is reliable enough for a ranked TVC reference table.

## Tier 1: Original Or Accountable Sources

Prefer these for final references:

- Brand official campaign/product-film page or official YouTube/Vimeo upload.
- Director, production company, agency, DOP, editor, colour house, sound studio, or post house single-work page.
- New campaign pages from accountable industry sources when they host or link the actual film.
- 新片场 creator/company pages when the single work is visible or browser-verified.

Tier 1 can still fail if the page is inaccessible, the video is a showreel, the duration is unknown, or the work is not relevant to the brief.

## Tier 2: Professional Platforms And Archives

Use as final references only when the actual video and credits can be checked:

- Vimeo or YouTube creator uploads.
- Little Black Book, shots, Ads of the World, Directors Library, Stash, agency archives, and award pages.
- Behance or portfolio projects that include a playable film or a credible link to the film.

These are often best used as credit graphs: identify campaign title, director, production company, agency, DOP, editor, colour house, or original upload, then recover the single-work source.

## Tier 3: Discovery Clues Only

Do not promote these to final references unless no better source exists and the row is clearly labeled as a clue:

- Pinterest, Xiaohongshu, generic repost pages, ad compilations, listicles, "best commercials" videos, and social repost accounts.
- Shopping pages, e-commerce product videos, marketplace pages, affiliate pages, stock sites, AI render galleries, templates, and mood-board saves.
- Search snippets, thumbnails, CDN media URLs, and video files detached from a source page.

## Video Kind Labels

Use these consistently:

| Label | Final Table? | Meaning |
| --- | --- | --- |
| `single_work` | yes | A standalone commercial/product film page. |
| `official_cut` | yes | Official 15/30/45/60s cutdown or master. |
| `director_cut` | maybe | Useful if clearly labeled; note if not the broadcast cut. |
| `case_study` | no by default | Use as clue unless the user requested case studies. |
| `showreel` / `reel` | no | Use only to discover single works. |
| `compilation` | no | Not a precise reference. |
| `bts` / `making_of` | no by default | Production clue, not final reference. |
| `tutorial` / `review` / `ugc` | no | Consumer/noise source. |

## Access And Verification Labels

- `verified`: source page opened and video relevance checked.
- `browser_verified`: browser was needed for JavaScript-heavy pages; content was visible.
- `browser_verified_login_context`: visible only in logged-in context; public access unconfirmed.
- `probable`: source chain and relevance look plausible, but one critical fact remains unproven. Use this when the source page opens but the video was not fully watched, duration is incomplete, official ownership is not fully proven, or the work needs second-pass browser/creator verification. Do not present `probable` rows as shoot-ready references.
- `unconfirmed_lead`: useful clue; never a final ranked reference.
- `rejected`: inspected and excluded; include reason.

## Platform Caveats

- Vimeo has many high-quality director/production-company uploads, but also passworded videos, director cuts, and vague titles. Account owner and page notes matter.
- YouTube has strong official brand uploads and the highest noise. Ordinary reposts and ad compilations are clues, not final evidence.
- 新片场 is useful for Chinese commercial directors and production companies, but pages may be JavaScript-heavy, blocked, or semi-private. Browser verification may be required.
- LBB, shots, Ads of the World, Directors Library, and award pages are strong for credits but may not host the exact film or may be paywalled.
- Brand product pages can prove product truth, but they are not TVC references unless an actual playable film is confirmed.

## 新片场 Blocked Or JS-Heavy Pages

If a 新片场 URL returns HTTP 406, blank content, script-only HTML, login gating, or inconsistent access:

1. Try a real browser if available and label the result `browser_verified` or `browser_verified_login_context`.
2. If browser verification is unavailable, keep the row as `unconfirmed_lead` or `probable` only when a creator/company page, title, duration, thumbnail, and category strongly align.
3. Recover the source by searching the exact Chinese title, brand, director, production company, and account name on Vimeo, YouTube, brand pages, agency pages, and general search.
4. Prefer the creator/company portfolio page over a blocked single-work URL when it exposes the work list and credits.
5. Never treat a blocked 新片场 page as `verified` merely because a search result snippet names the work.

Encoding note: all Chinese query examples in this skill are UTF-8. If they appear garbled, reload the file as UTF-8 before copying queries.

## Source Anchors

- Google Advanced Search documents exact phrase, unwanted words, and site/domain constraints: https://www.google.com/advanced_search
- YouTube Help documents platform search filters: https://support.google.com/youtube/answer/111997
- Cannes Lions Film and Film Craft categories are useful external anchors for separating advertising idea, execution, and craft: https://www.canneslions.com/awards/lions/film/what-you-need-to-know and https://www.canneslions.com/awards/lions/film-craft/what-you-need-to-know
