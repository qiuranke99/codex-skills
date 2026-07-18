# Route And Intent Contract

This file is the authority for intent freezing, clarification, modality routing, rerouting, and `both` semantics. Validate the resulting artifact against `intent_brief.schema.json`.

## 1. Decision-First Principle

Do not route from isolated nouns such as “reference”, “campaign”, “film”, or “image”. Determine the production decision the evidence must improve.

Use this precedence order:

1. explicit user instruction about the requested deliverable and modality;
2. explicit creative/production decision to inform;
3. required evidence type: static, temporal, or integrated;
4. supplied positive/negative anchors and project artifacts;
5. reversible inference recorded in the intent brief.

Never override a coherent explicit user route merely because another route would be easier to search. If the user's requested modality cannot answer the stated decision, identify the conflict and recommend the smallest route correction; do not silently change it.

## 2. Minimum Intent Brief

Freeze these fields before broad discovery:

- `run_id`
- `intent_id`
- `intent_version`
- `run_mode`: `test_fixture | retrospective_smoke | production_live`
- `decision_to_inform`
- `deliverable_type`
- `modality_route`: `image | video | both`
- `routing.strategy`: `single_modality | parallel_packs | unified_territory`
- `routing.pack_contracts` and `routing.unified_territory_quota`
- `subject`
- `scene_scale`
- `human_presence`
- `visual_axes`
- `temporal_axes`
- `must_have`
- `must_not_have`
- `positive_anchors`
- `negative_anchors`
- `market_region`
- `languages`
- `freshness_need`
- `access_policy`
- `rights_scope`
- `diversity_requirements`
- `clarification_questions`
- `route_reason_codes` and `route_evidence`
- `assumptions`
- `approval`

`scene_scale` and `human_presence` must be explicit. Use their schema value `unspecified` when the axis is genuinely open or immaterial; do not invent prose-only enum values. Do not bury them inside a mood paragraph. For each material inference record its evidence, confidence, and reversibility.

For a real live research run, freeze `production_live` before discovery. It may
become production-contract-eligible but package-local unsigned evidence is
never production-deliverable. `test_fixture` is synthetic, and
`retrospective_smoke` records evidence assembled after the fact; neither is
production-contract-eligible. A retrospective run must never be relabeled in
place as preregistered production evidence.

The production gate validates the chronology declared by the artifacts:
`approval.approved_at <= registration.frozen_at < min(earliest
approach.started_at, earliest candidate.discovered_at, earliest
capture.captured_at)`.
The plan hash binds the recorded plan projection. Neither the hash nor those
timestamps are a digital signature or independent proof that the plan or
browser action actually existed at the declared time.

Every qualified candidate binds the relevance-bearing subset above through
`intent_alignment.intent_constraints_sha256`. The candidate must account for
all must-have and must-not-have criteria and anchors, match the frozen subject,
scene scale, and human-presence constraint, cover all visual axes and every
applicable video temporal axis, respect `content_max_age_days`, and either match
the market/language or document a substantive transfer rationale. Candidate and
receipt rights may not exceed the frozen intent rights boundary. Draft intent,
contradictory route reason codes, or a modality/object-type mismatch are never
eligible for a completed pack.

## 3. Deterministic Route Table

### Route `image`

Use image research when the decision is primarily about a state visible in one frame:

- KV, layout, crop, composition, point of view, negative space;
- product treatment, packaging, texture, surface, material behavior;
- model/casting, wardrobe, styling, pose, expression;
- architecture, set design, installation, interior, scene scale;
- light architecture, color, tonal range, finish, typography;
- storyboard frame or still-frame visual grammar without a temporal question.

The candidate is one exact image within an accountable item page, bound by an asset locator. A portfolio landing page is not an image candidate.

### Route `video`

Use video research when the decision depends on change through time:

- camera trajectory, movement grammar, lens change, focus behavior;
- actor/model blocking, gesture, performance, choreography;
- narrative causality, reveal, suspense, comedic or emotional timing;
- edit pattern, rhythm, transition, montage, speed ramp;
- VFX evolution, transformation, simulation, motion identity;
- sound-image relationship, silence, sync, sonic transition.

The candidate is one exact playable work or cut. A channel, profile, reel index, thumbnail, or player shell is not a video candidate.

### Route `both`

Use `both` only when static and temporal evidence are both decision-critical. Do not use it as a hedge for unresolved intent.

Choose exactly one mode:

- `parallel_packs` — default for an integrated campaign that needs a standalone image pack and standalone video pack. Each pack independently produces 30 qualified, 20 selected, and 10 rejected results.
- `unified_territory` — only for one mixed reference deck whose territories intentionally combine still and moving-image evidence. Freeze exact image/video qualified and selected quotas before discovery. Qualified quotas must sum to 30; selected quotas must sum to 20; rejected quotas must sum to 10.

Changing `routing.strategy` after discovery increments `intent_version` and invalidates selection artifacts.

## 4. Clarification Budget

Ask zero to three actual user-facing clarification questions across the whole
intent-freeze phase. A subquestion joined with “and” still counts as one only
when one answer naturally covers both parts; do not game the limit with compound
questionnaires.

Questions must target high expected information gain:

1. **Decision/deliverable** — “Which concrete deliverable or production decision should these references inform?”
2. **Positive/negative boundary** — “What must appear, and what must be avoided; or what is one positive and one negative anchor?”
3. **Access/shareability** — “Must every result open without login, or may I use your already-authorized signed-in or paid sources?”

Ask only the unresolved question(s) that could change the run. Do not ask for keywords, known source sites, professional job titles, scoring weights, or arbitrary demographic fields when they can be inferred.

Maintain `clarification_questions` with every actual question, answer,
`asked_at`, and `effect_on_intent`. The operational budget applies to the actual
conversation; the array is its recorded representation. The run validator can
check only that the recorded array has at most three entries and is internally
valid. It cannot observe omitted conversation turns, so validator `PASS` is not
proof that no unrecorded question was asked. If runtime transcript attestation
exists, retain it separately as external attestation; do not invent it from the
array or add an unsupported row to the validator-input evidence contract.

## 5. Exploration Instead Of Interrogation

If uncertainty remains after the budget:

1. freeze the known hard constraints;
2. record uncertain axes and reversible defaults;
3. run a small probe across at least three substantially different territories;
4. compare evidence yield and contradiction rate;
5. choose the route or preserve competing territories with an inference note.

A probe may inform routing but does not count toward the final verified 30 until each candidate passes the normal hard gate.

## 6. Access Policy

Freeze the schema-defined `access_policy` booleans: `allow_public_web`, `allow_signed_chrome`, `allow_subscription`, `allow_geo_or_age_gated`, `public_shareable_required_for_delivery`, and `fallback_on_blocked`.

Common profiles are:

- public-only: public allowed, all session/gated modes false, public shareability required;
- authorized-session allowed: enable only the specifically authorized mode, label every session-bound item, and use public fallback when available;
- mixed with public priority: public allowed and preferred, authorized modes enabled only where they add material evidence, fallback enabled.

Authorization to inspect an existing login is not authorization to disclose identity, download media, bypass controls, or reuse the work. Rights are a separate matrix.

## 7. Rights Scope

Record the requested use of references without making legal conclusions unsupported by evidence. Keep these dimensions separate:

- discoverable;
- viewable;
- shareable without session;
- downloadable;
- usable in an internal reference board;
- commercially reusable.

Each dimension uses `allowed | prohibited | permission_required | unknown | not_applicable` plus an evidence basis. “Viewable” never implies any downstream permission.

## 8. Route Conflicts And Genuine Blockers

Ordinary ambiguity is not a blocker. Continue using reversible inferences. Block or return an incomplete run only when a non-inferable conflict changes the work's identity, such as:

- the user requires mutually exclusive modalities/deliverables and declines an integrated route;
- a required private source has no authorized access and no adequate fallback;
- exact market/legal/brand restrictions are indispensable but contradictory;
- the allowed source universe cannot yield 30 qualified candidates after all registered fallbacks.

In all cases complete unaffected artifacts, record the isolated blocker, and never relax verification or count requirements.

## 9. Feedback-Driven Rerouting

When feedback changes any hard axis:

1. write a feedback event before modifying the brief;
2. increment `intent_version`;
3. update only the evidence-backed fields;
4. invalidate candidates, approaches, receipts, territories, and selections that depended on the old field;
5. resume from the earliest affected phase;
6. preserve superseded artifacts for audit.

Example: “I need a full-body model inside a huge fashion set, not a product still life” changes `human_presence`, `scene_scale`, likely `deliverable_type`, source-family weights, and query lanes. It is not solved by adding more product-photography adjectives.

## 10. Route Acceptance Checks

The route passes only when:

- the decision to inform is specific enough to test relevance;
- the chosen modality can actually show the needed evidence;
- `both` has one declared mode and frozen quotas where required;
- no more than three clarification questions were actually asked, and every one
  is represented in `clarification_questions`;
- `scene_scale` and `human_presence` are explicit;
- access and rights are separated;
- every inference is evidence-bound and reversible;
- `intent_brief.json` validates before broad search.

These checks validate declared route evidence and internal consistency. Without
external transcript or tool attestation, they do not independently prove the
conversation history or the real-time existence of a production plan.
