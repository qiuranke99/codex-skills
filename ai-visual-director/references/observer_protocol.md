# Shadow Observer Protocol

The Shadow Observer is a sidecar learning mechanism for `ai-visual-director`. Its contract is:

```text
record, do not judge
propose, do not promote
observe, do not block
```

It exists to make the skill improve over time without turning every normal commercial run into a heavy review cycle.

## Non-Blocking Contract

Default production remains `standard_fast`.

The observer may:

- launch exactly one read-only Shadow Observer sub-agent when sub-agent tools are available;
- append facts to `_observer/events.jsonl`;
- ingest existing validator results;
- capture user corrections as evidence;
- generate `_observer/candidate_rules.json`;
- prepare `_observer/observer_packet.md` for later SSOT or sub-agent review.

The observer must not:

- block image generation, video-prompt generation, or final delivery;
- approve or reject the work;
- mutate deliverables;
- call image generation;
- convert one run's preference into a permanent rule;
- merge its output into certification audit files.

If the observer script fails, times out, or receives invalid data, the normal workflow continues. Use strict failure only in package verification or explicit certification diagnostics.

## Observer Modes

- `auto`: default. Start one read-only Shadow Observer sub-agent if tools are available, record existing artifacts and lightweight QC facts, and do not trigger creative re-review.
- `off`: skip observer event writing when the user requests no sidecar logging.
- `full`: allowed only for explicit audit, certification, or skill-improvement work. A read-only sub-agent may inspect the packet and propose rules, but still cannot mutate artifacts.

## Event Stream

Write observer events to:

```text
outputs/<date>_<slug>/_observer/events.jsonl
```

Each line must match `observer_event.schema.json`.

Recommended stages:

- `intake`
- `route`
- `shot_plan`
- `structure_gate`
- `storyboard_prompt`
- `post_image_qc`
- `video_prompt`
- `final_qc`
- `skill_packaging`

The event stream should prefer concrete evidence over opinion:

- exact validator warning or error;
- route decision that defaulted because duration was missing;
- user correction that reveals an unsupported brief pattern;
- image QC failure such as unrelated readable text, product identity mismatch, or panel separation failure;
- prompt failure such as static panel dump in a video segment.

## Failure Taxonomy

Routing:

- `route_misclass`
- `duration_defaulted`
- `escalation_trigger_missed`
- `reference_role_conflict`

Shot plan:

- `insufficient_camera_variety`
- `weak_attention_order`
- `missing_depth_layers`
- `unmotivated_movement`
- `generic_premium_language`
- `scale_unproven`

Prompt and image:

- `photoreal_drift`
- `anime_manga_drift`
- `readable_text`
- `panel_separation_failure`
- `identity_drift`
- `product_identity_mismatch`
- `wrong_camera_angle`
- `repeated_centered_composition`

Video:

- `static_panel_dump`
- `missing_first_last_frame`
- `segment_continuity_break`
- `motion_not_motivated`

Use `other` only when a failure is real but does not fit the current taxonomy. If `other` repeats, propose a taxonomy update instead of leaving it vague.

Use `readable_text` for captions, shot numbers, subtitles, handwritten notes, fake labels, signage, and non-product text. Use `product_identity_mismatch` when a user-provided product becomes blank, loses its supplied label text/logo/mark, invents a different brand or claim, changes package layout, or drops required packaging marks. Real product packaging text is identity evidence, not text contamination.

## Candidate Rules

Write candidate rules to:

```text
outputs/<date>_<slug>/_observer/candidate_rules.json
```

Each candidate must match `rule_candidate.schema.json` and include:

- the source event ids;
- the failure code;
- the hypothesis;
- proposed rule text;
- target file;
- applies-when condition;
- counterexample risk;
- regression case;
- promotion status.

Candidate rules are not accepted rules. They are proposals waiting for a skill-improvement pass, explicit user approval, or SSOT acceptance.

## Promotion Criteria

Generate a candidate when at least one condition is true:

- the same failure code appears in at least 3 observer events across runs;
- one severe blocker threatens product identity, character identity, legal safety, or deliverable correctness;
- the user explicitly says the finding should become durable;
- a certification run shows a benchmark regression.

Promote a candidate into the skill only when it is testable. A useful promotion must name at least one of:

- exact `SKILL.md` rule to add or modify;
- validator rule to implement;
- route heuristic to add;
- schema field to require;
- prompt-template constraint to strengthen;
- regression fixture to preserve.

## Sub-Agent Role

If sub-agent tools are available and `observer_mode` is not `off`, start exactly one read-only observer sub-agent. If tools are unavailable, create `_observer/events.jsonl` and `_observer/observer_packet.md` as the fallback handoff.

Launch timing:

- after intake and route decision exist; or
- after the first draft `03_shot_plan.json` exists if route data is not yet persisted.

Payload:

- `_observer/events.jsonl`;
- `_observer/observer_packet.md`;
- `_observer/candidate_rules.json` if it already exists;
- no full conversation history;
- no unrelated workspace files;
- no credentials or browser state.

The sub-agent's task is to detect improvement patterns, not to re-direct the commercial output. In `standard_fast`, do not wait for the sub-agent unless the main workflow is already blocked or it returns before closeout.

Use a prompt shaped like:

```text
You are the read-only Shadow Observer for ai-visual-director.
Inspect the observer events and compact packet.
Do not rewrite deliverables. Do not edit files. Do not call image generation.
Return candidate rule proposals only when the evidence is repeated, severe, or explicitly user-confirmed.
Do not judge taste. Focus on testable workflow improvements.
```

## Privacy And Scope

Observer packets may include:

- input manifest;
- reference-role summary;
- route decision;
- director brief;
- shot plan;
- validator output;
- storyboard image prompts;
- video prompts;
- QC summary.

Do not include credentials, browser state, unrelated workspace files, private source files, or full conversation history.

## Anti-Pattern

The strongest objection to the observer is valid: it can become a hidden audit system that slows production and creates low-quality rules. The defense is strict boundaries:

- no blocking;
- no automatic promotion;
- no extra creative review in normal production;
- no untestable rules.
