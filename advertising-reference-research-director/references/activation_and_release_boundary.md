# Activation And Release Boundary

This Skill is a standalone package. Its local activation check and a research
run's production-contract-eligible gate prove different things. Never collapse them
into one generic "installed" or "production-ready" claim.

## Required preflight

Resolve the directory containing this package's `SKILL.md`, then run exactly one
OS-native package launcher before workflow work:

```bash
./scripts/preflight.sh --format json
```

```powershell
.\scripts\preflight.ps1 -Format json
```

The launcher always runs `scripts/test_contract.py` with Python isolation and
bytecode writes disabled. `AI_AD_REFERENCE_PYTHON` may name an explicit Python
3.10+ executable. The successful result is
`gate_mode=standalone_package`, `package_contract_ready=true`, and
`ready_for_skill_workflow=true`. Package behavior is invariant to adjacent
directories; no sibling package or repository controller is a prerequisite.

## Claim boundary

Standalone mode is a valid execution entry for a separately maintained
canonical package. It does **not** establish any of the following:

- GitHub `main` freshness or remote publication;
- repository identity, commit provenance, or immutable snapshot protection;
- activation or compatibility of other packages;
- browser-action attestation or a production-deliverable research run.

Activation evidence and research-run evidence are orthogonal. A standalone
package may execute a `production_live` research run, but the run still needs
all preregistration, direct-capture, external-validation, 30/20/10, audit, and
rights-boundary gates in `SKILL.md`.

## Mutation boundary

The package preflight performs checks only. It never publishes, edits Codex
discovery, activates another Skill, changes repository state, or upgrades a
research artifact's evidence class.
