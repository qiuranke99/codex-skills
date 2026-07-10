# Character Casting Lock Board Test Cases

## Acceptance Scenarios

1. **Single reference**: plan the fixed main board; mark invisible back/side/shoe/bag evidence `safe_inferred`, never verified.
2. **Same person, multiple views**: combine identity evidence and preserve one target across portrait/front/back/side views.
3. **Different people, no selection**: return `selection_pending`; make no image call and do not blend faces.
4. **Explicit role assignments**: keep one selected identity while using other-person images only for assigned wardrobe or accessory evidence.
5. **Multiple candidates requested in one board**: route outside the Skill; do not create a comparison contact sheet.
6. **Fixed topology**: require one large frontal portrait and complete front, back, and side full-body views.
7. **Text-free conflict**: reject names, role labels, numbers, measurements, notes, arrows, or film-edge codes inside the image.
8. **Upper-body extension**: plan B only when a named continuity risk is material, cannot be read on A, and has source evidence or allowed inference.
9. **Hair extension**: plan C only for source-backed hair continuity risk that the main board cannot show legibly.
10. **Accessory extension**: plan D only for a source-backed shoe, bag, handheld, or accessory risk that the main board cannot show legibly.
11. **No decorative expansion**: never add expressions, silhouettes, generic poses, product ads, or scene panels.
12. **Runtime capability**: record `runtime_capability_snapshot`; do not claim model, seed, raster, or native 4K provenance unless exposed.
13. **Prompt trace**: freeze `final_generation_prompt`, compute `generation_prompt_sha256`, and set `prompt_disclosed_before_generation: true` before the image call.
14. **Terminal call**: set `terminal_generation_call: pending` before generation; only the later tool/runtime trace may prove `executed`; emit no text and call no tool after image generation in that turn.
15. **Multi-board package**: advance at most one generation call per turn; review or repair A before generating B, C, or D.
16. **Status separation**: before generation, keep `assistant_qa_status: pending_post_generation_inspection` and `production_approval_status: not_granted`; only explicit user or external-pipeline authorization may grant production approval.
17. **Later visual review**: only a later independent inspection may set assistant QA to `passed`, `conditional`, or `failed`.
18. **Repair**: freeze and disclose a new exact prompt and hash before a corrective terminal call; never attach a rejected prompt hash to a repaired image.
19. **Prompt-only false success**: a prompt without the image call does not complete the Skill.
20. **Unavailable runtime**: return `hard_blocked_generation_runtime`; do not claim an image or approval.
21. **Built-in request**: every main or extension `final_generation_prompt` requests one horizontal 16:9 board and offers no alternate ratio.
22. **Non-blocking dimensions**: a source-faithful 1672x941 built-in result records dimensions under `built_in_dimensions_policy: evidence_only_nonblocking`; it does not fail content QA, trigger repair, demote the board, or block per-board/package 4K handoff.
23. **Draft is not final**: before a board exists, keep `4k_enhancement_prompt_status: draft_pre_generation`; do not emit `final_4k_enhancement_prompt` or its hash.
24. **Per-board 4K traceability**: every generated A, B, C, or D board receives its own inspected-board-specific `final_4k_enhancement_prompt`, SHA-256, and handoff sidecar; omitted boards receive none.
25. **Complete reference bundle**: require the inspected Codex board plus all original identity and board-relevant references; a board-only enhancement is blocked for source fidelity.
26. **External runtime controls**: request exactly `aspect_ratio: "16:9"` and `image_size: "4K"`; when either control is unavailable, use `blocked_runtime_controls` and select no fallback.
27. **Returned-file evidence**: record provider, model, surface, model profile, requested settings, observed pixels, provider aspect-ratio profile, observed file aspect ratio, aspect-ratio evidence, and 4K evidence before `verified`.
28. **Identity-safe microtexture**: recover only source-supported facial, skin, and hair detail; reject beauty retouching, face reshaping, age drift, or invented pores and marks.
29. **Topology preservation**: 4K enhancement preserves A's portrait/front/back/side topology and each extension's approved evidence job without adding panels, faces, people, or styling systems.
30. **External status separation**: `handoff_ready`, `pending_external_generation`, `returned_unverified`, `verified`, and `rejected` remain distinct from assistant QA and production approval.
31. **Accepted-board count invariant**: `generation_attempt_count` includes every original or repair call; `generated_board_count` counts unique accepted/current board IDs only and equals `finalized_4k_prompt_count == 4k_prompt_hash_count == 4k_handoff_sidecar_count`.
32. **Continuation state**: every terminal generation turn is only stage-complete with `task_finalization_status: awaiting_post_generation_continuation`; the next continuation resumes inspection and prompt-pair finalization.
33. **Sidecar integrity**: before publication, reread each board's two prompt sidecars as original UTF-8/LF bytes and recompute both hashes; a missing sidecar or mismatch yields `blocked_prompt_pair_integrity` with no reconstruction.
34. **Final main result**: one later `final`-channel result includes, for every generated board, the complete inline `final_generation_prompt`, `generation_prompt_sha256`, `final_4k_enhancement_prompt`, and `4k_enhancement_prompt_sha256`; commentary, paths, sidecars, excerpts, summaries, or hashes alone fail.
35. **Published identity and count**: the final response itself declares published states only when `published_board_ids == accepted_board_ids` and `published_prompt_pair_count == generated_board_count`.
36. **Mandatory persistence**: no board generation starts unless its exact generation-prompt sidecar is persisted and readable; failure yields `blocked_generation_prompt_persistence`.
37. **External-state independence**: a verified prompt pair may become task-ready while external status remains `not_ready`; set per-board `handoff_ready` only after provider controls, original references, Codex board, and handoff sidecar are all ready.
38. **Accepted repair binding**: a failed A attempt followed by accepted A repair yields `generation_attempt_count: 2`, `generated_board_count: 1`, and publishes only the accepted repair prompt/hash with its `accepted_attempt_id`.
39. **Output capacity**: if one final response cannot contain every accepted board's complete pair, return `blocked_final_output_capacity`; never truncate, summarize, or split while claiming `published`.

## Quick Validation Checklist

- Folder and frontmatter name match `character-casting-lock-board`.
- Description states the fixed casting-board topology and identity selection gate.
- Main board remains text-free portrait/front/back/side casting documentation.
- Extension boards require a named evidence-closing risk.
- The seven shared runtime fields are present.
- Prompt disclosure precedes the terminal image-generation call.
- No post-generation prompt or QA response is required in the same turn.
- `assistant_qa_status` and `production_approval_status` are independent.
- `built_in_prompt_aspect_ratio_request: "horizontal 16:9"` and `built_in_dimensions_policy: evidence_only_nonblocking` are present.
- `final_4k_enhancement_prompt`, `4k_enhancement_prompt_sha256`, and `finalized_post_inspection` are present.
- The external bundle requires `codex_asset_board` and `original_source_references`.
- External runtime fields request `aspect_ratio: "16:9"` and `image_size: "4K"`.
- Per-board 4K prompt/hash/sidecar count equals the accepted/current board count, not generation attempts.
- Final main result requires every complete prompt pair inline in the `final` channel.
- `published_prompt_pair_count == generated_board_count` before package finalization.
- `published_board_ids == accepted_board_ids`; no rejected or superseded attempt prompt is published.
- Built-in ratio mismatch never fails content QA or blocks handoff; external exact 16:9 and 4K controls remain mandatory.
