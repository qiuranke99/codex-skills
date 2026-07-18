# Material-Sensitive Product Master Asset Board Test Cases

These scenarios are the maintained acceptance map for contract v6. A test is green only when it asserts process exit code, exact structured result or blocker, evidence-grade behavior, and absence of forbidden mutation. Passing deterministic tests proves contract behavior, not universal visual quality or exact reverse engineering.

## Green Scenarios

| ID | Scenario | Required evidence |
|---|---|---|
| G01 | Standalone package | Package copied alone to an empty discovery root; all package tests and package-local CLIs run with repository siblings unavailable and `PYTHONPATH` cleared. No High-Control, Studio, aggregate, or adjacent Skill path is required at runtime. |
| G02 | Single clear front accepted | One fully decoded local front image freezes as `source_coverage_profile: clear_front_only`; no request for additional user images occurs before audited research. |
| G03 | Browser-first research | When in-app Browser is available, the run records actual visited exact-variant, same-family, and packaging-archetype queries/URLs, captures/evidence, timestamps, and evidence classes. |
| G04 | Audited fallback | When in-app Browser transport is unavailable, the exact failure is recorded and audited fallback queries are attempted for all three lanes. If every online surface is unavailable, all lanes record `blocked` and a conflict-free source-visible identity may complete a coverage-limited board without hidden-view fabrication. |
| G05 | Identity conflict resolved | Filename/user shorthand conflicts with readable product text; official/exact-variant evidence agrees with visible text. The visible/exact identity wins, the filename remains a rejected lead, and no user question is required. |
| G06 | Research versus reference rights | Public official/research-only media may be observed and cited while `selected_generation_reference: false` keeps it out of provider references. Only `user_provided` or `licensed` exact-visible/exact-variant captures may set the selection true. |
| G07 | Graded structure claims | `material_research.v1.structure_claims` separately binds source-visible exact, exact-variant verified, evidence-supported reconstruction, and unknown components with evidence IDs, allowed surfaces, and forbidden exact claims. |
| G08 | Evidence-derived topology | A clear-front-only run freezes 4-6 truthful primary/material/front-visible-structure/detail panels and may contain zero `multi_angle` panels. A research-backed run can freeze up to ten. No fixed 3-4-angle quota exists. |
| G09 | Truthful rear/side/bottom | Reconstructed hidden views contain only evidence-supported silhouette, cavity, tube parallax, or bounded archetype structure; no invented rear copy, barcode, batch text, bottom code, dimensions, material composition, or exact pump mechanism. |
| G10 | Prompt and worker binding | Exact prompt block occurs once; deterministic nonce-first single-imagegen exec and receipt bind prompt, ordered authorized references, contract, and the single material-research hash. |
| G11 | Terminal-LF recovery | Resolver accepts exact bytes or omission of exactly one frozen file-terminal LF, records frozen/recorded hashes and transport mode, preserves exact prompt/reference/call semantics, and reuses the completed PNG without regeneration. |
| G12 | Decision-rendered graded QA | Main agent opens source, selected research captures, and board at original detail; every panel/invariant records distinct evidence and board observations plus `view_authority`; grade laundering and fabricated hidden copy fail. |
| G13 | Atomic post-generation acceptance | Compiler re-audits rollout, QA, the single material-research chain, and PNG; writes deterministic 4K handoff and accepted commit last; same-byte rerun is idempotent. |
| G14 | Artifact-backed publication | Builder independently validates the complete chain and publishes board, full prompt pair/hashes, evidence hashes, worker/call, exec transport mode, actual external status, QA, approval, and finalization status. |
| G15 | One-request lifecycle | Explicit invocation completes through research, one fresh non-decision worker per attempt, main-agent visual QA, and one non-empty final without a second user message. |

## Red Scenarios

| ID | Scenario | Expected result |
|---|---|---|
| R01 | Implicit routing attempts a worker. | `blocked_worker_authorization` |
| R02 | Runtime imports a neighboring Skill, aggregate router, Studio file, fixed release path, or High-Control manager. | standalone validation failure |
| R03 | Source is truncated, corrupt, mislabeled, symlink-escaped, duplicated, or mutates after freeze. | exact `blocked_reference_*`; no overwrite |
| R04 | One front image is aliased as front, three-quarter, side, rear, and bottom to manufacture multiview authority. | `blocked_panel_view_authority_laundering` or `blocked_material_source_contract_invalid` |
| R05 | Search result is graded exact solely because it is visually similar, purple/clear, same capacity, or from a marketplace aggregator. | `blocked_research_fact_authority` or `blocked_identity_resolution_invalid` |
| R06 | Same-family/archetype evidence becomes an exact identity, label, dimension, supplier, material, mold, or engineering invariant. | `blocked_research_fact_authority`, `blocked_research_surface_authority`, or `blocked_archetype_identity_contamination` |
| R07 | Public official/research-only/unknown/restricted image, or same-family/archetype media, is passed to imagegen. | `blocked_reference_generation_rights` or `blocked_archetype_identity_contamination`; no worker spawn |
| R08 | Filename says one variant while visible and official exact evidence say another; system silently adopts filename or merges the variants. | `blocked_identity_resolution_invalid` or resolved-visible result; silent merge forbidden |
| R09 | Rear view adds ingredients, barcode, batch/country text, readable invented copy, or treats refracted/reversed front marks as a verified rear label. | `blocked_board_inspection_invalid` |
| R10 | Side/bottom/open/cutaway view claims exact dimensions, wall/base thickness, nozzle, thread/crimp, retention, material composition, or markings from archetype evidence. | structure or board-inspection blocker |
| R11 | Browser is available but not actually used, or fallback is used without recording the Browser attempt/error; prose merely claims browsing. | `blocked_material_research_runtime_provenance` |
| R12 | Online research is unavailable and the plan fabricates hidden views to satisfy a panel-count or angle quota. | source-contract/view-authority blocker; truthful topology reduction required |
| R13 | Exec uses comment decoy, dynamic/bracket second call, variable/template/concatenation transport, wrapper text, or changed references. | `blocked_worker_exec_source_mismatch`; no output |
| R14 | Exec differs by CRLF, whitespace stripping, two LFs, missing non-terminal byte, Unicode normalization, altered prompt/path/order/nonce, or AST-equivalent rewrite. | `blocked_worker_exec_source_mismatch` |
| R15 | Worker has earlier task/turn, second image call, unknown tool, wrong wait cell, non-empty decision-bearing final, failed image, or wrong lineage. | exact `blocked_worker_*` |
| R16 | Image path is not derived from exact thread+call, traversal/newest-file selection occurs, PNG is invalid/truncated, or generated bytes equal a source. | exact image/provenance blocker |
| R17 | QA is pending/empty/copied, alters scaffold order/evidence, omits authority/forbidden-claim checks, or calls archetype reconstruction exact. | `blocked_board_inspection_invalid` |
| R18 | 4K prompt repairs or upgrades identity, topology, hidden copy, structure, fill, state, or material evidence; adds provider controls/crop/reorder/panels. | enhancement/handoff blocker |
| R19 | Conflicting destination exists; accepted record is hand-written, early, duplicate, stale, selects failed QA, or omits material-research/exec bindings. | exact post-generation/accepted blocker; no commit |
| R20 | Final omits complete prompt pair, evidence hashes, transport mode, actual statuses, or is truncated/overwritten. | publication blocker; no partial success |
| R21 | A valid prompt is saved under any filename other than `<asset_id>_<attempt_id>_generation_prompt.md`. | `blocked_worker_prompt_sidecar_invalid` before exec artifacts, spawn, or image generation |

## Historical And Adversarial Evidence Fixtures

| ID | Fixture | Required assertion |
|---|---|---|
| H01 | 2026-07-10 control-flow failure | Main-agent imagegen with shell-output wrapper and empty finals cannot pass worker-exec or publication gates. |
| H02 | Encrypted-nonce provenance block | Generated image without provable worker nonce stops without newest-file guessing, fake acceptance, or unnecessary regeneration. |
| H03 | Bracelet topology drift | Alternating link type/rhythm across hero and macro is identity/topology failure, never 4K cleanup. |
| H04 | Single-front SA-LOV fixture | One clear front can complete a front/material/detail board; it cannot be laundered into mandatory side/rear/bottom evidence. |
| H05 | Belle filename versus Gliss Lumiere source | Visible `GLISS LUMIERE` and official AD84-C evidence resolve identity; filename `Belle` and AD84-E sibling are retained as conflict/rejected lead, never merged. |
| H06 | Real terminal-LF omission | Frozen 12,826 versus recorded 12,825 characters (12,836/12,835 UTF-8 bytes because of the non-ASCII path), with exact shared prefix and one final LF omitted, passes only `single_terminal_lf_omitted`, binds the existing image, and never regenerates. |
| H07 | View-authority laundering | One front image assigned to multiple source aliases or panel roles cannot establish hidden-surface coverage. |
| H08 | Fabricated rear copy | A plausible-looking rear barcode/ingredients/registration block without exact hidden-surface evidence fails even if visual QA prose calls it realistic. |
| H09 | Same-family exactness laundering | Confirmed sibling mold may support bounded geometry reconstruction but cannot prove exact variant copy, liquid, print, marks, or engineering dimensions. |
| H10 | Browser outage | In-app Browser `Transport closed` is recorded; auditable fallback evidence can proceed. If fallback attempts are also `blocked`, a conflict-free direct source identity contracts output to source-only rather than hallucinating hidden views. |
| H11 | Research/reference rights split | Exact-variant official public media contributes observations with `selected_generation_reference: false` but is absent from `reference-manifest.json` and worker arguments. |
| H12 | Standalone release extraction | The package copied outside the High-Control checkout remains discoverable/invokable and passes package validation; High-Control is tested only as distribution integration. |

## Runtime Evidence Boundary

Deterministic package tests prove artifact, provenance, decoder, research-grade, rights, schema, decision-rendering, and state-transition behavior. They do not prove an exhaustive web search, exact hidden 3D geometry, universal visual quality, or native 4K. A real generation run is evidence only when its source bundle, single `material_research.v1` artifact with graded `structure_claims`, contract, worker rollout, PNG, opened evidence, panel/invariant decision, frozen QA, compiler-created accepted record, prompt pair, and non-empty final are retained.

The phrase “searched the whole web” is prohibited. State the queries, sources, surfaces, and evidence limits actually inspected. Assistant QA is not user approval, and evidence-supported reconstruction is not exact product CAD.
