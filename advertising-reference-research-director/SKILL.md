---
name: advertising-reference-research-director
description: "Research, verify, curate, and explain high-quality advertising image and video references from global design, photography, architecture, fashion, cinematography, motion, advertising, and creator sources. Use when a user needs production-useful visual references, a reference board, mood-board research, campaign precedents, image references, video references, or both. Route from the creative decision being informed, ask at most three actual high-information questions, form exactly 30 independently checked and evidence-bound qualified candidates per pack, select 20 and reject 10 with evidence, use signed-in Chrome only when authorized and necessary, and learn from user corrections without overgeneralizing. Do not use for casual one-link lookup, unverified inspiration lists, unauthorized media downloading, copying protected work, or claiming third-party links will remain permanently available."
---

# Advertising Reference Research Director

中文名：广告参考图与参考视频检索导演

## Standalone Package Preflight

Before any workflow action, resolve this `SKILL.md` directory and run its
package-local OS-native preflight: on Windows,
`& 'scripts\preflight.ps1' -Format json`; on macOS/Linux,
`./scripts/preflight.sh --format json`. Proceed only when it exits zero and
returns `gate_mode=standalone_package`, `package_contract_ready=true`, and
`ready_for_skill_workflow=true`. The launcher runs this package's deterministic
contract in isolated Python mode. It does not inspect, invoke, or depend on any
sibling package or repository-level orchestration surface.

This preflight proves only that the exact local package passed its own tests.
It does not prove repository freshness, immutable provenance, remote
publication, browser attestation, or production-deliverable research evidence.

Turn a real creative or production decision into a source-backed,
evidence-bound, media-checked reference pack. This Skill owns intent routing,
search-space design, evidence collection, deduplication, `30 -> 20` curation,
adversarial audit, and feedback-driven correction. It does not treat a
prestigious site, an HTTP 200 response, a thumbnail, or a search snippet as
sufficient declared evidence that a reference is usable.

## Trigger And Boundary

Use this Skill when the user asks to:

- find advertising image references, video references, campaign precedents, visual territories, or production references;
- research high-quality examples across design, photography, architecture, set design, models, fashion, color, cinematography, motion, VFX, advertising craft, or current-market ads;
- create an evidence-bound reference board for a KV, shoot, film, pitch,
  storyboard, treatment, identity system, campaign, or cross-media system;
- replace a weak or homogeneous reference list with a diverse, attributable, decision-useful pack;
- revise reference research after feedback such as “too product-still-like”, “needs a full-body model”, or “the space is not large enough”.

Do not use this Skill to:

- return a casual handful of links when no research pack is requested;
- claim that curation, awards, popularity, or active ad placement proves commercial effectiveness;
- copy a reference, impersonate its creator, or grant reuse rights;
- download images by default or download video without separate user authorization and a lawful basis;
- expose account identity, cookies, tokens, subscription details, or other private Chrome state;
- present fewer than the required qualified candidates as a completed run.

This Skill finds and evaluates references. It does not create the final ad, storyboard, image, video, campaign strategy, or legal clearance.

## Canonical Resources

Read each applicable resource completely before executing its phase. Do not redefine its fields in prose or silently weaken it:

- `references/activation_and_release_boundary.md`
- `references/route_and_intent_contract.md`
- `references/source_registry.json`
- `references/query_lane_playbook.md`
- `references/evidence_and_access_policy.md`
- `references/scoring_and_diversity_rubric.md`
- `references/multiagent_search_contract.md`
- `references/feedback_learning_contract.md`
- `references/source_registry.schema.json`
- `references/intent_brief.schema.json`
- `references/approach_registry.schema.json`
- `references/candidate_item.schema.json`
- `references/verification_receipt.schema.json`
- `references/browser_capture_record.schema.json`
- `references/shortlist_30.schema.json`
- `references/selected_20.schema.json`
- `references/rejected_10.schema.json`
- `references/feedback_event.schema.json`
- `references/verification_report.schema.json`

Use the package scripts as the mechanical authority for validation, deduplication, gallery building, and contract tests. A prose review never substitutes for validator success.

## Input Gate: Route From The Decision

The first question is not “image or video?” It is: **which creative or production decision must these references inform?**

Infer ordinary research parameters from the user's brief, supplied examples,
current project artifacts, and explicit constraints. Ask zero questions when the
route and hard constraints are already clear. Ask at most three actual
user-facing questions for the entire intent-freeze phase, and only when each
answer can materially change route, source family, access policy, or acceptance:

1. Which deliverable or decision should the references inform?
2. What is one must-have and one must-avoid feature, or one positive and one negative anchor?
3. Must every result be publicly shareable without login, or may the run use the user's already-authorized signed-in/paid sources?

Never ask the user to supply professional search vocabulary. If uncertainty remains after the allowed questions, run a diverse exploratory probe and record the inference; do not keep questioning.

Record every actual clarification in `clarification_questions`. The operational
limit applies to the conversation; the array is only its recorded
representation. The validator can check the recorded count and structure but
cannot detect an omitted conversation turn. Do not describe a recorded count as
proof of the actual question count unless external transcript attestation exists.

Route by the evidence in `references/route_and_intent_contract.md`:

- `image`: static decisions such as KV, composition, product treatment, casting, wardrobe, set, spatial scale, color, light, texture, material, typography, or frame design;
- `video`: temporal decisions such as camera movement, blocking, performance, story, edit, rhythm, transition, VFX, or sound-image relationship;
- `both`: an integrated campaign or cross-media system genuinely requires both.

For `both`, declare exactly one mode before discovery:

- `parallel_packs` is the default: one image pack with its own exact `30 -> 20`, plus one video pack with its own exact `30 -> 20`;
- `unified_territory` is allowed only for one integrated mixed deck: exactly 30 total qualified candidates and 20 selected, with image/video quotas frozen in the intent brief before discovery.

Create `00_intent/intent_brief.json`, validate it, and freeze `intent_version` before broad search. `scene_scale` and `human_presence` are mandatory first-class axes, not optional prose.

Freeze `run_mode` at the same time:

- `production_live` is the only mode eligible for a production contract check.
  Its artifacts must record a preregistered, hash-bound approach plan
  before the earliest recorded search start, candidate discovery, or direct
  capture and retain the direct-browser observation records; the next paragraph
  states the limit of what those declarations establish.
- `test_fixture` is synthetic contract evidence. It may pass structural validation but is never production-contract-eligible or production-deliverable.
- `retrospective_smoke` preserves and validates historical point-in-time evidence. It cannot be relabeled or upgraded in place to `production_live`.

For `production_live`, the validator checks that the recorded intent approval
precedes or equals the recorded plan freeze and that the recorded plan freeze
precedes the earliest `approach.started_at`, `candidate.discovered_at`, or
`capture.captured_at`. SHA-256 bindings and timestamps establish declared
artifact chronology and internal consistency only. They are not digital
signatures and do not independently prove when a plan or browser action
actually existed.

## Hard Invariants

These invariants are non-negotiable for every completed pack:

```text
qualified_candidate_count == 30
selected_count == 20
rejected_count == 10
selected and rejected are disjoint
selected union rejected equals the qualified shortlist
all 30 have fresh access, media, object-match, and provenance receipts
broken, duplicate, unconfirmed, probable, dead, challenge, placeholder,
wrong-object, and empty-player items are quarantined before the 30
```

The rejected 10 are valid references that lost a documented comparison. Bad links and failed verification never count as rejected candidates. A run that has 29 qualified candidates is incomplete, not “close enough”. For `parallel_packs`, apply every invariant independently to both modalities.

The run records only time-stamped verification declarations at delivery, never
permanent third-party availability. Default final-recheck freshness is 30
minutes unless the run records a stricter or explicitly justified wider window.

## Durable Run Package

Write every run under a project-selected root using this minimum layout:

```text
runs/ad-reference-research/<run_id>/
├── 00_intent/intent_brief.json
├── 01_orchestration/approach_registry.json
├── 02_candidates/candidate_ledger.jsonl
├── 03_verification/verification_receipts.jsonl
├── 03_verification/browser_capture_records.jsonl
├── 04_selection/shortlist_30.json
├── 04_selection/selected_20.json
├── 04_selection/rejected_10.json
├── 05_feedback/feedback_ledger.jsonl
├── 06_output/reference_board.html
└── 06_output/verification_report.json
```

`verification_report.json.artifact_contract` binds exactly ten fixed core
artifacts: intent, approach registry, candidate ledger, receipt ledger, capture
ledger, shortlist 30, selected 20, rejected 10, feedback ledger, and reference
board. The report itself is the contract container, not an eleventh input that
can validate itself.

The relevance, diversity, and resolution reviews referenced by the final
curation traces, the adversarial-audit result, feedback-invalidated intent
snapshots, and diversity-waiver evidence are variable. The
`referenced_evidence_contract` must exactly cover those validator-read files:
each safe run-local path appears once with its SHA-256 and complete purpose set.
Omissions and unused extras both fail. Other source or regression facts must be
captured inside a supported core or referenced artifact, not added as an
unconsumed contract row.
External `validation_result*.json` and `parallel_pack_validation_report.json`
files are validator outputs, never input evidence.

For `parallel_packs`, use one shared intent/orchestration root and two self-contained pack directories whose IDs exactly match `intent_brief.routing.pack_contracts`. Feedback is pack-local so every report hashes the exact correction chain that affected that pack; duplicate a cross-pack correction into both ledgers with the same feedback ID and scope.

```text
<run_root>/00_intent/intent_brief.json
<run_root>/01_orchestration/approach_registry.json
<run_root>/packs/<image_pack_id>/{02_candidates,03_verification,04_selection,05_feedback,06_output}/...
<run_root>/packs/<video_pack_id>/{02_candidates,03_verification,04_selection,05_feedback,06_output}/...
<run_root>/parallel_pack_validation_report.json
```

`parallel_pack_validation_report.json` is validator output written only after
both pack inputs have passed; it is never a preexisting input or self-asserted
gate. Every pack-specific artifact binds its `pack_id`. Validate each pack
independently, then require the external root result to record that both declared
pack IDs passed. Never merge their counts or let one pack compensate for the
other. Preserve all disqualified raw candidates and failure evidence in each
candidate ledger or declared quarantine records so the final 30 cannot hide
search failures.

## Workflow

### 1. Freeze intent, route, and acceptance

Extract the decision to inform, deliverable, modality route, subject, `scene_scale`, `human_presence`, visual axes, temporal axes, must-have, must-not-have, positive/negative anchors, market/region, freshness need, access policy, rights scope, and diversity constraints. Separate user facts from inference. Record every material inference with basis, confidence, and reversibility.

If the user corrects the brief at any later phase, stop ranking affected candidates, apply `references/feedback_learning_contract.md`, increment `intent_version`, invalidate affected evidence, and reroute from the earliest changed layer.

### 2. Register independent approaches before search

Preflight `references/source_registry.json` against its schema. Select sources by modality, object/intent tags, evidence role, region/language, current status, access mode, linkability, media-verification capability, and fallback—not by a flat prestige ranking. Treat `last_verified_at` and status as registry evidence, not a promise that the source is currently healthy; record observed drift in the run failure evidence and use declared fallbacks.

Create `01_orchestration/approach_registry.json` before broad discovery. Freeze
its immutable plan projection as `registration.plan_sha256` before the earliest
`approach.started_at`, `candidate.discovered_at`, or browser
`capture.captured_at`. Record each actual search start in `started_at`;
backfilling it after discovery is invalid. `production_live` requires
`registration.kind=preregistered`; reconstructed approaches belong only to
`retrospective_smoke`. Use at least three genuinely different methods, not
three synonym lists. Cover the lanes defined in
`references/query_lane_playbook.md`, including a challenger or
adjacent-discipline method when the brief permits it.

Each approach records its `pack_id`, hypothesis, decision axis, modality, source
families, queries, executor, returned count, qualified count, failures, and next
adjustment. Coverage is declared once per pack and may count only that pack's
completed methods. Maintain a failure registry. Repeating a failed query/source
combination without new evidence is forbidden.

Make every `approach_id` unique across the registry and every `query_id` unique
across the entire run. Every candidate trace must resolve to a registered
approach, query, and compatible executor. A completed run contains only terminal
`complete` or `abandoned` approaches: `complete` requires nonzero returned yield;
zero-yield lanes are `abandoned`. Derive `returned_count` from every candidate
ledger row traced to the approach and `qualified_count` from that approach's
final qualified/selected/rejected rows; never trust self-reported totals. Every
abandoned or partially qualifying lane records structured failures that exactly
cover its non-final candidates and any bound failed receipts. Count method
coverage from executed complete approaches, never from planned labels.

### 3. Discover broadly and traverse credit graphs

Target roughly 45–80 raw candidates per pack before hard-gating; this is a search target, not a completion count. Use global and region-compensating source families. Treat search engines and social feeds as discovery surfaces, then recover stable item pages and attributable origins.

When a strong candidate exposes credits, traverse the director, photographer, DOP, set designer, stylist, colorist, VFX studio, production company, agency, and brand graph. Use the graph to find original publication and adjacent work; do not merely keep rewriting adjectives.

### 4. Canonicalize and quarantine before verification

Normalize URLs and stable media IDs. For every final candidate, bind an
image-byte or sampled-video fingerprint to the media-purpose capture: exact or
sample-manifest SHA-256, 64-bit perceptual hash, sampling method/count, asset
locator, computation time, and tool identity. Bind every receipt to the same
validator-recomputed final-30 comparison-set hash and fixed perceptual-distance
threshold. Group exact duplicates, CDN variants, reposts, mirrors, cutdowns,
regional versions, same-campaign near matches, and perceptual near-duplicates.
Keep one representative per near-duplicate group unless version comparison is
itself an explicit research objective. Exact identity collisions are never
waivable. A retained soft near-duplicate group requires one hash-covered manual
version-review artifact that exactly binds the group members and fingerprints.

Quarantine inaccessible, irrelevant, weakly attributable, placeholder, wrong-object, duplicate, or otherwise ineligible items. Do not score them as rejected 10. Preserve compliant raw/screened/quarantined rows, but require every candidate, receipt, and capture row to bind the current run, intent version, pack, modality, and existing counterpart. Every capture must be referenced by a receipt, every receipt must resolve to a candidate, and no qualified receipt or qualified/selected/rejected candidate may exist outside the final 30.

Before qualification, populate each candidate's schema-backed
`intent_alignment`. Bind it to the frozen constraint projection with
`intent_constraints_sha256`; account exactly for the decision, subject,
scene scale, human presence, every visual axis, applicable temporal axes,
must-have/must-not-have criteria, every anchor, market, language, content-age
limit, and rights boundary. Cross-market or cross-language transfer requires a
substantive rationale. An image candidate must be a `project_image`; a video
candidate must be a `specific_video_work` or `specific_cut`. A changed intent
hash invalidates candidate qualification until alignment is rebuilt.

### 5. Verify every candidate independently

The finder cannot approve its own result. Assign an independent verifier and follow `references/evidence_and_access_policy.md`.

For images, verify the exact intended image renders and is addressable through a stable asset locator inside the item page. For videos, verify the exact work/cut, a real player, and playback-time advancement; a poster frame or player shell is insufficient. In all cases verify object match, provenance, access mode, and source role.

Persist each qualifying browser observation in `03_verification/browser_capture_records.jsonl`. Bind every E4 receipt to the canonical SHA-256 of its capture record(s) and cover access, media, object match, and provenance. A final receipt timestamp must equal its latest bound capture. Imported fixture or retrospective records cannot satisfy the production gate.

Use already-authorized signed-in Chrome only when it adds necessary evidence or access. One authenticated-source operator owns that session. Label session-bound evidence honestly and never make private state part of the deliverable.

### 6. Form exactly 30 qualified candidates

Only candidates that pass every hard gate may enter `shortlist_30.json`. Keep searching and verifying until each pack has exactly 30. If access or evidence cannot support 30 after the registered fallback approaches are exhausted, emit an honest incomplete or blocked run with the shortfall and failure evidence; do not create a final pack or claim completion.

### 7. Select 20 and reject 10

Apply the hard gates, scoring, dominance comparisons, near-duplicate control, and diversity rules in `references/scoring_and_diversity_rubric.md`. Use separate relevance-first and diversity-first reviews. Organize the selected 20 into 4–6 decision-useful visual territories unless a narrow-brief waiver is justified.

Every selected item explains:

- why it matches the frozen brief;
- which decision it informs;
- what mechanism may be borrowed;
- what content or execution must not be copied;
- source, access, sharing, and rights labels.

Every rejected item names the stronger comparison or territory pressure that dominated it. “Low score”, “less relevant”, or “broken link” alone is not an acceptable rejection rationale.

### 8. Recheck, audit, and render

Reverify all 30 within the declared freshness window. Run an adversarial audit for soft 404s, challenge pages, empty players, wrong versions, provenance drift, duplicates, hidden login dependence, score manipulation, quota violations, and rights overstatement. The adversarial auditor must be independent of discovery and final ranking.

Build `reference_board.html` from validated JSON, not as a second hand-edited source of truth. Include the 20 selected items, territory grouping, selection explanations, and a clear statement of access/rights limits. Preserve rejected and quarantined evidence in machine-readable artifacts.

Freeze the exactly-ten core `artifact_contract`, then resolve the final
relevance/diversity/resolution review refs, adversarial-audit result,
feedback-invalidated intent snapshots, and diversity-waiver evidence into the
variable `referenced_evidence_contract`. Its rows must exactly equal this
validator-read set; every path is canonical run-root-relative, appears once,
exists, and matches its recorded SHA-256 and complete purpose set.

Run the package validator and contract tests. Write validator results outside the
input report. The report, feedback ledger, and referenced evidence must never
point to a report as proof that the run was already validated. Any failed hard
gate returns the run to the earliest affected phase.

### 9. Learn from user feedback without corrupting global policy

Store user corrections in `05_feedback/feedback_ledger.jsonl`. Record the actual evidence/quote, failed assumption, matching feedback class/error layer, signal class, version-bound model delta, `invalidated_candidate_ids`, `invalidated_approach_ids`, `invalidated_query_ids`, invalidated artifact refs, scope evidence, confidence, supersession, and intent versions before/after.

For completed validator input, every feedback event has
`completion_evidence.status=applied`, a valid `completed_at`, and the exact
required run-local artifact type/path/SHA-256 bindings, with no `validator_ref`
field. Input must never claim `validated`. Only the external validator result
derives validated status after the repaired run passes; it does not mutate or
point back from the feedback input.

An explicit current-run constraint changes the brief immediately. A one-off inferred preference remains a soft session signal. Project promotion requires an explicitly confirmed project rule or two prior supporting corrections; global promotion requires an explicitly confirmed global rule. The ledger must say `external_persistence_state=not_applied_by_skill`; external memory changes require a separate authorized workflow. Never hide feedback learning in changed keywords alone.

## Multi-Agent Independence

Use all useful available agent capacity, but optimize for cognitive diversity rather than a fixed agent count. Required responsibilities are:

- method-diverse search scouts;
- credit-graph scout;
- one authenticated-source operator when needed;
- independent `verification_agent`;
- relevance curator;
- diversity curator;
- adversarial auditor;
- root synthesizer.

When concurrency is limited, execute roles in independent waves and preserve role identities and evidence boundaries. Do not let one agent silently combine finder, verifier, curator, and auditor. Follow `references/multiagent_search_contract.md` for structured handoffs and vetoes.

## Access, Chrome, And Rights

Keep these facts separate for every result: discoverable, viewable, link-shareable without session, downloadable, usable in an internal review board, and commercially reusable.

`browser_verified_login_context` means only that the item was verified in an authorized signed-in session. It does not mean the recipient can open it, the asset may be downloaded, or the work may be reused. Set `shareable_without_session=true` only after a session-free recheck succeeds, `false` only after session dependence is actually observed, and `unknown` when no session-free recheck was performed. Prefer a public canonical or fallback source when it preserves the same object and provenance.

Never print or persist account identity, cookies, auth headers, tokens, private messages, or unrelated browsing data. Image download is an explicit optional branch. Video download is out of scope unless separately authorized and legally permitted.

## Completion Gate

Claim a pack complete only when the execution obligations below were actually
met and the declared evidence plus external validator result establish their
mechanically checkable subset. Without external transcript or tool attestation,
conversation history, actor identity, and browser chronology remain declared
rather than cryptographically proven:

- route and both-mode semantics are frozen and explainable;
- no more than three actual clarification questions were asked, and the recorded
  `clarification_questions` contains every one;
- the exactly ten core artifacts exist, validate, and match their hashes;
- the variable `referenced_evidence_contract` exactly covers the final
  relevance/diversity/resolution reviews, adversarial audit,
  feedback-invalidated intent snapshots, and diversity-waiver evidence, with no
  omitted or unused row and matching paths, purposes, and hashes;
- for production contract eligibility, `run_mode=production_live`, recorded
  intent approval precedes or equals plan freeze, plan freeze strictly precedes
  the earliest `approach.started_at`, `candidate.discovered_at`, or
  `capture.captured_at`, and the package validator says
  `production_contract_eligible=true` and `production_deliverable=false`;
- each modality pack's complete candidate ledger has exactly the final 30 in
  qualified/selected/rejected states, with 20 selected and 10 rejected and no
  extra qualified rows; any additional raw/screened/quarantined rows remain
  pack-bound and evidence-closed;
- every receipt resolves to a same-pack candidate, every capture resolves to a
  same-pack candidate and registered approach, and every capture is hash-bound
  from at least one receipt—foreign-pack rows and orphan evidence are forbidden;
- all 30 have fresh independent receipts and hash-bound declared capture evidence
  for access, exact media, object match, and accountable provenance;
- every video receipt records playback advancement and every image receipt binds
  a concrete asset locator;
- no broken, probable, unconfirmed, duplicate, challenge, placeholder, wrong-object, or empty-player item entered the 30;
- deduplication and diversity rules pass or a narrow, evidence-backed waiver is recorded;
- at least three distinct completed approach methods satisfy unique ID, executor,
  terminal-status, yield, failure-recording, and coverage closure; verifier
  evidence, both curator reviews, and adversarial audit are traceable;
- selected and rejected explanations satisfy their contracts;
- access, session sharing, download, internal-use, and commercial-reuse states are not conflated;
- every user correction changed the appropriate legal `vN` intent version,
  invalidated dependent work, and reaches input status `applied`; only the
  external result may derive `validated`;
- all 30 passed final freshness recheck;
- `scripts/validate_research_run.py --run-dir <run_root> --require-production-contract-eligible --output <run_root>/parallel_pack_validation_report.json` (or a pack-local output path for single modality) and the applicable deterministic/adversarial tests exit zero.

Ordinary validator `PASS` may describe a fixture or retrospective smoke run and
is not by itself a production completion claim. Even a production-live PASS is
only contract-eligible. Validator success establishes
strict structure, hash bindings, recorded time/order constraints, and internal
consistency of declared point-in-time evidence. Because capture records are not
cryptographically attested, it does not independently establish that the browser
action occurred, permanent availability, legal clearance, originality,
aesthetic quality in the abstract, commercial performance, or permission to
reproduce the referenced work.

The legacy `--require-production-deliverable` flag always fails closed with
`ATTEST-01`. A separate trusted external attestation process must establish any
browser-action or delivery claim; never create or self-declare that attestation
inside the research run.

## Publication Boundary

Publish only the reusable Skill package. Never commit project `runs/`, browser receipts, user quotes, local paths, credentials, screenshots, or customer reference boards. GitHub synchronization must use the repository's validated release path and pass package tests, distribution checks, and a fresh-clone verification.

All bundled artifact writers fail closed: they serialize before mutation, write
through an fsynced sibling temporary file, atomically replace regular outputs,
refuse leaf symlinks and input/output clobbering, and preserve receipt history.

The package-local standalone preflight authorizes this package's workflow only;
it must never be cited as GitHub-latest, immutable-snapshot, whole-repository
release, browser-action, or production-deliverable evidence. Repository
publication is a separate maintainer operation and is never a runtime
prerequisite for this Skill.

## Minimal Invocation

`Use $advertising-reference-research-director to determine whether this brief needs image references, video references, or both; create independently checked, evidence-bound 30-to-20 reference pack(s); require the production-contract-eligible gate for a live run; label unsigned package evidence as not production-deliverable; and explain every selection and rejection without treating hashes as signatures or access as reuse permission.`
