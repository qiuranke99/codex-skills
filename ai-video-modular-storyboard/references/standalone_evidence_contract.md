# Standalone Source and Replacement Evidence

Use this branch for source-authorized intrinsic text or applied replacement
when no Project Canon integration is requested. It consumes direct files;
it neither creates a registry nor searches for producer packages. Ordinary
no-text, no-replacement packages retain the simple structural validator; they
may opt into this stronger direct-source check without being forced to do so.
The machine contract is `source_evidence.schema.json`.

## Freeze before production or replacement

Create a small input-lock document outside the mutable storyboard package from
the supplied approved source artifacts. Retain its byte SHA-256 in the calling
task or another caller-controlled checkpoint before generating or replacing
frames. Pass that retained value to the validator. Do not recompute it after a
failure to make changed evidence pass. Missing source approval blocks only work
that needs that source; drafting and unaffected authorized work can continue.

Each `sources` item contains an exact `artifact_ref`, an `artifact_type`, and
separate input-root-relative paths and SHA-256 hashes for primary bytes and the
complete JSON artifact record. The record must match the pinned identity/hash,
be approved (`assistant_validated` or `user_approved`) and non-stale. This checks
the supplied approval state, not whether an actual human granted it.

For Shot and Look authority the primary file is the JSON artifact itself.
Their semantic fields, declared source files, and visual-reference bytes are
validated. For intrinsic text the primary file is the actual source asset,
not an arbitrary URL or a prose assertion. Its category, shot scope, exact
prompt binding, and dependency must also match. Inspect source media before
using its text; byte validation does not perform OCR or establish legal rights.

## Replacement base

Before staging a replacement, add one `replacement_bases` item containing its
`transaction_id`, the original manifest's exact `artifact_ref`, and original
`file_sha256`. Preserve the original manifest and prior frame/prompt/board files.
The transaction's snapshot must match this independently retained lock. Its
upstream locks must equal the current manifest's locks; unaffected frame records
and hashes remain identical. Changed current and board versions must increase.

The external digest is the trust boundary. A local hash cannot defeat an actor
who can replace both the original sources and the caller's retained digest;
do not describe this as cryptographic approval or trusted historical attestation.

## Validate

```text
python scripts/validate_storyboard_package.py <package-root> --input-root <input-root> --source-evidence <caller-frozen.json> --source-evidence-sha256 <retained-sha256>
```

All three flags are required for these standalone risk branches. No Canon
receipt belongs to this branch. If Canon integration is explicitly supplied,
use `--project-root` and `--project-canon-manifest` instead; its active/superseded
entries, primary/record bytes and receipt remain mandatory and are never
replaced by standalone evidence.
