# Character Final Lock Board Test Cases

## Acceptance Scenarios

1. **Built-in request**: `final_generation_prompt` requests one horizontal 16:9 board and offers no alternate ratio.
2. **Non-blocking dimensions**: a source-faithful 1672x941 built-in result records dimensions under `built_in_dimensions_policy: evidence_only_nonblocking`; it does not fail content QA, trigger repair, demote the board, or block 4K handoff.
3. **Terminal call**: imagegen is the generation turn's final action; the turn ends with `task_finalization_status: awaiting_post_generation_continuation` and is only stage-complete.
4. **Continuation required**: the next continuation inspects the actual returned board before creating `final_4k_enhancement_prompt`.
5. **High-angle branch**: `required | optional | off` remains inside this Skill; a required high-angle panel and its crown-hair continuity survive 4K enhancement.
6. **Source bundle**: 4K handoff requires the Codex board plus the original identity, wardrobe, shoe, accessory, and prop references.
7. **Identity-safe texture**: enhancement recovers only source-supported skin and hair microtexture; it rejects beauty retouching, face reshaping, age drift, and invented pores or marks.
8. **Mandatory persistence**: generation cannot start unless the exact generation-prompt sidecar is persisted and readable; failure yields `blocked_generation_prompt_persistence`.
9. **Sidecar integrity**: publication rereads both prompt sidecars as original UTF-8/LF bytes and recomputes both hashes; missing bytes or mismatch yields `blocked_prompt_pair_integrity` with no reconstruction.
10. **Final main result**: the `final` channel contains the complete inline `final_generation_prompt`, `generation_prompt_sha256`, `final_4k_enhancement_prompt`, and `4k_enhancement_prompt_sha256`; commentary, paths, sidecars, excerpts, summaries, or hashes alone fail.
11. **Finalization states**: final publication sets `task_finalization_status: final_main_result_published` and `main_result_prompt_pair_status: published` only after the full verified pair appears.
12. **External controls**: third-party generation still requires exact `aspect_ratio: "16:9"` and `image_size: "4K"`; prompt-pair readiness does not imply `external_4k_status: handoff_ready` until controls, provider, references, and handoff sidecar are ready.
13. **External fidelity**: external verification requires original references plus Codex board, identity/topology fidelity, runtime evidence, and a passed source-fidelity gate.
14. **Output capacity**: if one final response cannot contain both complete prompts, return `blocked_final_output_capacity`; never truncate, summarize, link-only, or split while claiming `published`.
15. **Standalone package**: copy only this Skill directory to a fresh root; identity routing, prompt planning, and completion-state evaluation proceed without probing or synchronizing any neighboring package.
16. **Optional project handoff**: absent AI-video integration cannot block or demote an accepted board; only an external integrator may consume the locked artifacts after assistant QA, byte/hash readback, and explicit production approval.

## Counterexamples

- The generated image is the only main result and both prompts remain in commentary: fail.
- The later result says "prompts saved" and links sidecars without complete inline text: fail.
- A 1672x941 built-in board is repaired only because its pixels are not exact 16:9: fail.
- A prompt is reconstructed from chat after its sidecar hash fails: fail.
- A `final` response omits either publication-status field and promises to update it afterward: fail.
- The entrypoint refuses to start because an unrelated suite checkout, neighboring Skill, or external project integrator is absent: fail.
- This package attempts to import or invoke a project-Canon writer: fail; it may only hand locked artifacts to an external integrator after the existing approval gates pass.
