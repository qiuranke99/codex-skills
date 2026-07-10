# Neutral Appearance Rules

## Mandatory Decomposition

Before final generation, separate:

1. `intrinsic_scene_appearance`: material class, base color, texture, roughness, metalness, transparency, fixed paint, stable wear, fixed markings, intrinsic emission, and identity-defining color relations;
2. `intrinsic_scene_state`: identity-defining waves, currents, clouds, fog/smoke, dust, snow, flood, lava, fire, nebula structure, corona, accretion disk inclination, jets, and rings;
3. `external_illumination`: sunset, night illumination, hard backlight, colored light, strong one-sided light, window clipping, and temporary production lighting;
4. `camera_optical_effects`: shallow depth of field, blur, flare, bloom, vignette, chromatic aberration, lens dirt, diffusion, distortion, black bars, grain, oversharpening, denoise smearing, trails, and motion blur;
5. `postprocess_effects`: LUTs, teal/orange, global warm/cool casts, crushed blacks, tinted highlights/shadows, extreme contrast/saturation/desaturation, stylized exposure, cinematic fog, and synthetic glow;
6. `unresolved_appearance`: evidence too weak to classify reliably.

## Appearance Confidence

- `high`: multiple references or neutral evidence confirm material and base color.
- `medium`: material class is clear but lighting or grading affects color; use a conservative estimate.
- `low`: monochrome, severe clipping, deep underexposure, colored light, or strong grade destroys color evidence.

For low confidence, use a conservative, low-saturation, material-plausible value and label it `estimated_intrinsic_appearance`. Never promote it to Source-Locked. Freeze the same estimate across every view.

## Neutral Diagnostic Target

Neutralization preserves materials, intrinsic base colors, spatial volume, contact shadows, and scene-defining states while removing final-look dominance. It is not grayscale, desaturation, simple brightening, shadowless flat light, a white-box render, or final beauty lighting.

For interiors and architecture, use neutral white balance, broad soft illumination, low-to-medium contrast, readable shadows, unclipped highlights, clear contact shadows, sufficient depth of field, and no stylistic grade.

For exteriors and terrain, use soft natural daylight or mild directionality, readable landform/massing, controlled sky/ground exposure, and no inherited sunset, teal/orange, or extreme storm lighting. Do not force every exterior into directionless overcast light.

For ocean, sky, fluid, cloud, and volumetric scenes, preserve wave/cloud/flow structure, density, direction, vertical layers, and defining state while removing non-intrinsic tint, exaggerated glow, filters, and contrast.

For stars, black holes, nebulae, lava, and fire, preserve intrinsic emission, corona, accretion disk, jets, flame/lava form, and their relative structure. Compress excessive dynamic range for readability; remove added bloom, flare, lens glow, and grade. Never turn emissive scenes into ordinary white-lit gray models.

## Canonical Diagnostic Master

Use the original references to lock identity, geometry, landmarks, and observed evidence. Use Scene Canon to lock topology, scale, completion, exclusions, and state. Use the Canonical Diagnostic Master to lock neutral exposure, white balance, base colors, material response, and a look-free diagnostic presentation.

The master must be a complete, clean machine asset without people, products, temporary props, text, arrows, labels, watermarks, collage, grids, strong cinematic light, shallow focus, LUT, grain, flare, black bars, or advertising-still composition.
