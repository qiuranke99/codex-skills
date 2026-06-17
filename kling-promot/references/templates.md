# Templates

Use these as starting points, not rigid forms. Keep user-facing output concise unless the user asks for variants.

## Minimal Rough-Idea Template

User gives one sentence and no assets:

```text
Recommended target: Kling VIDEO 3.0

Final prompt:
Generate a [duration] [aspect] Kling VIDEO 3.0 video. [Subject] [one clear action] in [specific setting]. Camera [one motivated move]. Lighting [specific source and mood]. Native audio: [environment sound / music / dialogue]. Preserve [continuity rule]. Avoid [2-4 targeted failures].
```

## Product Ad With Reference

```text
Recommended target: Kling VIDEO 3.0 Omni because product identity must stay stable across shots.

Final prompt:
Use Kling 3.0 Omni. @ProductA anchors the exact product shape, logo placement, material, and packaging proportions. @Image2 provides the environment and color palette only. Generate a 12-second vertical product film.

Shot 1 (0-3s): Tight macro close-up of @ProductA on a dark reflective surface; a narrow sweep of light moves across the logo. Camera locked, then begins a slow push-in. Audio: soft room tone and a subtle light-sweep shimmer.
Shot 2 (3-8s): The product rotates once around its vertical axis at a controlled speed; reflections reveal material texture while the logo-facing side remains readable. Camera stays centered, no orbit.
Shot 3 (8-12s): Product settles into the @Image2 lifestyle environment; background falls into shallow depth of field, leaving clean space for brand copy. Music resolves softly.

Continuity: preserve exact product proportions, color, logo placement, and material. Avoid warped logo, changing package shape, random zoom, excessive particles, unreadable text.
```

## Cinematic Character Scene

```text
Recommended target: Kling VIDEO 3.0 Omni if @CharacterA exists; otherwise Kling VIDEO 3.0.

Final prompt:
Use Kling 3.0 Omni. @CharacterA anchors the character's identity, outfit, body type, and silhouette. Generate a 15-second cinematic scene in 16:9.

Shot 1 (0-4s): Wide shot of @CharacterA standing under a flickering train-station sign at night, rain hitting the platform. Camera slowly tracks from behind to a three-quarter profile. Audio: rain, distant train brakes, low electrical hum.
Shot 2 (4-10s): Medium close-up as @CharacterA turns toward the empty tracks; shoulders tense, breath visible in cold air. Camera slow push-in, stable and restrained.
Shot 3 (10-15s): @CharacterA whispers, Mandarin, controlled fear: "It came back." The sign behind them cuts out for one beat, then returns. Camera holds close, no sudden zoom.

Continuity: preserve @CharacterA's face, outfit, and proportions. Avoid facial warping, flicker on the face, identity drift, lip mismatch, random camera shake.
```

## Native Audio / Dialogue

```text
Recommended target: Kling VIDEO 3.0 for native dialogue, or Kling 3.0 Omni if voice-bound elements are used.

Final prompt:
Generate a 10-second Kling VIDEO 3.0 scene with native audio.

Shot 1 (0-4s): Two characters sit across a small kitchen table at dawn. Character A grips a ceramic mug with both hands, knuckles tense. Camera locked medium shot. Audio: refrigerator hum, faint street noise.
Shot 2 (4-10s): Character B leans forward, eyes fixed on Character A. Character B (English, low voice, exhausted): "You were never supposed to find it." Character A does not answer, only lowers the mug onto the table with a small ceramic click.

Avoid lip mismatch, unclear speaker attribution, extra fingers around the mug, sudden camera movement.
```

## Video Reference For Motion Only

```text
Use Kling 3.0 Omni. @CharacterA anchors identity. @Video1 is used only for camera rhythm and action timing, not character identity or scene design. Generate an 8-second video.

One continuous tracking shot: @CharacterA performs the same broad movement rhythm as @Video1, with matched step timing and torso direction. The camera follows at waist height with smooth lateral tracking. Preserve @CharacterA's outfit and proportions. Avoid copying @Video1's person, costume, or background; avoid sliding feet and jittery camera.
```

## API-Oriented Skeleton

Only use this when the user asks for API output:

```json
{
  "model": "kling-v3-omni",
  "duration": 12,
  "aspect_ratio": "9:16",
  "sound": true,
  "prompt": "<<<element_1>>> anchors the hero product. <<<image_1>>> provides the environment only. Shot 1...",
  "notes": "Verify the exact provider supports these fields before submission."
}
```
