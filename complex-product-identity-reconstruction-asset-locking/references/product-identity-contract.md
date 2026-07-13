# Product Identity Contract

Use this contract for Stage 1 evidence analysis and every board-source decision.

## Contents

1. Source normalization
2. Visual Product Identity Model
3. Product Part Tree
4. Material and surface decomposition
5. Marking identity
6. State Graph
7. Evidence statuses
8. Board eligibility

## 1. Source Normalization

Assign every input a stable source ID such as `S01`. Record:

- source path or conversation reference;
- original/official/manual/detail/screenshot role;
- whole product or crop;
- view and camera elevation;
- visible product state;
- suspected variant, revision, accessory, or mirror/flip;
- legibility and resolution limits;
- lighting/grade/environment contamination;
- conflicts with other sources.

Do not merge product variants because they look similar. Select one target identity or block.

## 2. Visual Product Identity Model

The model is the frozen set of source-evidenced product facts needed to reconstruct identity consistently. Record:

- product class and target variant;
- bounding silhouette and negative spaces;
- relative length/width/height and major proportional landmarks;
- frame, shell, support, base, and load-bearing relationships;
- primary/secondary component count;
- left/right asymmetry;
- repeated-part rhythm and spacing;
- visible interfaces and connection points;
- color regions, material regions, texture direction, and surface response;
- distinctive identity details;
- supported states and immutable features across states;
- unsafe or unknown zones that generation must not complete.

Use ratios and relative landmarks when physical measurements are unavailable. Do not invent dimensions.

## 3. Product Part Tree

Give every part a stable ID and record:

| Field | Meaning |
|---|---|
| `part_id` | Stable run-local identifier |
| `name` | Functional visual name, not guessed SKU terminology |
| `parent_part_id` | Parent assembly or `root` |
| `count` | Source-supported count or `unknown` |
| `side` | center, left, right, paired, radial, repeated, unknown |
| `attachment` | welded, bolted, screwed, clipped, hinged, slotted, sewn, molded, bonded, unknown |
| `detachable` | yes, no, unknown |
| `interface_location` | Relative product location |
| `material_id` | Linked material region |
| `identity_risk` | low, moderate, high, critical |
| `evidence_status` | One allowed evidence status |
| `source_ids` | Direct supporting sources |

Treat component count, connection topology, asymmetric controls, hinge axes, wheel/axle relationships, cable routing, and interface orientation as high-risk facts.

## 4. Material And Surface Decomposition

Separate intrinsic material from rendered appearance:

| Intrinsic | Photographic effect |
|---|---|
| base color | white balance / grade |
| roughness | highlight size from light source |
| metalness | environment reflections |
| transparency / opacity | background seen through material |
| texture direction / weave | moire / compression |
| coating / finish | bloom / glare |
| wear / patina | shadow / dirt from scene |

Record material boundaries and confidence. Preserve source-supported emissive screens or indicators as product state; remove only scene lighting contamination.

## 5. Marking Identity

For every logo, label, graphic, symbol, stitch path, control legend, or directional pattern, record:

- marking ID and type;
- host part;
- location and orientation;
- relative size and margins;
- color and contrast;
- exact readable text only when legible;
- source IDs and evidence status;
- exactness requirement.

Do not transcribe unreadable copy. Do not treat generative resemblance as exact typography, QR, barcode, certification mark, serial number, or legal copy.

## 6. State Graph

Represent each state as a node and each supported transition as an edge.

For a node, record component positions, locked/unlocked parts, detachable parts, persistent geometry, and sources. For an edge, record moving part IDs, axis or path only when observed, endpoints, intermediate evidence, and conflicts.

Only `Observed` and `Cross Validated` nodes may appear in a State Transition Asset Board. A familiar category behavior is insufficient evidence.

## 7. Evidence Statuses

- `Observed`: directly visible in one source.
- `Cross Validated`: independently supported by multiple sources or mutually consistent views.
- `Inferred`: plausible structural interpretation not directly shown.
- `Unknown`: insufficient evidence.
- `Conflicting`: sources disagree or identity/variant cannot be resolved.

Apply a status to atomic claims, not entire documents. A view may contain both observed and unknown zones.

## 8. Board Eligibility

Use board-scoped decisions:

| Board | Approval floor | Hard blockers |
|---|---|---|
| Geometry | Every required view and high-risk connection is Observed/Cross Validated or can be projected without inventing hidden topology | unknown rear/underside/internal topology, unresolved variant, component count conflict |
| Material | Material boundaries and identity-critical surface behavior are visible under usable evidence | strong contamination with no corroboration, unknown material assignment |
| Component | Every depicted node has clear orientation, attachment, scale, and neighboring parts | internal/hidden connection required, ambiguous mirrored side, unreadable interface |
| State | Every endpoint is Observed/Cross Validated and the transition does not require invented mechanics | inferred-only state, contradictory part travel, mixed product revisions |
| Marking | Placement and source-supported content are legible enough for the claimed exactness | unreadable copy, conflicting marks, generative-only exactness claim |

If an input set fails a board, preserve the blocked reason and continue only with independently eligible boards. A complete final package still requires Geometry and every board marked `required`.
