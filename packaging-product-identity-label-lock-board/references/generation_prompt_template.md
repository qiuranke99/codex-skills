# Frozen Generation Prompt Template

Create exactly one clean, photorealistic packaged-product identity asset board for downstream image and video models.

OUTPUT
- One horizontal 16:9 board only.
- Requested final design canvas: 3840 x 2160.
- Eight complete, uncropped product views: front, back, left side, right side, front three-quarter, rear three-quarter, high angle, low angle.
- Reserve four to six clean detail windows in a lower evidence strip. These windows will be replaced with source-derived evidence crops after generation.
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

This is one sparse-reference video identity board. It is not a 360-degree scan, print proof, dieline, or continuous rotation Canon.
