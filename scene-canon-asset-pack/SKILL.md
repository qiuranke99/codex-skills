---
name: scene-canon-asset-pack
description: "Create a reusable Scene Canon Asset Pack from one or more user-supplied scene reference images. Use when Codex must analyze scene evidence, separate intrinsic appearance and scene-defining state from lighting/camera/post effects, complete unseen space under explicit constraints, directly generate independent neutral environment plates with built-in image generation, verify cross-view consistency, and deliver one third-party 4K regeneration prompt per approved asset. Trigger for scene assets, environment plates, location assets, spatial expansion, scene continuity, indoor/exterior/terrain/ocean/sky/volumetric/cosmic/surreal environments; do not use for storyboards, shot anchors, characters, products, look or lighting masters, video prompts, video generation, ordinary retouching, source-image search, or simple upscaling."
---

# Scene Canon Asset Pack

## HIGH_CONTROL_RELEASE_GATE_V2

Before any action or production output, resolve this `SKILL.md` directory and run its sibling `../high-control-ai-tvc/tools/release_control.py check --format json`. Proceed only when `ready_latest=true`. On any failure, stop: run `sync`, then start a new Codex task. Bind the returned `release_commit` to this stage; never substitute a mutable Windows/Mac authoring checkout.

中文名：场景本体资产包

Build one minimum-complete, internally consistent scene canon from visible evidence, then generate a clean reusable asset package. Preserve observed facts, freeze one constrained completion for unseen regions, and prevent the source image's final look from becoming the scene identity.

## Input Gate

Require at least one usable user-supplied scene reference image. Accept single or multiple images, crops, detail views, alternate exposure or lighting states, and optional user constraints. Do not require a panorama, back view, plan, measurements, camera data, depth map, 3D model, neutral-light source, or complete photogrammetry.

If no scene reference exists, return `blocked_missing_scene_reference`; do not invent a production scene from this Skill. If the user forbids inference, deliver only source-supported coverage and a gap report. If the user requests engineering, survey, forensic, construction, or observational-science accuracy without corresponding evidence, separate verifiable facts from creative completion and reject any exactness claim.

Do not stop for missing optional inputs. Infer conservative defaults for purpose, coverage, target model, and target dimensions; use model-neutral 4K prompts when no third-party model is named.

## Output Contract

Deliver a package, never a single board or prompt-only plan. The package must include:

1. Scene Canon Manifest: `SCENE_CANON.md` and `SCENE_CANON.json`.
2. Source Evidence Report and conflict/coverage records.
3. Source Appearance Decomposition and Neutral Appearance Canon.
4. Canonical Diagnostic Master.
5. Spatial / Relational Master appropriate to the scene type.
6. Independent Coverage Plates, with each view generated separately.
7. Scale and Landmark Pack.
8. Fixed Content and Exclusion Map.
9. Conditional Intrinsic Scene State Set when required by scene identity.
10. Human Review Overview Board composed from approved independent assets.
11. Consistency QA and failure logs.
12. `4K_ASSET_REGENERATION_PROMPTS.md`, with exactly one asset-specific prompt for every approved machine image.

Record actual returned pixel dimensions. Never describe a non-native result as native 4K. Read `references/generation_and_packaging_contract.md` before generation or packaging.

## Canonical Sources Of Truth

Read these resources at the phase that needs them; do not redefine their fields elsewhere:

- `references/scene_canon.schema.json` — Scene Canon record and freeze state.
- `references/appearance_decomposition.schema.json` — source appearance and neutralization record.
- `references/asset_manifest.schema.json` and `references/asset_manifest_template.json` — generated asset ledger and one-to-one 4K mapping.
- `references/scene_type_rules.md` — scene classification and adaptive coverage.
- `references/canonical_completion_rules.md` — evidence priority, minimum-complete boundary, completion, and loop closure.
- `references/neutral_appearance_rules.md` — intrinsic appearance/state separation and neutral diagnostic treatment.
- `references/qa_checklist.md` and `references/look_contamination_checklist.md` — pre-delivery visual gates.
- `references/4k_regeneration_prompt_template.md` and `references/4k_prompt_qa_checklist.md` — final prompt records and mapping QA.
- `references/examples_and_test_cases.md` — examples, Test A-G, failure fixtures, and expected behavior.

## Five-Layer Workflow

### 1. Evidence And Scene Canonization

Inspect every input image. Cluster references by scene identity; never merge similar but distinct scenes. Detect crop, mirror/flip, time, lighting, state, material-detail, style-only, and conflicting references. Apply this evidence order:

`user-declared fact > Source-Corroborated > clear Source-Locked > perspective/geometry inference > material/scene prior > generative completion`

Classify each relevant fact as Source-Locked (`source_locked`), Source-Corroborated (`source_corroborated`), Canonical Completion (`canonical_completion`), Conflict (`conflict`), or Out-of-Scope Unknown (`out_of_scope_unknown`). Define the `minimum_complete_scene_boundary`; no area inside it may remain silently unresolved. Record fixed architecture/natural structures, fixed dressing, conditional scene elements, temporary/unwanted objects, prohibited additions, landmarks, orientation, topology, scale, entries/exits, horizon or vertical reference, and the initial coverage plan.

Use `references/scene_type_rules.md` and validate the evolving record against `scene_canon.schema.json`.

### 2. Appearance Decomposition And Neutral Canonicalization

Before any final asset generation, classify visible appearance into:

- intrinsic scene appearance;
- intrinsic scene state;
- external illumination;
- camera/optical effects;
- color grading/post-processing;
- unresolved appearance.

Record observed rendered colors separately from intrinsic or estimated base colors. Assign `high`, `medium`, or `low` appearance confidence per material/color inference. Preserve source-supported emissive structures, wave/cloud/flow states, fog/smoke distributions, snow/flood/lava/fire states, accretion disks, coronas, jets, rings, and other scene-defining physical states. Remove look contamination without turning the scene into a gray model or shadowless white-box render.

Freeze `neutral_appearance_canon`, then generate one Canonical Diagnostic Master. Use `references/neutral_appearance_rules.md` and validate the record against `appearance_decomposition.schema.json`.

### 3. Canonical Completion And Independent Coverage

Use the original references for identity/geometry, Scene Canon for topology/completion, Canonical Diagnostic Master for neutral appearance, and approved adjacent views for local continuity. Never generate all angles independently from a text summary and never discard source anchoring in later generations.

For consequential hidden regions, compare multiple low-cost candidates against evidence, perspective, scale, topology, material language, minimum necessary complexity, high/low-angle survivability, neutral appearance, and loop closure. Select exactly one completion; after approval, write it into Scene Canon and forbid later random reinterpretation.

Expand through adjacent anchors, then bidirectionally where possible. Use direct built-in image generation for every required asset. Generate every machine plate as an independent full-frame image. Do not generate a multi-panel image and crop it into assets. Default ordinary scene assets to horizontal 16:9; use 2:1 only for a true panorama and use an information-appropriate ratio for topology/system diagrams.

### 4. Consistency QA, Repair, And Packaging

Before each image call, record `terminal_generation_call: pending`. The image call must be the final event of that turn. Treat the returned image as `stage_complete` and set `awaiting_post_generation_continuation`; it cannot complete the package or task. In a later turn, confirm `terminal_generation_call: executed`, set `pending_post_generation_inspection`, inspect the returned image, record actual dimensions, update the manifest, and run source fidelity, topology, scale, landmark, material, fixed-content, high/low reveal, loop-closure, duplicate-view, content contamination, and Look Contamination checks.

On failure, identify the root cause, update Scene Canon or Neutral Appearance Canon if required, regenerate only the failed asset, rerun affected QA, and update all dependent manifest and prompt records. Do not approve an asset while a hard gate is unresolved.

Compose the Human Review Overview Board only from independently generated, QA-approved assets; never treat the board as a machine reference source. Run `scripts/build_review_board.py` when local files are available. Run `scripts/validate_scene_package.py <scene-canon-output>` before delivery.

### 5. Bound 4K Regeneration Prompt Packaging

Start only after Scene Canon, Neutral Appearance Canon, Canonical Completion, asset filenames, actual dimensions, and visual QA are frozen. Create one independent prompt record for every approved machine image, including diagnostic, spatial/relational, coverage, scale/landmark, and conditional state assets.

Use the QA-approved neutral Codex asset as the primary and highest-priority visual reference. Use the Canonical Diagnostic Master as appearance support; use the original heavy-grade reference only as optional structure/identity support. Permit only effective-resolution, edge-definition, distant-structure, texture, and material micro-detail enhancement. Forbid redesign, reframing, camera/perspective/topology/scale/material/base-color/state changes, new landmarks, and look restoration.

Generate `4K_ASSET_REGENERATION_PROMPTS.md` from `references/4k_regeneration_prompt_template.md`, then run the mapping checklist and package validator. If any approved asset lacks exactly one valid prompt, set package status to `four_k_mapping_failed` and do not claim completion.

## Runtime State Machine

Advance only in order:

`input_ready → evidence_locked → appearance_frozen → completion_selected → canon_frozen → generation_spec_frozen → generating → qa_pending → qa_approved → four_k_mapped → packaged`

Use `repair_required` as a branch from `qa_pending`; return to the earliest affected freeze state before regeneration. Use `awaiting_post_generation_continuation` immediately after each terminal image call and `pending_post_generation_inspection` in the later visual-QA turn. Use `blocked_missing_scene_reference`, `blocked_exactness_evidence`, or `hard_blocked_generation_runtime` only for non-substitutable blockers.

## Completion Gate

Claim `packaged` only when:

- all required files exist and the three JSON records validate;
- every machine image was generated independently and has verified actual dimensions;
- all Source-Locked and Source-Corroborated elements survive;
- one frozen Canonical Completion governs every view;
- topology, scale, landmarks, materials, fixed content, high/low reveals, and loop closure pass;
- no machine image contains layout, person, product, temporary-object, or look contamination;
- intrinsic emissive and scene-defining states remain intact;
- no two plates are redundant crops or near-duplicate views;
- every approved asset has exactly one asset-specific 4K prompt and every prompt points back to one approved asset;
- the 4K prompt uses the neutral Codex asset as primary reference and never claims that built-in output is native 4K without evidence;
- `scripts/validate_scene_package.py` exits zero.

Keep human or production approval separate from assistant QA. Validator success proves contract and package integrity, not taste, legal rights, or engineering-grade reconstruction.

## Minimal Invocation

`Use $scene-canon-asset-pack to turn these scene references into a neutral, consistent scene asset package and include one bound 4K regeneration prompt per approved image.`

## Optional AI-Video Project Canon Export

This downstream integration does not change scene canonization, independent
plate generation, neutral appearance, package QA, or one-to-one 4K prompt
mapping. Export one approved machine asset only after the package is
`packaged`, its assistant QA passed, its primary file hash and finalized
`four_k_regeneration_prompt` bytes are verified, and production approval is
explicitly `user_granted` or `external_pipeline_granted`.

The scene owner writes approval evidence conforming to
`../ai-video-shot-script-director/references/ai_video_owner_asset_approval.schema.json`,
binding this fixed owner, an asset key, the selected primary plate hash, its
exact finalized 4K regeneration prompt hash, affected canonical Shot UIDs, QA
pass, and approval decision. Invoke only
`scripts/export_ai_video_canon.py` with project-relative locked files; the
wrapper exposes no owner argument and verifies that it lives in this package.
It exports only `authority_mode: scene_canon` with
`control_roles_authorized: [scene_canon]`.
Pillow is required to verify and fully load the selected primary PNG/JPEG/WebP
scene plate and lock decoder-observed dimensions of at least 64×64. Missing
Pillow, corrupt pixels, or format/extension mismatch fails closed before Canon
mutation.

Success creates the owner-produced `ai-video-artifact-v1` sidecar, independent
binary primary/JSON-record four locks, immutable base snapshot, entry delta,
receipt, and validated pre/post Canon transition. The Prompt Director must use
the real `scene-canon-asset-pack` owner for feedback and may not synthesize an
authority projection. Export failure leaves the Scene Canon package unchanged.

Approval and export records must also bind
`authority_stage: terminal_scene_canon` and
`terminal_route_decision: not_applicable`. Install the pinned decoder with
`python3 -m pip install -r ../ai-video-shot-script-director/requirements.txt`.
