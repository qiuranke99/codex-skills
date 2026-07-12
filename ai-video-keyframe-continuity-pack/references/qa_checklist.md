# Keyframe Package QA Checklist

## Coverage

- [ ] Shot Contract count equals manifest shot-record count.
- [ ] Every `shot_uid` is unique and covered exactly once.
- [ ] Every shot has at least one approved independent anchor or fully validated storyboard promotion.
- [ ] No contact-sheet crop or multi-panel source is used as a keyframe.

## Authority And Dependency

- [ ] Every dependency resolves exact ID/owner/SemVer/hash.
- [ ] No `draft`, `blocked`, or `stale` dependency entered production bindings.
- [ ] Keyframes do not redefine upstream story, identity, geometry, scene, look, or timing.
- [ ] Ordinary inferred directing decisions are recorded and do not invent product claims.

## Visual Fidelity

- [ ] Character identity, wardrobe, hair, makeup, accessories, pose, gaze, and screen direction match ledgers.
- [ ] Product geometry, label-facing state, material, orientation, placement, and mechanism state match ledgers.
- [ ] Scene, framing, camera, subject placement, and Global Look match approved sources.
- [ ] Hands, faces, product contact, transparent layers, and material boundaries are readable.
- [ ] No unrelated subjects, duplicate people/products, invented text, storyboard annotation, grid, UI, or watermark appears.
- [ ] Any intrinsic packaging/product/in-world text is bound to exact downstream-eligible Canon source authorities; provenance is not misreported as OCR or exact-copy proof.

## Time And Dynamic State

- [ ] Multi-shot/timing-sensitive projects bind approved V1 motion timecodes.
- [ ] Single-static-shot exemption is explicit when used.
- [ ] K1 contains no guessed Generation Unit ID; P1 is the sole unit-plan authority.
- [ ] K2 is a separate artifact bound to exact K1 and P1 hashes, with a legal single-unit exemption or every adjacent-unit handoff.
- [ ] Dynamic state ladders contain every control-critical state and no filler states.
- [ ] Material trajectories record relevant fill, flow, droplets, meniscus, wetting, optical boundaries, and settled state.
- [ ] Every cross-generation-unit boundary has matched outgoing/incoming continuity facts.

## Mode Safety

- [ ] Every frame is declared `omni_reference_anchor`.
- [ ] No first-frame, last-frame, start-frame, end-frame, endpoint interpolation, T2V, or standalone/classic single-image-to-video instruction exists.
- [ ] Ordinary image references inside Omni R2V remain allowed and are not misclassified as standalone I2V.
- [ ] No music, editing, color-mastering, or output-QC artifact is included.

## Integrity

- [ ] Approved JSON envelopes pass the canonical hash rule.
- [ ] Each generated/promoted image has a verified `file_sha256`.
- [ ] Each generated image has an exact persisted prompt sidecar.
- [ ] Every prompt sidecar byte hash is verified.
- [ ] One manifest update receipt registers exact K1/projection/anchor artifacts and K2 when present.
- [ ] Visual inspection occurred after the terminal image-generation turn.
- [ ] Validator exits zero before `package_status: packaged`.
