# Prompt Package QA Checklist

## Input Truth

- [ ] Separate immutable P1 and P2 snapshots prove the entire `PROJECT_CANON_MANIFEST` was inventoried with no silent deletion.
- [ ] Original Shot/Look/Storyboard/K1/K2/Previs/P1 owner records were read from Canon `artifact_record_locator`, byte-hashed, envelope-rehashed, and exactly projected into IR; no Prompt-made authority projection exists.
- [ ] `<project_root>` and `<package_root>` are distinct explicit roots; Canon paths resolve only under project root, package outputs/revision anchors only under package root, with no absolute or `..` path.
- [ ] Actual post-write Canon descends from the compile snapshot and receipt base/result/registered IDs match its active Prompt-owned entries.
- [ ] P1 consumes K1 and freezes Generation Units; P2 consumes exact P1, K2, and required V2 without a dependency cycle.
- [ ] Final compile uses only `user_approved`, hash-valid, non-stale upstream artifacts.
- [ ] Every dependency includes artifact ID, owner, SemVer version, and hash.
- [ ] Canonical IR covers every scripted shot exactly once and in approved order.

## Capability Truth

- [ ] Model target and provider runtime profiles are separate.
- [ ] Seedance 2.5 is labeled forward-compatible unless the selected runtime is provider-schema verified.
- [ ] A 50-input or 30-second preview claim is not used as an executable budget without runtime verification.
- [ ] Stable `documented_backend_profile_id`, not provider model-name substring, selects the documented ceiling.
- [ ] Seedance 2.0 units obey 15s, 9 images, 3 videos, and 3 audio ceilings plus any stricter provider limit.
- [ ] Unknown provider capability remains unknown.
- [ ] Missing required modalities block execution instead of triggering a lower-control fallback.

## Reference Binding

- [ ] Every approved artifact is classified for every generation unit.
- [ ] Every relevant non-conflicting artifact is selected.
- [ ] Irrelevant, superseded, conflicting, and unsupported records have explicit reasons.
- [ ] Every selected alias has a complete role set, one primary role, scope, expected influence, artifact ID/owner/version/hash, and optional binary hash; multiple roles still count as one attachment.
- [ ] No capacity is filled with redundant evidence.
- [ ] Any deterministic atlas maps exact source pixels and cannot be mistaken for a new authority.
- [ ] Every binary reference and atlas has a producer-owned full JSON artifact record sidecar with an independent Canon lock.
- [ ] P1 dry-built and P2 byte-rebuilt the same PNG/JPEG/WebP→RGB8 PNG spec; native pixels, padding, Pillow/codec versions, and encoder parameters match the receipt.
- [ ] Every atlas panel meets the frozen 256×256 minimum (or a higher provider minimum), and label/microcopy evidence is bound directly rather than transported through an atlas.
- [ ] Every shot's `required_control_artifact_ids` is delivered directly or through a selected verified atlas.
- [ ] Provider snapshot locks MIME/codec/container/bytes/dimensions/aspect/fps/stream constraints and every actual selected media file passes live Pillow/ffprobe inspection.

## Prompt Structure

- [ ] Generation task/output specification exists.
- [ ] Reference/control mapping exists.
- [ ] Principal subjects and initial scene state exist.
- [ ] Emotion/advertising intent is translated into visible behavior.
- [ ] Exact Global Directing Grammar appears in every unit and repair prompt.
- [ ] Exact Global Look block appears in every unit and repair prompt.
- [ ] Every shot injects exact assigned Look State and State references between Global Look Core and legal Shot Delta.
- [ ] Every shot has action, camera, blocking/spatial change, state change, ending state, spoken/on-screen copy delivery, claim provenance, and legal Look Delta.
- [ ] Each shot has one primary camera movement.
- [ ] No opaque artifact ID is used as a bare actor in model-facing prose.

## Output And Revision

- [ ] Master, unit, repair, binding, payload, degradation, feedback, diff, lockfile, and manifest-update receipt artifacts exist.
- [ ] Provider payload status is executable only when all capability and binding gates pass.
- [ ] Shot repair prompts are self-contained.
- [ ] Feedback is routed to one owner with evidence.
- [ ] Prompt-owned revisions preserve upstream facts and unaffected bytes.
- [ ] Revise mode locks the previous IR, previous dependency lockfile, revision diff, and exact changed/unchanged output partition.
- [ ] Generation units split only between complete Shot UIDs; over-capacity single shots route upstream for new Shot UIDs.
- [ ] No independent model router, orchestrator, experiment log, music, editing, color-mastering, or footage-QC artifact exists.

## Generation Mode Safety

- [ ] `generation_mode` is exactly `omni_reference_to_video`.
- [ ] No text-only or endpoint-frame provider fallback is permitted.
- [ ] Keyframes and storyboards are ordinary multimodal bindings, not endpoint controls.

## Integrity

- [ ] Every non-draft JSON envelope passes canonical SHA-256.
- [ ] Dependency lockfile matches exact files and dependency versions.
- [ ] IR, bindings, input/record locks, output locks, manifest snapshots, update receipt, and actual post-Canon agree on exact artifact identities.
- [ ] Validator exits zero before `package_status: compiled`.
