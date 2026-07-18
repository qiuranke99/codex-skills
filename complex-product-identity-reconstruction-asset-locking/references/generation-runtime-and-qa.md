# Generation Runtime And Comparison QA

Read this file before preserving or generating a camera asset, generating a diagnostic board, inspecting pixels, or repairing a failure.

## 1. Authority Order

Use this order:

1. frozen original source bytes and direct observations;
2. verified existing 3D/CAD source plus deterministic render provenance;
3. frozen Product Identity Specification, Part Tree, Critical Node Ledger, and View Evidence Matrix;
4. target-specific source IDs, exclusions, and camera plan;
5. accepted generated assets only for cross-comparison or composition support, never as higher identity truth;
6. layout conventions.

A generated image never overwrites contradictory source evidence.

## 2. Reference Transport And Prompt Freeze

Before a built-in image call:

- select the smallest sufficient ordered reference set, normally no more than five;
- prioritize whole-product views and Critical Nodes required by the target;
- record omitted evidence and block if omitted evidence is necessary;
- bind exact source IDs, local paths/content identity when available, source/specification/camera-plan hashes, target camera/board ID, attempt, and prompt hash;
- compose one target-specific prompt and freeze its UTF-8/LF SHA-256.

Store only the prompt hash in the package. The private prompt must state target product identity, target camera or diagnostic topology, visible Critical Nodes, forbidden completion zones, neutral appearance, and negative constraints.

If the returned pixels omit the product, show another subject, or become an educational poster/infographic, classify `reference_transport_or_subject_mismatch`. Do not treat it as ordinary visual drift.

## 3. Camera Asset Lanes

### Source Copy

Copy exact usable source bytes into `02_Geometry_Camera_Coverage/camera_assets/`. Do not re-encode, crop, erase the background, or claim neutralization. The package asset hash must equal the frozen source asset hash.

Source copies are preferred over AI restaging because they retain observed topology. Background/style inconsistency is acceptable in a hard-authority evidence plate and can be addressed downstream without changing its authority.

### Verified Source Render

Use only when an existing 3D/CAD source is verified as the target variant and a compatible renderer is actually available. Freeze model/source hash or equivalent content identity, renderer/version, camera role, render settings, and provenance hash. A render from an unverified model or approximate reconstruction is not hard authority.

When rendering cannot execute, write the exact camera handoff and keep the target blocked. Do not substitute generative unseen views.

### Source-Aligned Generation

Use a built-in image call only for same-camera cleanup/neutralization or a closely source-aligned asset. Attach original evidence for that camera. Keep authority `auxiliary` even after QA because the model may alter topology.

### Bounded Reconstruction

Use for a candidate novel view only when every Critical Node expected to be visible is cross-validated. Explicitly exclude hidden or unknown zones. Keep authority `auxiliary`; it can support creative downstream work but cannot prove geometry or satisfy the hard multi-camera gate.

## 4. Independent Camera Generation

Generate one camera per image call. It is safe to create front/side/rear candidates sequentially when every call binds the same frozen original authority and no generated view becomes the source for the next.

Do not:

- generate all cameras as one collage;
- crop a generative collage into apparent camera assets;
- make a same-angle detail crop count as another camera;
- use a failed or accepted generated camera as the sole source for another camera;
- include multiple products, panels, labels, legends, arrows, measurements, people, props, or scene narrative.

Request one complete uncropped product, neutral seamless background, soft color-controlled light, controlled highlights, subtle ground shadow, and the frozen pose bin.

## 5. Diagnostic Board Generation

Material, Component, State, and Marking assets are separate calls. Give each one job and one bounded layout. Use a complete source-aligned product view when useful, plus only non-redundant evidence-supported details.

Do not let material/detail windows fill space that should have been useful camera coverage. Do not regenerate a whole package sheet and crop it.

## 6. Runtime State Machine

For a generative camera or diagnostic asset:

```text
planned
  -> generation_pending
  -> awaiting_post_generation_continuation
  -> qa_pending
  -> approved
      or repair_required -> generation_pending
      or blocked_generation_quality
      or blocked_generation_semantic_mismatch
```

Persist `generation_pending`, attempt, source/specification/camera-plan hashes, prompt hash, ordered references, and target path before the image call.

After the image call returns, bind the exact file and immediately record observed byte hash and dimensions. Inspect in the same task whenever the host continues. Do not ask the user for a “continue” message just to run QA. If the image call ends the current host turn, persist `awaiting_post_generation_continuation` and resume at the next automatic/user continuation without asking for a new decision.

For `source_copy` and `verified_source_render`, do not fabricate a built-in generation call. Use `terminal_generation_call: not_applicable` unless an actual render tool call is recorded.

## 7. Per-Camera Pixel QA

Inspect at original resolution and compare against the frozen sources.

Require all of these to pass:

- `subject_match`: the target product/variant is present; no unrelated poster, infographic, geometric-shape chart, butterfly, or wrong product;
- `complete_product`: one entire product, uncropped and unobstructed;
- `pose_match`: asset matches the declared azimuth/elevation/shot-size bin and has unique coverage value;
- `critical_node_consistency`: every visible node matches count, relationship, side, and attachment evidence;
- `cross_camera_consistency`: overlapping nodes, silhouette landmarks, materials, and immutable features agree with every accepted camera;
- `text_pollution`: no non-product titles, labels, arrows, legends, measurements, watermarks, UI, or invented copy.

Record exact failure flags such as:

- `subject_absent`, `wrong_subject`, `wrong_variant`, `infographic_semantics`;
- `added_part`, `missing_part`, `duplicated_part`, `fused_structure`;
- `spoke_count_drift`, `wheel_axle_handrim_drift`, `caster_fork_drift`;
- `frame_crossbrace_drift`, `seat_support_drift`, `control_side_swap`;
- `topology_drift`, `proportion_drift`, `material_drift`, `marking_drift`;
- `unsupported_state`, `deformation`, `collision`;
- `crop`, `overlap`, `duplicate_asset`, `duplicate_pose_bin`, `text_pollution`.

An attractive render fails when its Critical Node fingerprint differs from the source.

## 8. Cross-Camera Coverage QA

Recompute from accepted files, not self-attestation:

- observed SHA-256 and actual dimensions;
- unique file hashes;
- unique azimuth/elevation/shot-size tuples;
- front/rear/left/right/side/high/low sector coverage;
- hard-authority camera count;
- overlapping Critical Node agreement;
- exact blocked-camera requests.

Multiple crops or scales of the same source camera remain one pose. A contact sheet cannot create coverage. Any contact sheet must be derived after approval, list its camera IDs, and have `identity_authority: none`.

## 9. Diagnostic QA

Require geometry, material, identity, subject, and text-pollution checks. Compare every detail with its cited source and adjacent parts. For states, inspect endpoint topology and part travel. For markings, inspect placement and claimed exactness.

Diagnostic approval never increases camera count.

## 10. Causal Repair

Use the smallest causal change:

1. identify the exact camera/board, Critical Node, and failure flag;
2. classify transport mismatch, topology overload, evidence gap, camera redundancy, or local drift;
3. reuse frozen original sources and authority;
4. change representation, reference selection, target pose, or one relevant constraint;
5. never use the failed image as identity authority;
6. rerun full target QA and affected cross-camera checks.

Stop immediately on semantic subject mismatch until reference/prompt binding is audited. Do not spend two retries adding prompt adjectives.

Limit a camera to two total attempts and a diagnostic board to the original plus two repairs. Preserve rejected attempts and lineage. After the limit, mark `blocked_generation_quality` and continue truthfully with the accepted remainder.

## 11. Primary Upload Selection

Choose one to five approved assets. Prioritize non-redundant hard-authority cameras that expose complementary sectors and Critical Nodes. Add a diagnostic board only when it closes a specific downstream risk.

Write a selection reason per asset and one overall rationale. A complete package selects at least two independent cameras. Do not create a new generative final collage; the selected original assets are the upload authority.
