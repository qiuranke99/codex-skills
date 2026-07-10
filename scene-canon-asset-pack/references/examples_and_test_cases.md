# Examples And Test Cases

## Trigger Examples

- “Use these three room photos to create a reusable neutral scene asset pack with reverse/high/low coverage and 4K handoff prompts.”
- “Extend this single sunset building image into a consistent exterior Scene Canon without preserving the sunset grade.”
- “Build environment plates for this ocean storm while preserving wave direction and storm structure.”
- “Create a canonical black-hole scene pack; preserve accretion-disk inclination but remove lens bloom.”

Do not trigger for a storyboard, one shot anchor, character/product lock, Look Master, Lighting Master, ordinary retouch, source-image search, simple upscale, or video prompt.

## Test A — Heavy-Grade Single Interior

Pass only if the workflow separates warm/cool cast and crushed shadows from material base color; preserves fixed neon/emissive structure; creates a neutral diagnostic master; covers meaningful high/low reveals without new furniture; and the 4K prompt forbids source-look restoration.

## Test B — Sunset Architectural Exterior

Pass only if sunset gold is removed from the neutral canon, building material and facade/side/back relations remain stable, natural diagnostic daylight is used, and 4K prompts forbid reintroducing sunset.

## Test C — Night City Or Science-Fiction Scene

Pass only if fixed lighting hardware/emissive architecture is preserved while bloom, flare, and grade are removed; structure remains readable; and the result is not a gray model.

## Test D — Valley Or Desert

Pass only if landform base colors, horizon, ridges, scale, and high/low relations remain stable; cinematic grading is removed; and 4K prompts forbid new landforms or sunset color.

## Test E — Ocean, Cloud, Or Storm

Pass only if wave/cloud/flow direction and identity-defining state remain; non-intrinsic teal tint and bloom are removed; and neutralization does not turn a storm into generic clear weather.

## Test F — Black Hole, Star, Or Nebula

Pass only if intrinsic emission, accretion disk/corona/jets/nebula structure, viewing inclination, and spatial hierarchy remain while lens flare and post bloom are removed. Fail an ordinary white-lit gray model.

## Test G — 4K Mapping

Pass only if each approved machine image has one distinct prompt with correct path/dimensions/versions; the neutral Codex asset is primary; original heavy-grade references are optional support; look restoration is forbidden; and regeneration invalidates the old mapping.

## Deterministic Negative Fixtures

The bundled contract test must fail these mutations:

1. `gray_model_neutralization`: intrinsic colors/emission/state removed.
2. `grid_crop_asset`: machine asset has `independently_generated: false` or `derived_from_multipanel: true`.
3. `unverified_dimensions`: approved asset has `actual_dimensions_verified: false`.
4. `false_native_4k`: `native_4k_claim: true` without evidence or file dimensions below the target.
5. `prompt_many_to_one`: prompt count differs from approved machine asset count or asset/prompt IDs are duplicated.
6. `heavy_source_primary`: prompt primary reference is not its matching QA-approved neutral asset.
7. `look_return`: prompt omits the ban on restoring heavy grade/bloom/flare.
8. `stale_prompt`: prompt canon/appearance version does not match its asset.
9. `terminal_overclaim`: generation return is treated as package completion before later-turn visual QA.
10. `unresolved_inside_boundary`: approved Scene Canon keeps a conflict or unresolved region inside minimum-complete coverage.

## Visual Smoke-Test Boundary

A true end-to-end image smoke test requires at least one usable scene reference and a runtime that can continue after each terminal image-generation turn. Without that required reference, report `blocked_missing_scene_reference` for visual smoke only; static package, schema, routing, and negative-fixture tests can still pass. Never substitute a fabricated client reference or claim generated visual evidence that does not exist.
