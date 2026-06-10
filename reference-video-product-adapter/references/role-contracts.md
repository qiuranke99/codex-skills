# Role Contracts

Use these as role nodes inside one Codex skill. They are not separate autonomous agents unless the user explicitly asks for parallel agents.

## Local Video Ingest Agent

Input:

- local video file path such as `.mp4`, `.mov`, `.m4v`, or `.webm`
- output package directory

Output:

- `01-input/local-video/video_metadata.json`
- `01-input/local-video/frames/frame_*.jpg`
- `01-input/local-video/contact_sheet.jpg`
- `01-input/local-video/audio.wav` when audio exists and extraction succeeds
- `01-input/local-video/local_video_ingest_report.md`

Rules:

- Use `ffprobe` for metadata and `ffmpeg` for frame/audio extraction.
- Do not copy the original video into the output package.
- If `ffmpeg` or `ffprobe` is unavailable, stop with a dependency message.
- Extract frames for analysis, not final creative assets.
- Treat extracted frames as reference evidence; they do not authorize copying exact compositions.

Required fields in `video_metadata.json`:

- `source_video`
- `duration_sec`
- `width`
- `height`
- `fps`
- `video_codec`
- `audio_codec`
- `extracted_frames`
- `contact_sheet`
- `audio_path`

## Reference Video Analyst

Input:

- reference video URL, local-video ingest outputs, screenshots, transcript, or manual notes

Output:

- `reference_breakdown.md`
- `reference_breakdown.json`

Rules:

- Record only observable evidence.
- Separate shot-level facts from interpretation.
- Mark uncertain timing or camera motion as `estimated`.
- Do not infer product claims from the reference unless the reference itself contains them.
- For local video, cite frame filenames or timestamp ranges when possible.

Required fields:

- `reference_id`
- `duration_sec`
- `beats`
- `style_notes`
- `music_or_rhythm_notes`
- `text_or_logo_notes`

## Adaptation Boundary Agent

Input:

- `reference_breakdown`
- product pack

Output:

- `keep_change_avoid.md`
- `similarity_risk_report.md`

Rules:

- Keep abstract structure, pacing, and broad shot function.
- Change protected expression: characters, brand assets, wording, exact compositions, specific scene sequence.
- Flag high similarity risk when more than three consecutive beats preserve the same subject, action, composition, and timing.

## Product Mapping Agent

Input:

- product pack
- `keep_change_avoid`
- `reference_breakdown`

Output:

- `product_mapping.md`
- `product_mapping.json`

Rules:

- Each product claim must include `source_refs`.
- If no source exists, set `claim_status` to `needs_confirmation`.
- Product/logo/text accuracy is a risk area; prefer references over generated text.

## Adaptation Brief Agent

Input:

- `product_mapping`
- `keep_change_avoid`
- product pack

Output:

- `adaptation_brief.md`
- `adaptation_brief.json`

Rules:

- The brief is not a client claim source; it is a handoff built from traced inputs.
- Include `must_show`, `must_avoid`, `tone`, `target_duration_sec`, `reference_strategy`, and `open_questions`.

## Shot List Agent

Input:

- `adaptation_brief`
- `product_mapping`
- `reference_breakdown`

Output:

- `shot_list.md`
- `shot_list.json`
- `shot_list.docx`

Rules:

- Every shot must link to a `reference_beat_id`.
- Every product assertion must link to `source_refs` or be marked `needs_confirmation`.
- Prefer 6 to 9 shots for short AI video generation unless the user asks otherwise.
- Avoid exact reference-video compositions; adapt shot function instead.

Shot fields:

- `shot_id`
- `duration_sec`
- `reference_beat_id`
- `shot_size`
- `visual`
- `action`
- `camera`
- `product_role`
- `on_screen_text`
- `source_refs`
- `ai_video_notes`
- `risk_flags`

## Storyboard Agent

Input:

- `shot_list`
- product visual references
- mood/look references if available

Output:

- `storyboard_prompt.md`
- `storyboard_panel_spec.json`

Rules:

- One panel maps to one shot or beat.
- Keep image text minimal: panel number, maybe one short label.
- Do not ask the image model to render long copy, legal text, exact package text, or QR codes.
- Include: "Use the storyboard as sequential shot guidance, not as a static collage."

## Video Prompt Agent

Input:

- `shot_list`
- `storyboard_panel_spec`
- product, character, and mood references

Output:

- `video_platform_prompt.md`
- `asset_checklist.md`

Rules:

- State the role of each input asset.
- Keep product identity and logo accuracy as explicit constraints.
- Include text safety: no random subtitles, no invented brand text, no changed logo.

## Checker Node

Run after Product Mapping, Shot List, Storyboard, and Video Prompt:

- Source Trace Checker
- AI Video Feasibility Checker
- Similarity Risk Checker
- Schema Validator
