# Test Cases

## Positive Coverage

1. **Simple single-shot skip** — one static five-second shot, no complex motion, validated skip artifact, no empty videos.
2. **15-second three-shot sequence** — unequal shot durations, contiguous V1, one provider-verified 15-second V2 unit.
3. **30-second seven-shot sequence / 30-second provider** — one V2 unit only after provider preflight proves the limit.
4. **30-second fifteen-shot sequence / 15-second provider** — two contiguous V2 units; Shot UIDs and storyboard remain unchanged.
5. **Seventeen-shot sequence** — complete ordered coverage across multiple units without omission, duplication, or fixed three-second pacing.
6. **Liquid track** — volume, viscosity behavior, gravity, wetting, contacts, breakup/coalescence, and state at cut are explicit.
7. **Cloth track** — anchors, drape/stiffness, wind, collision, settling, and state at cut are explicit.
8. **Hair track** — root lock, inertia, gravity/wind, collision, settling, and state at cut are explicit.
9. **Provider change after V1** — V1 remains valid; only unit map, V2, and prompt dependencies become stale.
10. **Acyclic K2 handshake** — V2 binds the exact P1 plan and exact K2 Boundary Supplement; K1 never predicts Generation Unit IDs.
11. **Real media evidence** — V1/V2 are decodable videos whose live ffprobe duration, stream count, rational frame rate, dimensions, decoded frame/packet counts, and Shot UID chapters equal stored evidence and timelines.
12. **Actual Canon closure** — sources and every registered Previs artifact are active Canon entries whose project-relative locators, file hashes, JSON envelopes, dependencies, and scopes match; receipt binds the actual post Canon.
13. **Provider evidence projection** — local provider-runtime snapshot bytes and semantic limits exactly equal the P1-selected provider profile.
14. **Stable Canon slots** — P1 is `generation_unit_preflight_plan`, root is `previs_manifest`, V1 is `timing_animatic_v1`, and V2 units are `control_previs_v2:<GU>`; no alias slots pass.
15. **Primary/record separation** — Canon primary locator/hash binds manifest JSON, MP4, or motion JSON; artifact-record locator/hash independently binds the complete owned JSON sidecar.
16. **Project/package separation** — `package_root` is a child of explicit `project_root`; sibling owner packages resolve only through Canon record locators, while package files can never escape the package.
17. **Provider video-input closure** — the local evidence exactly projects Prompt provider `input_constraints.video`; live V2 ffprobe plus actual bytes satisfy media type, container, codec, file size, duration, dimensions, aspect ratio, fps, and audio policy.
18. **Omni image references remain legal** — storyboard/keyframe/asset images are ordinary references inside Omni R2V and do not trigger the standalone-I2V prohibition.

## Required Rejections

1. Multi-shot project uses the simple-shot skip branch.
2. V1 depends on keyframes/provider preflight or claims provider-specific control.
3. Timeline has a gap, overlap, nonpositive duration, wrong order, or wrong final runtime.
4. A V2 unit reorders shots, duplicates/omits a Shot UID, or exceeds provider max duration.
5. V2 exists without approved V1, keyframes, or provider preflight.
6. Provider profile lacks multimodal reference-video support.
7. Control video is marked as final edit, contains music, or claims final appearance.
8. Control dimensions include character identity, product geometry, packaging text, scene identity, Global Look, final edit, music, or output QC.
9. Liquid, cloth, or hair track lacks a class-specific physical behavior field.
10. T2V, first/last-frame, or standalone/classic single-image-to-video is used as fallback.
11. Artifact version is not SemVer, dependency lacks owner, or canonical hash excludes nested dependency hashes.
12. V2 omits K2, binds K2 from another P1 plan, or survives a changed Generation Unit Plan. Fail.
13. Media is an arbitrary binary, stored duration/frame rate/resolution/frame count/packet count differs from live media, Shot chapters differ, media path escapes project root, or ffprobe is unavailable. Fail closed.
14. An authority snapshot is internally self-consistent but not the exact active Canon entry; a Canon locator escapes the project root or has wrong bytes; receipt base/result/owner/registered IDs differ from actual Canon. Fail.
15. Provider profile claims reference video/duration limits without a local hash-bound runtime snapshot, or the snapshot projection differs. Fail.
16. Any root, V1, V2, timeline, media-probe, authority, input-evidence, motion-track, or invalidation record contains an undeclared field. Fail.
17. Canon conflates an MP4 primary with a JSON artifact record, points a record outside `owned_artifacts`, or lets motion primary JSON differ from its complete record. Fail.
18. CLI omits explicit project root, Canon is not at its canonical project path, package root is outside project root, or a package/Canon locator escapes its assigned root. Fail.
19. Provider video-input constraints are absent, differ from the exact Prompt runtime profile projection, or the real V2 file violates any projected container/codec/byte/duration/dimension/aspect/fps/audio constraint. Fail closed.
20. The required `standalone_single_image_to_video` deny marker is removed, while ordinary Omni image references remain accepted. Fail only the former.

## Automated Contract Suite

Run:

```bash
python3 scripts/test_contract.py
```

The suite covers single-shot skip, 15/30-second multi-shot units, N=3/7/15/17, motion classes, real micro-video probing, arbitrary-binary and false-metadata attacks, path traversal, actual Project Canon/receipt binding, exact provider video-input projection, live constraint enforcement, standalone-I2V exclusion, ordinary Omni image-reference acceptance, exact-field rejection, provider gates, and canonical artifact hashing.
