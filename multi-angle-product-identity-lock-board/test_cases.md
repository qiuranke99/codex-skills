# Multi-Angle Product Identity Lock Board Test Cases

## Green Scenarios

1. **One-request completion**: one explicit `$multi-angle-product-identity-lock-board` request spawns one fresh terminal image worker; the main agent continues without a second user message and publishes a non-empty final result.
2. **Exact worker binding**: the resolver binds one fresh worker thread, one completed `image_generation_end`, and one PNG using the exact agent path, checkpoint, thread ID, and call ID.
3. **Prompt integrity**: the worker's imagegen prompt is byte-identical to the UTF-8/LF generation sidecar and has the same SHA-256.
4. **Parseable worker call**: prompt and references are JSON literals in the imagegen argument object.
5. **Reference integrity**: the worker contains exactly the ordered run-scoped `referenced_image_paths`; manifest bytes, order, source hashes, and bundle hash all match.
6. **Main-agent inspection**: the main agent opens the copied run-scoped PNG before creating `final_4k_enhancement_prompt`.
7. **Six-view topology**: exactly six distinct complete views show the same product with no repeated angle, crop, overlap, invented structure, or non-product text.
8. **Built-in dimensions**: a source-faithful 1672x941 board is recorded under `built_in_dimensions_policy: evidence_only_nonblocking` and can pass content QA.
9. **Source-bound 4K**: the final 4K prompt uses the Codex board plus original references and names defects observed in the bound board.
10. **Sidecar integrity**: publication rereads both prompt sidecars and recomputes both hashes; exact bytes appear inline.
11. **Final main result**: `scripts/build_final_result.py` proves the accepted-attempt, worker, inspection, board, manifest, prompt, and handoff chain before the board, both complete prompts, both hashes, and both published states appear together in one non-empty `final` response.
12. **Repair isolation**: one repair uses a fresh worker and a newly frozen attempt prompt; the main agent never calls imagegen.
13. **Optional native 4K**: the native branch is off by default and never borrows evidence from an external enhancement.

## Red Scenarios

- The main agent calls imagegen, produces one image, emits an empty final, and assumes a later continuation: fail.
- The generation prompt appears only in commentary: fail.
- Implicit invocation is disabled; a non-explicit route must not spawn a worker.
- A self-reported continuation boolean exists without a bound worker trace: fail.
- The worker thread is missing, stale, or ambiguous: fail with `blocked_worker_thread_*`.
- More than one imagegen call or image-end event exists: fail.
- The tool prompt differs by one byte from the frozen sidecar: fail.
- Ordered reference paths differ from the frozen manifest: fail.
- Two references are swapped or a frozen source byte changes after the manifest is written: fail.
- The canonical worker path omits the exact 32-hex nonce suffix, adds a follow-up turn, emits non-empty final text, or makes a post-image tool call: fail.
- The newest PNG is selected by timestamp instead of thread ID plus call ID: fail.
- The board is not copied into the run directory or not visually inspected: fail.
- Any of the six views is missing, repeated, cropped, or shows conflicting product geometry: fail QA or repair.
- A repair overwrites an earlier attempt or publishes a non-accepted attempt's generation prompt: fail.
- The 4K prompt or handoff sidecar is missing: fail.
- The final claims `published` but omits the board, either complete prompt, either hash, or either published state: fail.
- A prompt is reconstructed after a sidecar or hash mismatch: fail.
- A 1672x941 board is repaired only because its pixels are not exact 16:9: fail.

## Required Runtime Proof

Static checks prove contract shape only. Before claiming this architecture works on a Codex surface, run an isolated worker smoke test and prove: worker imagegen completed; the worker final was empty as required; the parent continued; the resolver bound the exact PNG using worker thread ID plus call ID; the parent inspected that PNG; and a non-empty complete prompt-pair final trace passes while captured Oran failure thread `019f4b5a-e57c-7e60-a3f8-fdbec4babcb3` fails with main-agent imagegen, empty final, missing worker binding, missing inspection, and missing 4K sidecar violations.
