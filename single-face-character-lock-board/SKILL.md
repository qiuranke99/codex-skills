---
name: single-face-character-lock-board
description: "Use when the user provides materializable character references for one selected identity and needs exactly one text-free horizontal 16:9-requested board with one visible-face bust plus headless front and back full-body wardrobe views. When the local Codex Desktop evidence gate passes, freeze the source bytes and exact generation prompt, delegate the terminal built-in image call to one non-decision image worker, bind and inspect that worker's actual board, then publish the complete generation and image-specific 4K prompt pair with both SHA-256 values in the same task's final main result. Do not use for ordinary turnarounds, expression sheets, casting boards, posters, scenes, or prompt-only delivery."
---

# Single-Face Character Lock Board

中文名称：单脸角色资产锁定板

`asset_board_contract_version: delegated_image_worker_prompt_pair_v3`

Generate one board with exactly three visual components:

1. one bust portrait containing the only complete visible face;
2. one headless front full-body view from neck to complete feet;
3. one headless back full-body view from neck to complete feet.

The main agent owns identity resolution, prompt truth, visual QA, repair decisions, and the final main result. Exactly one non-decision image worker owns each terminal built-in imagegen call. This separation lets the worker obey the terminal image-call rule while the main agent continues the same user task and publishes both prompts without requiring a second user message.

## 1. Identity Selection Gate

Require at least one usable character reference and resolve one `target_identity` before generation.

- Combine identity evidence only when the references clearly show the same person.
- Respect user assignments for identity, hair, skin, body, outfit, shoes, and accessories.
- Treat a different person's outfit image as wardrobe evidence only.
- If two or more identities remain plausible, return `selection_pending` and ask the user to select `identity_source`.
- Do not average, blend, or infer a preferred face from different people.
- Route an explicitly requested composite identity outside this Skill.

Input status must be exactly one of:

- `ready`
- `selection_pending`
- `hard_blocked_no_character_reference`
- `policy_blocked`

Only `ready` permits generation.

Privately bind `identity_source`, `hair_source`, `skin_source`, `body_source`, `outfit_source`, `shoe_source`, and `accessory_source` as `user_locked`, `source_supported`, `safe_inferred`, or `missing_or_conflicting`. User assignments outrank inference. Keep local paths, private notes, and hidden reasoning outside the generation prompt.

## 2. Enforce The Fixed Board

Request one clean, text-free, horizontal 16:9 neutral-gray studio board with realistic photographic texture, soft even light, minimal shadow, and production-reference clarity.

### Bust portrait

- chest-up or upper-body, frontal or near-frontal;
- neutral natural expression;
- source-faithful hairline, facial geometry, skin, marks, facial hair, and visible identity-critical jewelry;
- exactly one complete visible face and the only face anywhere on the board.

### Headless front full-body

- neck downward to complete feet;
- the same body proportion, outfit, shoes, and accessories;
- readable front garment construction, waist, pockets, hems, and footwear;
- no head, face, partial face, reflected face, or printed face.

### Headless back full-body

- neck downward to complete feet;
- the same body proportion, outfit, shoes, and accessories;
- readable back collar, seams, pockets, hems, and shoe backs;
- no head, turned head, profile, or partial face.

Forbid additional panels, people, heads, faces in reflections or prints, mirrors, expression tiles, labels, arrows, measurements, watermarks, UI, poster styling, editorial scenes, illustration, anime, CGI, and decorative typography.

Set:

```yaml
built_in_prompt_aspect_ratio_request: "horizontal 16:9"
built_in_prompt_alternate_aspect_ratios_allowed: false
built_in_dimensions_policy: evidence_only_nonblocking
```

Returned dimensions are observational evidence. A nearby or different built-in raster ratio cannot by itself fail content QA, trigger repair, block prompt-pair finalization, or block the external 4K handoff.

## 3. Pass The Automatic Runtime Gate

Before composing a production prompt, verify all of the following:

- the main agent can create and wait for one isolated subagent;
- current authorization permits exactly one non-decision image-execution worker;
- one collaboration slot is available or can be freed without interrupting required work;
- the built-in image tool is callable by that worker;
- the main agent can read the local Codex state DB, the worker rollout, `$CODEX_HOME/generated_images`, and the generated PNG;
- the current main thread ID is exposed and can be frozen before worker spawn;
- every required source reference has a readable local file path that can be copied into the run directory;
- `scripts/freeze_reference_bundle.py` is readable and executable;
- `scripts/resolve_worker_image.py` is readable and executable;
- the run directory can be created, written, and reread;
- the main agent can inspect a local image and return a non-empty `final` response.

This delegated branch is proven for local Codex Desktop, not for every host. If the current thread ID is unavailable, return `blocked_parent_thread_identity`. If a conversation image cannot be materialized to a local file, return `blocked_reference_materialization`; a recent-image count is not byte identity. If any other condition fails, return `blocked_automatic_prompt_pair_runtime` before generation. Do not fall back to a main-agent imagegen call: that would make the main turn terminal and recreate the image-only failure. Do not claim that an untriggered host continuation will happen.

## 4. Freeze Prompt Truth

Use `outputs/character-locks/<asset_id>/` as the run directory.

Before spawning the worker:

1. Capture `runtime_capability_snapshot`, including collaboration, imagegen, reference transport, state/rollout access, image inspection, and known output limits. Leave unknown values `unknown`.
2. Deduplicate the physical source files while preserving first-use order. Map multiple source roles to one alias instead of passing one file more than once.
3. Run `scripts/freeze_reference_bundle.py` with one ordered `alias=path` argument per unique source. It copies the bytes to `references/` under the run directory and writes `<asset_id>_reference_manifest.json` with ordered aliases, absolute frozen paths, byte sizes, per-file SHA-256 values, and one ordered-bundle hash. Worker and resolver use only these frozen copies. No process writes them after freeze.
4. Reopen the reference manifest and every frozen copy. If a file, size, order, or hash differs, return the exact `blocked_reference_*` code before spawn.
5. Build the complete `final_generation_prompt` with attachment aliases, one selected identity, source-role bindings, the exact three-component topology, horizontal 16:9 request, realistic studio style, and strict negatives.
6. Normalize the prompt as UTF-8 with LF line endings and no BOM. Save exactly those bytes as `<asset_id>_generation_prompt.md`; add no heading, fence, frontmatter, or metadata wrapper.
7. Reopen the sidecar, compute `generation_prompt_sha256`, and require byte equality. If persistence or readback fails, return `blocked_generation_prompt_persistence`.
8. Keep `final_4k_enhancement_prompt` unset. A private `draft_4k_enhancement_prompt` may contain invariant topology and fidelity requirements, but it is not deliverable and has no final hash.
9. Create `asset_record.yaml`; record the current `parent_thread_id`, reference-manifest path/hash, and prompt hash before spawning.

Use these pre-worker states:

```yaml
image_worker_status: not_started
terminal_generation_call: worker_pending
assistant_qa_status: pending_post_generation_inspection
4k_enhancement_prompt_status: draft_pre_generation
task_finalization_status: worker_generation_pending
main_result_prompt_pair_status: pending
external_4k_status: not_ready
production_approval_status: not_granted
```

The frozen sidecar is the single source of truth. Commentary, chat memory, `asset_record.yaml`, summaries, and reconstructed strings cannot replace it.

## 5. Delegate One Terminal Image Worker

Generate a cryptographically unpredictable 32-character lowercase hexadecimal `worker_run_nonce`. Create a fresh, unique worker task named exactly `single_face_image_<normalized_asset_id>_<full_worker_run_nonce>` and record `worker_spawn_not_before_ms` immediately before spawning. Normalize the asset ID so the complete task name contains only lowercase letters, digits, and underscores. The full nonce must remain visible in the task-name suffix because Codex encrypts inter-agent task bodies in worker rollouts. Use the canonical agent path returned by `spawn_agent`; never infer it later.

Give the worker the minimum complete execution contract:

- use the available imagegen Skill and built-in image tool;
- use the exact frozen prompt text without changing one character;
- receive the ordered frozen paths from `<asset_id>_reference_manifest.json` through one exact `referenced_image_paths` list;
- pass `prompt` as one JSON double-quoted string literal and `referenced_image_paths` as one ordered JSON string-array literal inside the imagegen argument object; use no prompt variable, template literal, concatenation, or rewritten wrapper text;
- call imagegen exactly once;
- make no creative, identity, QA, repair, approval, or publication decisions;
- after imagegen, emit no text and call no unrelated tool.

Use `fork_turns="none"` and provide the complete prompt and frozen paths in the worker task; the worker needs no other conversation history. Treat the task body as encrypted transport, not as a source of plaintext provenance. The main agent remains the active finalizer and waits for the worker to reach a completed state. An empty worker final is expected and is not the deliverable.

For a repair, create a new uniquely named worker and a new frozen attempt prompt. Never reuse an ambiguous worker thread and never switch the repair call back to the main agent.

## 6. Bind The Exact Worker Result

After worker completion, run the bundled resolver with the recorded checkpoint, exact returned agent path, frozen prompt sidecar, exact reference contract, run image destination, and result-record path. The resolver reads the current parent rollout from local Codex state and binds the parent's `spawn_agent` call to the worker's encrypted task-delivery bytes. Use the bundled Python runtime when plain `python` is unavailable.

Example shape:

```text
python scripts/resolve_worker_image.py
  --agent-path <canonical worker path>
  --not-before-ms <checkpoint>
  --parent-thread-id <exact current main thread id>
  --worker-run-nonce <32 lowercase hex characters>
  --expected-prompt <asset_id>_generation_prompt.md
  --reference-manifest <asset_id>_reference_manifest.json
  --copy-to <asset_id>_single_face_lock_board.png
  --result-json <asset_id>_image_worker_result.json
```

The resolver must prove all of the following before the board can be inspected:

- exactly one fresh thread matches the exact worker agent path, checkpoint, and parent thread ID;
- its leading rollout session metadata equals the worker thread, agent path, and parent thread;
- the visible worker task-name suffix equals the complete 32-character nonce;
- the latest worker task contains exactly one `trigger_turn` envelope and one encrypted inter-agent delivery whose header names the exact task and parent agent; that delivery plus `task_started` / `turn_context` / `task_complete` share one turn ID;
- after the recorded checkpoint, the parent rollout contains one matching `spawn_agent` call, one started activity, and one spawn result in one parent turn; its encrypted message bytes equal the worker delivery bytes and all records bind the same worker thread and agent path;
- exactly one imagegen call and one `image_generation_end` exist in that latest task, in call-before-end order;
- the image event is `completed`;
- both worker final records are empty and occur after image completion but before task completion;
- the prompt sent to imagegen is byte-identical to the frozen sidecar;
- the `referenced_image_paths` list equals the frozen manifest in order and multiplicity;
- every frozen reference still matches its manifest size and SHA-256;
- `worker_thread_id + image_generation_call_id` maps to the reported PNG path;
- the PNG header, dimensions, copied bytes, and SHA-256 are valid.

Selecting the newest PNG by timestamp is forbidden because concurrent tasks can generate unrelated images. Resolver failure sets its exact `blocked_worker_*` code, keeps `main_result_prompt_pair_status: pending`, and prevents QA or publication.

On success, set:

```yaml
image_worker_status: bound
worker_binding_mode: parent_spawn_cipher_chain_v1
terminal_generation_call: worker_executed
task_finalization_status: worker_result_bound
4k_enhancement_prompt_status: awaiting_post_generation_inspection
codex_board_role: continuity_reference
```

Persist `<asset_id>_image_worker_result.json`; it is required provenance for final publication.

## 7. Inspect The Actual Board

Open the run-scoped copied PNG with the available image-inspection tool. Record source path, width, height, observed ratio, exact-16:9 boolean, image SHA-256, worker thread ID, and generation call ID.

Require:

- exactly one complete visible face, only in the bust;
- no other complete or partial face in reflections, prints, shadows, or the background;
- source-faithful identity in the bust;
- headless front and back body views, both complete to the feet;
- consistent body, outfit, shoes, and accessories;
- exactly three components and no text, scene, or editorial styling.

Set `assistant_qa_status: passed` when every structural and source-supported check passes, `conditional` only for a useful source-limited board, and `failed` for critical topology or identity drift. Keep `production_approval_status` independent.

Persist `<asset_id>_inspection.json` with `inspected: true`, the absolute run-board path, image SHA-256, dimensions, topology findings, observed defects, source-fidelity status, and `assistant_qa_status`. The record's board path and hash must match `<asset_id>_image_worker_result.json`.

One focused repair is allowed when a corrected prompt can plausibly close the failure. Preserve failed attempts as evidence, freeze a new exact prompt and hash, and repeat Sections 5–7 with a fresh worker. Reject the board when a repair cannot close the failure.

## 8. Create The Image-Specific 4K Prompt

Only after visual inspection, create `final_4k_enhancement_prompt`. The external reference bundle must contain both:

- `codex_asset_board` for layout and topology;
- `original_source_references` for identity, hair, skin, body, outfit, shoes, and accessories.

If original sources are unavailable, set `source_fidelity_status: blocked_missing_original_sources` and do not claim handoff readiness.

The final enhancement prompt must:

- request one exact 16:9 canvas at the external runtime's 4K tier;
- preserve the actual board's three components and positions;
- name only defects observed in the actual board;
- keep exactly one visible face and both body views headless, including reflections and prints;
- preserve facial geometry, age markers, skin tone, hairline, hairstyle, body proportion, garment construction, shoes, and accessories;
- recover only source-supported skin and hair microtexture;
- preserve natural asymmetry and reject beauty retouching, face reshaping, age drift, invented pores, invented marks, or invented product/wardrobe details;
- keep the board text-free and introduce no person, head, face, panel, crop, logo, label, background, or decorative element.

Normalize and save exact UTF-8/LF bytes as `<asset_id>_4k_enhancement_prompt.md`, compute `4k_enhancement_prompt_sha256`, set `4k_enhancement_prompt_status: finalized_post_inspection`, and create `<asset_id>_4k_handoff.yaml` with:

```yaml
external_runtime_request:
  provider: <selected provider or unknown>
  model_profile: nano_banana_pro | nano_banana_2 | model_agnostic
  aspect_ratio: "16:9"
  image_size: "4K"
```

Record the same model profile under `third_party_model_target`; keep a provider's runtime-observed model separate from the requested profile.

If exact external controls are unavailable, set `external_4k_status: blocked_runtime_controls`; choose no alternate ratio or size. Otherwise use `handoff_ready`, `pending_external_generation`, `returned_unverified`, `verified`, or `rejected` only as evidence warrants. Returned evidence records `observed_pixel_dimensions`, `provider_declared_aspect_ratio_profile`, `observed_file_aspect_ratio`, `aspect_ratio_evidence`, `four_k_evidence`, `source_fidelity_status`, and `external_4k_qa_status`.

`prompt_pair_ready` does not imply `external_4k_status: handoff_ready`; publication and external execution are independent gates.

## 9. Verify And Publish The Final Main Result

Reopen `<asset_id>_generation_prompt.md` and `<asset_id>_4k_enhancement_prompt.md` as their original bytes, recompute both hashes, and require exact equality with the recorded values. Reverify the reference manifest, worker-result JSON, board hash, inspection JSON, and 4K handoff. A missing sidecar or hash mismatch is `blocked_prompt_pair_integrity`. Never reconstruct either prompt from chat, memory, a summary, or YAML.

Preflight final-response capacity. If one final response cannot contain the generated board plus both complete prompts and hashes, return `blocked_final_output_capacity`; do not truncate, abbreviate, summarize, link-only, or split the pair while claiming publication.

Run `scripts/build_final_result.py` with the board, both prompt sidecars, worker result, inspection record, reference manifest, and 4K handoff. It must write `<asset_id>_final_main_result.md` in the run directory and return matching board/prompt/output hashes. Reopen that payload as UTF-8/LF bytes; use it verbatim as the `final` response. If the UI response cannot equal the payload, block publication.

Before `final`, persist `task_finalization_status: prompt_pair_ready`. Then publish the run-scoped board and this complete inline block in the task's non-empty final main result:

```text
![Single-Face Character Lock Board](<absolute run image path>)

final_generation_prompt:
<complete exact text reread from the generation sidecar>

generation_prompt_sha256: <verified sha256>

final_4k_enhancement_prompt:
<complete exact image-specific text reread from the 4K sidecar>

4k_enhancement_prompt_sha256: <verified sha256>

main_result_prompt_pair_status: published
task_finalization_status: final_main_result_published
```

Commentary, paths, sidecars, excerpts, summaries, or hashes alone cannot substitute for either complete prompt body. The final response is the publication transition evidence; call no tool afterward.

## 10. Completion Contract

The Skill completes only when:

- one identity is resolved;
- the frozen generation prompt exactly matches the worker tool prompt;
- the worker result is uniquely bound and copied into the run directory;
- the main agent has inspected the actual board;
- the image-specific 4K prompt and handoff sidecars exist;
- the inspection JSON binds an accepted visual review to the worker-bound board;
- both sidecar hashes pass byte verification;
- `<asset_id>_final_main_result.md` is built from the verified artifacts and is used verbatim;
- the non-empty final main result displays the board and both complete prompts with both hashes;
- `main_result_prompt_pair_status: published` and `task_finalization_status: final_main_result_published` appear in that final result.

A main-agent terminal imagegen call, an assumed future continuation, an image-only result, commentary-only prompt disclosure, an empty final, ambiguous newest-file selection, a prompt mismatch, an uninspected board, prompt reconstruction, or a missing 4K sidecar is failure.

For maintained red/green scenarios, read [test_cases.md](test_cases.md).

## Optional AI-Video Project Canon Export

This is a downstream-only branch. It never changes the exactly-one-face
three-component topology, terminal image call, later inspection, 4K handoff, or
complete prompt-pair publication. Start it only when the accepted board has
`assistant_qa_status: passed`, both prompt sidecars pass byte/hash readback, and
production approval is explicitly `user_granted` or
`external_pipeline_granted`.

After that grant, this owner writes strict approval evidence under
`../ai-video-shot-script-director/references/ai_video_owner_asset_approval.schema.json`,
binding the fixed owner, asset key, primary board hash, exact
`generation_prompt` and `four_k_enhancement_prompt` hashes, affected canonical
Shot UIDs, QA pass, and decision. Run only
`scripts/export_ai_video_canon.py`; it has no owner override and accepts only
project-relative locked files. The fixed authority mode is
`identity_and_wardrobe`, with exactly `[identity, wardrobe]` as authorized
control roles; the approval file must bind both.
Pillow is required for this optional export and must both verify and fully load
the primary PNG/JPEG/WebP board at 64×64 or larger. Decoder absence, corrupt
pixels, or an extension mismatch fails closed before Canon changes.

The wrapper creates the real owner `ai-video-artifact-v1` record, primary and
record four-lock Canon evidence, immutable base snapshot, entry delta, receipt,
and validated pre/post transition. Prompt Director may consume this entry but
may not synthesize or relabel its owner. Failure changes no visual asset state.

This is one terminal character alternative. Approval and export records must
bind `authority_stage: terminal_character_canon` and
`terminal_route_decision: single_face_character`. For one `asset_key`, it is
mutually exclusive with terminal casting and `character-final-lock-board`; a
cross-owner replacement is forbidden. Install the pinned decoder with
`python3 -m pip install -r ../ai-video-shot-script-director/requirements.txt`.
