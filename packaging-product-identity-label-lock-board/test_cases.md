# Packaging Product Identity Board Contract Cases

Executable acceptance suite: `python -B scripts/test_contract.py`.

## Sparse-reference behavior

1. Front, back, and three-quarter photos of a transparent pump bottle with dense bilingual labels and embossing.
   - Pass: one 16:9 board, eight complete views, four to six populated source-derived details, no request for more angles.
2. One complete front photo with readable primary label.
   - Pass conditionally: hidden surfaces are `bounded_inferred` or `unknown`; no exact hidden-copy claim.
3. OCR is unavailable or two OCR candidates disagree.
   - Pass the normal board path; lower only the affected copy authority.
4. User explicitly requests exact print-copy authority without readable sources or artwork.
   - Block the exact-copy claim, not the normal video-reference board.

## Board contract

1. Exactly eight complete views and one frozen count of four to six populated detail panels.
   - Pass when all views are distinct, every panel contains useful product evidence, and the final image is exactly 3840 × 2160.
2. A title, angle label, arrow, number, legend, QA badge, or UI box is visible.
   - Fail `non_product_text_pollution`.
3. One product view is cropped, duplicated, missing, or belongs to another SKU.
   - Fail visual inspection.
4. Generated pseudo-copy is presented as exact.
   - Fail label fidelity or exact-copy authority.
5. Critical label/graphic/material details come from frozen source crops and a deterministic receipt.
   - Pass source-evidence binding.
6. Any blank cell, empty rectangle, reserved slot, placeholder frame, future-fill box, or unused panel is visible.
   - Fail `all_cells_populated` and repair the layout before publication.
7. Two detail overlays target the same cell, one declared cell is unfilled, or a detail crop is near-background-only.
   - Fail deterministic composition mapping or non-background validation.

## Prompt handoff behavior

1. The frozen generation prompt is copied directly into an external image interface with the ordered references.
   - Pass when that single call is instructed to produce a fully populated board without relying on later composition.
2. A prompt asks the model to reserve, keep empty, or later replace any detail region.
   - Fail `blocked_staging_prompt_leakage`; never publish it as a final generation prompt.
3. High-angle or low-angle support views are requested.
   - Keep the product upright on its base and change camera position; a lying-down product fails the view contract.

## Worker and repair behavior

1. Explicit invocation freezes one prompt and ordered source bundle, then one fresh worker makes exactly one image call.
   - Pass when the resolver binds prompt, references, lineage, call ID, and PNG.
2. The main agent calls imagegen directly, one worker calls twice, or a worker makes decisions.
   - Fail the worker contract.
3. Initial attempt plus two repairs all fail.
   - Stop after three total image calls and report the failed checks.

## Forbidden legacy behavior

- Do not derive R8/R12/R16/R24 requirements.
- Do not request 16 source angles because the bottle is transparent, asymmetric, liquid-filled, or pump-operated.
- Do not create rotation/elevation rings, bridge masters, motion envelopes, per-copy-region masters, or require a Canon export as part of board creation.
- Do not split this workflow into additional Skills.
