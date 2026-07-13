# Single-Face Character Lock Board Test Cases

## Green Scenarios

1. **One-request completion**: one user request spawns one fresh terminal image worker; the main agent continues without a second user message and publishes a non-empty final result.
2. **Exact worker binding**: the resolver binds one fresh worker thread using the exact agent path whose visible task-name suffix contains the complete run nonce, checkpoint, parent thread ID, parent spawn call/activity/result, byte-identical encrypted task delivery, worker turn ID, completed `image_generation_end`, and call ID.
3. **Prompt integrity**: the prompt in the worker's imagegen call is byte-identical to the UTF-8/LF generation sidecar and has the same SHA-256.
4. **Parseable worker call**: the prompt and references are JSON literals in the imagegen argument object, so deterministic verification does not depend on evaluating arbitrary JavaScript.
5. **Reference integrity**: every source is copied into a run-scoped ordered manifest; the worker call preserves path order and multiplicity, and the resolver rechecks every frozen byte size and SHA-256.
6. **Main-agent inspection**: the main agent opens the run-scoped copied PNG before creating `final_4k_enhancement_prompt`.
7. **One-face topology**: the board contains exactly one visible face in the bust and headless front/back body views, including no reflected or printed faces.
8. **Built-in dimensions**: a source-faithful 1672x941 result is recorded under `built_in_dimensions_policy: evidence_only_nonblocking`; dimensions alone do not fail QA, trigger repair, or block finalization.
9. **Source-bound 4K**: the final 4K prompt uses the Codex board plus original references and names only defects observed in the actual board.
10. **Sidecar integrity**: publication rereads both prompt sidecars and recomputes both hashes; exact bytes appear inline in the final result.
11. **Final main result**: the board, complete `final_generation_prompt`, `generation_prompt_sha256`, complete `final_4k_enhancement_prompt`, `4k_enhancement_prompt_sha256`, and both publication states appear together in one non-empty `final` response.
12. **External controls**: the handoff requests only `aspect_ratio: "16:9"` and `image_size: "4K"`; external readiness remains independent of prompt-pair publication.
13. **Repair isolation**: one repair uses a fresh uniquely named worker and a newly frozen attempt prompt; the main agent never calls imagegen.

## Red Scenarios

- The main agent calls imagegen, produces one image, emits an empty final, and assumes a later continuation: fail.
- The generation prompt appears only in commentary: fail.
- A self-reported continuation boolean exists without a real later turn or a bound worker trace: fail.
- The worker thread is missing, stale, or ambiguous: fail with `blocked_worker_thread_*`.
- The worker belongs to another parent thread, its visible task name lacks the complete run nonce, or its encrypted task delivery is missing/misdirected: fail.
- The parent spawn ciphertext differs from the worker task-delivery ciphertext, or the spawn call/activity/result does not bind one thread and agent path: fail.
- More than one imagegen call or image-end event exists in the worker rollout: fail.
- Image completion precedes the image call, turn IDs disagree, or the worker final is non-empty: fail.
- The worker tool prompt differs by one byte from the frozen sidecar: fail.
- Reference paths are reordered/duplicated or any frozen reference byte changes: fail.
- The newest PNG is selected by timestamp instead of thread ID and call ID: fail.
- The board is not copied into the run directory or is not visually inspected: fail.
- The 4K prompt or handoff sidecar is missing: fail.
- The final claims `published` but omits either complete prompt, either hash, or the board: fail.
- The event-message final and UI `response_item` differ, the displayed hash is wrong, or the final is not byte-identical to the built payload: fail.
- A prompt is reconstructed after a sidecar or hash mismatch: fail.
- A 1672x941 board is repaired only because the pixels are not exact 16:9: fail.
- Enhancement creates a head or face in either body panel: fail.

## Required Runtime Proof

Static tests prove contract shape only. Before claiming the automatic architecture works on a Codex surface, run an isolated worker smoke test and prove: worker imagegen completed, worker final was empty as required, the parent continued, the parent resolved the exact PNG from worker thread ID plus image call ID, and the parent could inspect that PNG.
