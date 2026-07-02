# Codex Skills Index

Migration date: 2026-05-27

Last updated: 2026-07-02

Canonical root: `D:\AI\skill`

Codex discovery root: `C:\Users\Administrator\.codex\skills`

## Maintained Skills

| Skill | Target path | Purpose | Original path | Status |
| --- | --- | --- | --- | --- |
| `character-final-lock-board` | `D:\AI\skill\character-final-lock-board` | Generate final locked character asset boards from person/model and wardrobe references using direct image generation plus QA. | `D:\AI视觉工作室\.agents\skills\character-final-lock-board` | Active |
| `character-final-lock-board-high-angle-version` | `D:\AI\skill\character-final-lock-board-high-angle-version` | Generate high-angle final character lock boards from person/model and wardrobe references using direct image generation plus QA. | `D:\AI视觉工作室\.agents\skills\character-final-lock-board-high-angle-version` | Active |
| `cinematic_shot_image_explorer` | `D:\AI\skill\cinematic_shot_image_explorer` | Turn ideas, rough prompts, reference images, products, characters, scenes, or visual directions into exactly 10 cinematic film-still image prompts and 10 generated images. | `D:\AI视觉工作室\.agents\skills\cinematic_shot_image_explorer` | Active |

## Codex Discovery Entries

As of 2026-07-02, this workspace exposes the following user-maintained Codex discovery entries.

| Codex entry | Junction target |
| --- | --- |
| `C:\Users\Administrator\.codex\skills\character-final-lock-board` | `D:\AI\skill\character-final-lock-board` |
| `C:\Users\Administrator\.codex\skills\character-final-lock-board-high-angle-version` | `D:\AI\skill\character-final-lock-board-high-angle-version` |
| `C:\Users\Administrator\.codex\skills\cinematic_shot_image_explorer` | `D:\AI\skill\cinematic_shot_image_explorer` |

## Skipped Sources

The following classes are intentionally excluded from this archive:

- `C:\Users\Administrator\.codex\skills\.system`
- `C:\Users\Administrator\.codex\plugins\cache`
- `openai-bundled` plugin skills
- `openai-curated` plugin skills
- plugin cache, runtime, dependency, marketplace, and generated install directories

## Notes

- `D:\AI\skill` is the canonical maintenance location for these user-created skills.
- `C:\Users\Administrator\.codex\skills` keeps only the Codex discovery entries for these skills, as junctions pointing back to `D:\AI\skill`.
- Previous entries and obsolete duplicate sources were moved to `D:\AI\skill-migration-backups\20260527-112423`.
- Do not add loose skill files directly under `D:\AI\skill`; each skill must live in its own folder containing `SKILL.md`.
