# Package Contract

Use this contract to initialize, update, validate, and deliver `Complex_Product_Identity_Asset_Package/`.

## Contents

1. File tree
2. Root manifest
3. Board records
4. Package statuses
5. Final-board minimum gate
6. 4K prompt contract
7. Validation

## 1. File Tree

```text
Complex_Product_Identity_Asset_Package/
  01_Product_Identity_Specification.md
  02_Geometry_Lock_Board/
    geometry_lock_board.png                 # only when generated
  03_Material_Surface_Lock/
    material_surface_lock_board.png         # only when generated
  04_Component_Detail_Lock/
    component_detail_lock_board.png         # only when generated
  05_State_Transition_Lock/
    state_transition_lock_board.png         # only when generated
  06_Marking_Identity_Lock/
    marking_identity_lock_board.png          # only when generated
  07_Final_Product_Identity_Lock_Board/
    final_product_identity_lock_board.png    # only when complete gate passes
  08_4K_Upscale_Prompts.md
  asset_package_manifest.json
```

Empty conditional directories are allowed. Do not add placeholder images.

## 2. Root Manifest

Use schema version `complex_product_identity_asset_package.v1`. Required root fields:

- `asset_id`;
- `package_status`;
- `identity_specification`;
- `identity_specification_sha256`;
- `source_bundle_sha256`;
- `unresolved_hard_conflicts`;
- `boards`;
- `final_board`;
- `four_k_prompt_file`;
- `four_k_prompts`;
- `approved_asset_count`;
- `four_k_mapping_count`;
- `production_approval_status`.

Use SHA-256 lowercase hex. Keep `production_approval_status` separate from assistant QA; allowed values are `not_granted`, `user_granted`, and `external_pipeline_granted`.

## 3. Board Records

Use these board IDs exactly:

- `geometry_lock`;
- `material_surface_lock`;
- `component_detail_lock`;
- `state_transition_lock`;
- `marking_identity_lock`.

Each record contains:

- `directory`, `relevance`, `source_gate`, `source_gate_reasons`, `evidence_ids`;
- `status`, `attempt_count`, `terminal_generation_call`;
- `asset_file`, `actual_dimensions`, `generation_prompt_sha256`;
- `native_4k_claimed`, `native_4k_evidence`;
- `qa.geometry_consistency`, `qa.material_consistency`, `qa.identity_consistency`, and `qa.failure_flags`.

An approved board requires `source_gate: approved`, an existing non-empty PNG, positive actual dimensions, a prompt hash, no failure flags, and every board-relevant QA dimension passing. Keep `native_4k_claimed: false` and `native_4k_evidence: null` for every Codex package asset; external 4K results are a separate downstream surface and never replace the accepted Codex identity source inside this package.

The final board uses the same generation/QA fields plus `source_board_ids`. Every source board ID must be approved.

## 4. Package Statuses

- `initialized`: scaffold only.
- `analysis_complete`: specification frozen; no generation claim.
- `generation_in_progress`: at least one board is pending, awaiting continuation, or under QA.
- `partial_approved`: one or more boards approved, but the complete gate fails; every approved asset still has a 4K mapping.
- `complete`: all complete-package gates pass.
- `blocked_source_insufficient`: required evidence is missing.
- `blocked_identity_conflict`: one target identity cannot be resolved.
- `blocked_generation_runtime`: built-in generation cannot execute or bind.
- `four_k_mapping_failed`: approved assets lack one-to-one 4K handoff.

Never use `complete` when any relevant board is `generation_pending`, `awaiting_post_generation_continuation`, `qa_pending`, `repair_required`, `blocked`, or `blocked_generation_quality`.

## 5. Final-Board Minimum Gate

Require:

- approved Geometry Lock;
- every board with `relevance: required` approved;
- no unresolved hard identity conflict;
- approved source-board set in the final record;
- no unsupported state or marking exactness claim;
- final-board QA pass.

If this gate fails, keep the final board blocked. Do not synthesize a final board from a partial package.

## 6. 4K Prompt Contract

Create exactly one section for every approved generated board and the approved final board:

```markdown
## Asset: 02_Geometry_Lock_Board/geometry_lock_board.png

Preserve original product geometry. Preserve part count. Preserve proportions.
Preserve any source-supported logo and markings exactly; do not invent them if absent.
Preserve materials and colors. Enhance only clarity and realistic micro-texture.
Do not redesign the product.
```

Each `four_k_prompts` manifest entry contains:

- `asset_file`;
- `section_anchor` equal to `Asset: <asset_file>`;
- `preserves` containing `geometry`, `part_count`, `proportions`, `markings`, and `materials`;
- `allowed_changes` limited to `resolution`, `edge_definition`, `realistic_microtexture`, and `source_supported_fine_detail`;
- `redesign_forbidden: true`.

Bind both the accepted Codex asset and original source references. Preserve board topology, panel order, camera views, component/state relationships, and all source-supported identity. Do not claim external generation or verified 4K until a returned file is inspected.

## 7. Validation

Run:

```text
python scripts/validate_asset_package.py <package-path>
```

The validator checks structure, states, files, hashes, source gates, QA, final-board dependencies, false native-4K claims, one-to-one prompt mapping, and completion truthfulness. It does not replace pixel inspection, product engineering review, brand/legal approval, or user approval.
