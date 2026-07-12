# Generation Unit Prompt Template

Compile one prompt per independent asset. Replace every bracketed token with a
frozen run value. Do not submit this template itself.

```text
Create exactly one horizontal 16:9 full-frame packaging product reference asset.
This is generation unit [ASSET_ID], view [VIEW_ID], for product state
[PRODUCT_STATE_ID]. Show exactly one [SHOT_SCALE] view of the single frozen
product identity. No contact sheet, collage, second product, title, legend,
caption, UI, watermark, poster, scene, prop, person, or non-product-native text.
Return exact horizontal 16:9 pixels at no less than 1280x720; do not satisfy
this request by resizing a smaller generated image after generation.

CAMERA LOCK
- Frozen view family: [VIEW_FAMILY].
- Review-board semantic role: [REVIEW_BOARD_ROLE].
- Coordinate frame: [PRODUCT_COORDINATE_FRAME]
- Camera pose: azimuth [AZIMUTH_DEG] degrees, elevation [ELEVATION_DEG]
  degrees, roll [ROLL_DEG] degrees.
- Lens profile: [LENS_PROFILE]. Camera-distance profile:
  [CAMERA_DISTANCE_PROFILE]. Product occupancy and center: [OCCUPANCY_LOCK].
- This view must remain geometrically between approved adjacent anchors
  [PREVIOUS_ANCHOR_ID] and [NEXT_ANCHOR_ID].
- Frozen framing contract: [FRAMING_CONTRACT].

IDENTITY AND STATE LOCK
- Source bundle hashes: [SOURCE_BUNDLE_HASHES].
- Geometry landmarks: [GEOMETRY_LANDMARK_CONTRACT].
- Surface atlas SHA-256: [SURFACE_TEXTURE_ATLAS_SHA256].
- Preserve component count, topology, silhouette, width/depth ratio, shoulder,
  side walls, seams, base, closure, pump/nozzle vector, fill level, internal
  component topology, embossing registration, material identity, and product
  state exactly as frozen.
- Visible surfaces: [VISIBLE_SURFACE_IDS]. Do not invent any unseen surface,
  hidden code, seam, mechanism, label continuation, or internal component.

EXACT-COPY BOUNDARY
- Exact-copy bundle SHA-256: [EXACT_COPY_BUNDLE_SHA256].
- Exact-copy bundle file SHA-256: [EXACT_COPY_BUNDLE_FILE_SHA256].
- Protected copy regions: [PROTECTED_COPY_REGION_IDS].
- Deterministic composition plan: [DETERMINISTIC_COMPOSITION_PLAN_ID].
- generation_text_policy: no_model_generated_product_copy.
- Do not generate, typeset, rewrite, translate, autocorrect, approximate, or
  hallucinate any packaging word, letter, number, punctuation, unit, logo,
  certification mark, barcode, QR code, batch code, or date.
- Render only the source-bound package substrate and the protected blank/masked
  copy surfaces required by the deterministic composition plan. Exact product
  copy is applied after generation from the frozen assets and is not your task.
- raw_generated_asset_publishable: false.
- raw_generated_asset_registry_eligible: false.

MATERIAL AND CONTINUITY LOCK
- Required material features: [MATERIAL_FEATURE_IDS].
- Preserve [MATERIAL_CONTRACT].
- Closure/nozzle orientation is fixed in product space, not screen space.
- For upright rotation, liquid volume and level stay constant and world-horizontal.
- Transparent opposite-side copy is a mirrored/refracted physical layer, never
  new direct front copy.

MACHINE-READABLE UNIT LOCKS
azimuth_deg: [AZIMUTH_FLOAT]
elevation_deg: [ELEVATION_FLOAT]
roll_deg: [ROLL_FLOAT]
shot_scale: [SHOT_SCALE]
view_family: [VIEW_FAMILY]
review_board_role: [REVIEW_BOARD_ROLE]
minimum_returned_pixel_dimensions: {"height":720,"width":1280}
post_generation_resize_allowed_to_meet_minimum: false
lens_profile: [LENS_PROFILE]
camera_distance_profile: [CAMERA_DISTANCE_PROFILE]
visible_surface_ids: [COMPACT_JSON_VISIBLE_SURFACE_IDS]
visible_component_ids: [COMPACT_JSON_VISIBLE_COMPONENT_IDS]
occluded_surface_ids: [COMPACT_JSON_OCCLUDED_SURFACE_IDS]
geometry_landmark_ids: [COMPACT_JSON_GEOMETRY_LANDMARK_IDS]
material_feature_ids: [COMPACT_JSON_MATERIAL_FEATURE_IDS]
source_reference_ids: [COMPACT_JSON_SOURCE_REFERENCE_IDS]
parent_anchor_view_ids: [COMPACT_JSON_PARENT_ANCHOR_VIEW_IDS]
previous_anchor_id: [JSON_STRING_OR_NULL]
next_anchor_id: [JSON_STRING_OR_NULL]
protected_copy_region_ids: [COMPACT_JSON_PROTECTED_REGION_IDS]
deterministic_composition_plan_id: [DETERMINISTIC_COMPOSITION_PLAN_ID]
material_lock: preserve source-bound material response
geometry_lock: preserve source-bound topology and proportions
exact_copy_bundle_sha256: [EXACT_COPY_BUNDLE_SHA256]
exact_copy_bundle_file_sha256: [EXACT_COPY_BUNDLE_FILE_SHA256]
coverage_matrix_sha256: [COVERAGE_MATRIX_SHA256]
surface_texture_atlas_sha256: [SURFACE_TEXTURE_ATLAS_SHA256]
source_manifest_sha256: [SOURCE_MANIFEST_SHA256]
protected_region_masks_sha256: [PROTECTED_REGION_MASKS_SHA256]
composition_plan_sha256: [COMPOSITION_PLAN_SHA256]
composition_view_status: [COMPOSITION_VIEW_STATUS]
composition_projection_model: [COMPOSITION_PROJECTION_MODEL]
composition_source_layer_ids: [COMPACT_JSON_COMPOSITION_SOURCE_LAYER_IDS]
ocr_field_ids_visible: [COMPACT_JSON_OCR_FIELD_IDS_VISIBLE]
code_ids_visible: [COMPACT_JSON_CODE_IDS_VISIBLE]
graphic_ids_visible: [COMPACT_JSON_GRAPHIC_IDS_VISIBLE]
dynamic_region_contract: [COMPACT_JSON_DYNAMIC_REGION_CONTRACT_OR_NULL]

REFERENCE PRIORITY
[RANKED_REFERENCE_IDS]

FORBIDDEN CHANGES
[FORBIDDEN_INVENTIONS]

Return one complete, uncropped, neutral studio reference asset for [ASSET_ID]
only. Product correctness, calibrated camera continuity, and protected exact-copy
regions outrank beauty or advertising polish.
```

## Compiler rules

- Use `python3 scripts/compile_generation_prompts.py <run_root>`; do not perform
  manual token substitution for production prompts.
- Refuse to compile unless `prompt_compilation_allowed` and
  `image_generation_allowed` are both true in the frozen run manifest.
- Bind the exact-copy bundle and coverage-matrix hashes in every unit.
- Bind all four required unit dependencies: semantic exact-copy bundle hash,
  exact-copy bundle file hash, coverage-matrix hash, and surface-atlas hash.
- Also bind the source-manifest, protected-mask, and composition-plan hashes.
- Require each compiled prompt to name numeric pose, shot scale, lens/distance,
  the exact 16:9 minimum returned-pixel contract and no-post-resize rule,
  frozen view family, semantic review-board role, framing contract, visible and
  occluded surfaces, source reference IDs, previous/next neighbors,
  parent anchors, geometry landmark IDs, material feature IDs, protected
  regions, any exact-copy dynamic-region pixel contract, and the per-view
  deterministic composition status/model.
- Keep the global identity core byte-identical across units. Only the view delta,
  visible surfaces, adjacent anchors, and unit-specific detail job may vary.
- The block above is explanatory parity with the compiler. Production bytes are
  always emitted by `compile_generation_prompts.py`; never manually substitute
  this template or treat it as a second schema.
- Do not put OCR text into the prompt as a substitute for deterministic artwork.
- Persist and hash the exact compiled bytes before disclosure and submission.
- Any changed dependency requires a new prompt revision and invalidates the old
  asset.
