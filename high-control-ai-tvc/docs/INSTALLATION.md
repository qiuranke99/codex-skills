# Installation, update, audit, and removal

## What “installed” means

The `high-control-ai-tvc/` subsystem inside `qiuranke99/codex-skills` is the
installation/control surface, while the 15 Skill directories remain its sibling
packages at repository root. Installation exposes those Skill directories to
Codex under the user discovery root. It does not copy
customer assets, initialize Project Canon, call a paid video API, or claim that
the machine is production-ready.

- Default discovery root: `$HOME/.agents/skills`
- Default profile: all 15 Skills (13 core + 2 optional explorers)
- Single inventory SSOT: [`../SUITE_MANIFEST.json`](../SUITE_MANIFEST.json)
- Runtime SSOT: [`../config/runtime-requirements.json`](../config/runtime-requirements.json)

Do not expose the same Skill names in both `.agents/skills` and the legacy
`.codex/skills`. The installer detects that collision and stops before writing.

If an older installation already contains exact symlinks/junctions from one
discovery root to the 15 current repository Skill directories, explicitly adopt
them before normal status/update operations. Adoption is never automatic:

```bash
./tools/install.sh adopt --target "$HOME/.codex/skills" --allow-missing
```

```powershell
.\tools\install.ps1 adopt -Target "$HOME\.codex\skills" -AllowMissing
```

The command succeeds only when every selected entry is a symlink/junction whose
resolved target is exactly `<codex-skills>/<skill-name>`. It validates source
identity/digests and writes a suite receipt without changing links. It refuses
copies, ordinary directories, links to only part of a Skill, other checkouts, or any parallel
same-name entries in `.agents/skills`. Use `--profile core` / `-Profile core`
only when the older installation intentionally contains the 13 core Skills.

If the old installation predates the six workflow Skills and therefore contains
only a subset of the current 15, use the explicit partial-adoption flag, then
install the missing entries into the same legacy root:

```bash
./tools/install.sh adopt --target "$HOME/.codex/skills" --allow-missing
./tools/install.sh install --target "$HOME/.codex/skills"
```

```powershell
.\tools\install.ps1 adopt -Target "$HOME\.codex\skills" -AllowMissing
.\tools\install.ps1 install -Target "$HOME\.codex\skills"
```

`--allow-missing` never relaxes checks on entries that do exist: one ordinary
directory, copy or wrong link target still rejects the complete adoption before
writing a receipt.

## One-time setup

1. Clone `qiuranke99/codex-skills` to a stable local path. Do not install from a
   temporary download folder that will later be moved or deleted. Change into
   `<codex-skills>/high-control-ai-tvc` before running the commands below.
2. Install Python 3.11 or 3.12 and FFmpeg/ffprobe with `libx264` through an
   organization-approved package source.
3. Create the pinned repository-local Python runtime:

   macOS:

   ```bash
   ./tools/setup-runtime.sh
   ```

   Windows PowerShell:

   ```powershell
   .\tools\setup-runtime.ps1
   ```

   This creates `high-control-ai-tvc/.venv` and installs exactly
   `Pillow==11.3.0`. It does not modify system Python. `.venv` is local runtime
   state and must not be committed.
4. Install every Skill:

   macOS:

   ```bash
   ./tools/install.sh install
   ```

   Windows PowerShell:

   ```powershell
   .\tools\install.ps1 install
   ```

5. Run the automatic audit:

   macOS:

   ```bash
   ./tools/install.sh audit --automatic-only
   ```

   Windows PowerShell:

   ```powershell
   .\tools\install.ps1 audit -AutomaticOnly
   ```

6. Verify the three real capabilities, then record those confirmations in the
   full preflight:

   macOS:

   ```bash
   ./tools/install.sh audit \
     --confirm codex_image_generation \
     --confirm control_previs_path \
     --confirm provider_platform_access
   ```

   Windows PowerShell:

   ```powershell
   .\tools\install.ps1 audit `
     -Confirm codex_image_generation,control_previs_path,provider_platform_access
   ```

7. Restart Codex or open a new Codex task. Confirm that
   `$ai-video-shot-script-director` resolves before starting a customer project.

The audit is fail-closed. `NOT_READY` or `NEEDS_MANUAL_CONFIRMATION` is not a
successful production preflight.

## Install modes

| Mode | Default | Behavior | Use when |
|---|---|---|---|
| `symlink` | macOS | Skills always read the current checkout | The repository stays at a stable path |
| `junction` | Windows | Directory junctions expose the sibling Skill layout without copying | Repository and discovery root are on a local filesystem that supports junctions |
| `copy` | fallback | Creates suite-marked managed copies | Junction/symlink creation is prohibited or the repository is on an incompatible filesystem |

Windows `symlink` is available explicitly but may require Developer Mode or
elevated policy. The installer never silently falls back to another mode. If a
junction fails, rerun explicitly with copy mode:

```powershell
.\tools\install.ps1 install -Mode copy
```

On macOS, an explicit managed-copy installation is:

```bash
./tools/install.sh install --mode copy
```

Paths containing spaces are supported when quoted:

```bash
./tools/install.sh install --target "$HOME/My Codex/skills"
```

```powershell
.\tools\install.ps1 install -Target "$HOME\My Codex\skills"
```

The default installs all 15 Skills. `--profile core` / `-Profile core` installs
only the 13 production Skills; it does not remove optional Skills installed by a
previous all-profile run.

## Status and machine-readable evidence

Human-readable status:

```bash
./tools/install.sh status
```

```powershell
.\tools\install.ps1 status
```

JSON status or audit evidence:

```bash
./tools/install.sh status --format json
./tools/preflight.sh --automatic-only --format json
```

```powershell
.\tools\install.ps1 status -Format json
.\tools\preflight.ps1 -AutomaticOnly -Format json
```

JSON output is suitable for a machine/IT readiness record. It contains no
customer assets or credentials.

## Create a new production project

Create projects outside the repository. The helper creates only empty package
directories, a local README, and a non-authoritative project marker. It does not
copy client material or fabricate `PROJECT_CANON_MANIFEST.json`.

```bash
./tools/new-project.sh "/path/to/client projects/bath-oil-tvc" --name "Bath Oil TVC"
```

```powershell
.\tools\new-project.ps1 -Destination "D:\Client Projects\Bath Oil TVC" -Name "Bath Oil TVC"
```

Place the original script under `01_sources/script/original/`; place the brief,
licensed references, and source notes in the matching `01_sources/` category. The Shot Script Director creates the first real Canon after
it has produced and validated the Professional Shot Contract. Then use the
prompts in [`CODEX_PROMPTS.md`](CODEX_PROMPTS.md).

## Safe update

1. Stop active mutations to a customer Project Canon.
2. Update the `codex-skills` checkout with Git.
3. Re-run `setup-runtime` so the pinned Python dependency matches the checkout.
4. Re-run `install`; this is the idempotent update operation.
5. Run automatic and full preflight again.
6. Restart Codex or open a new task and verify one Skill trigger.

The updater refuses to overwrite:

- an entry without this suite's install receipt;
- a link/junction whose target no longer matches its receipt;
- a managed copy that contains local edits;
- a same-name entry in the other known discovery root.

Do not edit installed copies. Make source changes in a controlled repository
change and reinstall.

## Safe migration from legacy discovery

There is no silent one-command migration. Use an auditable two-step move:

1. Explicitly `adopt` exact existing links in `$HOME/.codex/skills`. If the
   legacy root contains the historical 9-Skill subset, use `--allow-missing`
   and then run `install` against that same legacy root to add the six missing
   workflow Skills under the new receipt.
2. Run `status` against that legacy target and require all 15 entries `READY`.
3. Run suite `uninstall` against the legacy target. It removes only the links
   proven by the new receipt.
4. Run `install` with the default `$HOME/.agents/skills` target.
5. Run the full audit, restart Codex, and trigger one Skill explicitly.

macOS:

```bash
./tools/install.sh adopt --target "$HOME/.codex/skills"
./tools/install.sh status --target "$HOME/.codex/skills"
./tools/install.sh uninstall --target "$HOME/.codex/skills"
./tools/install.sh install
```

For the historical 9-entry legacy root, replace the first two commands with:

```bash
./tools/install.sh adopt --target "$HOME/.codex/skills" --allow-missing
./tools/install.sh install --target "$HOME/.codex/skills"
./tools/install.sh status --target "$HOME/.codex/skills"
```

Windows PowerShell:

```powershell
.\tools\install.ps1 adopt -Target "$HOME\.codex\skills"
.\tools\install.ps1 status -Target "$HOME\.codex\skills"
.\tools\install.ps1 uninstall -Target "$HOME\.codex\skills"
.\tools\install.ps1 install
```

For the historical 9-entry legacy root, replace the first two commands with:

```powershell
.\tools\install.ps1 adopt -Target "$HOME\.codex\skills" -AllowMissing
.\tools\install.ps1 install -Target "$HOME\.codex\skills"
.\tools\install.ps1 status -Target "$HOME\.codex\skills"
```

If adoption refuses any entry, stop. Do not mass-delete the legacy discovery
root; first identify which checkout or installer owns the collision.

## Safe uninstall

Remove all entries proven to be owned by this suite:

```bash
./tools/install.sh uninstall
```

```powershell
.\tools\install.ps1 uninstall
```

Uninstall removes only receipt-bound links/junctions or unchanged marked copies.
It preserves unmanaged entries, changed copies, the repository, `.venv`, and all
customer project directories. A refusal is a safety result, not an instruction
to delete the whole discovery directory.

## Direct Python fallback

If an organization blocks shell or PowerShell scripts, the same guarded tools
can be called with the repository-local Python executable:

```text
<repo>/high-control-ai-tvc/.venv/.../python tools/manage_skills.py install
<repo>/high-control-ai-tvc/.venv/.../python tools/preflight.py --automatic-only --format json
```

Use `.venv/bin/python` on macOS and `.venv\Scripts\python.exe` on Windows.

## Production boundary

Installation plus a passing preflight makes the local SOP tooling ready. It
does not verify a future provider claim, submit video generations, or replace
human approvals. Each run still needs source-backed identities/claims, an
actual provider capability snapshot, and the approval gates defined in the six
workflow Skills.
