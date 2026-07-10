---
name: material-sensitive-product-master-asset-board
description: "Use when supplied references show one transparent, glass, acrylic, translucent, liquid, cream, crystal-cut, mirror-metal, high-reflective, frosted, or multi-layer product whose video consistency depends on material behavior. Generate exactly one 16:9 master board with a dominant hero, complementary angles, source-supported material/structure evidence, optional label micro-reference, and at most one source-supported state window. Freeze and disclose the exact prompt before the terminal image call. Do not use for low-risk six-view products, label-copy-first packaging, mechanisms, scenes, characters, posters, or prompt-only output."
---

# Material-Sensitive Product Master Asset Board

Chinese name: 特殊材质产品总资产板

Create one high-density, low-redundancy master asset-board image for a product whose video-generation stability depends on material behavior as much as shape. The leading rule is **one master board**: solve product identity, spatial understanding, material response, critical structure, and only necessary label/state evidence in a single 16:9 generated image.

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

Generate exactly one single master asset-board image. Default ratio is 16:9 horizontal. Default style is clean neutral studio product-reference presentation on white or light gray, with soft shadows, crisp edges, and no decorative scene.

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
- returned_file_inspectable: supported / unsupported / unknown
- post_generation_text_allowed_same_turn: supported / unsupported / unknown
- pixel_dimensions_inspectable: supported / unsupported / unknown
- hashing_available: supported / unsupported / unknown
```

Do not infer capability from prompt wording. If image generation or reference attachment is unavailable, report `blocked_capability`; do not replace the deliverable with prompt-only output.

Build one public `final_generation_prompt`. Before generation:

1. freeze the exact prompt bytes;
2. show the complete prompt in chat;
3. calculate `generation_prompt_sha256` when hashing is available;
4. set `prompt_disclosed_before_generation: true` only when the shown bytes will be submitted unchanged;
5. set `terminal_generation_call: pending`;
6. set `assistant_qa_status: pending_post_generation_inspection`;
7. set `production_approval_status: not_granted`.

Then submit that exact prompt and the product references. Treat the image-generation call as the terminal action of that assistant turn. Do not append reconstructed prompt text, QA, or commentary after the call when the runtime forbids post-generation text. If artifact inspection is available only in a later continuation, inspect and report QA there. A repair uses the same disclose/hash/terminal-call sequence.

The tool/runtime call trace is the evidence for changing `terminal_generation_call` from `pending` to `executed`; never predeclare execution. Without a separate subsequent visual inspection, leave `assistant_qa_status: pending_post_generation_inspection` and `production_approval_status: not_granted`.

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

Completion criterion: one generated image has been requested with a frozen final prompt, or missing image-generation capability is the only blocker.

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

Fail the board if the hero anchor is too small, material closeups are abstract, high-gloss/refraction directions contradict each other, transparent thickness is wrong, small marks drift, seams or caps move across panels, text becomes fake marketing copy, or the output behaves like an ad poster.

Use separate result levels:

- `assistant_qa_status: passed`: all observable board gates pass against available source evidence;
- `assistant_qa_status: conditional`: useful board, but some material, structure, label, panel, or state evidence is source-limited or unverified;
- `assistant_qa_status: failed`: a critical one-board, identity, material, legibility, source-state, no-poster, or prompt-binding gate fails;
- `assistant_qa_status: pending_post_generation_inspection`: no independent artifact inspection has occurred;
- `production_approval_status: not_granted / user_granted / external_pipeline_granted`.

Assistant QA never silently grants production approval or registry admission. Material styling that looks plausible is not evidence that the material is source-consistent.

Completion criterion: the final response states one honest result level and any non-approved blocker.

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

final_generation_prompt:
<exact prompt that will be submitted>
generation_prompt_sha256: <sha256 / unavailable>
prompt_disclosed_before_generation: true / false
terminal_generation_call: pending
assistant_qa_status: pending_post_generation_inspection
production_approval_status: not_granted
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

缺失或限制：
- <only list real missing evidence or caveats>
```

Keep the handoff concise: one frozen prompt record, one board, and evidence-bounded status. A prompt-only request routes outside this Skill and is not a successful run.

End condition: exactly one material-sensitive product master asset board has been generated or honestly blocked, its exact prompt was disclosed before the terminal call, and QA/production states remain pending until independently supported by artifact evidence.
