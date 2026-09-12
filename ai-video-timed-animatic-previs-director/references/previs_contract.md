# Timing Animatic And Control Previs Contract

## Phase Order

```text
Approved Shot Contract
→ Modular Storyboard
→ Timing Animatic V1
→ Generation-ready Keyframes
→ Prompt Director provider preflight and Generation Unit Map
→ Keyframe Boundary Supplement
→ Control Previs V2 per generation unit
→ final prompt compilation
```

V1 must not depend on final keyframes or a provider profile. V2 must depend on V1, keyframes, and provider preflight. This resolves the circular dependency between motion design and provider packaging.

## Absolute And Local Time

The V1 timeline uses absolute whole-ad seconds. It starts at `0.000`, is gapless and non-overlapping, and ends at the Shot Contract total duration. Each entry uses the same stable `shot_uid` and approved display order.

V2 uses local unit time. Every unit begins at `0.000`; its shot durations equal V1; its final end equals the unit target duration. Unit grouping does not create, delete, merge, split, or renumber storyboard shots.

Timecode is a target control, not proof of frame-exact generative obedience. Record actual returned runtime separately after generation; final deterministic trimming belongs to external editing, outside this Skill.

## Mode-Specific Reading

V1 and a legitimate skip do not require provider, K2, or registry evidence.
For V2, read `v2_control_contract.md` for generation-unit and provider gates.
For explicitly requested Canon registration, read `project_canon_integration.md`.
Neither reference adds a gate to the standalone V1 branch.

## V1 Output

V1 is a silent human timing artifact with neutral proxies. It may use simple cuts, 2D pan/zoom, or neutral 3D blocking. It is not the final video and is not the preferred model input once V2 exists.

V1 controls only `shot_boundaries`, `target_timing`, `camera_trajectory`, `subject_blocking`, `object_motion`, and coarse `material_physics` anchors.

## Real Media Evidence Gate

An approved V1 or V2 record is valid only when the validator re-runs `ffprobe` on the hash-bound real media file. The live probe must prove exactly one video stream, zero audio streams, positive rational frame rate and dimensions, positive decoded-frame and decoded-packet counts, real duration within tolerance, and chapter boundaries that exactly encode every manifest Shot UID/start/end record. Stored `actual_duration_seconds`, stored probe JSON, a filename extension, and a file hash do not replace live decoding. Missing or failing `ffprobe` blocks approval.

The deterministic V1 builder writes Shot UID chapters into the video and emits the complete live probe record. V2 control renders must do the same before packaging.

## Standalone Input And Output Integrity

Consume supplied Shot/Storyboard/Keyframe artifacts through explicit input
locators, envelope hashes and file locks; no registry or producer package is
required. Source snapshots must match those real supplied bytes, not merely
self-consistent invented records. Keep package and input roots distinct and
reject path escapes. Materialize complete root and nested V1/V2/track/skip
records under `00_manifest/owned_artifacts/`; verify their envelopes and primary
bytes independently. Hash verification does not grant user approval.

Optional registration adds the Canon checks in `project_canon_integration.md`
only when the caller supplied the registry and requested that mutation.

## Legitimate Skip

Skipping is valid only when all are true:

- exactly one shot;
- static or near-static camera;
- simple subject action;
- no multi-subject blocking;
- no consequential object, liquid, cloth, hair, smoke, or mechanical motion;
- no timing-sensitive transition.

The skip record is an artifact, is dependency-bound, and states `previs_needed: false`. Multi-shot work can never use the skip branch.

## Artifact Contract

Every artifact uses `contract_version: ai-video-artifact-v1`, owner `ai-video-timed-animatic-previs-director`, SemVer string, canonical artifact hash, standard envelope status, dependencies with artifact ID/owner/SemVer/hash, exact affected Shot UIDs, and stale reason.

Canonical hashing removes only the artifact's top-level `sha256`, not dependency hashes, then uses UTF-8 JSON with `sort_keys=true`, compact separators, `ensure_ascii=false`, and `allow_nan=false`.

## Non-Ownership

Forbidden dimensions are:

- character identity;
- wardrobe identity;
- product geometry;
- packaging text;
- scene identity;
- Global Look and final color grade;
- music;
- final edit;
- output QC.

The control render should be visually neutral enough that it cannot be mistaken for these authorities.

## Invalidation

Invalidate at the earliest changed authority and propagate only downstream. Keep unaffected V1 timing when only provider packaging changes. Keep neutral motion trajectories when only Global Look changes. A changed shot order always returns upstream to Shot Contract before any local re-render.
