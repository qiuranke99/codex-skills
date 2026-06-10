---
name: reference-video-product-adapter
description: Use when adapting a reference video into a product-related AI video plan, shot list, storyboard prompt, or video-platform prompt, especially when only reference footage and product materials are available.
---

# Reference Video Product Adapter

## Purpose

Turn a reference video plus product materials into a checked product-video package for AI video generation.

Default flow:

```text
reference video + product pack
-> local_video_ingest when the reference is a local video file
-> reference_breakdown
-> keep/change/avoid
-> product_mapping
-> adaptation_brief
-> shot_list
-> storyboard_panel_spec + storyboard_prompt
-> video_platform_prompt + asset_checklist
```

## When to Use

Use this skill when the user has:

- a reference video, reel, ad, storyboard, or example clip,
- product materials but no full customer brief,
- a request to "make something like this but for my product",
- a need for standardized `shot_list`, `storyboard prompt`, or `AI video platform prompt`.

Do not use it for traditional live-action production budgeting, generic film planning, or pure creative brainstorming without a product adaptation target.

## Required Inputs

Minimum viable input:

- reference video URL, local video path, screenshots, transcript, or written notes,
- product name and category,
- product images, logo, packaging, or product description,
- target duration or platform if known,
- what the user wants to keep from the reference.

If inputs are missing, produce `missing_info_questions.md` first. Do not invent product claims, product features, statistics, brand rules, prices, certifications, or legal claims.

## Resource Map

Load only what is needed:

- Role definitions: `references/role-contracts.md`
- Output package and file contracts: `references/output-contracts.md`
- Reusable prompt blocks: `references/prompt-blocks.md`
- Risk checks: `references/risk-checks.md`
- Schemas: `assets/schemas/*.schema.json`
- Templates: `assets/templates/`
- Local video ingest: `scripts/ingest_local_video.py`
- Validation scripts: `scripts/validate_output_package.py`

## Workflow

### 1. Intake

Create `01-input/reference_video_link.md` and `01-input/product_pack.md` from user materials. Mark each product claim as one of:

```text
provided | inferred | needs_confirmation
```

If there is no usable reference-video evidence, stop and ask for a video link, screenshots, transcript, or manual beat notes.

If the reference is a local video file, run:

```bash
python3 {skill_dir}/scripts/ingest_local_video.py <video_path> <output-package-dir>
```

This creates:

```text
01-input/local-video/video_metadata.json
01-input/local-video/frames/frame_*.jpg
01-input/local-video/contact_sheet.jpg
01-input/local-video/audio.wav
01-input/local-video/local_video_ingest_report.md
```

Do not copy the original client video into the skill or repository. Store only derived analysis assets in the project output package unless the user explicitly asks otherwise.

### 2. Reference Breakdown

Create:

```text
02-analysis/reference_breakdown.md
02-analysis/reference_breakdown.json
```

Break down only observable reference-video properties: duration, beat count, shot rhythm, visual style, scene type, subjects, camera movement, transitions, text, music cues, ending reveal, and any product/brand role in the reference. For local video files, use `local-video/contact_sheet.jpg`, extracted frames, metadata, transcript, and audio notes as evidence.

### 3. Adaptation Boundary

Create:

```text
02-analysis/keep_change_avoid.md
02-analysis/similarity_risk_report.md
```

Separate structure from copying:

- `Keep`: pacing, broad emotional arc, sequence function, general shot type.
- `Change`: characters, product, logo, setting, wording, specific actions, brand assets.
- `Avoid`: exact compositions, original brand marks, original copy, distinctive scene sequence, overly close frame-by-frame reuse.

### 4. Product Mapping

Create:

```text
02-analysis/product_mapping.md
02-analysis/product_mapping.json
```

Map the product into the adapted structure. Every product claim, visual promise, or text cue must link to a source note or be marked `needs_confirmation`.

### 5. Adaptation Brief

Create:

```text
03-brief/adaptation_brief.md
03-brief/adaptation_brief.json
```

The brief is the machine-readable creative handoff for later steps. Use Markdown for human editing and JSON as the workflow source of truth. Export DOCX only when the user needs client-facing delivery.

### 6. Shot List

Create:

```text
04-shot-list/shot_list.md
04-shot-list/shot_list.json
04-shot-list/shot_list.docx
```

Each shot must include: `shot_id`, `duration_sec`, `reference_beat_id`, `visual`, `action`, `camera`, `product_role`, `on_screen_text`, `source_refs`, `ai_video_notes`, and `risk_flags`.

### 7. Storyboard Package

Create:

```text
05-storyboard/storyboard_prompt.md
05-storyboard/storyboard_panel_spec.json
```

Default storyboard mode is one 6 or 9 panel sheet. It is sequence guidance, not a final production board. Use minimal text inside image panels; keep detailed notes in Markdown and JSON.

Required instruction:

```text
Use the storyboard as sequential shot guidance, not as a static collage. Treat each panel as a separate beat in order.
```

### 8. Video Platform Package

Create:

```text
06-video-platform/video_platform_prompt.md
06-video-platform/asset_checklist.md
07-review/feasibility_report.md
07-review/missing_info_questions.md
```

Keep asset roles separate: storyboard controls sequence, product reference controls product identity, character reference controls character identity, and mood reference controls look and lighting.

## Verification

Before claiming the package is ready, run:

```bash
python3 {skill_dir}/scripts/validate_output_package.py <output-package-dir>
```

For skill maintenance, run:

```bash
python3 {skill_dir}/scripts/validate_reference_video_product_adapter.py
python3 -m py_compile {skill_dir}/scripts/*.py
python3 ${CODEX_HOME:-~/.codex}/skills/.system/skill-creator/scripts/quick_validate.py {skill_dir}
```

Replace `{skill_dir}` with the actual skill directory.

## Hard Rules

- Do not treat a reference video as permission to copy exact protected expression.
- Do not invent product benefits, performance claims, awards, certifications, data, or customer promises.
- Do not put long text into generated storyboard images.
- Do not merge product identity, mood, storyboard, and copy into one overloaded prompt if separate references are available.
- Do not present a package as commercially ready until source trace, AI feasibility, similarity risk, and schema checks pass.
