# Camera and Prompt Contract

## Coordinate frame

Freeze one right-handed subject-local coordinate frame before naming anatomical views:

- origin: subject root or declared scene pivot;
- `+X`: subject right;
- `+Y`: subject forward;
- `+Z`: opposite gravity;
- `0°`: camera in front of the subject on `+Y`, looking at the pivot;
- `+90°`: camera on subject right `+X`;
- `180°`: camera behind the subject on `-Y`;
- `-90°` or `270°`: camera on subject left `-X`.

Use `azimuth_basis: subject_forward` only when subject forward is `observed`, `source_corroborated`, or `approved_canon`. Otherwise use `source_camera_relative` and name views relative to the source camera, not anatomical front/back.

Normalize angles with `((angle % 360) + 360) % 360`. Use circular difference `abs(((a - b + 180) % 360) - 180)`.

## Camera-family invariant

Every family records:

- family ID and `master` or `portrait` kind;
- coordinate-frame, Moment Canon, and lighting Canon hashes;
- projection and sensor/FOV or focal policy;
- orbit radius, elevation, derived height, look-at, and roll;
- focus target, aperture intent, exposure/white-balance intent;
- shot scale, framing, crop, aspect ratio, and subject-scale policy;
- `varying_fields`, normally exactly `["azimuth_deg"]`.

If focal length and sensor width are both known, derive horizontal FOV and require agreement within `0.05°`. Treat unknown optics as ranges or policies, never exact recovered measurements.

Create a new family when radius, height/elevation, focal/FOV, roll, look-at, focus, shot scale, framing, or crop policy changes. Portrait views never fill missing master-ring bins.

## Coverage profiles

### Targeted views

- one to three required views;
- arbitrary angles;
- `full_coverage_claim` must be false;
- micro coverage under 12° separation requires `micro_coverage: true` and expected parallax regions.

### Minimum ring

- one family;
- exactly four required views;
- bins `0`, `90`, `180`, `270`;
- each required angle must fall within `±3°` of exactly one bin;
- optional views do not fill bins.

### Robust ring

- one family;
- exactly eight required views;
- bins `0`, `45`, `90`, `135`, `180`, `225`, `270`, `315`;
- the same `±3°` bin and optional-view rules.

Tuple duplicates are exact canonical tuples. Flag angles within `1°` as angular duplicates and same-family angles under `12°` as near duplicates unless valid micro coverage is declared.

## Visibility and physical consistency

Each view declares:

- `must_remain_visible`;
- `expected_visible`;
- `expected_occluded`;
- `newly_revealed` with evidence class;
- `persistent_occluders`;
- `forbidden_reveals`;
- `face_visibility_goal`;
- common anchors with adjacent views.

Do not ask the subject to turn, look at the camera, move a hand, or reveal a face to satisfy a camera target. Use `natural_from_frozen_pose` when head/gaze vectors are unknown. When approved head/gaze vectors exist, reject a full-face request over `15°` yaw or `10°` pitch from the frozen head direction, and reject eye-contact over `5°` from the frozen gaze vector.

Lock light sources in world space. A key that is camera-left in one view may move screen-right in another. Never rewrite it as camera-relative beauty lighting.

## Complete prompt compilation

Compile every view into an independently usable prompt in this order:

1. state that this is the same frozen moment and only declared camera variables may change;
2. list ordered references and exact role scopes;
3. freeze identity, body, pose, head, expression, gaze, wardrobe, asymmetry, contacts, and props;
4. freeze scene topology, temporal state, and world-space lights;
5. state the family and target camera tuple;
6. state expected occlusion, reveal, and common anchors;
7. state evidence status of hidden regions and the uncertainty policy;
8. state optics, focus, depth, palette, texture, and grain intent;
9. prohibit mirror, crop/zoom substitute, subject rotation, pose change, relighting, scene relayout, unsupported salient additions, and commercial retouching.

Store exact UTF-8/LF bytes without BOM. Hash the complete prompt. A prompt path or hash without the complete visible body does not satisfy prompt-first publication.

Deliver a complete Chinese prompt for every view. An English equivalent is optional; when present, bind its own hash and require semantic equivalence rather than literal translation.

The built-in attempt prompt and portable master-regeneration prompt may differ only in explicitly recorded handoff wording. Do not invent unavailable controls, seeds, dimensions, weights, or model identity.

## Prompt-first receipts

For image input, publish the complete required-view prompt set and reference-plan hashes before the first worker.

For text generation, use two receipts:

1. `moment_anchor`: V00 prompt before the anchor worker;
2. `coverage`: all required coverage prompts after the V00 image and inspection are accepted, and before the first coverage worker.

Prompt-only requires zero worker spawns and zero image calls.

Each receipt records the phase, input mode, parent task/thread evidence when observable, publication event/order, required-view-set hash, prompt document path/hash, published prompt IDs/hashes, reference-plan hashes, and first worker event/order. Before coverage compilation, persist exact anchor-phase manifest, publication receipt, and prompt-document snapshots. The coverage manifest binds all three paths and hashes, and every validation replays the V00 attempt lineage. The text coverage receipt additionally binds the accepted anchor image and inspection hashes.
