# Prompt-First Worker Orchestration Contract

## Authority

Explicit `$scene-canon-asset-pack` invocation plus the matching project `AGENTS.md` exception authorizes one fresh non-decision worker per actual generation attempt. The main agent retains every decision. An implicit trigger cannot authorize any worker and must stop before generation.

## Prompt Publication Gate

Freeze all six generation prompts before the first worker. Write them to `00_manifest/GENERATION_PROMPTS.md` and to six manifest records. Each record binds:

- asset and graph node ID;
- dependency stage and predecessor asset IDs;
- complete UTF-8/LF prompt body;
- prompt SHA-256;
- ordered reference paths and their ordered-bundle SHA-256.

Publish all six prompt bodies inline in one assistant update with their IDs and hashes. Create `10_runtime/prompt-publication-receipt.json` only after publication. The receipt must bind the finalizing parent thread ID, parent rollout path/hash, the unique assistant event ID and event index, prompt-document hash, all six prompt IDs/hashes, non-negative elapsed publication time, and the later first-worker spawn time/index. The strict validator checks that the bound parent rollout has the same session ID, the runtime event occurs exactly once and contains all six IDs, hashes, and complete bodies, and every bound worker spawn event follows it.

If publication cannot be proven, stop `blocked_prompt_publication`. A path, template, summary, truncated body, placeholder, or hash-only disclosure is invalid.

## Dependency Queue

Use this exact order and predecessor closure:

1. `CDM_001`: no generated predecessor.
2. `SRM_001`: `CDM_001`.
3. `COV_001`: `CDM_001`, `SRM_001`.
4. `COV_002`: `CDM_001`, `SRM_001`; it is an independent convergence branch from `COV_001`, dispatched later only because parallelism is forbidden.
5. `COV_003`: `CDM_001`, `SRM_001`, `COV_001`, `COV_002`.
6. `SCL_001`: direct references `CDM_001`, `SRM_001`, and `COV_003`; the latter's transitive closure already binds `COV_001` and `COV_002`.

The prompt text stays frozen after publication. Reference 1 is always the frozen original scene source; up to four later entries are the exact ordered approved direct predecessors. Materialize this plan with `scripts/freeze_reference_bundle.py` into `10_runtime/<asset>/reference-manifest.json` and sibling `references/` bytes using `scene_canon_reference_bundle.v1`. The manifest asset ID, primary source ID, aliases, kinds, order, predecessor IDs, file sizes, hashes, and bundle hash must exactly equal the published prompt plan; the directory must contain no unlisted or nested stale files. Do not dispatch a stage while any predecessor is unapproved or stale.

## Thin Worker Task

Spawn with `fork_turns="none"` and a unique `scene_canon_image_<asset>_<32-hex-nonce>` task name. The task contains:

1. target asset ID and attempt ID;
2. full frozen prompt inline and its SHA-256;
3. ordered absolute reference paths and manifest path;
4. parent thread ID, spawn checkpoint, and run nonce;
5. one instruction: call built-in image generation exactly once with the exact prompt and ordered references, then terminate without text.

The worker cannot inspect, choose, edit, retry, QA, approve, reject, publish, or delegate. A repair uses a new attempt, nonce, worker, and asset revision.

## Runtime Binding

Run the vendored audited v3 `scripts/resolve_worker_image.py` after the worker terminates. It is self-contained and does not runtime-import a sibling Skill. It requires the exact asset ID, accepted-attempt candidate ID, prompt file, asset-scoped ordered reference manifest, parent/worker lineage, spawn checkpoint, run nonce, copy target, and result JSON path.

The resolver must prove:

- one matching fresh worker task;
- exactly one image-generation wrapper call and one image result;
- exact prompt bytes, permitting only the audited single terminal-LF transport normalization;
- exact ordered reference bytes and bundle hash;
- parent/worker/thread/turn/call lineage;
- the returned image path, SHA-256, format, and dimensions.

Do not select the newest image by timestamp. Do not handwrite a successful worker-result receipt. Resolver failure means generation is not bound.

## Main-Agent Inspection

The main agent opens the resolved image, compares it with the source, canon, graph node, predecessors, and edge invariants, and writes a separate inspection receipt. It includes the worker-result hash, image hash, graph node ID, inspector task ID, inspected-at time, all hard QA fields, and `decision: approved` or `rejected`.

Only an approved receipt followed by a zero-error `--mode stage --through-asset <ASSET_ID>` check advances the queue. The stage gate requires the exact contiguous generated prefix and replays all bound prefix evidence; the lighter `--mode state` is schema/state validation only. Rejection records root cause, invalidates descendants, and returns to the earliest affected freeze state.

## Timeouts And Unknown Calls

- If a worker does not submit within 90 seconds, interrupt it and stop `blocked_worker_submit_timeout`.
- If submission occurred but no result returns within 15 minutes, stop `blocked_imagegen_timeout`; do not create another worker while call state is unknown.
- If the runtime cannot spawn workers or expose trace evidence, stop `blocked_worker_runtime` before the first image call.

One explicit invocation must continue through all six stages automatically. Never ask the user to reply “continue” between assets.
