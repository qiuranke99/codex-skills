---
name: complex-structure-product-asset-lock-board
description: "Use when the user provides product reference images for complex structures, complex mechanical or electronic devices, multi-part objects, articulated/folding/open-close products, products with multiple states, interfaces, controls, connectors, support nodes, hidden top/bottom/back details, or high-risk structural nodes, and needs a video-ready Complex Structure Product Asset Lock package. First run a full source sufficiency gate; if any required view, state, interface, mechanism, decomposition relationship, or high-risk detail is missing or unverifiable, do not call /image gen and return not_approved with the required reference-image list. Call /image gen only for full_approved packages, then output the final image-generation prompt used for each delivered QA-passing board as chat text, not trace, hidden reasoning, or a single package-level prompt."
---

# Complex Structure Product Asset Lock Board

Chinese name: 复杂结构产品资产锁定板

Create a complex-structure product asset package for downstream image and video generation. The leading rule is **source-supported structural lock**: generate asset-board images only when the references are sufficient to lock the whole required structure without guessing.

This skill has only two final outcomes:

- `full_approved`: all required source evidence exists, image generation is allowed, and every required board can be generated and QA-checked.
- `not_approved`: either the source gate fails before image generation, or generated boards fail QA after an approved source gate. In both cases, no generated image is delivered, registered, reused, or treated as a video-ready asset board. If the source gate fails, no `/image gen` call is allowed and the user receives a concrete missing-reference list.

There is no intermediate asset package in this skill.

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

Completion criterion: accept the task only when complex structural stability is the core success factor.

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

Completion criterion: every reference image has a role, and every required structure is either verified by source evidence or placed on the missing-reference list before generation is considered.

## Full Source Sufficiency Gate

Run this gate before `/image gen`. If any required item fails, stop and output `not_approved`. Do not generate any asset-board image.

Required evidence for `full_approved`:

- the 8 structural overview views: front, back, left side, right side, 3/4 front, 3/4 rear, top, bottom / underside;
- enough closeup evidence for every high-risk node identified in the risk audit;
- every state endpoint that exists in the product or is expected in downstream video;
- every interface, port, control, connector, operation area, and user-contact zone expected to appear;
- every visible layer, accessory, lid/body, inner/outer, module, assembly, or decomposition relationship expected to appear;
- material and texture evidence for high-risk material zones;
- enough resolution and clarity to verify shape, position, orientation, hierarchy, and left/right/front/back/top/bottom relationships.

Create an internal **Structural Coverage Matrix** before generation. Track:

- `view_id`: front, back, left, right, 3/4 front, 3/4 rear, top, bottom / underside;
- `state_id`: every stable state endpoint and every state expected from product function or supplied references unless the brief explicitly excludes it;
- `node_id`: every high-risk structural node from the Critical Node Registry;
- `interface_id`: every port, control, button, connector, contact surface, and operation zone;
- `material_zone`: every high-risk material or finish region;
- `hidden_no_fill_zone`: every hidden, blocked, internal, underside, back, cavity, or uncertain region that must not be invented;
- `required_source`, `status`, and `failure_reason`.

For each required item, classify evidence only as:

- `verified`: supplied directly or cross-verified by multiple references with no structural contradiction.
- `missing`: absent, hidden, cropped, too blurry, too low-resolution, contradictory, or only guessable.

Rules:

- The 8 structural overview views require direct visible source evidence. Cross-verification may support only continuous, non-hidden, non-occluded surfaces; it may not replace true top, bottom / underside, back, hidden, or mechanism evidence.
- `missing` anywhere in a required view, board, state, interface, mechanism, high-risk node, or decomposition relationship forces `not_approved`.
- Do not infer, approximate, mirror, beautify, or synthesize missing structure to satisfy the gate.
- Do not call `/image gen` until every required item is `verified`.
- Do not create a reduced board set when evidence is incomplete.
- Do not let user pressure, downstream urgency, shot avoidance, text descriptions, generated guesses, or prompt constraints override missing source evidence.

Completion criterion: the workflow has a binary gate decision: `full_approved` may proceed to image generation; `not_approved` stops image generation and lists required references.

## Risk Audit

Identify the nodes that video models are most likely to damage. Prioritize:

- hinges, pivots, shafts, joints, connecting arms, rails, sliding parts, telescoping parts, folding nodes;
- support parts, cross-braces, wheel groups, underside mechanisms, load-bearing points;
- seams, split lines, latches, edges, socket/plug interfaces, ports, buttons, dials, levers, control surfaces;
- component boundaries, part nesting, caps, lids, inner/outer shell relationships, accessory attachment points;
- mesh, perforation, fabric, carbon fiber, rubber, metal, plastic, transparent/translucent material transitions;
- any asymmetric, easily simplified, easily merged, easily omitted, or easily mirror-flipped area.

Build a **Critical Node Registry**. Every node must include:

- `node_id`;
- owning component and connected component;
- front/back/left/right/top/bottom position;
- left-side, right-side, centered, or asymmetric status;
- symmetric counterpart, if any;
- source image evidence;
- required closeup board cell;
- mechanism role, if it moves, supports load, folds, locks, slides, hinges, or connects parts.

Every high-risk node must be `verified` before image generation. If any high-risk node is `missing`, the result is `not_approved`.

Completion criterion: all high-risk nodes are verified, or the missing-reference list names the exact node and required reference image.

## Motion And Hidden-Structure Logic

For every moving, folding, opening, sliding, rotating, detachable, telescoping, latching, locking, or load-bearing mechanism, lock:

- endpoint A and endpoint B;
- pivot axis, slide direction, rotation direction, travel path, or separation path;
- stop point, latch point, lock point, contact point, clearance, and collision boundary;
- user operation surface and force/contact area;
- which components move together and which stay fixed.

If any required motion logic is missing, output `not_approved` before image generation.

Create a **Hidden Structure / No-Fill Map**:

- mark hidden, internal, underside, back, occluded, cavity, blocked, or uncertain regions that must not be invented;
- if a hidden region will appear in downstream video and no source evidence exists, classify it as `missing`;
- if a hidden region will not appear, keep it invisible or neutral instead of exposing fabricated internals;
- never use a decomposition board to reveal an unsupported internal mechanism.

Completion criterion: every motion mechanism and every no-fill zone is represented in the Structural Coverage Matrix before generation.

## Required Boards

If and only if the Full Source Sufficiency Gate passes, generate separate boards. Do not compress all information into one busy image.

Fixed boards, never omit after approval:

1. **Structure Overview Board**: lock overall spatial structure and proportions.
2. **Critical Structure Closeup Board**: lock the most drift-prone local nodes.

Automatically required boards:

3. **State Variation Board**: required when the product has meaningful stable states.
4. **Interface / Operation Board**: required when ports, controls, buttons, contact zones, or operation logic matter.
5. **Structural Decomposition Relationship Board**: required when layered, modular, inner/outer, accessory, assembly, lid/body, or part hierarchy relationships matter.
6. **Material / Finish Lock Board**: required when high-risk material or finish zones matter.

If any required board lacks source evidence, stop before generation and return `not_approved`.

Before image generation, create a `required_board_manifest` with every required `board_id`, `board_name`, activation reason, and source-evidence basis. This manifest is internal until `full_approved`, but it controls generation, QA, and prompt count.

Completion criterion: every required board can be generated from verified evidence before `/image gen` is called, and the `required_board_manifest` contains exactly the boards that must be delivered.

## Board Specifications

All generated boards must use:

- separate generated image per board;
- horizontal 16:9, 4K ultra-clear;
- clean white, near-white, or light gray neutral background;
- clear even studio light or neutral lock-board light;
- subtle natural shadows only;
- no scene, props, hands, people, poster styling, dramatic lighting, cinematic stage lighting, ornate layout, decorative text, large titles, arrows, callouts, legends, status text, or explanatory overlays unless the user explicitly requests them;
- product-native text only when it truly exists on the product surface.

### A. Structure Overview Board

Generate one board with exactly these 8 complete verified views:

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
- treat top and bottom views as mandatory structural evidence;
- never mirror a real asymmetric design into a symmetrical one;
- never lock only the outline while letting internal structure drift.

### B. Critical Structure Closeup Board

Generate at least 6 closeups. This is a floor, not a cap. The actual count is determined by the Critical Node Registry; do not merge, omit, or down-rank real high-risk nodes to fit a fixed count.

Choose closeups from the risk audit, not from prettiness:

- connection nodes;
- hinges, pivots, joints, shafts, sliding or folding nodes;
- support structures, load-bearing points, cross-braces, wheel or underside mechanisms;
- component boundaries, seams, latches, edge transitions, assembly points;
- ports, buttons, levers, dials, grips, controls, user-contact surfaces;
- material-risk regions such as mesh, perforation, fabric, carbon fiber, rubber, metal, plastic, glass, or mixed-material seams.

Each closeup must retain enough surrounding context to reveal where the detail belongs.

### C. State Variation Board

Generate this board only when every required state endpoint is verified.

Cover at least 2 states, and 3-4 states when needed:

- expanded / stored;
- open / closed;
- working / off;
- extended / retracted;
- assembled / disassembled;
- use state / static state.

Each state endpoint must keep the same view logic needed to understand its front/back/left/right/top/bottom relationships. For mechanisms that change shape, include enough verified views to preserve the motion axis, support relation, exposed hidden regions, and attachment logic across states.

### D. Interface / Operation Board

Generate this board only when every required interface and operation area is verified.

Cover buttons, switches, levers, knobs, dials, sliders, screens, grips, handles, contact surfaces, ports, sockets, plugs, charging points, detachable connectors, and cable entry points.

### E. Structural Decomposition Relationship Board

Generate this board only when every required layer, module, accessory, lid/body, inner/outer, or assembly relationship is verified.

Use mild separation or gentle decomposition. Do not default to a technical exploded diagram. Do not reveal or fabricate hidden internal mechanisms without source evidence.

### F. Material / Finish Lock Board

Generate this board only when every high-risk material or finish zone is verified.

Require this board for mixed materials, transparent or translucent parts, mesh, perforation, fabric, carbon fiber, rubber, metal highlight zones, matte plastic, glossy plastic, glass, coating transitions, or texture-scale-sensitive surfaces.

Lock material boundaries, texture direction, reflection strength, translucency, perforation scale, weave or grain scale, edge transitions, and component ownership.

## Image Generation

Call Codex built-in `/image gen` only after `full_approved`.

Build a separate `final_image_generation_prompt` for each planned board from:

- all uploaded product references as the only product identity source;
- the verified structural lock map;
- the risk audit;
- board-specific requirements;
- global negative constraints.

Do not show, draft, or provide image-generation prompts before the source gate reaches `full_approved`. If the user asks for prompts while source evidence is missing, output the `not_approved` missing-reference report instead.

After `full_approved`, submit each `final_image_generation_prompt` to `/image gen` for its board. This prompt is the public image-generation prompt used for that delivered board, not trace, not hidden reasoning, not a source-audit log, and not a prompt-only substitute deliverable.

After generation and QA, output the exact final prompt for each delivered QA-passing board in the user-facing reply under `本次图片生成提示词`. If a board is repaired or regenerated, output only the final prompt corresponding to the accepted board. If the exact final submitted prompt for a delivered board is unavailable or cannot be matched to the accepted board, the package fails QA with `prompt mismatch`.

Do not output a single master prompt, package-level prompt, complete-package prompt, shared prompt, summary prompt, overview prompt, board-set prompt, generic reusable prompt, or any other single prompt as a substitute for board-level prompts. Each `final_image_generation_prompt` must correspond to exactly one planned and delivered board. A prompt that covers multiple boards, uses `board_id` values such as `package`, `all_boards`, or `complete_package`, or cannot be matched one-to-one to a delivered QA-passing board fails QA with `prompt_scope_mismatch`.

Prompts must be board-distinct. Two prompt entries must not be identical or differ only by `board_id`, `board_name`, ordering, numbering, or generic wording. Each prompt must include the board type and board-specific requirements for its own generated board.

After each board passes QA, bind its prompt entry to the accepted generated result with `accepted_result_ref`. If an accepted board has no matchable result reference, the package fails QA with `prompt mismatch`.

`generation_prompt_sha256`, trace notes, audit logs, or summaries may be internal or optional evidence only; they never satisfy `final_image_generation_prompt` and never replace the public final prompt text.

Never place prompts, prompt labels, prompt metadata, or prompt text inside generated images.

Global negative constraints for every board:

- no redesign, beautification, modernization, premiumization, simplification, restyling, rebranding, relabeling, recoloring, or invented features;
- no dropped parts, merged parts, wrong left/right, wrong front/back, wrong top/bottom, false symmetry, fake hidden structure, or unsupported underside/back/top invention;
- no single overloaded collage pretending to complete the whole asset package;
- no poster, advertisement, lifestyle scene, mood image, infographic, engineering blueprint, manual page, title-heavy layout, or non-product text pollution.

Completion criterion: `/image gen` is called only for `full_approved`; no image generation happens for `not_approved`.

## QA Gate

After each generated board, inspect it against the verified structural lock map before treating it as an asset-board image.

Check:

- same product identity across all boards;
- same silhouette, proportions, main components, connections, material direction, state logic, and asymmetry;
- full 8-view coverage for the Structure Overview Board, including top and bottom / underside;
- every `view_id` in the Structural Coverage Matrix passes;
- every `node_id` in the Critical Node Registry appears in the correct board cell and keeps enough context;
- every `state_id` preserves identity, motion logic, and verified stable endpoints;
- every `interface_id` preserves verified controls, ports, contact zones, and boundaries;
- every `material_zone` preserves verified boundaries, texture direction, reflection, translucency, and scale;
- every `hidden_no_fill_zone` remains hidden, neutral, or explicitly blocked rather than fabricated;
- decomposition boards preserve verified part ownership and assembly hierarchy;
- every delivered board has one matching `final_image_generation_prompt` in `本次图片生成提示词`;
- the number of entries in `final_image_generation_prompts` equals the number of entries in `本次图片生成提示词`, the number of delivered QA-passing boards, and the number of boards in `required_board_manifest`;
- every prompt entry includes `accepted_result_ref` for the accepted generated board;
- no package-level, all-board, master, shared, summary, overview, board-set, generic reusable, or multi-board prompt is accepted; prompt-to-board matching must be strictly one-to-one;
- prompts are board-distinct; no two final prompts are identical or differ only by `board_id`, `board_name`, ordering, numbering, or generic wording;
- every final prompt includes board-specific requirements and never only says to generate the full complex structure asset package;
- every visible prompt corresponds to the final accepted `/image gen` result, not a rejected attempt or after-the-fact reconstruction;
- `generation_prompt_sha256`, trace notes, audit logs, or summaries are not accepted as substitutes for `final_image_generation_prompt`;
- prompts include the board type, verified source identity, verified structural constraints, relevant matrix or registry items, 16:9 4K neutral board requirements, and no-text-pollution constraints;
- prompts do not include hidden reasoning, source-audit trace, unsupported inferred structure, or instructions to add labels, arrows, titles, legends, callouts, or non-product text;
- no prompt text appears inside the generated image;
- no invented part, missing real part, false symmetry, left/right swap, hidden-structure hallucination, decorative text pollution, poster style, or simple-product-board downgrade.

If generated output fails these checks while source evidence remains sufficient, repair or regenerate the failed board in the current run. Do not include failed attempts in the asset package.

If the current run still cannot produce a QA-passing full package after available repair attempts, the final result is `not_approved` with reason `generated_board_failed_qa`. The rejected generated images are not asset-board deliverables, must not be registered or reused, and do not create a limited package. Do not hide failure behind a softer status.

## Not Approved Output

When the source gate fails, do not call `/image gen`. Output only a concise Chinese not-approved report:

- `source_gate_status`: `not_approved`;
- `approval_status`: `not_approved`;
- `not_approved_reason`: `source_insufficient`;
- `image_generation_decision`: `refuse_generation`;
- `video_handoff_status`: `blocked_do_not_use`;
- `generated_assets_delivered`: `none`;
- `asset_registry_status`: `do_not_register_or_reuse`;
- `prompt_reuse_status`: `no_reusable_prompt_allowed`;
- `prompt_output_status`: `no_prompt_output_for_not_approved`;
- reason;
- provided references summary;
- missing required reference images;
- affected required boards;
- affected high-risk nodes, states, interfaces, or decomposition relationships;
- minimum new reference set needed to rerun;
- asset registry instruction: do not register, reuse, or treat this as a video-ready asset lock package;
- statement that no asset-board images, reusable image/video prompts, partial video-safe ranges, asset IDs, or downstream-use instructions were produced because doing so would require guessing complex structure.
- statement that no image-generation prompts are output because no QA-passing deliverable exists.
- statement that `final_image_generation_prompts` and `final_image_generation_prompt` are not output for `not_approved`.
- statement that the minimum new reference set is only a product-reference capture list, such as missing angles, states, interfaces, mechanisms, nodes, or material closeups; it must not include composition, style, rendering, prompt, model-generation, or downstream-video language.

When generated boards fail QA after a `full_approved` source gate and cannot be repaired in the current run, output a concise Chinese rejection report:

- `source_gate_status`: `full_approved`;
- `approval_status`: `not_approved`;
- `not_approved_reason`: `generated_board_failed_qa`;
- `image_generation_decision`: `call_image_gen`;
- `video_handoff_status`: `blocked_do_not_use`;
- `generated_assets_delivered`: `none`;
- `asset_registry_status`: `do_not_register_or_reuse`;
- `prompt_reuse_status`: `no_reusable_prompt_allowed`;
- `prompt_output_status`: `no_prompt_output_for_not_approved`;
- failed boards;
- failed structural checks;
- repair attempts made;
- minimum fix needed to rerun or regenerate;
- asset registry instruction: do not register, reuse, or treat rejected generated images as a video-ready asset lock package.
- statement that no image-generation prompts are output because rejected generated boards are not deliverables.
- statement that `final_image_generation_prompts` and `final_image_generation_prompt` are not output for `not_approved`.
- statement that `repair attempts made` and `minimum fix needed` may describe only structural failure points, QA failures, or additional product references needed; they must not include failed prompts, candidate prompts, repaired prompts, prompt deltas, style prompts, shot prompts, or downstream-use prompts.

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

## Output Contract

If `full_approved`, include generated images or image results, then report only:

- `source_gate_status`: `full_approved`;
- `approval_status`: `full_approved`;
- `image_generation_decision`: `call_image_gen`;
- `video_handoff_status`: `full_approved_video_ready`;
- `generated_assets_delivered`: `complete_package`;
- `asset_registry_status`: `register_video_ready_asset_package`;
- `prompt_reuse_status`: `reusable_only_with_this_QA_passing_package`;
- `prompt_output_status`: `delivered_as_chat_text_not_trace`;
- `required_board_manifest`: list the delivered QA-passing `board_id` / `board_name` values used for count matching;
- `final_image_generation_prompts`: same entries as `本次图片生成提示词`;
- asset registry instruction: register or reuse only this QA-passing package as the video-ready complex-structure asset lock package;
- generated boards;
- fixed boards;
- automatically required boards;
- `本次图片生成提示词`: for each delivered board, output `board_id`, `board_name`, `accepted_result_ref`, `prompt_role: public_final_image_generation_prompt`, `prompt_scope: accepted_QA_passing_board_only`, and `final_image_generation_prompt`;
- prompt count rule: `final_image_generation_prompts` must be a per-board list only, never a package-level prompt block; the number of `本次图片生成提示词` entries must equal the number of delivered QA-passing boards and the number of boards in `required_board_manifest`, and each entry must map to exactly one delivered board and one accepted result;
- verified key contents;
- QA result.

If `not_approved`, do not include generated images, reusable image/video prompts, style prompts, shot prompts, partial video-safe ranges, asset IDs, asset registry entries, or any downstream-use instruction except `blocked_do_not_use` and the missing-reference or rejected-board report. If the reason is `source_insufficient`, provide the required-reference list. If the reason is `generated_board_failed_qa`, provide the rejected-board QA report and no reusable image assets.

End condition: either a fully source-supported generated asset package passes QA as `full_approved`, the run stops before image generation as `not_approved` with exact additional product reference images required, or rejected generated boards are reported as `not_approved` with no deliverable assets and no video handoff.
