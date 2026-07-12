# Continuity And Promotion Rules

## Authority Boundaries

The keyframe pack may realize but never redefine:

- narrative function, advertising function, shot order, and timing from the Shot Contract;
- identity, wardrobe, product geometry, label evidence, material construction, and scene canon from asset owners;
- global lighting/color/texture from the Global Look owner;
- framing and representative moment from the modular storyboard;
- motion timing and rough blocking from V1 Timing Animatic.

If a requested keyframe would require changing one of these, emit an upstream change request and leave the affected shot stale or blocked.

## Anchor Selection

A primary anchor is the generation-ready visual statement of the shot's most control-critical state. It need not be the chronological first or last moment.

Additional anchors are justified only when at least one property changes materially:

- identity-readable facial or body pose;
- hand-object contact;
- product orientation, opening, dispensing, or visible state;
- liquid/material topology;
- camera-relative blocking or screen direction;
- generation-unit boundary state.

## Storyboard Promotion Gate

All gates must pass:

1. independent source file, not a grid crop;
2. exact `shot_uid` ownership;
3. final approved storyboard version;
4. generation-ready identity and wardrobe fidelity;
5. generation-ready product geometry/material/label fidelity;
6. correct scene and Global Look version;
7. correct composition, camera, placement, pose, screen direction, and time state;
8. actual dimensions and binary hash recorded;
9. later visual inspection passed;
10. no shot number, duration, editorial caption, arrow, grid line, gutter, UI, watermark, or other storyboard annotation; intrinsic packaging/product/in-world text is allowed only when every source is an exact downstream-eligible Canon authority required by the promoted keyframe;
11. no unsupported completion or conflicting source evidence;
12. promotion evidence persisted.

Persist these exact ordered evidence IDs so the validator can distinguish twelve real checks from twelve arbitrary strings:

`independent_source_file`, `exact_shot_uid_owner`, `final_approved_storyboard_version`, `identity_wardrobe_fidelity`, `product_geometry_material_label_fidelity`, `scene_global_look_match`, `composition_action_time_match`, `dimensions_binary_hash_verified`, `later_visual_inspection_passed`, `no_storyboard_annotation_intrinsic_text_source_bound`, `no_unsupported_completion_or_conflict`, `promotion_evidence_persisted`.

Failing any gate forces an independent keyframe generation.

The intrinsic-text gate proves source provenance, not OCR accuracy. It never authorizes guessed copy, logo reconstruction, claims, certifications, QR codes, or barcodes.

## Cross-Unit Continuity

At each generation-unit boundary, freeze the outgoing and incoming states for:

- each controlled character;
- each controlled product/prop;
- material state and motion direction;
- screen direction and spatial placement;
- scene state and Global Look state.

A boundary record does not instruct a provider to use endpoint frames. It is evidence consumed by Control Previs V2 and the prompt compiler.

A keyframe or promoted storyboard frame is an ordinary Omni R2V image
reference, never a standalone/classic single-image-to-video route. The latter
is forbidden; the former remains valid continuity evidence.

## Material State Rules

- Preserve source-supported material geometry and optical response.
- Use conservative physical inference only when no visual contradiction exists.
- Track fill level, meniscus, droplet/stream topology, wetting footprint, refraction edges, and highlight direction when relevant.
- Keep intrinsic material state separate from Global Look illumination.
- Never infer hidden mechanisms from a visible result.

## Invalidation Matrix

| Changed owner | Directly stale here | Downstream stale |
|---|---|---|
| Shot Contract | affected shot records | Storyboard-dependent anchors, V2, prompts |
| Storyboard | affected shot anchors | V1/V2 bindings, prompts |
| Canon asset | dependent anchors/ledgers | V2 appearance bindings, prompts |
| Global Look Core | all look-applied anchors | V2 appearance bindings, prompts |
| Shot Look Delta | affected anchors | affected prompts |
| V1 timing | dynamic ladders/boundary anchors | V2, prompts |
| Keyframe | none upstream | V2 appearance bindings, prompts |

Unaffected files remain byte-identical.
