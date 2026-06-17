# Reference Asset Syntax

Use this file when users mention images, videos, audio, elements, first/last frames, products, characters, or API usage.

## Intake Principle

Do not require a full asset spreadsheet. Infer roles from the user's wording and ask only when a reference's role is ambiguous enough to change the output.

Good minimal user input:

`I have @Image1 product photo and @Video1 as movement reference. Make a 12s premium ad.`

The skill should infer:

- `@Image1`: product identity and packaging anchor.
- `@Video1`: motion/camera/editing reference, not identity.
- Model: Kling 3.0 Omni if product consistency matters across shots.

## App-Style Prompt Labels

Use app-style labels by default:

- `@Image1`, `@Image2`
- `@Video1`
- `@Audio1`
- `@Element1`, `@CharacterA`, `@ProductA`

Always state what the asset controls:

| Role | Prompt wording |
|---|---|
| First frame | `@Image1 is the first frame and composition anchor.` |
| Last frame | `@Image2 is the final frame target; transition toward it by the last shot.` |
| Character identity | `@CharacterA anchors face, outfit, body type, and silhouette.` |
| Product identity | `@ProductA anchors exact shape, logo placement, material, and package proportions.` |
| Scene/environment | `@Image2 provides the environment, lighting, and palette only.` |
| Camera reference | `@Video1 provides camera movement and framing rhythm only.` |
| Motion reference | `@Video1 provides action timing and physical choreography only.` |
| Style reference | `@Image3 provides color grade, lighting contrast, and art direction only.` |
| Voice reference | `@Audio1 provides voice tone and delivery only.` |
| Music rhythm | `@Audio1 provides BPM/beat structure for cuts and movement accents.` |

## API-Style Tags

Use API-style tags only when the user asks for API payloads or names an API surface that expects tags.

Example dialect:

```text
<<<image_1>>> anchors the hero product. <<<image_2>>> provides the kitchen environment. Generate a 12-second multi-shot video...
```

Do not mix app-style `@Image1` and API-style `<<<image_1>>>` in the same final prompt unless the user explicitly requests both.

## API-Safe Notes

When the user asks for API guidance but does not name an exact provider/schema, output intent-level notes instead of a fake payload:

```text
API-safe notes:
- Intended model: Kling 3.0 Omni (`kling-v3-omni` only if your provider exposes that exact model id).
- Duration intent: 15 seconds.
- Aspect ratio intent: 16:9.
- Audio intent: native sound/dialogue enabled.
- Structure intent: custom multi-shot if the surface supports it.
- Prompt dialect: use API tags such as `<<<element_1>>>` only if required by the target API.
- Do not assume separate `negative_prompt`, CFG, seed, callback, or sound field names without checking the provider schema.
```

If the user names a provider, verify that provider's current API documentation before emitting exact JSON fields.

## Omni Element Readiness

For character/product elements, inspect or ask for coverage when the task depends on identity consistency:

- Front view.
- Three-quarter left.
- Three-quarter right.
- Back or side view.
- Clean product/logo detail if brand/package fidelity matters.
- Clean single-speaker audio or single-character video if binding voice.

If coverage is incomplete, still produce a prompt, but add an audit note:

`Identity consistency risk: only one front-view reference was provided. Add 3/4 and side/back references if Omni element drift appears.`

## Asset Limits To Check

For Kling 3.0 Omni:

- Up to 7 image/element references without video input.
- With a video input, up to 4 image/element references.
- One input video, 3-10 seconds, up to 200 MB, up to 2K.
- Images should be jpg/jpeg/png, at least 300 px on each side, up to 10 MB.

If user exceeds these limits, compress the creative plan by prioritizing:

1. Identity/product anchors.
2. Motion/camera reference.
3. Environment reference.
4. Style reference.
5. Optional mood references.

## Role Conflict Rules

Flag or resolve these conflicts:

- Same image used as both exact first frame and loose style reference.
- Same video used for identity and camera when it contains a different character/product.
- Product reference and desired transformation contradicting exact logo/package preservation.
- More than one subject called "main character" without labels.
- Audio reference requested as both background music and speaker voice without saying which track/voice to use.

When resolving, write:

`I will use @Video1 for camera rhythm only, not character identity.`
