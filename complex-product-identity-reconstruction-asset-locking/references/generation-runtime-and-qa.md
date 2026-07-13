# Generation Runtime And QA

Read this file before every built-in image-generation call and every post-generation inspection.

## Contents

1. Authority order
2. Prompt privacy and freeze
3. Independent board generation
4. Terminal-call state machine
5. Visual QA
6. Repair policy
7. Final-board generation

## 1. Authority Order

Use this order for every board:

1. frozen original reference bundle;
2. frozen Product Identity Specification and Part Tree;
3. board-specific evidence IDs and exclusions;
4. approved earlier boards only as secondary composition/detail support;
5. layout conventions.

Never let a generated board overwrite contradictory original evidence.

## 2. Prompt Privacy And Freeze

Compose one complete board-specific prompt immediately before the image call. Include product identity, board topology, required views/details, evidence exclusions, neutral appearance, and negative constraints.

Freeze its UTF-8/LF bytes and SHA-256. Record only `generation_prompt_sha256` in `asset_package_manifest.json`. Do not save the complete prompt in the deliverable package, print it in commentary, or publish it in the final response. Repair prompts are new attempts with new hashes and lineage.

This privacy rule does not apply to the user-requested external prompts in `08_4K_Upscale_Prompts.md`.

## 3. Independent Board Generation

Generate Geometry, Material, Component, State, and Marking boards as separate image calls. Do not generate a giant package sheet and crop it. Do not generate front, side, rear sequentially and use each output as the next identity source.

For each call, attach the same frozen original evidence needed by that board. If reference capacity is limited, prioritize identity-critical sources and record omitted evidence. Block the board when required evidence cannot be transported.

Use a clean light-gray or white seamless background, neutral soft studio light, controlled highlights, subtle grounding shadows, consistent product scale, and no environment narrative. Keep all non-product text out of pixels.

## 4. Terminal-Call State Machine

Use this sequence:

```text
planned
  -> generation_pending
  -> awaiting_post_generation_continuation
  -> qa_pending
  -> approved
      or repair_required -> generation_pending
      or blocked_generation_quality
```

Before the image call, persist:

- `terminal_generation_call: pending`;
- attempt number;
- source bundle hash;
- specification hash;
- private prompt hash;
- target asset path.

The built-in image call is the last action of that turn. On a later continuation, bind the exact returned asset, copy or reference it at the manifest path, record actual dimensions, set `terminal_generation_call: executed`, and inspect the pixels. A returned image means generation succeeded, not QA or package completion.

If the tool call fails, set `blocked_generation_runtime`; do not create an awaiting state. If the host does not auto-continue, the next user continuation resumes from the persisted manifest without requesting a new decision.

## 5. Visual QA

Inspect at original available resolution. Record `pass`, `fail`, or `not_applicable` for:

- `geometry_consistency`;
- `material_consistency`;
- `identity_consistency`.

Check every panel or detail window for:

- added, removed, duplicated, or fused parts;
- wrong component count or spacing;
- topology, attachment, hinge-axis, interface, cable, wheel, or support errors;
- silhouette or proportion drift;
- mirrored asymmetry, left/right swap, or wrong control side;
- deformation, impossible articulation, collision, or unsupported state;
- material reassignment, base-color drift, roughness/metalness/reflection drift, or texture-direction drift;
- logo, label, pattern, stitch, fastener, button, port, or marking drift;
- crop, overlap, inconsistent scale, missing required view, duplicate view, poster styling, props, people, or text pollution.

Compare across views as one 3D identity, not as isolated attractive panels.

## 6. Repair Policy

Diagnose the root cause and regenerate only the failed board. Keep approved boards unchanged unless the frozen source truth changes.

For repair:

1. cite the exact failed panel, part IDs, and failure flags;
2. strengthen only the relevant identity constraints;
3. reuse the frozen original sources and specification;
4. do not use the failed board as identity authority;
5. generate one replacement board;
6. rerun the entire board QA and affected cross-board checks.

Allow at most two repair attempts per board. After the limit, set `blocked_generation_quality`. Never hide rejected attempts by renaming the latest file as accepted without QA evidence.

## 7. Final-Board Generation

Generate the Final Product Identity Lock Board only after upstream gates pass. Use original sources as highest authority and approved boards as secondary support.

Minimum information density normally includes:

- one dominant front three-quarter or primary identity view;
- front and rear evidence;
- at least one side showing asymmetric controls/interfaces;
- one high-information component detail;
- one material/surface detail when relevant;
- one state pair when state is required;
- one marking detail when marking is required.

Remove any redundant view. Do not include a category merely because space is available. Use no titles, captions, arrows, labels, product names, or decorative poster elements.
