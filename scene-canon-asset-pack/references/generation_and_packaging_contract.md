# Generation And Packaging Contract

## Per-Asset Terminal State Machine

For each machine asset:

1. Freeze the asset-specific generation specification and set `terminal_generation_call: pending`.
2. Call built-in image generation. The image call is the final action of that turn.
3. Treat the returned result as `stage_complete`, not package or task completion.
4. In a later continuation, set `terminal_generation_call: executed`, verify file/provenance, record actual pixel dimensions, and set `pending_post_generation_inspection`.
5. Perform later-turn visual QA. On failure, set `repair_required`, invalidate the asset's old 4K prompt, repair the earliest affected canon/appearance state, and regenerate only that asset.
6. Set `assistant_qa_status: approved` only after inspection. Keep `production_approval_status` separate.

Never emit additional assistant text after the terminal image call. Never mark `packaged` merely because the generator returned an image. Generate and inspect one machine asset at a time when the active runtime requires terminal calls.

## Independent Generation Rule

Generate every Canonical Diagnostic Master, Spatial / Relational Master, Coverage Plate, Scale/Landmark asset, and Intrinsic Scene State asset as an independent full-frame image. Set `independently_generated: true` and `derived_from_multipanel: false`.

Do not generate a grid/contact sheet and crop tiles into machine assets. The Human Review Overview Board is a derived human-only montage of approved independent assets; set `generation_mode: approved_asset_composite` and `is_machine_asset: false`, exclude it from 4K one-to-one mapping, and never use it as a primary generation reference.

## Required Output Tree

```text
scene-canon-output/
├── 00_manifest/
│   ├── SCENE_CANON.md
│   ├── SCENE_CANON.json
│   ├── SOURCE_APPEARANCE_DECOMPOSITION.md
│   ├── SOURCE_APPEARANCE_DECOMPOSITION.json
│   ├── ASSET_INDEX.md
│   ├── ASSET_MANIFEST.json
│   └── actual_image_dimensions.json
├── 01_source_analysis/
│   ├── source_evidence_report.md
│   ├── conflict_report.md
│   └── coverage_assessment.md
├── 02_diagnostic_master/
├── 03_spatial_relational_master/
├── 04_coverage_plates/
├── 05_scale_landmarks/
├── 06_intrinsic_scene_state/        # only when required
├── 07_review_board/
├── 08_4k_regeneration/
│   └── 4K_ASSET_REGENERATION_PROMPTS.md
└── 09_qa/
    ├── QA_REPORT.md
    ├── failed_asset_log.md
    ├── look_contamination_report.md
    └── 4k_prompt_mapping_report.md
```

Do not create empty image placeholders for conditional modules. Treat JSON files as machine SSOT; render Markdown indexes and reports from the same records rather than maintaining contradictory copies.

## Asset Naming

Use stable uppercase asset IDs and lowercase filenames:

- `CDM_001` → `02_diagnostic_master/canonical_diagnostic_master.png`
- `SRM_001` → `03_spatial_relational_master/spatial_or_relational_master.png`
- `COV_001` → `04_coverage_plates/coverage_001_<view-role>.png`
- `LND_001` → `05_scale_landmarks/landmark_001_<landmark>.png`
- `SCL_001` → `05_scale_landmarks/scale_001_<relation>.png`
- `STA_001` → `06_intrinsic_scene_state/state_001_<state>.png`
- `HRB_001` → `07_review_board/scene_asset_overview_board.png`
- `4K_<ASSET_ID>` → corresponding prompt record.

Never reuse an asset ID for a regenerated file version. Increment `scene_canon_version` or `neutral_appearance_version` when the governing facts change and mark previous prompt mappings stale.

## Pixel Evidence

Request the highest native resolution exposed by the active tool, but treat the returned dimensions as facts. Verify each local image's pixels and write them to `actual_image_dimensions.json` and `ASSET_MANIFEST.json`. Set `native_4k_claim: true` only with explicit runtime/file evidence; width or height labels, requested size, or a 4K prompt are not evidence.

## Default Ratios And Cleanliness

Default ordinary plates to horizontal 16:9. Use 2:1 only for a true panorama; use an information-appropriate ratio for plan, topology, or multi-scale system assets. Machine assets contain no text, title, number, arrow, legend, watermark, border, collage, grid, UI, palette, logo, person, product, production equipment, temporary prop, or unsupported object.

## Package Status

Use only:

- `draft`
- `generating`
- `awaiting_post_generation_continuation`
- `pending_post_generation_inspection`
- `repair_required`
- `four_k_mapping_failed`
- `packaged`
- `blocked_missing_scene_reference`
- `blocked_exactness_evidence`
- `hard_blocked_generation_runtime`

`packaged` requires all approved machine assets to have actual-dimension evidence, passed QA, and exactly one finalized 4K prompt.
