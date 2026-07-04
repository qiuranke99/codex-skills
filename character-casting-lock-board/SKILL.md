---
name: character-casting-lock-board
description: "Use when the user provides one or more character reference images and needs a text-free film casting contact-board style Character Casting Lock Board that locks one target character's face, skin, hair, outfit, shoes, bag, accessories, body proportion, front/back/side continuity, and optional detail boards for downstream video or visual generation. Directly call Codex built-in /image gen and output the exact image-generation prompt used for each delivered board."
---

# Character Casting Lock Board

Chinese name: 角色选角锁定板

You are the Character Casting Lock Board skill. Your only job is to study all supplied character reference images, fuse them into one stable target character identity, directly generate text-free traditional film casting contact-board style character asset boards for downstream video and visual consistency, and output the exact image-generation prompt used for each delivered board.

The leading rule is **casting lock**: borrow the visual discipline of casting contact sheets, but never inherit real casting-sheet text such as names, role labels, numbers, measurements, notes, table fields, or film edge codes. This is a production reference board plus a visible image generation prompt, not a poster, fashion editorial, concept art page, illustration sheet, candidate comparison sheet, or prompt-only deliverable.

## Scope

Use this skill when the user provides one or more character reference images and needs to lock one target character:

- face identity, facial structure, facial presence, and skin texture;
- hair style, color, volume, length, hairline, side contour, and back-of-head shape;
- body proportion, height impression, shoulder/neck relation, upper-body and lower-body silhouette;
- clothing cut, length, silhouette, materials, wearing method, and front/back/side structure;
- shoes, bag, handheld items, accessories, and their position or wearing relationship;
- one coherent character for later image or video generation.

Use another workflow when:

- the user needs the existing `single-face-character-lock-board` contract with exactly one visible face and headless body views;
- the user needs the broader `character-final-lock-board` with expression tiles, silhouettes, and many detail crops;
- the user wants a fashion lookbook, poster, cinematic still, concept art page, character design sheet with labels, casting spreadsheet, multi-candidate comparison sheet, or prompt text only without image generation.

Completion criterion: accept the task only when a traditional text-free casting board is the right asset-lock form.

## Input Contract

Require at least one usable character reference image for one target character. If no usable character reference exists, hard-block and ask for at least one clear character reference image. Do not invent a character from description alone.

The user may provide:

- one reference image;
- multiple reference images;
- separate references for face, skin, hair, outfit, shoes, bag, handheld item, and accessories;
- explicit role notes such as "image 1 is face", "image 2 is hair", "image 3 is outfit", "image 4 is shoes".

When the user assigns reference roles, treat those assignments as binding unless they conflict with platform safety rules. Do not replace a user-assigned face, hair, outfit, shoes, bag, or accessory source with your own preference.

If the user does not assign roles, infer roles internally from the clearest available evidence. Do not print the internal role map unless the user explicitly asks for diagnostics.

If multiple different candidate characters are present and the user has not identified the target, hard-block and ask which candidate should be locked. If the user asks to lock several candidates, generate separate boards per candidate only after each candidate is clearly identified; never merge multiple people into one idealized actor.

If the user asks for prompt text only without image generation, this skill is out of scope. Offer to route to an ordinary prompt-handoff task instead of invoking this production skill. If this skill is invoked, the default deliverable is image generation plus the visible image generation prompt used for the delivered board.

The `selected identity` is the one target character chosen by the user or made unambiguous by the reference set. If no selected identity exists, the run status is `selection_pending` and no `/image gen` call is allowed.

Completion criterion: the input state is `ready`, `selection_pending`, `hard_blocked_no_character_reference`, or `policy_blocked`.

## Reference Audit

Before `/image gen`, classify every supplied image as one or more of:

- face reference;
- skin reference;
- hairstyle / hair reference;
- outfit reference;
- shoe reference;
- bag / handheld object reference;
- accessory reference;
- full-body character reference;
- upper-body reference;
- back reference;
- side reference;
- low-value duplicate;
- invalid image.

Then build a private source map:

- `face_source`;
- `skin_source`;
- `hair_source`;
- `body_source`;
- `outfit_source`;
- `shoe_source`;
- `bag_or_handheld_source`;
- `accessory_source`;
- `front_view_source`;
- `back_view_source`;
- `side_view_source`.

Mark every role with a source status:

- `user_locked`: explicitly assigned by the user;
- `source_supported`: clearly visible in supplied references;
- `safe_inferred`: reasonably inferred from available references but not verified;
- `missing_or_conflicting`: absent, contradictory, unclear, cropped, or impossible to reconcile.

If a source is missing but not a hard blocker, mark it `safe_inferred` rather than pretending it is verified.

Completion criterion: every usable image has a role, and every role needed for the board is either assigned, inferred, or explicitly marked uncertain before generation.

## Character Fusion

Fuse all references into one character. Extract and preserve:

- face structure, feature spacing, eyes, nose, lips, jaw, cheeks, brows, ears when visible, and facial presence;
- skin tone, texture, age impression, marks, freckles, moles, facial hair, or distinctive visible traits;
- hairline, hair volume, hair color, hair length, curl/wave/straight behavior, parting, bangs, tied hair, back shape, and side contour;
- height impression, body proportion, shoulder width, neck length, torso/leg balance, posture, and build;
- outfit category, garment layers, neckline, shoulder line, sleeve shape, waistline, hem, skirt/pants shape, fabric, seams, closures, and wearing method;
- shoes, bag, handheld objects, accessories, eyewear, jewelry, belt, hat, gloves, and their position relationships.

Do not create a collage of mismatched references. Do not treat multiple references as multiple characters. Do not redesign the character, outfit, shoes, bag, or accessories unless the user explicitly asks for a different character rather than a lock.

Completion criterion: the internal fused identity can be described as one person with one stable outfit system and one stable accessory system.

## Risk Gate And Board Set

Always generate the fixed main board:

- **A. Character Casting Lock Board**.

Automatically add extension boards when risk justifies them. Do not wait for the user to request them.

Add **B. Upper-Body Detail Board** when upper-body details are important or fragile:

- neckline, shoulder line, sleeve shape, chest/front structure, jacket lapel, buttons, jewelry, hair-to-collar transition, or face/hair/outfit overlap.

Add **C. Hairstyle Detail Board** when hair is complex or underspecified:

- important back hair, nape, tail, bun, braid, curl structure, hair volume, side contour, high-angle hair information, or a user-supplied hair reference.

Add **D. Accessory / Shoe / Bag Detail Board** when accessories are identity-critical or drift-prone:

- shoes, bag, hat, eyewear, jewelry, gloves, belt, handheld object, or any item likely to change across video generations.

High-risk signals include:

- insufficient back hair information;
- insufficient back outfit information;
- insufficient side contour information;
- bag or handheld item likely to drift between views;
- shoes too small or blurred in full-body references;
- neckline, shoulder, sleeve, waist, hem, skirt, or pants shape likely to change;
- important upper-body, accessory, or local detail not visible enough in the main board.

Completion criterion: the run has a board set: the fixed main board plus every justified extension board.

## Main Board Specification

Generate **A. Character Casting Lock Board** as a horizontal 16:9, 4K-style ultra-clear, text-free traditional film casting contact-board style image. If the image tool cannot guarantee an exact 3840 x 2160 raster, preserve the 16:9 composition and high-resolution production clarity.

The main board must contain these four core views:

1. large frontal face portrait;
2. front full-body view;
3. back full-body view;
4. side full-body view.

View requirements:

- Large frontal face portrait: frontal, shoulder-up or chest-up, clear facial identity, skin, hairline, hair color, and restrained natural expression.
- Front full-body: complete standing character, head to feet, with outfit, shoes, bag, and accessories visible.
- Back full-body: complete back view with back hair, back outfit, back body contour, rear shoe / heel information, and bag back or rear-side relationship.
- Side full-body: complete side view with forehead, nose bridge, jaw, hair side contour, clothing side silhouette, shoe side shape, and bag side relationship.

Board requirements:

- all views show the same character;
- same face logic across portrait and body views;
- same height impression, body proportion, outfit, shoes, bag, accessories, hairstyle, skin tone, and overall identity;
- natural neutral standing poses, close to traditional casting documentation;
- arms positioned to avoid hiding critical clothing and accessory relationships;
- legs naturally standing, no exaggerated crossing or action pose;
- no cropped head, feet, shoes, bag, or key clothing;
- clean white, near-white, light gray, or neutral gray background;
- even neutral light, clear asset-board visibility, minimal shadow;
- no title, name, role label, size scale, table field, note, number, arrow, caption, watermark, UI, film edge code, gibberish, or any text inside the image.

Completion criterion: the main board locks face, front body, back body, and side body without text pollution or fashion-poster behavior.

## Extension Board Specifications

### B. Upper-Body Detail Board

Generate only when the risk gate requires it.

Use a text-free neutral casting-reference layout focused on:

- shoulders, neck, collar, neckline, lapel, sleeve opening, upper garment structure, fabric, buttons, jewelry, bag strap, and hair-to-outfit transition;
- front, side, and back upper-body continuity when useful.

This board supports the main board; it must not replace it.

### C. Hairstyle Detail Board

Generate only when the risk gate requires it.

Use a text-free neutral casting-reference layout focused on:

- front hairline and face framing;
- side hair contour;
- back-of-head, nape, tail, bun, braid, curl, volume, or parting;
- high-angle hair information only when useful for continuity.

Do not turn it into a beauty, hair-salon, or fashion editorial image.

### D. Accessory / Shoe / Bag Detail Board

Generate only when the risk gate requires it.

Use a text-free neutral casting-reference layout focused on:

- shoe silhouette, sole/heel, toe shape, material, and worn relationship to pants/skirt;
- bag shape, strap, handle, opening, body-side placement, handholding or wearing method;
- eyewear, jewelry, hat, gloves, belt, handheld object, or other accessories;
- enough surrounding body context to show where each item belongs.

Do not make a product advertisement, e-commerce detail page, or labeled spec sheet.

Completion criterion: every generated extension board closes a specific risk identified before generation.

## Image Generation Rules

Call Codex built-in `/image gen` directly for each required board. If the current interface exposes another equivalent built-in image-generation tool, use it directly. If no image-generation capability is callable, report a hard blocker; do not replace the deliverable with prompt-only output.

Use all supplied reference images in the generation call when the tool supports reference attachments.

Before each `/image gen` call, build and freeze one `final_generation_prompt` for that board. The prompt must be the complete natural-language prompt actually submitted to the image-generation tool, including board type, selected identity, source-role bindings, reference attachment aliases, view requirements, consistency requirements, visual style, and strict negatives.

If tool syntax requires changes, update `final_generation_prompt` before generation so the returned prompt and generated board stay aligned. Do not reconstruct a cleaner prompt after generation and present it as the submitted prompt.

Keep `final_generation_prompt` safe to return under the heading `Image generation prompt:` or, when multiple boards are delivered, `Image generation prompts:`:

- Exclude private draft prompts, hidden planning, private source maps, and rejected variants; output only the final prompt actually submitted for each delivered board.
- use attachment aliases such as `face_reference_1`, `outfit_reference_1`, `shoe_reference_1`, or `selected_identity_reference`, not local absolute file paths;
- do not include hidden reasoning, scratchpad notes, private lock summaries, secrets, client-private notes, or unsupported identity claims;
- state that the prompt depends on the same reference images used in the run and is not a standalone guarantee of identity reproduction;
- keep all prompt text outside the generated image.

Internally verify the prompt before delivery. When the environment exposes tool-call payloads, transcript records, saved prompt files, or equivalent evidence, confirm that the accepted board used the frozen `final_generation_prompt`. When feasible, record `generation_prompt_sha256` for the exact prompt, but do not make hashes, call indexes, tool payload fields, or audit metadata part of the default user-facing final response. If the accepted board's exact submitted prompt is unknown or mismatched, mark that board `generated_board_failed_qa` instead of delivering an approximate prompt.

For one delivered board, output:

```text
Image generation prompt:
[exact final_generation_prompt used for the accepted /image gen result]
```

For multiple delivered boards, output one user-facing prompt per accepted board:

```text
Image generation prompts:
- A. Character Casting Lock Board:
  [exact final_generation_prompt used for the accepted main board]
- B. Upper-Body Detail Board:
  [exact final_generation_prompt used for the accepted upper-body board]
```

The number of visible prompts must equal the number of delivered boards, not the number of failed or rejected attempts. If one corrective regeneration is needed, output only the final corrective prompt that produced the accepted board, not the failed draft prompt. If the exact final prompt used for an accepted board is unknown, mark that board `generated_board_failed_qa` for prompt mismatch. Do not provide an approximate prompt.

Default image requirements for every board:

- horizontal 16:9;
- 4K ultra-clear;
- realistic photographic production reference;
- clean neutral background;
- clear, even, neutral light;
- asset-board clarity over beauty;
- no complex environment;
- no dramatic composition;
- no poster style;
- no fashion editorial style;
- no cinematic still;
- no cartoon, illustration, CGI, or concept-art treatment;
- clean orderly layout;
- absolutely no text inside the image.

The prompt is a required companion deliverable, but it must never be placed inside the generated image. Prompt output in chat or in a sidecar file is allowed and required; in-image text remains forbidden.

Completion criterion: `/image gen` has been called for the fixed main board and for every extension board required by the risk gate, and the exact prompt submitted for each delivered board is retained as `final_generation_prompt`.

## Consistency Rules

All generated boards must preserve:

- the same face;
- the same facial feature logic;
- the same hairstyle;
- the same skin tone and texture;
- the same body proportion and height impression;
- the same outfit;
- the same shoes;
- the same bag or handheld item;
- the same accessories;
- the same overall styling.

Reject any output where:

- different views become different people;
- front and side views change face;
- front and back views change hairstyle;
- front and back views change outfit;
- shoes, bag, or accessories change between views;
- body type or height impression drifts;
- the board becomes a fashion lookbook, poster, cinematic still, concept page, or labeled character sheet.

## Single-Image References

If the user provides only one usable reference image, still generate the main Character Casting Lock Board when possible.

Preserve all visible face, clothing, shoes, bag, accessory, hair, and body information from that single image. Do not make unsupported large changes.

If back, side, shoe, bag, or clothing information is impossible to lock reliably from the single image, proceed with the best source-faithful board unless the missing information is the only indispensable input for the user's stated use. Mention the information gap as `safe_inferred` or `missing_or_conflicting` briefly in the final response; do not claim those details are verified and do not turn it into a prompt-only handoff.

## Multi-Image References

If the user provides multiple images:

1. integrate them;
2. resolve user-assigned roles first;
3. unify them into one stable character;
4. generate the board set.

Do not make one board per source image unless the user explicitly asks for multiple separate characters.

If the references show multiple possible target people and the target is ambiguous, stop before image generation and ask the user to identify the target. Do not average faces, mix candidates, or create a composite actor.

## QA And Repair

After each generated board, inspect it before final response.

Check:

- main board includes the large frontal face portrait, front full-body, back full-body, and side full-body;
- all full-body views are complete head-to-toe with no cropped feet, shoes, bag, or key clothing;
- face identity, body proportion, hair, outfit, shoes, bag, and accessories remain consistent;
- back view genuinely shows back hair and back outfit;
- side view genuinely shows side facial and body silhouette;
- no text, labels, titles, captions, numbers, arrows, scales, UI, watermarks, or gibberish appear;
- background is clean and neutral;
- lighting is neutral and clear;
- the output reads as a traditional casting board, not fashion editorial, poster, concept art, or scene photography;
- each extension board actually closes its stated risk.

If a structural failure occurs and image generation remains available, run a corrective `/image gen` attempt focused on the dominant failure. Prioritize repairs in this order:

1. remove text pollution;
2. restore same-character identity;
3. restore outfit / shoe / bag / accessory consistency;
4. restore missing back or side view;
5. fix cropping;
6. remove poster, fashion, concept-art, or scenic styling.

If the main board is usable but cannot lock critical details, generate the required extension board instead of stopping at analysis.

Completion criterion: final delivered boards either pass QA or the response honestly states the remaining hard blocker or QA failure.

## Output Contract

Default final response is concise and in Chinese.

Runtime result statuses are:

- `hard_blocked`: no image generation; report only the blocker and the indispensable missing input, prompt-output limitation, or policy boundary.
- `selection_pending`: no image generation; the reference set contains more than one possible target identity and the user must select one target character or approve separate boards.
- `generated_main_board`: main board generated, image generation prompt output, and QA-checked.
- `generated_expansion_package`: main board plus risk-triggered extension boards generated, image generation prompts output, and QA-checked.
- `generated_board_failed_qa`: generated output failed visual QA after available targeted repair; do not register it as a lock asset.

When generation succeeds, report only:

- generated boards;
- which board is the fixed main board;
- which boards are automatic extensions;
- whether a hard blocker exists;
- source status for critical role sources when any are `safe_inferred` or `missing_or_conflicting`;
- `Image generation prompt:` for one delivered board, or `Image generation prompts:` for multiple delivered boards;
- the key character information locked in this run;
- brief QA result.

Do not write a long tutorial. Do not output prompt drafts, rejected prompt variants, hidden reasoning, or private source-map notes as if they were the generation prompt.

Use this structure:

```text
已生成：
- 固定主板：角色选角锁定板
- 自动扩展板：上半身细节板 / 发型细节板 / 配饰 / 鞋包细节板 / 无

硬阻塞：无 / 有，原因是...

来源状态：
- 已验证：
- 合理推断：
- 缺失或冲突：

Image generation prompt:
[本次实际提交给 /image gen、并生成已交付资产板的完整图片生成提示词]

If multiple boards are delivered, use:

Image generation prompts:
- A. Character Casting Lock Board:
  [本次实际提交给 /image gen、并生成固定主板的完整图片生成提示词]
- B. Upper-Body Detail Board:
  [本次实际提交给 /image gen、并生成上半身细节板的完整图片生成提示词]

本次锁定：
- 人脸：
- 皮肤：
- 发型：
- 体型：
- 服装：
- 鞋子：
- 包 / 手持物：
- 配饰：

验收：通过 / 需修正，原因是...
```

If hard-blocked, report only the missing indispensable input or policy boundary. Do not provide a substitute prompt.

## Hard Prohibitions

Never:

- output prompt text as a substitute for image generation in a successful runtime run;
- reconstruct a prettier prompt after generation and present it as the actual submitted prompt;
- include hidden reasoning, local absolute paths, secrets, private source maps, or unsupported identity claims in the visible image generation prompt;
- place prompt text, prompt fields, labels, or any written prompt content inside the generated image;
- stop at planning when usable references and image generation are available;
- generate only an analysis without images;
- create text inside the image;
- include unselected people, extra faces, background people, mirror faces, printed faces, or comparison faces in the final lock board;
- create poster, fashion editorial, lookbook, beauty ad, cinematic still, illustration, cartoon, concept art, or labeled design sheet;
- ignore back view or side view;
- generate only a portrait;
- generate only a front full-body image;
- crop off important clothing, shoes, bag, or accessories;
- alter user-assigned face, hair, skin, outfit, shoes, bag, or accessory sources;
- change the character identity across views.

Hard-block before image generation when:

- no usable character reference image exists;
- multiple possible target characters appear and the user has not identified which one to lock; report `selection_pending`;
- the user requires multiple candidates in one comparison board;
- the user requires names, role labels, numbers, measurements, notes, arrows, or any text inside the image;
- the user requires exact back, side, shoe, bag, or accessory locking while the required source is absent and inference is not allowed;
- image generation capability is unavailable;
- the final image generation prompt cannot be constructed before the image-generation call; report `hard_blocked_generation_prompt_unavailable`;
- platform safety policy blocks the requested generation.

## Acceptance Criteria

The skill is valid only if:

- the folder is `.agents/skills/character-casting-lock-board/`;
- `SKILL.md` frontmatter `name` is `character-casting-lock-board`;
- the English name `Character Casting Lock Board` appears in the file;
- the Chinese name `角色选角锁定板` appears in the file;
- `Input` and `Output` structure terms appear in the file;
- the skill requires direct Codex built-in `/image gen`;
- the skill outputs `Image generation prompt:` for one delivered board, or `Image generation prompts:` for multiple delivered boards;
- every visible prompt is the exact final prompt used for the accepted `/image gen` result it accompanies;
- prompt output is a companion deliverable, not a prompt-only substitute deliverable;
- prompt-only-without-image requests are out of scope for this production skill;
- the fixed main board requires four core views: large frontal face portrait, front full-body, back full-body, and side full-body;
- the skill supports single-image and multi-image references;
- the skill supports user-assigned role references for face, skin, hair, outfit, shoes, bag, handheld items, and accessories;
- extension boards are automatically chosen from risk, not from user follow-up;
- every generated board is text-free, neutral-background, non-poster, non-fashion-editorial, and identity-consistent.
