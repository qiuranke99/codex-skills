---
name: ai-video-shot-script-director
description: "Upgrade a user's rough idea, structured creative shot draft, or partially specified advertising script into a model-neutral, director-grade Professional Shot Contract. Use before storyboard production when shot timing, visible action, camera intent, continuity, advertising function, asset needs, keyframe needs, or previs needs are incomplete. Start from material as detailed as a shot table; infer ordinary directing decisions without blocking. Preserve poetic and associative advertising instead of forcing literal product demonstration. Do not use to invent unsupported product claims, create storyboards or images, bind provider attachments, write model-specific video prompts, generate video, or perform post-production."
---

# AI Video Shot Script Director

中文名：AI 视频广告专业分镜脚本导演

把用户现实中能够提供的创意、粗脚本或结构化视觉分镜稿，升级为后续资产、故事板、关键帧、Previs 和视频提示词都能读取的唯一导演事实源。用户提供类似“15 镜、30 秒的写意产品广告，每镜有画面/光影/景别/转场”的稿件时，输入已经充分；本 Skill 不得把普通导演工作退回给用户。

## Trigger And Boundary

Use this Skill when the user asks to：

- 将粗糙创意、视觉脚本、分镜表或准专业稿升级为专业导演脚本；
- 补齐镜头功能、目标时长、可见动作、机位、景别、构图、运镜、切点、进出状态与连续性；
- 为后续一镜一格故事板、关键帧和 Previs 建立稳定 Shot UID 与依赖合同；
- 审计并局部改写已经存在的分镜脚本。

Do not use this Skill to：

- 生成故事板、关键帧、影调图、控制视频或成片；
- 绑定模型附件编号、写平台参数或输出模型专用生成提示词；
- 发明功效、配方、测试数据、法规承诺、认证、包装文字或品牌决策；
- 负责音乐、后期制作、成片质量审查、模型路由或运行编排。

Generation-route boundary: `standalone_single_image_to_video: forbidden`;
`ordinary_image_references_in_omni_r2v: allowed`. A downstream plan may use
many ordinary image references in Omni R2V, but it may not collapse this
contract into classic one-image I2V.

## Input Gate: Start, Infer, Or Block

Accept any one of these as sufficient starting material:

1. rough idea or prose treatment;
2. partial shot list;
3. structured creative shot draft;
4. existing professional script needing audit or selective revision.

Optional inputs include total duration, aspect ratio, campaign objective, audience, platform, supplied copy, product truth, approved character/product/scene assets, and immutable shots. Missing optional inputs are not blockers.

### Autonomous inference rule

Infer and record ordinary directing decisions, including camera height, lens intent, blocking, subject placement, visible performance, focus behavior, one primary movement, cut motivation, entry/exit state, and continuity. Store every meaningful inference in `inferred_directing_decisions` with rationale, confidence, source basis, and reversibility.

Do not ask the user to supply professional directing language that this Skill exists to create. A poetic sensorial brand film does not need a literal usage demonstration unless the source explicitly makes product operation the message. Convert abstract feeling into observable behavior rather than demanding functional exposition.

### Creative-mode classification

Before expansion, classify the source as exactly one primary mode:

- `poetic_brand_film` — associative montage, sensorial or symbolic product expression;
- `functional_demonstration` — literal operation, application, comparison, or proof sequence;
- `narrative_advertisement` — character/event causality drives the ad;
- `mixed_mode` — explicit combination; declare which shots use which submode.

The classification controls what must be literal. It must never erase the user's creative mode.

### Only genuine blockers

Continue around all non-blocking gaps. Use a blocked state only when an indispensable fact cannot be inferred without changing the work's identity, such as mutually exclusive brand directions, an exact legally material claim, exact supplied copy that is unavailable, or a source contradiction that changes the target product. Even then, complete all unaffected fields and list the isolated blocker. Never block because a normal camera, performance, continuity, or staging decision is absent.

## Canonical Resources

Read these files completely before producing the contract:

- `references/creative_mode_and_inference_rules.md`
- `references/source_ingestion.md`
- `references/shot_contract.schema.json`
- `references/shot_contract.template.json`
- `references/revision_and_invalidation_contract.md`
- `references/project_canon_manifest_contract.md`
- `references/project_canon_manifest.schema.json`
- `references/project_canon_manifest.template.json`
- `references/manifest_update_receipt.schema.json`
- `references/manifest_update_receipt.template.json`
- `references/ai_video_owner_asset_export.schema.json`
- `references/ai_video_owner_asset_approval.schema.json`
- `references/ai_video_asset_canon_delta.schema.json`
- `references/ai_video_asset_canon_pending_transaction.schema.json`
- `references/ai_video_workflow_canon_pending_transaction.schema.json`

Use `scripts/validate_shot_contract.py --verify-files-root <project_root>` before claiming completion whenever any source is marked `verified_bytes`.
Use `scripts/validate_project_canon_manifest.py` before writing the shared project registry.
Use `scripts/validate_project_canon_transition.py` with the immutable base snapshot, its raw file SHA-256, the post manifest and bound receipt before claiming any atomic Canon update.
Use `scripts/extract_source_document.py` for legacy `.doc`, `.rtf`, `.docx`, and table-like source files.

## Workflow

### 1. Preserve source intent and classify it

Extract fixed user intent, supplied facts, supplied claims, immutable shots, total-duration expectation, brand tone, and uncertainty. Separate source truth from inferred directing decisions. Do not translate sensorial or symbolic images into unrequested product instruction.

For a legacy Word `.doc`, run the deterministic extraction contract first. On macOS, use `textutil` for `.doc`, `.rtf`, and `.docx`; the helper has a standard-library XML fallback for `.docx`. On another platform, use a configured deterministic compatible converter for legacy `.doc`/`.rtf`, record its identity and output hash, and never silently guess text. If no compatible converter exists, fail closed only for the fields whose source text cannot be recovered, preserve the source-byte hash and extraction report, and continue every unaffected directing decision. Preserve table cell and row order, shot number, time token, and supplied copy; persist the source-byte hash plus extraction report. A partially corrupt cell isolates only that field and never returns ordinary directing work to the user.

Register every source document, message or approved brief in `source_inputs`; use its stable source ID for exact copy and claim provenance. Compute `file_sha256` when readable bytes exist and keep runtime-only references explicit.

### 2. Design the global directing grammar

Create `GLOBAL_DIRECTING_GRAMMAR` as a reusable global block, serialized in JSON as `global_directing_grammar`, with:

- lens and shot-scale tendencies;
- camera-movement principles;
- composition rules;
- cutting motivations;
- performance restraint;
- product-reveal strategy;
- motion rhythm;
- immutable directing rules.

This owns directing style, not color, lighting, contrast, material rendering, or grading. Those belong to the downstream Global Look artifact.

Also freeze `global_directing_prompt_full`: one production block containing every structured grammar rule verbatim. Unit and repair prompts copy this field byte-for-byte; they never independently paraphrase the structured object. Changing this block invalidates every compiled prompt.

### 3. Convert every shot into observable production facts

For every stable `shot_uid`, define:

- target duration, narrative function, advertising function;
- delivery frame context plus supplied dialogue, voice-over and on-screen copy;
- subjects, scene, initial state, action path, ending state;
- shot size, camera height/angle, lens intent, composition and placement;
- exactly one primary camera movement plus focus behavior;
- blocking, screen direction, continuity in/out, cut motivation and transition intent;
- visible emotional expression, not abstract mood alone;
- must-preserve and must-avoid constraints;
- required assets and storyboard/keyframe/previs requirements.

Use model-neutral director language. Do not include attachment indexes, provider field names, or platform command syntax.

### 4. Close time and continuity

The shot durations must sum exactly to `timeline.total_duration_seconds` within the declared numerical tolerance. Build explicit continuity edges only where continuity is intended. Associative montage may use conceptual, color, shape, gesture, texture, or motion-rhyme continuity instead of pretending that all shots share one physical space.

### 5. Protect truth and claims

Populate `claim_boundary`:

- `supplied_claims` — claims explicitly supported by user or source;
- `used_claim_ids` — only IDs from `supplied_claims` that the contract actually uses;
- `prohibited_unsourced_claims` — claims the production must not add;
- `compliance_unknowns` — unresolved legal or exact-copy questions;
- `claim_generation_status` — whether the contract stayed inside supplied evidence.

Director invention may cover staging and visual metaphor. It may not turn category knowledge into product truth. For functional ads, represent only supported operation and benefits. For poetic ads, infer sensorial visuals without adding efficacy language.

### 6. Build downstream requirement maps

Every shot must appear once in each of:

- `asset_requirement_map`;
- `keyframe_requirement_map`;
- `previs_requirement_map`.

These maps express need and risk. They do not create the downstream artifacts.

### 7. Freeze, hash, validate and approve separately

During drafting, keep `sha256: null` and `approval_status: draft`. When content is frozen, calculate SHA-256 over canonical UTF-8 JSON after removing only the envelope's top-level `sha256`; nested dependency hashes remain part of the content. Serialize with `sort_keys=True`, `separators=(',', ':')`, `ensure_ascii=False`, and `allow_nan=False`. Write the result into the root `sha256` field. Run the validator. `assistant_validated` means the contract passes machine and reasoning gates; only an explicit user action may set `user_approved`.

### 8. Initialize or update PROJECT_CANON_MANIFEST

This Skill owns the shared registry schema and initializes the canonical file at `<project_root>/00_project_canon/PROJECT_CANON_MANIFEST.json`. Register the current Shot Contract, canonical Shot UID set, artifact hash, approval state, and any open change request. Initial creation is the only no-base exception and is legal only when neither the canonical manifest nor `PENDING_PROJECT_CANON_TRANSACTION.json` exists. Every revision of an existing Canon—including selective/global Shot Contract repair—must preserve exact base bytes as `<package_root>/00_manifest/BASE_PROJECT_CANON_SNAPSHOT.json`, materialize the validated post candidate as `<package_root>/00_manifest/CANDIDATE_PROJECT_CANON_POST.json`, and invoke `scripts/apply_project_canon_transition.py`. Later Skills follow the same shared gate and may mutate only their owned scope.

The manifest indexes artifacts but is never an upstream dependency. Keep its envelope `dependencies` empty and forbid every production artifact from depending on the manifest ID/hash. This prevents a manifest update from changing the hash of every artifact it lists.

## Selective Revision

Use stable `shot_uid`; never use display position as identity.

For `selective_revision`:

1. bind exactly one frozen `predecessor_artifact` and supply its actual JSON bytes to `--previous-contract`;
2. increase SemVer and declare `requested_shot_uids`;
3. change only those shots unless a proven dependency requires expansion;
4. record `actually_changed_shot_uids`, exact `changed_json_pointers`, and any expanded dependency with reason;
5. let the validator derive the real field and stable-UID diff; self-reported scope is not authority;
6. keep unaffected shot content and hashes byte-stable where stored separately;
7. list invalidated downstream artifacts and prove every preserved artifact against the immutable Project Canon base/post transition;
8. recompute adjacent continuity only where an edge touches a changed shot.

Changing only `display_no` is a reorder, not a new identity. A reorder invalidates affected adjacency, cut logic, timing animatic, control previs, keyframe timecodes, and generated prompts. Global duration, global directing grammar, creative mode, or claim-boundary changes are `global_revision` and may invalidate the whole project.

Follow `references/revision_and_invalidation_contract.md` exactly.

## Output Contract

Deliver one JSON artifact conforming to `shot_contract.schema.json`, a concise human-readable rendering generated from that JSON, and an atomic `PROJECT_CANON_MANIFEST` initialization/update. The Shot Contract JSON is the directing authority; the manifest is the registry.

- shared artifact envelope: `contract_version`, `artifact_id`, `owner_skill`, `version`, `sha256`, `approval_status`, `dependencies`, `affected_shot_uids`, `stale_reason`;
- stable `source_inputs` with integrity and extraction status;
- source classification and source-truth boundary;
- model-neutral production specification and exact/provisional copy status;
- `director_intent`, structured `global_directing_grammar`, and byte-stable `global_directing_prompt_full`;
- closed timeline and complete `shots`;
- continuity and downstream requirement maps;
- inference ledger and claim boundary;
- revision scope and invalidation records.

Do not claim completion from prose alone.

## Completion Contract

Claim `assistant_validated` only when:

- JSON parses and `scripts/validate_shot_contract.py` exits zero;
- creative mode is explicit and source intent remains intact;
- shot count, stable UIDs, display order, and timeline all close;
- every shot has an observable action path and ending state;
- every shot has a narrative and advertising function;
- every shot has one primary camera movement, even if that movement is `locked_off`;
- continuity edges reference valid shot UIDs and do not fabricate spatial continuity for associative montage;
- all downstream maps cover every shot exactly once;
- ordinary directing decisions are inferred and logged instead of returned as user homework;
- no unsupported product claim or exact copy was invented;
- shared artifact fields are present and the frozen hash is correct;
- every `verified_bytes` source locator resolves under the supplied project/source root and its bytes re-hash exactly;
- the canonical Shot UID set and current Shot Contract hash are registered in one valid `PROJECT_CANON_MANIFEST` with no reverse dependency;
- every non-initial revision is bound to one real frozen predecessor, has increasing SemVer, exact field-level diff evidence and validator-derived changed Shot UIDs;
- every Canon mutation passes immutable `BASE_PROJECT_CANON_SNAPSHOT.json` raw-file-hash plus real pre/post transition validation; a result receipt alone is insufficient;
- approval and stale status are honest.

Validator success proves contract integrity, not legal clearance, product-claim substantiation, user taste, storyboard quality, or model output quality.

## Minimal Invocation

`Use $ai-video-shot-script-director to upgrade this structured creative shot draft into a director-grade Professional Shot Contract. Infer ordinary directing decisions, preserve its poetic or functional mode, and do not invent product claims.`

## Shared Legacy-Asset Canon Bridge

This Skill owns the strict downstream interface that allows the seven maintained
character, product, packaging, material, and scene asset owners to enter the
AI-video Project Canon without Prompt Director projections or a seventh router
Skill. The shared implementation is
`scripts/build_asset_canon_export.py`; it deliberately exposes no generic owner
CLI. Each source Skill owns a package-local
`scripts/export_ai_video_canon.py` wrapper whose package path and frozen owner
profile must agree.

An export is legal only after the original owner has completed its unchanged
visual workflow, passed assistant QA, retained the primary asset bytes and its
required prompt sidecars, and recorded an explicit `user_granted` or
`external_pipeline_granted` production decision conforming to
`ai_video_owner_asset_approval.schema.json`. The bridge then verifies:

- primary asset locator plus byte SHA-256, fully decodable PNG/JPEG/WebP
  type, matching extension, and verified dimensions of at least 64×64 pixels;
  Pillow must successfully run both `verify()` and full `load()` and the export
  fails closed when that decoder is unavailable;
- the owner-profile-specific prompt roles, UTF-8/LF bytes, and SHA-256 values;
- approval evidence owner, asset key, exact prompt hash map, primary hash, QA
  result, production decision, fixed `authority_stage`, fixed
  `terminal_route_decision`, and canonical affected Shot UID scope;
- deterministic artifact ID, slot, type, SemVer, canonical artifact hash and
  fixed owner identity;
- one owner-approved `authority_mode` and its exact
  `control_roles_authorized`; downstream Prompt compilation reads these fields
  from the hashed owner record instead of guessing from a filename or broad
  artifact type;
- a strict project-relative package root and every no-traversal file locator.

On success the original owner—not Prompt Director—writes one complete
`ai-video-artifact-v1` record under
`owned_artifacts/<artifact_id>.json`. The canonical entry binds the independent
four locks `locator/file_sha256` and
`artifact_record_locator/artifact_record_file_sha256`. The owner wrapper also
preserves exact base bytes as
`00_manifest/BASE_PROJECT_CANON_SNAPSHOT.json`, writes a canonical
`CANON_ENTRY_DELTA.json`, applies one owner-scoped manifest revision, writes the
bound `MANIFEST_UPDATE_RECEIPT.json`, and revalidates the durable pre/post
transition. Replacing a registered asset atomically moves the old entry to
immutable history, preserves historical dependency locks/edges, and applies an
event-bound stale/ineligible registry overlay to every direct and transitive
consumer. The consumer owner record remains byte-locked and approved; only its
derived Canon usability state changes, and its owner must rebuild it before
downstream reuse.

The exporter holds a project-level cross-process lock from Canon read through
candidate validation, compare-and-swap replacement and durable readback. It
rechecks the exact raw base bytes immediately before replacement. Primary,
record, base and delta referents are published first; the mutable Canon is then
atomically replaced and read back; only after that may an `applied` receipt be
written. If execution stops after Canon replacement but before receipt, an
identical fixed-owner rerun reconstructs the receipt only when the immutable
base/delta/record and the exact current post manifest prove the same legal
transition. Thus no receipt may claim `applied` while Canon still contains the
base state, and concurrent exporters cannot silently overwrite one another.
The global
`00_project_canon/PENDING_PROJECT_CANON_TRANSACTION.json` journal prevents a
second owner from advancing the registry across an unfinished transaction. A
later writer must first reconstruct the prior committed receipt and clear the
journal, or it is blocked while the prior transaction is still only prepared.
If execution stops earlier—after base/delta preparation or after owner-record
publication but before Canon replacement—the same invocation reuses only
exactly identical immutable bytes and resumes the original compare-and-swap;
any byte difference fails closed.

Use `scripts/validate_asset_canon_export.py` to validate an exported sidecar
and its exact Canon binding. This bridge changes no source Skill's trigger,
board topology, generation ordering, visual QA, 4K handoff, or final prompt-pair
publication rule.

Character route selection is fail-closed. `character-casting-lock-board` is a
pre-Canon selection artifact by default and may export only with the explicit
`--casting-as-terminal` decision bound as
`authority_stage: terminal_character_canon` and
`terminal_route_decision: casting_as_terminal`. Otherwise choose exactly one
terminal alternative: `character-final-lock-board` or
`single-face-character-lock-board`. All three share the same deterministic
`character_asset:<asset_key>` slot, so one terminal owner can never replace a
different terminal owner under the same key.

Install the decoder dependency from this Skill's `requirements.txt` before any
legacy asset export. Its exact Pillow pin must remain identical to Prompt
Director's atlas runtime pin.

## Shared Project Canon Write Gate

The six suite owners use their package-local
`scripts/apply_project_canon_transition.py` wrapper for every mutation of an
existing Canon. The wrapper alone owns the project `.canon.lock`, global
`PENDING_PROJECT_CANON_TRANSACTION.json` recovery/block decision, raw-byte
compare-and-swap, durable post readback, and post-readback receipt publication.
No Skill may write the canonical manifest or an `applied` receipt directly.
An unfinished prepared transaction blocks every other writer; a committed
transaction missing only its receipt is reconstructed from its immutable
evidence before a successor may advance Canon.
