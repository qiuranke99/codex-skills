---
name: single-face-character-lock-board
description: Create a single-face character lock board from one or more character reference images. The board contains exactly one bust portrait with face, one headless front full-body view, and one headless back full-body view. Use Codex /image gen directly and output the image generation prompt after generation.
---

# Single-Face Character Lock Board

## 中文名称

单脸角色资产锁定板

## Skill Description

Create one clean character asset lock board from one or more character reference images.

The board contains exactly one bust portrait with face, one headless front full-body view, and one headless back full-body view.

Use Codex built-in `/image gen` directly, then output the image generation prompt used for the generated board.

The visible prompt is part of the final deliverable. Do not expose hidden reasoning, internal source maps, or unrelated implementation notes.

## Purpose

This skill creates a specialized character asset lock board for AI video workflows.

This is not a standard character turnaround sheet.  
This is not a multi-face expression board.  
This is not a fashion poster, lookbook, magazine layout, or cinematic still.

The output is one clean character asset board containing exactly three visual components:

1. One bust portrait with the only visible face.
2. One headless front full-body view.
3. One headless back full-body view.

The board is used to lock:
- facial identity
- hairstyle and hairline
- skin texture
- facial hair or no facial hair
- clothing design
- body proportions
- footwear
- accessories
- front outfit structure
- back outfit structure

## When to use this skill

Use this skill when the user asks for:
- 单脸角色资产锁定板
- single-face character lock board
- one-face character reference board
- character board with one face only
- bust portrait + headless front/back outfit views
- 角色资产锁定，但只需要一张脸
- 用于视频模型避免多脸漂移的人物资产板

Also use this skill when the user provides one or more character reference images and asks to create a reference board similar to:
- one bust portrait plus front/back outfit views
- one clear face plus headless body views
- a clean gray-background model asset board

## Core Output

Generate exactly one image board using Codex built-in `/image gen`.

Direct /image gen only. The deliverable is exactly one generated image plus the image generation prompt used for that image, not a prompt-only answer, not a multi-image set, and not a generic character sheet.

The board must contain:

### View 1: Bust portrait

A chest-up or upper-body portrait showing the only complete face in the whole board.

This is the single visible face only. No mirror face, printed face, poster face, background face, partial side face, or second facial panel may appear anywhere else on the board.

Requirements:
- clear frontal or near-frontal face
- neutral natural expression
- visible hairstyle and hairline
- visible eyebrows, eyes, nose, lips, ears if present
- visible skin texture
- visible facial hair if present in the reference
- visible neck and collar area
- preserve distinctive facial traits from the reference
- preserve jewelry, nose strip, earrings, necklace, freckles, moles, scars, or facial marks if clearly present in the reference

### View 2: Headless front full-body

A complete front-facing body view from neck or upper-neck downward to the feet.

The body views must be face-free.

Requirements:
- no head
- no face
- no partial face
- no cropped second portrait
- complete outfit from neck to shoes
- clear shirt, jacket, pants, belt, shoes, accessories, sleeves, hem, pockets, fabric texture
- natural standing pose
- hands should not block important outfit structure unless the reference requires it
- body proportions must match the portrait identity and reference images

### View 3: Headless back full-body

A complete back-facing body view from neck or upper-neck downward to the feet.

The body views must be face-free.

Requirements:
- no head
- no face
- no turning head
- no partial side face
- complete back outfit from neck to shoes
- clear back shirt structure, collar, seams, pants back pockets, shoe backs, accessories
- natural standing pose
- same body proportions as the front view
- same outfit as the front view

## Input Rules

The user may provide:
- one reference image
- multiple reference images
- mixed references for face, hair, skin, outfit, shoes, accessories

The user may explicitly assign reference roles, for example:
- this image is the face
- this image is the hair
- this image is the skin texture
- this image is the outfit
- this image is the shoes
- this image is the accessories

When the user assigns reference roles, follow those assignments strictly.

## Reference Role Recognition Rules

When the user does not assign roles, infer roles internally:
- clearest frontal face image controls facial identity
- clearest hair image controls hairstyle
- clearest skin image controls skin texture
- clearest outfit image controls clothing
- clearest footwear image controls shoes
- clearest accessory image controls accessories

Use an internal face/hair/skin/outfit/shoes/accessories source map to resolve reference responsibilities before generation. Do not output this source map unless the user explicitly asks for a diagnostic report.

If there are conflicts, use this priority:
1. user-stated reference role
2. clearest face reference
3. clearest hair reference
4. clearest outfit reference
5. clearest shoes/accessories reference
6. secondary references only as supporting information

## Reference fusion rule

When multiple references are provided, merge them into one coherent character.

The result must feel like one real person wearing one consistent outfit.

Do not create collage logic.  
Do not create mismatched body parts.  
Do not change the person into a new character.  
Do not redesign the outfit unless the user explicitly requests a redesign.  
Do not invent extra clothing elements.  
Do not remove distinctive reference details unless they conflict with higher-priority references.

## Output Board Structure

Default layout:
- horizontal board
- clean gray background
- three-part composition

Preferred layouts:
1. Left: bust portrait. Center: headless front full-body. Right: headless back full-body.
2. Left: headless front full-body. Center: headless back full-body. Right: bust portrait.

Do not use a chaotic collage layout.

The board must remain clean, readable, and asset-oriented.

## Visual style

Use:
- neutral gray or light gray background
- soft even studio lighting
- realistic photography
- high clarity
- accurate fabric texture
- accurate body proportions
- clean catalog-like asset board
- minimal shadows
- no dramatic mood
- no cinematic scene lighting
- no colorful atmosphere lighting
- no location background
- no props unless they are part of the character reference
- no design annotations

The board should look like a clean production asset reference, not a final advertisement image.

## Hard prohibitions

Never generate:
- more than one visible face
- any second face from mirrors, printed graphics, posters, background people, side profiles, partial faces, or face-like decorative panels
- multiple facial expressions
- side-face panels
- extra heads
- full-body views with heads
- front full-body with visible face
- back view with turned head
- ordinary multi-angle character sheet
- 3x3 grid
- comic sheet
- anime sheet
- fashion magazine page
- editorial poster
- cinematic still
- environment scene
- text labels
- captions
- numbers
- arrows
- measurements
- watermarks
- logo-like layout text
- instruction text inside the image
- UI elements
- decorative typography

## /image gen execution rule

When this skill is invoked, directly use Codex built-in `/image gen` to generate the final image board.

Do not ask the user to copy a prompt into another tool.

Do not stop after planning.

Do not only describe how the board should look.

Do not stop after writing a prompt.

Generate the board directly unless there is a hard blocker.

After the image is generated and passes the self-check, output the final image generation prompt visibly in the response under the heading `Image generation prompt`.

If one corrective regeneration is needed, output only the final corrective prompt that produced the accepted image, not the failed draft prompt.

The visible prompt must be the image prompt, not hidden reasoning, not the internal source map, and not a diagnostic explanation.

## Hard blocker

The only hard blocker is:

The user has not provided any usable character reference image.

If no usable character reference exists, ask the user to upload at least one clear character reference image.

If at least one usable character reference exists, proceed.

## Internal construction requirements

Before calling `/image gen`, construct a final image generation prompt with these locked requirements:

- one horizontal character asset board
- exactly one bust portrait with face
- one headless front full-body view
- one headless back full-body view
- same person identity
- same outfit system
- same body proportions
- same shoes
- same accessories
- clean gray studio background
- soft even light
- no text
- no labels
- no extra panels
- no extra faces
- no scenic background
- no poster styling

Freeze the exact same prompt submitted to `/image gen` before generation. Do not reconstruct a cleaner or prettier prompt after generation and present it as the submitted prompt.

Keep the prompt concise enough to be reusable, but explicit enough to preserve the single-face, headless-body, clean-board contract.

## Image Constraints

The generated board must use a horizontal composition, a neutral gray or light gray background, soft even studio lighting, high-definition realistic texture, and production asset-board clarity.

The generated board must not use cinematic styling, poster styling, magazine styling, fashion editorial styling, dramatic scene lighting, location background, decorative typography, UI elements, labels, arrows, numbers, captions, measurements, or watermarks.

## Self-Check And Repair Rules

After generation, inspect the result.

Check:

1. Does the board contain exactly one complete visible face?
2. Is the bust portrait clear enough to lock identity?
3. Is the front full-body view headless?
4. Is the back full-body view headless?
5. Are the outfit, shoes, and accessories consistent?
6. Does the back view match the front outfit?
7. Is the body proportion consistent across views?
8. Is the board free of labels, text, arrows, numbering, watermarks, or captions?
9. Is the background clean and neutral?
10. Does the image avoid cinematic, poster, magazine, or scene-like styling?
11. Will the final response include the image generation prompt used for the accepted image?
12. Is the visible prompt free of hidden reasoning, internal source maps, and unrelated implementation notes?

If a structural failure occurs, automatically attempt one corrective regeneration using `/image gen`.

Structural failures include:
- QA reject if the result is more than exactly one generated image
- more than one face
- head present on full-body views
- back view missing
- outfit mismatch
- text pollution
- ordinary multi-angle sheet instead of the required single-face board
- missing image generation prompt in the final response

## Final response rule

After successful generation, respond with:

1. a brief statement that the Single-Face Character Lock Board has been generated
2. `Image generation prompt:` followed by the final prompt used for the accepted `/image gen` result

Do not include hidden reasoning, internal source maps, intermediate failed prompts, or unnecessary explanation.

Do not make the prompt the only deliverable.

## Acceptance Criteria

The skill is valid only if:

- The skill folder exists.
- SKILL.md exists.
- SKILL.md contains the English name `Single-Face Character Lock Board`.
- SKILL.md contains the slug `single-face-character-lock-board`.
- SKILL.md explicitly requires direct `/image gen` execution.
- SKILL.md explicitly requires outputting the image generation prompt after generation.
- SKILL.md explicitly forbids prompt-only delivery.
- SKILL.md fixes the output to one bust portrait plus two headless full-body views.
- SKILL.md explicitly forbids extra faces, text pollution, labels, arrows, numbers, watermarks, and ordinary character sheets.
- SKILL.md supports single-image and multi-image reference input.
- SKILL.md supports user-assigned reference roles for face, hair, skin, outfit, shoes, and accessories.
