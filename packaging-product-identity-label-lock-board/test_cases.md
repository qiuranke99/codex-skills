# Packaging Product Identity Board Contract Cases

Executable acceptance suite: `python -B scripts/test_contract.py`.

## Sparse references and copy truth

1. Front, back, and three-quarter photos of a transparent pump bottle with dense bilingual labels and embossing.
   - Pass: no request for more angles; a source-cited ordered copy ledger; a borderless nine-region board.
2. OCR returns plausible but conflicting Chinese/Latin strings.
   - Pass: every candidate remains in the ledger, but only source-reconciled lines become `approved_exact`.
3. An `ocr_only` line is marked `approved_exact`.
   - Fail `blocked_copy_ledger_unverified_exact`.
4. The prompt says “preserve all text” but omits the compiled copy block.
   - Fail `blocked_copy_prompt_coverage`.
5. User requests exact copy without readable source or artwork.
   - Block `exact_copy_evidence`; the normal `video_reference` path may continue with explicit unknowns.

## Board topology and visual grammar

1. Seven complete views plus closure/top and one local detail.
   - Pass with exactly nine total regions.
2. A distinct third detail is needed for a separate copy/embossing/code risk.
   - Pass with ten total regions; eleven fails.
3. Both sides, multiple redundant three-quarters, or a six-panel lower strip are added.
   - Fail the fixed seven-view/two-to-three-detail contract.
4. Any full product is cropped, lying down, duplicated, merged, or overlapped.
   - Fail visual inspection.
5. A white rectangle, grid divider, card outline, evidence strip, panel frame, or visible border appears.
   - Fail `no_visible_frames`; a compositor plan with `border_px > 0` also fails deterministically.
6. A declared region is blank, near-blank, reserved, or unused.
   - Fail raw-board inspection or composition mapping.
7. A raw board contains a visible card/grid/blank region, but later source overlays cover it.
   - Fail `blocked_raw_board_qa`; final composition cannot upgrade a failed raw board.

## Copy pixel QA

1. Approved front-label lines are present in a source-reprojected detail and match ledger order.
   - Pass copy coverage.
2. A full view contains readable pseudo-Chinese or changed English even though the detail crop is correct.
   - Fail `board_wide_invented_or_corrupted_visible_copy`; the correct close-up does not excuse board-wide gibberish.
3. A source-reprojected region lacks `source_backed_pixels: true`.
   - Fail copy-QA binding.
4. An approved copy region has no accepted exact/source-reprojected board region.
   - Fail `blocked_copy_qa_coverage`.
5. All claimed exact lines are reviewed and source/artwork-backed with no candidates or unknowns.
   - `exact_copy_evidence` may pass.
6. All lines visually match, but the final pixels are model-rendered rather than source/artwork-backed.
   - The normal `video_reference` path may pass; `exact_copy_evidence` fails.

## Prompt and worker behavior

1. The frozen prompt includes the seven named views, exact detail count, no-frame bans, observed product facts, explicit unknowns, and compiled copy block.
   - Pass as an independently usable external generation prompt.
2. Prompt publication occurs after worker spawn or is replaced by a path/hash summary.
   - Fail dispatch trace.
3. The worker inherits context, reads the Skill, calls another tool, rewrites the prompt, or makes more than one image call.
   - Fail thin-worker contract.
4. A completed call differs only by omission of the file-terminal LF.
   - Re-resolve the same PNG; do not regenerate.
5. No image arrives within 15 minutes.
   - Stop `BLOCKED_IMAGEGEN_TIMEOUT`, do not create an orphan retry, and return the complete prompt.
6. The complete prompt is compiled only after the 180/120-second deadline.
   - Return it truthfully with `BLOCKED_PROMPT_READY_TIMEOUT`; do not continue to generation.
7. The user explicitly overrides the Skill to request prompt/evidence only.
   - Record `USER_SKIPPED_GENERATION`, spawn no worker, and record zero generation time.
8. The same prompt-only override misses the prompt-publication deadline.
   - Record `BLOCKED_PROMPT_READY_TIMEOUT`, preserve `user_prompt_only_override`, spawn no worker, and record zero generation time.
9. Raw-board QA uses arrays/objects where view IDs or numeric counts are required.
   - Reject deterministically with `blocked_raw_board_qa`; never crash with a Python type error.

## Forbidden legacy behavior

- Do not derive R8/R12/R16/R24 capture requirements.
- Do not require 16 source angles because packaging is transparent, asymmetric, liquid-filled, or text-heavy.
- Do not treat prompt enumeration alone as exact-copy proof.
- Do not accept visible gibberish because a close-up happens to be correct.
- Do not split this workflow into additional Skills.

## Standalone package and optional handoff

1. Copy only this Skill directory to a fresh root and run
   `python -B scripts/test_contract.py`.
   - Pass: all package scripts, templates, and tests resolve within the copied
     package; no neighboring Skill or external suite is inspected.
2. The package entrypoint attempts to synchronize or validate an unrelated
   suite before source freezing or prompt compilation.
   - Fail: source freezing and prompt compilation start directly from this
     package.
3. An AI-video project integrator is absent.
   - Pass: the accepted packaging board and its copy authority are unchanged;
     project handoff is optional and external.
4. The package attempts to import or invoke a project-Canon writer.
   - Fail: it may only expose locked board/copy artifacts after the package
     validator passes and production approval is explicit.
