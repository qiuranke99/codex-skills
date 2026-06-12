# 01_shot_spec_template.md

Knowledge file for `Storyboard Shot Planner`.

This file defines the stable shot-spec grammar for cinematic shot planning and storyboard handoff. It avoids temporary role labels and can be used with human storyboard artists, downstream storyboard generators, previs systems, cinematographers, image/video systems, or production teams.

## 1. Purpose

`Storyboard Shot Planner` turns a story, script, commercial idea, scene description, reference image, or revision note into a professional cinematic shot list and clean handoff specs.

This is not a production call sheet, not a camera-department equipment order, and not a finished image-generation prompt. It is a compact visual-planning document whose job is to make every shot drawable, legible, continuous, director-motivated, sequence-aware, and ready for handoff.

A strong spec must answer four questions:

1. What must the viewer understand in this shot?
2. Why is the camera here, at this size and angle?
3. Why does this shot cut from the previous shot and into the next shot?
4. What must remain stable so the downstream artist or generator does not drift?

## 2. Stable Terminology

Use long-term, migration-safe terms.

Preferred terms:

- `the planner`
- `shot planner`
- `Storyboard Shot Planner`
- `downstream storyboard generator`
- `storyboard artist`
- `previs artist`
- `image/video system`
- `production handoff`
- `storyboard handoff`

Avoid temporary or workflow-bound terms:

- numbered model-role labels
- temporary tool-role labels
- tool-specific generator names unless the user provides them
- model names, sampler settings, seeds, CFG, LoRA, ControlNet, render engine syntax, or image-generation parameters unless explicitly requested

## 3. Hard Output Boundary

The planner must:

- break the brief into story beats and shot logic;
- choose shot size, camera angle, lens feel, camera movement, composition, action, blocking, POV, cut logic, rhythm, and continuity constraints;
- preserve scale relationships, screen direction, geography, axis, eyeline, character identity, product identity, product state, prop state, and visual priorities;
- make each shot drawable as one rough storyboard panel;
- produce a readable shot list and clean handoff specs.

The planner must not:

- generate images;
- write full image-generation prompts unless explicitly requested;
- decide final sketch or render style unless the user asks for style planning;
- add rendering-engine syntax or model-specific parameters;
- bury shot logic under adjectives such as `cinematic`, `beautiful`, `epic`, `premium`, or `dramatic` without concrete frame instructions;
- invent extra plot, characters, brands, dialogue, claims, or lore unless required for visual readability.

Downstream storyboard or image systems handle:

- final sketch style;
- prompt construction;
- rendering or sketch generation;
- visual iteration after the shot logic is approved.

## 4. Director Decision Layer

Before writing a shot list, silently diagnose the scene. Do not expose the full diagnosis unless the user asks. Use the diagnosis to make director-level choices.

### Silent diagnosis

- `input_type`: script, scene description, ad concept, product demo, dialogue scene, action scene, suspense scene, montage, fast-cut ad, reference-image conversion, single frame, or revision.
- `core_visual_event`: the one thing the viewer must understand.
- `dramatic_change`: what changes from first shot to final shot: knowledge, emotion, power, scale, product state, physical danger, desire, clarity, or decision.
- `viewer_alignment`: objective, character-aligned, direct POV, OTS subjective, omniscient, witness camera, product-functional, surveillance, memory/dream.
- `information_strategy`: what appears first, what is delayed, what is hidden, what is revealed by action, and what must be clear before the next cut.
- `visual_anchor`: the strongest or most necessary shot in the sequence.
- `spatial_geography`: subject positions, camera side, entrances/exits, movement direction, background landmarks.
- `axis_and_eyeline`: axis of action, screen side, left/right relation, eyeline match, whether crossing the axis requires a reset.
- `blocking`: actor position, body orientation, gaze, hand action, prop interaction, start/end marks.
- `rhythm`: where to hold, accelerate, use inserts, reset to wide, or resolve.
- `continuity_anchors`: character, wardrobe, hairstyle, product shape, product state, prop state, location, light direction, screen direction, scale.
- `redundancy_risk`: repeated size, angle, subject, information, or emotional beat.

### Director priority order

1. Viewer comprehension.
2. Dramatic function.
3. POV and audience alignment.
4. Spatial continuity.
5. Blocking and performance.
6. Edit logic.
7. Rhythm.
8. Scale and visual proof.
9. Composition and lens feel.
10. Style.

Style is last. Style must never override readability, continuity, axis, eyeline, product clarity, or the user’s explicit requirements.

## 5. Core Shot Rules

Every shot must have one main visual job.

Strong shot purposes include:

- establish geography;
- establish baseline;
- introduce subject;
- reveal;
- withhold;
- subjective discovery;
- prove scale;
- prove product function;
- show obstacle;
- show contact;
- show reaction;
- show consequence;
- reset geography;
- shift power;
- shift POV;
- increase tension;
- release tension;
- compress time;
- punctuate rhythm;
- resolve the beat.

Weak shot purposes include:

- make it cinematic;
- make it emotional;
- show the vibe;
- beauty shot;
- cool angle;
- epic reveal;
- premium mood.

Every shot after `SH_001` needs `cut_logic`. The cut should add new information, change POV, prove a detail, show a reaction, reset geography, escalate, punctuate rhythm, or resolve consequence.

Every moving shot needs `panel_moment`: the exact drawable moment in the storyboard panel. Use `start frame`, `middle action frame`, `end frame`, or `decisive action moment`.

## 6. Field Priority for Handoff

If a response must be shortened, preserve fields in this order:

1. `SH_###`
2. `scene`
3. `dramatic_beat`
4. `shot_purpose`
5. `shot_size`
6. `camera_angle`
7. `main_subject`
8. `main_action`
9. `blocking`
10. `body_pose`
11. `composition`
12. `foreground`, `midground`, `background`
13. `pov_alignment`
14. `axis_of_action`, `screen_direction`, `eyeline`
15. `cut_logic`
16. `panel_moment`
17. `scale_reference`
18. `continuity_lock`
19. `camera_movement`
20. `lens_feel`
21. `must_preserve`
22. `avoid`
23. `duration`
24. `aspect_ratio`

Rationale: the downstream artist or generator must know what to draw, where the viewer is, what action is happening, and what cannot drift before it needs aesthetic or technical refinements.

## 7. Standard Shot Spec Fields

| Field | Definition | Good | Weak |
|---|---|---|---|
| `SH_###` | Stable shot ID for revision. | `SH_004` | `next shot` |
| `aspect_ratio` | Frame ratio if relevant. | `9:16 vertical` | `cinematic` |
| `scene` | Place, time, and story beat context. | `rainy Tokyo crossing, first scale reveal` | `city` |
| `duration` | Timing, required for timed ads or animatics. | `1.2s`, `hold 3s` | `short` |
| `dramatic_beat` | What changes or what this shot does emotionally/narratively/persuasively. | `viewer realizes the street is now tiny below her` | `emotional moment` |
| `shot_purpose` | Why this shot exists in the sequence. | `prove giant scale through taxi-to-shoe comparison` | `make it epic` |
| `shot_size` | Subject scale in frame. | `medium close-up`, `extreme wide shot`, `insert` | `35mm shot` |
| `camera_angle` | Camera position relative to subject. | `low street-level angle looking up from taxi bumper` | `dramatic angle` |
| `lens_feel` | Perceived spatial behavior, not equipment fetish. | `24mm wide feel, strong foreground exaggeration` | `ARRI 28mm f/1.4` |
| `camera_movement` | Static state or motivated move. | `locked-off`, `slow dolly-in`, `tilt-down reveal` | `dynamic camera` |
| `cut_logic` | Why this shot follows the previous shot. | `reaction cut after she sees the tiny taxis` | `another angle` |
| `panel_moment` | Which instant the storyboard panel should draw. | `decisive moment: foot hovering above taxi row` | `during movement` |
| `pov_alignment` | Viewer’s alignment. | `character-aligned discovery`, `objective wide`, `product-functional insert` | `cinematic POV` |
| `axis_of_action` | Spatial axis for action/dialogue. | `axis runs table-left to table-right between two characters` | `same axis` |
| `screen_direction` | Movement or geography direction on screen. | `girl moves left-to-right until SH_004` | `moving around` |
| `main_subject` | Primary drawable entity. | `teen girl in navy school uniform with red ribbon` | `a person` |
| `main_action` | Visible action at key moment. | `she lowers her gaze toward tiny taxis below` | `she realizes something` |
| `blocking` | Position and movement in space. | `standing on crosswalk center, shoulders turned toward traffic, left hand near chest` | `standing there` |
| `body_pose` | Pose, gesture, gaze, weight, hand state. | `knees bent, arms out, eyes down, mouth slightly open` | `surprised` |
| `eyeline` | Direction of gaze and match target. | `eyes down-right toward crane on pavement` | `looks emotional` |
| `composition` | Visual hierarchy and subject placement. | `shoe dominates lower foreground; body rises center; buildings frame sides` | `nice composition` |
| `foreground` | Closest visible layer. | `taxi hood and wet crosswalk stripe` | `foreground stuff` |
| `midground` | Main action layer. | `giant shoe, stopped taxis, tiny pedestrians` | `subject` |
| `background` | Distant environment. | `vertical neon signs and high windows behind shoulders` | `background city` |
| `scale_reference` | Objects that prove size/distance. | `shoe equals taxi length; pedestrians thumb-sized near curb` | `huge` |
| `continuity_lock` | Recurring details that must remain consistent. | `same red ribbon, navy uniform, rainy left-to-right street direction` | `same as before` |
| `must_preserve` | Non-negotiable facts. | `label faces camera; cap stays black; screen text remains short` | `quality` |
| `avoid` | Specific failure modes. | `avoid extra bottles, fake logos, destroyed buildings, axis flip` | `avoid mistakes` |

For real product work, product packaging is identity. If the user provides a product image, add two shot-level decisions whenever the product appears:

| Field | Definition | Good | Weak |
|---|---|---|---|
| `product_visibility` | Whether the product appears in this shot. Use `full_visible`, `partial_visible`, `detail_only`, or `not_visible`. | `full_visible` | `visible` |
| `product_identity_action` | How this panel preserves the locked product shape, label, text, logo/mark, cap/pump, colors, and proportions. | `front label faces camera; draw LUMA wordmark, HYDRATING SERUM line, pale blue stripe, black cap` | `same product` |

## 8. Clean Handoff Spec: Exact Field Order

Use this format when the user says `给手绘分镜用`, asks for clean handoff specs, or needs specs for a storyboard artist/generator.

```yaml
SH_001
aspect_ratio:
scene:
duration:
dramatic_beat:
shot_purpose:
shot_size:
camera_angle:
lens_feel:
camera_movement:
cut_logic:
panel_moment:
pov_alignment:
axis_of_action:
screen_direction:
main_subject:
main_action:
blocking:
body_pose:
eyeline:
composition:
foreground:
midground:
background:
scale_reference:
continuity_lock:
must_preserve:
avoid:
```

For `SH_001`, `cut_logic` may be `opening orientation`, `opening hook`, or `opening baseline`.

Use `not applicable` only when a field genuinely does not apply, such as `eyeline` in a product-only insert or `axis_of_action` in a static packshot.

Do not use `same as previous`. Repeat the actual locked details in `continuity_lock`.

## 9. Photoreal Previs Extra Fields

When the user says `给真实预演用`, use the clean handoff spec above and add these fields after `avoid`:

```yaml
camera_height:
camera_start_position:
camera_end_position:
actor_start_position:
actor_end_position:
entry_exit:
practical_constraints:
vfx_or_scale_note:
```

Previs needs physical clarity: camera height, camera path, actor marks, entrances/exits, usable movement path, and practical/VFX constraints.

## 10. Default Shot List Table

Use this table before clean handoff specs unless the user asks for handoff specs only.

```markdown
| Shot ID | Director Beat | Shot Purpose | Shot Size | Camera Angle | Lens Feel | Camera Movement | Action / Blocking | Composition / Depth | POV / Axis / Cut Logic | Scale / Continuity |
|---|---|---|---|---|---|---|---|---|---|---|
| SH_001 | | | | | | | | | | |
| SH_002 | | | | | | | | | | |
| SH_003 | | | | | | | | | | |
```

Column rules:

- `Director Beat`: the dramatic, persuasive, or informational beat.
- `Shot Purpose`: why the shot exists now.
- `Action / Blocking`: visible action, pose, gaze, hand action, prop relation, and movement path.
- `Composition / Depth`: subject placement plus foreground/midground/background when useful.
- `POV / Axis / Cut Logic`: viewer alignment, spatial axis/screen direction, and reason for the cut.
- `Scale / Continuity`: scale proof, wardrobe, product state, prop state, geography, or continuity lock.

## 11. Single-Shot Template

Use when the user asks for one frame or one storyboard panel.

```markdown
## Shot Spec

| Field | Value |
|---|---|
| Shot ID | SH_001 |
| Director Beat | |
| Shot Purpose | |
| Shot Size | |
| Camera Angle | |
| Lens Feel | |
| Camera Movement | |
| Panel Moment | |
| POV / Axis | |
| Main Subject | |
| Main Action / Blocking | |
| Composition / Depth | |
| Scale / Continuity | |
| Avoid | |
```

## 12. Sequence Templates

### 12.1 Compact four-shot sequence

Best for a compact beat: setup, discovery, proof, payoff.

| Shot ID | Purpose | Required logic |
|---|---|---|
| SH_001 | Establish geography and baseline | Show normal space/action before the change. |
| SH_002 | Reveal anomaly/product/emotional turn | Move closer or shift POV; make new information readable. |
| SH_003 | Prove change through action/detail | Use body action, object interaction, insert proof, or scale reference. |
| SH_004 | Payoff/reaction/consequence | Resolve the beat with a readable final image. |

Minimum requirements: at least one geography shot, one readable detail or proof shot, continuity lock, and scale references when scale matters.

### 12.2 Dialogue coverage template

Use for two-person or multi-person dialogue. Do not create random singles.

| Stage | Function | Notes |
|---|---|---|
| Master / medium wide | Establish geography and left/right relationship | Defines axis and eyelines. |
| OTS or clean single A | Align with speaker/listener A | Use when A controls or receives key information. |
| Reverse OTS or clean single B | Maintain eyeline and axis | Do not flip left/right without reset. |
| Reaction | Show listener’s change | Use when listening changes the scene. |
| Insert | Prove object/detail | Use only if object changes meaning. |
| Power-shift close-up | Mark decision, threat, lie, intimacy, silence, or reversal | Close-up must be earned. |
| Exit / consequence | Resolve or complicate the beat | Shows what the exchange caused. |

### 12.3 Commercial sequence template

Best for product, beauty, tech, service, food, or fashion.

| Shot ID | Purpose | Notes |
|---|---|---|
| SH_001 | Hook | One instantly readable problem, desire, contrast, or promise. |
| SH_002 | Product/hero reveal | Product or core subject identity must be clear. |
| SH_003 | Use-case setup | Human context or practical friction. |
| SH_004 | First operation/action | One visible function or interaction. |
| SH_005 | Proof detail | Mechanism, texture, result, before/after cue, UI, or tactile proof. |
| SH_006 | Human/world response | Show relief, confidence, clarity, or changed situation. |
| SH_007 | Continuity confirmation | Reconfirm product orientation/state if needed. |
| SH_008 | End lock | Clean final frame with no new confusion. |

Do not invent brand names, logos, health claims, medical claims, purification claims, safety claims, or performance claims unless the user provides them.

### 12.4 Fast-cut structure

Best for 10-20 second social ads or rhythm-heavy montage.

| Section | Shots | Function |
|---|---|---|
| Hook | 1-3 shots | Pattern interrupt, problem, contrast, or immediate promise. |
| Setup | 2-3 shots | Context and product/idea entrance. |
| Proof burst | 3-6 shots | Rapid concrete actions, textures, UI states, results. |
| Human/world response | 1-2 shots | Show emotional or spatial effect. |
| End lock | 1-2 shots | Product/idea identity and final clarity. |

Rules: every shot has one visual job; inserts are punctuation, not filler; repeat no shot size more than three times in a row unless deliberate; final shots should visually simplify.

### 12.5 Suspense reveal template

| Stage | Function | Notes |
|---|---|---|
| Baseline | Establish normal space or behavior | Make the anomaly detectable. |
| Withhold | Show partial information | Keep geography readable. |
| Discovery | Choose character POV or audience omniscience | Decide who knows first. |
| Proof insert | Show object/sound/source/detail | Must be drawable. |
| Reaction | Show embodied response | Gaze, stillness, hand tension, breath, retreat. |
| Consequence | What changes after discovery | Do not end on vague fear. |

### 12.6 Reference image conversion

Use when the user supplies one or more reference images.

```markdown
## Reference Image Extraction

- function:
- visible subject(s):
- shot size:
- camera angle:
- lens feel:
- composition:
- foreground:
- midground:
- background:
- pose / gesture:
- scale relationships:
- continuity elements to preserve:
- elements to ignore or reinterpret:
```

Rules:

- Separate observed facts from interpretation.
- Do not treat every reference equally.
- Follow the user-assigned function of each reference.
- If the user wants a sequence from one image, create one anchor shot that stays close to the reference, then derive motivated continuation shots.
- First-frame composition/camera outranks other references only when the user explicitly says it is locked or asks to preserve the reference shot.

Conflict priority:

1. user’s latest explicit instruction;
2. exact shot count and output mode;
3. user-written story, action, product, character, and continuity requirements;
4. user-assigned reference function;
5. first-frame camera/composition only when explicitly locked;
6. character/product/prop identity;
7. location geography, screen direction, axis, and eyeline;
8. style reference;
9. examples in knowledge files.

## 13. Continuity Lock Template

Use whenever the sequence has recurring characters, products, places, or scale.

```markdown
## Continuity Lock

- Character identity:
- Wardrobe:
- Hair / face / body features:
- Product identity:
- Product identity lock:
  - source reference:
  - exact visible product/brand text:
  - primary label text:
  - label layout:
  - packaging shape:
  - cap/pump/closure:
  - color/material marks:
  - required visible marks:
  - forbidden changes:
- Product state:
- Prop positions:
- Environment:
- Axis / screen direction:
- Eyeline rules:
- Lighting / time:
- Scale relationship:
- What may change shot to shot:
- What must not change:
```

Good continuity lock:

- `same navy uniform, red ribbon, wet black loafers, short black bob, no glasses; movement remains left-to-right until SH_004`.
- `same matte charcoal bottle, black cap, vertical filter window facing camera, blue light off until button press in SH_003`.
- `same white cylindrical serum bottle; black cap; centered front label rectangle; exact visible text LUMA / HYDRATING SERUM / 30 ml when label faces camera; no blank bottle, fake brand, new claims, or changed label layout`.

Weak continuity lock:

- `keep consistent`.
- `same vibe`.
- `same product`.
- `label on bottle`.

Product text rule: captions, subtitles, shot numbers, callouts, UI overlays, and invented labels are forbidden. User-provided product packaging text, label blocks, logo/mark shapes, and required visible marks are not forbidden; they must be preserved when the product faces camera. If a reference is too blurry to read, write `unreadable_from_reference` and preserve label geometry rather than inventing text.

## 14. Scale Relationship Template

Use for giants, miniatures, VFX, product macro, architecture, surreal transformations, and distance clarity.

```markdown
## Scale Relationship

- Primary subject:
- Reference object 1:
- Reference object 2:
- Relative size statement:
- Frame proof:
- Avoid:
```

Examples:

- `Primary subject: giant schoolgirl. Reference object 1: taxi. Reference object 2: crosswalk stripe. Relative size: one shoe equals taxi length. Frame proof: taxi bumper aligns beside shoe sole. Avoid: making her only slightly taller than pedestrians.`
- `Primary subject: serum droplet. Reference object 1: fingertip ridge. Reference object 2: bottle pipette. Relative size: droplet half the width of fingernail. Frame proof: droplet suspended between pipette and skin. Avoid: droplet becoming splash or pearl.`

## 15. Readability Checklist

Before final output, verify every shot:

- It can be drawn as one storyboard panel.
- It has one dominant subject.
- It has a visible action or meaningful stillness.
- It has a specific `dramatic_beat` and `shot_purpose`.
- It defines shot size, camera angle, lens feel, and movement/static state.
- It defines panel moment if movement exists.
- It defines blocking, body pose, gaze, hand action, or object state.
- It uses concrete composition and depth layers when useful.
- It includes POV alignment.
- It includes axis, screen direction, and eyeline when relevant.
- It includes scale proof when scale matters.
- It includes continuity lock when a subject recurs.
- For user-provided products, it includes a product identity lock and per-product-shot visibility/action notes.
- It includes specific avoid notes for likely drift.

## 16. Sequence Logic Checklist

Before final output, verify the sequence:

- The first shot orients the viewer unless disorientation is intentional.
- There is a visual anchor.
- Every shot has a distinct job.
- Shot sizes vary by purpose.
- Camera angles change only when information, power, POV, or geography changes.
- Movement is motivated by reveal, pursuit, intimacy, scale, proof, rhythm, geography reset, or subjective instability.
- Each cut gives new information or consequence.
- POV shifts are controlled.
- Axis, eyeline, and screen direction survive shot-to-shot.
- Product/character/prop continuity survives shot-to-shot.
- Inserts function as proof or rhythm punctuation, not filler.
- The final shot resolves, complicates, or deliberately leaves a clear question.

## 17. Revision and Versioning Rules

- Preserve existing `SH_###` IDs whenever possible.
- If inserting a shot, use `SH_003A` or `SH_003B`; renumber only when the user asks for a clean final.
- For major rewrites, label versions: `v1`, `v2`, `v3`.
- For single-shot revisions, repeat only the changed shot plus any updated continuity lock.
- Do not silently change continuity facts.
- If style changes, keep shot logic stable unless style affects frame readability.
- If aspect ratio changes, re-evaluate composition, negative space, and scale references.
- If downstream results drift, strengthen `continuity_lock`, `must_preserve`, `avoid`, `panel_moment`, `axis_of_action`, and `screen_direction`; do not merely add adjectives.

## 18. Common Failure Modes and Corrections

| Failure mode | Symptom | Correction |
|---|---|---|
| Prompt-poetry instead of shot planning | Many adjectives, no camera relation. | Rewrite as shot size + angle + action + composition. |
| Decorative shot | Looks cool but adds no new information. | Assign a dramatic beat or remove it. |
| Repeated information | Same subject, size, and emotion as prior shot. | Change to reaction, proof, geography reset, or consequence. |
| No POV | Viewer alignment is unclear. | Define objective, character-aligned, POV, OTS subjective, witness, or product-functional. |
| Axis flip | Left/right relationship changes accidentally. | Restore axis or add neutral reset/overhead/insert/motivated crossing. |
| Eyeline mismatch | Characters do not look toward the correct target. | Specify screen side and gaze direction. |
| Cut has no reason | Shot exists only as another angle. | Add reveal, match on action, POV shift, reaction, proof, reset, or consequence. |
| Blocking is vague | No body orientation or prop relationship. | Define stance, gaze, hands, movement path, and object relation. |
| Internal emotion | `she feels afraid` without drawable evidence. | Convert to stillness, gaze, breath, hand tension, posture, or object interaction. |
| Scale unproven | Giant/miniature/macro is asserted. | Add familiar reference objects in frame. |
| Product function vague | Product appears but operation is unclear. | Show hand operation, state change, proof detail, and final orientation. |
| Too many camera moves | Every shot pans/dollies/cranes. | Use movement only when it changes information, emotion, geography, or rhythm. |
| Shot buffet | Many cool shots, no progression. | Use establish → reveal → action/proof → reaction → consequence. |
| Reference overfit | Every shot copies one image. | Keep one anchor shot, then derive motivated continuation shots. |
| Style overwhelms readability | Mood words replace staging. | Replace style with camera, blocking, composition, scale, and continuity. |
| Close-up unearned | Generic emotional close-ups. | Use close-up only for decision, reaction, threat, intimacy, discovery, or proof. |
| Foreground blocks action | Main subject hidden by decorative layer. | Identify foreground object and keep main subject readable. |
| Fast-cut lacks rhythm architecture | 15 unrelated quick images. | Divide into hook, setup, proof burst, response, end lock. |
| Dialogue coverage generic | Random singles and close-ups. | Define master, OTS/single, reverse, reaction, insert, power shift, exit. |
| Tool-specific leakage | Specs mention model names or temporary role labels. | Remove tool labels and keep stable visual-planning fields. |
| Panel cannot be drawn | Action spans multiple moments. | Choose decisive frame and write `panel_moment`. |

## 19. Final Output Order

When producing a full answer, use this order:

1. `Assumptions` only if needed.
2. `Continuity Lock` if the sequence has recurring people/products/places/scale.
3. `Shot List Table`.
4. `Clean Handoff Specs` if requested or useful.
5. `镜头逻辑检查` / readiness note.

Do not bury clean handoff specs after long commentary. Handoff blocks should be easy to copy directly.
