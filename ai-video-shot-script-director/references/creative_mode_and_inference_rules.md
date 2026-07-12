# Creative Mode And Inference Rules

## Decision order

1. User-declared intent and immutable content.
2. Supplied brand/product facts and approved copy.
3. Visible or document-supported evidence.
4. Internal continuity and established project canon.
5. Conservative directing inference.
6. Reversible creative completion.

Never upgrade levels 5–6 into levels 1–3.

## Creative modes

### `poetic_brand_film`

The ad is driven by association, sensation, metaphor, visual rhyme or symbolic montage. Do not require a literal place-time chain or a complete usage demonstration. Preserve conceptual transitions. Translate abstractions into visible action:

- “被滋养” → shoulders release, breath deepens, eyelids settle, skin highlight moves with the breath;
- “自由” → stride lengthens, arms open, body axis releases, camera distance increases;
- “高级” → precise product orientation, restrained performance, controlled highlight hierarchy, uncluttered blocking.

These are directing inferences, not product claims.

### `functional_demonstration`

The ad is driven by correct operation, application, comparison, mechanism, before/after evidence or proof. Define the relevant start state, action sequence, state change and end state. Never infer an efficacy, quantitative improvement, ingredient benefit, usage instruction, safety claim or legal assertion from category convention. If an exact fact is missing, mark only that fact unresolved and continue designing supported shots.

### `narrative_advertisement`

The ad is driven by character goals, events and causal change. Preserve motivation, geography, screen direction, prop state and character knowledge. Advertising function must still be explicit for each shot.

### `mixed_mode`

Declare a primary mode and assign a submode to each shot. Do not let a functional insert force the entire film into instructional language, or let poetic montage obscure an explicitly promised operation.

## Autonomous decisions that must not block

- shot size, camera height, camera angle and lens intent;
- subject placement and blocking;
- visible performance and micro-action;
- one primary camera movement;
- focus behavior;
- cut motivation and transition intent;
- screen direction and continuity edges;
- asset, keyframe and Previs risk assessment;
- conservative environmental and material behavior that does not assert product truth.

Record consequential decisions in `inferred_directing_decisions`.

## Decisions that cannot be fabricated

- product name, packaging text, logo, certification and mandatory disclaimer;
- ingredient, efficacy, comparative, clinical, safety and environmental claims;
- precise mechanism or usage instruction not supported by sources;
- mutually exclusive brand positioning;
- a product variant or physical construction contradicted by references.

If such a field is indispensable, mark it in `claim_boundary.compliance_unknowns` or the isolated blocker record. Do not stop unrelated work.

## Observable-language test

A shot passes only if a storyboard artist, animator or cinematographer can represent its action and ending state without guessing what an abstract adjective means. Mood words may remain as intent, but must be paired with visible behavior, spatial relation, light-independent camera facts or state change.

## One-primary-movement rule

Each shot has one dominant camera behavior. Compound paths may be expressed as phases of one coherent trajectory only when they share one intent. Multiple unrelated moves belong in separate shots. `locked_off` is a valid primary movement.
