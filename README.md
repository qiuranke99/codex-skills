# D:\AI\skill

This directory is the canonical long-term archive for user-maintained Codex skills.

The real maintained content lives here. Codex discovers these skills through junction entries under `C:\Users\Administrator\.codex\skills`, each pointing back to the matching folder in `D:\AI\skill`.

## Layout

Each skill must live in its own stable folder:

```text
D:\AI\skill\
  AGENTS.md
  README.md
  SKILLS_INDEX.md
  <skill-name>\
    SKILL.md
    scripts\
    templates\
    examples\
    assets\
```

Only `AGENTS.md`, `README.md`, `SKILLS_INDEX.md`, and skill directories should be kept at the root.

## Rules

- Use concise, readable folder names such as `cinematic-composition-prompt-director`.
- Preserve the complete skill directory structure when archiving a skill.
- Do not archive system, official, plugin cache, runtime, or third-party generated skills here.
- Do not modify skill contents during archival unless a path reference is obviously broken by the move.
- Keep `C:\Users\Administrator\.codex\skills\<skill-name>` as a junction, not a second editable copy.
- Edit skills in `D:\AI\skill\<skill-name>`.
- Restart Codex after adding, removing, or renaming a skill so the available skill list is refreshed.
