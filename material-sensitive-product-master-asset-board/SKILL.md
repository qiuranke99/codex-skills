---
name: material-sensitive-product-master-asset-board
description: "Use only when explicitly invoked with local references for one transparent, glass, acrylic, translucent, liquid, cream, gel, crystal-cut, mirror-metal, high-reflective, frosted, or multi-layer product whose video continuity is dominated by material behavior. Freeze source authority and identity/material/structure invariants, create exactly one text-free 16:9 master board through one non-decision image worker per attempt, compare the bound PNG directly with its frozen sources, and deterministically publish the complete generation plus image-specific 4K prompt pair. Do not use for low-risk six-view products, exact-copy packaging, mechanisms, scenes, characters, posters, or prompt-only work."
---

# Material-Sensitive Product Master Asset Board

Chinese name: 特殊材质产品总资产板

`asset_board_contract_version: delegated_image_worker_prompt_pair_v5`

Generate exactly one high-density, low-redundancy material master board. Product identity, material physics, and source evidence outrank visual showmanship. A prompt, a moodboard, several independent sheets, or an image without post-generation inspection is not the deliverable.

## Standalone Runtime Boundary

Run from this package. Resolve every script, reference, and requirement relative to this `SKILL.md`. Core routing, source freezing, prompt compilation, worker binding, content QA, and publication must not probe, synchronize, import, or require a neighboring Skill or external release manager.

Use a Python 3.11 or 3.12 executable that can import Pillow. If the active environment lacks Pillow, install this package's `requirements.txt` before the production run. A missing decoder returns `blocked_material_decoder_unavailable`; never replace full image decoding with extension or header guessing.

The main agent owns applicability, source interpretation, prompt bytes, visual inspection, repair, acceptance, production approval, and final publication. One fresh non-decision image worker owns each terminal built-in imagegen call. Implicit routing does not authorize a worker.

## 1. Applicability And Source Gate

Require an explicit invocation and at least one readable local reference for one product variant. Record five risks:

- `identity_risk`: silhouette, proportions, component order, inner/outer relationship, deformable global form;
- `material_risk`: transparency, refraction, reflection, frosting, fill boundary, viscosity, crystal facets, finish transitions, or mixed material response;
- `structure_risk`: seam, neck, cap, pump, tube, liner, hinge, latch, base, connector, link topology, rim, edge thickness, or small identity mark;
- `label_risk`: logo, name, capacity, key copy, embossing, foil, and placement;
- `state_risk`: open/closed, cap on/off, exposed content, split component, use state, or transition.

Use this Skill only when material behavior is the dominant video-continuity risk. Route a simple opaque low-risk product to a low-risk multi-angle workflow; exact readable copy to a packaging workflow; mechanical/state topology to a complex-product workflow; and scenes, characters, posters, lifestyle images, source research, simple upscale, or prompt-only requests elsewhere.

If material and exact-copy risks are both high, the main agent must establish two independent evidence authorities and an external compound handoff. This Skill never grants exact-copy authority. Missing local source bytes returns `blocked_reference_materialization`; unresolved product variants return `blocked_product_variant_conflict`.

## 2. Freeze Source Truth And The Board Contract

Use an active project output directory when one exists; otherwise use `outputs/material-locks/<asset_id>/`. The run layout is:

```text
<run>/
  sources/reference-manifest.json
  sources/references/<ordered canonical images>
  sources/material-source-contract.json
  sources/material-prompt-block.md
  attempts/01/<asset_id>_01_generation_prompt.md
  attempts/01/worker_exec.js
  attempts/01/worker_exec.json
  attempts/01/worker_spawn.json
  attempts/01/worker_result.json
  attempts/01/board.png
  attempts/01/qa_decision.json
  attempts/01/qa.json
  attempts/01/<asset_id>_01_4k_enhancement_prompt.md
  attempts/01/<asset_id>_01_4k_handoff.json
  attempts/02/...
  attempts/03/...
  accepted_attempt.json
  <asset_id>_final_main_result.md
```

Freeze every unique authoritative image in semantic order:

```text
<python> scripts/freeze_reference_bundle.py
  --run-dir <run>
  --manifest <run>/sources/reference-manifest.json
  --reference <alias>=<local-image-path> [...]
```

`material_reference_bundle.v2` must contain one-based order, unique aliases, run-contained canonical paths, full byte hashes, actual decoder-reported format/MIME/dimensions, and one ordered-bundle hash. The freezer fully decodes every image, chooses the suffix from detected media rather than the supplied extension, rejects symlink escapes, and is create-only or byte-identical idempotent.

Create a draft `material_source_contract_draft.v1`, then freeze it with `scripts/freeze_material_source_contract.py`. The frozen `material_source_contract.v1` must bind:

- every alias to source authority, allowed uses, and excluded content;
- each relevant fact as `verified`, `inferred`, or `needs_source` with supporting aliases;
- every identity-, material-, topology-, structure-, label-, or state-critical invariant with its source aliases and required repair action;
- one 7-10 panel plan whose panels cite their allowed sources and invariants.

The panel plan contains exactly one largest primary anchor, 3-4 complementary spatial views, at least one material-response view, critical structure where required, at most one optional label reference, and at most one state window whose exact state is source-supported. No planned panel may require excluded or `needs_source` content.

The freezer also creates `material-prompt-block.md`. That exact UTF-8/LF block and its hash are derived from the frozen semantic contract. It must appear once, byte-for-byte, in every attempt's generation prompt; hand-written restatement is not evidence.

Request one text-free horizontal 16:9 board on white or light neutral gray with restrained studio shadows. No title, heading, label, view name, number, arrow, legend, measurement, caption, prompt text, UI, watermark, added logo, person, hand, prop, scenery, packaging, card, border, grid, or blank panel. Returned built-in dimensions are evidence only: a source-faithful `1672x941`, `1536x1024`, or other raster is not repaired merely for being non-exact 16:9.

## 3. Freeze And Disclose The Generation Attempt

Before spawn, write one complete public English generation prompt to the attempt directory as UTF-8/LF without BOM. Reopen it, require exact bytes, hash it, and verify the frozen material prompt block occurs exactly once. Keep the final 4K prompt unset until actual-board inspection.

Publish the complete generation prompt, its SHA-256, material-source-contract SHA-256, and ordered reference aliases before creating the worker. A path, excerpt, summary, or hash alone does not satisfy prompt disclosure.

Generate one random 32-character lowercase hexadecimal nonce, then render the only legal worker exec:

```text
<python> scripts/render_worker_exec.py
  --run-dir <run>
  --attempt-dir <run>/attempts/<attempt_id>
  --worker-run-nonce <32hex>
  --expected-prompt <generation-prompt>
  --reference-manifest <run>/sources/reference-manifest.json
  --source-contract <run>/sources/material-source-contract.json
  --exec-source <attempt>/worker_exec.js
  --exec-receipt <attempt>/worker_exec.json
```

The renderer emits one deterministic source file: exact nonce declaration, one literal imagegen argument object containing the frozen prompt and ordered frozen paths, and one `generatedImage(result)`. Comments, dynamic property access, variables, concatenation, template literals, wrapper text, second calls, and alternate reference modes are invalid.

Capture the exact current parent thread and a millisecond checkpoint immediately before `spawn_agent`. Create one fresh `fork_turns="none"` worker. After the tool returns its canonical agent path, freeze `material_worker_spawn.v2` with `scripts/freeze_worker_spawn.py`, binding agent path, parent, checkpoint, nonce, prompt, manifest, source contract, exec source, and exec receipt hashes. Existing non-identical artifacts are never overwritten.

## 4. Execute And Bind One Non-Decision Worker

The worker receives only the frozen exec source and ordered run-scoped references. It submits that exact source once, waits only on the yielded imagegen cell if necessary, makes no other tool call, and ends with empty final records. It cannot decide applicability, facts, panel composition, QA, repair, acceptance, approval, or publication.

The main agent remains active, waits for the worker, and resolves the result:

```text
<python> scripts/resolve_worker_image.py
  --worker-spawn <attempt>/worker_spawn.json
  --copy-to <attempt>/board.png
  --result-json <attempt>/worker_result.json
```

The v4 resolver must prove the complete worker rollout contains exactly one task/turn, exact parent and worker lineage, one exec whose full UTF-8 source bytes equal `worker_exec.js`, one completed image event, only cell-bound waits, empty final records, and no unknown call-shaped event. It must derive the PNG only from worker thread ID plus image call ID, fully verify and load it with Pillow, require a different hash from every source image, copy it create-only, and write `delegated_product_image_worker_result.v2` create-only.

Do not select a newest file, parse a decoy literal, accept recent-conversation images, accept direct original paths, continue a v1 run, or regenerate merely because provenance binding failed. Legacy artifacts return `blocked_legacy_material_run_v1`; ambiguity or mismatch returns the exact `blocked_worker_*` or `blocked_reference_*` code.

## 5. Inspect Content Against Source Invariants

Open the copied `board.png` and every frozen source image with the image-inspection tool at original detail. Do not judge from chat thumbnails or memory. Create the editable source-bound decision scaffold:

```text
<python> scripts/scaffold_board_inspection.py
  --run-dir <run>
  --attempt-dir <attempt>
  --reference-manifest <run>/sources/reference-manifest.json
  --source-contract <run>/sources/material-source-contract.json
  --decision-draft <attempt>/qa_decision.json
```

For every planned panel and critical invariant, preserve the scaffolded source aliases and record two separate one-line observations: what the cited frozen sources show and what the board shows. `pending`, an empty board observation, copied source/board prose, reordered evidence, or an uncited source cannot freeze. Complete the gates, defects, repair state, assistant QA, and production approval, then run:

```text
<python> scripts/freeze_board_inspection.py
  --run-dir <run>
  --attempt-dir <attempt>
  --board <attempt>/board.png
  --worker-result <attempt>/worker_result.json
  --reference-manifest <run>/sources/reference-manifest.json
  --source-contract <run>/sources/material-source-contract.json
  --decision-draft <attempt>/qa_decision.json
  --inspection <attempt>/qa.json
```

The freezer emits create-only/idempotent `material_board_qa.v3`. It derives rather than accepts the board hash/dimensions, worker thread/call, source image list, decision path/hash, and inspection method. The decision owns only visual judgments:

- a complete `board_gates` object for primary anchor, complementary angles, material evidence, source consistency, critical structure, low redundancy, panel legibility, single-board topology, no-poster pollution, state support, prompt binding, and video-reference readiness;
- one `panel_results` entry for every planned panel and no others, citing the matching panel ID and source aliases, then recording distinct `source_observation` and `board_observation` fields plus the pass/fail result;
- one `invariant_results` entry for every frozen critical invariant and no others, citing the invariant ID and source aliases, then recording distinct `source_observation` and `board_observation` fields plus the pass/fail result;
- structured observed defects with exact `category`, `severity`, affected `panel_ids`, affected `invariant_ids`, `source_aliases`, `cleanup_eligible`, and `cleanup_operation` fields. Cleanup is legal only for `category: artifact`, `severity: low | medium`, an empty `invariant_ids` list, and one of `reduce_raster_aliasing`, `remove_compression_blocking`, `remove_background_dust`, or `reduce_edge_halo`; every other defect uses `cleanup_eligible: false` and `cleanup_operation: none`;
- separate `assistant_qa_status` and `production_approval_status`.

Acceptance requires every board gate, planned panel, and critical invariant to pass. Cross-panel changes to product identity, component order, chain/link rhythm, connector topology, edge thickness, fill boundary, label identity, or source-supported state are failures even when one panel looks plausible. `assistant_qa_status: conditional` is evidence, not acceptance.

Identity, topology, structure, material-state, label-identity, or source-consistency defects require a new generation attempt or missing-source request. They are never delegated to a 4K cleanup prompt. Allow at most two focused repairs after attempt 01; every attempt has fresh immutable prompt, exec, spawn, result, PNG, and QA artifacts. If attempt 03 fails, stop with the exact missing/contradictory evidence.

## 6. Create The Image-Specific 4K Handoff

Only after `material_board_qa.v3` is frozen and passed, compile the complete post-generation record chain:

```text
<python> scripts/freeze_post_generation_records.py
  --run-dir <run>
  --attempt-dir <attempt>
  --board <attempt>/board.png
  --generation-prompt <attempt>/<asset>_<attempt_id>_generation_prompt.md
  --worker-spawn <attempt>/worker_spawn.json
  --worker-result <attempt>/worker_result.json
  --inspection-decision <attempt>/qa_decision.json
  --inspection <attempt>/qa.json
  --reference-manifest <run>/sources/reference-manifest.json
  --source-contract <run>/sources/material-source-contract.json
  --enhancement-prompt <attempt>/<asset>_<attempt_id>_4k_enhancement_prompt.md
  --handoff <attempt>/<asset>_<attempt_id>_4k_handoff.json
  --accepted-attempt <run>/accepted_attempt.json
  --external-4k-status <status>
  --external-4k-qa-status <status>
  --external-4k-production-approval-status <status>
```

This package-local compiler re-audits the worker rollout and saved PNG, re-renders QA from `qa_decision.json`, and preflights every destination before its first write. It freezes the deterministic 4K prompt, `material_4k_handoff.v3`, and `material_accepted_attempt.v3`; `accepted_attempt.json` is written last as the commit marker. A same-byte rerun is idempotent. A conflicting enhancement, handoff, or accepted artifact writes no accepted commit.

The compiler binds the accepted board plus every frozen original reference, preserves panel topology and every invariant, and names only the exact cleanup operations authorized by QA. Free prose is not an authority surface. The final builder independently re-renders the QA, 4K prompt, handoff, and accepted bytes; updated hashes cannot legalize a prompt or record that invents or repairs identity, topology, structure, fill, label, state, facets, highlights, or material microdetail.

Request only `aspect_ratio: "16:9"` and `image_size: "4K"`, with no alternate ratio, crop, stretch, reframing, panel reorder, added panel, advertising treatment, or non-product-native text. The v3 handoff directly binds the generation prompt, QA decision, frozen QA, accepted board, all original references, deterministic enhancement prompt, requested controls, source-fidelity status, actual `external_4k_status`, `external_4k_qa_status`, and `external_4k_production_approval_status`.

The only legal external status matrix is: `not_ready`, `handoff_ready`, or `blocked_runtime_controls` with `not_started + not_requested`; `pending_external_generation` or `returned_unverified` with `pending + not_requested`; `verified` with `passed + (pending | granted)`; or `rejected` with `failed + rejected`. Prompt-pair readiness does not imply external readiness, verification, or approval.

## 7. Freeze One Accepted Attempt And Publish

Do not hand-write QA, handoff, or accepted records. The post-generation compiler creates exactly one root `accepted_attempt.json` with schema `material_accepted_attempt.v3`. It directly binds absolute paths and hashes for the reference manifest, source contract, prompt block, `worker_exec_source_path`/`worker_exec_source_sha256`, `worker_exec_receipt_path`/`worker_exec_receipt_sha256`, worker spawn/result, board, QA decision, frozen QA, both prompt files, and handoff. Failed attempts remain immutable and cannot be selected.

Run the package-local final builder with the exact accepted chain:

```text
<python> scripts/build_final_result.py
  --run-dir <run>
  --accepted-attempt <run>/accepted_attempt.json
  --board <attempt>/board.png
  --generation-prompt <attempt>/<asset>_<attempt_id>_generation_prompt.md
  --enhancement-prompt <attempt>/<asset>_<attempt_id>_4k_enhancement_prompt.md
  --worker-spawn <attempt>/worker_spawn.json
  --worker-result <attempt>/worker_result.json
  --inspection-decision <attempt>/qa_decision.json
  --inspection <attempt>/qa.json
  --reference-manifest <run>/sources/reference-manifest.json
  --source-contract <run>/sources/material-source-contract.json
  --handoff <attempt>/<asset>_<attempt_id>_4k_handoff.json
  --output <run>/<asset>_final_main_result.md
```

The builder independently rehashes and revalidates every artifact, fully decodes the board, re-audits the worker rollout, and byte-compares the decision-rendered QA, 4K prompt, handoff, and accepted commit. It enforces complete panel/invariant comparisons and external-state matrices, rejects repair-only defects, and publishes the handoff's actual external status rather than inventing readiness. v1/v2 accepted records cannot resume as v5.

Reopen `<asset_id>_final_main_result.md` and emit its exact complete contents as one non-empty `final` response. It must contain:

```text
![Material-Sensitive Product Master Asset Board](<absolute accepted board path>)

final_generation_prompt:
<complete exact generation sidecar>
generation_prompt_sha256: <verified sha256>

final_4k_enhancement_prompt:
<complete exact image-specific 4K sidecar>
4k_enhancement_prompt_sha256: <verified sha256>

assistant_qa_status: passed
external_4k_status: <actual handoff state>
production_approval_status: <actual approval state>
main_result_prompt_pair_status: published
task_finalization_status: final_main_result_published
```

Also include observed dimensions and worker thread/call binding. If one response cannot hold both full prompt bodies, return `blocked_final_output_capacity`; never truncate, split, reconstruct, or claim publication. No tool call or state mutation follows the final response.

## 8. Completion And Failure Conditions

Complete only when frozen source bytes, source semantics, prompt block, generation prompt, deterministic exec, worker lineage, fully decoded PNG, direct source-to-board visual comparison, decision-rendered per-panel/invariant QA, compiler-created accepted record, image-specific handoff, artifact-backed payload, and displayed final response form one hash-bound chain.

Failure includes an implicit worker, missing local source, sibling dependency, main-agent imagegen, hand-written source restatement, prompt wrapper, parser decoy, multiple worker tasks, unknown tool call, corrupt image, source/board hash collision, newest-file selection, uninspected source or board, copied/empty source-to-board observation, hand-written QA/handoff/accepted record, topology false positive, 4K repair of identity/structure, overwritten artifact, legacy resume, empty final, or incomplete prompt pair.

Production approval remains `not_granted`, `user_granted`, or `external_pipeline_granted` and is never inferred from QA, imagegen success, handoff readiness, or external verification.

For maintained executable and historical fixtures, read [test_cases.md](test_cases.md).
