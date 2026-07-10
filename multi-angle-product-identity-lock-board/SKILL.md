---
name: multi-angle-product-identity-lock-board
description: Generate one clean 16:9 six-view identity board for a low-risk, mostly opaque product from supplied references, disclose its exact generation prompt, then inspect the actual board and deliver a source-bound 4K enhancement prompt and handoff for Nano Banana Pro, Nano Banana 2, or a comparable model. Use when silhouette, proportions, color, simple material, and non-text construction must stay consistent across common views; do not use for label-copy-first packaging, material-sensitive glass/liquid/reflective products, complex mechanisms, state changes, or advertising scenes. Treat native and external 4K as separate evidence-gated claims.
---

# Multi-Angle Product Identity Lock Board

Chinese name: 多角度产品身份锁定板

Generate exactly one six-view reference board for a low-risk product. Preserve identity rather than redesigning it. The deliverable is a generated board plus a traceable public prompt and an evidence-based QA record. A prompt-only request routes outside this Skill and is not a successful run.

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
- requested_aspect_ratio: 16:9 / not_exposed
- requested_native_size: value / not_exposed
- returned_file_inspectable: supported / unsupported / unknown
- pixel_dimensions_inspectable: supported / unsupported / unknown
- native_provenance_inspectable: supported / unsupported / unknown
- post_generation_text_allowed_same_turn: supported / unsupported / unknown
```

Do not infer a capability from prompt wording. `Target 3840x2160` inside a prompt is a creative target, not proof that a native-size control exists.

If image generation or reference attachment is unavailable, report `blocked_capability` and do not substitute a prompt-only result. If the user specifically requires **Codex-native** 4K and either native-size control or provenance inspection is unsupported, report `blocked_native_4k_contract` before generation. A final 4K requirement may instead use the post-inspection external 4K handoff below; in that branch the Codex board remains an intermediate layout-and-identity reference until the returned external artifact is verified.

## Board contract

Generate one clean horizontal 16:9 board with exactly six distinct full-product views. `target_aspect_ratio: 16:9` is fixed: request no alternate ratio and accept no automatic ratio fallback. If the built-in runtime returns another ratio despite the request, do not crop or stretch it or call it final; set `codex_board_role: intermediate_layout_reference` and use the external stage to rebuild the same source-faithful topology on the requested 16:9 provider profile. A matching returned board may be `final_candidate` after QA.

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
2. show the exact prompt in a `prompt_record`, with `final_generation_prompt` as the single source of truth and `english_prompt_used` as a compatibility alias pointing to the same bytes;
3. calculate and show `generation_prompt_sha256` when hashing is available;
4. set `prompt_disclosed_before_generation: true` only when the displayed bytes are the bytes that will be submitted;
5. set `terminal_generation_call: pending`;
6. set `assistant_qa_status: pending_post_generation_inspection` and `production_approval_status: not_granted`.

Before generation, an enhancement prompt may exist only as `draft_4k_enhancement_prompt`. Label it `4k_enhancement_prompt_status: draft_pre_generation`; do not call it final and do not publish a final-prompt hash. The actual board must be visually inspected before `final_4k_enhancement_prompt` is frozen.

Then submit that exact prompt with the target reference images. Treat the image-generation call as the terminal action of that assistant turn. Do not append reconstructed prompts, QA, or commentary after the call when the runtime forbids post-generation text.

The tool/runtime call trace is the evidence for changing `terminal_generation_call` from `pending` to `executed`; never predeclare execution. Without a separate subsequent visual inspection, leave `assistant_qa_status: pending_post_generation_inspection` and `production_approval_status: not_granted`.

When the trace proves `executed` and the board is available but not yet inspected, set `4k_enhancement_prompt_status: awaiting_post_generation_inspection`. Advance to `finalized_post_inspection` only after the actual board passes the post-generation inspection gate.

If the runtime permits artifact inspection only in a later continuation, inspect and report QA there. A repair follows the same sequence: publish and hash the repair prompt first, then make the repair generation call as that turn's terminal action.

The prompt must request:

- the exact same product as the supplied target reference;
- exactly six complete, non-redundant views in a clean 2x3 board;
- a horizontal 16:9 result, with 3840x2160 as the preferred native target when supported;
- identity preservation and no invented hidden structure;
- neutral studio presentation and no non-product text or advertising scene.

Never reconstruct a cleaner prompt after generation and claim it was submitted.

## Native-resolution evidence gate

Keep target, observation, and approval separate:

- `target_native_resolution`: requested creative/runtime target;
- `observed_pixel_dimensions`: dimensions read from the original returned artifact;
- `native_provenance`: evidence that those pixels came directly from generation rather than resize, upscale, screenshot, preview, or export enlargement.

Classify:

- `resolution_approved`: original generated artifact is verified at 3840x2160 or higher, remains horizontal 16:9, and native provenance is verified with no post-generation enlargement;
- `resolution_not_approved`: observed dimensions are lower, geometry is wrong, or any enlargement was used;
- `resolution_unverified`: dimensions or native provenance cannot be inspected.

Set `native_4k_claim: true` only for `resolution_approved`. Prompt wording, file naming, metadata copied from a request, or a delivered 4K-sized post-processed file is not native provenance.

When Codex-native 4K is preferred but unverified, the board may be a useful `conditional` candidate; it is not an approved native-4K asset. When Codex-native 4K is specifically mandatory, any status other than `resolution_approved` is `blocked_native_4k_contract`. A final external 4K requirement follows the separate handoff state instead.

This native gate applies only to claims about the original Codex-generated artifact. A later third-party 4K artifact is never `native_4k_claim: true`; track it under the external 4K contract.

## Post-inspection external 4K handoff

After inspecting the actual Codex board, create a board-specific 4K handoff for Nano Banana Pro, Nano Banana 2, or a comparable image-to-image model. Use **both** the inspected Codex board and the original product references. A board-only enhancement is incomplete because low-resolution pixels cannot prove missing product detail.

Freeze a public English `final_4k_enhancement_prompt` that names the observed panel-level defects and preserves:

- exactly the same 2x3 topology, six view assignments, complete products, spacing, and neutral studio presentation;
- source-supported silhouette, proportions, panels, openings, seams, handles, straps, buttons, ports, edges, texture direction, colors, simple material finish, and markings across all six views;
- only source-supported edge separation and surface micro-detail; leave unsupported details unresolved instead of inventing geometry, interfaces, copy, or marks;
- one 16:9 result using the provider's actual 4K profile, with no crop, stretch, reframing, panel reorder, extra view, advertising treatment, or non-product-native text.

Hash the frozen prompt as `4k_enhancement_prompt_sha256`. Materialize these logical sidecars, as files when the runtime supports file delivery or as clearly named fenced records otherwise:

- `<asset_id>_generation_prompt.md`: the exact `final_generation_prompt` single source of truth, never a rewritten duplicate;
- `<asset_id>_4k_enhancement_prompt.md`: the inspected-board-specific `final_4k_enhancement_prompt` and its SHA-256;
- `<asset_id>_4k_handoff.yaml`: model target, reference bundle, request, state, and verification evidence.

The handoff must contain:

```text
4k_enhancement_prompt_status: finalized_post_inspection
4k_enhancement_prompt_sha256: <sha256>
third_party_model_target: nano_banana_pro / nano_banana_2 / model_agnostic
codex_board_role: intermediate_layout_reference / final_candidate
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
- `aspect_ratio_status`: verified_16_9 / failed / unverified;
- `prompt_bound`: pass / fail;
- `resolution_status`: resolution_approved / resolution_not_approved / resolution_unverified.

Use these distinct decisions:

- `assistant_qa_status: passed`: the observable board contract passes;
- `assistant_qa_status: conditional`: useful but limited by inference, missing source, or unverified resolution;
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
6. 16:9 conformance;
7. native resolution, only when an actual native high-resolution path exists.

Do not upscale a failed artifact and present it as native 4K. Stop when missing references or unsupported runtime capability cannot be repaired by another generation.

## Output contract

Before the terminal generation call, provide concise Chinese text with:

```text
适用性：suitable / conditional / not_suitable
风险向量：geometry / label / material / structure / state
来源状态：source_verified / source_inferred / needs_source
runtime_capability_snapshot: ...

prompt_record:
target_aspect_ratio: "16:9"
alternate_aspect_ratios_allowed: false
codex_board_role: pending_observation
final_generation_prompt: <exact prompt that will be submitted>
english_prompt_used: <same exact bytes as final_generation_prompt>
generation_prompt_sha256: <sha256 / unavailable>
prompt_disclosed_before_generation: true / false
terminal_generation_call: pending
assistant_qa_status: pending_post_generation_inspection
production_approval_status: not_granted
4k_enhancement_prompt_status: draft_pre_generation / awaiting_post_generation_inspection
draft_4k_enhancement_prompt: <optional provisional prompt; never final>
external_4k_status: not_ready
```

In the later inspection turn, report the artifact QA fields, aspect-ratio and native-resolution evidence, the frozen `final_4k_enhancement_prompt`, its SHA-256, all three sidecars, external runtime request, external state, limitations, and production-approval state. After external return, append provider/surface/profile/dimension evidence and the external 4K QA result. Do not repeat long theory or expose hidden reasoning.

## End condition

End only when the run is honestly routed and either:

- one six-view candidate has been generated from source references with a pre-bound prompt and awaits or receives artifact QA;
- artifact QA has classified it without overstating source fidelity, native 4K, or production approval;
- a finalized 16:9 external 4K handoff has been emitted after inspection and any returned artifact has been classified as `verified` or `rejected` without relabeling it as native;
- a real source or runtime capability blocker has been reported before generation.
