# Scene Type Rules

Classify by spatial behavior, not by visual style. A scene may have one primary type and multiple secondary types. Use the primary type to choose the Spatial / Relational Master and coverage system; use secondary types to add only the evidence views they require.

## 1. Bounded Rigid Space

Examples: room, shop, factory, courtyard, cave, carriage, spacecraft interior.

Lock topology; wall/floor/ceiling relations; doors, windows, exits, fixed furniture, passages, occlusion, and high/low-angle reveals. Prefer main, reverse, left/right oblique, entrance-in, interior-out, elevated 3/4, low 3/4, and connection views. Use a plan, dollhouse, or elevated spatial master only when it increases relational evidence.

## 2. Architectural Exterior

Examples: standalone building, commercial exterior, factory, castle, tower, block, station, stadium, science-fiction architecture.

Lock massing, front/side/back relations, entrance, roads, ground contact, neighboring fixed structures, height ratios, top, base, and silhouettes at high/low angles. Cover front, sides, back, approach, departure, elevated, low, ground/road/landmark relationship, top, and base without inventing adjacent buildings.

## 3. Open Terrain And Landscape

Examples: valley, desert, coast, ice field, forest, grassland, canyon, volcano, planetary surface.

Lock terrain skeleton, horizon, ridges, rivers, roads, coastlines, landmarks, height relations, near/mid/far depth, and approach/departure directions. Cover main, reverse, lateral, high, low, arrival, departure, landmarks, horizon, and depth layers. Do not expand into an entire city, planet, or infinite terrain.

## 4. Fluid And Open Medium

Examples: ocean, underwater, cloud sea, upper atmosphere, liquid interior, giant gaseous environment.

Lock horizon or vertical axis, up/down relation, wave field, flow, depth strata, main cloud/fluid structures, stable anchors, medium boundary, density, and scale. Cover directions and layers that add spatial information; do not produce many near-identical water or sky plates.

## 5. Volumetric And Dynamic Environment

Examples: cloud, fog, smoke, fire, storm, dust, blizzard, waterfall, lava, nebula.

Lock volume morphology, density layers, dominant structure, flow, state boundary, semi-stable forms, and relation to terrain or enclosing space. Preserve identity-defining dynamics; do not force the scene into rigid geometry or erase the state during neutralization.

## 6. Astronomical And Cosmic System

Examples: planet, star, moon, galaxy, nebula, black hole, accretion disk, ring system, orbit system, deep space.

Lock subject identity, viewing inclination, relative celestial positions, multi-scale hierarchy, local structure, near/mid/deep-space layers, and intrinsic emission such as corona, jets, rings, or accretion disks. Use standard subject, inclination, side relation, detail, system-wide, scale, nearby-body, orbit/hierarchy, and defining-structure views. Do not apply ordinary front/back/left/right turns when they carry no spatial meaning.

## 7. Surreal Or Non-Euclidean Environment

Examples: infinite corridor, folded city, impossible architecture, dream space, gravity anomaly, abstract dimension.

Lock invariants, permitted transformation rules, connectivity, anchors, repetition, topology, and features the model must not "correct" into ordinary reality. The Spatial / Relational Master expresses rules, not a false Euclidean floor plan. Loop closure tests rule consistency rather than conventional geometry alone.

## Adaptive Coverage Decision

For every planned view, record `information_gain`. Reject a view when it is only a crop, focal-length change, or near duplicate. Require high/low coverage only when those angles can expose a structural or state error. Do not add people, vehicles, spacecraft, animals, boats, or other unapproved objects merely to communicate scale.
