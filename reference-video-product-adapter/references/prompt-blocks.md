# Prompt Blocks

Use these blocks inside Codex or GPT. Keep them as constraints, not as marketing copy.

## Reference Breakdown Prompt

```text
Analyze the reference video only from observable evidence. Produce a beat-by-beat breakdown with timestamps if available. Separate facts from interpretation. Do not infer product claims.

For each beat include: beat_id, estimated_time_range, visual, action, camera, transition, text_or_logo, rhythm_note, adaptation_function.
```

## Keep Change Avoid Prompt

```text
Convert the reference breakdown into an adaptation boundary.

Keep only abstract structure: pacing, broad emotional arc, shot function, rhythm, and reveal logic.
Change product, brand, character, setting, wording, exact actions, and exact compositions.
Avoid frame-by-frame imitation, original brand assets, original copy, and distinctive scene sequences.
```

## Product Mapping Prompt

```text
Map the product into the adapted structure. For each product appearance, specify shot function, product role, visible product feature, source_refs, and claim_status.

If a claim is not supported by product materials, mark it needs_confirmation instead of rewriting it as fact.
```

## Shot List Prompt

```text
Create a concise AI-video shot list from the adaptation brief and product mapping.

Each shot must include shot_id, duration_sec, reference_beat_id, shot_size, visual, action, camera, product_role, on_screen_text, source_refs, ai_video_notes, and risk_flags.

Do not copy exact reference compositions. Adapt the shot function.
```

## Storyboard Prompt Skeleton

```text
Create a [6/9]-panel storyboard sheet based strictly on the shot list.

Use the storyboard as sequential shot guidance, not as a static collage. Treat each panel as a separate beat in order.

Each panel should show one numbered beat with clear composition, product placement, action, and emotional rhythm. Use minimal text inside panels. Do not render long subtitles, exact package copy, legal claims, QR codes, or detailed logos.

Visual style: [style notes].
Panel layout: [grid].
Product identity: use product reference image as identity reference.
Mood reference: use mood image only for lighting, texture, palette, and atmosphere.

Avoid exact reference-video compositions and avoid original brand elements.
```

## Video Platform Prompt Skeleton

```text
Use Image A as storyboard sequence guidance. It is not a static collage. Treat each panel as a separate beat in order.

Use Image B as product identity reference. Preserve product shape, packaging color, logo position, and key material details.

Use Image C as mood and lighting reference only.

Generate a [duration] product-focused AI video following this sequence:
[shot sequence]

Constraints:
- no invented subtitles
- no random logo changes
- no unsupported product claims
- no frame-by-frame imitation of the reference video
- keep product identity consistent across shots
```
