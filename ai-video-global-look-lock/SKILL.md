---
name: ai-video-global-look-lock
description: "Create and freeze a production-wide visual look contract for AI video advertising from a Professional Shot Contract, approved identity assets, and optional look references. Use when color, lighting architecture, contrast, black floor, highlight roll-off, skin rendering, material response, optics, grain, atmosphere, and allowed scene-to-scene variation must remain coherent across storyboard frames, keyframes, and every video-generation prompt. Produce a Look Core, legal Look States, per-shot Look Deltas, and an independent visual reference set. Do not use to redesign product identity, replace scene or character canon, decide shot composition or action, generate storyboards, bind provider inputs, generate video, or perform post-production."
---

# AI Video Global Look Lock

## HIGH_CONTROL_RELEASE_GATE_V2

Before any action or production output, resolve this `SKILL.md` directory and execute the sibling OS-native launcher: on Windows, `& ..\\high-control-ai-tvc\\tools\\release-control.ps1 -Action check -Format json`; on macOS/Linux, `../high-control-ai-tvc/tools/release-control.sh check --format json`. The launcher must resolve the pinned runtime from the validated release receipt; never invoke `release_control.py` through an unverified global Python. Proceed only when `ready_latest=true`. On any failure, stop and run the same launcher with `sync`, then start a new Codex task. Bind the returned `release_commit` to this stage; never substitute a mutable Windows/Mac authoring checkout.

中文名：AI 视频全局影调锁定

Create one versioned visual-language authority that every look-applied storyboard frame, generation-ready keyframe, and video-generation prompt must inherit. A color card or one attractive reference image is not a complete lock. The Skill freezes a textual contract, a visual reference set, and a downstream inheritance rule together.

## Trigger And Boundary

Use this Skill when the project needs:

- consistent color, lighting, contrast, black level, highlight behavior, skin rendering, material response, optics, grain or atmosphere across shots;
- a hero look frame plus legal state variants for multiple scenes, times or lighting conditions;
- an explicit global look block repeated in every generation-unit prompt;
- controlled local look revision without unintentional project-wide drift.

Do not use this Skill to:

- change character identity, product geometry, packaging text, intrinsic product color, intrinsic material construction or scene topology;
- own shot order, timing, composition, camera movement, acting, blocking or physical motion;
- create storyboards, generation-ready identity keyframes, motion-control assets or final video;
- perform music, post-production, output review, model routing or run orchestration.

Generation-route boundary: `standalone_single_image_to_video: forbidden`;
`ordinary_image_references_in_omni_r2v: allowed`. Look references remain legal
parallel image controls inside Omni R2V; one Look image must never become a
classic standalone I2V route.

## Input Gate

For a final production lock, require:

1. a Professional Shot Contract with stable Shot UIDs;
2. all available approved character, product, packaging, material and scene identity assets;
3. optional user-supplied look images, color cards, visual treatments, films, stills or brand references.

If no look image is supplied, do not block. Derive a provisional Look Core from director intent and approved identity assets, then generate the minimum independent hero/state reference frames needed for visual proof. If a reference is supplied, treat it as evidence for look only; never let it override higher-authority identity, product, packaging, material or scene canon.

Missing exact product color or material evidence is not permission to stylize it. Mark the field source-limited and continue with the supported parts. Block only the affected production approval if a look decision would irreversibly misrepresent a legally or commercially critical product fact.

## Canonical Resources

Read these files completely before producing the artifact:

- `references/look_core_state_delta_rules.md`
- `references/reference_generation_and_authority_contract.md`
- `references/invalidation_contract.md`
- `references/global_look_contract.schema.json`
- `references/global_look_contract.template.json`

Run `scripts/validate_global_look.py` before claiming completion.

## Three-Layer Lock

The lock is valid only when all three surfaces agree:

1. **Textual contract** — frozen `GLOBAL_LOOK_PROMPT_FULL`, serialized as `global_look_prompt_full`, plus Look Core, State rules and negative look.
2. **Visual contract** — an approved independent `GLOBAL_LOOK_REFERENCE_SET`, serialized as `look_reference_set`, with one hero reference and enough state/risk validation references. Every visual reference owns a nested `ai-video-artifact-v1` record and is a first-class Canon asset; `reference_id` is only the internal State mapping key.
3. **Inheritance contract** — every look-applied storyboard/keyframe binds the same look version, and every video-generation prompt injects the complete global block verbatim.

None of the three can substitute for the others. A color card cannot prove light direction or material response. A hero image cannot define all legal scene states. Prompt prose without visual anchors is undercontrolled. Visual anchors without exact prompt inheritance are not global.

## Look Model: Core, State, Delta

### `LOOK_CORE`

Owns the production-wide invariant visual language:

- palette relationships, not isolated swatches alone;
- lighting architecture and source hierarchy;
- contrast curve, black floor and highlight roll-off;
- skin rendering and complexion protection;
- product/material response boundaries;
- optical texture, diffusion, halation and depth behavior;
- grain/texture and atmosphere;
- invariant rules that all states preserve.

### `LOOK_STATE`

Represents a legal manifestation of the Core under a distinct environment, time, exposure family or practical-light condition. Multi-scene work must not force one literal exposure and color temperature onto every scene. Every state declares its activation conditions, illumination, exposure relation, color-temperature relation, light direction, contrast behavior, skin protection, product-color protection, material response, allowed deltas and forbidden changes.

Freeze every State as `state_prompt_full`, preserving its structured rules verbatim. The artifact also owns one stable `look_state_matrix_id`. Render every structured `shot_look_delta` through the deterministic `shot_look_delta_prompt_full` form (`active`, exact JSON `scope`, `description`, `reason`, and `preserves_look_core`, one field per line); a paraphrase is not an authority. Downstream storyboard, keyframe, and video-prompt artifacts bind each Shot UID to exactly one State ID and copy the authoritative State and Delta blocks byte-for-byte after `GLOBAL_LOOK_PROMPT_FULL`. V1/V2 Previs remains a neutral motion/timing authority and never becomes a Look carrier.

### `SHOT_LOOK_DELTA`

Allows the minimum local adjustment required by a shot while preserving the Core and its assigned State. A delta can vary exposure relation, environmental separation, atmosphere density or approved optical texture. It cannot replace the palette system, redesign lighting architecture, recolor the product, change intrinsic material, alter skin identity, introduce a new grade family or contradict the assigned State.

Read `references/look_core_state_delta_rules.md` for the decision test.

## Workflow

### 1. Decompose inputs by authority

Separate:

- identity and intrinsic facts owned by approved character/product/material/scene assets;
- look evidence: illumination, palette relation, contrast, exposure, optical texture, grain and atmosphere;
- camera/composition/action evidence owned elsewhere;
- unresolved or conflicting appearance.

Register every supplied look image, treatment, color card or source film in `source_inputs` with integrity and authority scope. Link each decomposition record and derived look reference back to those stable source IDs.

Build explicit product and skin boundaries before aesthetic design. The Look artifact may describe how a real color or material responds to the look; it may not redefine that color or material.

### 2. Design Look Core and risk matrix

Translate the Shot Contract and references into one Core. Identify coverage risks such as skin under warm/cool light, transparent liquid, mirror metal, white packaging, black packaging, label legibility, interior/exterior changes, daylight/practical transitions, low-light blacks and highlight clipping.

Create only the Look States necessary to cover real project variation. One scene with one lighting family may use one State. Multiple materially different lighting conditions require separate States that share the Core.

### 3. Build the visual reference set

Use supplied references where they truthfully prove the intended look. Generate only missing hero, state or risk validation frames. Every machine-generated reference must be an independent clean image; do not create a multi-panel image and crop it into model inputs. A human contact sheet may be deterministically composed from approved independent references, but it is never the machine source of truth.

Before a built-in image call, freeze the reference specification and generation prompt. The image call must be terminal for that generation turn. On a later continuation, inspect the actual output, record dimensions and integrity state, compare it against Look Core and intrinsic boundaries, and approve or repair only that reference. Never treat an uninspected generation as locked.

Read `references/reference_generation_and_authority_contract.md` before generation.

### 4. Assign every shot to a legal State

Map every stable Shot UID exactly once to one State. State records continue to name internal `reference_id` values; before any downstream model input, resolve each internal ID to its nested `artifact.artifact_id` and bind that first-class asset plus exact file hash. Add a Shot Delta only when necessary and record its reason and allowed scope. Do not use local deltas to conceal an incoherent Core or missing State.

### 5. Freeze the global prompt block

Write `global_look_prompt_full` as a complete, production-ready description of Core, state-selection rule, product/skin preservation, allowed variation and negative look. Downstream prompt compilation must inject this block verbatim, then append the assigned State and any approved Shot Delta. A summary, paraphrase or “same style as before” reference fails.

### 6. Freeze, hash and approve separately

During drafting, use `sha256: null` and `approval_status: draft`. For a frozen artifact, remove only the envelope's top-level `sha256`; retain nested dependency hashes. Serialize canonical UTF-8 JSON with `sort_keys=True`, `separators=(',', ':')`, `ensure_ascii=False`, `allow_nan=False`, then calculate SHA-256. Binary references use `file_sha256` separately.

`assistant_validated` means the artifact passes the contract, visual-evidence and boundary gates. Only explicit user action may set `user_approved`.

## Selective Revision And Invalidation

- `core_revision` invalidates every look-applied storyboard, keyframe and video-generation prompt in the project. Neutral motion/timing data may remain valid.
- `state_revision` invalidates only shots assigned to that State plus derived visual references and prompts.
- `shot_delta_revision` invalidates only named Shot UIDs and their derived visuals/prompts.
- `reference_repair` invalidates every State and shot that binds the repaired reference; it does not silently rewrite the Core.

Use stable State IDs and Shot UIDs. Record changed scope, affected shots, invalidated artifacts and preserved artifacts. Any artifact with `approval_status: stale` requires a non-empty `stale_reason`.

Every non-initial revision must bind exactly one frozen `predecessor_artifact`, increase SemVer, and record the exact deterministic `changed_json_pointers`. Run the validator with `--previous-contract <frozen_previous.json>`; it derives Core change, changed State/reference bindings and propagated Shot UIDs from the actual bytes. A self-reported scope cannot authorize an extra change. Invalidated and preserved IDs are disjoint, and every preservation claim must be proved against the immutable Project Canon pre/post transition.

Follow `references/invalidation_contract.md` exactly.

## Output Contract

Read the single `<project_root>/00_project_canon/PROJECT_CANON_MANIFEST.json`, verify it, preserve its exact bytes as immutable `<package_root>/00_manifest/BASE_PROJECT_CANON_SNAPSHOT.json`, record the snapshot's raw SHA-256, and apply only this Skill's validated Global Look/reference entries through the shared atomic-delta protocol. Store `00_manifest/MANIFEST_UPDATE_RECEIPT.json`; the snapshot is historical proof and never a private current Canon. Validate the real base/post transition with the shared Shot Director helper; a receipt alone proves only result registration.

Deliver one authoritative JSON artifact conforming to `global_look_contract.schema.json`, the approved independent reference images, the manifest update receipt, and a concise human-readable rendering. The JSON must contain:

- shared envelope: `contract_version`, `artifact_id`, `owner_skill`, `version`, `sha256`, `approval_status`, `dependencies`, `affected_shot_uids`, `stale_reason`;
- complete project Shot UID set and project constraints;
- stable `source_inputs` and source-evidence decomposition;
- `look_core` and `global_look_prompt_full`;
- stable `look_state_matrix_id` and one byte-stable `state_prompt_full` per Look State;
- independent `look_reference_set`; every item includes a canonical nested artifact envelope whose dependencies equal the Global Look upstream locks and whose shot scope equals the shots assigned to States that use it;
- legal `look_states` and exact per-shot assignments, including the deterministic frozen `shot_look_delta_prompt_full` for every shot;
- structured `look_risk_coverage` for skin, product, material, label, black-floor and highlight risks;
- product/material and skin-tone boundaries;
- allowed deltas and negative look;
- three-layer downstream lock contract;
- revision scope and invalidation rules.

Do not claim completion from a mood board, color card, prompt paragraph or contact sheet alone.

## Completion Contract

Claim `assistant_validated` only when:

- JSON parses and `scripts/validate_global_look.py --verify-files-root <project_root>` exits zero for any artifact carrying `verified_bytes` sources/references;
- exactly one hero look reference is approved and every Look State has approved visual coverage;
- all generated references were independently generated and later inspected;
- every project Shot UID is assigned exactly once;
- multi-state projects preserve one Core rather than becoming unrelated grades;
- product intrinsic colors, packaging truth, material construction and skin identity have explicit preservation boundaries when present;
- `global_look_prompt_full`, every `state_prompt_full`, and every deterministic `shot_look_delta_prompt_full` are frozen and downstream byte-for-byte injection is required;
- the inheritance contract requires the same version in storyboards, keyframes and video prompts;
- Core/State/Delta revision scope and stale propagation are valid;
- the canonical hash is correct and approval status is honest.
- every `verified_bytes` source and look-reference locator resolves and re-hashes exactly.
- each look-reference owner record is materialized at `owned_artifacts/<artifact_id>.json`; its primary locator/file hash and artifact-record locator/file hash are separately locked in Project Canon;
- the current root Global Look and every nested reference artifact are active Canon entries and are registered together by one valid manifest update receipt against the canonical registry base hash.
- every non-initial revision binds one real frozen predecessor, increases SemVer, and passes exact field/State/Shot diff validation;
- the Canon update passes `validate_project_canon_transition.py` against the immutable raw-hash-verified base snapshot, with every claimed preserved artifact passed explicitly.

Validate that receipt with the shared Shot Director helper, including this Skill name and every owned artifact ID:

```bash
python3 scripts/validate_global_look.py <GLOBAL_LOOK_CONTRACT.json> \
  --project-root <project_root> \
  --project-canon-manifest <project_root>/00_project_canon/PROJECT_CANON_MANIFEST.json \
  --manifest-update-receipt 00_manifest/MANIFEST_UPDATE_RECEIPT.json
```

Validator success proves structural integrity and declared evidence coverage. It does not prove user taste, legal clearance, external provider obedience, or final-video appearance.

## Minimal Invocation

`Use $ai-video-global-look-lock to create a three-layer global look lock from this approved shot contract and these identity/look references. Preserve product and skin truth, generate only missing independent look references, and bind every shot to one legal Look State.`

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
