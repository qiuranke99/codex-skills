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
- exact frozen prompt text and prompt path/hash;
- exact ordered run-scoped reference paths and manifest/hash;
- instruction to call built-in image generation once and end with no text.

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

## Exact binding

Resolve one worker using the current Codex state database and exact canonical agent path. Bind:

- parent thread, worker thread, worker turn, spawn call, and encrypted task delivery;
- full nonce, view ID, attempt ID, and attempt revision;
- exactly one image-generation call and completion event;
- exact prompt bytes and ordered reference paths;
- returned call ID and the path derived from worker thread plus call ID;
- copied run image bytes, dimensions, format, and SHA-256.

Reject wrong parent, wrong worker, ambiguous thread, nonce reuse, call reuse, prompt/reference drift, non-empty worker final, missing completion, a newest-file guess, or a saved path that does not equal the thread/call-derived path.

Use `prompt_binding_mode: exact_bytes`. Do not add transport-normalization exceptions without new live evidence and dedicated negative tests.

## Reference freezing

Copy one to five ordered original-source references into each attempt directory. The first text-generated V00 instead uses the explicit zero-reference bundle and omits the image tool's reference parameter. Reject symlinks, path escape, nested or unlisted files, duplicate aliases, duplicate frozen paths, changed bytes, wrong first authority, every generated view-bridge role, and every non-null bridge-origin field.

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

Do not overwrite rejected or superseded attempts. Keep them under the run evidence tree with reasons.
