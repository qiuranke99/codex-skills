# Contract Test Cases

## 1. Seedance 2.5 Preview Claim, No Live Runtime

Input: user/project evidence says “up to 50 multimodal inputs,” but provider has no verified 2.5 endpoint/schema.
Expect: claim recorded as `preview_or_user_supplied_claim`, `runtime_verified: false`, and excluded from executable budget. Preflight may render the 2.5 semantic master; payload must use a verified compatible backend or remain blocked.
Fail: allocating 50 attachments or 30 seconds because the model name contains 2.5.

## 2. Seedance 2.0 Limits

Input: 30-second, 15-shot ad with 12 image, 4 video, and 1 audio references.
Expect: split into contiguous units no longer than 15 seconds and no unit over 9 images/3 videos/3 audio, preserving all shots and required controls.
Fail: one 30-second request, silent reference omission, fixed three seconds per shot, or claim of direct 2.5-package compatibility.

## 3. 15-Second Multi-Shot Unit

Input: six contiguous shots totaling 15 seconds with capacity-valid bindings.
Expect: one unit when complexity/previs/provider allow; six storyboard records remain six shots.
Fail: forcing six API calls or merging storyboard cells.

Automated fixture: six shots with non-uniform target durations `[1, 2, 3, 2, 4, 3]`, one P1 unit, K2 single-unit exemption, and required V2 video.

## 4. 30-Second Verified Provider

Input: provider runtime schema explicitly verifies 30 seconds and sufficient modality counts.
Expect: one 30-second unit is permitted if control complexity also passes.
Fail: relying only on preview/marketing evidence.

## 5. Partial R2V Provider

Input: provider accepts images but not the required Control Previs video.
Expect: `blocked_unsupported_required_modality` naming video/previs as missing.
Fail: dropping the video, translating its motion into prose, or falling back to text-only/endpoint-frame generation while claiming equivalence.

## 6. Full Relevant Asset Binding

Input: 20 approved project assets; GU001 needs 11, GU002 needs 14.
Expect: every asset classified for both units; all relevant non-conflicting assets selected subject to verified capacity; safe split/atlas applied if needed.
Fail: arbitrary “best 4–5” selection or filling unused capacity with irrelevant references.

## 7. Conflicting References

Input: approved product keyframe shows label forward; approved Previs shows back orientation.
Expect: affected unit blocked and upstream change request to the owning artifact; unaffected units remain compilable.
Fail: averaging, silently choosing one, or editing the upstream keyframe in prompt text.

## 8. Global Look Repetition

Input: three generation units and fifteen shot repair prompts.
Expect: exact `GLOBAL_LOOK_PROMPT_FULL` and `GLOBAL_DIRECTING_GRAMMAR` bytes appear in all 18 prompts.
Expect additionally: every shot injects its exact approved `LOOK_STATE_ID`, `LOOK_STATE_PROMPT_FULL`, State reference identities, and legal structured/exact Shot Delta after the global Core.
Fail: “same as above,” summary, version ID only, missing State, inheriting the previous scene's State, or missing block in repair prompts.

## 9. 2.0 Time Rendering

Input: canonical IR contains shot target windows.
Expect: 2.5-first render preserves explicit windows; 2.0 render preserves order/relative pacing and keeps exact windows in IR/payload metadata.
Fail: claiming frame-accurate cut timing or deleting target timing from canonical truth.

## 10. Single-Shot Repair

Input: user rejects only S005 because alias binding is wrong.
Expect: revise the S005 repair/unit binding, new version/hash/diff, and unchanged unrelated prompt bytes. Storyboard remains 15 shots.
Fail: regenerate all prompts or change S005 keyframe to hide a binding bug.

## 11. Upstream Feedback Route

Input A: user changes the already approved low-angle intent. Expect Shot Script Director.
Input B: Shot Contract remains low-angle but the storyboard frame is high-angle. Expect Modular Storyboard.
Input C: start frame is correct but the camera rises along the wrong path. Expect Timed Animatic/Previs Director.
Fail: routing all three to Storyboard, injecting edit/QC work, or changing prompt framing against an approved authority.

## 12. Shared Artifact Hash

Expect SemVer; exact dependency ID/owner/SemVer/hash; draft hash null; non-draft hash equals canonical JSON excluding only the envelope's top-level `sha256`, with nested hashes retained.
Fail: pretty-print-dependent hash, missing dependency owner, NaN, or binary hash substituted for envelope hash.

## 13. Full Canon Inventory And Two Snapshots

Input: P1 snapshot contains Shot Contract, canon assets, Look, final Storyboard, V1, and K1; P2 snapshot adds K2 and V2.
Expect: P1/P2 snapshot hashes are immutable, every active compile artifact appears exactly in final IR inventory, and supersession explains every removal.
Fail: delete an active asset from both IR and bindings, use `structure_draft`, or silently remove a preflight artifact from the compile snapshot.

## 14. Exact Locks And Output Locks

Expect: IR, binding, input lock, and payload agree on exact `(artifact_id, owner_skill, version, sha256, file_path, file_sha256)` identities; output locks cover every required generated file except self-referential exclusions.
Fail: replace only owner/version/hash/file hash with another syntactically valid value.

## 15. Copy And Claim Provenance

Expect: each shot preserves source-backed dialogue/on-screen copy and claim IDs with `model_spoken`, `external_overlay_handoff`, or `prohibited_model_text`.
Fail: flatten claims to prose, invent model text, or lose source IDs.

## 16. Recursive Payload Denylist

Fail any nested key or value containing T2V, first/last/start/end/endpoint-frame, first-last interpolation, or equivalent fallback—even if the provider display name is valid.

## 17. Stable Documented Backend

Input: provider alias `vendor/doubao-seedance-2.0-omni` claims 30 seconds but binds `documented_backend_profile_id: seedance_2_0_documented_omni`.
Expect: documented 15-second ceiling still applies and intersects the provider limit.
Fail: bypassing the ceiling because model-name substring matching did not recognize the alias.

## 18. Manifest Update Receipt

Expect: exact shared receipt fields, compile-snapshot base hash, resulting registry hash, and every Prompt-owned artifact ID exactly once. Snapshots are not registered as competing manifests.

## 19. Forbidden Scope

Fail any final package that creates music, editing, color-mastering, output-QC approval, independent model/prompt router, generation orchestrator, experiment log, text-only generation payload, or endpoint-frame payload.

## 20. Actual Upstream Semantic Read

Input: Canon-locked original Shot Contract, Global Look, Storyboard, K1, K2, Previs V1/V2, P1 records, binary files, and final IR.
Expect: record bytes, complete owner envelope, Canon identity, IR action/camera/timing/copy/claims, Global Directing, Look Core/State/Delta, Storyboard/Keyframe IDs, and P1/K2/V2 membership all agree exactly.
Fail: change IR alone; point Canon at a Prompt-made projection; change projection and IR together; change original owner JSON without matching actual post-Canon; or mismatch record/file/envelope hashes.

## 20A. Real Project Root And Applied Canon

Input: `<package_root>` nested under a different `<project_root>`, owner artifacts in sibling packages, and actual post-write Canon path.
Expect: Canon inputs resolve against project root, Prompt output/revision locks resolve against package root, compile snapshot descends from preflight snapshot, and receipt result equals actual post-Canon hash.
Fail: omit actual Canon, pass the wrong project root, use absolute/`..` paths, self-assert receipt hashes, mutate a compile-active entry, or omit a registered Prompt artifact.

## 21. Required Controls Cannot Be Classified Away

Input: every shot declares identity/product/scene/Look/Storyboard/Keyframe/V2 `required_control_artifact_ids`.
Expect: every ID reaches its unit as a direct selected binding or a source panel in a selected verified atlas.
Fail: relabel all images `irrelevant_to_unit`, delete the image binding, and claim the reduced count is still ready.

## 22. Provider Schema Snapshot

Input: `provider_schema_verified` profile and one local snapshot with file SHA-256.
Expect: exact equality for model ID, surface, backend, modalities, limits, and image/video/audio upload constraints.
Fail: URL-only evidence, snapshot drift, inverted ranges, or a MIME/codec/byte/dimension/aspect/fps/stream claim absent from the snapshot.

## 23. Deterministic Real-Image Atlas

Input: single-frame PNG/JPEG/WebP sources with mixed native sizes, ordered v2 spec, dry-build projection, RGB8 PNG atlas, and runtime receipt.
Expect: no scaling; fixed max-native-cell padding; P1 and P2 reproduce identical bytes, dimensions, roles, Pillow/codec versions, and receipt.
Fail: PPM/HEIC, one-panel group, low-resolution panel, label role, animation, source/runtime/hash drift, provider MIME/byte/dimension/aspect rejection, or receipt self-assertion.

## 24. Whole-Shot Unit Boundaries

Input: one scripted shot would exceed verified capacity.
Expect: block and route to Shot Script Director to create stable replacement Shot UIDs, then rebuild downstream.
Fail: `within_shot_split`, hidden segment IDs, or interior timing cuts inside one canonical Shot UID.

## 25. Anchored Revise

Input: user feedback, previous IR, previous dependency lockfile, current diff, and complete changed/unchanged output partition.
Expect: prior files are hash-locked; declared changed outputs have real byte diffs; all unchanged outputs retain prior hashes.
Fail: self-declared previous package, tampered prior lock, unrelated output drift, or a “changed” path with no byte change.

## 26. Standalone P1 Gate

Input: preflight Canon snapshot, exact current source Canon, P1 plan, model/provider capability profiles, and provider-schema evidence; no P2 files, K2, or V2 exist.
Expect: every active Canon artifact has one complete decision and role set; P1 directly depends on every active ref; counts derive from decisions; real direct media and atlas dry-builds satisfy upload constraints; whole-shot units pass; the standalone validator exits zero.
Fail: omit/forge/narrow an asset, collapse audio/video to text, fake counts, tamper an atlas projection, use one panel, remove Canon, split inside a Shot UID, exceed provider constraints, or require P2.

## Automated Coverage

`python3 scripts/test_preflight_contract.py` attacks omission, ref/count/role drift, audio-to-text collapse, one-panel/tampered atlas plans, Canon loss, within-shot units, and capacity. `python3 scripts/test_reference_atlas.py` proves deterministic common-raster decode, native-size padding, RGB8 PNG output, runtime locking, and fail-closed dependencies/codecs. `python3 scripts/test_contract.py` additionally attacks same-count identity swaps, role narrowing/omission, label injection, provider MIME/bytes/dimensions/aspect/container/codec/ranges, stored-probe lies, actual audio, semantic feedback roles, revisions, payload modes, and locks.

Prompt and standalone-P1 mutation cases execute sequentially inside ordinary byte-copy fixtures. The Packaging owner record, exact-copy evidence, approval/prompt evidence, and complete run tree are frozen behind a pre-write audit barrier; only dirty non-Packaging paths are restored between cases. A same-size overwrite plus timestamp-restoration attack must be rejected before bytes change. A real Packaging tamper canary uses a separate non-linked copy, bypasses the test cache, and must fail the production owner validator. Every suite child test retains the 180-second budget; timeout handling terminates the complete child process tree and reports the exact test label and elapsed time.
