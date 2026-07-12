# Deterministic Review Board Contract

The review board is a human interface, not a model asset.

## Source Rules

- Use only the current independently generated frame for every `shot_uid`.
- Sort by Shot Contract `display_order`, never filename or filesystem order.
- Verify every source `file_sha256` before composition.
- Never crop a board back into individual frames.

## Layout Rules

The default deterministic column count is:

```text
columns = min(5, max(1, ceil(sqrt(N * 16 / 9))))
rows = ceil(N / columns)
```

The caller may freeze another positive column count in the manifest. Once frozen, the same source frames, layout settings, font, dimensions, and tool version must produce the same binary board.

Each cell has an image area and a separate label band. The image is contained without generative extension or crop. The label band may show display order, `shot_uid`, target duration, stage, and version. No label is burned into the independent source frame.

Unused terminal layout slots may be blank but are not cells. `valid_cell_count` is always `N`.

## Required Board Record

```json
{
  "board_type": "deterministic_human_review_composite",
  "is_model_input": false,
  "deterministic": true,
  "valid_cell_count": 3,
  "cell_shot_uids": ["SHT_A", "SHT_B", "SHT_C"],
  "source_frame_hashes": {
    "SHT_A": "<file sha256>",
    "SHT_B": "<file sha256>",
    "SHT_C": "<file sha256>"
  }
}
```

## Model-Facing Rule

Downstream keyframe, previs, and prompt skills receive the independent frames and manifest. They must not use the contact sheet as a substitute merely because it is convenient.
