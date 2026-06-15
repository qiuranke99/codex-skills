# AI Visual Director Workflow Contract

This file is the execution contract for `ai-visual-director`. It keeps the
main `SKILL.md` focused on routing while preserving a strict delivery process.

## 1. Operating Boundary

Use this skill for director-led visual planning, storyboard sheets, image
prompts, and video-generation prompt packs. It is not a generic image prompt
writer. The skill must produce sequence logic, product/character/location
continuity, reference-role decisions, and validation evidence.

Do not modify project SSOT files or long-term indexes unless the user explicitly
asks. Temporary run artifacts belong in the current run directory.

If the user asks for real-world visual references, gather `source_url` evidence
first. Do not download media unless the user explicitly asks and the source
allows it.

## 2. Required Run Order

1. Intake: identify brief, duration, output targets, reference files, and risk.
2. Reference-role analysis: separate product identity, first-frame composition,
   style, lighting, environment, negative, and motion references.
3. Product identity lock: if a real product appears, extract the visual facts
   before shot planning.
4. Route decision: run or mirror `scripts/route_project.py`.
5. Advanced cinematic-language routing: if `00_route_decision.json` sets
   `cinematic_language_reference_required: true`, read
   `references/cinematic_language_decision_matrix.md` before shot planning.
   If it is false, do not load that reference for ordinary product-ad boards.
6. Shot plan: write `02_shot_plan.json` against `references/shot_plan.schema.json`.
7. Structure validation: run `scripts/validate_shot_plan.py`.
8. Internal revision: fix validation failures before image prompts.
9. Storyboard image prompts: one prompt per 3x3 sheet.
10. Video segment prompts: 10-second temporal segments with first/last frame and
   motion over time.
11. Video validation: run `scripts/validate_video_segments.py` when structured
    video JSON is produced.
12. Final QC: run `scripts/validate_run_package.py` on the run directory.
13. Report artifact paths and remaining risks.

`00_route_decision.json` may include:

- `cinematic_language_reference_required`
- `cinematic_language_triggers`
- `cinematic_language_depth`
- `recommended_references`

Treat these as routing evidence. They do not replace judgment: if the user
explicitly asks for VFX, sound design, camera report, color pipeline, complex
continuity, advanced lens language, or production handoff, read the advanced
reference even if a hand-written route object forgot to set the flag.

## 3. Product Identity Lock

When the user provides a product image, product packaging is identity. It is not
decorative style. A shot, storyboard sheet, or video prompt that omits or
changes visible product facts is a failure even if the mood, lighting, and
camera language are strong.

The top-level `product_identity_lock` must include:

- `source_reference`
- `product_name_text`
- `primary_label_text`
- `surface_text_inventory`
- `embossed_or_relief_marks`
- `label_layout`
- `packaging_shape`
- `physical_component_inventory`
- `color_material_marks`
- `required_visible_marks`
- `forbidden_changes`
- `forbidden_visual_additions`
- `full_view_fidelity_rule`

For every product-visible shot, include:

- `product_visibility`
- `product_identity_action`

For every `full_visible` product shot, also include:

- `visible_product_text_or_marks`
- `product_visual_facts`
- `forbidden_visual_additions`

Full-visible means the product is readable enough that the storyboard artist or
image/video system can inspect the package. In those shots, carry the exact
visible text, logo/wordmark, label blocks, embossed/debossed marks, cap/pump,
component inventory, material/color bands, and real proportions. If the
reference text is unreadable, write `unreadable_from_reference`, preserve the
label geometry, and do not invent replacement copy.

Forbidden additions are physical or graphic facts not present in the reference:
metal plates, front plaques, badges, extra emblems, new label panels, claims,
certification icons, extra bottles, changed caps, changed pumps, changed
materials, or altered product shape.

## 4. Storyboard Sheet Rule

A rough storyboard style is not permission to omit product facts. If a product
faces camera, the sheet prompt must instruct the artist/model to draw the real
product silhouette, component inventory, label placement, and every readable
short text/mark from the product lock. For microtext that cannot be rendered at
thumbnail scale, preserve the real block geometry and any readable primary
mark; never replace it with generic pseudo-text.

Global bans such as `no readable text`, `no logo`, or `no labels` are invalid
unless they explicitly exempt user-provided product packaging marks.

## 5. Video Segment Rule

Video prompts may use camera orbit, pan, push-in, reveal, parallax, foreground
occlusion, light sweeps, mist, petals, liquid, or environment motion. Those
motions are allowed when they do not mutate product facts.

A product must not be rebuilt from atmosphere, simplified into a generic object,
or given invented labels or hardware. If the product changes angle, the lock
still governs the visible faces and components.

## 6. Required Run Directory

Use these canonical artifact names when producing a complete run:

```text
00_route_decision.json
01_reference_roles.md
02_shot_plan.json
03_director_qc.json
04_storyboard_image_prompts.md
storyboard_sheet_01.png
storyboard_sheet_02.png
08_google_omni_video_prompts.md
08_google_omni_video_prompts.json
09_final_qc_report.md
10_run_package_validation.json
```

Bitmap storyboard sheets are optional only when image generation is not
requested or cannot run in the current environment. The prompt, plan, video, and
QC artifacts are still required.

## 7. Failure Handling

Do not hide failures in prose. If validation fails, revise the artifact and run
the validator again. If exact product facts are impossible because the reference
is blurry, say which fields are `unreadable_from_reference`, preserve geometry,
and ask for a clearer product image only when exact text accuracy is required.

When the final delivery includes a product, the final QC must explicitly state
whether the product lock was validated for:

- exact visible text/marks
- label layout
- product shape and proportions
- cap/pump/closure
- real physical components
- forbidden visual additions
- storyboard prompt carry-through
- video prompt carry-through
