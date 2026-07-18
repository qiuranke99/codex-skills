# Test Cases And Historical Regressions

Use these cases for routing, package validation, and fresh-context evaluation. Do not treat them as hidden expected answers.

## Should Trigger

1. Multiple wheelchair references show frame, wheels, brakes, footrests, folding mechanism, materials, markings, and several cameras; user needs reusable video-continuity views.
2. A wheelchair has only one front three-quarter source, and the user asks why no multi-camera coverage; produce one truthful source camera, a six-target plan, and exact missing-capture/render requests without inventing the rear.
3. An industrial robot has joint, cable, end-effector, and several verified 3D-render sources that can support deterministic camera coverage.
4. A stroller manual and official photos show chassis, wheel assemblies, latches, canopy, folded state, and marking locations.
5. A cinema camera rig has a body, mount, ports, cage, handles, battery plate, controls, and detachable components that must agree across shots.

## Should Not Trigger

1. A simple opaque speaker only needs a low-risk six-view board.
2. Glass, liquid, refraction, or reflection is the primary product risk.
3. Exact packaging copy/barcode/layout is the primary risk.
4. User wants a lifestyle ad, poster, scene, redesign, ordinary retouch, source search, prompt-only result, or engineering certification.
5. No usable visual product reference exists.

## Camera Evidence Boundaries

- One front photo: accept at most one `source_copy` or source-aligned auxiliary camera; block rear, opposite-side, underside, and hidden-node targets with exact requests.
- Multiple crops of one front three-quarter photo: one pose bin only, never multiple cameras.
- Two photos show opposite sides but neither rear: accept supported cameras; keep rear target blocked instead of blocking all Geometry.
- Existing verified 3D/CAD plus runnable renderer: source renders may carry hard authority only with frozen model/render provenance.
- A filename says “large wheel” but pixels show the small-wheel variant: pixels win; separate or block the variant.
- Generative novel rear view looks plausible: it remains auxiliary and cannot prove hidden topology.

## Historical Wheelchair Regressions

### Repeated-Angle Multi-Panel Board

Input: many D08T wheelchair references. Output: one board with seven whole-product cells, including near-duplicate side profiles and near-duplicate three-quarter views; geometry differs across cells.

Required result:

- reject duplicate pose bins and cross-camera Critical Node drift;
- do not count a crowded board as independent camera coverage;
- create one full-resolution asset per accepted camera;
- derive any contact sheet only after camera acceptance.

### Excessive Boards And Upload Ambiguity

Input: Geometry, detail, interface, and material boards with repeated content. User cannot tell which to upload.

Required result:

- camera coverage remains primary;
- each diagnostic board has one named risk job;
- approve a one-to-five-asset Primary Upload Bundle with explicit selection reasons;
- do not generate another final collage that can drift.

### Attractive But Wrong Large-Wheel Variant

Input source: silver wheelchair with a large rear wheel, coarse spoke system, separate handrim, specific caster/fork, frame, cross-brace, and footrest relationships. Generated material board increases spoke count and changes the caster/fork, brace, and footrest topology.

Required result:

- fail Critical Node comparison with `spoke_count_drift`, `wheel_axle_handrim_drift`, `caster_fork_drift`, and/or `frame_crossbrace_drift`;
- set only the affected asset to repair;
- do not approve on visual attractiveness or color similarity.

### Single-Angle Small-Wheel Variant

Input source: wine-red frame, black small rear wheels, no handrim, one front three-quarter view. Generated diagnostic board repeats the same whole-product angle plus details.

Required result:

- one source camera may be accepted;
- repeated details do not increase camera count;
- Geometry is `partial_approved`, not fully blocked and not complete;
- report exact missing opposite, side, rear, and high camera evidence.

### Semantic Derailment

Input: wheelchair references. Returned images: a “GEOMETRIC SHAPES” education poster and a “LIFE CYCLE OF A BUTTERFLY” infographic.

Required result:

- `subject_match: fail` with `subject_absent`/`infographic_semantics`;
- package/asset status `blocked_generation_semantic_mismatch`;
- audit prompt/reference transport before any retry;
- do not retry by adding more prompt adjectives.

## Diagnostic Boundaries

- Logo visible but unreadable: placement may be reference-locked; exact text remains blocked.
- Open/closed states shown but intermediate mechanics hidden: record endpoints; do not invent transition travel.
- Material colors conflict under different grades: separate observed rendered colors; do not infer base color without corroboration.
- Component closeup omits neighboring attachment: block the detail that would require invention.

## Package Contract Cases

Valid:

- complete v2 with six unique hard-authority cameras, required diagnostics, an approved five-or-fewer upload bundle, observed byte hashes/dimensions, and one 4K mapping per accepted asset;
- partial v2 with one exact source camera, five specifically blocked cameras, a one-asset upload recommendation, and matching 4K mapping;
- blocked v2 with no accepted asset, exact blockers, and no placeholders.

Invalid:

- v1 monolithic Geometry relabeled as v2;
- declared dimensions differ from decoded pixels;
- two accepted cameras share bytes or the same pose bin;
- bounded reconstruction claims hard authority;
- an unrelated poster passes subject QA;
- one camera claims approved multi-camera Geometry;
- upload bundle selects a non-approved asset;
- accepted asset lacks a one-to-one 4K mapping;
- source-gate-blocked camera or diagnostic is approved;
- complete package retains pending, continuation, QA, or repair state.
