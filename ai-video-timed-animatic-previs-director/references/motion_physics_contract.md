# Motion And Physics Contract

This contract describes visible control intent, not engineering simulation.

## Shared Track Fields

Every motion track has:

- stable `track_id` and `motion_class`;
- affected Shot UIDs and generation-unit IDs;
- source basis and confidence;
- explicit assumptions;
- absolute V1 anchors and local V2 anchors;
- start state, path/behavior, contacts/collisions, and end state;
- whether the track is `required_for_generation`.

## Camera

Record position/orientation intent, height, lens/focal intent, primary move, path, speed/easing, focus behavior, start/end framing, occlusion, and cut boundary. Use one primary camera move per shot unless the Shot Contract explicitly approves a compound move.

## Subject Blocking

Record world/screen position, facing, eyeline, entry/exit, hand/prop contacts, body path, screen direction, and inter-subject spacing. Do not redefine face, body, wardrobe, or performance appearance.

## Rigid Object

Require pivot or free path, acceleration/easing, orientation, contacts, collision/occlusion surfaces, handoff, and end state. Product geometry remains owned by the product asset.

## Liquid

Require:

- `volume_continuity`;
- `viscosity_behavior`;
- `gravity_direction`;
- `wetting_adhesion`;
- `contact_surfaces`;
- `breakup_coalescence`;
- `state_at_cut`.

Preserve container fill level and transferred volume plausibly across cuts. Do not invent precise viscosity, surface tension, or flow-rate claims when evidence is absent; record a visual assumption and confidence.

## Cloth

Require:

- `anchor_points`;
- `drape_stiffness_intent`;
- `wind_acceleration`;
- `body_object_collisions`;
- `settling_behavior`;
- `state_at_cut`.

Wardrobe design and material appearance remain owned by the character/wardrobe assets.

## Hair

Require:

- `root_lock`;
- `inertia`;
- `gravity_wind`;
- `body_wardrobe_collisions`;
- `settling_behavior`;
- `state_at_cut`.

Hair identity, length, cut, texture, and color remain owned by the character asset.

## Failure Conditions

Reject a track that teleports matter, changes volume without cause, passes through a collision surface, switches screen direction unintentionally, changes a product mechanism, or encodes final look/identity as motion authority.
