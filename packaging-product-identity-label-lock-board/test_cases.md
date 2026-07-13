# Packaging Asset Pack v3 Contract Cases

The executable acceptance suite is `python3 -B scripts/test_contract.py`.
These cases define the expected semantics.

## Delegated per-master worker transport

1. One explicit invocation freezes one unit prompt and ordered source bundle, then one fresh nonce-suffixed worker makes one image call.
   - Pass only when the resolver binds the exact parent/thread/turn/call, prompt bytes, reference bytes, and raw PNG.
2. A main agent calls imagegen, or an implicit trigger tries to spawn a worker.
   - Fail before generation with `blocked_worker_authorization` or `blocked_automatic_prompt_pair_runtime`.
3. A v1 generation receipt is attached to a v3 COMPLETE run.
   - Fail; v1 is `legacy_untrusted_generation_provenance`.
4. Two accepted views reuse one worker thread, turn, or image-call ID.
   - Fail; every master requires a unique provenance chain.
5. The worker tool-event prompt differs by one byte, references are reordered or mutated, or newest-file selection is attempted.
   - Fail the exact resolver/receipt binding.
6. The worker result matches the prompt but its raw image hash, canonical view path, dimensions, or reference-manifest hash differs.
   - Fail before composition and Canon export.

## OCR-first hard gates

1. Every source image has a full-image OCR discovery pass before any region OCR.
   - Pass only when source IDs exactly match the source manifest.
2. A source has region OCR but no whole-product pass.
   - Fail before prompt compilation.
3. OCR is unavailable or lacks the required Chinese/English language support.
   - Expect `blocked_ocr_capability` or `blocked_required_language_support`.
   - For exact-copy mode, forbid geometry generation or silent downgrade.
4. OCR candidates differ on one letter, digit, punctuation mark, unit, or case.
   - Expect `COPY_REVIEW_REQUIRED`; generation remains forbidden.
5. `all_visible_product_native_copy` contains a `C_texture` field.
   - Fail. Every visible product-native character must be `A_exact`.
6. OCR changes the printed phrase to a grammatically improved version.
   - Fail. Autocorrect and paraphrase are forbidden.
7. OCR arrays are emptied, counts are changed to zero, review remains pending,
   and Text SSOT cites nonexistent source/observation IDs.
   - Fail all source/OCR/region/SSOT cross-links before generation.
8. Surface inventory is empty but top-level gates claim pass.
   - Fail; required surfaces and detected field/code/graphic sets are derived
     from non-empty, source-bound inventory records.
9. A whole-product OCR detection is omitted from Text SSOT or has no reviewed
   disposition while its surface claims `verified_no_copy`.
   - Fail OCR/inventory reconciliation.
10. A region crop is replaced by a black or unrelated image and every visible
    hash is coordinated.
    - Fail installed-rectifier/source-geometry pixel replay.
11. A `text` or `mixed` region has a replayable crop receipt but zero region
    text detections.
    - Fail. Crop provenance does not satisfy the Text exact-copy gate.
12. A `code`-only or `graphic`-only region has zero text detections.
    - The v2 crop provenance may pass, but production remains blocked until a
      reciprocally mapped decode/graphic disposition and named reviewer pass.
13. `surface_id`, `physical_layer_id`, `visibility_mode`, or
    `region_purpose` differs between the v2 spec, ledger pass, region
    observation, or v2 adapter receipt.
    - Fail even when the attacker recomputes receipt and ledger hashes.

## Transparent-package text layers

1. Rear copy visible through the front is recorded as `mirrored_showthrough`
   and points to the direct rear region.
   - Pass when it remains one rear field.
2. Show-through text is duplicated as direct front copy.
   - Fail `blocked_unresolved_showthrough`.
3. A pump tube or refraction hides characters and the system completes them by
   language inference.
   - Fail `blocked_unreadable_required_copy`.

## Codes and graphics

1. Required barcode/QR payload and symbology decode and match.
   - Pass the payload gate; printed-symbol identity remains independent.
2. Code looks plausible but cannot decode, or checksum/payload differs.
   - Fail; exact copy cannot be approved.
3. QR payload matches but the printed module matrix differs from the approved
   symbol.
   - Payload may pass; symbol lock fails.
4. Logo or certification mark has no master or approved crop/hash.
   - Fail the graphic-binding gate; OCR resemblance is insufficient.
5. A code-only crop has no decoded observation disposition or named reviewer.
   - Fail code authority even when the crop itself replays pixel-for-pixel.
6. A graphic-only crop has no `mapped_to_graphic` disposition or named
   reviewer.
   - Fail graphic authority even when asset path/hash and crop receipt match.

## Rotation and elevation coverage

1. R16 contains all 16 neutral views at 22.5-degree spacing with a closed
   337.5-to-0 edge.
   - Pass only when numeric poses and previous/next IDs agree.
2. Any required side, front/rear three-quarter, high, low, top, bottom, or
   conditional detail view is missing or duplicated.
   - Fail coverage.
3. A generated side marks itself `source_verified`.
   - Fail; generated assets cannot self-upgrade authority.
4. Any required view has `needs_source` in pose, surface, copy, or material.
   - Expect `blocked_missing_source`; required production coverage cannot pass.
5. Four high-angle anchors are supplied for a continuous high-angle 360 orbit.
   - Fail; select a complete high-elevation R12/R16/R24 ring.
6. High three-quarter view is used as true-top evidence or low view as true
   bottom.
   - Fail role coverage.
7. A complete high-angle R8/R12/R16/R24 ring is declared in the motion envelope.
   - Pass when the dynamic view set, numeric poses, adjacency, composition plan,
     edge QA, and loop closure all match the selected profile.
8. Every view claims `source_verified` from `NO_SUCH_SOURCE`.
     - Fail source membership and visible-surface evidence checks.
9. Every azimuth, high/low view, top, bottom, and detail row claims only the
   front surface and front source.
   - Fail canonical camera-to-surface topology.
10. A generated intermediate view has zero parents, non-source parents, or
    first exposes a new surface/field/code/graphic.
    - Fail derived production authority.
11. An unknown misspelled feature silently lowers R16 risk to R8, or two HIGH
    rings collapse onto the same IDs.
    - Fail feature enum/ring-prefix collision gates.
12. `DETAIL_CLOSURE_TOP`, `DETAIL_TRUE_BOTTOM`, or another fixed detail uses a
    pose, shot scale, target surface, family, framing, focus, or board role that
    differs from its frozen profile spec.
    - Fail fixed-detail semantic parity before prompt compilation.
13. Any one of the four upper-half or four lower-half bridge masters is absent.
    - Fail required coverage; all eight are mandatory.
14. Two physical OCR/Text/Code/Graphic regions are collapsed into one dynamic
    detail, or one region-derived detail is missing.
    - Fail exact region-to-detail one-to-one derivation.
15. A dynamic region detail declares adequate resolution but its decoded final
    master and projected region bbox scale below the 4K-equivalent region,
    text-line, code, or graphic threshold.
    - Fail final-pixel readability authority.
16. `pitched_full_rotation` declares a high/low full-spin scope with no matching
    complete profile ring, or bounded motion supplies an unauthorized full ring.
    - Fail canonical motion type/scope/ring derivation.

## Continuity

1. Pump/nozzle screen direction is identical in front and back rather than
   remaining fixed in product coordinates.
   - Fail `nozzle_frame_binding_gate`.
2. Width/depth, shoulders, base, label surface, liquid level, internal tube,
   embossing, material response, camera distance, or object occupancy drifts.
   - Fail the matching continuity gate.
3. The final ring view does not close onto the 0-degree anchor.
   - Fail `loop_closure_gate`.
4. Continuity evidence is v1, names a synthetic method, has empty/manual
   metrics, forges the bundled tool hash, or changes a metric while recomputing
   only the receipt self-hash.
   - Fail v2 installed-builder replay.
5. V2 has no hash-bound semantic landmark/mask annotations, an annotation byte
   changes, or one gate/edge remains blocked.
   - COMPLETE remains forbidden.

## Independent masters and boards

1. Each view is an independently generated full-frame asset with a frozen
   prompt and later inspection.
   - Pass when every required asset has a one-to-one prompt and QA record.
2. A generated contact sheet is cropped into machine masters.
   - Fail. `derived_from_multipanel` must be false.
3. A board exceeds six full-product cells or four detail cells at 4K 16:9.
   - Split into additional boards; shrinking evidence is forbidden.
4. A review board is used as the sole downstream generation reference.
   - Fail the board-derivation/downstream-selection contract.
5. Every required view points to one reused master file/hash.
   - Fail unique path/hash, generation receipt, prompt binding, and post-result
     membership checks.
6. Every prompt file contains only `x` but is rehashed.
   - Fail dependency-bound prompt content validation.
7. A board path is missing, hash-forged, over capacity, or omits/repeats masters.
   - Fail deterministic board file/input/capacity coverage.
8. Official board-builder output is fed back into `asset_qa`.
   - Pass only with run-relative `file_path`, `file_sha256`, `asset_id` on every
     input, one semantic role, canonical ordered view IDs, exact 4K 16:9, and
     full one-time master coverage.
9. A neutral-ring board swaps adjacent azimuths, or one board mixes elevation,
   copy, code, structure, material, or framing-bridge assets.
   - Fail semantic role and ordered-sequence validation even when hashes and
     capacity are otherwise valid.

## Exact-copy composition and final QA

1. The raw generated base contains model pseudo-copy in protected regions.
   - Fail `generated_text_pollution_status` unless a deterministic mask proves
     complete pixel replacement.
2. A required view lacks a supported deterministic projection.
   - Fail `blocked_no_deterministic_projection`; do not ask the model to redraw.
3. Deterministic composition completes, then whole-product and region OCR match
   with zero unresolved differences; codes decode; graphics and registration
   pass.
   - Exact copy may be approved.
4. Any post-composite character, payload, symbol, logo, surface registration,
   or layer differs.
   - Fail exact-copy approval.
5. Any source, SSOT, bundle, coverage, prompt, asset, or QA byte/hash changes.
   - Invalidate dependent prompts/assets and fail integrity.
6. Generation receipt binds final bytes rather than unique raw bytes, raw and
   final are identical on a protected-copy view, job lacks base/layers/self
   hash, or plan chooses a projection unsupported by the bundled compositor.
   - Fail raw/final separation and compositor replay.
7. Final OCR contains one extra unknown/garbled product-native observation in
   addition to every expected field.
   - Fail exact-set post OCR reconciliation; no extra pseudo-copy is tolerated.
8. A prompt contains only hashes and a view token but omits numeric pose,
   lens/distance, surfaces, sources, neighbors, parents, protected regions,
   composition plan, or geometry/material locks.
   - Fail deterministic prompt compilation/content validation.

## Legacy and Canon

1. A v2 one-board run is imported.
   - Classify only as `legacy_geometry_layout_only`; never auto-upgrade it to
     rotation-ready or `label_copy` authority.
2. Packaging Canon export requests
   `geometry_layout_exact_copy_verified` without a locked exact-copy evidence
   manifest.
   - Reject and leave Canon unchanged.
3. Geometry-only export remains legal after the selected primary asset and
   ordinary prompt/approval evidence pass.
4. A v1 exact-copy sidecar, arbitrary PNG, review board, or empty status-only
   bundle/coverage/post package requests `label_copy`.
   - Reject before Canon mutation.
5. A v2 sidecar locks one COMPLETE run but its validator, bundle, prompt,
   asset-QA, continuity-QA, post-verification, primary member, or primary
   post-result bytes drift.
   - Live revalidation fails before Canon mutation.
6. `build_exact_copy_canon_evidence.py` selects a unique approved master from a
   production-approved COMPLETE all-visible run.
   - Pass, then the shared bridge re-runs the target validator and verifies the
     same primary path/bytes before authorizing `label_copy`.
