# Workflow Modes and Routing

Use this reference after read-only visual inspection of every readable input. The router chooses the least transformative manual external workflow that can fix the actual defect while preserving the user's intended structure and truth requirements. It routes and writes prompts; it never generates or edits pixels or operates the destination platform.

## 1. Truth and Scope Vetoes

Before choosing a reconstruction mode, answer these questions:

1. **Must the output preserve the target composition, camera intent, crop, layout, object count, position, scale, and occlusion?** If not, isomorphic reconstruction is the wrong category. State that boundary and, if useful, provide a separate prompt-only redesign package for the user's manual external execution; do not execute it.
2. **Will the output be used as forensic, medical, measurement, legal, documentary, or engineering evidence?** If yes, do not synthesize unseen content. Limit the plan to user-performed traceable pixel operations, annotation, or an explicitly separate illustration.
3. **Are exact text, logo, face, product identity, or hidden mechanical facts required?** If exact evidence is missing, preserve the missingness. Do not fill it from model priors. Plan an exact-asset composite lane or block the affected claim.
4. **Can a coherent scene topology and camera intent be recovered from the target or other authorized structural evidence?** If not, return `blocked_missing_evidence` or `bounded_proxy_only`; a plausible guess is not a factual correction.

Separate `camera_intent` from `projected_geometry`. A target may own the intended viewpoint and framing while its bent edges or inconsistent local vanishing lines remain defects to correct. If no single perspective system can be recovered, label the proposed correction `inferred` and require review.

## 2. Base Mode Decision Tree

### Implicit Trigger Versus Internal Pixel Route

A standalone ordinary request to sharpen, denoise, deblur, or upscale an otherwise correct image is outside this Skill's implicit trigger. Do not invoke this reconstruction director merely because those operations affect pixels. The `pixel_restore` branch below is an internal routing outcome only when the Skill is already in scope for a reference-guided or composition-preserving reconstruction task (or was explicitly invoked), and read-only diagnosis shows that semantic reconstruction is unnecessary. Even then, the deliverable is a manual external prompt and settings plan; the Skill performs no pixel operation.

### A. Pixel Restore

Choose `pixel_restore` only when all semantic content is already correct and the defects are limited to noise, compression, blur, banding, or insufficient resolution.

Do not use it when sharpening would merely make melted contours, wrong text, duplicated parts, bad perspective, or identity errors crisper.

In the structured manual action stage, put the target at `inputs[0]`; only an optional user-supplied mask may follow.

Record resolution separately from the prompt: semantic high-resolution intent does not prove a pixel size. Structured platform guidance uses `unknown + none + null`, or binds `known`, `observed`, and `user_reported` respectively to `authoritative_record`, `inspected_file_metadata`, and `user_report` plus actual positive width/height evidence.

### B. Constrained Local Edit

Choose `constrained_local_edit` when:

- the repair region and its physical consequences can be bounded;
- pixels outside the region remain authoritative;
- the edit does not require global re-solving of perspective, object count, lighting, or occlusion;
- removals include the complete cleanup closure, not just the foreground silhouette.

Escalate to isomorphic reconstruction when local defects are connected through global structure or when several patches would create inconsistent geometry.

In the structured manual action stage, put the target at `inputs[0]`; bounded references or an optional user-supplied mask may follow.

### C. Single-Stage Isomorphic Reconstruction

Choose `single_stage_isomorphic` when:

- the same composition is required;
- the target's scene graph, camera intent, and relative layout are recoverable;
- geometry errors are bounded enough for one reconstruction pass;
- references are absent or have narrow, non-conflicting roles;
- reference contamination risk for camera, crop, layout, count, and identity is low;
- no intermediate structure asset must be frozen for costly downstream work;
- exact text or identity is either not required or handled by an exact-asset lane.

The target remains the protected-structure authority. References may contribute only declared attributes.

Put the target at `inputs[0]`. Every authority required by the planned external stage must be supplied by a source actually listed for that stage, not merely named elsewhere in the contract.

### D. Staged Structure to Realism

Choose `staged_structure_to_realism` when any of these is material:

- melted, bent, fused, duplicated, or contradictory geometry is distributed across the image;
- the intended layout should survive but malformed contours must not;
- realism references use a different camera, crop, layout, object count, or subject arrangement;
- multiple references overlap, conflict, or carry high contamination risk;
- structure must be reviewed before adding material, construction, lighting, identity, or lens character;
- a wrong structural pass would make later iterations expensive.

#### Stage 1: Structure Master

- Upload the target first as `inputs[0]` and normally upload no realism, style, material, lighting, or identity references.
- The structured validator permits only the target plus an optional mask in this stage. Keep separate references, structure masters, and exact assets out of the structure-stage input set.
- Preserve recoverable composition, camera intent, crop, scene relationships, positions, relative scale, and occlusion.
- Correct malformed geometry rather than tracing it.
- Use neutral, low-distraction appearance so structural errors remain visible.
- Apply all explicit removal exceptions and their cleanup closure.
- The fresh text package remains `prompt_package_ready`. After the user manually runs the prompt externally and imports the actual result with bound provenance, that imported asset may use `structure_master_candidate`.

Do not proceed until the user explicitly approves the candidate for the next stage.

#### Stage 2: Realism Reconstruction

- Upload the approved structure master first. It is the sole authority for protected structure.
- Upload each reference after it, in the declared order, with an attribute-level role and `must_not_inherit` list.
- References may supply only authorized material, construction finish, lighting, color, lens response, surface realism, or exact identity attributes.
- Exclude the original problem target by default so its malformed geometry cannot re-enter the result.
- The text package remains `prompt_package_ready` until a user-manual external result is imported with bound provenance; only that imported result may use `candidate_unapproved`.

#### Limited Original-Target Reuse

Reuse the original target in Stage 2 only when all of the following hold:

- it is the only available evidence for a necessary attribute that the approved master does not carry;
- the reused attribute is explicitly named and does not include protected structure;
- every allowed reuse path is concrete; wildcard or generic grants such as `style.*`, `everything.*`, and `content.*` are forbidden;
- a crop, mask, or exact-asset lane cannot preserve that evidence more safely;
- the contract records a scoped justification, allowed attributes, and explicit denial of protected structure;
- contamination risk and the resulting uncertainty are disclosed.

Prefer a cropped identity or texture reference over re-uploading the whole contaminated target.

### E. Exact-Asset Composite

Use `exact_asset_composite` as a primary mode or auxiliary lane when product geometry, face identity, character identity, logo, label, typography, interface layout, or another truth-sensitive asset must remain exact.

The direct-copy external prompt may request a clean plate, environment, lighting integration, or contact-shadow treatment, but it must not ask the user-operated platform to redraw the truth-sensitive asset as if the result were exact. Require authoritative pixels, official artwork, an approved render, or other declared exact evidence. If no such evidence exists, keep the attribute unresolved.

In a structured contract, an `exact_asset` counts as used evidence only when it enters a `composite` stage. The manual composite plan must contain at least one exact asset and a base: either a target or structure master in its inputs, or `base_stage_id` naming an earlier actionable external stage. Supplying exact artwork without a base is not a substantive composite plan, and supplying it to structure, realism, pixel, local, or isomorphic does not convert those stages into exact compositing.

For every `required_exact` attribute, the covering resolved authority row must name one valid exact-evidence asset as its sole primary, and that primary asset itself must appear in a compatible manual external stage. A plausible or non-exact source cannot remain primary while the exact asset sits only in `allow`; likewise, using a secondary exact source does not compensate for leaving the authority primary unused.

## 3. When Not to Use Two Stages

Do not mechanically stage the task when:

- a traceable pixel operation fully solves the defect;
- a bounded local edit preserves the rest of the image more reliably;
- the target is already structurally correct and an unnecessary intermediate external result would add drift;
- the user wants a new camera, crop, layout, or concept rather than isomorphic reconstruction;
- the image is evidence and synthesis would destroy evidentiary integrity;
- exact identity or text would be regenerated without an exact-asset lane;
- no evidence can support the claimed structural correction;
- the second stage has no evidence-backed purpose and would only add generic model priors.

Use `structure_master_candidate` only for an actual user-manual external structure result that has been imported with provenance. Do not label a structure-only stage set `candidate_unapproved`; reserve that state for an imported downstream or otherwise non-structure-only result. A fresh structure plan is `prompt_package_ready`. `qa_failed_directional_retry_ready` requires a failed imported external result plus a directed text retry package.

## 4. Zero References and Unknown Roles

Zero references is valid. The Skill can still diagnose, route to a manual pixel/local workflow, compile a single-stage reconstruction prompt, or prepare a neutral structure-master prompt. If the user requests evidence-specific material, identity, or construction realism without references, state the missing evidence and stop the affected claim. Generic learned-prior realism may be offered only as a `chosen` look in an external-platform prompt, never as verified truth.

When a reference role is unknown:

1. inspect the image;
2. keep its role state `unknown` while the evidence does not support a role;
3. do not give it resolved primary/allow authority or upload it while it remains unknown;
4. promote the role to `inferred` only with recorded visual evidence, or to `chosen` only with a recorded decision, then give it the narrowest safe authority;
5. ask the user only if different role choices would materially alter the output or factual boundary; otherwise leave the reference unused and preserve the unknown.

## 5. Directional Mode Changes

If QA fails, change the smallest defect-owning decision:

- pixel failure -> direct the user to adjust the external pixel operation or settings;
- bounded patch failure -> expand or redefine the repair closure;
- structure drift -> provide a delta prompt for the user to rerun the external structure stage;
- reference pollution -> narrow or remove the offending reference authority;
- identity or text drift -> move the attribute to an exact-asset lane;
- insufficient evidence -> stop and request evidence instead of adding prompt intensity.

Never instruct the user to rerun all external stages blindly after a localized failure.
