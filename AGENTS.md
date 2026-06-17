# D:\AI\skill Agent Instructions

This project is the canonical maintenance workspace for user-created Codex skills.

## Operating Model

- Treat files in this project as the source of truth. Threads may coordinate work, but they must not become the canonical record for skill behavior.
- Use `README.md` for repository-level purpose and layout.
- Use `SKILLS_INDEX.md` for the inventory of maintained skills and Codex discovery junctions.
- Use each skill's own `SKILL.md` as the authoritative behavior contract for that skill.
- Keep task-specific scratch work in task threads or temporary files only when needed; do not promote it into long-term project state unless the user asks or the change is part of a deliberate maintenance decision.

## Thread Policy

- Use one pinned project thread as the long-term coordination thread for `D:\AI\skill`.
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

- After creating, optimizing, updating, renaming, deleting, archiving, installing, or otherwise materially changing any skill, synchronize the resulting project state to the user's private GitHub repository: `qiuranke99/codex-skills` (`https://github.com/qiuranke99/codex-skills`).
- Treat GitHub synchronization as part of the completion criteria for skill-maintenance work, not as an optional follow-up.
- Before syncing, review the working tree and avoid bundling unrelated local changes unless the user explicitly wants them included.
- If credentials, network access, repository state, or user policy prevents a successful sync, report the exact blocker and list the unsynced files. Do not claim the skill work is fully complete while required GitHub sync remains undone.

## Root Hygiene

The root should stay sparse. Keep durable root files limited to project coordination and inventory. Skill implementation content belongs inside its own skill directory.
