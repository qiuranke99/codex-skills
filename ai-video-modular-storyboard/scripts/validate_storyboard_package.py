#!/usr/bin/env python3
"""Validate an AI Video Modular Storyboard package using only stdlib."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SUITE_ROOT = Path(__file__).resolve().parents[2]
SHOT_SCRIPTS = SUITE_ROOT / "ai-video-shot-script-director" / "scripts"
LOOK_SCRIPTS = SUITE_ROOT / "ai-video-global-look-lock" / "scripts"
for helper_dir in (SHOT_SCRIPTS, LOOK_SCRIPTS):
    if str(helper_dir) not in sys.path:
        sys.path.insert(0, str(helper_dir))
from validate_global_look import validate_look, verify_declared_file_hashes as verify_look_files  # type: ignore  # noqa: E402
from validate_manifest_update_receipt import validate_receipt  # type: ignore  # noqa: E402
from validate_project_canon_manifest import validate_manifest as validate_project_canon, verify_artifact_files as verify_project_canon_files  # type: ignore  # noqa: E402
from validate_shot_contract import validate_contract as validate_shot_contract, verify_declared_file_hashes as verify_shot_files  # type: ignore  # noqa: E402

OWNER = "ai-video-modular-storyboard"
CONTRACT_VERSION = "ai-video-artifact-v1"
HASH_STATUSES = {"assistant_validated", "user_approved", "stale", "blocked"}
ALLOWED_STATUSES = {"draft", "assistant_validated", "user_approved", "stale", "blocked"}
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
ENVELOPE_FIELDS = {"contract_version", "artifact_id", "owner_skill", "version", "sha256", "approval_status", "dependencies", "affected_shot_uids", "stale_reason"}
ROOT_FIELDS = ENVELOPE_FIELDS | {"schema_version", "project_id", "package_status", "storyboard_stage", "script_shot_count", "shot_contract", "global_look", "frames", "review_board", "transactions", "downstream_invalidations"}
EXTERNAL_FIELDS = {"artifact_id", "owner_skill", "version", "sha256", "approval_status"}
FRAME_FIELDS = ENVELOPE_FIELDS | {"shot_uid", "display_order", "target_duration_seconds", "stage", "file_path", "file_sha256", "generation_prompt_path", "generation_prompt_file_sha256", "global_directing_prompt_full", "global_look_artifact_id", "global_look_prompt_full", "look_state_id", "look_state_prompt_full", "shot_look_delta_prompt_full", "look_reference_asset_ids", "actual_pixel_dimensions", "generation_mode", "independently_generated", "derived_from_multipanel", "is_model_input_eligible", "content_cleanliness"}
BOARD_FIELDS = ENVELOPE_FIELDS | {"board_type", "is_model_input", "deterministic", "file_path", "file_sha256", "valid_cell_count", "cell_shot_uids", "source_frame_hashes", "layout"}
TX_ALLOWED_FIELDS = ENVELOPE_FIELDS | {"transaction_id", "mode", "status", "requested_shot_uids", "atomic_commit", "route_to_shot_contract", "base_manifest_path", "base_manifest_file_sha256", "base_manifest_ref", "old_frames", "new_frames", "unaffected_hash_assertions", "downstream_invalidations"}
CONTENT_CLEANLINESS_FIELDS = {
    "no_shot_number_overlay", "no_duration_overlay", "no_editorial_caption_overlay",
    "no_arrow_overlay", "no_grid", "no_ui", "no_watermark", "no_layout_chrome",
    "intrinsic_text_policy", "intrinsic_text_source_refs",
}
ANNOTATION_CLEAN_FIELDS = CONTENT_CLEANLINESS_FIELDS - {"intrinsic_text_policy", "intrinsic_text_source_refs"}
INTRINSIC_TEXT_CATEGORY_TOKENS = {
    "product", "packaging", "package", "label", "scene", "environment",
    "location", "signage", "sign", "storefront",
}


def canonical_artifact_hash(value: dict[str, Any]) -> str:
    payload = copy.deepcopy(value)
    payload.pop("sha256", None)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def is_semver(value: Any) -> bool:
    return isinstance(value, str) and SEMVER_RE.fullmatch(value) is not None


def semver_tuple(value: Any) -> tuple[int, int, int] | None:
    if not is_semver(value):
        return None
    return tuple(int(part) for part in value.split("."))


def safe_file(root: Path, rel: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(rel, str) or not rel:
        errors.append(f"{label}: missing file_path")
        return None
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{label}: file_path escapes package root: {rel}")
        return None
    if not candidate.is_file():
        errors.append(f"{label}: file missing: {rel}")
        return None
    return candidate


def validate_dependency(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label}: dependency must be an object")
        return
    if set(value) != {"artifact_id", "owner_skill", "version", "sha256"}:
        errors.append(f"{label}: dependency must contain exactly artifact_id/owner_skill/version/sha256")
    if not isinstance(value.get("artifact_id"), str) or not value["artifact_id"]:
        errors.append(f"{label}: dependency artifact_id missing")
    if not isinstance(value.get("owner_skill"), str) or not value["owner_skill"]:
        errors.append(f"{label}: dependency owner_skill missing")
    if not is_semver(value.get("version")):
        errors.append(f"{label}: dependency version must be SemVer")
    if not is_sha(value.get("sha256")):
        errors.append(f"{label}: dependency sha256 invalid")


def validate_envelope(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label}: artifact must be an object")
        return
    required = ENVELOPE_FIELDS
    missing = sorted(required - value.keys())
    if missing:
        errors.append(f"{label}: missing envelope fields {missing}")
        return
    if value["contract_version"] != CONTRACT_VERSION:
        errors.append(f"{label}: contract_version must be {CONTRACT_VERSION}")
    if value["owner_skill"] != OWNER:
        errors.append(f"{label}: owner_skill must be {OWNER}")
    if not isinstance(value["artifact_id"], str) or not value["artifact_id"]:
        errors.append(f"{label}: artifact_id missing")
    if not is_semver(value["version"]):
        errors.append(f"{label}: version must be SemVer")
    status = value["approval_status"]
    if status not in ALLOWED_STATUSES:
        errors.append(f"{label}: invalid approval_status {status!r}")
    dependencies = value["dependencies"]
    if not isinstance(dependencies, list):
        errors.append(f"{label}: dependencies must be a list")
    else:
        for index, dep in enumerate(dependencies):
            validate_dependency(dep, f"{label}.dependencies[{index}]", errors)
    scope = value["affected_shot_uids"]
    if not isinstance(scope, list) or not all(isinstance(item, str) and item for item in scope):
        errors.append(f"{label}: affected_shot_uids must be a string list")
    elif len(scope) != len(set(scope)):
        errors.append(f"{label}: affected_shot_uids must be unique")
    if status == "stale" and (not isinstance(value["stale_reason"], str) or not value["stale_reason"].strip()):
        errors.append(f"{label}: stale artifact requires non-empty stale_reason")
    if status != "stale" and value["stale_reason"] is not None:
        errors.append(f"{label}: non-stale artifact must have stale_reason null")
    if status in HASH_STATUSES:
        try:
            expected = canonical_artifact_hash(value)
        except (TypeError, ValueError) as exc:
            errors.append(f"{label}: non-canonical JSON value: {exc}")
        else:
            if value["sha256"] != expected:
                errors.append(f"{label}: canonical artifact sha256 mismatch")
    elif value["sha256"] is not None:
        errors.append(f"{label}: draft sha256 must be null")


def validate_external_authority(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label}: external authority must be object")
        return
    if set(value) != EXTERNAL_FIELDS:
        errors.append(f"{label}: external authority must contain exact reference fields")
    if value.get("approval_status") not in {"assistant_validated", "user_approved"}:
        errors.append(f"{label}: external authority must be validated or user-approved")
    if not isinstance(value.get("artifact_id"), str) or not value["artifact_id"]:
        errors.append(f"{label}: artifact_id missing")
    if not isinstance(value.get("owner_skill"), str) or not value["owner_skill"]:
        errors.append(f"{label}: owner_skill missing")
    if not is_semver(value.get("version")):
        errors.append(f"{label}: version must be SemVer")
    if not is_sha(value.get("sha256")):
        errors.append(f"{label}: sha256 invalid")


def dependency_signature(value: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    return tuple(value.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))


def authority_dependency(value: dict[str, Any]) -> dict[str, Any]:
    return {field: value.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256")}


def require_dependencies(artifact: dict[str, Any], required: list[dict[str, Any]], label: str, errors: list[str]) -> None:
    actual = {dependency_signature(item) for item in artifact.get("dependencies", []) if isinstance(item, dict)}
    expected = {dependency_signature(item) for item in required}
    if expected != actual:
        errors.append(f"{label}: dependencies must exactly equal required artifact locks")


def validate_intrinsic_text_controls(
    cleanliness: Any,
    shot_uid: str,
    prompt_text: str,
    canon_manifest: dict[str, Any] | None,
    label: str,
    errors: list[str],
) -> list[dict[str, Any]]:
    """Validate annotation cleanliness separately from source-authorized intrinsic text."""
    if not isinstance(cleanliness, dict) or set(cleanliness) != CONTENT_CLEANLINESS_FIELDS:
        errors.append(f"{label}: content_cleanliness must contain exact annotation and intrinsic-text fields")
        return []
    if any(cleanliness.get(field) is not True for field in ANNOTATION_CLEAN_FIELDS):
        errors.append(f"{label}: storyboard overlay annotation assertions failed")
    policy = cleanliness.get("intrinsic_text_policy")
    refs = cleanliness.get("intrinsic_text_source_refs")
    if policy not in {"none_visible", "source_authorized_only"}:
        errors.append(f"{label}: invalid intrinsic_text_policy")
    if not isinstance(refs, list):
        errors.append(f"{label}: intrinsic_text_source_refs must be an array")
        return []
    for index, ref in enumerate(refs):
        validate_dependency(ref, f"{label}.intrinsic_text_source_refs[{index}]", errors)
    signatures = [dependency_signature(ref) for ref in refs if isinstance(ref, dict)]
    if len(signatures) != len(set(signatures)):
        errors.append(f"{label}: intrinsic_text_source_refs must be unique")
    if policy == "none_visible":
        if refs:
            errors.append(f"{label}: none_visible requires empty intrinsic_text_source_refs")
        return []
    if not refs:
        errors.append(f"{label}: source_authorized_only requires at least one intrinsic text source")
        return []
    if canon_manifest is None:
        errors.append(f"{label}: source-authorized intrinsic text requires actual Project Canon")
        return [ref for ref in refs if isinstance(ref, dict)]
    active = canon_manifest.get("active_artifacts")
    active = active if isinstance(active, list) else []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        entry = next(
            (
                item for item in active if isinstance(item, dict)
                and all(item.get(field) == ref.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))
            ),
            None,
        )
        if (
            entry is None
            or entry.get("eligible_for_downstream") is not True
            or entry.get("approval_status") not in {"assistant_validated", "user_approved"}
            or entry.get("stale_reason") is not None
        ):
            errors.append(f"{label}: intrinsic text source is not an exact downstream-eligible Project Canon artifact: {ref.get('artifact_id')}")
            continue
        category_tokens = set(
            token for token in re.split(
                r"[^a-z0-9]+",
                f"{entry.get('artifact_type', '')} {entry.get('artifact_slot', '')}".lower(),
            ) if token
        )
        if not category_tokens.intersection(INTRINSIC_TEXT_CATEGORY_TOKENS):
            errors.append(f"{label}: intrinsic text source is not a product/packaging/label/scene authority: {ref.get('artifact_id')}")
        scope = entry.get("affected_shot_uids")
        if not isinstance(scope, list) or shot_uid not in scope:
            errors.append(f"{label}: intrinsic text source does not cover shot {shot_uid}: {ref.get('artifact_id')}")
        if ref.get("artifact_id") not in prompt_text:
            errors.append(f"{label}: intrinsic text source artifact ID missing from generation prompt: {ref.get('artifact_id')}")
        if not all(isinstance(entry.get(field), str) and entry.get(field) for field in ("locator", "file_sha256", "artifact_record_locator", "artifact_record_file_sha256")):
            errors.append(f"{label}: intrinsic text source lacks complete primary/record byte locks: {ref.get('artifact_id')}")
    return [ref for ref in refs if isinstance(ref, dict)]


def load_active_authority(
    canon_manifest: dict[str, Any], project_root: Path | None, reference: Any, label: str, errors: list[str]
) -> dict[str, Any] | None:
    if not isinstance(reference, dict):
        return None
    active = canon_manifest.get("active_artifacts")
    if not isinstance(active, list):
        errors.append(f"{label}: Project Canon active_artifacts missing")
        return None
    entry = next((item for item in active if isinstance(item, dict) and all(item.get(field) == reference.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))), None)
    if entry is None:
        errors.append(f"{label}: reference is not the exact active Project Canon authority")
        return None
    if entry.get("approval_status") not in {"assistant_validated", "user_approved"} or entry.get("eligible_for_downstream") is not True or entry.get("stale_reason") is not None:
        errors.append(f"{label}: active Project Canon authority is not downstream-eligible")
    if project_root is None:
        errors.append(f"{label}: project_root is required to verify authority bytes")
        return None
    locator = entry.get("locator")
    file_hash = entry.get("file_sha256")
    if not isinstance(locator, str) or not locator or not is_sha(file_hash):
        errors.append(f"{label}: Canon authority needs locator and file_sha256")
        return None
    candidate = (project_root / locator).resolve()
    try:
        candidate.relative_to(project_root.resolve())
    except ValueError:
        errors.append(f"{label}: Canon authority locator escapes project root")
        return None
    if not candidate.is_file() or sha256_file(candidate) != file_hash:
        errors.append(f"{label}: Canon authority file missing or byte hash mismatch")
        return None
    try:
        value = json.loads(candidate.read_text(encoding="utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"{label}: authority artifact unreadable: {exc}")
        return None
    if not isinstance(value, dict) or any(value.get(field) != reference.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256")):
        errors.append(f"{label}: authority artifact envelope differs from Canon/reference lock")
        return None
    if reference.get("owner_skill") == "ai-video-shot-script-director":
        semantic_errors = [*validate_shot_contract(value), *verify_shot_files(value, project_root)]
    elif reference.get("owner_skill") == "ai-video-global-look-lock":
        semantic_errors = [*validate_look(value), *verify_look_files(value, project_root)]
    else:
        semantic_errors = ["unsupported storyboard authority owner"]
    if semantic_errors:
        errors.extend(f"{label}: invalid authority artifact: {item}" for item in semantic_errors)
        return None
    if reference.get("owner_skill") == "ai-video-global-look-lock":
        active_entries = canon_manifest.get("active_artifacts", [])
        for look_ref in value.get("look_reference_set", []):
            if not isinstance(look_ref, dict) or not isinstance(look_ref.get("artifact"), dict):
                continue
            ref_artifact = look_ref["artifact"]
            registered = next(
                (
                    item for item in active_entries if isinstance(item, dict)
                    and all(item.get(field) == ref_artifact.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))
                    and item.get("locator") == look_ref.get("locator")
                    and item.get("file_sha256") == look_ref.get("file_sha256")
                ),
                None,
            )
            if registered is None or registered.get("eligible_for_downstream") is not True:
                errors.append(f"{label}: look reference artifact is not an exact downstream-eligible Project Canon entry: {ref_artifact.get('artifact_id')}")
        if errors:
            return None
    return value


def validate_transaction(
    root: Path,
    tx: Any,
    frames_by_uid: dict[str, dict[str, Any]],
    all_uids: set[str],
    current_manifest: dict[str, Any],
    canon_manifest: dict[str, Any] | None,
    label: str,
    errors: list[str],
) -> None:
    validate_envelope(tx, label, errors)
    if not isinstance(tx, dict):
        return
    if not set(tx).issubset(TX_ALLOWED_FIELDS):
        errors.append(f"{label}: unexpected transaction fields")
    required = {"transaction_id", "mode", "status", "requested_shot_uids", "atomic_commit", "route_to_shot_contract"}
    missing = sorted(required - tx.keys())
    if missing:
        errors.append(f"{label}: missing transaction fields {missing}")
        return
    requested = tx["requested_shot_uids"]
    if not isinstance(requested, list) or not requested or not all(isinstance(item, str) and item for item in requested):
        errors.append(f"{label}: requested_shot_uids must be non-empty strings")
        return
    if len(requested) != len(set(requested)):
        errors.append(f"{label}: requested_shot_uids must be non-empty and unique")
        return
    if not set(requested) <= all_uids:
        errors.append(f"{label}: requested shot not present in current Shot Contract")
    if set(tx.get("affected_shot_uids", [])) != set(requested):
        errors.append(f"{label}: affected_shot_uids must equal requested_shot_uids")

    if tx["mode"] == "reorder_request":
        if tx["status"] != "routed_upstream" or tx["atomic_commit"] is not False or tx["route_to_shot_contract"] is not True:
            errors.append(f"{label}: reorder must leave board unchanged and route upstream")
        return
    if tx["mode"] != "replace_frames":
        errors.append(f"{label}: invalid mode {tx['mode']!r}")
        return
    if tx["route_to_shot_contract"] is not False:
        errors.append(f"{label}: replacement must not route to Shot Contract")
    if tx["status"] != "applied":
        return
    if tx["atomic_commit"] is not True:
        errors.append(f"{label}: applied replacement must be atomic")
    old_frames = tx.get("old_frames")
    new_frames = tx.get("new_frames")
    if not isinstance(old_frames, list) or not isinstance(new_frames, list):
        errors.append(f"{label}: applied replacement requires old_frames and new_frames")
        return
    base_path = safe_file(root, tx.get("base_manifest_path"), f"{label}.base_manifest", errors)
    base_manifest: dict[str, Any] = {}
    if base_path is not None:
        if not is_sha(tx.get("base_manifest_file_sha256")) or sha256_file(base_path) != tx.get("base_manifest_file_sha256"):
            errors.append(f"{label}: base manifest file hash mismatch")
        try:
            loaded_base = json.loads(base_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{label}: base manifest unreadable: {exc}")
        else:
            if isinstance(loaded_base, dict):
                base_manifest = loaded_base
                validate_envelope(base_manifest, f"{label}.base_manifest", errors)
                if set(base_manifest) != ROOT_FIELDS:
                    errors.append(f"{label}: pre-transaction manifest must contain exact storyboard root fields")
            else:
                errors.append(f"{label}: base manifest root must be object")
    base_ref = tx.get("base_manifest_ref")
    if not isinstance(base_ref, dict) or set(base_ref) != {"artifact_id", "owner_skill", "version", "sha256"}:
        errors.append(f"{label}: exact base_manifest_ref required")
        base_ref = {}
    expected_base_ref = {field: base_manifest.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256")}
    if base_manifest and base_ref != expected_base_ref:
        errors.append(f"{label}: base_manifest_ref does not match immutable pre-transaction manifest")
    if base_manifest:
        base_manifest_version = semver_tuple(base_manifest.get("version"))
        current_manifest_version = semver_tuple(current_manifest.get("version"))
        if base_manifest_version is None or current_manifest_version is None or current_manifest_version <= base_manifest_version:
            errors.append(f"{label}: current Storyboard manifest version must exceed pre-transaction manifest version")
        if base_manifest.get("shot_contract") != current_manifest.get("shot_contract") or base_manifest.get("global_look") != current_manifest.get("global_look"):
            errors.append(f"{label}: pre-transaction manifest must retain the exact current upstream authority locks")
        if base_manifest.get("storyboard_stage") != current_manifest.get("storyboard_stage") or base_manifest.get("script_shot_count") != current_manifest.get("script_shot_count"):
            errors.append(f"{label}: pre-transaction manifest stage/cardinality differs from current manifest")
        require_dependencies(base_manifest, current_manifest.get("dependencies", []), f"{label}.base_manifest", errors)
    dependency_refs = {dependency_signature(item) for item in tx.get("dependencies", []) if isinstance(item, dict)}
    if base_ref and dependency_signature(base_ref) not in dependency_refs:
        errors.append(f"{label}: transaction must depend on exact pre-transaction manifest")
    if canon_manifest is None:
        errors.append(f"{label}: applied replacement requires actual Project Canon manifest for immutable anchoring")
    else:
        active = canon_manifest.get("active_artifacts") if isinstance(canon_manifest, dict) else None
        superseded = canon_manifest.get("superseded_artifacts") if isinstance(canon_manifest, dict) else None
        active_match = next((item for item in active if isinstance(item, dict) and all(item.get(field) == current_manifest.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))), None) if isinstance(active, list) else None
        base_match = next((item for item in superseded if isinstance(item, dict) and all(item.get(field) == base_ref.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))), None) if isinstance(superseded, list) else None
        if active_match is None:
            errors.append(f"{label}: current storyboard manifest is not the active Project Canon entry")
        if base_match is None or base_match.get("superseded_by_artifact_id") != current_manifest.get("artifact_id"):
            errors.append(f"{label}: pre-transaction manifest is not the matching superseded Project Canon entry")
    base_frames = {
        item.get("shot_uid"): item for item in base_manifest.get("frames", []) if isinstance(item, dict)
    }
    if set(base_frames) != all_uids:
        errors.append(f"{label}: pre-transaction manifest must cover every current Shot UID")
    for uid, base_frame in base_frames.items():
        frame_label = f"{label}.base_manifest.frames[{uid}]"
        validate_envelope(base_frame, frame_label, errors)
        if set(base_frame) != FRAME_FIELDS:
            errors.append(f"{frame_label}: frame must contain exact fields")
        if base_frame.get("shot_uid") != uid or base_frame.get("affected_shot_uids") != [uid]:
            errors.append(f"{frame_label}: Shot UID/envelope scope mismatch")
        current_frame = frames_by_uid.get(uid, {})
        require_dependencies(base_frame, current_frame.get("dependencies", []), frame_label, errors)
        base_frame_path = safe_file(root, base_frame.get("file_path"), frame_label, errors)
        if base_frame_path is not None and sha256_file(base_frame_path) != base_frame.get("file_sha256"):
            errors.append(f"{frame_label}: file_sha256 mismatch")
        base_prompt_path = safe_file(root, base_frame.get("generation_prompt_path"), f"{frame_label}.generation_prompt", errors)
        if base_prompt_path is not None and sha256_file(base_prompt_path) != base_frame.get("generation_prompt_file_sha256"):
            errors.append(f"{frame_label}: generation prompt file hash mismatch")
    base_board = base_manifest.get("review_board")
    if not isinstance(base_board, dict):
        errors.append(f"{label}: pre-transaction manifest requires review_board")
    else:
        validate_envelope(base_board, f"{label}.base_manifest.review_board", errors)
        if set(base_board) != BOARD_FIELDS:
            errors.append(f"{label}: pre-transaction review_board must contain exact fields")
        expected_base_hashes = {uid: frame.get("file_sha256") for uid, frame in base_frames.items()}
        if base_board.get("cell_shot_uids") != list(base_frames) or base_board.get("source_frame_hashes") != expected_base_hashes:
            errors.append(f"{label}: pre-transaction review_board does not bind exact base frames")
        required_board_deps = [
            {field: frame.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256")}
            for frame in base_frames.values()
        ]
        require_dependencies(base_board, required_board_deps, f"{label}.base_manifest.review_board", errors)
        base_board_path = safe_file(root, base_board.get("file_path"), f"{label}.base_manifest.review_board", errors)
        if base_board_path is not None and sha256_file(base_board_path) != base_board.get("file_sha256"):
            errors.append(f"{label}: pre-transaction review_board file hash mismatch")
        current_board = current_manifest.get("review_board")
        if isinstance(current_board, dict) and current_board.get("source_frame_hashes") != base_board.get("source_frame_hashes"):
            base_board_version = semver_tuple(base_board.get("version"))
            current_board_version = semver_tuple(current_board.get("version"))
            if base_board_version is None or current_board_version is None or current_board_version <= base_board_version:
                errors.append(f"{label}: changed review-board sources require current board version to exceed pre-transaction board version")
    old_by_uid = {item.get("shot_uid"): item for item in old_frames if isinstance(item, dict)}
    new_by_uid = {item.get("shot_uid"): item for item in new_frames if isinstance(item, dict)}
    if set(old_by_uid) != set(requested) or set(new_by_uid) != set(requested):
        errors.append(f"{label}: applied transaction must include old/new record for every requested shot")
    for uid in requested:
        old = old_by_uid.get(uid, {})
        new = new_by_uid.get(uid, {})
        current = frames_by_uid.get(uid, {})
        old_version = semver_tuple(old.get("version"))
        new_version = semver_tuple(new.get("version"))
        if old_version is None or new_version is None or new_version <= old_version:
            errors.append(f"{label}: {uid} new version must exceed old version")
        for field in ("artifact_id", "version", "sha256", "file_sha256"):
            if new.get(field) != current.get(field):
                errors.append(f"{label}: {uid} current frame does not match committed new {field}")
            if old.get(field) != base_frames.get(uid, {}).get(field):
                errors.append(f"{label}: {uid} old frame does not match pre-transaction manifest {field}")
    expected_unaffected = all_uids - set(requested)
    assertions = tx.get("unaffected_hash_assertions")
    if not isinstance(assertions, dict) or set(assertions) != expected_unaffected:
        errors.append(f"{label}: unaffected hash assertions must cover every non-requested shot")
    else:
        for uid in expected_unaffected:
            base_hash = base_frames.get(uid, {}).get("file_sha256")
            if assertions[uid] != base_hash or frames_by_uid[uid].get("file_sha256") != base_hash:
                errors.append(f"{label}: unaffected shot {uid} hash changed")


def _validate_package(root: Path, canon_manifest: dict[str, Any] | None = None, project_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    manifest_path = root / "00_manifest" / "STORYBOARD_MANIFEST.json"
    if not manifest_path.is_file():
        return ["missing 00_manifest/STORYBOARD_MANIFEST.json"]
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"manifest unreadable: {exc}"]

    if not isinstance(data, dict):
        return ["manifest root must be an object"]
    if set(data) != ROOT_FIELDS:
        errors.append("manifest must contain exact storyboard root fields")
    validate_envelope(data, "manifest", errors)
    if data.get("owner_skill") != OWNER:
        errors.append(f"manifest owner_skill must be {OWNER}")

    if data.get("schema_version") != "ai-video-modular-storyboard.v1":
        errors.append("schema_version must be ai-video-modular-storyboard.v1")
    if data.get("package_status") not in {"draft", "generating", "assistant_validated", "user_approved", "repair_required", "stale", "blocked"}:
        errors.append("invalid package_status")
    stage = data.get("storyboard_stage")
    if stage not in {"structure_draft", "look_applied_final"}:
        errors.append("invalid storyboard_stage")
    count = data.get("script_shot_count")
    if not isinstance(count, int) or count < 1:
        errors.append("script_shot_count must be positive integer")
        count = 0
    validate_external_authority(data.get("shot_contract"), "shot_contract", errors)
    global_look = data.get("global_look")
    if stage == "look_applied_final":
        validate_external_authority(global_look, "global_look", errors)
    elif global_look is not None:
        validate_external_authority(global_look, "global_look", errors)
    authority_dependencies: list[dict[str, Any]] = []
    if isinstance(data.get("shot_contract"), dict):
        authority_dependencies.append(authority_dependency(data["shot_contract"]))
    if stage == "look_applied_final" and isinstance(global_look, dict):
        authority_dependencies.append(authority_dependency(global_look))
    require_dependencies(data, authority_dependencies, "manifest", errors)

    shot_authority: dict[str, Any] | None = None
    look_authority: dict[str, Any] | None = None
    if data.get("package_status") in {"assistant_validated", "user_approved"}:
        if canon_manifest is None:
            errors.append("validated storyboard package requires the actual Project Canon manifest")
        else:
            canon_errors = validate_project_canon(canon_manifest)
            if not canon_errors and project_root is not None:
                canon_errors.extend(verify_project_canon_files(canon_manifest, project_root))
            errors.extend(f"Project Canon invalid: {item}" for item in canon_errors)
            if not canon_errors:
                shot_authority = load_active_authority(canon_manifest, project_root, data.get("shot_contract"), "shot_contract", errors)
                if stage == "look_applied_final":
                    look_authority = load_active_authority(canon_manifest, project_root, global_look, "global_look", errors)

    frames = data.get("frames")
    if not isinstance(frames, list):
        errors.append("frames must be a list")
        frames = []
    if len(frames) != count:
        errors.append(f"cardinality mismatch: script={count}, frames={len(frames)}")
    uids: list[str] = []
    orders: list[Any] = []
    paths: list[Any] = []
    artifact_ids: list[Any] = []
    frames_by_uid: dict[str, dict[str, Any]] = {}
    for index, frame in enumerate(frames):
        label = f"frames[{index}]"
        validate_envelope(frame, label, errors)
        if not isinstance(frame, dict):
            continue
        if set(frame) != FRAME_FIELDS:
            errors.append(f"{label}: frame must contain exact fields")
        uid = frame.get("shot_uid")
        if not isinstance(uid, str) or not uid:
            errors.append(f"{label}: shot_uid missing")
            continue
        uids.append(uid)
        frames_by_uid[uid] = frame
        orders.append(frame.get("display_order"))
        paths.append(frame.get("file_path"))
        artifact_ids.append(frame.get("artifact_id"))
        if frame.get("affected_shot_uids") != [uid]:
            errors.append(f"{label}: affected_shot_uids must be exactly [{uid!r}]")
        if frame.get("stage") != stage:
            errors.append(f"{label}: frame stage must equal package stage")
        if not isinstance(frame.get("target_duration_seconds"), (int, float)) or isinstance(frame.get("target_duration_seconds"), bool) or frame.get("target_duration_seconds", 0) <= 0:
            errors.append(f"{label}: target_duration_seconds must be positive")
        if frame.get("generation_mode") != "independent_full_frame" or frame.get("independently_generated") is not True or frame.get("derived_from_multipanel") is not False:
            errors.append(f"{label}: frame must be independently generated, never derived from multipanel")
        expected_eligibility = stage == "look_applied_final"
        if frame.get("is_model_input_eligible") is not expected_eligibility:
            errors.append(f"{label}: model-input eligibility must be false for structure_draft and true only for look_applied_final")
        cleanliness = frame.get("content_cleanliness")
        file_path = safe_file(root, frame.get("file_path"), label, errors)
        if file_path is not None and sha256_file(file_path) != frame.get("file_sha256"):
            errors.append(f"{label}: file_sha256 mismatch")
        if canon_manifest is not None and project_root is not None and file_path is not None:
            expected_locator = str(file_path.resolve().relative_to(project_root.resolve())) if project_root.resolve() in file_path.resolve().parents else None
            canon_frame_entry = next(
                (
                    item for item in canon_manifest.get("active_artifacts", []) if isinstance(item, dict)
                    and all(item.get(field) == frame.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))
                ),
                None,
            )
            if expected_locator is None or canon_frame_entry is None or canon_frame_entry.get("locator") != expected_locator or canon_frame_entry.get("file_sha256") != frame.get("file_sha256"):
                errors.append(f"{label}: primary frame bytes are not the exact active Project Canon entry")
        prompt_path = safe_file(root, frame.get("generation_prompt_path"), f"{label}.generation_prompt", errors)
        prompt_text = ""
        if prompt_path is not None:
            if sha256_file(prompt_path) != frame.get("generation_prompt_file_sha256"):
                errors.append(f"{label}: generation prompt file hash mismatch")
            prompt_text = prompt_path.read_text(encoding="utf-8", errors="ignore")
        intrinsic_text_refs = validate_intrinsic_text_controls(
            cleanliness, uid, prompt_text, canon_manifest, label, errors
        )
        directing = frame.get("global_directing_prompt_full")
        if not isinstance(directing, str) or len(directing.strip()) < 40 or directing not in prompt_text:
            errors.append(f"{label}: exact Global Directing block missing from generation prompt")
        if stage == "structure_draft":
            for field in ("global_look_artifact_id", "global_look_prompt_full", "look_state_id", "look_state_prompt_full", "shot_look_delta_prompt_full"):
                if frame.get(field) is not None:
                    errors.append(f"{label}: structure_draft must not claim {field}")
            if frame.get("look_reference_asset_ids") != []:
                errors.append(f"{label}: structure_draft look_reference_asset_ids must be empty")
        else:
            if not isinstance(global_look, dict) or frame.get("global_look_artifact_id") != global_look.get("artifact_id"):
                errors.append(f"{label}: Global Look artifact binding mismatch")
            for field, minimum in (("global_look_prompt_full", 200), ("look_state_prompt_full", 80), ("shot_look_delta_prompt_full", 1)):
                value = frame.get(field)
                if not isinstance(value, str) or len(value.strip()) < minimum or value not in prompt_text:
                    errors.append(f"{label}: exact {field} missing from generation prompt")
            if not isinstance(frame.get("look_state_id"), str) or not frame["look_state_id"] or frame["look_state_id"] not in prompt_text:
                errors.append(f"{label}: exact look_state_id missing from generation prompt")
            references = frame.get("look_reference_asset_ids")
            if not isinstance(references, list) or not references or not all(isinstance(item, str) and item and item in prompt_text for item in references):
                errors.append(f"{label}: resolved Look Reference artifact IDs must be non-empty and appear in generation prompt")
        dims = frame.get("actual_pixel_dimensions")
        if not isinstance(dims, dict) or not all(isinstance(dims.get(key), int) and not isinstance(dims.get(key), bool) and dims[key] > 0 for key in ("width", "height")):
            errors.append(f"{label}: invalid actual_pixel_dimensions")
        required_frame_dependencies = copy.deepcopy(authority_dependencies)
        if stage == "look_applied_final" and look_authority is not None:
            assignment_for_dependencies = next((item for item in look_authority.get("shot_look_assignments", []) if isinstance(item, dict) and item.get("shot_uid") == uid), None)
            states_for_dependencies = {item.get("state_id"): item for item in look_authority.get("look_states", []) if isinstance(item, dict)}
            reference_by_internal_id = {
                item.get("reference_id"): item.get("artifact")
                for item in look_authority.get("look_reference_set", []) if isinstance(item, dict) and isinstance(item.get("artifact"), dict)
            }
            if isinstance(assignment_for_dependencies, dict):
                state_for_dependencies = states_for_dependencies.get(assignment_for_dependencies.get("state_id"), {})
                for ref_id in state_for_dependencies.get("reference_ids", []):
                    ref_artifact = reference_by_internal_id.get(ref_id)
                    if isinstance(ref_artifact, dict):
                        required_frame_dependencies.append({field: ref_artifact.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256")})
        required_frame_dependencies.extend(copy.deepcopy(intrinsic_text_refs))
        require_dependencies(frame, required_frame_dependencies, label, errors)

        if shot_authority is not None:
            source_shots = shot_authority.get("shots") if isinstance(shot_authority.get("shots"), list) else []
            source_shot = next((item for item in source_shots if isinstance(item, dict) and item.get("shot_uid") == uid), None)
            if source_shot is None:
                errors.append(f"{label}: Shot UID absent from authoritative Shot Contract")
            else:
                if source_shot.get("display_no") != frame.get("display_order") or source_shot.get("target_duration_seconds") != frame.get("target_duration_seconds"):
                    errors.append(f"{label}: order/duration differs from authoritative Shot Contract")
            if frame.get("global_directing_prompt_full") != shot_authority.get("global_directing_prompt_full"):
                errors.append(f"{label}: Global Directing block differs from authoritative Shot Contract")
        if stage == "look_applied_final" and look_authority is not None:
            assignment = next((item for item in look_authority.get("shot_look_assignments", []) if isinstance(item, dict) and item.get("shot_uid") == uid), None)
            states = {item.get("state_id"): item for item in look_authority.get("look_states", []) if isinstance(item, dict)}
            if not isinstance(assignment, dict):
                errors.append(f"{label}: no authoritative Global Look assignment for shot")
            else:
                state = states.get(assignment.get("state_id"), {})
                reference_artifact_by_id = {
                    item.get("reference_id"): item.get("artifact", {}).get("artifact_id")
                    for item in look_authority.get("look_reference_set", []) if isinstance(item, dict) and isinstance(item.get("artifact"), dict)
                }
                exact_values = {
                    "global_look_artifact_id": look_authority.get("artifact_id"),
                    "global_look_prompt_full": look_authority.get("global_look_prompt_full"),
                    "look_state_id": assignment.get("state_id"),
                    "look_state_prompt_full": state.get("state_prompt_full"),
                    "shot_look_delta_prompt_full": assignment.get("shot_look_delta_prompt_full"),
                    "look_reference_asset_ids": [reference_artifact_by_id.get(ref_id) for ref_id in state.get("reference_ids", [])],
                }
                for field, expected in exact_values.items():
                    if frame.get(field) != expected:
                        errors.append(f"{label}: {field} differs from authoritative Global Look")

    if len(uids) != len(set(uids)):
        errors.append("shot_uid values must be unique")
    if len(paths) != len(set(paths)):
        errors.append("current frame file paths must be unique")
    if len(artifact_ids) != len(set(artifact_ids)):
        errors.append("current frame artifact_id values must be unique")
    if orders != list(range(1, count + 1)):
        errors.append("display_order must be contiguous and frames must follow Shot Contract order")
    if shot_authority is not None:
        authoritative_uids = [item.get("shot_uid") for item in shot_authority.get("shots", []) if isinstance(item, dict)]
        if uids != authoritative_uids or count != len(authoritative_uids):
            errors.append("N/order must exactly equal the authoritative Shot Contract")
    if canon_manifest is not None and canon_manifest.get("canonical_shot_uids") != uids:
        errors.append("frame order must exactly equal Project Canon canonical_shot_uids")
    if data.get("affected_shot_uids") != uids:
        errors.append("manifest affected_shot_uids must equal current Shot UID order")

    board = data.get("review_board")
    if data.get("package_status") in {"assistant_validated", "user_approved"} and not isinstance(board, dict):
        errors.append("validated package requires review_board")
    if isinstance(board, dict):
        validate_envelope(board, "review_board", errors)
        if set(board) != BOARD_FIELDS:
            errors.append("review_board must contain exact fields")
        if board.get("board_type") != "deterministic_human_review_composite" or board.get("deterministic") is not True:
            errors.append("review_board must be deterministic human composite")
        if board.get("is_model_input") is not False:
            errors.append("review_board must never be a model input")
        if board.get("valid_cell_count") != count:
            errors.append("review_board valid_cell_count must equal script_shot_count")
        if board.get("cell_shot_uids") != uids:
            errors.append("review_board cell_shot_uids must exactly follow frame order")
        expected_hashes = {uid: frames_by_uid[uid].get("file_sha256") for uid in uids}
        if board.get("source_frame_hashes") != expected_hashes:
            errors.append("review_board source_frame_hashes do not match current frames")
        layout = board.get("layout")
        if not isinstance(layout, dict):
            errors.append("review_board layout missing")
        else:
            columns = layout.get("columns")
            rows = layout.get("rows")
            if not isinstance(columns, int) or columns < 1 or not isinstance(rows, int) or rows < 1 or columns * rows < count:
                errors.append("review_board layout cannot contain all valid cells")
            for key in ("cell_width", "image_height", "label_height"):
                if not isinstance(layout.get(key), int) or layout[key] < 1:
                    errors.append(f"review_board layout {key} must be positive integer")
            if not isinstance(layout.get("padding"), int) or layout["padding"] < 0:
                errors.append("review_board layout padding must be nonnegative integer")
        board_path = safe_file(root, board.get("file_path"), "review_board", errors)
        if board_path is not None and sha256_file(board_path) != board.get("file_sha256"):
            errors.append("review_board file_sha256 mismatch")
        if canon_manifest is not None and project_root is not None and board_path is not None:
            expected_board_locator = str(board_path.resolve().relative_to(project_root.resolve())) if project_root.resolve() in board_path.resolve().parents else None
            canon_board_entry = next(
                (
                    item for item in canon_manifest.get("active_artifacts", []) if isinstance(item, dict)
                    and all(item.get(field) == board.get(field) for field in ("artifact_id", "owner_skill", "version", "sha256"))
                ),
                None,
            )
            if expected_board_locator is None or canon_board_entry is None or canon_board_entry.get("locator") != expected_board_locator or canon_board_entry.get("file_sha256") != board.get("file_sha256"):
                errors.append("review_board primary bytes are not the exact active Project Canon entry")
        board_dependencies = [
            {
                "artifact_id": frame["artifact_id"],
                "owner_skill": OWNER,
                "version": frame["version"],
                "sha256": frame["sha256"],
            }
            for frame in frames if isinstance(frame, dict)
        ]
        require_dependencies(board, board_dependencies, "review_board", errors)

    transactions = data.get("transactions")
    if not isinstance(transactions, list):
        errors.append("transactions must be a list")
        transactions = []
    for index, tx in enumerate(transactions):
        validate_transaction(root, tx, frames_by_uid, set(uids), data, canon_manifest, f"transactions[{index}]", errors)

    if data.get("package_status") in {"assistant_validated", "user_approved"}:
        current_artifacts = [data, *frames]
        if isinstance(board, dict):
            current_artifacts.append(board)
        for artifact in current_artifacts:
            if isinstance(artifact, dict) and artifact.get("approval_status") not in {"assistant_validated", "user_approved"}:
                errors.append(f"current artifact {artifact.get('artifact_id')} must be validated or user-approved")

    receipt_path = root / "00_manifest/MANIFEST_UPDATE_RECEIPT.json"
    metadata_path = root / "02_review_board/storyboard_review_board.metadata.json"
    continuity_path = root / "04_qa/continuity_report.md"
    validation_path = root / "04_qa/validation_report.json"
    for path, label in (
        (receipt_path, "manifest update receipt"),
        (metadata_path, "review board metadata"),
        (continuity_path, "continuity report"),
        (validation_path, "validation report"),
    ):
        if not path.is_file():
            errors.append(f"missing required output: {path.relative_to(root)}")
    if receipt_path.is_file():
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"manifest update receipt unreadable: {exc}")
        else:
            expected_registered = {data.get("artifact_id"), *artifact_ids}
            if isinstance(board, dict):
                expected_registered.add(board.get("artifact_id"))
            errors.extend(
                f"manifest update receipt: {item}"
                for item in validate_receipt(receipt, OWNER, expected_registered, canon_manifest)
            )
    if metadata_path.is_file() and isinstance(board, dict):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"review board metadata unreadable: {exc}")
        else:
            for field in ("board_type", "is_model_input", "valid_cell_count", "cell_shot_uids", "source_frame_hashes", "file_sha256"):
                if metadata.get(field) != board.get(field):
                    errors.append(f"review board metadata mismatch: {field}")
    if continuity_path.is_file() and not continuity_path.read_text(encoding="utf-8", errors="ignore").strip():
        errors.append("continuity report must not be empty")
    if validation_path.is_file():
        try:
            report = json.loads(validation_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"validation report unreadable: {exc}")
        else:
            if report.get("status") != "passed" or report.get("validated_manifest_sha256") != data.get("sha256"):
                errors.append("validation report must lock the current manifest hash")
    return errors


def validate_package(root: Path, canon_manifest: dict[str, Any] | None = None, project_root: Path | None = None) -> list[str]:
    try:
        return _validate_package(root, canon_manifest, project_root)
    except (TypeError, KeyError, AttributeError, ValueError, OverflowError) as exc:
        return [f"malformed storyboard package rejected safely: {type(exc).__name__}: {exc}"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_root", type=Path)
    parser.add_argument("--project-canon-manifest", type=Path)
    parser.add_argument("--project-root", type=Path, help="resolve Canon authority locators relative to the whole project, never package_root")
    args = parser.parse_args()
    canon_manifest = None
    project_root = None
    if args.project_canon_manifest is not None:
        if args.project_root is None:
            print("ERROR: --project-root is required with --project-canon-manifest")
            return 2
        try:
            canon_manifest = json.loads(args.project_canon_manifest.read_text(encoding="utf-8"))
            project_root = args.project_root.resolve()
        except (OSError, json.JSONDecodeError) as exc:
            print(f"ERROR: Project Canon manifest unreadable: {exc}")
            return 2
    errors = validate_package(args.package_root.resolve(), canon_manifest, project_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"FAILED: {len(errors)} error(s)")
        return 1
    print("PASS: modular storyboard package contract is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
