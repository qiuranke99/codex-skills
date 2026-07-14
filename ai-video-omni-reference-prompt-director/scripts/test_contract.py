#!/usr/bin/env python3
"""System-level positive and adversarial fixtures for the Prompt Director."""

from __future__ import annotations

import copy
import atexit
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import wave
import zlib
from pathlib import Path
from typing import Any, Callable

from PIL import Image


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("validator", HERE / "validate_prompt_package.py")
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

# Prompt cases reuse one ordinary project fixture.  A process audit barrier
# blocks writes to the complete Packaging authority closure before the OS can
# mutate it; only non-Packaging dirty paths are restored between cases.  The
# production owner validator still runs once for every isolated harness.  A
# real Packaging mutation must use an independent, non-cached byte copy.
_ORIGINAL_VALIDATE_OWNER_ASSET_EXPORT = validator.validate_owner_asset_export
_PACKAGING_OWNER_VALIDATION_CACHE: dict[str, tuple[str, ...]] = {}
_PACKAGING_FIXTURE_CACHE: dict[str, Path] = {}
_PACKAGING_FIXTURE_TEMP_DIRS: list[tempfile.TemporaryDirectory[str]] = []
_PACKAGING_FIXTURE_MODULE: Any | None = None
_CASE_HARNESSES: list["CaseHarness"] = []
_FROZEN_PROJECTS: dict[Path, "CaseHarness"] = {}


def _resolve_non_symlink_project_path(project_root: Path, locator: str) -> Path | None:
    """Resolve one project locator only when no lexical path component is a symlink."""
    relative = Path(locator)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    root = project_root.resolve()
    lexical = root
    try:
        for part in relative.parts:
            lexical = lexical / part
            if lexical.is_symlink():
                return None
        resolved = lexical.resolve()
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved


def _packaging_tree_fingerprint(record: dict[str, Any], project_root: Path) -> str | None:
    if (
        record.get("profile_id") != "packaging_product"
        or record.get("authority_mode") != "geometry_layout_exact_copy_verified"
    ):
        return None
    frozen = _FROZEN_PROJECTS.get(project_root.resolve())
    if frozen is not None and frozen.active:
        record_digest = hashlib.sha256(
            json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if record_digest == frozen.packaging_record_digest:
            return (
                f"frozen:{frozen.fixture_id}:{record_digest}:"
                f"{frozen.packaging_tree_digest}"
            )
    authority = record.get("authority_evidence")
    if not isinstance(authority, dict) or not isinstance(authority.get("locator"), str):
        return None
    try:
        external_locators = {
            record["primary_asset"]["locator"],
            authority["locator"],
            record["production_approval"]["evidence_locator"],
            *(item["locator"] for item in record["prompt_evidence"]),
        }
        locked_external_files: list[tuple[str, Path]] = []
        for locator in external_locators:
            path = _resolve_non_symlink_project_path(project_root, locator)
            if path is None or not path.is_file():
                return None
            locked_external_files.append((Path(locator).as_posix(), path))
        evidence = json.loads((project_root / authority["locator"]).read_text(encoding="utf-8"))
        run_locator = evidence["packaging_run"]["run_root_locator"]
        run_root = _resolve_non_symlink_project_path(project_root, run_locator)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if run_root is None or not run_root.is_dir() or any(path.is_symlink() for path in run_root.rglob("*")):
        return None
    digest = hashlib.sha256()
    digest.update(str(record.get("sha256", "")).encode("utf-8"))
    for locator, path in sorted(locked_external_files):
        digest.update(locator.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    for path in sorted((item for item in run_root.rglob("*") if item.is_file()), key=lambda item: item.relative_to(run_root).as_posix()):
        digest.update(path.relative_to(run_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _cached_validate_owner_asset_export(record: Any, project_root: Path | None = None) -> list[str]:
    if not isinstance(record, dict) or project_root is None:
        return _ORIGINAL_VALIDATE_OWNER_ASSET_EXPORT(record, project_root)
    key = _packaging_tree_fingerprint(record, project_root)
    if key is None:
        return _ORIGINAL_VALIDATE_OWNER_ASSET_EXPORT(record, project_root)
    cached = _PACKAGING_OWNER_VALIDATION_CACHE.get(key)
    if cached is None:
        cached = tuple(_ORIGINAL_VALIDATE_OWNER_ASSET_EXPORT(record, project_root))
        _PACKAGING_OWNER_VALIDATION_CACHE[key] = cached
    return list(cached)


validator.validate_owner_asset_export = _cached_validate_owner_asset_export

SHOTS = [f"S{index:03d}" for index in range(1, 7)]
DURATIONS = [1.0, 2.0, 3.0, 2.0, 4.0, 3.0]
LOOK_ASSET_ID = "LOOK_REFERENCE_ASSET_HERO"
CHARACTER_ASSET_ID = "ASSET_FINAL_CHARACTER_LEAD_V1_0_0"
PRODUCT_ASSET_ID = "ASSET_MATERIAL_PRODUCT_HERO_V1_0_0"
PACKAGING_ASSET_ID = "ASSET_PACKAGING_PRODUCT_HERO_LABEL_V1_0_0"
SCENE_ASSET_ID = "ASSET_SCENE_CANON_FIELD_V1_0_0"
GLOBAL_LOOK_TEMPLATE_PATH = HERE.parents[1] / "ai-video-global-look-lock/references/global_look_contract.template.json"
GLOBAL_LOOK_TEMPLATE = json.loads(GLOBAL_LOOK_TEMPLATE_PATH.read_text(encoding="utf-8"))
GRAMMAR = (
    "GLOBAL DIRECTING GRAMMAR — restrained performance; one primary camera intention per shot; "
    "motivated cuts; alternating environmental wides and tactile macro inserts."
)
LOOK = GLOBAL_LOOK_TEMPLATE["global_look_prompt_full"]
STATE = GLOBAL_LOOK_TEMPLATE["look_states"][0]["state_prompt_full"]
DELTA = GLOBAL_LOOK_TEMPLATE["shot_look_assignments"][0]["shot_look_delta_prompt_full"]
ATLAS_SOURCE_ARTIFACT_TYPES = {
    "GLOBAL_LOOK_REFERENCE", "CHARACTER_ASSET", "PRODUCT_ASSET", "SCENE_ASSET",
    "CHARACTER_FINAL_LOCK_BOARD_ASSET", "MATERIAL_SENSITIVE_PRODUCT_ASSET", "SCENE_CANON_ASSET",
    "STORYBOARD_FRAME_LOOK_APPLIED_FINAL", "KEYFRAME_ANCHOR",
}

CONTROL_ROLES_BY_ARTIFACT_TYPE: dict[str, tuple[list[str], str]] = {
    "MODEL_CAPABILITY_PROFILE": (["provider_preflight"], "provider_preflight"),
    "PROVIDER_CAPABILITY_PROFILE": (["provider_preflight"], "provider_preflight"),
    "PROFESSIONAL_SHOT_CONTRACT": (["shot_contract"], "shot_contract"),
    "GLOBAL_LOOK_REFERENCE": (["global_look"], "global_look"),
    "GLOBAL_LOOK_CONTRACT": (["global_look"], "global_look"),
    "CHARACTER_FINAL_LOCK_BOARD_ASSET": (["identity", "wardrobe"], "identity"),
    "MATERIAL_SENSITIVE_PRODUCT_ASSET": (["product_geometry", "material_behavior"], "product_geometry"),
    "PACKAGING_PRODUCT_IDENTITY_ASSET": (["product_geometry", "label_copy"], "label_copy"),
    "SCENE_CANON_ASSET": (["scene_canon"], "scene_canon"),
    "STORYBOARD_FRAME_LOOK_APPLIED_FINAL": (["storyboard"], "storyboard"),
    "STORYBOARD_MANIFEST": (["storyboard"], "storyboard"),
    "TIMING_ANIMATIC_V1_MEDIA": (["timing_map"], "timing_map"),
    "PREVIS_MANIFEST": (["timing_map"], "timing_map"),
    "KEYFRAME_ANCHOR": (["keyframe_state"], "keyframe_state"),
    "KEYFRAME_CONTINUITY_MANIFEST": (["keyframe_state"], "keyframe_state"),
}


def control_roles_for(artifact_type: str) -> tuple[list[str], str]:
    roles, primary = CONTROL_ROLES_BY_ARTIFACT_TYPE.get(
        artifact_type, (["provider_preflight"], "provider_preflight")
    )
    return list(roles), primary


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))


def write_text_lf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dependency(value: dict[str, Any]) -> dict[str, Any]:
    return {field: value[field] for field in ("artifact_id", "owner_skill", "version", "sha256")}


def envelope(
    artifact_id: str,
    owner: str,
    shots: list[str],
    dependencies: list[dict[str, Any]] | None = None,
    status: str = "user_approved",
    version: str = "1.0.0",
) -> dict[str, Any]:
    return {
        "contract_version": "ai-video-artifact-v1",
        "artifact_id": artifact_id,
        "owner_skill": owner,
        "version": version,
        "sha256": None,
        "approval_status": status,
        "dependencies": copy.deepcopy(dependencies or []),
        "affected_shot_uids": list(shots),
        "stale_reason": None,
    }


def finalize(value: dict[str, Any]) -> dict[str, Any]:
    value["sha256"] = validator.canonical_envelope_hash(value)
    return value


def canonical_hash_omitting(value: dict[str, Any], field: str) -> str:
    payload = copy.deepcopy(value)
    payload.pop(field, None)
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def profile(
    profile_type: str,
    profile_id: str,
    surface_status: str,
    limits: dict[str, Any],
    provider: str | None,
    model_id: str | None,
    documented_backend_profile_id: str | None,
    evidence_tier: str,
    locator: str,
) -> dict[str, Any]:
    return {
        "profile_type": profile_type,
        "profile_id": profile_id,
        "provider": provider,
        "model_family": "Seedance",
        "model_id": model_id,
        "surface": "third-party-api" if provider else None,
        "documented_backend_profile_id": documented_backend_profile_id,
        "generation_mode": "omni_reference_to_video",
        "surface_status": surface_status,
        "supported_modalities": ["text", "image", "video", "audio"],
        "effective_limits": limits,
        "input_constraints": {"image": None, "video": None, "audio": None},
        "capability_claims": [],
        "evidence": [{
            "evidence_tier": evidence_tier,
            "retrieved_at": "2026-07-12",
            "locator": locator,
            "supports": profile_id,
            "snapshot_path": None,
            "snapshot_file_sha256": None,
        }],
    }


def make_capability_docs(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    unknown = {
        "max_duration_seconds": None, "max_image_inputs": None, "max_video_inputs": None,
        "max_audio_inputs": None, "max_total_multimodal_inputs": None,
    }
    limits = {
        "max_duration_seconds": 15, "max_image_inputs": 9, "max_video_inputs": 3,
        "max_audio_inputs": 3, "max_total_multimodal_inputs": 15,
    }
    target = profile(
        "model_target", "seedance_2_5_forward_compatible", "forward_target_only", unknown,
        None, None, None, "preview_or_user_supplied_claim", "user-supplied-forward-structure",
    )
    target["capability_claims"] = [{
        "claim": "up_to_50_multimodal_inputs", "evidence_tier": "preview_or_user_supplied_claim",
        "runtime_verified": False, "usable_for_payload_budget": False,
    }]
    documented = profile(
        "model_documented", "seedance_2_0_documented_omni", "first_party_documented", limits,
        None, "seedance-2.0", None, "first_party_documented",
        "https://seed.bytedance.com/blog/seedance-2-0-official-launch",
    )
    model_doc = envelope("MODEL_CAPS", validator.OWNER, [], status="user_approved")
    model_doc.update({"schema_version": "ai-video-capability-profile.v1", "profiles": [target, documented]})
    finalize(model_doc)
    write_json(root / validator.MODEL_CAPS, model_doc)

    provider = profile(
        "provider_runtime", "vendor_seedance_2_0_api", "provider_schema_verified", limits,
        "fixture-provider", "vendor/doubao-seedance-2.0-omni", "seedance_2_0_documented_omni",
        "provider_schema_verified", "fixture-provider-schema",
    )
    provider["input_constraints"] = {
        "image": {
            "accepted_media_types": ["image/png", "image/jpeg", "image/webp"],
            "max_file_bytes": 20_000_000,
            "min_width_px": 256, "max_width_px": 8192,
            "min_height_px": 256, "max_height_px": 8192,
            "min_aspect_ratio": 0.1, "max_aspect_ratio": 10.0,
        },
        "video": {
            "accepted_media_types": ["video/mp4"],
            "accepted_containers": ["mp4", "mov"],
            "accepted_video_codecs": ["h264"],
            "max_file_bytes": 50_000_000,
            "min_duration_seconds": 0.1, "max_duration_seconds": 15.0,
            "min_width_px": 256, "max_width_px": 4096,
            "min_height_px": 144, "max_height_px": 4096,
            "min_aspect_ratio": 0.5, "max_aspect_ratio": 2.4,
            "min_fps": 1.0, "max_fps": 60.0,
            "audio_track_policy": "forbidden",
        },
        "audio": {
            "accepted_media_types": ["audio/wav", "audio/mpeg"],
            "accepted_audio_codecs": ["pcm_s16le", "mp3"],
            "max_file_bytes": 20_000_000, "max_duration_seconds": 15.0,
            "min_channels": 1, "max_channels": 2,
            "min_sample_rate_hz": 16000, "max_sample_rate_hz": 48000,
        },
    }
    provider_snapshot = {
        "schema_version": "ai-video-provider-runtime-capability-snapshot.v1",
        "profile_id": provider["profile_id"], "provider": provider["provider"],
        "model_family": provider["model_family"], "model_id": provider["model_id"],
        "surface": provider["surface"],
        "documented_backend_profile_id": provider["documented_backend_profile_id"],
        "generation_mode": provider["generation_mode"], "surface_status": provider["surface_status"],
        "supported_modalities": provider["supported_modalities"], "effective_limits": provider["effective_limits"],
        "input_constraints": provider["input_constraints"],
    }
    provider_snapshot_rel = "sources/provider_schema_snapshot.json"
    write_json(root / provider_snapshot_rel, provider_snapshot)
    provider["evidence"][0]["snapshot_path"] = provider_snapshot_rel
    provider["evidence"][0]["snapshot_file_sha256"] = file_hash(root / provider_snapshot_rel)
    provider_doc = envelope("PROVIDER_CAPS", validator.OWNER, [], status="user_approved")
    provider_doc.update({"schema_version": "ai-video-capability-profile.v1", "profiles": [provider]})
    finalize(provider_doc)
    write_json(root / validator.PROVIDER_CAPS, provider_doc)
    return model_doc, provider_doc


def make_binary(root: Path, artifact_id: str, suffix: str = "bin") -> tuple[str, str]:
    rel = f"sources/{artifact_id}.{suffix}"
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(("SOURCE:" + artifact_id).encode("utf-8"))
    return rel, file_hash(path)


_CONTROL_VIDEO_FIXTURE_BYTES: bytes | None = None


def make_control_video(root: Path, artifact_id: str) -> tuple[str, str, dict[str, Any]]:
    """Materialize one cached, real, silent H.264 MP4 and live-probe it."""
    global _CONTROL_VIDEO_FIXTURE_BYTES
    rel = f"sources/{artifact_id}.mp4"
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if _CONTROL_VIDEO_FIXTURE_BYTES is None:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise AssertionError("Prompt contract tests require ffmpeg for the provider-ready V2 fixture")
        with tempfile.TemporaryDirectory() as temp:
            generated = Path(temp) / "control.mp4"
            command = [
                ffmpeg, "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", "color=c=black:s=320x180:r=30:d=15",
                "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(generated),
            ]
            try:
                subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
            except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                raise AssertionError(f"cannot build provider-ready V2 fixture: {exc}") from exc
            _CONTROL_VIDEO_FIXTURE_BYTES = generated.read_bytes()
    path.write_bytes(_CONTROL_VIDEO_FIXTURE_BYTES)
    return rel, file_hash(path), validator.probe_media(path)


def make_ppm(root: Path, artifact_id: str, color: tuple[int, int, int]) -> tuple[str, str]:
    rel = f"sources/{artifact_id}.ppm"
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    width = height = 256
    pixels = bytes(color) * (width * height)
    path.write_bytes(f"P6\n{width} {height}\n255\n".encode("ascii") + pixels)
    return rel, file_hash(path)


def make_png(root: Path, artifact_id: str, color: tuple[int, int, int]) -> tuple[str, str]:
    """Write a deterministic, structurally valid 256x256 RGB PNG fixture."""
    rel = f"sources/{artifact_id}.png"
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    width = height = 256

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    scanline = b"\x00" + bytes(color) * width
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(scanline * height, level=9))
    data += chunk(b"IEND", b"")
    path.write_bytes(data)
    return rel, file_hash(path)


def write_original_json(root: Path, value: dict[str, Any], suffix: str = "original.json") -> tuple[str, str]:
    """Seal and write the actual owner artifact, never a Prompt-authored projection."""
    finalize(value)
    rel = f"sources/{value['artifact_id']}.{suffix}"
    write_json(root / rel, value)
    return rel, file_hash(root / rel)


def write_artifact_record(root: Path, value: dict[str, Any]) -> tuple[str, str]:
    rel = f"artifact_records/{value['artifact_id']}.json"
    write_json(root / rel, value)
    return rel, file_hash(root / rel)


def make_source(
    artifact_id: str,
    owner: str,
    shots: list[str],
    deps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return finalize(envelope(artifact_id, owner, shots, deps, status="user_approved"))


def make_packaging_exact_copy_authority_evidence(
    project_root: Path,
    artifact_id: str,
    asset_key: str,
) -> tuple[str, str, dict[str, str]]:
    global _PACKAGING_FIXTURE_MODULE
    packaging_scripts = HERE.parents[1] / "packaging-product-identity-label-lock-board/scripts"
    if str(packaging_scripts) not in sys.path:
        sys.path.insert(0, str(packaging_scripts))
    if _PACKAGING_FIXTURE_MODULE is None:
        module_path = packaging_scripts / "test_contract.py"
        spec = importlib.util.spec_from_file_location("_omni_packaging_contract_fixture", module_path)
        if spec is None or spec.loader is None:
            raise AssertionError("packaging fixture module is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _PACKAGING_FIXTURE_MODULE = module
    module = _PACKAGING_FIXTURE_MODULE
    fixture_data = module.valid_fixture(
        project_root / f"sources/{artifact_id}_packaging_board_fixture"
    )
    run_root = Path(fixture_data["run_dir"])
    manifest_path = Path(fixture_data["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["ocr"] = {"status": "reviewed", "blocking": False}
    manifest["copy_authority"] = "exact_copy_evidence"
    manifest["unresolved_regions"] = []
    manifest["qa"]["assistant_qa_status"] = "passed"
    write_json(manifest_path, manifest)
    primary_path = Path(manifest["final_board_path"])
    run_root_rel = run_root.relative_to(project_root).as_posix()
    primary_rel = primary_path.relative_to(project_root).as_posix()
    primary_hash = file_hash(primary_path)
    manifest_rel = manifest_path.relative_to(project_root).as_posix()
    validator_path = packaging_scripts / "validate_asset_board_run.py"
    evidence = {
        "schema_version": "packaging-board-canon-evidence.v1",
        "owner_skill": "packaging-product-identity-label-lock-board",
        "asset_key": asset_key,
        "primary_asset_sha256": primary_hash,
        "packaging_run": {
            "run_root_locator": run_root_rel,
            "asset_board_manifest_locator": manifest_rel,
            "asset_board_manifest_file_sha256": file_hash(manifest_path),
        },
        "validator_file_sha256": file_hash(validator_path),
        "final_board": {"locator": primary_rel, "file_sha256": primary_hash},
        "sha256": None,
    }
    evidence["sha256"] = validator.canonical_envelope_hash(evidence)
    evidence_rel = f"sources/{artifact_id}_packaging_exact_copy_canon_evidence.json"
    write_json(project_root / evidence_rel, evidence)
    authority = {
        "role": "packaging_exact_copy",
        "locator": evidence_rel,
        "file_sha256": file_hash(project_root / evidence_rel),
        "semantic_sha256": evidence["sha256"],
    }
    return primary_rel, primary_hash, authority


def make_bridge_asset(
    project_root: Path,
    artifact_id: str,
    owner: str,
    profile_id: str,
    asset_key: str,
    artifact_slot: str,
    artifact_type: str,
    authority_mode: str,
    control_roles: list[str],
    prompt_roles: list[str],
    color: tuple[int, int, int],
) -> tuple[dict[str, Any], str, str, str, str]:
    lifecycle = {
        "character_casting": ("terminal_character_canon", "casting_as_terminal"),
        "character_final": ("terminal_character_canon", "character_final"),
        "single_face_character": ("terminal_character_canon", "single_face_character"),
        "multi_angle_product": ("terminal_product_canon", "not_applicable"),
        "packaging_product": ("terminal_packaging_canon", "not_applicable"),
        "material_sensitive_product": ("terminal_material_canon", "not_applicable"),
        "scene_canon": ("terminal_scene_canon", "not_applicable"),
    }
    authority_stage, terminal_route_decision = lifecycle[profile_id]
    authority_evidence = None
    if (
        profile_id == "packaging_product"
        and authority_mode == "geometry_layout_exact_copy_verified"
    ):
        primary_rel, primary_hash, authority_evidence = (
            make_packaging_exact_copy_authority_evidence(
                project_root, artifact_id, asset_key
            )
        )
    else:
        primary_rel, primary_hash = make_png(project_root, artifact_id, color)
    with Image.open(project_root / primary_rel) as primary_image:
        primary_image.verify()
        primary_width, primary_height = primary_image.size
    prompt_evidence: list[dict[str, str]] = []
    prompt_hashes: dict[str, str] = {}
    for role in prompt_roles:
        prompt_rel = f"sources/{artifact_id}_{role}.md"
        prompt_path = project_root / prompt_rel
        write_text_lf(
            prompt_path,
            f"Approved {role} for {artifact_id}; preserve the fixed owner evidence exactly.\n",
        )
        digest = file_hash(prompt_path)
        prompt_evidence.append({"role": role, "locator": prompt_rel, "file_sha256": digest})
        prompt_hashes[role] = digest
    approval_rel = f"sources/{artifact_id}_approval.json"
    approval = {
        "schema_version": "ai-video-owner-asset-approval.v1",
        "approval_event_id": f"APPROVAL_{artifact_id}",
        "owner_skill": owner,
        "asset_key": asset_key,
        "primary_asset_sha256": primary_hash,
        "prompt_evidence_sha256": prompt_hashes,
        "affected_shot_uids": SHOTS,
        "authority_mode": authority_mode,
        "control_roles_authorized": control_roles,
        "authority_stage": authority_stage,
        "terminal_route_decision": terminal_route_decision,
        "assistant_qa_status": "passed",
        "production_approval_status": "user_granted",
    }
    write_json(project_root / approval_rel, approval)
    record = envelope(artifact_id, owner, SHOTS, status="user_approved")
    record.update({
        "schema_version": "ai-video-owner-asset-export.v1",
        "profile_id": profile_id,
        "asset_key": asset_key,
        "artifact_slot": artifact_slot,
        "artifact_type": artifact_type,
        "authority_mode": authority_mode,
        "control_roles_authorized": control_roles,
        "authority_stage": authority_stage,
        "terminal_route_decision": terminal_route_decision,
        "primary_asset": {"locator": primary_rel, "file_sha256": primary_hash},
        "primary_asset_media": {
            "media_type": "image/png",
            "width_px": primary_width,
            "height_px": primary_height,
        },
        "prompt_evidence": prompt_evidence,
        "authority_evidence": authority_evidence,
        "production_approval": {
            "status": "user_granted",
            "evidence_locator": approval_rel,
            "evidence_file_sha256": file_hash(project_root / approval_rel),
        },
        "export_status": "canon_ready",
    })
    finalize(record)
    record_rel, record_hash = write_artifact_record(project_root, record)
    return record, primary_rel, primary_hash, record_rel, record_hash


def make_entry(
    artifact: dict[str, Any],
    slot: str,
    artifact_type: str,
    locator: str | None = None,
    binary_hash: str | None = None,
    artifact_record_locator: str | None = None,
    artifact_record_file_sha256: str | None = None,
) -> dict[str, Any]:
    return {
        "artifact_slot": slot,
        "artifact_id": artifact["artifact_id"],
        "artifact_type": artifact_type,
        "owner_skill": artifact["owner_skill"],
        "version": artifact["version"],
        "sha256": artifact["sha256"],
        "approval_status": artifact["approval_status"],
        "stale_reason": artifact["stale_reason"],
        "eligible_for_downstream": True,
        "affected_shot_uids": artifact["affected_shot_uids"],
        "locator": locator,
        "file_sha256": binary_hash,
        "artifact_record_locator": artifact_record_locator or locator,
        "artifact_record_file_sha256": artifact_record_file_sha256 or binary_hash,
        "dependencies": copy.deepcopy(artifact["dependencies"]),
    }


def make_manifest(
    entries: list[dict[str, Any]],
    version: str,
    current_phase: str,
    updated_by: str,
    base_hash: str | None,
    revision_counter: int,
) -> dict[str, Any]:
    manifest = envelope(
        "PROJECT_CANON_MANIFEST_FIXTURE", "ai-video-shot-script-director", SHOTS,
        dependencies=[], status="assistant_validated", version=version,
    )
    edges = []
    for entry in entries:
        for dep in entry["dependencies"]:
            edges.append({
                "producer_artifact_id": dep["artifact_id"],
                "consumer_artifact_id": entry["artifact_id"],
                "producer_sha256": dep["sha256"],
                "affected_shot_uids": entry["affected_shot_uids"],
            })
    manifest.update({
        "schema_version": "ai-video-project-canon-manifest.v1",
        "project_id": "PROJECT_FIXTURE",
        "manifest_role": "artifact_registry_only",
        "manifest_update_policy": "validated_atomic_delta_no_reverse_dependency",
        "current_phase": current_phase,
        "revision_counter": revision_counter,
        "updated_by_skill": updated_by,
        "base_manifest_sha256": base_hash,
        "canonical_shot_uids": SHOTS,
        "active_artifacts": entries,
        "superseded_artifacts": [],
        "dependency_edges": edges,
        "stale_events": [],
        "unresolved_change_requests": [],
    })
    return finalize(manifest)


def manifest_receipt(path: str, manifest: dict[str, Any], root: Path) -> dict[str, Any]:
    return {
        "manifest_artifact_id": manifest["artifact_id"],
        "manifest_version": manifest["version"],
        "manifest_sha256": manifest["sha256"],
        "snapshot_path": path,
        "snapshot_file_sha256": file_hash(root / path),
    }


def rendered_block(shot: dict[str, Any]) -> dict[str, Any]:
    expected = validator.shot_block_expected(shot)
    rendered = "\n".join(f"{key}: {validator.render_prompt_value(value)}" for key, value in expected.items())
    return {**expected, "rendered_block": rendered}


def fixture_media_probe(timeline: list[dict[str, Any]], duration: float) -> dict[str, Any]:
    return {
        "probe_contract_version": "ffprobe-media-evidence.v1", "container_format": "mov,mp4,m4a,3gp,3g2,mj2",
        "duration_seconds": duration, "width_pixels": 320, "height_pixels": 180, "frame_rate": "30/1",
        "media_type": "video/mp4", "video_codec": "h264",
        "decoded_video_frame_count": int(duration * 30), "decoded_video_packet_count": int(duration * 30),
        "video_stream_count": 1, "audio_stream_count": 0,
        "shot_chapters": [{"shot_uid": item["shot_uid"], "start_seconds": item["start_seconds"], "end_seconds": item["end_seconds"]} for item in timeline],
    }


def external_authority(value: dict[str, Any], snapshot_path: str, snapshot_hash: str) -> dict[str, Any]:
    return {
        **dependency(value), "approval_status": value["approval_status"],
        "snapshot_path": snapshot_path, "snapshot_file_sha256": snapshot_hash,
    }


def create_package(root: Path, project_root: Path | None = None) -> None:
    project_root = project_root or root
    root.mkdir(parents=True, exist_ok=True)

    def canon_locator(rel: str) -> str:
        return (root / rel).resolve().relative_to(project_root.resolve()).as_posix()

    model_doc, provider_doc = make_capability_docs(root)
    artifacts: dict[str, dict[str, Any]] = {
        model_doc["artifact_id"]: model_doc,
        provider_doc["artifact_id"]: provider_doc,
    }
    entries: list[dict[str, Any]] = [
        make_entry(model_doc, "model_capability", "MODEL_CAPABILITY_PROFILE", canon_locator(validator.MODEL_CAPS), file_hash(root / validator.MODEL_CAPS)),
        make_entry(provider_doc, "provider_capability", "PROVIDER_CAPABILITY_PROFILE", canon_locator(validator.PROVIDER_CAPS), file_hash(root / validator.PROVIDER_CAPS)),
    ]

    shot = envelope("SHOT_CONTRACT", "ai-video-shot-script-director", SHOTS, status="user_approved")
    contract_shots: list[dict[str, Any]] = []
    cursor = 0.0
    for display_no, (shot_uid, duration) in enumerate(zip(SHOTS, DURATIONS), 1):
        end = cursor + duration
        contract_shots.append({
            "shot_uid": shot_uid, "display_no": display_no, "target_duration_seconds": duration,
            "submode": "poetic_brand_film", "narrative_function": f"narrative function {shot_uid}",
            "advertising_function": f"advertising function {shot_uid}", "subjects": ["lead", "product"],
            "product_or_prop": ["faceted fragrance bottle"], "scene": "approved lunar glasshouse scene",
            "initial_state": f"approved initial state {shot_uid}", "action_path": [f"visible action {shot_uid}"],
            "ending_state": f"handoff state {shot_uid}", "shot_size": "medium close-up",
            "camera_height": "chest height", "camera_angle": "neutral angle",
            "lens_intent": f"approved lens intent {shot_uid}", "composition": f"approved composition {shot_uid}",
            "subject_placement": "lead on left third", "primary_camera_movement": "one calm motivated push",
            "focus_behavior": "hold approved subject and product plane", "blocking": f"approved blocking change {shot_uid}",
            "screen_direction": "stable camera-right world direction", "continuity_in": f"continuity in {shot_uid}",
            "continuity_out": f"continuity out {shot_uid}", "cut_motivation": f"motivated cut {shot_uid}",
            "transition_intent": "direct cut after action resolves",
            "visible_emotional_expression": f"restrained visible expression {shot_uid}",
            "spoken_content": {"mode": "none", "text": "", "copy_status": "not_used", "source_reference_ids": [], "claim_ids": []},
            "on_screen_copy": ([{
                "text": "Source supplied campaign line", "copy_status": "supplied_exact",
                "source_reference_ids": ["SOURCE_SCRIPT"], "claim_ids": ["CLAIM_1"],
                "timing_intent": "after the visible action resolves",
            }] if shot_uid == "S001" else []),
            "must_preserve": ["identity", "product", "material", "look"],
            "must_avoid": ["invented text", "invented efficacy claim"],
            "required_assets": ["approved character", "approved product", "approved scene"],
            "storyboard_requirement": "required", "keyframe_requirement": "required_single_anchor",
            "previs_requirement": "required",
        })
        cursor = end
    source_claim_boundary = {
        "supplied_claims": [{"claim_id": "CLAIM_1", "text": "Source supplied campaign line", "source_reference_ids": ["SOURCE_SCRIPT"]}],
        "used_claim_ids": ["CLAIM_1"], "prohibited_unsourced_claims": ["clinical efficacy"],
        "compliance_unknowns": [], "claim_generation_status": "source_supported_claims_only",
    }
    claim_boundary = {
        "claims": [{"claim_id": "CLAIM_1", "text": "Source supplied campaign line", "source_reference_ids": ["SOURCE_SCRIPT"], "usage": "used_source_supported"}],
        "prohibited_unsourced_claims": ["clinical efficacy"], "compliance_unknowns": [],
    }
    shot.update({
        "schema_version": "ai-video-shot-contract.v1", "project_id": "PROJECT_FIXTURE",
        "source_inputs": [{"source_id": "SOURCE_SCRIPT", "locator": "user/source.doc", "source_type": "structured_script_document", "file_sha256": None, "integrity_status": "runtime_reference_bound", "authority_scope": ["creative intent"], "extraction_status": "complete"}],
        "source_classification": {"source_type": "structured_creative_shot_draft", "creative_mode": "poetic_brand_film", "primary_mode": "poetic_brand_film", "narrative_logic": "associative montage", "product_expression": "sensorial symbolic", "literal_usage_demo": False, "source_intent_preserved": True},
        "director_intent": "Preserve poetic intent while converting every beat into observable direction.",
        "production_spec": {"aspect_ratio": "16:9", "distribution_context": ["online advertising"], "source_language": "zh-CN", "copy_policy": "Preserve supplied exact copy."},
        "global_directing_grammar": {"lens_and_scale_tendencies": ["approved lens rhythm"], "camera_movement_principles": ["one primary movement"], "composition_rules": ["stable product-readable composition"], "cutting_motivations": ["motivated cuts"], "performance_restraint": ["restrained performance"], "product_reveal_strategy": ["source-bound reveal"], "motion_rhythm": ["approved six-shot rhythm"], "immutable_core": ["restrained performance", "motivated cuts", "one primary movement"]},
        "global_directing_prompt_full": GRAMMAR,
        "timeline": {"total_duration_seconds": 15.0, "numerical_tolerance_seconds": 0.001, "shot_count": len(SHOTS)},
        "shots": contract_shots, "continuity_map": [],
        "asset_requirement_map": [{"shot_uid": uid, "requirements": ["approved character", "approved product", "approved scene"], "risk_note": "identity and product remain source-bound"} for uid in SHOTS],
        "keyframe_requirement_map": [{"shot_uid": uid, "requirement": "required_single_anchor", "reason": "generation-ready visual authority"} for uid in SHOTS],
        "previs_requirement_map": [{"shot_uid": uid, "requirement": "required", "reason": "multi-shot rhythm requires control previs"} for uid in SHOTS],
        "inferred_directing_decisions": [], "claim_boundary": source_claim_boundary, "isolated_blockers": [],
        "revision_scope": {
            "mode": "initial", "requested_shot_uids": [], "actually_changed_shot_uids": SHOTS,
            "global_fields_changed": True, "expanded_dependency_reasons": [],
            "invalidated_artifact_ids": [], "preserved_artifact_ids": [],
            "predecessor_artifact": None, "changed_json_pointers": [],
        },
    })
    shot_rel, shot_file_hash = write_original_json(project_root, shot)
    artifacts[shot["artifact_id"]] = shot
    entries.append(make_entry(shot, "professional_shot_contract", "PROFESSIONAL_SHOT_CONTRACT", shot_rel, shot_file_hash))

    look_ref = make_source(LOOK_ASSET_ID, "ai-video-global-look-lock", SHOTS, [dependency(shot)])
    look_ref_rel, look_ref_digest = make_png(project_root, look_ref["artifact_id"], (90, 120, 150))
    look_ref_record_rel, look_ref_record_digest = write_artifact_record(project_root, look_ref)
    artifacts[look_ref["artifact_id"]] = look_ref
    entries.append(make_entry(look_ref, "global_look_reference", "GLOBAL_LOOK_REFERENCE", look_ref_rel, look_ref_digest, look_ref_record_rel, look_ref_record_digest))

    look = copy.deepcopy(GLOBAL_LOOK_TEMPLATE)
    look.update({"artifact_id": "GLOBAL_LOOK", "version": "1.0.0", "sha256": None, "approval_status": "user_approved", "dependencies": [dependency(shot)], "affected_shot_uids": SHOTS, "stale_reason": None, "project_id": "PROJECT_FIXTURE", "project_shot_uids": SHOTS, "look_state_matrix_id": "LOOK_STATE_MATRIX_FIXTURE_V1"})
    look["project_constraints"]["multiple_look_states"] = False
    reference = copy.deepcopy(look["look_reference_set"][0])
    reference.update({"artifact": look_ref, "locator": look_ref_rel, "applicable_state_ids": ["LOOK_STATE_FIELD"], "approval_status": "approved", "inspection_status": "passed", "integrity_status": "verified_bytes", "file_sha256": look_ref_digest, "generation_prompt_sha256": "f" * 64, "actual_dimensions": {"width": 256, "height": 256}, "independent_full_frame": True, "derived_from_multipanel": False, "intrinsic_boundary_check": "passed"})
    look["look_reference_set"] = [reference]
    state = copy.deepcopy(look["look_states"][0])
    state["reference_ids"] = [reference["reference_id"]]
    look["look_states"] = [state]
    base_delta = copy.deepcopy(GLOBAL_LOOK_TEMPLATE["shot_look_assignments"][0]["shot_look_delta"])
    look["shot_look_assignments"] = [{"shot_uid": uid, "state_id": "LOOK_STATE_FIELD", "shot_look_delta": copy.deepcopy(base_delta), "shot_look_delta_prompt_full": DELTA} for uid in SHOTS]
    for risk in look["look_risk_coverage"]:
        risk.update({"state_ids": ["LOOK_STATE_FIELD"], "reference_ids": [reference["reference_id"]], "affected_shot_uids": SHOTS, "coverage_status": "covered"})
    look["intrinsic_product_boundaries"][0]["source_asset_ids"] = [PRODUCT_ASSET_ID, PACKAGING_ASSET_ID]
    look["skin_tone_boundaries"][0]["source_asset_ids"] = [CHARACTER_ASSET_ID]
    look["three_layer_lock"].update({"textual_contract_frozen": True, "visual_reference_set_approved": True})
    look["revision_scope"].update({"changed_state_ids": ["LOOK_STATE_FIELD"], "changed_shot_uids": SHOTS})
    look_rel, look_file_hash = write_original_json(project_root, look)
    look_schema = json.loads((HERE.parents[1] / "ai-video-global-look-lock/references/global_look_contract.schema.json").read_text(encoding="utf-8"))
    look_schema_errors = validator.validate_instance(look, look_schema, look_schema)
    if look_schema_errors:
        raise AssertionError(f"Global Look source fixture must satisfy its owner schema: {look_schema_errors}")
    artifacts[look["artifact_id"]] = look
    entries.append(make_entry(look, "global_look_contract", "GLOBAL_LOOK_CONTRACT", look_rel, look_file_hash))

    for artifact_id, owner, profile_id, asset_key, slot, artifact_type, authority_mode, roles, prompt_roles in (
        (CHARACTER_ASSET_ID, "character-final-lock-board", "character_final", "lead", "character_asset:lead", "CHARACTER_FINAL_LOCK_BOARD_ASSET", "identity_and_wardrobe", ["identity", "wardrobe"], ["generation_prompt", "four_k_enhancement_prompt"]),
        (PRODUCT_ASSET_ID, "material-sensitive-product-master-asset-board", "material_sensitive_product", "hero", "material_asset:hero", "MATERIAL_SENSITIVE_PRODUCT_ASSET", "geometry_and_material", ["product_geometry", "material_behavior"], ["generation_prompt", "four_k_enhancement_prompt"]),
        (PACKAGING_ASSET_ID, "packaging-product-identity-label-lock-board", "packaging_product", "hero-label", "packaging_asset:hero-label", "PACKAGING_PRODUCT_IDENTITY_ASSET", "geometry_layout_exact_copy_verified", ["product_geometry", "label_copy"], ["generation_prompt", "four_k_enhancement_prompt"]),
        (SCENE_ASSET_ID, "scene-canon-asset-pack", "scene_canon", "field", "scene_asset:field", "SCENE_CANON_ASSET", "scene_canon", ["scene_canon"], ["four_k_regeneration_prompt"]),
    ):
        color = (len(entries) * 29 % 256, len(entries) * 47 % 256, len(entries) * 71 % 256)
        source, rel, digest, record_rel, record_digest = make_bridge_asset(
            project_root, artifact_id, owner, profile_id, asset_key, slot, artifact_type,
            authority_mode, roles, prompt_roles, color,
        )
        artifacts[artifact_id] = source
        entries.append(make_entry(source, slot, artifact_type, rel, digest, record_rel, record_digest))

    storyboard_frames: list[dict[str, Any]] = []
    for display_no, (shot_uid, duration) in enumerate(zip(SHOTS, DURATIONS), 1):
        frame = envelope(f"SB_{shot_uid}", "ai-video-modular-storyboard", [shot_uid], [dependency(shot), dependency(look)], status="user_approved")
        rel, digest = make_png(project_root, frame["artifact_id"], (int(shot_uid[1:]) * 31 % 256, 80, 120))
        frame.update({
            "shot_uid": shot_uid, "display_order": display_no, "target_duration_seconds": duration,
            "stage": "look_applied_final", "file_path": rel, "file_sha256": digest,
            "generation_prompt_path": f"sources/{frame['artifact_id']}.prompt.md", "generation_prompt_file_sha256": "a" * 64,
            "global_directing_prompt_full": GRAMMAR, "global_look_artifact_id": look["artifact_id"],
            "global_look_prompt_full": LOOK, "look_state_id": "LOOK_STATE_FIELD", "look_state_prompt_full": STATE,
            "shot_look_delta_prompt_full": DELTA, "look_reference_asset_ids": [LOOK_ASSET_ID],
            "actual_pixel_dimensions": {"width": 256, "height": 256}, "generation_mode": "independent_full_frame",
            "independently_generated": True, "derived_from_multipanel": False, "is_model_input_eligible": True,
            "content_cleanliness": {
                "no_shot_number_overlay": True, "no_duration_overlay": True,
                "no_editorial_caption_overlay": True, "no_arrow_overlay": True,
                "no_grid": True, "no_ui": True, "no_watermark": True, "no_layout_chrome": True,
                "intrinsic_text_policy": "none_visible", "intrinsic_text_source_refs": [],
            },
        })
        finalize(frame)
        frame_record_rel, frame_record_digest = write_artifact_record(project_root, frame)
        storyboard_frames.append(frame)
        artifacts[frame["artifact_id"]] = frame
        entries.append(make_entry(frame, f"storyboard_frame:{shot_uid}", "STORYBOARD_FRAME_LOOK_APPLIED_FINAL", rel, digest, frame_record_rel, frame_record_digest))

    storyboard = envelope("STORYBOARD_MANIFEST", "ai-video-modular-storyboard", SHOTS, [dependency(shot), dependency(look)], status="user_approved")
    storyboard.update({"schema_version": "ai-video-modular-storyboard.v1", "project_id": "PROJECT_FIXTURE", "package_status": "user_approved", "storyboard_stage": "look_applied_final", "script_shot_count": len(SHOTS), "shot_contract": {**dependency(shot), "approval_status": shot["approval_status"]}, "global_look": {**dependency(look), "approval_status": look["approval_status"]}, "frames": storyboard_frames, "review_board": None, "transactions": [], "downstream_invalidations": []})
    storyboard_rel, storyboard_file_hash = write_original_json(project_root, storyboard)
    artifacts[storyboard["artifact_id"]] = storyboard
    entries.append(make_entry(storyboard, "storyboard_manifest", "STORYBOARD_MANIFEST", storyboard_rel, storyboard_file_hash))

    v1_media = envelope("TIMING_ANIMATIC_MEDIA_V1", "ai-video-timed-animatic-previs-director", SHOTS, [dependency(shot), dependency(storyboard)], status="user_approved")
    v1_path, v1_file_hash = make_binary(project_root, v1_media["artifact_id"], "mp4")
    timeline: list[dict[str, Any]] = []
    cursor = 0.0
    for display_no, (uid, duration) in enumerate(zip(SHOTS, DURATIONS), 1):
        timeline.append({"shot_uid": uid, "display_order": display_no, "start_seconds": cursor, "end_seconds": cursor + duration, "duration_seconds": duration, "cut_motivation": f"motivated cut {uid}", "rough_camera_path": f"rough camera {uid}", "rough_blocking": f"rough blocking {uid}", "motion_anchors": []})
        cursor += duration
    v1_media.update({"phase": "timing_animatic_v1", "provider_neutral": True, "uses_keyframes": False, "model_input_role": "timing_review_only", "is_model_input": False, "final_edit_asset": False, "silent": True, "render_style": "storyboard_cut_animatic", "file_path": v1_path, "file_sha256": v1_file_hash, "actual_duration_seconds": 15.0, "media_probe": fixture_media_probe(timeline, 15.0), "timeline": timeline, "control_dimensions": ["shot order", "timing"], "forbidden_dimensions": ["identity authority", "look authority"]})
    finalize(v1_media)
    v1_media_record_rel, v1_media_record_digest = write_artifact_record(project_root, v1_media)
    artifacts[v1_media["artifact_id"]] = v1_media
    entries.append(make_entry(v1_media, "timing_animatic_v1", "TIMING_ANIMATIC_V1_MEDIA", v1_path, v1_file_hash, v1_media_record_rel, v1_media_record_digest))
    v1 = envelope("PREVIS_MANIFEST_V1", "ai-video-timed-animatic-previs-director", SHOTS, [dependency(shot), dependency(storyboard)], status="user_approved")
    v1.update({"schema_version": "ai-video-timed-animatic-previs.v1", "project_id": "PROJECT_FIXTURE", "package_status": "user_approved", "delivery_stage": "timing_animatic_v1", "execution_mode": "active", "shot_count": len(SHOTS), "total_duration_seconds": 15.0, "source_authorities": {"shot_contract": external_authority(shot, shot_rel, shot_file_hash), "storyboard": external_authority(storyboard, storyboard_rel, storyboard_file_hash), "keyframe_pack": None, "keyframe_boundary_supplement": None, "provider_preflight": None, "provider_capability": None}, "input_file_evidence": [], "skip_record": None, "timing_animatic_v1": v1_media, "control_previs_v2_units": [], "motion_physics_tracks": [], "generation_modes_used": ["deterministic_animatic"], "forbidden_generation_modes": ["text_to_video", "first_last_frame", "standalone_single_image_to_video"], "downstream_invalidations": []})
    v1_rel, v1_manifest_file_hash = write_original_json(project_root, v1)
    artifacts[v1["artifact_id"]] = v1
    entries.append(make_entry(v1, "previs_manifest", "PREVIS_MANIFEST", v1_rel, v1_manifest_file_hash))

    keyframe_records: list[dict[str, Any]] = []
    for shot_uid in SHOTS:
        frame = artifacts[f"SB_{shot_uid}"]
        keyframe = envelope(f"KF_{shot_uid}", "ai-video-keyframe-continuity-pack", [shot_uid], [dependency(shot), dependency(look), dependency(storyboard), dependency(v1_media)], status="user_approved")
        rel, digest = make_png(project_root, keyframe["artifact_id"], (40, int(shot_uid[1:]) * 37 % 256, 180))
        keyframe_prompt_rel = f"sources/{keyframe['artifact_id']}_generation_prompt.md"
        write_text_lf(
            project_root / keyframe_prompt_rel,
            f"Generate {keyframe['artifact_id']} from approved source-authorized controls only.\n",
        )
        keyframe_prompt_hash = file_hash(project_root / keyframe_prompt_rel)
        finalize(keyframe)
        keyframe_record_rel, keyframe_record_digest = write_artifact_record(project_root, keyframe)
        artifacts[keyframe["artifact_id"]] = keyframe
        entries.append(make_entry(keyframe, f"keyframe:{shot_uid}", "KEYFRAME_ANCHOR", rel, digest, keyframe_record_rel, keyframe_record_digest))
        keyframe_records.append({
            "shot_uid": shot_uid, "storyboard_artifact_id": frame["artifact_id"], "required_authority_artifact_ids": [shot["artifact_id"], storyboard["artifact_id"], look["artifact_id"]],
            "global_directing_prompt_full": GRAMMAR, "global_look_artifact_id": look["artifact_id"], "global_look_prompt_full": LOOK,
            "look_state_id": "LOOK_STATE_FIELD", "look_state_prompt_full": STATE, "shot_look_delta_prompt_full": DELTA, "look_reference_asset_ids": [LOOK_ASSET_ID],
            "anchor_route": "independent_keyframe", "keyframes": [{"artifact": keyframe, "keyframe_id": keyframe["artifact_id"], "shot_uid": shot_uid, "frame_role": "primary_anchor", "usage_mode": "omni_reference_anchor", "source_mode": "independent_keyframe", "file_path": rel, "file_sha256": digest, "prompt_path": keyframe_prompt_rel, "prompt_file_sha256": keyframe_prompt_hash, "time_anchor": {"source": "v1_timing_animatic", "timecode_seconds": 0.0, "relative_state": "primary_control_state"}, "terminal_generation_call": "executed", "generation_turn": 1, "inspection_turn": 2, "visual_qa_status": "passed", "promotion_evidence": []}],
            "character_state_ledger": [], "product_state_ledger": [{"product_id": PRODUCT_ASSET_ID, "identity_asset_ids": [PRODUCT_ASSET_ID], "geometry_material_state": f"source-bound product state {shot_uid}", "label_facing_state": "source-bound", "orientation_placement": "approved", "hand_contact": "none", "mechanism_state": "closed", "visible_contents_state": "source-bound material state", "continuity_in": "approved", "continuity_out": "approved"}],
            "material_control_required": True, "material_control_reason": "oil and glass state must remain explicit", "material_anchor_keyframe_ids": [keyframe["artifact_id"]],
            "material_state_trajectory": [{"material_id": "SOURCE_MATERIAL", "source_asset_id": PRODUCT_ASSET_ID, "states": [{"state_id": f"MAT_{shot_uid}", "time_anchor": {"source": "v1_timing_animatic", "timecode_seconds": 0.0, "relative_state": "primary_control_state"}, "fill_level": "source-bound", "viscosity_flow": "source-bound viscosity", "droplet_stream_meniscus": "source-bound", "wetting_footprint": "none", "reflection_refraction": "source-bound refraction", "surface_highlight_state": "approved"}], "forbidden_inventions": ["unapproved material state"]}],
            "dynamic_state_ladder": [{"state_id": f"STATE_{shot_uid}", "order": 1, "time_anchor": {"source": "v1_timing_animatic", "timecode_seconds": 0.0, "relative_state": "primary_control_state"}, "subject_pose_state": "approved", "object_material_state": f"source-bound product state {shot_uid}", "camera_blocking_state": "approved", "transition_intent": "hold"}],
            "continuity_in": "approved", "continuity_out": "approved",
        })
    keyframe_pack = envelope("KEYFRAME_PACK", "ai-video-keyframe-continuity-pack", SHOTS, [dependency(shot), dependency(look), dependency(storyboard), dependency(v1_media)], status="user_approved")
    keyframe_pack.update({"schema_version": "ai-video-keyframe-continuity-pack.v1", "manifest_role": "core_keyframe_authority_before_generation_unit_preflight", "project_id": "PROJECT_FIXTURE", "package_id": "KEYFRAME_PACK", "package_status": "packaged", "assistant_qa_status": "passed", "production_approval_status": "user_granted", "forbidden_video_generation_modes": ["text_to_video", "first_last_frame", "standalone_single_image_to_video"], "timing_source": {"mode": "v1_timing_animatic", **dependency(v1_media)}, "authority_inventory": [
        {**dependency(shot), "locator": shot_rel, "file_sha256": shot_file_hash, "authority_type": "shot_contract", "approval_status": shot["approval_status"], "affected_shot_uids": SHOTS},
        {**dependency(storyboard), "locator": storyboard_rel, "file_sha256": storyboard_file_hash, "authority_type": "storyboard", "approval_status": storyboard["approval_status"], "affected_shot_uids": SHOTS},
        {**dependency(look), "locator": look_rel, "file_sha256": look_file_hash, "authority_type": "global_look", "approval_status": look["approval_status"], "affected_shot_uids": SHOTS},
        {**dependency(v1_media), "locator": v1_path, "file_sha256": v1_file_hash, "authority_type": "timing_animatic_v1", "approval_status": v1_media["approval_status"], "affected_shot_uids": SHOTS},
    ], "scripted_shot_uids": SHOTS, "shot_records": keyframe_records, "inferred_execution_decisions": [], "upstream_change_requests": [], "qa_report_path": "04_reports/QA_REPORT.md", "invalidation_report_path": "04_reports/INVALIDATION_REPORT.md"})
    keyframe_rel, keyframe_file_hash = write_original_json(project_root, keyframe_pack)
    artifacts[keyframe_pack["artifact_id"]] = keyframe_pack
    entries.append(make_entry(keyframe_pack, "keyframe_continuity_manifest", "KEYFRAME_CONTINUITY_MANIFEST", keyframe_rel, keyframe_file_hash))

    pre_manifest = make_manifest(entries, "1.0.0", "keyframes", "ai-video-keyframe-continuity-pack", None, 1)
    write_json(root / validator.PREFLIGHT_SNAPSHOT, pre_manifest)
    pre_receipt = manifest_receipt(validator.PREFLIGHT_SNAPSHOT, pre_manifest, root)

    plan_deps = [dependency(artifacts[entry["artifact_id"]]) for entry in entries]
    artifact_decisions = []
    for entry in entries:
        control_roles, primary_control_role = control_roles_for(entry["artifact_type"])
        is_atlas_source = entry["artifact_type"] in ATLAS_SOURCE_ARTIFACT_TYPES
        is_packaging_direct = entry["owner_skill"] == "packaging-product-identity-label-lock-board"
        controlled_shots = [uid for uid in entry["affected_shot_uids"] if uid in SHOTS]
        if entry["artifact_slot"] in validator.PREFLIGHT_REQUIRED_GLOBAL_SLOTS:
            controlled_shots = list(SHOTS)
        decision = "selected_direct" if is_packaging_direct else ("transported_via_atlas_planned" if is_atlas_source else "inline_text")
        artifact_decisions.append({
            "artifact": dependency(artifacts[entry["artifact_id"]]),
            "artifact_slot": entry["artifact_slot"],
            "artifact_type": entry["artifact_type"],
            "control_roles": control_roles,
            "control_role": primary_control_role,
            "decision": decision,
            "transport_modality": "image" if (is_atlas_source or is_packaging_direct) else "text",
            "transport_group_id": "ATLAS_PLAN_GU001" if is_atlas_source else None,
            "controlled_shot_uids": controlled_shots,
            "reason": (
                "Bind exact-copy-verified packaging evidence directly at full source resolution."
                if is_packaging_direct else "Transport this approved independent still through the deterministic unit atlas."
                if is_atlas_source else
                "Consume this approved authority as exact structured prompt/preflight context."
            ),
        })
    planned_atlas_source_ids = [
        decision["artifact"]["artifact_id"] for decision in artifact_decisions
        if decision["decision"] == "transported_via_atlas_planned"
    ]
    decision_by_artifact_id = {
        decision["artifact"]["artifact_id"]: decision for decision in artifact_decisions
    }
    entry_by_artifact_id = {entry["artifact_id"]: entry for entry in entries}
    preflight_atlas_spec = {
        "schema_version": "ai-video-deterministic-atlas-spec.v2",
        "atlas_id": "ATLAS_GU001", "generation_unit_id": "GU001",
        "layout_columns": 4, "background_rgb": [0, 0, 0],
        "minimum_panel_width_pixels": 256, "minimum_panel_height_pixels": 256,
        "legibility_policy": "identity_geometry_look_only_no_microcopy",
        "source_decode_policy": "pillow_common_raster_to_rgb8_no_resize_v1",
        "output_encode_policy": "pillow_png_rgb8_fixed_v1",
        "layout_policy": "max_native_cell_center_floor_no_resize_v1", "output_codec": "PNG_RGB8",
        "sources": [{
            "artifact_id": artifact_id,
            "file_path": entry_by_artifact_id[artifact_id]["locator"],
            "file_sha256": entry_by_artifact_id[artifact_id]["file_sha256"],
            "control_roles": decision_by_artifact_id[artifact_id]["control_roles"],
            "control_role": decision_by_artifact_id[artifact_id]["control_role"],
        } for artifact_id in planned_atlas_source_ids],
    }
    preflight_atlas_bytes, preflight_atlas_receipt = validator.build_from_spec(
        project_root, preflight_atlas_spec
    )
    planned_atlas_groups = [{
        "transport_group_id": "ATLAS_PLAN_GU001", "planned_atlas_id": "ATLAS_GU001",
        "source_artifact_ids": planned_atlas_source_ids,
        "layout_columns": 4, "background_rgb": [0, 0, 0],
        "minimum_panel_width_pixels": 256, "minimum_panel_height_pixels": 256,
        "legibility_policy": "identity_geometry_look_only_no_microcopy",
        "source_decode_policy": "pillow_common_raster_to_rgb8_no_resize_v1",
        "output_encode_policy": "pillow_png_rgb8_fixed_v1",
        "layout_policy": "max_native_cell_center_floor_no_resize_v1", "output_codec": "PNG_RGB8",
        "preflight_build": {
            "file_sha256": hashlib.sha256(preflight_atlas_bytes).hexdigest(),
            "file_bytes": len(preflight_atlas_bytes),
            "width": preflight_atlas_receipt["width"], "height": preflight_atlas_receipt["height"],
            "codec": preflight_atlas_receipt["codec"], "media_type": preflight_atlas_receipt["media_type"],
            "decoder_runtime": preflight_atlas_receipt["decoder_runtime"],
            "encoder_runtime": preflight_atlas_receipt["encoder_runtime"],
        },
    }]
    plan = envelope("PREFLIGHT_PLAN", validator.OWNER, SHOTS, plan_deps, status="user_approved")
    plan.update({
        "schema_version": "ai-video-generation-unit-preflight.v1",
        "project_id": "PROJECT_FIXTURE",
        "plan_status": "ready_for_boundary_supplement",
        "generation_mode": "omni_reference_to_video",
        "project_canon_read_receipt": pre_receipt,
        "target_profile_id": "seedance_2_5_forward_compatible",
        "documented_backend_profile_id": "seedance_2_0_documented_omni",
        "provider_profile_id": "vendor_seedance_2_0_api",
        "generation_unit_boundary_policy": "whole_shot_uids_only",
        "ordered_shot_uids": SHOTS,
        "generation_units": [{
            "generation_unit_id": "GU001", "ordered_shot_uids": SHOTS,
            "target_duration_seconds": 15.0, "timing_sensitive": True,
            "control_previs_requirement": "required", "required_modalities": ["text", "image", "video"],
            "planned_reference_counts": {"image": 2, "video": 1, "audio": 0, "total_multimodal": 3},
            "planned_reference_artifact_ids": [entry["artifact_id"] for entry in entries],
            "artifact_decisions": artifact_decisions,
            "planned_atlas_groups": planned_atlas_groups,
            "planned_future_inputs": [{
                "planned_input_id": "BOUNDARY_SUPPLEMENT:GU001",
                "producer_skill": "ai-video-keyframe-continuity-pack",
                "control_role": "keyframe_boundary_supplement",
                "transport_modality": "text",
                "controlled_shot_uids": SHOTS,
                "reason": "The exact P1 unit map requires one K2 boundary authority, including single-unit exemption.",
            }, {
                "planned_input_id": "CONTROL_PREVIS_V2:GU001",
                "producer_skill": "ai-video-timed-animatic-previs-director",
                "control_role": "control_previs_v2",
                "transport_modality": "video",
                "controlled_shot_uids": SHOTS,
                "reason": "The multi-shot timing-sensitive unit requires one provider-bound V2 control reference.",
            }],
            "split_reason": "one 15-second unit preserves the approved six-shot rhythm",
            "continuity_boundary_in": "project start", "continuity_boundary_out": "project end",
            "preflight_status": "ready",
        }],
        "reference_budget_decisions": ["transport approved still evidence through one deterministic atlas"],
        "blocked_reasons": [],
    })
    finalize(plan)
    write_json(root / validator.PREFLIGHT_PLAN, plan)
    artifacts[plan["artifact_id"]] = plan

    k2 = envelope("BOUNDARY_SUPPLEMENT", "ai-video-keyframe-continuity-pack", SHOTS, [dependency(keyframe_pack), dependency(plan)], status="user_approved")
    k2.update({"schema_version": "ai-video-keyframe-boundary-supplement.v1", "project_id": "PROJECT_FIXTURE", "core_keyframe_manifest": dependency(keyframe_pack), "prompt_preflight": dependency(plan), "scripted_shot_uids": SHOTS, "generation_units": [{"generation_unit_id": "GU001", "ordered_shot_uids": SHOTS}], "supplemental_keyframes": [], "cross_generation_unit_boundaries": [], "exemption": "single_generation_unit"})
    k2_rel, k2_file_hash = write_original_json(project_root, k2)
    artifacts[k2["artifact_id"]] = k2
    v2 = envelope("CONTROL_PREVIS_GU001", "ai-video-timed-animatic-previs-director", SHOTS, [dependency(v1_media), dependency(keyframe_pack), dependency(k2), dependency(plan)], status="user_approved")
    v2_rel, v2_file_hash, v2_probe = make_control_video(project_root, v2["artifact_id"])
    v2_probe["shot_chapters"] = fixture_media_probe(timeline, 15.0)["shot_chapters"]
    v2.update({"phase": "control_previs_v2", "generation_unit_id": "GU001", "shot_uids": SHOTS, "target_duration_seconds": 15.0, "provider_max_duration_seconds": 15.0, "multimodal_reference_video_supported": True, "local_timeline": timeline, "file_path": v2_rel, "file_sha256": v2_file_hash, "actual_duration_seconds": 15.0, "media_probe": v2_probe, "model_input_role": "control_reference_video", "is_model_input": True, "final_edit_asset": False, "silent": True, "render_style": "neutral_2d_blocking", "identity_authority": False, "look_authority": False, "control_dimensions": ["shot timing", "camera path", "blocking"], "forbidden_dimensions": ["identity", "look"], "motion_track_ids": []})
    finalize(v2)
    v2_record_rel, v2_record_digest = write_artifact_record(project_root, v2)
    artifacts[v2["artifact_id"]] = v2
    v2_manifest = envelope("PREVIS_MANIFEST_V2", "ai-video-timed-animatic-previs-director", SHOTS, [dependency(v1_media), dependency(keyframe_pack), dependency(k2), dependency(plan)], status="user_approved")
    v2_manifest.update({"schema_version": "ai-video-timed-animatic-previs.v1", "project_id": "PROJECT_FIXTURE", "package_status": "user_approved", "delivery_stage": "control_previs_v2", "execution_mode": "active", "shot_count": len(SHOTS), "total_duration_seconds": 15.0, "source_authorities": {"shot_contract": external_authority(shot, shot_rel, shot_file_hash), "storyboard": external_authority(storyboard, storyboard_rel, storyboard_file_hash), "keyframe_pack": external_authority(keyframe_pack, keyframe_rel, keyframe_file_hash), "keyframe_boundary_supplement": external_authority(k2, k2_rel, k2_file_hash), "provider_preflight": external_authority(plan, canon_locator(validator.PREFLIGHT_PLAN), file_hash(root / validator.PREFLIGHT_PLAN)), "provider_capability": external_authority(provider_doc, canon_locator(validator.PROVIDER_CAPS), file_hash(root / validator.PROVIDER_CAPS))}, "input_file_evidence": [], "skip_record": None, "timing_animatic_v1": v1_media, "control_previs_v2_units": [v2], "motion_physics_tracks": [], "generation_modes_used": ["neutral_2d_blocking"], "forbidden_generation_modes": ["text_to_video", "first_last_frame", "standalone_single_image_to_video"], "downstream_invalidations": []})
    v2_manifest_rel, v2_manifest_file_hash = write_original_json(project_root, v2_manifest)
    artifacts[v2_manifest["artifact_id"]] = v2_manifest

    image_source_ids = [
        entry["artifact_id"] for entry in entries
        if entry["artifact_type"] in ATLAS_SOURCE_ARTIFACT_TYPES
    ]
    atlas = envelope("ATLAS_GU001", validator.OWNER, SHOTS, [dependency(artifacts[item]) for item in image_source_ids], status="user_approved")
    source_entries = {entry["artifact_id"]: entry for entry in entries}
    atlas_spec_rel = "sources/ATLAS_GU001.spec.json"
    atlas_spec = copy.deepcopy(preflight_atlas_spec)
    write_json(project_root / atlas_spec_rel, atlas_spec)
    atlas_bytes, atlas_receipt = validator.build_from_spec(project_root, atlas_spec)
    atlas_rel = "sources/ATLAS_GU001.png"
    (project_root / atlas_rel).write_bytes(atlas_bytes)
    atlas_file_hash = file_hash(project_root / atlas_rel)
    atlas_receipt_rel = "sources/ATLAS_GU001.receipt.json"
    write_json(project_root / atlas_receipt_rel, atlas_receipt)
    atlas.update({
        "schema_version": "ai-video-deterministic-atlas-artifact.v1", "generation_unit_id": "GU001",
        "source_artifact_ids": image_source_ids, "composition_spec_path": atlas_spec_rel,
        "composition_spec_file_sha256": file_hash(project_root / atlas_spec_rel),
        "composition_receipt_path": atlas_receipt_rel,
        "composition_receipt_file_sha256": file_hash(project_root / atlas_receipt_rel),
        "file_path": atlas_rel, "file_sha256": atlas_file_hash, "file_bytes": len(atlas_bytes),
        "codec": atlas_receipt["codec"],
        "media_type": atlas_receipt["media_type"],
        "width": atlas_receipt["width"], "height": atlas_receipt["height"],
        "minimum_panel_width_pixels": atlas_receipt["minimum_panel_width_pixels"],
        "minimum_panel_height_pixels": atlas_receipt["minimum_panel_height_pixels"],
        "legibility_policy": atlas_receipt["legibility_policy"],
        "layout_policy": atlas_receipt["layout_policy"],
        "decoder_runtime": atlas_receipt["decoder_runtime"],
        "encoder_runtime": atlas_receipt["encoder_runtime"],
        "deterministic_composition": True, "generative_recomposition": False,
    })
    finalize(atlas)
    atlas_record_package_rel = f"owned_artifacts/{atlas['artifact_id']}.json"
    write_json(root / atlas_record_package_rel, atlas)
    atlas_record_rel = canon_locator(atlas_record_package_rel)
    atlas_record_digest = file_hash(root / atlas_record_package_rel)
    artifacts[atlas["artifact_id"]] = atlas

    v1_manifest_entry = next(item for item in entries if item["artifact_slot"] == "previs_manifest")
    compile_entries = [copy.deepcopy(item) for item in entries if item["artifact_slot"] != "previs_manifest"]
    compile_entries.extend([
        make_entry(plan, "generation_unit_preflight_plan", "GENERATION_UNIT_PREFLIGHT_PLAN", canon_locator(validator.PREFLIGHT_PLAN), file_hash(root / validator.PREFLIGHT_PLAN)),
        make_entry(k2, "keyframe_boundary_supplement", "KEYFRAME_BOUNDARY_SUPPLEMENT", k2_rel, k2_file_hash),
        make_entry(v2_manifest, "previs_manifest", "PREVIS_MANIFEST", v2_manifest_rel, v2_manifest_file_hash),
        make_entry(v2, "control_previs_v2:GU001", "CONTROL_PREVIS_V2", v2_rel, v2_file_hash, v2_record_rel, v2_record_digest),
        make_entry(atlas, "transport_atlas:GU001", "DETERMINISTIC_REFERENCE_ATLAS", atlas_rel, atlas_file_hash, atlas_record_rel, atlas_record_digest),
    ])
    compile_manifest = make_manifest(compile_entries, "1.1.0", "control_previs_v2", "ai-video-timed-animatic-previs-director", pre_manifest["sha256"], 2)
    compile_manifest["superseded_artifacts"] = [{
        **v1_manifest_entry, "approval_status": "stale", "stale_reason": "previs_manifest advanced to the V2 package root",
        "eligible_for_downstream": False, "superseded_by_artifact_id": v2_manifest["artifact_id"],
    }]
    finalize(compile_manifest)
    write_json(root / validator.COMPILE_SNAPSHOT, compile_manifest)
    compile_receipt = manifest_receipt(validator.COMPILE_SNAPSHOT, compile_manifest, root)

    inventory = []
    for entry in compile_entries:
        artifact = artifacts[entry["artifact_id"]]
        control_roles, primary_control_role = control_roles_for(entry["artifact_type"])
        if artifact.get("owner_skill") in validator.REGISTERED_ASSET_OWNERS:
            control_roles = list(artifact["control_roles_authorized"])
        elif entry["artifact_type"] == "CONTROL_PREVIS_V2":
            control_roles, primary_control_role = ["control_previs", "camera_path", "blocking", "physical_motion"], "control_previs"
        elif entry["artifact_type"] == "DETERMINISTIC_REFERENCE_ATLAS":
            control_roles, primary_control_role = [
                "identity", "wardrobe", "product_geometry", "material_behavior", "scene_canon",
                "global_look", "storyboard", "keyframe_state",
            ], "keyframe_state"
        elif entry["artifact_type"] == "KEYFRAME_BOUNDARY_SUPPLEMENT":
            control_roles, primary_control_role = ["keyframe_boundary"], "keyframe_boundary"
        inventory.append({
            "artifact": {
                "contract_version": "ai-video-artifact-v1",
                "artifact_id": entry["artifact_id"], "owner_skill": entry["owner_skill"],
                "version": entry["version"], "sha256": entry["sha256"],
                "approval_status": entry["approval_status"], "dependencies": entry["dependencies"],
                "affected_shot_uids": entry["affected_shot_uids"], "stale_reason": entry["stale_reason"],
            },
            "artifact_slot": entry["artifact_slot"], "artifact_type": entry["artifact_type"],
            "control_roles": control_roles, "control_role": primary_control_role,
            "approval_status": entry["approval_status"], "eligible_for_downstream": entry["eligible_for_downstream"],
            "file_path": entry["locator"], "file_sha256": entry["file_sha256"],
            "artifact_record_locator": entry["artifact_record_locator"],
            "artifact_record_file_sha256": entry["artifact_record_file_sha256"],
        })

    shot_records, projected_claim_boundary = validator.shot_contract_projection(shot)
    assert projected_claim_boundary == claim_boundary
    keyframe_record_by_uid = {item["shot_uid"]: item for item in keyframe_records}
    for shot_record in shot_records:
        shot_uid = shot_record["shot_uid"]
        keyframe_record = keyframe_record_by_uid[shot_uid]
        shot_record.update({
            "product_material_change": validator.compact_semantic_json({
                "product_state_ledger": keyframe_record["product_state_ledger"],
                "material_state_trajectory": keyframe_record["material_state_trajectory"],
                "dynamic_state_ladder": keyframe_record["dynamic_state_ladder"],
            }),
            "look_state_id": "LOOK_STATE_FIELD", "look_state_prompt_full": STATE,
            "look_state_reference_asset_ids": [LOOK_ASSET_ID],
            "shot_look_delta": {**copy.deepcopy(base_delta), "prompt_full": DELTA},
            "storyboard_artifact_id": f"SB_{shot_uid}", "storyboard_stage": "look_applied_final",
            "storyboard_model_input_eligible": True, "keyframe_artifact_ids": [f"KF_{shot_uid}"],
            "control_previs_artifact_id": v2["artifact_id"],
            "required_control_artifact_ids": [LOOK_ASSET_ID, CHARACTER_ASSET_ID, PRODUCT_ASSET_ID, PACKAGING_ASSET_ID, SCENE_ASSET_ID, f"SB_{shot_uid}", f"KF_{shot_uid}", v2["artifact_id"]],
        })

    all_refs = [dependency(artifacts[entry["artifact_id"]]) for entry in compile_entries]
    ir = envelope("FINAL_IR", validator.OWNER, SHOTS, all_refs, status="assistant_validated")
    ir.update({
        "schema_version": "ai-video-canonical-ir.v2", "ir_stage": "final_compile", "package_mode": "compile",
        "project_id": "PROJECT_FIXTURE", "package_id": "PROMPT_PACKAGE", "package_status": "compiled",
        "generation_mode": "omni_reference_to_video", "generation_unit_boundary_policy": "whole_shot_uids_only",
        "revision_anchor": None, "project_canon_read_receipt": compile_receipt,
        "preflight_plan_ref": dependency(plan), "boundary_supplement_ref": dependency(k2),
        "target_profile_id": "seedance_2_5_forward_compatible",
        "compatible_backend_profile_ids": ["seedance_2_0_documented_omni"],
        "source_artifact_inventory": inventory, "global_directing_prompt_full": GRAMMAR,
        "global_look": {"artifact_id": look["artifact_id"], "exact_prompt_block": LOOK, "reference_asset_ids": [LOOK_ASSET_ID], "look_state_matrix_id": "LOOK_STATE_MATRIX_FIXTURE_V1"},
        "ordered_shot_uids": SHOTS, "shots": shot_records,
        "generation_units": [{
            "generation_unit_id": "GU001", "ordered_shot_uids": SHOTS, "target_duration_seconds": 15.0,
            "continuity_boundary_in": "project start", "continuity_boundary_out": "project end",
            "timing_sensitive": True, "control_previs_requirement": "required",
            "control_previs_artifact_id": v2["artifact_id"], "boundary_supplement_artifact_id": k2["artifact_id"],
            "required_modalities": ["text", "image", "video"], "preflight_status": "ready",
        }],
        "claim_boundary": claim_boundary,
        "forbidden_fallbacks": ["text_only_generation", "endpoint_frame_generation"],
        "inferred_prompt_decisions": [], "upstream_change_requests": [],
    })
    finalize(ir)
    write_json(root / validator.IR_PATH, ir)

    image_ids = set(image_source_ids)
    preflight_decision_by_id = {
        decision["artifact"]["artifact_id"]: decision
        for decision in artifact_decisions
    }
    decision_to_binding_status = {
        "selected_direct": "relevant_selected",
        "transported_via_atlas_planned": "transported_via_atlas",
        "inline_text": "relevant_selected",
        "irrelevant": "irrelevant_to_unit",
        "conflict_blocked": "conflicting_blocked",
        "superseded": "superseded_version",
    }
    binding_inventory = []
    selected_ids: list[str] = []
    priority = 1
    for item in inventory:
        artifact_id = item["artifact"]["artifact_id"]
        slot = item["artifact_slot"]
        artifact_type = item["artifact_type"]
        modality = "text"
        role = "provider_preflight"
        scope = "project"
        controlled: list[str] = []
        stage: str | None = None
        eligible: bool | None = None
        status = "irrelevant_to_unit"
        reason = "read and classified; not a provider input for this unit"
        if artifact_id == PACKAGING_ASSET_ID:
            modality, role, controlled = "image", "label_copy", SHOTS
            status, reason = "relevant_selected", "exact-copy-verified packaging evidence remains a direct full-resolution binding"
        elif artifact_id in image_ids:
            modality = "image"
            if artifact_type == "STORYBOARD_FRAME_LOOK_APPLIED_FINAL":
                role, scope, controlled, stage, eligible = "storyboard", "shot", item["artifact"]["affected_shot_uids"], "look_applied_final", True
            elif artifact_type == "KEYFRAME_ANCHOR":
                role, scope, controlled = "keyframe_state", "shot", item["artifact"]["affected_shot_uids"]
            elif artifact_type == "GLOBAL_LOOK_REFERENCE":
                role = "global_look"
            elif artifact_type in {"CHARACTER_ASSET", "CHARACTER_FINAL_LOCK_BOARD_ASSET"}:
                role = "identity"
            elif artifact_type in {"PRODUCT_ASSET", "MATERIAL_SENSITIVE_PRODUCT_ASSET"}:
                role = "product_geometry"
            else:
                role = "scene_canon"
            status, reason = "transported_via_atlas", "source pixels transported through deterministic ATLAS_GU001"
        elif artifact_id == atlas["artifact_id"]:
            modality, role, controlled, status, reason = "image", "keyframe_state", SHOTS, "relevant_selected", "deterministic atlas transports approved still evidence"
        elif artifact_id == v2["artifact_id"]:
            modality, role, scope, controlled, status, reason = "video", "control_previs", "generation_unit", SHOTS, "relevant_selected", "required V2 motion control"
        elif slot == "professional_shot_contract":
            role, status, reason = "shot_contract", "relevant_selected", "inline canonical shot facts"
        elif slot == "global_look_contract":
            role, status, reason = "global_look", "relevant_selected", "inline global look authority"
        elif slot == "storyboard_manifest":
            role, status, reason, stage, eligible = "storyboard", "relevant_selected", "inline storyboard mapping", "look_applied_final", True
        elif slot == "keyframe_continuity_manifest":
            role, status, reason = "keyframe_state", "relevant_selected", "inline keyframe continuity ledger"
        elif slot == "previs_manifest":
            role, controlled, status, reason = "timing_map", SHOTS, "relevant_selected", "V2 package root supersedes and preserves the P1 V1 timing authority"
        elif slot == "generation_unit_preflight_plan":
            role, status, reason = "provider_preflight", "relevant_selected", "approved Generation Unit Plan"
        elif slot == "keyframe_boundary_supplement":
            role, status, reason = "keyframe_boundary", "relevant_selected", "approved cross-unit handoff"
        elif slot == "timing_animatic_v1":
            modality, role = "video", "timing_map"
        preflight_decision = preflight_decision_by_id.get(artifact_id)
        if preflight_decision is not None:
            status = decision_to_binding_status[preflight_decision["decision"]]
            modality = preflight_decision["transport_modality"]
            controlled = preflight_decision["controlled_shot_uids"]
        planned_future_input_id = None
        if artifact_id == k2["artifact_id"]:
            planned_future_input_id = "BOUNDARY_SUPPLEMENT:GU001"
            controlled = SHOTS
        elif artifact_id == v2["artifact_id"]:
            planned_future_input_id = "CONTROL_PREVIS_V2:GU001"
            controlled = SHOTS
        control_roles = [role]
        source_artifact = artifacts.get(artifact_id, {})
        if source_artifact.get("owner_skill") in validator.REGISTERED_ASSET_OWNERS:
            control_roles = list(source_artifact["control_roles_authorized"])
        elif artifact_id == atlas["artifact_id"]:
            control_roles = [
                "identity", "wardrobe", "product_geometry", "material_behavior", "scene_canon",
                "global_look", "storyboard", "keyframe_state",
            ]
        elif artifact_id == v2["artifact_id"]:
            control_roles = ["control_previs", "camera_path", "blocking", "physical_motion"]
        binding_item = {
            "artifact": {
                "artifact_id": artifact_id, "owner_skill": item["artifact"]["owner_skill"],
                "version": item["artifact"]["version"], "sha256": item["artifact"]["sha256"],
                "file_path": item["file_path"], "file_sha256": item["file_sha256"],
                "artifact_record_locator": item["artifact_record_locator"],
                "artifact_record_file_sha256": item["artifact_record_file_sha256"],
            },
            "artifact_slot": slot, "artifact_type": artifact_type,
            "approval_status": item["approval_status"], "eligible_for_downstream": item["eligible_for_downstream"],
            "modality": modality, "control_roles": control_roles, "control_role": role, "scope": scope,
            "controlled_shot_uids": controlled, "expected_influence": reason, "priority": priority,
            "storyboard_stage": stage, "storyboard_model_input_eligible": eligible,
            "unit_classification": [{
                "generation_unit_id": "GU001", "status": status,
                "controlled_shot_uids": controlled if status in {"relevant_selected", "transported_via_atlas", "conflicting_blocked"} else [],
                "preflight_planned_input_id": planned_future_input_id,
                "reason": reason,
            }],
        }
        priority += 1
        binding_inventory.append(binding_item)
        if status == "relevant_selected":
            selected_ids.append(artifact_id)

    bindings_list = []
    alias_counters = {"image": 0, "video": 0, "audio": 0}
    for index, artifact_id in enumerate(selected_ids, 1):
        source = next(item for item in binding_inventory if item["artifact"]["artifact_id"] == artifact_id)
        alias = f"INLINE:{artifact_id}"
        if source["modality"] in alias_counters:
            alias_counters[source["modality"]] += 1
            prefix = {"image": "@图片", "video": "@视频", "audio": "@音频"}[source["modality"]]
            alias = f"{prefix}{alias_counters[source['modality']]}"
        bindings_list.append({
            "binding_id": f"B{index:03d}", "artifact_id": artifact_id, "provider_alias": alias,
            "modality": source["modality"], "control_roles": source["control_roles"],
            "control_role": source["control_role"], "scope": source["scope"],
            "controlled_shot_uids": source["controlled_shot_uids"], "expected_influence": source["expected_influence"],
            "priority": source["priority"], "conflict_exclusions": [],
        })
    binding_doc = envelope("BINDINGS", validator.OWNER, SHOTS, all_refs, status="assistant_validated")
    binding_doc.update({
        "schema_version": "ai-video-binding-manifest.v2", "project_id": "PROJECT_FIXTURE", "package_id": "PROMPT_PACKAGE",
        "generation_mode": "omni_reference_to_video", "asset_inventory": binding_inventory,
        "generation_unit_bindings": [{
            "generation_unit_id": "GU001", "binding_status": "ready", "bindings": bindings_list,
            "selected_counts": {"image": 2, "video": 1, "audio": 0, "total_multimodal": 3},
        }],
        "atlas_records": [{
            "atlas_id": atlas["artifact_id"], "generation_unit_id": "GU001", "file_path": atlas_rel,
            "preflight_transport_group_id": "ATLAS_PLAN_GU001",
            "file_sha256": atlas_file_hash, "file_bytes": len(atlas_bytes),
            "source_artifact_ids": image_source_ids,
            "deterministic_composition": True, "generative_recomposition": False,
            "composition_spec_path": atlas_spec_rel, "composition_spec_file_sha256": file_hash(project_root / atlas_spec_rel),
            "composition_receipt_path": atlas_receipt_rel, "composition_receipt_file_sha256": file_hash(project_root / atlas_receipt_rel),
            "codec": atlas_receipt["codec"], "media_type": atlas_receipt["media_type"],
            "width": atlas_receipt["width"], "height": atlas_receipt["height"],
            "minimum_panel_width_pixels": atlas_receipt["minimum_panel_width_pixels"],
            "minimum_panel_height_pixels": atlas_receipt["minimum_panel_height_pixels"],
            "legibility_policy": atlas_receipt["legibility_policy"],
            "layout_policy": atlas_receipt["layout_policy"],
            "decoder_runtime": atlas_receipt["decoder_runtime"],
            "encoder_runtime": atlas_receipt["encoder_runtime"],
        }],
        "conflict_graph": [],
    })
    finalize(binding_doc)
    write_json(root / validator.BINDINGS, binding_doc)

    blocks = [rendered_block(shot_record) for shot_record in shot_records]
    bound_artifact_roles = [{
        "artifact_id": item["artifact_id"],
        "provider_alias": item["provider_alias"],
        "control_roles": item["control_roles"],
    } for item in bindings_list]
    mapping = "\n".join(
        f"{item['artifact_id']} = {item['provider_alias']}; control_roles="
        f"{json.dumps(item['control_roles'], ensure_ascii=False, separators=(',', ':'))}"
        for item in bindings_list
    )
    unit_prompt_text = (
        "[生成任务与输出规格]\nOmni reference-to-video, 15 seconds, six ordered shots.\n"
        f"[素材及控制权映射]\n{mapping}\n[主要主体]\nApproved lead and product.\n"
        "[场景与环境初始状态]\nApproved lunar glasshouse scene.\n"
        "[情绪与广告目标的可见表现]\nRestrained visible performance and product attention.\n"
        f"[全局导演语法｜原文逐字继承]\n{GRAMMAR}\n[全局影调｜原文逐字继承]\n{LOOK}\n"
        "[全局连续性与禁止项]\nPreserve every approved identity, product, material, scene, State, and claim boundary.\n"
        "[分段镜头]\n" + "\n\n".join(block["rendered_block"] for block in blocks) +
        "\n[稳定与负面约束]\nNo invented text, T2V, endpoint-frame mode, or unsupported claim."
    )
    unit_doc = envelope("UNIT_PROMPTS", validator.OWNER, SHOTS, all_refs, status="assistant_validated")
    unit_doc.update({
        "generation_mode": "omni_reference_to_video",
        "generation_unit_prompts": [{
            "generation_unit_id": "GU001", "backend_profile_id": "seedance_2_0_documented_omni",
            "generation_mode": "omni_reference_to_video", "bound_artifact_ids": selected_ids,
            "bound_artifact_roles": bound_artifact_roles,
            "shot_blocks": blocks, "prompt_text": unit_prompt_text,
        }],
    })
    finalize(unit_doc)
    write_json(root / validator.UNIT_PROMPTS, unit_doc)

    repair_items = []
    for shot_record, block in zip(shot_records, blocks):
        artifact_lines = mapping
        repair_items.append({
            "shot_uid": shot_record["shot_uid"], "generation_mode": "omni_reference_to_video",
            "bound_artifact_ids": selected_ids, "bound_artifact_roles": bound_artifact_roles,
            "shot_block": block,
            "prompt_text": (
                f"Repair {shot_record['shot_uid']} with complete bindings:\n{artifact_lines}\n{GRAMMAR}\n{LOOK}\n"
                f"{STATE}\n{DELTA}\n{block['rendered_block']}\nPreserve all other canon."
            ),
        })
    repair_doc = envelope("REPAIR_PROMPTS", validator.OWNER, SHOTS, all_refs, status="assistant_validated")
    repair_doc.update({"generation_mode": "omni_reference_to_video", "shot_repair_prompts": repair_items})
    finalize(repair_doc)
    write_json(root / validator.REPAIR_PROMPTS, repair_doc)

    for rel, text in {
        "02_prompts/PROJECT_GLOBAL_BLOCK.md": f"{GRAMMAR}\n{LOOK}\n",
        "02_prompts/SEEDANCE_2_5_MASTER_PROMPT.md": f"Forward-compatible semantic target only.\n{GRAMMAR}\n{LOOK}\n{unit_prompt_text}\n",
        "02_prompts/SEEDANCE_2_0_COMPATIBLE_RENDER.md": f"Seedance 2.0 compatible render.\n{GRAMMAR}\n{LOOK}\n{unit_prompt_text}\n",
        "04_reports/CAPACITY_DEGRADATION_REPORT.md": "2.5 preview capacity was not executable; verified Seedance 2.0 backend limits applied.\n",
        "04_reports/PROMPT_REVISION_DIFF.md": "Initial compile; no fabricated user feedback.\n",
    }.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        write_text_lf(path, text)

    payload_doc = envelope("PAYLOAD", validator.OWNER, SHOTS, all_refs, status="assistant_validated")
    payload_doc.update({
        "schema_version": "ai-video-provider-payload.v1", "generation_mode": "omni_reference_to_video",
        "payload_status": "executable", "provider_profile_id": "vendor_seedance_2_0_api",
        "documented_backend_profile_id": "seedance_2_0_documented_omni", "provider_surface": "third-party-api",
        "unit_payloads": [{
            "generation_unit_id": "GU001", "model_id": "vendor/doubao-seedance-2.0-omni",
            "generation_mode": "omni_reference_to_video", "prompt_artifact_id": unit_doc["artifact_id"],
            "binding_ids": [item["binding_id"] for item in bindings_list], "target_duration_seconds": 15.0,
            "api_parameters": {"aspect_ratio": "16:9", "duration_seconds": 15},
        }],
    })
    finalize(payload_doc)
    write_json(root / validator.PAYLOAD, payload_doc)

    feedback_doc = envelope("FEEDBACK", validator.OWNER, SHOTS, all_refs, status="assistant_validated")
    feedback_doc.update({
        "schema_version": "ai-video-feedback-route.v1", "package_mode": "compile",
        "revision_anchor": None,
        "feedback_routes": [], "upstream_change_requests": [],
        "independent_output_qc": False, "edit_action": "none", "music_action": "none",
    })
    finalize(feedback_doc)
    write_json(root / validator.FEEDBACK, feedback_doc)

    receipt = {
        "schema_version": "ai-video-manifest-update-receipt.v1",
        "canonical_manifest_locator": "00_project_canon/PROJECT_CANON_MANIFEST.json",
        "updated_by_skill": validator.OWNER,
        "delta_status": "applied",
        "base_manifest_sha256": compile_manifest["sha256"],
        "resulting_manifest_sha256": "7" * 64,
        "registered_artifact_ids": sorted([
            plan["artifact_id"], ir["artifact_id"], model_doc["artifact_id"], provider_doc["artifact_id"],
            "LOCKFILE", binding_doc["artifact_id"], unit_doc["artifact_id"], repair_doc["artifact_id"],
            payload_doc["artifact_id"], feedback_doc["artifact_id"], atlas["artifact_id"],
        ]),
    }
    write_json(root / validator.MANIFEST_RECEIPT, receipt)

    input_locks = [{
        "artifact_id": item["artifact"]["artifact_id"], "owner_skill": item["artifact"]["owner_skill"],
        "version": item["artifact"]["version"], "sha256": item["artifact"]["sha256"],
        "file_path": item["file_path"], "file_sha256": item["file_sha256"],
        "artifact_record_locator": item["artifact_record_locator"],
        "artifact_record_file_sha256": item["artifact_record_file_sha256"],
    } for item in inventory]
    output_locks = []
    for index, rel in enumerate(sorted(validator.EXPECTED_OUTPUT_LOCK_PATHS), 1):
        output_locks.append({
            "artifact_id": f"OUTPUT_{index:03d}", "version": "1.0.0", "file_path": rel,
            "file_sha256": file_hash(root / rel),
            "depends_on_artifact_ids": [item["artifact"]["artifact_id"] for item in inventory],
        })
    lockfile = envelope("LOCKFILE", validator.OWNER, SHOTS, all_refs, status="assistant_validated")
    lockfile.update({
        "schema_version": "ai-video-dependency-lockfile.v1", "project_id": "PROJECT_FIXTURE",
        "package_id": "PROMPT_PACKAGE", "input_locks": input_locks, "output_locks": output_locks,
    })
    finalize(lockfile)
    write_json(root / validator.LOCKFILE, lockfile)

    post_entries = copy.deepcopy(compile_entries)
    post_entries.extend([
        make_entry(ir, "canonical_generation_ir", "CANONICAL_VIDEO_GENERATION_IR", canon_locator(validator.IR_PATH), file_hash(root / validator.IR_PATH)),
        make_entry(lockfile, "prompt_dependency_lockfile", "PROMPT_DEPENDENCY_LOCKFILE", canon_locator(validator.LOCKFILE), file_hash(root / validator.LOCKFILE)),
        make_entry(binding_doc, "multimodal_binding_manifest", "MULTIMODAL_BINDING_MANIFEST", canon_locator(validator.BINDINGS), file_hash(root / validator.BINDINGS)),
        make_entry(unit_doc, "generation_unit_prompts", "GENERATION_UNIT_PROMPTS", canon_locator(validator.UNIT_PROMPTS), file_hash(root / validator.UNIT_PROMPTS)),
        make_entry(repair_doc, "shot_repair_prompts", "SHOT_LEVEL_REPAIR_PROMPTS", canon_locator(validator.REPAIR_PROMPTS), file_hash(root / validator.REPAIR_PROMPTS)),
        make_entry(payload_doc, "provider_payload_manifest", "PROVIDER_PAYLOAD_MANIFEST", canon_locator(validator.PAYLOAD), file_hash(root / validator.PAYLOAD)),
        make_entry(feedback_doc, "prompt_feedback_route", "PROMPT_FEEDBACK_ROUTE", canon_locator(validator.FEEDBACK), file_hash(root / validator.FEEDBACK)),
    ])
    post_manifest = make_manifest(post_entries, "1.2.0", "prompts", validator.OWNER, compile_manifest["sha256"], 3)
    write_json(project_root / validator.DEFAULT_POST_CANON, post_manifest)
    receipt["resulting_manifest_sha256"] = post_manifest["sha256"]
    write_json(root / validator.MANIFEST_RECEIPT, receipt)

    owner_schema_pairs = [
        (shot_rel, HERE.parents[1] / "ai-video-shot-script-director/references/shot_contract.schema.json"),
        (look_rel, HERE.parents[1] / "ai-video-global-look-lock/references/global_look_contract.schema.json"),
        (storyboard_rel, HERE.parents[1] / "ai-video-modular-storyboard/references/storyboard_manifest.schema.json"),
        (v1_rel, HERE.parents[1] / "ai-video-timed-animatic-previs-director/references/previs_manifest.schema.json"),
        (keyframe_rel, HERE.parents[1] / "ai-video-keyframe-continuity-pack/references/keyframe_manifest.schema.json"),
        (k2_rel, HERE.parents[1] / "ai-video-keyframe-continuity-pack/references/boundary_supplement.schema.json"),
        (v2_manifest_rel, HERE.parents[1] / "ai-video-timed-animatic-previs-director/references/previs_manifest.schema.json"),
    ]
    for source_rel, schema_path in owner_schema_pairs:
        source_value = json.loads((project_root / source_rel).read_text(encoding="utf-8"))
        owner_schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema_errors = validator.validate_instance(source_value, owner_schema, owner_schema)
        if schema_errors:
            raise AssertionError(f"owner source must satisfy {schema_path.name}: {schema_errors}")


def create_revise_package(root: Path, project_root: Path | None = None) -> None:
    project_root = project_root or root
    create_package(root, project_root)
    previous_dir = root / "previous"
    previous_dir.mkdir(parents=True, exist_ok=True)
    previous_ir_path = previous_dir / "PREVIOUS_IR.json"
    previous_lock_path = previous_dir / "PREVIOUS_DEPENDENCY_LOCKFILE.json"
    shutil.copy2(root / validator.IR_PATH, previous_ir_path)
    shutil.copy2(root / validator.LOCKFILE, previous_lock_path)
    previous_ir = json.loads(previous_ir_path.read_text(encoding="utf-8"))
    previous_lock = json.loads(previous_lock_path.read_text(encoding="utf-8"))
    previous_outputs = {
        item["file_path"]: item["file_sha256"] for item in previous_lock["output_locks"]
    }
    changed = {validator.IR_PATH, validator.FEEDBACK, validator.REPAIR_PROMPTS, "04_reports/PROMPT_REVISION_DIFF.md"}
    unchanged = validator.EXPECTED_OUTPUT_LOCK_PATHS - changed
    diff_path = root / "04_reports/PROMPT_REVISION_DIFF.md"
    write_text_lf(
        diff_path,
        "Revision R1: user requested a prompt-owned emphasis in S005; no upstream canon changed.\n",
    )
    anchor = {
        "previous_package_ref": dependency(previous_ir),
        "previous_ir_path": "previous/PREVIOUS_IR.json", "previous_ir_file_sha256": file_hash(previous_ir_path),
        "previous_lockfile_path": "previous/PREVIOUS_DEPENDENCY_LOCKFILE.json",
        "previous_lockfile_file_sha256": file_hash(previous_lock_path),
        "revision_diff_path": "04_reports/PROMPT_REVISION_DIFF.md", "revision_diff_file_sha256": file_hash(diff_path),
        "changed_output_paths": sorted(changed), "unchanged_output_paths": sorted(unchanged),
    }

    ir_path = root / validator.IR_PATH
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    ir.update({"version": "1.0.1", "ir_stage": "revision_compile", "package_mode": "revise", "revision_anchor": anchor})
    finalize(ir)
    write_json(ir_path, ir)

    repair_path = root / validator.REPAIR_PROMPTS
    repair = json.loads(repair_path.read_text(encoding="utf-8"))
    repair["version"] = "1.0.1"
    repair["shot_repair_prompts"][4]["prompt_text"] += "\nPrompt-owned revision: hold the approved emphasis one beat longer without changing timing."
    finalize(repair)
    write_json(repair_path, repair)

    feedback_path = root / validator.FEEDBACK
    feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
    feedback.update({
        "version": "1.0.1", "package_mode": "revise", "revision_anchor": anchor,
        "feedback_routes": [{
            "feedback_id": "FB_R1", "user_feedback": "S005 product emphasis is too weak",
            "affected_shot_uids": ["S005"], "diagnosis_scope": "prompt_binding_or_serialization",
            "affected_artifact_ids": [],
            "affected_control_roles": [],
            "evidence_comparison": ["canon timing and camera remain correct; prompt emphasis alone differs"],
            "owner_skill": validator.OWNER, "action": "revise_prompt_owned_surface",
            "owned_diff": {"path": validator.REPAIR_PROMPTS, "change": "one-beat semantic emphasis"},
            "upstream_change_request": None, "invalidated_artifact_ids": [],
            "unaffected_artifact_hashes": {path: previous_outputs[path] for path in sorted(unchanged)},
        }],
    })
    finalize(feedback)
    write_json(feedback_path, feedback)

    lock_path = root / validator.LOCKFILE
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    current_hashes = {path: file_hash(root / path) for path in validator.EXPECTED_OUTPUT_LOCK_PATHS}
    for output in lock["output_locks"]:
        output["file_sha256"] = current_hashes[output["file_path"]]
    lock["version"] = "1.0.1"
    finalize(lock)
    write_json(lock_path, lock)

    changed_docs = {
        ir["artifact_id"]: (ir, validator.IR_PATH),
        repair["artifact_id"]: (repair, validator.REPAIR_PROMPTS),
        feedback["artifact_id"]: (feedback, validator.FEEDBACK),
        lock["artifact_id"]: (lock, validator.LOCKFILE),
    }
    post_path = project_root / validator.DEFAULT_POST_CANON
    post = json.loads(post_path.read_text(encoding="utf-8"))
    for entry in post["active_artifacts"]:
        replacement = changed_docs.get(entry["artifact_id"])
        if replacement is None:
            continue
        document, rel = replacement
        entry.update({
            "version": document["version"], "sha256": document["sha256"],
            "approval_status": document["approval_status"], "stale_reason": document["stale_reason"],
            "affected_shot_uids": document["affected_shot_uids"], "dependencies": document["dependencies"],
            "locator": (root / rel).resolve().relative_to(project_root.resolve()).as_posix(),
            "file_sha256": file_hash(root / rel), "eligible_for_downstream": True,
            "artifact_record_locator": (root / rel).resolve().relative_to(project_root.resolve()).as_posix(),
            "artifact_record_file_sha256": file_hash(root / rel),
        })
    post["dependency_edges"] = [{
        "producer_artifact_id": dep["artifact_id"], "consumer_artifact_id": entry["artifact_id"],
        "producer_sha256": dep["sha256"], "affected_shot_uids": entry["affected_shot_uids"],
    } for entry in post["active_artifacts"] for dep in entry["dependencies"]]
    finalize(post)
    write_json(post_path, post)
    receipt_path = root / validator.MANIFEST_RECEIPT
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["resulting_manifest_sha256"] = post["sha256"]
    write_json(receipt_path, receipt)


def mutate_json(root: Path, rel: str, mutate: Callable[[dict[str, Any]], None]) -> None:
    path = root / rel
    value = json.loads(path.read_text(encoding="utf-8"))
    mutate(value)
    finalize(value)
    write_json(path, value)


def sync_revised_output_to_lock_and_post(root: Path, rel: str) -> None:
    """Reseal a revised output through its lock, actual post Canon, and receipt."""
    document = json.loads((root / rel).read_text(encoding="utf-8"))
    lock_path = root / validator.LOCKFILE
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    output = next(item for item in lock["output_locks"] if item["file_path"] == rel)
    output["file_sha256"] = file_hash(root / rel)
    finalize(lock)
    write_json(lock_path, lock)

    post_path = root.parent / validator.DEFAULT_POST_CANON
    post = json.loads(post_path.read_text(encoding="utf-8"))
    for value, value_rel in ((document, rel), (lock, validator.LOCKFILE)):
        entry = next(item for item in post["active_artifacts"] if item["artifact_id"] == value["artifact_id"])
        digest = file_hash(root / value_rel)
        entry.update({
            "version": value["version"], "sha256": value["sha256"],
            "approval_status": value["approval_status"], "stale_reason": value["stale_reason"],
            "affected_shot_uids": value["affected_shot_uids"], "dependencies": value["dependencies"],
            "file_sha256": digest, "artifact_record_file_sha256": digest,
        })
    post["dependency_edges"] = [{
        "producer_artifact_id": dep["artifact_id"], "consumer_artifact_id": entry["artifact_id"],
        "producer_sha256": dep["sha256"], "affected_shot_uids": entry["affected_shot_uids"],
    } for entry in post["active_artifacts"] for dep in entry["dependencies"]]
    finalize(post)
    write_json(post_path, post)
    receipt_path = root / validator.MANIFEST_RECEIPT
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["resulting_manifest_sha256"] = post["sha256"]
    write_json(receipt_path, receipt)


def reseal_actual_post(root: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    post_path = root.parent / validator.DEFAULT_POST_CANON
    post = json.loads(post_path.read_text(encoding="utf-8"))
    mutate(post)
    finalize(post)
    write_json(post_path, post)
    receipt_path = root / validator.MANIFEST_RECEIPT
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["resulting_manifest_sha256"] = post["sha256"]
    write_json(receipt_path, receipt)


def retarget_compile_locator(
    root: Path,
    artifact_id: str,
    rel: str,
    digest: str,
    mutate_ir: Callable[[dict[str, Any]], None] | None = None,
    replacement_artifact: dict[str, Any] | None = None,
) -> None:
    compile_path = root / validator.COMPILE_SNAPSHOT
    compile_manifest = json.loads(compile_path.read_text(encoding="utf-8"))
    entry = next(item for item in compile_manifest["active_artifacts"] if item["artifact_id"] == artifact_id)
    entry.update({"locator": rel, "file_sha256": digest, "artifact_record_locator": rel, "artifact_record_file_sha256": digest})
    if replacement_artifact is not None:
        for field in ("owner_skill", "version", "sha256", "approval_status", "stale_reason", "affected_shot_uids", "dependencies"):
            entry[field] = replacement_artifact[field]
    finalize(compile_manifest)
    write_json(compile_path, compile_manifest)
    ir_path = root / validator.IR_PATH
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    item = next(value for value in ir["source_artifact_inventory"] if value["artifact"]["artifact_id"] == artifact_id)
    item.update({"file_path": rel, "file_sha256": digest, "artifact_record_locator": rel, "artifact_record_file_sha256": digest})
    if replacement_artifact is not None:
        item["artifact"] = {field: replacement_artifact[field] for field in (
            "contract_version", "artifact_id", "owner_skill", "version", "sha256", "approval_status",
            "dependencies", "affected_shot_uids", "stale_reason",
        )}
        for dep in ir["dependencies"]:
            if dep["artifact_id"] == artifact_id:
                dep.update(dependency(replacement_artifact))
    ir["project_canon_read_receipt"].update({
        "manifest_sha256": compile_manifest["sha256"], "manifest_version": compile_manifest["version"],
        "snapshot_file_sha256": file_hash(compile_path),
    })
    if mutate_ir is not None:
        mutate_ir(ir)
    finalize(ir)
    write_json(ir_path, ir)


def _canonical_audit_path(value: Any) -> Path | None:
    if isinstance(value, int):
        return None
    try:
        raw = os.fsdecode(value)
    except TypeError:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    return Path(os.path.normcase(str(path.resolve(strict=False))))


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _remove_tree_with_absolute_paths(root: Path) -> None:
    """Delete one mutable harness subtree without shutil's dir_fd mutations.

    The audit barrier intentionally rejects every relative write, including
    otherwise-safe dir_fd operations.  CPython's POSIX shutil.rmtree uses
    relative dir_fd unlinks internally, so restoration owns this small,
    explicit absolute-path remover instead of weakening the barrier.
    """
    if not root.is_absolute():
        raise AssertionError(f"absolute harness cleanup path required: {root}")
    if root.is_symlink() or root.is_file():
        root.unlink()
        return
    if not root.is_dir():
        return
    root.chmod(stat.S_IMODE(root.stat().st_mode) | 0o700)
    with os.scandir(root) as iterator:
        entries = list(iterator)
    for entry in entries:
        path = Path(entry.path)
        if not path.is_absolute():
            raise AssertionError(f"scandir returned a relative cleanup path: {path}")
        if entry.is_symlink():
            path.unlink()
        elif entry.is_dir(follow_symlinks=False):
            _remove_tree_with_absolute_paths(path)
        else:
            try:
                path.chmod(stat.S_IMODE(path.stat().st_mode) | 0o600)
            except FileNotFoundError:
                continue
            path.unlink()
    root.rmdir()


class CaseHarness:
    """Reuse one isolated project while blocking writes to Packaging authority."""

    def __init__(
        self,
        fixture_id: str,
        builder: Callable[[Path, Path], None],
        package_name: str = "prompt_package",
    ) -> None:
        self.fixture_id = fixture_id
        self._temp = tempfile.TemporaryDirectory(prefix=f"omni-{fixture_id}-")
        self.project_root = Path(self._temp.name).resolve()
        self.root = self.project_root / package_name
        self.active = False
        self.capturing = False
        self.restoring = False
        self.dirty: set[Path] = set()
        builder(self.root, self.project_root)
        symlink = next((path for path in self.project_root.rglob("*") if path.is_symlink()), None)
        if symlink is not None:
            raise AssertionError(f"case harness baseline must not contain symlinks: {symlink}")

        snapshot = json.loads((self.root / validator.PREFLIGHT_SNAPSHOT).read_text(encoding="utf-8"))
        entry = next(
            item for item in snapshot["active_artifacts"]
            if item["owner_skill"] == "packaging-product-identity-label-lock-board"
        )
        record_path = (self.project_root / entry["artifact_record_locator"]).resolve()
        record = json.loads(record_path.read_text(encoding="utf-8"))
        authority_path = (self.project_root / record["authority_evidence"]["locator"]).resolve()
        authority = json.loads(authority_path.read_text(encoding="utf-8"))
        self.packaging_root = (
            self.project_root / authority["packaging_run"]["run_root_locator"]
        ).resolve()
        self.protected_files = {
            record_path,
            authority_path,
            (self.project_root / record["production_approval"]["evidence_locator"]).resolve(),
            *((self.project_root / item["locator"]).resolve() for item in record["prompt_evidence"]),
        }
        self.packaging_record_digest = hashlib.sha256(
            json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.packaging_tree_digest = _packaging_tree_content_digest_full(self.packaging_root)
        self.baseline_files, self.baseline_dirs = self._capture_mutable_baseline()
        self.active = True
        _CASE_HARNESSES.append(self)
        _FROZEN_PROJECTS[self.project_root] = self

    def _inside_project(self, path: Path) -> bool:
        return _path_is_within(path, self.project_root)

    def _touches_protected(self, path: Path) -> bool:
        if _path_is_within(path, self.packaging_root) or _path_is_within(self.packaging_root, path):
            return True
        return any(path == item or _path_is_within(item, path) for item in self.protected_files)

    def _is_protected_member(self, path: Path) -> bool:
        return _path_is_within(path, self.packaging_root) or path in self.protected_files

    def _capture_mutable_baseline(
        self,
    ) -> tuple[
        dict[Path, tuple[bytes, int, int, int]],
        dict[Path, tuple[int, int, int]],
    ]:
        files: dict[Path, tuple[bytes, int, int, int]] = {}
        dirs: dict[Path, tuple[int, int, int]] = {}
        for current, names, filenames in os.walk(self.project_root, topdown=True):
            current_path = Path(current).resolve()
            names[:] = [
                name for name in names
                if not _path_is_within((current_path / name).resolve(), self.packaging_root)
            ]
            for name in names:
                path = (current_path / name).resolve()
                if not self._touches_protected(path):
                    metadata = path.stat()
                    dirs[path.relative_to(self.project_root)] = (
                        stat.S_IMODE(metadata.st_mode), metadata.st_atime_ns, metadata.st_mtime_ns
                    )
            for name in filenames:
                path = (current_path / name).resolve()
                if not self._is_protected_member(path):
                    payload = path.read_bytes()
                    metadata = path.stat()
                    files[path.relative_to(self.project_root)] = (
                        payload, stat.S_IMODE(metadata.st_mode),
                        metadata.st_atime_ns, metadata.st_mtime_ns,
                    )
        return files, dirs

    def audit(self, event: str, args: tuple[Any, ...]) -> None:
        if not self.active:
            return
        candidates: list[Any] = []
        if event == "open":
            mode = args[1] if len(args) > 1 else None
            flags = args[2] if len(args) > 2 else 0
            write_mode = isinstance(mode, str) and any(marker in mode for marker in "wax+")
            write_flags = isinstance(flags, int) and bool(
                flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            )
            if write_mode or write_flags:
                candidates = [args[0]]
        elif event == "os.mkdir":
            path = _canonical_audit_path(args[0])
            if path is not None and path.is_dir():
                return
            candidates = [args[0]]
        elif event in {"os.remove", "os.rmdir", "os.truncate", "os.chmod", "os.utime", "os.chdir"}:
            candidates = [args[0]]
        elif event in {"os.rename", "os.link"}:
            candidates = [args[0], args[1]]
        elif event == "os.symlink":
            candidates = [args[1]]
        else:
            return
        if event == "os.chdir":
            raise PermissionError("case harness blocked cwd mutation during an active case")
        for value in candidates:
            if isinstance(value, int):
                raise PermissionError(
                    "case harness blocked mutation through an unresolved file descriptor"
                )
            try:
                raw_path = Path(os.fsdecode(value))
            except TypeError:
                continue
            if not raw_path.is_absolute():
                raise PermissionError(
                    "case harness blocked relative-path mutation while Packaging authority is frozen"
                )
            path = _canonical_audit_path(value)
            if path is None or not self._inside_project(path):
                continue
            if self._touches_protected(path):
                raise PermissionError(
                    f"case harness blocked mutation of frozen Packaging authority: {path}"
                )
            if self.capturing and not self.restoring:
                self.dirty.add(path)

    def _restore_dirty(self) -> None:
        if not self.dirty:
            return
        self.restoring = True
        try:
            dirty = sorted(self.dirty, key=lambda item: len(item.parts))
            minimal: list[Path] = []
            for path in dirty:
                if not any(_path_is_within(path, parent) for parent in minimal):
                    minimal.append(path)
            for path in sorted(minimal, key=lambda item: len(item.parts), reverse=True):
                rel = path.relative_to(self.project_root)
                if path.is_symlink() or path.is_file():
                    path.unlink()
                elif path.is_dir():
                    _remove_tree_with_absolute_paths(path)
                subtree_dirs = sorted(
                    (item for item in self.baseline_dirs if item == rel or _path_is_within(item, rel)),
                    key=lambda item: len(item.parts),
                )
                for item in subtree_dirs:
                    (self.project_root / item).mkdir(parents=True, exist_ok=True)
                subtree_files = {
                    item: payload for item, payload in self.baseline_files.items()
                    if item == rel or _path_is_within(item, rel)
                }
                for item, (payload, mode, atime_ns, mtime_ns) in subtree_files.items():
                    target = self.project_root / item
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(payload)
                    target.chmod(mode)
                    os.utime(target, ns=(atime_ns, mtime_ns))
            for item in sorted(self.baseline_dirs, key=lambda value: len(value.parts), reverse=True):
                target = self.project_root / item
                if target.is_dir():
                    mode, atime_ns, mtime_ns = self.baseline_dirs[item]
                    target.chmod(mode)
                    os.utime(target, ns=(atime_ns, mtime_ns))
        finally:
            self.dirty.clear()
            self.restoring = False

    def execute(
        self,
        mutator: Callable[[Path], None] | None,
        operation: Callable[[Path, Path], Any],
    ) -> Any:
        self._restore_dirty()
        self.capturing = True
        try:
            if mutator is not None:
                mutator(self.root)
            return operation(self.root, self.project_root)
        finally:
            self.capturing = False
            self._restore_dirty()

    def assert_packaging_unchanged(self) -> None:
        if _packaging_tree_content_digest_full(self.packaging_root) != self.packaging_tree_digest:
            raise AssertionError("case harness Packaging authority bytes changed")

    def cleanup(self) -> None:
        self.active = False
        _FROZEN_PROJECTS.pop(self.project_root, None)
        self._temp.cleanup()


def _packaging_tree_content_digest_full(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        (item for item in root.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(root).as_posix(),
    ):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _case_harness_audit(event: str, args: tuple[Any, ...]) -> None:
    for harness in tuple(_CASE_HARNESSES):
        harness.audit(event, args)


sys.addaudithook(_case_harness_audit)


def cleanup_case_harnesses() -> None:
    global _STANDARD_HARNESS, _REVISE_HARNESS
    for harness in reversed(_CASE_HARNESSES):
        if harness.active:
            harness.cleanup()
    _CASE_HARNESSES.clear()
    for fixture_temp in _PACKAGING_FIXTURE_TEMP_DIRS:
        fixture_temp.cleanup()
    _PACKAGING_FIXTURE_TEMP_DIRS.clear()
    _PACKAGING_FIXTURE_CACHE.clear()
    _PACKAGING_OWNER_VALIDATION_CACHE.clear()
    _FROZEN_PROJECTS.clear()
    _STANDARD_HARNESS = None
    _REVISE_HARNESS = None


atexit.register(cleanup_case_harnesses)


_STANDARD_HARNESS: CaseHarness | None = None
_REVISE_HARNESS: CaseHarness | None = None


def _standard_harness() -> CaseHarness:
    global _STANDARD_HARNESS
    if _STANDARD_HARNESS is None or not _STANDARD_HARNESS.active:
        _STANDARD_HARNESS = CaseHarness("standard", create_package)
    return _STANDARD_HARNESS


def _revise_harness() -> CaseHarness:
    global _REVISE_HARNESS
    if _REVISE_HARNESS is None or not _REVISE_HARNESS.active:
        _REVISE_HARNESS = CaseHarness("revise", create_revise_package)
    return _REVISE_HARNESS


def run_case(mutator: Callable[[Path], None] | None = None) -> list[str]:
    return _standard_harness().execute(
        mutator,
        lambda root, project_root: validator.validate_package(
            root, project_root, project_root / validator.DEFAULT_POST_CANON
        ),
    )


def run_revise_case(mutator: Callable[[Path], None] | None = None) -> list[str]:
    return _revise_harness().execute(
        mutator,
        lambda root, project_root: validator.validate_package(
            root, project_root, project_root / validator.DEFAULT_POST_CANON
        ),
    )


def run_provider_constraint_case(
    stage: str,
    provider_mutator: Callable[[dict[str, Any]], None] | None = None,
    package_mutator: Callable[[Path, dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]], None] | None = None,
) -> list[str]:
    """Exercise provider file constraints without unrelated Canon resealing noise."""
    def operation(root: Path, project_root: Path) -> list[str]:
        provider_doc = json.loads((root / validator.PROVIDER_CAPS).read_text(encoding="utf-8"))
        provider = next(item for item in provider_doc["profiles"] if item["profile_type"] == "provider_runtime")
        if provider_mutator is not None:
            provider_mutator(provider)
        if stage == "p1":
            plan = json.loads((root / validator.PREFLIGHT_PLAN).read_text(encoding="utf-8"))
            snapshot = json.loads((root / validator.PREFLIGHT_SNAPSHOT).read_text(encoding="utf-8"))
            _, active = validator.validate_manifest_snapshot(snapshot, "provider-negative snapshot")
            return validator.validate_preflight_decision_matrix(
                plan, active, provider, provider["effective_limits"], project_root=project_root,
            )
        ir = json.loads((root / validator.IR_PATH).read_text(encoding="utf-8"))
        bindings = json.loads((root / validator.BINDINGS).read_text(encoding="utf-8"))
        inventory = {
            item["artifact"]["artifact_id"]: item for item in ir["source_artifact_inventory"]
        }
        if package_mutator is not None:
            package_mutator(project_root, bindings, inventory, provider)
        errors, _ = validator.validate_bindings(
            project_root, bindings, inventory, ir["generation_units"], ir["shots"],
            provider, provider["effective_limits"],
        )
        return errors
    return _standard_harness().execute(None, operation)


def expect_error(name: str, mutator: Callable[[Path], None], needle: str) -> None:
    errors = run_case(mutator)
    if not any(needle in error for error in errors):
        raise AssertionError(f"{name}: expected {needle!r}, got {errors}")


def expect_revise_error(name: str, mutator: Callable[[Path], None], needle: str) -> None:
    errors = run_revise_case(mutator)
    if not any(needle in error for error in errors):
        raise AssertionError(f"{name}: expected {needle!r}, got {errors}")


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        atlas_root = Path(temp)
        low_sources = []
        for index in range(2):
            rel = f"low_{index}.png"
            path = atlas_root / rel
            width = height = 2
            def chunk(kind: bytes, payload: bytes) -> bytes:
                return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
            scanline = b"\x00" + bytes([index * 50, 20, 30]) * width
            data = b"\x89PNG\r\n\x1a\n"
            data += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            data += chunk(b"IDAT", zlib.compress(scanline * height, level=9))
            data += chunk(b"IEND", b"")
            path.write_bytes(data)
            low_sources.append({
                "artifact_id": f"LOW_{index}", "file_path": rel,
                "file_sha256": file_hash(atlas_root / rel), "control_roles": ["identity"],
                "control_role": "identity",
            })
        low_spec = {
            "schema_version": "ai-video-deterministic-atlas-spec.v2", "atlas_id": "LOW_ATLAS",
            "generation_unit_id": "GU_LOW", "layout_columns": 2, "background_rgb": [0, 0, 0],
            "minimum_panel_width_pixels": 256, "minimum_panel_height_pixels": 256,
            "legibility_policy": "identity_geometry_look_only_no_microcopy",
            "source_decode_policy": "pillow_common_raster_to_rgb8_no_resize_v1",
            "output_encode_policy": "pillow_png_rgb8_fixed_v1",
            "layout_policy": "max_native_cell_center_floor_no_resize_v1", "output_codec": "PNG_RGB8",
            "sources": low_sources,
        }
        try:
            validator.build_from_spec(atlas_root, low_spec)
        except ValueError as exc:
            if "below the frozen legibility threshold" not in str(exc):
                raise AssertionError(f"low-resolution atlas failed for the wrong reason: {exc}") from exc
        else:
            raise AssertionError("2x2 atlas panels must fail the frozen legibility threshold")

    errors = run_case()
    if errors:
        raise AssertionError(f"positive six-shot fixture failed: {errors}")

    def protected_packaging_write_canary(_root: Path) -> None:
        harness = _standard_harness()
        target = next(
            path for path in sorted(harness.packaging_root.rglob("*"))
            if path.is_file()
        )
        original = target.read_bytes()
        original_stat = target.stat()
        changed = bytes([original[0] ^ 1]) + original[1:]
        try:
            target.write_bytes(changed)
        except PermissionError as exc:
            if "blocked mutation of frozen Packaging authority" not in str(exc):
                raise
        else:
            raise AssertionError("same-size Packaging overwrite escaped the pre-write barrier")
        try:
            os.utime(target, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        except PermissionError as exc:
            if "blocked mutation of frozen Packaging authority" not in str(exc):
                raise
        else:
            raise AssertionError("Packaging timestamp restoration escaped the pre-write barrier")
        if os.name != "nt" and os.open in os.supports_dir_fd and os.unlink in os.supports_dir_fd:
            directory_fd = os.open(harness.packaging_root, os.O_RDONLY)
            try:
                try:
                    os.open(target.name, os.O_WRONLY, dir_fd=directory_fd)
                except PermissionError as exc:
                    if "blocked relative-path mutation" not in str(exc):
                        raise
                else:
                    raise AssertionError("dir_fd relative overwrite escaped the pre-write barrier")
                try:
                    os.unlink(target.name, dir_fd=directory_fd)
                except PermissionError as exc:
                    if "blocked relative-path mutation" not in str(exc):
                        raise
                else:
                    raise AssertionError("dir_fd relative unlink escaped the pre-write barrier")
            finally:
                os.close(directory_fd)
        if target.read_bytes() != original or target.stat().st_mtime_ns != original_stat.st_mtime_ns:
            raise AssertionError("Packaging write barrier allowed baseline drift")

    _standard_harness().execute(protected_packaging_write_canary, lambda _root, _project: None)

    mutable_path = _standard_harness().root / validator.PROVIDER_CAPS
    mutable_before = mutable_path.stat()
    _standard_harness().execute(
        lambda _root: os.utime(
            mutable_path,
            ns=(mutable_before.st_atime_ns, max(1, mutable_before.st_mtime_ns - 1_000_000_000)),
        ),
        lambda _root, _project: None,
    )
    mutable_after = mutable_path.stat()
    if (
        stat.S_IMODE(mutable_after.st_mode) != stat.S_IMODE(mutable_before.st_mode)
        or mutable_after.st_mtime_ns != mutable_before.st_mtime_ns
    ):
        raise AssertionError("case harness failed to restore mutable file metadata")

    cwd_before = Path.cwd()
    def cwd_mutation_canary(root: Path) -> None:
        try:
            os.chdir(root)
        except PermissionError as exc:
            if "blocked cwd mutation" not in str(exc):
                raise
        else:
            raise AssertionError("case harness allowed cwd leakage")
    _standard_harness().execute(cwd_mutation_canary, lambda _root, _project: None)
    if Path.cwd() != cwd_before:
        raise AssertionError("case harness changed the process cwd")
    revision_errors = run_revise_case()
    if revision_errors:
        raise AssertionError(f"positive anchored revision fixture failed: {revision_errors}")

    def root_boundary_checks(package_root: Path, project_root: Path) -> None:
        missing_actual = validator.validate_package(package_root, project_root, None)
        if not any("--project-canon-manifest is required" in error for error in missing_actual):
            raise AssertionError(f"final package passed without actual post Canon: {missing_actual}")
        wrong_root = validator.validate_package(
            package_root, package_root, project_root / validator.DEFAULT_POST_CANON
        )
        if not any("manifest path must be inside --project-root" in error for error in wrong_root):
            raise AssertionError(f"wrong project root was accepted: {wrong_root}")
    _standard_harness().execute(None, root_boundary_checks)

    def suppress_required_images(root: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            for item in value["asset_inventory"]:
                if item["modality"] == "image":
                    item["unit_classification"][0].update({"status": "irrelevant_to_unit", "reason": "malicious omission"})
            value["generation_unit_bindings"][0]["bindings"] = [
                item for item in value["generation_unit_bindings"][0]["bindings"] if item["modality"] != "image"
            ]
            value["generation_unit_bindings"][0]["selected_counts"].update({"image": 0, "total_multimodal": 1})
        mutate_json(root, validator.BINDINGS, mutate)
    expect_error("required controls cannot be classified away", suppress_required_images, "required controls not delivered")

    def tamper_provider_snapshot(root: Path) -> None:
        path = root / "sources/provider_schema_snapshot.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["effective_limits"]["max_image_inputs"] = 50
        write_json(path, value)
    expect_error("provider schema snapshot tamper", tamper_provider_snapshot, "provider capabilities/schema snapshot: file SHA-256 mismatch")

    def drift_provider_from_snapshot(root: Path) -> None:
        mutate_json(root, validator.PROVIDER_CAPS, lambda value: value["profiles"][0].update({"model_id": "invented-runtime-alias"}))
    expect_error("provider declared facts must equal snapshot", drift_provider_from_snapshot, "declared runtime fields differ from local provider schema snapshot")

    def expect_provider_constraint_error(
        name: str, stage: str, mutate: Callable[[dict[str, Any]], None], needle: str,
        package_mutator: Callable[[Path, dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]], None] | None = None,
    ) -> None:
        provider_errors = run_provider_constraint_case(stage, mutate, package_mutator)
        if not any(needle in error for error in provider_errors):
            raise AssertionError(f"{name}: expected {needle!r}, got {provider_errors}")

    expect_provider_constraint_error(
        "provider rejects PNG",
        "p1",
        lambda provider: provider["input_constraints"]["image"].update(
            {"accepted_media_types": ["image/jpeg"]}
        ),
        "image media type is not accepted by the provider",
    )
    expect_provider_constraint_error(
        "provider atlas byte ceiling",
        "p1",
        lambda provider: provider["input_constraints"]["image"].update({"max_file_bytes": 1}),
        "image file exceeds provider max_file_bytes",
    )
    expect_provider_constraint_error(
        "provider atlas dimensions",
        "p1",
        lambda provider: provider["input_constraints"]["image"].update({"max_width_px": 300}),
        "image width is outside provider constraints",
    )
    expect_provider_constraint_error(
        "provider atlas aspect ratio",
        "p1",
        lambda provider: provider["input_constraints"]["image"].update({"max_aspect_ratio": 0.5}),
        "image aspect ratio is outside provider constraints",
    )
    expect_provider_constraint_error(
        "provider V2 codec",
        "p2",
        lambda provider: provider["input_constraints"]["video"].update({"accepted_video_codecs": ["hevc"]}),
        "video codec is not accepted by the provider",
    )
    expect_provider_constraint_error(
        "provider V2 container",
        "p2",
        lambda provider: provider["input_constraints"]["video"].update({"accepted_containers": ["webm"]}),
        "video container is not accepted by the provider",
    )

    def lie_in_stored_v2_probe(
        project_root: Path,
        bindings: dict[str, Any],
        inventory: dict[str, dict[str, Any]],
        _provider: dict[str, Any],
    ) -> None:
        item = inventory["CONTROL_PREVIS_GU001"]
        record_path = project_root / item["artifact_record_locator"]
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["media_probe"]["video_codec"] = "hevc"
        write_json(record_path, record)
        digest = file_hash(record_path)
        item["artifact_record_file_sha256"] = digest
        binding_item = next(
            value for value in bindings["asset_inventory"]
            if value["artifact"]["artifact_id"] == "CONTROL_PREVIS_GU001"
        )
        binding_item["artifact"]["artifact_record_file_sha256"] = digest

    expect_provider_constraint_error(
        "stored V2 probe lie",
        "p2",
        lambda _provider: None,
        "stored media probe video_codec differs from live file",
        lie_in_stored_v2_probe,
    )

    with tempfile.TemporaryDirectory() as temp:
        project_root = Path(temp)
        package_root = project_root / "prompt_package"
        model_doc, provider_doc = make_capability_docs(package_root)
        provider = provider_doc["profiles"][0]
        provider["input_constraints"]["image"].update({"min_width_px": 9000, "max_width_px": 100})
        snapshot_path = package_root / provider["evidence"][0]["snapshot_path"]
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["input_constraints"] = provider["input_constraints"]
        write_json(snapshot_path, snapshot)
        provider["evidence"][0]["snapshot_file_sha256"] = file_hash(snapshot_path)
        range_errors, _, _ = validator.validate_capabilities(package_root, model_doc, provider_doc)
        if not any("image constraint range min_width_px/max_width_px is invalid" in error for error in range_errors):
            raise AssertionError(f"inverted provider constraint range passed: {range_errors}")

    with tempfile.TemporaryDirectory() as temp:
        audio_root = Path(temp)
        audio_path = audio_root / "voice.wav"
        with wave.open(str(audio_path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(16000)
            output.writeframes(b"\x00\x00" * 16000)
        audio_errors = validator.validate_audio_file_for_provider(
            audio_root, "voice.wav", file_hash(audio_path),
            {
                "accepted_media_types": ["audio/wav"], "accepted_audio_codecs": ["mp3"],
                "max_file_bytes": 1_000_000, "max_duration_seconds": 15.0,
                "min_channels": 1, "max_channels": 2,
                "min_sample_rate_hz": 16000, "max_sample_rate_hz": 48000,
            },
            "audio-negative",
        )
        if not any("audio codec is not accepted by the provider" in error for error in audio_errors):
            raise AssertionError(f"actual selected-audio provider preflight was not enforced: {audio_errors}")

    def swap_direct_and_atlas_identity(root: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            inventory = {
                item["artifact"]["artifact_id"]: item for item in value["asset_inventory"]
            }
            character = inventory[CHARACTER_ASSET_ID]
            packaging = inventory[PACKAGING_ASSET_ID]
            character["unit_classification"][0]["status"] = "relevant_selected"
            packaging["unit_classification"][0]["status"] = "transported_via_atlas"
            binding = next(
                item for item in value["generation_unit_bindings"][0]["bindings"]
                if item["artifact_id"] == PACKAGING_ASSET_ID
            )
            binding.update({
                "artifact_id": CHARACTER_ASSET_ID,
                "modality": character["modality"], "control_roles": character["control_roles"],
                "control_role": character["control_role"], "scope": character["scope"],
                "controlled_shot_uids": character["controlled_shot_uids"],
                "expected_influence": character["expected_influence"], "priority": character["priority"],
            })
        mutate_json(root, validator.BINDINGS, mutate)
    expect_error(
        "same-count direct-atlas identity swap",
        swap_direct_and_atlas_identity,
        "P2 classification differs from the exact P1 decision",
    )

    def narrow_fixed_owner_roles(root: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            item = next(
                item for item in value["asset_inventory"]
                if item["artifact"]["artifact_id"] == CHARACTER_ASSET_ID
            )
            item["control_roles"] = ["identity"]
        mutate_json(root, validator.BINDINGS, mutate)
    expect_error(
        "P2 fixed-owner role narrowing",
        narrow_fixed_owner_roles,
        "control_roles must exactly equal the fixed-owner asset record authorization",
    )

    def inject_label_copy_into_atlas(root: Path) -> None:
        project_root = root.parent
        spec_path = project_root / "sources/ATLAS_GU001.spec.json"
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        source = next(item for item in spec["sources"] if item["artifact_id"] == LOOK_ASSET_ID)
        source["control_roles"].append("label_copy")
        write_json(spec_path, spec)
        def mutate(value: dict[str, Any]) -> None:
            item = next(
                item for item in value["asset_inventory"]
                if item["artifact"]["artifact_id"] == LOOK_ASSET_ID
            )
            item["control_roles"].append("label_copy")
            value["atlas_records"][0]["composition_spec_file_sha256"] = file_hash(spec_path)
        mutate_json(root, validator.BINDINGS, mutate)
    expect_error(
        "label authority injected into atlas",
        inject_label_copy_into_atlas,
        "label_copy or packaging evidence must remain a direct image binding, never an atlas panel",
    )

    def omit_prompt_role_mapping(root: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            role_map = next(
                item for item in value["generation_unit_prompts"][0]["bound_artifact_roles"]
                if item["artifact_id"] == "ATLAS_GU001"
            )
            role_map["control_roles"] = [role for role in role_map["control_roles"] if role != "wardrobe"]
        mutate_json(root, validator.UNIT_PROMPTS, mutate)
    expect_error(
        "prompt omits one transported role",
        omit_prompt_role_mapping,
        "bound_artifact_roles must serialize every selected binding role exactly",
    )

    def arbitrary_atlas_bytes(root: Path) -> None:
        atlas_path = root.parent / "sources/ATLAS_GU001.png"
        atlas_path.write_bytes(b"arbitrary self-asserted atlas bytes")
        digest = file_hash(atlas_path)
        def mutate(value: dict[str, Any]) -> None:
            record = value["atlas_records"][0]
            record["file_sha256"] = digest
            item = next(item for item in value["asset_inventory"] if item["artifact"]["artifact_id"] == record["atlas_id"])
            item["artifact"]["file_sha256"] = digest
        mutate_json(root, validator.BINDINGS, mutate)
    expect_error("arbitrary atlas binary", arbitrary_atlas_bytes, "atlas pixels are not the deterministic composition result")

    def ir_camera_self_report(root: Path) -> None:
        mutate_json(root, validator.IR_PATH, lambda value: value["shots"][0].update({"camera_composition": "invented Prompt-owned camera"}))
    expect_error("IR camera must match actual Shot Contract file", ir_camera_self_report, "facts differ from Shot Contract file")

    def point_canon_to_fake_projection(root: Path, change_ir: bool = False) -> None:
        project_root = root.parent
        shot_source = json.loads((project_root / "sources/SHOT_CONTRACT.original.json").read_text(encoding="utf-8"))
        fake_rel = "malicious/SHOT_CONTRACT.projection.json"
        fake = {
            "schema_version": "ai-video-upstream-authority-projection.v1",
            "authority_type": "PROFESSIONAL_SHOT_CONTRACT",
            "authority_artifact_ref": dependency(shot_source),
            "payload": {"camera_composition": "invented Prompt projection"},
        }
        write_json(project_root / fake_rel, fake)
        retarget_compile_locator(
            root, "SHOT_CONTRACT", fake_rel, file_hash(project_root / fake_rel),
            (lambda ir: ir["shots"][0].update({"camera_composition": "invented Prompt projection"})) if change_ir else None,
        )
    expect_error(
        "Canon locator cannot target Prompt-made projection",
        lambda root: point_canon_to_fake_projection(root, False),
        "Prompt-made authority projection is forbidden",
    )
    expect_error(
        "simultaneous fake projection and IR rewrite still fails",
        lambda root: point_canon_to_fake_projection(root, True),
        "Prompt-made authority projection is forbidden",
    )

    def mutate_original_and_ir_together(root: Path) -> None:
        project_root = root.parent
        path = project_root / "sources/SHOT_CONTRACT.original.json"
        source = json.loads(path.read_text(encoding="utf-8"))
        source["shots"][0]["composition"] = "malicious source-and-IR coordinated camera rewrite"
        finalize(source)
        write_json(path, source)
        projected, _ = validator.shot_contract_projection(source)
        retarget_compile_locator(
            root, source["artifact_id"], "sources/SHOT_CONTRACT.original.json", file_hash(path),
            lambda ir: ir["shots"][0].update({"camera_composition": projected[0]["camera_composition"]}),
            source,
        )
    expect_error(
        "raw authority and IR cannot coordinate around actual Canon",
        mutate_original_and_ir_together,
        "compile-active artifact was changed or removed by Prompt: SHOT_CONTRACT",
    )

    def raw_file_hash_mismatch(root: Path) -> None:
        path = root.parent / "sources/SHOT_CONTRACT.original.json"
        path.write_bytes(path.read_bytes() + b" ")
    expect_error("raw authority file hash mismatch", raw_file_hash_mismatch, "file SHA-256 mismatch")

    def raw_envelope_hash_mismatch(root: Path) -> None:
        project_root = root.parent
        path = project_root / "sources/SHOT_CONTRACT.original.json"
        source = json.loads(path.read_text(encoding="utf-8"))
        source["shots"][0]["composition"] = "changed without resealing owner envelope"
        write_json(path, source)
        retarget_compile_locator(root, source["artifact_id"], "sources/SHOT_CONTRACT.original.json", file_hash(path))
    expect_error("raw authority envelope hash mismatch", raw_envelope_hash_mismatch, "canonical envelope hash mismatch")

    def arbitrary_binary_artifact_record(root: Path) -> None:
        project_root = root.parent
        compile_path = root / validator.COMPILE_SNAPSHOT
        compile_manifest = json.loads(compile_path.read_text(encoding="utf-8"))
        entry = next(item for item in compile_manifest["active_artifacts"] if item["artifact_id"] == CHARACTER_ASSET_ID)
        record_rel = entry["artifact_record_locator"]
        write_json(project_root / record_rel, {"self_asserted": True})
        record_digest = file_hash(project_root / record_rel)
        entry["artifact_record_file_sha256"] = record_digest
        finalize(compile_manifest)
        write_json(compile_path, compile_manifest)
        ir_path = root / validator.IR_PATH
        ir = json.loads(ir_path.read_text(encoding="utf-8"))
        source = next(item for item in ir["source_artifact_inventory"] if item["artifact"]["artifact_id"] == CHARACTER_ASSET_ID)
        source["artifact_record_file_sha256"] = record_digest
        ir["project_canon_read_receipt"].update({"manifest_sha256": compile_manifest["sha256"], "snapshot_file_sha256": file_hash(compile_path)})
        finalize(ir)
        write_json(ir_path, ir)
    expect_error(
        "binary record cannot be self-asserted JSON",
        arbitrary_binary_artifact_record,
        f"upstream record/{CHARACTER_ASSET_ID}: missing envelope fields",
    )

    expect_error(
        "within-shot generation unit forbidden",
        lambda root: mutate_json(root, validator.PREFLIGHT_PLAN, lambda value: value.update({"generation_unit_boundary_policy": "within_shot_split"})),
        "value differs from const",
    )

    def drift_unchanged_revision_output(root: Path) -> None:
        path = root / "04_reports/CAPACITY_DEGRADATION_REPORT.md"
        write_text_lf(path, path.read_text(encoding="utf-8") + "malicious unnoticed drift\n")
        def mutate(value: dict[str, Any]) -> None:
            item = next(item for item in value["output_locks"] if item["file_path"] == "04_reports/CAPACITY_DEGRADATION_REPORT.md")
            item["file_sha256"] = file_hash(path)
        mutate_json(root, validator.LOCKFILE, mutate)
    revision_drift_errors = run_revise_case(drift_unchanged_revision_output)
    if not any("unchanged output drifted from previous lock" in error for error in revision_drift_errors):
        raise AssertionError(f"anchored revision failed to reject unrelated drift: {revision_drift_errors}")

    def tamper_previous_revision_lock(root: Path) -> None:
        path = root / "previous/PREVIOUS_DEPENDENCY_LOCKFILE.json"
        write_text_lf(path, path.read_text(encoding="utf-8") + " ")
    revision_anchor_errors = run_revise_case(tamper_previous_revision_lock)
    if not any("previous lockfile: file SHA-256 mismatch" in error for error in revision_anchor_errors):
        raise AssertionError(f"revision accepted tampered previous lock: {revision_anchor_errors}")

    def wrong_post_canon_base(root: Path) -> None:
        path = root.parent / validator.DEFAULT_POST_CANON
        value = json.loads(path.read_text(encoding="utf-8"))
        value["base_manifest_sha256"] = "0" * 64
        finalize(value)
        write_json(path, value)
    expect_error("post Canon must descend from compile snapshot", wrong_post_canon_base, "base_manifest_sha256 must equal compile snapshot")

    expect_error(
        "post Canon version must strictly advance",
        lambda root: reseal_actual_post(root, lambda value: value.update({"version": "1.1.0"})),
        "version must exceed compile manifest version",
    )
    expect_error(
        "post Canon revision counter must strictly advance",
        lambda root: reseal_actual_post(root, lambda value: value.update({"revision_counter": 2})),
        "revision_counter must equal compile revision_counter + 1",
    )

    expect_error(
        "receipt result must bind actual post Canon",
        lambda root: (lambda path, value: (value.update({"resulting_manifest_sha256": "0" * 64}), write_json(path, value)))(
            root / validator.MANIFEST_RECEIPT,
            json.loads((root / validator.MANIFEST_RECEIPT).read_text(encoding="utf-8")),
        ),
        "result hash differs from actual post-Canon",
    )

    def mutate_actual_prompt_entry(root: Path) -> None:
        path = root.parent / validator.DEFAULT_POST_CANON
        value = json.loads(path.read_text(encoding="utf-8"))
        entry = next(item for item in value["active_artifacts"] if item["artifact_id"] == "FINAL_IR")
        entry["file_sha256"] = "0" * 64
        finalize(value)
        write_json(path, value)
    expect_error("post Canon Prompt entry must bind output bytes", mutate_actual_prompt_entry, "active identity/hash/file lock mismatch for FINAL_IR")

    def break_preflight_ancestry(root: Path) -> None:
        path = root / validator.COMPILE_SNAPSHOT
        value = json.loads(path.read_text(encoding="utf-8"))
        value["base_manifest_sha256"] = "0" * 64
        finalize(value)
        write_json(path, value)
    expect_error("P1 preflight ancestor must be provable", break_preflight_ancestry, "compile snapshot must directly descend")

    def absolute_output_lock(root: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            value["output_locks"][0]["file_path"] = str((root / validator.IR_PATH).resolve())
        mutate_json(root, validator.LOCKFILE, mutate)
    expect_error("absolute package output path", absolute_output_lock, "absolute paths are forbidden")

    def escaping_output_lock(root: Path) -> None:
        mutate_json(root, validator.LOCKFILE, lambda value: value["output_locks"][0].update({"file_path": "../outside.json"}))
    expect_error("escaping package output path", escaping_output_lock, "path escapes declared root")

    def escaping_project_input(root: Path) -> None:
        retarget_compile_locator(root, "SHOT_CONTRACT", "../outside.json", "0" * 64)
    expect_error("escaping project Canon locator", escaping_project_input, "forbidden not schema")

    expect_error(
        "omitted shot block",
        lambda root: mutate_json(root, validator.UNIT_PROMPTS, lambda value: value["generation_unit_prompts"][0]["shot_blocks"].pop()),
        "shot_blocks must cover exact unit shots",
    )

    def remove_v2(root: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            value["generation_units"][0]["control_previs_artifact_id"] = None
            for shot in value["shots"]:
                shot["control_previs_artifact_id"] = None
        mutate_json(root, validator.IR_PATH, mutate)
    expect_error("missing V2", remove_v2, "required V2 Control Previs artifact missing")

    def image_only_provider(root: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            profile = value["profiles"][0]
            profile["supported_modalities"] = ["text", "image"]
            profile["effective_limits"]["max_video_inputs"] = 0
        mutate_json(root, validator.PROVIDER_CAPS, mutate)
    expect_error("image-only provider", image_only_provider, "selected unsupported modality video")

    def endpoint_payload(root: Path) -> None:
        mutate_json(
            root,
            validator.PAYLOAD,
            lambda value: value["unit_payloads"][0]["api_parameters"].update({"first_frame_image": "A", "last_frame_image": "B"}),
        )
    expect_error("endpoint payload", endpoint_payload, "forbidden endpoint-generation key")

    def endpoint_camelcase_bypass(root: Path) -> None:
        mutate_json(
            root,
            validator.PAYLOAD,
            lambda value: value["unit_payloads"][0]["api_parameters"].update({
                "mode": "image_to_video", "startImage": "@图片1", "endImage": "@图片2", "tail_image": "@图片2",
            }),
        )
    expect_error("camelCase endpoint bypass", endpoint_camelcase_bypass, "forbidden normalized endpoint-generation")

    expect_error(
        "payload root endpoint field",
        lambda root: mutate_json(root, validator.PAYLOAD, lambda value: value.update({"first_frame": "malicious"})),
        "additional property forbidden",
    )

    expect_error(
        "missing Look State",
        lambda root: mutate_json(root, validator.IR_PATH, lambda value: value["shots"][0].update({"look_state_prompt_full": ""})),
        "look_state_prompt_full",
    )

    def omit_claim_provenance(root: Path) -> None:
        path = root / validator.UNIT_PROMPTS
        value = json.loads(path.read_text(encoding="utf-8"))
        block = value["generation_unit_prompts"][0]["shot_blocks"][0]
        exact = validator.render_prompt_value(block["claim_provenance"])
        block["rendered_block"] = block["rendered_block"].replace(exact, "")
        finalize(value)
        write_json(path, value)
    expect_error("claim provenance omitted from rendered prompt", omit_claim_provenance, "missing exact claim_provenance")

    def omit_master_unit(root: Path) -> None:
        unit = json.loads((root / validator.UNIT_PROMPTS).read_text(encoding="utf-8"))["generation_unit_prompts"][0]["prompt_text"]
        path = root / "02_prompts/SEEDANCE_2_5_MASTER_PROMPT.md"
        write_text_lf(path, path.read_text(encoding="utf-8").replace(unit, "unit omitted"))
    expect_error("master prompt omits unit", omit_master_unit, "missing complete generation-unit prompt")

    expect_error(
        "independent QC injection",
        lambda root: mutate_json(root, validator.FEEDBACK, lambda value: value.update({"independent_output_qc": True, "edit_action": "edit_final_video"})),
        "independent_output_qc",
    )

    def feedback_change(root: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
        mutate_json(root, validator.FEEDBACK, mutate)
        sync_revised_output_to_lock_and_post(root, validator.FEEDBACK)

    def bogus_asset_owner(value: dict[str, Any]) -> None:
        request = {
            "request_id": "CR_BOGUS", "target_owner_skill": "banana-owner",
            "affected_shot_uids": ["S005"], "affected_artifact_ids": [PRODUCT_ASSET_ID],
            "affected_control_roles": ["product_geometry"], "conflict": "identity mismatch",
            "required_resolution": "repair the canonical asset",
        }
        route = value["feedback_routes"][0]
        route.update({
            "diagnosis_scope": "identity_product_material_scene_canon", "owner_skill": "banana-owner",
            "affected_artifact_ids": [PRODUCT_ASSET_ID],
            "affected_control_roles": ["product_geometry"],
            "action": "issue_upstream_change_request", "owned_diff": None,
            "upstream_change_request": request,
        })
        value["upstream_change_requests"] = [request]
    expect_revise_error(
        "feedback rejects invented asset owner",
        lambda root: feedback_change(root, bogus_asset_owner),
        "existing asset owner",
    )

    def wrong_existing_asset_owner(value: dict[str, Any]) -> None:
        request = {
            "request_id": "CR_WRONG_EXISTING", "target_owner_skill": "character-final-lock-board",
            "affected_shot_uids": ["S005"], "affected_artifact_ids": [PRODUCT_ASSET_ID],
            "affected_control_roles": ["product_geometry"],
            "conflict": "product identity mismatch", "required_resolution": "repair product canon",
        }
        route = value["feedback_routes"][0]
        route.update({
            "diagnosis_scope": "identity_product_material_scene_canon",
            "owner_skill": "character-final-lock-board", "affected_artifact_ids": [PRODUCT_ASSET_ID],
            "affected_control_roles": ["product_geometry"],
            "action": "issue_upstream_change_request", "owned_diff": None,
            "upstream_change_request": request,
        })
        value["upstream_change_requests"] = [request]
    expect_revise_error(
        "feedback rejects a real but non-owning asset skill",
        lambda root: feedback_change(root, wrong_existing_asset_owner),
        "not owned by the routed sole owner",
    )

    def unauthorized_asset_role(value: dict[str, Any]) -> None:
        owner = "material-sensitive-product-master-asset-board"
        request = {
            "request_id": "CR_BAD_ROLE", "target_owner_skill": owner,
            "affected_shot_uids": ["S005"], "affected_artifact_ids": [PRODUCT_ASSET_ID],
            "affected_control_roles": ["identity"],
            "conflict": "material authority misdiagnosed as identity",
            "required_resolution": "repair only the authorized material role",
        }
        route = value["feedback_routes"][0]
        route.update({
            "diagnosis_scope": "identity_product_material_scene_canon", "owner_skill": owner,
            "affected_artifact_ids": [PRODUCT_ASSET_ID], "affected_control_roles": ["identity"],
            "action": "issue_upstream_change_request", "owned_diff": None,
            "upstream_change_request": request,
        })
        value["upstream_change_requests"] = [request]
    expect_revise_error(
        "feedback rejects unauthorized semantic role",
        lambda root: feedback_change(root, unauthorized_asset_role),
        "affected_control_roles exceed the affected artifacts' authorized role union",
    )

    def mismatched_request_roles(value: dict[str, Any]) -> None:
        owner = "material-sensitive-product-master-asset-board"
        request = {
            "request_id": "CR_ROLE_MISMATCH", "target_owner_skill": owner,
            "affected_shot_uids": ["S005"], "affected_artifact_ids": [PRODUCT_ASSET_ID],
            "affected_control_roles": ["material_behavior"],
            "conflict": "material response mismatch", "required_resolution": "repair material behavior",
        }
        route = value["feedback_routes"][0]
        route.update({
            "diagnosis_scope": "identity_product_material_scene_canon", "owner_skill": owner,
            "affected_artifact_ids": [PRODUCT_ASSET_ID], "affected_control_roles": ["product_geometry"],
            "action": "issue_upstream_change_request", "owned_diff": None,
            "upstream_change_request": request,
        })
        value["upstream_change_requests"] = [request]
    expect_revise_error(
        "feedback route/request role mismatch",
        lambda root: feedback_change(root, mismatched_request_roles),
        "upstream request control-role scope differs from route",
    )

    def prompt_scope_issues_request(value: dict[str, Any]) -> None:
        request = {
            "request_id": "CR_PROMPT", "target_owner_skill": validator.OWNER,
            "affected_shot_uids": ["S005"], "affected_artifact_ids": [PRODUCT_ASSET_ID],
            "affected_control_roles": ["product_geometry"], "conflict": "serialization",
            "required_resolution": "change prompt",
        }
        route = value["feedback_routes"][0]
        route.update({"action": "issue_upstream_change_request", "affected_artifact_ids": [PRODUCT_ASSET_ID], "affected_control_roles": [], "owned_diff": None, "upstream_change_request": request})
        value["upstream_change_requests"] = [request]
    expect_revise_error(
        "prompt-owned feedback cannot issue upstream request",
        lambda root: feedback_change(root, prompt_scope_issues_request),
        "schema",
    )

    def stochastic_with_diff(value: dict[str, Any]) -> None:
        route = value["feedback_routes"][0]
        route.update({"diagnosis_scope": "stochastic_model_failure", "action": "revise_prompt_owned_surface"})
    expect_revise_error(
        "stochastic failure cannot revise artifacts",
        lambda root: feedback_change(root, stochastic_with_diff),
        "schema",
    )

    def orphan_root_request(value: dict[str, Any]) -> None:
        value["upstream_change_requests"] = [{
            "request_id": "CR_ORPHAN", "target_owner_skill": "ai-video-global-look-lock",
            "affected_shot_uids": ["S005"], "affected_artifact_ids": ["GLOBAL_LOOK"],
            "affected_control_roles": ["global_look"], "conflict": "orphan",
            "required_resolution": "none",
        }]
    expect_revise_error(
        "feedback rejects orphan root request",
        lambda root: feedback_change(root, orphan_root_request),
        "exactly equal all route requests",
    )

    def same_ir_version(root: Path) -> None:
        mutate_json(root, validator.IR_PATH, lambda value: value.update({"version": "1.0.0"}))
        sync_revised_output_to_lock_and_post(root, validator.IR_PATH)
    expect_revise_error(
        "revised IR must advance SemVer",
        same_ir_version,
        "current IR version must exceed previous IR version",
    )

    def vendor_alias_overclaim(root: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            profile = value["profiles"][0]
            profile["model_id"] = "vendor/doubao-seedance-2.0-omni"
            profile["effective_limits"]["max_duration_seconds"] = 30
        mutate_json(root, validator.PROVIDER_CAPS, mutate)
    expect_error("vendor alias overclaim", vendor_alias_overclaim, "exceeds documented backend ceiling")

    expect_error(
        "P1 planned counts over capacity",
        lambda root: mutate_json(root, validator.PREFLIGHT_PLAN, lambda value: value["generation_units"][0]["planned_reference_counts"].update({"image": 99, "video": 3, "audio": 3, "total_multimodal": 105})),
        "planned image count exceeds effective capacity",
    )

    expect_error(
        "dependency lock drift",
        lambda root: mutate_json(root, validator.LOCKFILE, lambda value: value["input_locks"][0].update({"owner_skill": "wrong-owner"})),
        "input locks must exactly equal",
    )

    def structure_storyboard_transport(root: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            item = next(entry for entry in value["asset_inventory"] if entry["control_role"] == "storyboard" and entry["modality"] == "image")
            item["storyboard_stage"] = "structure_draft"
            item["storyboard_model_input_eligible"] = False
        mutate_json(root, validator.BINDINGS, mutate)
    expect_error("structure storyboard transport", structure_storyboard_transport, "structure-draft storyboard cannot enter model transport")

    def music_binding(root: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            item = next(entry for entry in value["asset_inventory"] if entry["unit_classification"][0]["status"] == "relevant_selected" and entry["modality"] == "text")
            item["modality"] = "audio"
            item["control_role"] = "music"
            selected = next(binding for binding in value["generation_unit_bindings"][0]["bindings"] if binding["artifact_id"] == item["artifact"]["artifact_id"])
            selected["modality"] = "audio"
            selected["control_role"] = "music"
        mutate_json(root, validator.BINDINGS, mutate)
    expect_error("music role", music_binding, "control_role")

    def silently_remove_asset(root: Path) -> None:
        compile_path = root / validator.COMPILE_SNAPSHOT
        manifest = json.loads(compile_path.read_text(encoding="utf-8"))
        manifest["active_artifacts"] = [item for item in manifest["active_artifacts"] if item["artifact_id"] != PRODUCT_ASSET_ID]
        manifest["dependency_edges"] = [
            item for item in manifest["dependency_edges"]
            if item["producer_artifact_id"] != PRODUCT_ASSET_ID and item["consumer_artifact_id"] != PRODUCT_ASSET_ID
        ]
        finalize(manifest)
        write_json(compile_path, manifest)
        compile_digest = file_hash(compile_path)
        def mutate_ir(value: dict[str, Any]) -> None:
            value["project_canon_read_receipt"].update({
                "manifest_sha256": manifest["sha256"], "manifest_version": manifest["version"],
                "snapshot_file_sha256": compile_digest,
            })
            value["source_artifact_inventory"] = [
                item for item in value["source_artifact_inventory"] if item["artifact"]["artifact_id"] != PRODUCT_ASSET_ID
            ]
        mutate_json(root, validator.IR_PATH, mutate_ir)
    expect_error("silent manifest deletion", silently_remove_asset, "silently removed preflight assets")

    expect_error(
        "manifest receipt misses Prompt artifact",
        lambda root: (lambda path, value: (value["registered_artifact_ids"].pop(), write_json(path, value)))(
            root / validator.MANIFEST_RECEIPT,
            json.loads((root / validator.MANIFEST_RECEIPT).read_text(encoding="utf-8")),
        ),
        "register every Prompt-owned artifact exactly",
    )

    malformed = finalize(envelope("MALFORMED", validator.OWNER, SHOTS, status="assistant_validated"))
    malformed["affected_shot_uids"] = [["unhashable"]]
    if not validator.validate_envelope(malformed, "malformed"):
        raise AssertionError("malformed envelope was not rejected")

    final_errors = run_case()
    if final_errors:
        raise AssertionError(f"post-mutation positive sentinel failed: {final_errors}")
    final_revision_errors = run_revise_case()
    if final_revision_errors:
        raise AssertionError(
            f"post-mutation revision sentinel failed: {final_revision_errors}"
        )
    for harness in _CASE_HARNESSES:
        harness.assert_packaging_unchanged()
    cleanup_case_harnesses()
    if _PACKAGING_FIXTURE_CACHE or _PACKAGING_OWNER_VALIDATION_CACHE or _FROZEN_PROJECTS:
        raise AssertionError("case harness cleanup left stale fixture or validation cache state")
    reentry_errors = run_case()
    if reentry_errors:
        raise AssertionError(f"case harness cleanup/re-entry failed: {reentry_errors}")
    _standard_harness().assert_packaging_unchanged()

    print(
        "PASS: prompt validator covers owner-schema-valid authorities, project/package roots, binary/record locks, "
        "actual post-Canon ancestry, exact P1->P2 artifact identities and multi-role bindings, provider snapshot and "
        "live image/video/audio upload constraints, stored-probe lies, deterministic atlas dry-build/rebuild and "
        "label exclusion, same-count swaps, role-complete prompts and feedback routing, whole-shot units, anchored "
        "revisions, payload denylist, and receipts"
    )
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    finally:
        cleanup_case_harnesses()
    raise SystemExit(exit_code)
