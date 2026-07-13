---
name: material-sensitive-product-master-asset-board
description: "Use when supplied references show one transparent, glass, acrylic, translucent, liquid, cream, crystal-cut, mirror-metal, high-reflective, frosted, or multi-layer product whose video consistency depends on material behavior. Freeze the exact generation prompt, delegate each terminal built-in image call to exactly one non-decision image worker, bind and inspect the worker's actual one-board result, then publish the complete generation and image-specific 4K prompt pair with both SHA-256 values in the same task's final main result. Preserve material/structure evidence, optional label micro-reference, and at most one source-supported state window. Do not use for low-risk six-view products, label-copy-first packaging, mechanisms, scenes, characters, posters, or prompt-only output."
---

# Material-Sensitive Product Master Asset Board

Chinese name: 特殊材质产品总资产板

`asset_board_contract_version: delegated_image_worker_prompt_pair_v3`

Generate exactly one high-density, low-redundancy material master board. The deliverable is one master board, not a multi-board package. A prompt-only workflow is outside this Skill. Product and material truth outrank visual showmanship.

The main agent owns applicability, source truth, material interpretation, prompt bytes, visual QA, repair decisions, accepted-attempt selection, production approval separation, and the final main result. Exactly one non-decision image worker owns each terminal built-in imagegen call. This separation lets the worker end at imagegen while the main agent remains active, binds the actual board, inspects it, and publishes both complete prompts without a second user message.

## 1. Input And Applicability Gate

Require at least one usable product reference. Study every supplied image and record:

- `identity_risk`: silhouette, proportions, inner/outer relationship, deformable global form;
- `material_risk`: transparency, translucency, glass, acrylic, mirror metal, high reflection, frosting, liquid, cream, gel, crystal, refraction, or mixed finish;
- `structure_risk`: seam, latch, cap, pump, spray head, tube, liner, base, bottom refraction, edge thickness, small mark, connector, or cosmetic hinge;
- `label_risk`: logo, brand, product name, capacity, key copy, and position;
- `state_risk`: open/closed, cap off/on, content exposed, split component, use state, or half-open transition.

Classify every useful fact as `verified`, `inferred`, or `needs_source`. Keep one source-supported product variant; never merge conflicting variants.

Use this Skill when material behavior is the dominant continuity risk. Route simple opaque low-risk products to `multi-angle-product-identity-lock-board`; exact-copy-first packaging to `packaging-product-identity-label-lock-board`; mechanical topology, folding, or multi-state engineering to a dedicated workflow; and scenes, characters, posters, lifestyle images, or prompt-only requests outside this Skill.

If label and material risks are both high, use a main-agent compound workflow; neither Skill may claim complete coverage alone. Missing usable product references return `blocked_missing_product_reference`.

Completion criterion: one product identity and its material/structure evidence are sufficiently source-bound to plan one truthful board.

## 2. Freeze The One-Board Contract

Request exactly one text-free horizontal 16:9 master board on white or light neutral gray with restrained studio shadows and crisp edges. Use a `panel_capacity_budget` of 7-10 functional panels only while every risk-bearing panel remains legible. Set `panel_legibility_status: unverified` until actual-board inspection.

### Primary Anchor Zone

Make one complete front or 3/4 hero the largest zone. Preserve silhouette, proportions, color distribution, material layering, cap/body relationship, and visible label/logo position. The hero must stand alone as the downstream identity reference.

### Multi-Angle Zone

Use only 3-4 complementary views selected from front, 3/4, side, top, bottom, and back. Every view adds spatial evidence; near-duplicate angles are not valid panels.

### Material Response Zone

Use source-supported contextual closeups for transparent shell thickness, glass edge refraction, crystal facets, mirror-metal highlight boundary, glossy/frosted/matte separation, liquid, cream, gel, powder, or balm texture, inner/outer layer depth and fill boundary, bottom refraction, seam, latch, cap mouth, pump, tube, liner, hinge, embossing, foil, or material-dependent mark. Every closeup remains recognizable as the same product rather than generic material art.

### Critical Structure Zone

Show each failure-prone seam, cap/body join, neck, rim, pump, spray assembly, hinge, latch, base ring, liner, tube, small mark, or content boundary once with enough context to locate it.

### Optional Label / Logo Zone

Use one small reference-like zone only when logo, product name, capacity, embossing, foil, or label position contributes to material identity. Preserve layout before microcopy. Exact readable text routes to the packaging Skill.

### Optional State Window

Use at most one state window only when the exact state and its interfaces are visible in a source. Set `state_window_status: source_supported`, `omitted_needs_source`, or `omitted_not_needed`. Never infer a hidden open, split, or content-exposed state.

Inside the board use no title, headings, labels, view names, numbers, arrows, legends, measurements, captions, prompt text, UI, watermark, added logo, people, hands, props, scenery, packaging, or marketing typography.

Set:

```yaml
built_in_prompt_aspect_ratio_request: "horizontal 16:9"
built_in_prompt_alternate_aspect_ratios_allowed: false
built_in_dimensions_policy: evidence_only_nonblocking
```

Returned dimensions are observations. A `1672x941`, `1536x1024`, or other built-in raster can remain `codex_board_role: content_qa_reference`; dimensions alone cannot fail material/content QA, trigger repair, block finalization, or block the external handoff.

Completion criterion: every planned panel has one evidence job and the one-board topology is source-supported.

## 3. Pass The Automatic Runtime Gate

Before composing a production prompt, verify:

- the current request explicitly invokes this Skill or separately authorizes its non-decision image worker;
- the main agent can create and wait for one isolated subagent;
- one collaboration slot is available or can be freed safely;
- the worker can call built-in imagegen with local references;
- the main agent can read the Codex state DB, worker rollout, `$CODEX_HOME/generated_images`, and generated PNG;
- the exact current `parent_thread_id` is available;
- every authoritative reference has a readable local path that can be frozen into the run directory;
- `scripts/freeze_reference_bundle.py`, `scripts/resolve_worker_image.py`, and `scripts/build_final_result.py` are readable and executable;
- the run directory is writable and rereadable;
- the main agent can inspect a local image and emit a non-empty `final` response.

An implicit trigger without separate worker authorization returns `blocked_worker_authorization`. A missing parent identity returns `blocked_parent_thread_identity`; an unmaterializable reference returns `blocked_reference_materialization`. Any other failed gate returns `blocked_automatic_prompt_pair_runtime` before generation.

This branch is proven for local Codex Desktop, not every host. The main agent must not call imagegen as a fallback and must not promise an untriggered host continuation.

Capture `runtime_capability_snapshot` with collaboration, authorization, worker capacity, imagegen, local reference transport, state/rollout access, image inspection, explicit ratio/size controls, hashing, and output capacity. Record unknown values as `unknown`.

Completion criterion: every automatic-runtime dependency is observed available before any generation attempt.

## 4. Freeze Source And Prompt Truth

Use the active project's output directory when one exists; otherwise use `outputs/material-locks/<asset_id>/`. Use:

```text
<run>/
  run-state.yaml
  sources/reference-manifest.json
  sources/references/<ordered frozen files>
  attempts/01/<asset_id>_01_generation_prompt.md
  attempts/01/worker_spawn.json
  attempts/01/worker_result.json
  attempts/01/board.png
  attempts/01/qa.json
  attempts/01/<asset_id>_01_4k_enhancement_prompt.md
  attempts/01/<asset_id>_01_4k_handoff.yaml
  attempts/02/...
  attempts/03/...
  accepted_attempt.json
  <asset_id>_final_main_result.md
```

Run `scripts/freeze_reference_bundle.py` with each unique authoritative product, material macro, label micro-reference, and source-supported state file in semantic order. Freeze schema `material_reference_bundle.v1` with one-based index, unique alias, absolute run-scoped path, byte size, per-file SHA-256, and ordered-bundle SHA-256. Bind multiple source roles to one alias rather than duplicate a file. Worker and resolver use only these frozen copies.

For each attempt:

1. Build the complete public English `final_generation_prompt` from the frozen source ledger and one-board plan.
2. Normalize UTF-8 bytes with LF line endings and no BOM.
3. Save exactly those bytes as `attempts/<attempt_id>/<asset_id>_<attempt_id>_generation_prompt.md`, reopen the file, require byte equality, and calculate `generation_prompt_sha256` from reread bytes.
4. Keep `final_4k_enhancement_prompt` unset. A private `draft_4k_enhancement_prompt` may contain invariant material constraints, but it is not deliverable and has no final hash.
5. Create `worker_spawn.json` with `attempt_id`, exact `parent_thread_id`, prompt hash, reference-manifest hash, and pre-spawn state.

Use:

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

The generation sidecar is the single source of truth. Commentary, chat memory, YAML, a shell-command result, reconstruction, or summary cannot replace its exact bytes. Persistence failure returns `blocked_generation_prompt_persistence`.

Completion criterion: frozen source bytes and attempt prompt bytes are reread and hash-locked before spawn.

## 5. Delegate One Terminal Image Worker

Generate a cryptographically random 32-character lowercase hexadecimal `worker_run_nonce`. Record `worker_spawn_not_before_ms` immediately before spawn. Create a fresh unique task such as `material_image_<asset_id>_<attempt_id>_<nonce_prefix>` and preserve the canonical agent path returned by `spawn_agent`.

Give the worker only this execution contract:

- execute only the already-frozen built-in image call; the main agent owns the applicable Skill instructions;
- include `worker_run_nonce: <32hex>` in its task body and repeat the same value as the exact first exec-source line `const worker_run_nonce = "<32hex>";`;
- submit the complete frozen prompt without changing one character;
- attach the exact ordered frozen paths from `sources/reference-manifest.json`;
- pass `prompt` as one JSON double-quoted string literal and `referenced_image_paths` as one ordered JSON string-array literal;
- call imagegen exactly once, with only resolver-linked waits for that same yielded call if it is asynchronous;
- make no applicability, source, material, creative, QA, repair, approval, or publication decision;
- finish after imagegen with no text and no unrelated tool call.

Use `fork_turns="none"`; include the full prompt, ordered frozen paths, attempt ID, hashes, and nonce in the task message. The main agent remains the active finalizer and waits. An empty worker final is expected and is not the deliverable.

Completion criterion: exactly one fresh non-decision worker owns the attempt's only imagegen call.

## 6. Bind The Exact Worker Result

After worker completion, run:

```text
python scripts/resolve_worker_image.py
  --agent-path <canonical worker path>
  --not-before-ms <worker_spawn_not_before_ms>
  --parent-thread-id <exact parent thread id>
  --worker-run-nonce <32 lowercase hex>
  --expected-prompt attempts/<attempt_id>/<asset_id>_<attempt_id>_generation_prompt.md
  --reference-manifest sources/reference-manifest.json
  --copy-to attempts/<attempt_id>/board.png
  --result-json attempts/<attempt_id>/worker_result.json
```

The resolver must prove:

- exactly one fresh worker thread matches agent path, checkpoint, and parent;
- leading rollout metadata equals worker thread, agent path, and parent;
- the imagegen exec source contains exactly one literal declaration of the exact nonce, so encrypted task-envelope storage does not weaken binding;
- the worker makes exactly one imagegen exec call and no other tool call except resolver-linked waits for that same yielded image cell;
- exactly one completed `image_generation_end` follows that call;
- both worker final records are empty and no post-image tool call exists;
- imagegen prompt bytes equal the frozen generation sidecar;
- ordered reference paths equal the manifest and every frozen source hash remains unchanged;
- `worker_thread_id + image_generation_call_id` maps to `$CODEX_HOME/generated_images/<worker-thread-id>/<call-id>.png`;
- PNG signature, dimensions, copied bytes, and SHA-256 are valid.

Newest-file guessing is invalid. Any ambiguity or mismatch returns an exact `blocked_worker_*` code and leaves publication pending. Do not regenerate merely because provenance binding failed.

On success set:

```yaml
image_worker_status: bound
terminal_generation_call: worker_executed
task_finalization_status: worker_result_bound
4k_enhancement_prompt_status: awaiting_post_generation_inspection
codex_board_role: content_qa_reference
```

Completion criterion: one run-scoped PNG and worker-result JSON are cryptographically bound to one attempt.

## 7. Inspect The Actual Board And Select An Attempt

Open `attempts/<attempt_id>/board.png` with the image-inspection tool. Persist `qa.json` containing `inspected: true`, absolute board path, image SHA-256, `observed_pixel_dimensions`, observed ratio, worker thread ID, image call ID, source-fidelity status, panel findings, observed defects, and `assistant_qa_status`.

Require `primary_anchor_clear`, `multi_angle_complementary`, `material_evidence_present`, `material_source_consistent` or honestly `unverified`, `critical_structure_useful` or `not_needed`, `low_redundancy`, `panel_legibility_status`, `single_board_contract`, `no_poster_pollution`, `video_reference_ready`, `state_window_source_supported: pass | fail | not_used`, and `prompt_bound`.

Check transparent layers and thickness, glass/acrylic refraction, fill level and content boundaries, crystal facets, mirror/reflection boundaries, matte/gloss/frosted separation, microbubbles or grain, seams, caps, pumps, tubes, liners, bases, marks, and consistent highlight direction where source-supported.

Set `assistant_qa_status: passed` only when observable gates pass, `conditional` for a useful source-limited board, and `failed` for critical identity, material, structure, legibility, source-state, prompt-binding, or one-board failure. Keep production approval limited to `not_granted`, `user_granted`, or `external_pipeline_granted`.

Allow at most two focused repair generations after the initial attempt. Repair one dominant issue in this order: pollution, primary anchor, redundancy, material response, critical structure, source-supported label detail. Every repair gets a fresh attempt directory, prompt bytes/hash, nonce, worker, call ID, board, worker result, and QA record. At most one worker may be active per attempt.

Freeze exactly one `accepted_attempt.json` with schema `material_accepted_attempt.v1`, accepted `attempt_id`, generation-prompt path/hash, worker-result path/hash, board path/hash, inspection path/hash, 4K-prompt path/hash, and handoff path/hash. Final publication uses only this accepted attempt. If attempt 03 still fails, reject and request the exact missing source evidence.

Completion criterion: exactly one inspected attempt is accepted without overwriting failed evidence.

## 8. Create The Image-Specific External 4K Handoff

Only after accepted-board inspection, freeze `final_4k_enhancement_prompt`. Use both the inspected `codex_asset_board` and all authoritative `original_source_references`.

Name only observed defects. Preserve board topology, dominant hero, complementary views, material/structure crops, optional label zone, optional state window, and neutral studio presentation. Preserve source-supported refraction/reflection boundaries, transparent/translucent layer relationship and edge thickness, fill level and content state, crystal facets, frosted/matte/gloss separation, seams, caps, bases, pumps, liners, tubes, marks, highlight direction, controlled grain, microbubbles, fine seams, and surface transitions.

Apply local cleanup only to observed generation artifacts. Preserve unresolved structure as unresolved. Request one exact 16:9 result at the selected provider's real 4K tier with no crop, stretch, reframing, panel reorder, added panel, advertising treatment, or non-product-native text.

Save exact UTF-8/LF bytes inside the accepted attempt as `<asset_id>_<attempt_id>_4k_enhancement_prompt.md`, reopen them, and calculate `4k_enhancement_prompt_sha256`. Save `<asset_id>_<attempt_id>_4k_handoff.yaml` beside it with:

```yaml
4k_enhancement_prompt_status: finalized_post_inspection
third_party_model_target: nano_banana_pro | nano_banana_2 | model_agnostic
codex_board_role: content_qa_reference
external_reference_bundle:
  codex_asset_board: <accepted board>
  original_source_references: <all authoritative frozen references>
source_fidelity_status: pending | passed | failed | unverified | blocked_missing_original_sources
external_runtime_request:
  aspect_ratio: "16:9"
  image_size: "4K"
  alternate_aspect_ratios_allowed: false
external_4k_status: not_ready | handoff_ready | blocked_runtime_controls | pending_external_generation | returned_unverified | verified | rejected
external_4k_qa_status: pending | passed | failed
```

`prompt_pair_ready` does not imply `external_4k_status: handoff_ready`; publication and external execution are independent gates. Missing exact controls returns `blocked_runtime_controls`.

For an external return record provider, surface, model profile, requested settings, `observed_pixel_dimensions`, `provider_declared_aspect_ratio_profile`, `observed_file_aspect_ratio`, `aspect_ratio_evidence`, and `four_k_evidence`. External QA requires `material_boundaries_preserved`, `transparent_layers_and_thickness_preserved`, `fill_level_and_content_state_preserved`, `reflection_refraction_highlights_source_consistent`, `no_over_denoising`, `no_invented_structure_or_material`, `external_reference_bundle_complete`, `external_16_9_verified`, and `external_4k_profile_verified`.

Completion criterion: the image-specific prompt and handoff bind the accepted board and original material evidence without inventing detail.

## 9. Output: Publish One Complete Final Main Result

Use only:

```text
task_finalization_status: worker_generation_pending | worker_result_bound | prompt_pair_ready | final_main_result_published
main_result_prompt_pair_status: pending | published
```

Reopen the accepted attempt's generation sidecar and the final 4K sidecar as their original bytes. Recompute both hashes and require equality. A missing file or hash mismatch returns `blocked_prompt_pair_integrity`; never reconstruct either prompt from chat, memory, YAML, commentary, or summaries.

Run `scripts/build_final_result.py` with the run directory, `accepted_attempt.json`, accepted board/prompt/worker/inspection artifacts, reference manifest, 4K prompt, and handoff. The builder validates run-scoped paths and hashes before writing `<asset_id>_final_main_result.md`.

Set `task_finalization_status: prompt_pair_ready` only after the builder succeeds. Reopen the payload as UTF-8/LF and emit its exact complete contents as one non-empty `final` response:

```text
![Material-Sensitive Product Master Asset Board](<absolute accepted board path>)

final_generation_prompt:
<complete exact accepted generation sidecar>
generation_prompt_sha256: <verified sha256>

final_4k_enhancement_prompt:
<complete exact image-specific 4K sidecar>
4k_enhancement_prompt_sha256: <verified sha256>

main_result_prompt_pair_status: published
task_finalization_status: final_main_result_published
```

Also include concise QA, observed dimensions, worker/thread/call binding, external handoff status, and production approval. A sidecar path, earlier commentary, excerpt, summary, or hash alone cannot substitute for either complete prompt. If one response cannot hold both prompt bodies, return `blocked_final_output_capacity` without truncating, abbreviating, splitting, or claiming publication.

The final response is the publication transition evidence; require no state mutation or tool call afterward.

Completion criterion: the displayed final response exactly contains the accepted board, both complete prompt bodies, both verified hashes, and both published states.

## 10. End Condition

Complete only when source bytes, prompt bytes, worker trace, accepted board, visual inspection, 4K handoff, final payload, and displayed final response form one unbroken evidence chain. A main-agent imagegen call, implicit worker use, assumed future continuation, image-only result, shell-wrapper prompt mismatch, unrelated worker tool call, empty final, ambiguous newest-image selection, uninspected board, overwritten attempt, reconstructed prompt, missing sidecar, or incomplete final payload is failure.

For maintained red/green scenarios, read [test_cases.md](test_cases.md).

## Optional AI-Video Project Canon Export

This optional downstream step never changes the one-master-board rule,
material/source gates, generation, inspection, external 4K classification, or
complete prompt-pair publication. It is legal only after assistant QA passes,
the `generation_prompt` and `four_k_enhancement_prompt` files pass exact
readback, and production approval is explicitly `user_granted` or
`external_pipeline_granted`.

The owner records that decision under
`../ai-video-shot-script-director/references/ai_video_owner_asset_approval.schema.json`,
binding this fixed owner, asset key, primary board hash, both prompt hashes,
affected canonical Shot UIDs, QA pass, and decision. Use only
`scripts/export_ai_video_canon.py` with project-relative locators and hashes;
the wrapper accepts no owner override. Its fixed authority mode is
`geometry_and_material`, authorizing exactly
`[product_geometry, material_behavior]`; it never grants `label_copy`.
Pillow must be available for the optional export and must verify and fully load
the primary PNG/JPEG/WebP master board at 64×64 or larger. A missing decoder,
corrupt image, arbitrary blob, or extension mismatch fails before Canon writes.

Success writes the true owner `ai-video-artifact-v1` record, binary-compatible
primary/record four locks, immutable base snapshot, entry delta, receipt, and
validated Canon transition. Prompt Director must preserve this material owner
and cannot manufacture a substitute projection. Export failure changes no
material QA or existing board state.

Approval and export records must also bind
`authority_stage: terminal_material_canon` and
`terminal_route_decision: not_applicable`. Install the pinned decoder with
`python3 -m pip install -r ../ai-video-shot-script-director/requirements.txt`.
