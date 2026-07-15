---
name: scene-canon-asset-pack
description: "Create a reusable six-image Scene Canon Asset Pack from one or more user-supplied scene reference images. Use only when the user explicitly invokes the Skill and needs a neutral, motion-bounded environment package with one frozen canon, six complete prompts disclosed before generation, dependency-staged non-decision image workers, an executable coverage graph, cross-view continuity QA, and one 4K regeneration prompt per approved machine asset. Trigger for scene assets, environment plates, location assets, spatial expansion, or scene continuity; do not use for storyboards, shot anchors, characters, products, look/lighting masters, retouching, source search, simple upscale, video prompts, or video generation."
---

# Scene Canon Asset Pack

## HIGH_CONTROL_RELEASE_GATE_V2

Before any production action, resolve this `SKILL.md` directory and execute the sibling OS-native launcher. On Windows run `& ..\\high-control-ai-tvc\\tools\\release-control.ps1 -Action check -Format json`; on macOS/Linux run `../high-control-ai-tvc/tools/release-control.sh check --format json`. Use the pinned runtime returned by the validated receipt; never bypass it with an unverified global Python. Proceed only when `ready_latest=true`. On failure, run the same launcher with `sync`, then start a fresh Codex task. Bind `release_commit` for the entire run.

中文名：场景本体资产包

Build one minimum-complete, internally consistent scene canon, then generate exactly six independent machine assets that support a declared camera-motion envelope. Preserve source evidence, freeze one constrained completion for unseen regions, and keep source look separate from scene identity.

## Authorization And Input Gate

Require explicit `$scene-canon-asset-pack` invocation and at least one usable user-supplied scene reference image. Explicit invocation authorizes the narrow `AGENTS.md` exception: one fresh non-decision image worker for each actual image-generation attempt. Do not spawn a worker after implicit routing or without the project authorization rule.

Accept one or more scene references, crops, material details, alternate lighting/state views, and optional camera-motion constraints. If no scene reference exists, return `blocked_missing_scene_reference`. If the user forbids inference, deliver a source-supported gap report and do not generate. Separate creative completion from engineering, survey, forensic, construction, or scientific truth claims.

The main agent owns evidence, canon, motion envelope, coverage graph, prompt text, dependency order, QA, repair, acceptance, and publication. A worker may receive only one frozen prompt, one target asset ID, one run nonce, and one ordered reference manifest; it makes exactly one built-in image call and terminates without text. It never chooses, edits, repairs, approves, rejects, or publishes anything.

## Exact Six-Asset Contract

Generate exactly these six full-frame machine assets, never one multi-panel image:

1. `CDM_001` — source-aligned Canonical Diagnostic Master.
2. `SRM_001` — elevated Spatial / Relational Master.
3. `COV_001` — left-adjacent continuity plate.
4. `COV_002` — right-adjacent continuity plate.
5. `COV_003` — motion-reveal plate; use low/elevated/path reveal according to the frozen envelope.
6. `SCL_001` — scale, landmark, and depth-relation plate.

Adapt camera poses and information roles to the scene type, but do not change the six asset IDs or reuse one asset for multiple roles. Integrate identity-defining intrinsic state into the relevant six assets; do not add a seventh machine asset. Compose `HRB_001` only after all six pass QA; it is a derived human-only review board and is not a machine reference.

Read `references/motion_coverage_contract.md`, `references/scene_type_rules.md`, and `references/canonical_completion_rules.md` before freezing coverage.

## Output Contract

Deliver the complete tree defined in `references/generation_and_packaging_contract.md`, including:

- `SCENE_CANON.md` and schema-valid `SCENE_CANON.json`;
- source evidence, conflict, appearance-decomposition, neutral-appearance, coverage, and exclusion records;
- `GENERATION_PROMPTS.md` containing the six complete prompt bodies;
- the six independently generated machine assets and derived `HRB_001`;
- prompt-publication, worker-result, and main-agent inspection receipts;
- actual pixel dimensions, consistency QA, failure/repair logs, and strict delivery report;
- `4K_ASSET_REGENERATION_PROMPTS.md` with exactly one finalized record per approved machine asset.

Record actual returned pixels. Never call a non-native result native 4K.

## Canonical Sources Of Truth

Read each resource before the phase it governs:

- `references/scene_canon.schema.json` — Scene Canon, motion envelope, and coverage graph.
- `references/appearance_decomposition.schema.json` — source appearance and neutralization.
- `references/asset_manifest.schema.json` and `references/asset_manifest_template.json` — six-asset, prompt, queue, and receipt ledger.
- `references/motion_coverage_contract.md` — default dependency DAG, graph semantics, motion support, parallax, reveal, and loop closure.
- `references/worker_orchestration_contract.md` — prompt-first publication, worker dispatch, resolver binding, inspection, timeout, and repair rules.
- `references/scene_type_rules.md`, `references/canonical_completion_rules.md`, and `references/neutral_appearance_rules.md` — adaptive evidence decisions.
- `references/qa_checklist.md`, `references/look_contamination_checklist.md`, `references/4k_regeneration_prompt_template.md`, and `references/4k_prompt_qa_checklist.md` — delivery gates.
- `references/examples_and_test_cases.md` — positive, negative, blocked, and boundary expectations.

## Workflow

### 1. Freeze Evidence, Appearance, And Canon

Inspect every input. Cluster by scene identity and detect crop, mirror, time, lighting, state, material, style-only, and conflict differences. Apply:

`user fact > source-corroborated > clear source-locked > geometry inference > scene/material prior > generative completion`

Classify facts as `source_locked` (Source-Locked), `source_corroborated` (Source-Corroborated), `canonical_completion`, `conflict`, or `out_of_scope_unknown`. Freeze the minimum-complete boundary, fixed content, prohibited additions, landmarks, topology, scale, orientation, intrinsic scene state, and neutral appearance. Preserve intrinsic emission and identity-defining physical states while removing illumination, optical, and grade contamination.

### 2. Freeze Motion Envelope And Coverage Graph

Declare supported and unsupported camera motion before prompt writing. Express azimuth, elevation, translation, path, reveal, and truth-status bounds. Never claim 360-degree, backside, entrance, overhead, or translated parallax coverage unless the graph and frozen completion support it.

Build exactly six mandatory graph nodes bound one-to-one to the six asset IDs. Record normalized camera pose, lens/FOV and framing class, visible landmarks, revealed and occluded regions, evidence/completion IDs, adjacent nodes, and overlap invariants. Build movement edges with direction, translation baseline, parallax expectation/evidence, reveal order, handedness, path membership, and shared invariants. Include at least one convergence loop. A crop, zoom, focal-only change, duplicate camera tuple, or repeated direction cannot satisfy another role.

### 3. Publish All Six Complete Prompts Before Generation

Create `00_manifest/GENERATION_PROMPTS.md` and the six `generation_prompt_records` from the frozen canon and graph. Each record contains the complete tool prompt, SHA-256, target asset/node, ordered references, dependency stage, and predecessor IDs. Use at most five provider references per worker.

Publish all six complete prompt bodies together in one assistant update before spawning any worker. Include asset IDs and SHA-256 values. Then write a runtime-bound prompt-publication receipt. A file path, summary, template, placeholder, hash-only list, or post-generation disclosure does not satisfy this gate. If all six prompts cannot be published, stop `blocked_prompt_publication` before any image call.

### 4. Generate Serially Through Non-Decision Workers

Use this serial dispatch order:

`CDM_001 → SRM_001 → COV_001 → COV_002 → COV_003 → SCL_001`

Keep the generation dependency DAG distinct from dispatch order: `CDM_001` has no generated predecessor; `SRM_001` depends on `CDM_001`; both `COV_001` and `COV_002` depend on `CDM_001 + SRM_001`; `COV_003` depends on those four approved assets; `SCL_001` directly binds `CDM_001 + SRM_001 + COV_003`, whose transitive closure already includes both convergence branches. `COV_001` and `COV_002` are independent convergence branches in the same dependency stage, but the one-worker limit still dispatches them serially. Every worker keeps the original source as reference 1, so the provider bundle remains within the five-reference limit.

Each later prompt may already be public, but its ordered references become dispatchable only after every predecessor is QA-approved. Spawn one fresh worker named `scene_canon_image_<asset>_<32-hex-nonce>` for the current asset, using `fork_turns="none"`. The worker task contains the exact frozen prompt inline, the same prompt hash, ordered reference paths, target asset ID, and the instruction to make one image call and terminate.

The main agent must not call image generation. Resolve each worker result with the vendored audited v3 `scripts/resolve_worker_image.py`; it binds parent/worker lineage, exact prompt transport, ordered reference bytes, call ID, image bytes, and returned dimensions without runtime-importing a sibling Skill. Inspect the actual image in the main agent, then write a separate inspection receipt. Advance the queue only after delivery-state validation confirms the current node is approved and all dependency hashes remain current.

Use a new worker and asset revision for a repair. Do not parallelize dependent nodes or spawn a replacement while the prior call state is unknown.

### 5. QA, Graph Closure, And Packaging

For every asset verify source fidelity, topology, scale, landmark order, material/base color, fixed content, high/low reveal when applicable, overlap invariants, parallax when translation is supported, path continuity, loop convergence, duplication, contamination, and neutral appearance. Repair the earliest affected canon/graph state and invalidate all dependent assets/prompts when a contradiction appears.

Compose `HRB_001`, the Human Review Overview Board, only from the six approved assets with `scripts/build_review_board.py`. Run intermediate checks explicitly with:

`python scripts/validate_scene_package.py <package-root> --mode state`

This may return `STATE_VALID_NOT_COMPLETE`; it is never delivery success. Final delivery must run:

`python scripts/validate_scene_package.py <package-root> --mode delivery`

Any planned, awaiting, failed, blocked, stale, duplicate, unmapped, graph-incomplete, receipt-unbound, or placeholder state must exit non-zero.

### 6. Bind Six 4K Regeneration Prompts

After all six assets and graph continuity are frozen, create exactly six finalized 4K records. Use the matching QA-approved neutral asset as primary and highest-priority reference, with CDM and original source only as bounded support. Permit resolution, edge, distant-structure, texture, and material-detail improvements; forbid redesign, reframing, pose/perspective/topology/scale/material/base-color/state changes, new landmarks, and look restoration.

## Runtime State Machine

Advance only:

`input_ready → evidence_locked → appearance_frozen → canon_frozen → motion_envelope_frozen → coverage_graph_frozen → six_prompts_published → generating_stage_1..6 → graph_qa_pending → six_assets_approved → four_k_mapped → packaged`

Use `repair_required` from any generation or graph-QA stage and return to the earliest affected freeze. Use `blocked_missing_scene_reference`, `blocked_exactness_evidence`, `blocked_prompt_publication`, `blocked_worker_runtime`, or `hard_blocked_generation_runtime` only for non-substitutable blockers.

## Completion Gate

Claim `packaged` only when strict delivery validation exits zero and all of these are true:

- six complete prompts were published before the first worker;
- six unique machine assets map one-to-one to graph nodes, prompt records, runtime-bound worker receipts, main-agent inspection receipts, actual files/dimensions, and finalized 4K prompts;
- worker thread IDs, image call IDs, asset files, camera tuples, and role assignments are unique;
- dependency order is complete and no user continuation was required;
- supported motion maps to verified graph edges, overlaps, reveals, parallax where required, paths, and loop convergence;
- every included unseen region remains labeled canonical completion rather than source truth;
- all six assets preserve the frozen canon and pass contamination/duplicate gates;
- `HRB_001` is derived only from approved independent assets;
- human or production approval remains separate from assistant QA.

Validator success proves the executable package contract, not taste, rights, engineering truth, external model success, or production approval.

## Minimal Invocation

`Use $scene-canon-asset-pack to turn these scene references into one neutral six-image motion-bounded Scene Canon package; publish all six complete prompts before generation and finish automatically through dependency-staged non-decision workers.`

## Optional AI-Video Project Canon Export

After `packaged`, export an approved scene asset only with `scripts/export_ai_video_canon.py` and the existing fixed-owner approval schema. The shared export dependency marker is `../ai-video-shot-script-director/requirements.txt`, whose Pillow pin must match the validated release runtime; this Skill's image QA helpers carry the same exact pin in local `requirements.txt`. Preserve `authority_mode: scene_canon`, `control_roles_authorized: [scene_canon]`, `authority_stage: terminal_scene_canon`, and `terminal_route_decision: not_applicable`. Export failure leaves this package unchanged.
