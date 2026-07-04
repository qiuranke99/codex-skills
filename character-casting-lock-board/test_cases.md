# Character Casting Lock Board Test Cases

## Acceptance Tests

1. Single reference image: verify the skill still generates the fixed main board, preserves visible identity and outfit, and reports any unavoidable back/side uncertainty briefly.
2. Multiple references with user roles: verify user-assigned face, skin, hair, outfit, shoes, bag, and accessory sources override inferred choices.
3. Multiple references without roles: verify every usable image is internally classified and fused into one character rather than separate people.
4. Fixed main board: verify the generated main board includes large frontal face portrait, front full-body, back full-body, and side full-body views.
5. Multiple target ambiguity: verify two or more different target people without a selected identity returns `selection_pending` before image generation.
6. Multi-candidate request: verify the skill refuses one combined comparison board and requires separate identified target boards.
7. Text-free rule: verify no title, name, role label, view label, number, arrow, scale, table field, film edge code, caption, watermark, UI, or gibberish appears inside any generated board.
8. Traditional casting conflict: verify a request for names, actor data, height, role name, notes, or numbering inside a "traditional casting sheet" keeps those details out of the image.
9. Casting-board style: verify the result reads as textless film casting contact-board documentation rather than fashion editorial, poster, lookbook, cinematic still, concept art, or illustration.
10. Full-body coverage: verify front, back, and side full-body views show complete head-to-foot character without cropping shoes, bag, head, or key clothing.
11. Identity consistency: verify face logic, skin tone, hairstyle, body proportion, outfit, shoes, bag, and accessories remain stable across all views and extension boards.
12. Back/side lock: verify back view locks back hair and back outfit; side view locks side face contour, hair side contour, outfit side silhouette, shoe side shape, and bag side relation.
13. Single-image source status: verify side/back/shoe/bag details are reported as `safe_inferred` when they are not actually visible, never as verified.
14. User-assigned conflict: verify conflicting references follow user assignment or hard-block if the conflict cannot be resolved.
15. Upper-body risk: if neckline, shoulder, sleeve, lapel, jewelry, or hair-to-collar transition is high risk, verify an Upper-Body Detail Board is generated.
16. Hair risk: if hair back, tail, bun, braid, curls, volume, or supplied hair reference is important, verify a Hairstyle Detail Board is generated.
17. Accessory/shoe/bag risk: if shoes, bag, hat, eyewear, jewelry, gloves, belt, or handheld object matter, verify an Accessory / Shoe / Bag Detail Board is generated.
18. Image generation prompt: verify every successful one-board generation outputs `Image generation prompt:` followed by the exact final prompt used for the accepted `/image gen` result.
19. Multi-board prompt output: verify a generated expansion package outputs `Image generation prompts:` with one clearly named prompt for each delivered board.
20. Prompt count accounting: verify the number of visible prompts equals the number of delivered boards, not the number of failed or rejected attempts.
21. Prompt safety: verify the visible image generation prompt contains no hidden reasoning, local absolute paths, secrets, private source maps, unsupported identity claims, or diagnostic metadata fields.
22. Prompt outside image: verify prompt text appears only in chat or a sidecar artifact, never inside the generated board image.
23. Prompt-only false success: verify a run that only outputs prompt text without calling `/image gen` is not approved unless the user explicitly requested a separate text-only handoff outside this skill.
24. Prompt unavailable: verify the skill reports `hard_blocked_generation_prompt_unavailable` if the final image generation prompt cannot be constructed before image generation.
25. prompt mismatch: verify a board whose exact final submitted prompt is unknown or mismatched after generation is marked `generated_board_failed_qa` rather than being delivered with an approximate prompt; when feasible, verify `generation_prompt_sha256` can be recorded internally without becoming the default user-facing output.
26. Hard blocker: verify ordinary hard blockers include no usable character reference, ambiguous target among multiple people, required in-image text, unavailable image generation, or safety-policy boundary.
27. Repair behavior: verify a failed generated board triggers targeted correction or a required extension board rather than prompt-only advice, and only the final corrective prompt that produced the accepted board is output.

## Quick Validation Checklist

- Skill file exists at `.agents/skills/character-casting-lock-board/SKILL.md`.
- `SKILL.md` frontmatter `name` matches the directory name.
- `SKILL.md` contains `Character Casting Lock Board` and `角色选角锁定板`.
- `SKILL.md` contains `Input` and `Output` structure terms.
- `SKILL.md` explicitly requires direct `/image gen`.
- `SKILL.md` explicitly requires `Image generation prompt:` for one delivered board or `Image generation prompts:` for multiple delivered boards.
- `SKILL.md` requires the number of visible prompts to equal the number of delivered boards.
- `SKILL.md` explicitly treats prompt output as a companion deliverable, not a prompt-only substitute deliverable.
- `SKILL.md` treats prompt-only-without-image requests as out of scope for this production skill.
- `SKILL.md` contains `selection_pending` for unresolved selected identity.
- `SKILL.md` fixes the main board to four core views.
- `SKILL.md` hard-blocks ambiguous multi-candidate fusion.
- `SKILL.md` resolves the traditional casting sheet vs no-text conflict in favor of no in-image text.
- `SKILL.md` requires automatic extension boards when risk justifies them.
- `SKILL.md` forbids in-image text pollution and poster/fashion/concept styling.
