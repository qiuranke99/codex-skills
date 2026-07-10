# Codex Skills Index

Migration date: 2026-05-27

Last updated: 2026-07-10

Canonical root: `D:\AI\skill`

Codex discovery root: `C:\Users\Administrator\.codex\skills`

## Maintained Skills

| Skill | Target path | Purpose | Original path | Status |
| --- | --- | --- | --- | --- |
| `character-final-lock-board` | `D:\AI\skill\character-final-lock-board` | Request a horizontal 16:9 final character board with nonblocking built-in dimensions, retain `high_angle_evidence: required | optional | off`, then publish the complete bound generation and image-specific 4K prompts with both hashes together in the later final main result. | `D:\AI视觉工作室\.agents\skills\character-final-lock-board` | Active |
| `character-casting-lock-board` | `D:\AI\skill\character-casting-lock-board` | Request horizontal 16:9 text-free casting boards with nonblocking built-in dimensions; every generated main/extension board receives a complete generation+4K prompt pair and both hashes in the later final main result. | `D:\AI视觉工作室\.agents\skills\character-casting-lock-board` | Active |
| `single-face-character-lock-board` | `D:\AI\skill\single-face-character-lock-board` | Request a horizontal 16:9 one-face topology board with nonblocking built-in dimensions, then publish the complete generation and topology-preserving 4K prompts with both hashes together in the later final main result. | `D:\AI视觉工作室\.agents\skills\single-face-character-lock-board` | Active |
| `cinematic_shot_image_explorer` | `D:\AI\skill\cinematic_shot_image_explorer` | Turn ideas, rough prompts, reference images, products, characters, scenes, or visual directions into exactly 10 cinematic film-still image prompts and 10 generated images. | `D:\AI视觉工作室\.agents\skills\cinematic_shot_image_explorer` | Active |
| `cinematic_world_builder` | `D:\AI\skill\cinematic_world_builder` | Turn ideas, settings, atmospheres, cultures, places, names, genres, image descriptions, or reference images into a coherent cinematic world and exactly 9 film-still visual prompts. | `D:\AI视觉工作室\.agents\skills\cinematic_world_builder` | Active |
| `multi-angle-product-identity-lock-board` | `D:\AI\skill\multi-angle-product-identity-lock-board` | Request a horizontal 16:9 six-view board with nonblocking built-in dimensions, keep optional native-resolution evidence separate, and publish the complete generation and source-bound 4K prompts with both hashes together in the later final main result. | `D:\AI视觉工作室\.agents\skills\multi-angle-product-identity-lock-board` | Active |
| `packaging-product-identity-label-lock-board` | `D:\AI\skill\packaging-product-identity-label-lock-board` | Request a horizontal 16:9 packaging geometry/layout board with nonblocking built-in dimensions, then publish both complete prompts and hashes together; exact copy still requires deterministic composition or OCR/field/QR/barcode evidence. | `D:\AI视觉工作室\.agents\skills\packaging-product-identity-label-lock-board` | Active |
| `material-sensitive-product-master-asset-board` | `D:\AI\skill\material-sensitive-product-master-asset-board` | Request one horizontal 16:9 material master board with nonblocking built-in dimensions, then publish the complete generation and material-preserving 4K prompts with both hashes together in the later final main result. | `D:\AI视觉工作室\.agents\skills\material-sensitive-product-master-asset-board` | Active |

## Codex Discovery Entries

As of 2026-07-04, this workspace exposes the following user-maintained Codex discovery entries.

| Codex entry | Junction target |
| --- | --- |
| `C:\Users\Administrator\.codex\skills\character-final-lock-board` | `D:\AI\skill\character-final-lock-board` |
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
- High-angle character continuity is maintained inside `character-final-lock-board` as the `high_angle_evidence` mode; the former standalone package was retired on 2026-07-10.
- Previous entries and obsolete duplicate sources were moved to `D:\AI\skill-migration-backups\20260527-112423`.
- Do not add loose skill files directly under `D:\AI\skill`; each skill must live in its own folder containing `SKILL.md`.
