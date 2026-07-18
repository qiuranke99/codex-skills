# Package Contract V2

Use this contract to initialize, update, validate, and deliver `Complex_Product_Identity_Asset_Package/`.

## 1. File Tree

```text
Complex_Product_Identity_Asset_Package/
  01_Product_Identity_Specification.md
  02_Geometry_Camera_Coverage/
    camera_assets/
      <camera-id>.(png|jpg|jpeg)              # only accepted/under-QA assets
    camera_coverage_report.md
    geometry_contact_sheet.png                # optional derived summary only
  03_Material_Surface_Lock/
    material_surface_lock_board.png            # conditional
  04_Component_Detail_Lock/
    component_detail_lock_board.png            # conditional
  05_State_Transition_Lock/
    state_transition_lock_board.png            # conditional
  06_Marking_Identity_Lock/
    marking_identity_lock_board.png             # conditional
  07_Primary_Upload_Bundle/
  08_4K_Upscale_Prompts.md
  asset_package_manifest.json
```

Empty conditional directories are allowed. Do not add placeholder images. `07_Primary_Upload_Bundle/` is a manifest-selected logical bundle; do not duplicate accepted image bytes into it.

## 2. Schema And Migration

Use `complex_product_identity_asset_package.v2`.

Version 1 represented Geometry as one generative multi-view board. That asset cannot be automatically decomposed into independently evidenced camera assets. The v2 validator rejects v1 and requires Stage 1 camera re-analysis; do not relabel a v1 board as v2 coverage.

## 3. Root Manifest

Required root fields:

- `schema_version`, `asset_id`, `package_status`;
- `identity_specification`, `identity_specification_sha256`;
- `source_bundle_sha256`, `camera_coverage_report`;
- `unresolved_hard_conflicts`;
- `geometry_coverage`, `diagnostic_boards`, `primary_upload_bundle`;
- `four_k_prompt_file`, `four_k_prompts`;
- `approved_asset_count`, `four_k_mapping_count`;
- `production_approval_status`.

Use SHA-256 lowercase hex. Keep `production_approval_status` separate from assistant QA: `not_granted`, `user_granted`, or `external_pipeline_granted`.

## 4. Geometry Coverage Record

`geometry_coverage` contains:

- `coverage_id: geometry_camera_coverage`;
- `directory: 02_Geometry_Camera_Coverage`;
- `status: planned | generation_in_progress | partial_approved | approved | blocked`;
- frozen `camera_plan_sha256`;
- unique `target_camera_ids`;
- `minimum_video_ready_camera_count` from 4 through 6;
- one `camera_assets` record per target;
- computed `coverage_metrics`;
- optional `contact_sheet` record.

Do not manually claim metrics that the accepted files do not support.

### Camera Record

Each target requires:

- `camera_id`, `role`;
- `pose_bin.azimuth`, `pose_bin.elevation`, `pose_bin.shot_size`;
- `coverage_sectors`, `critical_node_ids`;
- `source_gate`, `source_gate_reasons`, `source_ids`;
- `evidence_mode`, `identity_authority`;
- `status`, `attempt_count`, `terminal_generation_call`;
- `asset_file`, `asset_sha256`, `source_asset_sha256`, `provenance_sha256`;
- `actual_dimensions`, `generation_prompt_sha256`;
- camera QA and `failure_flags`.

Evidence modes:

- `source_copy`: hard authority; exact asset/source byte hashes must match; no generation prompt.
- `verified_source_render`: hard authority; frozen render provenance required; no image-generation prompt.
- `source_aligned_generation`: auxiliary authority; prompt hash and executed call required.
- `bounded_reconstruction`: auxiliary authority; prompt hash and executed call required.
- `blocked` or `unassigned`: no authority and cannot be approved.

An approved camera requires an existing PNG/JPEG, actual decoded dimensions matching the manifest, observed asset SHA-256 matching bytes, sources, Critical Nodes, source gate approval, all camera QA passes, and zero failure flags.

### Coverage Metrics

Record exact derived values:

- `approved_camera_count`;
- `hard_authority_camera_count`;
- `unique_pose_bin_count`;
- `covered_sectors`;
- `elevation_bands`;
- `redundancy_count` from duplicate bytes plus duplicate pose bins;
- `coverage_tier: none | source_aligned | multi_camera | full`.

`approved` Geometry requires at least the frozen minimum hard-authority cameras, at least that many unique pose bins, front/rear/side sector coverage, and zero redundancy. `partial_approved` contains one or more accepted cameras but fails the video-ready hard-authority gate.

### Contact Sheet

A contact sheet is optional. If present:

- use PNG;
- derive it only from at least two approved camera IDs;
- record its byte hash;
- keep `identity_authority: none`;
- never count it as a camera, approved asset, or 4K-mapped identity source.

## 5. Diagnostic Board Records

Use these four IDs:

- `material_surface_lock`;
- `component_detail_lock`;
- `state_transition_lock`;
- `marking_identity_lock`.

Each contains directory, relevance, source gate/reasons/evidence, status, attempt/terminal state, asset file/hash/observed dimensions, prompt hash, false native-4K fields, and QA for geometry, material, identity, subject, text pollution, and failure flags.

An approved diagnostic board requires source-gate approval, an existing PNG, matching dimensions/hash, prompt hash, executed call, all QA passes, and no failure flags. It does not increase camera coverage.

## 6. Primary Upload Bundle

`primary_upload_bundle` contains:

- `directory: 07_Primary_Upload_Bundle`;
- `status: planned | approved | blocked`;
- `max_asset_count: 5`;
- zero to five unique `selections` with `asset_file`, `role`, and optional `camera_id`;
- a substantive `selection_reason` when approved.

Every selection must already be an approved package asset. At least one must be a camera; a complete package selects at least two independent cameras. Prefer hard-authority, complementary camera assets and include a diagnostic only when it closes a named risk.

## 7. Package Statuses

- `initialized`: scaffold only.
- `analysis_complete`: evidence/specification/camera plan frozen; no asset claim.
- `generation_in_progress`: a camera or diagnostic awaits generation, continuation, QA, or repair.
- `partial_approved`: one or more assets accepted but a complete gate fails.
- `complete`: hard multi-camera coverage, required diagnostics, upload bundle, hashes, QA, and 4K mappings pass.
- `blocked_source_insufficient`: no truthful required coverage can proceed.
- `blocked_identity_conflict`: target identity/variant unresolved.
- `blocked_generation_runtime`: generation or render execution/binding failed.
- `blocked_generation_semantic_mismatch`: returned subject/semantics do not match the target.
- `four_k_mapping_failed`: accepted assets are not mapped one-to-one.

Never use `complete` while any target is pending, awaiting continuation, under QA, or under repair.

## 8. 4K Prompt Contract

Create exactly one section for every approved camera and diagnostic asset:

```markdown
## Asset: 02_Geometry_Camera_Coverage/camera_assets/cam_front_3q_left.png

Preserve original product geometry. Preserve part count. Preserve proportions.
Preserve the accepted camera pose. Preserve all critical nodes and their connections.
Preserve any source-supported logo and markings exactly; do not invent them if absent.
Preserve materials and colors. Enhance only clarity and realistic micro-texture.
Do not redesign the product.
```

Each mapping contains:

- `asset_file` and matching `section_anchor`;
- `preserves` exactly: `geometry`, `part_count`, `proportions`, `markings`, `materials`, `camera_pose`, `critical_nodes`;
- `allowed_changes` limited to resolution, edge definition, realistic micro-texture, and source-supported fine detail;
- `redesign_forbidden: true`.

Bind the accepted asset and original sources. Do not claim that an external 4K result exists until its returned file is inspected.

## 9. Validation

Run:

```text
python scripts/validate_asset_package.py <package-path>
```

The validator checks schema, required headings, per-camera evidence/authority, actual PNG/JPEG dimensions, byte hashes, duplicate files/pose bins, derived coverage metrics, diagnostic states, upload selection, false 4K claims, one-to-one prompts, and completion truthfulness.

It does not replace visual source comparison, product engineering/safety review, rights approval, or user approval.
