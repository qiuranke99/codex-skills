# Failure Modes And Audit

Run this checklist before presenting a final Kling prompt.

## Common Failure Modes

| Failure | Prompt-level mitigation |
|---|---|
| Identity drift across cuts | Use Omni elements or explicit identity anchors; label the same subject consistently; avoid re-describing identity differently in later shots. |
| Product/logo warping | Anchor exact product image/element early; request stable logo placement and readable packaging; avoid transformations that bend the logo unless intended. |
| Sliding feet / moonwalk | Add heel-to-toe contact, visible weight transfer, matched tracking speed, surface friction, and ground contact shadows. |
| Floating hands / extra fingers | Anchor hands to objects; describe grip/contact; add targeted avoidances for fused fingers, extra fingers, morphing hands. |
| Random camera drift | Specify locked tripod, smooth tracking, or one dominant camera move; avoid mixed camera commands. |
| Sudden zooms | State no sudden zoom if the shot should be stable; use slow push-in if zoom-like emphasis is needed. |
| Multi-character confusion | Give each character a stable label and role; bind dialogue to label and visible action. |
| Weak lip-sync or speaker ambiguity | Pair speaker, tone, language/accent, and line in the same shot. Keep lines short. |
| Overpacked duration | Use one primary action per shot. Split scene changes into shots. Reduce plot beats for 3-8 second outputs. |
| Flicker / unstable lighting | Describe stable lighting source; avoid many simultaneous light changes; add no flicker only when relevant. |
| Unmotivated cinematic filler | Replace generic style words with camera, light, lens, material, and action specifics. |

## Final Audit Checklist

Before output, answer internally:

- Is the target model chosen and justified?
- Does every referenced asset have a clear job?
- Are identity/product anchors front-loaded?
- Does each shot have duration, framing, one main action, and one camera behavior?
- Are physical mechanics described where motion fidelity matters?
- Is audio/dialogue assigned to visible speakers/actions?
- Are constraints target-specific rather than invented?
- Are negative/avoidance clauses short and failure-specific?
- Are there contradictions: static vs orbit, preserve logo vs melt product, first frame vs new opening composition?
- Is the prompt usable even if the user gave only a rough idea?

## When To Ask A Question

Ask at most one or two questions only when:

- The user references an asset but gives no clue whether it is identity, scene, motion, style, or audio.
- A brand/product/person must be preserved exactly but no reference exists.
- The target surface matters because the user asks for API fields, payloads, or a provider-specific workflow.
- The requested output violates known limits or safety constraints.

Otherwise infer and state assumptions.

## Negative Clause Builder

Use only relevant clauses:

- People close-up: `avoid facial warping, drifting eye direction, unstable lip sync`.
- Hands/object: `avoid extra fingers, fused fingers, floating hands, object passing through fingers`.
- Walking/running: `avoid sliding feet, moonwalk motion, foot-ground mismatch`.
- Product/logo: `avoid warped logo, unreadable text, changing package proportions`.
- Camera: `avoid sudden zoom, random camera drift, handheld shake unless specified`.
- Multi-shot identity: `avoid outfit drift, changing body proportions, inconsistent face or product color`.

Do not dump every negative clause into every prompt.
