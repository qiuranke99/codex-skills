# Codex Skills Index

Migration date: 2026-05-27

Canonical root: `D:\AI\skill`

Codex discovery root: `C:\Users\Administrator\.codex\skills`

| Skill | Target path | Purpose | Original path | Status |
| --- | --- | --- | --- | --- |
| `source-url-reference-research` | `D:\AI\skill\source-url-reference-research` | Source URL first visual reference research for images/videos, with evidence links and no original-media downloads. | `C:\Users\Administrator\.codex\skills\source-url-reference-research` | active |
| `commercial-video-project-planning` | `D:\AI\skill\commercial-video-project-planning` | Source-aware planning for commercial or product-video project folders, including brief, selling points, creative treatment, budget plan, and production handoff. | `C:\Users\Administrator\.codex\skills\commercial-video-project-planning` | active |
| `reference-video-product-adapter` | `D:\AI\skill\reference-video-product-adapter` | Adapts a reference video plus product materials into an AI video plan, shot list, storyboard prompt, platform prompt, and asset checklist. | `C:\Users\Administrator\.codex\skills\reference-video-product-adapter`; duplicate identical source: `D:\ai-workspace\03-workflows\codex\skills\reference-video-product-adapter` | active |
| `cinematic-composition-prompt-director` | `D:\AI\skill\cinematic-composition-prompt-director` | Converts scene ideas, rough prompts, or image observations into exactly 10 film-still composition prompts with camera-language diversity and audit gates. | `C:\Users\Administrator\.codex\skills\cinematic-composition-prompt-director` | active |

## Codex Discovery Entries

As of 2026-06-03, the three user-maintained skills above are installed for Codex discovery as Windows directory junctions:

| Codex entry | Junction target |
| --- | --- |
| `C:\Users\Administrator\.codex\skills\source-url-reference-research` | `D:\AI\skill\source-url-reference-research` |
| `C:\Users\Administrator\.codex\skills\commercial-video-project-planning` | `D:\AI\skill\commercial-video-project-planning` |
| `C:\Users\Administrator\.codex\skills\reference-video-product-adapter` | `D:\AI\skill\reference-video-product-adapter` |
| `C:\Users\Administrator\.codex\skills\cinematic-composition-prompt-director` | `D:\AI\skill\cinematic-composition-prompt-director` |

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
