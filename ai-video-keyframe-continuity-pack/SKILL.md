---
name: ai-video-keyframe-continuity-pack
description: "Use after an approved professional shot contract, one-shot-one-file storyboard, locked character/product/scene assets, global look, and—when timing matters—a V1 timing animatic exist, to create independently generated, generation-ready per-shot keyframe anchors and continuity ledgers for multimodal reference-to-video. Every scripted shot receives at least one approved anchor or a strictly validated storyboard promotion; complex action, liquid, material, and cross-generation-unit states receive additional anchors. These are Omni reference assets, never start/end-frame controls. Do not use for story ideation, storyboards, look design, video prompts, text-to-video, first/last-frame generation, editing, music, or output QC."
---

# AI Video Keyframe Continuity Pack

## HIGH_CONTROL_RELEASE_GATE_V2

Before any action or production output, resolve this `SKILL.md` directory and run its sibling `../high-control-ai-tvc/tools/release_control.py check --format json`. Proceed only when `ready_latest=true`. On any failure, stop: run `sync`, then start a new Codex task. Bind the returned `release_commit` to this stage; never substitute a mutable Windows/Mac authoring checkout.

中文名：AI 视频关键帧连续性包

Contract version: `ai-video-keyframe-continuity-pack.v1`
Shared artifact contract: `ai-video-artifact-v1`

Create the minimum complete set of high-fidelity visual anchors and state ledgers needed to keep characters, products, materials, composition, action state, and generation-unit boundaries continuous in an Omni / all-reference video workflow.

The word **keyframe** here means a normal multimodal visual reference associated with a shot and time/state intent. It never means an API start frame, end frame, first-frame/last-frame mode, or an instruction to interpolate between two endpoint images.

It also never authorizes standalone/classic single-image-to-video. Freeze
`standalone_single_image_to_video` in the manifest denylist. This restriction
does not forbid ordinary storyboard, keyframe, character, product, scene, or
Look images from being used as normal references inside Omni R2V; those image
references remain the purpose of this Skill.
Generation-route boundary: `standalone_single_image_to_video: forbidden`;
`ordinary_image_references_in_omni_r2v: allowed`.

Run this Skill in two explicit artifact modes:

1. `core_keyframes` — K1 per-shot anchors and state ledgers, created before Prompt Director preflight and therefore containing no assumed Generation Unit Map.
2. `boundary_supplement` — K2 cross-unit handoff records and only the additional boundary anchors proved necessary by the approved preflight plan. K2 never mutates the approved K1 hash.

## 1. Scope And Trigger

Use this Skill only when these upstream facts are available:

- an approved `PROFESSIONAL_SHOT_CONTRACT` with stable `shot_uid` values;
- one independently stored storyboard frame per scripted shot;
- approved character, product, packaging, material, and scene assets required by those shots;
- an approved Global Look contract and look reference set;
- V1 timing-animatic timecodes when the project is multi-shot or timing/motion is material.

For one genuinely static, single-shot generation, accept an explicit `timing_animatic_exemption: single_static_shot`. Do not invent that exemption for a multi-shot sequence.

Do not use this Skill to:

- decide the story, shot count, shot order, shot duration, or advertising function;
- redesign a character, product, label, material, scene, storyboard composition, or Global Look;
- compile model/provider prompts or plan reference budgets;
- generate video through text-to-video or first/last-frame controls;
- create music, edit footage, grade footage, or run an independent output-QC workflow.

## 2. Read The Contracts

Read these files before producing a package:

- `references/artifact_contract.md`
- `references/keyframe_manifest.schema.json`
- `references/keyframe_manifest_template.json`
- `references/boundary_supplement.schema.json`
- `references/boundary_supplement.template.json`
- `references/continuity_projection.schema.json`
- `references/continuity_and_promotion_rules.md`
- `references/qa_checklist.md`
- `test_cases.md`

Do not redefine their field names ad hoc.

## 3. Input Gate And Authority

Build an input inventory from `PROJECT_CANON_MANIFEST`. Keep `package_root` and `project_root` distinct: local keyframe files resolve under the package root; every Canon/cross-owner locator resolves under the explicit whole-project root. If a new project is being recovered from already approved artifacts, first register those exact artifacts through the shared manifest contract; do not create a private inventory. Accept only artifacts whose envelope:

- has `contract_version: ai-video-artifact-v1`;
- has `approval_status: user_approved` unless the user explicitly permits an `assistant_validated` working branch;
- has a valid canonical envelope hash;
- is not stale and has no unresolved stale dependency;
- includes the current shot in `affected_shot_uids` when shot-scoped.

Use this authority order:

1. professional Shot Contract — shot identity, intent, target time, action path, continuity in/out;
2. approved identity/product/packaging/material/scene assets — intrinsic appearance and geometry;
3. Global Look — lighting, color, contrast, texture, and allowed shot state;
4. storyboard — framing, camera position, subject placement, and representative moment;
5. V1 Timing Animatic — time anchors, rough blocking, motion direction, and boundary timing;
6. this Skill — generation-ready realization and state ledger, without altering any higher authority.

If two approved sources conflict, stop that shot with `blocked_upstream_conflict` and issue a precise upstream change request. Never average conflicting identities, geometries, label states, screen directions, or look versions.

Ordinary directing details are not blockers. For poetic or sensorial advertising, infer restrained visible posture, breath, gaze, hand articulation, plausible liquid behavior, and other low-risk execution details; record them under `inferred_execution_decisions`. Do not invent product claims, exact label copy, hidden mechanisms, or scientific facts.

## 4. Shot Coverage Invariant

Let `N` be the approved Shot Contract count. The package must satisfy:

```text
approved_script_shot_count
= keyframe_shot_record_count
= distinct_covered_shot_uid_count
= N
```

Every shot record must contain at least one approved generation-ready anchor by exactly one route:

- `independent_keyframe`: generate one or more independent full-frame keyframes; or
- `validated_storyboard_promotion`: promote the shot's own final storyboard frame only after it passes every promotion gate in `continuity_and_promotion_rules.md`.

Do not satisfy coverage with a contact-sheet crop, a multi-panel board, a prompt-only placeholder, an unapproved image, or a frame owned by another shot.

## 5. Plan The Anchor Set

Start with one primary anchor per shot. Add another state anchor only when a control ambiguity would otherwise remain, including:

- an action with materially different preparation, contact, release, or recovery states;
- a face/pose transition that affects identity or emotion continuity;
- product pickup, opening, dispensing, assembly, deformation, reveal, or orientation change;
- transparent liquid, oil, cream, gel, spray, foam, droplets, wetting, refraction, or fill-level change;
- a camera/blocking path whose middle state cannot be recovered from one still plus V1 timing;
- a handoff into or out of another generation unit.

Use the fewest anchors that close the uncertainty. Anchor count is driven by state complexity, not by duration, visual attractiveness, or a fixed frames-per-shot rule.

Each anchor must declare:

- `shot_uid`, `keyframe_id`, `frame_role`, and `time_anchor`;
- which storyboard, source assets, Global Look, and timing anchor it depends on;
- exact subjects, product state, material state, camera/framing state, and continuity purpose;
- whether it was independently generated or promoted from a storyboard;
- its immutable binary `file_sha256` after generation;
- its `ai-video-artifact-v1` envelope.

The per-shot record freezes the exact Global Directing block, Global Look Core, assigned Look State, resolved first-class Look Reference artifact IDs, then the legal Shot Look Delta. Internal State `reference_id` aliases never enter model inputs. Every independently generated keyframe prompt sidecar must contain those exact blocks in that order. A generic “cinematic Omni anchor” prompt is not generation-ready evidence even when its bytes are hashed.

Forbidden `frame_role` values include `first_frame`, `last_frame`, `start_frame`, `end_frame`, and any equivalent endpoint-control label.

## 6. Build State Ledgers Before Generation

For every shot, create the following ledgers before writing a keyframe prompt.

### Character State Ledger

For every visible character record:

- authoritative identity asset and version;
- wardrobe, hair, makeup, accessories, and held props;
- body orientation, gaze, expression, hand state, and pose;
- screen direction and frame position;
- continuity-in and continuity-out state.

### Product State Ledger

For every visible product record:

- authoritative geometry/material/packaging assets and versions;
- label-facing direction and verified-copy boundary;
- orientation, placement, hand contact, cap/pump/lid state, and visible contents;
- continuity-in and continuity-out state.

### Material State Trajectory

When a material changes over time, record only source-supported or physically conservative states:

- fill level and content boundary;
- viscosity class and flow regime;
- droplet count/size/location, stream continuity, meniscus, wetting footprint, foam/bubble state;
- refraction/reflection boundaries, transparent-layer thickness, highlight direction, and surface finish;
- start, intermediate, and end state IDs tied to V1 time anchors.

Do not invent a hidden dip tube, valve, hinge, internal chamber, fluid property, or packaging construction.

### Dynamic State Ladder

Represent the minimum ordered state sequence needed by the shot:

```text
preparation → action onset → contact/change → settled/exit state
```

Omit unnecessary rungs, but never skip a state whose absence creates a discontinuity or impossible material motion. Each rung binds a `state_id`, time anchor, subject pose, object/material state, camera/blocking state, and transition intent.

## 7. Generate Independent Full-Frame Anchors

For each planned anchor:

1. Build one complete image-generation prompt from approved authorities and the prewritten ledgers.
2. State that the output is one clean, full-frame cinematic image—not a board, grid, split screen, collage, diagram, or annotation-bearing layout. Source-authorized intrinsic packaging/product/in-world text may remain only when its exact approved Canon asset is bound; never invent or reconstruct unsupported copy.
3. Bind identity/product/scene sources by stable aliases, never by hidden local paths.
4. Apply the exact approved Global Look core plus the shot's legal Look State/Delta.
5. Preserve the storyboard's camera, framing, placement, and screen direction.
6. Preserve the timing anchor's action state without implying start/end-frame interpolation.
7. Persist and hash the exact prompt sidecar before generation.
8. Set `terminal_generation_call: pending`, then make the image-generation call the final action of that turn.

On a later continuation, inspect the actual image, record dimensions and `file_sha256`, run the QA checklist, and set `terminal_generation_call: executed`. A returned image is stage-complete, not package-complete.

Never generate a multi-panel keyframe sheet and crop it. Never upscale, repaint, or relabel an uninspected output as approved.

## 8. Validate Storyboard Promotion

Promotion is an optimization, not a shortcut. A storyboard frame may become the primary keyframe only when all of the following pass:

- it is the approved independent final frame for exactly that `shot_uid`;
- identity, wardrobe, product geometry, label boundary, material state, scene, and Global Look meet generation-ready fidelity;
- the source frame contains no storyboard annotation, grid, UI, or watermark; any intrinsic packaging/product/in-world text is locked to exact downstream-eligible Canon source artifacts that are also required Keyframe authorities;
- camera, framing, pose, screen direction, and target action state match the Shot Contract and V1 timing anchor;
- actual file dimensions and `file_sha256` are recorded;
- later visual inspection has passed;
- `promotion_evidence` records every promotion criterion and result.

If any criterion fails, create an independent keyframe. Renaming or copying the storyboard file is not promotion evidence.

## 9. K2 Boundary Supplement After Prompt Preflight

Do not write Generation Unit IDs into K1. After Prompt Director `preflight` produces an approved Generation Unit Plan, run `boundary_supplement` mode. The supplement depends on the immutable K1 manifest and the preflight artifact. This creates an acyclic artifact sequence:

```text
V1 Timing Animatic
→ K1 Core Keyframes
→ Prompt P1 Generation Unit Preflight
→ K2 Boundary Supplement
→ V2 Control Previs
→ Prompt P2 Final Compile
```

For one generation unit, emit `exemption: single_generation_unit` and no boundary records. For multiple units, emit exactly one handoff record per adjacent unit boundary. Reuse existing K1 anchors when they already close the boundary; generate supplemental `boundary_handoff` anchors only when a legal between-shot boundary leaves an uncontrolled state.

K2 is its own `ai-video-artifact-v1` artifact. Never revise the K1 manifest in place merely to add Generation Unit IDs.

### Close Cross-Generation-Unit Boundaries

For every boundary between generation units, record:

- `from_generation_unit_id`, `to_generation_unit_id`;
- last affected shot/anchor on the upstream side;
- first affected shot/anchor on the downstream side;
- character identity/wardrobe/pose/gaze state;
- product orientation/label/material/mechanism state;
- screen direction, frame position, scene state, and Global Look state;
- the exact values that must remain locked across the handoff.

Generation-unit boundaries are legal only between stable Shot UIDs. If provider capacity would split inside one scripted shot, do not invent a hidden sub-shot here. Route a scoped change request to `ai-video-shot-script-director`, split the source shot into explicit stable Shot UIDs with preserved total timing and intent, then invalidate and regenerate only the affected Storyboard/V1/K1/P1 chain. K2 accepts only `boundary_type: between_shots`.

Boundary records are continuity evidence, not instructions to use first/last-frame mode.

## 10. Change And Invalidation Rules

This Skill owns only keyframe images and its ledgers.

- A changed Shot Contract invalidates affected shot records and downstream prompt bindings.
- A changed storyboard invalidates the corresponding keyframes, timing-derived ledgers, dependent boundary records, and downstream prompts.
- A changed identity/product/material/scene asset invalidates only dependent keyframes and downstream prompts.
- A changed Global Look Core invalidates every look-applied keyframe; a legal shot Look Delta invalidates only affected shots.
- A changed V1 timing anchor invalidates affected dynamic ladders, keyframes tied to those states, boundary records, V2 control previs, and prompts.
- A changed keyframe invalidates dependent V2 appearance bindings and prompts, never an upstream artifact.
- A changed Generation Unit Plan invalidates K2, every dependent V2 unit, bindings, prompts, and payloads; K1 remains valid unless its per-shot state facts changed.

Regenerate only stale anchors. Preserve byte-identical unaffected files and hashes.

## 11. Required Output Package

Write a package under:

`outputs/ai-video-keyframes/<project_id>/<package_id>/`

Required artifacts:

```text
00_manifest/KEYFRAME_CONTINUITY_MANIFEST.json
00_manifest/KEYFRAME_CONTINUITY_MANIFEST.md
00_manifest/MANIFEST_UPDATE_RECEIPT.json
00_manifest/owned_artifacts/<binary-artifact-id>.json
01_keyframes/<shot_uid>/<keyframe_id>.<native_ext>
01_keyframes/<shot_uid>/<keyframe_id>_generation_prompt.md
02_ledgers/CHARACTER_STATE_LEDGER.json
02_ledgers/PRODUCT_STATE_LEDGER.json
02_ledgers/MATERIAL_STATE_TRAJECTORY.json
02_ledgers/DYNAMIC_STATE_LADDER.json
04_reports/PROMOTION_REPORT.md
04_reports/QA_REPORT.md
04_reports/INVALIDATION_REPORT.md
```

After preflight, add only when applicable:

```text
03_boundaries/BOUNDARY_SUPPLEMENT.json
03_boundaries/<shot_uid>/<boundary_keyframe_id>.<native_ext>
03_boundaries/<shot_uid>/<boundary_keyframe_id>_generation_prompt.md
```

The JSON manifest is the machine truth. The Markdown manifest is a human-readable rendering and cannot override it.

Submit only K1/K2 artifacts owned by this Skill as an atomic Project Canon delta. The receipt records the validated base manifest hash and exact registered artifact IDs; never store a second canonical manifest in the package.

Run:

```bash
python3 scripts/validate_keyframe_package.py <package_root> \
  --project-root <project_root> \
  --project-canon-manifest <project_root>/00_project_canon/PROJECT_CANON_MANIFEST.json
```

## 12. Completion Gate

Claim K1 `package_status: packaged` only when:

- every scripted `shot_uid` appears exactly once in the manifest;
- every shot has at least one approved anchor or a fully validated promotion;
- all binary keyframe files, prompt sidecars, versions, and hashes resolve;
- every binary keyframe has a complete owned-artifact JSON sidecar; Canon locks primary bytes and artifact-record bytes independently relative to project root;
- character/product ledgers cover every visible controlled subject;
- material trajectories and dynamic ladders close every material/action ambiguity;
- V1 timing anchors are bound, or a valid single-static-shot exemption exists;
- its authority inventory exactly locks the current Shot Contract, final Storyboard, Global Look, V1/exemption, and every required character/product/packaging/material/scene asset;
- every dependency is approved, hash-valid, and not stale;
- the manifest update receipt registers K1, owned projections/anchors, and K2 when present;
- no keyframe is a multi-panel crop or endpoint-control artifact;
- the manifest denylist includes `standalone_single_image_to_video`, and no
  prompt requests classic/standalone single-image I2V while ordinary Omni R2V
  image references remain allowed;
- visual QA passes and the standard-library validator exits zero.

Claim K2 ready only when its Generation Unit Plan exactly covers K1 Shot UIDs in order, its dependency locks match K1 and Prompt preflight, one ordered handoff record exists per adjacent unit boundary (or the single-unit exemption applies), every referenced anchor exists and is hash-valid, and the same validator exits zero with `03_boundaries/BOUNDARY_SUPPLEMENT.json` present.

Keep `assistant_qa_status` separate from `production_approval_status`. Validator success proves package integrity and continuity coverage, not creative taste or final video quality.

## Minimal Invocation

`Use $ai-video-keyframe-continuity-pack to create generation-ready Omni-reference keyframes and continuity ledgers for every approved shot.`

## Shared Project Canon Write Gate

Before any Canon mutation, preserve the exact current bytes at
`<package_root>/00_manifest/BASE_PROJECT_CANON_SNAPSHOT.json` and materialize
the validated post bytes at
`<package_root>/00_manifest/CANDIDATE_PROJECT_CANON_POST.json`. Invoke only this
package's `scripts/apply_project_canon_transition.py`. The shared writer owns
the project `.canon.lock`, `PENDING_PROJECT_CANON_TRANSACTION.json` recovery or
blocking, raw-byte compare-and-swap, durable post readback, and only then
`MANIFEST_UPDATE_RECEIPT.json`. Never write Canon or an applied receipt
directly.
