# Query Lane Playbook

This file governs search-space construction, approach registration, credit-graph expansion, failure recording, and stopping conditions. Search diversity means different explanatory methods, not cosmetic query variation.

## 1. Approach Registry Before Discovery

Create and validate `01_orchestration/approach_registry.json` before broad search. The registry root binds `registry_id`, `run_id`, `intent_id`, `intent_version`, `created_at`, the independence policy, agents, approaches, and coverage. Register at least three independent approaches per pack. Each approach must contain the schema fields:

- stable `approach_id`, exact `pack_id`, pack-compatible `modality`, non-empty
  `decision_axis`, canonical `method`, and falsifiable `hypothesis`;
- `queries`, each with stable ID, exact query text, locale, and round;
- `source_family_ids` and `executing_agent_id`;
- `favored_route_disclosed: false` for independent scouts;
- `returned_count`, `qualified_count`, and `qualification_rate`;
- structured `failure_records`, `next_round_adjustment`, and status.

Counts are ledger-derived. `returned_count` equals every candidate row whose
trace points to the approach; `qualified_count` equals only that approach's
qualified/selected/rejected rows in the final 30. Each failure record binds a
unique failure ID, one registered query/round and source family, observation
time, failure code, the exact non-final candidate IDs, any receipts for those
candidates, a substantive reason, and a fallback action. Across an approach,
those records must cover every non-final returned candidate and failed receipt
exactly once. A record with no candidate/receipt evidence is legal only for an
actual zero-yield abandoned lane. Every covered candidate must carry the same
`agent_trace.query_id` and `source.source_family_id` declared by its failure
record; split mixed query/source paths into separate records.

Express region, language, native-filter, credit-edge, and fallback intent through
the registered hypothesis, source-family IDs, and query records. Keep decision
axis and modality in their required structured fields. Preserve any additional
execution detail in schema-approved evidence artifacts rather than adding
undeclared JSON properties. Declare coverage as one unique row per routing pack;
never pool methods across parallel image/video packs.

An approach is distinct only when it changes the evidence route, source population, or retrieval model. Three synonym bundles over the same source are one approach.

## 2. Canonical Method Families

Use at least three of these; prefer four to six for a broad brief:

### A. Direct category lane

Search the product/service/category, campaign type, usage situation, market, format, and year. Good for market context; vulnerable to generic commercial imagery and SEO-heavy results.

Query grammar:

```text
[category/brand type] + [campaign/deliverable] + [scene/use] + [market/year]
```

### B. Visual or temporal mechanism lane

Search the visible mechanism that must be learned rather than the product noun.

Image mechanisms include full-body staging, monumental set, negative space, translucent material, hard-edge light, low-key palette, typographic image system, editorial casting, or architectural scale.

Video mechanisms include orbit/dolly/crane movement, gesture match, rhythmic montage, in-camera transition, simulation reveal, locked-off performance, macro-to-wide reveal, or sound-led cut.

```text
[mechanism] + [discipline/craft] + [format/source-role]
```

### C. Credit graph lane

Start with one strong attributable item. Extract accountable credits and traverse:

```text
work -> director / photographer / DOP / set designer / stylist / colorist
     -> production company / post studio / agency / brand
     -> original item page and adjacent works
```

This lane recovers origins, improves attribution, and finds coherent adjacent work. A credit edge must be evidenced by a source page, not guessed from style similarity.

### D. Award, editorial, and official lane

Use award archives, professional editorial curation, official brand/agency/creator pages, production-company rosters, and verified campaign archives. This lane provides craft or provenance signals, not proof of effectiveness.

### E. Adjacent-discipline lane

Translate the brief into another discipline that contains the missing mechanism:

- product still life -> fashion editorial or installation for human/scene scale;
- generic interior -> architecture, theatre, exhibition, or set design for spatial logic;
- generic animation -> title design, motion identity, scientific visualization, or VFX for motion grammar;
- generic beauty video -> dance/performance film for blocking and gesture;
- generic color adjectives -> cinematography/frame libraries for lighting architecture.

Record the translation rule so adjacent work remains decision-useful rather than merely attractive.

### F. Challenger lane

Seek a strong counterexample that preserves hard constraints while challenging the leading direction. Examples: low-production intimacy versus monumental spectacle; documentary casting versus polished fashion casting; locked camera versus constant motion. Challenger evidence prevents premature convergence.

### G. Region and language compensation lane

Search underrepresented markets and local-language sources when a global brief would otherwise collapse into US/Western-European English-language work. Record translation terms and region-specific archive depth. Do not manufacture a regional quota if the brief is explicitly local.

### H. Current-market lane

Use ad-transparency and performance-creative libraries for current cuts, placements, aspect ratios, and market variants. Treat “active” or “top ad” as a market/exposure signal only; independently assess craft and relevance.

G and H are coverage modifiers, not additional `approach_registry.method` enum values. Register them through the canonical method that actually performs the search—for example `award_editorial_official`, `direct_category`, `adjacent_discipline`, or `challenger`—and express region/current-market scope in the hypothesis, source families, and queries.

## 3. Route-Specific Coverage

### Image pack

Cover at least three distinct image evidence families appropriate to the decision, such as:

- original photographer/director/brand/agency work;
- design, packaging, campaign-system, or editorial portfolio;
- fashion/model/editorial;
- architecture/set/interior/installation;
- cinematography/frame/color;
- current print/social advertising.

Search for exact image-bearing item pages. Do not stop at mood-board pins, search-result thumbnails, or project indexes.

### Video pack

Cover at least three distinct moving-image evidence families, such as:

- original director/production/brand film;
- advertising craft and credits archive;
- award archive;
- curated film/fashion/culture;
- motion/CG/VFX;
- current-market ad library.

Search for exact works/cuts with playable evidence and accountable origin. Do not count channel pages or showreels unless the showreel itself is the research object.

### Unified mixed pack

Every approach declares which image and video quota it serves. Do not let the easier modality consume the quota. Territories must explain how still and temporal evidence work together.

## 4. Search Waves

### Wave 0 — calibration probe

When needed, test at least three divergent territories with a small sample. Record which assumption each probe tests. Probe results are not automatically qualified.

### Wave 1 — independent broad discovery

Run method-diverse scouts without broadcasting the root agent's favored candidates. Seek roughly 45–80 raw candidates per pack. Return structured candidate records, not prose lists.

### Wave 2 — provenance and credit recovery

For promising items, recover canonical item URLs, exact media locators, owner/credit evidence, dates/versions, and public fallbacks. Traverse credits for adjacent works.

### Wave 3 — gap-directed expansion

Inspect candidate coverage by decision axis, source family, territory, region, modality, human presence, and scene scale. Search only the missing cells. Do not keep expanding already saturated areas.

### Wave 4 — challenger and bias audit

Actively test the leading interpretation against contrary strong evidence. Register search-space blind spots, access bias, language bias, popularity bias, prestige bias, and same-creator clusters.

### Wave 5 — replacement search

After verification or dedup removes items, search for replacements through registered fallbacks. A replacement must pass the same gates; never relax evidence to close the count.

## 5. Candidate Capture

Each scout returns one record per exact candidate with, at minimum:

- candidate identity and modality;
- exact item URL plus canonical URL;
- exact image asset locator or video stable/player ID;
- title/work/campaign, creator/brand, date/version/region when observable;
- source ID, family, role, and signal type;
- query/approach/agent provenance;
- brief-match observations, not generic praise;
- credit edges and fallback sources;
- preliminary duplicate keys;
- access and rights unknowns;
- status `raw` or `screened`, never self-assigned `qualified`.

Search snippets, titles, summaries, and model recollection are leads only.

## 6. Failure Registry

Record every material failed path in the approach registry or its schema-approved failure collection:

- `no_results`
- `low_relevance`
- `product_still_bias`
- `missing_human_presence`
- `wrong_scene_scale`
- `homogeneous_style`
- `language_or_region_bias`
- `search_index_only`
- `unstable_deep_link`
- `login_required`
- `paywall_blocked`
- `challenge_or_bot_gate`
- `soft_404`
- `missing_exact_media`
- `empty_or_nonadvancing_player`
- `unknown_provenance`
- `duplicate_cluster`
- `rights_or_shareability_mismatch`
- `source_degraded`

For each failure record evidence, affected query/source, count, whether it is terminal, and the next alternative. Never retry the same method unchanged after a terminal failure.

## 7. Source Roles

Treat source role separately from source prestige:

- `discovery` — finds leads but may not prove the object;
- `evidence` — proves exact media, credits, date, version, or owner;
- `validation` — independently corroborates the same object or claim;
- `fallback` — preserves access or provenance when the preferred page is session-bound/degraded.

One source can serve multiple roles only when its evidence actually supports them. Social posts and search engines usually begin as discovery. Original owner pages usually provide evidence. Awards and trade archives often provide validation and credits.

Before using a source, resolve it through the schema-valid `source_registry.json`. Check its modalities, object/intent tags, signal type, region/language coverage, access requirements, linkability, verification capabilities, rights notes, fallbacks, `last_verified_at`, and `status`. `active` and `degraded` sources still require live run evidence. Record observed registry drift; never silently rewrite the historical run to pretend the source was always blocked.

Open-world discovery may surface a legitimate domain absent from the checked-in registry. In that case use `source_id=runtime:<normalized discovered_url host>`, bind it to one registered source family, require `source.domain` to equal the discovered URL host, and keep one registrable site domain mapped to one source/family identity within the run. Diversity counts registrable site domains, not arbitrary subdomains. A checked-in `source_id` must match its registry family. These rules prevent invented source names, domain aliases, or `s1.example.com` / `s2.example.com` host inflation from faking source diversity.

## 8. Stop Rules

Discovery does not stop because raw count reaches 30. Stop only when:

- every required pack has exactly 30 **qualified** candidates;
- all hard evidence receipts exist;
- candidate coverage satisfies the frozen decision axes;
- dedup and diversity gates pass or a valid narrow-brief waiver exists;
- unresolved failures cannot alter qualification or selection.

If fallback approaches are exhausted below 30, preserve the shortfall and failure evidence and return an incomplete/blocked state. Do not invent, duplicate, or downgrade candidates.

## 9. Anti-Patterns

Forbidden patterns include:

- static “top websites” list used as the search plan;
- multiple agents running the same query with different wording;
- domain prestige used as relevance or rights evidence;
- `site:` queries without opening the exact item;
- Pinterest/Instagram repost treated as original provenance when an origin can be recovered;
- 30 superficially different CDN URLs for the same work;
- all candidates from one language, market, creator, campaign, or visual trope without an explicit narrow brief;
- changing the brief to fit the available results;
- counting inaccessible candidates as the rejected 10.
