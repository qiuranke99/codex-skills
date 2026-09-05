---
name: advertising-reference-research-director
description: "Find and verify advertising image or video references for a visual or production decision. Use for mood boards, campaign precedents, lighting, sets, casting, camera, motion, or editing references; explain what each example contributes."
---

# Advertising Reference Research Director

Find attributable work that helps the user make a concrete creative decision.
Deliver useful references, with evidence for the actual images or video passages
discussed and clear reasons to select them.

## Scope the research

- Preserve the user's deliverable, requested count, references, exclusions, and
  level of detail. Infer ordinary search vocabulary yourself. Ask only for
  missing information that would materially change the research.
- Use images for composition, casting, set scale, light, colour, and materials;
  use video for camera movement, performance, rhythm, transitions, and sound.
  Research both only when both contribute to the decision.
- Notice scene scale and human presence when they matter. A tabletop product
  photograph cannot answer a brief for a full-body model in monumental space.
- If no count is specified, choose the smallest set that covers the useful
  directions. Do not expand a small request into a fixed-size candidate pool,
  rejected-item quota, multi-agent pipeline, or collection of JSON receipts.

## Search and select

1. Identify the hard constraints and the decisions the examples must inform.
   Use [query_lane_playbook.md](references/query_lane_playbook.md) when a direct
   search is too narrow, repetitive, or biased toward the wrong discipline.
2. Consult relevant entries in [source_registry.json](references/source_registry.json)
   for source leads. Search by modality, craft, object, or region; do not load
   the whole catalog by default. Its entries are starting points, not verified
   current availability, a whitelist, or a ranking of quality.
3. Open exact work pages and recover original creators or accountable credits.
   Follow useful credit links to adjacent work. Search elsewhere when a source
   is blocked or a method repeatedly yields irrelevant results.
4. Inspect the actual image or relevant video passage before describing its
   visual or temporal mechanism. Apply the checks in
   [evidence_and_access_policy.md](references/evidence_and_access_policy.md).
5. Remove wrong objects, inaccessible required media, repost duplicates, and
   redundant examples. Compare fit, execution, and additional decision value.
   A famous creator, award, or active ad placement does not establish relevance
   or commercial effectiveness. Do not manufacture numerical scores or Pareto
   dominance to justify a creative preference.
6. Stop when the requested count and decision coverage are met. If evidence or
   access prevents this, deliver the verified subset and explain the specific
   shortfall. Never fill a quota with weak or unverified examples.

Use a single agent for ordinary research. Delegate only when the user requests
parallel work or an applicable task instruction authorizes it and there is an
independent contribution. Never claim independent verification merely because
the same agent used different role labels. Coordinate access to a shared
authenticated browser when delegation is used.

## Deliver the useful evidence

Follow the requested format. A linked comparison list or table is sufficient
unless the user requests a board, deck, download, or machine-readable dataset.
For each selected work provide:

- title, creator/brand when verified, and the exact work link;
- the relevant image locator or video time range when the page contains more
  than the passage being discussed;
- the observed mechanism, the decision it informs, and any mismatch;
- what can guide the user's execution, with a distinction between a general
  technique and copying distinctive branded or protected content;
- material access limitations and the actual extent of verification.

Group by useful creative direction when it improves comparison. Explain
rejections only when requested or when the tradeoff matters. Recheck uncertain
or session-bound links near delivery; do not impose a universal expiry window
on stable observations or promise that third-party links will remain live.

Apply user corrections to the affected brief, search method, sources, or
selection. Revisit only dependent conclusions. A one-off correction is not a
global preference; do not update memory or project rules without authorization.

## Completion and maintenance

Completion means the requested references and explanations have been delivered
with evidence limits stated. File hashes, validator success, and self-written
receipts cannot establish media inspection, visual quality, rights clearance,
human approval, or business performance.

This package is independently usable. There is no runtime preflight or release
gate. Maintainers can run `python -B scripts/test_contract.py` after editing the
source catalog; it checks local catalog integrity only and is not research QA.
