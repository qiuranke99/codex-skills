# Contract test cases

Use these fixtures for static or forward validation. Passing requires the exact expected state; visual plausibility cannot override a state failure.

## Built-in dimensions are nonblocking

1. A built-in board returns `1672x941`, and all six views, geometry, seams, interfaces, and source identity pass.
   - Expect `built_in_dimensions_policy: evidence_only_nonblocking`.
   - Expect `codex_board_role: content_qa_reference` and content QA `passed`.
   - Forbid ratio-triggered repair, demotion, conditional QA, or 4K-handoff blocking.
2. Repeat with `1536x1024`; expect the same state behavior.
3. `native_4k_branch: off`; forbid any native-resolution field from affecting default completion.

## Terminal generation and continuation

1. Before generation, persist exact `final_generation_prompt` bytes, re-read them, verify `generation_prompt_sha256`, then call image generation as the turn's final action.
2. After the call, expect `task_finalization_status: awaiting_post_generation_continuation` and `main_result_prompt_pair_status: pending`; forbid a task-complete claim.
3. In the next continuation, inspect the actual board, finalize the board-specific 4K prompt, persist and re-read it, then verify both hashes.

## Final main result

The final channel must contain the complete unabridged values of all four fields in one main result:

- `final_generation_prompt`
- `generation_prompt_sha256`
- `final_4k_enhancement_prompt`
- `4k_enhancement_prompt_sha256`

Fail when either prompt appears only in commentary, an earlier turn, a path, a sidecar, an excerpt, or a summary. On success expect `main_result_prompt_pair_status: published` and `task_finalization_status: final_main_result_published`.

If output capacity cannot hold both complete prompts, expect `blocked_final_output_capacity`; forbid truncation, splitting, or a published claim.

## Integrity and external 4K

1. Mutate one byte in the generation sidecar after generation. Expect `blocked_prompt_pair_integrity`; forbid reconstruction.
2. Omit either the original product references or Codex board from the external bundle. Expect handoff not ready.
   - Even when both prompt hashes pass, `prompt_pair_ready` must not set `external_4k_status: handoff_ready`.
3. Omit exact external `aspect_ratio: "16:9"` or `image_size: "4K"` controls. Expect `blocked_runtime_controls`.
4. Return an external 4K board with a repeated view, moved seam, new port, or geometry drift. Expect external QA `failed` and `external_4k_status: rejected`.
