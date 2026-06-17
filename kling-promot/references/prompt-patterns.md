# Prompt Patterns

Use this file to compile final Kling 3.0 / Omni prompts from rough briefs.

## Secondary Research Sources

These are not official Kling specifications. Use them as pattern evidence, not hard platform claims.

- fal.ai Kling 3.0 prompting guide: https://blog.fal.ai/kling-3-0-prompting-guide/
- invideo Kling Omni elements guide: https://invideo.io/blog/kling-omni-elements/
- Atlas Cloud realistic human motion guide: https://www.atlascloud.ai/blog/guides/mastering-kling-3.0-10-advanced-ai-video-prompts-for-realistic-human-motion
- Leonardo Kling prompt guide: https://leonardo.ai/news/kling-ai-prompts
- Artlist negative prompt guide: https://artlist.io/blog/negative-prompts-ai-video/

Do not treat wrapper-specific controls, numeric motion values, or provider payload fields as official Kling behavior unless the target provider documentation confirms them.

## Compiler Blueprint

Build prompts in this order:

1. **Target model/surface**: Kling 3.0 or Kling 3.0 Omni; app or API dialect.
2. **Reference anchors**: subject, element, product, first/last frames, motion/style/audio references.
3. **Duration and structure**: single continuous shot or shot list.
4. **Shot blocks**: shot duration, framing, subject action, physical mechanics, camera, environment, sound/dialogue.
5. **Continuity rules**: identity, product shape/logo, environment logic, lighting continuity.
6. **Avoidances**: short targeted failure guards.
7. **Optional settings**: aspect ratio, sound on/off, resolution/mode, multi-shot/custom multi-shot.

## Shot Grammar

Use this format for 8-15 second outputs:

```text
Shot 1 (0-3s): [framing]. [Subject/reference] [one main action]. Camera [one move]. Environment/light [specific details]. Sound [one or two cues].
Shot 2 (3-7s): ...
Shot 3 (7-12s): ...
```

For 3-7 second outputs, use one continuous paragraph unless the user requests cuts.

## Physical Motion Grammar

Replace generic motion verbs with observable mechanics:

- Walking: heel-to-toe contact, weight transfer, matched tracking speed, surface friction.
- Running: torso lean, foot strike, arm rhythm, breath, ground impact.
- Hands: fingers wrap around object, wrist rotates, object contact, no floating palms.
- Product rotation: axis, speed, material reflections, logo side remains readable.
- Liquid/particles/fabric: gravity, collision, air resistance, timing, material response.

Bad:

`The woman runs cinematically through the street.`

Better:

`The woman accelerates from a walk into a run, shoulders leaning forward, heels striking wet pavement, arms swinging in a tight rhythm; the tracking camera matches her speed at waist height.`

## Camera Grammar

Use motivated camera moves:

- `locked tripod` for precision, product demos, clinical scenes.
- `slow push-in` for reveal, emotion, product premiumization.
- `tracking shot` for walking/running and spatial continuity.
- `orbit` for hero products or character reveals, but avoid fast orbit with complex body action.
- `pull-back` for reveal of environment or consequence.
- `pan/tilt` for following gaze, revealing clues, or vertical scale.

One shot should usually have one primary move. If a shot needs multiple camera events, sequence them:

`starts locked for the product reveal, then begins a slow push-in after the logo catches light.`

## Audio And Dialogue Grammar

For Kling 3.0 native audio, assign speaker, language/accent, tone, and timing:

```text
Audio: soft room tone, footsteps on wet asphalt, distant neon buzz.
Dialogue, Shot 2: Mina (Mandarin, restrained, breath trembling): "I saw it move."
```

For multi-character dialogue:

- Label each character consistently.
- Put the speaker's visible action before the line.
- Avoid long dialogue in short shots.
- If using Omni voice-bound elements, do not over-describe the bound voice; describe emotion and delivery instead.

## Prompt Order

Put critical constraints early:

1. Identity/product anchor.
2. Exact action.
3. Environment.
4. Camera.
5. Audio/dialogue.
6. Style and quality.
7. Avoidances.

Do not bury identity preservation or product logo fidelity at the end.

## Model-Specific Patterns

### Kling 3.0 Standard

Use for standard prompt generation:

```text
Generate a [duration] Kling 3.0 video, [aspect ratio]. [Subject] [action] in [scene]. Camera [move]. Lighting [style]. Native audio [sound/dialogue]. Avoid [targeted failures].
```

For custom multi-shot:

```text
Use custom multi-shot structure.
Shot 1 ...
Shot 2 ...
Continuity: ...
Audio: ...
Avoid: ...
```

### Kling 3.0 Omni

Use when references/elements matter:

```text
Use Kling 3.0 Omni. @Element1 anchors [identity/product]. @Image2 provides [environment/style only]. @Video1 provides [camera/motion only].
Shot 1 ...
Shot 2 ...
Continuity: preserve @Element1 [specific traits] across all shots.
Avoid: ...
```

## Translating From Seedance-Style Prompts

Preserve:

- Asset-role assignment.
- Time segmentation.
- Camera/action intent.
- Audio cues.

Rewrite:

- Use `@Element` identity anchors for Omni.
- Make each shot's action and camera explicit.
- Add physical mechanics.
- Add short targeted avoidances.
- Separate app prompt from API payload fields.

Do not copy Seedance-specific platform constraints into Kling.
