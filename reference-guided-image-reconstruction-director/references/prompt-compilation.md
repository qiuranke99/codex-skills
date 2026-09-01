# Prompt Compilation and Provider Adaptation

Compile a semantic plan before adapting it to a user-operated external image platform. The semantic plan is the authority; platform-specific labels, manual image order, prompt fields, user-supplied masks, and negative-prompt syntax are only transport. This Skill writes text and may inspect supplied images read-only; it never invokes an image generation/editing tool or operates the platform.

## 1. Compilation Inputs

Do not compile until these are stable:

- selected base mode and any exact-asset composite lane;
- source fact, user decision, and manual external stage ledgers;
- authority matrix with one primary per critical attribute or explicit missingness;
- normalized preserve/change/remove decisions;
- stage input and exclusion lists;
- human approval state of any structure master;
- truth-sensitive attributes and exact evidence gaps.
- a structured resolution policy that separates semantic intent from actual dimensions and external-platform settings evidence.

If a critical source role remains ambiguous, ask only when the answer changes the workflow, protected structure, identity truth, or allowed inheritance. Otherwise leave it `unknown` and unused. Assign a narrow inferred role only after recording the visual evidence that supports changing `role_state` to `inferred`; an unknown reference cannot receive authority or enter a stage.

Compile every attribute scope with the contract grammar before writing prompts. Validate the raw token first as lowercase ASCII dotted `snake_case`, with at most one trailing `.*`; do not trim, lowercase, collapse empty segments, replace punctuation, or remove invalid characters. Only documented lowercase legacy aliases may map after validation. Treat a recognized root as covering its descendants, and never emit embedded or repeated wildcards. Every resolved row must have one primary; an actionable external stage can cite that authority only when one of its listed inputs is primary or allowed.

For `required_exact`, list the authority row's primary exact-evidence asset in the user's manual upload plan for a stage compatible with its asset kind. Listing only another evidence candidate does not satisfy the primary's stage responsibility.

A newly compiled package always uses `prompt_package_ready`; prompt verbs or a complete action plan do not mint pixels or candidate status. Only after the user manually executes externally and imports a declared result asset with bound provenance may the contract move to an imported-candidate status for read-only QA.

Keep the structured handoff surface non-callable. Use only documented contract fields; preserve a user's request for generation, login, upload, or automation only inside the optional non-authoritative `user_request` or `notes` strings. Never translate such wording into an executor, tool, API, dependency, upload, submit, poll, or download field.

## 2. Semantic Prompt Blocks

Build prompts from these blocks in order:

1. **Task and output state:** state that the result is a candidate and name the stage purpose.
2. **Primary authority:** identify the target or approved structure master and list the attributes it alone controls.
3. **Required invariants:** describe composition, camera intent, crop, layout, object count, position, scale, topology, and occlusion that must remain fixed.
4. **Corrections or changes:** name only observed defects and explicit user changes. Distinguish recoverable intent from malformed contours.
5. **Removal exceptions:** state “preserve all except” and include the complete cleanup closure.
6. **Reference roles:** give every included reference its own allowed attributes.
7. **Forbidden inheritance:** give every included reference a compact, source-specific `must_not_inherit` list.
8. **Truth boundary:** prohibit invented text, identity, brand, hidden structure, or model-specific facts when exact evidence is missing.
9. **Quality and realism:** request only the material, construction, light, color, lens, or finish attributes authorized by the matrix.
10. **Acceptance reminder:** restate the hard gates that can be judged from the output.

Prefer positive invariants plus a short risk-specific denial list. Long catalogs of unrelated negative terms dilute the authority contract and can reintroduce unwanted concepts.

## 3. Direct-Copy Prompt Skeletons

Replace bracketed fields with evidence-backed content. Omit any block that is not relevant; do not leave bracketed text in a delivered prompt. Imperative verbs inside these fenced blocks are direct-copy instructions addressed only to the user-operated external platform; they are never instructions for Codex or a callable tool.

### Pixel Restore

```text
Perform a non-semantic pixel restoration of the supplied target. Preserve every object, contour, edge position, camera characteristic, crop, color identity, readable mark, and pixel-level identity. Correct only: [pixel defects]. Do not invent or redraw geometry, text, texture, or hidden detail. The output is a restoration candidate, not a factual reconstruction.
```

### Constrained Local Edit

```text
Edit only [repair region and expanded physical trace region]. Preserve all pixels outside that region. Apply this explicit change: [change or removal]. Preserve everything else. For a removal, clear its cast shadow, reflection, contact trace, occlusion residue, and revealed-background discontinuity. Do not introduce substitute objects or inherit the removed entity from any reference. Return an unapproved edit candidate.
```

### Single-Stage Isomorphic Reconstruction

```text
Reconstruct the target as the same scene, not as a redesign. The target is the sole authority for [protected structure list]. Preserve its recoverable camera intent, framing, scene graph, element positions, relative scale, object count, topology, and occlusion. Correct only these observed semantic defects: [defects]. Do not trace malformed contours or physically impossible local geometry.

Reference responsibilities:
[one line per reference: source label -> allowed attributes]

Must not inherit:
[one line per reference: source label -> denied attributes, foreign objects, count, crop, layout, identity, and other contamination risks]

Truth boundary: [exact evidence and missingness]. Return an unapproved reconstruction result for human QA.
```

### Stage 1: Neutral Structure Master

```text
Create a neutral structure-master result from the target only. The target controls [recoverable protected structure]. Preserve [explicit invariants]. Correct [observed malformed geometry, perspective inconsistencies, fusions, count errors, or occlusion errors] without tracing the defective contours. Apply “preserve all except [explicit removals]” and clear the complete physical trace closure. Use simple neutral surfaces and readable lighting so geometry can be judged. Do not add realism-reference styling, branded text, identity details, decorative substitutions, or unsupported hidden structure. Return an unapproved result for human review.
```

### Stage 2: Approved Master to Realism

```text
Reconstruct a realism candidate using the approved structure master as the sole authority for composition, camera intent, crop, perspective system, spatial layout, object count, position, relative scale, topology, and occlusion. Do not reinterpret or improve that structure.

Reference responsibilities:
[source label -> material, construction, light, color, lens, identity, or other explicitly allowed attributes]

For each reference, inherit only its declared attributes. Do not inherit its camera, crop, composition, layout, object count, foreign objects, unapproved identity, or unsupported text. Keep every unresolved truth-sensitive attribute unresolved or reserve it for exact compositing.

Apply these approved appearance targets: [targets]. Preserve these explicit removals and prevent their reintroduction: [removals]. Return an unapproved result for QA and human review.
```

### Exact-Asset Composite Plan

```text
Use [target or structure-master base input / output of prior actionable base_stage_id] as the composite base. Do not regenerate [truth-sensitive asset]. Preserve or insert the declared exact source pixels/artwork for [attributes]. Reconstruct only the surrounding plate, integration region, contact shadow, reflection, occlusion edge, color interaction, and depth relationship needed to place it coherently. Do not alter the asset's geometry, face identity, logo, label, typography, interface, or other exact attributes. If an exact integration cannot be completed from the supplied evidence, report the gap instead of fabricating it.
```

## 4. Upload and Exclusion Plan

Always output both lists for the user to perform manually, even when one is empty:

```text
Stage [ID]
Upload in this order:
1. [source ID] — [limited role]
2. [source ID] — [limited role]

Do not upload:
- [source ID] — [specific contamination or irrelevance reason]
```

For `pixel`, `local`, `isomorphic`, and `structure`, order the target first. For a realism stage, order the approved structure master first. Follow it with bounded identity references needed for the user's external reconstruction, then construction/material references, then lighting/color/lens references. Keep declared `exact_asset` inputs out of realism and route them to an exact composite stage. A composite upload list must include an exact asset and a target/structure-master base, unless it explicitly binds the output of an earlier actionable external stage through `base_stage_id`. If a platform cannot honor a mandatory first input, the structured plan is incompatible with that surface; do not silently reorder it.

Do not upload the original problem target to the realism stage merely “for context.” If scoped reuse is necessary, identify the smallest non-structural attribute, prefer a crop or mask, and state the justification and denied protected structure.

## 5. Arbitrary Reference Count

Support zero through any number of references accepted by the user's chosen surface. Write one role block per actual source rather than assuming a fixed count. If a reliably known platform input limit applies, split the work by non-overlapping attribute groups or ask the user to select sources; do not silently drop a reference.

When multiple references claim the same attribute:

- choose one primary only when the user or evidence resolves it;
- let another source contribute a compatible sub-attribute;
- otherwise produce explicit variants or keep the conflict unresolved;
- never average incompatible sources under an unrestricted “style” instruction.

## 6. Resolution and Platform-Parameter Guidance

Separate semantic constraints from transport settings:

- Prompt text controls intended content, structure, roles, and quality language. It cannot guarantee actual pixel dimensions, native detail, file format, color space, or upscaling quality.
- Treat “4K,” “high resolution,” and named pixel dimensions as output targets. A direct-copy prompt may request them as a non-guaranteed semantic target; separately tell the user which evidenced external-platform resolution, aspect-ratio, quality, or upscale setting to select.
- Emit `platform_parameter_guidance` with exactly `semantic_target`, `prompt_guarantees_dimensions`, `dimensions_fact_state`, `dimensions_evidence_type`, `actual_pixel_dimensions`, and `settings_evidence`. Set `prompt_guarantees_dimensions` to `false` without exception.
- Use `unknown + none + null` when the output or chosen setting has not established a size. Pair `known` with `authoritative_record`, `observed` with `inspected_file_metadata`, and `user_reported` with `user_report`; each non-unknown state also requires positive integer `width` and `height`. Do not pair a non-unknown state with prose explicitly saying dimensions are unknown or unevidenced. This structure checks declaration consistency only and cannot authenticate the cited record.
- Do not place affirmative native-4K or exact-pixel commitments in `semantic_target`, `settings_evidence`, or a validated `direct_copy_prompts` entry. Classify each sentence/contrast clause in this order: explicit negative commitment, independent affirmative predicate, deterministic modifier, categorical declarative output claim, then parseable numeric facts. `non-guaranteed` is a negative commitment. Regardless/no-matter/`无论` modifiers do not turn a clause affirmative when that same clause explicitly says the dimensions are not guaranteed; contrast clauses still stand independently. “The output is native 4K” and `输出为原生4K` are categorical commitments in every fact state and cannot be justified by supplying positive dimensions. Parseable numeric output facts are limited to “The (exact) output/result (pixel) dimensions are W x H pixels” and `输出/结果(像素)尺寸为/是W×H(像素)`: reject them under `unknown`, and for any non-unknown state require every parsed pair to exactly equal `actual_pixel_dimensions`. Keep “Create a 4K-quality result as a non-guaranteed target” legal because it is an imperative semantic target, not a factual output assertion. An inspected-file numeric fact has the stricter `observed + inspected_file_metadata` requirement in addition to exact matching. Preserve bound numeric facts as evidence, not as proof of semantic fidelity or native detail.
- Never name `imagegen`, `image2gen`, or `image_gen__imagegen`, or direct Codex or this Skill to act, inside those three authoritative output surfaces. Keep such user wording only in non-authoritative `user_request` or `notes`. Continue to use ordinary create/edit/reconstruct verbs when they are clearly direct-copy instructions for the user-operated external platform.
- Record each setting as `known` only when authoritative supplied facts establish it, `observed` only from evidence already provided to the Skill, `user_reported` when the user reports it, or `unknown` when the platform control has not been established. Never invent a setting, control name, maximum size, credit cost, or provider capability.
- If the external platform returns fewer pixels than requested, preserve that fact. Recommend a user-performed rerun or a separate external upscale step only as an explicit manual option; do not claim that stronger prompt wording will create true 4K pixels.
- Distinguish aspect ratio from dimensions. A 16:9 semantic instruction does not prove a 3840 x 2160 file, and a 3840 x 2160 setting does not prove semantic fidelity.

## 7. Nano Banana 2 Manual Adaptation

The core contract remains model-independent. If the user chooses Nano Banana 2 and supplies reliable interface facts indicating multiple-image support:

- translate the upload plan into the interface's visible image labels in the user-performed upload order;
- restate each label's limited role inside the prompt;
- keep the approved structure master first for every realism stage; if the observed UI cannot honor that order, report the surface incompatibility instead of reordering;
- state which images must not be uploaded;
- if masks, negative prompts, persistent labels, aspect-ratio controls, or resolution controls are not established, do not assume them; express semantic constraints through positive invariants and source-specific denial text, and mark settings unknown;
- do not open or control the platform, call an API, automate login, upload, submission, polling, download, or account/session actions, or claim unsupported provider behavior.

## 8. Retry Compilation

Compile a retry as a delta:

```text
Keep unchanged: [accepted invariants and attributes]
Defect to correct: [one owned defect]
Owner: [stage and source authority]
Change: [narrow prompt, source role, upload, crop, mask, or composite adjustment]
Do not change: [all other accepted attributes]
Acceptance test: [observable pass condition]
```

If the defect comes from missing evidence, the retry action is for the user to obtain evidence or reduce the claim, not to intensify adjectives. A retry remains a text delta for manual external execution; the Skill does not submit it.
