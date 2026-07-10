---
name: packaging-product-identity-label-lock-board
description: Use when supplied bottle, box, pouch, can, tube, jar, carton, bag, or other label-heavy packaging references need one clean 16:9 video-reference board that separates geometry and label-layout consistency from exact-copy verification. Disclose the exact generation prompt, then inspect the actual board and deliver a source-bound 4K enhancement prompt and handoff for Nano Banana Pro, Nano Banana 2, or a comparable model. Approve exact text, logos, QR codes, barcodes, specifications, or certifications only with source assets and deterministic composition or field-level OCR/decode evidence. Do not use for simple low-text products, material-first glass/liquid/reflective products, mechanisms, scenes, or posters.
---

# Packaging Product Identity + Label Lock Board

Chinese name: 包装产品身份与标签文案双锁定资产板

Create one clean composite product-reference board for label-heavy packaging. Treat `geometry_layout_lock` and `exact_copy_lock` as separate claims. A generated board may stabilize product form and label hierarchy without proving that every character, logo, barcode, QR code, certification, or legal field is exact.

Only product-native graphics may appear inside the image. Keep headings, view names, status, evidence, prompts, and registry IDs in chat text.

## Boundary and risk-vector routing

Require at least one usable target-product image. Before generation, classify:

- `geometry_risk`: package silhouette, volume, proportions, closure, edges, top/bottom;
- `label_risk`: copy density, logo, claims, specifications, certifications, codes;
- `material_risk`: glass, transparency, liquid, chrome, foil, refraction, mixed shells;
- `structure_risk`: mechanisms, joints, folding, complex open/close topology;
- `state_risk`: multiple use, assembly, open/closed, deployed/stored states.

Use this skill when label risk is primary and packaging geometry is source-supported. Route instead when:

- text is minimal and shape is the main risk: use `multi-angle-product-identity-lock-board`;
- material behavior is primary: use `material-sensitive-product-master-asset-board`;
- label and material are both high: use a main-agent compound workflow that coordinates both risk contracts; do not make either skill claim complete coverage alone;
- mechanisms or state topology dominate: use a main-agent/custom-agent workflow unless a dedicated active skill exists;
- the request is an ad poster, scene, redesign, campaign visual, or e-commerce layout: lock the product first or use a different workflow.

If no visual product source exists, stop and request it. Descriptive text alone cannot lock product identity.

## Source ledger

Build a source ledger before generation. Give each item a stable `field_id` and record:

```text
field_id:
field_type: geometry / label_layout / exact_text / logo / barcode / qr_code / certification / material
required_for_run: yes / no
expected_value_or_asset:
source_file_or_reference:
source_region:
source_status: source_verified / source_inferred / needs_source / conflict
planned_verification: visual_compare / ocr_field_match / code_decode_match / deterministic_composite / not_verifiable
```

Acceptable exact-copy sources include:

- original flat label artwork or package dieline;
- vector/raster logo master;
- high-resolution orthographic label crop;
- user-supplied exact text table;
- expected barcode or QR payload plus symbology;
- authoritative certification artwork or exact mark asset.

Do not treat a small, blurred, oblique, occluded, generated, or inferred surface as exact-copy source evidence. Do not merge conflicting variants. If required sources conflict and authority cannot be resolved, stop with `source_conflict`.

## Two independent lock layers

### Geometry and layout layer

`geometry_layout_lock` covers:

- package silhouette, volume, proportions, thickness, shoulder, cap, lid, pump, rim, base, seal, and closure;
- label position, scale relationship, hierarchy, color blocks, graphic zones, and orientation;
- consistency across video-relevant views.

It may be assessed visually against supplied product references. A pass does not imply exact readable copy.

### Exact-copy layer

Classify fields:

- `A_exact`: brand, logo, product name, hero title/claim, capacity/specification, and anything the user names as exact;
- `B_targeted`: ingredients, parameters, usage, warnings, side/back copy, certification text;
- `C_texture`: non-critical microcopy that may remain non-readable texture.

If the user requires all text to be exact, promote A, B, and C to `A_exact`.

An exact field can pass only when source evidence and final-artifact evidence both exist:

- readable text: authoritative expected text plus field-level OCR/transcription comparison of the final artifact, with normalization rules and a zero-unresolved-difference result;
- barcode or QR code: authoritative expected payload and symbology plus successful decode from the final artifact matching both;
- logo or certification artwork: supplied master asset plus deterministic placement/compositing evidence, or another reproducible region comparison that proves the final artwork was not generatively rewritten;
- flat label artwork: deterministic compositing of the supplied artwork onto the final board, with source/output asset hashes and transform record, may satisfy exactness without generative rerendering.

Visual resemblance, prompt wording, an agent reading what it expects to see, OCR without an expected field value, or a code-like pattern that was not decoded cannot approve exact copy.

Declare OCR normalization before comparison. It may normalize Unicode representation and ignorable spacing only when the source contract permits; it must not silently change letters, numbers, punctuation, units, order, language, capitalization, or legal meaning to manufacture a match.

If the board is produced only by generative image synthesis, `exact_copy_lock_status` is at most `conditional_unverified`, even when text looks correct. If required exact evidence is missing or a field differs, use `not_approved` for that field. Never fabricate unseen copy, claims, certification marks, codes, or logos.

## Angle and panel-capacity gate

Default video-reference views:

1. front;
2. back;
3. left;
4. right;
5. 3/4 front;
6. 3/4 back;
7. high angle;
8. low angle.

Mark each view `source_verified`, `source_inferred`, or `needs_source`. High/low views do not prove unseen top/bottom text or structure. A forward-use inferred view may be useful, but the board is at most conditional for those faces.

Before generation, allocate a `panel_capacity_budget` for the one-board composition. Include only detail crops required by the source ledger. Every product view and exact-copy region must remain distinguishable at the intended downstream reference size. If eight views plus required detail regions cannot remain legible:

- prioritize geometry views and A-exact regions;
- remove decorative or redundant details;
- do not shrink proof regions until text or code evidence becomes unreadable;
- mark the excluded fields `needs_source_or_separate_deterministic_evidence`;
- never claim one crowded generated board proves all microcopy.

## Clean-board contract

Generate exactly one horizontal 16:9 board image. `target_aspect_ratio: 16:9` is fixed: request no alternate ratio and accept no automatic ratio fallback. If the built-in runtime returns another ratio despite the request, do not crop or stretch it or call it final; set `codex_board_role: intermediate_layout_reference` and use the external stage to rebuild the same source-faithful topology on the requested 16:9 provider profile. A matching returned board may be `final_candidate` after QA. Use a neutral white, light-gray, or neutral-gray studio presentation with even lighting, complete uncropped products, and no dramatic scene.

The board may include:

- the eight product views;
- source-required close crops for logo, A-exact fields, codes, label adhesion, print, embossing, foil, closure, or package construction;
- real product-native text, logos, patterns, and marks only.

Forbid board titles, section headings, view labels, asset IDs, dates, statuses, legends, arrows, callouts, tables, UI, prompt text, captions, watermarks, people, hands, props, lifestyle scenes, posters, and non-product-native typography.

Preserve source-supported geometry, label placement, color, material, and graphic hierarchy. Do not redesign, premiumize, modernize, simplify, rebrand, relabel, recolor, advertise, or invent hidden surfaces.

## Runtime capability snapshot

Inspect the currently exposed tools and record only observed capabilities:

```text
runtime_capability_snapshot:
- image_generation_callable: supported / unsupported / unknown
- reference_images_attachable: supported / unsupported / unknown
- explicit_aspect_ratio_argument: supported / unsupported / unknown
- explicit_size_argument: supported / unsupported / unknown
- requested_aspect_ratio: 16:9 / not_exposed
- returned_file_inspectable: supported / unsupported / unknown
- pixel_dimensions_inspectable: supported / unsupported / unknown
- post_generation_text_allowed_same_turn: supported / unsupported / unknown
- deterministic_compositor_available: supported / unsupported / unknown
- ocr_available: supported / unsupported / unknown
- barcode_qr_decoder_available: supported / unsupported / unknown
- hashing_available: supported / unsupported / unknown
```

Do not infer a capability from desired prompt language. If generation or reference attachment is unavailable, report `blocked_capability`. If the user requires exact copy and no qualifying deterministic/OCR/decode path exists, generation may still create a geometry/layout candidate only with explicit `exact_copy_lock_status: blocked_verification_capability`; do not promise an exact lock.

## Prompt record and terminal generation call

Build one public `final_generation_prompt` from the source ledger, angle map, and panel budget. Before calling image generation:

1. freeze the exact prompt bytes;
2. show the complete `final_generation_prompt`;
3. calculate `generation_prompt_sha256` when available;
4. set `prompt_disclosed_before_generation: true` only when the shown bytes will be submitted unchanged;
5. set `terminal_generation_call: pending`;
6. set `assistant_qa_status: pending_post_generation_inspection`;
7. set `production_approval_status: not_granted`.

Before generation, an enhancement prompt may exist only as `draft_4k_enhancement_prompt`. Label it `4k_enhancement_prompt_status: draft_pre_generation`; do not call it final and do not publish a final-prompt hash. The actual board must be visually inspected before `final_4k_enhancement_prompt` is frozen.

Then submit the exact prompt with all source references. The image-generation call is the terminal action of that assistant turn. Do not append a prompt, QA, or commentary after the call when the runtime forbids post-generation text.

The tool/runtime call trace is the evidence for changing `terminal_generation_call` from `pending` to `executed`; never predeclare execution. Without a separate subsequent visual inspection, leave `assistant_qa_status: pending_post_generation_inspection` and `production_approval_status: not_granted`.

When the trace proves `executed` and the board is available but not yet inspected, set `4k_enhancement_prompt_status: awaiting_post_generation_inspection`. Advance to `finalized_post_inspection` only after the actual board passes the post-generation inspection gate.

The prompt must request one clean 16:9 board, consistent package geometry, the planned views and details, source-bound label layout, no invented readable text, and no non-product-native text. It must not offer another aspect ratio or claim that generation alone will produce verified exact copy.

If the runtime allows inspection only in a later continuation, perform artifact QA, OCR/decode, or deterministic compositing there. Any repair generation follows the same sequence: disclose and hash the repair prompt, then use the image call as the turn's terminal action.

## Artifact QA and exact-copy verification

In a separate inspection step, assess:

```text
geometry_layout_lock_status: passed / conditional / failed / unverified
angle_source_status: passed / conditional / failed
aspect_ratio_status: verified_16_9 / failed / unverified
no_non_product_text_pollution: pass / fail
material_source_consistent: pass / fail / unverified
panel_legibility_status: pass / fail / unverified
prompt_bound: pass / fail
exact_copy_lock_status: approved / conditional_unverified / not_approved / not_required
assistant_qa_status: passed / conditional / failed / pending_post_generation_inspection
production_approval_status: not_granted / user_granted / external_pipeline_granted
```

For every required exact field, append an evidence row:

```text
field_id:
expected_value_or_asset:
final_observation:
verification_method:
verification_evidence:
field_result: pass / fail / unverified
```

Set `exact_copy_lock_status: approved` only when every required exact field passes its qualifying evidence method. A geometry/layout pass and an exact-copy pass remain independently visible.

Assistant QA does not grant production approval or admission to an Approved Packaging Asset Registry. Registry admission requires all required gates, retained evidence, and an explicit user or external-pipeline approval.

## Post-inspection external 4K handoff

After inspecting the actual Codex board, create a board-specific 4K handoff for Nano Banana Pro, Nano Banana 2, or a comparable image-to-image model. Use **both** the inspected Codex board and the original product references; include authoritative flat artwork, logo masters, exact-text tables, and expected barcode/QR payloads when the exact-copy layer requires them. A board-only enhancement is incomplete because low-resolution pixels cannot prove missing package detail.

Freeze a public English `final_4k_enhancement_prompt` that names the observed panel-level defects and preserves:

- the exact board topology, planned view assignments, complete package geometry, closure, label positions, color blocks, graphic zones, and neutral studio presentation;
- source-supported edge separation, print boundaries, embossing/foil/material cues, and label-layout hierarchy without redesign or relabeling;
- existing exact-copy regions as protected evidence regions, while explicitly leaving unreadable or unsupported copy unresolved rather than generating plausible characters, logos, certifications, barcodes, or QR codes;
- one 16:9 result using the provider's actual 4K profile, with no crop, stretch, reframing, panel reorder, additional panel, advertising treatment, or non-product-native text.

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
- exact_copy_assets: <required authoritative assets or not_required>
source_fidelity_status: pending / passed / failed / unverified / blocked_missing_original_sources
external_runtime_request:
- aspect_ratio: "16:9"
- image_size: "4K"
- alternate_aspect_ratios_allowed: false
external_4k_status: not_ready / handoff_ready / blocked_runtime_controls / pending_external_generation / returned_unverified / verified / rejected
external_4k_qa_status: pending / passed / failed
```

Use `handoff_ready` only when the final prompt is hashed and every required reference is resolvable; `pending_external_generation` only after submission; `returned_unverified` only when an original returned file exists; `verified` only after the QA below; otherwise use `rejected`.

If the selected platform does not expose both the exact 16:9 aspect-ratio control and the 4K image-size control, set `external_4k_status: blocked_runtime_controls`; choose no fallback size or ratio.

For every returned external artifact, record `provider`, `model`, `surface`, `model_profile`, requested settings, `observed_pixel_dimensions`, `provider_declared_aspect_ratio_profile`, `observed_file_aspect_ratio`, `aspect_ratio_evidence`, and `four_k_evidence`. Accept only a returned artifact whose request and provider metadata identify the 16:9 profile, whose original-file dimensions match that provider/model/surface's documented 4K 16:9 profile, and whose `source_fidelity_status` and `external_4k_qa_status` pass. Arbitrary landscape dimensions, filenames, screenshots, previews, local resize, or export enlargement are insufficient.

External 4K QA must re-run geometry/layout QA and additionally pass `package_geometry_preserved`, `label_layout_preserved`, `no_generated_exact_copy_claim`, `external_reference_bundle_complete`, `external_16_9_verified`, and `external_4k_profile_verified`. Keep `exact_copy_lock_status` independent: a generative 4K result remains at most `conditional_unverified` for text, logos, certifications, barcodes, and QR codes. Only deterministic composition plus field-level OCR, reproducible region comparison, or payload decode evidence can approve those fields after enhancement.

## Repair rules

Attempt at most two generative repairs. Repair one dominant issue at a time:

1. geometry or cross-view identity;
2. missing/cropped/repeated views;
3. label position or hierarchy;
4. non-product text pollution;
5. material or panel legibility.
6. 16:9 conformance.

Do not repeatedly regenerate exact text, logos, or codes when deterministic compositing is the reliable path. A repair that improves text but breaks geometry, source identity, or clean-board rules still fails. Stop when missing source evidence or unavailable verification capability is the blocker.

## Output contract

Before the terminal generation call, provide concise Chinese text:

```text
风险向量：geometry / label / material / structure / state
来源账本：<compact field summary>
geometry_layout_lock_status: pending_generation
exact_copy_lock_status: pending_verification / blocked_verification_capability / not_required
panel_capacity_budget: pass / constrained / blocked
runtime_capability_snapshot: ...

target_aspect_ratio: "16:9"
alternate_aspect_ratios_allowed: false
codex_board_role: pending_observation
final_generation_prompt:
<exact prompt that will be submitted>
generation_prompt_sha256: <sha256 / unavailable>
prompt_disclosed_before_generation: true / false
terminal_generation_call: pending
assistant_qa_status: pending_post_generation_inspection
production_approval_status: not_granted
4k_enhancement_prompt_status: draft_pre_generation / awaiting_post_generation_inspection
draft_4k_enhancement_prompt: <optional provisional prompt; never final>
external_4k_status: not_ready
```

In the later inspection step, report the two lock-layer statuses, field evidence rows, 16:9 evidence, the frozen `final_4k_enhancement_prompt`, its SHA-256, all three sidecars, external runtime request, external state, limitations, registry eligibility, and production-approval state. After external return, append provider/surface/profile/dimension evidence and the external 4K QA result. Keep all of this metadata outside the image.

## End condition

End only when one of these is true:

- one source-bound packaging-board candidate has been generated with a disclosed prompt and awaits inspection;
- geometry/layout and exact-copy claims have been independently classified from retained evidence;
- a finalized 16:9 external 4K handoff has been emitted after inspection and any returned artifact has been classified as `verified` or `rejected` without allowing generative enhancement to approve exact copy;
- missing sources or runtime verification capability has been reported without substituting visual plausibility for exactness.
