# 4K Prompt QA Checklist

## Mapping Integrity

- Every QA-approved machine asset has exactly one `4K_<ASSET_ID>` prompt.
- No unapproved, failed, blocked, human-review, or superseded asset has a finalized prompt.
- Asset ID, name, path, source dimensions, target dimensions, canon version, and neutral-appearance version match the manifest.
- Regenerating an asset marks the former prompt `stale_after_asset_regeneration` until replaced.

## Reference Priority

- The matching QA-approved neutral Codex asset is primary and highest priority.
- Canonical Diagnostic Master is the neutral appearance support.
- Original heavy-grade source is optional structure/identity support only, never the default primary reference.
- Use at most the one or two directly relevant adjacent assets; do not feed the whole package by default.

## Prompt Specificity

- Lock camera position, height, direction, framing, crop, perspective, vanishing points/horizon, topology, landmarks, scale, fixed content, materials, base colors, completion, intrinsic state, and intentionally empty regions.
- Include asset-specific facts; reject generic prompts shared across multiple assets.

## Allowed Change Boundary

- Allow only effective resolution, edge definition, distant structural clarity, texture precision, material micro-detail, and minor low-resolution artifact repair.
- Forbid redesign, expansion, reframing, perspective changes, relighting, restyling, recoloring, beautification, and cinematization.
- Forbid restoration of heavy grade, dramatic light, crushed blacks, clipped highlights, colored cast, sunset, bloom, flare, vignette, shallow focus, grain, black bars, and camera filters.

## Resolution Honesty

- Source dimensions are verified facts.
- Target dimensions are requests until the third-party output is verified.
- A prompt, filename, or requested 3840×2160 does not prove native 4K.

## Pass Condition

Require `approved_machine_asset_count == four_k_prompt_mapping_count`, one-to-one asset/prompt IDs, matching frozen versions, and zero primary-reference or look-restoration violations.
