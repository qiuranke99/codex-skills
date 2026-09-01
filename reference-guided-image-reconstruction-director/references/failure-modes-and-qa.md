# Failure Modes, QA, and Directional Retry

User-operated external image generation and editing are probabilistic. A valid prompt-only contract reduces avoidable drift but cannot guarantee a correct image. The Skill performs read-only QA only after the user imports an external result with provenance. A fresh prompt package remains `prompt_package_ready`; an imported structure-only result may use `structure_master_candidate`, and an imported downstream result may use `candidate_unapproved`. The Skill never generates or edits the pixels it judges.

## 1. Common Failure Modes

| Failure | Observable symptom | Likely owner | Directional response |
| --- | --- | --- | --- |
| Defective contour tracing | Bent, melted, fused, or soft target geometry returns | Structure-stage prompt or contaminated input | Give the user a delta prompt to rebuild the neutral structure master externally; state recoverable relationships positively and exclude appearance references. |
| Reference composition takeover | Camera, crop, layout, position, or aspect changes toward a reference | Over-broad reference authority | Remove protected-structure permission, restate master-only authority, or remove the offending reference. |
| Root/leaf authority split | A broad family and child attribute behave inconsistently | Overlapping scopes resolve to different sources | Give overlapping rows identical primary/allow sets, or split them into non-overlapping paths. |
| Paper authority | A stage cannot preserve a required attribute despite a valid-looking matrix | Its authorized source is absent from that stage's manual input list | Add the bounded authority source to that manual stage or change the authority; a source listed elsewhere cannot supply it. |
| Object-count drift | Extra or missing subjects, devices, props, limbs, or fixtures | Count not explicitly protected; foreign objects in references | Give the master sole count authority and deny foreign entities per reference. |
| Deletion rebound | Removed entity or a substitute returns | Removal not normalized or reference reintroduction not denied | Add the explicit exception, complete cleanup closure, and per-reference `deny_entities`. |
| Residual deletion traces | Shadow, reflection, indentation, contact mark, or broken background remains | Local or structure repair region too narrow | Expand only the physical trace closure and repair the revealed background. |
| Perspective contradiction | Global camera feels right but local edges do not share a coherent projection | Camera intent confused with malformed projected geometry | Preserve camera intent; re-solve local geometry and disclose inference if evidence is incomplete. |
| Material or style averaging | Incompatible references produce a muddy hybrid | Multiple primaries or unresolved overlap | Select one primary, split sub-attributes, create explicit variants, or keep unresolved. |
| Text or logo hallucination | Misspelled, invented, or approximately copied graphics | User-operated external stage assigned truth-sensitive text | Remove text authority, use exact artwork/pixels, or leave the claim unresolved. |
| Exact-primary bypass | A secondary exact source is listed while the authority primary is absent | “Any evidence used” substituted for primary stage responsibility | Put the resolved primary exact-evidence asset in the compatible manual upload list or change authority explicitly. |
| Empty composite | Exact artwork is listed but no image base exists, or its base-stage link points forward | Composite lacks an exact asset or substantive base | Include an exact asset plus target/structure-master base, or bind an earlier actionable external stage with `base_stage_id`. |
| Product identity drift | Silhouette, parts, controls, state, or color becomes a similar but different product | Category reference treated as exact identity | Narrow reference role and move identity-bearing attributes to an exact-asset lane. |
| Face or character drift | Face, age, body, hair, wardrobe, or accessories merge across references | Identity and look roles not separated | Split attributes, isolate the identity source, and deny identity contribution from pose/look references. |
| Cropped-reference invention | Hidden portions are guessed as if source-backed | Crop missingness not recorded | Mark unseen regions unknown; add exact evidence or reduce the claim. |
| Original-target recontamination | Approved structure regresses toward the problem image in realism | Original target returned without scoped reuse | Exclude it, or replace it with the smallest safe crop and non-structural role. |
| Overloaded negative prompt | Result becomes generic, omits wanted details, or repeats unwanted concepts | Too many broad or contradictory denials | Keep positive invariants and only the highest-risk source-specific denials. |
| Generic-prior substitution | Plausible hidden details appear without evidence | Missingness converted into “realism” | Remove the claim, obtain evidence, or mark the result a bounded proxy. |
| Resolution claim contradiction | A false prompt-guarantee flag coexists with a positive commitment, a categorical native-4K output fact appears in any state, or `unknown + none + null` coexists with a declarative output/result size fact | Semantic target, prompt, settings evidence, and inspected-file facts were not separated | Keep only a non-guaranteed imperative target or explicit negative caveat; categorical output claims remain forbidden, and inspected-file numbers require an exact observed metadata binding. |
| Declarative output dimension binding failure | A parseable output/result width-height fact disagrees with `actual_pixel_dimensions` in a non-unknown state | Free-text numeric facts were not bound to the structured record | Require every parsed pair to equal the structured dimensions, otherwise correct or remove the assertion; keep the independent `E_DECLARATIVE_OUTPUT_DIMENSION_BINDING` error. |
| Inspected-file dimension binding failure | An inspected-file numeric fact uses the wrong fact/evidence state or disagrees with `actual_pixel_dimensions` | Free-text dimensions were treated as self-authenticating | Require `observed + inspected_file_metadata` and exact parsed width/height agreement, otherwise remove the fact or correct the structured evidence. |
| Resolution evidence contradiction | Positive dimensions and a non-unknown state coexist with “no dimensions are known or evidenced” | Free-text evidence was allowed to override the structured fact/evidence pair | Restore the one-to-one fact/evidence type mapping, or change the state to `unknown + none + null`; do not claim that the validator authenticates evidence. |
| Internal-tool prompt escape | Authoritative prompt or settings text tells Codex, this Skill, `imagegen`, `image2gen`, or `image_gen__imagegen` to act | User wording leaked into an authoritative output surface | Move the wording to non-authoritative `user_request`/`notes`, state the boundary, and keep only user-operated external-platform imperatives in the deliverable. |

## 2. Preflight QA

Before compiling prompts, verify:

- every readable image was visually inspected;
- exactly one target is identified and zero references remains valid;
- role states and confidence are present;
- source facts, user decisions, and manual external stage records are separate;
- `execution_boundary` is exactly `manual_external_prompt_only`, and the stage records are manual external action plans rather than callable tool steps;
- JSON keys are unique at every depth, all structured objects use only their documented fields, and any preserved `user_request` or `notes` text remains non-authoritative;
- every raw attribute uses lowercase ASCII dotted `snake_case`, with no whitespace cleanup, uppercase, punctuation cleanup, empty segments, or embedded/repeated wildcard;
- each resolved attribute has exactly one primary; unresolved rows are blocked-only;
- every stage-required attribute is supplied by a primary/allow source in that stage's manual input list;
- every reference has allowed and forbidden inheritance;
- preserve-all plus removals is normalized into explicit exceptions;
- every required exact attribute has covering resolved authority whose primary is valid exact evidence and itself enters a compatible manual external stage, or the contract remains blocked;
- a fresh package uses `delivery_state: prompt_plan`, empty external provenance, and `prompt_package_ready`;
- a fresh package declares no `candidate_result`; every imported `candidate_result` is provenance-bound, and none carries `approved: true`;
- any candidate/retry status binds complete user-manual external provenance to a declared status-compatible imported result asset;
- platform guidance sets `prompt_guarantees_dimensions: false`; uses `unknown + none + null`, `known + authoritative_record`, `observed + inspected_file_metadata`, or `user_reported + user_report`; binds every non-unknown state to positive integer width and height; and rejects explicit missingness prose for non-unknown states;
- direct-copy prompts, semantic targets, and settings evidence contain no affirmative native-4K/exact-pixel commitment, no categorical native-4K output/result fact in any state, no declarative output/result dimension under `unknown + none + null`, and no internal image-tool token or Codex/Skill action direction; every parseable numeric output pair in a non-unknown state exactly matches `actual_pixel_dimensions`, while every inspected-file numeric fact additionally uses `observed + inspected_file_metadata`; explicit negative commitments—including `non-guaranteed` and caveats whose regardless/no-matter/`无论` modifier stays in the same clause—remain valid, as do ordinary user-operated external-platform create/edit/reconstruct imperatives;
- no image generation/edit tool or third-party API, login, upload, submission, polling, download, account, or session automation is invoked or authorized.

## 3. Structure Master Gate

Reject the candidate if any hard gate fails:

- aspect ratio, crop, and camera intent depart from the target without an explicit user change;
- element position, relative scale, topology, object count, or occlusion drifts;
- malformed geometry, fusions, duplicated parts, or inconsistent local perspective remain;
- a removal, its trace, or a substitute remains;
- unsupported identity, text, branding, hidden construction, decoration, or realism has been invented;
- neutral appearance is too dark, textured, or stylized to judge geometry;
- missing evidence is disguised as certainty.

The structure-stage target must be `inputs[0]`, and every protected requirement must be supplied by a primary/allow source in that same manual plan. Only after the user manually produces and imports the result with bound provenance may it be reported as `structure_master_candidate`. If that imported candidate passes visual QA, request the user's explicit approval for use in the next manual stage. Do not infer approval from silence or technical success, and do not label a structure-only candidate `candidate_unapproved`.

## 4. Realism Candidate Gate

Reject the candidate if:

- protected structure differs from the approved master;
- a reference contributes camera, crop, layout, count, foreign objects, or unapproved identity;
- materials, construction, lighting, color, or lens character come from the wrong reference or from an unresolved blend;
- removed entities or physical traces return;
- exact text, logo, face, product detail, interface, or marking is hallucinated or distorted;
- textures use implausible scale, joins, repetition, or surface response;
- reflections, shadows, depth cues, or contact relationships contradict the approved structure;
- the output is described as approved, locked, exact, or bug-free without the external human gate.

## 5. Cross-Domain Stress Checks

### Architecture and Interiors

- protect vanishing system, opening positions, built-in count, circulation, and cabinet topology;
- let construction references contribute joints, material response, and finish only;
- deny their camera, crop, room layout, fixture count, furniture, and exterior view unless explicitly authorized.

### Products

- separate silhouette, component layout, operating state, label, color, material, and reflections;
- similar products are category realism references, not identity evidence;
- use exact compositing for labels, logos, interfaces, and model-specific controls when fidelity matters.

### People and Characters

- separate face, body, pose, expression, hair, wardrobe, accessories, and lighting;
- a pose or fashion reference cannot contribute identity;
- if the problem target is the only identity evidence, do not mechanically exclude it from the final plan; use scoped identity reuse or exact-pixel compositing.

### Target Only

- pixel or local routes remain available;
- a neutral structural candidate may be prepared when topology is recoverable;
- evidence-specific material, identity, or hidden geometry must remain missing;
- generic realism is a chosen interpretation, not verified truth.

### Conflicting References

- never average mutually exclusive primaries;
- ask only when the conflict materially changes the result;
- otherwise narrow roles, split variants, or leave the attribute unresolved.

### Removal and Reference Pollution

- test the full cleanup closure;
- test every reference for the removed entity or a substitute;
- compare count, crop, layout, and foreign objects against the target or approved master.

## 6. Directional Retry Record

Every retry must name:

- failed observable gate;
- defect-owning stage;
- defect-owning source or authority row;
- accepted invariants that must remain unchanged;
- one narrow input, authority, crop, mask, prompt, or composite change;
- images newly included and excluded;
- exact pass condition;
- residual risk and unresolved evidence.

Direct the user to rerun the external structure stage for structural drift. Direct the user to rerun only the external realism stage for material or lighting misassignment when the master remains valid. Move identity or text to exact compositing instead of repeatedly strengthening spelling or matching language. Stop when the requested correction lacks evidence; never execute or submit the retry from this Skill.

## 7. Acceptance Language

Use precise states:

- `prompt_package_ready`
- `blocked_missing_evidence`
- `bounded_proxy_only`
- `structure_master_candidate`
- `candidate_unapproved`
- `qa_failed_directional_retry_ready`

Keep state, delivery, provenance, and stage scope aligned: fresh and blocked packages remain `prompt_plan`; imported candidate/retry states require complete provenance bound to a declared result asset. Blocked states contain blocked stages only, `structure_master_candidate` contains structure stages only, and `candidate_unapproved` does not represent a structure-only set. `prompt_package_ready` may be structure-only as a text plan; `qa_failed_directional_retry_ready` may be structure-only only when it is backed by an imported failed result. The target is first for pixel/local/isomorphic/structure, and an approved master is first for realism. Do not combine a blocked plan with a speculative actionable fallback in one contract.

Only the user can provide the relevant approval. A structure master's scoped approval is recorded on that asset as `approved: true`; it is not an overall contract status and the validator cannot mint it. Approval of a candidate does not turn guessed geometry, illegible text, or invented identity into source truth.
