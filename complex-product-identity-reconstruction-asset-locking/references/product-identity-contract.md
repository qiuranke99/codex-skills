# Product Identity And Camera Evidence Contract

Use this contract for Stage 1 identity analysis, every camera decision, and every diagnostic source gate.

## 1. Source Normalization

Assign stable IDs such as `S01`. Record:

- path or conversation reference and byte hash when local;
- original photo, official image, manual, detail, screenshot, verified 3D/CAD, or render role;
- whole product or crop;
- observed azimuth/elevation and shot completeness;
- product state;
- variant, revision, accessory, or mirror/flip risk;
- resolution/legibility limits;
- lighting, grade, reflection, and environment contamination;
- conflicts with other sources.

Do not merge similar variants. A mislabeled filename does not override the pixels. Select one target identity or block.

## 2. Visual Product Identity Model

Freeze only source-evidenced facts needed for continuity:

- bounding silhouette and negative spaces;
- relative length, width, height, and proportional landmarks;
- frame, shell, support, base, and load-bearing relationships;
- primary/secondary part counts;
- left/right asymmetry;
- repeated-part rhythm and spacing;
- interfaces, connection points, and cable paths;
- color/material regions, texture direction, and surface response;
- distinctive identity details and markings;
- supported states and immutable features across states;
- unknown zones generation must not complete.

Use ratios when measurements are absent. Do not invent dimensions or engineering performance.

## 3. Product Part Tree

For every identity-relevant part record:

| Field | Meaning |
|---|---|
| `part_id` | Stable run-local ID |
| `name` | Functional visual name; do not guess a SKU term |
| `parent_part_id` | Parent assembly or `root` |
| `count` | Source-supported count or `unknown` |
| `side` | center, left, right, paired, radial, repeated, unknown |
| `attachment` | observed attachment or `unknown` |
| `detachable` | yes, no, unknown |
| `interface_location` | Relative product location |
| `material_id` | Linked material region |
| `identity_risk` | low, moderate, high, critical |
| `evidence_status` | One allowed evidence status |
| `source_ids` | Direct supporting sources |

Counts, connection topology, asymmetric controls, hinge axes, wheel/axle relationships, cable routing, and interface orientation are high-risk facts.

## 4. Critical Node Ledger

A Critical Node is a part or relationship whose drift changes product identity even when the overall silhouette still looks plausible.

Record:

- node ID and linked part IDs;
- relationship, attachment, count, and orientation;
- left/right or state dependency;
- expected visibility/occlusion by camera;
- evidence status and source IDs;
- explicit rejection conditions.

For wheelchairs, strollers, bicycles, and similar mobility products, test all applicable nodes:

1. rear wheel, hub, axle, handrim, spoke/rim system;
2. front caster, fork, axle, suspension, and frame interface;
3. primary frame rails, cross-brace, supports, hinges, and anti-tip structure;
4. seat, back, arm, side guard, leg rest, footplate, and attachment geometry;
5. brake, control, handle, battery/module, cable, or actuator side;
6. wheelbase, track, seat height, and proportional landmarks;
7. folding/deployment nodes and immutable geometry across supported states.

Equivalent product-specific nodes are mandatory for robots, camera rigs, machines, furniture, and electronics. Do not reduce the ledger to category names; name visible relationships and failure conditions.

## 5. Material And Surface Decomposition

Separate intrinsic material from photographic appearance:

| Intrinsic | Photographic effect |
|---|---|
| base color | white balance / grade |
| roughness | light-source highlight size |
| metalness | environment reflections |
| transparency / opacity | background through material |
| texture direction / weave | moire / compression |
| coating / finish | bloom / glare |
| wear / patina | scene shadow / dirt |

Record boundaries and confidence. Preserve source-supported indicators as state; remove only scene contamination.

## 6. Marking Identity

For every logo, label, graphic, symbol, stitch path, control legend, or directional pattern record host part, location, orientation, relative size, color, readable text, exactness requirement, evidence status, and source IDs.

Do not transcribe unreadable copy. A generative resemblance is not exact typography, barcode, certification, serial, or legal-copy evidence.

## 7. State Graph

Record each state node's component positions, locked parts, detachable parts, persistent geometry, and sources. Record a transition edge's moving parts, axis/path only when observed, endpoints, intermediate evidence, and conflicts.

Only `Observed` and `Cross Validated` states may become identity truth. Familiar product behavior is insufficient.

## 8. Evidence Statuses

- `Observed`: directly visible in one source.
- `Cross Validated`: independently supported by multiple mutually consistent sources/views.
- `Inferred`: plausible structural interpretation not directly shown.
- `Unknown`: insufficient evidence.
- `Conflicting`: sources disagree or identity cannot be resolved.

Apply statuses to atomic claims. One source can contain both observed and unknown zones.

## 9. View Evidence Matrix

For every source view record:

- observed azimuth/elevation and whole-product completeness;
- directly visible Critical Nodes;
- occluded/high-risk unknown zones;
- state and side;
- source resolution and confidence;
- closest target camera bin;
- whether exact source bytes are reusable.

The matrix prevents three different crops of one source angle from being counted as three cameras.

## 10. Per-Camera Evidence Modes

| Mode | Meaning | Identity authority | Required proof |
|---|---|---|---|
| `source_copy` | Exact reusable source bytes | hard | asset hash equals frozen source hash; complete product and pose verified |
| `verified_source_render` | Deterministic render from a verified existing 3D/CAD source | hard | model/source provenance, render recipe, camera role, observed output hash |
| `source_aligned_generation` | Same-pose neutralization or cleanup | auxiliary | original references, prompt hash, same-camera QA, source comparison |
| `bounded_reconstruction` | Candidate novel view | auxiliary | cross-validated visible topology, prompt hash, explicit unknown-zone exclusions |
| `blocked` | View requires unsupported identity completion | none | exact missing capture/render/evidence request |

Neither generative mode can establish hidden topology or count toward hard-authority coverage. If a renderer is unavailable, a 3D filename alone is not a verified render.

## 11. Camera Eligibility And Coverage

Approve each target independently. Require:

- one unique azimuth/elevation/shot-size bin;
- complete, uncropped product;
- source gate for every Critical Node expected in that view;
- exact source IDs and evidence mode;
- a unique coverage contribution;
- no unresolved variant conflict.

Block only the target whose visible topology would be invented. Do not block direct front coverage because the underside is unknown.

Hard multi-camera coverage requires at least four accepted hard-authority targets, at least four unique pose bins, front/rear/side sector coverage, and zero byte/pose duplication. `full` requires every frozen target.

## 12. Diagnostic Eligibility

| Diagnostic | Approve when | Block when |
|---|---|---|
| Material | material boundaries and identity-critical response are usable | assignment/grade conflict is unresolved |
| Component | depicted node orientation, attachment, scale, and neighbors are visible | hidden connection or mirrored side would be invented |
| State | endpoints and necessary mechanics are Observed/Cross Validated | inferred-only state or contradictory travel |
| Marking | placement/content are legible enough for claimed exactness | unreadable/conflicting/generative-only copy |

A diagnostic board can pass independently but cannot increase camera coverage. A complete package still requires hard multi-camera Geometry and every diagnostic marked `required`.
