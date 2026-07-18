# macOS workstation guide

Each top-level Skill can be installed independently by copying or symlinking
that package into a Codex discovery root and running its package-local
validation. A standalone Skill does not require `high-control-ai-tvc`, a suite
receipt, pinned runtime, sibling packages, or `AGGREGATE_READY_LATEST`.

## Required software

- Git, or another verified way to obtain the exact public repository commit
- Python 3.11 or 3.12
- FFmpeg and ffprobe on `PATH`, including `libx264`
- Codex with local file access and image-generation capability
- A real V2 Control Previs production path
- Access to the selected third-party video platform

The snapshot model below is an explicit opt-in aggregate compatibility and
maintenance profile. Its symlinks point to a GitHub-commit-addressed immutable
snapshot under the discovery root. Activation removes every write bit from the
snapshot; the aggregate gate proves both the permission state and rejected
write attempts before it accepts the profile. None of this controls unmanaged
standalone packages.

## Optional aggregate bootstrap

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

After explicitly choosing aggregate management, `sync` must print
`AGGREGATE_READY_LATEST`. Restart Codex or open a new task; the final aggregate audit must
print `AGGREGATE_READY_LATEST`, then test one profile Skill such as
`$ai-video-shot-script-director`. This status is not a single-Skill
availability gate.

## Aggregate Python runtime

`setup-runtime.sh` searches Python 3.12 and then 3.11, creates
aggregate maintenance runtime state, and installs the exact Pillow pin without
modifying the system Python. That runtime is compatibility-validation evidence,
not an individual Skill or immutable snapshot authority.

Aggregate release gates use `tools/release-control.sh`; it resolves the profile
interpreter and disables bytecode writes. Aggregate compatibility validators
consume the `runtime_python` returned by launcher readback rather than deriving
a path from the mutable authoring checkout. Independently installed packages
follow their own runtime and validator contracts; this profile pin does not
override them.

## Legacy documents

macOS can use `textutil` for legacy `.doc`/`.rtf` extraction, but `.docx` is the
portable project format and should be used when the same project moves between
home Mac and company Windows. Conversion must preserve the original content.

## macOS-specific failure interpretation

- **Aggregate symlink points to a different snapshot:** rerun profile `sync`;
  do not label the mixed aggregate state ready.
- **Duplicate `.codex/skills` entry:** migrate or remove it through its owning
  installer before using `.agents/skills`; never keep both live.
- **Pillow mismatch:** rerun `setup-runtime.sh`.
- **FFmpeg/ffprobe missing from Codex:** repair the PATH visible to the Codex
  process and reopen the app.
- **Managed copy contains edits:** the installer preserves it rather than
  overwriting or deleting it.
- **`UPDATE_REQUIRED`:** the aggregate profile's GitHub `main` advanced; stop
  that aggregate transaction, rerun `sync`, and use a new Codex task. This does
  not invalidate a standalone package.
- **`REMOTE_UNVERIFIED`:** aggregate latest cannot be proved; the fallback must
  not be labeled `AGGREGATE_READY_LATEST`. This is not a standalone availability result.

## New project

```bash
./tools/new-project.sh \
  "$HOME/AI Video Projects/New TVC" \
  --name "New TVC" \
  --aggregate-managed
```

The helper explicitly opts the directory into the aggregate SOP and is
idempotent only for a directory carrying this profile's project marker. It
refuses to adopt an unrelated non-empty directory and never creates a fake
Project Canon.

See [`INSTALLATION.md`](INSTALLATION.md) for update/removal rules and
[`CODEX_PROMPTS.md`](CODEX_PROMPTS.md) for the cross-platform Codex control
prompt.
