---
name: ai-visual-director
description: Use when the user asks for AI visual direction, product-ad film concepts, reference-image-to-storyboard work, cinematic shot planning, storyboard images, Google Omni/Veo-style video prompts, 故事板, 分镜, 9宫格, or turning brief/product/style references into director-led ad film deliverables.
---

# AI Visual Director

## Core Rule

Do not start with a fixed storyboard grid. For brief + product image + visual reference work,
first invent the ad film's story engine, then derive storyboard images and
Google Omni video prompts from that engine. Do not answer with one long prompt
or a repeated product-angle sequence.

Run this order:

1. Intake: brief, duration, dimensions, product image, visual references, and feasibility.
2. Reference roles: product identity reference outranks style, lighting, environment, mood, and motion references.
3. Reference deconstruction: each reference image must be decomposed into observed facts, transferable principles, and forbidden surface-copy risks before creative concept selection.
4. Product identity lock before route or shot planning when a real product is supplied.
5. Route, duration, and aspect: infer duration, segment seconds, and requested video aspect ratio from structured intake or brief text when structured intake is absent; default only when no time cue exists.
6. Mandatory agent activation: start `creative_director_agent`,
   `director_agent`, `screenwriter_agent`, and `art_director_agent`; record all
   four in `02_shot_plan.json.agent_activation_ledger` before concept council,
   script, storyboard, or shot-plan validation.
7. Story engine: advertising logline, dramatic question, world rule, product role, story arc, motion language, and anti-plastic material rules.
8. Beat map: allocate story beats across director concept boards, approved
   keyframe packets, and Google Omni segments; do not equate one sheet, one
   panel, or one story beat with one video cut.
9. Shot plan: concrete keyframe specs for every storyboard panel, including
   `reference_transform`, `shot_function_signature`, and aspect-ratio evidence.
10. Automated structure, story, semantic progression, aspect-ratio,
    product-fidelity, agent-ledger, and anti-plastic validation.
11. Internal revision until validation passes or the remaining risk is explicit.
12. Generate one storyboard image per sheet with Codex image generation when available.
13. Start `google_omni_prompt_expert_agent` after approved storyboard packets;
    record it and the director approval in
    `08_google_omni_video_prompts.json.agent_activation_ledger`.
14. Generate Google Omni prompts as concise temporal motion contracts with the
    same requested video aspect ratio as the storyboard panels.

If a required agent cannot be started and recorded, stop and report a hard
blocker. Do not simulate the agent in prose and continue.

Final user-facing output must contain only:

- storyboard image path(s);
- Google Omni video prompt path and paste-ready segment prompts.

Route decisions, reference roles, shot plan JSON, image prompt text, QC,
validation JSON, and observer files are internal run artifacts. Mention them
only if validation fails, image generation cannot run, or the user asks for
internals.

If the user provides only images and short keywords, infer the missing structure.
Ask only when a missing fact materially changes the route, such as unknown
product identity, unknown target duration, or conflicting reference roles.

## Reference Files

Use progressive disclosure. Read only the files needed for the requested output:

- Required run order, product-fidelity gates, artifact names, and final validation: `references/workflow_contract.md`.
- Mandatory agent roles, stage gates, and activation ledger: `AGENTS.md`.
- Shot-spec fields and handoff grammar: `references/shot_spec_template.md`.
- Advanced cinematic language, VFX/virtual production, sound-aware shot planning, color pipeline, camera report, and complex handoff routing: read `references/cinematic_language_decision_matrix.md` only when `00_route_decision.json` sets `cinematic_language_reference_required: true` or the user explicitly asks for those modes.
- Production-mode routing, escalation triggers, and director playbooks: `references/director_kernel.md`.
- World-class TVC principles, attention choreography, reference parity, and image-to-shot translation: `references/world_class_tvc_principles.md`.
- Non-blocking observer sidecar behavior and learning-loop rules: `references/observer_protocol.md`.
- Non-generic shot progression examples: `references/good_shotlist_examples.md`.
- Storyboard image quality, art-direction translation, and reference-to-world transformation are governed by `references/world_class_tvc_principles.md`, `references/director_kernel.md`, and `references/shot_spec_template.md`; do not impose a fixed sketch, wash, or house style unless the user supplies one.
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

Every shot plan must include reference parity decisions. If a storyboard sheet only
resembles the reference by keywords, not hierarchy, depth, light, material, or
visual restraint, treat it as a failure.

Reference parity is not enough. Every run using reference images must also
include a structured `reference_deconstruction`:

- `references[]`: one entry per supplied reference image with observed visual
  facts, transferable principles, forbidden surface-copy elements, and the
  accountable agent owner;
- `source_image_dna`: composition, light/material logic, negative space, and
  motion implications;
- `creative_translation`: what is borrowed, transformed, rejected, and the new
  advertising mechanism created from the reference DNA;
- `literal_copy_risks`: concrete ways the storyboard could collapse into
  repeated surface extraction;
- `agent_responsibility`: what the creative director, art director,
  screenwriter, and director each must veto.

Failure ownership is explicit:

- `creative_director_agent` owns the concept leap and must reject literal
  reference extraction presented as an idea;
- `art_director_agent` owns material, color, negative-space, and surface-copy
  vetoes;
- `screenwriter_agent` owns semantic progression: every beat must change
  information, desire, product role, or viewer question;
- `director_agent` owns shot-function variety, panel aspect, camera motivation,
  and the final rejection of repetitive compositions.

Every storyboard shot must include `reference_transform` and
`shot_function_signature`. A shot whose function is just another glamour
surface reveal, product angle, or color-pressure variant is a failure even if
the camera angle, scene name, or prose changes.

## Category Intelligence And Role Gates

Before concept lock, identify the category logic. At minimum, decide whether
the work behaves like `premium beauty`, `premium skincare`,
`fast-moving consumer goods`, `luxury goods`, or a hybrid. Each role must then
write category-specific evidence rather than generic luxury language:

- `category truth`: what the buyer already believes about the category and what
  the film must challenge, intensify, simplify, or make desirable;
- `purchase ritual`: the tactile or social behavior around discovery,
  inspection, use, replenishment, gifting, display, or status;
- `shelf memory`: the silhouette, color block, package geometry, gesture, or
  end-frame memory that should survive after the video;
- `ritual proof`: the visible action, material response, ingredient behavior,
  skin/hair/object interaction, or use moment that makes the promise credible;
- `brand altitude`: whether the film should behave as mass desire, premium
  proof, luxury restraint, clinical authority, sensual fantasy, or cultural
  object.

Role gates are accountable:

- `creative_director_agent` must turn category truth into a fresh advertising
  premise, not a mood board. It owns the leap from reference DNA to commercial
  desire.
- `screenwriter_agent` must make every beat change information, desire,
  product role, purchase ritual, or shelf memory.
- `director_agent` must design `lens progression`, `transition grammar`,
  `edit bridge`, motivated camera path, coverage strategy, and
  shot-to-shot causality before approving a storyboard.
- `art_director_agent` must transform references into a new material world:
  reference-to-world transformation, invented scene architecture, prop logic,
  material system, category-coded restraint, and set-piece invention.
- `google_omni_prompt_expert_agent` must preserve the approved category,
  product, camera, transition, and material contracts inside concise segment
  prompts rather than flattening them into a montage.

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
not let a global product lock turn a dynamic contact sheet into a wall of packshots.

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
python3 scripts/route_project.py intake.json > 00_route_decision.json
```

The route decision may include:

```yaml
cinematic_language_reference_required:
cinematic_language_triggers:
cinematic_language_depth:
recommended_references:
requested_video_aspect_ratio:
aspect_ratio_source:
aspect_contract:
```

If `cinematic_language_reference_required` is `true`, read
`references/cinematic_language_decision_matrix.md` before finalizing the shot
plan. If it is `false`, do not load that reference merely because the brief says
`cinematic`, `premium`, or `film look`; solve those with the normal shot-spec
grammar and reference parity rules.

Default duration logic:

- infer `duration_seconds` from structured intake first, then brief text such
  as `10s`, `20秒`, `40s`, `60秒`; if still unknown, default to 30s and mark
  `duration_missing_defaulted`;
- infer `video_segment_seconds` from structured intake first, then brief text
  such as `10s/段`; for Google Omni speed runs normalize generation units to
  10s so a 30s film routes to 3 generations unless the user explicitly chooses a
  different backend workflow;
- route decisions must not estimate storyboard panel count, grid layout, or
  shots per segment. Those fields belong only in `02_shot_plan.json` after
  creative concept, timecoded script map, and director approval;
- when the user specifies `9:16`, `16:9`, `1:1`, `4:5`, `3:4`, `1080x1920`,
  vertical, portrait, horizontal, landscape, 竖屏, or 横屏, carry the normalized
  `requested_video_aspect_ratio` into the route, shot plan, storyboard prompts,
  and video prompt JSON;
- for the Google Omni speed path, `storyboard_sheet_count` equals
  `video_segment_count`: each executable 10s segment gets one dynamic N-panel
  storyboard sheet and one JSON temporal prompt. N is director-decided from the
  approved script, not from duration or tempo presets;
- `panel_count` equals the final director-planned shot/cut count from the
  approved script map. `panels_per_sheet`, `grid_layouts`, and
  `shots_per_video_segment` must be declared by the director in the shot plan
  and may be uneven across segments;
- video segment count = `ceil(duration_seconds / video_segment_seconds)`, with
  default segment length 10 seconds for Omni speed runs;
- each video segment receives its mapped source-shot range and internal shot
  timing in the video prompt JSON.

Storyboard panels are shot/cut planning units, but not generation calls. Do not
hard-code any grid count for any duration. Do not turn panels into separate
generations. For Omni speed runs, one generation segment can contain multiple
mapped panels when the JSON supplies internal shot timing, transitions, and
source-shot intent.

Backend capability matters:

- `google_omni` / `google_flow`: default speed path, up to 10s multi-shot
  temporal segments. Use product identity reference plus the selected segment
  source-shot range; the storyboard sheet is a director overview.
- `veo_api` / `runway`: treat as single-scene or low-cut segment backends unless
  a newer capability is explicitly available. Do not rely on dense contact
  sheets as the sole model-facing input.
- `kling`: can use structured multi-shot controls when available.
- `luma`: prefer discrete keyframes/multi-keyframes over a dense overview sheet.

Examples:

- 10s Omni speed run: 1 executable segment, 1 dynamic N-panel storyboard sheet,
  1 JSON prompt; the director decides N after the script map.
- 30s Omni speed run: 3 executable segments, 3 dynamic N-panel storyboard
  sheets, 3 JSON prompts; each sheet can have a different panel count.
- 60s Omni speed run: 6 executable segments, 6 dynamic N-panel storyboard
  sheets, 6 JSON prompts; panel distribution is uneven when the story demands
  uneven rhythm.

Production modes:

- `standard_fast`: one route, one shot plan, automated validation, internal revision if needed, then prompts and final QC.
- `rush`: shortest valid path; no optional sub-agent review.
- `premium_pitch`: add deeper reference parity, stronger motif discipline, and a fuller QC report.
- `production_handoff`: approved keyframes, segment-level keyframe packets,
  multi-backend bidding, edit/sound/color assumptions, and clip QC/failure log
  readiness.
- `certification`: run offline audit and package verification before claiming completion.

Escalate when references conflict, regulated or likeness-sensitive claims appear,
the user asks to imitate a living artist or brand campaign too closely, product
identity is unclear, or generation visibly breaks identity, panel separation, or
the approved art-direction and storyboard-readability contract.

## Shot Planning

Every panel must become a keyframe shot spec with the fields from
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
reference_transform:
shot_function_signature:
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
camera is there, what story beat changes from the prior shot, what is in
foreground / midground / background, and what must not drift. Do not use adjectives such as
`cinematic`, `luxury`, `premium`, or `beautiful` as substitutes for staging,
lens relation, action, material behavior, or continuity facts.

`shot_function_signature` must include `information_delta`, `desire_delta`,
`product_role_delta`, `event_type`, `camera_relation_key`,
`reference_transform_id`, and `redundancy_risk`. This is the semantic
anti-repetition contract: the director may echo a motif, but cannot repeat the
same shot function with new adjectives.

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
dynamic-N product sheet must also preserve product visibility rhythm, scaled to
the actual panel count:

- avoid full-visible packshot walls unless the user explicitly requests a
  catalog, listing, SKU, e-commerce, or packshot-only board;
- include `not_visible` origin/world/benefit/metaphor shots when the story needs
  a world or benefit before product authority;
- include `detail_only` or `partial_visible` transition/proof shots when they
  help preserve product identity without repeating the same full package;
- include non-product-led panels when the product lock would otherwise consume
  every composition;
- make the first full-visible product reveal earned by the script, not by a
  fixed panel number.

## Validation Gates

For shot plans:

```bash
python3 scripts/validate_shot_plan.py 02_shot_plan.json
```

The shot-plan gate checks structural variety, required shot fields, product
identity locks, creative concept, scene arenas, dramatic events, visual
mechanisms, exact visible text carry-through, full-visible product facts,
forbidden visual additions, and avoid-list discipline.

For Google Omni video segment JSON:

```bash
python3 scripts/validate_video_segments.py 08_google_omni_video_prompts.json
```

For completed run directories:

```bash
python3 scripts/validate_run_package.py <run_dir> > 10_run_package_validation.json
```

Do not claim a product storyboard/video package is final until the relevant
validators pass or the remaining validation gap is explicitly reported.

For package certification:

```bash
python3 scripts/verify_skill_package.py <skill_dir>
```

## Shadow Observer

Use the Shadow Observer as a non-blocking sidecar. It logs failure evidence and
candidate rules; it does not block normal production and does not automatically
mutate the skill.

Append events when useful:

```bash
python3 scripts/observe_run.py append --run-dir <run_dir> --stage <stage> --event-type <type> --severity <level> --failure-codes <code> --evidence "<evidence>"
```

Use `references/observer_protocol.md`, `references/observer_event.schema.json`,
and `references/rule_candidate.schema.json` for event and candidate-rule shape.

## Storyboard Image Generation

Generate the actual storyboard bitmap image with Codex image generation when
the tool is available. Use one image generation call per sheet, not all sheets
in a single call. Do not expose storyboard prompt text as a final deliverable
unless image generation is unavailable; keep it as an internal artifact.

Each internal sheet prompt must contain:

- declared dynamic grid instruction selected by the director for that sheet's
  actual N panels;
- `Aspect Contract`: final video aspect ratio, sheet canvas aspect ratio, and
  the rule that every panel/cell must match the final video ratio;
- the exact declared number of panel descriptions with shot IDs;
- every panel line must include `[aspect_ratio: <requested_video_aspect_ratio>]`;
- per-panel camera angle, shot size, subject/action, and depth layers;
- reference parity decisions;
- product identity lock when a product appears;
- approved art-direction block derived from category strategy and references;
  do not force a fixed sketch, wash, pencil, or house style;
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

Base image-style rule:

```text
Use the approved art-direction language from the shot plan. If the user does
not supply a visual finish, create a clean production storyboard image whose
first job is legible shot design: clear panel boundaries, readable camera
angle, shot size, subject/action, foreground/midground/background, product
identity, and transition intent. Do not impose a fixed sketch aesthetic, color
wash, pencil imitation, or decorative house style.
```

## Google Omni Video Prompts

Create video prompts by temporal segment, not by storyboard sheet or individual
generation-per-panel. Every segment must be a paste-ready motion contract with
first frame, last frame, controlled story beats/source shots, camera plan,
cut strategy, subject motion, environment motion, motion continuity, continuity
lock, visual style, anti-plastic constraints, and negative constraints. Any
multi-shot segment must include explicit `internal_shots` with time spans,
camera states, transitions, and purposes.

For each segment, keep the final prompt concise. The internal JSON can be
structured and strict; the paste-ready prompt should be natural language that
states what moves, how the camera moves, how the scene changes over time, which
mapped source shots it covers, and which identity/material facts must stay
locked. Do not paste the whole contact sheet as a generic montage; use only the
segment's source-shot range.

For product video, start the prompt file with `Required Reference Setup` and
`Product Identity Lock`. The user product original, packshot, or multi-angle
image is the highest-priority `product_identity` reference. Style references may
control lighting, environment, camera mood, props, rhythm, and lens language,
but must not change package geometry, cap/pump/closure, label layout, visible
text/logo/mark, embossed or relief marks, color bands, materials, proportions,
or real component inventory.

Carry the same `product_identity_lock` from the shot plan into video prompt
JSON and into every paste-ready product-visible segment. Product-visible
segments must include `product_visibility`, `product_identity_reference`, and
`product_motion_rule`. Full-visible product segments must also include
`visible_product_text_or_marks`, `product_visual_facts`, and
`forbidden_visual_additions`.

When a segment is pasted into Google Omni, include the required reference setup,
the full product identity lock, and the selected segment together. A segment
without the lock is underspecified and may drift into a generic mood object.

Video prompts must carry `requested_video_aspect_ratio` at the JSON root and
`aspect_ratio` on each segment. The paste-ready segment prompt must state the
same vertical/portrait/horizontal framing contract; do not rely on a storyboard
sheet to imply output dimensions.

Do not instruct the user or video model to upload the storyboard sheet as the
sole input for a full 30-second generation. Use the storyboard sheet as a visual
planning reference only when the tool supports reference images; the executable
video input is the product identity reference plus the selected temporal segment
prompt, its source-shot range, and its lock. If a platform only accepts one
image and one prompt, prefer the product identity reference over the storyboard
contact sheet for product ads.

## Required Internal Artifacts And Final Deliverables

Use a run directory with stable names:

```text
run_dir/
  00_route_decision.json
  01_reference_roles.md
  02_shot_plan.json
  03_director_qc.json
  04_storyboard_image_prompts.md  # internal fallback/prompt trace
  05_agent_orchestration.json
  storyboard_sheet_01.png
  storyboard_sheet_02.png  # only when route asks for a second sheet
  08_google_omni_video_prompts.md
  08_google_omni_video_prompts.json
  09_final_qc_report.md
  10_run_package_validation.json
  11_video_generation_handoff.md
  approved_keyframe_packets/  # required for production_handoff/certification
  _observer/
    events.jsonl
    candidate_rules.json
```

If image generation is not requested or cannot run in the current environment,
still produce the route decision, reference roles, shot plan, storyboard image
prompts, video prompts, run-package validation, and QC summary. The final answer
must report that storyboard bitmap generation could not run, then provide the
internal storyboard prompt path as a fallback.

When image generation succeeds, the final answer must show only the storyboard
image path(s), the Google Omni video prompt path, validation status, and any
hard remaining risk. Do not list route JSON, shot-plan JSON, QC JSON, or
observer files as user-facing deliverables.

## Portability

This skill must remain self-contained. Packaged references, schemas, scripts,
assets, and tests live inside this folder. When root notes or temporary workflow
files change, copy accepted rules into this skill folder, update
`references/source_manifest.json`, run `scripts/verify_skill_package.py`, and
only then publish.
