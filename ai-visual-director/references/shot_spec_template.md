# 01_shot_spec_template.md

Knowledge file for `Storyboard Shot Planner`.

This file defines the shot-spec grammar that GPT 1 must use before handing work to `Rough Storyboard Sketch Generator` GPT 2.

## 1. Purpose

`Storyboard Shot Planner` turns a story, script, ad idea, scene description, or reference image into a professional cinematic shot list and clean handoff specs for rough hand-drawn storyboard generation.

This is not a production call sheet, not a camera-department equipment order, and not a finished image prompt. It is a compact visual-planning document whose job is to make every shot drawable, legible, continuous, and sequence-aware.

## 2. Research Basis

The structure below synthesizes recurring practice from professional shot-list, storyboard, cinematography, previs, and AI image-generation sources:

- [StudioBinder shot list guide](https://www.studiobinder.com/blog/shot-list-template-free-download/): core shot-list fields converge around scene/shot number, description, shot size, camera angle/type, and camera movement.
- [Boords storyboard templates](https://boords.com/storyboard-template): film storyboard templates prioritize shot composition, camera direction, movement notes, transition notes, and scene/shot numbering.
- [FilmSourcing advanced shot list](https://www.filmsourcing.com/advanced-shot-list-template-free-download/): traditional production sheets add take, gear, location, INT/EXT, duration, sound status, and preferred-shot fields.
- [B&H camera shot types](https://www.bhphotovideo.com/explora/video/tips-and-solutions/filmmaking-101-camera-shot-types): shot size is a shared visual language for subject scale; it is not the same thing as lens choice.
- [ASC Shot Craft: camera movement](https://theasc.com/article/shot-craft-camera-movement/): dolly, gimbal, stabilizer, and related tools imply different movement qualities, but GPT handoff usually needs the readable movement feel rather than equipment inventory.
- [ASC Shot Craft: analyzing a script](https://theasc.com/article/shot-craft-analyzing-a-script/): visual rules, POV, references, special tools, and lookbook logic belong in the planning document when they affect shot continuity.
- [Boords video storyboarding guide](https://boords.com/how-to-storyboard/video): good boards should include timing, camera angle, movement, subject movement, and only essential notes; overcomplication makes boards harder to follow.
- [StoryboardArt camera angles guide](https://storyboardart.org/storyboard-tutorials/camera-angles-for-storyboard-artists/): storyboard frames must communicate camera position through perspective, depth, pose, and composition.
- [Boords AI storyboard docs](https://boords.com/docs/creating-storyboards): AI storyboard workflows benefit from aspect-ratio decisions, shot suggestions, image prompts, and character/cast references for consistency.
- [OpenAI image-generation guidance](https://openai.com/academy/image-generation/): image instructions work best when grounded in purpose, main subject, action, location, style, framing, lighting, and clear spatial language; targeted revision prevents drift.
- [StoryBlender research](https://arxiv.org/abs/2604.03315): multi-shot consistency benefits from separating global assets from shot-specific variables and maintaining spatial/semantic continuity.
- [Camera Artist research](https://arxiv.org/abs/2604.09195): explicit cinematography-shot planning improves narrative continuity and cinematic language in multi-shot AI video generation.

## Multiple Reference Priority

- Image 1:
  - function:
  - must preserve:
  - may ignore:
- Image 2:
  - function:
  - must preserve:
  - may ignore:

Conflict priority:
1. user-written requirement
2. first-frame composition / camera
3. character identity
4. product / prop structure
5. location continuity
6. style reference

### Cross-source consensus

Most professional sources agree on five durable shot-list concepts:

1. Every shot needs an ID.
2. Every shot needs subject scale: shot size.
3. Every shot needs camera relation: angle/placement.
4. Every shot needs movement, or a clear locked/static state.
5. Every shot needs action/description sufficient for another person to draw or shoot it.

### What traditional fields are not ideal for AI handoff

Traditional fields such as `take`, `gear used`, `sound status`, `call time`, `setup time`, `preferred yes/no`, `crew notes`, `INT/EXT`, and exact equipment are useful on set, but they often pollute AI storyboard handoff. They make GPT 2 attend to logistics instead of visual readability. Use them only when they directly change what the frame must show.

### Why this file uses the final fields below

The final fields favor what a rough storyboard generator actually needs:

- subject identity and action;
- frame size and camera relation;
- foreground/midground/background layout;
- pose and composition;
- scale references for surreal, VFX, product, and spatial shots;
- continuity locks to prevent identity, prop, wardrobe, and geography drift;
- must-preserve and avoid lists to reduce common AI hallucinations.

## 3. Hard Output Boundary

GPT 1 must do:

- Break the brief into story beats and shot logic.
- Choose shot size, camera angle, lens feel, camera movement, composition, subject action, and continuity constraints.
- Produce a readable shot list and clean handoff specs.
- Make the sequence drawable as rough storyboard panels.
- Preserve scale relationships, screen direction, geography, character identity, product continuity, and visual priorities.

GPT 1 must not do:

- Generate images.
- Write full image-generation prompts.
- Decide the final rough sketch style.
- Add rendering-engine syntax, sampler settings, model names, seed values, CFG, LoRA, ControlNet, or other generation parameters.
- Bury the shot logic under decorative adjectives such as "cinematic", "beautiful", "epic", or "premium" without concrete frame instructions.

GPT 2 owns:

- rough hand-drawn storyboard sketch style;
- actual image-generation prompt construction;
- rendering or sketch generation;
- visual iteration after the shot specs are approved.

## 4. Field Priority for AI Storyboard Sketch Generation

If a response must be shortened, preserve fields in this order:

1. `SH_###`
2. `scene`
3. `shot_size`
4. `camera_angle`
5. `main_subject`
6. `main_action`
7. `body_pose`
8. `composition`
9. `foreground`, `midground`, `background`
10. `scale_reference`
11. `continuity_lock`
12. `camera_movement`
13. `lens_feel`
14. `must_preserve`
15. `avoid`

Rationale: GPT 2 needs to know what to draw before it needs to know how elegant the camera language is. Composition, action, pose, layers, and scale beat abstract mood language.

## 5. Standard Shot Spec Fields

| Field | Definition | Write it like this | Do not write it like this |
|---|---|---|---|
| `SH_###` | Stable shot ID. | `SH_004` | `next shot`, `another angle` |
| `scene` | Location/time/story beat context. | `rainy Shibuya crossing, afternoon, giant reveal beat` | `city` |
| `duration` | Optional timing, required for timed ads. | `1.0s`, `2.5s`, `hold 3s` | `short`, `long` |
| `shot_purpose` | Why this shot exists in the sequence. | `establish the girl's normal scale before the surreal shift` | `make it cinematic` |
| `shot_size` | Subject scale in frame. | `wide shot`, `medium close-up`, `extreme close-up insert` | `35mm shot` |
| `camera_angle` | Camera position relative to subject. | `low angle from street level looking up` | `dramatic angle` |
| `lens_feel` | Perceptual lens behavior, not equipment fetish. | `slightly wide, mild perspective exaggeration` | `ARRI Alexa 35 with 28mm unless relevant` |
| `camera_movement` | Static state or motivated move. | `locked-off`, `slow dolly-in`, `handheld follow from behind` | `dynamic camera` |
| `main_subject` | Primary drawable subject. | `teen girl in navy school uniform` | `a person` |
| `main_action` | Visible action at the key frame. | `she lifts one foot over a row of taxis` | `she realizes something` |
| `body_pose` | Pose, gesture, gaze, weight, direction. | `knees bent, left hand bracing on building roof, gaze down at traffic` | `surprised pose` |
| `composition` | Placement, balance, leading lines, negative space. | `subject fills right third; avenue recedes diagonally to tiny cars` | `nice composition` |
| `foreground` | Closest visible layer. | `blurred traffic lights and umbrella tops at bottom edge` | `foreground stuff` |
| `midground` | Main action layer. | `girl's legs straddling intersection; taxis stopped around her shoes` | `middle area` |
| `background` | Distant environment layer. | `vertical shop signs and wet glass towers behind her shoulders` | `background city` |
| `scale_reference` | Objects that prove relative size. | `her shoe is longer than a taxi; pedestrians are thumb-sized near curb` | `she is huge` |
| `continuity_lock` | What must remain consistent across shots. | `same uniform, red ribbon, short black bob, rainy afternoon, left-to-right street direction` | `keep consistent` |
| `must_preserve` | Non-negotiable visual facts for GPT 2. | `red ribbon; wet asphalt reflections; no smiling` | `quality` |
| `avoid` | Specific failure modes to prevent. | `avoid monster anatomy, destroyed buildings, extra characters, clean sunny streets` | `bad art` |

## 6. Clean Handoff Spec: Required Fields

Every final handoff block must use this exact field order:

```yaml
SH_001
aspect_ratio:
scene:
duration:
shot_size:
camera_angle:
lens_feel:
camera_movement:
cut_logic:
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

### Field Definitions, Good Examples, Weak Examples

#### `SH_###`

- Purpose: gives GPT 2 a stable handle for revisions.
- Good example: `SH_003`
- Weak example: `Shot after close-up`
- Why weak: it cannot survive reordering, insertion, or versioned feedback.

#### `scene`

- Purpose: anchors place, time, and story beat.
- Good example: `night kitchen, product proof beat, steam visible against dark window`
- Weak example: `inside`
- Why weak: no time, environment, or reason for the shot.

#### `shot_size`

- Purpose: defines how large the subject appears.
- Good example: `medium close-up, face and serum bottle both readable`
- Weak example: `beauty shot`
- Why weak: "beauty" is a genre, not a scale.

#### `camera_angle`

- Purpose: defines audience position relative to the subject.
- Good example: `table-height low angle looking slightly up at the product in hand`
- Weak example: `cool angle`
- Why weak: it cannot be drawn; no height, tilt, or relation.

#### `lens_feel`

- Purpose: communicates perceived spatial behavior without overfitting equipment.
- Good example: `macro feel, shallow depth, product texture enlarged but label still readable`
- Weak example: `85mm f/1.2 anamorphic masterpiece`
- Why weak: equipment detail may not translate to a rough sketch and can distract from composition.

#### `camera_movement`

- Purpose: tells whether the panel is static, moving, or needs start/end framing.
- Good example: `slow push-in from medium shot to tighter product handoff`
- Weak example: `moving camera`
- Why weak: no direction, speed, motivation, or final framing.

#### `main_subject`

- Purpose: names the primary drawable entity.
- Good example: `silver refillable water bottle with black cap and visible filter window`
- Weak example: `the product`
- Why weak: product identity and key shape are missing.

#### `main_action`

- Purpose: defines the visible action at the panel's key moment.
- Good example: `thumb presses filter button; small status light turns on`
- Weak example: `shows the feature`
- Why weak: no visible action.

#### `body_pose`

- Purpose: locks gesture, weight, gaze, and character readability.
- Good example: `model's chin lowered, eyes toward mirror, right hand applying cream to cheek`
- Weak example: `model looks elegant`
- Why weak: elegance is not a drawable pose.

#### `composition`

- Purpose: arranges attention inside the frame.
- Good example: `product centered on lower third; hand enters from left; diagonal bathroom counter leads to mirror`
- Weak example: `nice clean composition`
- Why weak: no placement or visual hierarchy.

#### `foreground`

- Purpose: defines near-frame depth cues or occluders.
- Good example: `soft out-of-focus sink edge and water droplets at bottom frame`
- Weak example: `foreground blur`
- Why weak: no object identity.

#### `midground`

- Purpose: locates the main action layer.
- Good example: `model's hand and cream jar at center; open jar lid on counter`
- Weak example: `subject`
- Why weak: does not say how subject and props relate.

#### `background`

- Purpose: creates environment without stealing the shot.
- Good example: `muted tiled wall and mirror reflection of shoulder line`
- Weak example: `luxury bathroom`
- Why weak: genre label, not visible background.

#### `scale_reference`

- Purpose: proves size, distance, or product scale.
- Good example: `jar fits in palm; fingertip width compared to cream texture`
- Weak example: `small product`
- Why weak: scale is asserted, not shown.

#### `continuity_lock`

- Purpose: prevents drift across shots.
- Good example: `same amber jar, white label, gold cap, model has short coily hair, cream on right cheek only`
- Weak example: `same as before`
- Why weak: GPT 2 may not know which prior details matter.

#### `must_preserve`

- Purpose: lists visual facts that must not be altered.
- Good example: `label faces camera; cap remains gold; cream is white, not gel`
- Weak example: `brand look`
- Why weak: too abstract to enforce.

#### `avoid`

- Purpose: preempt common wrong outputs.
- Good example: `avoid extra fingers, unreadable label, duplicate bottle, glamour retouching that removes skin texture`
- Weak example: `avoid mistakes`
- Why weak: no specific failure modes.

## 7. Single-Shot Output Template

Use when the user asks for one frame or one storyboard panel.

```markdown
## Shot Spec

| Field | Value |
|---|---|
| Shot ID | SH_001 |
| Shot Purpose | |
| Shot Size | |
| Camera Angle | |
| Lens Feel | |
| Camera Movement | |
| Main Subject | |
| Main Action | |
| Composition | |
| Scale / Continuity | |

## Clean Handoff Spec

SH_001
scene:
duration:
shot_size:
camera_angle:
lens_feel:
camera_movement:
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

## 8. Multi-Shot Shot List Table Template

Use this table before clean handoff specs.

```markdown
| Shot ID | Duration | Shot Purpose | Shot Size | Camera Angle | Lens Feel | Camera Movement | Action | Composition | Scale / Continuity |
|---|---:|---|---|---|---|---|---|---|---|
| SH_001 | | | | | | | | | |
| SH_002 | | | | | | | | | |
| SH_003 | | | | | | | | | |
```

Rules:

- `Duration` is optional for narrative boards but required for timed ads.
- `Shot Purpose` must be narrative, persuasive, or informational.
- `Action` must describe a visible moment, not an internal feeling.
- `Composition` must specify where the subject sits in the frame.
- `Scale / Continuity` must mention props, wardrobe, geography, product orientation, character identity, or surreal scale when relevant.

## 9. Clean Handoff Specs Template

```yaml
SH_001
scene:
duration:
shot_size:
camera_angle:
lens_feel:
camera_movement:
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

SH_002
scene:
duration:
shot_size:
camera_angle:
lens_feel:
camera_movement:
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

## 10. Four-Shot Sequence Template

Best for a compact beat: setup, discovery, escalation, payoff.

| Shot ID | Purpose | Required Logic |
|---|---|---|
| SH_001 | Establish geography and normal baseline | Show where we are and what normal scale/action looks like. |
| SH_002 | Introduce the anomaly, product, or emotional turn | Move closer; make the new information readable. |
| SH_003 | Prove the change through action | Use body pose, object interaction, or scale reference. |
| SH_004 | Payoff / reaction / final image | Resolve the beat with a readable final composition. |

Minimum handoff requirements:

- At least one wide shot.
- At least one close readable detail.
- Clear continuity lock.
- If scale changes, at least two scale references.

## 11. Eight-Shot Commercial Sequence Template

Best for product, beauty, tech, food, fashion, or service demos.

| Shot ID | Purpose | Notes |
|---|---|---|
| SH_001 | Hook image | One instantly readable visual promise. |
| SH_002 | Product or hero subject reveal | Product/subject shape and identity must be clear. |
| SH_003 | Use-case setup | Human problem, friction, or desire. |
| SH_004 | First feature action | Show one visible operation. |
| SH_005 | Proof detail | Macro, texture, result, mechanism, before/after cue. |
| SH_006 | Human response | Reaction, posture shift, confidence, relief, delight. |
| SH_007 | Brand/product continuity shot | Reconfirm product orientation, color, label, use context. |
| SH_008 | End frame | Final product/subject composition with no new visual confusion. |

Rules:

- Do not start with abstract mood if the product is unknown.
- Product continuity must state color, orientation, label side, cap/lid state, and hand position when relevant.
- Human continuity must state hair, wardrobe, skin detail, pose direction, and prop relationship.

## 12. Fifteen-Shot Fast-Cut AI Video Ad Template

Best for 10-20 second social ads where rhythm matters.

Recommended structure for 15 seconds:

| Section | Shots | Timing | Function |
|---|---|---:|---|
| Hook | SH_001-SH_003 | 0.5-1.0s each | Pattern interrupt, problem, visual contrast. |
| Setup | SH_004-SH_006 | 0.7-1.1s each | Show context and product/idea entrance. |
| Proof Burst | SH_007-SH_011 | 0.5-0.9s each | Rapid features, texture, action, result cues. |
| Human / World Response | SH_012-SH_013 | 0.8-1.2s each | Make the benefit emotionally or spatially legible. |
| End Lock | SH_014-SH_015 | 1.0-1.5s each | Final product/idea image and clean exit. |

Rules:

- Every shot needs a distinct visual job.
- Avoid 15 unrelated hero images.
- Repeat no shot size more than three times in a row.
- Use inserts as punctuation, not filler.
- Keep screen direction and product orientation stable unless the cut intentionally flips perspective.

## 13. Reference Image to Shot Spec Template

Use when the user supplies a reference image.

```markdown
## Reference Image Extraction

- Visible subject(s):
- Shot size:
- Camera angle:
- Lens feel:
- Camera movement implied, if any:
- Composition:
- Foreground:
- Midground:
- Background:
- Pose / gesture:
- Lighting and atmosphere, only if visually relevant:
- Scale relationships:
- Continuity elements to preserve:
- Elements to ignore or reinterpret:

## Converted Shot Specs

| Shot ID | Shot Purpose | Shot Size | Camera Angle | Lens Feel | Action | Composition | Scale / Continuity |
|---|---|---|---|---|---|---|---|
| SH_001 | preserve the reference image's core composition | | | | | | |
| SH_002 | alternate angle or narrative continuation | | | | | | |
```

Reference-image rules:

- Separate observed facts from interpretation.
- Do not assume the image's unseen geography unless the brief requires it.
- Preserve only what serves continuity or the user's stated intent.
- If the user wants a sequence from one image, create one anchor shot that stays close to the reference before inventing expansions.

## 14. Continuity Lock Template

Use this whenever the sequence has recurring characters, products, places, or surreal scale.

```markdown
## Continuity Lock

- Character identity:
- Wardrobe:
- Hair / face / body features:
- Product identity:
- Product state:
- Prop positions:
- Environment:
- Screen direction:
- Lighting/time:
- Scale relationship:
- What may change shot to shot:
- What must not change:
```

Good continuity locks are specific:

- `same navy uniform, red ribbon, wet black loafers, short black bob, no glasses`
- `same matte black bottle, white vertical label facing camera, cap removed only after SH_004`
- `camera keeps girl moving left-to-right until SH_006; do not reverse street direction`

Weak continuity locks are vague:

- `keep the same`
- `consistent character`
- `same product vibe`

## 15. Scale Relationship Template

Use for giants, miniatures, VFX, product macro, architectural scale, or surreal transformations.

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
- `Primary subject: serum droplet. Reference object 1: fingertip ridge. Reference object 2: bottle pipette. Relative size: droplet half the width of fingernail. Frame proof: droplet suspended between pipette and skin. Avoid: droplet becoming a splash or pearl.`

## 16. Shot Readability Checklist

Before final output, verify every shot:

- Can be drawn as one rough storyboard panel.
- Has one dominant visual subject.
- Has a visible action or stillness that matters.
- Defines shot size and camera angle.
- States movement or explicitly says `locked-off`.
- Has foreground/midground/background when depth matters.
- Uses concrete composition, not mood words.
- Includes scale reference when size is part of the story.
- Includes continuity lock when a subject recurs.
- Has `avoid` notes for likely AI failures.

## 17. Sequence Logic Checklist

Before final output, verify the whole sequence:

- The first shot orients the viewer unless intentional disorientation is the concept.
- Shot sizes vary with purpose: wide for geography, medium for action, close-up/insert for proof or emotion.
- Camera angles do not randomly change audience perspective.
- Movement is motivated by reveal, pursuit, intimacy, scale, proof, or rhythm.
- Each cut gives new information.
- Product or character continuity survives shot-to-shot.
- Screen direction is stable unless a reversal is motivated.
- Fast-cut sequences have timing and visual rhythm.
- The final shot resolves the sequence or leaves a deliberate question.

## 18. Revision and Versioning Rules

Use these rules when the user asks for changes:

- Preserve existing `SH_###` IDs unless shots are deleted.
- If inserting a shot, use `SH_003A` or renumber only when the user asks for a clean final.
- For major rewrites, label versions: `v1`, `v2`, `v3`.
- For single-shot revisions, repeat only the changed shot plus any updated continuity lock.
- Do not silently change continuity facts.
- If the user changes style, keep shot logic stable unless style changes frame readability.
- If the user changes aspect ratio, re-evaluate composition and scale references.
- If GPT 2 reports generation drift, strengthen `continuity_lock`, `must_preserve`, and `avoid`; do not merely add adjectives.

## 19. Common Failure Modes and Corrections

| Failure Mode | Symptom | Correction |
|---|---|---|
| Prompt-poetry instead of shot planning | Many adjectives, no camera relation. | Rewrite as shot size + angle + action + composition. |
| Product ad hides the product | Product appears late or tiny. | Add early product reveal and proof insert. |
| Surreal scale is unproven | Giant/miniature is asserted but not visible. | Add scale references in frame. |
| Too many camera moves | Every shot dollies, pans, or cranes. | Use movement only when it changes information or emotion. |
| Continuity drift | Wardrobe, product color, or geography changes. | Add explicit continuity lock and must-preserve list. |
| Unreadable action | Shot describes internal feeling. | Convert feeling into pose, gesture, gaze, object interaction. |
| Overloaded frame | Too many subjects and props. | Pick one dominant subject; move secondary info to foreground/background. |
| AI prompt leakage | Handoff contains model settings or full render prompt. | Remove generation syntax; keep visual spec only. |
| Shot list is a shot buffet | Sequence has many cool frames but no progression. | Assign each shot a purpose and remove duplicates. |
| Reference image overfit | Every shot copies the same angle. | Keep one anchor shot, then derive motivated alternate angles. |

## 20. Final Output Order

When producing a full answer, use this order:

1. `Research / reasoning note` if requested.
2. `Assumptions` if the brief is underspecified.
3. `Continuity Lock`.
4. `Shot List Table`.
5. `Clean Handoff Specs`.
6. `Readiness note for Rough Storyboard Sketch Generator`.

Do not bury the clean handoff specs after long commentary. GPT 2 should be able to copy them directly.
