# Canonical Completion Rules

## Authority And Source States

Use this fixed authority order:

1. explicit user fact;
2. Source-Corroborated multi-reference evidence;
3. clear Source-Locked single-reference evidence;
4. perspective, scale, occlusion, and geometry inference;
5. material and scene-type prior;
6. generative completion.

Never let a category prior overwrite clear reference evidence. Keep these states distinct:

- `source_locked`: directly visible and confirmable;
- `source_corroborated`: independently supported by multiple inputs;
- `canonical_completion`: unseen but required inside the minimum-complete boundary and approved after testing;
- `conflict`: evidence disagreement requiring resolution or a hard blocker;
- `out_of_scope_unknown`: outside the chosen coverage boundary and intentionally unresolved.

`Observed Rendered Color` is not automatically `Intrinsic Base Color`.

## Minimum Complete Scene Boundary

Include only regions needed to preserve scene identity, likely production viewing directions, main/reverse/necessary side directions, applicable high/low reveals, entries/exits/connections, landmark relations, occluded areas likely to be revealed, and continuity-critical scale/topology.

Exclude unused rooms, entire cities, infinite terrain, whole planets, entire star systems, and other regions no delivered asset can observe. No region inside the included boundary may remain `unresolved` when the package is approved.

## Candidate Completion

For every hidden region that can materially alter structure, compare multiple candidates internally. Score each candidate on:

- visible evidence and vanishing-point compatibility;
- scale and topology;
- material and scene language;
- unnecessary landmark count;
- high/low reveal survivability;
- bidirectional convergence and loop closure;
- minimum necessary complexity;
- neutral-appearance stability;
- absence of inherited source look.

Approve exactly one candidate. Record rejected candidates and reasons in `conflict_report.md`; write only the accepted result into `canonical_completion_elements`. Once frozen, all later assets and 4K prompts use that same completion. Reopen it only when visual QA proves a contradiction.

## Expansion And Shared Scene Memory

Expand from the primary reference through small adjacent changes before attempting fully hidden reverse views. Maintain source anchoring on every generation:

1. original scene references for identity and visible geometry;
2. frozen Scene Canon for topology, scale, exclusions, and completion;
3. Canonical Diagnostic Master for neutral appearance;
4. approved adjacent anchors for local continuity;
5. relevant landmark/scale assets for the current direction.

Never use only the previous generated image or only a text summary. Record each approved new structural fact immediately in Scene Canon. Never let separate views invent separate backs, exits, peaks, coastlines, roads, celestial positions, wave directions, or base colors.

## Bidirectional And Loop Closure Tests

For important directions, expand from both sides and test convergence through declared coverage-graph paths. Each path must name its directed edges, supported motion types, reveal order, overlap invariants, and any required translated parallax. A loop must return to its initial landmark identity and handedness with every directed edge present.

Check landmark position, counts, left/right relation, doors/windows, dimensions, roads/coastlines/ridges/horizon, celestial relations, fixed objects, materials/base colors, completion stability, and neutral appearance. The generation dependency DAG is separate: it controls when a frozen prompt can bind approved predecessor images, not whether a camera path exists.

If the paths do not converge, set `repair_required`; rebuild the conflicting region and invalidate dependent views and prompts. Do not preserve two contradictory versions.
