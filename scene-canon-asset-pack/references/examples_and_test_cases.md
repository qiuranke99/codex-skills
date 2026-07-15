# Examples And Test Cases

## Trigger Examples

- “Use these three room photos to create a reusable neutral scene asset pack with reverse/high/low coverage and 4K handoff prompts.”
- “Extend this single sunset building image into a consistent exterior Scene Canon without preserving the sunset grade.”
- “Build environment plates for this ocean storm while preserving wave direction and storm structure.”
- “Create a canonical black-hole scene pack; preserve accretion-disk inclination but remove lens bloom.”

Do not trigger for a storyboard, one shot anchor, character/product lock, Look Master, Lighting Master, ordinary retouch, source-image search, simple upscale, or video prompt.

An otherwise matching six-scene-asset request that does not explicitly invoke
`$scene-canon-asset-pack` must return `blocked_explicit_invocation_required`.
The main agent must not promise to perform the package later through generic
`imagegen`, ask only for a reference upload, or generate the six assets
directly. No Scene worker or image call is authorized.

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
15. `live_origin_relabel`: changing fixture origin labels cannot replace replay of real parent/worker rollout lineage.
16. `non_executable_path`: valid node and edge IDs still fail when their ordered sequence cannot execute the declared path.
17. `duplicate_4k_prompt_ids`: six assets cannot share one 4K prompt ID; Canon, asset back-pointers, and records must reconcile one-to-one.
18. `schema_additional_properties` and `non_finite_number`: schema-valued maps and JSON numbers fail closed instead of accepting malformed dimensions or `NaN`.
19. `empty_core_markdown`: present-but-empty Canon, appearance, or asset-index Markdown is not delivery.
20. `hrb_reuses_machine`: `HRB_001` must pixel-match the deterministic six-asset composite and cannot reuse any machine path or bytes.
21. `primary_reference_ghost`, `duplicate_source_id`, and `source_locator_escape`: source IDs are unique, primary must exist, and packaged source locators remain local and decodable.
22. `loop_edges_unrelated`, `ghost_edge_path`, `closure_landmark_ghost`, and `dangling_adjacency`: graph, path, loop, adjacency, and closure references are exact and bidirectional.
23. `envelope_reveal_ghost`, `edge_reveal_ghost`, `node_evidence_ghost`, and `node_completion_ghost`: all motion, reveal, evidence, completion, and landmark references resolve inside the frozen boundary.
24. `negative_publication_time` and `foreign_publication_parent`: publication uses non-negative time, one bound event index, and the same finalizing parent as all workers.
25. `wrong_worker_asset`, `attempt_mismatch`, and `inspection_owner`: worker namespace, target asset, accepted attempt, and parent inspection owner cannot be relabeled.
26. `same_pixels_reencoded`: identical decoded pixels fail even when bytes, claimed pose, and claimed reveal differ.
27. `tiny_4k_target` and `missing_4k_reference`: every 4K record uses the frozen target at least 3840×2160 and exactly the matching local approved asset.
28. `stale_structured_qa`: every asset/edge/path/loop/package QA record binds the exact required asset hashes and inspection receipt IDs.
29. `stage_attempt_mismatch` and `stage_inspection_owner`: the contiguous-prefix stage gate rejects stale attempt IDs or a foreign inspection owner before any later worker can dispatch; a schema-only state check cannot authorize advancement.
30. `unlisted_frozen_reference`: an asset-scoped `references/` directory must contain exactly the files listed in its bound manifest; stale or unlisted bytes fail.

## Visual Smoke-Test Boundary

A true end-to-end image smoke test requires explicit `$scene-canon-asset-pack` invocation, at least one usable user scene reference, the matching project `AGENTS.md` worker exception, and runtime trace access. Without those requirements, report the precise blocked state; static package, schema, routing, resolver, and negative-fixture tests can still pass, but deterministic fixture receipts cannot pass production delivery. Never substitute a fabricated client reference or claim generated visual evidence that does not exist.
