---
name: frozen-moment-camera-coverage
description: "Use only when the user explicitly invokes this Skill and wants one text-defined or reference-anchored frozen cinematic moment explored from controlled camera positions, with an evidence-bounded Frozen Moment Canon, configurable camera coverage, complete per-view prompts and ordered reference bindings, optional built-in image attempts through fresh non-decision workers, and actual-image continuity QA. Do not use for free cinematic variation, new actions or moments, character or product identity boards, neutral scene canon, true-scene reconstruction claims, retouching, video prompts, video generation, or implicit requests without worker authorization."
---

# Frozen Moment Camera Coverage

Build source-anchored, auditable views of one frozen moment while changing only declared camera variables. Treat built-in image generation as an opaque local tool. Preserve portable prompts and evidence even when no images are generated or some views fail.

## Read the required contracts

Read these files directly from this Skill before executing the matching branch:

- Always read `references/evidence_and_claims_contract.md`.
- Read `references/camera_and_prompt_contract.md` before freezing coverage or prompts.
- Read `references/worker_orchestration_contract.md` before any image worker.
- Read `references/qa_and_completion_contract.md` before inspecting or publishing images.
- Read `references/examples_and_test_cases.md` when routing, input sufficiency, or a boundary case is unclear.
- Use `references/coverage_manifest.schema.json` and `references/coverage_manifest.template.json` as the machine contract.

## Enforce the entry gate

Require explicit invocation of `$frozen-moment-camera-coverage` for every run. If the request only resembles this workflow, do not begin it and do not spawn a worker; return `blocked_explicit_invocation_required` with the exact invocation the user can send.

Accept either:

- `image_anchor`: one or more local reference images with declared roles; require a `moment_anchor` first.
- `text_anchor`: a concrete frozen moment description. Mark its Canon `synthetic_unrendered` until a generated anchor is inspected.

Require a requested mode:

- `prompt_only`: compile and publish the complete package with zero workers.
- `generate_and_package`: compile prompts, then generate serially and inspect actual images.

If the user explicitly invokes the Skill but omits the mode, use `generate_and_package`. If the user says not to generate, use `prompt_only`.

Block missing input as `blocked_missing_input`. Block unresolved conflicts between equal-authority sources as `blocked_conflicting_authority`; report the exact fields and source IDs instead of silently choosing.

## Keep the production boundary

Own one job: controlled camera coverage of one frozen moment.

Do not:

- create free variations of action, time, weather, lighting, wardrobe, or story;
- claim a single image recovered the real unseen reverse side;
- substitute character, product, packaging, or neutral-scene asset boards;
- turn cropping, mirroring, zooming, subject rotation, or relighting into a claimed new camera position;
- generate video or write downstream video prompts;
- treat an accepted generated view as higher authority than an original source;
- import a sibling Skill at runtime.

For free multi-shot exploration route to the adjacent cinematic-shot exploration capability. For explicit geometry, depth, or scan-based reconstruction, report that this Skill only produces source-anchored plausible coverage.

## Choose one coverage profile

- `targeted_views`: one to three user-declared views. Label the result targeted exploration, never full coverage.
- `minimum_ring`: exactly four required master views at `0`, `90`, `180`, and `-90` degrees.
- `robust_ring`: exactly eight required master views at 45-degree intervals from `0` through `315` degrees.
- `custom`: explicit view list with a stated completeness claim no stronger than its coverage.

Create a separate `portrait_ring` camera family for close-ups. Do not mix master and portrait views in one family. Within a family freeze radius, height, elevation, roll, focal/FOV policy, focus target, look-at target, framing class, and subject-scale policy unless the user explicitly authorizes a new family.

Angles are targets and QA labels, not claims of exact execution by the image tool.

## Preserve authority and change permissions

Classify every relevant fact as exactly one of:

- `observed`
- `source_corroborated`
- `inferred`
- `unknown`
- `approved_canon`

Use ordered reference roles:

1. `moment_anchor`
2. `identity_anchor`
3. `wardrobe_anchor`
4. `scene_topology_anchor`
5. `look_anchor`

Do not feed a generated coverage view back as reference authority in v1. Generated view bridges remain unsupported until the package can preserve and replay their complete origin package, attempt, worker, image, inspection, and supersession lineage.

Hard-freeze identity, visible age, body proportions, hair, wardrobe, asymmetric details, root position, pose, balance, head direction, expression, gaze, contacts, props, scene topology, object positions, temporal state, and world-space light sources. Permit only declared camera variables and their natural projection, reveal, occlusion, and view-dependent material consequences.

## Execute the workflow

### 1. Freeze evidence

Create the run root outside the public Skill repository. Materialize references with:

```powershell
python scripts/freeze_reference_bundle.py --view-id V00 --source "source_01:moment_anchor:<input-root>\frame.png" --output <run-root>\00_manifest\REFERENCE_BINDINGS.json
```

Use one to five ordered references. The sole exception is the first generated V00 of a `text_anchor`: freeze an explicit zero-reference attempt bundle with `--allow-empty-text-anchor`, and omit `referenced_image_paths` from that worker call. Record role scopes, original and frozen paths, byte sizes, SHA-256 values, rights state, and the ordered-bundle digest. Keep source paths outside the frozen destination.

### 2. Freeze the Moment Canon and camera matrix

Populate an input specification from `references/coverage_manifest.template.json`. Record:

- source and uncertainty policies;
- observed, inferred, unknown, and approved Canon fields;
- subjects, pose, contacts, scene topology, time state, lighting, and look;
- camera families, required views, expected visibility, new reveals, and evidence risk.

Compile the run package:

```powershell
python scripts/compile_coverage_plan.py <input-spec.json> <run-root>
```

Inspect the generated JSON and every prompt. Do not continue if the compiler reports an unsupported claim, mixed family, incomplete ring, or authority conflict.

### 3. Publish prompts before generation

For image input, freeze and publish all required-view prompts, prompt SHA-256 values, camera contracts, and ordered reference plans before the first worker.

For text input in `prompt_only`, publish a `synthetic_unrendered` package and use zero workers.

For text input in `generate_and_package`, first freeze and publish only the V00 anchor prompt, generate and inspect V00, and pass the real V00 attempt through the stage validator. A self-written inspection cannot unlock coverage. Before compiling coverage, preserve immutable anchor-phase manifest, publication-receipt, and full-prompt-document snapshots. Every later validation replays the original V00 worker, image, and main-inspection chain from those snapshots. Then freeze the accepted V00 pixels as the first source, freeze the visible Canon, and publish all remaining required-view prompts before the first coverage worker. Unrendered text evidence may cite `text_brief` but may not claim `observed` or `source_corroborated` image authority.

Never claim unrendered text supplied visible pixel evidence.

### 4. Generate through serial non-decision workers

Only use workers when the user explicitly invoked this Skill and the active repository instructions contain the matching narrow authorization.

For each attempt:

1. Capture a time checkpoint and create a fresh 32-hex nonce.
2. Spawn one fresh `fork_turns="none"` worker named `frozen_coverage_image_<view-id-lower>_<nonce>`.
3. Give it exactly one frozen prompt, one view/attempt ID, and the ordered run-scoped references.
4. Require exactly one built-in image-generation call and an empty final response.
5. Wait for that worker to finish before starting another.
6. Bind its exact thread, call, prompt, references, and returned image with `scripts/resolve_worker_image.py`; preserve immutable parent-rollout and coverage-manifest snapshots in the attempt directory.

The worker must not interpret evidence, choose or modify a view, change the prompt, retry, inspect, approve, repair, publish, or delegate.

Do not start a replacement while the prior call state is unknown. Use at most two attempts per view by default.

### 5. Inspect actual pixels

Open the original references and each bound generated image. Write `main-inspection.json` for every attempt. Use the hard gates in `references/qa_and_completion_contract.md`.

After writing the inspection, atomically append the bound attempt and decision to the manifest:

```powershell
python scripts/record_view_decision.py <run-root> --view-id <view-id> --attempt-id <attempt-id> --worker-result <worker-result.json> --inspection <main-inspection.json>
```

Reject any required view with changed subject pose, gaze, contact, handedness, scene topology, world-space light, camera-family invariants, unsupported salient invention, lineage ambiguity, crop/zoom masquerade, mirror, or duplicate/near-duplicate coverage.

Use deterministic checks only for structure, hashes, decodability, dimensions, camera tuple uniqueness, prompt/reference lineage, pixel duplicate candidates, and completion arithmetic. They never replace visual judgment.

### 6. Validate state and deliver

Run during execution:

```powershell
python scripts/validate_coverage_package.py --mode state <run-root>
python scripts/validate_coverage_package.py --mode stage --through-view <view-id> <run-root>
```

Run final validation:

```powershell
python scripts/finalize_coverage.py <run-root> --terminal package_ready
python scripts/validate_coverage_package.py --mode delivery <run-root>
```

Use `--terminal partial_handoff_ready` only after every remaining required view has exhausted its recorded attempt budget and at least one required view is approved. Both mutation commands validate immediately and restore the prior manifest on failure; do not hand-edit attempt or terminal state fields.

Build a human-only review board from approved independent images:

```powershell
python scripts/build_review_board.py <run-root> <run-root>\40_handoff\REVIEW_BOARD.png
```

Downstream authority remains the independent accepted images, prompt sidecars, reference bindings, and manifest—not the review board.

## Enforce the state machine

Common path:

```text
intake_pending -> evidence_locked -> moment_canon_locked -> coverage_locked -> prompts_locked
```

Prompt-only terminal:

```text
prompts_locked -> prompt_package_ready
```

Generated success:

```text
prompts_locked -> generation_in_progress -> inspection_pending -> view_approved
all_required_views_approved -> coverage_approved -> handoff_finalized -> package_ready
```

Repair and incomplete paths:

```text
inspection_pending -> repair_required -> generation_in_progress
inspection_pending -> blocked_attempt_budget -> partial_coverage -> partial_handoff_ready
```

Enter `all_required_views_approved` only when every required view has a bound image, a passing main-agent inspection, approved lineage, and current `view_approved` status. Never let repair, exhausted attempts, optional-only coverage, or prompt-only artifacts enter `coverage_approved`.

Terminal states are mutually exclusive: `prompt_package_ready`, `package_ready`, or `partial_handoff_ready`.

## Publish the complete handoff

Always return:

- source evidence and inference ledger;
- Frozen Moment Canon and camera families;
- coverage matrix and completeness label;
- every complete prompt and SHA-256;
- ordered reference roles, paths, and hashes;
- exact generated-attempt lineage when applicable;
- per-view inspection and rejection reasons;
- independent accepted images;
- portable master-regeneration prompts;
- terminal state and unresolved required views.

Call the result `source-anchored plausible coverage`. Do not call it a recovered real reverse angle, a geometric reconstruction, or proof of a shared physical scene.

## Completion gate

Complete only when the package validator exits successfully for the selected terminal state and every required artifact exists. If any required view exhausts its attempts, deliver the usable prompts and approved views as `partial_handoff_ready`; do not claim full generated coverage.
