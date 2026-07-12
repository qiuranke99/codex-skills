---
name: packaging-product-identity-label-lock-board
description: Use when label-heavy packaging must be OCRed before generation and delivered as a rotation-ready product asset pack. The workflow freezes an exact-copy SSOT, decodes codes, binds logos and label artwork, plans R8/R12/R16/R24 azimuth coverage plus high/low/top/bottom and detail masters, generates one independent horizontal 16:9 master per unit, applies product copy deterministically, verifies the final pixels, and compiles review boards only from approved masters. Do not use for low-text simple products, prompt-only output, ad posters, scenes, or any workflow that expects a generative model to typeset exact packaging copy.
---

# Packaging Product Identity + Exact-Copy Rotation Asset Pack

Contract version: `asset_pack_contract_version: whole_product_ocr_rotation_pack_v3`.

Chinese name: 包装产品身份、文案与旋转连续性资产包

This Skill creates a production reference pack, not one generative collage. Its machine assets are independently generated or deterministically composed full-frame masters. Horizontal 16:9 review boards are derived from approved masters and never become the sole product truth.

## Required resources

Before acting, read completely:

- `references/packaging_asset_pack_contract.md` for artifact, exact-copy, coverage, prompt, QA, and state contracts;
- `references/view_coverage_profiles.json` for the canonical R8/R12/R16/R24 view IDs and conditional detail requirements;
- `references/generation_unit_prompt_template.md` before compiling any image-generation prompt.

The copy-ready JSON starters are `references/*.template.json`. They are
structural starters with explicit `REPLACE_*` and zero-hash values, never
pre-approved evidence. At minimum instantiate the source, surface, OCR/Text
SSOT, code, graphic, texture, mask, coverage, motion, continuity, composition,
prompt-index, asset-QA, continuity-QA, and post-verification templates. Replace
every placeholder, expand every required view/edge/result, re-hash the real
files, and validate the run before advancing state.

Install the package's pinned raster dependency before any OCR, composition,
review-board, continuity, validation, or Canon-export command:

```bash
python3 -m pip install -r requirements.txt
```

Use the bundled tools when their stage applies:

```bash
python3 scripts/run_ocr_preflight.py --help
python3 scripts/run_region_ocr.py --help
python3 scripts/compose_exact_copy.py --help
python3 scripts/compile_generation_prompts.py --help
python3 scripts/run_post_composite_verification.py --help
python3 scripts/build_continuity_measurements.py --help
python3 scripts/validate_packaging_run.py --help
python3 scripts/build_review_boards.py --help
python3 scripts/build_exact_copy_canon_evidence.py --help
python3 scripts/validate_template_contract.py
```

`scripts/validate_template_contract.py` proves that the shipped starters close
their feature, ID, authority, projection, post-OCR, prompt, and continuity
interfaces. `scripts/test_contract.py` is the package acceptance suite. Do not
claim the Skill is valid after editing unless both pass.

## Non-negotiable rules

1. Run whole-product OCR before compiling any image prompt. Full-image discovery OCR must precede region OCR.
2. OCR output is candidate evidence, not truth. Reconcile it against authoritative artwork, text masters, direct photographs, code payloads, and field-level review.
3. Freeze `exact_copy_bundle_sha256` before prompt compilation. Any later byte change invalidates every dependent prompt and asset.
4. A generative model is never the typesetter for exact packaging copy, logos, certification marks, barcodes, QR codes, batch codes, or dates.
5. In exact-copy mode, missing OCR, language, code-decode, artwork, or deterministic-projection capability blocks generation. Never silently downgrade to a geometry-only preview.
6. One generation unit produces one independent full-frame asset. Do not generate a contact sheet and crop it into machine references.
7. For video rotation, use a closed azimuth coverage graph with calibrated neighboring views. Front/back/one three-quarter image is not 360-degree coverage.
8. High angle is not top view. Low angle is not bottom view. Treat all four as distinct evidence roles.
9. Generated or inferred assets can never upgrade themselves to `source_verified`.
10. Review boards are deterministic composites of approved masters. Never feed a crowded overview board to a video model when the matching 2-4 adjacent masters exist.
11. Every source OCR detection and every final OCR detection needs an explicit reviewed disposition. Unknown or extra pseudo-copy blocks exact-copy authority.
12. Production authority is validator-derived. A JSON field named `authorized`, `approved`, or `passed` never authorizes itself.
13. `05_masters_raw` and `05_masters` are different byte domains: the generation receipt binds the raw asset; the composition replay binds the final asset.

## Routing and compound risk

Classify:

- `geometry_risk`: silhouette, depth, shoulder, closure, side wall, base, seams;
- `copy_risk`: text, numerals, units, punctuation, layout, batch/date fields;
- `code_graphic_risk`: logo, certification, barcode, QR, handling marks;
- `material_risk`: transparency, liquid, refraction, chrome, foil, print adhesion;
- `mechanism_risk`: pump, spray head, cap, lock/unlock, open/closed state;
- `motion_risk`: static hero, partial orbit, full spin, pitched orbit, macro rotation.

Use this Skill when packaging copy and rotation continuity are primary. When transparent, liquid, reflective, or layered material risk is also high, apply the material-sensitive risk rules inside the same main-agent compound workflow; do not let either contract claim complete coverage alone. A multi-component kit requires one asset pack per component plus a relationship manifest.

If the request is only a scene, poster, ad layout, or lifestyle composition, lock the product here first and route the later scene separately.

## Run root and durable truth

Create one run root:

```text
<workspace>/runs/packaging-product-asset-pack/<run_id>/
```

The required layout is:

```text
00_manifest/run_manifest.json
00_source/source_manifest.json
00_source/surface_inventory.json
01_ocr/ocr_observations.json
01_ocr/exact_copy_text_ssot.json
01_ocr/code_manifest.json
01_ocr/logo_graphic_manifest.json
01_ocr/exact_copy_bundle_manifest.json
02_coverage/coverage_matrix.json
02_coverage/motion_envelope.json
02_coverage/continuity_contract.json
03_composition/surface_texture_atlas.json
03_composition/protected_region_masks.json
03_composition/deterministic_composition_plan.json
04_prompts/generation_prompt_index.json
04_prompts/generation_units/<asset_id>_generation_prompt.md
05_masters_raw/<family>/<view_id>.png
05_masters/neutral_ring/
05_masters/high_angle/
05_masters/low_angle/
05_masters/upper_half_close/
05_masters/lower_half_close/
05_masters/top_bottom/
05_masters/details_structure/
05_masters/details_copy/
05_masters/details_material/
06_review_boards/
07_qa/asset_qa.json
07_qa/continuity_qa.json
07_qa/continuity_measurements.json
07_qa/composition_jobs/
07_qa/composition_receipts/
07_qa/post_ocr/
07_qa/graphic_comparisons/
07_qa/post_composite_verification.json
08_validation/packaging_exact_copy_canon_evidence.json
08_4k/four_k_prompt_index.json
```

`run_manifest.json` is the run SSOT. Chat text, a generated board, or an earlier prompt never substitutes for these files.

## Stage 0: runtime capability gate

Record observed capabilities only:

```text
image_generation_callable
reference_images_attachable
whole_product_ocr_callable
required_language_support
region_ocr_callable
barcode_decoder_callable
qr_decoder_callable
deterministic_compositor_callable
hashing_callable
image_file_inspectable
pixel_dimensions_inspectable
final_post_composite_vision_callable
exact_16_9_external_control
exact_4k_external_control
```

The discovery and source-bound region OCR runners support macOS Vision on
compatible Macs or Tesseract when installed. The v3 final-master
post-composite adapter is deliberately narrower: it uses bundled macOS Vision
for combined accurate text plus barcode/QR detection and has no Tesseract code
decoder fallback. Therefore an all-visible exact-copy run may advance toward
generation only when Darwin, Swift, the bundled Vision script, and Pillow pass
the runtime preflight. On Windows or Linux, or when that toolchain is missing,
set `blocked_ocr_capability` before prompt compilation; do not generate assets
that cannot reach COMPLETE. `run_region_ocr.py` never auto-approves output; it
returns `review_required`. For exact-copy requests,
`allow_geometry_only_preview` defaults to `false` and can become true only
after an explicit user instruction that also accepts
`production_approval_status: forbidden` and `rotation_ready: false`.

`compile_generation_prompts.py` re-derives the final capability from the live
host; it does not trust a manifest boolean. Every non-geometry-only mode checks
Darwin, Swift, both installed bundled scripts, the exact pinned Pillow version,
then runs the bundled OCR/EAN/QR live smoke before writing any prompt or index
bytes. A missing or failing capability blocks the compiler. Cross-platform
contract tests may exercise downstream validation through an in-process
test-only override, but the production CLI exposes no bypass.

## Stage 1: source ingest, variant resolution, and coordinate frame

Hash every original file and record dimensions, orientation, source kind, target SKU/instance, photographed state, and visible surfaces. Every direct photograph must also bind one canonical `view_id`, numeric azimuth/elevation, and the exact surfaces physically visible from that pose; a three-quarter image cannot be relabeled as a direct side/top/bottom anchor. Generated files and prior failed boards have `source_authority: prohibited`.

Stop on unresolved product-variant conflict. Do not merge labels, batches, closures, colors, or capacities from different variants.

Audit every canonical product feature, not only features that appear obvious. Each `product_feature_classification` row is `present` or `reviewed_absent` and binds source IDs, a named reviewer, and an evidence note. The run manifest stores exactly the present subset. This closed-world audit uniquely derives the minimum R profile, conditional detail masters, and continuity gates; omitting an inconvenient feature cannot reduce required evidence.

Freeze a product coordinate frame:

```text
z_axis: product vertical axis, positive upward
front_axis: outward normal of the authoritative front face
right_axis: product right when viewed from the authoritative front
azimuth_0: straight front
positive_azimuth: camera moves clockwise around the product when viewed from above
elevation_0: horizontal lens axis through the product visual center
product_state_id: one immutable physical state
```

Record fixed component IDs, geometry-landmark IDs, material-feature IDs, label surface anchors, closure orientation, pump/nozzle direction in product space, fill level, internal-tube topology, seam positions, embossing map, and base shape. Every source and view must reference only these frozen inventories, and generated views cannot first expose an ID absent from their direct parents. These facts belong in the manifest and continuity contract, not only in prose prompts.

## Stage 2: mandatory whole-product OCR and exact-copy freeze

### 2.1 Surface inventory

Inventory every visible and required coordinate surface: `front`, `back`, `left`, `right`, `top`, and `bottom`. Do not overload this camera-facing topology with subparts. Freeze `closure`, `collar`, `shoulder`, `base edge`, `mold seam`, `batch_stamp`, `embossing`, label zones, and code zones as component IDs, physical-layer IDs, or region IDs anchored to one of those six coordinate surfaces. Every coordinate surface and every anchored region must end as:

```text
text_detected | verified_no_copy | decorative_graphic | occluded | needs_source
```

Absence of an OCR detection is not proof of `verified_no_copy`.

### 2.2 OCR order

1. Run full-image OCR on every original product source to discover all copy, including small or unexpected markings.
2. Create source-bound region crops for every detected or expected text, code,
   native-graphic, or mixed evidence region. Each spec binds `surface_id`,
   `physical_layer_id`, `visibility_mode`, and `region_purpose`.
3. Crop declared regions and run accurate region OCR without language-model autocorrection. V3 accepts only the bundled, replayable axis-aligned normalized crop implemented by `scripts/run_region_ocr.py`. A perspective, cylindrical, mesh, or depth-warped label requires a new authoritative orthographic source or a future contract version with a bundled deterministic rectifier; it blocks this V3 exact-copy path and cannot be approximated silently.
4. Compare multiple passes, preprocessing variants, engines, and source views where available.
5. Reconcile fields against authoritative sources. Escalate only genuinely unresolved differences; do not ask the user to retype information already legible in supplied files.

Every OCR observation must end with one reviewed disposition:

```text
mapped_to_field | duplicate_showthrough | decorative_non_product_copy | false_positive
```

`unresolved` and `review_required` are discovery states and block `READY_FOR_GENERATION`. A `verified_no_copy` surface requires a named reviewer and evidence note; it cannot be inferred from zero detections. Region crop authority additionally binds the original source hash, region spec, normalized crop geometry, surface, physical layer, visibility, purpose, installed rectifier hash, crop receipt self-hash, and pixel-for-pixel crop replay. Crop provenance and text presence are separate gates: `text` and `mixed` regions require at least one region text detection; `code`-only and `graphic`-only regions may contain zero OCR text, but they remain blocked until their decode or graphic disposition is reciprocally mapped and approved by a named reviewer. Zero text never proves `verified_no_copy`.

When all visible copy must be exact, `C_texture` is illegal. Promote every product-native character to `A_exact`.

### 2.3 Transparent packaging layers

Separate direct copy from show-through:

```text
front_print_outer
front_label_opaque
front_embossing
internal_content
internal_components
rear_print_outer
rear_label_or_compliance_block
```

Mirrored or refracted rear copy visible through the front is an observation of the rear field, not a new front field. It must carry `visibility_mode: mirrored_showthrough` or `refracted`. Occluded characters cannot be filled by language inference.

### 2.4 Codes and graphics

- Barcode: bind symbology, payload, checksum, source symbol asset, and successful final decode.
- QR: bind raw payload bytes and printed-symbol evidence separately.
- Logo, certification, recycling, and handling marks: bind a master asset or approved orthographic crop and SHA-256. OCR resemblance cannot approve a graphic.
- Batch/date/lot fields: prefer the photographed instance over a generic SKU artwork master.

### 2.5 Exact-copy bundle and hard gate

Freeze:

```text
text_ssot_sha256
code_manifest_sha256
logo_graphic_manifest_sha256
surface_texture_atlas_sha256
protected_region_masks_sha256
deterministic_composition_plan_sha256
exact_copy_bundle_sha256
exact_copy_bundle_file_sha256
```

Prompt compilation is legal only when:

```text
copy_preflight_status == passed_ssot_frozen
AND exact_copy_bundle_hash_verified == true
AND unresolved_required_field_count == 0
AND source_conflict_count == 0
AND required_code_decodes_pass == true
AND logo_graphic_binding_pass == true
AND deterministic_composition_plan_status == ready
AND required_view_surface_coverage_status == passed
```

Then and only then set `prompt_compilation_allowed: true` and `image_generation_allowed: true`.

## Stage 3: motion envelope and view coverage

Do not choose views from a generic checklist alone. Freeze the intended motion envelope first: static hero, bounded orbit, neutral-height full spin, pitched orbit, macro rotation, or mechanism state change.

Use only the canonical motion pairs in the contract. `bounded_high_orbit` and
`bounded_low_orbit` may use the four cardinal high/low anchors. A
`pitched_full_rotation` scope must declare the matching complete profile-sized
`HIGH` and/or `LOW` ring with every edge and final-to-first closure; four
anchors can never authorize a pitched full spin.

Select the neutral ring from `references/view_coverage_profiles.json`:

- `R8`: 45-degree spacing; only simple, near-rotationally-symmetric, low-copy products.
- `R12`: 30-degree spacing; default for ordinary label-heavy packaging.
- `R16`: 22.5-degree spacing; default for transparent, flat/rectangular, wrap-label, non-symmetric closure, pump, or high material-risk products.
- `R24`: 15-degree spacing; macro rotation, complex reflection, or continuous wrap-copy when the evidence supports it.

For a normal production pack also require:

- high-angle full-product front/right/back/left at approximately +25 to +35 degrees;
- low-angle full-product front/right/back/left at approximately -15 to -25 degrees;
- true top at +90 degrees;
- true bottom at -90 degrees;
- required structural, copy, code, and material details.
- four-way `upper_half_close` and four-way `lower_half_close` bridge masters at
  front/right/back/left, so video reframing never jumps directly from a full
  product to an unrelated macro.

If the target motion performs a full rotation at high or low elevation, four anchors are insufficient; use a full high/low R12, R16, or R24 ring.

Each coverage row records numeric pose, shot scale, visible surfaces, source refs, preceding and following view, visible field/code/graphic IDs, material features, derivation status, and production authority. Every `source_refs` value must resolve to the source manifest, and a `source_verified` surface claim must be covered by those source records. The neutral ring must close from the last angle back to 0 degrees. A pitched full rotation declares a complete `elevation_rings` sequence in the motion envelope; the validator compiles and checks its profile-matched adjacency and loop.

Use separate evidence dimensions:

```text
pose_source_status
surface_source_status
copy_source_status
material_source_status
derivation_status
```

`inferred_from_sources` is allowed only for a `generated` view with at least two unique source-verified parent anchors. The inferred view cannot first reveal a new surface, seam, top, bottom, field, code, graphic, or asymmetric mechanism; all four evidence dimensions must be inferred or legitimately not applicable. Any `needs_source` value blocks production authority.

The validator derives visible surfaces from the canonical product coordinate frame: 0° front, 90° right, 180° back, 270° left; intermediate azimuths require both adjacent surfaces; high views also require top, low views bottom, and true top/bottom require their own direct surfaces. One v3 run may declare at most one dynamic `HIGH` ring and one dynamic `LOW` ring because their IDs do not encode elevation. A second ring with the same prefix is a collision and fails closed.

## Stage 4: independent master assets, not a generated board

Every generation unit creates exactly one horizontal 16:9 full-frame asset with one product or one detail job. Full-product masters must keep one calibrated lens profile, camera distance profile, product-center height, object occupancy, neutral background, lighting, state, and rotation axis.

Exact 16:9 is necessary but not sufficient. Every raw and final machine master
must decode at no less than 1280x720. The generation receipt records the
returned pixel dimensions and `post_generation_resize_applied: false`; the
validator re-opens both files, rejects a smaller canvas, and requires exact-copy
composition to preserve the raw canvas dimensions. A 512x288 image placed on a
4K review board, or resized after generation merely to meet the floor, never
becomes an approved machine master. This is a minimum HD delivery floor, not a
native-4K claim.

Required shot scales:

```text
full_product
upper_half_close
lower_half_close
macro_component
rectified_surface_evidence
```

These are executable requirements, not a vocabulary list. The coverage
profile freezes all eight upper/lower bridge rows. Every fixed `DETAIL_*` also
freezes family, shot scale, numeric azimuth/elevation, target coordinate
surface, framing, focus, and semantic review-board role. A detail name that
contradicts its camera pose fails before prompt compilation.

Base detail families include:

- front and back label plates;
- left and right label wrap/seam;
- closure/pump front, side, and top;
- neck, collar, shoulder, and actuator interfaces;
- side-wall depth, mold seam, base edge, and true bottom;
- capacity, batch/date/lot, barcode, QR, certification, and handling marks;
- print boundary, foil/embossing, label adhesion, texture, and material transitions.

Transparent/liquid/pump products additionally require fill line, air layer, internal tube start/middle/end, bottle-wall thickness, refraction boundary, reverse show-through, and internal/external layer details.

The fixed detail catalog never substitutes for actual copy regions. Derive one
additional safe, collision-checked `DETAIL_REGION_<slug>_<hash>` master for
every unique Text SSOT, Code, or Graphic `region_id`. That master binds exactly
one physical region and exactly its field/code/graphic IDs. At COMPLETE, the
validator measures its projected bbox and smallest raw OCR line against the
frozen 3840x2160-equivalent region, text, code, and graphic thresholds. A
single generic back-label detail cannot absorb several dense or spatially
separate regions. “3840x2160-equivalent” is a normalized readability reference
canvas; it does not prove that the source master is native 4K.

## Stage 5: prompt compiler contract

Create one prompt per generation unit. It must bind:

```text
asset_id
product_coordinate_frame
product_state_id
camera_pose: azimuth/elevation/roll
shot_scale
lens_profile and camera_distance_profile
geometry_landmark_contract
surface_atlas_sha256
exact_copy_bundle_sha256
exact_copy_bundle_file_sha256
coverage_matrix_sha256
visible_surface_ids
ranked_reference_ids
previous_anchor_id and next_anchor_id
protected_copy_region_ids
deterministic_composition_plan_id
generation_authority
forbidden_inventions
```

The prompt must request one complete product or one explicit detail, not a board. It must use `horizontal 16:9` as the sole creative ratio request when the built-in image tool exposes no explicit ratio argument.

The prompt must explicitly set:

```text
generation_text_policy: no_model_generated_product_copy
raw_generated_asset_publishable: false
raw_generated_asset_registry_eligible: false
```

For text-bearing surfaces, generate only a source-bound substrate/base with protected copy regions or use an editing path that preserves supplied exact pixels. Do not paste OCR text into the prompt and expect the model to typeset it.

Before every image call:

1. after every hard gate passes, compile the frozen batch with
   `python3 scripts/compile_generation_prompts.py <run_root>`;
2. record the returned `generation_prompt_index_sha256` in
   `run_manifest.hashes.generation_prompt_index_sha256`; do not rewrite any
   prompt while doing so;
3. for the current unit, re-read the exact prompt bytes at
   `04_prompts/generation_units/<asset_id>_generation_prompt.md` and verify its
   SHA-256 against `generation_prompt_index.json`;
4. show the complete prompt and hash;
5. make the image-generation call the terminal action of that turn.

The compiler refuses closed generation gates, stale dependency hashes,
incomplete identity/material locks, unknown reference IDs, partial composition
coverage, or replacement of different frozen bytes without explicit
`--replace`. `--replace` is an invalidation action: recompile and regenerate
every affected asset; it is never a convenience overwrite.

Any dependency change invalidates the prompt and all derived assets. Never reconstruct a prompt after the fact.

## Stage 6: per-master inspection and continuity QA

Inspect each returned master in a later continuation. Reject:

- cropped or multiple products;
- camera/lens/scale drift;
- silhouette breathing or topology change;
- closure or nozzle rotating independently of the body;
- label migrating, duplicating, disappearing, or crossing surfaces;
- fill-level movement, broken internal tube, drifting embossing;
- incorrect transparent show-through or material response;
- any model-generated product copy in protected regions.

Run adjacent-edge QA for every neighboring view and loop-closure QA for the final-to-front edge. Build byte-bound measurements with `scripts/build_continuity_measurements.py`; the builder also reads and locks `00_source/source_manifest.json`. The only legal gate set is derived from the reviewed-present feature taxonomy. Universal gates cover product frame, topology, silhouette, label/surface binding, material, camera calibration, adjacent edges, loop closure, exact-copy render, and board derivation. A visible fill line/liquid boundary adds fill volume; pump/spray adds nozzle-frame binding; a visible dip tube adds tube topology; emboss/deboss adds registration; transparent/translucent adds show-through. A gate for a reviewed-absent feature is invalid, and omission of a derived gate is invalid.

`continuity_qa.json` must contain one result per derived hard gate and one hash-bound result per ring edge, each bound to actual approved master hashes, installed measurement-tool hash, non-empty metric records, declared comparator/tolerance, and a self-hashed evidence receipt. Screen-space constancy is not continuity authority: label registration is measured in a surface-local frame; nozzle vectors are measured in a product/closure-local frame; silhouette, material, and show-through compare each pose against source-bound baselines frozen in `continuity_contract.json` before generation; every adjacent edge and the final-to-first loop compare actual landmark motion vectors with frozen pose-conditioned baselines. Missing, stale, or post-hoc calibration remains blocked.

Pass `packaging-continuity-semantic-evidence.v2` with `--semantic-evidence`. It locks source manifest, asset QA, coverage, and continuity-contract bytes. Each `packaging-continuity-annotation.v2` contains only normalized, hash-bound raw landmarks, polylines, polygons, or masks; it cannot contain computed `value`, `status`, `tolerance`, `comparator`, or `algorithm_id`. The semantic file selects one frozen algorithm and parameters per derived gate/edge, and the bundled builder derives each value and status from raw structures, approved master bytes, and pre-generation calibration. Image statistics, pass strings, stationary billboard labels, or constant screen geometry never approve product-space continuity.

Repair only one failed asset or one failed dependency at a time. Never regenerate the complete pack because one view fails. Attempt at most two generative repairs per asset before stopping on the real source or capability blocker.

## Stage 7: deterministic exact-copy composition and post-verification

The raw generative master is never publishable. First verify that protected regions contain no surviving generated pseudo-copy. Then apply the frozen exact-copy assets using a recorded method:

```text
source_pixel_preservation
planar_rectangle
planar_homography
```

If a required view has no reliable projection method, set `blocked_no_deterministic_projection`; do not let the model redraw the label.

Use `scripts/compose_exact_copy.py` with `references/exact_copy_composition_job.template.json`. The bundled compositor supports source-pixel preservation, rectangular planar placement, and deterministic four-corner planar homography. Every job has a semantic self-hash, locks the raw base, layers, masks, visible field/code/graphic IDs, destination geometry, final output, and receipt path. The validator reloads the installed compositor and replays every COMPLETE job byte-for-byte. Cylindrical, conical, mesh, or depth-aware projection is not bundled in v3; a view needing one must remain `blocked_no_deterministic_projection` unless an equivalent callable and validator are added.

After composition, run `scripts/run_post_composite_verification.py` to repeat whole-product and projected-region OCR, barcode/QR decode, deterministic logo/graphic projection verification, and label-registration QA with the bundled OCR/decode adapter. The command intentionally writes immutable `07_qa/post_composite_verification.candidate.json`; it never edits the canonical manifest. Review the candidate and all referenced OCR/decode/graphic receipts, require `candidate_status: ready_for_manifest_binding`, copy the exact candidate bytes without rewriting into `07_qa/post_composite_verification.json`, record that file hash as `run_manifest.hashes.post_composite_verification_sha256`, and re-run the validator. If any byte changes, discard the promotion and rerun the adapter. This review-and-bind step is evidence promotion, not approval: only the validator may derive the locks below.

In v3 this final OCR/decode adapter is macOS-only. A Tesseract discovery or
region pass does not imply final barcode/QR capability. If the same frozen run
cannot return to a verified Mac for post-composite execution, block it during
Stage 0 rather than generating unfinishable exact-copy masters.

A Text SSOT field uses either one exact observation or explicitly declared ordered-line aggregation; the latter follows fixed bounding-box reading order and hashes the aggregate UTF-8 bytes without language-model correction. `post_composite_verification.json` must cover every approved master and exactly the field/code/graphic IDs declared visible for that view. Extra OCR text, duplicate fields, unknown product-native observations, undeclared codes, or an untrusted/run-local engine fail exact-copy approval. Every result binds the final master hash plus OCR/decode/comparison/compositor receipts. This adapter does not verify transparent-layer order, refraction, fill level, internal components, or material continuity; those remain owned by the continuity measurement and semantic-evidence pipeline. Top-level approval values are derived from these records, never accepted as self-reported truth. Report independently:

```text
copy_content_lock_status
label_artwork_lock_status
code_payload_lock_status
code_symbol_lock_status
logo_graphic_lock_status
geometry_lock_status
material_lock_status
continuity_lock_status
```

`exact_copy_lock_status: approved` is legal only when all required copy-related locks pass against the frozen bundle.

## Stage 8: deterministic review boards and downstream use

Build review boards only with `scripts/build_review_boards.py` from approved masters. Never image-generate them.

Build one semantic sequence at a time: `neutral_rotation`, `elevation`,
`framing_bridge`, `copy`, `code`, `structure`, or `material`. Neutral and
elevation/bridge boards use canonical camera order; detail boards use stable
view-ID order. The validator requires every approved master exactly once,
preserves the ordered view IDs across pagination, and rejects mixed-role or
reordered boards.

- geometry QA board: at most 6 full-product masters at 4K 16:9;
- detail QA board: at most 4 large evidence regions at 4K 16:9;
- dense index board: allowed only as `review_only_no_qa_authority`;
- split boards whenever the minimum cell size would be violated; never shrink evidence to force one board.

The 4K value above describes the review-board canvas only. It never upgrades
the resolution authority of any input master.

Typical outputs:

```text
overview_index_16x9.png
rotation_000_180_16x9.png
rotation_180_360_16x9.png
elevation_16x9.png
structure_details_16x9.png
copy_evidence_16x9.png
material_details_16x9.png
```

Downstream video prompts select the 2-4 approved masters adjacent to the intended camera/object trajectory, plus the required exact-copy and material anchors. Do not attach the entire contact sheet as the only reference.

## External 4K

External 4K enhancement is per approved master, not one global board rewrite. Every enhancement prompt binds the source master, original sources, exact-copy bundle, coverage plan, and observed defects. Exact copy must remain deterministic after enhancement and must pass OCR/decode again.

External 4K is a separate delivery state. A verified enhanced 4K result is not
`native_4k`, and no 4K claim is legal until the returned 3840x2160 pixels,
lineage, deterministic copy recomposition, and repeat OCR/decode/comparison have
all been validated. Masters below the 1280x720 floor cannot gain production
eligibility merely by upscaling.

Use exact external controls only:

```text
aspect_ratio: "16:9"
image_size: "4K"
alternate_aspect_ratios_allowed: false
```

If the provider lacks either control, set `blocked_runtime_controls`; do not substitute another size or ratio. Review boards are rebuilt deterministically from the returned verified masters.

## Run states and completion

Allowed run states:

```text
SOURCE_INGESTED
OCR_DISCOVERY_COMPLETE
COPY_REVIEW_REQUIRED
COPY_SSOT_FROZEN
COVERAGE_PLAN_FROZEN
READY_FOR_GENERATION
GENERATING
INSPECTING
COMPOSITING_EXACT_COPY
POST_COMPOSITE_VERIFYING
BUILDING_REVIEW_BOARDS
QA_PASSED
COMPLETE
BLOCKED
```

Per-asset states:

```text
PLANNED
PROMPT_FROZEN
GENERATED
INSPECTED
TEXT_POLLUTION_PASSED
COPY_COMPOSITED
POST_VERIFIED
APPROVED
REJECTED
```

The run is `COMPLETE` only when `python3 scripts/validate_packaging_run.py <run_root>` exits zero and:

- OCR and exact-copy bundle gates pass;
- the requested motion coverage graph is complete and closed;
- every required independent master is approved;
- every raw and final machine master is exact 16:9, at least 1280x720, and its
  generation receipt proves no post-generation resize was used to meet the floor;
- continuity, geometry, material, copy, codes, and graphics pass;
- review boards are deterministic and role-labeled;
- prompt, asset, board, manifest, and QA hashes re-read correctly;
- production approval is explicit when required.

A visually attractive board never overrides a failed gate.

## Final result contract

Per generation turn, disclose the complete unit prompt and its SHA-256 before the terminal image call. At final completion, publish concise Chinese text containing:

```text
run_root
run_manifest_path and sha256
source_manifest_sha256
exact_copy_bundle_sha256
coverage_matrix_sha256
generation_prompt_index_path and sha256
approved_master_count / required_master_count
review_board_paths and sha256 values
four_k_prompt_index_path and sha256 when applicable
copy_content_lock_status
label_artwork_lock_status
code_payload_lock_status
code_symbol_lock_status
logo_graphic_lock_status
geometry_lock_status
material_lock_status
continuity_lock_status
exact_copy_lock_status
coverage_status
assistant_qa_status
production_approval_status
task_finalization_status
```

The scalable prompt indexes and sidecars are the durable prompt truth. Do not concatenate dozens of full unit prompts into the final response; each was already disclosed before its generation call and remains hash-bound on disk.

## Optional AI-Video Project Canon Export

Canon export remains optional and cannot upgrade any lock. Use `scripts/export_ai_video_canon.py` only after the asset pack QA passes, prompt and asset indexes re-hash, the selected primary packaging asset is fully decodable, and production approval is explicit.

Default export uses `authority_mode: geometry_layout_only` and authorizes only `product_geometry`. Use `geometry_layout_exact_copy_verified` and authorize `label_copy` only when all copy, artwork, code, graphic, and post-composite gates pass. A review board with missing masters, an inferred view, a generative label, or a conditional exact-copy result cannot authorize `label_copy`.

Exact-copy export must use `scripts/build_exact_copy_canon_evidence.py` to create a v2 sidecar, then pass it with `--packaging-exact-copy-evidence LOCATOR=SHA256`. The v2 sidecar binds the COMPLETE run manifest, installed validator hash, frozen exact-copy bundle, coverage matrix, prompt index, asset QA, continuity QA, post verification, and one unique primary master/post-result member. During export the shared bridge executes `validate_packaging_run.py` again and compares the selected primary path and bytes. Approval JSON, a v1 sidecar, a review board, an arbitrary PNG, or status strings alone never grant `label_copy`.

The fixed lifecycle markers are:

```text
authority_stage: terminal_packaging_canon
terminal_route_decision: not_applicable
geometry_layout_only -> [product_geometry]
geometry_layout_exact_copy_verified -> [product_geometry, label_copy]
```

Pillow must be installed from this package's pinned dependency file before the
workflow or optional export: `python3 -m pip install -r requirements.txt`.
The shared bridge must verify and fully decode the selected primary
PNG/JPEG/WebP asset before any Canon write.

The existing fixed-owner bridge exports one selected primary packaging asset. It does not replace the run manifest or compress a rotation pack into one source of truth.
