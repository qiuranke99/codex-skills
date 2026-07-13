---
name: ai-video-omni-reference-prompt-director
description: "Use after the professional shot contract, approved canon assets, Global Look, modular storyboard, keyframe continuity pack, and any required Control Previs exist, to preflight, compile, or revise a provider-ready multimodal reference-to-video package. Read the entire approved project inventory, bind every relevant non-conflicting reference for each generation unit, compile a Seedance 2.5-first forward-compatible semantic prompt plus a strict Seedance 2.0 capability-aware render and provider payload, and route user feedback to the sole owning upstream skill when the defect is not prompt-owned. Do not use for story or asset creation, text-to-video, first/last-frame generation, music, editing, color mastering, independent video QC, or a standalone router/orchestrator."
---

# AI Video Omni-Reference Prompt Director

## HIGH_CONTROL_RELEASE_GATE_V2

Before any action or production output, resolve this `SKILL.md` directory and execute the sibling OS-native launcher: on Windows, `& ..\\high-control-ai-tvc\\tools\\release-control.ps1 -Action check -Format json`; on macOS/Linux, `../high-control-ai-tvc/tools/release-control.sh check --format json`. The launcher must resolve the pinned runtime from the validated release receipt; never invoke `release_control.py` through an unverified global Python. Proceed only when `ready_latest=true`. On any failure, stop and run the same launcher with `sync`, then start a new Codex task. Bind the returned `release_commit` to this stage; never substitute a mutable Windows/Mac authoring checkout.

中文名：AI 视频全能参考提示词导演

Contract version: `ai-video-omni-reference-prompt-director.v1`
Shared artifact contract: `ai-video-artifact-v1`

Compile approved director facts and multimodal controls into exact, traceable video-generation packages. The Skill owns prompt semantics, reference binding, generation-unit planning, capability degradation, and provider serialization. It does not own the story, assets, visual facts, motion facts, or final creative judgment.

This workflow uses only Omni / all-reference / multimodal reference-to-video generation. Keyframes, storyboards, look frames, asset boards, and control videos are ordinary parallel references. Never substitute text-only generation, single-image-to-video, or endpoint-frame generation.

Generation-route boundary: `standalone_single_image_to_video: forbidden`;
`ordinary_image_references_in_omni_r2v: allowed`. This marker excludes the
classic one-image I2V route without excluding any ordinary image attachment in
the multimodal Omni package.

## 1. Three Modes

Run exactly one mode at a time.

### `preflight`

Read every approved project artifact, verify target model/provider capabilities, plan generation units and reference budgets, detect conflicts, and produce the immutable `GENERATION_UNIT_PREFLIGHT_PLAN` (P1). P1 consumes K1 core keyframes but does not require or invent K2 boundary anchors or V2. No executable payload or final canonical IR is produced yet.

P1 is independently executable as a validation stage. Its package contains only the frozen preflight Canon snapshot, P1 plan, model capability profile, provider capability profile, and provider-schema evidence. Run `scripts/validate_preflight_package.py` before registering or approving P1; it must not require any P2 IR, binding, prompt, payload, feedback, K2, or V2 file.

### `compile`

Consume one approved P1 plan, K2 Boundary Supplement, and V2 Control Previs assets; then build the final canonical IR (P2), bind exact provider aliases, render complete Seedance 2.5-first and Seedance 2.0-aware prompts, create shot repair prompts, freeze payload records, and write a dependency lockfile.

### `revise`

Consume user review feedback plus the previous package. Modify only prompt-owned semantics, binding aliases, generation-unit boundaries, reference budgets, or provider serialization. If the requested correction belongs upstream, issue a precise change request instead of silently editing the upstream fact.

Do not merge these modes into a vague one-pass rewrite. A revised package must retain a machine-readable diff and new artifact versions/hashes.

## 2. Read The Contracts

Before work, read:

- `references/artifact_contract.md`
- `references/capability_profiles.md`
- `references/canonical_ir.schema.json`
- `references/canonical_ir_template.json`
- `references/generation_unit_preflight.schema.json`
- `references/generation_unit_preflight.template.json`
- `references/binding_manifest.schema.json`
- `references/dependency_lockfile.schema.json`
- `references/provider_payload_manifest.schema.json`
- `references/feedback_route.schema.json`
- `references/seedance_prompt_template.md`
- `references/feedback_routing.md`
- `references/ai_video_suite_workflow.md`
- `references/acceptance_gap_loop.md`
- `references/acceptance_gap_report.schema.json`
- `references/qa_checklist.md`
- `test_cases.md`

Do not invent provider limits from memory, a model name, a UI label, or a promotional claim.

Use `scripts/validate_ai_video_suite.py` only to validate development/release integration of the six Skills. It is an acceptance harness, not a runtime generation orchestrator or experiment log.

## 3. Required Upstream Inputs

Read the one canonical `<project_root>/00_project_canon/PROJECT_CANON_MANIFEST.json` in full, not only files the user mentions in the last message. `<package_root>` is a child of `<project_root>`; do not assume they are identical. Resolve Canon `locator` and `artifact_record_locator` values only against `<project_root>`, while resolving Prompt output locks and revision anchors only against `<package_root>`. Reject absolute paths and `..` traversal. For P1 and P2, persist separately named immutable input snapshots plus file hashes; snapshots are read evidence, never a second canonical registry. Inventory every active artifact and preserve its `ai-video-artifact-v1` identity/version/hash/status plus binary and artifact-record locators/hashes. Propose only Prompt-owned registry deltas and store a manifest update receipt.

Do not treat an IR field as evidence for itself and never create a Prompt-owned “authority projection” to self-validate. Read each required owner JSON from the active Canon entry's `artifact_record_locator`, verify its record-file hash, recompute its complete envelope hash, and match its identity/version/hash/dependencies/scope to Canon. An event-bound Canon stale/blocked registry overlay may demote a previously approved immutable owner record without rewriting it; this is the only permitted status divergence, and the artifact remains downstream-ineligible. Verify still/video/audio bytes separately through `locator` and `file_sha256`. For JSON roots the two locators may be identical; every binary needs a producer-materialized JSON artifact record. Compare action, camera, timing, copy, claims, Global Directing, Global Look Core, assigned State, the authoritative `shot_look_delta_prompt_full`, storyboard IDs/stage, keyframe IDs, and P1/K2/V2 membership against those original files before rendering prompts. A missing, unparsable, self-authored, or hash-inconsistent authority blocks compilation.

Use stable Canon slots: `previs_manifest` for the evolving Previs package root, `timing_animatic_v1` and `control_previs_v2:<generation_unit_id>` for media artifacts, and `generation_unit_preflight_plan` for P1. Do not accept aliases for the same semantic slot. A Global Look `reference_id` is an internal reference key, not an artifact ID: resolve it through `look_reference_set[].artifact.artifact_id`, then verify the nested envelope and corresponding Canon binary/record locks.

Final compilation normally requires:

- approved `PROFESSIONAL_SHOT_CONTRACT` and `GLOBAL_DIRECTING_GRAMMAR`;
- all approved character, product, packaging, material, and scene assets required by the shots;
- approved `GLOBAL_LOOK_PROMPT_FULL`, look references, Look State Matrix, and legal shot deltas;
- one approved independent storyboard frame per shot;
- approved generation-ready keyframes and continuity ledgers;
- approved K2 Boundary Supplement bound to the exact P1 Generation Unit Plan;
- approved Control Previs V2 for each multi-shot/timing-sensitive generation unit;
- model target and actual third-party provider capability evidence.

Accept a single-static-shot Previs exemption only when the upstream contracts explicitly allow it.

Final `compile` accepts only `user_approved` upstream artifacts. `assistant_validated` artifacts may be used for a clearly marked working preview, never an executable final payload. `draft`, `stale`, and `blocked` artifacts are forbidden.

## 4. Ownership And Conflict Rules

Use these authoritative owners:

| Fact | Owner |
|---|---|
| shot count/order/target duration/narrative and advertising function | `ai-video-shot-script-director` |
| character/product/packaging/material/scene identity | corresponding existing asset skill |
| lighting/color/contrast/texture and legal look states | `ai-video-global-look-lock` |
| normative shot size, camera height/angle, composition principle, placement target | `ai-video-shot-script-director` |
| representative still's static realization of approved framing/placement | `ai-video-modular-storyboard` |
| identity/product/material/action state anchors | `ai-video-keyframe-continuity-pack` |
| camera path/blocking/motion/cut timing | `ai-video-timed-animatic-previs-director` |
| generation-unit planning/reference binding/prompt/provider payload | this Skill |

This Skill may translate, compress, index, and serialize facts. It may not resolve an upstream contradiction by rewriting one authority to match another.

When two relevant references conflict:

1. mark both in the conflict graph;
2. identify the owning skill;
3. block only affected generation units;
4. emit an upstream change request with exact shot IDs and required resolution;
5. preserve unaffected units.

## 5. P1 Preflight: Freeze The Generation Unit Plan

Produce `GENERATION_UNIT_PREFLIGHT_PLAN.json` from the preflight manifest snapshot, approved Shot Contract, final Storyboard, Global Look, V1, K1 core keyframes, current asset inventory, documented model backend, and verified provider profile. P1 is the sole authority for Generation Unit IDs, shot membership, target unit duration, reference budgets, required modalities, and V2 requirement.

For every generation unit, classify every active preflight Canon artifact exactly once as `selected_direct`, `transported_via_atlas_planned`, `inline_text`, `irrelevant`, `conflict_blocked`, or `superseded`, with its complete artifact ref, Canon slot/type, complete `control_roles`, primary `control_role`, controlled Shot UIDs, transport modality, and reason. `planned_reference_artifact_ids` must equal the used decision records in order. The P1 envelope directly depends on every active preflight Canon artifact so a changed asset cannot leave the unit plan apparently current. Relevant shot-scoped and required global authorities cannot be classified away. Relevant image, video, voice, dialogue, or SFX media may not be collapsed into prose; bind the real matching modality or block.

Counts are derived, never typed independently: direct image/video/audio selections count once regardless of how many semantic roles they carry; every unique planned atlas group counts as one image; inline text and irrelevant records count zero; future K2 boundary anchors and the required V2 control video are explicit `planned_future_inputs` and count by modality. Every `planned_atlas_group` freezes ordered sources, layout/background/policies, then performs a real dry-build and locks PNG hash, bytes, dimensions, codec, media type, Pillow decoder runtime, and encoder runtime. The derived counts and actual media properties must fit the strict model/provider intersection. A multi-shot or timing-sensitive unit reserves exactly one future Previs-owned V2 video input before K2/V2 production.

For every unit set `control_previs_requirement` by rule, not by author self-report: more than one shot or any timing-sensitive camera/blocking/physics requirement means `required`, and `video` becomes a required modality. `exempt_single_static_shot` is legal only for one static shot in the entire project.

The artifact sequence must stay acyclic:

```text
V1 → K1 core keyframes → P1 unit preflight → K2 boundary supplement → V2 control previs → P2 final compile
```

## 6. P2 Compile: Build The Final Canonical IR

After K2 and V2 exist, create `CANONICAL_VIDEO_GENERATION_IR.json` as the model-neutral source for every backend. It must contain:

- exact artifact inventory with approval/version/hash;
- ordered shots and target timing;
- exact byte-stable `global_directing_prompt_full` from the Shot Contract;
- exact `GLOBAL_LOOK_PROMPT_FULL` and look-reference IDs;
- per-shot subjects, scene, initial state, visible action, camera, placement, motion, ending state, continuity, and legal look delta;
- storyboard, keyframe, state-ledger, and Control Previs links;
- per-shot `look_state_id`, exact State block, State references, and structured/exact Shot Delta;
- structure-preserving spoken/on-screen copy and claim provenance with explicit `model_spoken`, `external_overlay_handoff`, or `prohibited_model_text` delivery;
- forbidden changes and claim boundaries;
- inferred low-risk prompt decisions, visibly separated from sourced facts.

The IR is not a prompt and contains no provider attachment numbering. Its full source inventory must equal the active compile-time Project Canon manifest set; deleting an asset from both IR and binding records cannot hide its earlier unsuperseded existence.

## 7. Preflight: Model And Provider Profiles

Keep model semantics separate from provider runtime capability.

### Seedance 2.5-first target

Use `seedance_2_5_forward_compatible` as a forward-compatible semantic target. As of this contract, do not represent Seedance 2.5, a 50-reference limit, 30-second duration, or any endpoint as public runtime fact unless the current provider exposes verifiable schema/evidence.

Record unverified claims such as “50 multimodal inputs” only as:

```text
evidence_tier: preview_or_user_supplied_claim
runtime_verified: false
usable_for_payload_budget: false
```

If a provider later exposes a verified limit, record that provider-specific evidence and use it at runtime. Capacity is a ceiling, never a target number of references.

### Seedance 2.0 backend

The official first-party contract supports natural-language plus up to:

```text
9 images + 3 videos + 3 audio files + 15 seconds
```

It supports multimodal all-reference, textual storyboards, and multi-shot output. Encode those as first-party documented capabilities; still intersect them with the actual provider surface, which may expose less.

### Fail-closed provider rule

The provider must expose an Omni / multimodal reference-to-video path and every modality marked required for the unit. If it exposes only text input, only endpoint frames, or a partial R2V surface missing a required reference modality:

- set payload status `blocked_unsupported_required_modality`;
- name the exact missing modality/control;
- do not silently discard it;
- do not fall back to text-only, single-image-to-video, or endpoint-frame generation.

## 8. Preflight: Plan Generation Units

Storyboard shot count is independent from API request count. Preserve all Shot Contract `shot_uid` values.

Plan the fewest contiguous generation units that satisfy:

- verified duration limits;
- verified image/video/audio/total reference limits;
- shot and action continuity;
- Control Previs coverage;
- provider payload size and supported modalities;
- manageable scene/identity/motion complexity.

Split only between complete canonical Shot UIDs. Prefer cuts or major state boundaries. Never default every shot to three seconds. Never merge, drop, reorder, silently shorten, or split the interior of a Shot UID to fit a provider. If one scripted shot itself exceeds capacity, return to the Shot Script Director to replace it with multiple stable Shot UIDs, then regenerate all dependent artifacts.

For a 30-second sequence:

- one 30-second unit is allowed only if the selected provider's current verified profile supports it;
- Seedance 2.0 requires two or more units of no more than 15 seconds each;
- a single-shot repair unit is allowed after user feedback without changing the canonical storyboard count.

## 9. Compile: Bind The Full Relevant Reference Set

Read all approved assets. For each generation unit classify every artifact as:

- `relevant_selected`;
- `irrelevant_to_unit` with reason;
- `conflicting_blocked` with owner and resolution;
- `superseded_version` with the selected replacement;
- `unsupported_modality_blocked`.

Every relevant, approved, non-conflicting artifact must be selected. Do not arbitrarily reduce the set to four or five assets. Do not fill a capacity ceiling with redundant references.

For each shot, persist `required_control_artifact_ids`. For its generation unit, every required ID must be delivered either as a direct selected binding or as a source panel inside a selected, verified atlas. Reclassifying required identity, product, scene, Look, Storyboard, Keyframe, or V2 evidence as “irrelevant” is a hard error even when the declared attachment counts still fit.

For every selected binding record:

- modality and provider alias;
- complete ordered `control_roles` and one primary `control_role`; multiple roles never duplicate an attachment count;
- scope (`project | generation_unit | shot`);
- controlled shot IDs;
- expected influence;
- priority and conflict exclusions;
- artifact ID/owner/version/hash and binary hash when applicable.

Control roles include identity, wardrobe, product geometry, exact label evidence, material behavior, scene canon, global look, storyboard, keyframe state, keyframe boundary, camera path, blocking, physical motion, Control Previs, source-approved dialogue voice, and synchronous SFX. Score, soundtrack, or music creation is outside this suite and cannot enter a binding role.

When capacity is insufficient, use this order:

1. split at a continuity-safe generation-unit boundary;
2. remove only truly irrelevant/superseded evidence;
3. create a deterministic unit-specific reference atlas from approved independent stills when the provider counts images rather than internal panels and the atlas remains legible;
4. block rather than omit a required control.

An atlas is a transport artifact, not a new visual source. Its manifest maps every panel to the exact source ID/version/hash and complete role set, preserves native pixels, forbids generative recomposition, and never contains conflicting identities or tiny unreadable evidence. Every native panel must be at least 256×256 and obey `identity_geometry_look_only_no_microcopy`; any role set containing `label_copy` stays a direct source-authorized binding. The v2 compositor accepts single-frame PNG, JPEG, and WebP, deterministically handles EXIF/ICC/alpha, never scales, places mixed native sizes into max-native cells with center-floor padding, and emits metadata-free `PNG_RGB8`. It requires `Pillow==11.3.0` from `requirements.txt`; receipts lock Pillow, codec backends, and fixed encoder parameters. Missing Pillow, animation, unsupported codec (including PPM/HEIC), source/hash drift, or runtime-version drift fails closed. P1 dry-builds the exact group; P2 rebuilds and byte-compares its PNG and receipt. Materialize `owned_artifacts/<atlas_id>.json` separately from the image bytes. Arbitrary binaries labeled “atlas” fail closed.

The provider-runtime snapshot must lock `input_constraints` for every advertised non-text modality. P1 live-inspects direct inputs and dry-built atlases against accepted MIME, bytes, dimensions, aspect, duration, frame rate, streams, container, and codec. P2 repeats live Pillow/ffprobe checks on every actual selected image/video/audio; a stored media probe never substitutes for the actual file and must match it.

## 10. Compile: Prompt Structure

Render every unit with the exact structure in `seedance_prompt_template.md`:

1. generation task and output specification;
2. reference mapping and control authority;
3. principal subjects;
4. scene and initial environment state;
5. visible emotional/advertising objective;
6. exact `GLOBAL_DIRECTING_GRAMMAR`;
7. exact `GLOBAL_LOOK_PROMPT_FULL`;
8. global continuity and forbidden changes;
9. ordered shot blocks;
10. final stability/negative constraints.

Each shot block contains:

```text
Shot UID / target time window / advertising function
subject action path and visible expression
shot size, camera position, single primary camera movement
blocking and spatial change
material/product state change
ending state and continuity handoff
exact assigned LOOK_STATE block
legal SHOT_LOOK_DELTA
```

Use one primary camera-movement intention per shot. Translate emotion into visible performance. Preserve exact label copy only through deterministic/source-backed evidence; otherwise prohibit invented text.

### Seedance 2.5-first render

Preserve target time windows, explicit multimodal role bindings, and the full structured sequence. Label it a forward-compatible semantic render until the provider profile verifies a 2.5 runtime.

### Seedance 2.0 render

Keep target time windows in the IR and payload manifest, but phrase the model-facing shot body as ordered beats and relative pacing where precise seconds are not provider-reliable. Respect 15-second and 9-image/3-video/3-audio ceilings. Do not claim that a 2.5-sized attachment set is directly compatible.

### Global inheritance

Copy the complete approved `GLOBAL_DIRECTING_GRAMMAR` and `GLOBAL_LOOK_PROMPT_FULL` verbatim into every generation-unit prompt. A summary, ID-only reference, or “same look as above” fails.

## 11. Compile: Provider Adapter

The provider adapter is an internal serialization layer, not a standalone router Skill. It must:

- translate stable artifact IDs to provider aliases such as `@图片N`, `@视频N`, and `@音频N` only at the final payload boundary;
- keep canonical IDs in manifests and dependency records;
- avoid bare opaque asset IDs in model-facing action sentences;
- store actual endpoint/model/surface parameters exposed by the provider;
- require one local provider-schema snapshot, its file SHA-256, and exact equality between the snapshot's model ID, surface, modalities, backend binding, and limits and the provider capability profile;
- preserve request order and unit-local alias mapping;
- mark unknown controls as unknown rather than inventing them;
- emit no executable payload until every required binding and capability passes.
- serialize only `omni_reference_to_video`; recursively reject T2V, first/last/start/end/endpoint-frame, or interpolation keys and values in provider payloads.

## 12. Compile: Required Outputs

The independently validated P1 package requires only:

```text
00_manifest/PROJECT_CANON_PREFLIGHT_INPUT_SNAPSHOT.json
00_manifest/GENERATION_UNIT_PREFLIGHT_PLAN.json
00_manifest/MODEL_CAPABILITY_PROFILE.json
00_manifest/PROVIDER_CAPABILITY_PROFILE.json
<provider-schema evidence files referenced by the provider profile>
```

Validate it before K2/V2:

```bash
python3 scripts/validate_preflight_package.py <package_root> \
  --project-root <project_root> \
  --project-canon-manifest <project_root>/00_project_canon/PROJECT_CANON_MANIFEST.json
```

At this moment the supplied Canon must be the exact source manifest frozen in the P1 snapshot. After P1 passes, register the approved P1 through the shared Canon transition protocol; K2 and V2 consume that registered artifact.

P2 adds the following compile outputs under the same package contract:

Write under:

`outputs/ai-video-prompts/<project_id>/<package_id>/`

```text
00_manifest/PROJECT_CANON_PREFLIGHT_INPUT_SNAPSHOT.json
00_manifest/PROJECT_CANON_COMPILE_INPUT_SNAPSHOT.json
00_manifest/MANIFEST_UPDATE_RECEIPT.json
00_manifest/GENERATION_UNIT_PREFLIGHT_PLAN.json
00_manifest/CANONICAL_VIDEO_GENERATION_IR.json
00_manifest/MODEL_CAPABILITY_PROFILE.json
00_manifest/PROVIDER_CAPABILITY_PROFILE.json
00_manifest/DEPENDENCY_LOCKFILE.json
01_bindings/MULTIMODAL_BINDING_MANIFEST.json
02_prompts/PROJECT_GLOBAL_BLOCK.md
02_prompts/SEEDANCE_2_5_MASTER_PROMPT.md
02_prompts/SEEDANCE_2_0_COMPATIBLE_RENDER.md
02_prompts/GENERATION_UNIT_PROMPTS.json
02_prompts/SHOT_LEVEL_REPAIR_PROMPTS.json
03_payload/PROVIDER_PAYLOAD_MANIFEST.json
04_reports/CAPACITY_DEGRADATION_REPORT.md
04_reports/PROMPT_REVISION_DIFF.md
04_reports/FEEDBACK_ROUTE.json
owned_artifacts/<atlas_id>.json
```

`SHOT_LEVEL_REPAIR_PROMPTS.json` contains one self-contained repair prompt per canonical shot. A repair prompt repeats the full global directing/look blocks and all shot-relevant bindings; it never says only “fix Shot 5” or relies on hidden context.

The update receipt is package-local write evidence, not proof by itself. Final validation also reads the actual post-write Project Canon supplied on the command line. The compile snapshot must directly descend from the P1 preflight snapshot; actual post-Canon `base_manifest_sha256` must equal the compile snapshot hash; its `updated_by_skill` must be this Skill; and receipt base/result/registered IDs must exactly match the compile snapshot, actual post-Canon hash, and active Prompt-owned entries including file and artifact-record locks. The two snapshots remain read-only evidence and never become competing canonical manifests.

## 13. Revise: User Feedback And Upstream Routing

The user—not this Skill—reviews generated footage. This is a feedback intake and recompilation mode, not independent output QC.

Classify feedback using `feedback_routing.md`:

- prompt ambiguity, aliasing, unit split, budget, or provider serialization → repair here;
- story/order/duration/advertising function → Shot Script Director;
- identity/product/label/material/scene canon → the corresponding asset owner;
- global light/color/contrast/texture → Global Look Lock;
- changed normative camera/composition intent → Shot Script Director;
- wrong static realization of the approved framing/placement → Modular Storyboard;
- visual state/pose/product/material continuity → Keyframe Pack;
- motion/cut/blocking/physics timing → Timed Animatic/Previs Director.

For a prompt-owned change:

1. retain the approved upstream artifacts;
2. create a new package version;
3. change the smallest prompt/binding/unit surface that resolves the issue;
4. rebuild affected unit and repair prompts;
5. update the dependency lockfile and revision diff;
6. preserve unaffected prompt bytes and hashes when no global block changed.

`revise` additionally requires an immutable previous IR file and previous dependency lockfile, both with file hashes; the exact previous package reference; a hash-locked revision diff; and a disjoint complete partition of changed versus unchanged output paths. Every unchanged output must retain its previous byte hash. Self-declared “unchanged” records without the prior package evidence are invalid.

For an upstream-owned change, emit a structured `upstream_change_request`; do not patch the prompt to contradict the current canon.

Classify camera/framing feedback by evidence: a requested change to normative camera intent belongs to Shot Script; a static frame that fails the approved intent belongs to Storyboard; a time-varying camera path, speed, blocking, or cut realization belongs to Previs.

## 14. Invalidation Rules

- Shot Contract change → affected units, prompts, payloads, and repairs stale; replan units if timing/order changed.
- Canon asset change → dependent bindings/prompts/payloads stale.
- Global Directing Grammar or Global Look Core change → every unit and repair prompt stale.
- Storyboard, keyframe, or Control Previs change → affected bindings/unit prompts/repairs stale.
- Provider capability change → provider payload and capacity report stale; canonical IR remains valid if semantics did not change.
- Generation Unit Plan change → K2 Boundary Supplement, every affected V2 unit, bindings, prompts, payload, and repairs stale; no payload is executable until they are rebuilt.
- Prompt-owned wording change → upstream artifacts remain valid.

Never mutate an approved artifact in place. Use the shared envelope and exact dependency lock.

## 15. Completion Gate

Claim P1 `ready_for_boundary_supplement` only when:

- the standalone P1 validator exits zero without any P2 file;
- its frozen snapshot exactly equals the supplied source Canon and every active primary/record byte lock resolves under the project root;
- every active Canon artifact has one unit-local decision for every generation unit and the P1 dependencies lock all active refs directly;
- relevant assets are selected directly, planned through a deterministic atlas, or consumed as exact inline authority rather than hidden as irrelevant;
- planned reference IDs and modality counts are derived exactly from decisions, atlas groups, and future K2/V2 controls;
- every atlas group has at least two supported sources, exact dry-build evidence, and provider-valid output media properties;
- unit duration, required modalities, and derived counts fit the documented-backend/provider intersection;
- whole Shot UIDs cover the canonical order exactly, the plan is non-stale, and approval status is honest.

Claim `package_status: compiled` only when:

- canonical IR covers every scripted shot exactly once and preserves order;
- P1, K2, V2, and P2 form the approved acyclic artifact chain;
- both manifest input snapshots are hash-valid, and P2 inventory exactly matches every active compile-manifest artifact;
- the actual post-write Project Canon is inside `<project_root>`, directly descends from the compile snapshot, preserves all compile-active entries, and contains every registered Prompt-owned output with exact identity/binary/record locks;
- every upstream input is `user_approved`, hash-valid, and not stale;
- every canonical IR fact named above matches the actually read, hash-locked upstream authority file;
- every relevant non-conflicting reference is bound to each affected unit;
- every per-shot required control is delivered directly or through a byte-reproducible selected atlas;
- every binding/prompt preserves complete roles and every selected media file passes live provider upload constraints;
- no selected binding exceeds verified effective provider capacity;
- every required modality is supported by the provider;
- every generation-unit prompt repeats exact global directing and look blocks;
- every unit and repair prompt contains every assigned shot exactly once with target window, action, camera, state, exact Look State, and Delta;
- the 2.5 render is truthfully labeled forward-compatible unless runtime-verified;
- the 2.0 render obeys 15-second and 9/3/3 capability ceilings;
- master, unit, repair, binding, payload, degradation, feedback, and lockfile artifacts exist;
- there is no text-only or endpoint-frame fallback;
- provider payload recursive denylist, feedback sole-owner schema, and exact dependency/file lock all pass;
- the provider runtime profile equals its local schema snapshot, and any revision equals its prior-package lock except for declared changed outputs;
- the validator passes with the declared Pillow and ffprobe runtime dependencies.

Run:

```bash
python3 scripts/validate_prompt_package.py <package_root> \
  --project-root <project_root> \
  --project-canon-manifest <project_root>/00_project_canon/PROJECT_CANON_MANIFEST.json
```

Validator success proves package integrity and capability consistency. It does not assert provider availability, generation success, or creative approval.

## Minimal Invocation

`Use $ai-video-omni-reference-prompt-director in preflight, compile, or revise mode to produce a Seedance 2.5-first, Seedance 2.0-aware multimodal reference-to-video package from all approved project assets.`

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
