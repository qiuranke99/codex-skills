# 4K Asset Regeneration Prompt Template

Create one complete section per QA-approved machine asset in `4K_ASSET_REGENERATION_PROMPTS.md`. Do not include the Human Review Overview Board.

## Asset Record

```markdown
## <PROMPT_ID> — <ASSET_ID> — <ASSET_NAME>

- Asset ID: `<ASSET_ID>`
- Asset Name: `<ASSET_NAME>`
- Asset Type: `<ASSET_TYPE>`
- Source Image: `<QA_APPROVED_CODEX_ASSET_PATH>`
- Source Dimensions: `<WIDTH>x<HEIGHT>`
- Target Dimensions: `<3840x2160 or ratio-appropriate target>`
- Required Reference Images:
  1. `<QA_APPROVED_CODEX_ASSET_PATH>` — primary and highest priority
  2. `<CANONICAL_DIAGNOSTIC_MASTER_PATH>` — neutral appearance support
  3. `<OPTIONAL_ORIGINAL_SOURCE>` — structure/identity support only
  4. `<OPTIONAL_RELEVANT_ADJACENT_ASSET>` — local spatial support only
- Reference Priority: `approved Codex asset > Canonical Diagnostic Master > optional original source > optional adjacent asset`
- Scene Canon Version: `<VERSION>`
- Neutral Appearance Version: `<VERSION>`

### Preservation Checklist

<asset-specific camera position, camera height, direction, framing, crop, perspective, vanishing points/horizon, topology, landmark positions, scale, fixed content, material identity, intrinsic base colors, canonical completion, intrinsic scene state, and intentionally empty regions>

### Allowed Enhancements

<effective resolution, edge definition, material micro-detail, distant structural clarity, texture precision, light compression/artifact repair; no over-sharpening>

### Forbidden Structural Changes

<asset-specific camera/framing/perspective/topology/landmark/scale/content/material/state bans>

### Forbidden Look Changes

<source-specific heavy grade, dramatic lighting, crushed shadows, clipped highlights, colored cast, sunset, bloom, flare, vignette, shallow focus, grain, black bars, filters, cinematization>

### 4K Regeneration Prompt

Use the provided QA-approved Codex scene asset as the primary and highest-priority visual reference. Preserve the exact scene identity, geometry, camera position, camera height, framing, crop, perspective, horizon, topology, landmark placement, scale, fixed content, material identity, intrinsic base colors, canonical completion, intrinsic scene state, and neutral diagnostic appearance. Only increase effective resolution, edge definition, material micro-detail, distant structural clarity, and texture precision. Do not redesign, relight, restyle, recolor, expand, remove, move, beautify, or cinematize the scene. Do not restore the heavy color grade, dramatic lighting, crushed shadows, clipped highlights, bloom, flare, vignette, shallow depth of field, film grain, or other look characteristics from the original source reference. <append asset-specific preservation and negative constraints here>

### Negative Constraints

<one line per asset-specific forbidden change>

### Post-generation QA Checklist

<exact identity, camera, composition, topology, landmarks, scale, materials, base colors, completion, state, neutral look, no added objects, no look restoration, requested pixels verified>
```

Use Chinese field explanations and an English copy-ready prompt. Keep syntax model-neutral and compatible with any reference-image model that supports high-resolution generation, including Nano Banana Pro, Nano Banana 2, GPT Image 2 4K, or equivalent tools.
