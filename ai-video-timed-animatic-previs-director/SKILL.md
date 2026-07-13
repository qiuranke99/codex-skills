---
name: ai-video-timed-animatic-previs-director
description: "Design and package silent timing animatics and provider-bound control previs for high-control multimodal AI video generation. Use when a multi-shot generation unit needs explicit shot boundaries, timing, cuts, camera trajectory, subject blocking, object motion, or liquid/cloth/hair physics. Produce V1 Timing Animatic before keyframes, then V2 Control Previs after approved keyframes and provider preflight. Do not use for storyboards, identity/product/look ownership, text-to-video, first/last-frame generation, final editing, music, video-output QC, model routing, or orchestration."
---

# AI Video Timed Animatic / Previs Director

## HIGH_CONTROL_RELEASE_GATE_V2

Before any action or production output, resolve this `SKILL.md` directory and run its sibling `../high-control-ai-tvc/tools/release_control.py check --format json`. Proceed only when `ready_latest=true`. On any failure, stop: run `sync`, then start a new Codex task. Bind the returned `release_commit` to this stage; never substitute a mutable Windows/Mac authoring checkout.

中文名：AI 视频定时动画预演导演

Create two distinct control layers:

1. `timing_animatic_v1` — provider-neutral whole-ad timing and rough motion, produced after the modular storyboard and before high-cost keyframes.
2. `control_previs_v2` — provider-bound control video per approved generation unit, produced after generation-ready keyframes and Prompt Director preflight.

The Skill controls time and motion. It never becomes the authority for character identity, product geometry, packaging text, scene identity, or Global Look.

## Input Gates

### V1 Gate

Require an assistant-validated or user-approved Shot Contract and Modular Storyboard manifest. The Shot Contract owns shot count, order, target duration, advertising function, and continuity. The storyboard supplies one independent representative frame per shot.

Read the single canonical `<project_root>/00_project_canon/PROJECT_CANON_MANIFEST.json`. Keep `<package_root>` distinct from `<project_root>`: the Previs package is contained by the project, while Shot/Storyboard/Look/Keyframe packages may be siblings. Propose only Previs-owned registry deltas and store one `MANIFEST_UPDATE_RECEIPT.json`; never create a second registry. An `assistant_validated`, `user_approved`, packaged repair, stale, or blocked result must be validated against the actual post-delta Project Canon file via explicit `--project-root` plus `--project-canon-manifest`. A copied or self-authored authority snapshot is not authority by itself: every source and every registered Previs artifact must match its exact active Canon entry and that entry's project-relative `locator` plus `file_sha256` bytes. Resolve package media/snapshots/owned artifacts under `package_root`; resolve Canon locators under `project_root`; reject every escape.

Do not require final keyframes or provider selection for V1. V1 must remain provider-neutral. If the project has exactly one static or near-static shot and no complex camera, blocking, object, liquid, cloth, hair, smoke, or interaction requirement, emit a validated skip record instead of pretending a previs adds value.

### V2 Gate

Require all of:

- approved V1 timing;
- generation-ready keyframe pack;
- Prompt Director `preflight` output containing the Generation Unit Map;
- Keyframe `boundary_supplement` bound to that exact preflight plan, including the single-unit exemption when applicable;
- actual model/provider capability profile confirming multimodal reference-video input;
- no stale upstream dependency.

If the provider only exposes T2V or first/last-frame modes, set `blocked` and return to provider preflight. Never silently downgrade.

Provider capability is not a boolean assertion. Require a local, hash-bound `provider-runtime-capability-evidence.v1` snapshot copied into `input_file_evidence`. Its profile identity, backend binding, generation mode, input modalities, duration/reference-count limits, and complete `video_input_constraints` must exactly project the selected Prompt provider-runtime profile's `input_constraints.video`. The projection includes accepted media types, containers and codecs; file-byte, duration, width, height, aspect-ratio and frame-rate bounds; and audio-track policy. If the snapshot is absent, unreadable, stale, incomplete, or semantically different, V2 is blocked.

## Canonical Resources

Read before work:

- `references/previs_contract.md` — phase order, ownership, timeline, unit, invalidation, and completion rules.
- `references/motion_physics_contract.md` — camera, blocking, liquid, cloth, hair, and rigid-object contracts.
- `references/previs_manifest.schema.json` — machine-readable package structure.
- `references/previs_manifest_template.json` — V1 minimum example.
- `references/provider_runtime_capability_evidence.schema.json` — exact local provider-runtime evidence projection required by V2.
- `test_cases.md` — required positive and adversarial coverage.

## Phase 1: Timing Animatic V1

Build a silent whole-ad animatic in absolute project time. Use storyboard frames or neutral proxies. The first shot starts at `0.000`; adjacent boundaries are contiguous; the final shot ends at `TOTAL_DURATION`; target durations sum exactly to the advertised runtime.

For every shot record:

- `shot_uid`, display order, absolute start/end, and duration;
- cut motivation and transition intent;
- rough camera path and one primary camera move;
- rough subject blocking and screen direction;
- object/material motion anchors when relevant;
- action entry, action beat, and exit-state timecodes.

V1 validates shot order, rhythm, cuts, rough camera motion, blocking, and whole-ad pacing before keyframe expense. It may use a deterministic still-frame builder for cut timing, simple 2D pan/zoom, or neutral 3D blocking. It contains no final grading, beauty treatment, music, final edit claim, or output-QC judgment.

For the supplied deterministic builder, keep the Storyboard package and Previs package under one explicit project root and run `python3 scripts/build_timing_animatic.py <storyboard_manifest> <package_root>/00_manifest/PREVIS_MANIFEST.json 01_timing_animatic_v1/timing_animatic_v1.mp4 --project-root <project_root>`. Its output locator is package-relative and its embedded Shot chapters plus full live media probe are ready for the package validator.

If timing is wrong, return to the Shot Contract or Storyboard owner. Do not compensate by distorting keyframes later.

## Phase 2: Control Previs V2

After Prompt Director preflight freezes actual generation units, consume the K2 Boundary Supplement bound to that exact plan and produce one silent control video per generation unit. The stage handshake is `K1 → P1 → K2 Boundary Supplement → V2`; V2 never asks K1 to predict Generation Unit IDs. V2 inherits V1 shot boundaries and uses approved keyframes as appearance anchors without owning their visual facts.

Each unit must:

- contain a contiguous range of Shot UIDs in approved order;
- start local time at `0.000` and end at unit target duration;
- stay within the verified provider maximum duration;
- preserve every included shot's target duration and transition boundary;
- carry explicit camera trajectory, subject blocking, object motion, and required physical motion tracks;
- declare `model_input_role: control_reference_video`;
- declare `final_edit_asset: false` and `silent: true`;
- use a neutral diagrammatic, 2D animatic, or simple 3D blocking render style;
- avoid unsupported appearance, identity, geometry, label, and look claims.

One 30-second script may use one 30-second V2 unit only when the actual provider profile proves it. Under a 15-second provider it must be split into contiguous units; the Shot Contract and storyboard remain unchanged.

## Motion And Physics

Read `references/motion_physics_contract.md`. Every consequential motion gets an explicit track with evidence, assumptions, anchors, and collision/contact behavior.

- Camera: position, orientation, focal intent, path, speed profile, focus behavior, and transition boundaries.
- Subject blocking: actor/object positions, facing, screen direction, contacts, and handoffs.
- Liquid: volume continuity, viscosity behavior, gravity, adhesion/wetting, container/contact surfaces, breakup/coalescence, and state at cut.
- Cloth: anchors, drape/stiffness intent, wind/acceleration, body collision, and settling.
- Hair: root lock, inertia, gravity/wind, body/wardrobe collision, and settling.
- Rigid object: pivot, path, acceleration, contacts, occlusion, and end state.

Do not fabricate precise engineering simulation. Classify assumptions and use visually plausible control where evidence is absent.

## Shared Artifact Envelope

Every manifest, V1, V2, skip, and motion artifact includes:

```yaml
contract_version: ai-video-artifact-v1
artifact_id:
owner_skill: ai-video-timed-animatic-previs-director
version: 1.0.0
sha256:
approval_status:
dependencies:
affected_shot_uids:
stale_reason:
```

Envelope status is only `draft`, `assistant_validated`, `user_approved`, `stale`, or `blocked`. A draft may use `sha256: null`. Every other artifact hash is canonical JSON after removing only its own top-level `sha256`; nested dependency hashes remain. Serialize UTF-8 with sorted keys, separators `(',', ':')`, `ensure_ascii=false`, and `allow_nan=false`. Every dependency has artifact ID, owner skill, SemVer, and hash. Binary files carry `file_sha256` separately.

## Output Tree

```text
previs-package/
├── 00_manifest/
│   ├── PREVIS_MANIFEST.json
│   ├── MANIFEST_UPDATE_RECEIPT.json
│   ├── source_snapshots/<authority_id>.json
│   ├── source_inputs/<input_id>.<ext>
│   └── owned_artifacts/<artifact_id>.json
├── 01_timing_animatic_v1/
│   ├── timing_animatic_v1.mp4
│   └── timing_map.json
├── 02_control_previs_v2/
│   └── <generation_unit_id>/control_previs_v2.mp4
├── 03_motion/
│   ├── camera_trajectory_map.json
│   ├── blocking_map.json
│   ├── motion_physics_tracks.json
│   └── tracks/<track_id>.json
└── 04_qa/
    ├── timeline_validation.json
    └── control_boundary_report.md
```

For a legitimate skip, register only the manifest and skip artifact (plus mandatory Canon/receipt/source-evidence files). Do not create empty V1/V2 media or motion placeholders.

The `owned_artifacts` JSON files are materialized exact copies of the root and every current nested artifact so Project Canon can bind each registered artifact ID to a complete record. They are registry evidence, not an additional creative stage. Canon `artifact_record_locator`/`artifact_record_file_sha256` point to these sidecars. Canon `locator`/`file_sha256` point separately to the primary bytes: root manifest JSON, V1/V2 MP4, or per-track motion JSON.

Use stable Canon slots: root package `previs_manifest` (the same slot advances from V1 to V2), V1 `timing_animatic_v1`, each V2 unit `control_previs_v2:<generation_unit_id>`, and each motion track `motion_track:<track_id>`. V2 approval requires exactly one older V1-only root package in Canon `superseded_artifacts`, with a lower SemVer, slot `previs_manifest`, real locator bytes, and `superseded_by_artifact_id` pointing to the current root. Consume Prompt P1 only from `generation_unit_preflight_plan`; reject the legacy `prompt_preflight_ir` alias.

## Ownership Boundaries

This Skill owns:

- timing intent and shot boundaries;
- camera trajectory;
- subject/object blocking;
- motion paths, speed/easing intent, contacts, and visual physical behavior;
- V1/V2 control-video packaging.

It does not own:

- story, shot existence/order/duration intent;
- storyboard composition;
- character identity, wardrobe, product geometry, packaging text, or scene identity;
- Global Look or final color;
- generation-grade keyframe appearance;
- model/provider selection, reference routing, final prompt compilation, video generation;
- music, final editing, or output QC.

Do not invoke T2V or first/last-frame video generation. Render control assets through deterministic animatic, 2D/3D blocking, or another provider-neutral motion-authoring method.

## Invalidation And Repair

- Shot count/order/duration change: invalidate V1 and every affected V2 unit.
- Storyboard composition/position change: invalidate affected V1 blocking and downstream V2.
- V1 timing change: invalidate affected keyframe time anchors, unit preflight, V2, and prompts.
- Keyframe state change: V1 remains; invalidate affected V2 and prompts.
- Generation Unit Map/provider capability change: V1 remains; rebuild affected V2 units.
- Global Look change: neutral V1/V2 motion data remain valid unless visibility/blocking changes; this Skill does not relight them.
- V2 change: invalidate affected generation prompts only.

Regenerate only affected assets and record `stale_reason` precisely.

## Completion Gate

`scripts/build_timing_animatic.py` requires `ffmpeg` on `PATH`, and approved-media validation requires `ffprobe` on `PATH`. A different deterministic renderer may replace the builder only when it emits the same manifest and media evidence; missing `ffmpeg` blocks this bundled rendering path, while missing `ffprobe` blocks V1/V2 approval.

For V1 readiness require:

- every Shot UID appears exactly once in whole-ad order;
- timeline is positive, contiguous, starts at zero, and ends at total duration;
- V1 depends only on approved Shot Contract and Storyboard authorities;
- V1 is provider-neutral, silent, not a model input, and not a final edit asset;
- controls stay inside the allowed motion dimensions.

For every approved V1 and V2 media artifact, run `ffprobe` against the real file at validation time. Store and live-compare container, duration, exactly one video stream, zero audio streams, rational frame rate, pixel dimensions, decoded frame count, decoded packet count, and chapter records whose Shot UID boundaries exactly equal the authoritative timeline. File hashes and self-reported metadata are insufficient. If `ffprobe` is missing or cannot decode-count the media, fail closed; do not approve.

For V2, the same live probe plus actual file-byte count must satisfy every
field of the exact provider video-input projection: media type, container,
codec, bytes, duration, width, height, aspect ratio, fps, and audio-track
policy. Passing the generic control-video probe is insufficient when the
selected provider has stricter input constraints.

Standalone or classic single-image-to-video is forbidden as
`standalone_single_image_to_video`, alongside T2V and first/last-frame modes.
This prohibition does not reject ordinary image references used inside an
`omni_reference_to_video` package: storyboard frames, keyframes, product,
character, scene, and Look references remain legal multimodal controls.
Generation-route boundary: `standalone_single_image_to_video: forbidden`;
`ordinary_image_references_in_omni_r2v: allowed`.

For V2 completion additionally require:

- approved keyframe and provider-preflight dependencies;
- generation units cover every Shot UID exactly once, contiguously, with no reorder or overlap;
- local unit timelines match V1 shot durations and provider limits;
- every control video exists, has verified file hash/duration, is silent, and is explicitly non-final;
- all relevant liquid/cloth/hair/rigid-object tracks pass their class-specific contract;
- forbidden identity/geometry/look/edit/music/QC dimensions are absent;
- `python3 scripts/validate_previs_package.py <package_root> --project-root <project_root> --project-canon-manifest <project_root>/00_project_canon/PROJECT_CANON_MANIFEST.json` exits zero.

Validator success proves package and timeline integrity, not that a generative video model will obey frame-exact cuts.

## Minimal Invocation

`Use $ai-video-timed-animatic-previs-director to build V1 whole-ad timing now, then V2 provider-bound control previs after keyframes and generation-unit preflight.`

## Shared Project Canon Write Gate

Before any Canon mutation, preserve the exact current bytes at
`<package_root>/00_manifest/BASE_PROJECT_CANON_SNAPSHOT.json` and materialize
the validated post bytes at
`<package_root>/00_manifest/CANDIDATE_PROJECT_CANON_POST.json`. Invoke only this
package's `scripts/apply_project_canon_transition.py`. The shared writer owns
the project `.canon.lock`, `PENDING_PROJECT_CANON_TRANSACTION.json` recovery or
blocking, raw-byte compare-and-swap, durable post readback, and only then
`MANIFEST_UPDATE_RECEIPT.json`. Never write Canon or an applied receipt
directly.
