# macOS workstation guide

## Required software

- Git, or another verified way to obtain the exact public repository commit
- Python 3.11 or 3.12
- FFmpeg and ffprobe on `PATH`, including `libx264`
- Codex with local file access and image-generation capability
- A real V2 Control Previs production path
- Access to the selected third-party video platform

Use a stable local checkout of `qiuranke99/codex-skills`. Do not install
symlinks from a temporary Downloads checkout that will later move.

## Bootstrap

Obtain the public repository:

```bash
git clone https://github.com/qiuranke99/codex-skills.git
cd codex-skills/high-control-ai-tvc
```

From `<codex-skills>/high-control-ai-tvc`:

```bash
./tools/setup-runtime.sh
./tools/install.sh install
./tools/install.sh status
./tools/install.sh audit --automatic-only
```

Default macOS mode is symlink. If a managed copy is required:

```bash
./tools/install.sh install --mode copy
```

After independently checking the three real capabilities:

```bash
./tools/install.sh audit \
  --confirm codex_image_generation \
  --confirm control_previs_path \
  --confirm provider_platform_access
```

The final audit must print `READY`. Restart Codex or open a new task, then test
`$ai-video-shot-script-director`.

## Python runtime

`setup-runtime.sh` searches Python 3.12 and then 3.11, creates
`high-control-ai-tvc/.venv`, and installs the exact Pillow pin. The
install/preflight helpers prefer that environment automatically. This avoids
modifying the system Python.

When Codex invokes a Skill validator directly, instruct it to use the same
repository-local `.venv/bin/python` rather than an unrelated `python3` on PATH.
This rule matters when Apple system Python and package-manager Python coexist.

## Legacy documents

macOS can use `textutil` for legacy `.doc`/`.rtf` extraction, but `.docx` is the
portable project format and should be used when the same project moves between
home Mac and company Windows. Conversion must preserve the original content.

## macOS-specific failure interpretation

- **Symlink points to a different checkout:** rerun the suite installer from the
  checkout that should be authoritative. It updates only receipt-owned links.
- **Duplicate `.codex/skills` entry:** migrate or remove it through its owning
  installer before using `.agents/skills`; never keep both live.
- **Pillow mismatch:** rerun `setup-runtime.sh`.
- **FFmpeg/ffprobe missing from Codex:** repair the PATH visible to the Codex
  process and reopen the app.
- **Managed copy contains edits:** the installer preserves it rather than
  overwriting or deleting it.

## New project

```bash
./tools/new-project.sh \
  "$HOME/AI Video Projects/New TVC" \
  --name "New TVC"
```

The helper is idempotent only for a directory carrying this suite's project
marker. It refuses to adopt an unrelated non-empty directory and never creates
a fake Project Canon.

See [`INSTALLATION.md`](INSTALLATION.md) for update/removal rules and
[`CODEX_PROMPTS.md`](CODEX_PROMPTS.md) for the cross-platform Codex control
prompt.
