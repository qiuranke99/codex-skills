---
name: packaging-product-identity-label-lock-board
description: Use when label-heavy bottles, boxes, pouches, cans, tubes, jars, cartons, bags, or other packaging must become an OCR-first, exact-copy, rotation-ready product asset pack for High-Control AI TVC production. Freeze source truth, derive R8/R12/R16/R24 plus required elevation/detail coverage, generate each master independently through one explicit non-decision worker, apply exact copy deterministically, verify final pixels, and build review boards only from approved masters. Do not use for low-text simple products, prompt-only output, ad posters, scenes, implicit generation, or any workflow that expects a generative model to typeset exact packaging copy.
---

# Packaging Product Identity + Exact-Copy Rotation Asset Pack

## HIGH_CONTROL_RELEASE_GATE_V2

Before any action or production output, resolve this `SKILL.md` directory and execute the sibling OS-native launcher: on Windows, `& ..\\high-control-ai-tvc\\tools\\release-control.ps1 -Action check -Format json`; on macOS/Linux, `../high-control-ai-tvc/tools/release-control.sh check --format json`. The launcher must resolve the pinned runtime from the validated release receipt; never invoke `release_control.py` through an unverified global Python. Proceed only when `ready_latest=true`. On any failure, stop and run the same launcher with `sync`, then start a new Codex task. Bind the returned `release_commit` to this stage; never substitute a mutable Windows/Mac authoring checkout.

Chinese name: 包装产品身份、文案与旋转连续性资产包

`asset_pack_contract_version: whole_product_ocr_rotation_pack_v3`

`runtime_contract_version: delegated_master_worker_transport_v1`

`asset_board_contract_version: delegated_master_worker_prompt_pair_v1`

Create a production reference pack, not one generative collage. One generation unit produces one independent full-frame asset. Review boards are deterministic derivatives of approved masters and never become the sole product truth or the only downstream model input.

The main agent owns applicability, source truth, OCR review, coverage, prompt bytes, worker authorization, inspection, repair, acceptance, exact-copy composition, final QA, Canon export, and the final main result. Exactly one non-decision image worker owns each actual terminal built-in imagegen attempt.

## 1. Read The Required Contract

Before acting, read completely:

- [references/packaging_asset_pack_contract.md](references/packaging_asset_pack_contract.md);
- [references/view_coverage_profiles.json](references/view_coverage_profiles.json);
- [references/generation_unit_prompt_template.md](references/generation_unit_prompt_template.md).

Install the pinned dependency first:

```bash
python -m pip install -r requirements.txt
```

Use the bundled tools instead of rebuilding deterministic mechanics:

```bash
python scripts/run_ocr_preflight.py --help
python scripts/run_region_ocr.py --help
python scripts/compile_generation_prompts.py --help
python scripts/freeze_reference_bundle.py --help
python scripts/resolve_worker_image.py --help
python scripts/build_generation_receipt.py --help
python scripts/compose_exact_copy.py --help
python scripts/run_post_composite_verification.py --help
python scripts/build_continuity_measurements.py --help
python scripts/build_review_boards.py --help
python scripts/validate_packaging_run.py --help
```

Run `scripts/validate_template_contract.py` and `scripts/test_contract.py` after contract edits.

## 2. Pass The Packaging Gate

Require at least one usable target-product image. Classify geometry, copy, code/graphic, material, mechanism, state, and motion risk.

Use this Skill when packaging copy and rotation continuity are primary. Coordinate the material-sensitive owner when transparency, liquid, reflection, refraction, frosting, or layered construction is also high risk. Route mechanisms or dominant state topology to the complex-product workflow. If no visual product source exists, return `blocked_missing_product_reference`.

Freeze one product variant. Do not merge labels, batches, closures, colors, capacities, or package states from conflicting sources.

## 3. Pass The Runtime And Authorization Gate

This Skill requires explicit invocation because a generation attempt uses a delegated worker. An implicit trigger may analyze or report the blocked gate but must return `blocked_worker_authorization` before imagegen.

Record `runtime_capability_snapshot` and require:

- one collaboration worker slot;
- the exact current parent thread ID;
- readable Codex state DB, worker rollout, and generated-image directory;
- materializable, readable, run-scoped reference bytes;
- callable built-in imagegen in the worker;
- readable and executable freezer, resolver, receipt builder, and validators;
- main-agent image inspection and non-empty final-output capacity.

For every built-in attempt record:

```text
built_in_prompt_aspect_ratio_request: "horizontal 16:9"
built_in_prompt_alternate_aspect_ratios_allowed: false
built_in_dimensions_policy: evidence_only_nonblocking
```

Built-in dimensions alone cannot fail content QA, trigger a semantic repair, or block worker-result binding and prompt-pair finalization. Machine-master eligibility remains a separate packaging delivery gate: an accepted raw/final master must decode as exact 16:9 at no less than 1280x720 without post-generation resize used to meet that floor.

If collaboration, parent identity, state/rollout access, reference materialization, prompt equality, or image binding is unavailable, return `blocked_automatic_prompt_pair_runtime`, `blocked_parent_thread_identity`, or the exact `blocked_reference_*` / `blocked_worker_*` code. Never fall back to main-agent imagegen.

## 4. Freeze Source Truth Before Generation

Create one run root under `runs/packaging-product-asset-pack/<run_id>/`. The run manifest and its hash-bound source, OCR, coverage, composition, prompt, master, QA, validation, and optional 4K indexes are durable truth.

Run whole-product OCR before region OCR. Reconcile candidates against authoritative artwork, text masters, direct photographs, decoded codes, and field-level OCR review. OCR output is evidence, not truth.

Keep independent locks for:

```text
geometry_layout_lock
exact_copy_lock
copy_content_lock_status
label_artwork_lock_status
code_payload_lock_status
code_symbol_lock_status
logo_graphic_lock_status
material_lock_status
continuity_lock_status
```

Require `zero-unresolved-difference` for exact text and a successful decode plus `code_decode_match` for every barcode or QR code payload. Require `deterministic_composite` or reproducible comparison evidence for logos and flat art. Generated resemblance is `conditional_unverified` or `not_approved`, never exact-copy proof. A missing required verifier returns `blocked_verification_capability`; it cannot enter an Approved Packaging Asset Registry.

The final post-composite text plus barcode/QR adapter is currently macOS Vision only. On Windows/Linux, or without Darwin + Swift + the bundled Vision script, set `blocked_ocr_capability` before exact-copy prompt compilation unless the user explicitly accepts a non-production geometry-only preview.

## 5. Derive Coverage And Compile Unit Prompts

Derive the minimum legal R profile from the frozen feature and motion evidence. Add high/low/top/bottom, framing bridges, copy, code, structure, and material details only when the contract requires them.

Compile exactly one immutable `final_generation_prompt` per required view with `scripts/compile_generation_prompts.py`. Persist it as `04_prompts/generation_units/<asset_id>_generation_prompt.md`, reopen its UTF-8/LF bytes, verify `generation_prompt_sha256`, and use the prompt index as the run-level SSOT.

Do not generate a contact sheet and crop it into machine references. Do not generate exact text, logos, codes, certifications, batch strings, or dates as pixels that later claim exact-copy authority.

## 6. Execute One Delegated Worker Per Master Attempt

For each view and attempt:

1. Freeze only that unit's ordered unique source references under the run with `scripts/freeze_reference_bundle.py`. Use source IDs as aliases and preserve the coverage order.
2. Record `parent_thread_id`, a complete random 32-lowercase-hex `worker_run_nonce`, `worker_spawn_not_before_ms`, view ID, attempt ID, prompt hash, and reference-manifest hash.
3. Set `terminal_generation_call: worker_pending`, `unit_generation_status: worker_pending`, and `main_result_prompt_pair_status: pending`.
4. Spawn one fresh worker whose task name and canonical agent path end with the full nonce.
5. Give the worker only the exact prompt-sidecar path and ordered frozen paths. It may read those bytes, call built-in imagegen exactly once, and end empty. It may not analyze, rewrite, inspect, repair, select files, approve, publish, or call unrelated tools.
6. After completion, run `scripts/resolve_worker_image.py` with the exact agent path, checkpoint, parent ID, nonce, prompt, reference manifest, state DB, Codex home, attempt destination, and result JSON.
7. Require one matching worker thread/turn/call, exact prompt bytes, exact reference order and bytes, correct event order, empty worker final, and image bytes derived from that thread plus image-call ID.
8. Set `terminal_generation_call: worker_executed` and `unit_generation_status: worker_result_bound` only after resolver success.
9. Inspect the actual bound master. Attempt at most two targeted repairs, each with a fresh worker and nonce. Select exactly one accepted attempt.
10. Promote only the accepted bytes to `05_masters_raw/<family>/<view_id>.png`, then run `scripts/build_generation_receipt.py` to create `packaging-generation-receipt.v2`.

A v1 generation receipt is `legacy_untrusted_generation_provenance`. It cannot make a v3 run COMPLETE, authorize Canon, or grant `label_copy`.

## 7. Build Per-Master Prompt Pairs

After accepting and inspecting one master, freeze its image-specific `final_4k_enhancement_prompt`. Keep generation and 4K prompt bytes separate:

```text
<asset_id>_generation_prompt.md
<asset_id>_4k_enhancement_prompt.md
<asset_id>_4k_handoff.yaml
generation_prompt_sha256
4k_enhancement_prompt_sha256
4k_enhancement_prompt_status: finalized_post_inspection
```

Use unit states:

```text
unit_generation_status: not_started | worker_pending | worker_executed | worker_result_bound | inspected | accepted | rejected
unit_prompt_pair_status: generation_prompt_frozen | 4k_prompt_pending | prompt_pair_ready | prompt_pair_artifact_published
```

The unit-level prompt-pair artifact must contain the complete exact `final_generation_prompt`, complete image-specific `final_4k_enhancement_prompt`, both hashes, and the accepted master ID. Reopen both sidecars, reject any hash mismatch, and never reconstruct either prompt from chat, commentary, summaries, excerpts, or paths.

`prompt_pair_ready` does not imply `external_4k_status: handoff_ready`. External handoff still requires `codex_asset_board` or the accepted master, `original_source_references`, `source_fidelity_status`, `no_generated_exact_copy_claim`, and no `blocked_missing_original_sources`.

Use exact external controls:

```text
aspect_ratio: "16:9"
image_size: "4K"
alternate_aspect_ratios_allowed: false
```

If the provider lacks either control, return `blocked_runtime_controls`. Track `pending_external_generation`, `returned_unverified`, `verified`, or `rejected`; record `observed_pixel_dimensions`, `provider_declared_aspect_ratio_profile`, `observed_file_aspect_ratio`, `aspect_ratio_evidence`, `four_k_evidence`, and `external_4k_qa_status`.

If complete unit prompt publication exceeds one response, return `blocked_final_output_capacity`; do not truncate or abbreviate. The run-level final main result may remain concise by publishing hash-bound prompt indexes and per-master artifact locators instead of concatenating dozens of prompt bodies.

## 8. Compose Exact Copy And Verify Final Pixels

Apply product-native copy, logos, certifications, barcodes, QR codes, batch fields, and dates only through the deterministic composition plan. Bind raw and final byte domains separately.

Run post-composite whole-image/region OCR, barcode/QR decode, graphic comparison, registration QA, material/geometry checks, and continuity measurement. Production authority is validator-derived; a field named approved cannot approve itself.

Every required master must pass assistant QA, exact-copy composition, post verification, and continuity. Keep `assistant_qa_status`, `external_4k_qa_status`, and `production_approval_status: not_granted | user_granted | external_pipeline_granted` independent.

## 9. Build Deterministic Review Boards

Build review boards only from approved masters with `scripts/build_review_boards.py`.

- full-product boards contain at most six masters;
- copy/code/structure/material boards contain at most four evidence cells;
- preserve canonical semantic order across pagination;
- cover each approved master exactly once in QA boards;
- never treat a dense index board as QA authority;
- never feed one crowded board as the sole downstream reference.

Eight canonical complete views plus required detail evidence may be presented as a paginated studio acceptance projection. That projection is not `rich_packaging_board_topology_v2`, not a generated asset, and not the machine source of truth.

## 10. Validate And Publish

Run:

```bash
python scripts/validate_packaging_run.py <run_root>
```

Complete only when the validator exits zero, every required view has one unique accepted worker thread/turn/call and a v2 receipt, OCR/copy/graphics/code/geometry/material/continuity gates pass, deterministic review boards cover the approved masters, and all locked hashes re-read correctly.

The final main result publishes concise Chinese text with the run root, manifest and index hashes, approved/required master count, review-board paths/hashes, lock statuses, coverage status, `assistant_qa_status`, `production_approval_status`, `external_4k_status`, and `task_finalization_status: final_main_result_published`. Set `main_result_prompt_pair_status: published` only when every accepted master has one hash-bound prompt-pair artifact.

## Optional AI-Video Project Canon Export

Canon export cannot upgrade any lock. Use `scripts/export_ai_video_canon.py` only after asset-pack QA passes, prompt and asset indexes re-hash, the selected primary asset decodes, and production approval is explicit.

Use `authority_mode: geometry_layout_only` to authorize only `product_geometry`. Use `geometry_layout_exact_copy_verified` and authorize `label_copy` only when all exact-copy, code, graphic, and post-composite gates pass.

The fixed lifecycle markers are:

```text
authority_stage: terminal_packaging_canon
terminal_route_decision: not_applicable
geometry_layout_only -> [product_geometry]
geometry_layout_exact_copy_verified -> [product_geometry, label_copy]
```

Pillow must be installed from this package's pinned `requirements.txt`. The run manifest and rotation masters remain authoritative even when one primary image is exported.
