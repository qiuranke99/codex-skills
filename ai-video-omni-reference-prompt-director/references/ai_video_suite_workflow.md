# High-Control AI Video Advertising SOP

This is the executable handoff contract for the six new Skills plus the existing canon-asset Skills. It is optimized for high-quality advertising with many multimodal references, not free-form text-to-video.

## Non-negotiable generation mode

- Use Omni / all-reference / multimodal reference-to-video.
- Treat character, product, packaging, material, scene, look, storyboard, keyframe, and control-previs assets as separate authorities.
- Never substitute text-only video generation, single-image-to-video, first/last/start/end/endpoint-frame generation, or interpolation.
- Generation-route boundary: `standalone_single_image_to_video: forbidden`;
  `ordinary_image_references_in_omni_r2v: allowed`. Classic one-image I2V is
  excluded; ordinary image attachments remain valid controls in Omni R2V.
- Do not create a fixed attachment-count target. Bind every relevant non-conflicting authority, then split generation units or use a lossless source atlas only when a verified provider ceiling requires it.
- The currently integrated product owners cover low-risk opaque products, label-heavy packaging, and material-sensitive glass/liquid/reflective products. Do not claim coverage for mechanism-dominant or complex state-topology products unless a dedicated approved product-canon owner is supplied; block that asset scope explicitly rather than inventing mechanism geometry or states.
- Music, soundtrack creation, final editing, color mastering, and independent footage QC are outside this suite.

## Ordered production stages

### 0. Intake and source extraction

Use `ai-video-shot-script-director` to read the user's idea, prose, shot table, `.doc`, `.docx`, or existing draft. Preserve source order, wording, timing, creative mode, and claim evidence. Ordinary directing gaps are inference work, not user homework.

### 1. Professional Shot Contract

The Shot Script Director produces:

- stable Shot UIDs and exact target timing;
- observable action, state, camera intention, blocking, transitions, continuity, advertising function;
- exact/provisional spoken and on-screen copy status;
- claim provenance and prohibited claims;
- byte-stable `GLOBAL_DIRECTING_GRAMMAR` / `global_directing_prompt_full`;
- downstream asset, storyboard, keyframe, and Previs requirements;
- the canonical project registry at `00_project_canon/PROJECT_CANON_MANIFEST.json`.

This is the normative director authority, not a model prompt.

### 2. Canon asset production

Route each requirement to the existing narrow owner:

- character identity and wardrobe → Casting is pre-Canon selection by default, then choose exactly one terminal authority per `asset_key`: Final Character or Single-Face Character. Casting is terminal only through explicit `casting_as_terminal`; never keep two terminal character authorities for one `asset_key`;
- ordinary opaque product identity → multi-angle product identity lock board;
- label-heavy packaging → packaging identity/label lock board;
- glass, transparent, liquid, reflective, frosted, or material-sensitive product → material-sensitive master asset board;
- scene identity and reusable environment → scene canon asset pack.

Do not duplicate these capabilities in the six new Skills. Register every approved artifact, version, hash, scope, and dependency in the single Project Canon manifest.

### 3. Global Look Lock

`ai-video-global-look-lock` separates:

1. `GLOBAL_LOOK_PROMPT_FULL` — immutable production-wide Look Core;
2. `LOOK_STATE` — a small approved state family for real scene/time/material regimes;
3. `SHOT_LOOK_DELTA` — narrow per-shot variation that cannot contradict Core or State.

It also creates independent, inspectable look references with source/hash identity. One reference image alone is sufficient only when it proves the whole production's legal look range. Multi-state work requires enough independent references to prove each State. The look contract is used both when producing static authorities and in every video-generation prompt.

### 4. Modular Storyboard

`ai-video-modular-storyboard` produces exactly N independent frames for N scripted shots. Each frame has its own artifact/hash and can be replaced atomically. The multi-panel review board is a deterministic human-review derivative.

- `structure_draft`: composition/rhythm review only; never a model input.
- `look_applied_final`: identity/product/scene/look-authority compliant; model-input eligible after validation.

Changing Shot 5 and Shot 8 replaces only those frame artifacts and deterministically rebuilds the board. Unchanged frame bytes and hashes stay stable.

### 5. Timing Animatic V1

`ai-video-timed-animatic-previs-director` builds the full-ad V1 from storyboard frames and Shot Contract timing. V1 proves order, target windows, rhythm, and cut logic without assuming three seconds per shot. It is a planning authority, not a final video-model payload.

### 6. Core Keyframes K1

`ai-video-keyframe-continuity-pack` creates at least one generation-ready static anchor per shot plus only necessary action, product, material, and state-ladder anchors. K1 depends on V1 and the approved static authorities, but never invents Generation Unit IDs.

### 7. Generation Unit Preflight P1

`ai-video-omni-reference-prompt-director` reads an immutable snapshot of the complete current Project Canon manifest and creates the sole Generation Unit plan. It intersects:

- target semantics;
- first-party documented backend capability;
- the exact third-party provider runtime profile;
- duration and modality budgets;
- continuity-safe split points;
- required V2 control-video coverage.

For each unit, P1 records one decision and complete role set for every active Canon artifact, locks all direct dependencies, and derives counts from direct selections, planned atlas groups, and future K2/V2 inputs. Each atlas group freezes a PNG/JPEG/WebP→RGB8-PNG spec and is actually dry-built; existing direct media and planned output must satisfy hash-locked provider MIME/byte/dimension/aspect constraints. Run the standalone P1 validator against exact source Canon before K2 or V2; no P2 file may be required at this gate.

Storyboard count and request count are independent. A 15-second six-shot ad may be one unit when the provider supports the full reference set; a 30-second ad using documented Seedance 2.0 limits requires at least two units. No shot is forced to three seconds.

### 8. Boundary Supplement K2

After P1 freezes unit membership, the Keyframe Skill creates only the cross-unit handoff anchors required by that exact whole-Shot-UID plan. K2 never mutates the approved K1 hash. If one shot cannot fit a verified provider limit, return to Shot Script Director and replace it with stable Shot UIDs before K2; no generation unit may split a shot internally.

### 9. Control Previs V2

After P1 and K2, the Previs Skill produces provider-bound control videos for every multi-shot or timing-sensitive unit. V2 owns camera path, blocking, motion timing, cut realization, and relevant physical/material trajectory. A provider without required video-reference input blocks the unit; it does not trigger prose-only degradation.

### 10. Final Prompt Compile P2

The Prompt Director rereads the complete Canon manifest into a separate immutable compile snapshot and verifies that no active authority disappeared. It compiles:

- model-neutral canonical IR;
- complete per-unit multi-role bindings and any no-resize deterministic RGB8 PNG reference atlas;
- full Seedance 2.5-first forward-compatible semantic render;
- strict Seedance 2.0 documented-backend-compatible render;
- complete per-shot repair prompts;
- provider payload manifest and exact dependency/file locks.

Every unit and repair prompt repeats, in this order:

```text
GLOBAL_DIRECTING_GRAMMAR
→ GLOBAL_LOOK_PROMPT_FULL
→ assigned LOOK_STATE
→ legal SHOT_LOOK_DELTA
```

It also carries target timing, static and dynamic authorities, copy delivery mode, claim provenance, and forbidden changes.

### 11. User footage review and return loop

The user is the footage acceptance authority. If generated footage is not acceptable, diagnose against the frozen request package:

- prompt ambiguity, binding, budget, provider serialization → Prompt Director;
- changed normative shot intent → Shot Script Director;
- wrong asset identity/material/scene → corresponding canon-asset owner;
- global look error → Global Look Lock;
- wrong static realization → Modular Storyboard;
- wrong static state/continuity anchor → Keyframe Pack;
- wrong dynamic path, blocking, cut, or timing → Previs Director.

Rebuild only the owned artifact and its exact downstream descendants. Return to P1 if Generation Unit membership changes. This is revision routing, not an independent QC stage.

## Artifact DAG

```text
rough source
→ Professional Shot Contract
→ canon assets + Global Look + Storyboard Structure
→ Storyboard Final
→ V1
→ K1
→ P1 Generation Unit Plan
→ K2 Boundary Supplement
→ V2 Control Previs
→ P2 Final Prompt Package
→ [external third-party Omni generation]
→ user footage review → precise owner loop
```

The Project Canon manifest indexes the graph but is not an upstream dependency of the artifacts it lists; this prevents a registry hash cycle.

## Completion evidence

Do not advance on prose approval alone. Each stage requires its declared artifact files, producer-owned artifact records for binaries, valid shared envelope, exact dependency locks, non-stale registry entry, package validator, and manifest update receipt. Prompt final compile must also read the actual post-write Canon, prove the preflight → compile → post-write hash chain, preserve all compile-active entries, and match every registered Prompt output. Final compile additionally requires the suite validator and acceptance-gap loop to pass.
