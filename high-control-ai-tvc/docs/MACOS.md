# macOS workstation guide

## Required software

- Git, or another verified way to obtain the exact public repository commit
- Python 3.11 or 3.12
- FFmpeg and ffprobe on `PATH`, including `libx264`
- Codex with local file access and image-generation capability
- A real V2 Control Previs production path
- Access to the selected third-party video platform

The local checkout is an authoring/bootstrap workspace, not production
authority. Production symlinks point to a GitHub-commit-addressed immutable
snapshot under the discovery root, so moving an authoring checkout cannot
silently change the active release.

## Bootstrap

Obtain the public repository:

```bash
git clone https://github.com/qiuranke99/codex-skills.git
cd codex-skills/high-control-ai-tvc
```

From `<codex-skills>/high-control-ai-tvc`:

```bash
./tools/setup-runtime.sh
./tools/install.sh sync
./tools/install.sh check
./tools/install.sh audit --automatic-only
```

Default macOS mode is symlink. If a managed copy is required:

```bash
./tools/install.sh sync --mode copy
```

After independently checking the three real capabilities:

```bash
./tools/install.sh audit \
  --confirm codex_image_generation \
  --confirm control_previs_path \
  --confirm provider_platform_access
```

`sync` must print `READY_LATEST`. Restart Codex or open a new task; the final
audit must print `READY_LATEST`, then test
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

- **Symlink points to a different snapshot:** rerun `sync`; no local checkout is
  allowed to become production authority.
- **Duplicate `.codex/skills` entry:** migrate or remove it through its owning
  installer before using `.agents/skills`; never keep both live.
- **Pillow mismatch:** rerun `setup-runtime.sh`.
- **FFmpeg/ffprobe missing from Codex:** repair the PATH visible to the Codex
  process and reopen the app.
- **Managed copy contains edits:** the installer preserves it rather than
  overwriting or deleting it.
- **`UPDATE_REQUIRED`:** GitHub `main` advanced; stop, rerun `sync`, and use a
  new Codex task.
- **`REMOTE_UNVERIFIED`:** latest cannot be proved; offline fallback is not
  production-ready.

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
