---
name: complex-product-identity-reconstruction-asset-locking
description: "Reconstruct and lock a source-evidenced Visual Product Identity Model for complex multi-part, multi-material, stateful products, then directly generate and validate a geometry/material/component/state/marking asset package plus one minimal-dense final identity board and per-asset 4K enhancement handoff. Use for wheelchairs, medical or industrial equipment, robots, cameras, fitness machines, complex furniture, strollers, bicycles, motorcycles, electronics, and other products whose topology, interfaces, moving parts, or state changes make a simple product board unsafe. Do not use for simple low-risk products, packaging-copy-first work, material-response-first glass/liquid products, ads or lifestyle scenes, source search, ordinary retouching, prompt-only delivery, or products without a usable visual reference."
---

# Complex Product Identity Reconstruction & Asset Locking

## Standalone Runtime Contract

Run this Skill directly from its own package. Its evidence contracts, initializer, validator, deterministic tests, and package templates are package-local and require no release manager or sibling Skill. Built-in image generation remains the only host production capability; the package's core scripts otherwise use the Python standard library.

The accepted `partial_approved` or `complete` package is a portable downstream input artifact. Other workflows may consume its frozen specification, approved boards, manifest, and 4K handoff, but no exporter or downstream package is required for identity analysis, board generation, validation, or delivery. A supplied upstream evidence ledger is treated as input and must still pass this Skill's source gates.

Chinese name: 复杂产品身份重建与资产锁定 Skill

`runtime_contract_version: complex_product_identity_asset_package_v1`

Build a reusable product identity system for downstream AI video, keyframes, TVC, and commercial visual production. Treat the input as evidence for one Visual Product Identity Model, never as a request for an attractive multi-angle product collage.

The main agent owns identity resolution, evidence classification, board eligibility, visual QA, repair decisions, package validation, and final delivery. This Skill does not authorize subagents, external model calls, product redesign, or unsupported completion.

## Input Gate

Require at least one usable image of the target product. Accept single or multiple product photographs, official images, detail-page screenshots, manual illustrations, documentation images, and local component crops.

Resolve one product variant before generation. If references show conflicting models, revisions, accessories, colorways, or states that cannot be separated, return `blocked_identity_conflict`. A single image may pass analysis while failing one or more board source gates.

Do not require the user to restate downstream purpose, aspect ratio, or folder structure. Default to video-continuity assets, horizontal 16:9, neutral studio treatment, and the package contract below.

## Output Contract

Create `Complex_Product_Identity_Asset_Package/` with:

1. `01_Product_Identity_Specification.md`
2. `02_Geometry_Lock_Board/`
3. `03_Material_Surface_Lock/`
4. `04_Component_Detail_Lock/`
5. `05_State_Transition_Lock/`
6. `06_Marking_Identity_Lock/`
7. `07_Final_Product_Identity_Lock_Board/`
8. `08_4K_Upscale_Prompts.md`
9. `asset_package_manifest.json`

Use `scripts/init_asset_package.py --output <exact-package-path> --asset-id <stable-id>` before analysis. Read `references/package-contract.md` before writing manifests, generating 4K prompts, or claiming completion.

## Required References

- Read `references/product-identity-contract.md` before identity analysis, part-tree construction, confidence labeling, or board eligibility decisions.
- Read `references/generation-runtime-and-qa.md` before composing any built-in image-generation call, inspecting a returned board, or repairing a failure.
- Read `references/package-contract.md` before initializing, validating, or delivering a package.
- Read `references/test-cases.md` when validating trigger behavior or revising the Skill.

## Stage 1 — Product Identity Analysis

Inspect every input before any image-generation call.

1. Build a source ledger with stable source IDs, file paths or conversation references, source role, crop/state/variant notes, and conflicts.
2. Separate product-intrinsic facts from camera perspective, lighting, reflections, environment color, grade, motion blur, and compression artifacts.
3. Write one Product Identity Specification covering overall geometry, proportions, silhouette, frame/support system, primary components, component count, connection topology, materials, colors, surface response, texture direction, markings, interfaces, and supported states.
4. Build a Product Part Tree with parent/child relationships, detachable parts, connectors, attachment method, interface location, symmetry, count, and identity risk.
5. Build an evidence-bounded State Graph. Include a state or transition only when directly observed or cross-validated. Do not infer a motion mechanism merely because the product category commonly has one.
6. Label every atomic claim exactly `Observed`, `Cross Validated`, `Inferred`, `Unknown`, or `Conflicting`. Never promote `Inferred` or `Unknown` into source truth.
7. Freeze the specification and source bundle hashes before Stage 2. If a newly found conflict changes identity truth, return to this stage and invalidate affected downstream boards.

Do not generate while `01_Product_Identity_Specification.md` lacks the five evidence classes, a Product Part Tree, a State Graph, board-source decisions, or unresolved-conflict disclosure.

## Stage 2 — Identity Reconstruction

Generate boards sequentially by risk, never as one all-in-one generation. Every board uses the frozen original reference bundle plus the frozen specification as authority. Do not use a previously generated board as the sole or higher product-identity authority for another board.

For every generation request:

- call Codex built-in image generation directly;
- request one horizontal 16:9 image;
- use high-quality commercial product photography under neutral, soft, color-controlled studio lighting;
- preserve exact source-supported geometry, component count, proportions, materials, markings, and state;
- exclude titles, labels, captions, arrows, legends, measurements, watermarks, UI, product names, people, props, scenes, posters, and decorative backgrounds;
- keep every product view complete, non-overlapping, consistently scaled, and grounded by subtle neutral shadows;
- keep the complete internal generation prompt private; write only its SHA-256 to the manifest and never publish the prompt in chat or the asset package.

### Phase A — Geometry Lock

Treat Geometry Lock as required for a complete package. Generate one Canonical Geometry Asset Board containing exactly eight complete, non-redundant views: front, rear, left, right, front three-quarter, rear three-quarter, high-angle, and low-angle.

Approve the board source gate only when the inputs support every high-risk surface, component count, and connection relationship needed by those views. If hidden or underside structure would require invention, block this board instead of generating a partial or fabricated eight-view board.

### Phase B — Material & Surface Lock

Set relevance to `required` when mixed materials, coatings, reflective response, fabric direction, rubber/plastic/metal boundaries, transparent parts, wear, or surface texture materially affect identity. Set it to `not_applicable` only for genuinely homogeneous low-risk products.

Generate neutral diagnostic whole-product views plus source-supported material/detail windows. Separate intrinsic base color, roughness, metalness, translucency, reflectivity, texture, and coating from photographic lighting effects. Exclude cinematic contrast, environment color contamination, stylized grade, bloom, dramatic haze, and colored rim light.

### Phase C — Component Detail Lock

Set relevance to `required` when identity or function depends on joints, hinges, fasteners, pivots, wheel hubs/axles, brakes, controls, buttons, ports, mounts, latches, cables, interfaces, or structural connection nodes.

Generate only evidence-supported component closeups that preserve part-to-part relationships, orientation, attachment, scale, and material boundaries. Do not show internal construction that the sources do not reveal.

### Phase D — State & Motion Lock

Set relevance to `required` only when the product has source-supported operational or storage states such as open/closed, folded/deployed, raised/lowered, attached/detached, rotated, adjusted, or working/idle.

Generate one State Transition Asset Board only when every depicted state and transition endpoint is `Observed` or `Cross Validated`. An `Inferred`, `Unknown`, or `Conflicting` mechanism blocks the affected state board. Do not invent intermediate mechanics or impossible part travel.

### Phase E — Marking Identity Lock

Set relevance to `required` when logos, brand text, labels, graphics, stitch patterns, symbols, control legends, serial plates, or directional patterns are identity-critical.

Generate a Marking Identity Asset only from legible, sufficiently resolved evidence. Preserve placement, scale, orientation, color, hierarchy, and pattern relationship. Never redesign a logo or fill unreadable copy. Record `marking_exactness_status: reference_locked | visually_verified | blocked_exactness_evidence`; generative resemblance alone cannot establish exact copy.

## Board-Scoped Source Gate

For each A–E board, record:

- `relevance: required | conditional | not_applicable`;
- `source_gate: approved | blocked | not_applicable`;
- evidence IDs and unsupported zones;
- `status: planned | generation_pending | awaiting_post_generation_continuation | qa_pending | repair_required | approved | blocked | not_applicable`.

Generate only when `source_gate: approved`. A blocked conditional board does not invalidate approved boards, but the package remains `partial_approved` unless the complete-package gate is satisfied. Never describe a partial set as the final Product Identity Lock Board package.

## Terminal Image-Generation State

Before each built-in image call, persist `generation_pending` and `terminal_generation_call: pending`. The image call is the final action of that turn. After the returned image exists, persist `awaiting_post_generation_continuation`; do not claim QA or package completion.

On the next continuation, bind the exact returned image, record actual dimensions, set `qa_pending`, visually inspect it, and either approve it or set `repair_required`. If the host does not continue automatically, resume from the manifest on the next user continuation. Never reconstruct completion from memory alone.

## Automatic QA And Local Repair

Inspect the exact pixels of every returned board. Check:

- geometry consistency: silhouette, proportions, part count, topology, interfaces, symmetry, and view agreement;
- material consistency: base color, material assignment, texture direction, roughness, metalness, reflectivity, transparency, and coating boundaries;
- identity consistency: logo/marking placement, patterns, stitch lines, fasteners, controls, ports, and distinctive details;
- failure flags: added part, missing part, fused structure, mirrored asymmetry, left/right swap, duplicated component, material drift, color drift, marking drift, unsupported state, deformation, crop, overlap, or text pollution.

On failure, diagnose the smallest affected board, update only the relevant constraints, and regenerate only that board from the frozen original sources and specification. Do not regenerate approved boards unless their source truth changed. Limit repairs to two attempts per board; after two failed repairs, set that board to `blocked_generation_quality` and keep the accepted remainder explicitly partial.

## Stage 3 — Final Asset Packaging

### Internal Product Asset Package

Package every approved relevant A–E board, its manifest record, actual dimensions, source-evidence IDs, prompt hash, QA result, and repair lineage. Preserve `blocked` and `not_applicable` decisions in the root manifest; do not create decorative placeholder images.

### Final Product Identity Lock Board

Generate the final board only when Geometry Lock is approved, every `required` board is approved, no hard identity conflict remains, and the selected references meet the minimum downstream coverage in `references/package-contract.md`.

Use the frozen original sources as the highest authority and approved A–E boards as secondary layout/detail support. Include only the smallest non-redundant set that carries maximum identity information. Exclude repeated views, decorative backgrounds, advertising design, titles, captions, and product-name text. Inspect and repair the final board with the same QA gate.

## 4K Enhancement Handoff

After each generated asset passes QA, add exactly one independent section to `08_4K_Upscale_Prompts.md`. Bind the accepted Codex asset and original source references. Permit only resolution, edge definition, realistic micro-texture, and source-supported fine-detail enhancement. Require preservation of original product geometry, component count, proportions, logos/markings, materials, colors, board topology, camera views, and state. Forbid redesign, re-layout, new parts, removed parts, reframing, material substitution, text invention, and state invention.

Do not claim a Codex board or third-party output is native 4K without observed file evidence. The 4K file is a handoff, not proof that external generation occurred.

## Completion Gate

Run `scripts/validate_asset_package.py <Complex_Product_Identity_Asset_Package>` before delivery.

Claim `complete` only when:

- the specification and root manifest exist and their hashes are frozen;
- Geometry Lock, all required boards, and the Final Product Identity Lock Board are approved;
- no board is awaiting generation, continuation, QA, or repair;
- no unresolved hard identity conflict remains;
- every approved generated image has actual dimensions and passing board-specific QA;
- approved final-board sources are approved A–E boards only;
- every approved generated image maps to exactly one valid 4K enhancement prompt;
- the validator exits zero.

Use `partial_approved` for a truthful board-scoped subset and `blocked_source_insufficient`, `blocked_identity_conflict`, `blocked_generation_runtime`, or `four_k_mapping_failed` for the corresponding hard stop. Validator success proves package-contract consistency, not production approval, product safety, engineering correctness, usage rights, external 4K success, or user approval.
