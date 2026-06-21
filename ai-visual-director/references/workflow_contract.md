# AI Visual Director Workflow Contract

This file is the execution contract for `ai-visual-director`. It keeps the
main `SKILL.md` focused on routing while preserving a strict delivery process.

## 1. Operating Boundary

Use this skill for director-led visual planning, storyboard bitmap images, and
video-generation prompt packs. It is not a generic image prompt writer or a
fixed-grid storyboard template. The skill must produce sequence logic, product/character/
location continuity, reference-role decisions, story-engine evidence, and
validation evidence. The final user-facing output is only storyboard image(s)
and Google Omni video prompts; internal artifacts exist to make those outputs
auditable.

Do not modify project SSOT files or long-term indexes unless the user explicitly
asks. Temporary run artifacts belong in the current run directory.

If the user asks for real-world visual references, gather `source_url` evidence
first. Do not download media unless the user explicitly asks and the source
allows it.

## 2. Required Run Order

1. Intake: identify brief, duration, dimensions, output targets, reference files, and risk.
2. Reference-role analysis: separate product identity, first-frame composition,
   style, lighting, environment, negative, and motion references.
3. Product identity lock: if a real product appears, extract the visual facts
   before route, story, or shot planning.
4. Route decision: run or mirror `scripts/route_project.py`, inferring duration
   and segment seconds from brief text when structured intake is absent.
5. Story engine: define advertising logline, dramatic question, world rule,
   product role, story arc, motion language, duration design, and anti-plastic
   material rules.
6. Creative concept: define big idea, audience desire, story tension, world
   rule, visual mechanism, scene ladder, and signature images. It must derive
   from the story engine, not from a product-angle template.
7. Advanced cinematic-language routing: if `00_route_decision.json` sets
   `cinematic_language_reference_required: true`, read
   `references/cinematic_language_decision_matrix.md` before shot planning.
   If it is false, do not load that reference for ordinary product-ad boards.
8. Mandatory agent activation: follow `AGENTS.md`. Start
   `creative_director_agent`, `director_agent`, `screenwriter_agent`, and
   `art_director_agent`, then record their `completed` entries in
   `02_shot_plan.json.agent_activation_ledger`. If any required agent is
   missing, skipped, simulated, or blocked, do not proceed to concept council or
   shot planning.
9. Internal concept council: creative director proposes creative candidates,
   then director, screenwriter, and art director produce structured vetoes and
   a final `director_resolution` without asking the user to choose unless the
   user explicitly requests an approval checkpoint.
10. Timecoded script map: screenwriter writes the exact-duration script map;
   director approves it before storyboard planning.
11. Shot plan: write `02_shot_plan.json` against
   `references/shot_plan.schema.json`; only here, after director approval, set
   `panel_count`, `panels_per_sheet`, `grid_layouts`, and
   `shots_per_video_segment`.
12. Structure validation: run `scripts/validate_shot_plan.py`.
13. Internal revision: fix validation failures before image generation or video prompts.
14. Storyboard and approved-keyframe planning: for the Google Omni speed path,
    create one dynamic-N bitmap storyboard sheet per executable 10-second
    segment when image generation is available; also prepare mapped source-shot
    ranges or keyframe packets per executable video segment.
15. Google Omni expert activation: start `google_omni_prompt_expert_agent`
    after approved storyboard packets exist. `08_google_omni_video_prompts.json`
    must include completed prompt-expert and director entries in
    `agent_activation_ledger`; without them, video validation fails.
16. Video segment prompts: temporal segments with first/last frame, controlled
    story beats/source shots, camera plan, cut strategy, subject/environment
    motion, motion continuity, product lock, and anti-plastic constraints. Any
    multi-shot segment requires explicit internal shot time spans and
    transitions.
17. Video validation: run `scripts/validate_video_segments.py`; structured video
    JSON is required for a complete run.
18. Final QC: run `scripts/validate_run_package.py` on the run directory.
19. Report only storyboard image path(s), Google Omni prompt path, validation
    status, remaining hard risks, and the minimal segment-usage rule needed to
    prevent misuse of the storyboard sheet as a video input.

The activation ledger is not optional metadata. It is the evidence that the
role gate ran and produced a stage artifact. Validators reject missing,
non-completed, or simulated role entries.

`00_route_decision.json` may include:

- `cinematic_language_reference_required`
- `cinematic_language_triggers`
- `cinematic_language_depth`
- `recommended_references`

Treat these as routing evidence. They do not replace judgment: if the user
explicitly asks for VFX, sound design, camera report, color pipeline, complex
continuity, advanced lens language, or production handoff, read the advanced
reference even if a hand-written route object forgot to set the flag.

## 3. Story Engine Gate

For brief + product image + visual reference work, `story_engine` is mandatory
before shot planning. It is the source of the storyboard and video segment
logic.

Required fields:

- `advertising_logline`: one sentence that sells the idea, not the product category;
- `world_rule`: how this film's world behaves on screen;
- `dramatic_question`: what is withheld, crossed, awakened, transformed, or resolved;
- `dramatic_arc`: beginning, turn, escalation, and resolution;
- `product_role`: how the product becomes inevitable without appearing in every panel;
- `reference_synthesis`: what each supplied reference controls and what it must not control;
- `duration_design`: beat allocation across total seconds, storyboard sheets, and Omni segments;
- `motion_language`: camera and world motion grammar derived from the story engine;
- `anti_plastic_rules`: material truth, tactile imperfections, restraint, and non-gloss constraints.

Reject story engines that can be summarized as `product + petals + glass +
light sweep`, `premium product reveal`, or `beautiful packshot sequence`.

## 4. Creative Concept Gate

For non-catalog product ads, do not begin shot planning until the plan has a
top-level `creative_concept`:

- `big_idea`
- `audience_desire`
- `story_tension`
- `world_rule`
- `visual_mechanism`
- `scene_ladder`
- `signature_images`

This gate exists because product identity and product visibility are not
advertising ideas. A high-end TVC needs sceneable invention: a world, a rule,
and on-screen events that make the product feel inevitable. If the concept is
only `petals`, `glass`, `aura`, `light sweep`, `premium`, or `packshot`, it is
not ready.

Every product-ad shot must also include:

- `scene_arena`
- `scene_role`
- `dramatic_event`
- `visual_mechanism`

The `dramatic_event` must describe what happens in the frame. `light sweeps
across the product`, `product holds`, `ribbon drifts`, or `premium reflection`
are weak unless they cause a reveal, transformation, decision, use action,
benefit metaphor, or final memory image.

## 5. Product Identity Lock

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

The product lock must not collapse the film into repeated product coverage. In
product work, every shot declares `product_visibility`, including shots where
the product is absent. Treat the values as narrative rhythm:

- `not_visible`: origin, world, human response, benefit metaphor, or atmosphere
  with no product, bottle, package, label, logo, or product text in frame;
- `detail_only`: one real component, text area, material, cap, pump, edge, tube,
  relief mark, or label block, not the full package;
- `partial_visible`: cropped, occluded, reflected, silhouetted, or transitional
  product presence;
- `full_visible`: inspection-grade product view with exact visible text,
  component inventory, and forbidden additions locked.

For non-catalog dynamic-N product sheets, scale the rhythm to the actual story:
avoid full-visible packshot walls; use `not_visible` world/benefit shots when
the script needs a world before product authority; use `detail_only` or
`partial_visible` proof shots when they protect identity without repeating the
same full package; and include non-product-led panels when the product identity
lock would otherwise consume every composition. If the user asks for catalog,
listing, e-commerce, SKU, packshot-only, or detail-board work, state that
exception in the `visual_strategy`.

## 6. Storyboard, Approved Keyframe, And Segment Rule

Storyboard panels are script-level shot/cut planning units. They map the edit
rhythm, but they are not generation calls. A 10-second Omni segment can contain
multiple mapped source shots without becoming multiple model calls.

Separate three control layers:

- `dynamic_segment_storyboards`: storyboard sheets whose panel count is
  determined by creative concept, timecoded script map, and director approval;
- `source_shot_ranges` or `approved_keyframe_packets`: model-facing source
  ranges, first/last frames, or multi-keyframe anchors for each executable
  generation segment;
- `temporal_segment_prompts`: concise motion contracts for each generation
  segment.

Storyboard panel count follows the approved script map, not a fixed grid.
`panel_count` equals the intended shot/cut count. For the Google Omni speed
path, `storyboard_sheet_count` equals `video_segment_count`: each 10-second
generation segment receives one dynamic N-panel storyboard sheet and one JSON
temporal prompt. N may differ by segment. Do not turn panels into separate
generations.

For Google Omni/Flow, the executable handoff is the product identity reference,
the visual reference if available, the product identity lock, the segment's
source-shot range, and one temporal segment prompt at a time. For Veo API and
Runway, prefer cleaner single-scene or low-cut segments unless capability is
explicitly available. For Kling or Luma, use structured multi-shot or keyframe
controls when available. If a tool accepts only one image reference, prefer the
product identity reference or the segment's start/end keyframe over a dense
overview sheet.

For other backends, use the backend capability profile instead of assuming the
Omni speed contract. If a backend cannot execute dense multi-shot segments,
reduce the segment's internal shot density or switch to keyframe/shot-level
generation only after a documented failure.

A rough storyboard style is not permission to omit product facts. If a product
faces camera, the sheet prompt must instruct the artist/model to draw the real
product silhouette, component inventory, label placement, and every readable
short text/mark from the product lock. For microtext that cannot be rendered at
thumbnail scale, preserve the real block geometry and any readable primary
mark; never replace it with generic pseudo-text.

Global bans such as `no readable text`, `no logo`, or `no labels` are invalid
unless they explicitly exempt user-provided product packaging marks.

A product storyboard sheet prompt must include a `Product Visibility Rhythm`
block and must repeat `[product_visibility: ...]` in every panel line. For
`not_visible` panels, explicitly forbid product/package/bottle/label/product
text in that panel. For `detail_only` panels, say which real component or
surface detail appears and forbid the full package. For `partial_visible`
panels, state the crop, occlusion, reflection, or reveal mechanism. Only
`full_visible` panels carry the full visible text inventory.

It must also include `Creative Concept`, `World Rule`, `Scene Ladder`, and
`Visual Mechanism` blocks, then repeat `[scene_arena: ...]`,
`[scene_role: ...]`, `[dramatic_event: ...]`, and `[visual_mechanism: ...]` in
every panel line. These fields are not captions for the final image; they are
directional constraints that prevent the sheet from becoming a repeated product
detail board.

## 7. Video Segment Rule

Video prompts may use camera orbit, pan, push-in, reveal, parallax, foreground
occlusion, light sweeps, mist, petals, liquid, or environment motion. Those
motions are allowed when they do not mutate product facts.

A product must not be rebuilt from atmosphere, simplified into a generic object,
or given invented labels or hardware. If the product changes angle, the lock
still governs the visible faces and components.

Each segment must be a concise motion contract, not a storyboard transcription:

- multi-shot segments must include `internal_shots` with shot IDs, time spans,
  camera states, transitions, and purposes;
- first frame and last frame must differ;
- `camera_plan` must name a physical camera state or movement;
- `cut_strategy` must say whether the segment is one continuous move, a hidden
  transition, or a small beat sequence;
- `subject_motion`, `environment_motion`, and `motion_continuity` must state
  what changes over time;
- `anti_plastic_constraints` must specify material, lens, light, shadow,
  texture, or physical-detail behavior.

Do not paste the entire storyboard contact sheet into one 10-second prompt. Use
only the mapped source-shot range for that segment.

Do not use the storyboard sheet as the sole reference image for a product video
segment when a product identity reference is available. The product reference
outranks the storyboard sheet. Use the storyboard sheet only as optional visual
planning context, and only together with the product identity lock and the
selected temporal segment prompt.

## 8. Required Run Directory

Use these canonical artifact names when producing a complete run:

```text
00_route_decision.json
01_reference_roles.md
02_shot_plan.json
03_director_qc.json
04_storyboard_image_prompts.md
05_agent_orchestration.json
storyboard_sheet_01.png
storyboard_sheet_02.png  # only when route asks for a second sheet
08_google_omni_video_prompts.md
08_google_omni_video_prompts.json
09_final_qc_report.md
10_run_package_validation.json
11_video_generation_handoff.md
approved_keyframe_packets/  # required for production_handoff/certification
```

Bitmap storyboard sheets are optional only when image generation cannot run in
the current environment. The prompt trace, plan, video JSON, and QC artifacts
are still required internally, but the final user-facing answer must not list
them as deliverables unless validation fails or the user asks for internals.

## 9. Failure Handling

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
