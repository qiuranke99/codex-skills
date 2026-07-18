# Codex Skills Index

Migration date: 2026-05-27

Last updated: 2026-07-18

Windows canonical checkout used by the existing workstation: `D:\AI\skill`

Current recommended user discovery root: `%USERPROFILE%\.agents\skills`

Legacy workstation discovery snapshot: `C:\Users\Administrator\.codex\skills`

Do not expose the same Skill name in both discovery roots.

## Independent Skill Packages

The repository maintains 16 independently installable and runnable Skill
packages. Fifteen may also be selected together as an optional High-Control AI
TVC compatibility profile:

- 13 core production Skills: six workflow owners plus seven Canon Asset Owners;
- 2 optional cinematic exploration Skills;
- one unique top-level directory per Skill, with no duplicate copies.

The optional profile's SOP, SVG, bulk installation tools, compatibility
manifest and workstation preflight live under
[`high-control-ai-tvc/`](high-control-ai-tvc/README.md). None is a prerequisite
for installing, invoking or accepting one Skill.
The production endpoint is a provider-ready P2 package. Actual paid video
generation, music, final editing, color mastering and independent output QC are
outside the distribution.

## Maintained Skills

| Skill | Target path | Purpose | Original path | Status |
| --- | --- | --- | --- | --- |
| `character-final-lock-board` | `D:\AI\skill\character-final-lock-board` | Request a horizontal 16:9 final character board with nonblocking built-in dimensions, retain `high_angle_evidence: required / optional / off`, publish the complete prompt pair, and expose approved identity/wardrobe artifacts for an optional external integrator. | `D:\AI视觉工作室\.agents\skills\character-final-lock-board` | Active |
| `character-casting-lock-board` | `D:\AI\skill\character-casting-lock-board` | Request horizontal 16:9 text-free casting boards with complete prompt pairs; casting stays pre-Canon unless explicitly selected as terminal character authority by an external integrator. | `D:\AI视觉工作室\.agents\skills\character-casting-lock-board` | Active |
| `single-face-character-lock-board` | `D:\AI\skill\single-face-character-lock-board` | Request a horizontal 16:9 one-face topology board, publish the complete topology-preserving prompt pair, and expose approved identity/wardrobe artifacts for an optional external integrator. | `D:\AI视觉工作室\.agents\skills\single-face-character-lock-board` | Active |
| `cinematic_shot_image_explorer` | `D:\AI\skill\cinematic_shot_image_explorer` | Turn ideas, rough prompts, reference images, products, characters, scenes, or visual directions into exactly 10 cinematic film-still image prompts and 10 generated images. | `D:\AI视觉工作室\.agents\skills\cinematic_shot_image_explorer` | Active |
| `cinematic_world_builder` | `D:\AI\skill\cinematic_world_builder` | Turn ideas, settings, atmospheres, cultures, places, names, genres, image descriptions, or reference images into a coherent cinematic world and exactly 9 film-still visual prompts. | `D:\AI视觉工作室\.agents\skills\cinematic_world_builder` | Active |
| `scene-canon-asset-pack` | `D:\AI\skill\scene-canon-asset-pack` | Explicit-only six-image Scene Canon pack: publish all six frozen prompts first, then complete a serial continuity-dependent non-decision-worker queue with motion envelope, coverage graph, strict runtime receipts, structured QA, and one-to-one 4K handoff. | `D:\AI视觉工作室\.agents\skills\scene-canon-asset-pack` | Active |
| `multi-angle-product-identity-lock-board` | `D:\AI\skill\multi-angle-product-identity-lock-board` | Request a horizontal 16:9 six-view opaque-product board, publish the complete prompt pair, and expose approved product-geometry artifacts for an optional external integrator. | `D:\AI视觉工作室\.agents\skills\multi-angle-product-identity-lock-board` | Active |
| `packaging-product-identity-label-lock-board` | `D:\AI\skill\packaging-product-identity-label-lock-board` | Build one compact borderless packaging video asset board with seven upright views, two source-grounded details by default, a source-cited copy ledger, deterministic overlays, evidence-bound QA, and an optional external Project Canon handoff. | `D:\AI视觉工作室\.agents\skills\packaging-product-identity-label-lock-board` | Active |
| `material-sensitive-product-master-asset-board` | `D:\AI\skill\material-sensitive-product-master-asset-board` | Request one horizontal 16:9 material master board, freeze source semantics and critical invariants, reject cross-panel topology drift, publish the complete material-preserving prompt pair, and expose accepted artifacts for an optional external integrator. | `D:\AI视觉工作室\.agents\skills\material-sensitive-product-master-asset-board` | Active |
| `ai-video-shot-script-director` | `D:\AI\skill\ai-video-shot-script-director` | Upgrade rough ideas or structured creative shot drafts into a validated Professional Shot Contract with stable Shot UIDs, closed timing, observable action, camera and continuity direction, inference provenance, and the shared Project Canon registry contract. | Created in place | Active |
| `ai-video-global-look-lock` | `D:\AI\skill\ai-video-global-look-lock` | Freeze Look Core, legal Look States, per-shot Look Deltas, independent visual references, and exact downstream prompt inheritance without changing intrinsic identity or product facts. | Created in place | Active |
| `ai-video-modular-storyboard` | `D:\AI\skill\ai-video-modular-storyboard` | Create exactly one independent editable frame per scripted shot, deterministic human review boards, and atomic one-shot or multi-shot replacement with dependency invalidation. | Created in place | Active |
| `ai-video-timed-animatic-previs-director` | `D:\AI\skill\ai-video-timed-animatic-previs-director` | Build a whole-ad V1 timing animatic and P1/K2-bound per-generation-unit V2 control previs with motion and physics tracks plus live media-probe evidence. | Created in place | Active |
| `ai-video-keyframe-continuity-pack` | `D:\AI\skill\ai-video-keyframe-continuity-pack` | Create K1 per-shot Omni-reference anchors and continuity ledgers, then an immutable P1-bound K2 boundary supplement; never endpoint-frame controls. | Created in place | Active |
| `ai-video-omni-reference-prompt-director` | `D:\AI\skill\ai-video-omni-reference-prompt-director` | Preflight and compile complete all-reference packages with Seedance 2.5-first semantics, capability-verified Seedance 2.0/provider renders, exact asset bindings, payloads, locks, and owner-routed selective revisions. | Created in place | Active |

## Sixteenth Maintained Skill

`complex-product-identity-reconstruction-asset-locking` is an active,
independently maintained package outside the optional 15-Skill High-Control profile.
Its canonical path is
`complex-product-identity-reconstruction-asset-locking` relative to this
checkout, and this workstation exposes it through the matching junction under
`$HOME/.codex/skills`.

## Legacy workstation discovery snapshot

As of 2026-07-10, the existing Windows workstation exposed the following
user-maintained entries through the legacy root. This is historical machine
state, not the current cross-platform installation contract.

| Codex entry | Junction target |
| --- | --- |
| `C:\Users\Administrator\.codex\skills\character-final-lock-board` | `D:\AI\skill\character-final-lock-board` |
| `C:\Users\Administrator\.codex\skills\character-casting-lock-board` | `D:\AI\skill\character-casting-lock-board` |
| `C:\Users\Administrator\.codex\skills\single-face-character-lock-board` | `D:\AI\skill\single-face-character-lock-board` |
| `C:\Users\Administrator\.codex\skills\cinematic_shot_image_explorer` | `D:\AI\skill\cinematic_shot_image_explorer` |
| `C:\Users\Administrator\.codex\skills\cinematic_world_builder` | `D:\AI\skill\cinematic_world_builder` |
| `C:\Users\Administrator\.codex\skills\scene-canon-asset-pack` | `D:\AI\skill\scene-canon-asset-pack` |
| `C:\Users\Administrator\.codex\skills\multi-angle-product-identity-lock-board` | `D:\AI\skill\multi-angle-product-identity-lock-board` |
| `C:\Users\Administrator\.codex\skills\packaging-product-identity-label-lock-board` | `D:\AI\skill\packaging-product-identity-label-lock-board` |
| `C:\Users\Administrator\.codex\skills\material-sensitive-product-master-asset-board` | `D:\AI\skill\material-sensitive-product-master-asset-board` |

### Historical pending entries for the six newly published Skills

These targets were not live in the 2026-07-10 snapshot. Install any one package
directly, or explicitly choose the optional bulk installer under
`high-control-ai-tvc/tools/`; in either case audit legacy roots first and do not
create duplicate discovery entries.

| Pending Codex entry | Repository target |
| --- | --- |
| `C:\Users\Administrator\.codex\skills\ai-video-shot-script-director` | `D:\AI\skill\ai-video-shot-script-director` |
| `C:\Users\Administrator\.codex\skills\ai-video-global-look-lock` | `D:\AI\skill\ai-video-global-look-lock` |
| `C:\Users\Administrator\.codex\skills\ai-video-modular-storyboard` | `D:\AI\skill\ai-video-modular-storyboard` |
| `C:\Users\Administrator\.codex\skills\ai-video-timed-animatic-previs-director` | `D:\AI\skill\ai-video-timed-animatic-previs-director` |
| `C:\Users\Administrator\.codex\skills\ai-video-keyframe-continuity-pack` | `D:\AI\skill\ai-video-keyframe-continuity-pack` |
| `C:\Users\Administrator\.codex\skills\ai-video-omni-reference-prompt-director` | `D:\AI\skill\ai-video-omni-reference-prompt-director` |

## Skipped Sources

The following classes are intentionally excluded from this archive:

- `C:\Users\Administrator\.codex\skills\.system`
- `C:\Users\Administrator\.codex\plugins\cache`
- `openai-bundled` plugin skills
- `openai-curated` plugin skills
- plugin cache, runtime, dependency, marketplace, and generated install directories

## Notes

- `D:\AI\skill` is the canonical maintenance location on the existing Windows
  workstation. A macOS checkout may live at any stable local path.
- New cross-platform installations use `%USERPROFILE%\.agents\skills` or
  `$HOME/.agents/skills` by default. Existing `.codex/skills` entries are legacy
  and must be audited before migration; never keep two live copies of one name.
- Skill packages may be installed independently and need not remain siblings.
  An explicitly selected High-Control workflow may discover several completed
  package artifacts and integrate them externally, but cannot become a runtime
  dependency of those packages.
- High-angle character continuity is maintained inside `character-final-lock-board` as the `high_angle_evidence` mode; the former standalone package was retired on 2026-07-10.
- Previous entries and obsolete duplicate sources were moved to `D:\AI\skill-migration-backups\20260527-112423`.
- Do not add loose skill files directly under `D:\AI\skill`; each skill must live in its own folder containing `SKILL.md`.
