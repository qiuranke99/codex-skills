# Frozen Generation Prompt Template

Create exactly one clean, photorealistic packaged-product identity asset board for downstream image and video models.

REFERENCE BINDING
- Use exactly {{provider_reference_count}} ordered provider references; never submit more than five paths.
- Reference roles in order: {{provider_reference_roles}}
- Direct complete-product anchors and deterministic detail sheets are different evidence roles. Preserve the source identities represented inside every declared sheet.

OUTPUT AND BORDERLESS TOPOLOGY
- One horizontal 16:9 board only. Requested final design canvas: 3840 x 2160.
- Use one continuous seamless white or very light gray studio background across the entire canvas.
- Default to exactly nine open-spaced product regions; ten is the absolute maximum. No drawn grid, panel border, white rectangular frame, card outline, evidence strip, divider line, or boxed cell.
- Render exactly seven complete, uncropped product views: front, back, one evidence-supported side, side 45-degree high-angle, side 45-degree low-angle, top-down full product, and low-up full product.
- Keep every product complete and upright on its base. High, low, top-down, and low-up describe camera position; never lay the product down.
- Render exactly {{detail_count}} source-grounded close-ups, where detail_count is two by default and never exceeds three.
- Populate close-ups in this exact order: {{detail_region_list}}.
- The first close-up is closure/top evidence. The second is the highest-risk local identity detail, normally a label/copy, embossing, texture, base, or code region. Use an optional third only for a distinct source-evidenced risk.
- Blend every close-up into the same continuous background using open spacing. Every region must already contain useful product evidence at generation time.
- Soft even studio light, consistent product identity, enough breathing room for readability, no overlap, no crop.

PRODUCT IDENTITY LOCK
- SKU / variant: {{sku_variant}}
- Silhouette and proportions: {{silhouette}}
- Closure / pump / cap: {{closure}}
- Nozzle orientation in product coordinates: {{nozzle_orientation}}
- Container material and finish: {{container_material}}
- Fill color and liquid level: {{fill_and_liquid}}
- Internal tube or components: {{internal_components}}
- Front label architecture: {{front_label}}
- Back label architecture: {{back_label}}
- Logos, graphics, ornaments, codes: {{graphics}}
- Texture, embossing, debossing, seams, base: {{surface_features}}

COPY CONTRACT — EMBED VERBATIM BELOW
{{copy_contract_block}}

COPY RENDERING RULES
- The embedded copy contract contains every OCR/transcription line, its region, source binding, status, format, and reading order.
- Render only APPROVED EXACT strings as readable text and preserve them verbatim. Never transform a CANDIDATE or UNRESOLVED line into readable product copy.
- Do not invent pseudo-Chinese, pseudo-Latin, fake digits, fake barcode values, fake QR modules, certification marks, or hidden label text.
- Prompt inclusion improves content/order control but is not pixel proof. Critical readable copy must remain source/artwork-backed in the accepted board.

EVIDENCE BOUNDARIES
- Source-observed views: {{source_observed_views}}
- Bounded completion views: {{bounded_completion_views}}
- Unknown or unverified regions: {{unknown_regions}}
- Preserve label color, scale, placement, border, ornament, logo silhouette, graphics, and embossing from the references.
- Keep unresolved microcopy non-readable and visually quiet; do not fill it with invented glyphs.

CLEAN-BOARD BANS
- No heading, title, asset name, view name, angle label, number, arrow, callout, legend, date, status, table, UI, caption, watermark, or non-product text.
- No props, hands, splashes, scenery, duplicate SKU, alternate packaging, campaign styling, or packaging redesign.
- No cropped, merged, overlapping, or lying-down product views.
- No blank cells, empty rectangles, placeholders, reserved slots, future-fill boxes, wireframes, unused panels, or drawn empty borders anywhere.
- No white frames, grid lines, panel outlines, card containers, evidence-strip boxes, or visual dividers.

This prompt must produce one independently usable, fully populated, borderless sparse-reference video identity board in a single image-generation call. It is not a 360-degree scan, print proof, dieline, or continuous rotation Canon.
