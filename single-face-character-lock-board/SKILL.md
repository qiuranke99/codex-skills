---
name: single-face-character-lock-board
description: "Create one text-free character identity board from references: one visible-face bust and headless front/back wardrobe views. Use for this exact three-part topology, with source-bound visual QA and a complete generation/enhancement prompt pair."
---

# Single-Face Character Lock Board

Generate one horizontal 16:9-requested board with exactly three components:
one bust containing the only visible face, one headless front body view, and
one headless back body view. Both body views extend from neck to complete feet.
This package is independently usable; project integration is optional.

Contract: `asset_board_contract_version: direct_image_prompt_pair_v4`.

## Resolve identity and reference roles

Require a usable reference for one selected identity. Combine identity evidence
only when the images depict the same person. A different person's outfit may
control wardrobe when assigned that role, but cannot change the target face.
If multiple identities remain plausible, ask for the target; do not blend or
choose a preferred face. Missing identity evidence blocks generation.

Bind identity, hair, skin, body, outfit, shoes, and accessories to the supplied
references. Distinguish `user_locked`, `source_supported`, `safe_inferred`, and
`missing_or_conflicting` details. Preserve user assignments; never describe an
inferred back view or garment detail as observed. If exactness is required but
the evidence is missing, identify the affected requirement rather than invent it.

Requests for ordinary turnarounds, expression sheets, multiple candidates,
composite identities, or prompt-only delivery belong outside this fixed board
workflow. Respect the user's requested task instead of imposing this board.

## Compose the board

- Bust: chest-up or upper-body, frontal or near-frontal, neutral expression;
  preserve facial geometry, age markers, skin tone, marks, hairline, hairstyle,
  facial hair, and identity-critical jewelry supported by the sources.
- Front body: neck to complete feet, readable front construction, waist,
  pockets, hems, and footwear; no head or partial face.
- Back body: neck to complete feet, readable back collar, seams, pockets,
  hems, and shoe backs; no head, turned head, profile, or partial face.

All components share body proportions, wardrobe, shoes, and accessories.
Use a neutral-gray studio background, soft even light, minimal shadow, and
realistic photographic texture. Keep the board text-free. Exclude extra
panels, people, heads, faces in prints or reflections, mirrors, expression
tiles, labels, measurements, UI, watermarks, scenes, and editorial styling.

Request horizontal 16:9. Record the actual returned dimensions and ratio;
an aspect-ratio mismatch alone does not fail content QA or justify repair.
Prompt wording cannot prove native 4K or the identity of an unexposed model.

## Generate and inspect

Use the currently available built-in image tool directly. Follow its current
reference-input and output rules. This workflow requires no subagent, Codex
state database, rollout parser, encrypted-message binding, or sibling Skill.

1. Use the user's output directory, or a distinct run directory under
   `outputs/character-locks/<asset_id>/`. Preserve source files and old attempts.
2. Inspect source images and assign stable aliases. Preserve their ordered
   reference roles in the call. Use local paths when available; use supported
   conversation-image references when appropriate. Do not invent missing paths.
3. Write the complete `final_generation_prompt` in the requested language.
   Save its exact UTF-8/LF bytes without a metadata wrapper; read them back and
   compute `generation_prompt_sha256`. Send that exact text to the image tool.
   Preserve the prompt, reference list, and attempt identity before generation.
4. Generate the board. Bind the result using the actual tool response or its
   returned image artifact. Record the call identifier when exposed; leave it
   unknown otherwise. Never select the newest image in a shared directory.
5. Once the call has completed and its result is available, inspect that result
   in the same turn when the host permits. If the actual host ends the turn or
   the result is pending, preserve state and resume inspection when available.
   A completed call alone is not a completed or approved board.
6. Save the accepted image in the run directory and record its path, dimensions,
   and file hash when bytes are available. A visible result without accessible
   bytes may be reviewed, but cannot be described as a persisted, hash-verified
   package. Report the specific unavailable artifact without inventing evidence.

Check all three components, exactly one face anywhere in the image, complete
feet, identity and wardrobe consistency, and absence of text or extra panels.
Record actual observed defects. `assistant_qa_status` is `passed`, `conditional`
for source-limited usefulness, or `failed`; critical identity or topology drift
cannot pass. `production_approval_status` changes only on explicit approval.

Allow one focused repair when it can plausibly fix the dominant failure. Save
a new prompt, hash, and result for that attempt. Inspect it before accepting it;
the final prompt must belong to the accepted image, not the rejected attempt.

## Create the image-specific 4K handoff

After inspecting the accepted board, write `final_4k_enhancement_prompt`.
Use that board for layout and the original references for identity and detail.
Preserve the exact three components, crop, pose, source-supported appearance,
and single-face topology, including prints and reflections.

Name only defects observed in that image. Recover source-supported skin, hair,
and garment detail while preserving natural asymmetry. Do not reshape the
face, alter age, beautify, invent pores or marks, add garment construction,
or introduce another person, face, panel, logo, background, or decoration.

Request exact 16:9 at the selected external provider's 4K tier. Keep those
requested controls separate from observed resolution and native provenance.
If provider controls or original references are unavailable, deliver the
prepared prompt with the missingness stated and keep external readiness false.
A prompt pair does not prove external submission, 4K output, or visual approval.

Save the exact enhancement prompt bytes and calculate
`4k_enhancement_prompt_sha256`. Keep a concise handoff record with the board,
original references, requested provider/model if selected, settings, and actual
readiness. Do not call an external paid platform without task authorization.

## Deliver the complete result

Read both accepted prompt sidecars again and verify their recorded hashes.
Do not reconstruct missing or mismatched text from memory. By default, show
the accepted board, both complete prompts, both computed hashes, concise QA,
observed dimensions, and external-handoff status in the final response.
Follow a user-specified delivery format; if complete text does not fit inline,
provide the complete saved files and state what was delivered. Never silently
truncate a prompt or withhold an otherwise usable board because a display
template is too large.

Completion requires the real board, actual visual inspection, the accepted
generation prompt, and its image-specific enhancement prompt. An image-only
result or a promised future inspection is incomplete. Hash checks establish
byte consistency, not identity truth or human approval.

Optional project handoff may export the approved board and prompt paths/hashes,
asset key, affected Shot UIDs, `authority_mode: identity_and_wardrobe`,
`control_roles_authorized: [identity, wardrobe]`,
`authority_stage: terminal_character_canon`, and
`terminal_route_decision: single_face_character`. Require explicit production
approval for that authority promotion; do not write Project Canon or require
an external integrator to finish this board.

Maintenance examples are in [test_cases.md](test_cases.md).
