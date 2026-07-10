# Codex Skills Index

Migration date: 2026-05-27

Last updated: 2026-07-10

Canonical root: `D:\AI\skill`

Codex discovery root: `C:\Users\Administrator\.codex\skills`

## Maintained Skills

| Skill | Target path | Purpose | Original path | Status |
| --- | --- | --- | --- | --- |
| `character-final-lock-board` | `D:\AI\skill\character-final-lock-board` | Lock one selected character in an exact 16:9 final board, retain `high_angle_evidence: required | optional | off`, disclose the bound generation prompt, and produce an inspected-board-specific source-bound 4K handoff with separate QA/approval. | `D:\AI视觉工作室\.agents\skills\character-final-lock-board` | Active |
| `character-casting-lock-board` | `D:\AI\skill\character-casting-lock-board` | Generate exact 16:9 text-free casting boards for one identity; every generated main/extension board receives its own generation prompt trace and inspected-board-specific source-bound 4K prompt/hash/handoff. | `D:\AI视觉工作室\.agents\skills\character-casting-lock-board` | Active |
| `single-face-character-lock-board` | `D:\AI\skill\single-face-character-lock-board` | Generate an exact 16:9 one-face topology board—one visible-face bust plus headless front/back views—and a source-bound 4K handoff that must preserve the same topology. | `D:\AI视觉工作室\.agents\skills\single-face-character-lock-board` | Active |
| `cinematic_shot_image_explorer` | `D:\AI\skill\cinematic_shot_image_explorer` | Turn ideas, rough prompts, reference images, products, characters, scenes, or visual directions into exactly 10 cinematic film-still image prompts and 10 generated images. | `D:\AI视觉工作室\.agents\skills\cinematic_shot_image_explorer` | Active |
| `cinematic_world_builder` | `D:\AI\skill\cinematic_world_builder` | Turn ideas, settings, atmospheres, cultures, places, names, genres, image descriptions, or reference images into a coherent cinematic world and exactly 9 film-still visual prompts. | `D:\AI视觉工作室\.agents\skills\cinematic_world_builder` | Active |
| `multi-angle-product-identity-lock-board` | `D:\AI\skill\multi-angle-product-identity-lock-board` | Generate an exact 16:9 six-view board for low-risk products, separate native from external 4K evidence, and deliver a source-bound 4K regeneration handoff that preserves cross-view geometry. | `D:\AI视觉工作室\.agents\skills\multi-angle-product-identity-lock-board` | Active |
| `packaging-product-identity-label-lock-board` | `D:\AI\skill\packaging-product-identity-label-lock-board` | Generate an exact 16:9 packaging geometry/layout board and source-bound 4K handoff; exact copy still requires source artwork plus deterministic composition or OCR/field/QR/barcode evidence. | `D:\AI视觉工作室\.agents\skills\packaging-product-identity-label-lock-board` | Active |
| `material-sensitive-product-master-asset-board` | `D:\AI\skill\material-sensitive-product-master-asset-board` | Generate one exact 16:9 material master board and an inspected-board-specific source-bound 4K handoff that preserves refraction, reflection, layer thickness, liquid state, and material evidence. | `D:\AI视觉工作室\.agents\skills\material-sensitive-product-master-asset-board` | Active |

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
