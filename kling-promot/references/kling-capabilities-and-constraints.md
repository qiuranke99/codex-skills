# Kling Capabilities And Constraints

Use this file to avoid inventing Kling 3.0 or Kling 3.0 Omni behavior. Treat official sources as stronger than wrapper-provider guides. When the target surface is unclear, state assumptions instead of pretending every UI/API exposes the same controls.

## Primary Sources

- Official Kling VIDEO 3.0 guide: https://app.klingai.com/global/quickstart/klingai-video-3-model-user-guide
- Official Kling VIDEO 3.0 Omni guide: https://kling.ai/quickstart/klingai-video-3-omni-model-user-guide
- Official text-to-video prompt guide: https://kling.ai/quickstart/text-to-video-prompt-guide
- Official camera-control guide: https://kling.ai/blog/kling-ai-camera-control-video-guide
- Official prompt weighting / keyword priority guide: https://kling.ai/blog/kling-ai-prompt-weighting-keyword-priority
- Official 4K launch note: https://kling.ai/blog/kling-ai-introduces-native-4k-video-model
- Official API docs may be rendered dynamically; search-index snippets have shown `kling-v3`, `kling-v3-omni`, `multi_shot`, `shot_type`, `sound`, `aspect_ratio`, `duration`, `callback_url`, and `multi_prompt`, but verify before emitting a payload as final.

## Model Routing

Use **Kling VIDEO 3.0** when:

- The user needs text-to-video, image-to-video, start/end frames, native audio, dialogue, or standard multi-shot generation.
- The scene has one clear subject or a small number of manually described characters.
- The user does not need reusable element profiles or multiple reference assets.

Use **Kling VIDEO 3.0 Omni** when:

- The user has multiple references, product/character elements, video references, or reusable identity assets.
- The task depends on identity/product consistency across shots, scene changes, or camera motion.
- The user mentions element references, video elements, voice-bound characters, or combining multiple reference images/videos.

## Confirmed Capabilities

Kling VIDEO 3.0:

- Supports text-to-video, image-to-video, start/end-frame workflows, native audio, custom multi-shot, element references, multiple-character coreference, and multilingual dialogue.
- Supports flexible duration up to 15 seconds according to official 3.0 guidance.
- Official guide describes 720p and 1080p modes; later official blog announced native 4K for the Kling 3.0 video model series. Treat 4K as target-surface dependent until the exact UI/API confirms it.

Kling VIDEO 3.0 Omni:

- Supports native audio, multi-shot, image-to-video, multi-image reference, element reference, video element reference, element voice control, and up to 15 seconds generation.
- Is the better branch for reusable characters/products, multi-reference scenes, voice-bound elements, and video references.

## Input And Output Limits

Use these as official Omni constraints unless newer target-surface docs contradict them:

- Images: up to 7; jpg/jpeg/png; minimum 300 px width and height; up to 10 MB.
- Video input: one video; 3-10 seconds; up to 200 MB; up to 2K.
- If using a video input, total referenced images/elements is up to 4.
- Without video input, total referenced images/elements is up to 7.
- Voice-bound multi-image character elements can use 5-30 second single-person speech audio.
- Voice-bound video character elements can use 3-8 second single-character video and bind voice tone.

General Kling video defaults:

- Older official prompt guidance lists 16:9, 9:16, and 1:1 as supported aspect ratios. Use these as safe defaults unless the target surface exposes more.
- Output duration for 3.0/Omni can be 3-15 seconds in current official guidance.

## Prompt Formula

Official prompt guidance supports this base skeleton:

`subject + subject movement + scene + camera language + lighting + atmosphere`

For Kling 3.0 / Omni, expand it to:

`subject/reference anchors + shot sequence + action mechanics + camera/framing + scene/light + audio/dialogue + constraints`

## Audio And Dialogue

Kling VIDEO 3.0 supports native audio and multi-character dialogue attribution. Officially supported languages include Chinese, English, Japanese, Korean, and Spanish, plus code-switching, dialects, and accents.

Prompt dialogue as:

`Character label (language, accent, emotional tone, delivery): "line"`

Pair speech with visible action in the same shot to reduce speaker ambiguity.

## Camera And Motion

Use concrete camera terms: static, slow push-in, pull-back, pan, tilt, tracking shot, orbit, handheld, crane, overhead, low angle, close-up, medium shot, wide shot.

Keep one dominant camera move per shot. Avoid contradictions like `locked tripod` plus `fast orbiting handheld dolly zoom`.

## Negative Prompt Policy

Accessible 3.0 user guides do not establish a universal separate `negative_prompt` field. Some API wrappers expose negative prompt fields, and official API snippets suggest adding negative constraints inside positive prompts for some surfaces.

Default: include targeted avoidance clauses inside the final prompt. Only output a separate `negative_prompt` field when the user specifies an API/provider that supports it.

## Target-Surface Dependent Claims

Mark these as target-dependent unless verified during the run:

- 4K availability for the exact selected mode.
- Separate `negative_prompt` field.
- CFG scale, motion strength, camera-axis parameters, seed, keep-audio flags, and wrapper-specific controls.
- API tag syntax and exact payload shape.
