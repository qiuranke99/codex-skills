# Shared Artifact Contract

Every canonical JSON artifact owned or consumed by this Skill uses this required envelope:

```json
{
  "contract_version": "ai-video-artifact-v1",
  "artifact_id": "KF_PACK_PROJECT01_V1",
  "owner_skill": "ai-video-keyframe-continuity-pack",
  "version": "1.0.0",
  "sha256": null,
  "approval_status": "draft",
  "dependencies": [],
  "affected_shot_uids": ["S001"],
  "stale_reason": null
}
```

## Required Fields

- `contract_version`: exactly `ai-video-artifact-v1`.
- `artifact_id`: stable ID; never recycle it for a different logical artifact.
- `owner_skill`: the only Skill allowed to mutate the artifact's owned fields.
- `version`: immutable version identifier.
- `sha256`: `null` only while `approval_status` is `draft`; otherwise the canonical JSON hash.
- `approval_status`: `draft | assistant_validated | user_approved | stale | blocked`.
- `dependencies`: exact upstream artifact ID/owner/version/hash records.
- `affected_shot_uids`: all and only shots whose output depends on this artifact; project-global artifacts may use an empty array.
- `stale_reason`: non-empty when status is `stale`; otherwise `null`.

Dependency records use:

```json
{
  "artifact_id": "STORYBOARD_S001_V3",
  "owner_skill": "ai-video-modular-storyboard",
  "version": "3.0.0",
  "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
}
```

## Canonical Hash

For a JSON artifact envelope:

1. copy the complete JSON object;
2. remove only the envelope's top-level `sha256` field;
3. keep every nested dependency `sha256` and every `file_sha256`;
4. serialize UTF-8 JSON with `sort_keys=True`, `separators=(',', ':')`, `ensure_ascii=False`, and `allow_nan=False`;
5. calculate SHA-256 over those exact bytes.

Binary images use their own `file_sha256`; that hash does not replace the artifact-envelope hash. Materialize every complete binary artifact record under the producing package's `owned_artifacts/` directory. Project Canon separately locks the project-relative primary locator/hash and JSON artifact-record locator/hash; package locators never resolve against another package root.

## Approval And Staleness

- `draft`: `sha256` must be `null`; downstream production compilation is forbidden.
- `assistant_validated`: hash required; may enter a working branch only when the user explicitly allows it.
- `user_approved`: hash required; eligible for final prompt compilation.
- `stale`: hash required and `stale_reason` required; must not enter downstream bindings.
- `blocked`: hash required; must not enter downstream bindings.

Changing an owned semantic field creates a new version and hash. Never rewrite an approved version in place.
