---
name: multi-angle-product-identity-lock-board
description: Generate one six-view identity board for a low-risk, mostly opaque product from supplied references while requesting horizontal 16:9, then inspect it and publish one final main result containing the complete exact generation prompt and image-specific 4K enhancement prompt with both SHA-256 values. Use when silhouette, proportions, color, simple material, and non-text construction must stay consistent across common views; do not use for label-copy-first packaging, material-sensitive glass/liquid/reflective products, complex mechanisms, state changes, or advertising scenes. Treat external 4K as evidence-gated and Codex-native 4K as an explicit opt-in branch only.
---

# Multi-Angle Product Identity Lock Board

Contract version: `asset_board_contract_version: built_in_nonblocking_prompt_pair_v2`.

Chinese name: 多角度产品身份锁定板

Generate exactly one six-view reference board for a low-risk product. Preserve identity rather than redesigning it. The deliverable is a generated board, a traceable prompt record, an image-specific external 4K handoff, and one final-channel main result that visibly contains both complete prompts and both hashes. A prompt-only request routes outside this Skill and is not a successful run.

## Boundary and route gate

Require at least one usable target-product image. Treat it as the only identity source. A sample board may control layout only.

Before generation, record this risk vector as `low`, `moderate`, or `high`:

- `geometry_risk`: silhouette, proportion, panels, openings, handles, straps, seams;
- `label_risk`: amount and importance of readable text, logo, claims, marks;
- `material_risk`: transparency, liquid, glass, chrome, mirror, refraction, mixed shells;
- `structure_risk`: joints, hinges, folding, moving parts, engineering interfaces;
- `state_risk`: open/closed, deployed/stored, assembled/split, worn/unused.

Use this skill only when geometry is low or manageable-moderate and the other four risks are low. Route instead when:

- exact packaging copy, barcode, QR code, certification, or dense label text matters: use `packaging-product-identity-label-lock-board`;
- glass, transparency, liquid, cream, crystal, mirror metal, high reflection, refraction, or layered material is identity-critical: use `material-sensitive-product-master-asset-board`;
- mechanisms, engineering topology, or multiple states dominate: use a main-agent/custom-agent workflow unless a dedicated active skill exists;
- the user wants a poster, scene, campaign visual, redesign, or product concept: do not use a lock-board skill.

Classify applicability as:

- `suitable`: all route gates pass;
- `conditional`: a moderate risk can be bounded and disclosed;
- `not_suitable`: any high out-of-scope risk or missing target image.

Stop before generation when `not_suitable`. Never force six inferred views onto an evidence-poor or high-risk product.

## Source map

Extract only visible facts:

- product type and overall silhouette;
- proportions and primary/secondary color placement;
- opaque or simple material finish;
- seams, edges, openings, panels, handles, straps, buttons, laces, texture direction, and visible markings;
- which faces or details are supplied, hidden, cropped, blurred, or contradictory.

For each required feature or view, mark:

- `source_verified`: visible clearly enough to compare;
- `source_inferred`: plausible but not directly visible;
- `needs_source`: required for the user's purpose but unavailable or contradictory.

Do not merge variants. Do not invent hidden structure. If references conflict and no authoritative target can be identified, stop with `not_suitable: identity_conflict`.

## Runtime capability snapshot

Inspect the currently exposed image-generation interface before promising an output. Record only observed capabilities:

```text
runtime_capability_snapshot:
- image_generation_callable: supported / unsupported / unknown
- reference_images_attachable: supported / unsupported / unknown
- explicit_aspect_ratio_argument: supported / unsupported / unknown
- explicit_size_argument: supported / unsupported / unknown
- built_in_prompt_aspect_ratio_request: horizontal 16:9
- built_in_prompt_alternate_aspect_ratios_allowed: false
- requested_native_size: value / not_exposed
- returned_file_inspectable: supported / unsupported / unknown
- pixel_dimensions_inspectable: supported / unsupported / unknown
- native_provenance_inspectable: supported / unsupported / unknown
- post_generation_text_allowed_same_turn: supported / unsupported / unknown
```

Do not infer a capability from prompt wording. `Target 3840x2160` inside a prompt is a creative target, not proof that a native-size control exists.

If image generation or reference attachment is unavailable, report `blocked_capability` and do not substitute a prompt-only result. Set `built_in_dimensions_policy: evidence_only_nonblocking`: built-in dimensions and ratio are observations, never content-QA, repair, role-demotion, finalization, or external-handoff gates. Activate `native_4k_branch` only when the user explicitly requires Codex-native 4K; keep it `off` in every default run.

## Board contract

Generate one clean board with exactly six distinct full-product views. Put `horizontal 16:9` in the built-in generation prompt as the sole creative ratio request. The built-in tool exposes no ratio or size argument, so record the original returned file's dimensions and observed ratio without turning them into a pass/fail condition. A `1672x941`, `1536x1024`, or other returned size remains `codex_board_role: content_qa_reference` when the six-view content contract passes. Do not crop or stretch it; the external stage must rebuild from that board plus the original references using its own exact 16:9 and 4K controls.

1. front or primary view;
2. rear;
3. left profile;
4. right profile;
5. slight overhead top view, or underside when more informative;
6. 3/4 front hero view, or 3/4 rear when needed to avoid repetition.

Use a neutral white or light-gray studio background, soft diffused light, subtle grounding shadows, complete uncropped products, generous margins, and no overlap.

Preserve source-supported silhouette, proportions, colors, materials, construction, texture, and markings. Never redesign, premiumize, modernize, simplify, beautify, recolor, relabel, or invent features.

Keep all non-product-native text outside the image. Forbid titles, view labels, numbers, arrows, callouts, prompt text, captions, watermarks, UI, extra logos, props, hands, people, scenes, and decorative advertising layout. If visible product text is not an exact-lock requirement, preserve its placement and visual hierarchy without inventing readable copy.

## Prompt binding and terminal generation

Build one public English `final_generation_prompt` from the source map and selected views. Before calling image generation:

1. freeze the exact prompt bytes;
2. write those exact bytes to `<asset_id>_generation_prompt.md`, re-read the file as bytes, and calculate `generation_prompt_sha256` from the re-read bytes;
3. stop with `blocked_generation_prompt_persistence` if write, re-read, or hash verification fails; never reconstruct the prompt later;
4. show the exact prompt in a `prompt_record`, with `final_generation_prompt` as the single source of truth and `english_prompt_used` as a compatibility alias pointing to the same bytes;
5. set `prompt_disclosed_before_generation: true` only when the displayed, persisted, hashed, and submitted bytes are identical;
6. set `terminal_generation_call: pending`, `assistant_qa_status: pending_post_generation_inspection`, and `production_approval_status: not_granted`.

Before generation, an enhancement prompt may exist only as `draft_4k_enhancement_prompt`. Label it `4k_enhancement_prompt_status: draft_pre_generation`; do not call it final and do not publish a final-prompt hash. The actual board must be visually inspected before `final_4k_enhancement_prompt` is frozen.

Then submit that exact prompt with the target reference images. Treat the image-generation call as the terminal action of that assistant turn. Do not append reconstructed prompts, QA, or commentary after the call when the runtime forbids post-generation text.

Before the terminal call, set `task_finalization_status: generation_terminal_pending`. The tool/runtime call trace is the evidence for changing `terminal_generation_call` from `pending` to `executed`; never predeclare execution. Only an executed trace promotes the task to `awaiting_post_generation_continuation`. The generation turn is then only `stage_complete`, never task-complete. If the host does not automatically continue, leave that derived awaiting state with `main_result_prompt_pair_status: pending`. The next continuation must inspect the actual board and finish prompt-pair finalization. A failed or missing call never enters the awaiting state.

When the trace proves `executed` and the board is available but not yet inspected, set `4k_enhancement_prompt_status: awaiting_post_generation_inspection`. Advance to `finalized_post_inspection` only after the actual board passes the post-generation inspection gate.

If the runtime permits artifact inspection only in a later continuation, inspect and report QA there. A repair follows the same sequence: publish and hash the repair prompt first, then make the repair generation call as that turn's terminal action.

The prompt must request:

- the exact same product as the supplied target reference;
- exactly six complete, non-redundant views in a clean 2x3 board;
- a horizontal 16:9 result as a creative request, without implying runtime size control;
- identity preservation and no invented hidden structure;
- neutral studio presentation and no non-product text or advertising scene.

Never reconstruct a cleaner prompt after generation and claim it was submitted.

## Optional Codex-native 4K branch

Keep `native_4k_branch: off` unless the user explicitly requests Codex-native 4K. When off, omit native-resolution status from default assistant QA, repairs, handoff readiness, and task completion.

When explicitly activated, keep target, observation, and approval separate:

- `target_native_resolution`: requested creative/runtime target;
- `observed_pixel_dimensions`: dimensions read from the original returned artifact;
- `native_provenance`: evidence that those pixels came directly from generation rather than resize, upscale, screenshot, preview, or export enlargement.

Classify:

- `resolution_approved`: original generated artifact is verified at 3840x2160 or higher, remains horizontal 16:9, and native provenance is verified with no post-generation enlargement;
- `resolution_not_approved`: observed dimensions are lower, geometry is wrong, or any enlargement was used;
- `resolution_unverified`: dimensions or native provenance cannot be inspected.

Set `native_4k_claim: true` only for `resolution_approved`. Prompt wording, file naming, metadata copied from a request, or a delivered 4K-sized post-processed file is not native provenance.

Report this optional branch independently. If the user made Codex-native 4K mandatory, any status other than `resolution_approved` fails that explicit branch; it does not retroactively change the default content QA or external prompt-pair contract.

This native gate applies only to claims about the original Codex-generated artifact. A later third-party 4K artifact is never `native_4k_claim: true`; track it under the external 4K contract.

## Post-inspection external 4K handoff

After inspecting the actual Codex board, create a board-specific 4K handoff for Nano Banana Pro, Nano Banana 2, or a comparable image-to-image model. Use **both** the inspected Codex board and the original product references. A board-only enhancement is incomplete because low-resolution pixels cannot prove missing product detail.

Freeze a public English `final_4k_enhancement_prompt` that names the observed panel-level defects and preserves:

- exactly the same 2x3 topology, six view assignments, complete products, spacing, and neutral studio presentation;
- source-supported silhouette, proportions, panels, openings, seams, handles, straps, buttons, ports, edges, texture direction, colors, simple material finish, and markings across all six views;
- only source-supported edge separation and surface micro-detail; leave unsupported details unresolved instead of inventing geometry, interfaces, copy, or marks;
- one 16:9 result using the provider's actual 4K profile, with no crop, stretch, reframing, panel reorder, extra view, advertising treatment, or non-product-native text.

Hash the frozen prompt as `4k_enhancement_prompt_sha256`. Persist these required sidecar files in run-scoped writable storage. If any file cannot be written and re-read, set `blocked_prompt_pair_persistence`; a fenced record or chat copy cannot substitute:

- `<asset_id>_generation_prompt.md`: the pre-generation frozen `final_generation_prompt` single source of truth, re-read rather than rewritten;
- `<asset_id>_4k_enhancement_prompt.md`: the inspected-board-specific `final_4k_enhancement_prompt` and its SHA-256;
- `<asset_id>_4k_handoff.yaml`: model target, reference bundle, request, state, and verification evidence.

The handoff must contain:

```text
4k_enhancement_prompt_status: finalized_post_inspection
4k_enhancement_prompt_sha256: <sha256>
third_party_model_target: nano_banana_pro / nano_banana_2 / model_agnostic
codex_board_role: content_qa_reference
external_reference_bundle:
- codex_asset_board: <inspected artifact id/path>
- original_source_references: <all authoritative product references>
source_fidelity_status: pending / passed / failed / unverified / blocked_missing_original_sources
external_runtime_request:
- aspect_ratio: "16:9"
- image_size: "4K"
- alternate_aspect_ratios_allowed: false
external_4k_status: not_ready / handoff_ready / blocked_runtime_controls / pending_external_generation / returned_unverified / verified / rejected
external_4k_qa_status: pending / passed / failed
```

Use `handoff_ready` only when the final prompt is hashed and every reference is resolvable; `pending_external_generation` only after submission; `returned_unverified` only when an original returned file exists; `verified` only after the QA below; otherwise use `rejected`.

If the selected platform does not expose both the exact 16:9 aspect-ratio control and the 4K image-size control, set `external_4k_status: blocked_runtime_controls`; choose no fallback size or ratio.

For every returned external artifact, record `provider`, `model`, `surface`, `model_profile`, requested settings, `observed_pixel_dimensions`, `provider_declared_aspect_ratio_profile`, `observed_file_aspect_ratio`, `aspect_ratio_evidence`, and `four_k_evidence`. Accept only a returned artifact whose request and provider metadata identify the 16:9 profile, whose original-file dimensions match that provider/model/surface's documented 4K 16:9 profile, and whose `source_fidelity_status` and `external_4k_qa_status` pass. Arbitrary landscape dimensions, filenames, screenshots, previews, local resize, or export enlargement are insufficient.

External 4K QA must re-run all board QA and additionally pass `six_view_geometry_preserved`, `interfaces_and_seams_preserved`, `no_new_product_detail`, `external_reference_bundle_complete`, `external_16_9_verified`, and `external_4k_profile_verified`. A post-processed 4K file may be production-usable after these gates, but it remains an externally generated/enhanced artifact and never becomes evidence of Codex-native 4K.

## Final main-result prompt pair

Use only these finalization vocabularies:

```text
task_finalization_status: generation_terminal_pending | awaiting_post_generation_continuation | prompt_pair_ready | final_main_result_published
main_result_prompt_pair_status: pending | published
```

In the post-generation continuation, inspect the actual board, finalize the image-specific `final_4k_enhancement_prompt`, write it to `<asset_id>_4k_enhancement_prompt.md`, re-read the exact bytes, and calculate `4k_enhancement_prompt_sha256`. Then re-read `<asset_id>_generation_prompt.md` and verify its bytes against the recorded `generation_prompt_sha256`. A missing file, byte mismatch, or hash mismatch is `blocked_prompt_pair_integrity`; do not reconstruct either prompt.

Set `task_finalization_status: prompt_pair_ready` only when both re-read hashes pass. Then publish one **final-channel main result**, not commentary, containing the complete unabridged text of both prompts and both hashes in the fixed fields below. A sidecar, path, summary, excerpt, earlier commentary, or earlier turn never substitutes for either complete prompt.

`prompt_pair_ready` proves prompt integrity only. It does not imply `external_4k_status: handoff_ready`; the external reference bundle and exact 16:9/4K runtime controls must independently pass their existing gates.

If the final response cannot contain both complete prompts because of a real output-capacity limit, set `blocked_final_output_capacity`; do not truncate, abbreviate, split across responses, or claim either published state.

```text
final_generation_prompt:
<complete exact bytes re-read from the frozen generation sidecar>
generation_prompt_sha256: <verified sha256>

final_4k_enhancement_prompt:
<complete exact bytes re-read from the finalized enhancement sidecar>
4k_enhancement_prompt_sha256: <verified sha256>

main_result_prompt_pair_status: published
task_finalization_status: final_main_result_published
```

Include both published statuses in that final block. Successful emission of the complete block is the transition evidence; require no write or status mutation after the terminal final response. Until emission succeeds, the task remains incomplete even when the board, sidecars, or handoff already exist.

## Artifact QA and approval separation

In a post-generation inspection turn, inspect the actual artifact and report:

- `six_views_present`: pass / fail;
- `views_distinct`: pass / fail;
- `complete_uncropped_views`: pass / fail;
- `identity_source_consistent`: pass / fail / unverified;
- `geometry_source_consistent`: pass / fail / unverified;
- `color_material_source_consistent`: pass / fail / unverified;
- `no_invented_structure`: pass / fail / unverified;
- `no_non_product_text_pollution`: pass / fail;
- `built_in_dimensions_policy`: evidence_only_nonblocking;
- `built_in_observed_pixel_dimensions`: width x height / unavailable;
- `built_in_observed_aspect_ratio`: value / unavailable;
- `prompt_bound`: pass / fail;
- `native_4k_branch_status`: off / resolution_approved / resolution_not_approved / resolution_unverified; report a resolution value only when the user explicitly activated that branch.

Use these distinct decisions:

- `assistant_qa_status: passed`: the observable board contract passes;
- `assistant_qa_status: conditional`: useful but limited by inference or missing source evidence, never by built-in dimensions;
- `assistant_qa_status: failed`: a critical observable gate fails;
- `production_approval_status: not_granted / user_granted / external_pipeline_granted`.

Assistant QA never silently grants production approval or registry admission. A visually plausible view is not source proof.

## Repair limit

Attempt at most two repair generations. Repair one dominant failure at a time in this order:

1. product identity or geometry;
2. missing, cropped, or repeated views;
3. invented structure or fake text;
4. color/material mismatch;
5. text pollution or layout;
6. optional native resolution, only when `native_4k_branch` was explicitly activated and an actual native high-resolution path exists.

Do not upscale a failed artifact and present it as native 4K. Stop when missing references or unsupported runtime capability cannot be repaired by another generation.

## Output contract

Before the terminal generation call, provide concise Chinese text with:

```text
适用性：suitable / conditional / not_suitable
风险向量：geometry / label / material / structure / state
来源状态：source_verified / source_inferred / needs_source
runtime_capability_snapshot: ...

prompt_record:
built_in_prompt_aspect_ratio_request: "horizontal 16:9"
built_in_prompt_alternate_aspect_ratios_allowed: false
built_in_dimensions_policy: evidence_only_nonblocking
codex_board_role: pending_content_qa
final_generation_prompt: <exact prompt that will be submitted>
english_prompt_used: <same exact bytes as final_generation_prompt>
generation_prompt_sha256: <verified sha256>
prompt_disclosed_before_generation: true / false
terminal_generation_call: pending
assistant_qa_status: pending_post_generation_inspection
production_approval_status: not_granted
4k_enhancement_prompt_status: draft_pre_generation / awaiting_post_generation_inspection
draft_4k_enhancement_prompt: <optional provisional prompt; never final>
external_4k_status: not_ready
task_finalization_status: generation_terminal_pending
main_result_prompt_pair_status: pending
```

In the later inspection continuation, report content QA, nonblocking built-in dimension observations, external runtime state, limitations, and production approval, then publish the complete prompt pair in the final-channel main result exactly as required above. After an external return, append provider/surface/profile/dimension evidence and external 4K QA. Do not repeat long theory or expose hidden reasoning.

## End condition

The image-generation turn may end only as `stage_complete` with `task_finalization_status: awaiting_post_generation_continuation`. The task completes only when board content QA is classified, the source-bound exact-16:9/4K handoff is ready or honestly runtime-blocked, and `task_finalization_status: final_main_result_published` proves the final channel displayed both complete prompts and both verified hashes. A real source, capability, persistence, or prompt-integrity blocker may end the run without a completion claim.
