# Codex Skills Index

Migration date: 2026-05-27

Canonical root: `D:\AI\skill`

Codex discovery root: `C:\Users\Administrator\.codex\skills`

| Skill | Target path | Purpose | Original path | Status |
| --- | --- | --- | --- | --- |
| `cinematic-composition-prompt-director` | `D:\AI\skill\cinematic-composition-prompt-director` | Converts scene ideas, rough prompts, or image observations into exactly 10 film-still composition prompts with camera-language diversity and audit gates. | `C:\Users\Administrator\.codex\skills\cinematic-composition-prompt-director` | active |
| `ai-visual-director` | `D:\AI\skill\ai-visual-director` | Story-first AI visual director for product-ad briefs, product images, and visual references; no fixed storyboard house style; enforces premium beauty/skincare/FMCG/luxury category strategy plus creative director, director, screenwriter, art director, and Google Omni prompt expert gates before dynamic segment storyboards and structured Omni video prompts can pass validation. | `https://github.com/qiuranke99/ai-visual-director-skill` | active |
| `seedance-prompt-en` | `D:\AI\skill\seedance-prompt-en` | English prompt writing guide for Jimeng Seedance 2.0 multimodal AI video generation, including @ references, camera language, extension/editing, ads, short dramas, and educational content. | `https://github.com/dexhunter/seedance2-skill` | active |
| `seedance-prompt-zh` | `D:\AI\skill\seedance-prompt-zh` | Chinese prompt writing guide for Jimeng Seedance 2.0 multimodal AI video generation, including @ references, camera replication, effects, extension/editing, ads, short dramas, and educational content. | `https://github.com/dexhunter/seedance2-skill/tree/main/zh` | active |
| `kling-promot` | `D:\AI\skill\kling-promot` | World-class Kling 3.0 and Kling VIDEO 3.0 Omni prompt director for text/image/video/audio references, elements, custom multi-shot, native audio, dialogue, and API-oriented prompt payloads. | Local skill created from official Kling documentation plus prompt-pattern research; display name: `Kling-Promot` | active |

## Codex Discovery Entries

As of 2026-06-22, the five user-maintained skills above are installed for Codex discovery as Windows directory junctions:

| Codex entry | Junction target |
| --- | --- |
| `C:\Users\Administrator\.codex\skills\cinematic-composition-prompt-director` | `D:\AI\skill\cinematic-composition-prompt-director` |
| `C:\Users\Administrator\.codex\skills\ai-visual-director` | `D:\AI\skill\ai-visual-director` |
| `C:\Users\Administrator\.codex\skills\seedance-prompt-en` | `D:\AI\skill\seedance-prompt-en` |
| `C:\Users\Administrator\.codex\skills\seedance-prompt-zh` | `D:\AI\skill\seedance-prompt-zh` |
| `C:\Users\Administrator\.codex\skills\kling-promot` | `D:\AI\skill\kling-promot` |

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
