# Optional aggregate installation, update, audit, and removal

## Scope and authority

The 17 top-level Skills in this repository are independent packages. Each can
be copied or linked directly into a Codex discovery root and validated with its
own package-local instructions. An individual Skill does not require
`high-control-ai-tvc`, `SUITE_MANIFEST.json`, an aggregate receipt, a release
launcher, a pinned aggregate runtime, or sibling packages.

The commands in this document are for a user who explicitly opts into the
High-Control aggregate compatibility and maintenance profile. They provide
bulk installation, immutable snapshots, aggregate preflight, and coordinated
updates. Their receipts describe only entries managed by this profile and
never decide whether an unmanaged standalone Skill is available.

## Aggregate snapshot authority

GitHub repository id `1264973746`, `qiuranke99/codex-skills`, branch `main` is
the cross-machine update source for an explicitly selected aggregate snapshot.
The aggregate discovery entries point to an immutable
`releases/<GitHub OID>/repo` snapshot produced by the OS-native
`release-control.ps1` / `release-control.sh` launcher.
Activation removes write access from that snapshot (Windows current-user RX
ACL; macOS/Linux no-write permission modes). Every aggregate check proves
that creating a file and opening an existing file for writing are rejected,
then independently re-verifies every Git blob. A hash-only or writable
snapshot is not ready for this aggregate-managed workflow.

`install`, `adopt`, and `status` remain safety/migration tools. They do not
prove GitHub-latest aggregate state. Only `sync` followed by a new Codex task
and passing `check` can produce `AGGREGATE_READY_LATEST` for this profile. Offline or an
advanced/unstable remote is `AGGREGATE_NOT_READY_LATEST` for the profile; that status
does not revoke a standalone package that still passes its own validation.

## What “installed” means

When explicitly selected, `high-control-ai-tvc/` is the aggregate bulk
installation/control surface. The top-level Skill directories remain
independent packages; physical sibling layout inside an aggregate snapshot is
an implementation detail of that profile, not a single-package runtime
requirement. Aggregate installation exposes selected Skill directories to
Codex under the user discovery root. It does not copy
customer assets, initialize Project Canon, call a paid video API, or claim that
the machine is production-ready.

- Default discovery root: `$HOME/.agents/skills`
- Explicit aggregate `all` profile: 15 managed workflow members
  (13 core + 2 optional explorers); `excluded_from_aggregate_profile` keeps two
  standalone Skills outside aggregate installation and receipts only. All 17
  top-level packages remain standalone.
- Aggregate inventory: [`../SUITE_MANIFEST.json`](../SUITE_MANIFEST.json)
- Aggregate runtime requirements: [`../config/runtime-requirements.json`](../config/runtime-requirements.json)

Neither aggregate file is an authority for direct installation, invocation, or
validation of an individual top-level Skill.

Do not expose the same Skill names in both `.agents/skills` and the legacy
`.codex/skills`. The installer detects that collision and stops before writing.

If a user wants this aggregate profile to manage an older installation that
already contains exact symlinks/junctions from one discovery root to the
selected repository Skill directories, explicitly adopt them. Adoption is
never automatic and is not required for ordinary standalone use:

```bash
./tools/install.sh adopt --target "$HOME/.codex/skills" --allow-missing
```

```powershell
.\tools\install.ps1 adopt -Target "$HOME\.codex\skills" -AllowMissing
```

The command succeeds only when every selected aggregate entry is a
symlink/junction whose
resolved target is exactly `<codex-skills>/<skill-name>`. It validates source
identity/digests and writes an aggregate receipt without changing links. It refuses
copies, ordinary directories, links to only part of a Skill, other checkouts, or any parallel
same-name entries in `.agents/skills`. Use `--profile core` / `-Profile core`
only when the user explicitly wants the aggregate tool to manage the 13-entry
core profile.

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

## One-time aggregate setup

Run this section only after explicitly choosing aggregate management. A direct
single-Skill install does not perform these steps.

1. Clone `qiuranke99/codex-skills` to a stable local path. Do not bootstrap the
   aggregate profile from a temporary download folder that will later be moved
   or deleted. Change into
   `<codex-skills>/high-control-ai-tvc` before running the commands below.
2. Install Python 3.11 or 3.12 and FFmpeg/ffprobe with `libx264` through an
   organization-approved package source.
3. Create the aggregate compatibility-validation runtime:

   macOS:

   ```bash
   ./tools/setup-runtime.sh
   ```

   Windows PowerShell:

   ```powershell
   .\tools\setup-runtime.ps1
   ```

   The bootstrap helper installs exactly `Pillow==11.3.0` without modifying
   system Python. This environment is aggregate maintenance state, not an
   individual Skill authority and not part of an immutable Skill tree. Do not
   hard-code an authoring-checkout path into project artifacts; subsequent
   commands consume the validated `runtime_python` returned by the aggregate
   launcher/readback. Runtime state must not be committed.
4. Fetch GitHub `main`, validate its exact Git object snapshot, and atomically
   activate the selected aggregate profile:

   macOS:

   ```bash
   ./tools/install.sh sync
   ```

   Windows PowerShell:

   ```powershell
   .\tools\install.ps1 sync
   ```

5. Start a new Codex task, prove the active snapshot is still GitHub latest,
   then run the automatic audit:

   macOS:

   ```bash
   ./tools/install.sh check
   ./tools/install.sh audit --automatic-only
   ```

   Windows PowerShell:

   ```powershell
   .\tools\install.ps1 check
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

7. For the aggregate workflow, confirm in a real fresh Codex task—not only a
   debug catalog—that
   `$ai-video-shot-script-director` resolves from the receipt's snapshot before
   starting a customer project.

The aggregate audit is fail-closed. `NOT_READY` or
`NEEDS_MANUAL_CONFIRMATION` is not a successful aggregate preflight; it is not
a general statement about any independently installed Skill.

## Aggregate install modes

| Mode | Default | Behavior | Use when |
|---|---|---|---|
| `symlink` | macOS | Skills read the accepted immutable GitHub snapshot | Discovery root supports symlinks |
| `junction` | Windows | Junctions expose the accepted immutable GitHub snapshot without copying | Discovery root is on local NTFS |
| `copy` | fallback | Creates suite-marked managed copies | Junction/symlink creation is prohibited or the repository is on an incompatible filesystem |

Windows `symlink` is available explicitly but may require Developer Mode or
elevated policy. The installer never silently falls back to another mode. If a
junction fails, rerun explicitly with copy mode:

```powershell
.\tools\install.ps1 sync -Mode copy
```

On macOS, an explicit managed-copy installation is:

```bash
./tools/install.sh sync --mode copy
```

Paths containing spaces are supported when quoted:

```bash
./tools/install.sh sync --target "$HOME/My Codex/skills"
```

```powershell
.\tools\install.ps1 sync -Target "$HOME\My Codex\skills"
```

The explicit aggregate `sync` command activates all 15 aggregate members for
the `all` profile. `--profile core` / `-Profile core` manages only the 13 core
entries and does not satisfy the full aggregate profile; it does not remove
the two optional entries from a previous `all` run. Neither profile constrains
standalone entries outside its receipt.

## Aggregate status and machine-readable evidence

Human-readable GitHub-latest status:

```bash
./tools/install.sh check
```

```powershell
.\tools\install.ps1 check
```

JSON status or audit evidence:

```bash
./tools/install.sh check --format json
./tools/preflight.sh --automatic-only --format json
```

```powershell
.\tools\install.ps1 check -Format json
.\tools\preflight.ps1 -AutomaticOnly -Format json
```

JSON output is suitable for an aggregate maintenance/readiness record. It
contains no customer assets or credentials and must not be presented as a
single-Skill availability certificate.

## Create a new aggregate-managed production project

This helper opts the project into the documented aggregate workflow. Create
projects outside the repository. The helper creates only empty package
directories, a local README, and a non-authoritative project marker. It does not
copy client material or fabricate `PROJECT_CANON_MANIFEST.json`.

```bash
./tools/new-project.sh "/path/to/client projects/bath-oil-tvc" --name "Bath Oil TVC" --aggregate-managed
```

```powershell
.\tools\new-project.ps1 -Destination "D:\Client Projects\Bath Oil TVC" -Name "Bath Oil TVC" -AggregateManaged
```

Place the original script under `01_sources/script/original/`; place the brief,
licensed references, and source notes in the matching `01_sources/` category. The Shot Script Director creates the first real Canon after
it has produced and validated the Professional Shot Contract. Then use the
prompts in [`CODEX_PROMPTS.md`](CODEX_PROMPTS.md).

## Safe aggregate update

1. Stop active mutations to a customer Project Canon.
2. Run aggregate `sync`. It queries canonical GitHub directly and never resets, stashes,
   rebases, or overwrites either machine's authoring checkout.
3. `sync` validates the exact new snapshot and activates only if the remote
   remains stable before and after validation.
4. Restart Codex or open a new task; run aggregate `check`, automatic/full
   preflight, and verify one real Skill trigger from the activated profile.

The updater refuses to overwrite:

- an entry without this aggregate profile's install receipt;
- a link/junction whose target no longer matches its receipt;
- a managed copy that contains local edits;
- a same-name entry in the other known discovery root.

Do not edit aggregate-managed copies or release snapshots. Make source changes
in an authoring checkout, commit and push them, then run aggregate `sync` on
each participating machine. Standalone packages follow their own update and
readback contract.

## Safe migration into aggregate management

There is no silent one-command migration. Use an auditable two-step move:

1. Explicitly `adopt` exact existing links in `$HOME/.codex/skills`. If the
   legacy root contains the historical 9-Skill subset, use `--allow-missing`
   and then run `install` against that same legacy root to add the six missing
   workflow Skills under the new receipt.
2. Run `status` against that legacy target, then use `sync` to converge on the
   explicitly selected aggregate profile. Legacy `READY` is not
   `AGGREGATE_READY_LATEST` for that profile.
3. Run suite `uninstall` against the legacy target. It removes only the links
   proven by the new receipt.
4. Run `sync` with the default `$HOME/.agents/skills` target.
5. Run the full aggregate audit, restart Codex, and trigger one profile Skill
   explicitly.

macOS:

```bash
./tools/install.sh adopt --target "$HOME/.codex/skills"
./tools/install.sh status --target "$HOME/.codex/skills"
./tools/install.sh uninstall --target "$HOME/.codex/skills"
./tools/install.sh sync
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
.\tools\install.ps1 sync
```

For the historical 9-entry legacy root, replace the first two commands with:

```powershell
.\tools\install.ps1 adopt -Target "$HOME\.codex\skills" -AllowMissing
.\tools\install.ps1 install -Target "$HOME\.codex\skills"
.\tools\install.ps1 status -Target "$HOME\.codex\skills"
```

If adoption refuses any entry, stop. Do not mass-delete the legacy discovery
root; first identify which checkout or installer owns the collision.

## Safe aggregate uninstall

Remove only entries proven by the receipt to be owned by this aggregate
profile:

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

## Aggregate launcher fallback

If an organization blocks wrapper scripts but permits an approved equivalent
route, use the same aggregate tools with the profile runtime shown below. This
does not establish a Python requirement for standalone Skill validators:

```text
Windows: tools\release-control.ps1 -Action sync -Format json
Windows: tools\release-control.ps1 -Action check -Format json
macOS/Linux: tools/release-control.sh sync --format json
macOS/Linux: tools/release-control.sh check --format json
<runtime_python returned by aggregate check> tools/preflight.py --automatic-only --format json
```

Do not infer `runtime_python` from the current checkout path. Consume the
launcher result so a moved or removed authoring checkout cannot silently become
snapshot authority.

## Boundary

GitHub-latest aggregate activation plus a passing aggregate preflight makes the
coordinated SOP tooling ready for the selected profile. It does not certify
individual Skill availability, verify a future provider claim, submit video
generations, or replace human approvals. Each run still needs source-backed
identities/claims, an actual provider capability snapshot, and the approval
gates defined by the packages that participate in that run.
