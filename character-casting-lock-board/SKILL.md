---
name: character-casting-lock-board
description: "Use when the user provides character references and needs a text-free film casting contact-board asset for one selected character: one large frontal portrait plus complete front, back, and side full-body views, with narrowly justified hair, upper-body, shoe, bag, or accessory extension boards when source-backed continuity risk requires them. Resolve identity ambiguity before generation. Freeze and disclose each exact prompt and SHA-256 before its terminal image-generation call. Do not use for candidate comparison, general character sheets, poster or lookbook layouts, or prompt-only delivery."
---

# Character Casting Lock Board

中文名称：角色选角锁定板

Create a text-free production asset that borrows the observational discipline of a film casting contact sheet without inheriting names, numbers, measurements, notes, labels, or film-edge text. Keep this Skill narrow: it locks one selected character through a fixed portrait/front/back/side topology. It is not a universal character-board workflow.

## 1. Route The Request

Use this Skill only for one selected character and casting-contact-board visual logic.

Route elsewhere when the user needs:

- exactly one visible face with headless front/back views: use `single-face-character-lock-board`;
- the comprehensive expression/detail/silhouette board: use `character-final-lock-board`;
- multiple candidates in one comparison board, a casting spreadsheet, prompt-only handoff, fashion lookbook, poster, scene, or labeled design sheet.

Require at least one usable character reference. If the set contains multiple possible identities, accept only when the user has selected one target. Never average or fuse different people into an idealized actor.

Input status must be exactly one of:

- `ready`
- `selection_pending`
- `hard_blocked_no_character_reference`
- `policy_blocked`

Only `ready` permits generation.

## 2. Audit Sources

Privately map supplied attachments to:

- `identity_source`
- `skin_source`
- `hair_source`
- `body_source`
- `outfit_source`
- `shoe_source`
- `bag_or_handheld_source`
- `accessory_source`
- `front_view_source`
- `back_view_source`
- `side_view_source`

Mark each role as:

- `user_locked`
- `source_supported`
- `safe_inferred`
- `missing_or_conflicting`

User-assigned roles are binding unless policy prevents them. Another person may provide explicitly assigned wardrobe evidence, but never identity evidence. Do not call an inferred back, side, shoe, bag, or accessory detail verified.

If the user requires exact continuity for evidence that is absent and forbids inference, hard-block that requirement rather than inventing it.

## 3. Fix The Main Board

Always plan **A. Character Casting Lock Board** with exactly these core views:

1. one large frontal shoulder-up or chest-up portrait;
2. one complete front full-body view;
3. one complete back full-body view;
4. one complete side full-body view.

All views must preserve one identity, facial logic, skin, hairstyle, body proportion, outfit, shoes, bag, accessories, and height impression. Keep full-body views head-to-toe, neutrally posed, and unobstructed.

Use a horizontal 16:9 composition, white-to-neutral-gray background, even neutral light, realistic photographic rendering, minimal shadow, and casting-documentation clarity. Treat “4K” as an output preference only; claim exact raster size or native provenance only when the runtime exposes it.

Inside the image, forbid names, role labels, text, numbers, measurements, arrows, captions, tables, film edge codes, watermarks, UI, gibberish, extra people, comparison faces, posters, fashion-editorial treatment, cinematic scenes, beauty ads, illustration, anime, CGI, or concept art.

## 4. Add Only Evidence-Closing Extensions

Do not add detail boards for decorative completeness. Add an extension only when all three conditions hold:

1. the detail is materially important to downstream continuity;
2. the main board cannot show it at a usable scale;
3. supplied evidence supports it, or the user explicitly permits clearly labeled inference.

Allowed extensions:

- **B. Upper-Body Detail Board**: collar, neckline, shoulders, sleeves, jewelry, lapel, garment construction, hair-to-clothing transition.
- **C. Hairstyle Detail Board**: front hairline, side contour, back hair, nape, bun, braid, curls, parting, or crown information.
- **D. Accessory / Shoe / Bag Detail Board**: shoe structure, bag shape and wearing method, eyewear, hat, jewelry, belt, glove, or handheld continuity.

Every extension must close one named risk. It must remain text-free, neutral, source-faithful, and subordinate to the main board. Never expand into expressions, silhouettes, generic pose libraries, product ads, or scene assets.

Record the planned `board_set` before generation. Generate the main board first. A failed main board must be repaired or rejected before any extension is generated.

## 5. Freeze Each Prompt Before Its Terminal Call

Use the available built-in image-generation capability directly. Do not claim a model, seed, exact size, or native 4K provenance unless exposed by the runtime.

For each board, before its image-generation call:

1. Capture `runtime_capability_snapshot`: callable image tool, exposed model choice, exposed size controls, usable reference count, and known output/provenance limits. Leave unknown values `unknown`.
2. Build the complete `final_generation_prompt` with selected identity, attachment aliases, board type, source bindings, views, continuity requirements, style, and strict negatives.
3. Normalize the exact prompt as UTF-8 with LF line endings.
4. Compute `generation_prompt_sha256` from those exact bytes.
5. When filesystem access exists, save `<asset_id>_<board_id>_generation_prompt.md` and update the prompt record in `asset_record.yaml` before generation.
6. Present the exact prompt, board ID, and hash to the user, then set `prompt_disclosed_before_generation: true`. State that the prompt depends on the same attached references.
7. Set `terminal_generation_call: pending`, `assistant_qa_status: pending`, and `production_approval_status: not_granted`.
8. Call image generation as the final action of the turn.

Do not send text, call another tool, inspect the result, reconstruct a prompt, or claim visual success after generation in that turn. The returned image is the terminal result.

Because each generation call is terminal, a multi-board package advances one board per turn. On a later continuation, inspect the preceding board first; repair it if necessary, otherwise freeze the next extension prompt and generate it as that turn's final action. Do not claim the package complete until every planned board has later-turn visual QA.

If the exact prompt cannot be frozen or image generation is unavailable, return `hard_blocked_generation_runtime`. Prompt-only delivery is not success.

Use this pre-generation disclosure shape:

```text
Board: A. Character Casting Lock Board

Image generation prompt:
<exact final_generation_prompt>

generation_prompt_sha256: <sha256>
prompt_disclosed_before_generation: true
terminal_generation_call: pending
assistant_qa_status: pending
production_approval_status: not_granted
```

Use attachment aliases such as `selected_identity_reference`, `outfit_reference_1`, and `shoe_reference_1`, never local paths. Exclude private source maps, hidden reasoning, secrets, and unsupported identity claims. Keep all prompt text outside the image.

## 6. Artifacts And State

When filesystem access exists, use:

`outputs/character-locks/<asset_id>/`

Maintain:

- one prompt sidecar per generated board;
- `asset_record.yaml` with the planned board set and per-board hash;
- generated image results;
- an optional later-turn `qa_report.md`.

Recommended state shape:

```yaml
asset_id:
asset_type: character_casting_lock_board
selected_identity:
runtime_capability_snapshot:
board_set:
  A: required
  B: omitted | planned | generated
  C: omitted | planned | generated
  D: omitted | planned | generated
boards:
  A:
    final_generation_prompt:
    generation_prompt_path:
    generation_prompt_sha256:
    prompt_disclosed_before_generation: true
    terminal_generation_call: pending
    assistant_qa_status: pending
production_approval_status: not_granted
```

`terminal_generation_call` stays `pending` until the tool/runtime trace proves `executed` on a later turn. `assistant_qa_status` and `production_approval_status` are separate. Without independent later visual review, assistant QA remains `pending`; production approval remains `not_granted` until the user or an authorized external pipeline explicitly sets `user_granted` or `external_pipeline_granted`.

## 7. Later-Turn Visual QA

Inspect each returned board only on a later turn. For the main board, verify:

- the required portrait, front, back, and side views exist;
- body views are complete to head and feet;
- identity, hair, body, outfit, shoes, bag, and accessories remain consistent;
- back and side views genuinely show their intended evidence;
- no text pollution, extra people, scene, poster, editorial, or concept-art drift appears.

For an extension, verify that it closes its named risk and does not introduce a competing identity or styling system.

Use `visual_pass`, `visual_warn`, or `visual_fail`. Keep production approval unchanged. If one targeted repair is justified, freeze and disclose a new complete prompt and hash before a new terminal call.

## 8. Completion Contract

A generation turn succeeds only when one target identity is resolved, the exact prompt and hash are disclosed before generation, and the image call is terminal. A package is complete only after later-turn visual QA covers the main board and every planned extension.

Never treat declarative prompt compliance, a preflight check, or assistant visual QA as production approval. Never substitute prompt text for a generated board.

For maintained acceptance scenarios, read [test_cases.md](test_cases.md).
