# AI Visual Director Agent Contract

This skill is a multi-agent production workflow. These agents are mandatory
role gates, not decorative labels. A complete run must record the canonical
orchestration in `05_agent_orchestration.json` and mirror stage-relevant entries
in `agent_activation_ledger` fields before downstream artifacts can pass
validation.

## Mandatory Agents

| Agent | Must Start Before | Required Output |
|---|---|---|
| `creative_director_agent` | creative concept selection | creative concept candidates and rejected-route rationale |
| `director_agent` | script approval, shot planning, storyboard layout, video prompt approval | director resolution, script approval, panel/segment mapping, final overrides |
| `screenwriter_agent` | shot planning | exact-duration `timecoded_script_map` |
| `art_director_agent` | final concept decision and shot planning | art-direction veto, material/color/world-rule constraints |
| `google_omni_prompt_expert_agent` | video prompt JSON | model-facing segment prompt translation from approved storyboard packets |

## Stage Gates

1. Intake and reference-role work may run before agent activation.
2. `creative_director_agent` must activate before `creative_concept_candidates`.
3. `director_agent`, `screenwriter_agent`, and `art_director_agent` must activate before `concept_council`, `timecoded_script_map`, `director_script_approval`, and storyboard layout.
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

If the runtime provides real Codex subagents, use real subagents and record
their artifact outputs. If the runtime does not provide a subagent mechanism,
report a hard blocker instead of pretending the agents ran.

## Non-Negotiable Rule

No creative concept council, script map, storyboard sheet, Google Omni segment
JSON, or final run package is valid without the corresponding orchestration and
activation ledgers. The validators enforce this; do not bypass them in prose.
