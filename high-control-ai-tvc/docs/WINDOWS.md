# Windows workstation guide

## Supported operating model

Use native PowerShell when Codex is operating on Windows paths. Each top-level
Skill can be installed independently by copying or linking that package into a
Codex discovery root, then running its package-local validation. Standalone
installation does not require `high-control-ai-tvc`, a suite receipt, pinned
runtime, sibling packages, or `AGGREGATE_READY_LATEST`.

The immutable snapshot and commands below are an explicit opt-in aggregate
compatibility/maintenance profile. For that profile, keep the discovery root
on local NTFS and use managed-copy mode when junction creation is unavailable.
Its receipt controls only aggregate-managed entries and never unmanaged
standalone packages.

Do not install the same suite once in native Windows and again in WSL unless the
two Codex environments are intentionally separate. Native
`%USERPROFILE%\.agents\skills` and WSL `~/.agents/skills` are different
discovery roots.

## Required software

- Git, or another verified way to obtain the exact public repository commit
- 64-bit Python 3.11 or 3.12
- FFmpeg and ffprobe on `PATH`
- FFmpeg build exposing the `libx264` encoder
- Codex with local file access and image-generation capability
- A real V2 Control Previs production path
- Access to the selected third-party video platform

Install these through the company software center or another IT-approved
source. Reopen PowerShell and Codex after PATH changes.

## Optional aggregate bootstrap

Obtain the public repository without requiring a GitHub SSH key:

```powershell
git clone https://github.com/qiuranke99/codex-skills.git
Set-Location codex-skills\high-control-ai-tvc
```

From `<codex-skills>\high-control-ai-tvc`:

```powershell
.\tools\setup-runtime.ps1
.\tools\install.ps1 sync
.\tools\install.ps1 check
.\tools\install.ps1 audit -AutomaticOnly
```

Default Windows mode is a directory junction. If policy or filesystem behavior
blocks it:

```powershell
.\tools\install.ps1 sync -Mode copy
```

After independently checking the three real capabilities:

```powershell
.\tools\install.ps1 audit `
  -Confirm codex_image_generation,control_previs_path,provider_platform_access
```

A successful legacy aggregate `install` does not satisfy the full profile.
After the user explicitly chooses aggregate management, `sync` must report
`AGGREGATE_READY_LATEST`, Codex must be restarted or a new task opened, and the final
aggregate audit must print `AGGREGATE_READY_LATEST`. Then test one profile Skill such as
`$ai-video-shot-script-director`. This status is not a single-Skill
availability gate.

## Aggregate pinned release launcher

For an aggregate-managed workflow, use the OS-native launcher for profile
release checks; it resolves the profile runtime, leaves the active snapshot
before execution, and disables bytecode writes. This launcher does not replace
the runtime contract of an independently installed package:

```powershell
.\tools\release-control.ps1 -Action sync -Format json
.\tools\release-control.ps1 -Action check -Format json
.\tools\preflight.ps1 -AutomaticOnly -Format json
```

For machine-readable automation, consume `runtime_python` and
`active_system_root` from launcher readback; do not construct either path from
the mutable authoring checkout.

Successful aggregate activation applies a recursive read/execute ACL to the
exact GitHub commit snapshot. Aggregate `check` must report
`snapshot_write_protection=pass`. If company policy blocks `.ps1`, do not
bypass the policy; obtain the approved route for this optional profile, or use
individual packages without claiming aggregate readiness.

The tools accept quoted paths containing spaces and do not require the current
directory to be added to global PATH.

## Legacy Word documents

The bundled cross-platform ingestion path handles `.docx`, TXT, Markdown, CSV,
and TSV. Legacy `.doc` and `.rtf` extraction depends on macOS `textutil` and is
not a portable Windows route. Open the source in Word and use **Save As →
`.docx`**. Do not rewrite or “improve” the customer's script during conversion.

This is a format constraint only. A poetic or incomplete advertising draft is
still valid input: the Shot Script Director must infer ordinary directing,
camera, blocking, timing, and product-use decisions without refusing the job.

## Windows-specific failure interpretation

- **Junction creation failed:** release snapshot or target filesystem/policy does not
  support the chosen method; use explicit copy mode.
- **Duplicate discovery entry:** the same Skill name already exists under
  `.codex\skills` or `.agents\skills`; remove it through the installer/repository
  that owns it, then retry. Do not mass-delete either directory.
- **Python not production-tested:** create the runtime with Python 3.11/3.12;
  do not accept a newer/older interpreter merely because it launches.
- **Pillow mismatch:** rerun `setup-runtime.ps1`; do not install a floating
  Pillow version.
- **FFmpeg/ffprobe missing:** repair system PATH and reopen Codex.
- **`libx264` missing:** replace the FFmpeg build with one that includes the
  required encoder.
- **`UPDATE_REQUIRED`:** the aggregate profile's GitHub `main` advanced; stop
  that aggregate stage, rerun `sync`, then open a new Codex task. Standalone
  package validity is unchanged unless its own readback fails.
- **`REMOTE_UNVERIFIED`:** the aggregate profile cannot prove latest; its
  coordinated workflow stays blocked and must not label the previous snapshot
  `AGGREGATE_READY_LATEST`. This is not a standalone availability result.
- **Managed copy contains changes:** the installer preserves it. Treat this as
  integrity failure; review it rather than forcing an overwrite or uninstall.

## New project

```powershell
.\tools\new-project.ps1 `
  -Destination "D:\Client Projects\New TVC" `
  -Name "New TVC" `
  -AggregateManaged
```

The generated project is outside the Skill repository and explicitly follows
the aggregate SOP. It contains no fake Canon, customer material, provider
credentials, or paid-generation action.

See [`INSTALLATION.md`](INSTALLATION.md) for update/removal rules and
[`CODEX_PROMPTS.md`](CODEX_PROMPTS.md) for the cross-platform Codex control
prompt.
