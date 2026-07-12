---
name: material-sensitive-product-master-asset-board
description: "Use when supplied references show one transparent, glass, acrylic, translucent, liquid, cream, crystal-cut, mirror-metal, high-reflective, frosted, or multi-layer product whose video consistency depends on material behavior. Generate one master board while requesting horizontal 16:9, then inspect it and publish one final main result containing the complete exact generation prompt and image-specific 4K enhancement prompt with both SHA-256 values. Preserve material/structure evidence, optional label micro-reference, and at most one source-supported state window. Do not use for low-risk six-view products, label-copy-first packaging, mechanisms, scenes, characters, posters, or prompt-only output."
---

# Material-Sensitive Product Master Asset Board

Contract version: `asset_board_contract_version: built_in_nonblocking_prompt_pair_v2`.

Chinese name: 特殊材质产品总资产板

Create one high-density, low-redundancy master asset-board image for a product whose video-generation stability depends on material behavior as much as shape. The leading rule is **one master board**: solve product identity, spatial understanding, material response, critical structure, and only necessary label/state evidence in one generated image while requesting horizontal 16:9. Completion also requires one final-channel main result that visibly contains both complete prompts and both hashes.

This skill is not a multi-board package, ordinary multi-angle product sheet, poster generator, marketing layout, beauty collage, or prompt-only workflow. Product correctness outranks visual showmanship.

## Scope

Use this skill when the user provides product visual references and the product has material-sensitive identity risk:

- transparent, translucent, glass, acrylic, crystal-cut, or visible inner/outer layers;
- liquid, cream, gel, powder compact, cushion compact, perfume bottle, skincare bottle/jar, or makeup case;
- mirror metal, chrome, high-reflective cap, glossy foil, frosted glass, matte translucent shell, or mixed finishes;
- material response is likely to drift: edge thickness, refraction, reflection boundary, highlight hardness, bottom refraction, seam, latch, cap mouth, pump, spray head, inner tube, visible liner, small mark, or content texture.

Use another workflow when:

- the product is simple, opaque, low-risk, and only needs a six-view identity board: use `multi-angle-product-identity-lock-board`;
- exact packaging copy, label hierarchy, ingredients, specs, or certification text is the primary risk: use `packaging-product-identity-label-lock-board`;
- mechanical topology, joints, interfaces, folding/open-close structure, or multiple engineering states are the primary risk: do not use this material-sensitive skill; handle the task with main-agent/custom-agent workflow unless a dedicated active production skill exists;
- the user wants a scene, character, cinematic still, ad poster, lifestyle visual, e-commerce layout, prompt rewrite, or marketing concept rather than a video-reference product asset board.

If label and material risks are both high, use a main-agent compound workflow that coordinates this material contract with `packaging-product-identity-label-lock-board`; neither skill may claim complete coverage alone. Keep the three product skills independent and route by the five-part risk vector below.

If no usable product image exists, ask for product reference images instead of generating from imagination.

Completion criterion: the task is accepted only when one material-sensitive product can be truthfully locked from the supplied visual references.

## Input

Study every provided product image before generation. Build a compact source map:

- `identity_risk`: silhouette complexity, proportion drift, inner/outer relationship, deformable global shape;
- `material_risk`: transparency, translucency, glass, acrylic, mirror/high-reflective metal, frosted finish, liquid, cream, crystal facets, refraction edge, mixed materials;
- `structure_risk`: seam, latch, cap, pump, spray head, inner tube, liner, base, bottom refraction, edge thickness, small mark, turn face, connector, hinge-like cosmetic case detail;
- `label_risk`: logo, brand name, Chinese/English product name, capacity, key product copy, label position;
- `state_risk`: open/closed, cap off/on, content revealed, component split, use state, half-open transition.

Classify every useful detail as:

- `verified`: visible or supplied clearly enough to preserve;
- `inferred`: plausible but not directly supplied; may appear only as a bounded visual inference, never as source truth;
- `needs_source`: important but hidden, blurred, cropped, contradictory, too small, or not supplied.

Do not merge conflicting product variants into one object. If references disagree, preserve the highest-authority same-product reference and report the conflict.

Completion criterion: the board plan knows which identity, material, structure, label, and state details are verified, inferred, or blocked.

## Board Specification

Generate exactly one single master asset-board image and put `horizontal 16:9` in the built-in prompt as the sole creative ratio request. The built-in tool exposes no ratio or size argument, so record the original returned file's dimensions and observed ratio without turning them into a pass/fail condition. A `1672x941`, `1536x1024`, or other returned size remains `codex_board_role: content_qa_reference` when the material/content contract passes. Do not crop or stretch it; the external stage must rebuild from that board plus the original references using its own exact 16:9 and 4K controls. Use a clean neutral studio product-reference presentation on white or light gray, with soft shadows, crisp edges, and no decorative scene.

The board must be a single image with functional zones, not separate boards and not many repeated collages. Recommended total panel count is 7-10, including the hero, supporting views, closeups, label zone, and state window. Before generation, record a `panel_capacity_budget` and assign one evidence job to every panel. Reduce panel count when any planned material boundary, structure detail, or product-native label becomes indistinguishable at the intended downstream reference size. Never shrink proof regions merely to fit more panels. `panel_legibility_status` must remain `unverified` until the returned artifact is inspected.

### Primary Anchor Zone

Make this the largest visual zone.

- Show one complete, stable hero product view: front or 3/4 view depending on which best defines identity.
- Preserve real silhouette, proportions, color distribution, material layering, cap/body relationship, and visible label/logo placement.
- Do not crop the product, exaggerate perspective, make the anchor smaller than detail cells, or let supporting panels compete with it.

Completion criterion: this hero anchor can stand alone as the default video-model identity reference.

### Multi-Angle Zone

Use only the 3-4 most complementary supporting angles.

Choose from front, 3/4, side, top, bottom, and back. Include back only when back structure or label matters. Include top/bottom when edge thickness, cap, compact hinge, bottle base, or bottom refraction matters.

Do not repeat near-identical frontal views or minor angle variations. Every supporting angle must add spatial information the Primary Anchor Zone cannot supply.

Completion criterion: the product's three-dimensional form is clarified without duplicated view families.

### Material Response Zone

This is the reason this skill exists. Include only high-value closeups that teach the video model how the product responds to light.

Prioritize the relevant verified zones:

- transparent shell thickness;
- glass edge refraction;
- crystal facets;
- mirror-metal highlight boundary;
- glossy versus frosted surface behavior;
- liquid, cream, gel, powder, or balm texture;
- inner/outer layer depth relationship;
- base or bottom refraction;
- seam edge, latch, small mark, cap mouth, pump core, spray head, inner tube, visible liner, or compact hinge;
- label adhesion, embossing, foil, printed area, or logo surface only when it affects material identity.

Every closeup must still read as part of the same product. Do not create abstract material art or unrelated beauty macro crops.

Completion criterion: the planned closeups provide source-consistent material evidence rather than merely suggesting a generic material style.

### Critical Structure Zone

Add a few structure details only when they reduce drift:

- seam line, cap-body join, bottle neck, jar rim, pump/spray assembly, compact hinge, latch, base ring, inner liner, black mark, bottom ring, or content boundary.

This zone may overlap with the Material Response Zone. Delete duplicate details rather than filling space.

Completion criterion: the most failure-prone local structure is visible once, with enough context to locate it on the product.

### Optional Label / Logo Zone

Include this only when logo, product name, capacity, or label position is important.

- Keep it small and reference-like.
- Preserve layout relation and position before chasing perfect microcopy.
- Do not invent new marketing copy, legal text, ingredients, certifications, slogans, or a large packaging ad layout.
- If exact readable text is critical, route to `packaging-product-identity-label-lock-board` instead.

Completion criterion: text/logo evidence supports product identity without turning the board into a label-copy workflow.

### Optional State Window

Include at most one small state window only when the user's video use needs it and the exact shown state is directly visible in a supplied source:

- open/closed;
- cap off/on;
- content exposed;
- compact opened;
- component separated.

Mark a state `source_supported` only when the supplied references visibly show that same state and its relevant interfaces. Do not infer an open state from a closed product, a separated component from an assembled product, or exposed content from an opaque source. If state evidence is missing, contradictory, or unnecessary, omit the window and set `state_window_status: omitted_needs_source` or `omitted_not_needed`.

Completion criterion: the state window adds unique video-use value and does not compete with the Primary Anchor Zone.

## Runtime, prompt binding, and generation

Inspect the currently exposed interface and record only observed capabilities:

```text
runtime_capability_snapshot:
- image_generation_callable: supported / unsupported / unknown
- reference_images_attachable: supported / unsupported / unknown
- explicit_aspect_ratio_argument: supported / unsupported / unknown
- explicit_size_argument: supported / unsupported / unknown
- built_in_prompt_aspect_ratio_request: horizontal 16:9
- built_in_prompt_alternate_aspect_ratios_allowed: false
- returned_file_inspectable: supported / unsupported / unknown
- post_generation_text_allowed_same_turn: supported / unsupported / unknown
- pixel_dimensions_inspectable: supported / unsupported / unknown
- hashing_available: supported / unsupported / unknown
```

Do not infer capability from prompt wording. If image generation or reference attachment is unavailable, report `blocked_capability`; do not replace the deliverable with prompt-only output. Set `built_in_dimensions_policy: evidence_only_nonblocking`: built-in dimensions and ratio are observations, never material/content QA, repair, role-demotion, finalization, or external-handoff gates.

Build one public `final_generation_prompt`. Before generation:

1. freeze the exact prompt bytes;
2. write those exact bytes to `<asset_id>_generation_prompt.md`, re-read the file as bytes, and calculate `generation_prompt_sha256` from the re-read bytes;
3. stop with `blocked_generation_prompt_persistence` if write, re-read, or hash verification fails; never reconstruct the prompt later;
4. show the complete prompt in chat;
5. set `prompt_disclosed_before_generation: true` only when the shown, persisted, hashed, and submitted bytes are identical;
6. set `terminal_generation_call: pending`, `assistant_qa_status: pending_post_generation_inspection`, and `production_approval_status: not_granted`.

Before generation, an enhancement prompt may exist only as `draft_4k_enhancement_prompt`. Label it `4k_enhancement_prompt_status: draft_pre_generation`; do not call it final and do not publish a final-prompt hash. The actual board must be visually inspected before `final_4k_enhancement_prompt` is frozen.

Then submit that exact prompt and the product references. Treat the image-generation call as the terminal action of that assistant turn. Do not append reconstructed prompt text, QA, or commentary after the call when the runtime forbids post-generation text. If artifact inspection is available only in a later continuation, inspect and report QA there. A repair uses the same disclose/hash/terminal-call sequence.

Before the terminal call, set `task_finalization_status: generation_terminal_pending`. The tool/runtime call trace is the evidence for changing `terminal_generation_call` from `pending` to `executed`; never predeclare execution. Only an executed trace promotes the task to `awaiting_post_generation_continuation`. The generation turn is then only `stage_complete`, never task-complete. If the host does not automatically continue, leave that derived awaiting state with `main_result_prompt_pair_status: pending`. The next continuation must inspect the actual board and finish prompt-pair finalization. A failed or missing call never enters the awaiting state.

When the trace proves `executed` and the board is available but not yet inspected, set `4k_enhancement_prompt_status: awaiting_post_generation_inspection`. Advance to `finalized_post_inspection` only after the actual board passes the post-generation inspection gate.

The prompt must instruct the image model to create:

- one single 16:9 master asset board;
- one strong hero anchor;
- complementary multi-angle product views;
- a material response zone;
- a critical structure detail zone;
- optional logo/text micro zone only when necessary;
- optional state window only when necessary;
- clean neutral studio reference-board presentation;
- high-density information, low redundancy;
- product correctness first;
- no poster styling;
- no unnecessary decorative layout;
- no prompt text, headings, labels, view names, arrows, numbers, legends, UI, watermarks, or explanatory copy inside the generated image.

The prompt must preserve uploaded product references as the only source of truth for product identity, proportions, colors, visible material evidence, structure, label/logo position, and any optional state. Do not turn a prompt target into an observed claim. Do not redesign, premiumize, simplify, beautify, relabel, recolor, rebrand, invent hidden structure or state, invent readable text, or add props, hands, people, lifestyle background, or a marketing scene.

Generation-stage criterion: one generated image has been requested with a frozen persisted prompt, or missing image-generation capability is the only blocker. This leaves the task awaiting post-generation continuation; it is not the task-completion criterion.

## Artifact QA and approval separation

Inspect the actual returned artifact in a separate continuation when necessary. Keep prompt targets, source facts, and artifact observations separate.

Set `assistant_qa_status: passed` only when all observable gates pass:

- `primary_anchor_clear`: the hero view is complete, stable, largest or clearly dominant, and sufficient for product identity.
- `multi_angle_complementary`: 3-4 supporting views add non-redundant spatial information.
- `material_evidence_present`: the required transparency, reflection, refraction, thickness, crystal, liquid/cream, matte/gloss, or layered-shell evidence is visibly present.
- `material_source_consistent`: visible material boundaries and responses are consistent with supplied references; use `unverified` when the source cannot support comparison.
- `critical_structure_useful`: seam, cap, base, latch, mark, pump, inner tube, hinge, or other high-risk details are covered only where needed.
- `low_redundancy`: every panel has a separate job; no filler beauty crops or repeated angles.
- `panel_legibility_status`: each risk-bearing panel remains distinguishable at intended downstream reference size.
- `single_board_contract`: exactly one master board is delivered; no second or third board is generated by default.
- `no_poster_pollution`: no title, marketing layout, scenic background, props, decorative typography, arrows, labels, numbers, captions, or prompt text appears inside the image.
- `video_reference_ready`: the board is clear enough to feed into downstream video models as a product reference.
- `state_window_source_supported`: pass / fail / not_used.
- `prompt_bound`: the disclosed `final_generation_prompt` matches the prompt submitted for the inspected image.

Record `built_in_dimensions_policy: evidence_only_nonblocking`, `built_in_observed_pixel_dimensions`, and `built_in_observed_aspect_ratio` outside this pass/fail list. Those observations cannot make content QA passed, conditional, or failed.

Fail the board if the hero anchor is too small, material closeups are abstract, high-gloss/refraction directions contradict each other, transparent thickness is wrong, small marks drift, seams or caps move across panels, text becomes fake marketing copy, or the output behaves like an ad poster.

Use separate result levels:

- `assistant_qa_status: passed`: all observable board gates pass against available source evidence;
- `assistant_qa_status: conditional`: useful board, but some material, structure, label, panel, or state evidence is source-limited or unverified;
- `assistant_qa_status: failed`: a critical one-board, identity, material, legibility, source-state, no-poster, or prompt-binding gate fails;
- `assistant_qa_status: pending_post_generation_inspection`: no independent artifact inspection has occurred;
- `production_approval_status: not_granted / user_granted / external_pipeline_granted`.

Assistant QA never silently grants production approval or registry admission. Material styling that looks plausible is not evidence that the material is source-consistent.

Completion criterion: the final response states one honest result level and any non-approved blocker.

## Post-inspection external 4K handoff

After inspecting the actual Codex board, create a board-specific 4K handoff for Nano Banana Pro, Nano Banana 2, or a comparable image-to-image model. Use **both** the inspected Codex board and every authoritative original product reference, including material macros and state references used by the source map. A board-only enhancement is incomplete because low-resolution pixels cannot prove material microstructure or hidden construction.

Freeze a public English `final_4k_enhancement_prompt` that names the observed panel-level defects and preserves:

- the exact board topology, dominant hero, complementary views, material/structure crops, optional label zone, optional state window, and neutral studio presentation;
- source-supported refraction and reflection boundaries, transparent/translucent layer relationships, glass or acrylic edge thickness, liquid/cream/gel fill level and content boundary, crystal facets, frosted/matte/gloss separation, seams, caps, bases, pumps, liners, tubes, and real highlight direction;
- genuine material evidence such as controlled grain, microbubbles, refraction edges, fine seams, and surface transitions; apply local cleanup only to identified generation artifacts rather than globally smoothing evidence-bearing areas;
- source-supported micro-detail only, leaving unresolved structure unresolved instead of inventing highlights, internal parts, liquid states, facets, labels, or mechanisms;
- one 16:9 result using the provider's actual 4K profile, with no crop, stretch, reframing, panel reorder, extra panel, beauty-ad styling, or non-product-native text.

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
- original_source_references: <all authoritative product and material references>
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

External 4K QA must re-run all board QA and additionally pass `material_boundaries_preserved`, `transparent_layers_and_thickness_preserved`, `fill_level_and_content_state_preserved`, `reflection_refraction_highlights_source_consistent`, `no_over_denoising`, `no_invented_structure_or_material`, `external_reference_bundle_complete`, `external_16_9_verified`, and `external_4k_profile_verified`. A passing result is an externally generated/enhanced 4K artifact; never relabel it as Codex-native 4K.

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

Include both published statuses in that final block. Successful emission of the complete block is the transition evidence; require no write or status mutation after the terminal final response. Until emission succeeds, the task remains incomplete even when the board, sidecars, material QA, or handoff already exist.

## Repair

If the generated image fails and image generation remains available, run up to two repair generations. Repair one dominant issue at a time in this order:

1. remove poster, label, title, arrow, number, UI, watermark, or prompt-text pollution;
2. enlarge or stabilize the Primary Anchor Zone;
3. remove duplicated angles or filler panels;
4. fix material response, reflection, refraction, thickness, liquid/cream texture, or layered-shell consistency;
5. fix critical structure such as seam, cap, base, latch, mark, pump, hinge, inner tube, or bottom refraction;
6. fix logo/text micro-reference only when it is source-supported and not a label-copy workflow.

Before each repair call, disclose and hash the exact repair `final_generation_prompt`; then make the repair image call the terminal action of that turn. If two repairs fail, stop and request the exact missing references, such as higher-resolution front, side, back, top, bottom, material macro, logo/label crop, source-supported state, or content closeup.

Completion criterion: no more than two repairs are attempted, and every delivered image remains a single master board.

## Output

Before the terminal image-generation call, provide concise Chinese text:

```text
锁定摘要：
- 产品类型：
- 主锚点：
- 辅助角度：
- 材质证据：verified / inferred / needs_source
- 关键结构：
- 文案 / logo：
- 状态小窗：source_supported / omitted_needs_source / omitted_not_needed
- source_status：verified / inferred / needs_source
- panel_capacity_budget：pass / constrained / blocked
- runtime_capability_snapshot：...

built_in_prompt_aspect_ratio_request: "horizontal 16:9"
built_in_prompt_alternate_aspect_ratios_allowed: false
built_in_dimensions_policy: evidence_only_nonblocking
codex_board_role: pending_content_qa
final_generation_prompt:
<exact prompt that will be submitted>
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

In the later inspection step, report:

```text

验收结果：
- assistant_qa_status: passed / conditional / failed / pending_post_generation_inspection
- production_approval_status: not_granted / user_granted / external_pipeline_granted
- primary_anchor_clear: pass / fail
- multi_angle_complementary: pass / fail
- material_evidence_present: pass / fail
- material_source_consistent: pass / fail / unverified
- critical_structure_useful: pass / fail / not_needed
- low_redundancy: pass / fail
- panel_legibility_status: pass / fail / unverified
- single_board_contract: pass / fail
- no_poster_pollution: pass / fail
- video_reference_ready: yes / no
- state_window_source_supported: pass / fail / not_used
- prompt_bound: pass / fail
- built_in_dimensions_policy: evidence_only_nonblocking
- built_in_observed_pixel_dimensions: width x height / unavailable
- built_in_observed_aspect_ratio: value / unavailable
- external_4k_status: not_ready / handoff_ready / blocked_runtime_controls / pending_external_generation / returned_unverified / verified / rejected

缺失或限制：
- <only list real missing evidence or caveats>
```

Keep the handoff concise, then publish the complete prompt pair in the final-channel main result exactly as required above. After external return, append provider/surface/profile/dimension evidence and external 4K QA. A prompt-only request routes outside this Skill and is not a successful run.

The image-generation turn may end only as `stage_complete` with `task_finalization_status: awaiting_post_generation_continuation`. The task completes only when material/content QA is classified, the source-bound exact-16:9/4K handoff is ready or honestly runtime-blocked, and `task_finalization_status: final_main_result_published` proves the final channel displayed both complete prompts and both verified hashes. Source, capability, persistence, or prompt-integrity failures may end the run without a completion claim. Any returned external artifact remains externally generated and is classified without being relabeled as native.

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
