---
name: packaging-product-identity-label-lock-board
description: Use when the user supplies one to three ordinary photos of a packaged product with dense copy, labels, logos, patterns, transparent liquid, texture, or embossing and wants exactly one clean horizontal 16:9 product identity asset board for downstream image or video models. The board combines eight complete product views with four to six source-evidenced detail windows; OCR is discovery evidence, never a reason to demand a 16-angle capture set.
---

# Packaging Product Identity Label Lock Board

Create one usable video-model reference board for one packaged product. Keep the stable Skill slug. Do not turn this workflow into a 360-degree capture factory, a print-proof system, or a family of new Skills.

## Runtime release gate

This package belongs to the High-Control AI TVC release suite. Before any production action, run `HIGH_CONTROL_RELEASE_GATE_V2` through the OS-native pinned-runtime launcher:

- Windows: `high-control-ai-tvc/tools/release-control.ps1 -Action check -Format json`
- macOS/Linux: `high-control-ai-tvc/tools/release-control.sh check --format json`

Continue only when `ready_latest=true`. Never use an unverified global Python to bypass the release gate or its pinned runtime.

## Core outcome

Deliver exactly one clean horizontal 16:9 board containing:

- exactly eight complete product views;
- four to six evidence detail windows selected from the real packaging risks;
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

If the user asks to OCR first, perform OCR discovery before prompt freeze. OCR remains nonblocking.

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

Select four to six detail windows by risk, not by a fixed checklist. Prefer:

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
- overwrite the detail windows with source-derived crops through `scripts/compose_asset_board.py`;
- keep critical readable copy in source-derived windows instead of trusting model-rendered microcopy.

This hybrid board is the primary fix for sparse-view, text-heavy products.

## Layout and visual rules

- requested canvas: 3840 × 2160, horizontal 16:9;
- neutral white or very light gray studio background;
- even, soft product light; no dramatic campaign styling;
- eight full-product views arranged as a coherent grid with generous separation;
- one clean evidence strip or reserved detail area containing four to six windows;
- no decorative props, hands, splashes, scenery, packaging redesign, duplicate SKUs, or alternate variants;
- only genuine product-native text and graphics may appear.

The generated raw board may reserve blank detail windows. The deterministic compositor may then replace those windows with frozen source crops and normalize the final canvas to exact 4K 16:9.

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

Do not make OCR completion a global gate.

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

### 3. Freeze the exact generation prompt

Write the complete prompt to `<run-dir>/attempts/<attempt-id>/final_generation_prompt.md` as UTF-8/LF without BOM. Start from `references/generation_prompt_template.md`, then replace every placeholder with product-specific observed facts and explicit unknowns.

The prompt must state:

- one board only;
- eight complete product views and four to six reserved detail windows;
- exact SKU and identity locks;
- which views are source anchors and which are bounded completions;
- copy/graphic/texture/embossing constraints;
- clean-board bans;
- no claim of 360 or hidden-surface exactness.

### 4. Delegate one image call

Only an explicit user invocation of this Skill authorizes a worker.

For each actual generation attempt:

1. Create a fresh 32-character lowercase hexadecimal nonce.
2. Record the parent thread ID and a spawn-time checkpoint.
3. Spawn exactly one fresh nonce-suffixed, non-decision image worker.
4. Give it the frozen prompt bytes and ordered frozen reference paths.
5. Require exactly one `imagegen` call using `referenced_image_paths` and then termination with no commentary.
6. Do not let the worker select references, rewrite the prompt, inspect quality, approve, repair, publish, or call any other agent.
7. Never use `num_last_images_to_include` for production binding.

The main agent must not call imagegen directly. Resolve the returned PNG with `scripts/resolve_worker_image.py` so prompt bytes, reference bytes, parent/worker lineage, call ID, and image bytes are bound.

### 5. Compose source evidence

After inspecting the raw board, create a composition plan from `references/composition_plan.template.json`.

- Add one to three source anchor overlays when a supplied view should remain exact.
- Add four to six source-derived detail overlays for the highest copy/graphic/material risks.
- Use only frozen run-scoped sources and real crop boxes.
- Place overlays only into the corresponding reserved board cells.
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
- four to six detail windows;
- stable SKU, silhouette, proportions, closure, liquid, material, label architecture, and feature placement;
- front/back/three-quarter anchors match their sources;
- critical copy/graphics are present in source-derived evidence windows;
- no invented readable copy is presented as exact;
- no non-product text pollution;
- exact 3840 × 2160 final canvas;
- frozen prompt/reference/worker/composition/final-image integrity.

### 7. Repair narrowly

Allow at most two repair attempts after the initial attempt. Each repair uses one new worker and one image call.

Repair only the failed class in this order:

1. non-product text pollution or broken board layout;
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

## Blocking conditions

Block only when:

- no supplied image identifies the product at all;
- reference files cannot be materialized or hash-bound;
- an explicitly requested exact-copy claim cannot be supported;
- the worker provenance cannot be bound;
- the final board cannot pass the eight-view, four-to-six-detail, clean-image, or identity-consistency checks after three total attempts.

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

The Skill succeeds when one board is useful and honest for downstream video generation. It does not succeed by manufacturing more views, more files, more gates, or more authority than the evidence supports.
