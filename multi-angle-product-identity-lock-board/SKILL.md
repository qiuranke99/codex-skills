---
name: multi-angle-product-identity-lock-board
description: "Use when the user provides references for one low-risk, mostly opaque product and needs one text-free six-view identity board. Freeze the exact generation prompt, delegate the terminal built-in image call to exactly one non-decision image worker, bind and inspect that worker's actual board, then publish the complete generation and image-specific 4K prompt pair with both SHA-256 values in the same task's final main result. Use for clear silhouettes, simple construction, and non-critical text; route label-heavy packaging, material-sensitive glass/liquid/reflective products, mechanisms, state changes, advertising scenes, and prompt-only requests elsewhere."
---

# Multi-Angle Product Identity Lock Board

Chinese name: 多角度产品身份锁定板

`asset_board_contract_version: delegated_image_worker_prompt_pair_v3`

Generate exactly one clean 2x3 board containing six complete views of one low-risk product. Preserve product identity rather than redesigning it.

The main agent owns applicability, source truth, prompt bytes, visual QA, repair decisions, and the final main result. Exactly one non-decision image worker owns each terminal built-in imagegen call. This separation lets the worker end at imagegen while the main agent continues the same user task and publishes the board plus both prompts without a second user message.

## 1. Pass The Product Gate

Require at least one usable target-product image. Treat it as the identity authority; treat a sample board as layout evidence only.

Record each risk as `low`, `moderate`, or `high`:

- `geometry_risk`: silhouette, proportion, panels, openings, handles, straps, seams;
- `label_risk`: readable copy, logos, claims, marks;
- `material_risk`: transparency, liquid, glass, chrome, mirror, refraction, layered shells;
- `structure_risk`: joints, hinges, folding, moving parts, engineering interfaces;
- `state_risk`: open/closed, deployed/stored, assembled/split, worn/unused.

Classify applicability as:

- `suitable`: geometry is low and every other risk is low;
- `conditional`: geometry is manageable-moderate and every other risk is low;
- `not_suitable`: any high risk, identity conflict, or missing target image.

Route exact packaging copy to `packaging-product-identity-label-lock-board`; route identity-critical glass, transparency, liquid, cream, crystal, mirror metal, or high reflection to `material-sensitive-product-master-asset-board`; route mechanisms or multi-state engineering to a dedicated workflow. Stop before generation on `not_suitable`.

## 2. Freeze Source Truth And Board Topology

Record visible facts only: product type, silhouette, proportions, color placement, simple material finish, seams, edges, openings, panels, straps, handles, buttons, laces, texture direction, and markings.

Classify every required feature or view as:

- `source_verified`: clearly visible;
- `source_inferred`: plausible but not directly visible;
- `needs_source`: required but unavailable or contradictory.

Keep one source-supported product variant. Leave hidden unsupported structure unresolved.

Request one text-free horizontal 16:9 composition with exactly six complete non-redundant views:

1. front or primary view;
2. rear;
3. left profile;
4. right profile;
5. slight overhead top view, or underside when more informative;
6. 3/4 front hero view, or 3/4 rear when needed to avoid repetition.

Use a neutral white or light-gray seamless studio background, soft diffused light, subtle grounding shadows, consistent scale, generous margins, and no overlap. Preserve source-supported silhouette, proportions, colors, simple materials, construction, texture, and markings. Keep every panel free of non-product titles, labels, numbers, arrows, callouts, captions, watermarks, UI, props, people, scenes, and advertising treatment.

Set:

```yaml
built_in_prompt_aspect_ratio_request: "horizontal 16:9"
built_in_prompt_alternate_aspect_ratios_allowed: false
built_in_dimensions_policy: evidence_only_nonblocking
```

Returned dimensions are observations. Dimensions alone cannot fail QA, trigger repair, or block handoff or finalization. A `1672x941`, `1536x1024`, or other built-in raster can remain `codex_board_role: content_qa_reference` when content QA passes.

## 3. Pass The Automatic Runtime Gate

Before composing the production prompt, verify:

- the current request explicitly authorizes multi-agent execution or explicitly invokes this Skill whose declared contract includes one non-decision image worker;
- the main agent can create and wait for one isolated subagent;
- one collaboration slot is available or can be freed safely;
- the worker can call built-in imagegen with the required references;
- the main agent can read the local Codex state DB, worker rollout, `$CODEX_HOME/generated_images`, and generated PNG;
- `scripts/freeze_reference_bundle.py`, `scripts/freeze_prompt.py`, `scripts/resolve_worker_image.py`, and `scripts/build_final_result.py` are readable and executable;
- the run directory can be written and reread;
- the main agent can inspect a local image and emit a non-empty final response.

An implicit Skill trigger without separate worker authorization does not pass the first gate. This delegated branch is proven for local Codex Desktop, not every host. If any gate fails, return `blocked_automatic_prompt_pair_runtime` before generation. The main agent must not call imagegen as a fallback and must not promise an untriggered host continuation.

Capture `runtime_capability_snapshot` with collaboration, imagegen, reference transport, state/rollout access, image inspection, explicit ratio/size controls, and output capacity. Record unknown values as `unknown`.

## 4. Freeze Prompt Truth

Use the active project's output directory when one exists; otherwise use `outputs/product-locks/<asset_id>/`. Use this run structure:

```text
<run>/
  run-state.yaml
  sources/reference-manifest.json
  sources/references/<ordered frozen reference files>
  attempts/01/<asset_id>_01_generation_prompt.md
  attempts/01/worker_spawn.json
  attempts/01/worker_result.json
  attempts/01/board.png
  attempts/01/qa.yaml
  attempts/02/...
  accepted_attempt.json
  <asset_id>_4k_enhancement_prompt.md
  <asset_id>_4k_handoff.yaml
```

Materialize every unique authoritative source file into `sources/references/` before spawning. Run `scripts/freeze_reference_bundle.py` with source files in semantic order:

```text
python scripts/freeze_reference_bundle.py
  --run-dir <run>/sources
  --manifest <run>/sources/reference-manifest.json
  --reference <alias>=<source path> [repeat in order]
```

The script freezes UTF-8/LF schema `multi_angle_reference_bundle.v1` with one-based `index`, unique `alias`, absolute run-scoped `frozen_path`, `size_bytes`, SHA-256, and `ordered_bundle_sha256`. Preserve source order and bind multiple semantic roles to one alias; reject duplicate source files. If any required reference cannot be materialized locally, return `blocked_reference_materialization` before generation.

Before spawning the worker:

1. Build one public English `final_generation_prompt` from the source map and fixed six-view topology.
2. Canonicalize it as UTF-8 without BOM, LF for internal line endings, and no terminal line break. Use `scripts/freeze_prompt.py`; this is the exact JSON-string payload the worker must submit.
3. Save exactly those bytes as `attempts/<attempt_id>/<asset_id>_<attempt_id>_generation_prompt.md`, reopen the file, require byte equality, and calculate `generation_prompt_sha256` from the reread bytes.
4. Expose the complete prompt in `prompt_record`; set `english_prompt_used` as a byte-identical compatibility alias.
5. Keep `final_4k_enhancement_prompt` unset. A private `draft_4k_enhancement_prompt` may contain invariant topology and fidelity constraints, but it is not deliverable and has no final hash.
6. Create or update the run record before spawning.

Use these pre-worker states:

```yaml
image_worker_status: not_started
terminal_generation_call: worker_pending
assistant_qa_status: pending_post_generation_inspection
production_approval_status: not_granted
4k_enhancement_prompt_status: draft_pre_generation
task_finalization_status: worker_generation_pending
main_result_prompt_pair_status: pending
external_4k_status: not_ready
```

The generation sidecar is the single source of truth. A missing, unreadable, BOM/CRLF-contaminated, terminal-line-break-bearing, or mismatched sidecar returns `blocked_generation_prompt_persistence`.

## 5. Delegate One Terminal Image Worker

Create a cryptographically random `worker_run_nonce` of exactly 32 lowercase hexadecimal characters. Immediately before spawning, record `worker_spawn_not_before_ms`, exact `parent_thread_id`, `attempt_id`, and the nonce. Create a fresh unique task name such as `multi_angle_image_<normalized_asset_id>_<attempt_id>_<full_32hex_nonce>`; the canonical agent path must end with the full nonce. Record the exact path returned by `spawn_agent`.

Give the worker the minimum complete execution contract:

- use the available imagegen Skill and built-in image tool;
- submit the exact frozen prompt without changing one character;
- attach every frozen reference through the exact ordered `referenced_image_paths` list from the manifest;
- pass `prompt` as one JSON double-quoted string literal and references as one JSON string-array literal;
- call imagegen exactly once;
- make no applicability, source, creative, QA, repair, approval, or publication decision;
- end after imagegen with no text and no unrelated tool call.

Use `fork_turns="none"` and include the complete prompt, exact ordered frozen paths, SHA-256 values, attempt ID, and full nonce in the worker task. The resolver verifies the nonce from the unencrypted canonical agent path because the inter-agent task payload may be encrypted in the rollout.

The main agent remains the active finalizer and waits for the worker to complete. An empty worker final is expected. A repair uses a new frozen attempt prompt and a fresh uniquely named worker.

## 6. Bind The Exact Worker Result

After worker completion, run the bundled resolver with the recorded checkpoint, exact canonical worker path, frozen prompt sidecar, reference contract, run-scoped image destination, and result-record path. Include the exact parent thread ID when available.

```text
python scripts/resolve_worker_image.py
  --agent-path <canonical worker path>
  --not-before-ms <checkpoint>
  --parent-thread-id <exact parent thread id>
  --worker-run-nonce <32 lowercase hex>
  --expected-prompt attempts/<attempt_id>/<asset_id>_<attempt_id>_generation_prompt.md
  --reference-manifest sources/reference-manifest.json
  --copy-to attempts/<attempt_id>/board.png
  --result-json attempts/<attempt_id>/worker_result.json
```

The resolver must prove:

- exactly one fresh worker thread matches the exact agent path and checkpoint;
- rollout session ID equals worker thread ID;
- exactly one imagegen call and one completed `image_generation_end` exist;
- the imagegen prompt bytes equal the frozen sidecar;
- the exact ordered reference transport equals the frozen manifest and every frozen source byte/hash remains unchanged;
- the worker has one task/turn, its canonical path ends with the exact nonce, it emits an empty final, and it makes no post-image tool call;
- `worker_thread_id + image_generation_call_id` maps to `$CODEX_HOME/generated_images/<worker-thread-id>/<call-id>.png`;
- PNG signature, dimensions, copied bytes, and SHA-256 are valid.

Selecting the newest image by timestamp is invalid. Resolver failure returns its exact `blocked_worker_*` code and keeps publication pending.

On success, set:

```yaml
image_worker_status: bound
terminal_generation_call: worker_executed
task_finalization_status: worker_result_bound
4k_enhancement_prompt_status: awaiting_post_generation_inspection
codex_board_role: content_qa_reference
```

## 7. Inspect The Actual Board

Open the run-scoped copied PNG with the available image-inspection tool. Record the source path, `observed_pixel_dimensions`, observed ratio, exact-16:9 boolean, image SHA-256, worker thread ID, and image-generation call ID.

Classify:

- `six_views_present`: pass / fail;
- `views_distinct`: pass / fail;
- `complete_uncropped_views`: pass / fail;
- `identity_source_consistent`: pass / fail / unverified;
- `geometry_source_consistent`: pass / fail / unverified;
- `color_material_source_consistent`: pass / fail / unverified;
- `no_invented_structure`: pass / fail / unverified;
- `no_non_product_text_pollution`: pass / fail;
- `prompt_bound`: pass / fail.

Set `assistant_qa_status: passed` when every observable gate passes, `conditional` for a useful source-limited board, and `failed` for critical identity/topology failure. Keep `production_approval_status: not_granted` unless the user or external pipeline explicitly grants approval.

At most two focused repair generations are allowed when a new prompt can plausibly close one dominant failure. Every repair gets a new attempt directory, prompt sidecar, hash, nonce, worker, call ID, board, result record, and QA record. Preserve failed attempts without overwriting them. Freeze `accepted_attempt.json` with schema `multi_angle_accepted_attempt.v1`, one accepted `attempt_id`, the exact generation-prompt/board/worker-result/inspection paths, `generation_prompt_sha256`, and `image_sha256`. Final publication uses only that accepted attempt. Reject the board when the second repair cannot close the failure.

## 8. Keep Native 4K Optional

Keep `native_4k_branch: off`; Codex-native 4K is an explicit opt-in branch separate from the external 4K handoff. Activate it only when the user explicitly requests Codex-native 4K. When activated, separate:

- `target_native_resolution`;
- `observed_pixel_dimensions`;
- `native_provenance`.

Use `resolution_approved`, `resolution_not_approved`, or `resolution_unverified`. Set `native_4k_claim: true` only when the original generated artifact is verified at 3840x2160 or higher, remains horizontal 16:9, and native provenance excludes resize or export enlargement. Prompt wording and filenames are not provenance.

This optional branch never changes the default content-QA or external-handoff contract.

## 9. Post-inspection external 4K handoff

Only after inspecting the bound board, freeze `final_4k_enhancement_prompt`. Use both the inspected Codex board and every authoritative original reference.

Name observed panel-level defects and preserve the same 2x3 topology, view assignments, complete products, spacing, silhouette, proportions, panels, openings, seams, straps, handles, interfaces, texture direction, colors, simple material finish, and markings. Request one exact 16:9 result at the selected provider's real 4K tier. Preserve unsupported details as unresolved rather than inventing geometry, copy, or marks.

Canonicalize the exact prompt bytes with `scripts/freeze_prompt.py` as `<asset_id>_4k_enhancement_prompt.md`, reopen them, and calculate `4k_enhancement_prompt_sha256`. The enhancement sidecar follows the same UTF-8/no-BOM, internal-LF, no-terminal-line-break transport contract. Save `<asset_id>_4k_handoff.yaml` with:

```yaml
4k_enhancement_prompt_status: finalized_post_inspection
third_party_model_target: nano_banana_pro | nano_banana_2 | model_agnostic
codex_board_role: content_qa_reference
external_reference_bundle:
  codex_asset_board: <bound run image>
  original_source_references: <all authoritative references>
source_fidelity_status: pending | passed | failed | unverified | blocked_missing_original_sources
external_runtime_request:
  aspect_ratio: "16:9"
  image_size: "4K"
  alternate_aspect_ratios_allowed: false
external_4k_status: not_ready | handoff_ready | blocked_runtime_controls | pending_external_generation | returned_unverified | verified | rejected
external_4k_qa_status: pending | passed | failed
```

Use `handoff_ready` only when the prompt is hashed and every reference resolves. If the provider lacks exact 16:9 and 4K controls, set `blocked_runtime_controls`.

External QA must include `six_view_geometry_preserved`, `interfaces_and_seams_preserved`, `no_new_product_detail`, `external_reference_bundle_complete`, `external_16_9_verified`, and `external_4k_profile_verified`. External enhancement never becomes Codex-native-4K evidence.

For every returned external artifact, record provider, model, surface, model profile, requested settings, `observed_pixel_dimensions`, `provider_declared_aspect_ratio_profile`, `observed_file_aspect_ratio`, `aspect_ratio_evidence`, and `four_k_evidence` before external verification.

## 10. Publish One Complete Final Main Result

Use only:

```text
task_finalization_status: worker_generation_pending | worker_result_bound | prompt_pair_ready | final_main_result_published
main_result_prompt_pair_status: pending | published
```

Before publication, reopen the accepted `<asset_id>_<attempt_id>_generation_prompt.md`, recompute `generation_prompt_sha256`, reopen `<asset_id>_4k_enhancement_prompt.md`, recompute `4k_enhancement_prompt_sha256`, and require exact UTF-8 byte equality. A missing sidecar, byte mismatch, or hash mismatch returns `blocked_prompt_pair_integrity`; preserve the accepted board's original prompt truth. Do not reconstruct either prompt.

Run `scripts/build_final_result.py` with the run directory, accepted-attempt record, accepted board/prompt/worker/inspection artifacts, reference manifest, image-specific 4K prompt, and handoff. The builder must validate their paths and hashes before writing `<run>/final_main_result.md`:

```text
python scripts/build_final_result.py
  --run-dir <run>
  --accepted-attempt <run>/accepted_attempt.json
  --board <run>/attempts/<accepted>/board.png
  --generation-prompt <run>/attempts/<accepted>/<asset_id>_<accepted>_generation_prompt.md
  --enhancement-prompt <run>/<asset_id>_4k_enhancement_prompt.md
  --worker-result <run>/attempts/<accepted>/worker_result.json
  --inspection <run>/attempts/<accepted>/qa.json
  --reference-manifest <run>/sources/reference-manifest.json
  --handoff <run>/<asset_id>_4k_handoff.yaml
  --output <run>/final_main_result.md
```

Set `prompt_pair_ready` only after the builder succeeds. Reopen `final_main_result.md` and emit its complete exact contents as the one non-empty `final` response. The payload contains the bound board as a local absolute Markdown image plus this block:

```text
final_generation_prompt:
<complete exact generation sidecar bytes>
generation_prompt_sha256: <verified sha256>

final_4k_enhancement_prompt:
<complete exact image-specific enhancement sidecar bytes>
4k_enhancement_prompt_sha256: <verified sha256>

main_result_prompt_pair_status: published
task_finalization_status: final_main_result_published
```

Also report concise QA, observed dimensions, worker/thread/call binding, external handoff status, and production approval. A sidecar path, earlier commentary, excerpt, summary, or hash alone does not replace either complete prompt. If one response cannot hold both prompt bodies, return `blocked_final_output_capacity` without a published claim.

`prompt_pair_ready` proves prompt integrity and does not imply `external_4k_status: handoff_ready`. If output capacity is insufficient, do not truncate or abbreviate either prompt.

The emitted non-empty final response is the publication transition evidence; perform no required state mutation after it.

## End Condition

Complete only when the worker result is unambiguously bound, the actual board is visually classified, both prompt sidecars pass reread hashing, and one final main result visibly contains the board, both complete prompts, both hashes, and both published states. A real source, authorization, capability, worker, persistence, integrity, or output-capacity blocker may end the run without a completion claim.

## Optional AI-Video Project Canon Export

This downstream branch does not change product routing, the six-view topology,
generation, later inspection, external 4K evidence, or final prompt-pair rules.
Use it only for an accepted product board with `assistant_qa_status: passed`,
verified `generation_prompt` and `four_k_enhancement_prompt` sidecar bytes, and
explicit `user_granted` or `external_pipeline_granted` production approval.

The owner records that decision using
`../ai-video-shot-script-director/references/ai_video_owner_asset_approval.schema.json`,
binding this fixed owner, asset key, primary board hash, both prompt hashes,
affected canonical Shot UIDs, QA pass, and approval. Then invoke only
`scripts/export_ai_video_canon.py` with project-relative paths and exact hashes;
there is no owner argument. This low-risk product owner exports only
`authority_mode: geometry_only` and
`control_roles_authorized: [product_geometry]`; it never grants label-copy or
material-behavior authority.
Pillow is required to verify and fully load the primary PNG/JPEG/WebP board and
lock decoder-observed dimensions of at least 64×64. Missing Pillow, arbitrary
binary bytes, or a format/extension mismatch fails closed before Canon update.

The wrapper emits the owner-produced `ai-video-artifact-v1` record, independent
primary/record four locks, base snapshot, entry delta, receipt, and validated
Canon transition. Prompt Director must retain this actual product owner in
feedback routing and cannot fabricate a projection. Export failure does not
change the approved board or its existing handoff.

Approval and export records must also bind
`authority_stage: terminal_product_canon` and
`terminal_route_decision: not_applicable`. Install the pinned decoder with
`python3 -m pip install -r ../ai-video-shot-script-director/requirements.txt`.
