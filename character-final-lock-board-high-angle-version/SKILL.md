---
name: character-final-lock-board-high-angle-version
description: "Use when the user provides person/model reference images, optional wardrobe/shoe/accessory references, and optional character notes, and needs one high-angle Character Final Lock Board for AI video identity continuity. Directly generate the final board image with GPT Image 2 or the available image-generation tool; also output the actual image-generation prompt as a secondary trace file, with QA and optional asset_record.yaml. Do not create candidate sheets or make prompt text the primary deliverable."
---

# Character Final Lock Board High Angle Version

Generate one final locked character asset board for AI video continuity. The primary deliverable is an actual image file; the exact image-generation prompt is a secondary trace deliverable saved outside the image.

## Input Gate

Classify the user's supplied files and notes before generation.

- Require at least one person/model reference image. If none exists, hard-block with `hard_blocked_no_person_reference`.
- Accept optional wardrobe, shoe, accessory, prop, and layout-style references. Respect explicit user labels.
- If no wardrobe reference exists, inherit the visible outfit from the person/model reference.
- If only wardrobe, shoe, accessory, prop, or layout references exist and no person/model reference exists, hard-block. Do not invent an identity.
- If multiple person references show the same person, use them together as identity evidence. If they show different people and the user has not selected one identity, stop and ask for the identity source instead of blending faces.
- Accept optional role notes, asset IDs such as `@hero`, and tonal directions such as more daily, mature, younger, advertising-realistic, or commuter. Treat age-direction words as styling pressure only; do not biologically change age, face structure, or body type unless the user explicitly requests a different character rather than a lock.
- If a request conflicts with image-generation safety policy, stop on that policy boundary and offer a non-identifying character alternative.

Completion criterion: the input state is exactly one of `ready`, `hard_blocked_no_person_reference`, `identity_conflict`, or `policy_blocked`.

## Lock Summary

Before generation, write a private lock summary for yourself:

- `identity_source`: person/model reference filenames or attachment names.
- `body_source`: person/model reference unless the user clearly provides a separate body source.
- `wardrobe_source`: wardrobe reference, or inherited visible wardrobe from the person/model reference.
- `shoe_source`: explicit shoe reference first, then inherited visible shoes.
- `accessory_source`: explicit accessories first, then inherited visible accessories.
- `prop_source`: explicit prop/handheld/bag references or visible carried objects.
- `asset_id`: user-provided ID, otherwise a short timestamped ID such as `character_20260701_1530`.
- `direction_notes`: only notes compatible with identity and wardrobe lock.

Use the lock summary to build the generation call and prompt trace. Do not print the lock summary unless saving `asset_record.yaml` or explaining a blocker.

## Image Generation

Call the available Codex image-generation capability directly. Select GPT Image 2 or `/image gen2` when the interface exposes a model choice. If no image-generation tool is callable, report a hard blocker; do not replace the image with a prompt-only deliverable.

Use all relevant reference images in the generation call when the tool supports references. The board must lock one person and one outfit system, not explore alternatives.

Compose the actual image-generation prompt from the following prompt scaffold plus the lock summary. The `final_generation_prompt` is the exact text submitted to the image-generation tool for the delivered image; it must not be replaced with the scaffold, private reasoning, lock summary, or a retrospective summary.

Image-generation prompt scaffold:

```text
Create one wide 16:9 or wider Character Final Lock Board for AI video continuity.
Use the supplied person/model reference as the locked identity and body source.
Use the supplied wardrobe, shoe, accessory, and prop references as the locked styling source; if no wardrobe reference is supplied, preserve the visible outfit from the person/model reference.

Board style: clean white or light gray seamless studio background, neutral studio catalog lighting, soft even shadows, realistic high-resolution photography, engineered asset-board clarity, no scene environment, no poster layout, no fashion editorial treatment.

Required board content:
- one large clear front facial portrait;
- one neutral front full-body view with no prop interference;
- one back full-body view;
- one side full-body view, left or right;
- one 3/4 front full-body view;
- at least one high-angle view, preferably high-angle 3/4 full-body, high-angle upper-body, or slight top-down pose view;
- one or two natural pose variants such as relaxed standing, slight turn, walking, seated, leaning, or role-appropriate neutral movement;
- four to six expression head tiles, such as neutral, slight smile, focused, surprised, thinking, and natural laugh;
- three to five detail crops for hair, face, collar, sleeve, fabric, shoes, accessories, or prop;
- two or three simple black silhouettes from front, side, or light dynamic stance.

High-angle rule: include a readable high-angle or slight top-down view that locks crown hair, hairline, shoulder-neck proportion, collar/neckline, upper-body perspective, and body proportion under high camera placement. Do not use an extreme 90-degree overhead top view unless the user explicitly asks for overhead top view.

Identity lock: preserve face shape, feature spacing, eyes, nose, mouth, hairstyle, hair volume, skin tone, age impression, body type, height impression, posture, and character presence across every view.

Wardrobe lock: preserve top, bottom, shoes, accessories, fabric type, core colors, garment cut, silhouette, and wearing method across every view.

Prop control: keep character identity and wardrobe dominant. Include at least one neutral front full-body view with no prop interference. Include at least one side or back full-body view with no prop interference. Props may appear in extra pose views, 3/4 views, or detail crops. If a prop is only incidental styling, reduce its visual footprint.

Strict negatives: no headless model, no missing head, no face swap, no biological age change, no body type change, no identity change, no wardrobe redesign, no new unrelated clothing layer, no shoe-type change, no extra people, no indoor scene, no outdoor scene, no cinematic lighting, no dramatic shadows, no poster design, no fashion editorial, no illustration, no anime, no CGI, no 3D render, no concept art, no text, no title, no arrows, no labels, no logo, no watermark, no UI, no gibberish.
```

Save or append the exact prompt before each image-generation call in `<asset_id>_image_prompt.md`. The trace must identify `attempt_1` and, if regeneration is used, `attempt_2`; it must also mark which attempt produced the delivered image and include a hash for the final prompt when practical.

Prompt text may be returned only as external documentation. Do not render the prompt, labels, titles, arrows, or any other text inside the generated image.

## Output Contract

Save outputs in a run folder when filesystem access is available:

`outputs/character-locks/<asset_id>/`

Required:

- `<asset_id>_final_lock_board_high_angle.png` or the native image filename returned by the generator.
- `<asset_id>_image_prompt.md`, containing the exact prompt trace for the delivered image.

Recommended:

- `asset_record.yaml`
- `qa_report.md`

`<asset_id>_image_prompt.md` should contain:

~~~md
# Image Prompt Trace

asset_id:
generation_tool:
final_image_path:
final_prompt_attempt: attempt_1
final_prompt_hash:
reference_images:
created_at:

## Attempt 1
status: submitted | final_used | failed
qa_result:
prompt:
```text
<exact prompt submitted to image generation tool>
```

## Attempt 2
regeneration_reason:
status: submitted | final_used
qa_result:
prompt:
```text
<exact regeneration prompt submitted to image generation tool>
```
~~~

Omit `Attempt 2` when no regeneration is used.

`asset_record.yaml` should contain:

```yaml
asset_id:
asset_type: character_final_lock_board_high_angle
status: final_lock_candidate
created_at:
identity_source:
body_source:
wardrobe_source:
shoe_source:
accessory_source:
prop_source:
direction_notes:
image_path:
image_prompt_path:
prompt_attempts:
final_prompt_attempt:
final_prompt_hash:
generation_tool:
qa_report_path:
revision_count:
```

`qa_report.md` should contain the QA checklist, result, prompt trace path, prompt-save checks, and whether regeneration was used.

## QA Gate

Inspect the generated image visually. Use an image viewing tool when available.

Check:

- every human body view keeps the head visible;
- one consistent face and identity appear across the board;
- wardrobe, shoes, accessories, and body proportions match the chosen sources;
- neutral front full-body view exists and is not blocked by props;
- back full-body view exists;
- side full-body view exists;
- 3/4 full-body view exists;
- at least one high-angle or slight top-down view exists and is not a 90-degree overhead unless requested;
- expression group exists with four to six head tiles;
- detail crops exist with three to five useful closeups;
- silhouettes exist with two or three clean shapes;
- background is white or light gray studio only;
- no extra people appear;
- no text, title, arrows, labels, logo, watermark, UI, or gibberish appears inside the image;
- if props exist, prop weight does not overpower character identity and wardrobe lock.
- `<asset_id>_image_prompt.md` exists;
- the prompt trace was saved before generation;
- the prompt trace identifies the delivered `final_prompt_attempt`;
- if regeneration was used, both attempt prompts are recorded and the regeneration reason is stated.
- `asset_record.yaml`, `qa_report.md`, and `<asset_id>_image_prompt.md` refer to the same `asset_id`, delivered image path, and final attempt.

Result levels:

- `pass`: all core lock requirements pass; minor spacing or crop imbalance is acceptable.
- `warn`: the image is usable but has a minor missing secondary element.
- `fail`: identity drift, wardrobe drift, missing head, extra person, scene background, text pollution, missing high-angle view, missing neutral no-prop front full-body view, or missing required full-body angles.

If the first generation is an obvious `fail`, regenerate exactly once. The second attempt must tighten identity consistency, wardrobe consistency, no text, no background, complete head-to-toe body views, the high-angle view, and no-prop front/side/back lock views. Record `attempt_1` before the first call and append `attempt_2` before the regeneration call. After the second attempt, stop and deliver the best image with an honest QA result; do not loop.

## User-Facing Reply

Return only:

- image path or generated image result;
- `<asset_id>_image_prompt.md` path;
- final prompt attempt, `attempt_1` or `attempt_2`;
- `asset_record.yaml` path if created;
- `qa_report.md` path if created;
- short QA result and whether one regeneration was used.

If filesystem output is unavailable, return the actual final prompt text after the image result under a secondary heading such as `Secondary deliverable: image prompt used`. Do not put the prompt before the image result.

Do not make the prompt text or a candidate sheet the primary output. The prompt is required trace evidence, secondary to the generated board image.
