---
name: character-casting-lock-board
description: "Use when the user provides character references and needs a text-free 16:9 film casting contact-board asset for one selected character: one large frontal portrait plus complete front, back, and side full-body views, with narrowly justified hair, upper-body, shoe, bag, or accessory extension boards when source-backed continuity risk requires them. Resolve identity ambiguity before generation; freeze each generation prompt before its terminal image call, then later inspect every generated board and deliver one source-bound 4K enhancement prompt and handoff per board. Do not use for candidate comparison, general character sheets, poster or lookbook layouts, or prompt-only delivery."
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

Use one exact 16:9 composition, white-to-neutral-gray background, even neutral light, realistic photographic rendering, minimal shadow, and casting-documentation clarity. Author and request only 16:9; never offer, request, or silently fall back to another aspect ratio. If the runtime returns a different ratio despite the prompt, record it as a non-final intermediate layout reference and require the external 4K stage to rebuild the same content on an exact 16:9 canvas. Treat 4K as an external handoff request; claim exact raster size or native provenance only when runtime evidence exposes it.

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
2. Build the complete `final_generation_prompt` with selected identity, attachment aliases, board type, source bindings, views, continuity requirements, exact 16:9 composition, style, and strict negatives.
   Each board's `final_generation_prompt` remains its single source of truth for generating or repairing that Codex board; do not create a rewritten second generation prompt for the external handoff.
3. Keep that board's `final_4k_enhancement_prompt` unset. An optional private `draft_4k_enhancement_prompt` may capture invariant 16:9, identity, topology, source-reference, and skin-fidelity requirements, but it is not a deliverable, has no final hash, and cannot claim to diagnose a board that does not yet exist. Set `4k_enhancement_prompt_status: draft_pre_generation`.
4. Normalize the exact generation prompt as UTF-8 with LF line endings.
5. Compute `generation_prompt_sha256` from those exact bytes.
6. When filesystem access exists, save `<asset_id>_<board_id>_generation_prompt.md` and update the prompt state in `asset_record.yaml` before generation.
7. Present the exact generation prompt, board ID, and hash. Set `prompt_disclosed_before_generation: true`; state that the inspected-board-specific 4K prompt will be delivered only after later visual inspection with the original references available.
8. Set `terminal_generation_call: pending`, `assistant_qa_status: pending_post_generation_inspection`, `external_4k_status: not_ready`, and `production_approval_status: not_granted` for this board.
9. Call image generation as the final action of the turn.

Do not send text, call another tool, inspect the result, reconstruct a prompt, or claim visual success after generation in that turn. The returned image is the terminal result.

On the next continuation for that board, when the tool trace proves `terminal_generation_call: executed` and the board is available but not yet inspected, set its `4k_enhancement_prompt_status: awaiting_post_generation_inspection`. Advance to `finalized_post_inspection` only after that actual board passes later-turn inspection.

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
assistant_qa_status: pending_post_generation_inspection
4k_enhancement_prompt_status: draft_pre_generation
external_4k_status: not_ready
production_approval_status: not_granted
```

Use attachment aliases such as `selected_identity_reference`, `outfit_reference_1`, and `shoe_reference_1`, never local paths. Exclude private source maps, hidden reasoning, secrets, and unsupported identity claims. Keep all prompt text outside the image.

## 6. Artifacts And State

When filesystem access exists, use:

`outputs/character-locks/<asset_id>/`

Maintain:

- one generation-prompt sidecar per generated board;
- one finalized 4K enhancement prompt and one 4K handoff sidecar per visually accepted board;
- `asset_record.yaml` with the planned board set and every per-board generation and enhancement hash;
- generated image results;
- an optional later-turn `qa_report.md`.

Use `<asset_id>_<board_id>_4k_enhancement_prompt.md` and `<asset_id>_<board_id>_4k_handoff.yaml` for each finalized board. Keep A, B, C, and D records independent; never reuse one board's enhancement prompt or hash for another board.

Recommended state shape:

```yaml
asset_id:
asset_type: character_casting_lock_board
selected_identity:
runtime_capability_snapshot:
target_aspect_ratio: "16:9"
alternate_aspect_ratios_allowed: false
board_set:
  A: required
  B: omitted | planned | generated
  C: omitted | planned | generated
  D: omitted | planned | generated
package_external_4k_status: not_ready | handoff_ready | blocked_runtime_controls | pending_external_generation | returned_unverified | verified | rejected
boards:
  A:
    final_generation_prompt:
    generation_prompt_path:
    generation_prompt_sha256:
    draft_4k_enhancement_prompt:
    final_4k_enhancement_prompt:
    4k_enhancement_prompt_path:
    4k_enhancement_prompt_sha256:
    4k_enhancement_prompt_status: draft_pre_generation | awaiting_post_generation_inspection | finalized_post_inspection
    codex_board_role: intermediate_layout_reference | final_candidate
    external_reference_bundle:
      codex_asset_board: required
      original_source_references: required
    source_fidelity_status: pending | passed | failed | unverified | blocked_missing_original_sources
    third_party_model_target: nano_banana_pro | nano_banana_2 | model_agnostic
    external_runtime_request:
      provider:
      model_profile: nano_banana_pro | nano_banana_2 | model_agnostic
      aspect_ratio: "16:9"
      image_size: "4K"
      alternate_aspect_ratios_allowed: false
    external_4k_status: not_ready | handoff_ready | blocked_runtime_controls | pending_external_generation | returned_unverified | verified | rejected
    external_runtime_observation:
      provider: unknown
      model: unknown
      surface: unknown
      model_profile: unknown
      observed_pixel_dimensions: unknown
      provider_declared_aspect_ratio_profile: unknown
      observed_file_aspect_ratio: unknown
      aspect_ratio_evidence: unknown
      four_k_evidence: unknown
    external_4k_qa_status: pending | passed | failed
    prompt_disclosed_before_generation: true
    terminal_generation_call: pending
    assistant_qa_status: pending_post_generation_inspection
production_approval_status: not_granted
```

`terminal_generation_call` stays `pending` until the tool/runtime trace proves `executed` on a later turn. `assistant_qa_status` and `production_approval_status` are separate. Without independent later visual review, assistant QA remains `pending_post_generation_inspection`; production approval remains `not_granted` until the user or an authorized external pipeline explicitly sets `user_granted` or `external_pipeline_granted`.

## 7. Later-Turn Visual QA

Inspect each returned board only on a later turn. For the main board, verify:

- the required portrait, front, back, and side views exist;
- body views are complete to head and feet;
- identity, hair, body, outfit, shoes, bag, and accessories remain consistent;
- back and side views genuinely show their intended evidence;
- no text pollution, extra people, scene, poster, editorial, or concept-art drift appears.

For an extension, verify that it closes its named risk and does not introduce a competing identity or styling system.

Use `passed`, `conditional`, or `failed`. Keep production approval unchanged. If one targeted repair is justified, freeze and disclose a new complete prompt and hash before a new terminal call.

Do not finalize a 4K handoff for identity drift, a missing or wrong core view, incomplete head-to-toe framing, a decorative extension, a new styling system, or invented content. Repair or reject that Codex board first. A source-faithful board with only resolution, noise, edge, or microtexture limitations may proceed to its own 4K handoff.

## 8. Finalize One 4K Handoff Per Board

Only after later-turn visual inspection, replace each generated board's draft with its own image-specific `final_4k_enhancement_prompt`. Treat that Codex board as the layout and continuity reference, not as sufficient high-frequency evidence. Its external reference bundle must contain both:

- the actual Codex-generated A, B, C, or D board being enhanced;
- the original identity and board-relevant hair, skin, body, outfit, shoe, bag, handheld, or accessory references used to create it.

The final enhancement prompt for every board must:

- request source-bound enhancement or regeneration on one exact 16:9 canvas while preserving that board's panel count, placement, crops, poses, and evidence windows;
- name only defects observed in that actual board, such as noise, compression, soft facial detail, weak garment edges, or inconsistent fine texture;
- preserve the selected identity, facial geometry, age markers, skin tone, hairline, hairstyle, body proportion, outfit construction, shoes, bag, handhelds, accessories, and all cross-view continuity visible on that board;
- recover natural skin and hair microtexture only where the original references support it; preserve natural asymmetry and use photographic texture without beauty retouching, face reshaping, eye or tooth alteration, age drift, or invented pores and skin marks;
- keep the board text-free and introduce no new face, person, view, panel, garment detail, accessory, logo, label, background, crop, or decorative element;
- state that runtime settings live in the handoff record, outside the image.

For A, preserve exactly one large frontal portrait plus complete front, back, and side full-body views. For B, preserve only its approved upper-body evidence. For C, preserve only its approved hairstyle evidence, including source-supported hairline, side, back, nape, parting, braid, bun, curl, or crown structure. For D, preserve only its approved shoe, bag, handheld, or accessory evidence. An enhancement prompt for one board may not add, repair by borrowing from, or stand in for another board.

For each board, normalize the final prompt as UTF-8 with LF line endings, compute a distinct `4k_enhancement_prompt_sha256`, save `<asset_id>_<board_id>_4k_enhancement_prompt.md`, disclose the exact prompt and hash, and set `4k_enhancement_prompt_status: finalized_post_inspection` and `external_4k_status: handoff_ready`. Do not publish a draft hash or reuse another board's hash.

Write `<asset_id>_<board_id>_4k_handoff.yaml` with exact reference aliases and this only allowed request profile:

```yaml
external_runtime_request:
  provider: <selected provider or unknown>
  model_profile: nano_banana_pro | nano_banana_2 | model_agnostic
  aspect_ratio: "16:9"
  image_size: "4K"
```

Record the same selection as `third_party_model_target` for that board; the runtime-observed model remains separate evidence.

Do not encode another size or aspect-ratio option. If the selected platform cannot expose both controls, set that board's `external_4k_status: blocked_runtime_controls` and select no fallback size or ratio. Set `pending_external_generation` only when the complete handoff has actually been submitted.

When an external result returns, set that board's `external_4k_status: returned_unverified`; record provider, model, surface, model profile, requested settings, `observed_pixel_dimensions`, provider-declared aspect-ratio profile, `observed_file_aspect_ratio`, `aspect_ratio_evidence`, and `four_k_evidence`. Inspect it against the corresponding Codex board and original references. Set `verified` only when runtime evidence proves the requested 16:9 provider profile and 4K tier, the board-specific topology remains source-faithful, `source_fidelity_status: passed`, and `external_4k_qa_status: passed`. Otherwise set `rejected` and record the failing gate. Provider or model claims without runtime evidence remain `unknown`.

The number of finalized enhancement prompts, SHA-256 hashes, and handoff sidecars must equal the number of generated boards. Omitted B, C, or D boards require none; every generated board requires all three.

## 9. Completion Contract

A generation turn succeeds only when one target identity is resolved, the exact prompt and hash are disclosed before generation, and the image call is terminal. Set `package_external_4k_status: handoff_ready` only after later-turn visual QA and distinct final 4K prompt/hash/sidecar coverage for the main board and every generated extension. Set package status to `blocked_runtime_controls` if any required board lacks the exact external controls, and to `verified` only when every generated board has `external_4k_status: verified`; production approval remains a separate explicit grant.

Never treat declarative prompt compliance, a preflight check, or assistant visual QA as production approval. Never substitute prompt text for a generated board.

A pre-generation draft presented as final, a reused cross-board prompt or hash, incomplete prompt coverage, or an external result with unverified aspect ratio or size is failure.

For maintained acceptance scenarios, read [test_cases.md](test_cases.md).
