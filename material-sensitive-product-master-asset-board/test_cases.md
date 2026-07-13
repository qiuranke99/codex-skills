# Material-Sensitive Product Master Asset Board Test Cases

## Green Scenarios

1. **One-request completion**: an explicit Skill invocation authorizes one fresh non-decision image worker for the attempt; the main agent remains active and publishes a non-empty final result without a second user message.
2. **Reference freeze**: every authoritative product/material source is copied into the run-scoped reference bundle in semantic order with byte size, SHA-256, and ordered-bundle hash.
3. **Exact worker binding**: resolver binds one fresh worker thread, one task/turn/nonce, one imagegen call, one completed image event, and one PNG using exact agent path, checkpoint, parent thread, worker thread, and call ID. Because nested Codex task bodies can be stored as encrypted content, the same nonce must appear as one literal declaration in the auditable imagegen exec source.
4. **Tool isolation**: the worker's only primary tool call is imagegen; resolver-linked waits tied to that same yielded image call may occur, but any unrelated tool call fails.
5. **Prompt integrity**: the imagegen prompt is a JSON string literal byte-identical to the UTF-8/LF generation sidecar; the shell-wrapper failure is rejected.
6. **Reference integrity**: the ordered `referenced_image_paths` list exactly equals the frozen manifest and every frozen byte still matches its hash.
7. **Material QA**: the main agent opens the copied board and evaluates primary anchor, complementary views, transparent/reflection/refraction/fill/finish evidence, critical structure, panel legibility, source state, and pollution.
8. **Built-in dimensions**: a source-faithful `1672x941` or `1536x1024` board remains `content_qa_reference`; dimensions alone do not fail QA, trigger repair, or block publication/handoff.
9. **Repair ledger**: up to two focused repairs use attempts 02 and 03 with fresh prompt, nonce, worker, board, result, and QA; one immutable `accepted_attempt.json` selects the final source of truth.
10. **Image-specific 4K**: the final enhancement prompt is created only after accepted-board inspection, names observed defects, and uses the accepted board plus all frozen original material references.
11. **Artifact-backed publication**: the final builder verifies accepted attempt, prompt/board/inspection/worker/reference/handoff hashes and writes one payload containing the board, both complete prompts, both hashes, and published states.
12. **External controls**: external handoff requests only `aspect_ratio: "16:9"` and `image_size: "4K"`; external readiness stays independent from prompt-pair publication.

## Red Scenarios

- Implicit invocation attempts to spawn a worker: `blocked_worker_authorization`.
- Main agent calls imagegen and assumes a continuation: fail.
- Worker thread is missing, stale, wrong-parent, wrong-nonce, or ambiguous: exact `blocked_worker_*` failure.
- Worker task envelope is encrypted and the imagegen exec omits or changes the literal nonce declaration: `blocked_worker_nonce_mismatch`.
- Worker contains zero or multiple imagegen calls/events: fail.
- Worker calls an unrelated tool before or after imagegen: fail.
- Imagegen arguments use a variable, template literal, concatenation, decoy object, shell-command result, or non-literal wrapper: fail.
- Submitted prompt differs by one byte or has the 44-character `Exit code / Wall time / Output` wrapper: `blocked_worker_prompt_mismatch`.
- Reference order, path, size, or hash differs from the manifest: fail.
- Source, copy destination, result JSON, or prompt escapes the frozen run/attempt boundary: fail.
- Image call ID, worker thread ID, or generated path contains unsafe traversal or does not derive the exact PNG path: fail.
- Newest PNG is selected by timestamp: fail.
- Board is not copied into the attempt directory or not visually inspected: fail.
- `assistant_qa_status: failed` is selected as accepted attempt: fail.
- Two accepted attempts exist or failed attempt artifacts are overwritten: fail.
- 4K prompt is frozen before inspection or invents fill level, internal structure, facets, highlights, labels, or material microdetail: fail.
- A `1672x941` board is repaired only because it is not exact 16:9: fail.
- Final claims `published` but omits the board, either complete prompt, either SHA-256, or either published state: fail.
- A prompt is reconstructed after missing sidecar or hash mismatch: fail.

## Required Runtime Proof

Static checks prove contract shape only. Acceptance requires a real local Codex smoke test in which a fresh Skill-using main agent spawns one terminal image worker, the worker imagegen completes with an empty worker final, the main agent resolves the exact PNG from worker thread ID plus call ID, visually inspects it, creates the image-specific 4K prompt, and emits one non-empty final main result containing the complete prompt pair and hashes.

Maintain the 2026-07-10 bracelet rollout `019f4b71-b716-71f0-bfc8-24ec7b650ff5` as a red fixture: main-agent imagegen completed, the submitted prompt had the 44-character shell wrapper, both final records were empty, and the task completed without post-image publication.
