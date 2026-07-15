---
name: packaging-product-identity-label-lock-board
description: Use when the user supplies usually one to three photos, optionally plus close-ups or artwork, of one packaged product with dense multilingual copy, labels, codes, transparent liquid, texture, or embossing and wants exactly one clean horizontal 16:9 identity asset board for downstream image or video models. Build a source-cited OCR/copy ledger, embed every transcribed line and its reading order in the generation prompt, produce seven complete views plus two or three source-grounded close-ups on one borderless continuous background, and reject visible gibberish; never demand a fixed multi-angle capture set.
---

# Packaging Product Identity Label Lock Board

Create one usable video-model identity board for one packaged product. Keep this stable Skill slug. Do not create sibling Skills, a 360-degree capture factory, or a print-proof workflow.

## Final outcome

Return exactly one clean horizontal 16:9 board at requested 3840 × 2160, plus the complete copyable generation prompt and run evidence.

The board contains:

- exactly seven complete product views;
- two source-grounded detail regions by default, with a third allowed only for one distinct unresolved identity risk;
- nine regions by default and never more than ten;
- one `borderless_continuous_background` with open spacing, not a drawn grid or a set of cards;
- one SKU with consistent silhouette, closure, material, fill, label architecture, graphics, texture, embossing, and product-native copy.

This board is a downstream video/image reference. It does not claim unseen geometry or unreadable copy has been measured.

## Runtime release gate

This package belongs to the High-Control AI TVC release suite. Start one monotonic run clock, then run `HIGH_CONTROL_RELEASE_GATE_V2` exactly once through the OS-native pinned-runtime launcher:

- Windows: `high-control-ai-tvc/tools/release-control.ps1 -Action check -Format json`
- macOS/Linux: `high-control-ai-tvc/tools/release-control.sh check --format json`

Give the gate 60 seconds. Continue only when `ready_latest=true`. Never rerun it inside the image worker and never use an unverified global Python to bypass the pinned runtime. If it fails or times out, compile and publish the complete prompt as `prompt_status: release_unverified`, do not generate, and terminate `BLOCKED_RELEASE_GATE`.

## Prompt-first latency contract

The complete reusable generation prompt is the first user deliverable.

- Publish the complete frozen prompt within 180 seconds of invocation and within 120 seconds of a successful release gate.
- If OCR is requested, spend at most 45 seconds on the first OCR discovery pass. Mark unresolved lines rather than silently waiting.
- Before prompt publication, do not run package tests, composition planning, project archiving, release maintenance, or deep copy cleanup.
- Publish the complete prompt text inline before worker spawn, with prompt path, frozen-file SHA-256, provider-content SHA-256, ordered provider references, copy-ledger SHA-256, copy-block SHA-256, and `copy_authority`.
- Spawn the image worker within 30 seconds after prompt publication. Require imagegen submission within 90 seconds after spawn.
- Send truthful status at least every 60 seconds while generation runs.
- Give an image call at most 15 minutes and all automatic attempts at most 20 minutes. Never start a retry while the previous call state is unknown.
- Show a resolver-bound result within 60 seconds as `unaccepted raw preview`; do not claim acceptance before composition and QA.

Persist these milestones in `prompt-dispatch-trace.json` from `references/prompt_dispatch_trace.template.json` and validate it with `scripts/validate_prompt_dispatch_trace.py`.

## Input sufficiency and evidence limits

One front, one back, and one three-quarter/side photograph are a normal sufficient set. One or two complete views are also legal. Additional close-ups or approved artwork may be used when already supplied.

- never request a fixed 8/12/16/24-angle capture set;
- never convert missing label copy into a demand for more angles;
- never claim hidden text, QR payloads, barcode digits, underside markings, or unseen panels are exact;
- classify geometry as `source_observed`, `source_crop`, `deterministic_reprojection`, `bounded_inferred`, or `unknown`;
- record unknowns explicitly and continue the normal `video_reference` path.

Do not block the board because a barcode, QR code, hidden side panel, or microcopy line is unresolved. Copy uncertainty must not trigger an angle request.

## Copy truth layer

OCR remains nonblocking for geometry/material work, but a structured copy ledger is mandatory whenever visible product copy exists. OCR is candidate extraction, not authority.

Do not make OCR completion a global gate. An OCR timeout or disagreement lowers only the affected copy authority; it does not block the board or trigger an angle request.

It only lowers the affected copy region's authority. It never authorizes guessed wording or a larger capture demand.

### 1. Freeze sources before transcription

Use `scripts/freeze_reference_bundle.py`. Every copy region must cite one frozen `source_alias` and exact `source_sha256`. Do not cite mutable originals.

### 2. OCR and visually reconcile region by region

Transcribe all visible copy into `copy-ledger.json` based on `references/copy_ledger.template.json`.

For every label, print, embossing, date/code block, or other copy region:

- keep a stable `region_id`;
- record surface, source alias, source SHA-256, orientation, alignment, reading order, and column order;
- split copy into one ledger entry per physical line in the correct sequence;
- preserve spelling, case, punctuation, spaces, units, line breaks, multilingual distinctions, and source typos exactly;
- retain every OCR result as `approved_exact`, `candidate`, or `unresolved`;
- use `approved_exact` only after the line is visibly reconciled against the frozen source or approved artwork;
- never approve an `ocr_only` or `not_readable` line as exact;
- keep mirrored show-through, reflections, and embossed patterns separate from printed copy.

If OCR engines disagree, record candidates and continue. Do not choose the most plausible wording. The ledger must make uncertainty visible rather than manufacture certainty.

### 3. Compile the complete prompt block deterministically

Run:

```text
python -X utf8 scripts/compile_copy_prompt.py --ledger <run-dir>/copy-ledger.json --output <attempt>/copy-prompt-block.md --receipt <attempt>/copy-prompt-receipt.json
```

The compiler emits every approved, candidate, and unresolved line in ledger order. Approved lines are separated from audit-only candidates. It also binds the ledger and block hashes and proves all lines were emitted in order.

Render the final prompt with `scripts/render_generation_prompt.py`, using `references/generation_prompt_values.template.json` for product-specific substitutions. The renderer embeds `copy-prompt-block.md` verbatim at `{{copy_contract_block}}`, rejects missing values or surviving placeholders, and writes a prompt receipt. Do not summarize the block as “preserve all text.” The final prompt must contain the actual strings, region mapping, format, and reading order.

### 4. Respect the pixel-authority boundary

Listing all text in a prompt reduces omission and ordering errors; it does not make generated pixels exact. Therefore:

- critical readable copy must be preserved with source crops or approved artwork reprojection;
- Use source crops or approved artwork for critical readable copy and codes. Do not ask the image model to invent unreadable characters;
- source-derived front/back anchors may be used when they blend into the continuous background and keep the product complete;
- generated full views may keep unresolved dense microcopy visually quiet, but must never replace it with invented glyphs;
- any visible pseudo-Chinese, pseudo-Latin, fake digits, altered punctuation, fake barcode value, or fake QR module is a board failure;
- `copy_authority: exact_copy_evidence` is legal only when every claimed line is approved, reviewed, and source/artwork-backed in the final pixels;
- otherwise publish `copy_authority: video_reference` and name unresolved regions.

## Fixed board topology

Use these seven complete, uncropped product views in this semantic order:

1. front full product;
2. back full product;
3. one evidence-supported side full product;
4. side 45-degree high-angle full product;
5. side 45-degree low-angle full product;
6. top-down full product;
7. low-up full product.

High, low, top-down, and low-up describe camera position. Keep the product upright on its base; never turn a requested angle into a lying-down product.

Then add:

8. closure/top close-up;
9. highest-risk local identity close-up, normally front/back label copy, embossing, texture, code block, or base;
10. optional second local identity close-up only when it resolves a distinct, source-evidenced risk.

The default is nine regions. Do not add both left and right sides, redundant three-quarter views, a lower strip of many thumbnails, or filler regions.

## Borderless visual grammar

Treat “region” as semantic content, not a drawn box.

- use one seamless white or very light gray studio background across the whole canvas;
- use open spacing, scale, and grouping to separate views;
- allow asymmetrical/freeform placement when it improves view size and text legibility;
- make front, back, and copy-risk regions larger than low-risk views;
- no white rectangular frames, card containers, grid lines, panel outlines, divider rules, evidence strips, or bordered crops;
- no heading, angle labels, arrows, numbers, captions, legends, UI, QA badges, or non-product text;
- no blank cells, empty rectangles, placeholders, reserved slots, future-fill boxes, wireframes, or unused panels;
- no overlap, crop, duplicate SKU, extra closure, hands, props, splashes, or scenery.

The image model must generate every declared region as populated content. The compositor may improve copy fidelity but cannot hide a blank, framed, or broken raw layout.

## Provider reference materialization

The frozen source ledger may contain up to eight images, but imagegen may receive at most five paths. The worker must never submit more than five paths. Run `scripts/build_generation_reference_pack.py` before prompt freeze.

- one to five sources remain ordered direct references;
- six to eight sources become three complete-product anchors plus at most two deterministic detail sheets;
- preserve order: front/primary, back, three-quarter/side, then detail/artwork;
- if the provider pack contains zero or more than five paths, stop `BLOCKED_REFERENCE_MATERIALIZATION`.

## Freeze and publish the prompt

Write product facts to one run-scoped values JSON and render the prompt deterministically:

```text
python -X utf8 scripts/render_generation_prompt.py --template references/generation_prompt_template.md --values <attempt>/generation-prompt-values.json --copy-block <attempt>/copy-prompt-block.md --output <attempt>/final_generation_prompt.md --receipt <attempt>/generation-prompt-receipt.json
```

The output is UTF-8/LF without BOM with exactly one file-terminal LF.

The prompt must include:

- one 3840 × 2160 horizontal board;
- the seven named complete views and exact two/three close-up count;
- nine regions by default, ten maximum;
- one continuous background and explicit no-frame/no-grid bans;
- observed identity facts and explicit unknowns;
- the full deterministic copy contract block verbatim;
- source-backed copy rules and visible-gibberish rejection;
- No blank cells, empty rectangles, placeholders, reserved slots, future-fill boxes, wireframes, or unused panels;
- independently usable as a final single-call prompt.

Compute the file hash and provider-content hash, publish the complete prompt text inline, and record `PROMPT_PUBLISHED`. A path, summary, or hash without full prompt text is not delivery.

## Delegate exactly one image call

Only an explicit user invocation of this Skill authorizes a worker. Implicit invocation must stop before generation. The main agent must not call imagegen directly.

1. Create a fresh 32-character lowercase hexadecimal nonce and spawn exactly one fresh nonce-suffixed non-decision worker with `fork_turns="none"`.
2. Give it the frozen provider prompt content, both prompt hashes, the ordered provider paths, and a run nonce.
3. Its first and only tool action is one imagegen call.
4. Forbid it from reading this Skill, performing OCR, changing text, selecting references, running gates, inspecting, approving, repairing, or publishing.
5. Resolve the returned PNG with `scripts/resolve_worker_image.py` and bind prompt, reference bytes, lineage, call ID, and image bytes.

Only exact prompt bytes or omission of exactly one file-terminal LF are acceptable. Re-resolve that same completed call for a terminal-LF-only mismatch; never spend another image call on that binding-only condition.

## Raw-board gate

Before deterministic overlays, inspect the actual raw board and reject it if:

- it has fewer/more than seven complete views or fewer than two/more than three close-ups;
- total regions are below nine or above ten;
- any full product is cropped, duplicated, merged, overlapping, or lying down;
- any declared region is blank, placeholder-like, or unused;
- any white frame, card border, grid line, divider, evidence strip, or boxed panel is visible;
- product identity, closure, liquid level, label architecture, graphics, or embossing drift;
- any invented/corrupted readable copy is visible.

Do not let later source overlays turn a failed raw layout into a pass.

## Deterministic composition

Build `composition-plan.json` from `references/composition_plan.template.json` and run `scripts/compose_asset_board.py`.

- use schema `packaging_board_composition_plan.v2`;
- require `layout_style: borderless_continuous_background` and `drawn_borders: false`;
- map every detail region one-to-one to a unique non-overlapping target;
- use `fit: cover` for detail overlays so contain-padding cannot form white cards;
- require `seamless_background_match: true` and `border_px: 0` on every overlay;
- use source-backed front/back anchors only when the complete product remains uncropped and the background blends seamlessly;
- never draw a stroke, border, label, or card around a region.

The compositor outputs an exact 3840 × 2160 PNG and a v2 receipt binding raw board, sources, crops, targets, and final image.

## Post-generation copy QA

Create `copy-qa.json` from `references/copy_qa.template.json` after inspecting the final board.

For every board region:

- compare visible strings against ledger line IDs in physical reading order;
- mark only `exact_match`, `source_reprojected`, or `no_readable_copy_present`;
- list all covered copy-region IDs and require zero mismatch line IDs;
- require `source_backed_pixels: true` for source-reprojected regions;
- set `board_wide_invented_or_corrupted_visible_copy: false` only after inspecting the entire board, including full views;
- reject rather than excuse any readable gibberish.

Run:

```text
python -X utf8 scripts/validate_copy_contract.py --ledger <run-dir>/copy-ledger.json --block <attempt>/copy-prompt-block.md --receipt <attempt>/copy-prompt-receipt.json --prompt <attempt>/final_generation_prompt.md --qa <attempt>/copy-qa.json --copy-authority video_reference
```

This proves the prompt contains the complete ledger block and the accepted board has source-backed coverage for every approved copy region.

## Final board validation

Fill `references/asset_board_manifest.template.json`, then run:

```text
python -X utf8 scripts/validate_asset_board_run.py --manifest <run-dir>/asset-board-manifest.json
```

Acceptance requires:

- exactly seven complete views;
- exactly two or three source-derived close-ups;
- exactly nine or ten total regions;
- exact 3840 × 2160 PNG;
- `borderless_continuous_background: pass` and `no_visible_frames: pass` from main-agent inspection;
- complete prompt copy coverage and passed pixel copy QA;
- no invented/corrupted visible copy;
- no non-product annotations or blank regions;
- frozen prompt/reference/worker/composition/final-image hashes all valid.

## Repair limits

Allow at most two repair attempts after the initial attempt. Each repair must target one observed failure class: topology/frame, geometry/identity, or copy fidelity. Reuse the frozen ledger and copy block unless source evidence changes. Never make random prompt rewrites or request more angles as a repair.

If generated text is wrong:

1. verify the prompt still embeds the deterministic block;
2. prefer deterministic source/artwork reprojection for readable copy;
3. if model rendering is still required, issue one narrow repair referencing exact line IDs and regions;
4. reject after the third total attempt rather than accepting gibberish.

## Deliverables and terminal states

Return:

- final board PNG and SHA-256;
- complete frozen generation prompt inline and its file/content hashes;
- copy ledger, compiled copy block, compilation receipt, and copy QA paths/hashes;
- ordered provider references;
- copy authority and unresolved regions;
- asset-board manifest and validation result;
- terminal status.

Valid bounded failures are `BLOCKED_RELEASE_GATE`, `BLOCKED_REFERENCE_MATERIALIZATION`, `BLOCKED_PROMPT_READY_TIMEOUT`, `BLOCKED_WORKER_START_TIMEOUT`, `BLOCKED_WORKER_SUBMIT_TIMEOUT`, `BLOCKED_IMAGEGEN_TIMEOUT`, `BLOCKED_VALIDATION`, and `REJECTED_AFTER_MAX_ATTEMPTS`. Every state after prompt compilation still returns the complete prompt. Sparse angles, OCR disagreement, or hidden copy alone do not block a normal `video_reference` board.

On every terminal success or failure after compilation, repeat the complete frozen prompt inline with its hashes and truthful terminal status.

## Optional AI-Video Project Canon Export

This appendix is downstream compatibility for the already accepted board, not another board, angle set, or default deliverable. Run `scripts/export_ai_video_canon.py` only when an AI-video project explicitly needs a fixed-owner Canon record.

- Runtime dependency: this package's `requirements.txt` pins `Pillow` for deterministic board and copy-evidence validation.
- `authority_stage: terminal_packaging_canon`
- `terminal_route_decision: not_applicable`
- `geometry_layout_only` authorizes `[product_geometry]` from an accepted board.
- `geometry_layout_exact_copy_verified` authorizes `[product_geometry, label_copy]` only when the bound v2 board manifest has `copy_authority: exact_copy_evidence`, reviewed copy ledger, zero unresolved claimed regions, verbatim prompt coverage, passed board-wide copy QA, source/artwork-backed pixels, and a live package-validator pass.
- The export bridge never generates, repairs, expands, or upgrades the board by inference.

The Skill succeeds only when the board is compact, borderless, copy-auditable, and honest enough for downstream video generation. It does not succeed by filling the canvas with more views, by listing text without validating pixels, or by accepting visible gibberish.
