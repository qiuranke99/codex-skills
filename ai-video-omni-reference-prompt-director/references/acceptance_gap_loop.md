# Acceptance-Gap Closure Loop

This is a development/release audit for the six-Skill suite. It is not a generation orchestrator, experiment log, footage-QC service, or runtime workflow engine.

## Independent audit roles

Run all three roles against the same frozen candidate:

1. **Boundary and ownership audit** — find responsibility overlap, missing handoffs, circular dependencies, prohibited-scope leakage, and wrong revision owners.
2. **Contract and package audit** — attack schemas, hashes, dependency locks, stale propagation, required outputs, malformed inputs, discovery metadata, and validators.
3. **Scenario and counterexample audit** — exercise poetic product ads, non-uniform multi-shot timing, atomic storyboard changes, material continuity, missing provider modalities, and feedback returns.

The main agent compares reports, reproduces claims, rejects unsupported findings, merges duplicates, assigns one owner to each accepted gap, fixes the implementation, and runs the full suite again. Sub-agent conclusions are evidence candidates, not final decisions.

## Structured gap record

Every candidate or accepted gap uses:

- `gap_id`
- `source_agent`
- `severity`: `critical | high | medium | low`
- `artifact`
- `owner`
- `evidence`
- `status`: `open | adjudicated | fixing | verified | rejected`
- `fix`
- `verification`

`rejected` requires concrete counterevidence. `verified` requires a regression test or deterministic inspection command. Do not close gaps by editing only prose when the defect is executable.

## Loop

```text
freeze candidate
→ three independent audits
→ main-agent adjudication and deduplication
→ repair accepted gaps
→ add negative regression
→ run every package test + shared manifest tests + suite validator
→ repeat independent audits on repaired state
```

## Exit gate

Release is allowed only when:

- every accepted gap is `verified`;
- every rejected gap has reproducible counterevidence;
- zero `critical` or `high` gaps remain open, adjudicated, or fixing;
- no actionable `medium` or `low` gap remains silently deferred;
- all six package tests, legacy-source test, Project Canon manifest tests, suite self-test, JSON parse checks, Python compile checks, forbidden-scope checks, local discovery checks, and clone-side checks pass;
- the pushed commit is read back from the remote branch and contains the same six tree objects that were locally validated.

If a unique external condition prevents one check, record it as a real blocker with the missing condition, why it cannot be substituted, completed work, and exact resume action. Difficulty or incomplete analysis is not a blocker.
