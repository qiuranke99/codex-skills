# QA and Completion Contract

## Main inspection record

Write one `frozen_moment_main_inspection.v1` record per bound attempt. Bind the run, view, attempt, exact inspector thread UUID, inspection time, worker-result path/hash, image path/hash, Moment Canon hash, camera-contract hash, prompt hash, reference-bundle hash, actual dimensions, decision, hard checks, failure codes, repair scope, deviations, and evidence summary.

`record_view_decision.py` must resolve that thread from local Codex state and prove that a completed `view_image` call at `original` detail exposed the exact bound image bytes before `inspected_at_utc`. It freezes the matching call/output events as a hashed rollout slice and records a `frozen_moment_pixel_open_receipt.v1`. Every later state, stage, and delivery validation replays the slice, decodes the actual returned image bytes, and recomputes their hash. Missing, forged, late, wrong-thread, wrong-path, or hash-mismatched pixel evidence fails closed.

Allowed decisions:

- `approved`
- `rejected`
- `repair_required`

Every applicable hard check must be `pass`. Use `not_applicable_with_reason` only where the view contract proves non-applicability. A failed or missing check forbids `approved`.

After the main agent writes the inspection, record the bound attempt through `scripts/record_view_decision.py`. This command recomputes artifact hashes, advances only the affected view and aggregate QA state, validates the complete live state, and rolls both manifest and publication receipt back if validation fails. Do not append attempts by hand.

## Required visual hard checks

- identity and visible age;
- body proportions, skeleton, balance, and root orientation;
- head direction, gaze, expression, and face visibility physics;
- hand, body, wardrobe, prop, and environmental contacts;
- wardrobe, hair, props, text, handedness, and asymmetric details;
- scene topology, object positions, doors/windows, foreground/background ordering;
- instantaneous smoke, liquid, weather, cloth, and action phase;
- world-space light direction, source position, shadow logic, and no camera-following beauty light;
- camera view is meaningfully distinct and belongs to its family;
- expected reveal, occlusion, common anchors, and hidden-region evidence honesty;
- original source remains the highest authority;
- no mirror, crop/zoom substitute, duplicate, or near-duplicate view;
- no unsupported salient invention or commercial retouching artifact.

The main agent must open actual image bytes. Worker text, a tool success event, decoding, dimensions, hashes, similarity metrics, or a review board cannot replace visual inspection.

## Deterministic hard checks

Automatically fail:

- prompt, reference, worker, image, inspection, or state hash mismatch;
- required prompt body absent or unpublished before the applicable worker;
- repeated worker nonce, thread, call, image, or attempt ID;
- exact camera tuple or pixel duplicate;
- incomplete/mixed 4-view or 8-view ring;
- master/portrait aggregation;
- targeted coverage claiming full coverage;
- family-invariant drift;
- approved inspection with any failed/missing hard check;
- a bound image with no main inspection;
- required view marked approved without a bound independent image;
- `package_ready` with a required view blocked, unstarted, repairing, rejected, or uninspected.

Treat weak crop/zoom, homography, mirror, or perceptual similarity as `review_required`, never automatic approval. The main agent decides after checking subject/background parallax and frozen-world consistency.

## Attempt ledger

For each view record required flag, attempt budget/count, attempt IDs, accepted attempt, current status, artifact paths/hashes, supersession, decisions, and failure codes. Required approval must point to exactly one current accepted attempt.

Default budget is two exact-bound attempts. `attempt_revision` is contiguous from one and counts only attempts whose worker, call, image, and lineage were successfully bound. A call whose binding fails is unknown runtime state: stop safely and resolve that uncertainty; it cannot be entered as evidence, consume a fabricated revision, or self-authorize a skipped revision. All state, finalization, and delivery arithmetic uses the same bound-attempt count. Exhaustion enters `blocked_attempt_budget`; it never enters repair or success again without a new explicit user decision that changes the budget.

## Partial handoff

Use `partial_handoff_ready` only when at least one independent view is approved and at least one required view is failed, blocked, or unstarted. Include:

- approved, failed, unstarted, and remaining required view IDs;
- blocker codes per view;
- accepted image hashes;
- the complete prompt-package hash;
- every failed reason;
- `coverage_completeness: partial_required_set`;
- `full_coverage_claim: false`.

Zero approved views is a blocker, not a partial handoff. Partial output can preserve all prompts and usable images, but it cannot be promoted to `package_ready`.

## Terminal-state gates

### `prompt_package_ready`

- mode is `prompt_only`;
- evidence, Canon, coverage, prompts, and references validate;
- every required prompt exists and matches its hash;
- worker spawn and image-call counts are zero;
- no generated-coverage claim.

### `package_ready`

- mode is `generate_and_package`;
- every required view has one current accepted attempt;
- every accepted attempt has bound worker, image, and passing main inspection;
- no unknown in-flight calls;
- all required views are `view_approved`;
- `all_required_views_approved`, `coverage_approved`, and `handoff_finalized` are true in that order;
- prompts, references, accepted images, inspections, and handoff artifacts match their hashes.
- `ACCEPTED_PROMPT_INDEX.json` and `ACCEPTED_REGENERATION_PROMPTS.md` reproduce the exact prompt bytes and lineage of every accepted attempt, including attempt-scoped repair prompts rather than silently falling back to the base prompt.

### `partial_handoff_ready`

- generated mode;
- at least one approved independent view;
- not all required views approved;
- attempt budgets and blockers are explicit;
- full-coverage claim false;
- complete prompt package remains available.

The three terminal states are mutually exclusive.

Finalize only through `scripts/finalize_coverage.py --terminal package_ready|partial_handoff_ready`. The command validates the pre-terminal state and complete delivery, then restores the previous manifest if any terminal gate fails. Directly editing `state.terminal_state` is not an accepted completion path.

## Review board

Compose only from accepted independent images. Use contain/padding, never crop. Record its hash as a derived artifact with `machine_authority: false`. Do not use a multi-panel board as an input replacement for independent view images.
