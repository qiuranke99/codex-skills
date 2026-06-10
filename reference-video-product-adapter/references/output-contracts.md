# Output Contracts

## Package Layout

```text
project-name/
  01-input/
    reference_video_link.md
    product_pack.md
    local-video/
      video_metadata.json
      frames/
      contact_sheet.jpg
      audio.wav
      local_video_ingest_report.md
  02-analysis/
    reference_breakdown.md
    reference_breakdown.json
    keep_change_avoid.md
    similarity_risk_report.md
    product_mapping.md
    product_mapping.json
  03-brief/
    adaptation_brief.md
    adaptation_brief.json
  04-shot-list/
    shot_list.md
    shot_list.json
    shot_list.docx
  05-storyboard/
    storyboard_prompt.md
    storyboard_panel_spec.json
  06-video-platform/
    video_platform_prompt.md
    asset_checklist.md
  07-review/
    feasibility_report.md
    missing_info_questions.md
```

## Source Status Values

Use exactly:

```text
provided
inferred
needs_confirmation
not_applicable
```

## Risk Flag Values

Use one or more:

```text
product_identity
logo_accuracy
text_rendering
unsupported_claim
similarity_risk
too_many_scene_changes
too_many_characters
duration_pressure
reference_dependency
none
```

## Shot List DOCX

The DOCX is an export of `shot_list.json`, not the workflow source of truth. Generate it with:

```bash
python3 {skill_dir}/scripts/create_shot_list_docx.py shot_list.json shot_list.docx
```

## Local Video Ingest

When the reference is a local video file, create ingest assets with:

```bash
python3 {skill_dir}/scripts/ingest_local_video.py <video_path> <output-package-dir>
```

The original video should stay outside the output package unless the user explicitly asks to copy it. The ingest folder contains metadata, extracted frames, a contact sheet, and optionally audio for transcription.

## Commercial Readiness Gate

A package can be called ready only when:

- all required JSON files parse,
- local video metadata parses when `01-input/local-video/video_metadata.json` exists,
- required fields are present,
- `shot_list` has 3 to 12 shots,
- every shot has at least one `source_refs` entry,
- `storyboard_panel_spec` maps panels to valid shots,
- `video_platform_prompt.md` contains the sequential guidance instruction,
- feasibility and similarity reports exist,
- no product claim is silently unsupported.
