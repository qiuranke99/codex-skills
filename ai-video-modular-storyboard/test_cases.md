# Test Cases

## Positive Coverage

1. **N=1 static shot** — one stable Shot UID, one independently generated frame, one valid review cell.
2. **N=3 short ad** — three frames and three cells in exact Shot Contract order.
3. **N=7 mixed montage** — associative continuity is declared; no literal geography is invented.
4. **N=15 thirty-second ad** — all fifteen frames remain independent even if downstream generation uses fewer API units.
5. **N=17 long board** — deterministic layout has blank terminal slots but exactly seventeen valid cells.
6. **Single-cell replacement** — requested frame version increments, every other file hash remains byte-identical, and the board is rebuilt.
7. **Two-cell atomic replacement** — both staged cells pass and activate in one commit; neither activates on partial failure.
8. **Structure-to-final promotion** — promotion succeeds only when the binary passes all final identity/product/scene/look gates.
9. **Label-heavy source-bound frame** — source-authorized packaging text is legal when every source is an exact downstream-eligible Canon product/packaging/scene authority, dependency, and prompt binding; no OCR or exact-copy claim is inferred.
9. **Model-input stage gate** — `structure_draft` is human/V1-only and false for model input; only validated `look_applied_final` can become eligible.
10. **Legitimate poetic montage** — screen direction and emotional continuity are checked without forcing literal product-use geography.
11. **Independent roots** — storyboard package lives below its own package root while Shot/Look/Canon locators resolve only from the explicit whole-project root.
12. **First-class Look Reference** — State internal reference IDs resolve to nested Look Reference artifact IDs; frame dependencies, prompt sidecars, Canon entries, primary bytes, and owned-record sidecars agree.

## Required Rejections

1. A generator produces a 3x3 board and the workflow crops nine shot files from it.
2. `script_shot_count` differs from frame count or `valid_cell_count`.
3. Two frame records share a `shot_uid`, file, or display order.
4. A review board is marked `is_model_input: true`.
5. A final board lacks an approved Global Look dependency.
6. An applied one-cell transaction changes any unaffected frame hash.
7. A two-cell transaction applies only one requested shot.
8. A reorder is locally applied rather than routed to the Shot Contract owner.
9. An approved artifact has null/incorrect canonical hash or non-null `stale_reason`.
10. A stale artifact is included as current.
11. A frame contains burned-in shot numbers, duration, editorial captions, arrows, grid, UI, watermark, or multi-panel layout.
12. A frame declares intrinsic packaging/product/in-world text but supplies an invented, stale, wrong-category, out-of-scope, or unbound source reference.
13. A fully resealed applied replacement keeps the current root manifest SemVer equal to or below the immutable base manifest.
14. A fully resealed applied replacement changes `source_frame_hashes` while keeping the current review-board SemVer equal to or below the base board.
12. The workflow invokes T2V, first/last-frame video, music, editing, output QC, routing, or orchestration.
13. A model-facing frame uses an internal `reference_id`, a forged reference asset ID, or omits the exact Look Reference artifact dependency.
14. Canon points a frame/board artifact at different primary bytes than its package record, or its `owned_artifacts` sidecar is missing/tampered.

## Automated Contract Suite

Run:

```bash
python3 scripts/test_contract.py
```

The suite builds positive N=1/3/7/15/17 packages plus adversarial count, independence, board-input, hash, transaction, and reorder fixtures.
