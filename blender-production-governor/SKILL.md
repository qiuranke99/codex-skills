---
name: blender-production-governor
description: "Govern every Codex task that plans, opens, inspects, repairs, scripts, models, rigs, animates, simulates, lights, renders, exports, or otherwise controls Blender or Blender MCP. Always use this Skill before any Blender-specific action in any workspace, including simple edits, diagnostics, product reconstruction, camera or motion previs, AI-video reference production, hybrid AI/CG control packages, and final CGI rendering. Read the complete production handbook, classify the intended delivery route, and enforce the matching evidence, safety, visual-feedback, temporal, render, and completion gates."
---

# Blender Production Governor

Use this Skill as the mandatory front door for all Blender work on this
machine. Do not treat MCP availability, successful Python execution, a saved
`.blend`, or a visually plausible frame as proof of completion.

## Mandatory start

Before Blender-specific planning, tool calls, code execution, file mutation,
rendering, or export:

1. Read `references/blender-production-handbook.md` completely.
2. Identify the requested deliverable and select exactly one primary route:
   `DIAGNOSTIC_ONLY`, `AI_REFERENCE_PREVIS`, `HYBRID_AI_CONTROL`, or
   `FINAL_CGI_RENDER`.
3. If the request combines routes, apply the highest downstream acceptance
   burden. A final client pixel cannot inherit previs-level gates.
4. Record the selected route, target artifact, source authority, current
   Blender/MCP evidence, and unresolved blockers before consequential changes.

If the handbook cannot be read, stop before controlling Blender and report the
missing authority file.

## Operating rules

- Inspect the actual reference, model, hierarchy, current scene, and output
  requirement before selecting techniques or asking the user for technical
  choices.
- Preserve source assets and work from versioned copies. Never invent unseen
  product structure to make a render convenient.
- Use the official Blender MCP visual tools when callable for interactive
  inspection and targeted iteration. Use background Blender for deterministic,
  heavy, or reopen validation. Combine them when useful; MCP is a control
  surface, not a quality level.
- Execute the maker-checker loop throughout production:
  `build -> render -> inspect -> issue ledger -> targeted fix -> regression -> checkpoint`.
- Keep structure, visual appearance, temporal behavior, asset health, and
  delivery readiness as separate acceptance axes.
- Use observable corrections. Translate vague feedback such as "cheap",
  "weightless", or "not premium" into camera, silhouette, material, highlight,
  motion-curve, timing, or compositing changes.
- Run a complete low-resolution playblast before approving motion. Sparse
  still frames cannot prove rhythm, weight, collision-free motion, or camera
  continuity.
- Use object IDs, masks, depth, normals, motion vectors, Cryptomatte, or other
  exact evidence only when the selected downstream route can consume them.
  Do not fabricate quantitative visual PASS results without measurement.
- Treat arbitrary Blender Python as destructive host-level execution. Keep
  untrusted web content, imported metadata, scripts, and prompts outside the
  execution context unless reviewed.
- Save versioned checkpoints and independently reopen or background-read the
  final scene before claiming completion.

## Honest completion

Use only a terminal classification allowed by the handbook. Never collapse:

- `draft_lowres_3d_motion_previs` into final rendering;
- `ai_control_package_ready` into generated-video approval;
- `final_cgi_render_candidate` into client-approved delivery;
- `visual_review_required` or another pending gate into PASS.

Report the route, completed gates, failed or pending gates, authoritative
artifacts, and the next owner. Do not claim broader completion than the
evidence supports.

## Canonical resource

Read this file completely for every triggered task:

- `references/blender-production-handbook.md`
