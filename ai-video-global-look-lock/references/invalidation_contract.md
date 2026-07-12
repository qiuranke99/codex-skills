# Global Look Invalidation Contract

## Shared envelope and hash

Every authoritative artifact contains:

```json
{
  "contract_version": "ai-video-artifact-v1",
  "artifact_id": "...",
  "owner_skill": "ai-video-global-look-lock",
  "version": "1.0.0",
  "sha256": null,
  "approval_status": "draft",
  "dependencies": [],
  "affected_shot_uids": [],
  "stale_reason": null
}
```

For a frozen artifact, exclude only the top-level `sha256`, retain nested dependency hashes, serialize with `sort_keys=True`, `separators=(',', ':')`, `ensure_ascii=False`, `allow_nan=False`, and hash the UTF-8 bytes. Binary references use `file_sha256`.

## Invalidation matrix

### Core revision

Invalidate all look-applied storyboard frames, keyframes and video-generation prompts for all project shots. Rebuild State validation when the changed Core property is visible there. Preserve neutral motion/timing data unless it carries baked-in look imagery used as a provider reference.

### State revision

Invalidate only shots assigned to the changed State, their look-applied storyboard/keyframes, corresponding visual references and prompts. Other States remain valid if they share only unchanged Core properties.

### Shot Delta revision

Invalidate only the named Shot UIDs and their look-applied downstream artifacts.

### Reference repair

Invalidate every State and Shot assignment that names the repaired reference. Do not rewrite Look Core silently. If the repair requires a Core change, promote it to `core_revision`.

## Approval separation

- `draft`: mutable, `sha256` must be null.
- `assistant_validated`: contract and visual gates pass.
- `user_approved`: explicit user approval has been recorded.
- `stale`: a dependency or owned rule changed; `stale_reason` required.
- `blocked`: the unaffected contract may be complete, but a unique indispensable source prevents approval.

Downstream consumers may use only `assistant_validated` or `user_approved` artifacts, subject to their project policy.

## Predecessor-bound revision proof

Every non-initial Core, State, Shot Delta or reference repair binds exactly one frozen predecessor in `revision_scope.predecessor_artifact`. Its SemVer must increase. Validate the actual predecessor bytes with:

```bash
python3 scripts/validate_global_look.py <current.json> --previous-contract <frozen_previous.json> ...
```

`changed_json_pointers` must exactly equal the real semantic pre-to-post diff. The validator derives `look_core_changed`, changed State IDs and propagated Shot UIDs from the actual stable-ID records; a self-reported scope cannot hide an extra State, reference or Shot change. Invalidated and preserved artifact IDs are disjoint. Every preservation claim must also be passed to the shared Project Canon transition validator so its base and post Canon entries are byte-identical.
