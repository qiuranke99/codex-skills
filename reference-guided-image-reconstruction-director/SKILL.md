---
name: reference-guided-image-reconstruction-director
description: Produce prompt-only, manually executable reconstruction direction when a supplied target must retain its composition while semantic geometry defects or references require attribute-level authority control. Use for reference-constrained isomorphic rebuilding, staged structure-to-realism planning, or exact-asset compositing decisions. Never use this Skill to generate or edit pixels, operate an image platform, or perform ordinary sharpening, denoising, upscaling, or unconstrained edits.
---

# Reference-Guided Image Reconstruction Director

## Purpose

Turn one target image and zero or more optional references into a source-bound, prompt-only reconstruction package for the user to execute manually on an external platform. Separate recoverable composition intent from malformed pixels, and prevent a realism, material, lighting, identity, or style reference from silently taking over camera, crop, layout, object count, or other protected structure.

The terminal deliverable from this Skill is text: diagnosis, authority decisions, manual upload/exclusion instructions, direct-copy external-platform prompts, parameter guidance, QA, and directional retry instructions.

## Prompt-Only Hard Boundary

- Set every structured contract to `execution_boundary: manual_external_prompt_only`.
- This Skill produces manual external-platform prompt plans; it does not generate or edit pixels. Direct-copy verbs such as “create,” “edit,” and “reconstruct” address the user-operated platform.
- If the user requests direct generation or editing, route that task to the appropriate available image tool or Skill instead of imposing this manual workflow. Carry forward the user's reference roles and composition constraints, and do not label tool-generated output as a user-manual external result.
- Read-only visual inspection of supplied or user-imported images, including `view_image`, is allowed. Do not alter pixels, create masks, or render candidates. Do not use any image generation/editing tool for QA.
- Do not call third-party APIs or automate browser/platform login, upload, submission, polling, download, account, or session actions. The user performs those actions manually on Nano Banana 2 or another chosen high-resolution platform.
- A request for “4K,” “high resolution,” or a pixel size is a target and a platform-settings recommendation. Semantic prompt text cannot guarantee actual pixel dimensions, native resolution, or successful upscaling; report the required platform control as observed, user-reported, or unknown.

## Non-Negotiable Boundaries

- Inspect every readable image before assigning it a role. Do not infer content from filenames.
- Preserve source filenames, dimensions, provenance, rights state, and unreadable or missing evidence as facts. Never promote an inference into source truth.
- Record reference roles as `known`, `inferred`, `chosen`, or `unknown`; include a non-empty evidence or reasoning statement. An `unknown` reference may remain inventoried but cannot receive resolved primary/allow authority or appear in a manual external stage upload list. Ask only when resolving it would materially change inheritance or workflow.
- A fresh package remains `prompt_package_ready`. Only after the user manually produces a result on an external platform and imports it with provenance may the contract use `structure_master_candidate`, `candidate_unapproved`, or `qa_failed_directional_retry_ready`. The Skill did not generate that result and cannot mint candidate status from a prompt alone.
- Never call an imported result `LOCKED`, approved, exact, final, or bug-free without the required external human decision.
- Keep text, logos, brands, faces, product identity, and hidden geometry missing when exact evidence is absent. Use an exact-pixel or compositing lane when regeneration would fabricate facts.
- Keep source facts, user decisions, and manual external stage records in separate ledgers. A later prompt or imported output cannot rewrite an earlier fact or approval.

## Minimal Workflow

1. Inventory the target and all references. Verify that there is exactly one target; zero references is valid.
2. Visually diagnose pixel defects separately from semantic geometry, perspective, occlusion, count, identity, text, material, and lighting defects.
3. Assign one primary source per attribute and bound what every reference may and may not change. Resolve conflicting composition, identity, material, and style authority before writing prompts. Use the exact scope grammar and validation rules in [reference-authority-contract.md](references/reference-authority-contract.md) only when producing a structured JSON contract.
4. Normalize every removal into an explicit exception, whether or not `preserve_all` is true. Include shadows, reflections, contact traces, occlusion residue, revealed background, and reference-driven reintroduction in the removal closure, and make every reference deny all removed entities.
5. Route the base task to one of the modes below. Add an exact-asset composite lane when identity or text must remain exact.
6. Produce a stage-by-stage manual upload and exclusion list, direct-copy prompts, narrow negative constraints, platform-parameter guidance, hard QA gates, and a directional retry plan. For each actionable external stage, at least one listed input must be a primary/allow source for every attribute that stage requires. Put the target first in `pixel`, `local`, `isomorphic`, and `structure`; put the approved master first in `realism`.
7. Stop at the relevant manual/human gate. A blocked plan contains no actionable external stage. A structure-master prompt plan remains `prompt_package_ready`; `structure_master_candidate` is legal only after the user imports the manually generated external result with provenance. An intermediate structure master must be explicitly approved and listed first before it can govern a realism stage.

## Mode Routing

- **Implicit-routing boundary:** a standalone ordinary request to sharpen, denoise, deblur, or upscale an otherwise correct image does not trigger this Skill. `pixel_restore` is an internal diagnostic/manual-handoff route only after this Skill is already in scope for a reference-guided or composition-preserving reconstruction problem (or the user explicitly invokes it) and inspection establishes that no semantic reconstruction is needed. It still produces prompts and settings guidance only; it never performs the restoration.
- `pixel_restore`: Plan a user-operated external restoration when the content, geometry, identity, and text are already correct and only noise, compression, blur, or resolution is defective.
- `constrained_local_edit`: The change and its physical traces can be bounded while pixels outside the repair region remain authoritative.
- `single_stage_isomorphic`: The target's scene topology and camera intent are recoverable, defects are bounded, and reference contamination risk is low enough for one controlled reconstruction.
- `staged_structure_to_realism`: Geometry defects are distributed, reference images conflict with protected structure, or an intermediate structural gate is needed. Stage 1 normally receives only the target. Stage 2 receives an approved structure master plus limited-role references and normally excludes the original problem target.
- `exact_asset_composite`: Preserve or replace exact product, face, character, logo, label, typography, or other truth-sensitive pixels separately. A composite stage is substantive only when it includes at least one `exact_asset` and either a target/structure-master base input or a validated `base_stage_id` pointing to an earlier actionable external stage. This may be the primary mode or a lane after another mode.

Do not mechanically choose two stages. Read [workflow-modes.md](references/workflow-modes.md) for the decision tree, vetoes, no-reference path, and original-target reuse exception.

## Authority and Prompt Compilation

Read [reference-authority-contract.md](references/reference-authority-contract.md) whenever references, deletions, exact identity, text, brands, or conflicting instructions are present. It defines the three ledgers, protected attributes, authority matrix, conflict rules, and the JSON validation contract.

Read [prompt-compilation.md](references/prompt-compilation.md) after the mode and authority matrix are stable. Compile provider-neutral semantic instructions first, then adapt labels, manual upload order, and settings guidance to user-supplied or otherwise reliable interface facts. Do not open or operate the platform. A “style reference” never grants unlimited authority.

Read [failure-modes-and-qa.md](references/failure-modes-and-qa.md) before accepting an intermediate master, assessing a final candidate, or preparing a retry.

## Output

Follow the user's requested language, template, length, and deliverable. For a prompt-only request, return the clean copyable prompt plus essential upload instructions; keep diagnostic notes brief. A full report or structured contract is optional unless requested or needed to resolve conflicting authority.

When a full reconstruction report is requested, use these components:

1. `diagnosis`: observed defects, uncertainty, and why pixel restoration is or is not sufficient.
2. `source_and_decision_ledgers`: preserved source facts and explicit user decisions.
3. `reference_authority_table`: one row per source and attribute family, including forbidden inheritance.
4. `mode_decision`: selected base mode, optional exact-asset lane, rejected alternatives, and blocking unknowns.
5. `stage_plan`: purpose, user-performed upload order, included inputs, excluded inputs, role labels, settings, and acceptance gate for every external stage.
6. `direct_copy_prompts`: copy-only, external-platform prompts with stage-specific positive instructions plus a compact `must_not_inherit` block.
7. `platform_parameter_guidance`: separate semantic prompt constraints from user-selected aspect ratio, pixel dimensions, quality, file, or upscale settings; mark unavailable controls unknown and never promise prompt-guaranteed 4K.
8. `qa_checklist`: structure, count, deletion closure, identity, text, material, and contamination checks.
9. `directional_retry_plan`: change only the defect-owning stage or source scope while preserving already accepted invariants.
10. `status`: use `prompt_package_ready` for every fresh text package. Candidate/retry states require an actual user-manual external result imported with provenance; blocked states remain available when evidence is insufficient.

When a structured reconstruction contract is requested, use the complete schema
and examples in [reference-authority-contract.md](references/reference-authority-contract.md)
and run `scripts/validate_reconstruction_contract.py` before handoff. A fresh
text package uses `execution_boundary: manual_external_prompt_only`,
`delivery_state: prompt_plan`, and `status: prompt_package_ready`. Candidate
states require a real imported external result with provenance. A passing
contract proves internal consistency only, not pixels, provenance truth,
dimensions, visual quality, or human approval.
