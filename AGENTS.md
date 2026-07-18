# codex-skills Agent Instructions

The current checkout is the canonical maintenance workspace for its user-created Codex skills.

## Operating Model

- Treat files in this project as the source of truth. Threads may coordinate work, but they must not become the canonical record for skill behavior.
- Use `README.md` for repository-level purpose and layout.
- Use `SKILLS_INDEX.md` for the inventory of maintained skills and Codex discovery junctions.
- Use each skill's own `SKILL.md` as the authoritative behavior contract for that skill.
- Keep task-specific scratch work in task threads or temporary files only when needed; do not promote it into long-term project state unless the user asks or the change is part of a deliberate maintenance decision.

## Thread Policy

- Use one pinned project thread as the long-term coordination thread for the current checkout.
- Create temporary task threads under this project when work is scoped, experimental, or potentially noisy.
- Do not create projectless threads for this workspace unless the user explicitly asks for a projectless thread.
- Archive temporary threads after their output has either been merged into project files or intentionally discarded.

## Skill Quality Bar

Every maintained skill should have:

- A `SKILL.md` with a clear trigger, boundary, and completion contract.
- Stable examples, fixtures, scripts, or tests when the skill contains repeatable mechanics.
- Explicit source, evidence, and failure-mode handling when the skill performs research or planning.
- No hidden reliance on stale chat context.

## Maintenance Workflow

Before changing a skill:

1. Read the target skill's `SKILL.md` completely.
2. Inspect any referenced files that define behavior, examples, scripts, tests, schemas, or templates.
3. Preserve the existing skill boundary unless the user explicitly asks to expand or narrow it.
4. Make minimal, source-backed edits.
5. Run the most relevant available verification: tests, scripts, schema checks, example dry runs, or direct file inspection.
6. Update `SKILLS_INDEX.md` only when inventory, status, purpose, path, or discovery entries actually change.

## GitHub Sync Requirement

- After creating, optimizing, updating, renaming, deleting, archiving, installing, or otherwise materially changing any skill, synchronize the resulting project state to the user's public GitHub repository: `qiuranke99/codex-skills` (`https://github.com/qiuranke99/codex-skills`).
- Treat GitHub synchronization as part of the completion criteria for skill-maintenance work, not as an optional follow-up.
- Before syncing, review the working tree and avoid bundling unrelated local changes unless the user explicitly wants them included.
- If credentials, network access, repository state, or user policy prevents a successful sync, report the exact blocker and list the unsynced files. Do not claim the skill work is fully complete while required GitHub sync remains undone.

## Root Hygiene

The root should stay sparse. Keep durable root files limited to project coordination, inventory, top-level Skill packages, `.github/`, and the single `high-control-ai-tvc/` production-system distribution. Skill implementation content belongs inside its own skill directory.

## High-Control AI TVC Production System

- Every top-level Skill is independently installable, discoverable, invocable,
  and testable. Its own package is the runtime authority. No Skill may require
  `high-control-ai-tvc`, a suite receipt, a release-control launcher, or a
  sibling package before performing its declared core work.
- Treat `high-control-ai-tvc/SUITE_MANIFEST.json` only as the inventory for the
  explicitly selected 15-Skill aggregate compatibility profile. Never copy the
  Skill packages into the subsystem, and never use that manifest to decide
  whether an individual Skill is ready.
- Cross-Skill transformations belong to the optional aggregate integrator.
  Standalone packages emit portable, hash-bound artifacts; they do not import
  sibling implementations at runtime.
- The supported route is Omni / all-reference / multimodal
  reference-to-video. Do not substitute T2V, standalone single-image I2V,
  first/last-frame, endpoint-frame, or interpolation workflows.
- The production endpoint is a provider-ready P2 package. This repository does
  not submit paid video generations and does not own music, final editing,
  color mastering, or independent output QC.
- Ordinary directing gaps are inference work. Do not return a rough script to
  the user merely because it lacks professional camera, blocking, continuity,
  product-use, or timing language. Exact claims, packaging copy, regulated
  facts, identity, and mechanism evidence remain source-bound.
- Before changing the aggregate compatibility contract, installer, release
  manager, or end-to-end SOP, read `high-control-ai-tvc/docs/SOP.md` in full
  and run aggregate validation. A change confined to one Skill requires that
  package's own tests plus the root standalone-isolation validator; aggregate
  validation is integration regression, never an invocation gate.

## Public Repository Data Boundary

- Never commit customer scripts, private briefs, identities, reference media,
  Project Canon, storyboards, keyframes, V1/V2 media, P2 payloads, provider
  credentials, `.env` files, certificates, or secrets.
- Real production projects live outside this repository. The installer only
  exposes Skill directories to Codex; it does not import project data.
- Public visibility is not evidence that third-party assets or customer data
  may be redistributed.
