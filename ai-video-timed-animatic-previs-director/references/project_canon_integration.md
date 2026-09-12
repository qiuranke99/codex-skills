# Optional Project Canon Integration

Read only when the caller supplies a registry and explicitly requests
registration. Standalone V1/V2/skip creation, validation and handoff do not
require this integration or a sibling Skill.

## Registry And Source Binding

Use the actual post-delta
`<project_root>/00_project_canon/PROJECT_CANON_MANIFEST.json`. For this branch,
`package_root` must be a contained child of, but not conflated with,
`project_root`. Registered source packages resolve through Canon locators.
Validate the registry and prove each source authority and Previs-owned
registered artifact is the exact active, downstream-eligible entry.

Resolve Canon locators against explicit `project_root`; resolve Previs media,
copied inputs, snapshots and owned JSON records against `package_root`. Entries
must bind safe project-relative locators, actual file hashes, matching artifact
envelopes, dependencies, approval, scope, version and canonical hash. Local
snapshots must equal the Canon-located originals, not replace them.

## Receipt And Separate Primary/Record Locks

The update receipt must match the actual post Canon `sha256`,
`base_manifest_sha256`, `updated_by_skill`, and exact current Previs-owned IDs.
Materialize root and nested V1/V2/track/skip records under
`00_manifest/owned_artifacts/`. Canon record locator/hash fields bind these
complete JSON records; separate primary locator/hash fields bind the root
manifest, V1/V2 MP4 or per-track motion JSON.

Stable slots are `previs_manifest`, `timing_animatic_v1`,
`control_previs_v2:<generation_unit_id>`, and `motion_track:<track_id>`.
When the root advances to V2, move its preceding V1-only root into
`superseded_artifacts` with lower version, a hash-bound locator and a replacement
link. P1 uses `generation_unit_preflight_plan`; reject `prompt_preflight_ir`.

## Mutation Boundary

Preserve exact base/candidate bytes. Invoke the package-local
`scripts/apply_project_canon_transition.py` only with the caller's explicit
compatible `--transition-runner`; never find a sibling writer or directly
fabricate Canon/receipt bytes. Missing transition input blocks registration,
not the otherwise valid standalone Previs artifact.
