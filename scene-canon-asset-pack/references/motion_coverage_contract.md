# Motion Envelope And Coverage Graph Contract

## Fixed Six-Node Profile

Use `scene_motion_six.v1`. The graph contains exactly six mandatory nodes and exactly one node per machine asset:

| Asset | Graph role | Default information job | Dependency stage |
| --- | --- | --- | --- |
| `CDM_001` | `source_aligned_diagnostic` | source identity, neutral appearance, primary landmark frame | 1 |
| `SRM_001` | `elevated_spatial_relation` | topology, upper boundaries, depth and connection relations | 2 |
| `COV_001` | `left_adjacent_continuity` | left reveal order, shared landmark overlap, lateral baseline | 3 |
| `COV_002` | `right_adjacent_continuity` | right reveal order, convergence against left path | 4 |
| `COV_003` | `motion_reveal` | low/elevated/path reveal selected by the supported envelope | 5 |
| `SCL_001` | `scale_landmark_depth` | scale, landmark spacing, near/mid/far depth relation | 6 |

Do not let one asset satisfy two roles. Do not replace a role with a crop, zoom, focal-length-only change, repeated camera tuple, or review-board tile.

## Motion Envelope

Freeze the motion envelope before prompt publication. Record:

- `profile_id: scene_motion_six.v1`;
- supported movement types;
- azimuth and elevation degree ranges;
- normalized translation bounds for x/y/z;
- supported path IDs;
- included reveal-region IDs;
- unsupported movement claims;
- backside truth status: `source_supported`, `canonical_completion`, or `outside_envelope`.

Use conservative values from evidence and the minimum-complete boundary. `digital_push_no_new_reveal` needs no translation evidence. `truck`, `crane`, `approach`, `departure`, and translated `orbit` require a non-zero normalized baseline and verified parallax. A rotational pan from one origin cannot stand in for translated coverage.

Do not claim a complete orbit unless the envelope covers a closed azimuth path and every revealed backside region is source-supported or frozen as canonical completion. Do not claim entrance traversal unless the connection and both sides of the boundary are in the canon.

## Node Contract

Every node records:

- unique `node_id`, `asset_id`, and one fixed graph role;
- normalized position `x/y/z`;
- `yaw_degrees`, `pitch_degrees`, `roll_degrees`;
- lens/FOV class and distance/framing class;
- non-empty visible landmark IDs;
- revealed and occluded region IDs;
- source evidence and canonical-completion IDs used by the view;
- adjacent node IDs;
- non-empty overlap invariant IDs;
- `mandatory: true`.

Camera tuples must be unique after normalization to four decimal places. Source evidence and canonical completion stay distinct; a generated view cannot upgrade completion to source truth.

## Edge Contract

Every edge records:

- unique `edge_id`, `from_node_id`, and `to_node_id`;
- movement type and direction;
- normalized translation baseline;
- whether parallax is expected and whether evidence is `verified` or `not_applicable`;
- ordered reveal-region IDs;
- handedness;
- non-empty overlap invariant IDs;
- one or more path IDs.

Every edge endpoint must exist and must be declared adjacent in both nodes. Any edge with a translational movement type requires `translation_baseline_normalized > 0`, `parallax_expected: true`, and `parallax_evidence_status: verified` at delivery. Rotational or digital-only edges use `not_applicable` only when no new spatial reveal is claimed.

## Path And Loop Closure

Every supported path contains at least two connected nodes and all of its edges. Every node belongs to at least one path. Include at least one loop with three or more unique nodes, corresponding edge IDs, one or more closure landmarks, and `convergence_status: verified`.

Loop closure compares landmark count/order, left/right relation, connection position, topology, scale, material identity, intrinsic state, and completion stability from both directions. A declared loop that is open, unverified, or missing an edge fails delivery.

## Scene-Type Adaptation

Keep the six roles but adapt their camera semantics:

- Bounded rigid space: left/right, upper/lower boundaries, connections, and depth.
- Architectural exterior: facade-side-back relation only inside the envelope, ground contact, top/base, and approach.
- Open terrain: lateral/reverse relation, horizon, ridge/road/coast order, and near/mid/far depth.
- Fluid/volumetric: stable anchors, flow direction, density layers, medium boundary, and scale.
- Cosmic: inclination, nearby-body relation, system hierarchy, and defining emission; do not invent meaningless front/back turns.
- Non-Euclidean: invariants, permitted transformations, connectivity, and rule-consistent loop closure.

Unsupported motion remains explicit. Six nodes are a bounded continuity package, not a universal 3D reconstruction.
