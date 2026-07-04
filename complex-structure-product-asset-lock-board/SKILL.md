---
name: complex-structure-product-asset-lock-board
description: "Use when the user provides product reference images for complex structures, complex mechanical or electronic devices, multi-part objects, articulated/folding/open-close products, products with multiple states, interfaces, controls, connectors, support nodes, hidden top/bottom/back details, or high-risk structural nodes, and needs one or more video-ready Complex Structure Product Asset Lock boards. First run a per-board source gate: generate every requested or automatically relevant board whose own source evidence is sufficient, block only boards whose required evidence is missing, and clearly report whether the result is a complete package, a partial board-scoped deliverable, or no deliverable. Call /image gen only for board-source-approved boards, then output the final image-generation prompt used for each delivered QA-passing board as chat text, not trace, hidden reasoning, or a single package-level prompt."
---

# Complex Structure Product Asset Lock Board

Chinese name: 复杂结构产品资产锁定板

Create source-supported complex-structure product asset boards for downstream image and video generation. The leading rule is **board-scoped structural lock**: generate only the boards whose required visible structure can be verified from the user's references, and block the boards that would require guessing.

This skill has three final outcomes:

- `full_approved`: every board in the requested scope is source-approved, generated, QA-passed, prompt-bound, and delivered. If `request_scope` is `complete_package`, this also means the complete package is deliverable.
- `partial_approved`: at least one requested or automatically relevant board is delivered, but one or more requested, automatically relevant, or complete-package boards are blocked, not requested, or QA-failed. This is a board-scoped deliverable, not a complete package.
- `not_approved`: no board can be delivered because no board passes source gate and QA, or a systemic identity/structure failure invalidates all generated boards.

There is no prompt-only outcome, and there is no permission to invent missing hidden structure. A partial board set is allowed only as `partial_approved` with explicit `blocked_board_manifest`; it must never be called `complete_package`.

## Scope

Use this skill when the product reference set contains or implies any of these risks:

- mechanical complexity, exposed structure, arms, hinges, pivots, wheels, screws, clamps, supports, motors, cables, rails, telescoping parts, or load-bearing nodes;
- complex electronics, ports, controls, screens, connectors, buttons, knobs, handles, contact surfaces, or human-operation areas;
- multiple parts, layers, modules, accessories, inner/outer shells, lids, cases, inserts, modular assemblies, or visible assembly logic;
- multiple stable states such as expanded/stored, open/closed, working/off, extended/retracted, assembled/disassembled, use/static;
- top, bottom, back, underside, asymmetric, hidden, or easily mirrored geometry that matters for video continuity;
- high-risk materials such as mesh, perforation, fabric, carbon fiber, rubber, metal, plastic, glass, translucent parts, or mixed finishes.

Use another workflow when:

- the product is low-risk, simple, and needs only one simple six-view identity board: use `multi-angle-product-identity-lock-board`;
- the hard problem is dense packaging text, label copy, logo, specs, ingredients, or certifications on packaging: use `packaging-product-identity-label-lock-board`;
- the user asks only for an ad scene, mood image, poster, prompt rewrite, or concept exploration without structural locking.

If the user asks for only one board, set `request_scope: selected_boards` and gate only that board plus its dependency closure. If the user asks for a full asset package or does not narrow scope, set `request_scope: complete_package`, evaluate all relevant boards, deliver approved boards, and block the rest.

## Input Audit

Require at least one product visual reference. If no product image exists, output `not_approved` and ask for product reference images instead of inventing the product.

Before any image generation, study every uploaded reference and classify each image as one or more of:

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
- top, bottom, back, underside, and hidden structures;
- moving, folding, opening, detachable, telescoping, or modular parts;
- interfaces, controls, contact areas, and human-operation zones;
- material directions, surface textures, seams, joints, and drift-prone local regions.

If the global product identity, primary body proportions, or main component layout cannot be verified, all boards are blocked. If only a board-specific area is missing, block that board and continue with other source-approved boards.

## Per-Board Source Gate

Run this gate before `/image gen`. Create a **Structural Coverage Matrix** and classify evidence for each board independently. For each matrix item, use only:

- `verified`: supplied directly or cross-verified by multiple references with no structural contradiction.
- `missing`: absent, hidden, cropped, too blurry, too low-resolution, contradictory, or only guessable.
- `not_required_for_this_board`: not needed for the requested board's truthful scope.

The matrix must track:

- `view_id`: front, back, left, right, 3/4 front, 3/4 rear, true top, true bottom / underside, plus `source_scoped_verified_view` when only user-supplied views are approved;
- `state_id`: every stable state endpoint needed by the requested or automatically relevant board;
- `node_id`: every high-risk structural node needed by the board;
- `interface_id`: every port, control, button, connector, contact surface, and operation zone needed by the board;
- `material_zone`: every high-risk material or finish region needed by the board;
- `hidden_no_fill_zone`: every hidden, blocked, internal, underside, back, cavity, or uncertain region that must not be invented;
- `required_source`, `status`, and `failure_reason`.

Create these manifests before generation:

- `complete_package_required_manifest`: every board that would be required for a complete complex-structure package.
- `requested_board_manifest`: boards requested by the user or selected by default for this run.
- `approved_board_manifest`: boards whose own source gate passes and may be submitted to `/image gen`.
- `blocked_board_manifest`: boards blocked by missing source, missing dependency closure, user exclusion, or QA failure.
- `delivered_board_manifest`: boards generated, QA-passed, prompt-bound, and delivered.

Use these run-level statuses:

- `request_scope`: `complete_package` or `selected_boards`;
- `source_gate_status`: `full_source_approved`, `partial_source_approved`, or `source_not_approved`;
- `approval_status`: `full_approved`, `partial_approved`, or `not_approved`;
- `package_completeness_status`: `complete_package`, `partial_board_set`, or `no_deliverable`;
- `generated_assets_delivered`: `complete_package`, `board_scoped_partial_set`, or `none`;
- `video_handoff_status`: `full_package_video_ready`, `approved_boards_video_ready_only`, or `blocked_do_not_use`;
- `asset_registry_status`: `register_complete_package`, `register_approved_boards_only`, or `do_not_register`;
- `prompt_output_status`: `per_delivered_board_only` or `no_prompt_output_for_not_approved`;
- `contamination_guard_status`: `pass` or `fail`.

Use these board-level statuses:

- `board_source_gate_status`: `source_approved`, `source_blocked_missing_reference`, or `not_applicable`;
- `board_delivery_status`: `delivered_approved_asset_board`, `blocked_not_delivered`, `qa_failed_not_delivered`, or `not_requested`;
- `board_dependency_status`: `closed`, `blocked_by_missing_source`, or `blocked_by_systemic_failure`;
- `prompt_status`: `final_prompt_bound`, `no_prompt_for_blocked_board`, or `prompt_mismatch`.

Rules:

- Missing evidence for one board blocks that board, not every board.
- Missing global identity, main silhouette, primary proportions, or core component layout blocks all boards.
- Missing hidden, bottom, internal, or interface evidence must not be imported into an approved board prompt except as a negative no-fill constraint.
- `blocked_board_manifest` content must not appear as positive generated content in approved boards.
- Do not infer, approximate, mirror, beautify, or synthesize missing structure to satisfy a board gate.
- Do not generate a board whose required dependency closure is missing.

## Risk Audit

Identify nodes that video models are most likely to damage. Prioritize:

- hinges, pivots, shafts, joints, connecting arms, rails, sliding parts, telescoping parts, folding nodes;
- support parts, cross-braces, wheel groups, underside mechanisms, load-bearing points;
- seams, split lines, latches, edges, socket/plug interfaces, ports, buttons, dials, levers, control surfaces;
- component boundaries, part nesting, caps, lids, inner/outer shell relationships, accessory attachment points;
- mesh, perforation, fabric, carbon fiber, rubber, metal, plastic, transparent/translucent material transitions;
- any asymmetric, easily simplified, easily merged, easily omitted, or easily mirror-flipped area.

Build a **Critical Node Registry**. Every node must include:

- `node_id`;
- owning component and connected component;
- front/back/left/right/top/bottom position when verified;
- left-side, right-side, centered, or asymmetric status;
- symmetric counterpart, if any;
- source image evidence;
- required closeup board cell when a closeup board is source-approved;
- mechanism role, if it moves, supports load, folds, locks, slides, hinges, or connects parts.

If a node is needed for a requested board and cannot be verified, block that board. If it is not needed for the board's truthful scope, keep it out of the positive prompt.

## Motion And Hidden-Structure Logic

For every moving, folding, opening, sliding, rotating, detachable, telescoping, latching, locking, or load-bearing mechanism that appears in a requested board, lock:

- endpoint A and endpoint B when both are visible;
- pivot axis, slide direction, rotation direction, travel path, or separation path when visible;
- stop point, latch point, lock point, contact point, clearance, and collision boundary when visible;
- user operation surface and force/contact area when visible;
- which components move together and which stay fixed when visible.

Create a **Hidden Structure / No-Fill Map**:

- mark hidden, internal, underside, back, occluded, cavity, blocked, or uncertain regions that must not be invented;
- if a hidden region is required for a board and no source evidence exists, block that board;
- if a hidden region is not required for a source-scoped board, keep it invisible, neutral, or covered rather than exposing fabricated internals;
- never use a decomposition, underside, interface, or closeup board to reveal unsupported internal mechanisms.

## Board Selection

Fixed complete-package boards:

1. **Structure Overview Board**: locks overall spatial structure and proportions.
2. **Critical Structure Closeup Board**: locks the most drift-prone local nodes.

Automatically required complete-package boards:

3. **State Variation Board**: required when the product has meaningful stable states.
4. **Interface / Operation Board**: required when ports, controls, buttons, contact zones, or operation logic matter.
5. **Structural Decomposition Relationship Board**: required when layered, modular, inner/outer, accessory, assembly, lid/body, or part hierarchy relationships matter.
6. **Material / Finish Lock Board**: required when high-risk material or finish zones matter.

For `request_scope: complete_package`, put all fixed and automatically required boards into `complete_package_required_manifest`, approve the boards with sufficient evidence, and block the rest.

For `request_scope: selected_boards`, put only user-requested boards into `requested_board_manifest`, evaluate their dependency closure, and mark other complete-package boards as `not_requested`.

## Board Specifications

All generated boards must use:

- separate generated image per board;
- horizontal 16:9, 4K ultra-clear;
- clean white, near-white, or light gray neutral background;
- clear even studio light or neutral lock-board light;
- subtle natural shadows only;
- no scene, props, hands, people, poster styling, dramatic lighting, cinematic stage lighting, ornate layout, decorative text, large titles, arrows, callouts, legends, status text, or explanatory overlays unless the user explicitly requests them;
- product-native text only when it truly exists on the product surface;
- no prompt text inside the generated image.

### A. Structure Overview Board

For a complete package, generate the full 8-view overview only when all views are verified:

1. front;
2. back;
3. left side;
4. right side;
5. 3/4 front;
6. 3/4 rear;
7. true top view;
8. true bottom / underside view.

For a partial board-scoped deliverable or selected-board request, the Structure Overview Board may be a `source_scoped_structure_overview_board` when the references verify the product's exterior identity, proportions, front/back/side/3/4 relationships, major frame geometry, and visible state, but lack true top or true bottom. In that case:

- show only verified views;
- do not fabricate top, underside, interior, or blocked mechanisms;
- report the missing true top/bottom in `blocked_board_manifest` as the reason the board is not a complete 8-view overview;
- set `package_completeness_status: partial_board_set` unless the complete package was not requested and all selected boards passed.

Requirements:

- show the complete product in every delivered view with no cropping of key visible structures;
- keep one product identity across all views;
- keep proportions, part positions, connection logic, material direction, front/back/left/right relationships, and asymmetry consistent;
- never mirror a real asymmetric design into a symmetrical one;
- never lock only the outline while letting visible internal structure drift.

### B. Critical Structure Closeup Board

Generate this board only when enough high-risk nodes are verified for a useful closeup set. Include at least 6 closeups unless the user explicitly requests a smaller selected closeup board.

Choose closeups from the risk audit, not from prettiness:

- connection nodes;
- hinges, pivots, joints, shafts, sliding or folding nodes;
- support structures, load-bearing points, cross-braces, wheel or underside mechanisms;
- component boundaries, seams, latches, edge transitions, assembly points;
- ports, buttons, levers, dials, grips, controls, user-contact surfaces;
- material-risk regions such as mesh, perforation, fabric, carbon fiber, rubber, metal, plastic, glass, or mixed-material seams.

Every closeup must retain enough surrounding context to reveal where the detail belongs. Missing nodes remain in `blocked_board_manifest`; they must not be invented inside a delivered closeup board.

### C. State Variation Board

Generate this board only for verified state endpoints. Cover at least 2 states when available, and 3-4 states when needed and verified:

- expanded / stored;
- open / closed;
- working / off;
- extended / retracted;
- assembled / disassembled;
- use state / static state.

If the user provides only one state, block the state board unless the selected request explicitly asks for a one-state lock board instead of a variation board.

### D. Interface / Operation Board

Generate this board only when the relevant interface and operation areas are verified. Cover buttons, switches, levers, knobs, dials, sliders, screens, grips, handles, contact surfaces, ports, sockets, plugs, charging points, detachable connectors, and cable entry points that are visible in the sources.

### E. Structural Decomposition Relationship Board

Generate this board only when every shown layer, module, accessory, lid/body, inner/outer, or assembly relationship in the board is verified. Use mild separation or gentle decomposition. Do not default to a technical exploded diagram. Do not reveal or fabricate hidden internal mechanisms without source evidence.

### F. Material / Finish Lock Board

Generate this board only when enough material or finish zones are verified for a useful lock board. Lock material boundaries, texture direction, reflection strength, translucency, perforation scale, weave or grain scale, edge transitions, and component ownership for verified zones only.

## Image Generation

Call Codex built-in `/image gen` only for boards in `approved_board_manifest`.

Build a separate `final_image_generation_prompt` for each approved board from:

- all uploaded product references as the only product identity source;
- the verified structural lock map for that board;
- the risk audit items approved for that board;
- board-specific requirements;
- global negative constraints.

Do not show, draft, or provide image-generation prompts for blocked boards. If no board is approved, output the `not_approved` missing-reference report instead.

After board source approval, submit each board's `final_image_generation_prompt` to `/image gen`. This prompt is the public image-generation prompt used for that delivered board, not trace, not a trace, not hidden reasoning, not a hidden-reasoning log, not a source-audit log, and not a prompt-only substitute deliverable.

After generation and QA, output the exact final prompt for each delivered QA-passing board in the user-facing reply under `本次图片生成提示词`. If a board is repaired or regenerated, output only the final prompt corresponding to the accepted board. If the exact final submitted prompt for a delivered board is unavailable or cannot be matched to the accepted board, that board fails QA with `prompt mismatch`.

Do not output a single master prompt, package-level prompt, complete-package prompt, shared prompt, summary prompt, overview prompt, board-set prompt, generic reusable prompt, or any other single prompt as a substitute for board-level prompts. Each `final_image_generation_prompt` must correspond to exactly one delivered board. A prompt that covers multiple boards, uses `board_id` values such as `package`, `all_boards`, or `complete_package`, or cannot be matched one-to-one to a delivered QA-passing board fails QA with `prompt_scope_mismatch`.

Prompts must be board-distinct. Two prompt entries must not be identical or differ only by `board_id`, `board_name`, ordering, numbering, or generic wording. Each prompt must include the board type and board-specific requirements for its own generated board.

After each board passes QA, bind its prompt entry to the accepted generated result with `accepted_result_ref`. If an accepted board has no matchable result reference, that board fails QA with `prompt mismatch`.

`generation_prompt_sha256`, trace notes, audit logs, or summaries may be internal or optional evidence only; they never satisfy `final_image_generation_prompt` and never replace the public final prompt text.

Global negative constraints for every board:

- no redesign, beautification, modernization, premiumization, simplification, restyling, rebranding, relabeling, recoloring, or invented features;
- no dropped visible parts, merged visible parts, wrong left/right, wrong front/back, false symmetry, fake hidden structure, or unsupported underside/back/top invention;
- no single overloaded collage pretending to complete the whole asset package;
- no poster, advertisement, lifestyle scene, mood image, infographic, engineering blueprint, manual page, title-heavy layout, or non-product text pollution.

## QA Gate

After each generated board, inspect it against the verified structural lock map before treating it as an asset-board image.

Check:

- same product identity across delivered boards;
- same silhouette, proportions, main components, connections, material direction, state logic, and asymmetry within the delivered board scope;
- no delivered board shows unsupported true top, underside, hidden internals, ports, controls, or mechanisms;
- every `view_id`, `node_id`, `state_id`, `interface_id`, and `material_zone` approved for the board appears correctly;
- every `hidden_no_fill_zone` remains hidden, neutral, or explicitly blocked rather than fabricated;
- decomposition boards preserve verified part ownership and assembly hierarchy;
- every delivered board has one matching `final_image_generation_prompt` in `本次图片生成提示词`;
- the number of entries in `final_image_generation_prompts` equals the number of entries in `本次图片生成提示词`, the number of delivered QA-passing boards, and the number of boards in `delivered_board_manifest`;
- in `full_approved` complete-package runs, `delivered_board_manifest` must also equal `complete_package_required_manifest`;
- every prompt entry includes `accepted_result_ref` for the accepted generated board;
- no package-level, all-board, master, shared, summary, overview, board-set, generic reusable, or multi-board prompt is accepted; prompt-to-board matching must be strictly one-to-one;
- prompts are board-distinct; no two final prompts are identical or differ only by `board_id`, `board_name`, ordering, numbering, or generic wording;
- every final prompt includes board-specific requirements and never only says to generate the full complex structure asset package;
- every visible prompt corresponds to the final accepted `/image gen` result, not a rejected attempt or after-the-fact reconstruction;
- `generation_prompt_sha256`, trace notes, audit logs, or summaries are not accepted as substitutes for `final_image_generation_prompt`;
- prompts do not include hidden reasoning, source-audit trace, unsupported inferred structure, or instructions to add labels, arrows, titles, legends, callouts, or non-product text;
- no prompt text appears inside the generated image.

If a generated board fails local QA while other boards remain valid, move only that board to `blocked_board_manifest` with `board_delivery_status: qa_failed_not_delivered`. If the failure shows systemic identity, proportion, or structural drift that affects the whole product, set `contamination_guard_status: fail`, re-QA every generated board, and return `not_approved` if the package cannot be trusted.

## Output Contract

If at least one board is delivered, include generated images or image results, then report:

- `request_scope`;
- `source_gate_status`;
- `approval_status`;
- `package_completeness_status`;
- `generated_assets_delivered`;
- `video_handoff_status`;
- `asset_registry_status`;
- `prompt_reuse_status`: `reusable_only_with_delivered_QA_passing_boards`;
- `prompt_output_status`: `per_delivered_board_only`;
- `contamination_guard_status`;
- `complete_package_required_manifest`;
- `requested_board_manifest`;
- `approved_board_manifest`;
- `blocked_board_manifest`;
- `delivered_board_manifest`;
- generated boards;
- fixed boards delivered;
- automatically required boards delivered;
- blocked boards and exact missing product references needed;
- `final_image_generation_prompts`: same entries as `本次图片生成提示词`;
- `本次图片生成提示词`: for each delivered board, output `board_id`, `board_name`, `accepted_result_ref`, `prompt_role: public_final_image_generation_prompt`, `prompt_scope: accepted_QA_passing_board_only`, and `final_image_generation_prompt`;
- prompt count rule: `final_image_generation_prompts` must be a per-board list only, never a package-level prompt block; the number of `本次图片生成提示词` entries must equal the number of delivered QA-passing boards and `delivered_board_manifest`, and each entry must map to exactly one delivered board and one accepted result;
- verified key contents;
- QA result.

When `approval_status: partial_approved`, state plainly: `本次不是 complete package；只交付以下 QA 通过的 board-scoped assets。` Register or reuse only delivered approved boards, not a complete package.

When `approval_status: full_approved` and `package_completeness_status: complete_package`, register or reuse the package as a video-ready complex-structure asset lock package.

When `approval_status: full_approved` but `request_scope: selected_boards`, register or reuse only the selected delivered boards unless the selected set equals the complete package manifest.

If no board is delivered, output `not_approved`:

- `request_scope`;
- `source_gate_status`: `source_not_approved`;
- `approval_status`: `not_approved`;
- `not_approved_reason`: `source_insufficient`, `generated_board_failed_qa`, or `systemic_identity_or_structure_failure`;
- `package_completeness_status`: `no_deliverable`;
- `image_generation_decision`: `refuse_generation` if no board source-passed, or `discard_failed_generation` if generated boards failed QA;
- `video_handoff_status`: `blocked_do_not_use`;
- `generated_assets_delivered`: `none`;
- `asset_registry_status`: `do_not_register`;
- `prompt_reuse_status`: `no_reusable_prompt_allowed`;
- `prompt_output_status`: `no_prompt_output_for_not_approved`;
- `complete_package_required_manifest`;
- `requested_board_manifest`;
- `blocked_board_manifest`;
- reason;
- provided references summary;
- missing required product reference images;
- affected boards, high-risk nodes, states, interfaces, or decomposition relationships;
- minimum new product-reference set needed to rerun;
- statement that no asset-board images, reusable image/video prompts, partial video-safe ranges, asset IDs, or downstream-use instructions were produced because no QA-passing deliverable exists;
- statement that `final_image_generation_prompts` and `final_image_generation_prompt` are not output for `not_approved`.

The missing-reference list must be concrete, for example:

- true back view;
- true top view;
- true bottom / underside view;
- left and right side views;
- 3/4 rear view;
- hinge / pivot closeups;
- wheel group / underside mechanism closeups;
- port / button / control-area closeups;
- open and closed state references;
- folded and expanded state references;
- assembled and disassembled references;
- lid/body, inner/outer, accessory attachment, or module relationship references;
- material/texture closeups for mesh, perforation, fabric, carbon fiber, rubber, metal, plastic, glass, or translucent zones.

End condition: either all requested boards pass as `full_approved`, at least one board passes as `partial_approved`, or no board passes as `not_approved`.
