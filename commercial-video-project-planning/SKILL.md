---
name: commercial-video-project-planning
description: "Use when a local commercial or product-video project folder needs source-aware planning: read client materials, product资料, references, budgets, templates, prior scripts, or existing outputs; produce a structured Brief, selling-point brief, creative treatment, budget plan, on-screen copy direction, shot list, storyboard, 分镜头脚本, or shooting rundown handoff."
---

# Commercial Video Project Planning

## Overview

Use this skill to turn a messy local product-video project folder into a verified planning package before writing copy, scripts, storyboards, or production documents.

It complements `reference-video-product-adapter`: use that skill when the center of gravity is adapting one specific reference video. Use this skill when the center of gravity is the whole project folder, client demand, product evidence, budget, and production handoff.

## Decision

Use this skill when the user asks for any of:

- reading all files in a commercial video/product film project folder,
- producing or checking a structured `Brief`, `视频策划`, `上屏文案`, `shot list`, `分镜头脚本`, storyboard, or shooting rundown,
- turning product资料, client demand, reference films, and budget into a production-ready direction,
- rescuing work that feels low-end, generic, ungrounded, or disconnected from product evidence.

Do not use it for:

- a single reference-video adaptation package -> use `reference-video-product-adapter`,
- pure public-web visual research without project planning -> out of scope unless it can be reframed as project planning or TVC reference-video research,
- recurring autonomous maintenance inside `D:\Agent\video_script_agent` -> use that repo's CLI and automation.

## Workflow

1. Establish the working surface.
   - Confirm the project root and whether the user wants file edits or only a planning answer.
   - Inspect the folder structure before reading deeply. Identify client docs, product docs, reference videos/images, prior scripts, templates, outputs, and planning notes.
   - If a `.md`, `agent.md`, `memory.md`, or project agent folder exists, read the routing docs before drafting.

2. Build a source map first.
   - Record each useful source with path, type, what it proves, and reliability.
   - Separate `provided`, `inferred`, and `needs_confirmation` claims.
   - Never invent product efficacy, certifications, data, awards, customer promises, prices, or compliance claims.

3. Produce the planning layer before copy/script.
   - `strategy_brief`: client goal, audience, platform, core message, route, constraints, success criteria.
   - `product_selling_points_brief`: normalized selling points, evidence, risky claims, safe rewrites, visualizable points, weak points, questions.
   - `creative_treatment`: tone, visual mood, lighting, color, camera language, edit rhythm, scene/prop/texture strategy, reference adaptation boundary.
   - `budget_design_plan`: allowed scene/setup count, talent/prop/camera/lighting complexity, recommended duration, high-cost ideas to avoid, lower-cost alternatives.

4. Write downstream work only from the approved planning layer.
   - On-screen copy must preserve the chosen message hierarchy and avoid unverified claims.
   - Script or storyboard must lock approved copy instead of silently rewriting it.
   - Shot plans should include duration, visual, action, camera, product role, props/scene, on-screen text, source refs, budget risk, and open questions.

5. Run the high-end quality check.
   - Reject generic e-commerce packshot thinking, flat beauty-lighting defaults, unmotivated macro shots, fake luxury language, and unrealistic budget escalation.
   - Check whether reference reuse is structural rather than frame-by-frame copying.
   - Check whether the result can be executed by the likely crew, location, props, time, and budget.

6. Deliver in the right form.
   - If the user wants files, write Markdown/JSON as source of truth, then use document, spreadsheet, or presentation tools for DOCX/XLSX/PPTX deliverables.
   - If the user wants a chat answer, use the same sections and keep source/gap notes visible.
   - End with what is ready, what is blocked, and what input would improve the next pass.

## Output Contract

For full planning passes, create or return these sections:

```text
00_source_map
01_strategy_brief
01_product_selling_points_brief
01_creative_treatment
01_budget_design_plan
02_onscreen_copy_direction
03_shot_list_or_script_handoff
99_open_questions_and_risks
```

For detailed field checklists, read `references/project-output-contract.md`.

## Stop Conditions

Stop and ask for input only when a missing detail would change the plan materially: product identity, product claims, target platform/duration, budget tier, mandatory reference, or whether the output is for internal planning or client-facing delivery.

Otherwise proceed with explicit assumptions and mark weak claims as `needs_confirmation`.
