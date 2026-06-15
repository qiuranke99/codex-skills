# Advanced Cinematic Language Decision Matrix

Use this reference only when the brief needs advanced cinematic language,
complex continuity, sound-aware shot planning, VFX/virtual-production planning,
or production-handoff traceability. Do not load this reference by default for
routine product-storyboard or fast concept work.

This file distills the source method library into execution rules for
`ai-visual-director`. It is not a full cinematography encyclopedia and must not
turn every storyboard into a camera-department report.

## When To Read

Read this file when `00_route_decision.json` contains
`cinematic_language_reference_required: true`, or when the user explicitly asks
for any of these:

- advanced cinematic language, cinematography grammar, lens language, shot
  language, camera report, camera handoff, DP handoff, or production handoff;
- VFX, CG, virtual production, LED volume, greenscreen, tracking markers,
  witness camera, HDRI/light probe, lens grid, distortion chart, or compositing;
- sound design, sound bridge, J-cut, L-cut, MOS, ambience, Foley, VO, ADR, or
  sound/visual relationship;
- ACES, LUT, HDR/SDR, color pipeline, delivery color space, show LUT, or DI;
- anamorphic/spherical choice, filtration, shutter angle, frame rate,
  slow-motion, time-lapse, rack focus, split diopter, or focus-pull behavior;
- 180-degree rule, axis crossing, eyeline match, screen direction, match on
  action, coverage, master shot, safety shot, or edit-continuity diagnosis.

Do not read it merely because a brief says `cinematic`, `premium`, `beautiful`,
or `film look`. Those words require concrete shot planning, but they do not
automatically require advanced delivery fields.

## Core Model

Design shot language through four domains and three depth levels.

Four domains:

- `mise_en_scene`: what is inside the frame, where it sits, how it moves, and
  what performance or product action it carries.
- `cinematography`: how the camera records it: framing, lens feel, depth of
  field, light, movement, motion texture, and color.
- `editing`: how shots connect: axis, eyeline, match on action, rhythm, cut
  type, screen direction, and coverage.
- `sound`: how sound enters the visual plan: dialogue, ambience, Foley, music,
  silence, sound bridge, J-cut, L-cut, MOS, or VO.

Three levels:

- `L1 - always required`: readability and continuity. Viewer understands the
  space, action, product/character identity, axis, eyeline, and cut logic.
- `L2 - advanced creative controls`: meaning generation through lens relation,
  light direction, depth of field, motion texture, color, point of view, and
  sound/visual design.
- `L3 - complex delivery and traceability`: production safety for VFX,
  virtual production, multi-team handoff, camera report, timecode, lens grids,
  tracking markers, color pipeline, and sound capture notes.

## Routing Matrix

| Trigger | Read this file? | Add fields |
|---|---:|---|
| Routine product ad, simple storyboard, mood route | No | Use normal shot spec and product identity lock. |
| User asks for camera/lens/DP handoff | Yes | Add L2 lens/light/focus fields and L3 camera report flag. |
| VFX, CG, virtual production, LED volume, greenscreen | Yes | Add VFX notes, tracking/HDRI/lens-grid requirements, camera report flag. |
| Sound design or edit sound relationship matters | Yes | Add `sound_intent`, sound bridge, J-cut/L-cut/MOS/VO decisions. |
| Axis, continuity, coverage, or edit problem is explicit | Yes | Add continuity grammar and coverage strategy fields. |
| Certification or premium pitch with high production complexity | Yes | Add L2 fields and only the L3 fields justified by the brief. |

## L1 - Always Required

Keep these inside ordinary shot planning. They do not require bloated camera
metadata:

- `shot_purpose`: what the viewer must understand now.
- `shot_size`: story importance and readable subject scale.
- `camera_angle`: power, vulnerability, geography, or product authority.
- `camera_movement`: static or motivated movement; name what changes.
- `composition`: subject hierarchy, negative space, frame-within-frame, lead
  room, look room, foreground blocker, or symmetry.
- `blocking`: start position, path, stop point, hand/product action, body or
  product orientation.
- `axis_of_action`, `screen_direction`, `eyeline`: continuity base.
- `cut_logic`: why this shot follows the previous shot.
- `foreground`, `midground`, `background`: what each layer does.
- `continuity_lock`: product, character, wardrobe, prop, geography, light
  direction, scale, and screen direction facts that must not drift.

## L2 - Advanced Creative Controls

Add these fields only when they change the shot decision or handoff quality:

```yaml
lens_language:
focus_strategy:
depth_of_field:
lighting_motivation:
lighting_shape:
motion_texture:
color_strategy:
sound_intent:
coverage_strategy:
edit_continuity_strategy:
```

Field rules:

- `lens_language`: write perceived behavior, not gear fetish. Prefer
  `wide lens feel exaggerates foreground hand and product scale` over
  `24mm because cinematic`.
- `focus_strategy`: name focus subject, rack/follow-focus intent, or why deep
  focus is required.
- `depth_of_field`: use shallow/deep/pan-focus as attention strategy, not as
  automatic beauty.
- `lighting_motivation`: state whether light is motivated by a practical,
  window, screen, product glow, laboratory source, sun, or stylized expression.
- `lighting_shape`: direction, quality, contrast, color temperature, and
  whether hard/soft/rim/top/bottom/back light creates meaning.
- `motion_texture`: frame-rate, shutter feel, speed ramp, time-lapse, or motion
  blur only when temporal texture matters.
- `color_strategy`: dominant hue, contrast, saturation, character/product color
  coding, and whether a LUT/ACES note matters.
- `sound_intent`: dialogue/SFX/ambience/music/silence role and whether sound
  leads, follows, bridges, or contradicts the picture.
- `coverage_strategy`: master/OTS/reverse/reaction/insert/safety/minimal
  coverage when editability matters.
- `edit_continuity_strategy`: axis, screen direction, eyeline, match on action,
  30-degree rule, cross-line method, or deliberate discontinuity.

## L3 - Complex Delivery And Traceability

Add these only for VFX, virtual production, production handoff, certification,
or multi-team execution:

```yaml
camera_report_required:
camera_report_fields:
vfx_or_tracking_notes:
virtual_production_notes:
color_pipeline_notes:
sound_capture_notes:
handoff_risk:
```

Use concrete requirements:

- `camera_report_required`: `true` only when later departments need camera,
  lens, focus, timecode, filter, or take metadata.
- `camera_report_fields`: scene/shot/take, timecode, lens, focal length,
  T-stop/F-stop, filter, focus distance, camera ID, sound method, remarks.
- `vfx_or_tracking_notes`: tracking markers, greenscreen/bluescreen extent,
  HDRI/light probe, lens grid, distortion chart, witness camera, CG interaction
  point, or safety boundary.
- `virtual_production_notes`: LED volume constraints, screen reflection risk,
  parallax relationship, practical/virtual light matching, or environment sync.
- `color_pipeline_notes`: show LUT, ACES, IDT/ODT, Rec.709, DCI-P3, HDR/SDR,
  or DI dependency.
- `sound_capture_notes`: boom/lav/VO/ADR/MOS decision and sync risk.
- `handoff_risk`: the one field most likely to break downstream execution.

## Cut And Continuity Priority

Use Murch's hierarchy when judging cuts:

1. emotion
2. story
3. rhythm
4. eye trace
5. 2D screen plane
6. 3D spatial continuity

Breaking continuity is allowed only when the break has a named expressive
purpose. Otherwise preserve axis, screen direction, eyeline, and match on
action.

## Common Mistakes

| Mistake | Correction |
|---|---|
| Adding every L2/L3 field to a simple product board | Keep default shot spec; load this reference only when triggers justify it. |
| Writing `50mm` without format or visual reason | Write equivalent field of view or perceived lens behavior. |
| Treating camera movement as decoration | Name reveal, follow, compare, transform, withhold, or rhythm function. |
| Ignoring sound until video prompt stage | Add `sound_intent` when sound changes cut logic, pacing, or emotional design. |
| Calling VFX without traceability | Add tracking/HDRI/lens-grid/camera-report fields required by downstream work. |
| Over-specifying production metadata for AI-only ideation | Keep L3 out unless handoff, VFX, or certification requires it. |

## Output Pattern

When this reference is active, add a compact block to the shot plan:

```yaml
cinematic_language_depth:
  level: L2_or_L3
  active_domains: [mise_en_scene, cinematography, editing, sound]
  reason:
  added_fields:
  omitted_fields_with_reason:
```

Then include only the extra shot-level fields justified by `added_fields`. The
default remains disciplined shot planning, not exhaustive camera reporting.
