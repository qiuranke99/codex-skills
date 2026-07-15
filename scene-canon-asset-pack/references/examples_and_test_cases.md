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

1. `one_machine_plus_review_packaged`: one machine image plus a review board cannot masquerade as a six-image delivery.
2. `missing_required_asset_role`: removing any mandatory graph node fails schema and delivery.
3. `coverage_graph_manifest_gap`: a manifest asset that points to the wrong graph node fails one-to-one reconciliation.
4. `same_asset_multiple_roles`: duplicate role assignment cannot satisfy missing coverage.
5. `same_direction_views`: six files with inadequate direction diversity fail coverage.
6. `duplicate_camera_tuple`: two mandatory nodes cannot share one camera tuple.
7. `exact_duplicate_bytes`: byte-identical files fail even under different paths.
8. `near_duplicate_reencode`: visually identical re-encoding/crop/focal-only coverage fails perceptual duplicate checks.
9. `loop_closure_missing`: motion support without a verified closed path fails.
10. `awaiting_continuation_delivery`: a running queue or user continuation boundary is not delivery.
11. `self_attested_without_runtime`: prose or manifest claims without a bound audited worker receipt fail.
12. `published_prompt_mutated`: a prompt changed after publication fails its SHA-256 binding.
13. `missing_primary_source_anchor`: generated predecessors cannot displace the frozen original scene source from reference 1.
14. `placeholder_qa_report`: placeholder prose cannot substitute for structured QA evidence.

## Visual Smoke-Test Boundary

A true end-to-end image smoke test requires explicit `$scene-canon-asset-pack` invocation, at least one usable user scene reference, the matching project `AGENTS.md` worker exception, and runtime trace access. Without those requirements, report the precise blocked state; static package, schema, routing, resolver, and negative-fixture tests can still pass, but deterministic fixture receipts cannot pass production delivery. Never substitute a fabricated client reference or claim generated visual evidence that does not exist.
