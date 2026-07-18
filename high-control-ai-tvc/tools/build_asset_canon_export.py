#!/usr/bin/env python3
"""Aggregate bridge from approved owner assets into AI-video Project Canon.

This bridge belongs to the explicitly selected High-Control aggregate profile.
It keeps the seven asset-owner profiles and six workflow Canon writers fixed,
but exposes them through one auditable CLI whose ``--profile`` value is always
explicit.  Independently installable owner packages do not import this module
and do not need package-local bridge wrappers.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import uuid
import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Sequence

# The aggregate is allowed to consume the installed Shot Director's canonical
# Project Canon validators.  Resolve them from the immutable aggregate release
# root instead of relying on PYTHONPATH or an independently installed owner.
AGGREGATE_REPO_ROOT = Path(__file__).resolve().parents[2]
SHOT_VALIDATOR_ROOT = AGGREGATE_REPO_ROOT / "ai-video-shot-script-director" / "scripts"
if str(SHOT_VALIDATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(SHOT_VALIDATOR_ROOT))

from validate_manifest_update_receipt import validate_receipt
from validate_project_canon_manifest import (
    canonical_hash,
    validate_manifest,
    verify_artifact_files,
)
from validate_project_canon_transition import validate_transition


SHA = re.compile(r"^[a-f0-9]{64}$")
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
ASSET_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
RECORD_FIELDS = {
    "contract_version", "artifact_id", "owner_skill", "version", "sha256",
    "approval_status", "dependencies", "affected_shot_uids", "stale_reason",
    "schema_version", "profile_id", "asset_key", "artifact_slot", "artifact_type",
    "authority_mode", "control_roles_authorized", "authority_stage",
    "terminal_route_decision", "primary_asset", "primary_asset_media",
    "prompt_evidence", "authority_evidence", "production_approval", "export_status",
}
APPROVAL_FIELDS = {
    "schema_version", "approval_event_id", "owner_skill", "asset_key",
    "primary_asset_sha256", "prompt_evidence_sha256", "affected_shot_uids",
    "authority_mode", "control_roles_authorized", "authority_stage",
    "terminal_route_decision", "assistant_qa_status",
    "production_approval_status",
}
DELTA_FIELDS = {
    "schema_version", "updated_by_skill", "base_snapshot_locator",
    "base_snapshot_file_sha256", "base_manifest_sha256", "resulting_manifest_sha256", "operation",
    "registered_artifact_id", "superseded_artifact_id", "stale_overlay_artifact_ids",
    "artifact_entry", "sha256",
}
PENDING_FIELDS = {
    "schema_version", "status", "profile_id", "updated_by_skill", "artifact_id",
    "package_root_locator", "base_snapshot_locator", "delta_locator",
    "artifact_record_locator", "receipt_locator", "base_manifest_sha256",
    "resulting_manifest_sha256", "registered_artifact_ids", "sha256",
}
PENDING_JOURNAL_LOCATOR = "00_project_canon/PENDING_PROJECT_CANON_TRANSACTION.json"
WORKFLOW_CANON_WRITERS = {
    "ai-video-shot-script-director",
    "ai-video-global-look-lock",
    "ai-video-modular-storyboard",
    "ai-video-timed-animatic-previs-director",
    "ai-video-keyframe-continuity-pack",
    "ai-video-omni-reference-prompt-director",
}
WORKFLOW_PENDING_FIELDS = {
    "schema_version", "status", "updated_by_skill", "transaction_id",
    "package_root_locator", "base_snapshot_locator", "candidate_post_locator",
    "candidate_post_file_sha256", "receipt_locator", "base_manifest_sha256",
    "resulting_manifest_sha256", "registered_artifact_ids",
    "preserved_artifact_ids", "sha256",
}


@dataclass(frozen=True)
class OwnerProfile:
    profile_id: str
    owner_skill: str
    artifact_id_code: str
    artifact_slot_prefix: str
    artifact_type: str
    required_prompt_roles: tuple[str, ...]
    authority_modes: tuple[tuple[str, tuple[str, ...]], ...]
    authority_stage: str
    terminal_route_decision: str
    requires_explicit_terminal_route: bool = False

    def roles_for_mode(self, mode: str) -> tuple[str, ...] | None:
        return dict(self.authority_modes).get(mode)


OWNER_PROFILES: dict[str, OwnerProfile] = {
    "character_casting": OwnerProfile(
        "character_casting", "character-casting-lock-board", "CASTING_CHARACTER",
        "character_asset", "CHARACTER_CASTING_LOCK_BOARD_ASSET",
        ("generation_prompt", "four_k_enhancement_prompt"),
        (("identity_and_wardrobe", ("identity", "wardrobe")),),
        "terminal_character_canon", "casting_as_terminal", True,
    ),
    "character_final": OwnerProfile(
        "character_final", "character-final-lock-board", "FINAL_CHARACTER",
        "character_asset", "CHARACTER_FINAL_LOCK_BOARD_ASSET",
        ("generation_prompt", "four_k_enhancement_prompt"),
        (("identity_and_wardrobe", ("identity", "wardrobe")),),
        "terminal_character_canon", "character_final",
    ),
    "single_face_character": OwnerProfile(
        "single_face_character", "single-face-character-lock-board", "SINGLE_FACE_CHARACTER",
        "character_asset", "SINGLE_FACE_CHARACTER_LOCK_BOARD_ASSET",
        ("generation_prompt", "four_k_enhancement_prompt"),
        (("identity_and_wardrobe", ("identity", "wardrobe")),),
        "terminal_character_canon", "single_face_character",
    ),
    "multi_angle_product": OwnerProfile(
        "multi_angle_product", "multi-angle-product-identity-lock-board", "MULTI_ANGLE_PRODUCT",
        "product_asset", "MULTI_ANGLE_PRODUCT_IDENTITY_ASSET",
        ("generation_prompt", "four_k_enhancement_prompt"),
        (("geometry_only", ("product_geometry",)),),
        "terminal_product_canon", "not_applicable",
    ),
    "packaging_product": OwnerProfile(
        "packaging_product", "packaging-product-identity-label-lock-board", "PACKAGING_PRODUCT",
        "packaging_asset", "PACKAGING_PRODUCT_IDENTITY_ASSET",
        ("generation_prompt", "four_k_enhancement_prompt"),
        (
            ("geometry_layout_only", ("product_geometry",)),
            ("geometry_layout_exact_copy_verified", ("product_geometry", "label_copy")),
        ),
        "terminal_packaging_canon", "not_applicable",
    ),
    "material_sensitive_product": OwnerProfile(
        "material_sensitive_product", "material-sensitive-product-master-asset-board", "MATERIAL_PRODUCT",
        "material_asset", "MATERIAL_SENSITIVE_PRODUCT_ASSET",
        ("generation_prompt", "four_k_enhancement_prompt"),
        (("geometry_and_material", ("product_geometry", "material_behavior")),),
        "terminal_material_canon", "not_applicable",
    ),
    "scene_canon": OwnerProfile(
        "scene_canon", "scene-canon-asset-pack", "SCENE_CANON",
        "scene_asset", "SCENE_CANON_ASSET",
        ("four_k_regeneration_prompt",),
        (("scene_canon", ("scene_canon",)),),
        "terminal_scene_canon", "not_applicable",
    ),
}
PROFILE_BY_OWNER = {profile.owner_skill: profile for profile in OWNER_PROFILES.values()}


class ExportError(ValueError):
    """Fail-closed user-facing export error."""


def _json_hash(value: dict[str, Any]) -> str:
    payload = copy.deepcopy(value)
    payload.pop("sha256", None)
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_hash_omitting(value: dict[str, Any], field: str) -> str:
    payload = copy.deepcopy(value)
    payload.pop(field, None)
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_locator(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    if "\\" in value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        return False
    return ".." not in PurePosixPath(value).parts


def _resolve_locked_file(project_root: Path, locator: str, expected_sha256: str, label: str) -> tuple[Path, bytes]:
    if not _safe_locator(locator):
        raise ExportError(f"{label} locator must be a safe project-relative path")
    if not isinstance(expected_sha256, str) or not SHA.fullmatch(expected_sha256):
        raise ExportError(f"{label} expected SHA-256 must be lowercase hexadecimal")
    root = project_root.resolve()
    candidate = (root / locator).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ExportError(f"{label} locator escapes project root") from exc
    if not candidate.is_file():
        raise ExportError(f"{label} file does not exist: {locator}")
    data = candidate.read_bytes()
    actual = _sha(data)
    if actual != expected_sha256:
        raise ExportError(f"{label} SHA-256 mismatch: expected {expected_sha256}, got {actual}")
    return candidate, data


def _validate_prompt_bytes(data: bytes, role: str) -> None:
    if not data:
        raise ExportError(f"prompt evidence {role} is empty")
    if data.startswith(b"\xef\xbb\xbf"):
        raise ExportError(f"prompt evidence {role} must not contain a UTF-8 BOM")
    if b"\r" in data:
        raise ExportError(f"prompt evidence {role} must use LF line endings")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExportError(f"prompt evidence {role} must be UTF-8 text") from exc
    if not text.strip():
        raise ExportError(f"prompt evidence {role} contains no prompt text")


def _image_metadata(data: bytes, locator: str) -> dict[str, Any]:
    """Fully decode an allowed raster and return decoder-observed metadata."""
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:
        raise ExportError("Pillow is required to validate AI-video visual primary assets") from exc
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as probe:
                image_format = probe.format
                width, height = probe.size
                probe.verify()
            with Image.open(io.BytesIO(data)) as decoded:
                if decoded.format != image_format or decoded.size != (width, height):
                    raise ExportError("primary image decoder metadata changed between verify and load")
                decoded.load()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombWarning) as exc:
        raise ExportError("primary asset is not a fully decodable PNG, JPEG, or WebP image") from exc

    mapping = {"PNG": ("image/png", {".png"}), "JPEG": ("image/jpeg", {".jpg", ".jpeg"}), "WEBP": ("image/webp", {".webp"})}
    selected = mapping.get(str(image_format).upper())
    if selected is None:
        raise ExportError("primary asset decoder format must be PNG, JPEG, or WebP")
    media_type, allowed_suffixes = selected
    if Path(locator).suffix.lower() not in allowed_suffixes:
        raise ExportError("primary asset extension does not match the decoded image format")
    if width < 64 or height < 64:
        raise ExportError("primary asset dimensions must be at least 64x64 pixels")
    return {"media_type": media_type, "width_px": width, "height_px": height}


def _parse_prompt_spec(value: str) -> tuple[str, str, str]:
    parts = value.split("=", 2)
    if len(parts) != 3 or not all(parts):
        raise argparse.ArgumentTypeError("prompt evidence must be ROLE=PROJECT_RELATIVE_LOCATOR=SHA256")
    return parts[0], parts[1], parts[2]


def _parse_file_lock_spec(value: str) -> tuple[str, str]:
    parts = value.split("=", 1)
    if len(parts) != 2 or not all(parts):
        raise argparse.ArgumentTypeError("file evidence must be PROJECT_RELATIVE_LOCATOR=SHA256")
    return parts[0], parts[1]


def _semver_tuple(value: str) -> tuple[int, int, int]:
    if not SEMVER.fullmatch(value):
        raise ExportError("asset version must be SemVer x.y.z")
    return tuple(int(part) for part in value.split("."))  # type: ignore[return-value]


def _next_patch(value: str) -> str:
    major, minor, patch = _semver_tuple(value)
    return f"{major}.{minor}.{patch + 1}"


def _artifact_identity(profile: OwnerProfile, asset_key: str, version: str) -> tuple[str, str]:
    safe_key = asset_key.upper().replace("-", "_")
    version_token = version.replace(".", "_")
    artifact_id = f"ASSET_{profile.artifact_id_code}_{safe_key}_V{version_token}"
    artifact_slot = f"{profile.artifact_slot_prefix}:{asset_key.lower()}"
    return artifact_id, artifact_slot


def _read_json_bytes(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ExportError(f"{label} must be strict UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ExportError(f"{label} root must be an object")
    return value


def validate_packaging_exact_copy_evidence(
    value: Any,
    project_root: Path,
    asset_key: str,
    primary_asset_sha256: str,
    primary_asset_path: Path | None = None,
) -> list[str]:
    if not isinstance(value, dict):
        return ["packaging exact-copy evidence root must be an object"]
    required_fields = {
        "schema_version", "owner_skill", "asset_key", "primary_asset_sha256",
        "packaging_run", "validator_file_sha256", "final_board", "sha256",
    }
    errors: list[str] = []
    if set(value) != required_fields:
        errors.append("packaging exact-copy evidence must contain exact fields")
    if value.get("schema_version") != "packaging-board-canon-evidence.v1":
        errors.append("packaging exact-copy evidence schema_version is invalid")
    if value.get("owner_skill") != "packaging-product-identity-label-lock-board":
        errors.append("packaging exact-copy evidence owner_skill is invalid")
    if value.get("asset_key") != asset_key:
        errors.append("packaging exact-copy evidence asset_key mismatch")
    if value.get("primary_asset_sha256") != primary_asset_sha256:
        errors.append("packaging exact-copy evidence primary_asset_sha256 mismatch")
    digest = value.get("sha256")
    if not isinstance(digest, str) or not SHA.fullmatch(digest) or digest != _json_hash(value):
        errors.append("packaging exact-copy evidence sha256 is not canonical")
    packaging_run = value.get("packaging_run")
    if not isinstance(packaging_run, dict) or set(packaging_run) != {
        "run_root_locator", "asset_board_manifest_locator", "asset_board_manifest_file_sha256",
    }:
        errors.append("packaging exact-copy evidence packaging_run lock is invalid")
        return errors
    run_root_locator = packaging_run.get("run_root_locator")
    if not _safe_locator(run_root_locator):
        errors.append("packaging run_root_locator must be a safe project-relative path")
        return errors
    run_root = (project_root.resolve() / str(run_root_locator)).resolve()
    try:
        run_root.relative_to(project_root.resolve())
    except ValueError:
        errors.append("packaging run root escapes project root")
        return errors
    if not run_root.is_dir():
        errors.append("packaging run root is missing")
        return errors
    expected_manifest_path = (run_root / "asset-board-manifest.json").resolve()
    try:
        manifest_path, manifest_bytes = _resolve_locked_file(
            project_root,
            packaging_run.get("asset_board_manifest_locator"),
            packaging_run.get("asset_board_manifest_file_sha256"),
            "packaging asset-board manifest",
        )
    except ExportError as exc:
        errors.append(str(exc))
        return errors
    if manifest_path != expected_manifest_path:
        errors.append("packaging asset-board manifest must be the canonical run-root manifest")
    run_manifest = _read_json_bytes(manifest_bytes, "packaging asset-board manifest")
    ocr = run_manifest.get("ocr")
    qa = run_manifest.get("qa")
    if (
        run_manifest.get("schema_version") != "packaging_video_asset_board.v2"
        or run_manifest.get("run_status") != "COMPLETE"
        or run_manifest.get("copy_authority") != "exact_copy_evidence"
        or not isinstance(ocr, dict)
        or ocr.get("status") != "reviewed"
        or ocr.get("blocking") is not False
        or run_manifest.get("unresolved_regions") != []
        or not isinstance(qa, dict)
        or qa.get("assistant_qa_status") != "passed"
        or qa.get("label_fidelity") != "pass"
        or qa.get("copy_prompt_coverage") != "pass"
        or qa.get("copy_pixel_qa") != "pass"
        or qa.get("no_visible_frames") != "pass"
    ):
        errors.append("packaging Canon authority requires a passed COMPLETE exact-copy-evidence board")

    validator_path = (
        Path(__file__).resolve().parents[2]
        / "packaging-product-identity-label-lock-board/scripts/validate_asset_board_run.py"
    )
    if not validator_path.is_file():
        errors.append("packaging run validator is unavailable; exact authority fails closed")
        return errors
    validator_sha = _sha(validator_path.read_bytes())
    if value.get("validator_file_sha256") != validator_sha:
        errors.append("packaging evidence validator_file_sha256 is stale")

    final_board = value.get("final_board")
    if not isinstance(final_board, dict) or set(final_board) != {"locator", "file_sha256"}:
        errors.append("packaging final_board lock is invalid")
        return errors
    try:
        board_path, board_bytes = _resolve_locked_file(
            project_root,
            final_board.get("locator"),
            final_board.get("file_sha256"),
            "packaging final board",
        )
    except ExportError as exc:
        errors.append(str(exc))
        return errors
    manifest_board_value = run_manifest.get("final_board_path")
    if not isinstance(manifest_board_value, str):
        errors.append("packaging manifest final_board_path is invalid")
        return errors
    manifest_board_path = Path(manifest_board_value)
    if not manifest_board_path.is_absolute():
        manifest_board_path = (run_root / manifest_board_path).resolve()
    else:
        manifest_board_path = manifest_board_path.resolve()
    if board_path != manifest_board_path:
        errors.append("packaging final_board lock does not match the board manifest")
    board_sha = _sha(board_bytes)
    if (
        board_sha != run_manifest.get("final_board_sha256")
        or board_sha != primary_asset_sha256
        or board_sha != final_board.get("file_sha256")
    ):
        errors.append("packaging final board hash does not match Canon primary")
    if primary_asset_path is not None and primary_asset_path.resolve() != board_path:
        errors.append("Canon primary path is not the accepted packaging asset board")

    # Run the package validator after all cheap evidence and hash checks pass.
    if errors:
        return errors
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(validator_path), "--manifest", str(manifest_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stdout + result.stderr).strip()
        errors.append(f"packaging asset-board live validation failed: {detail}")
    return errors


def validate_approval_evidence(
    value: Any,
    profile: OwnerProfile,
    asset_key: str,
    primary_sha256: str,
    prompt_hashes: dict[str, str],
    affected_shot_uids: list[str],
    authority_mode: str,
    control_roles_authorized: list[str],
    authority_stage: str,
    terminal_route_decision: str,
) -> list[str]:
    if not isinstance(value, dict):
        return ["approval evidence root must be an object"]
    errors: list[str] = []
    if set(value) != APPROVAL_FIELDS:
        errors.append("approval evidence must contain exact fields")
    if value.get("schema_version") != "ai-video-owner-asset-approval.v1":
        errors.append("approval evidence schema_version is invalid")
    if not isinstance(value.get("approval_event_id"), str) or not value["approval_event_id"].strip():
        errors.append("approval_event_id must be non-empty")
    if value.get("owner_skill") != profile.owner_skill:
        errors.append(f"approval evidence owner_skill must equal fixed owner {profile.owner_skill}")
    if value.get("asset_key") != asset_key:
        errors.append("approval evidence asset_key mismatch")
    if value.get("primary_asset_sha256") != primary_sha256:
        errors.append("approval evidence primary_asset_sha256 mismatch")
    if value.get("prompt_evidence_sha256") != prompt_hashes:
        errors.append("approval evidence prompt_evidence_sha256 must exactly bind every required prompt")
    if value.get("affected_shot_uids") != affected_shot_uids:
        errors.append("approval evidence affected_shot_uids must exactly equal canonical export scope")
    if value.get("authority_mode") != authority_mode:
        errors.append("approval evidence authority_mode mismatch")
    if value.get("control_roles_authorized") != control_roles_authorized:
        errors.append("approval evidence control_roles_authorized mismatch")
    if value.get("authority_stage") != authority_stage:
        errors.append("approval evidence authority_stage mismatch")
    if value.get("terminal_route_decision") != terminal_route_decision:
        errors.append("approval evidence terminal_route_decision mismatch")
    if value.get("assistant_qa_status") != "passed":
        errors.append("only an owner asset with assistant_qa_status passed can enter Canon")
    if value.get("production_approval_status") not in {"user_granted", "external_pipeline_granted"}:
        errors.append("explicit user or external-pipeline production approval is required")
    return errors


def validate_export_record(value: Any, project_root: Path | None = None) -> list[str]:
    if not isinstance(value, dict):
        return ["asset export record root must be an object"]
    errors: list[str] = []
    if set(value) != RECORD_FIELDS:
        errors.append("asset export record must contain exact fields")
    profile = OWNER_PROFILES.get(value.get("profile_id"))
    if profile is None:
        errors.append("profile_id is not one of the seven fixed owner profiles")
        return errors
    if value.get("contract_version") != "ai-video-artifact-v1":
        errors.append("contract_version must be ai-video-artifact-v1")
    if value.get("schema_version") != "ai-video-owner-asset-export.v1":
        errors.append("schema_version is invalid")
    if value.get("owner_skill") != profile.owner_skill:
        errors.append("owner_skill does not match the fixed profile")
    asset_key = value.get("asset_key")
    version = value.get("version")
    if not isinstance(asset_key, str) or not ASSET_KEY.fullmatch(asset_key):
        errors.append("asset_key is invalid")
        return errors
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        errors.append("version must be SemVer x.y.z")
        return errors
    artifact_id, artifact_slot = _artifact_identity(profile, asset_key, version)
    if value.get("artifact_id") != artifact_id:
        errors.append("artifact_id is not the deterministic fixed-owner identity")
    if value.get("artifact_slot") != artifact_slot:
        errors.append("artifact_slot is not the deterministic fixed-owner slot")
    if value.get("artifact_type") != profile.artifact_type:
        errors.append("artifact_type does not match the fixed owner profile")
    authority_mode = value.get("authority_mode")
    expected_roles = profile.roles_for_mode(authority_mode) if isinstance(authority_mode, str) else None
    if expected_roles is None:
        errors.append("authority_mode is not allowed for the fixed owner profile")
    if value.get("control_roles_authorized") != list(expected_roles or ()):
        errors.append("control_roles_authorized must exactly equal the fixed authority-mode capability set")
    if value.get("authority_stage") != profile.authority_stage:
        errors.append("authority_stage does not match the fixed owner lifecycle stage")
    if value.get("terminal_route_decision") != profile.terminal_route_decision:
        errors.append("terminal_route_decision does not match the fixed owner route")
    if value.get("dependencies") != []:
        errors.append("legacy canon asset export dependencies must be empty")
    scope = value.get("affected_shot_uids")
    if not isinstance(scope, list) or not scope or not all(isinstance(uid, str) and uid for uid in scope) or len(scope) != len(set(scope)):
        errors.append("affected_shot_uids must be a non-empty unique string array")
    if value.get("stale_reason") is not None:
        errors.append("canon-ready export stale_reason must be null")
    approval = value.get("production_approval")
    expected_approval = None
    if isinstance(approval, dict):
        expected_approval = "user_approved" if approval.get("status") == "user_granted" else "assistant_validated"
    if value.get("approval_status") != expected_approval:
        errors.append("approval_status does not match explicit production approval evidence")
    if value.get("export_status") != "canon_ready":
        errors.append("export_status must be canon_ready")
    digest = value.get("sha256")
    if not isinstance(digest, str) or not SHA.fullmatch(digest) or digest != _json_hash(value):
        errors.append("asset export record sha256 is not canonical")

    primary = value.get("primary_asset")
    primary_media = value.get("primary_asset_media")
    prompts = value.get("prompt_evidence")
    authority_evidence = value.get("authority_evidence")
    if not isinstance(primary, dict) or set(primary) != {"locator", "file_sha256"}:
        errors.append("primary_asset must contain exact locator/file_sha256 fields")
    if (
        not isinstance(primary_media, dict)
        or set(primary_media) != {"media_type", "width_px", "height_px"}
        or primary_media.get("media_type") not in {"image/png", "image/jpeg", "image/webp"}
        or not isinstance(primary_media.get("width_px"), int)
        or isinstance(primary_media.get("width_px"), bool)
        or not isinstance(primary_media.get("height_px"), int)
        or isinstance(primary_media.get("height_px"), bool)
        or primary_media.get("width_px", 0) < 64
        or primary_media.get("height_px", 0) < 64
    ):
        errors.append("primary_asset_media must lock an allowed image type and dimensions >=64x64")
    if not isinstance(prompts, list):
        errors.append("prompt_evidence must be an array")
        prompts = []
    roles = [item.get("role") for item in prompts if isinstance(item, dict)]
    if tuple(roles) != profile.required_prompt_roles:
        errors.append("prompt_evidence roles/order must exactly match the fixed owner profile")
    for index, item in enumerate(prompts):
        if not isinstance(item, dict) or set(item) != {"role", "locator", "file_sha256"}:
            errors.append(f"prompt_evidence[{index}] must contain exact fields")
    exact_packaging_mode = (
        profile.profile_id == "packaging_product"
        and authority_mode == "geometry_layout_exact_copy_verified"
    )
    if exact_packaging_mode:
        if (
            not isinstance(authority_evidence, dict)
            or set(authority_evidence) != {"role", "locator", "file_sha256", "semantic_sha256"}
            or authority_evidence.get("role") != "packaging_exact_copy"
        ):
            errors.append("exact packaging export requires locked packaging_exact_copy authority_evidence")
    elif authority_evidence is not None:
        errors.append("authority_evidence is forbidden outside exact packaging export mode")
    if not isinstance(approval, dict) or set(approval) != {"status", "evidence_locator", "evidence_file_sha256"}:
        errors.append("production_approval must contain exact fields")

    if project_root is not None and isinstance(primary, dict) and isinstance(scope, list):
        try:
            primary_path, primary_bytes = _resolve_locked_file(project_root, primary.get("locator"), primary.get("file_sha256"), "primary asset")
            observed_media = _image_metadata(primary_bytes, str(primary.get("locator")))
            if observed_media != primary_media:
                errors.append("primary_asset_media differs from the actual image bytes")
            prompt_hashes: dict[str, str] = {}
            for item in prompts:
                if not isinstance(item, dict):
                    continue
                _, prompt_bytes = _resolve_locked_file(project_root, item.get("locator"), item.get("file_sha256"), f"prompt evidence {item.get('role')}")
                _validate_prompt_bytes(prompt_bytes, str(item.get("role")))
                prompt_hashes[str(item.get("role"))] = _sha(prompt_bytes)
            if exact_packaging_mode and isinstance(authority_evidence, dict):
                _, authority_bytes = _resolve_locked_file(
                    project_root,
                    authority_evidence.get("locator"),
                    authority_evidence.get("file_sha256"),
                    "packaging exact-copy authority evidence",
                )
                authority_value = _read_json_bytes(
                    authority_bytes, "packaging exact-copy authority evidence"
                )
                if authority_evidence.get("semantic_sha256") != authority_value.get("sha256"):
                    errors.append("packaging exact-copy authority evidence semantic hash mismatch")
                errors.extend(validate_packaging_exact_copy_evidence(
                    authority_value, project_root, asset_key, _sha(primary_bytes), primary_path
                ))
            if isinstance(approval, dict):
                _, approval_bytes = _resolve_locked_file(
                    project_root, approval.get("evidence_locator"), approval.get("evidence_file_sha256"), "approval evidence"
                )
                approval_value = _read_json_bytes(approval_bytes, "approval evidence")
                errors.extend(validate_approval_evidence(
                    approval_value, profile, asset_key, _sha(primary_bytes), prompt_hashes, scope,
                    str(authority_mode), list(expected_roles or ()), profile.authority_stage,
                    profile.terminal_route_decision,
                ))
        except ExportError as exc:
            errors.append(str(exc))
    return errors


def validate_canon_delta(value: Any, profile: OwnerProfile | None = None) -> list[str]:
    if not isinstance(value, dict):
        return ["Canon delta root must be an object"]
    errors: list[str] = []
    if set(value) != DELTA_FIELDS:
        errors.append("Canon delta must contain exact fields")
    if value.get("schema_version") != "ai-video-asset-canon-delta.v1":
        errors.append("Canon delta schema_version is invalid")
    if profile is not None and value.get("updated_by_skill") != profile.owner_skill:
        errors.append("Canon delta updated_by_skill does not match fixed owner")
    if value.get("base_snapshot_locator") != "00_manifest/BASE_PROJECT_CANON_SNAPSHOT.json":
        errors.append("Canon delta base snapshot locator is invalid")
    for field in ("base_snapshot_file_sha256", "base_manifest_sha256", "resulting_manifest_sha256"):
        if not isinstance(value.get(field), str) or not SHA.fullmatch(value[field]):
            errors.append(f"Canon delta {field} is invalid")
    if value.get("operation") not in {"add", "replace"}:
        errors.append("Canon delta operation is invalid")
    if value.get("operation") == "add" and value.get("superseded_artifact_id") is not None:
        errors.append("add delta cannot name a superseded artifact")
    if value.get("operation") == "replace" and not isinstance(value.get("superseded_artifact_id"), str):
        errors.append("replace delta must name a superseded artifact")
    overlays = value.get("stale_overlay_artifact_ids")
    if not isinstance(overlays, list) or not all(isinstance(item, str) and item for item in overlays) or len(overlays) != len(set(overlays)):
        errors.append("Canon delta stale_overlay_artifact_ids must be a unique string array")
    if value.get("operation") == "add" and overlays != []:
        errors.append("add delta cannot carry stale overlays")
    entry = value.get("artifact_entry")
    if not isinstance(entry, dict) or value.get("registered_artifact_id") != entry.get("artifact_id"):
        errors.append("Canon delta registered_artifact_id must bind artifact_entry")
    if value.get("sha256") != _json_hash(value):
        errors.append("Canon delta sha256 is not canonical")
    return errors


def validate_pending_transaction(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["pending transaction root must be an object"]
    errors: list[str] = []
    if set(value) != PENDING_FIELDS:
        errors.append("pending transaction must contain exact fields")
    if value.get("schema_version") != "ai-video-asset-canon-pending-transaction.v1":
        errors.append("pending transaction schema_version is invalid")
    if value.get("status") != "prepared_or_committed_receipt_pending":
        errors.append("pending transaction status is invalid")
    profile = OWNER_PROFILES.get(value.get("profile_id"))
    if profile is None or value.get("updated_by_skill") != profile.owner_skill:
        errors.append("pending transaction fixed profile/owner mismatch")
    for field in (
        "package_root_locator", "base_snapshot_locator", "delta_locator",
        "artifact_record_locator", "receipt_locator",
    ):
        if not _safe_locator(value.get(field)):
            errors.append(f"pending transaction {field} must be a safe project-relative path")
    package_locator = value.get("package_root_locator")
    if isinstance(package_locator, str):
        package_prefix = package_locator.rstrip("/") + "/"
        for field in ("base_snapshot_locator", "delta_locator", "receipt_locator"):
            locator = value.get(field)
            if isinstance(locator, str) and not locator.startswith(package_prefix):
                errors.append(f"pending transaction {field} must remain inside package_root_locator")
    for field in ("base_manifest_sha256", "resulting_manifest_sha256"):
        if not isinstance(value.get(field), str) or not SHA.fullmatch(value[field]):
            errors.append(f"pending transaction {field} is invalid")
    registered = value.get("registered_artifact_ids")
    if not isinstance(registered, list) or not registered or not all(isinstance(item, str) and item for item in registered) or len(registered) != len(set(registered)):
        errors.append("pending transaction registered_artifact_ids must be non-empty and unique")
    if value.get("sha256") != _json_hash(value):
        errors.append("pending transaction sha256 is not canonical")
    return errors


def validate_workflow_pending_transaction(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["workflow pending transaction root must be an object"]
    errors: list[str] = []
    if set(value) != WORKFLOW_PENDING_FIELDS:
        errors.append("workflow pending transaction must contain exact fields")
    if value.get("schema_version") != "ai-video-workflow-canon-pending-transaction.v1":
        errors.append("workflow pending transaction schema_version is invalid")
    if value.get("status") != "prepared_or_committed_receipt_pending":
        errors.append("workflow pending transaction status is invalid")
    if value.get("updated_by_skill") not in WORKFLOW_CANON_WRITERS:
        errors.append("workflow pending transaction writer is not fixed")
    if not isinstance(value.get("transaction_id"), str) or not value["transaction_id"].strip():
        errors.append("workflow pending transaction_id is required")
    for field in (
        "package_root_locator", "base_snapshot_locator", "candidate_post_locator", "receipt_locator",
    ):
        if not _safe_locator(value.get(field)):
            errors.append(f"workflow pending transaction {field} is unsafe")
    package_locator = value.get("package_root_locator")
    if isinstance(package_locator, str):
        prefix = package_locator.rstrip("/") + "/"
        for field in ("base_snapshot_locator", "candidate_post_locator", "receipt_locator"):
            locator = value.get(field)
            if isinstance(locator, str) and not locator.startswith(prefix):
                errors.append(f"workflow pending transaction {field} must stay inside package root")
    for field in (
        "candidate_post_file_sha256", "base_manifest_sha256", "resulting_manifest_sha256",
    ):
        if not isinstance(value.get(field), str) or not SHA.fullmatch(value[field]):
            errors.append(f"workflow pending transaction {field} is invalid")
    for field, minimum in (("registered_artifact_ids", 1), ("preserved_artifact_ids", 0)):
        items = value.get(field)
        if not isinstance(items, list) or len(items) < minimum or not all(isinstance(item, str) and item for item in items) or len(items) != len(set(items)):
            errors.append(f"workflow pending transaction {field} is invalid")
    if value.get("sha256") != _json_hash(value):
        errors.append("workflow pending transaction sha256 is not canonical")
    return errors


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        with temp.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temp.exists():
            temp.unlink()


def _write_immutable_or_verify(path: Path, data: bytes, label: str) -> None:
    if path.exists():
        if not path.is_file() or path.read_bytes() != data:
            raise ExportError(f"existing immutable {label} differs from the exact resumed transaction")
        return
    _write_atomic(path, data)


def _remove_with_directory_fsync(path: Path) -> None:
    path.unlink()
    try:
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        return
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _strict_child(child: Path, parent: Path) -> bool:
    child_resolved, parent_resolved = child.resolve(), parent.resolve()
    if child_resolved == parent_resolved:
        return False
    try:
        child_resolved.relative_to(parent_resolved)
        return True
    except ValueError:
        return False


@contextmanager
def _project_canon_lock(project_root: Path) -> Iterator[None]:
    """Portable process lock covering the complete Canon compare-and-swap."""
    lock_path = project_root / "00_project_canon/.canon.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt  # type: ignore[import-not-found]

            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _journal_project_path(project_root: Path, locator: str, label: str) -> Path:
    if not _safe_locator(locator):
        raise ExportError(f"pending transaction {label} locator is unsafe")
    candidate = (project_root / locator).resolve()
    try:
        candidate.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ExportError(f"pending transaction {label} escapes project root") from exc
    return candidate


def _recover_or_gate_asset_pending_transaction(
    project_root: Path,
    requested_profile: OwnerProfile | None,
    requested_artifact_id: str,
    requested_package_root: Path,
) -> None:
    journal_path = project_root / PENDING_JOURNAL_LOCATOR
    if not journal_path.is_file():
        return
    journal = _read_json_bytes(journal_path.read_bytes(), "pending Canon transaction journal")
    errors = validate_pending_transaction(journal)
    if errors:
        raise ExportError("pending Canon transaction journal is invalid: " + "; ".join(errors))
    pending_profile = OWNER_PROFILES[journal["profile_id"]]
    requested_package_locator = requested_package_root.resolve().relative_to(project_root.resolve()).as_posix()
    requested_matches = (
        requested_profile is not None
        and journal.get("profile_id") == requested_profile.profile_id
        and journal.get("artifact_id") == requested_artifact_id
        and journal.get("package_root_locator") == requested_package_locator
    )
    manifest_path = project_root / "00_project_canon/PROJECT_CANON_MANIFEST.json"
    if not manifest_path.is_file():
        raise ExportError("pending Canon transaction exists but canonical manifest is missing")
    current = _read_json_bytes(manifest_path.read_bytes(), "current Canon during pending recovery")
    current_hash = current.get("sha256")
    if current_hash == journal.get("base_manifest_sha256"):
        if requested_matches:
            return
        raise ExportError(
            "another prepared Canon transaction must be resumed or resolved first: "
            f"{journal.get('artifact_id')} owned by {journal.get('updated_by_skill')}"
        )
    if current_hash != journal.get("resulting_manifest_sha256"):
        raise ExportError(
            "pending Canon transaction cannot be recovered because current Canon is neither its base nor exact post"
        )

    base_path = _journal_project_path(project_root, journal["base_snapshot_locator"], "base snapshot")
    delta_path = _journal_project_path(project_root, journal["delta_locator"], "delta")
    record_path = _journal_project_path(project_root, journal["artifact_record_locator"], "artifact record")
    receipt_path = _journal_project_path(project_root, journal["receipt_locator"], "receipt")
    if not base_path.is_file() or not delta_path.is_file() or not record_path.is_file():
        raise ExportError("committed pending transaction lacks base, delta, or owner record evidence")
    base_bytes = base_path.read_bytes()
    stored_base = _read_json_bytes(base_bytes, "pending recovery base snapshot")
    delta = _read_json_bytes(delta_path.read_bytes(), "pending recovery Canon delta")
    record = _read_json_bytes(record_path.read_bytes(), "pending recovery owner record")
    recovery_errors = validate_canon_delta(delta, pending_profile)
    recovery_errors += validate_export_record(record, project_root)
    if _sha(base_bytes) != delta.get("base_snapshot_file_sha256"):
        recovery_errors.append("pending recovery base raw hash differs from delta")
    if stored_base.get("sha256") != journal.get("base_manifest_sha256"):
        recovery_errors.append("pending recovery base canonical hash differs from journal")
    if delta.get("resulting_manifest_sha256") != journal.get("resulting_manifest_sha256"):
        recovery_errors.append("pending recovery delta post hash differs from journal")
    if delta.get("registered_artifact_id") != journal.get("artifact_id"):
        recovery_errors.append("pending recovery delta artifact differs from journal")
    if record.get("artifact_id") != journal.get("artifact_id") or record.get("owner_skill") != pending_profile.owner_skill:
        recovery_errors.append("pending recovery owner record identity differs from journal")
    delta_entry = delta.get("artifact_entry") if isinstance(delta.get("artifact_entry"), dict) else {}
    if delta_entry.get("artifact_record_locator") != journal.get("artifact_record_locator"):
        recovery_errors.append("pending recovery delta record locator differs from journal")
    if delta_entry.get("artifact_record_file_sha256") != _sha(record_path.read_bytes()):
        recovery_errors.append("pending recovery owner record bytes differ from delta four-lock")
    current_entries = [
        item for item in current.get("active_artifacts", [])
        if isinstance(item, dict) and item.get("artifact_id") == journal.get("artifact_id")
    ]
    if len(current_entries) != 1 or current_entries[0] != delta.get("artifact_entry"):
        recovery_errors.append("pending recovery current Canon lacks the exact candidate entry")
    registered_ids = set(journal["registered_artifact_ids"])
    receipt = {
        "schema_version": "ai-video-manifest-update-receipt.v1",
        "canonical_manifest_locator": "00_project_canon/PROJECT_CANON_MANIFEST.json",
        "updated_by_skill": pending_profile.owner_skill,
        "base_manifest_sha256": stored_base.get("sha256"),
        "resulting_manifest_sha256": current.get("sha256"),
        "registered_artifact_ids": sorted(registered_ids),
        "delta_status": "applied",
    }
    recovery_errors += validate_manifest(current)
    recovery_errors += verify_artifact_files(current, project_root)
    recovery_errors += validate_transition(
        stored_base, current, pending_profile.owner_skill, receipt, registered_ids, set()
    )
    recovery_errors += validate_receipt(receipt, pending_profile.owner_skill, registered_ids, current)
    if recovery_errors:
        raise ExportError("pending committed transaction recovery failed closed: " + "; ".join(recovery_errors))
    if receipt_path.exists():
        existing_receipt = _read_json_bytes(receipt_path.read_bytes(), "pending recovery existing receipt")
        if existing_receipt != receipt:
            raise ExportError("pending recovery existing receipt differs from reconstructed receipt")
    else:
        _write_atomic(receipt_path, _json_bytes(receipt))
    _remove_with_directory_fsync(journal_path)


def _recover_or_gate_workflow_pending_transaction(
    project_root: Path,
    requested_writer: str,
    requested_transaction_id: str,
    requested_package_root: Path,
    requested_registered_artifact_ids: set[str] | None = None,
    requested_preserved_artifact_ids: set[str] | None = None,
) -> bool:
    journal_path = project_root / PENDING_JOURNAL_LOCATOR
    journal = _read_json_bytes(journal_path.read_bytes(), "workflow Canon transaction journal")
    errors = validate_workflow_pending_transaction(journal)
    if errors:
        raise ExportError("workflow Canon transaction journal is invalid: " + "; ".join(errors))
    package_locator = requested_package_root.resolve().relative_to(project_root.resolve()).as_posix()
    requested_matches = (
        journal.get("updated_by_skill") == requested_writer
        and journal.get("transaction_id") == requested_transaction_id
        and journal.get("package_root_locator") == package_locator
    )
    if requested_matches and (
        requested_registered_artifact_ids is not None
        and set(journal["registered_artifact_ids"]) != requested_registered_artifact_ids
    ):
        raise ExportError("resumed workflow registered artifact IDs differ from the pending transaction")
    if requested_matches and (
        requested_preserved_artifact_ids is not None
        and set(journal["preserved_artifact_ids"]) != requested_preserved_artifact_ids
    ):
        raise ExportError("resumed workflow preserved artifact IDs differ from the pending transaction")
    manifest_path = project_root / "00_project_canon/PROJECT_CANON_MANIFEST.json"
    current_bytes = manifest_path.read_bytes()
    current = _read_json_bytes(current_bytes, "current Canon during workflow recovery")
    if current.get("sha256") == journal.get("base_manifest_sha256"):
        if requested_matches:
            return False
        raise ExportError(
            "another prepared Canon transaction must be resumed or resolved first: "
            f"{journal.get('transaction_id')} owned by {journal.get('updated_by_skill')}"
        )
    if current.get("sha256") != journal.get("resulting_manifest_sha256"):
        raise ExportError(
            "workflow pending transaction cannot recover: current Canon is neither its base nor exact post"
        )
    base_path = _journal_project_path(project_root, journal["base_snapshot_locator"], "workflow base")
    candidate_path = _journal_project_path(project_root, journal["candidate_post_locator"], "workflow candidate")
    receipt_path = _journal_project_path(project_root, journal["receipt_locator"], "workflow receipt")
    if not base_path.is_file() or not candidate_path.is_file():
        raise ExportError("committed workflow transaction lacks base or candidate-post evidence")
    base_bytes = base_path.read_bytes()
    candidate_bytes = candidate_path.read_bytes()
    base = _read_json_bytes(base_bytes, "workflow recovery base")
    candidate = _read_json_bytes(candidate_bytes, "workflow recovery candidate post")
    registered_ids = set(journal["registered_artifact_ids"])
    preserved_ids = set(journal["preserved_artifact_ids"])
    receipt = {
        "schema_version": "ai-video-manifest-update-receipt.v1",
        "canonical_manifest_locator": "00_project_canon/PROJECT_CANON_MANIFEST.json",
        "updated_by_skill": journal["updated_by_skill"],
        "base_manifest_sha256": base.get("sha256"),
        "resulting_manifest_sha256": current.get("sha256"),
        "registered_artifact_ids": sorted(registered_ids),
        "delta_status": "applied",
    }
    recovery_errors: list[str] = []
    if _sha(candidate_bytes) != journal.get("candidate_post_file_sha256"):
        recovery_errors.append("workflow candidate-post file hash differs from journal")
    if candidate_bytes != current_bytes:
        recovery_errors.append("workflow candidate-post bytes are not the exact current Canon bytes")
    if base.get("sha256") != journal.get("base_manifest_sha256"):
        recovery_errors.append("workflow recovery base hash differs from journal")
    recovery_errors += validate_manifest(current)
    recovery_errors += verify_artifact_files(current, project_root)
    recovery_errors += validate_transition(
        base, current, journal["updated_by_skill"], receipt, registered_ids, preserved_ids
    )
    recovery_errors += validate_receipt(
        receipt, journal["updated_by_skill"], registered_ids, current
    )
    if recovery_errors:
        raise ExportError("workflow committed transaction recovery failed: " + "; ".join(recovery_errors))
    if receipt_path.exists():
        existing = _read_json_bytes(receipt_path.read_bytes(), "workflow existing receipt")
        if existing != receipt:
            raise ExportError("workflow existing receipt differs from reconstructed receipt")
    else:
        _write_atomic(receipt_path, _json_bytes(receipt))
    _remove_with_directory_fsync(journal_path)
    return requested_matches


def recover_or_gate_global_pending_transaction(
    project_root: Path,
    requested_writer: str,
    requested_transaction_id: str,
    requested_package_root: Path,
    requested_asset_profile: OwnerProfile | None = None,
    requested_registered_artifact_ids: set[str] | None = None,
    requested_preserved_artifact_ids: set[str] | None = None,
) -> bool:
    """Shared pre-write gate for every Project Canon producer."""
    journal_path = project_root / PENDING_JOURNAL_LOCATOR
    if not journal_path.is_file():
        return False
    journal = _read_json_bytes(journal_path.read_bytes(), "global pending Canon journal")
    schema_version = journal.get("schema_version")
    if schema_version == "ai-video-asset-canon-pending-transaction.v1":
        _recover_or_gate_asset_pending_transaction(
            project_root,
            requested_asset_profile,
            requested_transaction_id,
            requested_package_root,
        )
        return False
    if schema_version == "ai-video-workflow-canon-pending-transaction.v1":
        return _recover_or_gate_workflow_pending_transaction(
            project_root,
            requested_writer,
            requested_transaction_id,
            requested_package_root,
            requested_registered_artifact_ids,
            requested_preserved_artifact_ids,
        )
    raise ExportError("global pending Canon journal has an unknown schema_version")


def _apply_fixed_owner_export_locked(
    profile: OwnerProfile,
    project_root: Path,
    package_root: Path,
    asset_key: str,
    version: str,
    primary_asset_locator: str,
    primary_asset_sha256: str,
    prompt_specs: Sequence[tuple[str, str, str]],
    authority_mode: str,
    approval_evidence_locator: str,
    approval_evidence_sha256: str,
    requested_shot_uids: Sequence[str],
    explicit_terminal_route: bool = False,
    packaging_exact_copy_evidence_spec: tuple[str, str] | None = None,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    package_root = package_root.resolve()
    if not project_root.is_dir():
        raise ExportError("project_root must be an existing directory")
    if not _strict_child(package_root, project_root):
        raise ExportError("package_root must be a strict child of project_root")
    if not ASSET_KEY.fullmatch(asset_key):
        raise ExportError("asset_key must match ^[A-Za-z0-9][A-Za-z0-9_-]*$")
    _semver_tuple(version)
    if profile.requires_explicit_terminal_route and not explicit_terminal_route:
        raise ExportError(
            "character casting is pre-Canon by default; explicit --casting-as-terminal "
            "is required before this casting board may become the terminal character authority"
        )
    authority_roles = profile.roles_for_mode(authority_mode)
    if authority_roles is None:
        raise ExportError(
            "authority_mode must be one of the fixed profile modes: "
            + ", ".join(mode for mode, _ in profile.authority_modes)
        )

    manifest_path = project_root / "00_project_canon/PROJECT_CANON_MANIFEST.json"
    if not manifest_path.is_file():
        raise ExportError("canonical PROJECT_CANON_MANIFEST.json is missing")
    base_bytes = manifest_path.read_bytes()
    base_file_sha = _sha(base_bytes)
    base = _read_json_bytes(base_bytes, "PROJECT_CANON_MANIFEST")
    manifest_errors = validate_manifest(base)
    if manifest_errors:
        raise ExportError("base PROJECT_CANON_MANIFEST is invalid: " + "; ".join(manifest_errors))
    if base.get("approval_status") == "draft":
        raise ExportError("draft PROJECT_CANON_MANIFEST cannot accept downstream asset registration")
    file_errors = verify_artifact_files(base, project_root)
    if file_errors:
        raise ExportError("base PROJECT_CANON_MANIFEST file locks are invalid: " + "; ".join(file_errors))

    canonical_shots = base.get("canonical_shot_uids")
    if not isinstance(canonical_shots, list) or not all(isinstance(uid, str) for uid in canonical_shots):
        raise ExportError("base Canon has no valid canonical Shot UID set")
    requested = list(requested_shot_uids)
    if not requested or len(requested) != len(set(requested)):
        raise ExportError("at least one unique --affected-shot-uid is required")
    unknown = sorted(set(requested) - set(canonical_shots))
    if unknown:
        raise ExportError("affected Shot UIDs are not in Project Canon: " + ", ".join(unknown))
    affected = [uid for uid in canonical_shots if uid in set(requested)]

    primary_path, primary_bytes = _resolve_locked_file(
        project_root, primary_asset_locator, primary_asset_sha256, "primary asset"
    )
    primary_asset_media = _image_metadata(primary_bytes, primary_asset_locator)
    authority_evidence: dict[str, Any] | None = None
    exact_packaging_mode = (
        profile.profile_id == "packaging_product"
        and authority_mode == "geometry_layout_exact_copy_verified"
    )
    if exact_packaging_mode:
        if packaging_exact_copy_evidence_spec is None:
            raise ExportError(
                "geometry_layout_exact_copy_verified requires --packaging-exact-copy-evidence "
                "LOCATOR=SHA256"
            )
        evidence_locator, evidence_expected_sha = packaging_exact_copy_evidence_spec
        _, evidence_bytes = _resolve_locked_file(
            project_root, evidence_locator, evidence_expected_sha,
            "packaging exact-copy authority evidence",
        )
        evidence_value = _read_json_bytes(evidence_bytes, "packaging exact-copy authority evidence")
        evidence_errors = validate_packaging_exact_copy_evidence(
            evidence_value, project_root, asset_key, _sha(primary_bytes), primary_path
        )
        if evidence_errors:
            raise ExportError(
                "packaging exact-copy authority evidence is invalid: " + "; ".join(evidence_errors)
            )
        authority_evidence = {
            "role": "packaging_exact_copy",
            "locator": evidence_locator,
            "file_sha256": _sha(evidence_bytes),
            "semantic_sha256": evidence_value["sha256"],
        }
    elif packaging_exact_copy_evidence_spec is not None:
        raise ExportError(
            "--packaging-exact-copy-evidence is only allowed for packaging "
            "geometry_layout_exact_copy_verified exports"
        )
    prompt_by_role: dict[str, tuple[str, str]] = {}
    for role, locator, expected_hash in prompt_specs:
        if role in prompt_by_role:
            raise ExportError(f"duplicate prompt evidence role: {role}")
        _, prompt_bytes = _resolve_locked_file(project_root, locator, expected_hash, f"prompt evidence {role}")
        _validate_prompt_bytes(prompt_bytes, role)
        prompt_by_role[role] = (locator, _sha(prompt_bytes))
    if tuple(prompt_by_role) != profile.required_prompt_roles:
        raise ExportError(
            "prompt evidence roles/order must be exactly " + ", ".join(profile.required_prompt_roles)
        )
    prompt_hashes = {role: lock[1] for role, lock in prompt_by_role.items()}

    _, approval_bytes = _resolve_locked_file(
        project_root, approval_evidence_locator, approval_evidence_sha256, "approval evidence"
    )
    approval = _read_json_bytes(approval_bytes, "approval evidence")
    approval_errors = validate_approval_evidence(
        approval, profile, asset_key, _sha(primary_bytes), prompt_hashes, affected,
        authority_mode, list(authority_roles), profile.authority_stage,
        profile.terminal_route_decision,
    )
    if approval_errors:
        raise ExportError("approval evidence is invalid: " + "; ".join(approval_errors))

    artifact_id, artifact_slot = _artifact_identity(profile, asset_key, version)
    approval_status = (
        "user_approved" if approval["production_approval_status"] == "user_granted" else "assistant_validated"
    )
    record: dict[str, Any] = {
        "contract_version": "ai-video-artifact-v1",
        "artifact_id": artifact_id,
        "owner_skill": profile.owner_skill,
        "version": version,
        "sha256": None,
        "approval_status": approval_status,
        "dependencies": [],
        "affected_shot_uids": affected,
        "stale_reason": None,
        "schema_version": "ai-video-owner-asset-export.v1",
        "profile_id": profile.profile_id,
        "asset_key": asset_key,
        "artifact_slot": artifact_slot,
        "artifact_type": profile.artifact_type,
        "authority_mode": authority_mode,
        "control_roles_authorized": list(authority_roles),
        "authority_stage": profile.authority_stage,
        "terminal_route_decision": profile.terminal_route_decision,
        "primary_asset": {"locator": primary_asset_locator, "file_sha256": _sha(primary_bytes)},
        "primary_asset_media": primary_asset_media,
        "prompt_evidence": [
            {"role": role, "locator": prompt_by_role[role][0], "file_sha256": prompt_by_role[role][1]}
            for role in profile.required_prompt_roles
        ],
        "authority_evidence": authority_evidence,
        "production_approval": {
            "status": approval["production_approval_status"],
            "evidence_locator": approval_evidence_locator,
            "evidence_file_sha256": _sha(approval_bytes),
        },
        "export_status": "canon_ready",
    }
    record["sha256"] = _json_hash(record)
    record_errors = validate_export_record(record, project_root)
    if record_errors:
        raise ExportError("generated owner artifact record is invalid: " + "; ".join(record_errors))
    record_locator = f"owned_artifacts/{artifact_id}.json"
    record_path = project_root / record_locator
    record_bytes = _json_bytes(record)
    record_file_sha = _sha(record_bytes)
    entry = {
        "artifact_slot": artifact_slot,
        "artifact_id": artifact_id,
        "artifact_type": profile.artifact_type,
        "owner_skill": profile.owner_skill,
        "version": version,
        "sha256": record["sha256"],
        "approval_status": approval_status,
        "stale_reason": None,
        "eligible_for_downstream": True,
        "affected_shot_uids": affected,
        "locator": primary_asset_locator,
        "file_sha256": _sha(primary_bytes),
        "artifact_record_locator": record_locator,
        "artifact_record_file_sha256": record_file_sha,
        "dependencies": [],
    }

    manifest_dir = package_root / "00_manifest"
    base_snapshot_path = manifest_dir / "BASE_PROJECT_CANON_SNAPSHOT.json"
    delta_path = manifest_dir / "CANON_ENTRY_DELTA.json"
    receipt_path = manifest_dir / "MANIFEST_UPDATE_RECEIPT.json"

    # Crash recovery distinguishes a prepared-but-uncommitted transaction from
    # a committed transaction missing only its receipt. Exact record bytes are
    # reusable; different bytes at the deterministic path always fail closed.
    record_preexists = record_path.exists()
    if record_preexists and record_path.read_bytes() != record_bytes:
        raise ExportError(f"immutable owner artifact record already exists: {record_locator}")
    current_entries = [
        item for item in base.get("active_artifacts", [])
        if isinstance(item, dict) and item.get("artifact_id") == artifact_id
    ]
    if record_preexists and current_entries:
        if len(current_entries) != 1:
            raise ExportError("current Canon contains duplicate committed candidate entries")
        recovery_inputs_exist = base_snapshot_path.is_file() and delta_path.is_file()
        if not recovery_inputs_exist:
            raise ExportError("committed candidate lacks immutable base/delta recovery evidence")
        stored_base_bytes = base_snapshot_path.read_bytes()
        stored_base = _read_json_bytes(stored_base_bytes, "recovery base snapshot")
        stored_delta = _read_json_bytes(delta_path.read_bytes(), "recovery Canon delta")
        recovery_errors = validate_canon_delta(stored_delta, profile)
        if _sha(stored_base_bytes) != stored_delta.get("base_snapshot_file_sha256"):
            recovery_errors.append("recovery base snapshot raw SHA-256 differs from delta")
        if stored_base.get("sha256") != stored_delta.get("base_manifest_sha256"):
            recovery_errors.append("recovery base manifest hash differs from delta")
        if base.get("sha256") != stored_delta.get("resulting_manifest_sha256"):
            recovery_errors.append("current Canon hash differs from the exact candidate post locked by delta")
        if current_entries[0] != stored_delta.get("artifact_entry"):
            recovery_errors.append("current Canon does not contain the exact committed candidate entry")
        overlay_ids = stored_delta.get("stale_overlay_artifact_ids")
        overlay_ids = overlay_ids if isinstance(overlay_ids, list) else []
        current_by_id = {
            item.get("artifact_id"): item for item in base.get("active_artifacts", [])
            if isinstance(item, dict) and isinstance(item.get("artifact_id"), str)
        }
        recovery_registered_ids = {artifact_id} | {
            item for item in overlay_ids
            if current_by_id.get(item, {}).get("owner_skill") == profile.owner_skill
        }
        recovered_receipt = {
            "schema_version": "ai-video-manifest-update-receipt.v1",
            "canonical_manifest_locator": "00_project_canon/PROJECT_CANON_MANIFEST.json",
            "updated_by_skill": profile.owner_skill,
            "base_manifest_sha256": stored_base.get("sha256"),
            "resulting_manifest_sha256": base.get("sha256"),
            "registered_artifact_ids": sorted(recovery_registered_ids),
            "delta_status": "applied",
        }
        recovery_errors += validate_transition(
            stored_base, base, profile.owner_skill, recovered_receipt, recovery_registered_ids, set()
        )
        recovery_errors += verify_artifact_files(base, project_root)
        recovery_errors += validate_receipt(
            recovered_receipt, profile.owner_skill, recovery_registered_ids, base
        )
        if recovery_errors:
            raise ExportError("committed-transition recovery failed closed: " + "; ".join(recovery_errors))
        status = "already_applied"
        if receipt_path.exists():
            existing_receipt = _read_json_bytes(receipt_path.read_bytes(), "existing manifest update receipt")
            if existing_receipt != recovered_receipt:
                raise ExportError("existing manifest update receipt differs from reconstructed transition")
        else:
            _write_atomic(receipt_path, _json_bytes(recovered_receipt))
            status = "recovered_applied_receipt"
        return {
            "status": status,
            "owner_skill": profile.owner_skill,
            "artifact_id": artifact_id,
            "artifact_slot": artifact_slot,
            "artifact_record_locator": record_locator,
            "artifact_record_file_sha256": record_file_sha,
            "primary_asset_sha256": _sha(primary_bytes),
            "base_snapshot_file_sha256": _sha(stored_base_bytes),
            "resulting_manifest_sha256": base["sha256"],
            "receipt_locator": receipt_path.relative_to(project_root).as_posix(),
        }

    post = copy.deepcopy(base)
    active = post.get("active_artifacts")
    history = post.get("superseded_artifacts")
    edges = post.get("dependency_edges")
    if not isinstance(active, list) or not isinstance(history, list) or not isinstance(edges, list):
        raise ExportError("base Canon artifact collections are invalid")
    all_ids = {
        item.get("artifact_id") for collection in (active, history) for item in collection if isinstance(item, dict)
    }
    if artifact_id in all_ids:
        raise ExportError(f"artifact_id already exists in Project Canon: {artifact_id}")
    existing = next((item for item in active if isinstance(item, dict) and item.get("artifact_slot") == artifact_slot), None)
    operation = "add"
    superseded_id: str | None = None
    stale_overlay_ids: list[str] = []
    receipt_registered_ids: set[str] = {artifact_id}
    if existing is not None:
        if existing.get("owner_skill") != profile.owner_skill:
            raise ExportError("fixed owner cannot replace another owner's artifact slot")
        if _semver_tuple(version) <= _semver_tuple(str(existing.get("version"))):
            raise ExportError("replacement asset version must exceed the current slot version")
        active_by_id = {
            str(item.get("artifact_id")): item
            for item in active if isinstance(item, dict) and isinstance(item.get("artifact_id"), str)
        }
        adjacency: dict[str, set[str]] = {}
        for dependency_edge in edges:
            if not isinstance(dependency_edge, dict):
                continue
            producer_id = dependency_edge.get("producer_artifact_id")
            consumer_id = dependency_edge.get("consumer_artifact_id")
            if isinstance(producer_id, str) and isinstance(consumer_id, str):
                adjacency.setdefault(producer_id, set()).add(consumer_id)
        queue = sorted(adjacency.get(str(existing.get("artifact_id")), set()))
        seen_consumers: set[str] = set()
        while queue:
            consumer_id = queue.pop(0)
            if consumer_id in seen_consumers:
                continue
            seen_consumers.add(consumer_id)
            queue.extend(sorted(adjacency.get(consumer_id, set()) - seen_consumers))
        stale_overlay_ids = sorted(consumer_id for consumer_id in seen_consumers if consumer_id in active_by_id)
        active.remove(existing)
        archived = copy.deepcopy(existing)
        archived["eligible_for_downstream"] = False
        archived["superseded_by_artifact_id"] = artifact_id
        history.append(archived)
        operation = "replace"
        superseded_id = str(existing.get("artifact_id"))
        for consumer_id in stale_overlay_ids:
            consumer = active_by_id[consumer_id]
            consumer["approval_status"] = "stale"
            consumer["eligible_for_downstream"] = False
            overlay_reason = (
                f"Upstream asset {superseded_id} was replaced by {artifact_id}; "
                "the owning Skill must rebuild this artifact against the replacement."
            )
            consumer["stale_reason"] = overlay_reason
            if consumer.get("owner_skill") == profile.owner_skill:
                receipt_registered_ids.add(consumer_id)
            post["stale_events"].append({
                "event_id": f"STALE_{artifact_id}_TO_{consumer_id}",
                "changed_artifact_id": artifact_id,
                "stale_artifact_ids": [consumer_id],
                "affected_shot_uids": list(consumer.get("affected_shot_uids", [])),
                "reason": overlay_reason,
            })
    active.append(entry)
    active.sort(key=lambda item: (str(item.get("artifact_slot")), str(item.get("artifact_id"))))
    post.update({
        "version": _next_patch(str(base.get("version"))),
        "sha256": None,
        "current_phase": "canon_assets",
        "revision_counter": int(base.get("revision_counter")) + 1,
        "updated_by_skill": profile.owner_skill,
        "base_manifest_sha256": base.get("sha256"),
    })
    post["sha256"] = canonical_hash(post)

    receipt = {
        "schema_version": "ai-video-manifest-update-receipt.v1",
        "canonical_manifest_locator": "00_project_canon/PROJECT_CANON_MANIFEST.json",
        "updated_by_skill": profile.owner_skill,
        "base_manifest_sha256": base["sha256"],
        "resulting_manifest_sha256": post["sha256"],
        "registered_artifact_ids": sorted(receipt_registered_ids),
        "delta_status": "applied",
    }
    delta: dict[str, Any] = {
        "schema_version": "ai-video-asset-canon-delta.v1",
        "updated_by_skill": profile.owner_skill,
        "base_snapshot_locator": "00_manifest/BASE_PROJECT_CANON_SNAPSHOT.json",
        "base_snapshot_file_sha256": base_file_sha,
        "base_manifest_sha256": base["sha256"],
        "resulting_manifest_sha256": post["sha256"],
        "operation": operation,
        "registered_artifact_id": artifact_id,
        "superseded_artifact_id": superseded_id,
        "stale_overlay_artifact_ids": stale_overlay_ids,
        "artifact_entry": entry,
        "sha256": None,
    }
    delta["sha256"] = _json_hash(delta)

    post_errors = validate_manifest(post)
    transition_errors = validate_transition(base, post, profile.owner_skill, receipt, receipt_registered_ids, set())
    receipt_errors = validate_receipt(receipt, profile.owner_skill, receipt_registered_ids, post)
    delta_errors = validate_canon_delta(delta, profile)
    errors = post_errors + transition_errors + receipt_errors + delta_errors
    if errors:
        raise ExportError("candidate Canon transition is invalid: " + "; ".join(errors))

    package_root_locator = package_root.relative_to(project_root).as_posix()
    pending_journal: dict[str, Any] = {
        "schema_version": "ai-video-asset-canon-pending-transaction.v1",
        "status": "prepared_or_committed_receipt_pending",
        "profile_id": profile.profile_id,
        "updated_by_skill": profile.owner_skill,
        "artifact_id": artifact_id,
        "package_root_locator": package_root_locator,
        "base_snapshot_locator": base_snapshot_path.relative_to(project_root).as_posix(),
        "delta_locator": delta_path.relative_to(project_root).as_posix(),
        "artifact_record_locator": record_locator,
        "receipt_locator": receipt_path.relative_to(project_root).as_posix(),
        "base_manifest_sha256": base["sha256"],
        "resulting_manifest_sha256": post["sha256"],
        "registered_artifact_ids": sorted(receipt_registered_ids),
        "sha256": None,
    }
    pending_journal["sha256"] = _json_hash(pending_journal)
    pending_errors = validate_pending_transaction(pending_journal)
    if pending_errors:
        raise ExportError("candidate pending transaction journal is invalid: " + "; ".join(pending_errors))
    pending_journal_path = project_root / PENDING_JOURNAL_LOCATOR

    if receipt_path.exists():
        raise ExportError(f"applied receipt exists without a recoverable committed transition: {receipt_path}")

    # Exact-byte idempotence lets an identical invocation resume after either
    # preparation write without weakening immutability.
    _write_immutable_or_verify(
        pending_journal_path, _json_bytes(pending_journal), "project Canon pending transaction journal"
    )
    _write_immutable_or_verify(base_snapshot_path, base_bytes, "base snapshot")
    _write_immutable_or_verify(delta_path, _json_bytes(delta), "Canon entry delta")
    if os.environ.get("AI_VIDEO_CANON_TEST_FAULT_AFTER_BASE_DELTA") == "1":
        raise ExportError("test fault injected after base/delta and before owner record")
    _write_immutable_or_verify(record_path, record_bytes, "owner artifact record")
    if os.environ.get("AI_VIDEO_CANON_TEST_FAULT_AFTER_RECORD") == "1":
        raise ExportError("test fault injected after owner record and before Canon replace")
    post_file_errors = verify_artifact_files(post, project_root)
    if post_file_errors:
        raise ExportError("post Canon four-lock verification failed: " + "; ".join(post_file_errors))

    # Compare-and-swap guard immediately before the only mutable replacement.
    # The process lock serializes cooperating writers; this raw-byte check also
    # rejects an out-of-band writer that ignored the lock.
    current_precommit_bytes = manifest_path.read_bytes()
    if current_precommit_bytes != base_bytes or _sha(current_precommit_bytes) != base_file_sha:
        raise ExportError("PROJECT_CANON changed after base read; compare-and-swap rejected the stale candidate")
    _write_atomic(manifest_path, _json_bytes(post))

    # Read back Canon before an applied receipt can exist.  This ordering makes
    # false-applied receipts impossible.  A fault after this point is recovered
    # on the next identical fixed-owner invocation from base+delta+record.
    durable_post = _read_json_bytes(manifest_path.read_bytes(), "durable post PROJECT_CANON_MANIFEST")
    durable_base = _read_json_bytes(base_snapshot_path.read_bytes(), "durable BASE_PROJECT_CANON_SNAPSHOT")
    durable_errors = validate_manifest(durable_post)
    durable_errors += verify_artifact_files(durable_post, project_root)
    durable_errors += validate_transition(
        durable_base, durable_post, profile.owner_skill, receipt, receipt_registered_ids, set()
    )
    if _sha(base_snapshot_path.read_bytes()) != base_file_sha:
        durable_errors.append("durable base snapshot raw file SHA-256 drift")
    if durable_errors:
        raise ExportError("durable export readback failed: " + "; ".join(durable_errors))

    if os.environ.get("AI_VIDEO_CANON_TEST_FAULT_AFTER_MANIFEST_REPLACE") == "1":
        raise ExportError("test fault injected after Canon replace and before applied receipt")

    _write_atomic(receipt_path, _json_bytes(receipt))
    durable_receipt = _read_json_bytes(receipt_path.read_bytes(), "durable MANIFEST_UPDATE_RECEIPT")
    receipt_readback_errors = validate_receipt(
        durable_receipt, profile.owner_skill, receipt_registered_ids, durable_post
    )
    if durable_receipt != receipt or receipt_readback_errors:
        raise ExportError(
            "durable applied receipt readback failed: "
            + "; ".join(receipt_readback_errors or ["receipt bytes differ from candidate"])
        )
    _remove_with_directory_fsync(pending_journal_path)

    return {
        "status": "applied",
        "owner_skill": profile.owner_skill,
        "artifact_id": artifact_id,
        "artifact_slot": artifact_slot,
        "artifact_record_locator": record_locator,
        "artifact_record_file_sha256": record_file_sha,
        "primary_asset_sha256": _sha(primary_bytes),
        "base_snapshot_file_sha256": base_file_sha,
        "resulting_manifest_sha256": durable_post["sha256"],
        "receipt_locator": receipt_path.relative_to(project_root).as_posix(),
    }


def apply_fixed_owner_export(
    profile: OwnerProfile,
    project_root: Path,
    package_root: Path,
    asset_key: str,
    version: str,
    primary_asset_locator: str,
    primary_asset_sha256: str,
    prompt_specs: Sequence[tuple[str, str, str]],
    authority_mode: str,
    approval_evidence_locator: str,
    approval_evidence_sha256: str,
    requested_shot_uids: Sequence[str],
    explicit_terminal_route: bool = False,
    packaging_exact_copy_evidence_spec: tuple[str, str] | None = None,
) -> dict[str, Any]:
    root = project_root.resolve()
    if not root.is_dir():
        raise ExportError("project_root must be an existing directory")
    package = package_root.resolve()
    if not _strict_child(package, root):
        raise ExportError("package_root must be a strict child of project_root")
    if not ASSET_KEY.fullmatch(asset_key):
        raise ExportError("asset_key must match ^[A-Za-z0-9][A-Za-z0-9_-]*$")
    _semver_tuple(version)
    requested_artifact_id, _requested_slot = _artifact_identity(profile, asset_key, version)
    with _project_canon_lock(root):
        recover_or_gate_global_pending_transaction(
            root,
            profile.owner_skill,
            requested_artifact_id,
            package,
            requested_asset_profile=profile,
        )
        return _apply_fixed_owner_export_locked(
            profile=profile,
            project_root=root,
            package_root=package,
            asset_key=asset_key,
            version=version,
            primary_asset_locator=primary_asset_locator,
            primary_asset_sha256=primary_asset_sha256,
            prompt_specs=prompt_specs,
            authority_mode=authority_mode,
            approval_evidence_locator=approval_evidence_locator,
            approval_evidence_sha256=approval_evidence_sha256,
            requested_shot_uids=requested_shot_uids,
            explicit_terminal_route=explicit_terminal_route,
            packaging_exact_copy_evidence_spec=packaging_exact_copy_evidence_spec,
        )


def _apply_workflow_canon_transition_locked(
    owner_skill: str,
    project_root: Path,
    package_root: Path,
    transaction_id: str,
    registered_artifact_ids: set[str],
    preserved_artifact_ids: set[str],
) -> dict[str, Any]:
    base_path = package_root / "00_manifest/BASE_PROJECT_CANON_SNAPSHOT.json"
    candidate_path = package_root / "00_manifest/CANDIDATE_PROJECT_CANON_POST.json"
    receipt_path = package_root / "00_manifest/MANIFEST_UPDATE_RECEIPT.json"
    manifest_path = project_root / "00_project_canon/PROJECT_CANON_MANIFEST.json"
    for path, label in (
        (base_path, "BASE_PROJECT_CANON_SNAPSHOT.json"),
        (candidate_path, "CANDIDATE_PROJECT_CANON_POST.json"),
        (manifest_path, "canonical PROJECT_CANON_MANIFEST.json"),
    ):
        if not path.is_file():
            raise ExportError(f"workflow Canon writer missing {label}")
    base_bytes = base_path.read_bytes()
    candidate_bytes = candidate_path.read_bytes()
    current_bytes = manifest_path.read_bytes()
    base = _read_json_bytes(base_bytes, "workflow base snapshot")
    candidate = _read_json_bytes(candidate_bytes, "workflow candidate post")
    current = _read_json_bytes(current_bytes, "workflow current Canon")
    receipt = {
        "schema_version": "ai-video-manifest-update-receipt.v1",
        "canonical_manifest_locator": "00_project_canon/PROJECT_CANON_MANIFEST.json",
        "updated_by_skill": owner_skill,
        "base_manifest_sha256": base.get("sha256"),
        "resulting_manifest_sha256": candidate.get("sha256"),
        "registered_artifact_ids": sorted(registered_artifact_ids),
        "delta_status": "applied",
    }
    errors = validate_manifest(base)
    errors += validate_manifest(candidate)
    errors += verify_artifact_files(base, project_root)
    errors += verify_artifact_files(candidate, project_root)
    errors += validate_transition(
        base, candidate, owner_skill, receipt, registered_artifact_ids, preserved_artifact_ids
    )
    errors += validate_receipt(receipt, owner_skill, registered_artifact_ids, candidate)
    if errors:
        raise ExportError("workflow Canon candidate is invalid: " + "; ".join(errors))

    if receipt_path.exists() and current == candidate:
        existing = _read_json_bytes(receipt_path.read_bytes(), "existing workflow receipt")
        if existing != receipt:
            raise ExportError("existing workflow receipt differs from exact candidate transition")
        return {
            "status": "already_applied",
            "updated_by_skill": owner_skill,
            "transaction_id": transaction_id,
            "resulting_manifest_sha256": current["sha256"],
            "registered_artifact_ids": sorted(registered_artifact_ids),
        }
    if receipt_path.exists():
        raise ExportError("workflow applied receipt exists but current Canon is not its exact candidate post")
    if current_bytes != base_bytes or current.get("sha256") != base.get("sha256"):
        raise ExportError("workflow base snapshot is not the exact current Canon bytes")

    package_locator = package_root.relative_to(project_root).as_posix()
    journal: dict[str, Any] = {
        "schema_version": "ai-video-workflow-canon-pending-transaction.v1",
        "status": "prepared_or_committed_receipt_pending",
        "updated_by_skill": owner_skill,
        "transaction_id": transaction_id,
        "package_root_locator": package_locator,
        "base_snapshot_locator": base_path.relative_to(project_root).as_posix(),
        "candidate_post_locator": candidate_path.relative_to(project_root).as_posix(),
        "candidate_post_file_sha256": _sha(candidate_bytes),
        "receipt_locator": receipt_path.relative_to(project_root).as_posix(),
        "base_manifest_sha256": base["sha256"],
        "resulting_manifest_sha256": candidate["sha256"],
        "registered_artifact_ids": sorted(registered_artifact_ids),
        "preserved_artifact_ids": sorted(preserved_artifact_ids),
        "sha256": None,
    }
    journal["sha256"] = _json_hash(journal)
    journal_errors = validate_workflow_pending_transaction(journal)
    if journal_errors:
        raise ExportError("workflow pending journal candidate is invalid: " + "; ".join(journal_errors))
    journal_path = project_root / PENDING_JOURNAL_LOCATOR
    _write_immutable_or_verify(journal_path, _json_bytes(journal), "workflow pending transaction journal")
    if os.environ.get("AI_VIDEO_CANON_TEST_FAULT_AFTER_RECORD") == "1":
        raise ExportError("test fault injected after workflow journal and before Canon replace")
    if manifest_path.read_bytes() != base_bytes:
        raise ExportError("PROJECT_CANON changed after workflow base read; compare-and-swap rejected candidate")
    _write_atomic(manifest_path, candidate_bytes)
    durable = _read_json_bytes(manifest_path.read_bytes(), "durable workflow post Canon")
    durable_errors = validate_manifest(durable)
    durable_errors += verify_artifact_files(durable, project_root)
    durable_errors += validate_transition(
        base, durable, owner_skill, receipt, registered_artifact_ids, preserved_artifact_ids
    )
    if durable != candidate:
        durable_errors.append("durable workflow post differs from candidate bytes")
    if durable_errors:
        raise ExportError("workflow durable Canon readback failed: " + "; ".join(durable_errors))
    if os.environ.get("AI_VIDEO_CANON_TEST_FAULT_AFTER_MANIFEST_REPLACE") == "1":
        raise ExportError("test fault injected after workflow Canon replace and before receipt")
    _write_atomic(receipt_path, _json_bytes(receipt))
    readback_receipt = _read_json_bytes(receipt_path.read_bytes(), "workflow receipt readback")
    if readback_receipt != receipt:
        raise ExportError("workflow applied receipt readback differs from candidate")
    _remove_with_directory_fsync(journal_path)
    return {
        "status": "applied",
        "updated_by_skill": owner_skill,
        "transaction_id": transaction_id,
        "resulting_manifest_sha256": durable["sha256"],
        "registered_artifact_ids": sorted(registered_artifact_ids),
    }


def apply_workflow_canon_transition(
    owner_skill: str,
    project_root: Path,
    package_root: Path,
    transaction_id: str,
    registered_artifact_ids: set[str],
    preserved_artifact_ids: set[str],
) -> dict[str, Any]:
    if owner_skill not in WORKFLOW_CANON_WRITERS:
        raise ExportError("workflow Canon writer is not one of the six fixed Canon owners")
    if not transaction_id.strip():
        raise ExportError("transaction_id must be non-empty")
    if not registered_artifact_ids:
        raise ExportError("at least one registered artifact ID is required")
    root = project_root.resolve()
    package = package_root.resolve()
    if not root.is_dir() or not _strict_child(package, root):
        raise ExportError("workflow project/package roots are invalid")
    with _project_canon_lock(root):
        recovered_same = recover_or_gate_global_pending_transaction(
            root,
            owner_skill,
            transaction_id,
            package,
            requested_registered_artifact_ids=registered_artifact_ids,
            requested_preserved_artifact_ids=preserved_artifact_ids,
        )
        if recovered_same:
            current = _read_json_bytes(
                (root / "00_project_canon/PROJECT_CANON_MANIFEST.json").read_bytes(),
                "recovered workflow Canon",
            )
            return {
                "status": "recovered_applied_receipt",
                "updated_by_skill": owner_skill,
                "transaction_id": transaction_id,
                "resulting_manifest_sha256": current["sha256"],
                "registered_artifact_ids": sorted(registered_artifact_ids),
            }
        return _apply_workflow_canon_transition_locked(
            owner_skill, root, package, transaction_id,
            registered_artifact_ids, preserved_artifact_ids,
        )


def run_fixed_workflow_canon_writer_cli(
    owner_skill: str, wrapper_path: Path, argv: Sequence[str] | None = None
) -> int:
    if owner_skill not in WORKFLOW_CANON_WRITERS:
        print("ERROR: wrapper selected an unknown workflow Canon owner")
        return 2
    try:
        package_name = wrapper_path.resolve().parents[1].name
    except IndexError:
        print("ERROR: workflow Canon wrapper path is invalid")
        return 2
    if package_name != owner_skill:
        print("ERROR: workflow Canon wrapper path/owner mismatch")
        return 2
    parser = argparse.ArgumentParser(
        description=f"Atomically apply one {owner_skill} Project Canon transition"
    )
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--package-root", required=True, type=Path)
    parser.add_argument("--transaction-id", required=True)
    parser.add_argument("--expected-registered-artifact-id", action="append", required=True)
    parser.add_argument("--preserved-artifact-id", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        result = apply_workflow_canon_transition(
            owner_skill,
            args.project_root,
            args.package_root,
            args.transaction_id,
            set(args.expected_registered_artifact_id),
            set(args.preserved_artifact_id),
        )
    except (ExportError, OSError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def run_fixed_owner_cli(profile_id: str, wrapper_path: Path, argv: Sequence[str] | None = None) -> int:
    profile = OWNER_PROFILES.get(profile_id)
    if profile is None:
        print("ERROR: wrapper selected an unknown fixed owner profile")
        return 2
    try:
        package_name = wrapper_path.resolve().parents[1].name
    except IndexError:
        print("ERROR: fixed-owner wrapper path is invalid")
        return 2
    if package_name != profile.owner_skill:
        print(
            f"ERROR: fixed-owner wrapper/profile mismatch: package {package_name!r}, "
            f"profile owner {profile.owner_skill!r}"
        )
        return 2

    parser = argparse.ArgumentParser(
        description=f"Export one approved {profile.owner_skill} asset into AI-video Project Canon"
    )
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--package-root", required=True, type=Path)
    parser.add_argument("--asset-key", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument(
        "--authority-mode", required=True,
        choices=[mode for mode, _roles in profile.authority_modes],
    )
    parser.add_argument("--primary-asset", required=True)
    parser.add_argument("--primary-asset-sha256", required=True)
    parser.add_argument(
        "--prompt-evidence", action="append", required=True, type=_parse_prompt_spec,
        metavar="ROLE=LOCATOR=SHA256",
    )
    parser.add_argument("--approval-evidence", required=True)
    parser.add_argument("--approval-evidence-sha256", required=True)
    parser.add_argument("--affected-shot-uid", action="append", required=True)
    if profile.profile_id == "packaging_product":
        parser.add_argument(
            "--packaging-exact-copy-evidence",
            type=_parse_file_lock_spec,
            metavar="LOCATOR=SHA256",
            help="Required COMPLETE-run-bound v2 exact-copy authority evidence for label_copy exports",
        )
    if profile.requires_explicit_terminal_route:
        parser.add_argument(
            "--casting-as-terminal",
            action="store_true",
            help="Explicitly select the casting board as the terminal character Canon route",
        )
    args = parser.parse_args(argv)
    try:
        result = apply_fixed_owner_export(
            profile=profile,
            project_root=args.project_root,
            package_root=args.package_root,
            asset_key=args.asset_key,
            version=args.version,
            primary_asset_locator=args.primary_asset,
            primary_asset_sha256=args.primary_asset_sha256,
            prompt_specs=args.prompt_evidence,
            authority_mode=args.authority_mode,
            approval_evidence_locator=args.approval_evidence,
            approval_evidence_sha256=args.approval_evidence_sha256,
            requested_shot_uids=args.affected_shot_uid,
            explicit_terminal_route=getattr(args, "casting_as_terminal", False),
            packaging_exact_copy_evidence_spec=getattr(args, "packaging_exact_copy_evidence", None),
        )
    except (ExportError, OSError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def run_aggregate_cli(argv: Sequence[str] | None = None) -> int:
    """Run the optional aggregate bridge with an explicit fixed profile."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)

    asset = subparsers.add_parser(
        "asset", description="Register one approved fixed-owner visual asset in Project Canon"
    )
    asset.add_argument("--profile", required=True, choices=sorted(OWNER_PROFILES))
    asset.add_argument("--project-root", required=True, type=Path)
    asset.add_argument("--package-root", required=True, type=Path)
    asset.add_argument("--asset-key", required=True)
    asset.add_argument("--version", required=True)
    asset.add_argument("--authority-mode", required=True)
    asset.add_argument("--primary-asset", required=True)
    asset.add_argument("--primary-asset-sha256", required=True)
    asset.add_argument(
        "--prompt-evidence", action="append", required=True, type=_parse_prompt_spec,
        metavar="ROLE=LOCATOR=SHA256",
    )
    asset.add_argument("--approval-evidence", required=True)
    asset.add_argument("--approval-evidence-sha256", required=True)
    asset.add_argument("--affected-shot-uid", action="append", required=True)
    asset.add_argument(
        "--packaging-exact-copy-evidence", type=_parse_file_lock_spec,
        metavar="LOCATOR=SHA256",
    )
    asset.add_argument("--casting-as-terminal", action="store_true")

    workflow = subparsers.add_parser(
        "workflow", description="Atomically apply one fixed workflow-owner Canon transition"
    )
    workflow.add_argument("--profile", required=True, choices=sorted(WORKFLOW_CANON_WRITERS))
    workflow.add_argument("--project-root", required=True, type=Path)
    workflow.add_argument("--package-root", required=True, type=Path)
    workflow.add_argument("--transaction-id", required=True)
    workflow.add_argument("--expected-registered-artifact-id", action="append", required=True)
    workflow.add_argument("--preserved-artifact-id", action="append", default=[])

    args = parser.parse_args(argv)
    try:
        if args.operation == "asset":
            profile = OWNER_PROFILES[args.profile]
            if args.casting_as_terminal and profile.profile_id != "character_casting":
                raise ExportError("--casting-as-terminal is only valid for character_casting")
            result = apply_fixed_owner_export(
                profile=profile,
                project_root=args.project_root,
                package_root=args.package_root,
                asset_key=args.asset_key,
                version=args.version,
                primary_asset_locator=args.primary_asset,
                primary_asset_sha256=args.primary_asset_sha256,
                prompt_specs=args.prompt_evidence,
                authority_mode=args.authority_mode,
                approval_evidence_locator=args.approval_evidence,
                approval_evidence_sha256=args.approval_evidence_sha256,
                requested_shot_uids=args.affected_shot_uid,
                explicit_terminal_route=args.casting_as_terminal,
                packaging_exact_copy_evidence_spec=args.packaging_exact_copy_evidence,
            )
        else:
            result = apply_workflow_canon_transition(
                args.profile,
                args.project_root,
                args.package_root,
                args.transaction_id,
                set(args.expected_registered_artifact_id),
                set(args.preserved_artifact_id),
            )
    except (ExportError, OSError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


__all__ = [
    "ExportError", "OWNER_PROFILES", "OwnerProfile", "apply_fixed_owner_export",
    "WORKFLOW_CANON_WRITERS", "apply_workflow_canon_transition", "run_aggregate_cli",
    "run_fixed_owner_cli", "run_fixed_workflow_canon_writer_cli",
    "validate_approval_evidence", "validate_canon_delta",
    "validate_export_record", "validate_packaging_exact_copy_evidence",
]


if __name__ == "__main__":
    raise SystemExit(run_aggregate_cli())
