---
name: character-final-lock-board
description: "Use when the user provides person or model reference images, optional wardrobe/shoe/accessory references, and optional character notes, and wants a final locked character asset board for AI video or image continuity. Directly generate one Character Final Lock Board image with GPT Image 2 or the available image generation tool, and output the exact image generation prompt used for the delivered image. Do not produce a candidate sheet or prompt-only result."
---

# Character Final Lock Board

Generate one final locked character asset board, not exploratory candidates. The deliverable is an actual image file plus the exact image generation prompt used for that delivered image. `asset_record.yaml` and `qa_report.md` are recommended companion artifacts.

## Input Contract

Classify the user's inputs before generation.

- Require at least one person/model reference image. If none exists, hard-block and explain that a person/model reference is required.
- Accept optional wardrobe, shoe, accessory, and prop references. If the user labels references, respect the labels.
- If no wardrobe reference is provided, inherit visible clothing from the person/model reference.
- If only wardrobe, shoe, or accessory references exist and no person/model reference exists, hard-block. Do not invent an identity.
- Accept optional role notes, asset IDs such as `@hero`, and direction such as more daily, more premium, more advertising-realistic.
- Treat age-shift requests as styling pressure only. Do not biologically change age, body type, identity, or face structure unless the user explicitly asks for a different character rather than a lock.
- If a request conflicts with image-generation safety policy, stop on that policy boundary and offer a non-identifiable character alternative.

Completion criterion: the input state is one of `ready`, `hard_blocked_no_person_reference`, or `policy_blocked`.

## Lock Sources

Before generation, write a private lock summary for yourself:

- `identity_source`: person/model reference file names or attachment names.
- `body_source`: person/model reference unless the user clearly specifies otherwise.
- `wardrobe_source`: wardrobe reference, or inherited visible wardrobe from the person/model reference.
- `shoe_source` and `accessory_source`: explicit references first, then inherited visible items.
- `asset_id`: user-provided ID, otherwise a short timestamped ID such as `character_20260701_1530`.
- `direction_notes`: only notes that do not break identity or wardrobe lock.

Use the lock summary to build the generation prompt. Do not print the lock summary unless it is saved to `asset_record.yaml` or needed to explain a blocker.

## Image Generation

Call the available Codex image-generation capability directly. Select GPT Image 2 or `/image gen2` when the interface exposes a model choice. If no image generation tool is callable, report a hard blocker; do not replace the image with a prompt-only deliverable.

Use all supplied reference images in the generation call when the tool supports reference attachments. The generation must create one final board from the locked identity and wardrobe, not multiple alternate identities.

Build `final_generation_prompt` before the image-generation call. It must be the complete natural-language prompt actually sent to the image-generation tool, including board layout, identity lock, wardrobe lock, reference binding notes, and strict negatives. If you change the prompt to satisfy tool syntax, update `final_generation_prompt` before generation so the saved prompt and generated image stay traceable.

Keep `final_generation_prompt` safe to return:

- Refer to input images by attachment aliases such as `person_reference_1` and `wardrobe_reference_1`, not by local absolute paths.
- Do not include private lock summaries, hidden reasoning, secrets, client-private notes, or unsupported identity claims.
- State that the prompt depends on the same reference images used in the run and is not a standalone guarantee of identity reproduction.
- Keep all prompt text outside the image. The generated board itself must still contain no text, labels, arrows, UI, watermarks, or gibberish.

Prompt base:

```text
Create one wide 16:9 or wider Character Final Lock Board for AI video continuity.
Use the provided person/model reference as the locked identity and body source.
Use the provided wardrobe, shoe, and accessory references as the locked clothing source; if absent, preserve the visible outfit from the person reference.

Board style: clean white or light gray seamless studio background, neutral catalog/studio lighting, soft even shadows, realistic high-resolution photography, engineered asset-board clarity, no scene environment, no editorial fashion styling, no poster design.

Composition: one large clear front facial portrait on the left; front full-body, back full-body, side full-body, and 3/4 full-body views across the center/right; one or two natural pose variants; four to six expression head tiles; three to five detail crops for hair/face/collar/sleeve/fabric/shoes/accessories; two or three simple black silhouettes. Keep one consistent person and one consistent outfit across every view.

Identity lock: preserve face shape, feature spacing, eyes, nose, mouth, hairstyle, hair volume, skin tone, age impression, body type, height impression, posture, and character presence.

Wardrobe lock: preserve top, bottom, shoes, accessories, fabric type, core colors, garment cut, silhouette, and wearing method.

Strict negatives: no headless model, no missing head, no face swap, no age change, no body type change, no identity change, no wardrobe redesign, no new unrelated clothing layer, no shoe-type change, no extra people, no indoor or outdoor scene, no cinematic lighting, no dramatic shadows, no poster, no fashion editorial, no illustration, no anime, no CGI, no 3D render, no concept art, no text, no title, no arrows, no labels, no logo, no watermark, no UI, no gibberish.
```

Save and return the exact `final_generation_prompt` used for the delivered image. The prompt is a required companion deliverable, but the image remains required; do not finish with prompt text alone.

When generation is hard-blocked because no image-generation tool is callable, do not output a reusable generation prompt as if the run succeeded. Report the blocker and the missing capability.

## Output Contract

Save outputs in a run folder when filesystem access is available:

`outputs/character-locks/<asset_id>/`

Required:

- `<asset_id>_final_lock_board.png` or the native image filename returned by the generator.
- `<asset_id>_generation_prompt.md` containing the exact prompt used for the delivered image.

Recommended:

- `asset_record.yaml`
- `qa_report.md`

`asset_record.yaml` should contain:

```yaml
asset_id:
asset_type: character_final_lock_board
status: final_lock_candidate
created_at:
identity_source:
body_source:
wardrobe_source:
shoe_source:
accessory_source:
direction_notes:
image_path:
generation_prompt_path:
generation_prompt_sha256:
generator_model:
prompt_contract_version:
final_generation_attempt:
qa_report_path:
revision_count:
```

`qa_report.md` should contain the QA checklist, result, whether regeneration was used, and whether the delivered image is traceable to the returned prompt.

If the image tool cannot save files but can return an image result, return the full prompt text in the user-facing reply and mark `prompt_saved: false` in the QA result. If filesystem access exists, prefer saving the prompt file and also include the full prompt text in the reply when it is not excessively long.

## QA Gate

Inspect the generated image visually. Use an image viewing tool when available.

Check:

- head is present in every human body view;
- one consistent face and identity across the board;
- wardrobe, shoes, and accessories stay consistent with the chosen sources;
- front full-body view exists;
- back full-body view exists;
- side full-body view exists;
- 3/4 full-body view exists;
- expression group exists with four to six head tiles;
- detail crops exist with three to five useful closeups;
- silhouettes exist with two or three clean shapes;
- background is white or light gray studio only;
- no extra people appear;
- no text, title, arrows, labels, logo, watermark, UI, or gibberish appears inside the image;
- the prompt artifact or returned prompt is the exact prompt used for the delivered image;
- if regeneration occurred, the final prompt corresponds to the delivered regenerated image, not the rejected first attempt.
- the prompt record does not contain local absolute paths, hidden reasoning, secrets, private lock summaries, or unsupported identity claims;
- the prompt record states that it depends on the same reference images used in the run.

Result levels:

- `pass`: all core lock requirements pass; minor crop imbalance is acceptable.
- `warn`: the image is usable but has a minor missing secondary element.
- `fail`: identity/wardrobe drift, missing head, extra person, scene background, text pollution, or missing required full-body angles.

If the first generation is an obvious `fail`, regenerate exactly once. Save the rejected attempt prompt as `<asset_id>_generation_prompt_attempt_1.md` when filesystem access is available. The second attempt must emphasize identity consistency, wardrobe consistency, no text, no background, complete head-to-toe body views, and all required angles. Save the second prompt as the final `<asset_id>_generation_prompt.md` if that image is delivered. After the second attempt, stop and deliver the best image with an honest QA result; do not loop.

## User-Facing Reply

Return only:

- image path or generated image result;
- `generation_prompt.md` path and the exact prompt text, or the exact prompt text with `prompt_saved: false` if no file could be written;
- `asset_record.yaml` path if created;
- `qa_report.md` path if created;
- short QA result and whether one regeneration was used.

Do not make prompt text a substitute for image generation, and do not produce a candidate sheet.
