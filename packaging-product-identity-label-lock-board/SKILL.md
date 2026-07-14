---
name: packaging-product-identity-label-lock-board
description: Use when the user supplies usually one to three complete photos, optionally plus additional close-up evidence, of one packaged product with dense copy, labels, logos, patterns, transparent liquid, texture, or embossing and wants exactly one clean horizontal 16:9 product identity asset board for downstream image or video models. The board combines eight complete product views with four to six fully populated, source-evidenced detail panels; OCR is discovery evidence, never a reason to demand a fixed multi-angle capture set.
---

# Packaging Product Identity Label Lock Board

Create one usable video-model reference board for one packaged product. Keep the stable Skill slug. Do not turn this workflow into a 360-degree capture factory, a print-proof system, or a family of new Skills.

## Runtime release gate

This package belongs to the High-Control AI TVC release suite. Start one monotonic run clock, then run `HIGH_CONTROL_RELEASE_GATE_V2` exactly once through the OS-native pinned-runtime launcher:

- Windows: `high-control-ai-tvc/tools/release-control.ps1 -Action check -Format json`
- macOS/Linux: `high-control-ai-tvc/tools/release-control.sh check --format json`

Give the gate 60 seconds. Continue to reference mutation, worker spawn, imagegen, composition, or publication only when `ready_latest=true`. Never rerun the gate inside the worker and never use an unverified global Python to bypass its pinned runtime. If the gate fails or times out, compile and publish the complete prompt as `prompt_status: release_unverified`, do not generate, and terminate as `BLOCKED_RELEASE_GATE`.

## Prompt-first latency contract

Treat a complete copyable generation prompt as the first user deliverable, not as post-generation metadata.

- Publish the complete frozen prompt within 180 seconds of invocation and within 120 seconds of a successful release gate.
- If the user requested OCR, spend at most 45 seconds on OCR discovery. On timeout or disagreement, mark the affected copy `unknown` or `candidates_only` and continue.
- Before prompt publication, do not run package tests, composition planning, worker-provenance resolution, project archiving, release maintenance, or deep supporting-copy review.
- Publish the exact prompt bytes inline in a user-visible commentary message before worker spawn. Include the prompt path, SHA-256, ordered provider references, and `copy_authority`. A path, hash, summary, or progress sentence alone is not prompt delivery.
- Spawn the worker within 30 seconds after prompt publication. Require imagegen submission within 90 seconds after spawn.
- While the worker runs, send a truthful user-visible status update at least every 60 seconds.
- Give each submitted image call at most 15 minutes and all automatic generation attempts together at most 20 minutes. Interrupt a timed-out worker. Do not retry while the prior call state is unknown.
- After one completed image event is resolver-bound to a PNG, show that raw board within 60 seconds as `unaccepted raw preview` before composition and QA. Never claim generation success before that evidence exists.
- On every terminal success, parameter failure, worker timeout, imagegen timeout, or validation failure, repeat the complete frozen prompt inline with its SHA-256 and the exact terminal status.

Record the milestones in a run-scoped trace based on `references/prompt_dispatch_trace.template.json`. Validate the terminal trace with `scripts/validate_prompt_dispatch_trace.py`.

## Core outcome

Deliver exactly one clean horizontal 16:9 board containing:

- exactly eight complete product views;
- four to six fully populated evidence detail panels selected from the real packaging risks;
- the same SKU, silhouette, proportions, closure, liquid level, materials, label architecture, graphics, texture, embossing, and major product-native copy across the board;
- no titles, view names, arrows, numbers, legends, tables, UI, QA text, dates, or other non-product text inside the image.

The board is a downstream image/video identity reference. It is not a claim that hidden copy, unseen geometry, or a continuous 360-degree orbit has been measured exactly.

## Normal inputs

Treat one front, one back, and one three-quarter photograph as a normal and sufficient input set. One or two photographs are also legal. More references may be accepted when the user already has them, but never request a fixed 8/12/16/24-angle capture set.

Only request one additional targeted image when the product cannot be identified without it, for example:

- no image shows the complete silhouette;
- the primary front label is wholly unreadable;
- the closure or dispensing mechanism is completely hidden and materially defines the SKU.

Do not block the board because a barcode, QR code, hidden side panel, microcopy line, or underside is unresolved. Record that region as unknown or unverified and keep working.

## Non-goals

Do not produce:

- independent per-angle masters;
- a rotation ring or elevation ring;
- R8/R12/R16/R24 capture requirements;
- bridge masters, motion envelopes, or loop-closure authority;
- print-ready label artwork;
- exact-copy authority for text that is not source-visible or artwork-backed;
- a required packaging Canon export as part of the core board run.

## Evidence model

Before prompting, build a compact internal ledger. Keep it outside the image.

For every useful source and region, record one of:

- `source_observed`: directly visible in a supplied photograph;
- `source_crop`: a crop from a frozen source, used as an anchor or detail;
- `deterministic_reprojection`: a crop that was resized, rectified, or placed by a deterministic compositor;
- `bounded_inferred`: a model-generated completion constrained by observed shape/material evidence;
- `unknown`: not supported and not safe to infer.

Generated pixels never upgrade themselves to `source_observed`. Unknown evidence does not block the whole board unless it prevents product identification.

## OCR and copy handling

If the user asks to OCR first, perform one time-bounded OCR discovery pass before prompt freeze. OCR remains nonblocking and shares the 45-second budget in the prompt-first latency contract.

1. Run OCR or careful visual transcription on only the supplied images.
2. Treat OCR output as candidates, not truth. Preserve spelling, case, punctuation, units, line breaks, mirrored show-through, and multilingual distinctions.
3. Separate copy into:
   - major identity copy: brand, product name, variant, net content, hero claim;
   - dense supporting copy: ingredients, directions, manufacturer text;
   - codes/graphics: barcode, QR, certification marks, ornaments, logos;
   - surface-native marks: embossing, debossing, texture, molded lettering.
4. Use source crops or approved artwork for critical readable copy and codes. Do not ask the image model to invent unreadable characters.
5. A normal video-reference board may remain `copy_authority: video_reference` with named unresolved microcopy. Use `copy_authority: exact_copy_evidence` only when every claimed field is visibly verified and the final pixels are source/artwork-backed.

OCR failure, missing language support, or disagreement between OCR candidates must not trigger an angle request and must not prevent geometry/material generation. It only lowers the affected copy region's authority.

## Board architecture

Use this default view set:

1. front;
2. back;
3. left side;
4. right side;
5. front three-quarter;
6. rear three-quarter;
7. high angle;
8. low angle.

Keep all eight products complete and uncropped. Preserve the closure/nozzle direction in product coordinates, not screen coordinates.

Select four to six detail panels by risk, not by a fixed checklist. Use four by default for a single-call board; add a fifth or sixth only when each extra panel resolves a distinct video-identity risk. Before prompt freeze, lock one exact count and name every panel. Prefer:

- front label and major identity copy;
- back label/dense-copy block;
- barcode or QR only when useful downstream;
- pump, cap, dispenser, shoulder, or neck construction;
- transparent liquid level, dip tube, or internal component;
- embossing, debossing, molded pattern, foil, gloss/matte boundary, or texture;
- base, edge, seam, or distinctive graphic ornament.

For text-heavy packaging, the final board should be hybrid:

- use source-observed full-product anchors for the supplied front/back/three-quarter views when possible;
- use bounded model completion for the missing support views;
- require the generated board to populate every selected detail panel with visible source-grounded content;
- overwrite those already-populated panels with source-derived crops through `scripts/compose_asset_board.py` when Codex executes the full workflow;
- keep critical readable copy in source-derived panels instead of trusting model-rendered microcopy.

This hybrid board is the primary fix for sparse-view, text-heavy products.

## Layout and visual rules

- requested canvas: 3840 × 2160, horizontal 16:9;
- neutral white or very light gray studio background;
- even, soft product light; no dramatic campaign styling;
- eight full-product views arranged as a coherent grid with generous separation;
- one clean evidence strip containing the exact frozen count of fully populated detail panels;
- no decorative props, hands, splashes, scenery, packaging redesign, duplicate SKUs, or alternate variants;
- only genuine product-native text and graphics may appear.

Every visible panel must already contain useful product evidence in the generated board. Never request or accept blank cells, empty rectangles, placeholders, reserved slots, future-fill boxes, wireframes, or unused panels. Use narrow neutral gutters instead of drawn placeholder borders. The generation prompt must be independently usable as a final single-call prompt in an external image interface. The deterministic compositor may replace populated panels with frozen source crops for higher fidelity and normalize the canvas to exact 4K 16:9; it must never be required merely to remove blanks.

## Run sequence

### 1. Inspect and freeze identity

Inspect every supplied source. Freeze:

- silhouette and proportions;
- closure/pump/cap geometry and orientation;
- transparent/opaque material behavior;
- fill line, liquid color, dip tube, and internal elements;
- front/back label position, size, color, border, ornament, logo, and major copy;
- texture, embossing, seam, base, and edge features;
- unresolved regions and their evidence status.

Do not make OCR completion a global gate. Freeze enough observed facts to identify the SKU, silhouette, closure, material, label architecture, major source-visible copy, and selected detail risks; defer deep microcopy review until after imagegen submission.

### 2. Freeze the reference bundle

Copy the ordered user sources into a run-scoped immutable bundle:

```powershell
python scripts/freeze_reference_bundle.py `
  --run-dir <run-dir> `
  --manifest <run-dir>/reference-manifest.json `
  --reference front=<front-image> `
  --reference back=<back-image> `
  --reference three_quarter=<three-quarter-image>
```

Use only the aliases that exist. Preserve the order: primary/front, back, three-quarter, then optional detail/artwork sources.

The source ledger may contain more than five images, but imagegen may receive at most five paths. Never pass every frozen source path directly to the worker. Compile the provider-bound pack before prompt freeze:

```powershell
python scripts/build_generation_reference_pack.py `
  --reference-manifest <run-dir>/reference-manifest.json `
  --output-dir <run-dir>/attempts/<attempt-id>/provider-references `
  --manifest <run-dir>/attempts/<attempt-id>/generation-reference-pack.json
```

For one to five sources, the pack keeps the ordered frozen paths. For six or more, it keeps the first three complete-product anchors and deterministically combines the remaining evidence into two clean, text-free detail sheets. Use exactly the returned `provider_paths`, in order, for imagegen. Treat any provider count outside one to five as `BLOCKED_REFERENCE_MATERIALIZATION`; do not spawn a worker.

### 3. Freeze the exact generation prompt

Write the complete prompt to `<run-dir>/attempts/<attempt-id>/final_generation_prompt.md` as UTF-8/LF without BOM. Start from `references/generation_prompt_template.md`, then replace every placeholder with product-specific observed facts and explicit unknowns.

The prompt must state:

- one board only;
- eight complete product views and the exact frozen count of fully populated detail panels;
- the name and source-grounded content of every detail panel;
- exact SKU and identity locks;
- which views are source anchors and which are bounded completions;
- copy/graphic/texture/embossing constraints;
- front, back, side, three-quarter, high-angle, and low-angle views all keep the product upright on its base; high/low describe camera position, never a product lying down;
- No blank cells, empty rectangles, placeholders, reserved slots, future-fill boxes, wireframes, or unused panels;
- clean-board bans;
- no claim of 360 or hidden-surface exactness.

Reject the prompt before generation if it asks any region to remain visually empty, be reserved for later replacement, or omit generated content. Do not publish a staging prompt as a final generation prompt.

Describe direct anchors and deterministic detail sheets exactly as declared by `generation-reference-pack.json`. Write the prompt once, compute its SHA-256, then immediately publish the complete bytes inline. Record `PROMPT_PUBLISHED` before doing any other production work. If the prompt deadline is reached, freeze the best source-grounded version with explicit unknowns and terminate as `BLOCKED_PROMPT_READY_TIMEOUT`; do not continue silently rewriting it.

### 4. Delegate one image call

Only an explicit user invocation of this Skill authorizes a worker.

For each actual generation attempt:

1. Create a fresh 32-character lowercase hexadecimal nonce.
2. Record the parent thread ID and a spawn-time checkpoint.
3. Spawn exactly one fresh nonce-suffixed, non-decision image worker with `fork_turns="none"`.
4. Give it the already frozen prompt bytes and the one-to-five ordered `provider_paths`. Do not mention or invoke this Skill in the worker task.
5. Instruct the worker to make one `imagegen` call as its first and only tool action, using `referenced_image_paths`, then terminate with empty text.
6. Forbid the worker from reading the Skill, reading project/task files, rerunning the release gate, creating files, performing OCR, selecting references, rewriting the prompt, inspecting quality, approving, repairing, publishing, or calling any other agent.
7. Never use `num_last_images_to_include` for production binding and never submit more than five paths.

The main agent must not call imagegen directly. If the worker has not submitted imagegen within 90 seconds, interrupt it and terminate `BLOCKED_WORKER_SUBMIT_TIMEOUT` with the complete prompt. If submission occurred but no image is returned within 15 minutes, interrupt it and terminate `BLOCKED_IMAGEGEN_TIMEOUT`; do not create a replacement worker while the call state is unknown. Resolve a returned PNG with `scripts/resolve_worker_image.py` so prompt bytes, provider-reference bytes, parent/worker lineage, call ID, and image bytes are bound. Resolver failure means no generation-success claim.

### 5. Compose source evidence

Only after the resolver-bound raw preview has been shown, inspect the raw board and create a composition plan from `references/composition_plan.template.json`.

Fail the raw layout gate and repair before composition when any declared detail panel is blank, near-blank, framed as an empty placeholder, missing, or unused, or when a high/low-angle product is lying down. Do not let deterministic overlays hide a failed generation layout.

- Add one to three source anchor overlays when a supplied view should remain exact.
- Add one source-derived detail overlay for every frozen detail panel.
- Use only frozen run-scoped sources and real crop boxes.
- Bind every detail overlay by `region_id` to one explicit detail target box. Detail target boxes must be unique, non-overlapping, and filled exactly once.
- Replace the corresponding already-populated generated panel; do not create a new panel or rely on an empty target.
- Do not cover a different view, hide a defect, or introduce non-product text.

Run:

```powershell
python scripts/compose_asset_board.py `
  --run-dir <run-dir> `
  --plan <run-dir>/attempts/<attempt-id>/composition-plan.json `
  --receipt <run-dir>/attempts/<attempt-id>/composition-receipt.json
```

The output is an exact 3840 × 2160 PNG. The receipt binds the raw board, every source crop, every target box, and the final board.

### 6. Inspect and validate

Main-agent visual inspection is mandatory. Bind the accepted attempt in an asset manifest based on `references/asset_board_manifest.template.json`, then run:

```powershell
python scripts/validate_asset_board_run.py `
  --manifest <run-dir>/asset-board-manifest.json
```

Validate:

- exactly eight complete and distinct product views;
- the exact frozen count of four to six populated detail panels;
- every declared detail panel maps one-to-one to a unique, non-overlapping source-derived overlay and contains non-background pixels;
- stable SKU, silhouette, proportions, closure, liquid, material, label architecture, and feature placement;
- front/back/three-quarter anchors match their sources;
- critical copy/graphics are present in source-derived evidence windows;
- no invented readable copy is presented as exact;
- no non-product text pollution;
- `all_cells_populated: pass` from both main-agent inspection and deterministic detail evidence;
- exact 3840 × 2160 final canvas;
- frozen prompt/reference/worker/composition/final-image integrity.

### 7. Repair narrowly

Allow at most two repair attempts after the initial attempt. Each repair uses one new worker and one image call.

Start a repair only when enough of the 20-minute total automatic budget remains. A parameter error before an external image event permits one deterministic correction within 60 seconds; otherwise terminate with the complete prompt and explicit status. Never spend an unbounded interval rebuilding the ledger, prompt, or run directory.

Repair only the failed class in this order:

1. blank, empty, placeholder, unused, or broken board cells and non-product text pollution;
2. wrong SKU, silhouette, closure, label placement, liquid, or major graphic;
3. missing/duplicate/cropped full-product view;
4. source-anchor or detail-window mismatch;
5. material, embossing, or texture drift;
6. minor polish.

Do not respond to copy uncertainty by requesting a rotation capture set.

### 8. Publish one accepted board

Select exactly one accepted attempt. Return the final board image and a concise statement of:

- `assistant_qa_status: passed | conditional`;
- `copy_authority: video_reference | exact_copy_evidence`;
- any unresolved regions that matter to downstream use.

Persist the exact generation prompt and its SHA-256 next to the accepted board. Keep all operational metadata outside the image.

Repeat the complete prompt inline in the final result. Validate `prompt-dispatch-trace.json` before claiming acceptance. `ACCEPTED` requires exactly one completed image event for the accepted attempt, a resolver-bound PNG, a shown raw preview, passed board validation, and no premature success statement.

## Blocking conditions

Block only when:

- no supplied image identifies the product at all;
- reference files cannot be materialized or hash-bound;
- an explicitly requested exact-copy claim cannot be supported;
- the worker provenance cannot be bound;
- the final board cannot pass the eight-view, fully-populated four-to-six-detail, clean-image, or identity-consistency checks after three total attempts.

Use explicit runtime terminal states for bounded failures: `BLOCKED_RELEASE_GATE`, `BLOCKED_REFERENCE_MATERIALIZATION`, `BLOCKED_PROMPT_READY_TIMEOUT`, `BLOCKED_WORKER_START_TIMEOUT`, `BLOCKED_WORKER_SUBMIT_TIMEOUT`, `BLOCKED_IMAGEGEN_TIMEOUT`, `BLOCKED_VALIDATION`, or `REJECTED_AFTER_MAX_ATTEMPTS`. Every state after prompt compilation still delivers the complete prompt; none authorizes a request for more angles.

Missing hidden copy, unavailable OCR, or sparse angles alone are not blocking conditions for a normal `video_reference` board.

An optional later Canon bridge may consume the already accepted board without creating more views. It may authorize `label_copy` only when the board manifest already passed `copy_authority: exact_copy_evidence`; it is never part of the default board deliverable.

## Optional AI-Video Project Canon Export

This appendix is downstream compatibility for the already accepted board, not another board, angle set, or default deliverable. Run `scripts/export_ai_video_canon.py` only when an AI-video project explicitly needs a fixed-owner Canon record.

- Runtime dependency: this package's `requirements.txt` pins `Pillow` for deterministic board validation.
- `authority_stage: terminal_packaging_canon`
- `terminal_route_decision: not_applicable`
- `geometry_layout_only` authorizes `[product_geometry]` from an accepted board.
- `geometry_layout_exact_copy_verified` authorizes `[product_geometry, label_copy]` only when the bound board manifest has `copy_authority: exact_copy_evidence`, reviewed nonblocking OCR, zero unresolved claimed regions, passed label fidelity, and a live package-validator pass.
- The export bridge never generates, repairs, expands, or upgrades the board by inference.

## Final rule

The Skill succeeds when one board is useful and honest for downstream video generation and the user never waits through a hidden orchestration failure without a complete reusable prompt and truthful state. It does not succeed by manufacturing more views, more files, repeated gates, silent repair loops, or more authority than the evidence supports.
