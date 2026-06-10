---
name: cinematic-composition-prompt-director
description: "Use when the user asks for cinematic image prompts, film-still composition variants, camera-angle prompt exploration, or exactly 10 visual prompt options from a scene idea, rough prompt, or uploaded image; including Chinese requests such as 电影构图提示, 电影感提示词, 10个构图. Do not use for storyboard planning, real-world source_url research, direct image generation, or final asset production unless explicitly requested."
---

# Cinematic Composition Prompt Director

## Overview

Transform a simple idea, rough prompt, scene description, or uploaded-image observation into exactly 10 cinematic image prompts around one locked core subject. The output must feel like plausible film stills with deliberate camera placement, spatial depth, practical light, environmental texture, and narrative tension.

This skill generates prompts only. Do not generate images, browse for references, make storyboards, or plan production unless the user explicitly asks for those follow-on tasks.

## Boundary Rules

- Preserve the user's core subject, setting, mood, and constraints unless the user asks for alternatives.
- If the user asks for real-world visual references, source URLs, brands, venues, products, or evidence, route to source_url-first research before prompt generation.
- If the user asks to generate images, first produce or confirm the prompt set unless they explicitly choose a prompt for image generation.
- If the input is an image, analyze visible subject, scene, mood, light, pose/action, and composition, then create new inspired variants. Do not literally copy the image unless requested.
- Do not mention living directors or living artists as a style reference.
- Do not introduce brand names unless the user supplied them.
- Avoid poster, portrait, fashion editorial, staged photo, generic concept art, and black-bar framing unless requested.

## Workflow

1. Normalize the input into a one-sentence core scene: subject, location, action or emotional state, atmosphere, and any constraints.
2. Lock the core scene. All 10 prompts must explore the same idea, not 10 different stories.
3. Choose 10 distinct composition concepts from different camera-language families. Use the user-provided composition if given, but do not repeat it mechanically.
4. Write each prompt as one concise paragraph. Include camera height, angle, lens/framing implication, subject placement, foreground, midground, background, practical or natural light source, atmosphere, texture, and implied story.
5. Add the default negative phrase to the end of every prompt.
6. Run the audit loop below before answering. Revise until all gates pass or state the specific remaining blocker.

## Composition Families

Prefer a varied set of 10. Good families include:

- extremely low angle
- high angle
- overhead/top-down view
- over-the-shoulder view
- foreground obstruction
- reflection shot
- silhouette shot
- frame-within-frame
- deep vanishing point
- wide negative space
- compressed telephoto distance
- handheld close perspective
- diagonal motion
- symmetrical staging
- asymmetrical balance
- partially hidden subject
- environmental scale
- subjective point-of-view composition
- layered foreground, midground, background

## Output Contract

Return exactly 10 prompts. Each prompt must contain:

1. a short title
2. one composition concept
3. one complete image prompt

Use the user's language unless they request another language.

For Chinese output, append this exact default negative phrase at the end of every prompt:

```text
无干净数字锐度、无CGI外观、无海报构图、无居中肖像、无黑边
```

For English output, append:

```text
no clean digital sharpness, no CGI look, no poster composition, no centered portrait, no black bars
```

Use this format exactly:

```markdown
1. **标题**
   **构图：[简要镜头/构图想法]**

   提示：
   [完整电影化提示]

---

2. **标题**
   **构图：[简要镜头/构图想法]**

   提示：
   [完整电影化提示]

---
```

Continue until item 10.

## Quality Standard

Each prompt should read like a frame captured during a real scene, not a generic "good image" request. Prefer action, emotional pressure, uncertainty, weather, dust, reflections, motion blur, soft focus falloff, practical light, natural light, shadow, imperfect realism, film grain, and environmental texture.

Avoid unsupported vague praise such as "epic", "beautiful", "cool", "史诗般的", "美丽", or "酷". If such a word is necessary, replace it with concrete visual evidence.

## Audit Loop

Before final output, perform this loop:

1. **Format audit**: exactly 10 numbered items; every item has title, composition line, prompt label, and default negative phrase.
2. **Diversity audit**: no repeated composition concept; at least 8 distinct composition families are represented.
3. **Cinematic audit**: every prompt includes camera position, spatial layers, light source, environmental texture, and a narrative or emotional moment.
4. **Contamination audit**: remove poster framing, centered portrait defaults, living-artist/director styles, unsupported brand names, black bars, generic concept-art language, and generic praise.
5. **Commercial-readiness audit**: revise any prompt that a professional art director could not hand to an image model or visual team without extra clarification.

If writing prompts to a Markdown file, run `scripts/audit_cinematic_prompts.py <file>` and fix failures before delivery. Read `references/quality-rubric.md` when judging borderline output quality.
