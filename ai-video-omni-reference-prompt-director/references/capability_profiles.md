# Capability Profiles

## Separate Three Layers

1. `model_target_profile`: desired semantic grammar.
2. `model_documented_profile`: first-party documented capability.
3. `provider_runtime_profile`: exact surface/endpoint currently available to the user.

The executable limit is the strict intersection of documented model capability and verified provider capability.

Bind this intersection through the stable `documented_backend_profile_id`, never by substring matching a provider's display name or model alias. A provider alias such as `vendor/doubao-seedance-2.0-omni` still inherits the documented Seedance 2.0 ceiling when it declares `documented_backend_profile_id: seedance_2_0_documented_omni`; an unknown backend cannot borrow that ceiling.

## Seedance 2.5-First Forward Target

Use profile ID `seedance_2_5_forward_compatible` for the richer semantic structure requested by the user.

Do not assume a live endpoint, 30-second duration, 50 multimodal references, or modality-specific limits unless the actual provider profile verifies them. Store public-preview or user-supplied claims as non-executable evidence:

```json
{
  "claim": "up_to_50_multimodal_inputs",
  "evidence_tier": "preview_or_user_supplied_claim",
  "runtime_verified": false,
  "usable_for_payload_budget": false
}
```

When the provider later verifies the claim, record provider, surface, model ID, retrieval timestamp, evidence locator, and exact counting rule.

## Seedance 2.0 Documented Profile

Profile ID: `seedance_2_0_documented_omni`

```text
generation mode: multimodal all-reference / reference-to-video
duration ceiling: 15 seconds
image ceiling: 9
video ceiling: 3
audio ceiling: 3
natural-language text: supported
textual storyboard: supported
multi-shot output: supported
```

These are model-level ceilings. A third-party provider may expose fewer modalities or lower counts.

First-party evidence: ByteDance Seed, “Seedance 2.0 Official Launch,” retrieved 2026-07-12: `https://seed.bytedance.com/blog/seedance-2-0-official-launch`. Preserve the URL and retrieval date in the capability artifact. This contract does not treat the absence of an official Seedance 2.5 runtime page as proof that a third-party surface cannot exist; it means such a surface must be provider-verified before its limits become executable.

## Provider Evidence Tiers

- `provider_schema_verified`: live API/UI schema and model ID verified now.
- `first_party_documented`: current official model documentation.
- `preview_or_user_supplied_claim`: useful forward-planning evidence; never a payload budget.
- `third_party_marketing_claim`: non-executable until schema-verified.
- `unknown`: no safe assumption.

`provider_schema_verified` is not a self-asserted label. Persist a local JSON snapshot and its SHA-256. The validator requires exact equality for provider, model family/ID, surface, documented backend profile, generation mode, supported modalities, every effective limit, and `input_constraints`. A URL, marketing page, model-name substring, or unbound locator alone cannot make a payload executable.

For every advertised non-text modality, `input_constraints` must be complete rather than unknown: image MIME/bytes/width/height/aspect; video MIME/container/codec/bytes/duration/width/height/aspect/fps/audio-track policy; audio MIME/codec/bytes/duration/channels/sample rate. Every minimum must be no greater than its maximum. P1 live-checks existing direct media and dry-built atlas output; V2 targets the same frozen video constraint profile; P2 live-checks actual files again with Pillow/ffprobe and compares stored video probe evidence with the live stream.

## Effective Capacity

For each numeric capability:

```text
effective_limit = min(documented_backend_limit, provider_verified_limit)
```

When either required limit is unknown, do not infer a larger value. Use a verified compatible backend or block.

## Partial R2V

If the provider supports images but not required video or audio references, the unit is not equivalent to the canonical package. Do one of:

- select a verified provider exposing the required modalities;
- redesign upstream controls only after explicit user approval;
- block the unit.

Never drop a required control, convert it to prose, or fall back to text-only/endpoint-frame generation while claiming equivalent control.

## Reference Budget Order

1. retain all relevant identity/product/material/scene/look/storyboard/keyframe/previs controls;
2. split generation units at continuity-safe boundaries between complete Shot UIDs;
3. remove only irrelevant or superseded inputs;
4. create a deterministic still-image atlas when provider counting and legibility make it valid;
5. block rather than silently omit required evidence.

Capacity is a ceiling, not a target. Redundant inputs can conflict or dilute control.

P1 never stores a freehand count without evidence. Every active preflight Canon artifact receives one unit-local decision, complete semantic role set, and artifact lock. Direct selections count once, one deterministic-atlas group counts as one image, inline authority counts zero attachments, and future K2/V2 controls are reserved by modality. Each atlas group is actually dry-built from its frozen spec and locks output hash/bytes/dimensions/runtime. `planned_reference_counts` and media feasibility must both fit effective capacity before K2/V2 begins.

If a shot interior would need splitting, the Prompt Director blocks and routes back to Shot Script Director to create stable new Shot UIDs. It never invents segment IDs inside a canonical shot.
