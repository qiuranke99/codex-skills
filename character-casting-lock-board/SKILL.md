---
name: character-casting-lock-board
description: "Use when the user provides character references and needs text-free horizontal 16:9-requested casting-board assets for one selected character: one large frontal portrait plus complete front, back, and side full-body views, with narrowly justified extension boards when source-backed continuity risk requires them. Resolve identity ambiguity before generation; freeze each generation prompt before its terminal image call, then inspect every board and publish every complete generation and image-specific 4K prompt pair in one later final main result. Do not use for candidate comparison, general character sheets, poster or lookbook layouts, or prompt-only delivery."
---

# Character Casting Lock Board

Contract version: `asset_board_contract_version: built_in_nonblocking_prompt_pair_v2`.

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

Request one horizontal 16:9 composition with a white-to-neutral-gray background, even neutral light, realistic photographic rendering, minimal shadow, and casting-documentation clarity. The built-in prompt must request horizontal 16:9 and no alternate ratio, but returned pixel dimensions are observational evidence only. Record each original file's dimensions and ratio without downgrading a source-faithful board, failing content QA, triggering repair, or blocking its 4K handoff when the built-in runtime returns a nearby or different ratio. Treat 4K as an external handoff request; claim exact raster size or native provenance only when runtime evidence exposes it.

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
6. Assign a monotonically increasing `attempt_id`, persist `<asset_id>_<board_id>_attempt_<attempt_id>_generation_prompt.md`, and update the attempt state in `asset_record.yaml` before generation. The sidecar bytes must be exactly the normalized prompt text with no BOM, heading, fence, frontmatter, or metadata wrapper. This sidecar is mandatory because later publication must reread the accepted attempt's original bytes. If persistence or readback is unavailable, return `blocked_generation_prompt_persistence` before image generation.
7. Present the exact generation prompt, board ID, and hash. Set `prompt_disclosed_before_generation: true`; state that the inspected-board-specific 4K prompt will be delivered only after later visual inspection with the original references available.
8. Set `terminal_generation_call: pending`, `assistant_qa_status: pending_post_generation_inspection`, `built_in_dimensions_policy: evidence_only_nonblocking`, `task_finalization_status: generation_terminal_pending`, `main_result_prompt_pair_status: pending`, `external_4k_status: not_ready`, and `production_approval_status: not_granted` for this board/package.
9. Call image generation as the final action of the turn.

Do not send text, call another tool, inspect the result, reconstruct a prompt, or claim visual success after generation in that turn. The returned image is the terminal result.

On the next continuation for that board, when the tool trace proves `terminal_generation_call: executed` and the board is available but not yet inspected, promote `task_finalization_status` from `generation_terminal_pending` to `awaiting_post_generation_continuation`, increment `generation_attempt_count` exactly once, and set its `4k_enhancement_prompt_status: awaiting_post_generation_inspection`. Count every executed original or repair call as an attempt; do not increment `generated_board_count` yet. Advance to `finalized_post_inspection` only after that actual board passes later-turn inspection. If the host does not automatically continue, the executed tool trace leaves the package at `awaiting_post_generation_continuation`; the next continuation must resume that board's inspection and prompt-pair finalization. Each generation turn is stage-complete, never package-complete. A failed or missing call never enters the awaiting state or increments the attempt count.

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
built_in_dimensions_policy: evidence_only_nonblocking
task_finalization_status: generation_terminal_pending
main_result_prompt_pair_status: pending
external_4k_status: not_ready
production_approval_status: not_granted
```

Use attachment aliases such as `selected_identity_reference`, `outfit_reference_1`, and `shoe_reference_1`, never local paths. Exclude private source maps, hidden reasoning, secrets, and unsupported identity claims. Keep all prompt text outside the image.

## 6. Artifacts And State

Use this mandatory output directory:

`outputs/character-locks/<asset_id>/`

Treat it as the writable run-scoped location for prompt truth and handoff state. If it cannot be created, written, and reread, stop before generation with `blocked_generation_prompt_persistence`.

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
built_in_prompt_aspect_ratio_request: "horizontal 16:9"
built_in_prompt_alternate_aspect_ratios_allowed: false
built_in_dimensions_policy: evidence_only_nonblocking
task_finalization_status: generation_terminal_pending | awaiting_post_generation_continuation | prompt_pair_ready | final_main_result_published
main_result_prompt_pair_status: pending | published
generated_board_count: 0
generation_attempt_count: 0
accepted_board_ids: []
finalized_4k_prompt_count: 0
4k_prompt_hash_count: 0
4k_handoff_sidecar_count: 0
published_prompt_pair_count: 0
published_board_ids: []
board_set:
  A: required
  B: omitted | planned | generated
  C: omitted | planned | generated
  D: omitted | planned | generated
package_external_4k_status: not_ready | handoff_ready | blocked_runtime_controls | pending_external_generation | returned_unverified | verified | rejected
boards:
  A:
    accepted_attempt_id:
    accepted_generation_prompt_path:
    final_generation_prompt:
    generation_prompt_path:
    generation_prompt_sha256:
    draft_4k_enhancement_prompt:
    final_4k_enhancement_prompt:
    4k_enhancement_prompt_path:
    4k_enhancement_prompt_sha256:
    4k_enhancement_prompt_status: draft_pre_generation | awaiting_post_generation_inspection | finalized_post_inspection
    codex_board_role: continuity_reference
    built_in_dimensions_observation:
      source_file:
      width_px: unknown
      height_px: unknown
      observed_aspect_ratio: unknown
      exact_16_9: unknown
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

For every generated board, read the original built-in result file header and record its width, height, observed ratio, and exact-16:9 boolean. This is provenance evidence under `built_in_dimensions_policy: evidence_only_nonblocking`; it never changes content QA, board role, repair eligibility, prompt-pair finalization, per-board handoff readiness, or package readiness.

Use `passed`, `conditional`, or `failed`. Keep production approval unchanged. If one targeted repair is justified, freeze and disclose a new complete prompt and hash before a new terminal call.

When a board becomes the current accepted A, B, C, or D result, bind its `accepted_attempt_id`, `accepted_generation_prompt_path`, `final_generation_prompt`, and `generation_prompt_sha256` to that exact attempt. Add its unique `board_id` to `accepted_board_ids` once and set `generated_board_count` to the size of that set. Rejected attempts increase only `generation_attempt_count`; a repair that replaces a prior accepted attempt updates the binding without increasing `generated_board_count`. Final publication may use only the current accepted attempt, never a rejected or superseded prompt.

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

For each board, normalize the final prompt as UTF-8 with LF line endings, compute a distinct `4k_enhancement_prompt_sha256`, and save exactly those bytes as `<asset_id>_<board_id>_4k_enhancement_prompt.md` with no BOM, heading, fence, frontmatter, or metadata wrapper. Do not publish a draft hash or reuse another board's hash.

Before marking that board's pair ready, reopen its `accepted_generation_prompt_path` and `<asset_id>_<board_id>_4k_enhancement_prompt.md` as their original UTF-8/LF bytes, recompute both SHA-256 values, and require exact equality with the accepted frozen records. Never reconstruct either prompt from memory, chat, a summary, or `asset_record.yaml`. A missing sidecar or hash mismatch is `blocked_prompt_pair_integrity`; keep the package `main_result_prompt_pair_status: pending`. After both checks pass, set only the board's `4k_enhancement_prompt_status: finalized_post_inspection`; external readiness remains independent.

Write `<asset_id>_<board_id>_4k_handoff.yaml` with exact reference aliases and this only allowed request profile:

```yaml
external_runtime_request:
  provider: <selected provider or unknown>
  model_profile: nano_banana_pro | nano_banana_2 | model_agnostic
  aspect_ratio: "16:9"
  image_size: "4K"
```

Record the same selection as `third_party_model_target` for that board; the runtime-observed model remains separate evidence. Increment `finalized_4k_prompt_count`, `4k_prompt_hash_count`, and `4k_handoff_sidecar_count` exactly once when that board's verified artifacts exist. Set that board's `external_4k_status: handoff_ready` only when its Codex board plus original-reference bundle, handoff sidecar, selected provider, and exposed exact 16:9 and 4K controls are all ready; otherwise retain `not_ready` or use `blocked_runtime_controls` as applicable.

Do not encode another size or aspect-ratio option. If the selected platform cannot expose both controls, set that board's `external_4k_status: blocked_runtime_controls` and select no fallback size or ratio. Set `pending_external_generation` only when the complete handoff has actually been submitted.

If more boards remain planned, persist the verified pair and continue the one-terminal-call-per-turn sequence. After every accepted board has a verified pair, require `generated_board_count == finalized_4k_prompt_count == 4k_prompt_hash_count == 4k_handoff_sidecar_count` and coverage of every `accepted_board_id`, then set `task_finalization_status: prompt_pair_ready`. `prompt_pair_ready` proves prompt integrity only and does not imply any board or package `external_4k_status: handoff_ready`; the external reference and runtime-control gates remain independent.

Preflight whether one final response can contain every accepted board's complete pair and hashes. If a real output ceiling prevents that, return `blocked_final_output_capacity`, keep `main_result_prompt_pair_status: pending`, and never truncate, summarize, link-only, or split the package while claiming publication.

Publish one block per accepted board in the task's final main result using the `final` channel. Each block must include both complete prompt texts inline; commentary, sidecars, paths, hashes alone, excerpts, or summaries cannot replace them.

```text
board_id: <A | B | C | D>
accepted_attempt_id: <current accepted attempt>

final_generation_prompt:
<complete exact text reread from this board's frozen generation sidecar>

generation_prompt_sha256: <verified sha256>

final_4k_enhancement_prompt:
<complete exact image-specific text reread from this board's frozen 4K sidecar>

4k_enhancement_prompt_sha256: <verified sha256>
```

End the same final result with this package record:

```text
accepted_board_ids: [<every accepted board_id>]
published_board_ids: [<every board_id whose complete block appears above>]
generated_board_count: <accepted-board count>
published_prompt_pair_count: <complete-block count>
main_result_prompt_pair_status: published
task_finalization_status: final_main_result_published
```

Publication requires set equality `published_board_ids == accepted_board_ids` and count equality `published_prompt_pair_count == generated_board_count`. The complete final response is itself the transition evidence. Because a `final` response is terminal, require no status write or tool call after emission.

When an external result returns, set that board's `external_4k_status: returned_unverified`; record provider, model, surface, model profile, requested settings, `observed_pixel_dimensions`, provider-declared aspect-ratio profile, `observed_file_aspect_ratio`, `aspect_ratio_evidence`, and `four_k_evidence`. Inspect it against the corresponding Codex board and original references. Set `verified` only when runtime evidence proves the requested 16:9 provider profile and 4K tier, the board-specific topology remains source-faithful, `source_fidelity_status: passed`, and `external_4k_qa_status: passed`. Otherwise set `rejected` and record the failing gate. Provider or model claims without runtime evidence remain `unknown`.

The number of finalized enhancement prompts, SHA-256 hashes, handoff sidecars, and published complete prompt pairs must equal the number of accepted/current boards. Omitted and rejected A, B, C, or D attempts require no published pair; every accepted board requires all four.

## 9. Completion Contract

A generation turn is stage-complete only when one target identity is resolved, the exact prompt and hash are disclosed before generation, the image call is terminal, and `task_finalization_status: awaiting_post_generation_continuation`. `generation_attempt_count` counts every executed call; `generated_board_count` counts unique accepted/current board IDs only. The Skill task completes only after its later final main result contains every accepted board's complete verified prompt pair, `published_board_ids == accepted_board_ids`, `published_prompt_pair_count == generated_board_count`, and `main_result_prompt_pair_status: published`. Built-in pixel dimensions remain non-blocking evidence; a ratio mismatch cannot cause content failure, repair, demotion, or handoff blocking.

Set `package_external_4k_status: handoff_ready` only after later-turn visual QA and distinct source-bound 4K prompt/hash/sidecar coverage for the main board and every generated extension, with original references plus each Codex board. Set package status to `blocked_runtime_controls` if any required external board lacks exact 16:9 and 4K controls, and to `verified` only when every generated board has `external_4k_status: verified`; production approval remains a separate explicit grant.

Never treat declarative prompt compliance, a preflight check, or assistant visual QA as production approval. Never substitute prompt text for a generated board.

A pre-generation draft presented as final, a reused cross-board prompt or hash, incomplete prompt coverage, or an external result with unverified aspect ratio or size is failure.

For maintained acceptance scenarios, read [test_cases.md](test_cases.md).

## Optional AI-Video Project Canon Export

This is a downstream-only integration and changes none of the board topology,
terminal generation, later-turn inspection, 4K handoff, or complete prompt-pair
publication rules above. Use it only when the current accepted board has
`assistant_qa_status: passed`, both accepted prompt sidecars have passed byte
readback, and production approval is explicitly `user_granted` or
`external_pipeline_granted`.

After that explicit decision, this owner may write a strict approval JSON
conforming to
`../ai-video-shot-script-director/references/ai_video_owner_asset_approval.schema.json`.
It must bind this Skill name, asset key, primary board SHA-256, the exact
`generation_prompt` and `four_k_enhancement_prompt` hashes, approved Shot UIDs,
QA pass, and production decision. Then run only this package's fixed-owner
`scripts/export_ai_video_canon.py`; it has no owner override. Supply
project-relative primary/prompt/approval locators and their exact hashes plus
every affected Shot UID. This owner exports only
`authority_mode: identity_and_wardrobe` with
`control_roles_authorized: [identity, wardrobe]`; the hashed approval evidence
must bind the same values.
The export runtime requires Pillow to `verify()` and fully `load()` the primary
PNG/JPEG/WebP board; missing Pillow, decode failure, mismatched extension, or a
board below 64×64 fails closed before Canon mutation.

The wrapper writes the owner-produced `ai-video-artifact-v1` record, four-lock
Canon entry, immutable base snapshot, entry delta, receipt, and validated
pre/post transition. Prompt Director must consume this real Canon owner record;
it may not manufacture an authority projection. Export failure does not alter
or demote the accepted visual asset.

This casting board remains pre-Canon by default. Export is forbidden unless it
is deliberately selected as the terminal character route and the wrapper is
invoked with `--casting-as-terminal`. Approval and export records must bind
`authority_stage: terminal_character_canon` and
`terminal_route_decision: casting_as_terminal`. For one `asset_key`, this route
is mutually exclusive with both final-character owners. Install the pinned
decoder with `python3 -m pip install -r ../ai-video-shot-script-director/requirements.txt`.
