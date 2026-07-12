# Revision And Invalidation Contract

## Stable identity

- `shot_uid` is permanent.
- `display_no` is an ordering label and may change.
- Deleting a shot retires its UID; never reuse it for different content.
- Splitting a shot creates new UIDs and records the parent UID.

## Revision modes

### `initial`

Creates the first complete Professional Shot Contract.

### `selective_revision`

Allowed when the requested change is confined to named shots and does not change creative mode, total duration, global directing grammar or claim boundary. The artifact must record requested and actually changed UIDs. Any expanded scope requires a dependency explanation.

Invalidate only:

- changed storyboard frames;
- continuity edges touching changed shots;
- changed shot keyframes and time anchors;
- timing/control Previs segments that use changed shots;
- generation prompts and bindings containing changed shots.

Every non-initial revision binds exactly one frozen predecessor through `revision_scope.predecessor_artifact` and must be validated against that predecessor's actual JSON bytes. The current SemVer must be greater. `changed_json_pointers` must equal the deterministic real semantic diff after excluding only revision/envelope metadata; the validator derives `actually_changed_shot_uids` from stable-ID Shot and requirement-map records rather than trusting the declaration. Unchanged Shot UIDs remain byte-identical. Run:

```bash
python3 scripts/validate_shot_contract.py <current.json> --previous-contract <frozen_previous.json>
```

`invalidated_artifact_ids` and `preserved_artifact_ids` are disjoint. Preservation is not proved by this artifact alone: pass every claimed preserved ID to `validate_project_canon_transition.py --preserved-artifact-id ...` so the immutable base and post registry entries must be exactly equal.

### `global_revision`

Required when changing creative mode, total duration, global directing grammar, product/claim truth, or a large structural sequence. Revalidate all shots and all downstream artifacts.

### `reorder`

Shot content may remain, but every changed adjacency invalidates cut motivation, continuity, timing, Previs, keyframe timecodes and generation-unit prompts for the affected range.

## Shared artifact envelope

Every authoritative artifact contains:

```json
{
  "contract_version": "ai-video-artifact-v1",
  "artifact_id": "...",
  "owner_skill": "ai-video-shot-script-director",
  "version": "1.0.0",
  "sha256": null,
  "approval_status": "draft",
  "dependencies": [],
  "affected_shot_uids": [],
  "stale_reason": null
}
```

`sha256` is null only while draft. For a frozen artifact, remove only the top-level envelope `sha256`; retain every nested dependency hash. Serialize canonical UTF-8 JSON with `sort_keys=True`, `separators=(',', ':')`, `ensure_ascii=False`, and `allow_nan=False`, then calculate SHA-256. Binary files use a separate `file_sha256`. `assistant_validated` never means `user_approved`.

## Stale propagation

- Source intent or claim truth changed → entire shot contract stale.
- Global directing grammar changed → all storyboard, Previs, keyframe timecode and video-prompt dependants stale.
- One shot changed → only that shot and proven adjacency/dependency range stale.
- Display text or commentary changed without canonical JSON change → no downstream invalidation.

Every stale artifact must carry a non-empty `stale_reason`. Non-stale artifacts must use `stale_reason: null`.
