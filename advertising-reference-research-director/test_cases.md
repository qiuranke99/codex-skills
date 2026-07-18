# Runtime and Validator Test Cases

## Canonical command

```bash
python3 scripts/test_contract.py
```

The suite uses only the Python standard library. The checked-in
`valid_run_blueprint.json` is intentionally a minimal sentinel: the harness
reads only `candidate_count=30`, `selected_count=20`, and `rejected_count=10`.
`scripts/test_contract.py` constructs and validates the complete temporary run;
no unused blueprint field is presented as tested behavior. The suite never
treats a network request as browser media proof.

## Valid contract

The generated image fixture must pass all checked-in JSON schemas and the
computed gates:

- exactly 30 qualified candidates;
- exactly 20 selected and 10 qualified-but-rejected candidates;
- disjoint partition whose union is the shortlist;
- 30 fresh, independent, modality-specific browser receipts;
- hash-bound capture records covering access, media, object match, and provenance;
- accountable provenance and six separately assessed rights dimensions;
- no unapproved duplicate group;
- broad-brief diversity of at least five domains, four source families, and
  four to six territories, with the declared metrics equal to computed values;
- finder, verifier, relevance curator, diversity curator, and auditor separation;
- globally unique approach/query IDs, compatible executors, candidate trace
  closure, terminal approach states, nonzero yield for completed approaches,
  ledger-reconciled structured failure records where required, and at least three distinct executed
  completed methods with exact coverage declarations;
- a passed adversarial audit covering all 30 candidates;
- a concrete feedback event that changes `v1` to `v2`, reaches input
  `completion_evidence.status=applied`, and records its repair;
- exactly ten byte-hashed core artifacts, including the capture ledger and
  generated review board;
- a variable `referenced_evidence_contract` that exactly hash-binds the final
  relevance/diversity/resolution reviews, adversarial audit,
  feedback-invalidated intent snapshots, and diversity-waiver evidence read by
  the validator, with neither omissions nor unused extras;
- `run_mode=test_fixture`, with ordinary PASS explicitly ineligible for production delivery.

## Representative adversarial mutations

`tests/fixtures/adversarial_cases.json` drives independent mutations. Every
mutation must fail closed with the named stable finding code, not an exception:

The table is representative, not a complete enumeration. The executable
`test_contract.py` families are the authority for the full regression set.

| Mutation | Required finding |
|---|---|
| selected item removed | `SCHEMA-01` (schema gate stops semantic validation) |
| receipt removed | `VERIFY-01` |
| stale receipt | `FRESHNESS-01` |
| video poster/player without playback progress | `VERIFY-02` |
| discovery-only provenance rejected by the qualified-receipt schema | `SCHEMA-01` |
| duplicate canonical item URL | `DEDUP-01` |
| source/territory diversity collapse without waiver | `DIVERSITY-01` |
| finder verifies its own candidate | `AGENT-01` |
| auditor independence contradicts the passed-report schema | `SCHEMA-01` |
| feedback keeps the same intent version | `FEEDBACK-01` |
| one rights dimension is removed | `SCHEMA-01` |
| HTTP precheck is substituted for browser verification | `VERIFY-01` |
| candidate and receipt use a foreign run/intent/version | `CANDIDATE-01` |
| receipt source or checked URL does not bind the candidate | `VERIFY-01` |
| image/video evidence locator does not bind the candidate | `VERIFY-02` |
| passed provenance has no accountable owner or URL | `PROVENANCE-01` |
| accessible item declares HTTP 404 | `VERIFY-03` |
| receipt uses an access mode forbidden by intent | `VERIFY-03` |
| route reason contradicts the frozen modality | `ROUTE-01` |
| draft intent is presented as complete | `INTENT-01` |
| scene/human/axis/must-have/anchor constraint is unbound or contradicted | `RELEVANCE-01` |
| market, language, or content maximum age is contradicted | `RELEVANCE-01` |
| image candidate declares a video object type | `SCHEMA-01` |
| candidate rights exceed the frozen intent boundary | `RIGHTS-01` |
| selected/report broad-brief flags contradict intent | `DIVERSITY-01` |
| feedback repair remains pending | `FEEDBACK-01` |
| approaches remain planned in a completed run | `AGENT-01` |
| audit evidence reference does not exist | `AUDIT-01` |
| review board is blank or omits the 20/10 partition | `ARTIFACT_INTEGRITY` |
| rights summary differs from receipt evidence | `RIGHTS-01` |

The strict-boundary and tool-safety families also exercise the post-audit trust
boundaries: strict JSON rejects duplicate keys and non-finite numbers; all
artifact writers serialize before mutation, use atomic replacement, preserve
the prior file on injected I/O failure, clean temporary files, and refuse leaf
symlinks or input/output clobbering. Receipt import preserves the full history,
binds every row to the current run/intent/pack/source/modality and independent
finder/verifier identities, evaluates qualification from the unique latest UTC
instant, and rejects same-instant receipts even when their timezone strings
differ. Repeated receipt/approach/query IDs fail; future
timestamps, 1×1 images, video progress beyond duration, title-only video matches,
high-risk rights overclaims, session-based public-link claims, empty approaches,
reposts, report self-validation, nonexistent or unbound referenced evidence,
inverted dominance, capture-hash drift, fixture-to-production relabeling,
production plan freeze after search/discovery began,
cross-pack global-feedback divergence, and unsafe gallery URLs all fail closed.
`--require-production-contract-eligible` rejects a structurally valid fixture,
and the legacy `--require-production-deliverable` rejects even an unsigned
production-live simulation with `ATTEST-01`. Feedback
input may say only `applied`; `validated` is derived by the external validator
result and never by a report reference inside the input run.

The `drop_selected_item` case is a specific regression test: malformed
partition data previously reached a `StopIteration`; it must now fail at the
schema gate without reaching unsafe semantic indexing.

## BOTH routing

`parallel_packs` has a fixed layout:

```text
<run_root>/
├── 00_intent/intent_brief.json
├── 01_orchestration/approach_registry.json
└── packs/
    ├── <image_pack_id>/02_candidates ... 05_feedback ... 06_output
    └── <video_pack_id>/02_candidates ... 05_feedback ... 06_output
```

The root validator reads both pack contracts and returns `PASS` only when the
image pack independently passes 30/20/10 and the video pack independently
passes 30/20/10. A missing or extra pack directory is `ROUTE-02`.

For `unified_territory`, the single mixed pack must satisfy the exact image and
video qualified/selected targets declared by the intent contract and the
cross-modal territory minimum. Those counts are computed from candidates, not
trusted from the report.

## HTTP and browser boundary

`verify_candidates.py --http-precheck` makes no network request and emits a schema-valid receipt with
`verification_surface=http` and `outcome=blocked`. Even HTTP 200 cannot set:

- `page_rendered=true`;
- media rendered/played;
- object matched;
- provenance confirmed;
- qualified outcome.

An imported final receipt must use `in_app_browser`, `chrome_authenticated`, or
`manual_visual_review`; image receipts require a concrete rendered asset and
dimensions, while video receipts require player presence, playback start,
positive observed progress, and a matched specific work.

Historical blocked, failed, or stale receipts remain in the ledger. They do not
block delivery when—and only when—the candidate has one unambiguous, newer,
qualified browser/manual receipt and its `verification_receipt_id` binds that
latest row.

`test_fixture`, `retrospective_smoke`, and `production_live` are deliberately
distinct. A fixture or retrospective run may receive ordinary `PASS` for its
own acceptance class, but only a `production_live` run whose *recorded* plan
freeze precedes its *recorded* direct captures can pass
`--require-production-contract-eligible`. This is an internal chronology and
binding check, not cryptographic proof that the plan or browser action existed
at the declared time; the package always reports `production_deliverable=false`.

## Dedup and gallery

- tracking parameters are stripped before URL identity comparison;
- stable ID, capture-bound exact/sample-manifest hash, perceptual hash, and
  declared version groups are checked independently;
- every receipt binds the validator-recomputed final-30 comparison-set hash;
- exact identity collisions cannot be waived as authorized versions;
- soft near-duplicates require a hash-covered manual version review whose
  members and fingerprint evidence exactly match the detected group;
- dominance requires no worse score on all nine direction-normalized
  dimensions and a strict improvement on the declared axis; mixed trade-offs
  fail, while exact vectors require the deterministic stable-ID tie-break;
- generated HTML escapes untrusted titles and rationales;
- gallery links remain canonical landing pages and do not copy remote media.

## JSON-Schema enforcement

The local schema runtime implements and tests `$ref`, `allOf`, `if/then/else`,
`anyOf`, `oneOf`, `not`, `contains`, `minContains`, and `maxContains`, plus every
structural keyword used by the checked-in schemas. It recursively rejects any
unsupported keyword, including one hidden in an untaken branch. The complete
checked-in `source_registry.json` is also validated against its schema.

## Non-deterministic release acceptance

These deterministic tests validate declared contract behavior and internal
consistency only. They do not replace the
retrospective media-path smoke evidence for one historical image 30→20 run and
one historical video 30→20 run, a real user-correction reroute, or a new
preregistered production audit. Retrospective evidence is not
production-contract-eligible or production-deliverable and must never be
upgraded in place. Project browser
artifacts belong in the validation SSOT, never in this public Skill package.
