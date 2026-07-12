# PROJECT_CANON_MANIFEST Contract

`PROJECT_CANON_MANIFEST` is the one project-level registry for the complete AI-video workflow. It is not a seventh Skill and it is not an orchestrator. It records which artifact version is current, which hashes were consumed, which artifacts became stale, and which owner must resolve an open change request.

## Canonical location

Store exactly one mutable registry at:

```text
<project_root>/00_project_canon/PROJECT_CANON_MANIFEST.json
```

Packages store an immutable `MANIFEST_UPDATE_RECEIPT.json` conforming to `manifest_update_receipt.schema.json`. It contains the canonical locator, producing Skill, before/after manifest hashes, exact registered owned artifact IDs, and `delta_status: applied`. They must not create another file called `PROJECT_CANON_MANIFEST.json` or treat a package snapshot as project truth.

The receipt proves result registration; by itself it does **not** prove a legal atomic transition. Before applying a delta, copy the exact frozen canonical file to the producing package at `00_manifest/BASE_PROJECT_CANON_SNAPSHOT.json`, never mutate that snapshot, and retain its raw file SHA-256. The snapshot is historical evidence, not a second current registry. Completion requires the shared pre/post validator:

```bash
python3 scripts/validate_project_canon_transition.py \
  <package_root>/00_manifest/BASE_PROJECT_CANON_SNAPSHOT.json \
  <project_root>/00_project_canon/PROJECT_CANON_MANIFEST.json \
  --base-snapshot-file-sha256 <exact_raw_file_sha256> \
  --updated-by-skill <producing-skill> \
  --receipt <package_root>/00_manifest/MANIFEST_UPDATE_RECEIPT.json \
  --expected-registered-artifact-id <owned-current-artifact-id>
```

Repeat `--expected-registered-artifact-id` for every owned active entry changed or added. Repeat `--preserved-artifact-id` for every preservation claim made by the owner artifact. This closes stale-base, owner-only-delta and fake-preservation attacks against the actual bytes.

Receipt validation must bind to the actual post-update canonical file: `resulting_manifest_sha256 == PROJECT_CANON_MANIFEST.sha256`, `base_manifest_sha256 == PROJECT_CANON_MANIFEST.base_manifest_sha256`, `updated_by_skill` matches, and every registered ID is an active artifact owned by that Skill. Format-only receipt validation is insufficient.

## Ownership and update protocol

- `ai-video-shot-script-director` owns the registry schema and initializes the project and stable Shot UID set.
- Every producing Skill may propose a `manifest_delta` only for artifacts it owns.
- Apply a delta atomically: preserve and raw-hash the current manifest as `BASE_PROJECT_CANON_SNAPSHOT.json`; verify its canonical hash; verify the producer artifact; reject stale base hashes; change only legal entries; increment `revision_counter` by exactly one and increase manifest SemVer; set `updated_by_skill`; validate; compute the new hash; replace the canonical file; then validate the real pre/post transition and bound receipt.
- A producer cannot overwrite, approve, un-stale, or delete an artifact owned by another Skill. It may add a structured change request or stale-propagation record naming that owner.
- A producer may record another owner's derived stale/blocked **registry overlay** only by changing `approval_status`, `stale_reason`, and `eligible_for_downstream`; the immutable owner record keeps its prior approved status while identity, version, hashes, locators, scope and dependencies remain exact. File verification accepts this sole status divergence only when the active Canon entry is stale/blocked and downstream-ineligible and exactly one event with the same reason and Shot scope names it. Exactly one new complete `stale_event` must also bind that demotion to an artifact changed by the updater. The updater may never repair or promote the foreign artifact.
- `user_approved` may be set only from explicit user approval. A validator may set `assistant_validated`; it cannot impersonate the user.

## No hash cycle

The manifest is a registry, not an input authority:

- its envelope-level `dependencies` must always be empty;
- it must never list itself in `active_artifacts`;
- no production artifact may include the manifest artifact ID or hash in its own `dependencies`;
- production artifacts depend directly on the exact upstream artifact ID, owner, SemVer, and hash they consumed;
- the manifest may index those artifacts and dependency edges, so an artifact change changes the manifest hash but never retroactively changes that artifact's hash.

This direction is mandatory:

```text
upstream artifact hash -> downstream artifact dependency
artifact hashes and edges -> PROJECT_CANON_MANIFEST registry
```

The reverse edge is forbidden.

## Active, superseded, and stale records

`active_artifacts` contains at most one current version per `artifact_slot`. An active artifact may be draft while work is in progress, but `eligible_for_downstream: true` is legal only for `assistant_validated` or `user_approved` artifacts with `stale_reason: null`.

Every downstream-eligible entry carries two independent project-relative evidence pairs:

- `locator` + `file_sha256` lock the primary asset bytes (JSON, image, video, audio, or another owned artifact);
- `artifact_record_locator` + `artifact_record_file_sha256` lock a complete JSON artifact record whose ID, owner, version, approval, dependencies, shot scope and canonical `sha256` exactly equal the Canon entry.

When the primary asset is itself the complete root artifact JSON, both locator pairs may point to that file. For a binary or a nested artifact, its owner must materialize the complete nested record at `owned_artifacts/<artifact_id>.json`; the validator never guesses or recursively searches a parent manifest. A newly registered external canon asset follows the same rule through an owner-produced adapter record—this is a registration artifact, not a seventh Skill. Superseded entries preserve both immutable evidence pairs. Absolute paths, `..` traversal, half-pairs, missing files, byte drift, record-envelope drift, and pseudo/non-canonical artifact hashes fail closed.

When replacing an active artifact:

1. move the old entry to `superseded_artifacts` without changing its recorded hash;
2. add the new current entry;
3. traverse `dependency_edges` from the changed artifact;
4. mark affected consumers stale in their own artifacts before they can be used again;
5. record the propagation under `stale_events`;
6. preserve unaffected artifact bytes and hashes.

The old producer lock in a stale current consumer is not rewritten. An active consumer may depend on a superseded producer only when the consumer is `stale` or `blocked`, is downstream-ineligible, retains the exact historical dependency lock, has the exact historical dependency edge, and has exactly one complete `stale_event` naming the replacement and its full consumer shot scope. Superseded artifacts' own dependencies are resolved against the complete active-plus-superseded registry and participate in the same acyclic historical DAG. Fabricated history edges, unresolved locks, and dependency or supersession cycles fail closed.

A manifest alone cannot make an artifact stale or valid. It records the verified state of the artifact; the owning artifact must carry the corresponding `approval_status` and `stale_reason`.

## Artifact slots

Use stable semantic slots, not filenames, for example:

- `professional_shot_contract`
- `global_look_contract`
- `storyboard_manifest`
- `timing_animatic_v1`
- `previs_manifest` (the stable root package slot; V1 and V2 are version/phase evolution of the same root authority)
- `keyframe_continuity_manifest`
- `generation_unit_preflight_plan` (the one stable Prompt P1 slot; do not alias it as `prompt_preflight_ir`)
- `control_previs_v2:<generation_unit_id>`
- `compiled_prompt_package:<generation_unit_id>`
- existing character, product, packaging, material, and scene asset slots

The manifest records all project assets, including outputs from existing canon-asset Skills. It does not reduce the project to the six new Skills.

## Phase graph

The artifact graph is acyclic even though the Prompt Director is invoked twice:

```text
professional_shot_contract
  -> canon_assets + global_look + storyboard_structure
global_look + canon_assets + storyboard_structure
  -> storyboard_final
professional_shot_contract + storyboard
  -> timing_animatic_v1
storyboard_final + global_look + canon_assets + timing_animatic_v1
  -> core_keyframe_continuity_manifest
all approved authorities + timing_animatic_v1 + core_keyframes
  -> generation_unit_preflight_plan (P1)
generation_unit_preflight_plan (P1) + core_keyframes
  -> keyframe_boundary_supplement
generation_unit_preflight_plan (P1) + keyframe_boundary_supplement + timing_animatic_v1 + core_keyframes
  -> control_previs_v2
control_previs_v2 + keyframe_boundary_supplement + generation_unit_preflight_plan (P1) + all approved authorities
  -> compiled_prompt_package
```

`preflight` and `compile` are separate artifact phases. Do not collapse them into a skill-level cycle.

## Completion gate

Run:

```bash
python3 scripts/validate_project_canon_manifest.py <PROJECT_CANON_MANIFEST.json> \
  --verify-files-root <project_root>
python3 scripts/validate_manifest_update_receipt.py <MANIFEST_UPDATE_RECEIPT.json> \
  --canonical-manifest <PROJECT_CANON_MANIFEST.json> \
  --expected-skill <producing-skill>
python3 scripts/validate_project_canon_transition.py \
  <BASE_PROJECT_CANON_SNAPSHOT.json> <PROJECT_CANON_MANIFEST.json> \
  --base-snapshot-file-sha256 <sha256> --updated-by-skill <producing-skill> \
  --receipt <MANIFEST_UPDATE_RECEIPT.json>
```

A valid non-draft registry proves structural consistency, a complete acyclic current-and-historical dependency index, primary bytes, and the complete canonical artifact record for every registered entry. Only the additional immutable-base transition validation proves that the named updater applied a legal owner-scoped delta. Semantic package validators remain responsible for owner-specific meaning.
