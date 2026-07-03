---
name: packaging-product-identity-label-lock-board
description: "Use when the user provides packaging, bottle, box, pouch, can, tube, jar, carton, bag, or other label-heavy product references and needs one clean generated Packaging Product Identity + Label Lock Board for downstream ad image or video generation. Directly call Codex built-in /image gen to lock 8 video-ready product angles, logo, label layout, exact key copy, specs, certifications, and material details, then output the final image-generation prompt as chat text; never replace the image with prompt-only output."
---

# Packaging Product Identity + Label Lock Board

Chinese name: 包装产品身份与标签文案双锁定资产板

Generate one clean composite image asset board for a packaging product whose geometry, surface information, and video perspective must stay stable. The deliverable is the generated image, the final image-generation prompt used for that image, and concise QA.

The leading rule is **clean board**: the generated image may contain only the product body, product views, product detail crops, and text/logos/patterns that truly exist on the product packaging. The image-generation prompt, asset names, labels, status, view names, explanations, and registry text stay in the chat reply, not inside the image.

## Scope

Use this skill for packaging or label-heavy products such as bottles, boxes, pouches, cans, tubes, jars, cartons, bags, and wrapped products when any of these are true:

- the product surface includes logo, brand name, product name, title, subtitle, claims, ingredients, specs, certifications, barcode, QR code, back-label copy, or dense packaging text;
- the user says labels, copy, logo, text, or packaging shape must not change;
- the result will be used for orbit, side move, rotation, reveal, hand-turn, high-angle, low-angle, close product-shot, or other video generation;
- both `geometry / identity` and `label / copy / logo / surface` must be locked before advertising image or video work.

Use a different workflow when:

- text is minimal and only shape needs locking: use `multi-angle-product-identity-lock-board`;
- the hard problem is mechanical structure, supports, joints, connectors, or engineering parts: use a complex-structure lock workflow if available;
- the hard problem is folded/unfolded, open/closed, deployed/stored, or use-state variation: use a state-change lock workflow if available;
- the user only wants an ad poster, mood image, or scene concept: explain that product asset locking should come first.

Completion criterion: the task is accepted only when packaging surface information or video perspective stability is a core success factor.

## Input Audit

Audit inputs before generation. Treat a product visual reference as required for a real lock; descriptions alone are not enough to lock product identity.

Check whether the user provided:

- front, back, left, right, top, and bottom product views;
- unfolded package, flat label artwork, high-resolution label closeups, or logo file;
- brand name, product name, front title, subtitle, claims, capacity, size, variant, flavor, or specification;
- back-label copy, ingredients, parameters, usage, warnings, barcode, QR code, or certification marks;
- whether all text must be readable, only core text must be exact, or tiny text may remain texture-level;
- whether the product will be used for high-angle, low-angle, orbit, rotation, reveal, hand-turn, side move, or close product-shot video.

Mark every angle and surface text region as:

- `approved`: supplied or visible with enough source quality to verify;
- `inferred`: generated from visible packaging logic, not a true supplied source;
- `needs_source`: required for precision but missing, blurred, hidden, cropped, too small, or not supplied.

If no product visual reference exists, ask for the target product image, packaging artwork, or label files. Do not invent a brand/product lock from imagination.

Completion criterion: the run has a source map for angles, text, logo, material, and video perspectives before `/image gen`.

## Angle Gate

Default to 8 core product angles for video-ready packaging lock:

1. front;
2. back;
3. left side;
4. right side;
5. 3/4 front;
6. 3/4 back;
7. high-angle overhead perspective;
8. low-angle upward perspective.

Use fixed visual order instead of text labels. Preferred layout:

- one row: front, back, left, right, 3/4 front, 3/4 back, high-angle, low-angle;
- or two rows when space requires it: front/back/left/right, then 3/4 front/3/4 back/high-angle/low-angle.

Do not write `Front`, `Back`, `Left`, `Right`, `Top`, `Bottom`, `High Angle`, `Low Angle`, or any equivalent view label inside the image.

Apply confidence rules:

- If front, back, left, and right references are supplied, generate a high-confidence 8-angle board.
- If top and bottom references are supplied, high-angle and low-angle perspectives may be high confidence.
- If top or bottom references are missing, still generate high-angle and low-angle views for video usefulness, but mark them as `inferred`.
- If only a front view exists and video use is requested, generate a forward-use 8-angle exploration board and mark non-front angles as `inferred`.
- A forward-use exploration board is not a fully approved lock board. If back, side, top, or bottom sources are missing, the result can be at most `conditional` unless the missing faces are irrelevant to the user's requested lock.
- If exact back, side, top, or bottom label copy is required without matching source, state: `缺少该角度的真实参考，无法保证该面标签逐字准确。`
- Treat high-angle and low-angle views as video perspective references. They do not verify top labels, bottom labels, seals, cap codes, bottom marks, barcodes, or unseen structure unless the matching source reference was supplied.
- Never present inferred angles as approved source truth.

Completion criterion: every output angle can be reported as `approved`, `inferred`, or `needs_source`.

## Copy Risk Classes

Classify text before generation:

- `A_exact`: brand name, logo, product name, front main title, front hero claim, capacity/specification, user-named exact text, and large clear front text.
- `B_targeted`: back-label key copy, parameters, ingredients, usage, warnings, side-panel information, secondary claims, certification text.
- `C_texture`: tiny dense text that is unreadable at normal reference scale and not requested word-for-word.

If the user asks for all text to be fully correct, treat A/B/C as `A_exact`.

Rules:

- Do not fabricate unseen back-label copy, certification marks, barcode, QR code, legal text, logo, or product claim.
- Do not use gibberish as if it were real copy.
- If exact text is required but the source is inadequate, still generate a useful forward asset board when possible, but mark the missing text as `needs_source`.
- Require high-resolution label art or exact source text when word-for-word fidelity is a hard requirement.
- One clean board cannot prove all dense microcopy word-for-word unless the user supplied high-resolution label or text sources. Approve only core readable copy and explicitly supplied closeup crops; keep unsupported dense back-label text as `needs_source` or `C_texture`.
- Do not approve the board into the asset registry when any `A_exact` item is wrong or unverifiable.

Completion criterion: exact-copy claims never exceed the available source evidence.

## Board Specification

Generate one single clean image, not multiple images and not separate board files.

The board must visually combine:

- 8 core product views for geometry and perspective stability;
- close product crops for logo, front title, front key claim, capacity/spec, supplied back-label key area, supplied ingredients/specs/certifications, barcode/QR/certification detail when relevant;
- 1-3 material/detail crops for label adhesion, paper, plastic, glass, metal, matte, gloss, transparent or translucent material, liquid level, print, embossing, foil, lamination, reflection, texture, cap/lid, shoulder, edge, seal, tube opening, base thickness, or package corner construction.

Allowed inside the image:

- the real product;
- real packaging text, logo, label, and graphic patterns that belong to the product;
- detail crops of the same product;
- clean whitespace;
- very subtle non-text separators if useful.

Forbidden inside the image:

- board title, section title, view label, asset ID, date, approval status, source status, legend, footnote, instructional text, caption, table, UI frame, callout line, arrow, number, status color block, diagram label, or any non-product-native text;
- `Front`, `Back`, `Left`, `Right`, `Top`, `Bottom`, `High Angle`, `Low Angle`, `Source of truth`, `Approved`, `Inferred`, `Needs source`, `@product_front`, or similar strings;
- infographic, presentation slide, design spec sheet, annotated board, technical manual, PPT, e-commerce detail page, or poster composition.

Asset registry IDs are text-only output after generation:

- `@product_packaging_lock_board`
- `@product_front`
- `@product_back`
- `@product_left`
- `@product_right`
- `@product_3q_front`
- `@product_3q_back`
- `@product_high_angle`
- `@product_low_angle`
- `@product_logo_detail`
- `@product_copy_detail`
- `@product_material_detail`

Completion criterion: the generated image is a clean visual reference board with no non-product text pollution.

## Image Generation

Call the available Codex image-generation capability directly. Use Codex built-in `/image gen` when exposed by the interface. If no image-generation tool is callable, report a hard blocker; do not replace the deliverable with prompt-only output.

Build a concrete `final_image_generation_prompt` from the input audit, source map, angle gate, copy classes, and board specification before generation. Use that prompt for `/image gen`. After generation, output that exact prompt in the chat as `本次图片生成提示词`.

The prompt is a user-facing production handoff artifact. It is also non-product-native text, so it must stay outside the generated image. Do not output hidden reasoning, private deliberation, raw tool metadata, or model-call logs. If repair generations are used, output the final prompt used for the delivered image and state the revision count; include earlier repair prompts only when the user explicitly asks.

Internal generation constraints:

- use uploaded product references as the only product identity source;
- preserve packaging outline, volume, proportions, thickness, curvature, edge logic, box depth, pouch inflation, bottle shoulder, cap, lid, pump, tube opening, can rim, jar body, seal, top, bottom, and closure structure;
- preserve brand name, product name, logo, label position, label size relationship, layout hierarchy, color placement, material type, finish, and approved copy;
- keep unverifiable dense microcopy as texture-level only; never invent readable fake copy;
- generate a clean white, light gray, or neutral gray studio reference board with even product lighting, no strong depth of field, no motion blur, no dramatic shadows, no lifestyle setting, no props, no hands, and no people;
- make the 8 views belong to the same product and make closeups consistent with the full product views;
- do not redesign, premiumize, modernize, simplify, rebrand, relabel, recolor, resize, restyle, or advertise the product;
- do not add any non-product-native words, labels, headings, asset names, numbers, arrows, callouts, UI panels, status marks, or explanatory graphics inside the image.

Completion criterion: `/image gen` has been called for one clean composite image board and the final image-generation prompt is available for the chat reply, or missing image-generation capability has been reported as the only blocker.

## QA Gate

Inspect the generated image before final reply. Use visual inspection tools when available.

Check geometry:

- package shape, proportion, silhouette, volume, thickness, top, bottom, cap/lid/seal, edge/corner, tube opening, bottle shoulder, and base relationships are correct;
- front, back, side, 3/4, high-angle, and low-angle views belong to the same product;
- high-angle and low-angle perspectives are plausible for video use and do not replace the product with pure technical top/bottom views unless requested;
- no deformation, invented structure, missing closure, wrong box depth, wrong pouch inflation, or wrong bottle/can/tube geometry appears.

Check label/copy/logo:

- brand name, logo, product name, front title, hero claim, capacity/spec, and other A-class text are correct where source allows;
- label position, scale, hierarchy, color blocks, and local detail crops match the product views;
- no gibberish, fake logo, invented claim, invented back-label text, missing hero text, or copy drift appears;
- inferred surfaces are not treated as approved.

Check material:

- packaging material and finish match the source;
- transparent, translucent, liquid, matte, gloss, metallic, glass, foil, holographic, embossed, laminated, printed, reflective, and label-adhesion relationships are plausible and stable.

Check non-product text pollution:

- no title, section heading, view label, asset name, date, approval status, source status, note, legend, table, UI frame, arrow, number, callout line, or explanatory graphic appears;
- any non-product-native text inside the image is a failure.

Check video usability:

- board can support orbit, side move, rotation, reveal, hand-turn, close product-shot, high-angle, and low-angle references;
- enough views and detail crops exist for downstream image/video models;
- image reads as a clean asset reference board rather than an ad poster, infographic, spec sheet, or presentation slide.

Check prompt trace:

- final reply includes `本次图片生成提示词`;
- the prompt corresponds to the final delivered image, not an abandoned draft;
- the prompt is consistent with the source map, clean-board ban, 8-angle requirement, and repair state;
- the prompt does not expose hidden reasoning, private deliberation, raw tool metadata, or model-call logs.

Result levels:

- `approved`: geometry, A-class text, logo, label placement, material, 8-angle perspective, no-text-pollution, video usability, source map, and prompt trace pass.
- `conditional`: usable as a forward asset board, but some angles or copy are `inferred` or `needs_source`.
- `not_approved`: geometry, logo, A-class text, material identity, perspective, or clean-board rule fails.

Completion criterion: the final reply states one honest approval status and the blocking reason for any non-approved state.

## Repair Loop

If the generated result fails and image generation remains available, run up to two repair generations before final delivery.

Repair one main issue at a time in this priority order:

1. remove non-product text pollution;
2. fix structure or angle identity;
3. fix logo, label, or A-class copy;
4. fix high-angle or low-angle perspective;
5. fix material/detail behavior;
6. fix layout cleanliness.

Do not rewrite the whole board instruction when one issue dominates. After two repairs, stop and report which source material is needed:

- higher-resolution front image;
- back, left, right, top, or bottom image;
- unfolded package or flat label artwork;
- exact label text, back-label text, ingredients, specs, or certification files;
- logo file;
- material notes.

After each repair, rerun the full QA gate. A repair that removes prompt/text pollution but breaks logo, A-class copy, geometry, material, or source-state honesty is still a failure.

Completion criterion: no more than two repair generations are attempted, the final prompt corresponds to the delivered image, and any remaining blocker is tied to missing source evidence or generation failure.

## Output Contract

Default user-facing reply is concise and in Chinese:

1. include the generated single clean asset-board image or image result;
2. provide `本次图片生成提示词`, meaning the final image-generation prompt used for the delivered image;
3. provide the lock checklist;
4. provide QA acceptance;
5. state whether it can enter `Approved Packaging Asset Registry`;
6. list missing source materials when needed.

Keep the image-generation prompt, lock checklist, asset names, confidence labels, and QA results in chat text only. Do not put them inside the image.

Use this structure:

```text
本次图片生成提示词：
<输出最终用于本次 /image gen 的提示词。若经过修正，输出最终交付图对应的最终提示词。>

锁定清单：
- 品牌：
- 产品名：
- 已锁定角度：
- 已锁定标签面：
- 已锁定关键文字：
- 已锁定材质：
- 高置信度角度：
- 推断角度：
- 未确认信息：
- 是否进入视频资产库：

验收结果：
- 几何身份：通过 / 需修正
- 标签文案：通过 / 需修正
- logo：通过 / 需修正
- 材质：通过 / 需修正
- 俯视/仰视透视：通过 / 需修正 / 推断
- 非产品文字污染：无 / 有，需修正
- 视频可用性：是 / 否
- 是否进入 Approved Packaging Asset Registry：是 / 否

资产登记：
- @product_packaging_lock_board
- @product_front
- @product_back
- @product_left
- @product_right
- @product_3q_front
- @product_3q_back
- @product_high_angle
- @product_low_angle
- @product_logo_detail
- @product_copy_detail
- @product_material_detail
```

If the user provides a concrete product name, replace `product` in registry IDs with a short safe product slug when useful.

Do not default to:

- long theory;
- model-call details;
- prompt-only response;
- multi-image output;
- hidden reasoning or raw tool logs;
- generated image containing the prompt, non-product labels, headings, view text, asset IDs, or QA text.

End condition: one clean packaging product identity and label-copy lock board has been generated, the final image-generation prompt has been output as chat text, QA is complete, and the user can tell which angles and text are `approved`, `inferred`, or `needs_source` without any of that metadata polluting the image itself.
