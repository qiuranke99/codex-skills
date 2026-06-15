---
name: ai-visual-director
description: >-
  Use when the user asks for AI visual direction, reference-image-to-storyboard work, cinematic shot planning, 9-panel/3x3 storyboard sheets, product-ad storyboard prompts, Google Omni video prompt segments, 故事板, 分镜, 9宫格, 蓝灰手绘稿, or turning images, folders, keywords, product briefs, campaign briefs, or story briefs into director-led visual deliverables.
---

# AI Visual Director

## Core Rule

Do not answer these tasks with one long prompt. Run a staged director workflow:

1. Intake and reference-role analysis.
2. Route decision: project type, duration logic, sheet count, panel count, and video segment count.
3. Creative concept: big idea, audience desire, story tension, world rule, visual mechanism, scene ladder, and signature images.
4. Director brief: dramatic arc, visual motif, continuity locks, failure modes.
5. Product identity lock before shot planning when a real product is supplied.
6. Shot plan: concrete shot specs for every storyboard panel.
7. Automated structure, creative-standard, and product-fidelity validation.
8. Internal revision until validation passes or the remaining risk is explicit.
9. One storyboard image prompt per 3x3 sheet.
10. Google Omni prompts in temporal segments, normally 10 seconds each.
11. Run-package validation, final QC summary, and saved artifact paths.

If the user provides only images and short keywords, infer the missing structure.
Ask only when a missing fact materially changes the route, such as unknown
product identity, unknown target duration, or conflicting reference roles.

## Reference Files

Use progressive disclosure. Read only the files needed for the requested output:

- Required run order, product-fidelity gates, artifact names, and final validation: `references/workflow_contract.md`.
- Shot-spec fields and handoff grammar: `references/shot_spec_template.md`.
- Advanced cinematic language, VFX/virtual production, sound-aware shot planning, color pipeline, camera report, and complex handoff routing: read `references/cinematic_language_decision_matrix.md` only when `00_route_decision.json` sets `cinematic_language_reference_required: true` or the user explicitly asks for those modes.
- Production-mode routing, escalation triggers, and director playbooks: `references/director_kernel.md`.
- World-class TVC principles, attention choreography, reference parity, and image-to-shot translation: `references/world_class_tvc_principles.md`.
- Non-blocking observer sidecar behavior and learning-loop rules: `references/observer_protocol.md`.
- Non-generic shot progression examples: `references/good_shotlist_examples.md`.
- Blue-gray previs sketch visual target: `references/blue_gray_previs_style_bible.md`; inspect `assets/blue_gray_previs_reference.jpeg` when style drift is likely.
- Structured contracts: `references/intake.schema.json`, `references/shot_plan.schema.json`, `references/video_segments.schema.json`, `references/audit.schema.json`, `references/observer_event.schema.json`, and `references/rule_candidate.schema.json`.

Do not depend on project-root notes, old local templates, or files outside this
skill folder. If a rule is required for the skill, it must live inside this
skill.

## Reference Parity

When the user supplies reference images, extract their visual DNA instead of
copying surface style blindly:

- subject hierarchy: what dominates first, second, third;
- camera relation: height, distance, angle, lens feel, compression, intimacy;
- depth architecture: foreground blockers, midground subject, background geometry;
- light logic: direction, contrast, reflection, haze, specular behavior;
- material behavior: what looks wet, dry, glassy, matte, translucent, metallic, soft, or rigid;
- motif grammar: repeated shapes, gestures, props, color accents, framing devices;
- negative constraints: what the reference refuses to show;
- restraint: what the reference deliberately leaves empty or unresolved.

Every shot plan must include reference parity decisions. If a 9-panel sheet only
resembles the reference by keywords, not hierarchy, depth, light, material, or
visual restraint, treat it as a failure.

## Creative Concept Gate

Before shot planning, define a top-level `creative_concept`. A high-end TVC is
not a tour of product parts. It needs a world, a rule, and events that make the
product feel inevitable.

For non-catalog product ads, `creative_concept` must include:

- `big_idea`: the advertising thought, not a mood phrase;
- `audience_desire`: what the viewer should want or feel;
- `story_tension`: what is withheld, transformed, awakened, crossed, or resolved;
- `world_rule`: how this film's world behaves;
- `visual_mechanism`: the repeatable image logic that drives reveals and cuts;
- `scene_ladder`: at least three distinct arenas or phases;
- `signature_images`: at least three frames a director could pitch verbally.

If the idea can be summarized as `petals + glass + product + light sweep`, it is
not yet a TVC concept. Keep working until there is a sceneable mechanism such as
`a mirrored hotel corridor folds into the bottle edge`, `a dawn greenhouse opens
only where the scent passes`, or `a fingertip ripple turns into the final base
reflection`. Do not copy those examples; invent an equivalent mechanism from
the supplied references and brief.

## Product Identity

When the user supplies a real product image, package photo, packshot, label
reference, or product-identity reference, treat the packaging as identity, not
decoration. A storyboard or video prompt must not simplify the product into a
blank bottle, generic jar, invented brand, approximate label, or mood object.

Before shot planning, extract a top-level `product_identity_lock` with the
fields defined in `references/workflow_contract.md` and
`references/shot_plan.schema.json`. The lock must cover:

- exact visible product/brand text, or `unreadable_from_reference`;
- primary label text and surface text inventory;
- embossed, debossed, raised, engraved, relief, printed, or transparent marks;
- label layout and product geometry;
- cap, pump, closure, spray tube, box, applicator, seal, window, and other real components;
- color, material, finish, transparency, and proportion facts;
- required visible marks;
- forbidden changes and forbidden visual additions.

For every product-visible shot, include `product_visibility` and
`product_identity_action`. For every `full_visible` product shot, also include
`visible_product_text_or_marks`, `product_visual_facts`, and
`forbidden_visual_additions`.

Product identity is a fidelity constraint, not a mandate to make every panel a
product panel. In a product storyboard, every shot must still declare
`product_visibility`, including `not_visible` origin, world, benefit, or
metaphor shots. Product-absent panels must explicitly keep the product,
package, label, logo, and product text out of the frame. `detail_only` panels
draw only the specified real component or material fact; `partial_visible`
panels crop, occlude, reflect, or reveal only part of the locked product. Do
not let a global product lock turn a 9-panel sheet into a wall of packshots.

Full-visible product shots must carry the exact visible text/wordmark/logo/mark
inventory from the real reference. If the real product has a raised wordmark,
embossed mark, transparent spray tube, no metal plate, no badge, no front
plaque, no extra label panel, or a specific cap shape, say so. Do not invent
missing microcopy, legal copy, claims, certification icons, hardware, emblems,
or label panels.

Camera orbit, hero reveal, push-in, parallax, foreground occlusion, light sweep,
mist, liquid, petals, and environment motion are allowed when they serve the
sequence. The failure condition is visible product fact drift: wrong/missing
text, blank label, fake brand, changed component, invented metal plate, changed
cap/pump/closure, altered material, or generic package shape.

## Intake And Routing

Use the intake schema when a structured brief is needed. Route with
`scripts/route_project.py` or mirror its logic:

```bash
python scripts/route_project.py intake.json > 00_route_decision.json
```

The route decision may include:

```yaml
cinematic_language_reference_required:
cinematic_language_triggers:
cinematic_language_depth:
recommended_references:
```

If `cinematic_language_reference_required` is `true`, read
`references/cinematic_language_decision_matrix.md` before finalizing the shot
plan. If it is `false`, do not load that reference merely because the brief says
`cinematic`, `premium`, or `film look`; solve those with the normal shot-spec
grammar and reference parity rules.

Default duration logic:

- storyboard sheet count = `ceil(duration_seconds / 13.5)`, minimum 1;
- panel count = `storyboard_sheet_count * 9`;
- video segment count = `ceil(duration_seconds / video_segment_seconds)`, default segment length 10 seconds.

Do not equate one storyboard sheet with one video segment. A 40-second ad is
normally 3 storyboard sheets / 27 panels and 4 Google Omni prompts / 10 seconds
each.

Production modes:

- `standard_fast`: one route, one shot plan, automated validation, internal revision if needed, then prompts and final QC.
- `rush`: shortest valid path; no optional sub-agent review.
- `premium_pitch`: add deeper reference parity, stronger motif discipline, and a fuller QC report.
- `certification`: run offline audit and package verification before claiming completion.

Escalate when references conflict, regulated or likeness-sensitive claims appear,
the user asks to imitate a living artist or brand campaign too closely, product
identity is unclear, or generation visibly breaks identity, panel separation, or
the blue-gray storyboard grammar.

## Shot Planning

Every panel must become a shot spec with the fields from
`references/shot_spec_template.md`. At minimum include:

```yaml
shot_id:
aspect_ratio:
scene:
scene_arena:
scene_role:
dramatic_event:
visual_mechanism:
duration:
shot_purpose:
shot_size:
camera_angle:
lens_feel:
camera_movement:
cut_logic:
attention_order:
eye_trace:
depth_strategy:
reference_parity:
main_subject:
main_action:
body_pose:
composition:
foreground:
midground:
background:
scale_reference:
continuity_lock:
must_preserve:
avoid:
```

Strong shot planning is concrete: it names what the viewer reads first, why the
camera is there, what changes from the prior shot, what is in foreground /
midground / background, and what must not drift. Do not use adjectives such as
`cinematic`, `luxury`, `premium`, or `beautiful` as substitutes for staging,
lens relation, action, material behavior, or continuity facts.

Every product-ad panel also needs a creative scene layer:

- `scene_arena`: where the panel lives visually, such as greenhouse corridor,
  reflective tray threshold, rain-lit elevator, skin-ripple world, or clean
  packshot memory space;
- `scene_role`: what this panel does in the commercial arc, such as origin
  world, inciting transformation, partial reveal, use action, benefit metaphor,
  return bridge, or final authority;
- `dramatic_event`: the on-screen event or transformation, not merely `light
  sweep` or `product holds`;
- `visual_mechanism`: how the film's world rule creates the image or cut.

For product ads, the sequence must include product identity, material proof,
texture proof, use action or interaction, benefit metaphor or proof, and final
packshot clarity unless the user specifies another structure. A non-catalog
9-panel product sheet must also preserve product visibility rhythm:

- maximum 4 `full_visible` product shots per 9 panels;
- at least 1 `not_visible` origin/world/benefit/metaphor shot;
- at least 3 `detail_only` or `partial_visible` transition/proof shots;
- at least 2 panels whose main subject is not the product or package;
- the first full-visible product reveal should not arrive in panel 1 or 2
  unless the user explicitly requests a catalog, listing, or packshot-only
  board.

## Validation Gates

For shot plans:

```bash
python scripts/validate_shot_plan.py 02_shot_plan.json
```

The shot-plan gate checks structural variety, required shot fields, product
identity locks, creative concept, scene arenas, dramatic events, visual
mechanisms, exact visible text carry-through, full-visible product facts,
forbidden visual additions, and avoid-list discipline.

For Google Omni video segment JSON:

```bash
python scripts/validate_video_segments.py 08_google_omni_video_prompts.json
```

For completed run directories:

```bash
python scripts/validate_run_package.py <run_dir> > 10_run_package_validation.json
```

Do not claim a product storyboard/video package is final until the relevant
validators pass or the remaining validation gap is explicitly reported.

For package certification:

```bash
python scripts/verify_skill_package.py <skill_dir>
```

## Shadow Observer

Use the Shadow Observer as a non-blocking sidecar. It logs failure evidence and
candidate rules; it does not block normal production and does not automatically
mutate the skill.

Append events when useful:

```bash
python scripts/observe_run.py append --run-dir <run_dir> --stage <stage> --event-type <type> --severity <level> --failure-codes <code> --evidence "<evidence>"
```

Use `references/observer_protocol.md`, `references/observer_event.schema.json`,
and `references/rule_candidate.schema.json` for event and candidate-rule shape.

## Storyboard Image Generation

Generate one image per sheet, not all sheets in a single imagegen call. Each
prompt must contain:

- exact 3x3 grid instruction;
- aspect ratio and title strip behavior;
- nine panel descriptions with shot IDs;
- per-panel camera angle, shot size, subject/action, and depth layers;
- reference parity decisions;
- product identity lock when a product appears;
- blue-gray hand-drawn previs style block;
- negative constraints against polish, fake UI, invented captions, extra panels, photorealism, and panel bleeding.

For user-provided products, the sheet prompt must explicitly preserve the exact
product silhouette, cap/pump/closure, label placement, visible product text,
logo/mark, embossed/debossed marks, color bands, real components, material
facts, and package proportions. Draw exact supplied short label text when it is
legible in the reference. If microtext is too small for rough storyboard scale,
draw the correct label blocks and any readable primary mark rather than leaving
the package blank.

Every product storyboard sheet prompt must include a `Product Visibility
Rhythm` block before the panel plan, then repeat each shot's visibility in the
panel line:

```text
Product Visibility Rhythm: SH_001 not_visible -> SH_002 detail_only -> ...
- SH_001 [product_visibility: not_visible]: no product, no bottle, no package,
  no label, and no product text in this panel; draw only the origin/world beat.
- SH_004 [product_visibility: full_visible]: draw the exact supplied product
  with the locked text, label layout, component inventory, and forbidden
  additions.
```

Never rely on a global product lock alone. The global lock protects
full-visible product facts, but per-panel visibility tells the image model when
not to draw the product, when to draw only a component, and when to draw the
full package.

Every product storyboard sheet prompt must also include:

```text
Creative Concept:
World Rule:
Scene Ladder:
Visual Mechanism:
```

Then every panel line must repeat:

```text
[scene_arena: ...] [scene_role: ...] [dramatic_event: ...] [visual_mechanism: ...]
```

This is not decorative metadata. It is the antidote to repetitive bottle
details: the image model needs to know the scene, event, and mechanism that make
each panel different.

Base style phrase:

```text
rough hand-drawn production storyboard sheet, animatic previs sketch, director's working storyboard thumbnails, loose black pencil linework, dark graphite searching lines, visible construction lines, very light blue-gray storyboard wash, sparse tonal blocks, clean white paper background, simplified faceless characters when people appear, sparse cinematic environment detail, linework primary, wash secondary
```

## Google Omni Video Prompts

Create video prompts by temporal segment, not by storyboard sheet. Every segment
must include first frame, last frame, camera plan, subject motion, environment
motion, continuity lock, visual style, and negative constraints.

For product video, start the prompt file with `Required Reference Setup` and
`Product Identity Lock`. The user product original, packshot, or multi-angle
image is the highest-priority `product_identity` reference. Style references may
control lighting, environment, camera mood, props, rhythm, and lens language,
but must not change package geometry, cap/pump/closure, label layout, visible
text/logo/mark, embossed or relief marks, color bands, materials, proportions,
or real component inventory.

Carry the same `product_identity_lock` from the shot plan into video prompt
JSON. Product-visible segments must include `product_visibility`,
`product_identity_reference`, and `product_motion_rule`. Full-visible product
segments must also include `visible_product_text_or_marks`,
`product_visual_facts`, and `forbidden_visual_additions`.

When a segment is pasted into Google Omni, include the required reference setup,
the full product identity lock, and the selected segment together. A segment
without the lock is underspecified and may drift into a generic mood object.

## Required Final Deliverables

Use a run directory with stable names:

```text
run_dir/
  00_route_decision.json
  01_reference_roles.md
  02_shot_plan.json
  03_director_qc.json
  04_storyboard_image_prompts.md
  storyboard_sheet_01.png
  storyboard_sheet_02.png
  08_google_omni_video_prompts.md
  08_google_omni_video_prompts.json
  09_final_qc_report.md
  10_run_package_validation.json
  _observer/
    events.jsonl
    candidate_rules.json
```

If image generation is not requested or cannot run in the current environment,
still produce the route decision, reference roles, shot plan, storyboard image
prompts, video prompts, run-package validation, and QC summary. The final answer
must report the exact saved artifact paths and any validations that could not be
run.

## Portability

This skill must remain self-contained. Packaged references, schemas, scripts,
assets, and tests live inside this folder. When root notes or temporary workflow
files change, copy accepted rules into this skill folder, update
`references/source_manifest.json`, run `scripts/verify_skill_package.py`, and
only then publish.
