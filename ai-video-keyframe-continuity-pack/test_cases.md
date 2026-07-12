# Contract Test Cases

The package is valid only when the expected behavior—not merely attractive imagery—passes.

## 1. One Anchor Per Scripted Shot

Input: a 15-shot Shot Contract and 15 independent storyboard frames.
Expect: 15 unique shot records, each with at least one approved keyframe.
Fail: 14 records, duplicate `shot_uid`, a prompt-only placeholder, or a grid crop.

## 2. Validated Storyboard Promotion

Input: S004 final storyboard already has source-faithful identity/product/scene/look, correct pose/time state, actual dimensions, binary hash, and later visual QA.
Expect: `anchor_route: validated_storyboard_promotion`, `terminal_generation_call: not_applicable_promoted`, and non-empty promotion evidence.
Fail: promotion by filename rename, contact-sheet crop, missing QA, or stale source.

For label-heavy packaging or in-world signage, promotion remains legal only when Storyboard annotation controls pass and every intrinsic-text source is an exact downstream-eligible Canon product/packaging/scene authority retained in the Keyframe `required_authority_artifact_ids`. Provenance does not imply OCR or exact-copy verification. Fail if the source is invented, missing, stale, wrong-category, out of scope, or dropped during promotion.

## 3. Omni Reference, Never Endpoint Or Standalone I2V Mode

Input: a shot with two state anchors.
Expect: both use `usage_mode: omni_reference_anchor`; the roles describe action/material state; ordinary storyboard, keyframe, Look, character, product, and scene images remain legal references inside Omni R2V; the manifest carries `standalone_single_image_to_video` in its denylist.
Fail: `first_frame`, `last_frame`, `start_frame`, `end_frame`, interpolation, T2V, standalone/classic single-image-to-video, or removal of the required deny marker anywhere in the package.

## 4. Poetic Bath-Oil Montage

Input: sensorial shot of oil on palm/skin without literal usage instructions.
Expect: conservative viscosity, highlight, droplet, wetting, pose, and emotion execution inferred; no question about an unstated product-use condition; no invented efficacy claim, usage instruction, or hidden mechanism structure.

## 5. Material State Trajectory

Input: transparent bottle and one amber oil drop moving from dropper to palm.
Expect: source-supported fill level, meniscus, drop/stream topology, viscosity class, refraction edges, wetting footprint, and settled state tied to V1 time anchors.
Fail: invented dip tube, changing fill level without cause, water-like motion for viscous oil, or conflicting highlight direction.

## 6. V1 Timing Requirement

Input: 15-second multi-shot sequence.
Expect: `timing_source.mode: v1_timing_animatic` and dynamic ladder anchors tied to its timecodes.
Fail: `single_static_shot_exemption`.

Input: one static packshot with no material motion.
Expect: explicit single-static-shot exemption is allowed.

## 7. Acyclic K1/P1/K2 Handshake

Input: approved V1 plus static authorities, before Prompt preflight.
Expect: K1 owns per-shot anchors and state ledgers and contains no Generation Unit IDs. Prompt P1 later freezes unit IDs; K2 is a separate artifact locked to exact K1 and P1 hashes.
Fail: K1 predicts `GU001`, P1 mutates K1, or K2 rewrites the K1 hash.

## 8. Cross-Generation-Unit Boundary

Input: S008 ends GU001 and S009 starts GU002 with the same character and bottle.
Expect: one boundary record locking character, wardrobe, hand, screen direction, product orientation/label, material, scene, and look states.
Fail: relying on “same as before,” missing keyframe IDs, or converting the handoff to first/last-frame mode.

## 9. Capacity Would Split Inside A Shot

Input: provider capacity would split S010 across two units.
Expect: K2 rejects the plan and routes a scoped request to Shot Director to replace S010 with explicit stable Shot UIDs before Storyboard/V1/K1/P1 are rebuilt for that scope.
Fail: `within_shot_split`, hidden sub-shot IDs, or an unrecorded midpoint.

## 10. Selective Invalidation

Input: only S005 storyboard changes.
Expect: only S005 keyframes/ledgers, dependent V2 controls, boundary records touching S005, and prompts become stale. Other keyframe binary hashes remain identical.
Fail: regenerating all shots or preserving a stale S005 keyframe.

## 11. Shared Artifact Hash And Prompt Sidecar

Draft envelope: expect `sha256: null`.
Approved envelope: expect SemVer `version` plus SHA-256 of canonical JSON after removing only the top-level envelope `sha256`; nested dependency owner/version/hash remain included.
Fail: omitting nested hashes, hashing pretty-printed JSON, allowing NaN, using image `file_sha256` as the envelope hash, or changing a persisted generation prompt without changing its `prompt_file_sha256`.

## 12. Full Authority Inventory

Input: K1 for a product shot.
Expect: exact current Shot Contract, final Storyboard, Global Look root, every resolved first-class Look Reference asset, V1/exemption, and every relevant character/product/packaging/material/scene authority are locked per shot and in the manifest dependencies; all Canon locators resolve from explicit project root.
Fail: one generic fixture authority substitutes for the real owners, or any current required authority is silently omitted.

## 13. Upstream Conflict

Input: approved storyboard places the bottle label forward while approved timing animatic requires a back-facing handoff.
Expect: `blocked_upstream_conflict` for affected shots and a precise change request to the correct owner.
Fail: silently rotating the bottle or editing the Shot Contract.

## 14. Project Canon Receipt

Expect: one shared-format `MANIFEST_UPDATE_RECEIPT.json` registers exact K1, anchor, projection, and optional K2 artifact IDs against before/after registry hashes; each binary anchor has separate primary-byte and complete record-sidecar locks.
Fail: a private canonical manifest, missing owned artifact ID, duplicated ID, receipt from another Skill, pseudo artifact hash, or swapped binary behind an unchanged record sidecar.

## 15. No Out-Of-Scope Artifacts

Fail any package containing video-generation payloads, music, edit decisions, color-mastering instructions, an independent output-QC report, a model router, or an orchestrator.

## Automated Coverage

`python3 scripts/test_contract.py` exercises positive K1 with ordinary Omni image-reference language, single-unit K2, two-unit K2, authority omission, material-state gating, prompt-byte drift, endpoint-mode rejection, classic single-image-I2V prompt injection, missing I2V deny marker, envelope hash drift, projections, receipt registration, and malformed fail-closed behavior.
