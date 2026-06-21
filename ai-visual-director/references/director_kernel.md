# Director Kernel

This file contains production-time routing rules. Use it to make strong director decisions before output, not to add slow review loops after output.

## Production Principle

Commercial speed requires most quality to be encoded upstream:

1. classify the job correctly;
2. lock reference roles and continuity;
3. deconstruct reference image visual DNA;
4. choose a proven dramatic arc;
5. choreograph what the viewer sees first, second, and third;
6. enforce shot grammar, depth staging, camera variety, and eye-trace continuity;
7. run a cheap structural gate;
8. escalate only on red flags.

Do not default to multi-review or weighted scoring for routine jobs.

## Runtime Modes

| Mode | Use | Cost | Behavior |
|---|---|---|---|
| `standard_fast` | normal commercial production | low | one route, one shot plan, automated gate, auto-revise once on gate failure |
| `rush` | same-day ideation or rough draft | lowest | route and generate required deliverables only, keep QC summary short |
| `premium_pitch` | high-budget pitch, multiple creative directions | medium | create two route variants, choose one, preserve the rejected direction briefly |
| `certification` | skill release, benchmark suite, explicit audit request | high | run audit schema, weighted score, adversarial review, regression cases |

## Escalation Triggers

Escalate from `standard_fast` to `premium_pitch` or `certification` only if:

- reference images conflict about product identity, person identity, location, or first-frame composition;
- target duration, platform, or deliverable type is missing and changes the route;
- the user asks for a launch campaign, major client pitch, or multiple creative territories;
- the user requests regulated benefit claims, medical/financial/legal proof, celebrity likeness, or close brand imitation;
- the structural gate fails twice;
- generated sheets break product/character identity, panel separation, or blue-gray previs style.

## Route Playbooks

### Premium Product Ad

Default arc is not a shot list. Start with a story engine:
origin pressure -> first rule violation -> partial product inevitability ->
material/use proof -> benefit metaphor -> final authority.

Before shot planning, define `story_engine` and then the creative concept.
Product beauty is not a concept. A premium product ad must have:

- an `advertising_logline` that sells the idea, not the product category;
- a `dramatic_question` that names what is withheld, crossed, awakened,
  transformed, or resolved;
- a `product_role` that explains why the product becomes inevitable without
  appearing in every panel;
- a `duration_design` that maps story beats to seconds, storyboard keyframes,
  and Omni/Veo segments;
- `anti_plastic_rules` grounded in material, lens, light, shadow, texture, and
  physical detail;
- a `big_idea` that can be pitched in one sentence;
- an `audience_desire` beyond "looks premium";
- a `story_tension` such as withholding, awakening, crossing a threshold,
  transformation, or return;
- a `world_rule` that decides how images behave;
- a `visual_mechanism` that motivates reveals and cuts;
- a `scene_ladder` with at least three distinct arenas or phases;
- at least three `signature_images` that are not all product details.

Weak concept pattern: petals -> glass -> cap -> label -> packshot. This is
ingredient/product coverage, not advertising direction. Upgrade it into a
sceneable world: a greenhouse threshold, mirrored corridor, rain-lit elevator,
skin-ripple table, silk veil, window reflection, or another invented arena
motivated by the references and brand promise.

Duration arcs:

- 10-15s: one world rule, one earned reveal, one tactile proof, one final identity.
- 20-30s: origin/reveal, texture/use, benefit/payoff.
- 40s: slow discovery 0-10, tactile proof 10-20, use/benefit 20-30, authority 30-40.
- 60s: add a second turn or human/world response; do not add more product angles.

Dynamic N-panel segment storyboards:

1. creative director proposes creative concept candidates from the product image,
   visual/style references, platform, duration, and backend constraints;
2. director, screenwriter, and art director run a structured veto review and
   produce one `director_resolution`;
3. screenwriter writes the `timecoded_script_map` for the exact requested
   duration;
4. director approves the script map and decides `panel_count`,
   `panels_per_sheet`, `grid_layouts`, and `shots_per_video_segment`;
5. for the Google Omni speed path, create one dynamic N-panel storyboard sheet
   per executable 10-second segment. N can differ by segment.

The route never infers panel count, shot count, or grid layout from duration or
tempo. Those values live in `02_shot_plan.json` only after the script map and
director resolution exist.

For executable AI video handoff, separate:

- dynamic N-panel segment storyboard sheets for story rhythm and visual memory;
- source-shot ranges or model-facing keyframes for each executable generation
  segment;
- temporal video prompts: `ceil(duration_seconds / video_segment_seconds)`,
  normalized to 10-second Google Omni units for speed runs unless a different
  backend workflow is explicitly selected.

Minimum shot mix per sheet: 1 establishing, 2 macro/insert, 1 hero product angle, 1 movement bridge, 1 payoff.

Product visibility rhythm is mandatory for real product storyboards. The
product lock preserves facts only when the product is visible; it must not make
every panel a full bottle view.

Per non-catalog dynamic-N sheet:

- avoid full-visible packshot walls unless the brief explicitly says catalog,
  listing, SKU, e-commerce, or packshot-only;
- include `not_visible` origin/world/benefit/metaphor shots when the script
  needs world or benefit proof before product authority;
- include `detail_only` or `partial_visible` transition/proof shots when they
  protect identity without repeating the same full package;
- include non-product-led panels when the product identity lock would otherwise
  consume every composition;
- the first full-visible reveal should be earned by story logic, not by a fixed
  panel position.

Use this default visibility arc unless the brief gives a stronger one:

```text
not_visible -> detail_only -> partial_visible -> full_visible ->
detail_only -> partial_visible/use -> not_visible/benefit ->
partial_visible/return -> full_visible payoff
```

Every panel also needs:

- `scene_arena`: the visual place or world of the panel;
- `scene_role`: the panel's commercial function;
- `dramatic_event`: the on-screen event or transformation;
- `visual_mechanism`: how the world rule makes this image happen.

Per dynamic-N sheet, use at least 3 distinct `scene_arena` values, 3 distinct
`visual_mechanism` values, and 4 distinct `scene_role` values when the sheet is
long enough; scale down for shorter sheets. If the sheet can be summarized as
"more macro details of the same object with different crops", it is still a
failure even when product visibility counts pass.

Forbidden defaults: centered product packshot walls, repeated eye-level table shots, abstract luxury language without visible proof.

### Beauty Or Fashion

Default arc: identity -> material/tactile detail -> application/gesture -> transformation -> beauty payoff.

Minimum shot mix: identity medium shot, profile or 3/4 beauty angle, hand/skin/material macro, mirror or touch action, movement/pose shot, payoff.

Forbidden defaults: beauty portrait repetition, over-detailed faces in storyboard sketch mode, random wardrobe drift.

### Narrative Or Surreal

Default arc: normal baseline -> anomaly reveal -> scale/stakes proof -> reaction -> consequence -> emotional payoff.

Minimum shot mix: normal-scale establishing shot, subjective discovery shot, low/high scale-proof shot, reaction close-up, wide payoff.

Forbidden defaults: showing the anomaly before baseline, asserting scale without objects, destruction fantasy unless requested.

### Food Or Beverage

Default arc: ingredient origin -> preparation action -> texture proof -> serving context -> appetite payoff.

Minimum shot mix: ingredient macro, process action, texture insert, human hand/use shot, final serving hero.

Forbidden defaults: generic table beauty shots, no process, no texture proof.

### Architecture Or Space

Default arc: spatial establish -> material detail -> human scale -> circulation -> hero reveal.

Minimum shot mix: wide spatial shot, low/high perspective, material insert, human scale reference, final perspective hero.

Forbidden defaults: empty showroom repetition, no human scale, no circulation logic.

### Tech Or Science

Default arc: problem -> mechanism -> proof visualization -> human use -> clean payoff.

Minimum shot mix: problem setup, UI/device/product hero, mechanism insert, proof visualization, human use, clean result.

Forbidden defaults: fake hologram overload, unreadable interfaces, claims without visual mechanism.

## Attention Choreography

Every shot must define:

- `attention_order`: first read, second read, third read;
- `eye_trace`: where the gaze enters, travels, and exits;
- `depth_strategy`: how foreground, midground, and background stage the idea;
- `reference_parity`: which reference qualities survive in this shot.

Across cuts:

1. keep emotional or product meaning above spatial cleverness;
2. make every cut advance story, proof, or desire;
3. vary rhythm by beat, not randomly;
4. preserve or deliberately redirect eye trace;
5. keep the 2D screen position legible;
6. preserve 3D geography unless disorientation is intentional.

For TVC work, the viewer's first read should usually be the product, face, ingredient, action, or benefit metaphor. If the first read is background decor, the shot is probably weak.

## Reference Parity

Reference parity is not "same style." It is the transfer of visual intelligence:

- hierarchy: what is visually dominant and why;
- depth: how layers create premium space;
- light: what edge, reflection, shadow, or softness creates value;
- material: what surfaces prove quality;
- restraint: what is left out;
- motion implication: where the shot wants to move next.

For each reference image, classify it as product identity, character identity, motif, environment/material language, style, first-frame composition, or negative reference. Then decide what must preserve and what may ignore. Do not average references into a generic image.

## Fast Gate Philosophy

The fast gate checks structure, not taste. It should catch:

- no camera variety;
- no shot purpose;
- no foreground/midground/background staging;
- no establishing or macro/detail shots;
- repeated centered static compositions;
- missing continuity locks.

If the gate fails once, revise internally and rerun. If it fails twice, escalate.
