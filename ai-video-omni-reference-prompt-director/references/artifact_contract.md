# Shared Artifact Contract

Every canonical JSON artifact owned or consumed by this Skill uses:

```json
{
  "contract_version": "ai-video-artifact-v1",
  "artifact_id": "PROMPT_PACKAGE_PROJECT01_V1",
  "owner_skill": "ai-video-omni-reference-prompt-director",
  "version": "1.0.0",
  "sha256": null,
  "approval_status": "draft",
  "dependencies": [],
  "affected_shot_uids": ["S001"],
  "stale_reason": null
}
```

## Envelope Rules

- `contract_version`: exactly `ai-video-artifact-v1`.
- `version`: SemVer matching `^[0-9]+\.[0-9]+\.[0-9]+$`.
- `approval_status`: `draft | assistant_validated | user_approved | stale | blocked`.
- `sha256`: `null` only for `draft`; every other status requires the canonical hash.
- `dependencies`: exact `artifact_id`, `owner_skill`, SemVer `version`, and `sha256`.
- `affected_shot_uids`: unique affected shots; may be empty for genuinely global capability records.
- `stale_reason`: required for `stale`, otherwise `null`.

Dependency record:

```json
{
  "artifact_id": "GLOBAL_LOOK_PROJECT01_V2",
  "owner_skill": "ai-video-global-look-lock",
  "version": "2.0.0",
  "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
}
```

## Canonical Hash

1. Copy the complete JSON object.
2. Remove only that envelope's top-level `sha256`.
3. Keep nested dependency hashes and all binary `file_sha256` fields.
4. Serialize UTF-8 JSON using `sort_keys=True`, `separators=(',', ':')`, `ensure_ascii=False`, `allow_nan=False`.
5. SHA-256 those exact bytes.

Changing semantic fields creates a new version. Never mutate an approved artifact in place.

Only `user_approved` upstream artifacts may enter a final executable payload. `assistant_validated` may enter an explicitly non-executable working preview. `draft`, `stale`, and `blocked` are forbidden.

## Actually Read Original Semantic Authorities

The Prompt IR cannot be its own source of truth, and Prompt must never manufacture a reduced authority projection. Every active Canon entry preserves two independent locks:

- `locator` + `file_sha256` for the actual binary or JSON payload;
- `artifact_record_locator` + `artifact_record_file_sha256` for the producer-owned full JSON artifact record.

For JSON root authorities these paths may be identical. Every binary image/video/audio/atlas requires a materialized JSON record sidecar. Resolve both only against `<project_root>`, reject absolute or `..` paths, recompute the record's complete canonical envelope hash, and compare envelope identity/version/hash/dependencies/scope exactly to the Canon entry. Status is also exact unless an active entry is a downstream-ineligible stale/blocked registry overlay over a previously approved immutable record and exactly one matching stale event carries the same reason and Shot scope. Read the original Shot Contract, Global Look, Storyboard, K1, K2, Previs V1/V2, and P1 shapes through owner-specific adapters. A self-authored projection, an unproved status divergence, a file/record mismatch, or a coordinated projection-plus-IR rewrite fails.

Global Look reference IDs are internal keys. Resolve `look_states[].reference_ids` through `look_reference_set[].reference_id` to the nested `artifact.artifact_id`; then verify the nested envelope, binary lock, record lock, and active Canon entry.
