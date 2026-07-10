---
name: character-final-lock-board
description: "Use when the user provides one or more person/model references, optional wardrobe, shoe, accessory, or prop references, and wants one comprehensive 16:9 character lock board for AI image or video continuity. Generate a text-free board with portrait, complete multi-angle body views, expressions, details, and silhouettes; support high-angle evidence as required, optional, or off. Freeze the exact generation prompt before the terminal image call, then later inspect the result and deliver a source-bound 4K enhancement prompt and handoff. Do not use for candidate comparison, the exactly-one-face headless-body topology, or prompt-only delivery."
---

# Character Final Lock Board

Generate one comprehensive final character lock board. Keep one selected identity and one coherent wardrobe system across every panel. This is not a candidate sheet, fashion layout, scene image, or prompt-only workflow.

## 1. Resolve Inputs

Require at least one usable person/model reference. Accept optional wardrobe, shoe, accessory, prop, role, direction, and asset-ID inputs.

Resolve the target identity before building a prompt:

- Combine multiple references only when they clearly depict the same target identity.
- If references depict different people and the user selected one identity, use only that person as identity evidence. Other people may be used solely for explicitly assigned non-identity roles such as wardrobe.
- If two or more identities remain plausible and the target is not selected, return `identity_conflict` and ask for one target. Do not blend, average, or infer a preferred face.
- If only wardrobe or accessory references exist, return `hard_blocked_no_person_reference`.
- Treat age-direction words as styling pressure unless the user explicitly requests a new character rather than an identity lock.
- Stop at `policy_blocked` when generation policy prevents the request.

Input status must be exactly one of:

- `ready`
- `identity_conflict`
- `hard_blocked_no_person_reference`
- `policy_blocked`

Do not call image generation unless status is `ready`.

## 2. Build The Source Ledger

Privately record attachment aliases and evidence status for:

- `identity_source`
- `body_source`
- `wardrobe_source`
- `shoe_source`
- `accessory_source`
- `prop_source`

Use source statuses:

- `user_locked`: explicitly assigned by the user;
- `source_supported`: visibly supported by a supplied reference;
- `safe_inferred`: necessary low-risk inference from incomplete evidence;
- `missing_or_conflicting`: absent or contradictory.

Never present `safe_inferred` details as verified. Do not put private paths, hidden reasoning, or confidential notes in the generation prompt.

## 3. Select High-Angle Evidence

Set `high_angle_evidence` to exactly one of:

- `required`: the user asks for a high-angle, top-down, crown-hair, or elevated-camera continuity view. The board must contain a readable high-angle view and visual QA must later verify it.
- `optional`: the user did not require it, but crown hair, hairline, shoulder-neck proportion, collar, neckline, or elevated-camera continuity is materially fragile. Add it only when the board can remain readable without weakening core views.
- `off`: high-angle evidence is neither requested nor risk-justified. Do not spend panel capacity on it.

Use a high-angle 3/4 full-body, upper-body, or slight top-down view. Do not use an extreme 90-degree overhead view unless explicitly requested.

Keep high-angle evidence as this Skill's `required | optional | off` branch. Never create, invoke, or restore a separate high-angle Skill package for this capability.

## 4. Compose The Board

Always require:

- one large frontal or near-frontal facial portrait;
- front, back, side, and 3/4 complete full-body views with heads present;
- one or two restrained natural pose variants;
- four to six expression head tiles;
- three to five useful detail crops for identity, hair, garment, shoe, accessory, or prop continuity;
- two or three simple silhouettes.

Use an exact 16:9 composition, clean white or light-gray studio background, neutral catalog light, realistic photographic rendering, and asset-board clarity. Keep every body view head-to-toe and prevent props from hiding a neutral front view. Author and request only 16:9; never offer, request, or silently fall back to another aspect ratio. If the runtime returns a different ratio despite the prompt, record it as a non-final intermediate layout reference and require the external 4K stage to rebuild the same content on an exact 16:9 canvas.

If `high_angle_evidence` is `required`, add at least one high-angle panel. If `optional`, add one only after all mandatory views remain legible. If `off`, omit it.

Inside the image, forbid text, titles, labels, arrows, measurements, logos, watermarks, UI, gibberish, scene environments, dramatic cinematic light, fashion-editorial treatment, illustration, anime, CGI, and unrelated people.

## 5. Freeze The Runtime Contract

Call the available built-in image-generation capability directly. Prefer GPT Image 2 only when the interface exposes that choice. Do not claim a model, raster size, seed, or native 4K provenance that the runtime does not expose.

Before the image-generation call:

1. Capture `runtime_capability_snapshot`: callable image tool, exposed model choice, exposed size controls, usable reference count, and any known output/provenance limits. Unknown values remain `unknown`; never infer them.
2. Build the complete `final_generation_prompt`, including reference aliases, board topology, identity and wardrobe locks, `high_angle_evidence`, and strict negatives.
   `final_generation_prompt` remains the single source of truth for generating or repairing the Codex board; do not create a rewritten second generation prompt for the external handoff.
3. Keep `final_4k_enhancement_prompt` unset. An optional private `draft_4k_enhancement_prompt` may capture invariant 16:9, identity, topology, source-reference, and skin-fidelity requirements, but it is not a deliverable, has no final hash, and cannot claim to diagnose an image that does not yet exist. Set `4k_enhancement_prompt_status: draft_pre_generation`.
4. Normalize the exact generation prompt as UTF-8 text with LF line endings.
5. Compute `generation_prompt_sha256` from those exact bytes.
6. When filesystem access exists, save the generation prompt before generation as `<asset_id>_generation_prompt.md` and record the prompt state in `asset_record.yaml`.
7. Present the exact generation prompt and its hash before generation. Set `prompt_disclosed_before_generation: true`; state that the inspected-board-specific 4K prompt will be delivered only after later visual inspection with the original references available.
8. Set `terminal_generation_call: pending`, `assistant_qa_status: pending_post_generation_inspection`, `external_4k_status: not_ready`, and `production_approval_status: not_granted`.
9. Call image generation as the final action of the turn.

Do not send text, call another tool, reconstruct the prompt, inspect the image, or claim visual success after the generation call in the same turn. The generation result itself completes that turn. If the tool contract later permits post-call actions, preserve this ordering unless exact prompt traceability remains equally strong.

On the next continuation, when the tool trace proves `terminal_generation_call: executed` and the board is available but not yet inspected, set `4k_enhancement_prompt_status: awaiting_post_generation_inspection`. Advance to `finalized_post_inspection` only after the actual board passes the later-turn inspection gate.

If the prompt cannot be frozen or the image tool is unavailable, return `hard_blocked_generation_runtime` without presenting a substitute run as successful.

Use this pre-generation disclosure shape:

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

## 6. Prompt Requirements

The frozen prompt must state:

- which attachment aliases control identity, body, wardrobe, shoes, accessories, and props;
- that one selected identity and one wardrobe system must persist across all panels;
- the mandatory board views and panel counts;
- the selected `high_angle_evidence` behavior;
- an exact 16:9 board with no alternate aspect-ratio branch;
- background, lighting, photographic style, and complete-body requirements;
- strict negatives;
- that all prompt text stays outside the generated image.

Use aliases such as `person_reference_1` and `wardrobe_reference_1`, never local absolute paths. Exclude source maps, hidden reasoning, secrets, and unsupported identity claims.

## 7. Artifacts And Status

When filesystem access exists, use:

`outputs/character-locks/<asset_id>/`

Pre-generation artifacts:

- `<asset_id>_generation_prompt.md`
- `asset_record.yaml`

Generation result:

- `<asset_id>_final_lock_board.png` or the native result returned by the generator.

Later-turn 4K handoff artifacts:

- `<asset_id>_4k_enhancement_prompt.md`
- `<asset_id>_4k_handoff.yaml`

Recommended `asset_record.yaml` fields:

```yaml
asset_id:
asset_type: character_final_lock_board
status: generation_pending
runtime_capability_snapshot:
target_aspect_ratio: "16:9"
alternate_aspect_ratios_allowed: false
identity_source:
body_source:
wardrobe_source:
shoe_source:
accessory_source:
prop_source:
high_angle_evidence: required | optional | off
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
generator_model_claim: runtime_exposed_only
prompt_disclosed_before_generation: true
terminal_generation_call: pending
assistant_qa_status: pending_post_generation_inspection
production_approval_status: not_granted
```

`terminal_generation_call` is a state machine: keep it `pending` before the call and change it to `executed` only from the tool/runtime trace on a later turn. `assistant_qa_status` and `production_approval_status` are independent. Without an independent later visual review, assistant QA remains `pending_post_generation_inspection`; production approval remains `not_granted` until the user or an authorized external pipeline explicitly changes it to `user_granted` or `external_pipeline_granted`.

## 8. Later-Turn Visual Review

Only on a later turn with the generated image available, inspect it and check:

- one identity and one wardrobe system remain consistent;
- all mandatory views and full heads/feet are present;
- expressions, details, and silhouettes meet their counts;
- the required high-angle panel exists when mode is `required`;
- optional high-angle evidence did not displace a core view;
- no extra people, text pollution, scene background, or style drift appears;
- the image corresponds to the frozen prompt and reference set.

Set `assistant_qa_status` to `passed`, `conditional`, or `failed`. Keep `production_approval_status` unchanged.

If one repair is justified, build a new complete prompt, freeze and disclose its new hash before calling image generation. The repair call is again the final action of its turn. Never claim that a rejected attempt and a repaired image share the same prompt hash.

Do not finalize a 4K handoff for identity drift, missing core views, a wrong board topology, a missing required high-angle panel, or invented content. Repair or reject the Codex board first. A source-faithful board with only resolution, noise, edge, or microtexture limitations may proceed to the 4K handoff.

## 9. Finalize The 4K Handoff

Only after later-turn visual inspection, replace the draft with one image-specific `final_4k_enhancement_prompt`. Treat the Codex board as the layout and continuity reference, not as sufficient high-frequency evidence. The external reference bundle must contain both:

- the actual Codex-generated board;
- the original person, wardrobe, shoe, accessory, and prop references used to create it.

The final enhancement prompt must:

- request source-bound enhancement or regeneration on one exact 16:9 canvas, preserving panel count, placement, crops, poses, expressions, detail windows, silhouettes, and all source-supported content;
- name only defects observed in the actual board, such as noise, compression, soft facial detail, weak garment edges, or inconsistent fine texture;
- preserve exact facial geometry, age markers, skin tone, hairline, hairstyle, body proportion, wardrobe construction, shoes, accessories, and cross-panel identity;
- recover natural skin and hair microtexture only where the original references support it; preserve natural asymmetry and use photographic texture without beauty retouching, face reshaping, eye or tooth alteration, age drift, or invented pores and skin marks;
- preserve the resolved `high_angle_evidence` mode; when required, retain the elevated-camera perspective, crown hair, head shape, shoulder-neck relationship, collar, and accessories without converting it into an extreme overhead view;
- keep the board text-free and introduce no new face, person, panel, garment detail, prop, logo, label, background, crop, or decorative element;
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

When an external result returns, set `external_4k_status: returned_unverified`; record provider, model, surface, model profile, requested settings, `observed_pixel_dimensions`, provider-declared aspect-ratio profile, `observed_file_aspect_ratio`, `aspect_ratio_evidence`, and `four_k_evidence`. Inspect the final image against the Codex board and original references. Set `verified` only when runtime evidence proves the requested 16:9 provider profile and 4K tier, every panel remains source-faithful, `source_fidelity_status: passed`, and `external_4k_qa_status: passed`. Otherwise set `rejected` and record the failing gate. Provider or model claims without runtime evidence remain `unknown`.

## 10. Completion Contract

A generation turn succeeds only when:

- input status was `ready`;
- `high_angle_evidence` was resolved;
- the exact prompt and hash were disclosed before generation;
- image generation was called as the terminal action;
- the result is described as pending visual review and production approval, not as an approved lock.

The Skill reaches `external_4k_status: handoff_ready` only after later-turn inspection, final enhancement-prompt disclosure, SHA-256 creation, and sidecar creation. It reaches production-complete state only after an external result returns with `external_4k_status: verified`; production approval remains a separate explicit grant.

Prompt-only output, an unresolved identity conflict, a missing image call, a pre-generation draft presented as final, an external result with an unverified aspect ratio or size, or a post-hoc reconstructed prompt is not success.
