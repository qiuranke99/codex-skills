# Reference Generation And Authority Contract

## Reference roles

- `hero_core` — the single primary visual anchor for Look Core.
- `state_validation` — proves one or more legal Look States.
- `risk_validation` — proves a high-risk rendering case such as skin, transparent liquid, mirror metal, white packaging or low-light labels.

Exactly one approved reference has role `hero_core`. Every State must be covered by at least one approved reference. One reference may cover several States only if those states are simultaneously and legibly demonstrated.

## Supplied references

Analyze the actual pixels before approval. Record locator, dimensions when available, applicable States, authority scope and conflicts. A supplied reference controls only the look dimensions named in `authority_scope`; it never becomes identity truth by implication.

Every approved reference is a first-class asset. Keep its human/internal `reference_id` for State mapping, but create a distinct nested `artifact.artifact_id`, freeze its `ai-video-artifact-v1` record, and materialize that record as `owned_artifacts/<artifact_id>.json`. Project Canon locks both the image bytes and this JSON record. Downstream model inputs use the artifact ID, never the internal reference ID.

## Generated references

1. Freeze a single-image generation specification and prompt.
2. Persist the prompt hash.
3. Generate one clean independent full-frame image.
4. End the generation turn at the image call.
5. On a later continuation, inspect the actual image.
6. Record actual dimensions, file hash when bytes are available, and inspection result.
7. Approve, repair only this reference, or reject it.

Do not generate one multi-panel board and crop cells into machine inputs. A human contact sheet is a deterministic derivative and never part of `look_reference_set`.

## Integrity states

- `verified_bytes` — file bytes were available and `file_sha256` was calculated.
- `runtime_reference_bound` — the runtime supplied a stable reference identifier but not readable bytes; record the identifier and do not claim byte integrity.
- `pending` — not ready for production binding.

An `assistant_validated` look artifact permits only approved and inspected references. If integrity is `runtime_reference_bound`, the limitation must remain visible; it is not equivalent to byte verification.

## Conflict handling

Resolve conflicts by declared authority:

`approved identity/intrinsic asset > approved Look Core contract > approved state reference > aesthetic prior`

If a look frame changes product color, label, material, face or scene topology, repair or reject the look frame. Do not update identity sources to match a contaminated look frame.
