---
name: multi-angle-product-identity-lock-board
description: Directly generate a six-view product identity lock board for low-risk products using Codex built-in /image gen.
---

# Multi-Angle Product Identity Lock Board
# 多角度产品身份锁定板

## Purpose

This skill creates one six-view multi-angle product identity lock board image for low-risk products by directly using Codex built-in `/image gen`.

The purpose is to lock product identity for downstream visual consistency, reusable product asset libraries, advertising image generation, video generation, storyboard creation, and commercial visualization.

This skill is not a text-only instruction workflow. The default result is a generated image plus QA judgment. Do not stop at a written generation instruction unless the user explicitly asks not to generate an image.

This skill is not for product redesign, advertising poster creation, lifestyle scene generation, packaging redesign, technical blueprinting, complex product reconstruction, exact label-copy lock, exact logo reproduction, or engineering-precision modeling.

Accuracy is more important than beauty. Never sacrifice accuracy for style.

## Chinese Name

多角度产品身份锁定板

## Scope

Use this skill only for low-risk products with clear silhouettes, simple structures, readable proportions, and minimal text.

Suitable products include:

- shoes
- bags
- headphones
- cups
- simple furniture
- small home appliances
- stationery
- simple consumer electronics
- simple accessories
- simple consumer products with clear silhouettes
- products with minimal text
- products with simple, visible, non-mechanical structure

This skill is suitable when most of the following are true:

- the target product reference image clearly shows the product shape
- the silhouette is simple and readable
- the visible structure is not mechanically complex
- text, labels, logos, and markings are limited or non-critical
- exact readable copy is not a success criterion
- the product does not require hidden or unseen engineering details
- the product can be represented safely across six common views without inventing unknown structure
- the product does not depend on transparent, liquid, glass, chrome, mirror-like, or highly reflective material behavior
- the user wants a product identity board, not an advertisement, poster, packshot campaign, or design exploration

## Out of Scope

Do not use this skill if the product has any of the following conditions:

1. Dense label text, packaging copy, ingredient lists, specifications, certification marks, barcode areas, or legally important written content.
2. A requirement for fully accurate readable text, exact logo reproduction, exact packaging copy, or zero text distortion.
3. Complex mechanical structure, articulated parts, folding structure, movable joints, exposed skeleton, wheel systems, hinges, screws, motors, cables, or engineering-critical geometry.
4. Transparent, translucent, liquid, glass, acrylic, glossy mirror, chrome, or highly reflective materials as the core product identity.
5. Multiple operational states such as open/closed, folded/unfolded, deployed/stored, installed/uninstalled, expanded/collapsed, worn/unused.
6. Missing key reference views where the user requires accurate true back, side, top, bottom, underside, or internal structure.
7. Medical, industrial, transportation, technical equipment, mobility device, safety-critical, compliance-sensitive, or high-precision structure products.
8. Products where invisible structure must be guessed.

If the product is out of scope, stop before image generation and output:

```text
This product is outside the safe scope of Multi-Angle Product Identity Lock Board. Use a higher-precision workflow such as label-copy lock, structural lock, state-variation lock, or material-detail lock.
```

Do not force this skill onto high-risk products.

## Input Requirements

The user may provide:

- one or more target product reference images
- an optional sample asset-board image
- optional product name
- optional notes about colors, materials, logo, or visible markings
- optional output ratio
- optional required views

Require at least one target product reference image. If no target product reference image is provided, ask for the target reference instead of generating from imagination.

If no output ratio is specified, default to a 16:9 horizontal asset board.

If no view set is specified, default to six views.

## Reference Handling Rules

Always distinguish between two reference types.

### Target Product Reference

The target product reference is the only source of truth for product identity.

Preserve:

- product type
- silhouette
- proportions
- primary color
- secondary color
- color placement
- material finish
- seams
- edges
- openings
- panels
- straps
- handles
- buttons
- laces
- stitching
- surface texture
- pattern direction
- visible construction details
- visible markings
- visible logo placement

Do not:

- redesign the product
- modernize the product
- beautify the product
- simplify the product
- replace the product
- reinterpret the product
- invent features
- remove real features
- change colors
- change materials
- change proportions
- change silhouette
- add extra accessories
- add new logos
- create fake text
- turn the product into another model or brand

### Sample Asset-Board Reference

The sample asset-board reference is only a layout and presentation reference.

Use it only for:

- board layout
- six-view organization
- neutral studio background
- spacing
- shadow style
- clean product reference-sheet logic
- light gray or white commercial product-board look

Never copy the sample product identity unless the user explicitly says the sample product is also the target product.

If the user uploads a shoe board as a sample and the target product is not a shoe, do not turn the target product into a shoe.

## Default Board Specification

Generate one clean six-view product identity lock board image.

Default board format:

- one image
- exactly six distinct product views
- horizontal 16:9 board unless the user specifies another ratio
- clean commercial product identity board
- neutral light gray or pure white background
- soft diffused studio lighting
- subtle natural grounding shadows
- no text annotations
- no arrows
- no labels
- no numbers
- no measuring lines
- no graphic overlays
- no people
- no hands
- no props
- no lifestyle environment
- no packaging unless the packaging itself is the target product

Default six views:

1. front view or primary front-facing view
2. rear view or back view
3. left side profile
4. right side profile
5. slight overhead top view
6. 3/4 front hero view

If the underside is more important than the top, replace the overhead top view with bottom or underside view.

If the product's front and back are visually similar, include a 3/4 rear view to avoid repeated views.

All six views must be meaningfully different. Avoid repeated or nearly duplicated camera angles. Each view must show the complete product with generous margins. No cropping. No overlap between product views. Do not add unrelated elements.

## Visual Style

Use a clean commercial product identity board style.

Preferred style:

- neutral studio product photography
- light gray background or pure white background
- soft diffused studio lighting
- subtle natural grounding shadows
- high clarity
- accurate material rendering
- clean spacing
- non-dramatic presentation
- professional product identity reference sheet

Avoid:

- cinematic lighting
- dramatic shadows
- lifestyle scene
- poster styling
- ad composition
- concept art
- technical blueprint
- labels
- arrows
- callouts
- text overlays
- decorative typography
- extra graphics
- watermarks
- extra logos
- model variants
- color variants
- packaging campaign layout

## Priority Order

Always prioritize:

1. product identity accuracy
2. structural completeness
3. proportion accuracy
4. silhouette accuracy
5. color accuracy
6. material accuracy
7. visible detail preservation
8. distinct angle coverage
9. clean board layout
10. visual neatness

Never sacrifice accuracy for style.

Never use phrases that encourage redesign, such as:

- make it more premium
- improve the design
- modernize the product
- make it sleeker
- enhance the product design
- redesign it
- create a better version
- luxury redesign
- futuristic version

## Workflow

When invoked, perform these steps in order.

### Step 1 - Applicability Check

Determine whether the product fits this skill.

Classify only as:

- Suitable
- Risky
- Not suitable

If not suitable, stop and do not generate an image.

If risky, continue only when the risk is manageable within a low-risk product identity board. State the risk plainly before generation.

Completion criterion: the scope decision is explicit, and high-risk products are rejected before `/image gen`.

### Step 2 - Product Identity Extraction

Extract visible identity features from the target product reference image.

Summarize:

- product type
- overall silhouette
- primary color
- secondary color
- material
- visible structural features
- texture features
- logo / visible text status
- immutable elements

Do not invent unseen details. If a feature is not visible, mark it as unknown rather than guessing.

Completion criterion: the immutable product identity is clear enough to guide generation without redesign.

### Step 3 - Board Planning

Plan the six views.

Default:

- front
- rear
- left side
- right side
- top / overhead
- 3/4 front

Adjust only when necessary for the product. Ensure the six angles are distinct and non-redundant.

Completion criterion: the selected six views cover the product identity without duplicated angles.

### Step 4 - Image Generation

If the product is suitable or manageable-risk, directly use Codex built-in `/image gen` to generate one six-view product identity lock board.

Use the uploaded target product reference as the product identity source. Use any uploaded sample asset-board image only as layout/style reference. Generate one six-view product identity lock board image.

Construct the internal image-generation instruction from the identity extraction and board plan. Do not expose this instruction to the user by default.

Internal generation instruction must include:

```text
Create one clean six-view product identity lock board of the exact same product shown in the uploaded target product reference image. Use the uploaded target product image as the only source of truth for product identity, silhouette, proportions, colors, materials, surface texture, visible construction details, logo placement, and visible markings.

Show the product in exactly six clearly distinct views arranged as a clean 2x3 studio product reference board: front view, rear view, left side profile, right side profile, slight overhead top view, and 3/4 front hero view. Each view must show the complete product with generous margins, no cropping, no overlap, and no repeated or nearly duplicated angles.

Maintain the exact original product design. Do not redesign, simplify, stylize, modernize, beautify, replace, reinterpret, or invent any part of the product. Preserve the original silhouette, proportions, color distribution, material finish, seams, edges, openings, panels, handles, straps, buttons, surface details, texture direction, and visible markings as conservatively as possible from the reference.

Use a neutral light gray or pure white studio background, soft diffused product photography lighting, subtle natural shadows under each view, high clarity, accurate material rendering, clean spacing, and a professional commercial product identity reference-sheet layout. No lifestyle scene, no props, no hands, no people, no annotations, no arrows, no labels, no numbering, no added text, no watermark, no extra logo, no packaging unless it appears in the target reference.

Negative constraints: no product redesign, no changed colors, no changed materials, no invented features, no missing parts, no duplicated angle, no distorted proportions, no warped geometry, no extra accessories, no fake text, no text overlays, no captions, no labels, no messy background, no cinematic scene, no dramatic lighting, no AI-looking plastic texture.
```

Completion criterion: `/image gen` has been called or, if the image-generation tool is unavailable, the run is reported as blocked by missing image-generation capability. Do not silently fall back to text-only output.

### Step 5 - QA

After image generation, inspect the generated result against the QA rules.

Completion criterion: the response includes an Approved / Not approved judgment with the main failure reason if any.

### Step 6 - Repair

If the result fails, write one repair instruction targeting only the main failure. Do not change multiple variables at once.

Completion criterion: the repair instruction is specific enough to drive a second `/image gen` attempt without widening scope.

## Required Output Format

Default output is not a final English prompt. It is a generation action plus QA result.

Always output these sections:

### 1. Applicability

```text
Applicability: Suitable / Risky / Not suitable
Reason: ...
```

### 2. Product Identity Lock Summary

Write this section in Chinese using this exact structure:

- 产品类型：
- 整体轮廓：
- 主色：
- 辅助色：
- 材质：
- 结构特征：
- 纹理特征：
- logo / 文字：
- 不可改变元素：

### 3. Image Generation Action

State that Codex built-in `/image gen` is being used to generate the six-view product identity lock board.

Include the generated image result when available.

Do not output the internal English generation instruction by default.

### 4. QA Result

```text
Approved / Not approved
Failure reason if any: ...
Repair instruction if needed: ...
```

If the product is Not suitable, skip sections 3 and 4 and output the scope refusal.

## No-Generation Text Exception

Use text-only mode only when the user explicitly says "只给提示词", "只输出 prompt", "不要直接生图", or an equivalent instruction.

In text-only mode:

- do not call `/image gen`
- still perform applicability check
- still summarize product identity
- output one concise written image-generation instruction for later use
- clearly mark it as text-only because the user requested no direct image generation

Text-only mode is never the default.

## QA Rules

Before finalizing, check:

1. Is the product suitable for this skill?
2. Are there exactly six views?
3. Are all six views meaningfully different?
4. Is the product fully visible in every view?
5. Is there enough margin around each view?
6. Is the silhouette preserved?
7. Are the proportions preserved?
8. Are the colors preserved?
9. Are the materials preserved?
10. Are visible details preserved?
11. Has any structure been invented?
12. Has any real structure been omitted?
13. Were extra accessories added?
14. Is there any fake text?
15. Are there unwanted people, hands, scenes, props, labels, arrows, annotations, or text?
16. Does the result read as a product identity lock board rather than an advertising poster?

If any critical item fails, output:

```text
Not approved. Failure reason: ... Suggested fix: ...
```

## Repair Rules

When repairing a failed result, change only one main issue at a time.

### Repeated Angles

Add:

```text
Each of the six views must be clearly different. No two views may share the same camera angle or product orientation.
```

### Product Redesign

Add:

```text
Preserve the exact original product design from the uploaded target reference. Do not improve, redesign, stylize, simplify, modernize, or reinterpret any element.
```

### Cropped Product

Add:

```text
Every view must show the full product with generous margins and blank space around the complete object.
```

### Wrong Colors or Materials

Add:

```text
Match the exact color distribution and material finish from the uploaded target product reference.
```

### Fake Text or Logo Distortion

Add:

```text
Do not invent or rewrite any logo or text. Preserve only visible markings from the reference. If exact text cannot be rendered accurately, keep markings non-readable rather than creating fake readable text.
```

### Background Too Complex

Add:

```text
Use only a plain neutral studio background. No room, no environment, no lifestyle setting, no props.
```

## Hard Prohibitions

Never output or encourage:

- product redesign
- advertising poster
- lifestyle scene
- packaging campaign image
- user interaction image
- labeled diagram
- callout sheet
- engineering blueprint
- technical drawing
- multi-color variant board
- multi-model comparison board
- cinematic hero render
- dramatic commercial hero render
- fake product upgrade
- invented features
- fake labels
- unrelated accessories

This skill only creates a six-view multi-angle product identity lock board for low-risk products.

## End Condition

The skill output is successful when it provides:

1. a clear applicability judgment,
2. a Chinese product identity lock summary,
3. direct Codex built-in `/image gen` generation of one six-view product identity lock board,
4. an Approved / Not approved QA result,
5. no default text-only substitution,
6. no scope creep into complex product locking, exact label-copy locking, product redesign, or advertising image generation.
