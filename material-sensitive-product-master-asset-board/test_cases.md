# Material-Sensitive Product Master Asset Board Test Cases

These scenario IDs are the maintained acceptance map for contract v4. A test is green only when it asserts the process exit code, the exact structured result or blocker, and absence of forbidden output mutation.

## Green Scenarios

| ID | Scenario | Required evidence |
|---|---|---|
| G01 | Standalone package | Package copied alone to an empty discovery root; all 40 package regressions plus every package-local core CLI run with repository siblings unavailable and `PYTHONPATH` cleared. |
| G02 | Decoded reference freeze | Valid PNG/JPEG/WebP sources are fully decoded; v2 manifest records detected format/MIME/dimensions, canonical suffix, ordered paths, sizes, file hashes, and bundle hash. |
| G03 | Idempotent freeze | Repeating the exact source freeze produces byte-identical artifacts; a differing existing artifact is not overwritten. |
| G04 | Semantic source contract | A complete draft freezes source authority/allowed use/exclusions, verified-inferred-needs_source facts, all critical invariants, and a legal 7-10 panel plan into one contract and exact prompt block. |
| G05 | Prompt-block binding | The exact frozen material prompt block occurs once in the UTF-8/LF generation prompt and is bound into the worker exec receipt. |
| G06 | Deterministic worker exec | Renderer produces the exact nonce-first, single-literal-imagegen, ordered-reference exec source and receipt; resolver compares the entire actual source byte-for-byte. |
| G07 | Whole-worker binding | One fresh worker has exactly one task/turn, exact parent/checkpoint/agent/nonce binding, one imagegen exec, only bound waits, one completed image event, and empty finals. |
| G08 | Complete PNG decode | Resolver verifies and fully loads the thread+call-derived PNG, records actual dimensions/hash, and creates board/result artifacts without overwriting. |
| G09 | Non-exact dimensions | A source-faithful `1672x941` or `1536x1024` board remains content-QA evidence; dimensions alone do not fail or trigger repair. |
| G10 | Complete content QA | QA covers every board gate, every planned panel, and every critical invariant exactly once; all accepted results pass and cite observed source fidelity. |
| G11 | Focused repair ledger | At most attempts 01-03 exist; every repair has fresh prompt/exec/spawn/result/board/QA and only one immutable accepted attempt. |
| G12 | Image-specific 4K handoff | Deterministic package-local renderer derives the exact prompt from the accepted board, every original source, source contract, and QA-authorized artifact cleanup operations; strict JSON handoff binds both prompt paths, exact 16:9/4K request, and a legal external status/QA/approval tuple. |
| G13 | Artifact-backed publication | Builder independently revalidates every accepted path/hash/schema/image and emits one create-only payload containing board, full prompt pair, hashes, QA/status evidence, and published states. |
| G14 | One-request lifecycle | Explicit invocation completes through one non-decision worker and one non-empty main-agent final without a second user message. |

## Red Scenarios

| ID | Scenario | Expected result |
|---|---|---|
| R01 | Implicit routing attempts a worker. | `blocked_worker_authorization` |
| R02 | v1 manifest, v1 accepted attempt, or direct original-path resolver mode. | `blocked_legacy_material_run_v1` |
| R03 | Source is truncated, corrupt, mislabeled, symlink-escaped, duplicated, or mutates after freeze. | exact `blocked_reference_*` code; no frozen overwrite |
| R04 | Source contract omits an alias, authority, fact class, critical invariant, or required panel; plan has not 7-10 panels, not exactly one anchor, not 3-4 angles, or no material response. | exact `blocked_source_contract_*` code |
| R05 | Planned panel uses excluded content or a `needs_source` fact. | source-contract blocker |
| R06 | Prompt omits, changes, or duplicates the frozen material prompt block. | prompt/exec blocker |
| R07 | Actual imagegen uses a compliant literal in a comment but a bracket-notation/dynamic second call with different arguments. | exact exec-source mismatch; no output |
| R08 | Prompt has variable/template/concatenation/shell-result transport or the historical 44-character `Exit code / Wall time / Output` wrapper. | exact exec-source or prompt mismatch |
| R09 | Worker has an earlier task/turn, second image call, unknown call-shaped event, unrelated tool, wrong wait cell, non-empty final, or failed image event. | exact `blocked_worker_*` code |
| R10 | Worker/reference/spawn/exec/result/hash lineage differs by one byte or path. | exact provenance blocker |
| R11 | Image event path is not derived from exact thread+call, contains traversal, or newest-file selection is attempted. | exact image-path blocker |
| R12 | PNG has only signature/IHDR, bad CRC, missing IDAT/IEND, is truncated, or cannot be fully decoded. | `blocked_worker_image_invalid`; no board/result |
| R13 | Generated board bytes equal an original source. | generated/source collision blocker |
| R14 | Output path aliases prompt, source, board, accepted record, result, or an existing different output. | location/conflict blocker; all inputs unchanged |
| R15 | QA omits or duplicates a planned panel/invariant, contradicts its own status, or accepts a failed gate. | `blocked_board_inspection_invalid` |
| R16 | Hero/macro panels change source chain type, link rhythm, connector topology, component order, edge thickness, fill boundary, label identity, or source-supported state while QA says passed. | repair-required content blocker |
| R17 | A defect is cleanup-eligible while not a low/medium raster artifact, cites any critical invariant, omits a source alias, or uses an unapproved cleanup operation. | board-inspection or handoff/publication blocker |
| R18 | 4K prompt is free prose or differs from the deterministic re-render; handoff is YAML/regex-like text, omits either prompt/source, adds provider controls, uses an illegal external status/QA/approval tuple, or has mismatched hashes. | exact enhancement-prompt or `blocked_4k_handoff_invalid` blocker |
| R19 | Accepted record is empty, selects failed QA, omits a direct worker exec source/receipt path or hash, binds stale artifacts, exists twice, or is frozen before the 4K artifacts. | `blocked_accepted_attempt_*` |
| R20 | Final output omits either full prompt/hash/status, exceeds capacity, or overwrites an artifact. | exact publication blocker; no partial output |

## Historical Evidence Fixtures

- `H01-control-flow-red`: 2026-07-10 thread `019f4b71-b716-71f0-bfc8-24ec7b650ff5`. Main-agent imagegen completed with a 44-character shell-output wrapper, both final records were empty, and no post-image prompt pair was published. It must never pass the worker-exec or final-output contract.
- `H02-provenance-block-green`: the first v3 material smoke generated an image but could not prove the encrypted worker nonce. It correctly stopped without newest-file guessing, regeneration, or fake acceptance.
- `H03-content-qa-red`: the v3 accepted bracelet board changed the fine uniform source chain into larger alternating round/oval links across hero and macro panels while another panel used a different chain. It is a topology failure, not a minor 4K cleanup defect, and must fail R16/R17.

## Runtime Evidence Boundary

Deterministic package tests prove artifact, provenance, decoder, schema, and state-transition behavior. They do not prove universal visual quality or native 4K. A real image-generation run may be cited only when its exact source contract, worker rollout, PNG, actual inspection, complete QA matrix, accepted record, prompt pair, and non-empty final are retained. Assistant QA alone is not user approval, and the prior bracelet smoke is not a visual-success fixture.
