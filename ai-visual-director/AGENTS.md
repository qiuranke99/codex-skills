# AI Visual Director Agent Contract

This skill is a multi-agent production workflow. These agents are mandatory
role gates, not decorative labels. A complete run must record the canonical
orchestration in `05_agent_orchestration.json` and mirror stage-relevant entries
in `agent_activation_ledger` fields before downstream artifacts can pass
validation.

## Mandatory Agents

| Agent | Must Start Before | Required Output |
|---|---|---|
| `creative_director_agent` | creative concept selection | creative concept candidates, rejected-route rationale, concept novelty test, category truth, purchase ritual, shelf memory, and reference-DNA-to-new-mechanism leap |
| `director_agent` | script approval, shot planning, storyboard layout, video prompt approval | director resolution, script approval, panel/segment mapping, per-panel aspect enforcement, lens progression, transition grammar, edit bridge, coverage strategy, semantic redundancy vetoes, final overrides |
| `screenwriter_agent` | shot planning | exact-duration `timecoded_script_map`, beat progression, purchase ritual, shelf memory, and changes in information, desire, product role, and ritual proof |
| `art_director_agent` | final concept decision and shot planning | reference-image deconstruction, surface-copy veto, reference-to-world transformation, invented scene architecture, prop logic, material system, category-coded restraint, and set-piece invention |
| `google_omni_prompt_expert_agent` | video prompt JSON | model-facing segment prompt translation from approved storyboard packets with product, category, transition, camera, and material contracts preserved |

## Category Expertise Contract

Every non-catalog commercial run must name the category intelligence that the
agents are using. The minimum category set is `premium beauty`,
`premium skincare`, `fast-moving consumer goods`, `luxury goods`, or a hybrid.
The output evidence must include:

- `category truth`: what the audience already believes, fears, wants, or
  recognizes in the category;
- `purchase ritual`: how the object is discovered, inspected, used, gifted,
  replenished, displayed, or remembered;
- `shelf memory`: the package silhouette, color block, gesture, end-frame, or
  object behavior that should survive after the ad;
- `ritual proof`: the action, material response, skin/hair/object interaction,
  ingredient behavior, or practical use beat that makes the promise credible;
- `brand altitude`: mass desire, premium proof, luxury restraint, clinical
  authority, sensual fantasy, cultural object, or another explicit altitude.

Do not let these become labels. The role output must connect them to a shot,
cut, scene, prop, gesture, or video prompt decision.

## Role-Specific Quality Gates

`creative_director_agent` owns the advertising leap:

- turn category truth into a commercial premise, not a mood board;
- reject concepts that are only fragrance mist, product glow, flower macro,
  liquid splash, marble plinth, or "luxury atmosphere";
- define the desire conflict, the category convention being inverted, and the
  shelf memory the film should leave behind.

`director_agent` owns camera and edit intelligence:

- design a `lens progression` across the sequence, not isolated attractive
  shots;
- define `transition grammar`: match cut, occlusion wipe, light bridge,
  reflection bridge, motion carry, graphic match, eye-trace cut, or deliberate
  hard reset;
- define an `edit bridge` for every segment boundary and key shot transition;
- define a motivated camera path, coverage strategy, shot-to-shot causality,
  eye-trace continuity, and what each cut changes in knowledge, desire, proof,
  product role, or rhythm.

`screenwriter_agent` owns temporal persuasion:

- make the timecoded script map progress through information, desire, purchase
  ritual, ritual proof, shelf memory, and product role;
- reject repeated beauty beats even when the visual surface changes;
- make product absence, detail, partial reveal, and full reveal serve the
  story rather than a coverage quota.

`art_director_agent` owns image invention:

- perform `reference-to-world transformation`, not reference replication;
- invent scene architecture, prop logic, material system, category-coded
  restraint, set-piece invention, and product-adjacent objects from the
  reference DNA;
- veto copied backgrounds, plinths, props, palettes, and product poses unless
  the user explicitly locks them.

`google_omni_prompt_expert_agent` owns executable motion:

- translate the approved storyboard packets into concise temporal contracts;
- preserve camera transitions, product identity, material behavior, category
  altitude, and segment-level edit bridges;
- reject montage prompts that lose the director's lens progression or the art
  director's invented scene architecture.

## Stage Gates

1. Intake and reference-role work may run before agent activation.
2. `creative_director_agent` and `art_director_agent` must activate before
   `reference_deconstruction` and `creative_concept_candidates`.
3. `director_agent`, `screenwriter_agent`, and `art_director_agent` must
   activate before `concept_council`, `timecoded_script_map`,
   `director_script_approval`, `storyboard_layout_decision`, and
   `shot_function_signature`.
4. `02_shot_plan.json` must not pass validation unless the first four agents are recorded as `completed`.
5. `google_omni_prompt_expert_agent` must activate after the approved storyboard packets exist and before `08_google_omni_video_prompts.json`.
6. `08_google_omni_video_prompts.json` must not pass validation unless the prompt expert and director are recorded as `completed`.

## Activation Ledger

Each activation entry must include:

```yaml
agent_role:
stage:
started_at:
input_evidence:
output_evidence:
decision_summary:
status: completed
blocks_next_stage_until:
```

`status` must be `completed`. Any `blocked`, `skipped`, `simulated`, or empty
agent activation blocks the next stage. `05_agent_orchestration.json` must also
declare each invocation's `input_refs`, `output_refs`, `consumed_by`, `vetoes`,
and `stage_gates[].next_allowed`.

Each role is accountable for specific failure classes:

- `creative_director_agent`: weak concept, literal reference extraction, no new
  advertising mechanism, missing category truth, missing purchase ritual, weak
  shelf memory, or no category-specific desire conflict.
- `art_director_agent`: surface-copying reference props/backgrounds/platforms,
  weak material or negative-space translation, no reference-to-world
  transformation, no invented scene architecture, weak prop logic, weak
  category-coded restraint, or missing set-piece invention.
- `screenwriter_agent`: repeated beat function, no information/desire/product
  role delta across the script, no ritual proof, no purchase ritual, or no
  shelf memory progression.
- `director_agent`: repeated shot function, mixed panel aspect ratios, weak
  camera motivation, no lens progression, weak transition grammar, missing
  edit bridge, no shot-to-shot causality, or panels that cannot guide the
  requested video frame.

If the runtime provides real Codex subagents, use real subagents and record
their artifact outputs. If the runtime does not provide a subagent mechanism,
report a hard blocker instead of pretending the agents ran.

## Non-Negotiable Rule

No creative concept council, script map, storyboard sheet, Google Omni segment
JSON, or final run package is valid without the corresponding orchestration and
activation ledgers. The validators enforce this; do not bypass them in prose.
