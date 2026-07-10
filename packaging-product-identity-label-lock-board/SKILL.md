---
name: packaging-product-identity-label-lock-board
description: Use when supplied bottle, box, pouch, can, tube, jar, carton, bag, or other label-heavy packaging references need one clean video-reference board that separates geometry and label-layout consistency from exact-copy verification. Generate a source-bound multi-angle board, but approve exact text, logos, QR codes, barcodes, specifications, or certifications only with source assets and deterministic composition or field-level OCR/decode evidence. Do not use for simple low-text products, material-first glass/liquid/reflective products, mechanisms, scenes, or posters.
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

Generate exactly one board image. Use a neutral white, light-gray, or neutral-gray studio presentation with even lighting, complete uncropped products, and no dramatic scene.

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
- returned_file_inspectable: supported / unsupported / unknown
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

Then submit the exact prompt with all source references. The image-generation call is the terminal action of that assistant turn. Do not append a prompt, QA, or commentary after the call when the runtime forbids post-generation text.

The tool/runtime call trace is the evidence for changing `terminal_generation_call` from `pending` to `executed`; never predeclare execution. Without a separate subsequent visual inspection, leave `assistant_qa_status: pending_post_generation_inspection` and `production_approval_status: not_granted`.

The prompt must request one clean board, consistent package geometry, the planned views and details, source-bound label layout, no invented readable text, and no non-product-native text. It must not claim that generation alone will produce verified exact copy.

If the runtime allows inspection only in a later continuation, perform artifact QA, OCR/decode, or deterministic compositing there. Any repair generation follows the same sequence: disclose and hash the repair prompt, then use the image call as the turn's terminal action.

## Artifact QA and exact-copy verification

In a separate inspection step, assess:

```text
geometry_layout_lock_status: passed / conditional / failed / unverified
angle_source_status: passed / conditional / failed
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

## Repair rules

Attempt at most two generative repairs. Repair one dominant issue at a time:

1. geometry or cross-view identity;
2. missing/cropped/repeated views;
3. label position or hierarchy;
4. non-product text pollution;
5. material or panel legibility.

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

final_generation_prompt:
<exact prompt that will be submitted>
generation_prompt_sha256: <sha256 / unavailable>
prompt_disclosed_before_generation: true / false
terminal_generation_call: pending
assistant_qa_status: pending_post_generation_inspection
production_approval_status: not_granted
```

In the later inspection step, report the two lock-layer statuses, field evidence rows, limitations, registry eligibility, and production-approval state. Keep all of this metadata outside the image.

## End condition

End only when one of these is true:

- one source-bound packaging-board candidate has been generated with a disclosed prompt and awaits inspection;
- geometry/layout and exact-copy claims have been independently classified from retained evidence;
- missing sources or runtime verification capability has been reported without substituting visual plausibility for exactness.
