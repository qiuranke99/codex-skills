---
name: single-face-character-lock-board
description: "Use when the user provides character references and needs exactly one text-free 16:9 single-face asset board: one bust portrait containing the board's only visible face, one headless front full-body outfit view, and one headless back full-body outfit view. Resolve one target identity before generation; freeze the exact generation prompt before the terminal image call, then later inspect the result and deliver a source-bound 4K enhancement prompt and handoff. Do not use for ordinary turnarounds, expression sheets, casting contact boards, or prompt-only delivery."
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

Use one exact 16:9, clean, neutral-gray studio board with realistic photographic texture, soft even light, minimal shadow, and production-reference clarity. Author and request only 16:9; never offer, request, or silently fall back to another aspect ratio. If the runtime returns a different ratio despite the prompt, record it as a non-final intermediate layout reference and require the external 4K stage to rebuild the same three components on an exact 16:9 canvas.

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
   `final_generation_prompt` remains the single source of truth for generating or repairing the Codex board; do not create a rewritten second generation prompt for the external handoff.
3. Keep `final_4k_enhancement_prompt` unset. An optional private `draft_4k_enhancement_prompt` may capture invariant 16:9, exactly-one-face, headless-body, source-reference, and skin-fidelity requirements, but it is not a deliverable, has no final hash, and cannot claim to diagnose an image that does not yet exist. Set `4k_enhancement_prompt_status: draft_pre_generation`.
4. Normalize the exact generation prompt as UTF-8 with LF line endings.
5. Compute `generation_prompt_sha256` from those exact bytes.
6. When filesystem access exists, save `<asset_id>_generation_prompt.md` and write the prompt state to `asset_record.yaml` before generation.
7. Present the exact generation prompt and its hash. Set `prompt_disclosed_before_generation: true`; state that the inspected-board-specific 4K prompt will be delivered only after later visual inspection with the original references available.
8. Set `terminal_generation_call: pending`, `assistant_qa_status: pending_post_generation_inspection`, `external_4k_status: not_ready`, and `production_approval_status: not_granted`.
9. Call image generation as the final action of the turn.

Do not send text, call another tool, inspect the output, reconstruct the prompt, or claim visual success after the image-generation call in that turn. The returned image is the terminal result.

On the next continuation, when the tool trace proves `terminal_generation_call: executed` and the board is available but not yet inspected, set `4k_enhancement_prompt_status: awaiting_post_generation_inspection`. Advance to `finalized_post_inspection` only after the actual board passes the later-turn inspection gate.

If no image tool is callable or the prompt cannot be frozen exactly, return `hard_blocked_generation_runtime`. Do not present prompt-only output as success.

Use this disclosure shape before the terminal call:

```text
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

## 5. Prompt Content

The frozen prompt must require:

- exactly one 16:9 board and exactly three panels, with no alternate aspect-ratio branch;
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

Later-turn 4K handoff artifacts:

- `<asset_id>_4k_enhancement_prompt.md`
- `<asset_id>_4k_handoff.yaml`

Recommended record fields:

```yaml
asset_id:
asset_type: single_face_character_lock_board
status: generation_pending
runtime_capability_snapshot:
target_aspect_ratio: "16:9"
alternate_aspect_ratios_allowed: false
identity_source:
body_source:
outfit_source:
shoe_source:
accessory_source:
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

`terminal_generation_call` stays `pending` until a tool/runtime trace proves `executed` on a later turn. `assistant_qa_status` and `production_approval_status` are separate. Without an independent later visual review, assistant QA remains `pending_post_generation_inspection`; production approval remains `not_granted` until the user or an authorized external pipeline explicitly sets `user_granted` or `external_pipeline_granted`.

## 7. Later-Turn Visual Review And Repair

On a later turn with the generated image available, inspect:

- exactly one complete visible face exists, with no other complete or partial face;
- the bust clearly preserves the selected identity;
- front and back body views are headless and complete to the feet;
- body, outfit, shoes, and accessories remain consistent;
- no text, additional panels, scenic background, or editorial style appears.

If all structural checks pass, set `assistant_qa_status: passed`; use `conditional` for a useful but source-limited board and `failed` for a critical topology or fidelity failure. Keep `production_approval_status` unchanged.

If one repair is justified, freeze and disclose a new complete prompt and new hash before a new terminal generation call. Never output a failed draft prompt as the prompt for an accepted image.

Do not finalize a 4K handoff when the board contains more or fewer than three components, more than one complete or partial face, a head on either body view, identity drift, missing feet, or invented content. Repair or reject the Codex board first. A source-faithful board with only resolution, noise, edge, or microtexture limitations may proceed to the 4K handoff.

## 8. Finalize The 4K Handoff

Only after later-turn visual inspection, replace the draft with one image-specific `final_4k_enhancement_prompt`. Treat the Codex board as the layout and topology reference, not as sufficient high-frequency evidence. The external reference bundle must contain both:

- the actual Codex-generated board;
- the original identity, hair, skin, body, outfit, shoe, and accessory references used to create it.

The final enhancement prompt must:

- request source-bound enhancement or regeneration on one exact 16:9 canvas while preserving exactly three components and their positions;
- name only defects observed in the actual board, such as noise, compression, soft facial detail, weak garment edges, or inconsistent fine texture;
- keep exactly one complete visible face in the bust portrait and keep both front and back body views headless from the neck downward, including reflections, prints, shadows, and background details;
- preserve exact facial geometry, age markers, skin tone, hairline, hairstyle, body proportion, outfit construction, shoes, accessories, and identity continuity;
- recover natural skin and hair microtexture only where the original references support it; preserve natural asymmetry and use photographic texture without beauty retouching, face reshaping, eye or tooth alteration, age drift, or invented pores and skin marks;
- keep the board text-free and introduce no new head, face, person, panel, garment detail, accessory, logo, label, background, crop, or decorative element;
- state that runtime settings live in the handoff record, outside the image.

Normalize the final prompt as UTF-8 with LF line endings, compute `4k_enhancement_prompt_sha256`, save it as `<asset_id>_4k_enhancement_prompt.md`, disclose the exact prompt and hash, and set `4k_enhancement_prompt_status: finalized_post_inspection` and `external_4k_status: handoff_ready`. Do not publish or reuse a draft hash.

Write `<asset_id>_4k_handoff.yaml` with the exact reference aliases and this only allowed request profile:

```yaml
external_runtime_request:
  provider: <selected provider or unknown>
  model_profile: nano_banana_pro | nano_banana_2 | model_agnostic
  aspect_ratio: "16:9"
  image_size: "4K"
```

Record the same selection as `third_party_model_target`; the runtime-observed model remains separate evidence.

Do not encode another size or aspect-ratio option. If the selected platform cannot expose both controls, set `external_4k_status: blocked_runtime_controls` and select no fallback size or ratio. Set `pending_external_generation` only when the complete handoff has actually been submitted.

When an external result returns, set `external_4k_status: returned_unverified`; record provider, model, surface, model profile, requested settings, `observed_pixel_dimensions`, provider-declared aspect-ratio profile, `observed_file_aspect_ratio`, `aspect_ratio_evidence`, and `four_k_evidence`. Inspect the final image against the Codex board and original references. Set `verified` only when runtime evidence proves the requested 16:9 provider profile and 4K tier, the board still contains exactly one visible face and two headless body views, every component remains source-faithful, `source_fidelity_status: passed`, and `external_4k_qa_status: passed`. Otherwise set `rejected` and record the failing gate. Provider or model claims without runtime evidence remain `unknown`.

## 9. Completion Contract

A generation turn succeeds only when one target identity is resolved, the exact prompt and hash are disclosed before generation, and image generation is the terminal action. The generated image remains pending visual review, 4K handoff finalization, and production approval.

The Skill reaches `external_4k_status: handoff_ready` only after later-turn inspection, final enhancement-prompt disclosure, SHA-256 creation, and sidecar creation. It reaches production-complete state only after an external result returns with `external_4k_status: verified`; production approval remains a separate explicit grant.

Unselected multiple identities, prompt-only delivery, a missing image call, extra board views, a pre-generation draft presented as final, an external result with an unverified aspect ratio or size, or post-hoc prompt reconstruction is failure.
