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

## Generation Unit Rules

- Units contain contiguous Shot UIDs in current order.
- The ordered union of all complete-stage units equals the V1 Shot UID list exactly once.
- A unit target duration cannot exceed the verified provider maximum.
- Never assume 30-second or 50-reference capability from a preview claim; bind the actual provider preflight artifact.
- If required control-video reference input is unavailable, block V2 rather than degrade to T2V or first/last-frame mode.
- Never degrade to standalone/classic single-image-to-video. Normal image
  references inside Omni R2V remain allowed; only the one-image-as-the-entire
  video-generation-route fallback is forbidden.

## V1 Output

V1 is a silent human timing artifact with neutral proxies. It may use simple cuts, 2D pan/zoom, or neutral 3D blocking. It is not the final video and is not the preferred model input once V2 exists.

V1 controls only `shot_boundaries`, `target_timing`, `camera_trajectory`, `subject_blocking`, `object_motion`, and coarse `material_physics` anchors.

## V2 Output

V2 is a silent multimodal reference control video. It can visually carry approved keyframes but must point to those keyframes as dependencies and may not redefine their identity, geometry, scene, label, or look.

Required declarations:

```json
{
  "model_input_role": "control_reference_video",
  "final_edit_asset": false,
  "silent": true,
  "render_style": "neutral_diagrammatic_or_simple_3d",
  "identity_authority": false,
  "look_authority": false
}
```

## Real Media Evidence Gate

An approved V1 or V2 record is valid only when the validator re-runs `ffprobe` on the hash-bound real media file. The live probe must prove exactly one video stream, zero audio streams, positive rational frame rate and dimensions, positive decoded-frame and decoded-packet counts, real duration within tolerance, and chapter boundaries that exactly encode every manifest Shot UID/start/end record. Stored `actual_duration_seconds`, stored probe JSON, a filename extension, and a file hash do not replace live decoding. Missing or failing `ffprobe` blocks approval.

The deterministic V1 builder writes Shot UID chapters into the video and emits the complete live probe record. V2 control renders must do the same before packaging.

## Provider Evidence Gate

`multimodal_reference_video_supported: true` is never evidence. V2 must consume a local hash-bound `provider-runtime-capability-evidence.v1` snapshot from the selected provider surface. Its profile ID, provider/model/surface/backend binding, omni-reference mode, supported modalities, effective duration/input limits, and full `input_constraints.video` projection must exactly equal the selected Prompt provider-runtime profile and P1 preflight. Live ffprobe plus real file bytes must then prove every V2 input satisfies the projected media type, container, codec, byte, duration, dimension, aspect-ratio, fps, and audio-track constraints. Drift, a URL-only claim, a self-reported media record, or a missing local snapshot blocks V2.

## Project Canon Binding

Packaged and approved results require the actual post-delta `<project_root>/00_project_canon/PROJECT_CANON_MANIFEST.json`. `package_root` must be a contained child of, but must not be conflated with, `project_root`; sibling Shot/Storyboard/Keyframe packages remain reachable only through Canon. Validate the registry itself, then prove every source authority and every Previs-owned registered artifact is the exact active, downstream-eligible Canon entry. Resolve Canon locators only against explicit `project_root`; resolve Previs media, copied inputs, snapshots, and owned-artifact JSON only against `package_root`. Each entry must bind to a safe project-relative locator, real file bytes, matching `file_sha256`, the same artifact envelope, dependencies, approval, scope, version, and canonical hash. Package-local source snapshots are caches only and must equal the Canon-located originals.

The shared update receipt must match the actual post Canon `sha256`, its `base_manifest_sha256`, `updated_by_skill`, and the exact set of current Previs-owned artifact IDs. Materialize the root and nested V1/V2/track/skip records under `00_manifest/owned_artifacts/`. Canon record locator/hash fields bind those complete JSON records; the separate primary locator/hash fields bind the root manifest, V1/V2 MP4, or per-track motion JSON.

Stable Canon slots are `previs_manifest` for the evolving root package, `timing_animatic_v1`, `control_previs_v2:<generation_unit_id>`, and `motion_track:<track_id>`. When the root advances to V2, the one preceding V1-only root must move to `superseded_artifacts` with a lower version, hash-bound locator, and replacement link to the active root. P1 must be consumed from `generation_unit_preflight_plan`; `prompt_preflight_ir` is not a second alias.

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
