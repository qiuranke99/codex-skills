---
name: ai-visual-director
description: >-
  Use when Codex needs to automate AI visual direction from reference images, image folders, keywords, campaign/product/story briefs, or duration into director-led deliverables: reference-role analysis, route decisions, 9-panel/3x3 blue-gray hand-drawn storyboard sheets, imagegen prompts/images, and Google omni 10s-per-segment video generation prompts. Trigger for requests mentioning 9宫格, 故事板, 分镜, 蓝灰手绘稿, storyboard, shot list, director thinking, imagegen, Google omni video prompts, product ads, visual ads, or converting reference images plus keywords into storyboard/video prompts.
---

# AI Visual Director

## Core Rule

Do not solve these tasks with one long prompt. Run a staged director workflow:

1. intake and reference-role analysis
2. route decision from the director kernel: project type, duration logic, sheet count, panel count, video segment count
3. director brief: dramatic arc, visual motif, continuity locks, failure modes
4. shot plan: concrete shot specs for every panel
5. lightweight automated production gate, not multi-review
6. Shadow Observer sidecar event logging for non-blocking skill learning
7. one imagegen prompt per 3x3 storyboard sheet
8. Google omni prompts in 10s temporal segments
9. final QC summary and saved artifact paths

If the user provides only images and short keywords, infer the missing structure. Ask only when a missing fact materially changes the route, such as unknown product identity, unknown target duration, or conflicting reference roles.

## Reference Files

Load only what is needed:

- For shot-spec fields and handoff grammar, read `references/shot_spec_template.md`.
- For production-mode routing, escalation triggers, and director playbooks, read `references/director_kernel.md`.
- For world-class TVC principles, attention choreography, reference parity, and image-to-shot translation, read `references/world_class_tvc_principles.md`.
- For non-blocking observer sidecar behavior and learning-loop rules, read `references/observer_protocol.md`.
- For examples of non-generic shot progression, read `references/good_shotlist_examples.md`.
- For the blue-gray previs sketch visual target, read `references/blue_gray_previs_style_bible.md` and inspect `assets/blue_gray_previs_reference.jpeg` when visual drift is likely.
- For structured data contracts, read `references/shot_plan.schema.json`, `references/video_segments.schema.json`, `references/audit.schema.json`, `references/observer_event.schema.json`, and `references/rule_candidate.schema.json`.

The blue-gray style is a sketch grammar, not a beauty finish. Preserve camera logic, shot size, camera height, foreground/midground/background, scale proof, and continuity before style polish.

## Reference Parity Contract

When the user supplies world-class reference images, do not copy surface style blindly. Extract and preserve the reference's visual DNA:

- subject hierarchy: what dominates first, second, third
- camera relation: height, distance, angle, lens feel, compression, intimacy
- depth architecture: foreground blockers, midground subject, background geometry
- light logic: direction, hardness, contrast, reflective highlights, negative fill
- material language: glass, metal, skin, liquid, fabric, product surfaces
- color/tone structure: contrast, saturation, dominant and accent values
- motion implication: where the eye travels and what movement the frame suggests
- restraint: what the reference deliberately leaves empty or unresolved

Every shot plan must include reference parity decisions. If a generated 9-panel sheet only resembles the reference by keywords but not by hierarchy, depth, light, material, or visual restraint, treat it as failure.

## Product Identity Fidelity Contract

When the user supplies a real product image, package photo, packshot, label reference, or product-identity reference, treat the packaging as identity, not decoration. Do not simplify a real product into a blank bottle, generic jar, invented brand, or approximate label.

Before shot planning, extract a `product_identity_lock`:

```json
{
  "source_reference": "user product image or file path",
  "product_name_text": "exact visible product/brand text, or unreadable_from_reference",
  "primary_label_text": ["exact short label lines visible on the package"],
  "surface_text_inventory": ["all visible printed, engraved, embossed, debossed, relief, logo, wordmark, and volume marks"],
  "embossed_or_relief_marks": ["raised/debossed marks visible in the reference, or none_visible"],
  "label_layout": "where the label, wordmark, icon, color bands, and claims sit on the package",
  "packaging_shape": "bottle/jar/tube/box silhouette, cap/pump/closure, proportions",
  "physical_component_inventory": ["only real visible parts: body, cap, pump, collar, tube, label panel, box flap, etc."],
  "color_material_marks": "body color, label color, material, finish, transparent/opaque areas",
  "required_visible_marks": ["marks that must appear whenever the product faces camera"],
  "forbidden_changes": ["blank package", "fake logo", "new text", "changed label layout"],
  "forbidden_visual_additions": ["components not present in the product reference, such as metal plates, badges, plaques, extra labels"],
  "full_view_fidelity_rule": "when product_visibility is full_visible, show the exact text/mark inventory and physical component inventory; do not omit, misspell, or add parts"
}
```

If the product reference is too blurry to read exact text, write `unreadable_from_reference` and preserve the visible label geometry. Ask for a clearer product reference only when exact label accuracy is materially required by the user or final deliverable. Never invent missing brand text, claims, ingredient names, certification icons, or legal copy.

The global no-text rule has a narrow exception: user-provided product packaging text, labels, logos, marks, and label blocks must be preserved when the product is visible. Captions, shot numbers, handwritten notes, callouts, UI overlays, fake signage, and invented labels remain forbidden.

Do not confuse product fidelity with conservative motion. Camera orbit, hero reveal, rotation, rise, cap action, or other shot-language choices are allowed when they serve the sequence. They become failures only if they change the real product's visible facts: wrong or missing text, wrong embossing/relief, wrong label layout, invented metal plate/badge/plaque, extra hardware, changed material, wrong cap/pump/closure, duplicate packaging, or a generic substitute.

## Intake Contract

Normalize user input into an intake object before planning:

```json
{
  "brief": "short user keywords or campaign/story brief",
  "duration_seconds": 40,
  "reference_images": [
    {"path": "optional local path or attachment label", "role_hint": "optional"}
  ],
  "output_targets": ["storyboard_sheets", "google_omni_prompts"],
  "video_segment_seconds": 10,
  "observer_mode": "auto"
}
```

For every image, assign a role:

- `product_identity`
- `character_identity`
- `ingredient_or_motif`
- `environment_or_material_language`
- `style_reference`
- `first_frame_or_composition`
- `negative_reference`

Conflict priority:

1. explicit user requirement
2. first-frame composition or camera
3. character identity
4. product or prop structure
5. location continuity
6. style reference

## Route Decision

Use `scripts/route_project.py` when the input can be represented as JSON. Otherwise apply the same logic manually.

Default timing:

- storyboard sheet count = `ceil(duration_seconds / 13.5)`, minimum 1
- panel count = `storyboard_sheet_count * 9`
- video segment count = `ceil(duration_seconds / video_segment_seconds)`
- default video segment length = 10s

Do not equate one storyboard sheet with one video segment. For example, a 40s ad normally becomes 3 storyboard sheets / 27 panels and 4 Google omni prompts / 10s each.

Route by intent:

- `premium_product_ad`: origin, product reveal, texture/material proof, use action, benefit visualization, packshot payoff
- `beauty_or_fashion`: identity, tactile detail, transformation, motion/pose language, beauty payoff
- `narrative_or_surreal`: baseline, anomaly/reveal, scale or stakes proof, reaction, consequence, emotional payoff
- `food_or_beverage`: ingredient origin, preparation action, texture proof, serving context, appetite payoff
- `architecture_or_space`: spatial establish, material detail, human scale, circulation, hero reveal
- `tech_or_science`: problem, mechanism, proof visualization, human use, clean payoff

## Production Modes

Default to `standard_fast`, not audit-heavy.

- `standard_fast` (default): one route decision, one complete shot plan, one automated structure gate, automatic internal revision if the gate fails, then storyboard prompts and video prompts.
- `rush`: same as `standard_fast` but skip optional route variants and keep only required deliverables; use when the user explicitly prioritizes speed.
- `premium_pitch`: create two route/shot-plan variants and keep the stronger one; use only when the user asks for multiple directions, major campaign options, or high-budget pitch material.
- `certification`: run the full audit and benchmark flow; use when updating the skill, publishing a new package, building a portfolio benchmark, or when the user explicitly asks for audit/scoring.

Do not run multi-role review, weighted scoring, or variant tournament on every normal commercial output. Commercial scalability comes from a strong default route kernel plus fast automatic gates, not from human-like review loops on every job.

Escalate from `standard_fast` only when one of these is true:

- reference images conflict about product, person, location, or first-frame composition
- target duration, output format, or intended channel is missing and materially changes the structure
- user asks for brand imitation, regulated claims, medical/financial/legal substantiation, celebrity likeness, or a real high-budget campaign
- automated structure gate fails twice
- generated image visibly breaks product/character identity, panel separation, or the blue-gray storyboard style

## Shot Planning Rules

Every panel must become a shot spec with the fields from `references/shot_spec_template.md`. At minimum include:

```yaml
SH_001
aspect_ratio:
scene:
duration:
shot_purpose:
shot_size:
camera_angle:
lens_feel:
camera_movement:
cut_logic:
attention_order:
eye_trace:
depth_strategy:
reference_parity:
product_visibility:
product_identity_action:
main_subject:
main_action:
body_pose:
composition:
foreground:
midground:
background:
scale_reference:
continuity_lock:
must_preserve:
avoid:
```

Do not write vague camera language. Replace "cinematic", "premium", "beautiful", "high-end", "高级", "电影感", or "奢华" with visible decisions: camera height, subject scale, movement direction, foreground/midground/background, action, cut logic, and scale proof.

`attention_order` must say what the viewer sees first, second, and third. `eye_trace` must say where the viewer's gaze enters and exits the frame, and how that sets up the next cut. `depth_strategy` must explain the foreground/midground/background relation or why the shot is intentionally flat. `reference_parity` must name which reference image qualities are being preserved and which are intentionally ignored.

For product work, `product_visibility` must be one of `full_visible`, `partial_visible`, `detail_only`, or `not_visible`. Any shot where the product is visible must use `product_identity_action` to say exactly how the locked package shape, front/back label, product text, wordmark, logo/mark, color bands, cap/pump, and proportions are preserved in that panel. `must_preserve` must repeat the relevant visible package marks; do not write only `same product`.

## Director QC Gate

Before calling imagegen, the shot plan must pass these checks. If it fails, revise the shot plan first.

Per 3x3 sheet:

- exactly 9 shots
- at least 5 distinct shot-size/camera-scale choices
- at least 4 distinct camera-angle choices
- at least 3 distinct movement states, including at least one motivated move
- at least one establishing/world shot
- at least two macro/insert/detail shots
- at least one high-angle, low-angle, top, overhead, or ground-level shot
- every shot has foreground, midground, and background unless it is a justified extreme macro
- every shot has an attention order, eye trace, depth strategy, and reference parity note
- no run of 3 consecutive centered static shots
- no panel exists only to "look premium"; every panel has a shot purpose

For product ads, also require product identity, material proof, texture proof, use action, benefit metaphor, and final packshot across the sequence.

For any product ad or product-identity reference, also require:

- a complete top-level `product_identity_lock`
- `product_visibility` and `product_identity_action` on every product shot
- visible product panels preserve supplied package text/label/logo/mark/layout rather than blanking or inventing them
- `avoid` forbids fake logos, fake claims, blank generic packaging, changed label layout, extra bottles, and wrong cap/pump/closure
- no storyboard prompt may use a broad `no readable text/no logos/no labels` ban unless it explicitly exempts user-provided product packaging marks

For narrative/surreal work, also require normal baseline, reveal, scale/stakes proof, reaction, and payoff.

When a JSON shot plan is available, run:

```bash
python .agents/skills/ai-visual-director/scripts/validate_shot_plan.py <shot_plan.json>
```

Treat validator warnings as serious creative-review notes. Treat errors as blockers.

## Shadow Observer

When this skill enters a workflow, start a non-blocking Shadow Observer sidecar. The observer is a fact recorder and candidate-rule generator, not a second director, quality gate, or hidden audit loop.

Default `observer_mode` is `auto`:

- start exactly one read-only Shadow Observer sub-agent when sub-agent tools are available;
- record existing artifacts and lightweight QC facts;
- ingest validator errors and warnings;
- capture user corrections that reveal missing rules;
- propose candidate rules only when failures are repeated, severe, or explicitly confirmed by the user;
- continue the main workflow even if the observer fails, times out, or returns invalid data.

Sub-agent launch contract:

- Launch the observer after intake and route decision exist, or after the first draft `03_shot_plan.json` exists if route data is not yet persisted.
- Give it only `_observer/events.jsonl`, `_observer/observer_packet.md`, and candidate-rule context, not the full conversation or unrelated workspace files.
- Ask it to monitor workflow behavior and propose testable rule candidates, not to judge taste or re-direct the work.
- Do not wait for it in `standard_fast`; continue imagegen, video prompts, and final delivery.
- If sub-agent tools are unavailable, create `_observer/events.jsonl` and `_observer/observer_packet.md` as the fallback handoff artifact.

Do not trigger an extra LLM creative review in normal `standard_fast` production. The sub-agent must remain read-only, must not call image generation, must not edit deliverables, and must not block imagegen or final delivery.

Record observer events under:

```text
outputs/<date>_<slug>/_observer/events.jsonl
```

Useful stages:

- `intake`
- `route`
- `shot_plan`
- `structure_gate`
- `storyboard_prompt`
- `post_image_qc`
- `video_prompt`
- `final_qc`

Use the event schema in `references/observer_event.schema.json`. Use the candidate schema in `references/rule_candidate.schema.json`.

Record facts with:

```bash
python .agents/skills/ai-visual-director/scripts/observe_run.py append --run-dir outputs/<date>_<slug> --stage route --artifact 02_director_brief.json --event-type artifact_recorded
python .agents/skills/ai-visual-director/scripts/observe_run.py ingest-validator --run-dir outputs/<date>_<slug> --validator-result outputs/<date>_<slug>/validator.json
python .agents/skills/ai-visual-director/scripts/observe_run.py propose-rules --events outputs/<date>_<slug>/_observer/events.jsonl --out outputs/<date>_<slug>/_observer/candidate_rules.json
python .agents/skills/ai-visual-director/scripts/create_observer_packet.py outputs/<date>_<slug>
```

Default observer failures are non-blocking. Use `--strict` only for package verification or certification diagnostics.

Common failure codes:

- routing: `route_misclass`, `duration_defaulted`, `escalation_trigger_missed`, `reference_role_conflict`
- shot plan: `insufficient_camera_variety`, `weak_attention_order`, `missing_depth_layers`, `unmotivated_movement`, `generic_premium_language`, `scale_unproven`
- prompt/image: `photoreal_drift`, `anime_manga_drift`, `readable_text`, `panel_separation_failure`, `identity_drift`, `wrong_camera_angle`, `repeated_centered_composition`
- video: `static_panel_dump`, `missing_first_last_frame`, `segment_continuity_break`, `motion_not_motivated`

Rule promotion criteria:

- the same failure code appears in at least 3 observer events across runs;
- one severe post-image blocker threatens product identity, character identity, legal safety, or deliverable correctness;
- the user explicitly confirms that a finding should become a durable rule;
- a certification run shows a benchmark regression.

Even then, the observer only creates a proposal. A rule can enter `SKILL.md`, validators, schemas, or prompt templates only after an explicit skill-improvement pass or SSOT acceptance.

## Offline Audit And Skill Certification

Do not run this on every normal job. Use it to improve and certify the skill itself, or when the user explicitly asks for audit/scoring.

For certification runs, use this loop:

1. **Automated structure gate:** run `validate_shot_plan.py` on `03_shot_plan.json`.
2. **Director review:** score narrative arc, shot purpose, camera motivation, edit rhythm, and emotional/product payoff.
3. **DP review:** score camera height, lens feel, depth layers, lighting logic, scale proof, and composition variety.
4. **Continuity review:** score reference-role accuracy, product/character/location consistency, motif discipline, and avoid-list enforcement.
5. **Video director review:** score first-frame/last-frame logic, motion over time, temporal escalation, and Google omni segment continuity.
6. **Adversarial review:** write the strongest case that the output is generic, non-commercial, visually repetitive, or not world-class; revise if the critique identifies a real failure.
7. **Variant tournament for high-stakes work:** create at least two route/shot-plan variants, score both, keep the higher-scoring plan, and preserve the rejected plan in the audit log.
8. **Post-image visual review:** after imagegen, inspect every sheet for style drift, readable text, panel separation, camera readability, identity drift, and repeated compositions.

Use `references/audit.schema.json` for the audit object. Score with:

```bash
python .agents/skills/ai-visual-director/scripts/score_audit.py <audit.json>
```

Skill-certification rule:

- `fail`: any blocker, total score below 75, or any critical dimension below 3/5
- `revise`: 75-84.99, or unresolved serious warnings
- `commercial_candidate`: 85-91.99, no blockers, all critical dimensions at least 4/5
- `world_class_candidate`: at least 92, no blockers, all critical dimensions at least 4.5/5, at least two review rounds, and at least one adversarial review

This certifies the skill version or a benchmark output, not every future job. "World-class" is a candidate label, not a guarantee. Routine production should use `standard_fast` and only escalate on red flags.

## Storyboard Image Generation

Use the built-in imagegen path for final bitmap generation. Generate one image per sheet, not all sheets in a single imagegen call.

Each sheet prompt must contain:

- 3x3 separate-panel layout
- sheet number and total sheet count
- global continuity locks
- product_identity_lock when a product appears
- the 9 panel-specific shot specs, compressed but concrete
- blue-gray previs sketch style lock
- negative constraints: no captions, no shot numbers, no unrelated readable text, no invented labels/logos/claims, no photorealism, no anime/manga, no polished illustration

When a user product appears in a storyboard sheet, the sheet prompt must explicitly say: preserve the exact user-provided product silhouette, cap/pump/closure, label placement, visible product text, logo/mark, color bands, and package proportions; draw exact supplied short label text when legible in the reference; do not invent missing text. If product text is too small for rough storyboard readability, draw the correct label blocks and the supplied primary wordmark/short text at the product-facing scale rather than leaving the package blank.

Use this style lock:

```text
rough hand-drawn production storyboard sheet, animatic previs sketch, director's working storyboard thumbnails, loose black pencil linework, dark graphite searching lines, visible construction lines, very light blue-gray storyboard wash, sparse tonal blocks, clean white paper background, simplified faceless characters when people appear, sparse cinematic environment detail, linework primary, wash secondary
```

After generation, inspect the image. Reject and regenerate if the sheet has readable text outside user-provided product packaging, photoreal finish, repeated centered compositions, missing panel separation, inconsistent product/character identity, or unclear camera angles.

## Google Omni Video Prompts

Create video prompts by temporal segment, not by storyboard sheet.

For any product video, start the prompt file with a `Required Reference Setup` and `Product Identity Lock` before the segments. The user's product original, packshot, or multi-angle product image is the highest-priority `product_identity` reference; style references may affect lighting, environment, camera mood, props, rhythm, and lens language, but must not change bottle/package geometry, cap/pump/closure, label layout, visible text/logo/mark, embossed or relief marks, color bands, materials, proportions, or real component inventory.

Carry the same `product_identity_lock` from the shot plan into the video prompt JSON. Product-visible segments must include `product_visibility`, `product_identity_reference`, and `product_motion_rule`. Full-product views must also include `visible_product_text_or_marks`, `product_visual_facts`, and `forbidden_visual_additions`.

For full-visible product shots, write the product as an inspected artifact, not a mood object: repeat the exact visible text/wordmark/logo/embossing inventory from the reference, repeat the actual physical component inventory, and explicitly forbid absent high-risk additions. If the real bottle has no metal plate, badge, plaque, or extra label panel, say so. If the real product has raised or engraved text, name it. If exact microtext is unreadable, preserve the correct location/geometry and any readable primary mark; never substitute a new phrase.

When a segment is pasted into Google Omni, include the `Required Reference Setup`, the full `Product Identity Lock`, and the selected segment together. A segment without the lock is underspecified and may drift into a generic mood object.

For each 10s segment:

```yaml
SEG_01_0s_10s
purpose:
source_shots:
product_visibility:
product_identity_reference:
product_motion_rule:
visible_product_text_or_marks:
product_visual_facts:
forbidden_visual_additions:
first_frame:
last_frame:
camera_plan:
subject_motion:
environment_motion:
continuity_lock:
visual_style:
negative_constraints:
```

Write the segment as motion direction over time. Include first frame, last frame, camera movement, subject motion, and continuity locks. Do not paste nine static panel descriptions as a video prompt.

## Required Final Deliverables

For a full run, save:

```text
outputs/<date>_<slug>/
  00_input_manifest.json
  01_reference_roles.md
  02_director_brief.json
  03_shot_plan.json
  04_storyboard_image_prompts.md
  storyboard_sheet_01.png
  storyboard_sheet_02.png
  ...
  08_google_omni_video_prompts.md
  09_qc_report.md
  _observer/events.jsonl  # optional non-blocking sidecar
  _observer/candidate_rules.json  # optional proposals, not accepted rules
  _observer/observer_packet.md  # optional only for sub-agent or SSOT review handoff
```

Only certification or explicit audit runs need:

```text
  10_audit_round_01.json
  11_score_report.json
  12_revision_log.md
  rejected_variants/
```

If image generation is not requested or cannot be completed in the current environment, still produce the route decision, shot plan, storyboard image prompts, Google omni prompts, and QC summary.

For skill improvement passes, promote observer events into candidate rules with:

```bash
python .agents/skills/ai-visual-director/scripts/observe_run.py propose-rules --events outputs/<date>_<slug>/_observer/events.jsonl --out outputs/<date>_<slug>/_observer/candidate_rules.json
python .agents/skills/ai-visual-director/scripts/observe_run.py aggregate-runs --root outputs --out outputs/observer_candidate_rules.json
```

Treat that output as candidate evidence, not as automatic permission to edit the skill. Temporary-thread candidate rules remain draft evidence until the SSOT main thread accepts them.

## Portability

This skill must be self-contained. Do not depend on files outside this folder when packaging or copying it to another Codex installation.

Before migration, run:

```bash
python .agents/skills/ai-visual-director/scripts/verify_skill_package.py .agents/skills/ai-visual-director
python .agents/skills/ai-visual-director/scripts/package_skill.py .agents/skills/ai-visual-director --out dist
```

Install the resulting `ai-visual-director-*.tar.gz` by extracting the `ai-visual-director` folder into either:

- project-local `.agents/skills/ai-visual-director`
- user-level `$HOME/.agents/skills/ai-visual-director`

Use project-local installation when the workflow belongs to this method library. Use user-level installation when the workflow should be available in all Codex projects on that machine.
