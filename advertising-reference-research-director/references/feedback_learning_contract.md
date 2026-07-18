# Feedback Learning Contract

This file governs user corrections, versioned learning, invalidation, scope, and regression evidence. Curation from 30 to 20 is not itself learning. Learning exists only when feedback changes an explicit model of the brief or process and the dependent work is recomputed.

## 1. Feedback Event

Capture the event facts and freeze the pre-change snapshot before applying a
material correction. The final validator-input row written to
`05_feedback/feedback_ledger.jsonl` must represent the applied repair and validate
against `feedback_event.schema.json`.

Each event must bind:

- `feedback_id`, timestamp, and the current `pack_id`;
- `signal_class`, kept separate from the causal `error_layer`;
- user evidence or a concise faithful quote;
- failed assumption;
- exactly one primary `error_layer`;
- structured `constraint_delta` whose before/after model refs, JSON pointer,
  existence flags, and operation are mutually consistent;
- invalidated candidate IDs, `invalidated_approach_ids`,
  `invalidated_query_ids`, and schema-defined artifact references covering
  affected receipts, territories, and selections;
- scope: `session | project | global`, plus scope basis, supporting feedback
  IDs, counterexamples, owner, and reversal procedure;
- confidence and promotion evidence; the ledger always states
  `external_persistence_state=not_applied_by_skill`;
- one superseded feedback ID when applicable;
- `intent_version_before` and `intent_version_after`;
- repair start phase and completion evidence whose input status is `applied`,
  whose completion time follows application, and whose exact required artifact
  types, paths, and SHA-256 values close the repair.

`feedback_id` is unique within one pack ledger. A single correction with
`scope=global` is mirrored into every affected parallel pack with the same
`feedback_id` and semantic fields, while `pack_id`, invalidated
candidate/approach/query IDs, artifact references, completion references, and
application trace remain pack-local. Cross-pack validation compares the global
semantic projection, not the byte identity of those pack-local bindings.

Do not store hidden reasoning or unrelated personal information. A faithful paraphrase is allowed when quoting would disclose private data.

### Input versus validator-derived state

The run is validator input. It must never claim that it has validated itself.

- `completion_evidence.status` in a completed input run is exactly `applied`.
- `completion_evidence.artifact_bindings` names and hashes the repaired input artifacts.
- `completion_evidence` contains only `status`, `completed_at`, and
  `artifact_bindings`;
  `validator_ref` is forbidden rather than nullable, so input cannot point to
  `verification_report.json` or any other artifact as validation proof.
- `validated` is a derived external result produced only after the validator has
  accepted the run. It belongs in `validation_result.json` or the external
  parallel-pack validation result, not in `feedback_ledger.jsonl`.

A work-in-progress implementation may hold a pending event in transient state,
but `pending` is not valid completed-run input. Rewriting `applied` to
`validated` inside the input after validation would create a circular claim and
invalidate the external result hash.

## 1.1 Core And Referenced Evidence

The verification report has exactly ten fixed core artifact-contract entries:
intent, approach registry, candidates, receipts, capture records, shortlist,
selected, rejected, feedback ledger, and reference board. Feedback-related
evidence outside those ten belongs to the variable
`referenced_evidence_contract`, including:

- every invalidated `intent_brief` snapshot cited by a feedback event;
- the relevance, diversity, and resolution reviews referenced by the final
  selected/rejected curation traces;
- the run's adversarial-audit result; and
- any diversity-waiver evidence used by the final selection.

Every referenced file must be run-local, exist, and be SHA-256 bound. The
contract must exactly cover those validator-read variable files, with each path
declared once and its `purposes` equal to the complete purpose set for that
path; omitted evidence and unused extras both fail. Other repair/regression
facts must be captured inside a supported core or referenced artifact rather
than padding this contract. External validator outputs are not input evidence
and must not appear in either input contract.

## 2. Error Layers

Use this taxonomy to find the earliest real cause:

- `intent` — decision, subject, hard constraint, scene scale, human presence, positive/negative anchor, or deliverable misunderstood;
- `route` — image/video/both or both-mode wrong;
- `query` — search axes or method family failed to express the intent;
- `source` — wrong source population, discipline, market, language, or prestige bias;
- `access` — session, deep-link, provenance, media, or shareability evidence insufficient;
- `scoring` — correct candidates ranked under wrong weights or observations;
- `diversity` — result set collapsed around duplicate mechanism/source/creator/territory;
- `presentation` — evidence is correct but grouping, explanations, or board rendering miscommunicates it.

Choose the earliest causal layer, not the most visible symptom. Example: a result set full of product still lifes when the user wanted full-body models in monumental environments is primarily `intent` if `scene_scale`/`human_presence` were never frozen; it is `query` or `source` only if those intent fields were correct but the methods ignored them.

## 3. Hard Constraint Versus Preference

Classify feedback as:

- `explicit_hard_constraint` — direct user requirement; update the current brief immediately;
- `explicit_soft_preference` — direct preference that affects ranking but is not an exclusion;
- `inferred_session_signal` — plausible preference inferred from one correction; do not generalize;
- `confirmed_project_rule` — repeated or explicitly confirmed rule for the current project;
- `confirmed_global_rule` — user explicitly asks for cross-project persistence or repeated evidence makes the generalization safe and the storage policy authorizes it.

Never promote an inferred session signal directly to project/global. Never write global memory unless the runtime's memory policy and user authorization permit it. The run ledger may record the proposed scope without mutating external memory.

## 4. Constraint Delta

Record field-level operations rather than “updated keywords”. A delta identifies:

- `target_artifact_type`: versioned `intent_brief` or `approach_registry`;
- run-local `before_ref` and `after_ref` bound to the before/after intent versions;
- JSON pointer or canonical field;
- operation: `add | replace | remove`;
- truthful before/after existence flags (`add=false/true`,
  `replace=true/true`, `remove=true/false`);
- old value;
- new value;
- evidence;
- hard/soft status;
- affected phases.

The recorded values must equal their JSON pointers in the bound before/after
models. The final event's `after_ref` is the current model; earlier events retain
versioned after-model evidence. Intent/route/rights corrections change the
intent model. Query/source corrections change the approach registry, so a
keyword-only intent edit cannot masquerade as a query repair.

Examples:

```text
/human_presence: open -> full_body_model_required
/scene_scale: tabletop_or_open -> monumental_interior
/must_not_have: add product_only_still_life
/visual_axes: add fashion_editorial_casting
/source_family_weights: product_photography down, fashion_editorial/set_design up
```

A keyword-only edit without intent/source/method delta is not accepted as learning.

## 5. Version And Invalidation

Every material correction increments `intent_version`. Versions use the legal
schema form `v1`, `v2`, and so on; forms such as `intent-v1` are invalid.
The ledger begins at `v1`, contains exactly one sequential increment per event,
and ends at the current intent version.
Preserve the old brief and artifacts as superseded evidence. Invalidate from the
earliest affected phase:

| Changed layer | Minimum invalidation |
|---|---|
| intent | route if affected; all approaches, candidates, receipts, scores, selections, board |
| route | modality packs, quotas, all downstream artifacts |
| query | affected approaches and their candidates; downstream set artifacts |
| source | affected candidates/receipts and dependent selections |
| access | affected receipts and qualification; replace candidates if gate fails |
| scoring | scores, curator reviews, selected/rejected sets, board |
| diversity | territories, diversity review, selected/rejected sets, board |
| presentation | rendered board and explanations only, if machine facts remain unchanged |

Do not reuse a receipt after the candidate object, canonical URL, media version, or intent-dependent object match changed. A transport-only freshness recheck cannot validate a new creative intent.

## 6. Repair Loop

For every correction:

1. capture the event facts and freeze the pre-change version;
2. diagnose the earliest error layer;
3. apply the field-level delta;
4. increment and validate the intent brief;
5. invalidate dependent approaches/evidence/selections;
6. register replacement approaches or changed source weights;
7. rerun independent discovery/verification/curation/audit as required;
8. write post-change evidence showing the delta affected results;
9. append the final input event with `completion_evidence.status=applied`, a
   valid completion time, and exact run-local artifact path/hash bindings, with
   no `validator_ref` field;
10. keep both versions for regression comparison and let the external validator
    derive `validated`.

The repair is not complete merely because the final 20 changed. Show from the
declared, hash-bound artifacts that the intended axis changed in the candidate
population, source mix, query lanes, or ranking evidence.

## 7. Feedback Conflict And Supersession

When new feedback conflicts with earlier feedback:

- prefer the more explicit, specific, and recent statement for the same scope;
- do not delete the earlier event;
- link it through `supersedes` and explain the scope;
- distinguish a new campaign state from a contradiction when both can be true in different territories;
- ask a clarification only if the conflict is identity-changing and the three-question budget has not been exhausted; otherwise preserve the conflict as an isolated blocker and complete unaffected work.

Do not average mutually exclusive hard constraints into a vague compromise.

## 8. Negative Evidence

User rejection is valuable only when its cause is captured. Record:

- which candidate/territory triggered the correction;
- the observed offending feature;
- whether the feature is universally prohibited or wrong only in this context;
- the counterexample or replacement evidence, if any;
- false generalizations to avoid.

Example: “These keywords only return small product still lifes” does not show
that the user globally dislikes product photography. It supports a current-run
scene-scale and human-presence correction and a shift toward fashion editorial
plus large-scale set design.

## 9. Scope Promotion Rules

### Session to project

Promote only as `confirmed_project_rule` when:

- the user explicitly says the preference applies to the project; or
- at least two independent corrections show the same stable rule and no counterexample exists;
- the proposed project rule is shown to the user or otherwise follows the project's explicit governance.

### Project to global

Promote only as `confirmed_global_rule` with explicit user authorization.
Repetition alone is insufficient. This Skill records authorization but cannot
claim external durable-memory mutation; that requires a separate authorized
workflow.

All promotions record supporting feedback IDs, counterexamples considered, scope owner, and reversal procedure.

## 10. Regression Evidence

An external correction-regression validation passes only when:

- `intent_version_after > intent_version_before`;
- the event validates and links the changed fields;
- invalidated artifacts are no longer presented as current;
- affected query/source approaches changed in the registered way;
- candidates violating the new hard constraint are quarantined or absent from the qualified 30;
- the replacement set again satisfies exact 30/20/10 and all verification gates;
- selection explanations reference the new intent version;
- an independent auditor confirms that the original failure did not recur;
- unrelated hard constraints did not regress.

The successful external result may report the repair as validated. It does not
mutate the feedback input or point back from the input to the verification
report.

## 11. Anti-Patterns

Forbidden:

- treating 20 selections out of 30 as learning without user feedback;
- silently editing prompts while leaving `intent_version` unchanged;
- storing one-off taste as a permanent global preference;
- reducing every correction to a keyword addition;
- discarding failed candidates/queries and losing the causal evidence;
- reusing stale scores or receipts after a material intent change;
- fixing presentation when the error was intent or source selection;
- claiming the system “learned” when no durable delta and regression evidence exist.
- writing `completion_evidence.status=validated`, adding any `validator_ref`,
  or omitting a completion artifact hash
  field inside validator input;
- leaving a referenced invalidated intent snapshot outside the hash-bound
  `referenced_evidence_contract`.
