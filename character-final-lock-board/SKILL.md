---
name: character-final-lock-board
description: "Use when the user provides one or more person/model references, optional wardrobe, shoe, accessory, or prop references, and wants one final comprehensive character lock board for AI image or video continuity. Generate one text-free board with portrait, complete multi-angle body views, expressions, details, and silhouettes; support high-angle evidence as required, optional, or off. Freeze and disclose the exact generation prompt and SHA-256 before the terminal image-generation call. Do not use for candidate comparison, the exactly-one-face headless-body topology, or prompt-only delivery."
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

## 4. Compose The Board

Always require:

- one large frontal or near-frontal facial portrait;
- front, back, side, and 3/4 complete full-body views with heads present;
- one or two restrained natural pose variants;
- four to six expression head tiles;
- three to five useful detail crops for identity, hair, garment, shoe, accessory, or prop continuity;
- two or three simple silhouettes.

Use a wide 16:9-or-wider composition, clean white or light-gray studio background, neutral catalog light, realistic photographic rendering, and asset-board clarity. Keep every body view head-to-toe and prevent props from hiding a neutral front view.

If `high_angle_evidence` is `required`, add at least one high-angle panel. If `optional`, add one only after all mandatory views remain legible. If `off`, omit it.

Inside the image, forbid text, titles, labels, arrows, measurements, logos, watermarks, UI, gibberish, scene environments, dramatic cinematic light, fashion-editorial treatment, illustration, anime, CGI, and unrelated people.

## 5. Freeze The Runtime Contract

Call the available built-in image-generation capability directly. Prefer GPT Image 2 only when the interface exposes that choice. Do not claim a model, raster size, seed, or native 4K provenance that the runtime does not expose.

Before the image-generation call:

1. Capture `runtime_capability_snapshot`: callable image tool, exposed model choice, exposed size controls, usable reference count, and any known output/provenance limits. Unknown values remain `unknown`; never infer them.
2. Build the complete `final_generation_prompt`, including reference aliases, board topology, identity and wardrobe locks, `high_angle_evidence`, and strict negatives.
3. Normalize the exact prompt as UTF-8 text with LF line endings.
4. Compute `generation_prompt_sha256` from those exact bytes.
5. When filesystem access exists, save the prompt before generation as `<asset_id>_generation_prompt.md` and record the prompt record in `asset_record.yaml`.
6. Present the exact prompt and hash to the user before generation, then set `prompt_disclosed_before_generation: true`. State that it depends on the same attached references and is not a standalone identity guarantee.
7. Set `terminal_generation_call: pending`, `assistant_qa_status: pending`, and `production_approval_status: not_granted`.
8. Call image generation as the final action of the turn.

Do not send text, call another tool, reconstruct the prompt, inspect the image, or claim visual success after the generation call in the same turn. The generation result itself completes that turn. If the tool contract later permits post-call actions, preserve this ordering unless exact prompt traceability remains equally strong.

If the prompt cannot be frozen or the image tool is unavailable, return `hard_blocked_generation_runtime` without presenting a substitute run as successful.

Use this pre-generation disclosure shape:

```text
Image generation prompt:
<exact final_generation_prompt>

generation_prompt_sha256: <sha256>
prompt_disclosed_before_generation: true
terminal_generation_call: pending
assistant_qa_status: pending
production_approval_status: not_granted
```

## 6. Prompt Requirements

The frozen prompt must state:

- which attachment aliases control identity, body, wardrobe, shoes, accessories, and props;
- that one selected identity and one wardrobe system must persist across all panels;
- the mandatory board views and panel counts;
- the selected `high_angle_evidence` behavior;
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

Recommended `asset_record.yaml` fields:

```yaml
asset_id:
asset_type: character_final_lock_board
status: generation_pending
runtime_capability_snapshot:
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
generator_model_claim: runtime_exposed_only
prompt_disclosed_before_generation: true
terminal_generation_call: pending
assistant_qa_status: pending
production_approval_status: not_granted
```

`terminal_generation_call` is a state machine: keep it `pending` before the call and change it to `executed` only from the tool/runtime trace on a later turn. `assistant_qa_status` and `production_approval_status` are independent. Without an independent later visual review, assistant QA remains `pending`; production approval remains `not_granted` until the user or an authorized external pipeline explicitly changes it to `user_granted` or `external_pipeline_granted`.

## 8. Later-Turn Visual Review

Only on a later turn with the generated image available, inspect it and check:

- one identity and one wardrobe system remain consistent;
- all mandatory views and full heads/feet are present;
- expressions, details, and silhouettes meet their counts;
- the required high-angle panel exists when mode is `required`;
- optional high-angle evidence did not displace a core view;
- no extra people, text pollution, scene background, or style drift appears;
- the image corresponds to the frozen prompt and reference set.

Set `assistant_qa_status` to `visual_pass`, `visual_warn`, or `visual_fail`. Keep `production_approval_status` unchanged.

If one repair is justified, build a new complete prompt, freeze and disclose its new hash before calling image generation. The repair call is again the final action of its turn. Never claim that a rejected attempt and a repaired image share the same prompt hash.

## 9. Completion Contract

A generation turn succeeds only when:

- input status was `ready`;
- `high_angle_evidence` was resolved;
- the exact prompt and hash were disclosed before generation;
- image generation was called as the terminal action;
- the result is described as pending visual review and production approval, not as an approved lock.

Prompt-only output, an unresolved identity conflict, a missing image call, or a post-hoc reconstructed prompt is not success.
