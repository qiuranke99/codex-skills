---
name: single-face-character-lock-board
description: "Use when the user provides character references and needs exactly one text-free single-face asset board: one bust portrait containing the board's only visible face, one headless front full-body outfit view, and one headless back full-body outfit view. Resolve a single target identity before generation; never fuse different people when multiple references are ambiguous. Freeze and disclose the exact prompt and SHA-256 before the terminal image-generation call. Do not use for ordinary turnarounds, expression sheets, casting contact boards, or prompt-only delivery."
---

# Single-Face Character Lock Board

中文名称：单脸角色资产锁定板

Generate exactly one board with exactly three visual components:

1. one bust portrait containing the only complete visible face;
2. one headless front full-body view from neck to feet;
3. one headless back full-body view from neck to feet.

This deliberately unusual topology separates identity evidence from front/back wardrobe evidence to reduce multi-face drift. Do not convert it into a standard turnaround, expression board, casting sheet, poster, or scene.

## 1. Identity Selection Gate

Require at least one usable character reference and resolve one `target_identity` before generation.

For multiple references:

- Combine identity evidence only when the images clearly show the same person.
- Respect explicit user assignments for face, hair, skin, outfit, shoes, and accessories.
- An outfit reference may show another person, but it contributes wardrobe evidence only; never import that person's face, body identity, age, or skin.
- If references show two or more plausible target people and the user has not selected one, return `selection_pending`. Ask the user to identify the target person or assign one attachment as `identity_source`.
- Do not average, blend, or infer a preferred face from different people.
- If a user explicitly requests a new composite identity, route outside this lock skill rather than disguising synthesis as identity preservation.

Input status must be exactly one of:

- `ready`
- `selection_pending`
- `hard_blocked_no_character_reference`
- `policy_blocked`

Only `ready` permits image generation.

## 2. Source Ledger

Privately map:

- `identity_source`
- `hair_source`
- `skin_source`
- `body_source`
- `outfit_source`
- `shoe_source`
- `accessory_source`

Use `user_locked`, `source_supported`, `safe_inferred`, or `missing_or_conflicting` for each role. User assignments outrank inference. Never claim an inferred back garment, shoe detail, or body feature is verified.

Do not expose the private source ledger unless the user asks for diagnostics. Never copy local paths, hidden reasoning, secrets, or private notes into the generation prompt.

## 3. Fixed Board Topology

Use a horizontal, clean, neutral-gray studio board with realistic photographic texture, soft even light, minimal shadow, and production-reference clarity.

### Bust portrait

- chest-up or upper-body, frontal or near-frontal;
- neutral natural expression;
- clear hairline, facial structure, skin texture, facial hair, marks, and visible identity-critical jewelry;
- exactly one complete visible face and the only face anywhere on the board.

### Headless front full-body

- neck or upper-neck downward to complete feet;
- same target body's proportion and same outfit system;
- clear front garment structure, sleeves, waist, hem, pockets, shoes, and accessories;
- no head, face, partial face, printed face, or reflected face.

### Headless back full-body

- neck or upper-neck downward to complete feet;
- same proportion, outfit, shoes, and accessories as the front view;
- clear back collar, seams, garment structure, pockets, hems, and shoe backs;
- no head, turned head, profile, or partial face.

Inside the image, forbid extra panels, expression tiles, side portraits, heads on body views, mirrors, people, printed faces, text, labels, arrows, numbers, measurements, watermarks, UI, poster styling, fashion editorial, cinematic scenes, illustration, anime, CGI, and decorative typography.

## 4. Freeze The Prompt Before Generation

Call the available built-in image-generation capability directly. Do not ask the user to copy a prompt elsewhere. Do not claim a generator model, seed, exact raster size, or native-resolution provenance unless the runtime exposes it.

Before the image-generation call:

1. Capture `runtime_capability_snapshot`: callable image tool, exposed model choice, exposed size controls, usable reference count, and known output/provenance limits. Leave unknown values `unknown`.
2. Build the complete `final_generation_prompt` with attachment aliases, selected identity, source-role bindings, exact three-panel topology, style, and strict negatives.
3. Normalize the exact prompt as UTF-8 with LF line endings.
4. Compute `generation_prompt_sha256` from those exact bytes.
5. When filesystem access exists, save `<asset_id>_generation_prompt.md` before generation and write the prompt record to `asset_record.yaml`.
6. Present the exact prompt and hash to the user, then set `prompt_disclosed_before_generation: true`. State that the prompt depends on the same reference attachments.
7. Set `terminal_generation_call: pending`, `assistant_qa_status: pending`, and `production_approval_status: not_granted`.
8. Call image generation as the final action of the turn.

Do not send text, call another tool, inspect the output, reconstruct the prompt, or claim visual success after the image-generation call in that turn. The returned image is the terminal result.

If no image tool is callable or the prompt cannot be frozen exactly, return `hard_blocked_generation_runtime`. Do not present prompt-only output as success.

Use this disclosure shape before the terminal call:

```text
Image generation prompt:
<exact final_generation_prompt>

generation_prompt_sha256: <sha256>
prompt_disclosed_before_generation: true
terminal_generation_call: pending
assistant_qa_status: pending
production_approval_status: not_granted
```

## 5. Prompt Content

The frozen prompt must require:

- exactly one horizontal board and exactly three panels;
- exactly one visible face, only in the bust portrait;
- headless front and back body views with complete feet;
- one selected identity, body proportion, outfit, shoes, and accessories across all panels;
- clean gray studio background, soft neutral light, realistic asset-board rendering;
- no additional panels, faces, heads, text, scene, or editorial styling;
- attachment aliases rather than local paths;
- all prompt text outside the generated image.

## 6. Artifacts And Approval States

When filesystem access exists, use:

`outputs/character-locks/<asset_id>/`

Pre-generation artifacts:

- `<asset_id>_generation_prompt.md`
- `asset_record.yaml`

Generation result:

- `<asset_id>_single_face_lock_board.png` or the native image result.

Recommended record fields:

```yaml
asset_id:
asset_type: single_face_character_lock_board
status: generation_pending
runtime_capability_snapshot:
identity_source:
body_source:
outfit_source:
shoe_source:
accessory_source:
final_generation_prompt:
generation_prompt_path:
generation_prompt_sha256:
prompt_disclosed_before_generation: true
terminal_generation_call: pending
assistant_qa_status: pending
production_approval_status: not_granted
```

`terminal_generation_call` stays `pending` until a tool/runtime trace proves `executed` on a later turn. `assistant_qa_status` and `production_approval_status` are separate. Without an independent later visual review, assistant QA remains `pending`; production approval remains `not_granted` until the user or an authorized external pipeline explicitly sets `user_granted` or `external_pipeline_granted`.

## 7. Later-Turn Visual Review And Repair

On a later turn with the generated image available, inspect:

- exactly one complete visible face exists, with no other complete or partial face;
- the bust clearly preserves the selected identity;
- front and back body views are headless and complete to the feet;
- body, outfit, shoes, and accessories remain consistent;
- no text, additional panels, scenic background, or editorial style appears.

If all structural checks pass, set `assistant_qa_status: visual_pass`; otherwise use `visual_warn` or `visual_fail`. Keep `production_approval_status` unchanged.

If one repair is justified, freeze and disclose a new complete prompt and new hash before a new terminal generation call. Never output a failed draft prompt as the prompt for an accepted image.

## 8. Completion Contract

A generation turn succeeds only when one target identity is resolved, the exact prompt and hash are disclosed before generation, and image generation is the terminal action. The generated image remains pending visual review and production approval.

Unselected multiple identities, prompt-only delivery, a missing image call, extra board views, or post-hoc prompt reconstruction is failure.
