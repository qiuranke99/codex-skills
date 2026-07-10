# Character Casting Lock Board Test Cases

## Acceptance Scenarios

1. **Single reference**: plan the fixed main board; mark invisible back/side/shoe/bag evidence `safe_inferred`, never verified.
2. **Same person, multiple views**: combine identity evidence and preserve one target across portrait/front/back/side views.
3. **Different people, no selection**: return `selection_pending`; make no image call and do not blend faces.
4. **Explicit role assignments**: keep one selected identity while using other-person images only for assigned wardrobe or accessory evidence.
5. **Multiple candidates requested in one board**: route outside the Skill; do not create a comparison contact sheet.
6. **Fixed topology**: require one large frontal portrait and complete front, back, and side full-body views.
7. **Text-free conflict**: reject names, role labels, numbers, measurements, notes, arrows, or film-edge codes inside the image.
8. **Upper-body extension**: plan B only when a named continuity risk is material, cannot be read on A, and has source evidence or allowed inference.
9. **Hair extension**: plan C only for source-backed hair continuity risk that the main board cannot show legibly.
10. **Accessory extension**: plan D only for a source-backed shoe, bag, handheld, or accessory risk that the main board cannot show legibly.
11. **No decorative expansion**: never add expressions, silhouettes, generic poses, product ads, or scene panels.
12. **Runtime capability**: record `runtime_capability_snapshot`; do not claim model, seed, raster, or native 4K provenance unless exposed.
13. **Prompt trace**: freeze `final_generation_prompt`, compute `generation_prompt_sha256`, and set `prompt_disclosed_before_generation: true` before the image call.
14. **Terminal call**: set `terminal_generation_call: pending` before generation; only the later tool/runtime trace may prove `executed`; emit no text and call no tool after image generation in that turn.
15. **Multi-board package**: advance at most one generation call per turn; review or repair A before generating B, C, or D.
16. **Status separation**: before generation, keep `assistant_qa_status: pending_post_generation_inspection` and `production_approval_status: not_granted`; only explicit user or external-pipeline authorization may grant production approval.
17. **Later visual review**: only a later independent inspection may set assistant QA to `passed`, `conditional`, or `failed`.
18. **Repair**: freeze and disclose a new exact prompt and hash before a corrective terminal call; never attach a rejected prompt hash to a repaired image.
19. **Prompt-only false success**: a prompt without the image call does not complete the Skill.
20. **Unavailable runtime**: return `hard_blocked_generation_runtime`; do not claim an image or approval.
21. **Only 16:9**: every main or extension board requests `target_aspect_ratio: "16:9"` with `alternate_aspect_ratios_allowed: false`; no alternate ratio or silent fallback is offered.
22. **Non-16:9 Codex return**: retain a source-faithful result only as `codex_board_role: intermediate_layout_reference`; never call it the final 16:9 asset.
23. **Draft is not final**: before a board exists, keep `4k_enhancement_prompt_status: draft_pre_generation`; do not emit `final_4k_enhancement_prompt` or its hash.
24. **Per-board 4K traceability**: every generated A, B, C, or D board receives its own inspected-board-specific `final_4k_enhancement_prompt`, SHA-256, and handoff sidecar; omitted boards receive none.
25. **Complete reference bundle**: require the inspected Codex board plus all original identity and board-relevant references; a board-only enhancement is blocked for source fidelity.
26. **External runtime controls**: request exactly `aspect_ratio: "16:9"` and `image_size: "4K"`; when either control is unavailable, use `blocked_runtime_controls` and select no fallback.
27. **Returned-file evidence**: record provider, model, surface, model profile, requested settings, observed pixels, provider aspect-ratio profile, observed file aspect ratio, aspect-ratio evidence, and 4K evidence before `verified`.
28. **Identity-safe microtexture**: recover only source-supported facial, skin, and hair detail; reject beauty retouching, face reshaping, age drift, or invented pores and marks.
29. **Topology preservation**: 4K enhancement preserves A's portrait/front/back/side topology and each extension's approved evidence job without adding panels, faces, people, or styling systems.
30. **External status separation**: `handoff_ready`, `pending_external_generation`, `returned_unverified`, `verified`, and `rejected` remain distinct from assistant QA and production approval.
31. **Count invariant**: `generated_board_count == finalized_4k_prompt_count == 4k_prompt_hash_count == 4k_handoff_sidecar_count`.

## Quick Validation Checklist

- Folder and frontmatter name match `character-casting-lock-board`.
- Description states the fixed casting-board topology and identity selection gate.
- Main board remains text-free portrait/front/back/side casting documentation.
- Extension boards require a named evidence-closing risk.
- The seven shared runtime fields are present.
- Prompt disclosure precedes the terminal image-generation call.
- No post-generation prompt or QA response is required in the same turn.
- `assistant_qa_status` and `production_approval_status` are independent.
- `target_aspect_ratio: "16:9"` and `alternate_aspect_ratios_allowed: false` are present.
- `final_4k_enhancement_prompt`, `4k_enhancement_prompt_sha256`, and `finalized_post_inspection` are present.
- The external bundle requires `codex_asset_board` and `original_source_references`.
- External runtime fields request `aspect_ratio: "16:9"` and `image_size: "4K"`.
- Per-board 4K prompt/hash/sidecar count equals the generated board count.
