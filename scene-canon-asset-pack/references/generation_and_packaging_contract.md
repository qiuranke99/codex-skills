# Generation And Packaging Contract

## Prompt-First Six-Asset Runtime

Freeze Scene Canon, neutral appearance, motion envelope, coverage graph, and all six generation prompts before any image call. Publish the complete six-prompt document inline and bind the publication receipt. Then generate one asset at a time through one fresh non-decision worker per attempt.

For each machine asset:

1. Confirm every predecessor is QA-approved and hash-current.
2. Freeze the ordered reference manifest with `scripts/freeze_reference_bundle.py`; require the Scene-owned schema, exact prompt-plan order, one source first, exact direct predecessors, and asset-scoped frozen bytes; then set `generation_status: spec_frozen`.
3. Spawn one fresh worker and set the queue to the current dependency stage.
4. Resolve the single image call into a runtime-bound worker result.
5. Inspect the real image in the still-running main agent and write an independent inspection receipt.
6. Run `validate_scene_package.py --mode stage --through-asset <ASSET_ID>`; do not advance unless the exact generated prefix, reference bundles, asset/attempt lineage, same-parent publication/inspection ownership, serialization, bytes, dimensions, and dependency approvals pass.
7. On failure, set `repair_required`, invalidate descendants and stale 4K prompts, repair the earliest affected canon/graph state, and retry only with a new worker and revision.
7. On approval, advance to the next stage without user continuation.

The worker's image call is terminal only for the worker turn. It never terminates the main-agent finalizer.

## Independent Generation Rule

Generate `CDM_001`, `SRM_001`, `COV_001`, `COV_002`, `COV_003`, and `SCL_001` as independent full-frame images. Set `independently_generated: true` and `derived_from_multipanel: false`.

Do not generate a grid and crop tiles. `HRB_001` is a derived human-only montage of the six approved assets; set `generation_mode: approved_asset_composite`, `is_machine_asset: false`, exclude it from coverage and 4K mapping, and never use it as a generation reference.

## Required Output Tree

```text
scene-canon-output/
├── 00_manifest/
│   ├── SCENE_CANON.md
│   ├── SCENE_CANON.json
│   ├── SOURCE_APPEARANCE_DECOMPOSITION.md
│   ├── SOURCE_APPEARANCE_DECOMPOSITION.json
│   ├── GENERATION_PROMPTS.md
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
├── 07_review_board/
├── 08_4k_regeneration/
│   └── 4K_ASSET_REGENERATION_PROMPTS.md
├── 09_qa/
│   ├── QA_REPORT.md
│   ├── failed_asset_log.md
│   ├── look_contamination_report.md
│   ├── coverage_graph_report.md
│   └── 4k_prompt_mapping_report.md
└── 10_runtime/
    ├── prompt-publication-receipt.json
    └── <asset-id-lower>/
        ├── reference-manifest.json
        ├── references/
        │   └── <ordered frozen source and predecessor bytes>
        ├── worker-result.json
        └── inspection-receipt.json
```

JSON is machine SSOT. Markdown reports render from the same records. Do not create empty conditional image placeholders.

## Stable Asset Paths

- `CDM_001` → `02_diagnostic_master/canonical_diagnostic_master.png`
- `SRM_001` → `03_spatial_relational_master/spatial_relational_master.png`
- `COV_001` → `04_coverage_plates/coverage_001_left_adjacent.png`
- `COV_002` → `04_coverage_plates/coverage_002_right_adjacent.png`
- `COV_003` → `04_coverage_plates/coverage_003_motion_reveal.png`
- `SCL_001` → `05_scale_landmarks/scale_landmark_depth.png`
- `HRB_001` → `07_review_board/scene_asset_overview_board.png`

Never reuse an asset revision after regeneration. Increment the asset revision and invalidate descendants when its governing bytes change.

## Pixel And Duplicate Evidence

Request the highest native resolution exposed by the active tool, but treat returned pixels as facts. Verify local pixels and record them in both the manifest and `actual_image_dimensions.json`. Set `native_4k_claim: true` only with explicit runtime/file evidence.

Strict delivery rejects identical file bytes and near-identical decoded image content across machine assets regardless of claimed camera pose, reveal, or role. A recolor, re-encode, crop-only, or focal-only variation cannot satisfy a second graph role.

## Cleanliness

Default to horizontal 16:9. Machine assets contain no text, title, number, arrow, legend, watermark, border, collage, grid, UI, palette, logo, person, product, production equipment, temporary prop, or unsupported object.

## State Validation Versus Delivery Validation

`--mode state` validates schema and in-progress consistency. It prints `STATE_VALID_NOT_COMPLETE` for any non-packaged state.

`--mode delivery` is the only completion gate. It requires `package_status: packaged`, queue complete, exactly six approved machine assets, referentially closed graph/path/loop/reveal/evidence records, prompt-first same-parent runtime proof, six asset/attempt-bound worker results, six parent-owned independent inspections, exact structured-QA hash/receipt bindings, six actual files, six asset-specific finalized 4K prompts at the frozen 4K target, and one pixel-rebuilt derived review board. Any planned, awaiting, failed, blocked, stale, duplicate, dangling, placeholder, non-finite, or self-attested-only record exits non-zero.

## Package Status

Use only:

- `draft`
- `prompts_frozen`
- `prompts_published`
- `generating`
- `repair_required`
- `graph_qa_pending`
- `four_k_mapping_failed`
- `packaged`
- `blocked_missing_scene_reference`
- `blocked_exactness_evidence`
- `blocked_prompt_publication`
- `blocked_worker_runtime`
- `hard_blocked_generation_runtime`

`packaged` means delivery validation passed. It does not imply production approval.
