# Search Playbook

Use this reference when the brief needs high-end/professional source coverage, especially beauty, skincare, fragrance, luxury, jewelry, fashion accessories, cosmetics, and product still life.

## Source Tiers

### Tier 1: original or accountable sources

- Brand/campaign/product editorial pages and official social posts.
- Photographer, director, stylist, set designer, retoucher, studio, agency, or production-company portfolio pages.
- Official Vimeo, YouTube, Instagram, Behance, Xinpianchang, Bilibili, or Weibo uploads from the brand or creator.
- Editorial pages that credit the production team and host the actual image/video.

### Tier 2: professional platforms and portfolios

- Behance project pages; Instagram creator posts; Vimeo staff/creator uploads.
- Photographer directories and portfolio networks: AtEdge, Production Paradise, Wonderful Machine, Workbook, Luerzer's Archive, The Dots, Le Book, PhotoVogue, Models.com, Art Partner, CLM, Management Artists, Streeters, Cadence, Walter Schupfer, See Management.
- Commercial/film sources: Little Black Book, shots, Directors Library, Stash, Nowness, Campaign, Ads of the World, agency/production-company reels. Treat compilation pages as clues unless they link to the original.

### Tier 3: discovery clues only

- Pinterest, Are.na, Savee, Xiaohongshu, generic inspiration blogs, search image tabs, repost accounts, shopping pages, stock sites.
- Use these to identify creators, campaign titles, or visual mechanisms; then search for original/professional pages.

## Query Grammar

Build lanes. Do not run only brand/product queries.

### Direct category lane

```text
("eyeliner" OR "eye pencil" OR "liquid eyeliner" OR "gel eyeliner") ("product photography" OR "still life" OR "beauty photography" OR "cosmetics photography") -tutorial -review -amazon -ebay -stock -render -mockup -AI
```

Use local-language variants when useful:

```text
("eye pencil" OR eyeliner OR "liquid liner") ("campaign" OR "still life" OR "beauty editorial")
("yan xian bi" OR "yan xian ye") ("chan pin she ying" OR "jing wu" OR "mei zhuang she ying")
```

### Creator/professional-source lane

```text
site:behance.net (eyeliner OR cosmetics OR beauty) "product photography"
site:instagram.com/p (eyeliner OR "eye pencil" OR cosmetics) (photographer OR "still life" OR "set design")
site:vimeo.com (beauty OR skincare OR cosmetics OR luxury) (film OR campaign OR director)
site:productionparadise.com beauty "still life photographer"
site:at-edge.com cosmetics photographer
site:wonderfulmachine.com cosmetics photographer
```

### Visual-mechanism lane

```text
("black cosmetic pencil" OR "slim cosmetics tube" OR "makeup pencil") ("macro" OR "tip detail" OR "swatch" OR "texture")
("cosmetics still life") ("hard shadow" OR "specular highlight" OR "wet texture" OR "black lacquer" OR "chrome")
("beauty product photography") ("set design" OR "monochrome" OR "editorial still life" OR "floating product")
```

### Video lane

```text
site:vimeo.com (beauty OR skincare OR cosmetics OR fragrance) ("campaign film" OR "product film" OR "director")
site:xinpianchang.com (beauty OR skincare OR cosmetics) (TVC OR film OR campaign)
site:lbbonline.com beauty campaign film director
site:shots.net cosmetics campaign film
```

### Original-source recovery lane

When a strong image is found on a weak source:

```text
"<exact campaign title>" photographer
"<brand>" "<product>" "photographer"
"<creator name>" "<brand>" beauty
reverse image search in browser if available, then verify the original page
```

## Eyeliner / Eye-Pencil Coverage Matrix

For an eyeliner brief, build a balanced set instead of collecting only product shots.

| Reference Role | What To Look For | Query Additions |
| --- | --- | --- |
| product_still_life | premium hero object, cap/body geometry, box or applicator role | still life, cosmetics product photography, hero |
| macro_detail | tip, nib, brush, pencil point, pigment edge | macro, tip detail, close-up, applicator |
| material_texture | black lacquer, matte plastic, chrome, pigment smear, skin swatch | texture, swatch, smear, black glossy, matte |
| lighting_mood | hard shadow, rim light, low key, editorial contrast | hard shadow, low key, specular, reflection |
| set_design | surface, plinth, prop, monochrome world, architectural stage | set design, plinth, monochrome, geometry |
| analogy_form_factor | lip liner, brow pencil, mascara, luxury pen, slim cylindrical object | slim tube, pencil cosmetics, form factor |
| application_gesture | eye area, hand gesture, line drawing, model crop | application, eye detail, gesture, makeup artist |

## Platform Caveats

- Instagram can be visually excellent but often login-gated, region-sensitive, and weak for stable direct image URLs. Use it for creator discovery and browser-verified links; capture public source URL and creator handle, not CDN-only URLs.
- Behance projects are usually better for stable source pages and downloadable previews, but image assets may be resized. Prefer the project page as evidence.
- Vimeo and Xinpianchang are stronger for moving references. Confirm duration and whether the upload is official, creator-owned, or a repost.
- Brand product detail pages are useful for SKU truth but often poor visual references. Do not over-index on them unless the user asks for product accuracy.
- Stock and AI-render sites are usually rejected unless the user explicitly asks for stock/AI references.
