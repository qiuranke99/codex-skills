---
name: multi-angle-product-identity-lock-board
description: "Create a text-free six-view identity board for one simple, mostly opaque product, with visual QA and a complete generation/enhancement prompt pair. Use for low-risk geometry; route exact labels, optical materials, mechanisms, and changing product states to specialized workflows."
---

# Multi-Angle Product Identity Lock Board

Generate one horizontal 16:9-requested 2x3 board with six complete, distinct
views of the same low-risk product. Preserve product identity. This package
is independently usable; downstream project integration is optional.

Contract: `asset_board_contract_version: direct_image_prompt_pair_v4`.

## Check suitability and source authority

Require a usable target-product image. It controls identity; a sample board
controls layout only. Check geometry, label, material, structure, and state
risk. This method fits clear silhouettes, simple construction, mostly opaque
surfaces, and non-critical markings. Moderate geometry may be handled with
explicit source limits; high risk or unresolved identity is unsuitable.

Route exact packaging copy to a packaging workflow; identity-critical glass,
liquid, cream, transparency, refraction, chrome, or mirror behavior to a
material workflow; hinges, folding, internal mechanisms, and changing states
to a complex-product workflow. Do not claim six generated views establish
hidden engineering truth. Advertising scenes and prompt-only requests are
outside this fixed board workflow.

Record visible silhouette, proportions, color placement, material finish,
seams, openings, panels, handles, straps, buttons, laces, texture direction,
and markings. Mark each required detail as `source_verified`,
`source_inferred`, or `needs_source`. Keep one product variant. Ask only for
missing evidence that materially prevents the requested identity fidelity;
leave unsupported hidden details unresolved.

## Compose six views

1. Front or primary view.
2. Rear.
3. Left profile.
4. Right profile.
5. Slight overhead top view, or underside when more informative.
6. Three-quarter front, or three-quarter rear when needed to avoid repetition.

Use a neutral white or light-gray seamless background, soft diffused light,
subtle grounding shadows, consistent scale, generous margins, and no overlap.
Keep every product complete and uncropped. Preserve source-supported geometry,
colors, construction, materials, texture, and markings. Exclude non-product
titles, labels, numbers, arrows, callouts, UI, watermarks, people, props, scenes,
and advertising styling.

Request horizontal 16:9. Record actual dimensions and ratio separately.
Dimensions alone do not fail content QA, trigger repair, or block the prompt
handoff. Never infer native 4K or an unexposed model from prompt wording.

## Generate and inspect directly

Use the currently available built-in image tool under its current reference
and output rules. This one-board task requires no subagent, collaboration slot,
Codex database, rollout parser, nonce, or encrypted-message chain.

1. Use the user's output directory, or a distinct run under
   `outputs/product-locks/<asset_id>/`. Preserve source files and old attempts.
2. Inspect the sources and assign ordered aliases with explicit roles. Use
   supported local-file or conversation-image reference transport; do not
   invent paths or substitute a generated panel as unseen source truth.
3. Write the complete `final_generation_prompt` in the requested language,
   save exact UTF-8/LF bytes, read them back, and calculate
   `generation_prompt_sha256`. Preserve the reference list and attempt ID,
   then submit that exact prompt to the image tool.
4. Bind the result to the actual call response or returned artifact. Record
   identifiers when exposed and leave unavailable ones unknown. Never pick
   the newest image in a shared output directory.
5. Inspect the completed image as soon as it is available. Continue in the
   same turn when the host permits; preserve pending state only when the
   real tool or host requires waiting or a continuation. Do not request a
   second user message merely to run visual QA.
6. Save the image in its attempt directory and record path, observed
   dimensions, and file hash when bytes are available. A visible image without
   accessible bytes is not a persisted, hash-verified package; state that limit.

Check six distinct complete views, consistent identity, geometry, colors and
materials, supported construction, no extra text, and correspondence with the
submitted prompt. `assistant_qa_status` may be `passed`, `conditional` for
source-limited usefulness, or `failed`. Critical topology or identity failure
cannot pass. Keep production approval separate and explicit.

Allow at most two focused repairs when each targets an observed defect that
can plausibly be corrected. Each gets a new prompt, hash, result, and QA record.
Do not overwrite failed attempts. Select one accepted attempt and use only
its image and generation prompt for final delivery.

## Prepare the external enhancement prompt

After inspecting the accepted board, write `final_4k_enhancement_prompt` using
both the board and all authoritative original references. Name only observed
panel defects. Preserve the 2x3 topology, view assignments, complete products,
spacing, silhouette, proportions, interfaces, seams, texture, colors, finish,
and supported markings. Do not invent unseen structure or exact copy.

Request exact 16:9 at the selected provider's actual 4K tier. Record the board,
source bundle, requested model/settings, and readiness in a concise handoff.
Missing source references or unexposed provider controls keep external
readiness false; they do not prevent delivery of the prepared prompt with
those limits stated. Submission requires task authorization and an actual
call; a completed prompt is not a submitted or verified external generation.

Save the exact enhancement bytes and calculate
`4k_enhancement_prompt_sha256`. External verification requires inspection of
the returned file, preserved six-view geometry and seams, no invented product
detail, the complete source bundle, actual dimensions, and evidence for the
requested provider resolution profile.

Codex-native 4K is optional and off unless explicitly requested. Track its
target resolution, observed pixels, and native provenance separately. A native
4K claim requires a source artifact at least 3840x2160 with the requested 16:9
ratio and evidence excluding resize/export enlargement. External enhancement
cannot supply that native provenance.

## Deliver

Read both accepted prompt sidecars again and verify their recorded hashes.
Do not reconstruct missing or mismatched text. By default, show the board,
both complete prompts, both hashes, concise QA, observed dimensions, source
limits, and external readiness in the final response. Honor the user's
requested delivery format. If complete prompts cannot fit inline, provide
their complete saved files and disclose the delivery format; never silently
truncate text or withhold a useful board to satisfy a display template.

Complete only after generating and inspecting the real board and preparing
its accepted generation/enhancement prompt pair. An image-only answer or a
promised future inspection is incomplete. Byte integrity does not prove
visual accuracy, hidden geometry, native resolution, or human approval.

After explicit production approval, an optional project handoff may export
the board and prompt paths/hashes, asset key, affected Shot UIDs,
`authority_mode: geometry_only`,
`control_roles_authorized: [product_geometry]`,
`authority_stage: terminal_product_canon`, and
`terminal_route_decision: not_applicable`. Do not confer packaging-copy or
material-behavior authority, write Project Canon, or require another package
to finish this board.

Maintenance examples are in [test_cases.md](test_cases.md).
