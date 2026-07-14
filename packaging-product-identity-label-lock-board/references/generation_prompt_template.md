# Frozen Generation Prompt Template

Create exactly one clean, photorealistic packaged-product identity asset board for downstream image and video models.

REFERENCE BINDING
- Use exactly {{provider_reference_count}} ordered provider references; never submit more than five paths.
- Reference roles in order: {{provider_reference_roles}}
- Direct complete-product anchors and deterministic detail sheets are different evidence roles. Preserve the source identities represented inside every declared sheet.

OUTPUT
- One horizontal 16:9 board only.
- Requested final design canvas: 3840 x 2160.
- Eight complete, uncropped product views: front, back, left side, right side, front three-quarter, rear three-quarter, high angle, low angle.
- Keep every bottle upright on its base. High angle and low angle describe camera position; never lay the product down.
- Below the eight-view grid, render exactly {{detail_count}} fully populated, edge-to-edge photographic macro panels in one lower evidence strip.
- Populate the detail panels in this exact order: {{detail_panel_list}}
- Derive every macro panel from visible evidence in the supplied references. Every panel must contain clearly visible product evidence at generation time.
- Neutral white or very light gray studio background, soft even light, consistent scale and spacing.

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
- Major exact source-visible copy: {{major_copy}}
- Logos, graphics, ornaments, borders, codes: {{graphics}}
- Texture, embossing, debossing, seams, base: {{surface_features}}

EVIDENCE BOUNDARIES
- Source-observed views: {{source_observed_views}}
- Bounded completion views: {{bounded_completion_views}}
- Unknown or unverified regions: {{unknown_regions}}
- Do not invent readable microcopy, barcode payloads, QR modules, certification marks, or hidden label panels.
- Preserve label color, scale, placement, border, ornament, logo silhouette, and major identity copy from the references.
- Keep unreadable dense microcopy visually quiet rather than fabricating plausible characters.

CLEAN-BOARD BANS
- No heading, title, asset name, view name, angle label, number, arrow, callout, legend, date, status, table, UI, caption, watermark, or non-product text.
- No props, hands, splashes, scenery, duplicate SKU, alternate packaging, campaign styling, or packaging redesign.
- No cropped product views and no merged or overlapping products.
- No blank cells, empty rectangles, placeholders, reserved slots, future-fill boxes, wireframes, unused panels, or drawn empty borders anywhere.

This prompt must produce one independently usable, fully populated sparse-reference video identity board in a single image-generation call. It is not a 360-degree scan, print proof, dieline, or continuous rotation Canon.
