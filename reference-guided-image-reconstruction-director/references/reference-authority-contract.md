# Reference Authority Contract

Use an attribute-level contract instead of assigning a reference a global label such as “style.” The contract must preserve what is known, expose what is inferred or chosen, and prevent a later stage from rewriting upstream facts or approvals.

## 1. Three Separate Ledgers

### Source Fact Ledger

Record immutable input facts:

- source ID, original filename, byte or file provenance, dimensions, readability, rights state, and declared role;
- directly observed content and defects;
- absent, cropped, occluded, illegible, contradictory, or otherwise missing evidence;
- claim status: `known`, `observed`, `inferred`, `chosen`, or `unknown`;
- confidence and the source supporting each consequential claim.

Do not rewrite this ledger after a user decision or imported result. An image that the user manually generated on an external platform becomes a new source only after import with its own provenance; the Skill did not generate it.

### User Decision Ledger

Record explicit choices separately:

- preserve, change, remove, and replace instructions;
- role declarations for each reference;
- selected workflow and acceptable inference level;
- approvals, rejections, and exact-asset requirements;
- the user's intended manual external platform and acceptable inference level. This records an execution preference; it never authorizes the Skill, Codex, or a tool to generate or edit pixels.

An instruction to preserve everything does not erase a specific removal. Normalize it into an explicit exception.

### Manual External Stage Ledger

Separate the actionable plan from what the user later reports or imports:

- planned stage purpose, exact user-performed upload order, included and excluded sources;
- source labels, role scopes, direct-copy prompt, platform-settings guidance, and known or unknown interface constraints;
- after manual external execution only: imported output provenance and status;
- read-only QA result, defects, approval gate, and retry delta.

A fresh plan remains `prompt_package_ready`. Manual external execution alone does not change the contract; only a result that the user then imports with bound provenance may become `structure_master_candidate`, `candidate_unapproved`, or `qa_failed_directional_retry_ready`. Human approval for an intermediate master applies only to its declared downstream scope.

## 2. Attribute Families

Do not collapse these families into one style role:

- **Protected structure:** composition, camera intent, crop, aspect ratio, perspective system, spatial layout, object count, position, relative scale, topology, and occlusion.
- **Geometry and construction:** visible shape, proportions, joins, thickness, manufacturing or installation precision, articulation, and surface continuity.
- **Identity:** product model, face, character, body proportions, wardrobe, accessory, prop, and brand identity.
- **Appearance:** material, texture scale, color, finish, wear, lighting direction, light quality, exposure, contrast, lens response, depth of field, grain, and atmosphere.
- **Truth-sensitive graphics:** readable text, logo, label, interface, symbols, numerical markings, and regulated claims.

The target or an approved structure master normally owns protected structure. A realism reference must not receive protected-structure authority merely because it looks more realistic.

## 3. Authority Matrix

Create one row per consequential attribute or coherent attribute group:

| Field | Meaning |
| --- | --- |
| `attribute` | One specific attribute or coherent group. |
| `primary` | At most one source that can decide the attribute. |
| `allow` | Sources allowed to contribute evidence without overriding the primary. |
| `deny` | Sources explicitly forbidden to contribute the attribute. |
| `role_state` | `known`, `inferred`, `chosen`, or `unknown`. |
| `evidence` | Visual observation or user declaration supporting the assignment. |
| `confidence` | Calibrated confidence, not a substitute for evidence. |
| `conflicts` | Overlap, contradiction, crop risk, count risk, or identity risk. |
| `missingness` | Facts the available sources cannot establish. |

Hard conflicts include:

- multiple primary sources for a critical attribute;
- pattern-overlapping rows such as `appearance.*` and `appearance.material` that resolve to different `primary` or `allow` source sets;
- the same source appearing in `allow` and `deny` for one attribute;
- a reference receiving protected-structure authority;
- an `unknown` reference receiving resolved `primary` or `allow` authority;
- two references claiming mutually exclusive identity, material, count, or camera facts;
- a source being treated as exact evidence for an attribute it does not show or declare exact;
- a deleted entity being allowed back through a reference.

Do not solve a conflict by averaging references. Narrow roles, choose one authority with the user's decision, split into explicit variants, or keep the attribute unresolved.

## 4. Preservation and Removal Normalization

For every removed entity, create an explicit exception with the full cleanup closure:

```text
preserve_scope = all target elements
explicit_exception = removed entity
cleanup = cast shadows + reflections + contact traces + occlusion residue
          + revealed-background repair + reference reintroduction paths
```

Add the removed entity to every reference permission's `deny_entities` list, including inventoried references not currently uploaded. If a reference explicitly allows the entity, or omits that denial, the contract is invalid until the permission or user decision is corrected.

## 5. Truth-Sensitive Boundaries

- Exact text, logos, labels, faces, product details, and hidden structure require exact evidence.
- A visually similar reference is not exact evidence unless the user or provenance establishes the required identity and the relevant attribute is visible.
- If exact evidence is absent, keep the attribute unresolved, leave the affected area blank or non-legible when acceptable, or move it to a later exact composite.
- Do not claim that a plausible generated detail is authentic, approved, or source-backed.
- For people and characters, split face identity, body proportions, pose, hair, expression, wardrobe, and lighting. A pose or look reference cannot silently contribute identity.
- For products, split silhouette, visible components, labels, color, material, and state. Do not infer hidden or model-specific construction from a category look reference.

## 6. Structured JSON Contract

The validator at `../scripts/validate_reconstruction_contract.py` accepts one UTF-8 JSON object. These top-level fields are mandatory and correctly typed: `execution_boundary`, `delivery_state`, `external_result_provenance`, `platform_parameter_guidance`, `assets`, `intent`, `authority`, `reference_permissions`, `stages`, `truth_sensitive`, and `status`. An assets-only object is invalid.

The structured surface is closed. The only top-level keys are the required fields above plus optional `version`, `target_id`, `direct_copy_prompts`, `protected_structure`, `user_request`, and `notes`. `user_request` and `notes` may be strings only and preserve non-authoritative user wording; text such as “call imagegen” cannot grant an action, tool, or permission. Every nested asset, provenance, resolution-guidance, dimensions, intent, exception, authority, permission, stage, target-reuse, and truth-sensitive object is likewise closed to the fields documented below. Unknown keys are hard errors. In particular, fields such as `tool_calls`, `tool`, `executor`, `action`, `dependencies`, `automation`, `api`, `login`, `upload`, `submit`, `poll`, `download`, and `generated_by` are never callable contract fields.

JSON object keys must be unique at every depth. The CLI parser rejects duplicates before first-wins or last-wins interpretation can occur; this includes top-level boundary/status fields and nested asset, stage, or provenance fields.

`authority` and `stages` must be non-empty and substantive. Here, a stage is an actionable manual external plan, not a callable Codex or tool action. When the user cannot proceed, use an unresolved authority row plus an explicit `blocked` stage and blocked status rather than empty arrays.

### Prompt-Only Delivery Boundary

- `execution_boundary` must be exactly `manual_external_prompt_only`. No other value can authorize direct pixel generation or editing.
- `delivery_state` is `prompt_plan` for a fresh text package and `imported_external_candidate` only after the user manually generated a result externally and imported it.
- `external_result_provenance` is empty for `prompt_plan`. For an imported candidate it contains one or more objects with exactly four fields: a unique non-empty `result_id`, exact `origin: user_manual_external_generation`, boolean `imported_by_user: true`, and a non-empty user-supplied `provenance` statement.
- Every provenance `result_id` must bind to a declared asset. `structure_master_candidate` binds only to a `structure_master`; `candidate_unapproved` and `qa_failed_directional_retry_ready` bind only to a `candidate_result`.
- A `prompt_plan` cannot declare any `candidate_result` asset. In `imported_external_candidate`, every declared `candidate_result` must be bound by a valid provenance row; one valid row cannot legitimize an extra stray candidate. A `candidate_result` with `approved: true` is always invalid in this contract lifecycle.
- The validator checks declaration consistency only. It cannot inspect external-platform history or prove that a provenance statement is true.

### Resolution and Platform Parameters

`platform_parameter_guidance` is required and contains exactly:

- `semantic_target`: non-empty string describing the desired output quality without an affirmative native-4K or exact-pixel guarantee;
- `prompt_guarantees_dimensions`: boolean and exactly `false`;
- `dimensions_fact_state`: `known`, `observed`, `user_reported`, or `unknown`;
- `dimensions_evidence_type`: `authoritative_record`, `inspected_file_metadata`, `user_report`, or `none`;
- `actual_pixel_dimensions`: `null` when the fact state is `unknown`; otherwise an object containing exactly positive integer `width` and `height`;
- `settings_evidence`: non-empty evidence or missingness statement that also makes no affirmative native-4K or exact-pixel guarantee.

The fact state and evidence type are one-to-one: `unknown -> none`, `known -> authoritative_record`, `observed -> inspected_file_metadata`, and `user_reported -> user_report`. A non-unknown state cannot pair positive dimensions with a settings statement that explicitly says no dimensions are known or evidenced. This is a declaration-consistency gate only; the validator cannot prove that an authoritative record, inspected metadata, or user report is truthful.

Optional `direct_copy_prompts` is an array of non-empty strings. It may express a semantic high-resolution target and tell the user to choose an external-platform setting, but it cannot make an affirmative commitment that wording, a setting, or a process guarantees native 4K or exact pixel dimensions. The same rule applies to `semantic_target` and `settings_evidence`. Classification is sentence/contrast-clause based: first identify and remove explicit negative commitment phrases, including `non-guaranteed`; then reject any remaining independent affirmative predicate. Deterministic modifiers such as always, regardless/irrespective of settings, independent of platform controls, in all cases, no matter the platform settings, `无论平台设置如何`, `不受平台设置影响`, and `在所有情况下` are affirmative only when that clause has no explicit negative commitment. Therefore “Regardless of platform settings, native 4K is not guaranteed” remains a legal caveat. Categorical declarative output/result claims such as “The output is native 4K” and `输出为原生4K` are commitments in every fact state; a positive dimensions record never exempts them. Numeric declarative output facts use only the parseable English form “The (exact) output/result (pixel) dimensions are W x H pixels” and narrow Chinese form `输出/结果(像素)尺寸为/是W×H(像素)`. They are invalid under `unknown`; under `known`, `observed`, or `user_reported`, every parsed pair must exactly equal `actual_pixel_dimensions`, otherwise validation emits `E_DECLARATIVE_OUTPUT_DIMENSION_BINDING`. The existing one-to-one evidence-type gate still determines whether that non-unknown state is structurally valid. An inspected-file numeric fact additionally requires `observed + inspected_file_metadata` and exact width/height agreement; its documented forms are “The inspected file dimensions are W x H pixels” and `经检查，文件/图像/图片尺寸为W×H像素`, with failures reported as `E_INSPECTED_FILE_DIMENSION_BINDING`. An imperative non-guaranteed target remains legal.

All three authoritative text surfaces reject the internal tokens `imagegen`, `image2gen`, and `image_gen__imagegen`, and any language directing Codex or this Skill to act. Ordinary imperatives addressed to a user-operated external platform—such as create, edit, or reconstruct—remain legal. These checks do not censor optional non-authoritative `user_request` or `notes` strings; those fields preserve wording but grant no permission.

### `assets`

Required non-empty array. Each item contains:

- `id`: unique non-empty string;
- `kind`: `target`, `reference`, `structure_master`, `candidate_result`, `exact_asset`, or `mask`; `candidate_result` is an imported downstream or QA output and is not a stage input;
- optional `approved`: strictly boolean; `true` records an external scoped human decision but the validator cannot create that decision;
- optional `contamination_risk`: string enum `low`, `medium`, or `high`; surrounding whitespace is normalized and every other value or type is invalid;
- optional `exact_attributes`: array of meaningful attribute paths for which this asset is declared exact evidence.

Those five keys are the complete asset object surface; no execution, tool, automation, or provenance shortcut field is allowed.

Exactly one asset must have kind `target`. Zero or more assets may have kind `reference`.

### `intent`

Required object with all three fields:

- `preserve_all`: boolean;
- `remove`: array of entity IDs or stable entity names;
- `explicit_exceptions`: array of objects containing `entity` and `cleanup`.

These are the only intent keys. Each exception contains exactly `entity` and `cleanup`.

Every removed entity requires an explicit exception regardless of `preserve_all`. The cleanup list must include `cast_shadows`, `reflections`, `contact_traces`, `occlusion_residue`, `revealed_background`, and `reference_reintroduction`.

### Attribute Paths and Protected Structure

Use one shared raw scope grammar everywhere the contract names an attribute. Validate the raw string before any normalization. It must be lowercase ASCII dotted `snake_case`: each segment contains lowercase ASCII letters or digits separated by single underscores, segments are separated by one dot, and there may be at most one wildcard only as a trailing `.*`. Leading/trailing whitespace, uppercase, empty segments, punctuation, slash/colon replacement, embedded wildcards, and repeated wildcards are hard errors. Thus `appearance.material`, `appearance.material.*`, and the recognized root `appearance` are valid; `Appearance.Material`, `appearance.*?`, `appearance..material`, `appearance.?.material`, `appearance.*.*`, and `appearance.*.material` are invalid. Global `*` is accepted only as a deny umbrella.

After raw validation, the following lowercase legacy aliases may map deterministically to qualified paths: `composition`, `camera`, `camera_intent`, `crop`, `aspect_ratio`, `perspective`, `perspective_system`, `spatial_layout`, `layout`, `object_count`, `position`, `relative_scale`, `scale`, `topology`, and `occlusion`. Uppercase aliases are invalid; the validator never silently lowercases or removes characters.

A recognized bare family root covers its descendants: `appearance` overlaps and covers `appearance.material`. A qualified path without `.*` is exact; `appearance.material` does not silently cover `appearance.material.roughness`. A trailing wildcard covers its base and descendants. Authority overlap, authority-to-permission matching, protected-structure checks, exact-evidence coverage, and conflict checks all use these same semantics.

Protected structure includes all `frame.*` and `structure.*` paths plus the documented defaults. `protected_structure.*` is a shorthand that denies every protected attribute. `frame.*` and `structure.*` may be used together for the same coverage. `appearance.texture_scale` is appearance, not structure. The optional `protected_structure` array may add stricter paths or families but cannot remove defaults.

### `authority`

Required non-empty array. Each row contains:

- `attribute`;
- `primary`: array containing zero or one source ID;
- `allow`: array of contributing source IDs;
- `deny`: array of forbidden source IDs;
- optional `role_state`: `known`, `inferred`, `chosen`, or `unknown`;
- optional `evidence`, `confidence`, `conflicts`, and `missingness`.
- optional `unresolved`: boolean, and `reason`: string, only for an explicitly unresolved row.

These are the complete authority-row keys. A resolved row cannot carry a blocked-only `reason`; confidence must be numeric from zero through one, and `conflicts` and `missingness` are arrays of non-empty strings when present.

A resolved row must contain exactly one primary source. An `allow`-only or `deny`-only row is not resolved authority. To retain a deny-only observation while authority is missing, mark the row `unresolved: true`, leave `primary` and `allow` empty, and provide a non-empty `reason`; unresolved rows are valid only in a blocked-only contract. Any actionable external stage makes unresolved authority a hard error.

Authority paths are pattern scopes, not independent labels. If two resolved rows overlap hierarchically, for example `appearance` or `appearance.*` with `appearance.material`, their `primary` sets and `allow` sets must be identical. Different source sets on overlapping scopes are ambiguous and invalid; narrow the broad row, align the sources, or split the contract into non-overlapping attributes. When a reference is primary or allowed, its permission must allow the attribute and must not deny it. When authority denies a reference, its permission must not allow that attribute and must contain a matching deny. A permission allow without a corresponding authority assignment is invalid. A reference whose permission role remains `unknown` cannot appear in any resolved `primary` or `allow` set, whether or not a stage uploads it.

### `reference_permissions`

Required array with exactly one object per reference; it may be empty only when no reference asset exists. Each object contains:

- `asset_id`;
- `role_state`: `known`, `inferred`, `chosen`, or `unknown`;
- `role_evidence`: non-empty visual evidence or user-decision reason;
- `allow_attributes` and non-empty `deny_attributes`;
- `allow_entities` and `deny_entities`.

These seven keys are the complete permission object surface.

`deny_attributes` is the machine form of the source-specific must-not-inherit list and must cover every protected structure path. Unlimited scope is detected by canonical root semantics: `*`, `all.*`, `everything.*`, `any.*`, `unrestricted.*`, `style.*`, `content.*`, and equivalent generic roots are invalid. Wildcards are accepted only under the recognized bounded families `appearance`, `construction`, `geometry`, `graphics`, and `identity`; an unrecognized wildcard root is not treated as safely bounded. A family such as `appearance.*` is allowed only when a matching authority row bounds it and no protected scope is included. An `unknown` reference may remain in the inventory but cannot receive resolved authority or be uploaded. Every permission must deny every removed entity; allowing and denying the same attribute family or entity is invalid.

### `stages`

Required non-empty array. Each object contains:

- `id`: unique non-empty stage ID;
- `kind`: `pixel`, `local`, `isomorphic`, `structure`, `realism`, `composite`, or `blocked`;
- `inputs`: non-empty ordered array of unique, existing source IDs.

The only additional stage keys are conditional: `target_reuse` on `realism`, `base_stage_id` on `composite`, and `reason` on `blocked`. A `target_reuse` object contains exactly `justification`, `allowed_attributes`, and `deny_protected_structure`. No stage field is callable; `inputs` is a user-performed manual upload list, not a tool invocation.

These rules describe the user's manual external action plan. They do not authorize this Skill to upload, submit, generate, edit, poll, or download anything.

Stage rules:

- `pixel` requires the target as `inputs[0]` and permits only the target plus optional `mask`; references, structure masters, and exact assets are semantic inputs and are invalid here.
- `local` requires the target as `inputs[0]` and may additionally use bounded references and an optional mask.
- `isomorphic` requires the target as `inputs[0]` and may additionally use bounded references and an optional mask.
- `structure` requires the target as `inputs[0]` and permits only the target plus an optional mask. References, structure masters, and exact assets are incompatible semantic inputs.
- `realism` requires exactly one structure master, that asset must have `approved: true`, and it must be the first input. Later inputs may be bounded references, an optional mask, or the original target under the reuse exception; exact assets do not belong in this stage.
- `composite` is the compatible manual external stage for `exact_asset` inputs and must include at least one. It must also have a substantive base: either a target or structure-master input, or a non-empty `base_stage_id` naming an earlier actionable external stage. A missing, forward, self, blocked, or unknown stage reference is invalid.
- Any original target entering `realism`, regardless of contamination risk, requires `target_reuse` with a non-empty `justification`, at least one concrete non-structural `allowed_attributes` value, and `deny_protected_structure: true`. Wildcards and generic roots such as `style.*`, `everything.*`, or `content.*` are not scoped justification.
- `blocked` requires the target, a non-empty `reason`, and a blocked or bounded-proxy status.

The stage set is closed by status. A blocked status may contain only `blocked` stages and no actionable stage. A blocked stage cannot coexist with `realism` or any other actionable kind. `structure_master_candidate` may contain only `structure` stages; `realism` and `composite` require a downstream candidate status after an external result is imported. A fresh structure-only plan uses `prompt_package_ready`; an imported structure result uses `structure_master_candidate`; a failed imported result with a directional retry package may use `qa_failed_directional_retry_ready`. A structure-only plan cannot use `candidate_unapproved`. Duplicate stage IDs, duplicate stage inputs, unknown inputs, and asset roles incompatible with a stage kind are hard errors.

Stage requirements are not satisfied by authority that exists only on paper. For every attribute required by an actionable external stage, at least one source in that stage's listed `inputs` must appear in the covering resolved authority row's `primary` or `allow` set. A master, target, or reference absent from the manual upload list cannot supply its authority.

### `truth_sensitive`

Required array; it may be empty. Each row contains:

- `attribute`;
- `required_exact`: boolean;
- `evidence_ids`: source IDs.

Those three keys are the complete truth-sensitive row surface.

Every required exact attribute must have an existing evidence asset whose declared `exact_attributes` scope covers the same attribute. It must also have a covering resolved authority row, and that row's sole primary must be one of the valid exact-evidence assets. Placing evidence only in `allow`, or using a non-evidence primary, is invalid. The primary exact-evidence asset itself must appear in a planned external stage compatible with its asset role; using a secondary evidence asset while leaving the authority primary unused is invalid. In particular, an `exact_asset` primary must enter a substantive `composite` stage. Putting exact brand artwork into a `structure` stage neither authorizes that stage input nor counts as using the evidence.

### `status`

Required string enum. The only validator-safe values are:

- `prompt_package_ready`;
- `blocked_missing_evidence`;
- `bounded_proxy_only`;
- `structure_master_candidate`;
- `candidate_unapproved`;
- `qa_failed_directional_retry_ready`.

Values such as `LOCKED`, `approved`, `final`, `exact`, or `bug-free` are outside this validator's proof boundary and are invalid. A structure master's external approval is represented narrowly by that asset's boolean `approved` field, not by promoting the overall contract status.

Status also constrains delivery and the stage set:

- every fresh text package uses `prompt_package_ready`, `delivery_state: prompt_plan`, and an empty `external_result_provenance` array;
- `blocked_missing_evidence` and `bounded_proxy_only` require blocked-only prompt plans;
- `structure_master_candidate`, `candidate_unapproved`, and `qa_failed_directional_retry_ready` require `delivery_state: imported_external_candidate`, complete bound provenance, and an unapproved imported result asset of the status-compatible kind;
- `structure_master_candidate` requires structure-only stages;
- `candidate_unapproved` cannot represent a structure-only plan;
- no non-blocked status may contain a `blocked` stage, and unresolved authority is valid only in blocked-only states.

## 7. Validator Meaning

Run:

```powershell
py -3 -X utf8 scripts/validate_reconstruction_contract.py contract.json --pretty
```

The validator returns JSON with `errors`, `warnings`, `normalized_exceptions`, and `summary`. Exit code `0` means no hard consistency error, `1` means a parsed contract failed one or more invariants, and `2` means the input could not be read or parsed as UTF-8 JSON. Duplicate object keys at any depth also return exit code `2` with `E_DUPLICATE_JSON_KEY`. Passing does not prove that images or provenance are truthful, visually good, or human-approved. It never authorizes a tool call or external-platform operation.
