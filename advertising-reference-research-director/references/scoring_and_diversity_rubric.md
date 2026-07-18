# Scoring And Diversity Rubric

This file governs hard gates, scoring, dominance, territory formation, diversity, selection, and rejection explanations. Scoring never rescues a failed evidence gate.

## 1. Gate Before Score

A candidate may be scored for the qualified shortlist only after it passes:

- exact candidate identity;
- current access and page-render check;
- exact image render plus locator, or exact video playback advancement;
- object match to the frozen intent;
- accountable provenance at the implemented evidence level E4;
- deduplication eligibility;
- hard must-have/must-not-have constraints;
- rights/shareability constraints that the brief marks as hard.

Failed items are quarantined and remain outside `shortlist_30.json`, `selected_20.json`, and `rejected_10.json`.

## 2. Multi-Dimensional Evaluation

Evaluate each qualified candidate on the nine schema-defined dimensions. Every dimension is `0–100` with an evidence-based rationale. Do not collapse them into one total.

| Dimension | Direction | Question |
|---|---|---|
| `relevance` | higher is better | Does the observed media satisfy the frozen subject, scene scale, human presence, must-have, must-not-have, visual/temporal axes, market, deliverable, and decision? |
| `craft_signal` | higher is better | Is the relevant execution unusually resolved, legible, and intentional? |
| `source_authority` | higher is better | How accountable and close to the responsible creator/owner is the source? |
| `freshness` | higher is better | How well does the work and receipt satisfy the brief's recency need? |
| `access_reliability` | higher is better | Can the item be repeatedly opened in its declared access context? |
| `link_durability` | higher is better | Is the canonical item/stable ID likely to remain addressable relative to available alternatives? |
| `evidence_completeness` | higher is better | How complete are exact media, object, credits, date/version, and provenance evidence? |
| `rights_risk` | lower is better | How much uncertainty or restriction affects the requested review/sharing use? This is risk evidence, not a rights grant. |
| `diversity_contribution` | higher is better | Does it add a useful territory, source family, market, creator, mechanism, scale, casting mode, or temporal grammar? |

Record the current `intent_version` through the candidate artifact, plus one concise rationale for every score. Legal state remains authoritative in the six-part rights matrix; `rights_risk` only helps compare candidates under the declared use case.

## 3. Relevance Anchors

Calibrate `relevance` with observable evidence:

- 90–100: satisfies all hard axes and nearly all important soft axes; no material contradiction;
- 75–89: satisfies hard axes and the core decision, with one noncritical gap;
- 50–74: interesting but only partially answers the decision; normally dominated in a strong pool;
- 0–49: weak or contradictory; should have failed object-match/hard relevance gate unless the brief explicitly preserves it as a qualified challenger.

Prestige, fame, awards, popularity, production budget, and source ranking cannot replace brief evidence.

## 4. Decision Utility And Adaptation

High decision utility identifies a mechanism, not a mood adjective. Examples:

- how a full-body model establishes scale inside a monumental set;
- how the key light separates translucent product edges;
- how a camera move converts product detail into environmental reveal;
- how cutting follows gesture rather than beat;
- how typography and imagery divide campaign roles.

For every selected item, name:

- `decision_informed`;
- `transferable_mechanism`;
- `do_not_copy`.

`do_not_copy` should identify distinctive composition, character identity, branded assets, exact set, campaign device, copy, music, or protected sequence where relevant. It is not a generic disclaimer.

## 5. Dominance And 30 To 20 Selection

The qualified shortlist contains exactly 30. Selection chooses exactly 20 and rejects exactly 10.

Candidate A dominates candidate B only when A is no worse on every scored
dimension (treating lower `rights_risk` as better) and strictly stronger on at
least one dimension. It should also be materially stronger on one or more of:

- decision utility;
- exact intent match;
- evidence/provenance;
- access durability under the brief;
- non-duplicative mechanism;
- territory or source diversity;
- adaptation value.

There is no total-score shortcut. Use relevance as the primary ordering, compare the other dimensions explicitly, and apply a novelty/diversity penalty to candidates that repeat an already selected mechanism, campaign, creator, source, or visual territory. Treat lower `rights_risk` as preferable only for the declared use case. Record every comparison that causes a rejection.

For every declared selected comparator, the machine gate enforces the actual
Pareto claim:

- the selected item cannot be worse on any of the nine dimensions;
- at least one dimension must be strictly better;
- `dominance_dimension` must name one of those strict improvements;
- if all nine scores are exactly equal, the rejection requires the schema-defined `score_tie_break` using `object.stable_id` in ascending lexicographic order;
- any mixed-sign trade-off fails `CURATION-02`; it may support a preference
  explanation, but it is not dominance and cannot be recorded as one.

This is a score-vector Pareto and tie-determinism check, not proof that the
scores or creative judgment are objectively correct. Do not describe validator
PASS as proving aesthetic quality.

Every rejected item must contain:

- `candidate_id`;
- `dominance_reason` with concrete evidence;
- one or more `dominated_by_candidate_ids` that belong to the selected 20;
- one schema-defined `dominance_dimension` naming the primary comparison axis;
- `stronger_candidate_class` explaining the winning class or territory role;
- `score_tie_break`, set to `null` unless all nine dimensions are exactly equal;
- `reuse_condition` explaining when this still-qualified reference would become useful.

Forbidden rejection reasons: “broken”, “unavailable”, “duplicate”, “unconfirmed”, “low quality”, “low score”, or “less relevant” without a concrete comparison. The first four belong in quarantine.

## 6. Default Diversity Contract

For a broad brief, the selected 20 must satisfy all defaults:

- at least 5 independent domains;
- at least 4 source families;
- 4–6 coherent visual territories;
- no more than 4 selected items from one domain;
- no more than 2 selected items from one campaign;
- no more than 2 selected items from one creator, unless co-credit identity would make this misleading and the waiver explains it;
- no more than 1 selected item from each near-duplicate group;
- appropriate market/region and discipline coverage for the frozen brief.

These are anti-collapse constraints, not an instruction to maximize arbitrary difference. A territory must still answer the same decision.

For `parallel_packs`, apply the full diversity contract independently to image and video. For `unified_territory`, apply it to the mixed 20 and also satisfy frozen modality quotas.

## 7. Narrow-Brief Waiver

A tightly constrained campaign, single-creator study, exact remake analysis, or limited source universe may justify a waiver. The waiver must be frozen before final selection and contain, directly or through its evidence records:

- violated rule(s);
- evidence that compliant alternatives were searched and why they were worse or nonexistent;
- why relaxing the rule improves the stated decision rather than convenience;
- the smallest necessary deviation;
- approver/auditor identity;
- remaining concentration risk.

A waiver cannot relax exact `30/20/10`, evidence level, media verification, provenance, freshness, or finder/verifier independence.

## 8. Territory Formation

Organize the selected 20 into 4–6 territories for broad briefs. Each territory must contain:

- a precise territory name based on mechanism, not vague mood;
- decision hypothesis;
- inclusion rule and exclusion rule;
- member candidate IDs;
- shared borrowable mechanism;
- meaningful internal variations;
- risk or failure mode;
- relationship to other territories.

Avoid decorative labels such as “Bold”, “Premium”, “Fresh”, or “Cinematic” without observable definition. Examples of useful territory names include “full-body figure as architectural scale marker”, “hard specular product edges in deep negative space”, or “gesture-matched cuts across practical locations”.

No territory may exist only to absorb leftovers. Every selected candidate belongs to exactly one primary territory; secondary tags are allowed.

## 9. Independent Curator Reviews

Two reviews are required:

- `relevance_curator`: optimizes hard brief match and decision utility without access to the diversity curator's final ranking;
- `diversity_curator`: audits concentration, duplicate mechanisms, source/region/creator collapse, and territory coverage without silently lowering hard relevance.

The root synthesizer resolves disagreements and records the decision. Neither curator may be the original finder for all affected candidates. The adversarial auditor independently tests the resulting set.

## 10. Selection Explanation Template

For each selected item, populate the schema fields:

```text
why_fit: <observable match to frozen brief>
decision_supported: <specific decision>
transferable_mechanism: <mechanism that can be adapted>
do_not_copy: <distinctive/protected content or execution>
source_tags: <source role/signal>
access_tags: <public/session-bound and shareability>
rights_tags: <summary labels backed by the candidate rights matrix>
diversity_contribution: <territory/set contribution>
```

For each rejected item, populate the schema fields:

```text
qualified_before_selection: true
dominance_dimension: <primary schema-defined comparison axis>
dominance_reason: <specific evidence-backed comparison>
stronger_candidate_class: <winning class or territory role>
dominated_by_candidate_ids: <selected candidate ID(s)>
score_tie_break: <null, or the schema-defined exact-vector stable-ID tie rule>
reuse_condition: <condition under which this qualified candidate becomes preferable>
```

## 11. Final Set Checks

Before rendering the board, prove:

- shortlist has exactly 30 unique qualified IDs;
- selected has exactly 20 IDs and rejected exactly 10;
- the two sets are disjoint and their union equals the shortlist;
- every selected/rejected item remains E4 within freshness;
- diversity defaults pass or a valid waiver exists;
- modality quotas pass where applicable;
- selected items have complete adaptation/do-not-copy explanations;
- rejected items have concrete dominance records;
- scores bind the current `intent_version` and current media receipt.
