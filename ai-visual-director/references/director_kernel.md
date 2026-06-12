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

Default arc: ingredient/world origin -> product reveal -> material/texture proof -> use action -> benefit metaphor -> packshot payoff.

For 9 shots:
1. world/ingredient establish
2. macro ingredient or material detail
3. motion bridge into product world
4. product silhouette reveal
5. 3/4 hero product identity
6. opening/useable product detail
7. texture proof macro
8. benefit metaphor or use-action bridge
9. final packshot or sheet payoff

For 27 shots: sheet 1 = origin/reveal, sheet 2 = texture/use, sheet 3 = benefit/payoff.

Minimum shot mix per sheet: 1 establishing, 2 macro/insert, 1 hero product angle, 1 movement bridge, 1 payoff.

Forbidden defaults: nine centered product packshots, repeated eye-level table shots, abstract luxury language without visible proof.

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
