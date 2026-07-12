# Modular Storyboard Contract

## Authority And Ownership

The approved Shot Contract owns shot existence, stable `shot_uid`, order, target duration, narrative and advertising function, and continuity intent. The storyboard owns only the visual interpretation of one representative instant per existing shot.

The storyboard must not locally add, delete, merge, split, or reorder shots. Route those requests to the Shot Contract owner, then rebuild affected storyboard records from the newly approved contract.

## Non-Negotiable Cardinality

For an approved storyboard package:

```text
Shot Contract shot count
= current frame records
= unique current frame files
= independent generated frames
= valid review-board cells
= ordered cell_shot_uids
= N
```

Layout placeholders are not valid cells. A duplicated frame is not a second valid frame. A crop from a generated multi-panel image is not an independently generated frame.

## Stable Identity

- `shot_uid` comes from the Shot Contract and never changes when a display number changes.
- `display_order` is a mutable projection of the approved Shot Contract order.
- A regenerated frame keeps `shot_uid`, increments artifact `version`, and gets a new file path and hash.
- Never reuse an artifact ID for a different shot.

## Frame Generation

Each current frame must declare independent generation. Model-input eligibility is stage-dependent:

```json
{
  "generation_mode": "independent_full_frame",
  "independently_generated": true,
  "derived_from_multipanel": false,
  "is_model_input_eligible": false
}
```

Use `false` for `structure_draft`; it may feed human review and V1 timing only. Use `true` only for inspected `look_applied_final` frames whose approved identity/product/scene/Global Look dependencies are locked. Global Look State `reference_id` values are internal mappings; model-facing frame records resolve them to the nested reference artifact IDs and exact dependency hashes.

The frame itself contains no storyboard annotations: no shot number, duration, editorial caption, arrow, border, grid, UI, watermark, or montage layout. An image generator may use approved source evidence but may not generate multiple storyboard cells in one image.

Intrinsic text is a separate source-bound category. Packaging copy, a product mark, or in-world signage is legal only when `content_cleanliness.intrinsic_text_policy` is `source_authorized_only` and every visible-text source is locked by an exact `ai-video-artifact-v1` reference in `intrinsic_text_source_refs`. Each reference must match a current downstream-eligible Project Canon entry in a product, packaging, label, scene, environment, location, or signage category, cover the shot, be a frame dependency, and appear by artifact ID in the generation prompt. Use `none_visible` with an empty source list when no intrinsic text is visible. This is a provenance gate, not an OCR or exact-copy guarantee; exact label copy still requires evidence from its owning asset workflow.

## Visual Stages

`structure_draft` checks shot logic and composition cheaply. `look_applied_final` binds approved character/product/scene assets and the approved Global Look. A final-stage package requires non-null look artifact/version/hash dependencies.

A structure draft may be promoted only after explicit final-stage QA. Promotion means the same binary passes; it does not mean changing the stage label without evidence.

## Atomic Replacement

An applied `replace_frames` transaction must:

1. name exactly the affected `shot_uid` set;
2. stage every replacement before activation;
3. increment every requested frame version;
4. increment the current root Storyboard manifest above the immutable base manifest;
5. include old and new artifact and file hashes;
6. include unaffected hash assertions for every other current shot;
7. set `atomic_commit: true`;
8. switch all requested shots in one manifest commit;
9. rebuild the board and increment its SemVer whenever its `source_frame_hashes` changes;
10. rebuild the downstream invalidation list.

If any staged replacement fails, set the transaction to `rejected`; do not activate a partial subset.

## Reorder, Insert, Delete, Split, Merge

These are Shot Contract changes, not storyboard edits. Record a `reorder_request` or upstream change request, keep the active storyboard unchanged, and route upstream. An applied local reorder is a hard validation failure.

## Artifact Envelope

Every artifact record contains:

- `contract_version`: exactly `ai-video-artifact-v1`;
- `artifact_id`: stable package-unique identity;
- `owner_skill`: exactly `ai-video-modular-storyboard`;
- `version`: SemVer string matching `^[0-9]+\.[0-9]+\.[0-9]+$`;
- `sha256`: null for draft or canonical artifact JSON hash for validated/approved/stale/blocked records;
- `approval_status`: `draft`, `assistant_validated`, `user_approved`, `stale`, or `blocked`;
- `dependencies`: exact artifact ID/owner/version/hash records;
- `affected_shot_uids`: sorted unique scope;
- `stale_reason`: null unless stale.

Canonical artifact hashing removes only the artifact's own top-level `sha256`; nested dependency hashes remain. It then serializes JSON as UTF-8 with sorted keys, separators `(',', ':')`, `ensure_ascii=false`, and `allow_nan=false`. Binary files carry `file_sha256` separately. Materialize every complete frame/board artifact record under `00_manifest/owned_artifacts/`; Project Canon resolves both asset and record locators relative to the project root, never the storyboard package root.

## Invalidation

- Shot Contract content change: invalidate affected frames and all their derivatives.
- Shot order change: route upstream; once approved, invalidate the board, V1 timing, affected adjacency QA, V2 units, and prompts.
- Look Core/State change: invalidate every look-applied frame using it, plus downstream keyframes/prompts; geometry-only structure drafts may remain.
- One frame replacement: invalidate its board, dependent keyframes, V1/V2 segments, and prompts only.
- Board-only layout change: invalidate no model-facing asset because the board is human-only.

## Completion Semantics

`assistant_validated` means assistant structural and visual checks passed. `user_approved` separately records that the user accepted the creative choice. Never conflate them.
