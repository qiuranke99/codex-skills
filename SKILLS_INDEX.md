# Codex Skills Index

Migration date: 2026-05-27

Last updated: 2026-07-04

Canonical root: `D:\AI\skill`

Codex discovery root: `C:\Users\Administrator\.codex\skills`

## Maintained Skills

| Skill | Target path | Purpose | Original path | Status |
| --- | --- | --- | --- | --- |
| `character-final-lock-board` | `D:\AI\skill\character-final-lock-board` | Generate final locked character asset boards from person/model and wardrobe references using direct image generation, exact prompt output, prompt-image traceability, and QA. | `D:\AI视觉工作室\.agents\skills\character-final-lock-board` | Active |
| `character-final-lock-board-high-angle-version` | `D:\AI\skill\character-final-lock-board-high-angle-version` | Generate high-angle final character lock boards from person/model and wardrobe references using direct image generation plus QA. | `D:\AI视觉工作室\.agents\skills\character-final-lock-board-high-angle-version` | Active |
| `character-casting-lock-board` | `D:\AI\skill\character-casting-lock-board` | Generate text-free film casting contact-board style character asset boards from character reference images using direct image generation, risk-triggered detail boards, exact image generation prompt output, and QA. | `D:\AI视觉工作室\.agents\skills\character-casting-lock-board` | Active |
| `single-face-character-lock-board` | `D:\AI\skill\single-face-character-lock-board` | Directly generate one Single-Face Character Lock Board from character references using Codex built-in `/image gen`, output the final image generation prompt, and enforce exactly one visible face plus headless front/back full-body views. | `D:\AI视觉工作室\.agents\skills\single-face-character-lock-board` | Active |
| `cinematic_shot_image_explorer` | `D:\AI\skill\cinematic_shot_image_explorer` | Turn ideas, rough prompts, reference images, products, characters, scenes, or visual directions into exactly 10 cinematic film-still image prompts and 10 generated images. | `D:\AI视觉工作室\.agents\skills\cinematic_shot_image_explorer` | Active |
| `cinematic_world_builder` | `D:\AI\skill\cinematic_world_builder` | Turn ideas, settings, atmospheres, cultures, places, names, genres, image descriptions, or reference images into a coherent cinematic world and exactly 9 film-still visual prompts. | `D:\AI视觉工作室\.agents\skills\cinematic_world_builder` | Active |
| `multi-angle-product-identity-lock-board` | `D:\AI\skill\multi-angle-product-identity-lock-board` | Directly generate native-4K-verified six-view product identity lock boards for low-risk products using Codex built-in `/image gen`, exact `english_prompt_used` traceability, pixel-dimension verification, and QA. | `D:\AI视觉工作室\.agents\skills\multi-angle-product-identity-lock-board` | Active |
| `packaging-product-identity-label-lock-board` | `D:\AI\skill\packaging-product-identity-label-lock-board` | Directly generate clean 8-angle packaging product identity and label-copy lock boards with logo, key copy, material details, high/low perspective, final image-generation prompt output, QA, and no non-product text pollution. | `D:\AI视觉工作室\.agents\skills\packaging-product-identity-label-lock-board` | Active |
| `material-sensitive-product-master-asset-board` | `D:\AI\skill\material-sensitive-product-master-asset-board` | Directly generate one 16:9 Material-Sensitive Product Master Asset Board for transparent, glass, acrylic, translucent, liquid, cream, crystal-cut, mirror-metal, high-reflective, frosted, or multi-layer-shell products using Codex built-in `/image gen`, a dominant hero anchor, complementary angles, material-response closeups, critical structure details, optional logo/text micro reference, optional state window, exact final image-generation prompt output, and QA. | `D:\AI视觉工作室\.agents\skills\material-sensitive-product-master-asset-board` | Active |

## Codex Discovery Entries

As of 2026-07-04, this workspace exposes the following user-maintained Codex discovery entries.

| Codex entry | Junction target |
| --- | --- |
| `C:\Users\Administrator\.codex\skills\character-final-lock-board` | `D:\AI\skill\character-final-lock-board` |
| `C:\Users\Administrator\.codex\skills\character-final-lock-board-high-angle-version` | `D:\AI\skill\character-final-lock-board-high-angle-version` |
| `C:\Users\Administrator\.codex\skills\character-casting-lock-board` | `D:\AI\skill\character-casting-lock-board` |
| `C:\Users\Administrator\.codex\skills\single-face-character-lock-board` | `D:\AI\skill\single-face-character-lock-board` |
| `C:\Users\Administrator\.codex\skills\cinematic_shot_image_explorer` | `D:\AI\skill\cinematic_shot_image_explorer` |
| `C:\Users\Administrator\.codex\skills\cinematic_world_builder` | `D:\AI\skill\cinematic_world_builder` |
| `C:\Users\Administrator\.codex\skills\multi-angle-product-identity-lock-board` | `D:\AI\skill\multi-angle-product-identity-lock-board` |
| `C:\Users\Administrator\.codex\skills\packaging-product-identity-label-lock-board` | `D:\AI\skill\packaging-product-identity-label-lock-board` |
| `C:\Users\Administrator\.codex\skills\material-sensitive-product-master-asset-board` | `D:\AI\skill\material-sensitive-product-master-asset-board` |

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
