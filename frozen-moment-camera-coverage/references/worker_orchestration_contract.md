# Worker Orchestration Contract

## Authorization

Use image workers only after an explicit `$frozen-moment-camera-coverage` invocation and only under the matching active repository authorization. The Skill description, default prompt, implicit match, package state, or main-agent desire cannot create authority.

`prompt_only` always uses zero workers. An implicit request returns `blocked_explicit_invocation_required` and the minimal explicit invocation.

## Queue invariant

- maximum parallel image workers: one;
- one fresh `fork_turns="none"` worker per attempt;
- one view and one attempt per worker;
- one built-in image-generation call per worker;
- no replacement while a prior call is unknown;
- default attempt budget: two per required view;
- every repair creates a new attempt, nonce, worker, call, prompt hash, and reference bundle.

Use the task name:

```text
frozen_coverage_image_<normalized-view-id>_<32-lowercase-hex-nonce>
```

The complete nonce must appear in the observable task name. Never guess a worker by recency.

## Worker input

Give the worker only:

- exact view and attempt IDs;
- exact frozen prompt bytes and prompt path/hash, including the compiler's terminal LF;
- exact ordered run-scoped reference paths and manifest/hash;
- instruction to call built-in image generation once and end with no text.

The image-generation argument object is exact: `prompt` plus `referenced_image_paths` for a nonempty frozen bundle, or `prompt` alone for a zero-reference anchor. `num_last_images_to_include` and every unlisted property are forbidden. On Windows, serialize reference paths with forward slashes or a static `String.raw` literal. Never place a backslash path such as `\10_runtime` in a plain JavaScript template/string: escape interpretation can abort the wrapper before generation, and the worker has no retry authority. The main agent must validate transport serialization before spawn.

Do not give it alternative prompts, creative options, source interpretation tasks, QA rubrics, repair authority, or publishing work.

## Worker prohibitions

The worker must not:

- interpret or select evidence;
- select, rename, or modify a view;
- change the prompt or reference order;
- call another tool before image generation;
- retry or spawn another agent;
- inspect, approve, reject, repair, or publish;
- emit a textual final response.

One narrow runtime continuation is allowed after the single generation call yields: `wait` may target only the exact cell ID named by that call's running receipt, must be non-terminating, must stay within the frozen duration/output bounds, and must have one matching output. No other function call, different cell, termination, more than five continuations, or second image call is valid.

## Exact binding

Resolve one worker using the current Codex state database and exact canonical agent path. Bind:

- parent thread, worker thread, worker turn, spawn call, encrypted task delivery, and exactly one completion receipt;
- full nonce, view ID, attempt ID, and attempt revision;
- exactly one outer image-exec call, one matching wrapper output, and one inner image-generation completion event;
- exact prompt bytes and ordered reference paths;
- exact frozen prompt repeated by the inner completion event;
- the inner generation call ID and the path derived from worker thread plus that call ID;
- copied run image bytes, dimensions, format, and SHA-256.

The outer `exec` call ID and inner generation-event call ID are different runtime namespaces and must not be equated. Bind them by exclusive containment and ordering: one outer wrapper, no second image call, an exact revised-prompt match, one inner completion, its thread-derived saved path, and the matching wrapper or bounded-wait receipts. Reject wrong parent, wrong worker, ambiguous thread, nonce reuse, call reuse, prompt/reference drift, hidden image inputs, non-empty worker final, missing completion, a newest-file guess, or a saved path that does not equal the thread/inner-call-derived path.

The completion receipt may be either one matching `sub_agent_activity` completion event or the current runtime's one empty `FINAL_ANSWER` mailbox receipt. The mailbox form must immediately follow `inter_agent_communication_metadata` with `trigger_turn: false`, use the exact worker path as sender, use the exact parent path as recipient, carry the spawn turn ID, and contain no payload text. If both forms appear, or either is ambiguous, reject the chain.

Use `prompt_binding_mode: exact_bytes`. Prompt dispatch must preserve the compiler's terminal LF; use an out-of-band sentinel or place a static template literal's closing delimiter on the following line. Do not describe the prompt as ending at its final punctuation, because that strips the LF. Do not add transport-normalization exceptions without new live evidence and dedicated negative tests.

## Reference freezing

Copy one to five ordered original-source references into each attempt directory only after the current run has compiled. Bind the attempt bundle to the current compiled manifest's source-evidence, Moment-Canon, and reference-plan digests; never reuse those digest values from another run. The first text-generated V00 instead uses the explicit zero-reference bundle and omits the image tool's reference parameter. Reject symlinks, path escape, nested or unlisted files, duplicate aliases, duplicate frozen paths, changed bytes, wrong first authority, every generated view-bridge role, and every non-null bridge-origin field.

Record source evidence, Moment Canon, reference plan, per-file, and ordered-bundle hashes. A generated output cannot replace or supplement the original moment anchor in v1.

At resolution time, freeze exact `parent-rollout-at-resolution.jsonl` and `coverage-manifest-at-resolution.json` bytes beside the worker result. Delivery validation must re-hash and replay those immutable snapshots; a changing live parent rollout is not durable attempt evidence.

## Main-agent ownership

The main agent alone:

- defines evidence, Canon, families, views, prompts, and reference plans;
- spawns and waits for workers;
- binds the exact returned image;
- opens original and generated pixels;
- writes the inspection;
- decides approved, rejected, repair, blocked, partial, or final;
- publishes the handoff.

Worker success means only that one bound call returned an image. It never means the view passed.

## Repair and invalidation

Record root cause, preserved invariants, mutable repair fields, new prompt/reference hashes, and the superseded attempt. Repairs must use a fresh worker, nonce, call, and inspection.

Create repairs only with `scripts/prepare_repair_prompt.py`. It writes the fixed attempt-scoped paths `00_manifest/repair-prompts/<view>/<attempt>.zh.txt` and `.publication.json` transactionally. The receipt binds the immediately preceding failed attempt, image and inspection, base and parent prompts, failure codes, repair scope, Canon, camera, reference plan, coverage contract, and publication checkpoint. It may not reuse any historical prompt hash, skip a revision, exceed the frozen budget, follow an approved attempt, or mutate `manifest.prompts`, `prompt_set_sha256`, `coverage_contract_sha256`, or the base publication.

The worker resolver, decision recorder, state/stage/delivery validator, and resolution snapshot all replay the repair receipt. A retry without this authority fails closed.

Do not overwrite rejected or superseded attempts. Keep them under the run evidence tree with reasons.
