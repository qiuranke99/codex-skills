# Test Cases

Use these cases for description routing, package-state tests, and forward tests. Do not use them as hidden expected answers in a fresh-context evaluation.

## Should Trigger

1. Multiple wheelchair references show frame, wheels, brakes, footrests, folding mechanism, fabric, logos, and folded/deployed states; user needs video-continuity assets.
2. Industrial robotic arm references show multiple joints, cable routing, end-effector interfaces, mixed metal/polymer surfaces, and several observed operating poses.
3. A stroller manual plus official photos show chassis, wheel assemblies, latch nodes, canopy, folded storage state, and marking locations.
4. A cinema camera rig has body, lens mount, ports, cage, handles, battery plate, buttons, textured grips, and detachable components that must stay consistent across keyframes.

## Should Not Trigger

1. One simple opaque speaker with clear silhouette and non-critical text needs one six-view board: route to a simple-product multi-angle identity workflow when available.
2. A perfume bottle's glass, liquid, and refraction are the primary risk: route to a material-response-first product workflow when available.
3. A label-heavy box requires exact copy and barcode layout: route to a packaging-copy-first identity workflow when available.
4. User wants a lifestyle ad, poster, or cinematic product scene: use ordinary creative production, not an identity package.
5. User wants prompts only, a simple upscale, source search, 3D CAD engineering, safety certification, or product redesign.

These routing alternatives are scope guidance, not runtime dependencies. Their absence never blocks an in-scope complex-product package; for an out-of-scope request, explain the mismatch without claiming that an unavailable workflow ran.

## Blocked And Boundary Cases

- Single front photo of a folding wheelchair: complete Stage 1, mark rear/underside/fold topology unknown, block Geometry and State boards, and do not generate a final lock board.
- Mixed references from two wheelchair revisions: return `blocked_identity_conflict` unless the variants can be separated.
- Logo is visible but unreadable: Marking may be `reference_locked`; never claim exact text.
- Open and closed states are shown, but the transition mechanics are hidden: endpoints may be recorded; block any depiction that invents intermediate mechanics.
- Material colors conflict under different grades: keep observed rendered colors separate, infer no base color without corroboration, and block Material Lock when unresolved.

## Package Contract Cases

- Full valid: all required boards and final board approved, all files/dimensions/hashes/QA present, one 4K mapping per approved asset.
- Partial valid: one evidence-supported board approved and mapped, required board blocked, final board blocked, package status `partial_approved`.
- Blocked valid: specification exists, Geometry blocked for missing source, no generated assets, status `blocked_source_insufficient`.
- Invalid complete: an approved asset lacks a 4K mapping.
- Invalid complete: a board remains `awaiting_post_generation_continuation`.
- Invalid source gate: State board is approved while its `source_gate` is blocked.
- Invalid 4K claim: `native_4k_claimed: true` without observed dimensions and provenance evidence.
