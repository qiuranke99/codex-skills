# Multi-Agent Search Contract

This file governs agent roles, independence, search-space diversity, structured handoff, authenticated browsing, adversarial review, and root synthesis. More agents are useful only when they add independent hypotheses or checks.

## 1. Required Responsibilities

Every completed run must cover these responsibilities:

- `root_synthesizer` — freezes intent, owns the approach registry, resolves conflicts, and approves the final report;
- `search_scout` — executes one or more distinct method families and returns raw structured candidates;
- `credit_graph_scout` — recovers origins, credits, and adjacent works through accountable edges;
- `authenticated_source_operator` — solely controls signed-in Chrome sources when required;
- `capture_operator` — records browser/media observations without approving the evidence it captured;
- `verification_agent` — independently checks access, exact media, object match, provenance, and evidence level;
- `relevance_curator` — ranks by frozen brief and decision utility;
- `diversity_curator` — audits near-duplicates, territories, domains, source families, creators, regions, and modality quotas;
- `adversarial_auditor` — tries to falsify the completed pack.

Physical runtimes may be reused in different waves when capacity is constrained,
but reuse is not evidence of independence. Every decision-critical responsibility
below requires a distinct attributable agent execution ID and a persisted handoff:

- finder, capture operator, and approving verifier use pairwise-distinct IDs across the final set;
- relevance curator, diversity curator, root synthesizer, and adversarial auditor use distinct IDs and do not overlap finder/capture/verifier IDs;
- authenticated-source operator cannot approve evidence captured under its session identity;
- both curators receive the same hash-bound frozen input and attest that the counterpart's result was unseen;
- root resolution starts only after both curator reviews are frozen and hash-binds both review files;
- adversarial audit occurs only after root resolution and names every operative ID in `independent_from`.

## 2. Cognitive Diversity, Not Headcount Theatre

Use all useful available concurrency. Do not target a fixed number such as 64. Register a new scout only when it contributes at least one of:

- different method family;
- different source population;
- different discipline or credit graph;
- different market/language/region;
- explicit challenger hypothesis;
- independent evidence or audit responsibility.

Multiple agents running the same query over the same source are one method and do not satisfy diversity. When only a few slots exist, execute independent waves and persist all handoffs.

## 3. Information Firewalls

Before first-wave discovery:

- record no `approach.started_at` until intent approval and the immutable plan
  hash are frozen; then stamp the real search start before issuing the query;

- give each scout the frozen intent and its assigned hypothesis;
- freeze `run_mode` and the canonical approach-plan hash before any `production_live` search or capture;
- do not give scouts the root agent's favorite candidates or a shared preliminary ranking;
- do not let one scout's low yield redefine the brief for others;
- require candidates and failures in the same structured format.

Before curation:

- give both curators the same qualified 30 and frozen intent;
- do not reveal one curator's final ordering to the other until both reports are frozen;
- persist each review's shared `input_contract_sha256`, start/completion times, blindness assertion, and reviewer ID;
- persist a root resolution that binds the two review paths and exact file hashes;
- give the adversarial auditor the artifacts and requirements, but not a request to confirm the preferred answer.

The root synthesizer may share factual corrections across agents. It must record any intervention that changes an approach.

For `production_live`, the validator compares the recorded plan-freeze and
capture timestamps and verifies the plan hash. That establishes declared
artifact chronology and internal consistency only. Without signed external tool
attestation, it does not independently prove when the plan was created or when a
browser action occurred.

## 4. Approach Assignment

Each scout assignment names:

- `agent_id` and role;
- `approach_id`;
- falsifiable hypothesis;
- modality pack and intent version;
- source families and regions/languages;
- query lane and excluded overlap;
- expected evidence contribution;
- stop condition;
- structured return schema.

The approach registry, not an “Agent 1/2/3” list, is the orchestration authority. An agent can own multiple approaches; every approach remains independently traceable.

IDs and closure are run-global hard requirements:

- every `approach_id` is unique across the registry;
- every `query_id` is unique across all approaches, not merely within one
  approach;
- every approach binds exactly one declared `pack_id`, that pack's modality,
  and a non-empty decision axis;
- every executing agent is registered with a compatible scout/operator role;
- every candidate's approach/query trace resolves to the registered executor;
- a completed run contains only terminal `complete` or `abandoned` approaches;
- `complete` requires nonzero returned yield;
- `abandoned`, or any approach with returned items that did not all qualify,
  records structured failures that exactly cover its non-final candidates and
  failed receipts;
- `returned_count` exactly equals all candidate-ledger rows traced to the
  approach, while `qualified_count` exactly equals its final qualified rows; and
- at least three distinct methods occur among executed `complete` approaches;
  each pack has exactly one coverage row whose count and method set exactly
  match that pack's completed approaches, never planned labels or another
  pack's work.

## 5. Structured Scout Handoff

Scouts return:

- candidate JSONL records only for exact items;
- approach execution summary with raw/canonical counts;
- queries/native filters/credit edges actually used;
- source access observations;
- suspected duplicates;
- provenance leads and public fallbacks;
- failure codes and blind spots;
- next-step recommendation.

Scouts may mark candidates `raw`, `screened`, or `quarantined`; they may not mark their own items `qualified`, `selected`, or `audit_passed`.

A zero-yield lane is not a completed method. Close it as `abandoned` with its
failure evidence and next adjustment. A lane marked `complete` must contain
nonzero execution yield and arithmetically consistent returned/qualified counts.

## 6. Verification Wave

Assign candidates so no verifier approves its own discoveries. Verification may use automation for transport and metadata plus browser inspection for rendered-media semantics. Each receipt names:

- candidate and verifier;
- finder identity;
- independence relation;
- verification time and tool/access mode;
- access, media, object, provenance, dedup, and rights findings;
- evidence level and outcome;
- failure codes and replacement need.

Each E4 receipt also binds the browser capture record(s) used for access, media, object-match, and provenance decisions. Capture operators and verification agents remain separately attributable. The capture ledger records `record_origin`; synthetic and retrospective imports cannot cross the production-delivery gate.

If capacity requires one verifier for many candidates, independence is still valid as long as that verifier did not discover them. For high-risk login/player items, use a second spot-check or adversarial replay.

## 7. Authenticated-Source Operator

Only one active agent controls the user's signed-in Chrome research session at a time. Other agents submit a bounded queue containing canonical URLs, expected object, and required evidence. The operator returns sanitized observations and evidence references.

The operator must:

- follow the Chrome-control Skill/runtime contract;
- inspect only task-relevant pages;
- avoid actions that change external state;
- omit account identity and private session data;
- label session dependence and public shareability;
- finalize controlled tabs/session as required.

Other agents must not open competing browser-control sessions or infer login evidence from the operator's prose alone.

## 8. Curator Independence

### Relevance curator

Produces a frozen ordering and proposed 20 based on intent match, decision utility, craft, adaptation, and evidence. Reports weak axes and any candidate that should not have passed qualification.

### Diversity curator

Produces a separate concentration map, near-duplicate audit, 4–6 territory proposal, domain/source/creator/region counts, modality quota check, and any justified swaps. It cannot retain an irrelevant item merely to satisfy diversity.

### Root resolution

The root synthesizer compares both reviews candidate by candidate. Every swap from either curator's proposal records:

- disputed candidate IDs;
- competing criteria;
- evidence considered;
- final decision and rationale;
- affected territories and rejection dominance.

## 9. Adversarial Audit

The adversarial auditor assumes the pack is wrong until the evidence survives these attacks:

- soft 404, challenge, deleted/private page, consent wall, or irrelevant redirect hidden behind HTTP 200;
- image placeholder, wrong gallery item, missing asset locator, low-resolution unloaded proxy;
- poster-only, nonadvancing, muted background, wrong-version, or empty video player;
- search snippet or aggregator presented as original provenance;
- stale receipt or timestamp manipulation;
- exact/near duplicate, repost, mirror, cutdown, or same-campaign cluster hidden by URL variation;
- broken items counted among rejected 10;
- selected/rejected set mismatch;
- scorer drift after an intent-version change;
- one source/domain/creator/region/visual trope dominating the pack;
- signed-in item presented as publicly shareable;
- viewability presented as download or commercial-use permission;
- finder self-approval or missing role evidence;
- feedback recorded without invalidating dependent work.

The auditor returns pass/fail per attack, evidence, affected IDs, and earliest repair phase. A hard failure vetoes delivery.

## 10. Failure And Replacement Wave

When verification or audit fails:

1. quarantine the failed item; never move it to rejected 10;
2. register the failure against its approach/source;
3. choose a different registered fallback or new hypothesis;
4. discover and independently verify the replacement;
5. rerun dedup, both curator reviews where set composition changed, diversity, and adversarial checks;
6. recheck all 30 at delivery freshness.

Repeating a failed method unchanged is allowed only when evidence shows the failure was transient; record the new evidence.

## 11. Root Synthesis Contract

The root synthesizer accepts only schema-valid artifacts and attributable
declared evidence. It must establish from the input artifacts:

- intent and route are current;
- approach diversity and failure history are real;
- every qualified item has independent receipt;
- selection and diversity decisions reconcile;
- audit vetoes are closed;
- access and rights claims do not exceed evidence;
- the final board is rendered from the schema-valid, hash-bound input artifacts.

The root may not repair missing evidence by writing confident prose. If a required role or receipt is missing, the run is incomplete.

Every report binds exactly ten fixed core artifacts: intent, approach registry,
candidate ledger, receipt ledger, browser-capture ledger, shortlist, selected,
rejected, feedback ledger, and reference board. Reviews, resolution, adversarial
audit result, feedback-invalidated intent snapshots, and diversity-waiver
evidence are variable. `referenced_evidence_contract` must exactly cover these
validator-read files with canonical run-local paths, SHA-256 values, and complete
purpose sets; an omitted file or unused extra row fails. The report itself and
external validator results are not input evidence and cannot appear as
self-validating references.

## 12. Minimum Agent Trace

The verification report should expose, without private reasoning:

- agents/roles used;
- approach-to-agent mapping;
- candidate finder-to-verifier mapping;
- curator report references;
- authenticated-source operator evidence references when applicable;
- adversarial audit identity, time, checks, and outcome;
- unresolved dissent or waived constraints.

This trace makes the declared process separation internally auditable. Without
externally verifiable task attestations, role labels and hashes do not prove that
separate actors actually executed the work. They establish only declared
identity, content binding, and internal consistency. The trace must not include
chain-of-thought, credentials, private browser state, or unrelated agent
conversation.
