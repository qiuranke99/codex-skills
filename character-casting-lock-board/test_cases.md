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
16. **Status separation**: before generation, keep `assistant_qa_status: pending` and `production_approval_status: not_granted`; only explicit user or external-pipeline authorization may grant production approval.
17. **Later visual review**: only a later independent inspection may set assistant QA to `visual_pass`, `visual_warn`, or `visual_fail`.
18. **Repair**: freeze and disclose a new exact prompt and hash before a corrective terminal call; never attach a rejected prompt hash to a repaired image.
19. **Prompt-only false success**: a prompt without the image call does not complete the Skill.
20. **Unavailable runtime**: return `hard_blocked_generation_runtime`; do not claim an image or approval.

## Quick Validation Checklist

- Folder and frontmatter name match `character-casting-lock-board`.
- Description states the fixed casting-board topology and identity selection gate.
- Main board remains text-free portrait/front/back/side casting documentation.
- Extension boards require a named evidence-closing risk.
- The seven shared runtime fields are present.
- Prompt disclosure precedes the terminal image-generation call.
- No post-generation prompt or QA response is required in the same turn.
- `assistant_qa_status` and `production_approval_status` are independent.
