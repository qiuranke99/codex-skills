# Examples and Test Cases

## Should trigger only when explicit

- `$frozen-moment-camera-coverage Use this still as moment_anchor and produce a four-view minimum ring while freezing the actor, contact with the doorway, room topology, and world-space light.`
- `$frozen-moment-camera-coverage In prompt_only mode, turn this text-defined frozen moment into eight controlled master views and a separate portrait family.`
- `$frozen-moment-camera-coverage Generate targeted reverse angles from these moment, identity, wardrobe, and scene references; keep all hidden surfaces marked as inference.`

## Should not trigger

- `Give me ten visually different cinematic shots with new actions and moods.` Route to free cinematic-shot exploration.
- `Build a neutral empty scene Canon with movement coverage.` Route to Scene Canon.
- `Make a character identity board from this portrait.` Route to a character lock-board capability.
- `Make a multi-angle product identity board.` Route to a product identity capability.
- `Write a video-generation prompt for this shot.` Route to the relevant video prompt/directing workflow.
- `Recover the exact real room behind the photographer from one still.` Return the unsupported-claim boundary.
- An implicit request to rotate the camera around the same moment. Return `blocked_explicit_invocation_required`; do not spawn a worker.

## Positive deterministic cases

1. Image anchor plus `minimum_ring`, prompt-only: four prompts, one family, zero workers, `prompt_package_ready`.
2. Image anchor plus shuffled robust angles: normalize and pass all eight bins.
3. Text anchor plus prompt-only: `synthetic_unrendered`, complete prompts, zero pixel claims.
4. Master and portrait minimum rings: two independent families and two separate completeness reports.
5. Generated synthetic trace: every required view has unique nonce/call/image, passing inspection, and `package_ready`.
6. Honest partial trace: at least one approved view, one exhausted required view, all prompts retained, `partial_handoff_ready`.

## Negative and boundary cases

- Minimum ring with `176.9°` instead of the `180° ±3°` bin: fail missing bin.
- Targeted views with `full_coverage_claim: true`: fail overclaim.
- Master and portrait views combined to fill one ring: fail family mix.
- Same-family FOV, radius, elevation, roll, look-at, crop, or framing drift: fail.
- Duplicate tuple or identical image bytes: fail.
- Small-angle pair without micro-coverage declaration and parallax regions: fail near duplicate.
- Crop/upscale of another view presented as a 90° move: fail visual QA; deterministic exact derivation also fails.
- Head/gaze frozen away from a requested full-face or eye-contact view: fail physical conflict; do not rotate the subject.
- Hidden room, wardrobe, logo, text, or identity detail labeled observed without a source: fail evidence contract.
- A generated coverage image submitted as `view_bridge`, even with a matching minimal inspection: fail as unsupported in v1.
- Worker uses wrong prompt/reference order, calls twice, emits text, or returns an image from another thread: fail binding.
- Image exists without main inspection: fail delivery.
- Approved inspection contains a failed hard check: fail.
- Repair reuses worker, nonce, call, attempt, or overwrites the prior attempt: fail.
- Prompt-only contains a worker spawn or image call: fail.
- Any required view remains repairing, blocked, unstarted, rejected, or uninspected while state claims `package_ready`: fail.

## Visual forward-test rubric

Inspect source and outputs together. Try to disprove camera-only movement by checking:

- whether the actor actually turned or was reposed;
- whether gaze or face presentation was cosmetically changed for the new camera;
- whether contacts, hands, pockets, door edges, and props changed;
- whether the background could be one stable topology rather than a new set;
- whether light stayed in the world rather than following the camera;
- whether different views are mirrors, reframes, or zooms;
- whether newly revealed content is conservative and honestly labeled;
- whether prompt/reference/image lineage identifies exactly what was inspected.

One failed required invariant is enough to reject a view. Do not average hard failures into an aesthetic score.
