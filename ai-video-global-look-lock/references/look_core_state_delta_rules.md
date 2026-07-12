# Look Core, State And Delta Rules

## Authority split

The look owns rendered appearance under light. It does not own object identity.

| Question | Authority |
|---|---|
| What exact product, person or scene is this? | approved identity/canon asset |
| What is the product's intrinsic color/material/label? | approved product, packaging and material asset |
| What is the shot's framing, action or camera movement? | Shot Contract, Storyboard and Previs |
| How do light, color relation, contrast, highlight, black, skin, optics, grain and atmosphere render? | Global Look |

When evidence conflicts, identity and intrinsic sources outrank look references for object truth. Look references outrank identity boards only for their declared look dimensions.

## Core test

A property belongs in `look_core` if changing it would make the project feel like a different visual language across most shots. Examples: palette relation, light-source hierarchy, contrast shape, black floor, highlight roll-off, complexion treatment, material highlight behavior, optical diffusion, grain family and atmospheric philosophy.

Core does not mean identical values in all scenes. It defines relationships and behavior.

## State test

A property belongs in a `look_state` when the environment, time, practical sources or exposure family require a distinct legal manifestation of the same Core. A State must retain every Core invariant. Use a new State for materially different interior/exterior, daylight/night, warm practical/cool ambient, high-key/low-key or underwater/surface conditions when a local delta would be too large.

Do not create states merely because every shot looks slightly different.

## Delta test

A `shot_look_delta` is allowed only when all answers are yes:

1. The shot still visibly belongs to its assigned State.
2. No Core invariant changes.
3. Product intrinsic color/material and skin identity remain protected.
4. The variation is narrow, named and reversible.
5. The delta is necessary for the shot rather than stylistic novelty.

Examples: a half-stop relative darkening, slightly denser environmental haze, reduced halation around a critical label, or a narrowly cooler background separation while skin and product remain protected.

The structured Delta is not complete until the Skill deterministically renders and freezes `shot_look_delta_prompt_full` with exactly these lines: authority header, boolean `active`, JSON-array `scope`, exact `description`, exact `reason`, and boolean `preserves_look_core`. Storyboard frames, keyframes, control previs and video prompts copy that complete block byte-for-byte. They may not reconstruct or paraphrase it.

## Product and material boundary

Distinguish:

- `intrinsic`: base color, transparent/translucent structure, metallic finish, glass thickness, liquid color and fill, gloss/matte boundary, label/logo and construction;
- `rendered`: highlight direction, reflected environment, exposure, shadow density, color adaptation and local contrast under the approved look.

The Look may define rendered response. It may not change intrinsic properties. A warm grade cannot turn a verified white package cream, shift a brand red, remove transparency, invent iridescence or turn frosted glass glossy.

## Skin boundary

Preserve source-supported complexion, undertone, marks and age. The Look may define exposure, highlight texture, color separation and grain. It may not whiten, tan, smooth, reshape, de-age or change identity.

## Single-state versus multi-state

- One coherent environment and lighting family: one State plus one approved hero reference can be sufficient if product/material/skin risks are covered.
- Multiple materially different conditions: define separate States and approve at least one reference covering each State. A single hero image is still the Core anchor, not proof of every State.
- A color card is auxiliary evidence only and never counts as the sole hero or state reference.
