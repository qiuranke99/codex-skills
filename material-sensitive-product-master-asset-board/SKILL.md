---
name: material-sensitive-product-master-asset-board
description: "Use when the user provides product reference images for transparent, glass, acrylic, translucent, liquid, cream, crystal-cut, mirror-metal, high-reflective, frosted, multi-layer-shell, perfume, skincare, or cosmetics packaging products and needs one video-ready Material-Sensitive Product Master Asset Board. Directly call Codex built-in /image gen to generate exactly one 16:9 master board with a strong hero anchor, complementary angles, material-response closeups, critical structure details, optional logo/text micro reference, and optional state window; output the exact final image-generation prompt used. Do not use for low-risk simple six-view products, label-copy-first packaging boards, complex mechanical structures, scene boards, character boards, ad posters, or prompt-only output."
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
- mechanical topology, joints, interfaces, folding/open-close structure, or multiple engineering states are the primary risk: use `complex-structure-product-asset-lock-board`;
- the user wants a scene, character, cinematic still, ad poster, lifestyle visual, e-commerce layout, prompt rewrite, or marketing concept rather than a video-reference product asset board.

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

The board must be a single image with functional zones, not separate boards and not many repeated collages. Recommended total panel count is 7-10. Avoid 12+ tiny cells unless the user explicitly supplies enough evidence and legibility stays high.

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

Completion criterion: the generated image proves the product is not a generic plastic block.

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

Include at most one small state window only when the user's video use needs it:

- open/closed;
- cap off/on;
- content exposed;
- compact opened;
- component separated.

If state evidence is missing or state does not matter, omit this window.

Completion criterion: the state window adds unique video-use value and does not compete with the Primary Anchor Zone.

## Image Generation

Call Codex built-in `/image gen` directly when the input has a usable product visual reference. If the current interface exposes a different image-generation tool, use that tool as the `/image gen` equivalent. If no image-generation capability is callable, report a hard blocker; do not replace the deliverable with a prompt-only answer.

Before generation, freeze one public `final_image_generation_prompt`. Submit that exact prompt to `/image gen`. After generation, output the same prompt as `Image generation prompt:` in the chat. If the exact submitted prompt cannot be matched to the delivered image, the run is not approved with `prompt_mismatch`.

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

The prompt must preserve the uploaded product references as the only source of truth for product identity, proportions, colors, material response, visible structure, and visible label/logo position. Do not redesign, premiumize, simplify, beautify, relabel, recolor, rebrand, invent hidden structure, invent readable text, or add props, hands, people, lifestyle background, or a marketing scene.

Completion criterion: one generated image has been requested with a frozen final prompt, or missing image-generation capability is the only blocker.

## QA

Inspect the generated result before final reply. Use visual inspection when available.

Approve only when all gates pass:

- `primary_anchor_clear`: the hero view is complete, stable, largest or clearly dominant, and sufficient for product identity.
- `multi_angle_complementary`: 3-4 supporting views add non-redundant spatial information.
- `material_response_locked`: transparency, reflection, refraction, thickness, crystal, liquid/cream, matte/gloss, or layered material behavior is visible and consistent.
- `critical_structure_useful`: seam, cap, base, latch, mark, pump, inner tube, hinge, or other high-risk details are covered only where needed.
- `low_redundancy`: every panel has a separate job; no filler beauty crops or repeated angles.
- `single_board_contract`: exactly one master board is delivered; no second or third board is generated by default.
- `no_poster_pollution`: no title, marketing layout, scenic background, props, decorative typography, arrows, labels, numbers, captions, or prompt text appears inside the image.
- `video_reference_ready`: the board is clear enough to feed into downstream video models as a product reference.
- `prompt_bound`: the visible `Image generation prompt:` matches the final prompt submitted for the accepted image.

Fail the board if the hero anchor is too small, material closeups are abstract, high-gloss/refraction directions contradict each other, transparent thickness is wrong, small marks drift, seams or caps move across panels, text becomes fake marketing copy, or the output behaves like an ad poster.

Result levels:

- `approved`: one generated master board passes all QA gates.
- `conditional`: the board is useful, but one or more details are inferred or source-limited; reuse only with the listed caveats.
- `not_approved`: source is insufficient, image generation is unavailable, generated image fails the one-board/material/structure/no-poster contract, or prompt binding fails.

Completion criterion: the final response states one honest result level and any non-approved blocker.

## Repair

If the generated image fails and image generation remains available, run up to two repair generations. Repair one dominant issue at a time in this order:

1. remove poster, label, title, arrow, number, UI, watermark, or prompt-text pollution;
2. enlarge or stabilize the Primary Anchor Zone;
3. remove duplicated angles or filler panels;
4. fix material response, reflection, refraction, thickness, liquid/cream texture, or layered-shell consistency;
5. fix critical structure such as seam, cap, base, latch, mark, pump, hinge, inner tube, or bottom refraction;
6. fix logo/text micro-reference only when it is source-supported and not a label-copy workflow.

After repair, output only the final prompt used for the accepted generated image. If two repairs fail, stop and request the exact missing references, such as higher-resolution front, side, back, top, bottom, material macro, logo/label crop, open/closed state, or content closeup.

Completion criterion: no more than two repairs are attempted, and every delivered image remains a single master board.

## Output

Default user-facing reply should be concise and in Chinese. Show the generated single master-board image first when available, then include:

```text
Image generation prompt:
<exact final public prompt submitted to /image gen for the delivered image>

锁定摘要：
- 产品类型：
- 主锚点：
- 辅助角度：
- 材质响应：
- 关键结构：
- 文案 / logo：
- 状态小窗：
- source_status：verified / inferred / needs_source

验收结果：
- result_level: approved / conditional / not_approved
- primary_anchor_clear: pass / fail
- multi_angle_complementary: pass / fail
- material_response_locked: pass / fail
- critical_structure_useful: pass / fail / not_needed
- low_redundancy: pass / fail
- single_board_contract: pass / fail
- no_poster_pollution: pass / fail
- video_reference_ready: yes / no
- prompt_bound: pass / fail

缺失或限制：
- <only list real missing evidence or caveats>
```

Do not output long theory, multiple prompt variants, hidden reasoning, raw model logs, separate board plans as final deliverables, or a prompt-only answer unless the user explicitly requested no generation.

End condition: exactly one material-sensitive product master asset board has been generated or honestly blocked, the exact final image-generation prompt is shown in chat text, QA is complete, and the user can tell whether the board is safe for downstream video reference use.
