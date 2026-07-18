---
name: complex-product-identity-reconstruction-asset-locking
description: "Reconstruct and lock a source-evidenced Visual Product Identity Model for complex multi-part, mechanical, multi-material, or stateful products, then build independent non-redundant camera assets, risk-specific diagnostic boards, a clear primary upload bundle, and per-asset 4K handoff. Use for wheelchairs, medical or industrial equipment, robots, cameras, fitness machines, complex furniture, strollers, bicycles, motorcycles, electronics, and other products whose topology, interfaces, moving parts, occlusion, or state changes make a simple multi-view collage unsafe. Do not use for simple low-risk products, packaging-copy-first work, material-response-first glass/liquid products, ads or lifestyle scenes, source search, ordinary retouching, prompt-only delivery, or products without a usable visual reference."
---

# Complex Product Identity Reconstruction & Asset Locking

## Standalone Runtime Contract

Run this Skill directly from its own package. Its evidence contracts, v2 initializer, validator, deterministic tests, and templates are package-local and require no release manager or sibling Skill. Built-in image generation is optional: direct source plates and verified source renders are preferred when they carry stronger identity truth. Package scripts use only the Python standard library.

The accepted `partial_approved` or `complete` package is a portable downstream input. No downstream integrator is required. A supplied evidence ledger still has to pass this Skill's source and camera gates.

Chinese name: 复杂产品身份重建与资产锁定 Skill

`runtime_contract_version: complex_product_identity_asset_package_v2`

Build a reusable product identity system for downstream AI video, keyframes, TVC, and commercial visual production. Do not confuse a crowded multi-view collage with verified camera coverage.

The main agent owns identity resolution, camera planning, evidence classification, visual QA, repair, package validation, and final delivery. This Skill does not authorize subagents, external paid generation, product redesign, engineering certification, or unsupported completion.

## Input Gate

Require at least one usable image of one target product variant. Accept photographs, official images, detail screenshots, manual illustrations, local crops, and existing verified 3D/CAD source or renders as optional evidence. Existing 3D/CAD may support a deterministic render lane when a compatible renderer is actually available; this Skill does not create, repair, or certify engineering geometry.

Resolve one variant before asset creation. If references mix revisions, wheel systems, handrims, frame colors, controls, accessories, or folding topology and cannot be separated, return `blocked_identity_conflict`.

A single view can produce one truthful source camera and a coverage-gap report. It cannot authorize unseen rear, underside, internal, interface, marking, or motion truth.

Default to video-continuity assets, neutral product treatment, and the camera coverage plan below. Do not ask the user to restate folder structure or aspect ratio.

## Output Contract

Initialize `Complex_Product_Identity_Asset_Package/` with:

1. `01_Product_Identity_Specification.md`
2. `02_Geometry_Camera_Coverage/camera_assets/`
3. `02_Geometry_Camera_Coverage/camera_coverage_report.md`
4. `03_Material_Surface_Lock/`
5. `04_Component_Detail_Lock/`
6. `05_State_Transition_Lock/`
7. `06_Marking_Identity_Lock/`
8. `07_Primary_Upload_Bundle/`
9. `08_4K_Upscale_Prompts.md`
10. `asset_package_manifest.json`

Run `scripts/init_asset_package.py --output <exact-package-path> --asset-id <stable-id>` before analysis. Read `references/package-contract.md` before editing the manifest or claiming completion.

Version 1 packages used one monolithic Geometry board. They do not prove independent camera coverage and must be re-analyzed into v2; the v2 validator fails them closed.

## Required References

- Read `references/product-identity-contract.md` before identity analysis, Critical Node Ledger, View Evidence Matrix, or camera eligibility decisions.
- Read `references/generation-runtime-and-qa.md` before preserving or generating a camera asset, generating a diagnostic board, inspecting pixels, or repairing a failure.
- Read `references/package-contract.md` before initialization, manifest updates, upload selection, 4K mapping, validation, or delivery.
- Read `references/test-cases.md` when revising trigger behavior or regression gates.

## Stage 1 — Evidence-Bounded Product Identity

Inspect every input at original available resolution before image generation.

1. Build a stable source ledger with paths/references, hashes when local, source role, camera/view, state, variant, crop, resolution, and conflicts.
2. Separate product-intrinsic facts from perspective, lighting, reflection, environment color, grade, blur, and compression.
3. Freeze one Product Identity Specification covering silhouette, proportions, frame/support system, part count, connection topology, materials, markings, interfaces, asymmetry, supported states, and forbidden completion zones.
4. Build a Product Part Tree with parent/child relationships, count, side, attachment, interface, material, and identity risk.
5. Build a Critical Node Ledger. For a wheelchair, explicitly cover rear-wheel/axle/handrim, caster/fork, frame/cross-brace/support links, seat/back/arm/footrest, brake/control side, accessories, cables/modules, and state-dependent topology when present. Use equivalent nodes for other product classes.
6. Build an evidence-bounded State Graph. Category familiarity is not evidence of a mechanism.
7. Label atomic claims exactly `Observed`, `Cross Validated`, `Inferred`, `Unknown`, or `Conflicting`. Never promote the last three into source truth.
8. Build a View Evidence Matrix mapping every source to azimuth/elevation, visible critical nodes, occluded zones, whole-product completeness, and variant confidence.
9. Freeze the source bundle, specification, and camera-plan SHA-256 values. New identity conflicts invalidate affected downstream assets.

Do not create assets while the specification lacks the five evidence classes, Part Tree, Critical Node Ledger, State Graph, View Evidence Matrix, Camera Coverage Plan, exact coverage-gap requests, or unresolved-conflict disclosure.

## Stage 2 — Independent Camera Coverage

### Default Camera Plan

Plan these six independent whole-product targets unless the product or downstream shot risk justifies an explicit change:

1. `CAM_FRONT_3Q_LEFT`
2. `CAM_FRONT_3Q_RIGHT`
3. `CAM_LEFT_PROFILE`
4. `CAM_RIGHT_PROFILE`
5. `CAM_REAR_3Q`
6. `CAM_HIGH_FRONT_3Q`

Each target has one unique azimuth/elevation/shot-size bin, expected critical nodes, unique coverage value, source IDs, evidence mode, and exact blocker. Add front, rear, low, underside, folded, or control-side cameras only when they close a named risk.

Never place multiple camera targets into one generative board. Each accepted camera is a separate full-resolution, complete, uncropped product asset. A contact sheet is optional, deterministic, derived only from accepted camera assets, and has no identity authority.

### Per-Camera Evidence Priority

Use the strongest feasible lane for each target:

1. `source_copy` — exact source bytes with a directly observed complete view; hard identity authority.
2. `verified_source_render` — deterministic render from a verified existing 3D/CAD source with frozen model/render provenance; hard identity authority.
3. `source_aligned_generation` — same-camera cleanup or neutralization bound to the original sources; auxiliary authority only.
4. `bounded_reconstruction` — a candidate novel view only when visible critical topology is cross-validated; auxiliary authority only and never proof of hidden geometry.
5. `blocked` — the view would invent a critical node, hidden topology, variant fact, or unsupported camera reveal.

Do not generate a new view when copying a usable source plate is more faithful. Do not pretend a generative reconstruction is an observation. A missing rear or underside view blocks only the affected camera, not all observed cameras.

If an existing verified 3D/CAD source is available but no compatible renderer can run, record a source-render handoff with exact camera roles and keep those targets blocked. Do not silently fall back to hallucinated views.

### Coverage Tiers

- `none`: no accepted camera.
- `source_aligned`: at least one accepted camera, but no video-ready hard-authority coverage.
- `multi_camera`: at least four hard-authority cameras, at least four unique pose bins, front/rear/side sector coverage, and zero duplicate hashes or pose bins.
- `full`: every frozen target camera is accepted with hard authority.

`partial_approved` may deliver truthful source-aligned cameras plus exact missing-capture requests. `complete` requires `multi_camera` or `full`; multiple renderings of the same three-quarter pose do not count.

## Stage 3 — Risk-Specific Diagnostic Assets

Geometry camera coverage is primary. Generate the following as separate diagnostic assets only when relevant and source-approved:

- **Material & Surface Lock** — intrinsic material regions and response, not cinematic lighting contamination.
- **Component Detail Lock** — evidence-supported joints, axles, brakes, controls, latches, interfaces, and attachment nodes.
- **State & Motion Lock** — only observed/cross-validated endpoints and mechanics; no invented intermediate travel.
- **Marking Identity Lock** — only legible, resolved logos/copy/patterns at the exactness level the sources support.

Every diagnostic asset has one identity job. Prefer a complete source-aligned product view plus only the minimum necessary details. It cannot substitute for a missing camera and is not selected for upload merely because space exists.

## Source Gate And Generation State

Camera source gates are independent. Diagnostic source gates remain board-scoped. Generate only when the relevant gate is approved.

Before any built-in image call, persist the target, attempt, source/specification/camera-plan hashes, prompt hash, and `generation_pending`. After the tool returns, bind the exact file, observed SHA-256 and dimensions, then inspect it in the same task when the host continues. Never ask the user to type “continue” merely to run QA. If the host ends at the image call, keep `awaiting_post_generation_continuation` and resume automatically at the next available continuation without requesting a new creative decision.

Keep complete built-in generation prompts private and store only their SHA-256. The explicit external 4K prompts remain deliverables.

## Comparison-Based Visual QA

Inspect the exact pixels at original resolution. For each camera require:

- target product present and no infographic/poster semantic substitution;
- whole product complete, uncropped, unoccluded, and free of people/props/text;
- declared camera pose and unique coverage contribution;
- source comparison of silhouette, proportions, part count, and every visible Critical Node;
- wheel/spoke/axle/handrim, caster/fork, frame/joint/support, seat/control/accessory, and asymmetry fingerprints when applicable;
- cross-camera agreement for all overlapping nodes and immutable features;
- no exact duplicate file or duplicate pose bin.

Diagnostic QA also checks geometry, material, identity, subject presence, and text pollution. Reject attractive-but-wrong redesign, identity averaging, added/missing/fused parts, spoke-count drift, changed joints, mirrored controls, unsupported state, crop, overlap, or board-cell contamination.

The validator independently checks actual image dimensions and SHA-256 against the manifest. Declared dimensions alone are not evidence.

## Causal Repair Policy

Classify failures before retrying:

- `reference_transport_or_subject_mismatch` — target absent, geometric-shape poster, butterfly infographic, wrong product, or wrong variant. Stop generation, set `blocked_generation_semantic_mismatch`, and audit prompt/reference binding. Do not inflate the prompt and retry blindly.
- `topology_overload` — split the job to one independent camera or one critical-node diagnostic; do not add more panels.
- `view_evidence_gap` — request the exact missing capture or verified source render; do not invent the occluded zone.
- `camera_redundancy` — change the pose bin and coverage objective, not cosmetic phrasing.
- `local_identity_drift` — repair only the failed camera/diagnostic asset from frozen original sources and named Critical Nodes.

Allow at most two attempts per camera and two repairs per diagnostic board. Record the causal variable changed. After repeated quality failure, set `blocked_generation_quality` and preserve the accepted remainder as partial.

## Primary Upload Bundle

Select one to five approved assets and record why each is needed. Prefer non-redundant hard-authority cameras; add at most the diagnostic asset that closes a real downstream identity risk. Never make the user infer the upload set from a directory of boards.

A complete package requires at least two selected independent camera assets. The bundle references accepted package assets; it does not create another generative “final board” that can redesign the product.

## 4K Enhancement Handoff

After each accepted camera or diagnostic asset passes QA, add exactly one section to `08_4K_Upscale_Prompts.md`. Bind the accepted asset and original sources. Permit only resolution, edge definition, realistic micro-texture, and source-supported fine detail. Preserve geometry, part count, proportions, camera pose, Critical Nodes, markings, materials, and colors. Forbid redesign, new/removed parts, reframing, pose change, material substitution, text invention, and state invention.

Do not claim native 4K or external 4K success without observed returned-file evidence.

## Completion Gate

Run `scripts/validate_asset_package.py <Complex_Product_Identity_Asset_Package>` before delivery.

Claim `complete` only when:

- specification, hashes, camera plan, coverage report, and manifest are frozen;
- Geometry reaches `multi_camera` or `full` using hard-authority assets;
- all required diagnostic boards are approved;
- no asset awaits generation, continuation, QA, or repair;
- no hard identity conflict remains;
- every accepted image has observed byte hash, observed dimensions, and passing comparison QA;
- the Primary Upload Bundle is approved and contains at least two independent cameras;
- every accepted asset has exactly one valid 4K mapping;
- the validator exits zero.

Use `partial_approved` for truthful lower coverage. Use the exact blocked status for source, identity, runtime, semantic-mismatch, or mapping failures. Validator success proves package consistency, not engineering/safety correctness, rights clearance, product approval, external 4K success, or user approval. Keep `production_approval_status` separate from technical QA.
