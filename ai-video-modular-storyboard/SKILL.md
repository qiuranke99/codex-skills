---
name: ai-video-modular-storyboard
description: "Create and maintain an editable, generation-ready AI-video storyboard from an approved professional Shot Contract. Use when every scripted shot must have exactly one independently generated storyboard frame, stable shot identity, deterministic human review sheets, local one-shot or multi-shot replacement, and downstream dependency invalidation. Do not use for rough-script professionalization, look development, keyframes, previs, video prompts, video generation, a single generative multi-panel board, editing, music, or output QC."
---

# AI Video Modular Storyboard

This Skill is a self-contained entrypoint. Consume one supplied Professional
Shot Contract and any supplied authority artifacts by contract, without
requiring their producer packages or a workflow-suite installation. Optional
pipeline handoff does not gate storyboard creation or validation.

中文名：AI 视频模块化故事板

Turn an approved professional Shot Contract into independent, editable storyboard assets. Preserve the invariant:

`script_shot_count = independent_storyboard_frame_count = rendered_valid_cell_count = N`

The independent frames are the source assets. A contact sheet is only a deterministic human-review derivative. Never generate one multi-panel image and crop it into shot assets.

## Input Gate

Require a supplied, approved Professional Shot Contract artifact with stable
`shot_uid`, display order, target duration, visible action, composition intent,
initial state, ending state, and continuity relations for every shot. Require
references only when that contract marks them as authoritative. Read supplied
character, product, packaging, material, scene, and Global Look artifacts when
available; never require their producer directories.

A supplied `<project_root>/00_project_canon/PROJECT_CANON_MANIFEST.json` may be
used as an optional artifact index. If it is absent, validate the Shot Contract
and authority files directly from their declared locators and hashes. Do not
create a private registry merely to use this Skill.

If the input is only a rough or structured creative draft, return
`blocked_missing_professional_shot_contract` with the exact missing fields; do
not require or locate a named sibling package and do not silently invent the
definitive shot count. If the user asks to reorder, insert, delete, merge, or
split shots, emit a change request addressed to the Shot Contract's declared
owner before changing the storyboard. Missing optional detail is not a reason
to stop: infer conservative directing detail and record it.

## Canonical Resources

Read before producing or changing assets:

- `references/storyboard_contract.md` — ownership, generation, review, transaction, invalidation, and completion rules.
- `references/storyboard_manifest.schema.json` — machine-readable package contract.
- `references/storyboard_manifest_template.json` — minimum manifest example.
- `references/change_transaction.schema.json` — atomic one-shot and multi-shot replacement record.
- `references/review_board_contract.md` — deterministic human-review board rules.
- `test_cases.md` — positive, adversarial, and regression fixtures.

The deterministic human review-board compositor uses Pillow. Treat Pillow as an explicit runtime dependency for `scripts/build_review_board.py`; missing Pillow blocks only review-board composition, not independent frame generation or preservation. Do not replace it with a generative multi-panel image.

## Two Storyboard Stages

### `structure_draft`

Use independent low-cost frames to test shot order, representative instant, composition, eyeline, blocking, screen direction, and visual information. The Global Look may be provisional. These frames may be reviewed but must not be presented as final look-applied model references.

### `look_applied_final`

Rebuild or promote every required frame only after character/product/scene assets and the Global Look version are bound. Preserve the approved composition while applying identity, geometry, material, packaging, scene, wardrobe, and look evidence. A frame is downstream-ready only after later-turn visual inspection and approval.

Promotion is evidence-gated: a structure frame may be promoted without regeneration only if it already passes every final identity, product, scene, material, packaging, continuity, and look check.

## Workflow

### 1. Freeze Coverage

Read the Shot Contract, preserve each stable `shot_uid`, and create one frame specification per shot. Never create a storyboard-only shot and never omit a scripted shot. Display numbers are mutable labels; `shot_uid` is permanent identity.

For each shot freeze:

- representative instant and why it best communicates the shot;
- composition, camera height/angle, lens intent, subject placement, screen direction, and negative space;
- visible subject action, prop/product state, entry state, and exit state;
- required identity, product, scene, and look versions;
- continuity dependencies and forbidden changes.

### 2. Generate Independent Frames

Generate every storyboard frame as an independent full-frame image. Set `generation_mode: independent_full_frame`, `independently_generated: true`, and `derived_from_multipanel: false`. Do not put shot numbers, duration, editorial captions, arrows, grid lines, UI, watermark, or layout chrome inside a model-facing frame.

Do not confuse storyboard annotation with intrinsic scene content. Source-authorized packaging copy, a product mark, or in-world signage may remain visible only under `intrinsic_text_policy: source_authorized_only`, with one exact Project Canon artifact reference per source in `intrinsic_text_source_refs`. Each reference must resolve to a current downstream-eligible product, packaging, label, scene, environment, location, or signage asset, cover the shot, appear in the generation prompt, and be included in the frame dependencies. Otherwise use `intrinsic_text_policy: none_visible` and an empty reference list. This binding proves provenance only; it is not OCR evidence and does not certify exact spelling, logo geometry, legal copy, QR codes, or barcodes.

Before each image call, freeze the frame prompt and persist its path/hash. Every prompt repeats the exact Global Directing block. A `look_applied_final` prompt additionally repeats the exact Global Look Core, assigned Look State, resolved first-class Look Reference **artifact IDs** (never the State's internal `reference_id` aliases), then the legal Shot Look Delta; the frame artifact depends on those exact reference hashes. `structure_draft` must not claim those final-look blocks. Mark the artifact `generating`. The image call is terminal for that turn. In a later continuation inspect the actual image, record actual dimensions and `file_sha256`, compare it with source authorities and adjacent shots, and only then set approval.

If one frame fails, regenerate only that `shot_uid`. Do not regenerate unaffected frames to make a prettier board.

### 3. Validate Shot Continuity

For every adjacent pair check identity, wardrobe, prop hand, product orientation/state, geography, screen direction, eyeline, pose progression, scene state, and look-state legality. A storyboard may use associative montage and need not assert literal spatial continuity; it must explicitly record that directing grammar rather than fabricate continuity.

### 4. Compose The Human Review Board

Compose the board only from current independent frames using `scripts/build_review_board.py`. The layout algorithm, cell order, padding, labels, and background must be deterministic. Human-only labels live in a separate label band outside each image.

Set:

- `board_type: deterministic_human_review_composite`;
- `is_model_input: false`;
- `valid_cell_count: N`;
- `cell_shot_uids` in Shot Contract order;
- `source_frame_hashes` to the current approved file hashes.

Blank layout slots after the last shot are not valid cells. Never send the contact sheet to the video model when independent frames are available.

### 5. Commit Local Changes Atomically

For one-shot or multi-shot replacement, create a transaction before generation. Stage every replacement under a new artifact version while old approved frames remain active. Inspect all staged frames. Commit the manifest switch only when every requested frame passes; otherwise reject the entire transaction and leave the old manifest active.

At commit, retain the exact pre-transaction Storyboard manifest as an immutable snapshot, hash the snapshot file, lock its artifact ID/owner/version/hash in the transaction, and prove that snapshot is the matching superseded entry in the actual Project Canon manifest. Self-reported “unaffected” hashes without this external anchor are insufficient.

Then:

- increment only affected frame versions;
- increment the root Storyboard manifest version above the immutable pre-transaction manifest version;
- assert every unaffected `file_sha256` is byte-identical;
- rebuild the review board and increment its version whenever `source_frame_hashes` changes;
- invalidate only truly dependent keyframes, V1/V2 previs assets, and generation prompts;
- preserve old frame versions for rollback.

A reorder transaction must have `mode: reorder_request`, `status: routed_upstream`, `atomic_commit: false`, and `route_to_shot_contract: true`. Never apply the reorder locally.

### 6. Write Shared Artifact Records

Every manifest, frame, board, and transaction artifact uses this envelope:

```yaml
contract_version: ai-video-artifact-v1
artifact_id:
owner_skill:
version:
sha256:
approval_status:
dependencies:
affected_shot_uids:
stale_reason:
```

The owner is `ai-video-modular-storyboard`, `contract_version` is `ai-video-artifact-v1`, and `version` is a SemVer string. Use only `draft`, `assistant_validated`, `user_approved`, `stale`, or `blocked` for envelope `approval_status`. A draft may use `sha256: null`. For every other status, compute `sha256` from canonical JSON of that artifact after removing only its own top-level `sha256` field; nested dependency hashes remain. Serialize as UTF-8 with sorted keys, compact separators, `ensure_ascii=false`, and non-finite numbers forbidden. Every dependency contains artifact ID, owner, SemVer, and hash. Binary files use a separate `file_sha256`. A validated/approved artifact must have `stale_reason: null`; a stale artifact must state why.

## Output Tree

```text
storyboard-package/
├── 00_manifest/
│   ├── STORYBOARD_MANIFEST.json
│   ├── owned_artifacts/<frame-or-board-artifact-id>.json
│   └── pre_transactions/<transaction_id>_BASE.json
├── 01_frames/
│   ├── <shot_uid>/structure_draft_vNN.png + generation prompt sidecar
│   └── <shot_uid>/look_applied_final_vNN.png + generation prompt sidecar
├── 02_review_board/
│   ├── storyboard_review_board.png
│   └── storyboard_review_board.metadata.json
├── 03_transactions/
│   └── <transaction_id>.json
└── 04_qa/
    ├── continuity_report.md
    └── validation_report.json
```

Do not create empty placeholder files for stages not produced.

Add `00_manifest/MANIFEST_UPDATE_RECEIPT.json` only after an explicitly
requested Project Canon handoff succeeds.

## Hard Boundaries

This Skill owns representative frame selection, storyboard composition, stable mapping, deterministic review composition, and local storyboard replacement. It does not own:

- story, shot count, order, duration, or advertising function;
- character/product/packaging/material/scene identity;
- Global Look;
- generation-grade keyframes;
- timing animatics, camera paths, blocking animation, or material motion;
- video prompts, model/provider routing, video generation, editing, music, or output QC.

Do not call text-to-video or first/last-frame video modes. This Skill creates still storyboard assets only.

Generation-route boundary: `standalone_single_image_to_video: forbidden`;
`ordinary_image_references_in_omni_r2v: allowed`. Independently generated
storyboard frames remain legal image references within Omni R2V, but no one
frame is a classic standalone I2V generation route.

## Completion Gate

Claim the package ready only when:

- `N` is identical across the approved Shot Contract, frame list, independent file count, valid board-cell count, and ordered `cell_shot_uids`;
- every shot has exactly one current independent frame and every current file/hash exists;
- no frame is derived from a generated multi-panel image;
- all `shot_uid` values are unique and match the Shot Contract;
- display order is contiguous and follows the current Shot Contract;
- final-stage frames bind an approved Global Look version and required authority assets;
- every frame prompt sidecar is hash-valid; final frames prove exact Core → assigned State → Shot Delta inheritance;
- the board is a deterministic human-only composite and not a model input;
- applied replacement transactions are atomic and prove unaffected hashes stayed unchanged;
- reorder requests were routed upstream;
- no approved artifact is stale;
- every binary frame/board has a complete owned-artifact JSON record; when optional Project Canon registration was requested, its primary bytes and record-sidecar bytes are locked separately;
- `python3 scripts/validate_storyboard_package.py <storyboard-package>` exits zero; when optional Project Canon integration is supplied, add `--project-root <project-root> --project-canon-manifest <actual-project-canon>` and require the same result.

Validator success proves structural integrity, not aesthetic or production approval.

## Minimal Invocation

`Use $ai-video-modular-storyboard to turn this approved Shot Contract into N independent editable storyboard frames and a deterministic human review board.`

## Optional Project Canon Handoff

Do not require Project Canon for frame generation, inspection, review-board
composition, replacement transactions, or package validation. If registry
mutation is explicitly requested, preserve exact base/candidate bytes and
invoke `scripts/apply_project_canon_transition.py` with an explicit compatible
`--transition-runner`. Without that input the wrapper returns
`blocked_missing_project_canon_transition_input`; the standalone storyboard
package remains valid. Never locate a sibling package or write Canon/receipt
bytes directly.
