---
name: complex-structure-product-asset-lock-board
description: "Use when the user provides product reference images for complex structures, complex mechanical or electronic devices, multi-part objects, articulated/folding/open-close products, products with multiple states, interfaces, controls, connectors, support nodes, hidden top/bottom/back details, or high-risk structural nodes, and needs a video-ready Complex Structure Product Asset Lock package. Directly call Codex built-in /image gen to create separate 16:9 asset boards that lock structure overview, critical closeups, state variants, interface/operation areas, and decomposition relationships; never treat this as a simple multi-angle product board, poster, or prompt-only task."
---

# Complex Structure Product Asset Lock Board

Chinese name: 复杂结构产品资产锁定板

Create a complex-structure asset package for downstream image and video generation. The leading rule is **structural lock**: preserve the product's real structure, part hierarchy, connection logic, state logic, interfaces, materials, and high-risk nodes before caring about beauty.

This skill is not a pretty product rendering workflow, not a single crowded collage, not a poster, not a generic multi-angle board, and not an engineering drawing unless the user explicitly asks for that style.

## Scope

Use this skill when the product reference set contains or implies any of these risks:

- mechanical complexity, exposed structure, arms, hinges, pivots, wheels, screws, clamps, supports, motors, cables, rails, telescoping parts, or load-bearing nodes;
- complex electronics, ports, controls, screens, connectors, buttons, knobs, handles, contact surfaces, or human-operation areas;
- multiple parts, layers, modules, accessories, inner/outer shells, lids, cases, inserts, modular assemblies, or visible assembly logic;
- multiple stable states such as expanded/stored, open/closed, working/off, extended/retracted, assembled/disassembled, use/static;
- top, bottom, back, underside, asymmetric, hidden, or easily mirrored geometry that matters for video continuity;
- high-risk materials such as mesh, perforation, fabric, carbon fiber, rubber, metal, plastic, glass, translucent parts, or mixed finishes.

Use another workflow when:

- the product is low-risk, simple, and needs only one six-view identity board: use `multi-angle-product-identity-lock-board`;
- the hard problem is dense packaging text, label copy, logo, specs, ingredients, or certifications on packaging: use `packaging-product-identity-label-lock-board`;
- the user asks only for an ad scene, mood image, poster, prompt rewrite, or concept exploration without structural locking.

Completion criterion: accept the task only when complex structural stability is a core success factor.

## Input Gate

Require at least one product visual reference. If no product image exists, ask for reference images instead of inventing the product.

Before image generation, study every uploaded reference and classify each image as one or more of:

- overall view;
- multi-angle view;
- local structure view;
- key component view;
- different state view;
- folded / expanded / open / closed / stored state view;
- interface / button / control / operation area view;
- material / texture view;
- detail closeup;
- packaging / accessory view;
- low-value duplicate;
- invalid image.

Then extract the structural lock map:

- overall silhouette, volume, and proportions;
- primary body, secondary structures, and key components;
- connection, support, load-bearing, hierarchy, front/back/left/right/top/bottom relationships;
- asymmetry and non-mirrored features;
- top, bottom, back, underside, or hidden structures that are visible or source-supported;
- moving, folding, opening, detachable, telescoping, or modular parts;
- interfaces, controls, contact areas, and human-operation zones;
- material directions, surface textures, seams, joints, and drift-prone local regions.

Completion criterion: every reference image has a role, and the product's structure can be described without inventing unseen critical details.

## Risk Audit

Identify the nodes that video models are most likely to damage. Prioritize:

- hinges, pivots, shafts, joints, connecting arms, rails, sliding parts, telescoping parts, folding nodes;
- support parts, cross-braces, wheel groups, underside mechanisms, load-bearing points;
- seams, split lines, latches, edges, socket/plug interfaces, ports, buttons, dials, levers, control surfaces;
- component boundaries, part nesting, caps, lids, inner/outer shell relationships, accessory attachment points;
- mesh, perforation, fabric, carbon fiber, rubber, metal, plastic, transparent/translucent material transitions;
- any asymmetric, easily simplified, easily merged, easily omitted, or easily mirror-flipped area.

Classify each important node:

- `locked`: visible enough to generate and check;
- `inferred`: partly visible, structurally plausible, but not source-confirmed;
- `blocked`: critical and not visible enough to lock.

Only report a hard blocker when a missing view or detail would make a critical structural lock unreliable. Do not stop unrelated boards because one node is blocked.

Completion criterion: high-risk nodes are ranked before boards are planned.

## Asset Package Plan

Always generate separate boards. Do not compress all information into one busy image.

Fixed boards, never omit:

1. **Structure Overview Board**: lock overall spatial structure and proportions.
2. **Critical Structure Closeup Board**: lock the most drift-prone local nodes.

Automatically add extension boards when the audit calls for them:

3. **State Variation Board**: add when the product has key stable states.
4. **Interface / Operation Board**: add when ports, controls, buttons, contact zones, or operation logic matter.
5. **Structural Decomposition Relationship Board**: add when layered, modular, inner/outer, accessory, assembly, lid/body, or part hierarchy relationships matter.

Completion criterion: the plan names every board that will be generated and explains which audit finding activates each extension board.

## Board Specifications

All boards default to:

- separate generated image per board;
- horizontal 16:9, 4K ultra-clear;
- clean white, near-white, or light gray neutral background;
- clear even studio light or neutral lock-board light;
- subtle natural shadows only;
- no scene, props, hands, people, poster styling, dramatic lighting, cinematic stage lighting, ornate layout, decorative text, large titles, arrows, callouts, legends, status text, or explanatory overlays unless the user explicitly requests them;
- product-native text only when it truly exists on the product surface.

### A. Structure Overview Board

Generate one board with exactly these 8 complete views unless source evidence makes one view impossible:

1. front;
2. back;
3. left side;
4. right side;
5. 3/4 front;
6. 3/4 rear;
7. top view;
8. bottom / underside view.

Requirements:

- show the complete product in every view with no cropping of key structures;
- keep one product identity across all views;
- keep proportions, part positions, connection logic, material direction, front/back/left/right/top/bottom relationships, and asymmetry consistent;
- treat top and bottom views as mandatory structural evidence, not decorative extras;
- show back, top, bottom, and underside structures when they are source-supported;
- never mirror a real asymmetric design into a symmetrical one;
- never lock only the outline while letting internal structure drift.

Completion criterion: the overview board gives video models a stable full-body structural reference from all eight structural directions.

### B. Critical Structure Closeup Board

Generate at least 6 closeups. Expand to 8-12 closeups when complexity warrants it.

Choose closeups from the risk audit, not from prettiness:

- connection nodes;
- hinges, pivots, joints, shafts, sliding or folding nodes;
- support structures, load-bearing points, cross-braces, wheel or underside mechanisms;
- component boundaries, seams, latches, edge transitions, assembly points;
- ports, buttons, levers, dials, grips, controls, user-contact surfaces;
- material-risk regions such as mesh, perforation, fabric, carbon fiber, rubber, metal, plastic, glass, or mixed-material seams.

Each closeup must retain enough surrounding context to reveal where the detail belongs. Avoid abstract crops that cannot be reattached to the product.

Completion criterion: the closeup board locks the areas most likely to deform, disappear, merge, or be guessed incorrectly in video generation.

### C. State Variation Board

Add this board whenever the product has meaningful stable states.

Cover at least 2 states, and 3-4 states when needed:

- expanded / stored;
- open / closed;
- working / off;
- extended / retracted;
- assembled / disassembled;
- use state / static state.

Requirements:

- show clear static endpoints, not animation frames;
- keep the same product identity across states;
- do not change proportions, components, materials, or connection logic between states except where the real mechanism changes them;
- do not invent an intermediate or final state without source evidence.

Completion criterion: a downstream model can tell that all states are the same product in different stable configurations.

### D. Interface / Operation Board

Add this board whenever interfaces, controls, operation areas, or human-contact zones matter.

Cover:

- buttons, switches, levers, knobs, dials, sliders, screens, grips, handles, contact surfaces;
- ports, sockets, plugs, charging points, detachable connectors, cable entry points;
- operation zones whose shape, position, boundary, or hierarchy must not drift.

Requirements:

- show the operation area clearly without turning the board into a manual;
- lock shape, placement, boundaries, layer order, and surrounding structural context;
- avoid explanatory arrows, labels, and instruction text unless the user explicitly requests them.

Completion criterion: ports, controls, and operation zones are visually stable enough for close product shots and handling shots.

### E. Structural Decomposition Relationship Board

Add this board whenever the product has visible hierarchy, assembly logic, layered structure, modular parts, lids, inner/outer shells, accessories, or part nesting.

Use mild separation or gentle decomposition. Do not default to a technical exploded diagram.

Requirements:

- show which part belongs where;
- show what sits above/below, inside/outside, front/back, attached/detached;
- preserve real proportions, material identity, and assembly relationships;
- do not reveal or fabricate hidden internal mechanisms without source evidence.

Completion criterion: a downstream model can infer component ownership and assembly relationships without relying on text labels.

## Image Generation

Call the available Codex image-generation capability directly, using Codex built-in `/image gen` when exposed by the interface. If no image-generation tool is callable, report this as a hard blocker and do not substitute a prompt-only deliverable.

Generate boards one by one from the asset package plan. Build an internal prompt for each board from:

- all uploaded product references as the only product identity source;
- the structural lock map;
- the risk audit and node confidence labels;
- the board-specific specification;
- the global negative constraints.

Do not show internal image prompts unless the user explicitly asks to inspect prompts.

Global negative constraints for every board:

- no redesign, beautification, modernization, premiumization, simplification, restyling, rebranding, relabeling, recoloring, or invented features;
- no dropped parts, merged parts, wrong left/right, wrong front/back, wrong top/bottom, false symmetry, fake hidden structure, or unsupported underside/back/top invention;
- no single overloaded collage pretending to complete the whole asset package;
- no poster, advertisement, lifestyle scene, mood image, infographic, engineering blueprint, manual page, title-heavy layout, or non-product text pollution.

Completion criterion: every planned board is generated as a separate image, or a specific board is marked blocked only because required source evidence or image-generation capability is missing.

## QA And Continuation

After each generated board, inspect it against the structural lock map.

Check:

- same product identity across all boards;
- same silhouette, proportions, main components, connections, material direction, state logic, and asymmetry;
- full 8-view coverage for the Structure Overview Board, including top and bottom / underside;
- closeups target the ranked high-risk nodes and keep enough context;
- state boards preserve identity across stable endpoints;
- interface boards preserve controls, ports, contact zones, and boundaries;
- decomposition boards preserve part ownership and assembly hierarchy;
- no invented part, missing real part, false symmetry, left/right swap, hidden-structure hallucination, decorative text pollution, poster style, or simple-product-board downgrade.

If a board fails but generation can continue, repair or add the narrowest necessary board rather than stopping at analysis. Prioritize repairs:

1. missing or wrong critical structure;
2. false symmetry, left/right/front/back/top/bottom error;
3. missing top, bottom, underside, or back view;
4. state inconsistency;
5. interface/control drift;
6. decomposition/part ownership confusion;
7. material or high-risk detail drift;
8. non-product text pollution or layout clutter.

Completion criterion: final delivery either has all required boards generated and checked, or names the precise missing source evidence that blocks the remaining structural lock.

## Output Contract

Default user-facing reply is concise and in Chinese. Include the generated images or image results, then report only:

- 本次生成了哪些资产板；
- 哪些是固定板；
- 哪些是自动扩展板；
- 发现了哪些硬阻塞，如有；
- 本次复杂结构资产包已锁定哪些关键内容；
- QA 结果：`approved` / `conditional` / `not_approved`。

Do not output a long tutorial, internal prompt dump, or text-only plan when image generation is available.

Use `conditional` when some useful boards were generated but one or more critical views/details are `inferred` or `blocked`. Use `not_approved` when structure, identity, state logic, or high-risk nodes drift enough that the package should not be used for downstream video continuity.

End condition: the complex product has a video-ready structural asset package consisting of separate generated boards, with fixed structure overview and critical closeup boards plus every automatically required extension board, and the user can tell exactly what is locked, inferred, blocked, or rejected.
