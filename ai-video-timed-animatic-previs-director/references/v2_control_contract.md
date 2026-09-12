# V2 Control Previs Contract

Read only for the `control_previs_v2` branch. These gates do not apply to V1 or
a legitimate single-shot skip. V2 requires approved V1, K1, the exact P1
generation-unit plan, matching K2, and verified provider capability evidence.

## Generation Unit Rules

- Units contain contiguous Shot UIDs in approved order.
- Their ordered union covers the V1 Shot UID list exactly once.
- Unit local time begins at zero; per-shot durations equal V1 and the unit total.
- A unit target duration cannot exceed the verified provider maximum.
- Unit grouping never creates, deletes, merges, splits or renumbers shots.
- Never assume 30-second or 50-reference capability from a preview claim.
- Missing reference-video capability blocks V2; do not downgrade to T2V,
  first/last-frame, or standalone/classic single-image-to-video. Ordinary
  image references inside Omni R2V remain legal.

## Output Declarations

V2 is a silent multimodal control video. Approved keyframes can appear as
dependency-bound anchors; the video may not redefine their identity, geometry,
scene, label or Look.

```json
{
  "model_input_role": "control_reference_video",
  "final_edit_asset": false,
  "silent": true,
  "render_style": "neutral_diagrammatic_or_simple_3d",
  "identity_authority": false,
  "look_authority": false
}
```

## Provider Evidence Gate

`multimodal_reference_video_supported: true` alone is not evidence. Copy a
local hash-bound `provider-runtime-capability-evidence.v1` snapshot into
`input_file_evidence`. Its profile identity, provider/model/surface/backend
binding, generation mode, modalities, effective duration/reference-count limits
and complete `video_input_constraints` must exactly project the P1-selected
provider-runtime profile's `input_constraints.video`.

The projection includes accepted media types, containers and codecs; file-byte,
duration, width, height, aspect-ratio and frame-rate bounds; and audio-track
policy. Read `provider_runtime_capability_evidence.schema.json` when validating
this record; the companion template is an optional starting example, never
proof of current provider support.

Live ffprobe and actual file-byte count must prove each V2 file satisfies every
projected limit as well as the common real-media gate. Absent, unreadable,
stale, incomplete or semantically different capability evidence blocks V2.
A URL-only assertion or self-reported media properties cannot replace it.

## Prior V1 Binding

Bind V2 to immutable older V1 bytes with lower SemVer and the exact K1/P1/K2
locks. Consume P1 as `generation_unit_preflight_plan`, not the legacy
`prompt_preflight_ir` alias. Explicit Canon integration additionally proves
the registry's supersession and stable-slot relationships.
