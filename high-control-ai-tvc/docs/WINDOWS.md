# Windows workstation guide

## Supported operating model

Use a native Windows checkout of `qiuranke99/codex-skills` and native
PowerShell when Codex is operating on Windows paths. Keep the repository on a
stable local NTFS path. A network share, temporary download location, or
removable drive can prevent junction creation; use managed-copy mode when
necessary.

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

## Bootstrap

Obtain the public repository without requiring a GitHub SSH key:

```powershell
git clone https://github.com/qiuranke99/codex-skills.git
Set-Location codex-skills\high-control-ai-tvc
```

From `<codex-skills>\high-control-ai-tvc`:

```powershell
.\tools\setup-runtime.ps1
.\tools\install.ps1 install
.\tools\install.ps1 status
.\tools\install.ps1 audit -AutomaticOnly
```

Default Windows mode is a directory junction. If policy or filesystem behavior
blocks it:

```powershell
.\tools\install.ps1 install -Mode copy
```

After independently checking the three real capabilities:

```powershell
.\tools\install.ps1 audit `
  -Confirm codex_image_generation,control_previs_path,provider_platform_access
```

A successful install is not sufficient; the final audit must print `READY`.
Then restart Codex or open a new task and test
`$ai-video-shot-script-director`.

## Company PowerShell policy

If `.ps1` execution is blocked, do not change machine policy without IT
authorization. Use the direct Python form instead:

```powershell
.\.venv\Scripts\python.exe tools\manage_skills.py install
.\.venv\Scripts\python.exe tools\preflight.py --automatic-only --format json
```

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

- **Junction creation failed:** repository or target filesystem/policy does not
  support the chosen method; use explicit copy mode.
- **Path contains a literal `%`:** junction mode refuses it because `cmd.exe`
  expands environment tokens; move the checkout/target to a stable path without
  `%`, or use explicit managed-copy mode.
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
- **Managed copy contains changes:** the installer preserves it. Review the
  local edits rather than forcing an overwrite or uninstall.

## New project

```powershell
.\tools\new-project.ps1 `
  -Destination "D:\Client Projects\New TVC" `
  -Name "New TVC"
```

The generated project is outside the Skill repository. It contains no fake
Canon, customer material, provider credentials, or paid-generation action.

See [`INSTALLATION.md`](INSTALLATION.md) for update/removal rules and
[`CODEX_PROMPTS.md`](CODEX_PROMPTS.md) for the cross-platform Codex control
prompt.
