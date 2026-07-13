# Packaging Asset Pack Contract v3

This reference is normative. It defines the artifacts validated by
`scripts/validate_packaging_run.py` and the evidence required before exact-copy
or rotation-ready claims.

## 1. Contract boundary

The pack has three different kinds of artifacts:

1. **Source evidence**: original photos, artwork, dielines, CAD, text masters,
   decoded payloads, approved crops, and their hashes.
2. **Machine masters**: one independently generated or deterministically
   composed product view or detail per file. These are the downstream reference
   assets.
3. **Review boards**: deterministic layouts of approved masters. They are for
   human review and indexing; they are not generation truth.

Never promote a review board, a crop of a generated contact sheet, or a
generated view into source evidence.

## 2. Source authority

Use field-specific authority rather than one global ranking:

- SKU-static text: approved artwork/dieline > authoritative text/PIM table >
  direct high-resolution orthographic photo with review > multi-view OCR
  consensus > single oblique photo.
- Batch/date/lot: direct photographed-instance evidence outranks generic SKU
  artwork.
- Logos and marks: master asset > approved orthographic crop. OCR has no
  authority over graphic shape.
- Hidden geometry: CAD/turntable/photogrammetry > direct photos > bounded
  interpolation. A generated guess has no source authority.
- A generated file or prior failed asset always has
  `source_authority: prohibited`.

Every direct photograph also binds one canonical `view_id`, finite
`azimuth_deg`/`elevation_deg`, and the exact canonical `visible_surfaces` for
that camera pose. A front source cannot simultaneously claim the back surface,
and a three-quarter source cannot be relabeled as a direct side/top/bottom
anchor. Parent-anchor IDs in generated views resolve to an actually attached
source whose `view_id` matches that anchor; prompt prose cannot invent the
binding.

Conflicting equal-authority variants block. Do not silently vote or merge.

`source_manifest.product_feature_classification` covers the complete canonical
taxonomy. Every row is either
`present` or `reviewed_absent` and carries source IDs, a named reviewer, and an
evidence note; the run manifest stores exactly the present subset. Minimum
rotation is validator-derived: R8 only for reviewed simple near-rotational,
low-copy products; otherwise R12; transparent/liquid/pump/wrap/reflective/flat
or asymmetric material risk raises to R16; macro rotation, complex reflection,
or continuous wrap copy raises to R24. A missing classification row cannot
silently lower either view coverage or continuity gates.

## 3. Whole-product OCR contract

### Surface topology

Use exactly six camera-facing coordinate surfaces (`front`, `right`, `back`,
`left`, `top`, `bottom`) for view topology. Closure, collar, shoulder, base
edge, mold seam, embossing, batch stamp, labels, codes, and other localized
features are frozen component IDs, physical-layer IDs, or region IDs anchored
to one of those six surfaces. This separation prevents a camera-pose validator
from treating a pump collar as if it were a seventh face while still requiring
every localized packaging feature to be inventoried and reviewed.

Every coordinate surface uses one closed text state only:

```text
text_detected | verified_no_copy | decorative_graphic | occluded | needs_source
```

`occluded` and `needs_source` block a production-ready exact-copy run. Unknown
or convenience statuses such as `expected_copy` are invalid.

### Discovery pass

Run OCR on every complete original image before any region crop. This prevents
small batch codes, base printing, closure marks, embossing, or unexpected copy
from disappearing outside a label-only crop.

Each source record must contain:

```json
{
  "source_id": "SRC_FRONT",
  "whole_product_ocr_passes": [
    {
      "pass_id": "SRC_FRONT_FULL_01",
      "engine_id": "macos_vision",
      "engine_version": "observed-runtime-version",
      "preflight_adapter_path": "scripts/run_ocr_preflight.py",
      "preflight_adapter_sha256": "...",
      "engine_adapter_path": "scripts/macos_vision_ocr.swift",
      "engine_adapter_sha256": "...",
      "language_set": ["zh-Hans", "en-US"],
      "uses_language_correction": false,
      "source_sha256": "...",
      "observation_count": 1
    }
  ]
}
```

The ledger itself carries `ledger_semantic_sha256`, computed over canonical
JSON with that field omitted. Top-level engine/version/language/adapter locks
must exactly match every whole-product pass. V3 source discovery and region
OCR trust only the installed bundled macOS Vision route or the live hash of
the selected Tesseract executable; a named-but-unbound OCR engine is not
evidence. This portability does not extend to final-master code verification:
the v3 post-composite adapter uses bundled macOS Vision for combined text plus
barcode/QR detection. Non-Darwin production must either schedule that frozen
run for final verification on a compatible Mac or fail the capability gate
before generation.

Zero detections require an explicit reviewed status; they do not prove that the
surface contains no copy.

Before generation, every OCR record's file path, file hash, and decoded
dimensions must match the source manifest. Pass IDs and observation IDs are
unique, declared observation counts equal the actual arrays, and
`ocr_review_status` is `reviewed`; pending output is discovery evidence only.

Every detection also has a reviewed disposition: `mapped_to_field`,
`duplicate_showthrough`, `decorative_non_product_copy`, or `false_positive`.
`unresolved`, a missing reviewer, or a one-way mapping that is not reciprocally
bound by Text SSOT blocks exact-copy generation. A bare `verified_no_copy`
surface is invalid without named review evidence.

### Region pass

Every detected or expected text, code, native-graphic, or mixed evidence area
receives a stable `region_id`, source polygon, rectified crop, crop hash,
`surface_id`, `physical_layer_id`, `visibility_mode`, and `region_purpose`:

```text
text | code | graphic | mixed
```

The region crop pass is always created so source provenance can be replayed.
Text detection is a separate purpose-specific gate: `text` and `mixed` regions
require at least one accurate region OCR detection. `code`-only and
`graphic`-only regions may legally produce zero OCR text; their crop receipt
may still be valid, but production remains blocked until the code decode or
graphic disposition is reciprocally mapped, reviewed, and signed by a named
reviewer. Zero detections never establish `verified_no_copy`.

`scripts/run_region_ocr.py` implements hash-bound axis-aligned source crops.
Each pass binds source ID/hash, region-spec path/hash, normalized box and
coordinate origin, surface, physical layer, visibility, purpose, installed
rectifier hash, crop-receipt file/self hashes, and the final crop hash. The
same four authority fields must match byte-locked v2 spec, ledger pass, and v2
adapter receipt. The validator repeats the crop from the locked source and
compares decoded pixels; an arbitrary same-size crop is not evidence.
V3 deliberately does not authorize a separately supplied rectifier.
Perspective, cylindrical, mesh, or depth-aware source geometry requires a new
authoritative orthographic source or a later contract version with its own
bundled deterministic replay. Unsupported geometry blocks.

Allowed visibility modes:

```text
direct
oblique
mirrored_showthrough
refracted
reflected
occluded
```

Only `direct` or reviewed `oblique` evidence can independently authorize exact
copy. Show-through observations must point to the direct region they echo.

### Normalization

Default exact-copy normalization:

```text
Unicode: NFC only
letters: preserve
numbers: preserve
punctuation: preserve
units: preserve
capitalization: preserve
language order: preserve
line order: preserve
autocorrect: forbidden
```

Whitespace or line-break normalization is legal only when explicitly declared
for a field and cannot change semantic order.

Final-master OCR uses one of two field-level match policies:

```text
single_observation_exact
ordered_line_aggregation_exact
```

Every Text SSOT field declares `ocr_match_policy` and `line_joiner`. A single
observation requires `line_joiner: none`. An ordered aggregation uses only raw
Vision observations from one hash-bound projected-region crop. The bundled
adapter orders geometric lines top-to-bottom and fragments on the same line
left-to-right. Two vertical centers are considered the same line only when
their distance is at most `max(0.0025, 0.35 * max(fragment heights))`. Fragments
within a line use one literal U+0020; `line_joiner: newline | space | none`
controls only the boundary between geometric lines. The resulting UTF-8 bytes
must hash exactly to `expected_text_sha256`.

Successfully aggregated raw fragments remain in `raw_scan_observations` and
bind the aggregate observation ID. They are not counted again as extra
pseudo-copy. Any unconsumed fragment, second spatial occurrence, ambiguous
aggregate, invalid bounding box, or non-exact aggregate remains unresolved.
No language-model correction, semantic reconstruction, punctuation repair, or
Unicode rewrite is permitted during this aggregation.

### Text SSOT

Every exact field must include:

```text
field_id
region_id
surface_id
semantic_role
volatility: static | batch_variable | date_variable
expected_raw_text
expected_text_sha256
ocr_match_policy: single_observation_exact | ordered_line_aggregation_exact
line_joiner: newline | space | none
authority_source_ids
ocr_observation_ids
engine_consensus_status
human_review_status
verification_basis
authority_asset_path
authority_asset_sha256
field_status: verified | conflict | unreadable | needs_source
render_policy
required_view_ids
```

For `exact_copy_mode: all_visible_product_native_copy`, every visible
product-native character is exact. `C_texture` is invalid.

Authority source IDs must be a non-empty source-manifest subset. OCR observation
IDs must resolve to region observations on the same region and authority source.
Surface-inventory `required_copy_field_ids` and Text SSOT fields are an exact
two-way match. Verification requires an exact OCR match or a reviewed,
hash-locked source crop/artwork master.

Authority bytes also need derivation provenance. For
`ocr_exact_match`/`authoritative_source_crop_reviewed`, the authority asset path
and hash must be exactly the rectified crop named by the source/region crop
receipt. For `approved_artwork_text_master`, the bytes must exactly equal a
source-manifest entry whose `source_kind` is `approved_artwork`, `dieline`, or
`authoritative_text_master`. Coordinating hashes around an unrelated or
re-typeset image does not create authority. Printed code and native-graphic
assets follow the same crop-or-approved-master rule.

## 4. Transparent packaging layer contract

Transparent packaging must not collapse copy, liquid, internal components, and
the opposite wall into one texture. Use stable physical layers such as:

```text
front_print_outer
front_label_opaque
front_embossing
front_wall
internal_content
internal_components
rear_wall
rear_print_outer
rear_label_or_compliance_block
```

The surface inventory records direct and show-through observations separately.
A rear field visible through the front remains one rear `field_id`. Its screen
appearance may be mirrored, attenuated, and refracted, but its authority remains
the direct rear source.

## 5. Codes and native graphics

### Barcode

Require symbology, expected payload, checksum result, printed-symbol asset hash,
and at least one successful final-artifact decode. A visually barcode-like
pattern is not evidence.

### QR

Record raw payload bytes separately from printed module geometry. Matching
payload does not prove a source-identical printed symbol.

A code-only region does not need a text OCR detection. It does need a decoded
source observation whose disposition is reciprocally mapped to the manifest
code, payload/checksum match, and named human review; otherwise the region is
only a replayed crop, not exact-copy code authority.

### Logos, certifications, and handling marks

Bind a master asset or approved source crop and SHA-256. Approve with
deterministic composition plus a reproducible region comparison. OCR output
cannot approve these graphics.

A graphic-only region may contain zero OCR text, but every required graphic
record needs a `mapped_to_graphic` disposition that reciprocally names the
manifest graphic, `review_status: reviewed`, a non-empty `reviewer_id`, and an
evidence note. A valid crop receipt alone does not approve graphic identity.

The post-composite adapter must generate the graphic comparison receipt itself;
it must not trust a supplied `deterministic_similarity: 1.0`. The receipt binds
the installed adapter path/hash, composition job path/hash, composition receipt
path/hash, unique graphic layer ID, source graphic hash, projection model,
destination box/quad, mask path/hash, and byte-identical final compositor
replay. `deterministic_similarity: 1.0` means that exact locked composition
replayed to the final asset bytes; it is not a generative visual-similarity
judgment.

## 6. Exact-copy bundle and generation gate

The exact-copy bundle contains the frozen text SSOT, code manifest,
logo/graphic manifest, texture atlas, protected masks, composition plan, and
their source locks. Hash canonical JSON with UTF-8, sorted keys, no NaN, and
compact separators.

`exact_copy_bundle_manifest.json` contains:

```text
schema_version: packaging-exact-copy-bundle.v1
exact_copy_mode
text_ssot_sha256
code_manifest_sha256
logo_graphic_manifest_sha256
surface_texture_atlas_sha256
protected_region_masks_sha256
deterministic_composition_plan_sha256
exact_copy_bundle_sha256
freeze_status: frozen
```

The bundle hash is calculated over the manifest with
`exact_copy_bundle_sha256` omitted.

No prompt may be compiled until all gate fields are true. In exact-copy mode,
capability failure blocks. A geometry-only preview is a separate user-authorized
mode with blank/masked copy regions and no production authority.

## 7. Coordinate, coverage, and motion graph

The product coordinate frame defines front, right, up, azimuth direction,
elevation, and one immutable `product_state_id`.

Every view row contains:

```text
view_id
family: neutral_ring | high_angle | low_angle | top_bottom | detail
azimuth_deg
elevation_deg
roll_deg
shot_scale
lens_profile
camera_distance_profile
product_state_id
visible_surface_ids
visible_component_ids
occluded_surface_ids
geometry_landmark_ids
label_region_ids
ocr_field_ids_visible
code_ids_visible
graphic_ids_visible
material_feature_ids
pose_source_status
surface_source_status
copy_source_status
material_source_status
derivation_status
source_refs
parent_anchor_view_ids
previous_view_id
next_view_id
required
production_authority
```

`identity_lock.geometry_landmark_contract` freezes both
`required_landmark_ids` and `component_ids`;
`identity_lock.material_contract` freezes `material_feature_ids`. Every view
references only those inventories. Every source declares its visible component
IDs. Generated views may use only the union of their direct parents' surfaces,
components, landmarks, materials, fields, codes, and graphics. Detail target
components and evidence IDs must resolve to these frozen inventories or the
exact-copy manifests; arbitrary `EVIDENCE_*` strings have no authority.

The neutral ring must contain every ID in the selected R profile and a closed
edge from the final view to the first. Duplicate numeric poses do not satisfy
different IDs.

Eight bridge masters are always required: `UPPER_0000/0900/1800/2700` use
`upper_half_close`, and `LOWER_0000/0900/1800/2700` use
`lower_half_close`. Their family, pose, target surface, framing, semantic board
role, and source-inference rules come from `view_coverage_profiles.json` and
are validator-enforced.

Every source reference resolves to the source manifest. A source-verified
surface claim requires those source records to cover all visible surfaces. A
`derivation_status: source` full-product view additionally requires at least
one attached source with the identical canonical view ID, numeric pose, and
visible-surface set. High/low interpolation from a cardinal plus top/bottom
source is still `generated` with two source-verified parents; it cannot call
itself a photographed high/low master. A
full pitched orbit declares an `elevation_rings` entry whose view IDs exactly
follow the selected R profile; each elevation ring has its own adjacency and
loop closure.

Motion envelopes list required view and edge IDs. Any evidence dimension set to
`needs_source` blocks that required production view. Generated views require
at least two unique source-verified parent anchors and cannot first expose a
surface, field, code, graphic, or mechanism absent from their parents. The
validator derives expected surfaces from azimuth/elevation, so a 180-degree
view cannot claim the front surface and a true top/bottom cannot reuse a front
row. Full 360 authority requires a closed path without missing authority.

V3 IDs permit at most one dynamic `HIGH` ring and one dynamic `LOW` ring. Two
rings with the same prefix would collide and therefore fail closed.

V3 detail masters are generated/inferred units with at least two direct
full-product anchors, then exact copy is composed deterministically. A normal
full-product photograph is not enough to call a macro detail `source_verified`.
Promoting a dedicated photographed macro or a crop into source authority would
require a later contract with an explicit source-detail pose/crop replay; V3
fails that claim closed.

Every fixed detail ID has one canonical semantic spec containing family, shot
scale, numeric pose, target coordinate surface, framing, focus, and review
role. In addition, the validator derives one mandatory detail view per unique
Text/Code/Graphic `region_id`. Its stable ID is a sanitized bounded slug plus
an eight-hex SHA-256 prefix; collisions fail. The view binds exactly one region
and exactly the fields/codes/graphics owned by that region. At final QA, its
actual projected bbox is scaled from the decoded final-master dimensions to a
3840x2160 reference canvas. Region width/height, smallest raw OCR line height,
and code/graphic short edges must meet the frozen profile thresholds. Declared
numbers without final-pixel geometry have no authority.

Canonical motion pairs are closed enums. Bounded high/low orbits use the four
base anchors only. `pitched_full_rotation/high_full_360_rotation`,
`low_full_360_rotation`, or `high_and_low_full_360_rotation` uniquely requires
the corresponding complete profile-matched HIGH/LOW ring(s), exact derived
edge list, and loop closure. Omitting a ring or attaching an extra ring fails.

## 8. Continuity hard gates

The validator derives one and only one legal gate set from the complete,
named-review feature audit. Universal gates cover product frame, topology,
silhouette, label-to-surface binding, material, camera/lens/distance,
adjacent-edge movement, final-to-first closure, exact-copy render, and review
board derivation. Conditional gates are added only when the corresponding
feature is reviewed present:

- `visible_fill_line_or_liquid_boundary` -> fill volume/world-horizontal line;
- `pump_or_spray` -> nozzle vector in the closure/product frame;
- `visible_dip_tube` -> internal tube start/middle/end connectivity;
- `embossing_or_debossing` -> emboss/deboss registration;
- `transparent_or_translucent` -> show-through/layering response.

Thus a box, pouch, opaque jar, or tube cannot be forced to invent liquid,
dip-tube, transparency, pump, or embossing evidence. Conversely, removing a
gate from a reviewed-present feature fails closed. The source manifest is a
complete present/`reviewed_absent` taxonomy audit; the run manifest equals its
present subset exactly.

Declare numeric geometry tolerances in the continuity contract. Topology,
field text, code payload, and mark-identity differences are zero-tolerance.
`packaging-continuity-measurements.v2` binds the installed measurement-tool
hash, all actual master hashes, per-gate non-empty metric records, per-edge
metric records, comparator/tolerance/status derivation, and a semantic
self-hash. Generic image statistics cannot approve semantic gates without
hash-bound landmark/mask evidence. Cross-view screen-space constancy is not a
valid continuity model: it rewards billboards and punishes correct perspective.
Label centroids therefore use surface-local basis landmarks; nozzle vectors use
closure/product-local basis landmarks. Silhouette area/aspect, material region
statistics, and transparent show-through compare each view against a
source/pose baseline frozen before generation in `continuity_contract.json`.
Adjacent edges and the last-to-first loop compare actual landmark displacement
vectors to frozen pose-conditioned vectors, so stationary or backwards screen
motion cannot pass. Missing calibration yields `blocked`, never an inferred
pass.

Semantic input uses `packaging-continuity-semantic-evidence.v2` and
must lock the current source-manifest, asset-QA, coverage, and
continuity-contract hashes. Each
referenced annotation is a run-relative JSON file with schema
`packaging-continuity-annotation.v2`, a stable annotation ID/type, approved
master hashes, coverage region IDs, and raw normalized landmarks, polylines,
polygons, and masks only. Annotation files cannot contain computed values,
status, tolerance, comparator, or algorithm authority. Every semantic gate and
edge selects its contract-fixed `algorithm_id`, parameters, annotations,
comparator, and no-weaker-than-hard tolerance. The bundled builder verifies
every path/hash/binding, recomputes the numeric value from raw geometry and/or
approved image/evidence bytes, and derives status. Missing named evidence stays
blocked; wrong geometry fails; changed annotation bytes fail before a receipt
is written.

## 9. Generation unit contract

Every returned raw machine master and deterministic final master must decode as
exact horizontal 16:9 at a minimum of 1280x720. The generation receipt binds
the actual returned dimensions and records that no post-generation resize was
used to satisfy this floor. The final compositor preserves the raw canvas size.
Review-board canvas size cannot upgrade an input master, and a sub-HD master
cannot become production-eligible by later upscaling. This HD floor is distinct
from the optional external-4K delivery state.

One generation unit produces one asset. The compiler output record binds:

```text
asset_id
view_id
prompt_path
prompt_sha256
compiler_sha256
dependency_hashes:
  exact_copy_bundle_sha256
  exact_copy_bundle_file_sha256
  coverage_matrix_sha256
  surface_texture_atlas_sha256
extended_dependency_hashes:
  source_manifest_sha256
  protected_region_masks_sha256
  composition_plan_sha256
product_state_id
reference_ids
ranked_reference_bindings
previous_anchor_id
next_anchor_id
parent_anchor_view_ids
protected_copy_region_ids
deterministic_composition_plan_id
generation_text_policy: no_model_generated_product_copy
```

Raw generated assets are always:

```text
publishable: false
registry_eligible: false
exact_copy_lock_status: not_approved
```

Generation receipts bind `05_masters_raw/...`; they never bind final
`05_masters/...` bytes. Final bytes exist only after a self-hashed composition
job runs and the installed compositor replays them byte-for-byte.

Each generation receipt also records the actual submitted reference set:
role, reference ID, source ID, run-relative locator, and file SHA-256. Its
canonical set hash must match the coverage source refs and every declared
parent anchor. A prompt that names a reference is insufficient when that exact
file was not submitted.

### Delegated per-master worker transport

`runtime_contract_version: delegated_master_worker_transport_v1` applies to
every actual image-generation attempt. Explicit Skill invocation authorizes
exactly one fresh non-decision worker for one unit attempt. The main agent owns
the source, prompt, inspection, repair, acceptance, composition, validation,
and publication decisions; it must never make the terminal imagegen call.

Before spawning, freeze the current unit's unique ordered source files with
`scripts/freeze_reference_bundle.py`. Use the coverage `source_refs` as aliases
in their frozen order. Record the exact parent thread, a full random
32-lowercase-hex nonce, a pre-spawn millisecond checkpoint, prompt path/hash,
reference-manifest path/hash, view ID, and attempt ID. The worker task name and
canonical agent path must end with the full nonce.

The worker may read the frozen prompt and references, transport those exact
bytes to one built-in imagegen call, and end empty. It may not interpret,
rewrite, inspect, repair, approve, select files, or publish. Resolve the result
with `scripts/resolve_worker_image.py`; newest-file selection, a non-empty
worker final, multiple completed image events, wrong parent/thread/call,
prompt-byte drift, reference reorder/mutation, or a saved path unrelated to the
worker thread plus image-call ID blocks the unit.

Promote only a main-agent-inspected accepted attempt to the canonical
`05_masters_raw/<family>/<view_id>.png` path. Build its receipt with
`scripts/build_generation_receipt.py`. `packaging-generation-receipt.v2`
hash-binds the resolver result, worker thread/turn/call, full nonce-bearing
agent path, prompt bytes, ordered frozen-reference bundle, raw image bytes,
dimensions, semantic source/parent bindings, and accepted view. Durable
receipt locators are run-relative POSIX paths even when the run-scoped worker
transport manifest contains machine-local absolute paths.

Receipt v1 is `legacy_untrusted_generation_provenance`. It may document a
historical asset but cannot make a v3 run `COMPLETE`, authorize Project Canon,
or grant `label_copy`. A v3 COMPLETE run requires one unique v2 worker
provenance chain per approved master; one worker thread/turn/call cannot be
reused across views.

If a raw base contains pseudo-copy in protected regions, reject it or prove the
deterministic mask fully replaces those pixels before composition.

### Executable compiler

`scripts/compile_generation_prompts.py <run_root>` is the normative prompt
compiler. It reads `00_manifest/run_manifest.json` and the manifest-bound source
manifest, coverage matrix, composition plan, texture atlas, protected masks,
and exact-copy bundle. It refuses compilation unless both generation gates are
open and every file/hash lock still matches.

Coverage must freeze a non-empty `product_coordinate_frame` and `identity_lock`.
The latter contains `geometry_landmark_contract`, `material_contract`,
`occupancy_lock`, and non-empty `forbidden_inventions`. Every required view also
contains numeric pose, lens/distance profiles, visible and occluded surfaces,
geometry landmark IDs, material feature IDs, source reference IDs, parent
anchors, calibrated previous/next neighbors, and exact-copy visibility sets.

The compiler emits exactly one UTF-8 prompt per required view plus
`generation_prompt_index.json`. Prompt bytes explicitly bind:

```text
pose + shot scale + lens + camera distance
visible/occluded surfaces
source reference IDs + ranked reference bindings
previous/next neighbors + parent anchors
geometry landmark IDs + global geometry/material contracts
protected copy regions + deterministic composition view
exact_copy_bundle_sha256
exact_copy_bundle_file_sha256
coverage_matrix_sha256
surface_texture_atlas_sha256
source_manifest_sha256
protected_region_masks_sha256
composition_plan_sha256
```

The first four values are the unit `dependency_hashes` required by the run
validator. The remaining three are `extended_dependency_hashes`. Compilation
is deterministic: rerunning against byte-identical dependencies produces
byte-identical prompts and index; different frozen bytes are not overwritten
without explicit `--replace`.

After compilation, copy the returned index hash into
`run_manifest.hashes.generation_prompt_index_sha256`. Advancing to `GENERATING`
does not authorize batch submission: the complete current unit prompt and hash
must still be disclosed before that unit's terminal image call.

Compiled prompt bytes must contain the view and state IDs, exact-copy semantic
and file hashes, coverage and atlas hashes, the horizontal 16:9 single-asset
request, and raw-publication prohibitions. A short placeholder prompt remains
invalid even when its hash is internally consistent.

## 10. Deterministic copy composition

Allowed recorded projection families:

```text
source_pixel_preservation
planar_rectangle
planar_homography
```

Every binding records input asset hashes, transform parameters or mesh/renderer
receipt, depth order, visibility rule, protected mask hash, output region, and
output asset hash. Unsupported geometry blocks the affected view.

Post-composite verification repeats whole-image OCR, region OCR, code decode,
graphic comparison, layer/show-through QA, geometry QA, and continuity QA.

The bundled v3 post-composite OCR/decode implementation is macOS-only and
requires Darwin, Swift, the installed `macos_vision_ocr.swift`, and Pillow.
Python and Swift exchange authority through one unique atomic result file, not
stdout. The result envelope binds a fresh invocation nonce, ordered canonical
input paths, one observation per input, and schema version
`packaging-macos-vision-result.v1`; stdout/stderr are diagnostic-only byte
streams. A missing/trailing result document, nonzero process exit, stale nonce,
or path/count/order mismatch fails closed.
Tesseract remains valid for source discovery/region review but does not supply
the final barcode/QR path. A run without a callable Mac final-verification route
is not executable exact-copy production and must stop before prompt compilation.
The compiler derives this from the live host instead of trusting a manifest
flag: non-geometry-only compilation requires Darwin, Swift, both bundled
scripts, the exact pinned Pillow version, and a passing live OCR/EAN/QR smoke.
It writes no prompt or index when preflight fails, and the production CLI has
no runtime-bypass option.

`scripts/compose_exact_copy.py` provides deterministic replay for source-pixel
preservation, rectangular planar placement, and four-corner planar homography.
Its job binds raw base, layers, masks, field/code/graphic IDs, destination
geometry, output, receipt, and a semantic self-hash. Cylindrical, conical,
mesh, or depth-aware projection is not an executable v3 capability and must
remain blocked until both a callable and validator are added.

Post verification contains one result per required master. Each binds the final
master hash, composition receipt, post-OCR receipt, and the exact visible
field/code/graphic sets from coverage. Top-level approval values are recomputed
from these records rather than trusted as status strings.

The bundled adapter writes `post_composite_verification.candidate.json` only.
Promotion is explicit and byte preserving: a named reviewer checks
`candidate_status: ready_for_manifest_binding` plus every referenced receipt,
copies those exact bytes to the canonical manifest locator, records the new
file hash in `run_manifest.hashes.post_composite_verification_sha256`, and runs
the validator. Editing the candidate during promotion, accepting a
`review_required` candidate, or treating promotion as production approval is
forbidden.
The post OCR/decode adapter is the installed bundled script, never an arbitrary
run-local executable. The observed product-native field and code sets must
equal the view's expected sets exactly; extra pseudo-copy, duplicates, unknown
fields, or undeclared symbols fail exact-copy approval.

## 11. Packaging-specific detail branches

- Flat/rectangular pump bottle: R16 minimum. Either `flat_or_rectangular_body`
  or `pump_or_spray` independently triggers R16; transparency or an asymmetric
  closure adds evidence obligations but never lowers that profile. Require side
  depth, four shoulder corners, nozzle vector, and thick base.
- Round bottle/jar/can: R8 geometry may suffice only when it is reviewed simple,
  near-rotationally symmetric, and low-copy. Ordinary label-heavy packaging
  without an R16/R24 trigger requires R12; `wrap_label` requires R16;
  `continuous_wrap_copy` requires R24. Require top, bottom, and seam.
- Box/carton: six orthographic faces, four vertical-edge three-quarters, top,
  bottom, flap/adhesive seams, and preferably a dieline.
- Pouch/bag: front, back, both gussets, bottom gusset, top seal/spout, and state
  separation for full/empty or deployed/stored.
- Tube: front, back, narrow sides, tail crimp, cap/nozzle, shoulder, and one fixed
  deformation state.
- Pump/spray/dropper: closure state is an independent product state. Never merge
  locked/unlocked, pressed/released, open/closed, or cap-on/cap-off.
- Multi-component kit: one asset pack per component plus a relationship manifest.

## 12. Review-board derivation

Review boards are built from approved masters only. Store each input path and
hash, board layout, output dimensions, output hash, and role.

- geometry board: at most six full-product cells at verified 4K 16:9;
- detail board: at most four large evidence cells at verified 4K 16:9;
- dense overview: `review_only_no_qa_authority`;
- never crop, stretch, or relabel masters;
- every board file exists, decodes, hash-matches, is exact 16:9, stays within
  capacity, and lists inputs that exactly match approved masters;
- every approved master appears exactly once across QA-authority boards; dense
  indexes are paginated and never gain QA authority;
- metadata and view names may be rendered only outside the product-native image
  region and only on human review boards, never on machine masters.

“4K” in this review-board section refers only to the 3840x2160 board canvas.
Likewise, dynamic-region “4K-equivalent” thresholds are normalized readability
measurements on a 3840x2160 reference canvas; neither statement proves a master
is native 4K. External 4K must retain enhancement lineage and repeat exact-copy
composition plus OCR/decode/graphic verification before it may be called
verified enhanced 4K; it must never be labeled native 4K.

QA boards are semantically partitioned as `neutral_rotation`, `elevation`,
`framing_bridge`, `copy`, `code`, `structure`, and `material`. A board cannot
mix roles. Neutral/elevation/bridge views follow canonical pose order; detail
views follow stable ID order. Pagination preserves one continuous ordered
sequence per role, and all approved masters appear exactly once across
QA-authority boards.

## 13. Legacy v2 migration

Old `built_in_nonblocking_prompt_pair_v2` boards and prompts remain immutable
historical evidence. They may be classified only as
`legacy_geometry_layout_only`. They cannot auto-upgrade to rotation-ready,
exact-copy-approved, or `label_copy` Canon authority.
Every retained legacy run directory must carry a conspicuous sibling
`LEGACY_V2_QUARANTINE.md`; absence of that marker is a migration defect. The
historical prompt bytes remain untouched.

## 14. Canon boundary

The run manifest and rotation masters remain authoritative even if one selected
primary image is exported to Project Canon. `geometry_layout_exact_copy_verified`
requires `packaging-exact-copy-canon-evidence.v2`, built only by
`scripts/build_exact_copy_canon_evidence.py` from a COMPLETE all-visible run.
The sidecar locks the installed validator, COMPLETE manifest, bundle, coverage,
prompt index, asset QA, continuity QA, post verification, and one unique primary
master/post-result member. The shared bridge re-runs the packaging validator at
export time. Approval JSON, v1 evidence, arbitrary PNGs, review boards, or status
strings alone are insufficient; otherwise export only `geometry_layout_only`.
