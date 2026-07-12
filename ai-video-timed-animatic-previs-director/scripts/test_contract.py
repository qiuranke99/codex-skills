#!/usr/bin/env python3
"""Exercise positive and adversarial timing/previs fixtures with real video media."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from probe_control_media import probe_media
from validate_previs_package import (
    FORBIDDEN_DIMENSIONS,
    canonical_artifact_hash,
    sha256_file,
    validate_package,
)

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
OWNER = "ai-video-timed-animatic-previs-director"
SUITE_ROOT = SKILL_ROOT.parent
PROMPT_HELPERS = SUITE_ROOT / "ai-video-omni-reference-prompt-director" / "scripts"
if str(PROMPT_HELPERS) not in sys.path:
    sys.path.insert(0, str(PROMPT_HELPERS))
from validate_schema_parity import validate_instance  # type: ignore  # noqa: E402

PREVIS_SCHEMA = json.loads((SKILL_ROOT / "references/previs_manifest.schema.json").read_text(encoding="utf-8"))
PROVIDER_EVIDENCE_SCHEMA = json.loads((SKILL_ROOT / "references/provider_runtime_capability_evidence.schema.json").read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_bytes(path: Path, value: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return sha256_file(path)


def dependency_from(value: dict[str, Any]) -> dict[str, Any]:
    return {field: value[field] for field in ("artifact_id", "owner_skill", "version", "sha256")}


def envelope(
    artifact_id: str,
    owner: str,
    uids: list[str],
    dependencies: list[dict[str, Any]] | None = None,
    version: str = "1.0.0",
) -> dict[str, Any]:
    return {
        "contract_version": "ai-video-artifact-v1",
        "artifact_id": artifact_id,
        "owner_skill": owner,
        "version": version,
        "sha256": None,
        "approval_status": "assistant_validated",
        "dependencies": copy.deepcopy(dependencies or []),
        "affected_shot_uids": list(uids),
        "stale_reason": None,
    }


def seal(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact["sha256"] = canonical_artifact_hash(artifact)
    return artifact


def authority_snapshot(root: Path, artifact: dict[str, Any]) -> dict[str, Any]:
    rel = f"00_manifest/source_snapshots/{artifact['artifact_id']}.json"
    write_json(root / rel, artifact)
    return {
        "artifact_id": artifact["artifact_id"],
        "owner_skill": artifact["owner_skill"],
        "version": artifact["version"],
        "sha256": artifact["sha256"],
        "approval_status": artifact["approval_status"],
        "snapshot_path": rel,
        "snapshot_file_sha256": sha256_file(root / rel),
    }


def input_evidence(
    root: Path,
    input_id: str,
    source_artifact_id: str,
    role: str,
    shot_uids: list[str],
    upstream_path: str,
    payload: bytes,
) -> tuple[dict[str, Any], str]:
    suffix = Path(upstream_path).suffix or ".bin"
    copied = f"00_manifest/source_inputs/{input_id}{suffix}"
    digest = write_bytes(root / copied, payload)
    return ({
        "input_id": input_id,
        "source_artifact_id": source_artifact_id,
        "role": role,
        "shot_uids": shot_uids,
        "copied_file_path": copied,
        "file_sha256": digest,
        "upstream_declared_path": upstream_path,
        "upstream_declared_file_sha256": digest,
    }, digest)


def duration_plan(count: int, total: float) -> list[float]:
    weights = [1.0 + (index % 4) * 0.2 for index in range(count)]
    factor = total / sum(weights)
    durations = [round(weight * factor, 3) for weight in weights[:-1]]
    durations.append(round(total - sum(durations), 3))
    if durations[-1] <= 0:
        raise AssertionError("invalid duration plan")
    return durations


def make_timeline(
    uids: list[str],
    durations: list[float],
    global_orders: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    cursor = 0.0
    timeline: list[dict[str, Any]] = []
    for index, (uid, duration) in enumerate(zip(uids, durations), 1):
        end = round(cursor + duration, 3)
        timeline.append({
            "shot_uid": uid,
            "display_order": global_orders[uid] if global_orders else index,
            "start_seconds": cursor,
            "end_seconds": end,
            "duration_seconds": duration,
            "cut_motivation": "information or action beat",
            "rough_camera_path": "single controlled move or static hold",
            "rough_blocking": "explicit screen position and direction",
            "motion_anchors": [
                {"time_seconds": cursor, "state": "entry"},
                {"time_seconds": end, "state": "exit"},
            ],
        })
        cursor = end
    return timeline


def write_test_video(path: Path, timeline: list[dict[str, Any]], fps: int = 25) -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        raise AssertionError("contract tests require ffmpeg and ffprobe")
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = path.with_suffix(".ffmetadata")
    metadata_lines = [";FFMETADATA1"]
    for entry in timeline:
        metadata_lines.extend([
            "[CHAPTER]",
            "TIMEBASE=1/1000000",
            f"START={round(float(entry['start_seconds']) * 1000000)}",
            f"END={round(float(entry['end_seconds']) * 1000000)}",
            f"title={entry['shot_uid']}",
        ])
    metadata_path.write_text("\n".join(metadata_lines) + "\n", encoding="utf-8")
    colors = ["red", "blue", "green", "yellow", "magenta", "cyan", "orange", "purple"]
    command = [ffmpeg, "-y", "-loglevel", "error"]
    for index, entry in enumerate(timeline):
        command.extend([
            "-f", "lavfi", "-t", f"{float(entry['duration_seconds']):.6f}",
            "-i", f"color=c={colors[index % len(colors)]}:s=64x36:r={fps}",
        ])
    metadata_index = len(timeline)
    command.extend(["-f", "ffmetadata", "-i", str(metadata_path)])
    filters = [f"[{index}:v]setpts=PTS-STARTPTS[v{index}]" for index in range(len(timeline))]
    filters.append("".join(f"[v{index}]" for index in range(len(timeline))) + f"concat=n={len(timeline)}:v=1:a=0[outv]")
    command.extend([
        "-filter_complex", ";".join(filters), "-map", "[outv]", "-map_metadata", str(metadata_index),
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps),
        "-t", f"{float(timeline[-1]['end_seconds']):.6f}", "-movflags", "+faststart", str(path),
    ])
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise AssertionError(f"cannot build real control-video fixture: {exc}") from exc
    metadata_path.unlink()
    return probe_media(path, ffprobe)


def unit_groups(uids: list[str], durations: list[float], maximum: float) -> list[tuple[list[str], list[float]]]:
    groups: list[tuple[list[str], list[float]]] = []
    current_uids: list[str] = []
    current_durations: list[float] = []
    current_total = 0.0
    for uid, duration in zip(uids, durations):
        if current_uids and current_total + duration > maximum + 0.001:
            groups.append((current_uids, current_durations))
            current_uids, current_durations, current_total = [], [], 0.0
        current_uids.append(uid)
        current_durations.append(duration)
        current_total += duration
    groups.append((current_uids, current_durations))
    return groups


def make_sources(
    root: Path,
    uids: list[str],
    durations: list[float],
    groups: list[tuple[list[str], list[float]]],
    provider_max: float,
    include_v2: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    input_records: list[dict[str, Any]] = []
    shot_contract = envelope("SHOT_CONTRACT", "ai-video-shot-script-director", uids)
    shot_contract.update({
        "schema_version": "ai-video-shot-contract.v1",
        "timeline": {"shot_count": len(uids), "total_duration_seconds": round(sum(durations), 3)},
        "shots": [
            {"shot_uid": uid, "display_no": index, "target_duration_seconds": duration}
            for index, (uid, duration) in enumerate(zip(uids, durations), 1)
        ],
    })
    seal(shot_contract)

    storyboard_stage = "look_applied_final" if include_v2 else "structure_draft"
    storyboard = envelope("STORYBOARD_MANIFEST", "ai-video-modular-storyboard", uids, [dependency_from(shot_contract)])
    frames: list[dict[str, Any]] = []
    for index, (uid, duration) in enumerate(zip(uids, durations), 1):
        frame_path = f"02_frames/{uid}.png"
        frame_record, frame_hash = input_evidence(
            root, f"SB_FRAME_{uid}", storyboard["artifact_id"], "storyboard_frame", [uid],
            frame_path, ("PNG_FIXTURE:" + uid).encode("utf-8"),
        )
        input_records.append(frame_record)
        prompt_path = f"02_frames/{uid}_generation_prompt.md"
        prompt_record, prompt_hash = input_evidence(
            root, f"SB_PROMPT_{uid}", storyboard["artifact_id"], "storyboard_generation_prompt", [uid],
            prompt_path, f"Storyboard generation prompt for {uid}.".encode("utf-8"),
        )
        input_records.append(prompt_record)
        frames.append({
            "shot_uid": uid,
            "display_order": index,
            "target_duration_seconds": duration,
            "stage": storyboard_stage,
            "file_path": frame_path,
            "file_sha256": frame_hash,
            "generation_prompt_path": prompt_path,
            "generation_prompt_file_sha256": prompt_hash,
            "is_model_input_eligible": include_v2,
        })
    storyboard.update({
        "schema_version": "ai-video-modular-storyboard.v1",
        "storyboard_stage": storyboard_stage,
        "script_shot_count": len(uids),
        "frames": frames,
    })
    seal(storyboard)

    source_refs: dict[str, Any] = {
        "shot_contract": authority_snapshot(root, shot_contract),
        "storyboard": authority_snapshot(root, storyboard),
        "keyframe_pack": None,
        "keyframe_boundary_supplement": None,
        "provider_preflight": None,
        "provider_capability": None,
    }
    if not include_v2:
        return source_refs, input_records

    keyframe = envelope(
        "KEYFRAME_PACK", "ai-video-keyframe-continuity-pack", uids,
        [dependency_from(shot_contract), dependency_from(storyboard)],
    )
    shot_records: list[dict[str, Any]] = []
    for uid in uids:
        image_path = f"01_keyframes/{uid}/KF_{uid}.png"
        image_record, image_hash = input_evidence(
            root, f"KF_IMAGE_{uid}", keyframe["artifact_id"], "keyframe_image", [uid],
            image_path, ("KEYFRAME_FIXTURE:" + uid).encode("utf-8"),
        )
        input_records.append(image_record)
        prompt_path = f"01_keyframes/{uid}/KF_{uid}_generation_prompt.md"
        prompt_record, prompt_hash = input_evidence(
            root, f"KF_PROMPT_{uid}", keyframe["artifact_id"], "keyframe_generation_prompt", [uid],
            prompt_path, f"Generation-ready keyframe prompt for {uid}.".encode("utf-8"),
        )
        input_records.append(prompt_record)
        shot_records.append({
            "shot_uid": uid,
            "keyframes": [{
                "keyframe_id": f"KF_{uid}",
                "file_path": image_path,
                "file_sha256": image_hash,
                "prompt_path": prompt_path,
                "prompt_file_sha256": prompt_hash,
            }],
        })
    keyframe.update({
        "schema_version": "ai-video-keyframe-continuity-pack.v1",
        "scripted_shot_uids": uids,
        "shot_records": shot_records,
    })
    seal(keyframe)

    provider_capability = envelope("PROVIDER_CAPABILITY", "ai-video-omni-reference-prompt-director", uids)
    schema_upstream_path = "provider_runtime/schema_snapshot.json"
    video_input_constraints = {
        "accepted_media_types": ["video/mp4"],
        "accepted_containers": ["mp4"],
        "accepted_video_codecs": ["h264"],
        "max_file_bytes": 10_000_000,
        "min_duration_seconds": 0.1,
        "max_duration_seconds": provider_max,
        "min_width_px": 32,
        "max_width_px": 4096,
        "min_height_px": 18,
        "max_height_px": 4096,
        "min_aspect_ratio": 0.25,
        "max_aspect_ratio": 4.0,
        "min_fps": 1.0,
        "max_fps": 120.0,
        "audio_track_policy": "forbidden",
    }
    runtime_profile_projection = {
        "schema_version": "provider-runtime-capability-evidence.v1",
        "profile_id": "fixture_provider_runtime",
        "provider": "fixture-provider",
        "model_family": "Seedance",
        "model_id": "fixture/omni-reference",
        "surface": "third-party-api",
        "documented_backend_profile_id": "seedance_2_0_documented_omni",
        "generation_mode": "omni_reference_to_video",
        "surface_status": "provider_schema_verified",
        "supported_modalities": ["text", "image", "video"],
        "effective_limits": {
            "max_duration_seconds": provider_max,
            "max_image_inputs": 9,
            "max_video_inputs": 3,
            "max_audio_inputs": 3,
            "max_total_multimodal_inputs": 15,
        },
        "video_input_constraints": copy.deepcopy(video_input_constraints),
    }
    provider_projection_errors = validate_instance(
        runtime_profile_projection, PROVIDER_EVIDENCE_SCHEMA, PROVIDER_EVIDENCE_SCHEMA,
    )
    if provider_projection_errors:
        raise AssertionError(f"provider runtime projection fixture violates input schema: {provider_projection_errors}")
    schema_record, schema_hash = input_evidence(
        root, "PROVIDER_SCHEMA", provider_capability["artifact_id"], "provider_schema_snapshot", [],
        schema_upstream_path, json.dumps(runtime_profile_projection, sort_keys=True).encode("utf-8"),
    )
    input_records.append(schema_record)
    provider_capability.update({
        "schema_version": "ai-video-capability-profile.v1",
        "profiles": [{
            "profile_type": "provider_runtime",
            "profile_id": "fixture_provider_runtime",
            "provider": "fixture-provider",
            "model_family": "Seedance",
            "model_id": "fixture/omni-reference",
            "surface": "third-party-api",
            "documented_backend_profile_id": "seedance_2_0_documented_omni",
            "generation_mode": "omni_reference_to_video",
            "surface_status": "provider_schema_verified",
            "supported_modalities": ["text", "image", "video"],
            "effective_limits": runtime_profile_projection["effective_limits"],
            "input_constraints": {
                "image": None,
                "video": copy.deepcopy(video_input_constraints),
                "audio": None,
            },
            "capability_claims": [],
            "evidence": [{
                "evidence_tier": "provider_schema_verified",
                "retrieved_at": "2026-07-12",
                "locator": "fixture-provider-schema",
                "supports": "fixture_provider_runtime",
                "snapshot_path": schema_upstream_path,
                "snapshot_file_sha256": schema_hash,
            }],
        }],
    })
    seal(provider_capability)

    preflight = envelope(
        "PROVIDER_PREFLIGHT", "ai-video-omni-reference-prompt-director", uids,
        [
            dependency_from(shot_contract), dependency_from(storyboard),
            dependency_from(keyframe), dependency_from(provider_capability),
        ],
    )
    planned_units = []
    for index, (group_uids, group_durations) in enumerate(groups, 1):
        planned_units.append({
            "generation_unit_id": f"GU_{index:02d}",
            "ordered_shot_uids": group_uids,
            "target_duration_seconds": round(sum(group_durations), 3),
            "control_previs_requirement": "required",
            "preflight_status": "ready",
        })
    preflight.update({
        "schema_version": "ai-video-generation-unit-preflight.v1",
        "plan_status": "ready_for_boundary_supplement",
        "generation_mode": "omni_reference_to_video",
        "provider_profile_id": "fixture_provider_runtime",
        "ordered_shot_uids": uids,
        "generation_units": planned_units,
    })
    seal(preflight)

    boundary = envelope(
        "KEYFRAME_BOUNDARY_SUPPLEMENT", "ai-video-keyframe-continuity-pack", uids,
        [dependency_from(keyframe), dependency_from(preflight)],
    )
    boundary.update({
        "schema_version": "ai-video-keyframe-boundary-supplement.v1",
        "core_keyframe_manifest": dependency_from(keyframe),
        "prompt_preflight": dependency_from(preflight),
        "scripted_shot_uids": uids,
        "generation_units": [
            {"generation_unit_id": item["generation_unit_id"], "ordered_shot_uids": item["ordered_shot_uids"]}
            for item in planned_units
        ],
    })
    seal(boundary)

    source_refs.update({
        "keyframe_pack": authority_snapshot(root, keyframe),
        "keyframe_boundary_supplement": authority_snapshot(root, boundary),
        "provider_preflight": authority_snapshot(root, preflight),
        "provider_capability": authority_snapshot(root, provider_capability),
    })
    return source_refs, input_records


def bind_v1_into_v2_sources(root: Path, source: dict[str, Any], v1: dict[str, Any]) -> None:
    """Complete the real V1 -> P1 -> K2 authority chain before V2 construction."""
    preflight_ref = source["provider_preflight"]
    preflight_path = root / preflight_ref["snapshot_path"]
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    preflight["dependencies"].append(dependency_from(v1))
    seal(preflight)
    write_json(preflight_path, preflight)
    preflight_ref.update({
        "sha256": preflight["sha256"],
        "snapshot_file_sha256": sha256_file(preflight_path),
    })

    boundary_ref = source["keyframe_boundary_supplement"]
    boundary_path = root / boundary_ref["snapshot_path"]
    boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    boundary["dependencies"] = [dependency_from(source["keyframe_pack"]), dependency_from(preflight_ref)]
    boundary["prompt_preflight"] = dependency_from(preflight_ref)
    seal(boundary)
    write_json(boundary_path, boundary)
    boundary_ref.update({
        "sha256": boundary["sha256"],
        "snapshot_file_sha256": sha256_file(boundary_path),
    })


def make_v1(
    root: Path,
    uids: list[str],
    durations: list[float],
    source: dict[str, Any],
) -> dict[str, Any]:
    rel = "01_timing_animatic_v1/timing_animatic_v1.mp4"
    timeline = make_timeline(uids, durations)
    media_probe = write_test_video(root / rel, timeline)
    deps = [dependency_from(source["shot_contract"]), dependency_from(source["storyboard"])]
    v1 = envelope("TIMING_ANIMATIC_V1", OWNER, uids, deps)
    v1.update({
        "phase": "timing_animatic_v1",
        "provider_neutral": True,
        "uses_keyframes": False,
        "model_input_role": "timing_review_only",
        "is_model_input": False,
        "final_edit_asset": False,
        "silent": True,
        "render_style": "storyboard_cut_animatic",
        "file_path": rel,
        "file_sha256": sha256_file(root / rel),
        "actual_duration_seconds": media_probe["duration_seconds"],
        "media_probe": media_probe,
        "timeline": timeline,
        "control_dimensions": [
            "shot_boundaries", "target_timing", "camera_trajectory", "subject_blocking",
            "object_motion", "material_physics",
        ],
        "forbidden_dimensions": sorted(FORBIDDEN_DIMENSIONS),
    })
    return seal(v1)


def make_motion_track(
    track_id: str,
    motion_class: str,
    uid: str,
    unit_id: str,
    v1: dict[str, Any],
    source: dict[str, Any],
    unit_shot_uids: list[str],
) -> dict[str, Any]:
    parameters_by_class = {
        "liquid": {
            "volume_continuity": "preserve plausible volume", "viscosity_behavior": "slow cosmetic-oil flow",
            "gravity_direction": "down", "wetting_adhesion": "thin adherent film", "contact_surfaces": ["palm", "skin"],
            "breakup_coalescence": "single bead stretches then rejoins", "state_at_cut": "film settled",
        },
        "cloth": {
            "anchor_points": ["shoulders", "waist"], "drape_stiffness_intent": "soft lightweight drape",
            "wind_acceleration": "low lateral breeze", "body_object_collisions": "no penetration",
            "settling_behavior": "two diminishing folds", "state_at_cut": "near rest",
        },
        "hair": {
            "root_lock": "roots fixed to approved hairstyle", "inertia": "small lag behind head turn",
            "gravity_wind": "gravity plus low lateral breeze", "body_wardrobe_collisions": "clear shoulders and garment",
            "settling_behavior": "one soft overshoot", "state_at_cut": "controlled loose strands",
        },
    }
    deps = [
        dependency_from(source["shot_contract"]), dependency_from(source["storyboard"]),
        dependency_from(v1), dependency_from(source["keyframe_pack"]),
        dependency_from(source["keyframe_boundary_supplement"]), dependency_from(source["provider_preflight"]),
    ]
    track = envelope(f"MOTION_{track_id}", OWNER, [uid], deps)
    by_uid = {item["shot_uid"]: item for item in v1["timeline"]}
    shot_timing = by_uid[uid]
    unit_origin = by_uid[unit_shot_uids[0]]["start_seconds"]
    local_start = round(shot_timing["start_seconds"] - unit_origin, 3)
    local_end = round(shot_timing["end_seconds"] - unit_origin, 3)
    track.update({
        "track_id": track_id,
        "motion_class": motion_class,
        "shot_uids": [uid],
        "generation_unit_ids": [unit_id],
        "source_basis": "Shot Contract, storyboard, V1, keyframe, K2 and P1",
        "confidence": "medium",
        "assumptions": ["visual-control intent, not measured engineering simulation"],
        "required_for_generation": True,
        "absolute_anchors": [
            {"time_seconds": shot_timing["start_seconds"], "state": "entry"},
            {"time_seconds": shot_timing["end_seconds"], "state": "exit"},
        ],
        "local_anchors": [
            {"time_seconds": local_start, "state": "entry"},
            {"time_seconds": local_end, "state": "exit"},
        ],
        "start_state": "stable initial state",
        "end_state": "explicit state at cut",
        "parameters": parameters_by_class[motion_class],
    })
    return seal(track)


def project_canon_artifacts(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = [manifest]
    for key in ("skip_record", "timing_animatic_v1"):
        value = manifest.get(key)
        if isinstance(value, dict):
            artifacts.append(value)
    for key in ("control_previs_v2_units", "motion_physics_tracks"):
        artifacts.extend(item for item in manifest.get(key, []) if isinstance(item, dict))
    return artifacts


def materialize_project_canon(package_root: Path, project_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Create a real post-delta Canon with file-bound source and owned artifacts."""

    artifacts: list[tuple[dict[str, Any], str, str, str]] = []
    source_slots = {
        "shot_contract": "professional_shot_contract",
        "storyboard": "storyboard_manifest",
        "keyframe_pack": "keyframe_continuity_manifest",
        "keyframe_boundary_supplement": "keyframe_boundary_supplement",
        "provider_preflight": "generation_unit_preflight_plan",
        "provider_capability": "provider_capability",
    }
    for name, reference in manifest["source_authorities"].items():
        if not isinstance(reference, dict):
            continue
        snapshot = json.loads((package_root / reference["snapshot_path"]).read_text(encoding="utf-8"))
        locator = f"project_artifacts/sources/{name}_{snapshot['artifact_id']}.json"
        write_json(project_root / locator, snapshot)
        artifacts.append((snapshot, locator, source_slots[name], locator))

    package_prefix = package_root.resolve().relative_to(project_root.resolve()).as_posix()
    for artifact in project_canon_artifacts(manifest):
        record_package_locator = f"00_manifest/owned_artifacts/{artifact['artifact_id']}.json"
        record_locator = f"{package_prefix}/{record_package_locator}"
        write_json(package_root / record_package_locator, artifact)
        if artifact is manifest:
            locator = f"{package_prefix}/00_manifest/PREVIS_MANIFEST.json"
            slot = "previs_manifest"
        elif artifact.get("phase") in {"timing_animatic_v1", "control_previs_v2"}:
            locator = f"{package_prefix}/{artifact['file_path']}"
            if artifact.get("phase") == "timing_animatic_v1":
                slot = "timing_animatic_v1"
            else:
                slot = f"control_previs_v2:{artifact['generation_unit_id']}"
        elif artifact.get("track_id") is not None:
            track_package_locator = f"03_motion/tracks/{artifact['track_id']}.json"
            write_json(package_root / track_package_locator, artifact)
            locator = f"{package_prefix}/{track_package_locator}"
            slot = f"motion_track:{artifact['track_id']}"
        else:
            locator = record_locator
            slot = "previs_skip"
        artifacts.append((artifact, locator, slot, record_locator))

    active: list[dict[str, Any]] = []
    dependency_edges: list[dict[str, Any]] = []
    for artifact, locator, slot, record_locator in artifacts:
        active.append({
            "artifact_slot": slot,
            "artifact_id": artifact["artifact_id"],
            "artifact_type": artifact.get("schema_version", artifact.get("phase", "previs_artifact")),
            "owner_skill": artifact["owner_skill"],
            "version": artifact["version"],
            "sha256": artifact["sha256"],
            "approval_status": artifact["approval_status"],
            "stale_reason": artifact["stale_reason"],
            "eligible_for_downstream": True,
            "affected_shot_uids": artifact["affected_shot_uids"],
            "locator": locator,
            "file_sha256": sha256_file(project_root / locator),
            "artifact_record_locator": record_locator,
            "artifact_record_file_sha256": sha256_file(project_root / record_locator),
            "dependencies": copy.deepcopy(artifact["dependencies"]),
        })
        for dependency in artifact["dependencies"]:
            dependency_edges.append({
                "producer_artifact_id": dependency["artifact_id"],
                "consumer_artifact_id": artifact["artifact_id"],
                "producer_sha256": dependency["sha256"],
                "affected_shot_uids": artifact["affected_shot_uids"],
            })

    superseded: list[dict[str, Any]] = []
    if manifest["delivery_stage"] == "control_previs_v2":
        previous = copy.deepcopy(manifest)
        previous.update({
            "artifact_id": "PREVIS_MANIFEST_V1_SUPERSEDED",
            "version": "0.9.0",
            "sha256": None,
            "dependencies": [
                dependency_from(manifest["source_authorities"]["shot_contract"]),
                dependency_from(manifest["source_authorities"]["storyboard"]),
            ],
            "delivery_stage": "timing_animatic_v1",
            "source_authorities": {
                "shot_contract": copy.deepcopy(manifest["source_authorities"]["shot_contract"]),
                "storyboard": copy.deepcopy(manifest["source_authorities"]["storyboard"]),
                "keyframe_pack": None,
                "keyframe_boundary_supplement": None,
                "provider_preflight": None,
                "provider_capability": None,
            },
            "input_file_evidence": [
                copy.deepcopy(item) for item in manifest["input_file_evidence"]
                if item["role"] in {"storyboard_frame", "storyboard_generation_prompt"}
            ],
            "control_previs_v2_units": [],
            "motion_physics_tracks": [],
            "generation_modes_used": ["deterministic_animatic"],
        })
        seal(previous)
        previous_locator = "project_artifacts/history/PREVIS_MANIFEST_V1_SUPERSEDED.json"
        write_json(project_root / previous_locator, previous)
        previous_record_locator = "project_artifacts/history/records/PREVIS_MANIFEST_V1_SUPERSEDED.json"
        write_json(project_root / previous_record_locator, previous)
        superseded.append({
            "artifact_slot": "previs_manifest",
            "artifact_id": previous["artifact_id"],
            "artifact_type": previous["schema_version"],
            "owner_skill": previous["owner_skill"],
            "version": previous["version"],
            "sha256": previous["sha256"],
            "approval_status": previous["approval_status"],
            "stale_reason": previous["stale_reason"],
            "eligible_for_downstream": False,
            "affected_shot_uids": previous["affected_shot_uids"],
            "locator": previous_locator,
            "file_sha256": sha256_file(project_root / previous_locator),
            "artifact_record_locator": previous_record_locator,
            "artifact_record_file_sha256": sha256_file(project_root / previous_record_locator),
            "dependencies": previous["dependencies"],
            "superseded_by_artifact_id": manifest["artifact_id"],
        })
        for dependency in previous["dependencies"]:
            dependency_edges.append({
                "producer_artifact_id": dependency["artifact_id"],
                "consumer_artifact_id": previous["artifact_id"],
                "producer_sha256": dependency["sha256"],
                "affected_shot_uids": previous["affected_shot_uids"],
            })

    canon = {
        "contract_version": "ai-video-artifact-v1",
        "artifact_id": f"PROJECT_CANON_MANIFEST_{manifest['project_id']}",
        "owner_skill": "ai-video-shot-script-director",
        "version": "1.0.0",
        "sha256": None,
        "approval_status": "assistant_validated",
        "dependencies": [],
        "affected_shot_uids": manifest["affected_shot_uids"],
        "stale_reason": None,
        "schema_version": "ai-video-project-canon-manifest.v1",
        "project_id": manifest["project_id"],
        "manifest_role": "artifact_registry_only",
        "manifest_update_policy": "validated_atomic_delta_no_reverse_dependency",
        "current_phase": "control_previs_v2" if manifest["delivery_stage"] == "control_previs_v2" else "timing_animatic_v1",
        "revision_counter": 1,
        "updated_by_skill": OWNER,
        "base_manifest_sha256": "8" * 64,
        "canonical_shot_uids": manifest["affected_shot_uids"],
        "active_artifacts": active,
        "superseded_artifacts": superseded,
        "dependency_edges": dependency_edges,
        "stale_events": [],
        "unresolved_change_requests": [],
    }
    canon["sha256"] = canonical_artifact_hash(canon)
    write_json(project_root / "00_project_canon/PROJECT_CANON_MANIFEST.json", canon)
    return canon


def write_package_reports(root: Path, manifest: dict[str, Any], canon: dict[str, Any]) -> None:
    registered = [manifest["artifact_id"]]
    for key in ("skip_record", "timing_animatic_v1"):
        value = manifest.get(key)
        if isinstance(value, dict):
            registered.append(value["artifact_id"])
    registered.extend(item["artifact_id"] for item in manifest.get("control_previs_v2_units", []))
    registered.extend(item["artifact_id"] for item in manifest.get("motion_physics_tracks", []))
    write_json(root / "00_manifest/MANIFEST_UPDATE_RECEIPT.json", {
        "schema_version": "ai-video-manifest-update-receipt.v1",
        "updated_by_skill": OWNER,
        "canonical_manifest_locator": "00_project_canon/PROJECT_CANON_MANIFEST.json",
        "base_manifest_sha256": canon["base_manifest_sha256"],
        "resulting_manifest_sha256": canon["sha256"],
        "registered_artifact_ids": registered,
        "delta_status": "applied",
    })
    if manifest["delivery_stage"] == "skipped_simple_single_shot":
        return
    write_json(root / "01_timing_animatic_v1/timing_map.json", {
        "timeline": manifest["timing_animatic_v1"]["timeline"],
        "source_artifact_id": manifest["timing_animatic_v1"]["artifact_id"],
    })
    qa = root / "04_qa"
    qa.mkdir(parents=True, exist_ok=True)
    write_json(qa / "timeline_validation.json", {"status": "passed", "validated_manifest_sha256": manifest["sha256"]})
    (qa / "control_boundary_report.md").write_text("All media probes and boundaries validated.\n", encoding="utf-8")
    if manifest["delivery_stage"] == "control_previs_v2":
        tracks = manifest["motion_physics_tracks"]
        write_json(root / "03_motion/camera_trajectory_map.json", {"tracks": [item for item in tracks if item["motion_class"] == "camera"]})
        write_json(root / "03_motion/blocking_map.json", {"tracks": [item for item in tracks if item["motion_class"] == "subject_blocking"]})
        write_json(root / "03_motion/motion_physics_tracks.json", {"tracks": tracks})


def create_active_package(
    root: Path,
    count: int,
    total: float,
    stage: str,
    provider_max: float = 15.0,
    include_physics: bool = False,
) -> dict[str, Any]:
    complete = stage == "control_previs_v2"
    uids = [f"SHT_{index:03d}" for index in range(1, count + 1)]
    durations = duration_plan(count, total)
    groups = unit_groups(uids, durations, provider_max) if complete else []
    source, evidence = make_sources(root, uids, durations, groups, provider_max, complete)
    v1 = make_v1(root, uids, durations, source)
    if complete:
        bind_v1_into_v2_sources(root, source, v1)
    unit_ids = [f"GU_{index:02d}" for index in range(1, len(groups) + 1)]
    uid_to_unit = {uid: unit_id for unit_id, (group_uids, _) in zip(unit_ids, groups) for uid in group_uids}
    unit_uids = {unit_id: group_uids for unit_id, (group_uids, _) in zip(unit_ids, groups)}
    tracks: list[dict[str, Any]] = []
    if complete and include_physics:
        for index, motion_class in enumerate(["liquid", "cloth", "hair"]):
            uid = uids[min(index, len(uids) - 1)]
            tracks.append(make_motion_track(
                f"TRK_{motion_class.upper()}", motion_class, uid, uid_to_unit[uid], v1, source,
                unit_uids[uid_to_unit[uid]],
            ))

    orders = {uid: index for index, uid in enumerate(uids, 1)}
    units: list[dict[str, Any]] = []
    for unit_id, (group_uids, group_durations) in zip(unit_ids, groups):
        rel = f"02_control_previs_v2/{unit_id}/control_previs_v2.mp4"
        local_timeline = make_timeline(group_uids, group_durations, orders)
        media_probe = write_test_video(root / rel, local_timeline)
        intersecting_tracks = [track for track in tracks if set(track["shot_uids"]) & set(group_uids)]
        deps = [
            dependency_from(source["shot_contract"]), dependency_from(source["storyboard"]),
            dependency_from(v1), dependency_from(source["keyframe_pack"]),
            dependency_from(source["keyframe_boundary_supplement"]), dependency_from(source["provider_preflight"]),
            dependency_from(source["provider_capability"]),
        ] + [dependency_from(track) for track in intersecting_tracks]
        target = round(sum(group_durations), 3)
        unit = envelope(f"CONTROL_PREVIS_{unit_id}", OWNER, group_uids, deps)
        unit.update({
            "phase": "control_previs_v2",
            "generation_unit_id": unit_id,
            "shot_uids": group_uids,
            "target_duration_seconds": target,
            "provider_max_duration_seconds": provider_max,
            "multimodal_reference_video_supported": True,
            "local_timeline": local_timeline,
            "file_path": rel,
            "file_sha256": sha256_file(root / rel),
            "actual_duration_seconds": media_probe["duration_seconds"],
            "media_probe": media_probe,
            "model_input_role": "control_reference_video",
            "is_model_input": True,
            "final_edit_asset": False,
            "silent": True,
            "render_style": "neutral_diagrammatic_or_simple_3d",
            "identity_authority": False,
            "look_authority": False,
            "control_dimensions": [
                "shot_boundaries", "target_timing", "camera_trajectory", "subject_blocking",
                "object_motion", "material_physics",
            ],
            "forbidden_dimensions": sorted(FORBIDDEN_DIMENSIONS),
            "motion_track_ids": [track["track_id"] for track in intersecting_tracks],
        })
        units.append(seal(unit))

    manifest = envelope(
        "PREVIS_MANIFEST", OWNER, uids,
        [dependency_from(item) for item in source.values() if isinstance(item, dict)],
    )
    manifest.update({
        "schema_version": "ai-video-timed-animatic-previs.v1",
        "project_id": f"FIXTURE_{count}_{stage}",
        "package_status": "assistant_validated",
        "delivery_stage": stage,
        "execution_mode": "active",
        "shot_count": count,
        "total_duration_seconds": total,
        "source_authorities": source,
        "input_file_evidence": evidence,
        "skip_record": None,
        "timing_animatic_v1": v1,
        "control_previs_v2_units": units,
        "motion_physics_tracks": tracks,
        "generation_modes_used": ["deterministic_animatic"] + (["neutral_3d_blocking"] if complete else []),
        "forbidden_generation_modes": [
            "text_to_video", "first_last_frame", "standalone_single_image_to_video",
        ],
        "downstream_invalidations": [],
    })
    seal(manifest)
    write_json(root / "00_manifest/PREVIS_MANIFEST.json", manifest)
    canon = materialize_project_canon(root, root.parent, manifest)
    write_package_reports(root, manifest, canon)
    return manifest


def create_skip_package(root: Path) -> dict[str, Any]:
    uid = "SHT_001"
    durations = [5.0]
    source, _ = make_sources(root, [uid], durations, [], 15.0, False)
    deps = [dependency_from(source["shot_contract"]), dependency_from(source["storyboard"])]
    skip = envelope("PREVIS_SKIP", OWNER, [uid], deps)
    skip.update({
        "reason": "static_or_near_static_single_shot",
        "previs_needed": False,
        "complexity_flags": {
            "complex_camera": False, "multi_subject_blocking": False,
            "consequential_object_motion": False, "liquid_motion": False, "cloth_motion": False,
            "hair_motion": False, "smoke_or_particles": False, "timing_sensitive_transition": False,
        },
    })
    seal(skip)
    manifest = envelope("PREVIS_MANIFEST", OWNER, [uid], deps)
    manifest.update({
        "schema_version": "ai-video-timed-animatic-previs.v1",
        "project_id": "FIXTURE_SKIP",
        "package_status": "assistant_validated",
        "delivery_stage": "skipped_simple_single_shot",
        "execution_mode": "skipped_simple_single_shot",
        "shot_count": 1,
        "total_duration_seconds": 5.0,
        "source_authorities": source,
        "input_file_evidence": [],
        "skip_record": skip,
        "timing_animatic_v1": None,
        "control_previs_v2_units": [],
        "motion_physics_tracks": [],
        "generation_modes_used": [],
        "forbidden_generation_modes": [
            "text_to_video", "first_last_frame", "standalone_single_image_to_video",
        ],
        "downstream_invalidations": [],
    })
    seal(manifest)
    write_json(root / "00_manifest/PREVIS_MANIFEST.json", manifest)
    canon = materialize_project_canon(root, root.parent, manifest)
    write_package_reports(root, manifest, canon)
    return manifest


def save(root: Path, data: dict[str, Any], reseal: bool = True) -> None:
    if reseal and data.get("approval_status") != "draft":
        data["sha256"] = canonical_artifact_hash(data)
    write_json(root / "00_manifest/PREVIS_MANIFEST.json", data)


def expect_valid(name: str, root: Path) -> None:
    project_root = root.parent
    canon = json.loads((project_root / "00_project_canon/PROJECT_CANON_MANIFEST.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "00_manifest/PREVIS_MANIFEST.json").read_text(encoding="utf-8"))
    schema_errors = validate_instance(manifest, PREVIS_SCHEMA, PREVIS_SCHEMA)
    if schema_errors:
        raise AssertionError(f"{name} schema expected valid, got {schema_errors}")
    errors = validate_package(root, canon_manifest=canon, project_root=project_root)
    if errors:
        raise AssertionError(f"{name} expected valid, got {errors}")


def expect_invalid(name: str, root: Path, needle: str, ffprobe_binary: str = "ffprobe") -> None:
    project_root = root.parent
    canon_path = project_root / "00_project_canon/PROJECT_CANON_MANIFEST.json"
    canon = json.loads(canon_path.read_text(encoding="utf-8")) if canon_path.is_file() else None
    errors = validate_package(root, ffprobe_binary, canon, project_root if canon is not None else project_root)
    if not any(needle in error for error in errors):
        raise AssertionError(f"{name} expected {needle!r}, got {errors}")


def expect_invalid_all(
    name: str, root: Path, needles: list[str], ffprobe_binary: str = "ffprobe"
) -> None:
    project_root = root.parent
    canon_path = project_root / "00_project_canon/PROJECT_CANON_MANIFEST.json"
    canon = json.loads(canon_path.read_text(encoding="utf-8")) if canon_path.is_file() else None
    errors = validate_package(root, ffprobe_binary, canon, project_root)
    missing = [needle for needle in needles if not any(needle in error for error in errors)]
    if missing:
        raise AssertionError(f"{name} expected {missing!r}, got {errors}")


def mutate_fixture(
    base: Path,
    target_project_root: Path,
    mutator: Callable[[Path, dict[str, Any]], None],
) -> Path:
    shutil.copytree(base.parent, target_project_root)
    target = target_project_root / base.name
    data = json.loads((target / "00_manifest/PREVIS_MANIFEST.json").read_text(encoding="utf-8"))
    mutator(target, data)
    save(target, data)
    return target


def smoke_test_v1_builder(root: Path) -> None:
    package_root = root / "previs-package"
    frame_rel = "02_frames/SHT_001.ppm"
    frame_path = root / "storyboard" / frame_rel
    # Valid 2x2 PPM, kept tiny so the deterministic builder test is cheap.
    frame_hash = write_bytes(frame_path, b"P6\n2 2\n255\n" + bytes([255, 0, 0] * 4))
    storyboard_path = root / "storyboard/00_manifest/STORYBOARD_MANIFEST.json"
    write_json(storyboard_path, {
        "frames": [{"shot_uid": "SHT_001", "file_path": frame_rel, "file_sha256": frame_hash}],
    })
    timeline = make_timeline(["SHT_001"], [0.5])
    previs_path = package_root / "00_manifest/PREVIS_MANIFEST.json"
    write_json(previs_path, {"timing_animatic_v1": {"timeline": timeline}})
    output_rel = "01_timing_animatic_v1/timing_animatic_v1.mp4"
    result = subprocess.run(
        [
            sys.executable, str(HERE / "build_timing_animatic.py"),
            "storyboard/00_manifest/STORYBOARD_MANIFEST.json",
            str(previs_path), output_rel, "--project-root", str(root), "--fps", "25",
        ],
        cwd=root, text=True, capture_output=True, timeout=120, check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"V1 builder smoke test failed: {result.stdout}{result.stderr}")
    built = json.loads(result.stdout)
    if built.get("file_path") != output_rel:
        raise AssertionError("V1 builder must emit a project-relative output path")
    probe = built.get("media_probe")
    if not isinstance(probe, dict) or probe.get("decoded_video_frame_count", 0) < 1 or probe.get("decoded_video_packet_count", 0) < 1:
        raise AssertionError("V1 builder must emit live decoded frame/packet evidence")
    if probe.get("shot_chapters") != [{"shot_uid": "SHT_001", "start_seconds": 0.0, "end_seconds": 0.5}]:
        raise AssertionError("V1 builder must embed exact Shot UID chapter boundaries")

    equal_root_manifest = root / "00_manifest/PREVIS_MANIFEST.json"
    write_json(equal_root_manifest, {"timing_animatic_v1": {"timeline": timeline}})
    equal_root = subprocess.run(
        [
            sys.executable, str(HERE / "build_timing_animatic.py"),
            "storyboard/00_manifest/STORYBOARD_MANIFEST.json", str(equal_root_manifest),
            "equal-root.mp4", "--project-root", str(root),
        ],
        cwd=root, text=True, capture_output=True, timeout=120, check=False,
    )
    if equal_root.returncode == 0 or "strict child" not in (equal_root.stdout + equal_root.stderr):
        raise AssertionError("V1 builder must reject package_root == project_root")


def main() -> int:
    json.loads((SKILL_ROOT / "references/previs_manifest.schema.json").read_text(encoding="utf-8"))
    json.loads((SKILL_ROOT / "references/previs_manifest_template.json").read_text(encoding="utf-8"))
    provider_template = json.loads((SKILL_ROOT / "references/provider_runtime_capability_evidence.template.json").read_text(encoding="utf-8"))
    provider_template_errors = validate_instance(provider_template, PROVIDER_EVIDENCE_SCHEMA, PROVIDER_EVIDENCE_SCHEMA)
    if provider_template_errors:
        raise AssertionError(f"provider runtime evidence template violates schema: {provider_template_errors}")
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        smoke_test_v1_builder(root / "builder_smoke")
        skip = root / "skip/previs-package"
        create_skip_package(skip)
        expect_valid("single skip", skip)
        v1_only = root / "v1_only/previs-package"
        create_active_package(v1_only, 3, 15.0, "timing_animatic_v1")
        expect_valid("V1 structure-stage real media", v1_only)
        cli = subprocess.run(
            [
                sys.executable, str(HERE / "validate_previs_package.py"), str(v1_only),
                "--project-root", str(v1_only.parent),
                "--project-canon-manifest", str(v1_only.parent / "00_project_canon/PROJECT_CANON_MANIFEST.json"),
            ],
            text=True, capture_output=True, timeout=120, check=False,
        )
        if cli.returncode != 0:
            raise AssertionError(f"Canon-bound validator CLI expected valid, got {cli.stdout}{cli.stderr}")
        cli_missing_project_root = subprocess.run(
            [
                sys.executable, str(HERE / "validate_previs_package.py"), str(v1_only),
                "--project-canon-manifest", str(v1_only.parent / "00_project_canon/PROJECT_CANON_MANIFEST.json"),
            ],
            text=True, capture_output=True, timeout=120, check=False,
        )
        if cli_missing_project_root.returncode == 0 or "--project-root is required" not in cli_missing_project_root.stdout:
            raise AssertionError("validator CLI must require explicit project_root for Canon locator resolution")
        v1_canon = json.loads((v1_only.parent / "00_project_canon/PROJECT_CANON_MANIFEST.json").read_text(encoding="utf-8"))
        outside_errors = validate_package(v1_only, canon_manifest=v1_canon, project_root=root / "unrelated_project")
        if not any("package_root must be contained by project_root" in item for item in outside_errors):
            raise AssertionError(f"package/project containment expected failure, got {outside_errors}")
        equal_root_errors = validate_package(v1_only, canon_manifest=v1_canon, project_root=v1_only)
        if not any("strict child" in item for item in equal_root_errors):
            raise AssertionError(f"package/project equality expected failure, got {equal_root_errors}")
        p3 = root / "complete_3/previs-package"
        create_active_package(p3, 3, 15.0, "control_previs_v2", 15.0, include_physics=True)
        expect_valid("15s N=3 V2 physics real media", p3)

        def mutate_authority(
            fixture: Path,
            data: dict[str, Any],
            authority_name: str,
            mutate: Callable[[dict[str, Any]], None],
        ) -> None:
            ref = data["source_authorities"][authority_name]
            path = fixture / ref["snapshot_path"]
            source = json.loads(path.read_text(encoding="utf-8"))
            mutate(source)
            seal(source)
            write_json(path, source)
            ref.update({
                "owner_skill": source["owner_skill"], "version": source["version"],
                "sha256": source["sha256"], "snapshot_file_sha256": sha256_file(path),
            })
            for dependency in data["dependencies"]:
                if dependency["artifact_id"] == ref["artifact_id"]:
                    dependency.update(dependency_from(ref))

        expect_invalid(
            "P1 dependencies cannot be emptied even when resealed",
            mutate_fixture(
                p3, root / "bad_empty_p1_dependencies",
                lambda fixture, data: mutate_authority(fixture, data, "provider_preflight", lambda value: value.update({"dependencies": []})),
            ),
            "Prompt preflight: missing required dependency records",
        )
        expect_invalid(
            "K2 dependencies must exactly bind K1 and P1",
            mutate_fixture(
                p3, root / "bad_empty_k2_dependencies",
                lambda fixture, data: mutate_authority(fixture, data, "keyframe_boundary_supplement", lambda value: value.update({"dependencies": []})),
            ),
            "K2 Boundary Supplement: missing required dependency records",
        )
        expect_invalid(
            "P1 owner is fixed",
            mutate_fixture(
                p3, root / "bad_p1_owner",
                lambda fixture, data: mutate_authority(fixture, data, "provider_preflight", lambda value: value.update({"owner_skill": "untrusted-skill"})),
            ),
            "owner_skill must be ai-video-omni-reference-prompt-director",
        )
        expect_invalid(
            "P1 schema is fixed",
            mutate_fixture(
                p3, root / "bad_p1_schema",
                lambda fixture, data: mutate_authority(fixture, data, "provider_preflight", lambda value: value.update({"schema_version": "garbage"})),
            ),
            "schema_version must be ai-video-generation-unit-preflight.v1",
        )
        expect_invalid(
            "K2 owner is fixed",
            mutate_fixture(
                p3, root / "bad_k2_owner",
                lambda fixture, data: mutate_authority(fixture, data, "keyframe_boundary_supplement", lambda value: value.update({"owner_skill": "untrusted-skill"})),
            ),
            "owner_skill must be ai-video-keyframe-continuity-pack",
        )
        expect_invalid(
            "K2 schema is fixed",
            mutate_fixture(
                p3, root / "bad_k2_schema",
                lambda fixture, data: mutate_authority(fixture, data, "keyframe_boundary_supplement", lambda value: value.update({"schema_version": "garbage"})),
            ),
            "schema_version must be ai-video-keyframe-boundary-supplement.v1",
        )
        p7 = root / "complete_7/previs-package"
        create_active_package(p7, 7, 30.0, "control_previs_v2", 30.0)
        expect_valid("30s N=7 one unit", p7)
        p15 = root / "complete_15/previs-package"
        create_active_package(p15, 15, 30.0, "control_previs_v2", 15.0)
        expect_valid("30s N=15 split units", p15)
        p17 = root / "complete_17/previs-package"
        create_active_package(p17, 17, 30.0, "control_previs_v2", 10.0)
        expect_valid("N=17 multi-unit", p17)

        expect_invalid(
            "multi-shot skip",
            mutate_fixture(skip, root / "bad_skip", lambda _root, data: data.__setitem__("shot_count", 2)),
            "exactly one shot",
        )

        def v1_gap(_fixture: Path, data: dict[str, Any]) -> None:
            data["timing_animatic_v1"]["timeline"][1]["start_seconds"] += 0.25
            seal(data["timing_animatic_v1"])
        expect_invalid("V1 gap", mutate_fixture(v1_only, root / "bad_gap", v1_gap), "gap or overlap")

        def arbitrary_binary(fixture: Path, data: dict[str, Any]) -> None:
            v1 = data["timing_animatic_v1"]
            path = fixture / v1["file_path"]
            path.write_bytes(b"NOT A VIDEO")
            v1["file_sha256"] = sha256_file(path)
            seal(v1)
        expect_invalid("arbitrary binary rejected", mutate_fixture(v1_only, root / "bad_binary", arbitrary_binary), "live media probe failed closed")

        def fake_duration(_fixture: Path, data: dict[str, Any]) -> None:
            v1 = data["timing_animatic_v1"]
            v1["actual_duration_seconds"] = 14.0
            v1["media_probe"]["duration_seconds"] = 14.0
            seal(v1)
        expect_invalid("self-reported duration rejected", mutate_fixture(v1_only, root / "bad_fake_duration", fake_duration), "differs from live")

        def fake_resolution(_fixture: Path, data: dict[str, Any]) -> None:
            v1 = data["timing_animatic_v1"]
            v1["media_probe"]["width_pixels"] = 1920
            seal(v1)
        expect_invalid("self-reported resolution rejected", mutate_fixture(v1_only, root / "bad_resolution", fake_resolution), "width_pixels differs from live")

        def fake_frame_rate(_fixture: Path, data: dict[str, Any]) -> None:
            v1 = data["timing_animatic_v1"]
            v1["media_probe"]["frame_rate"] = "24/1"
            seal(v1)
        expect_invalid("self-reported frame rate rejected", mutate_fixture(v1_only, root / "bad_fps", fake_frame_rate), "frame_rate differs from live")

        def fake_packet_count(_fixture: Path, data: dict[str, Any]) -> None:
            v1 = data["timing_animatic_v1"]
            v1["media_probe"]["decoded_video_packet_count"] += 1
            seal(v1)
        expect_invalid("self-reported packet evidence rejected", mutate_fixture(v1_only, root / "bad_packets", fake_packet_count), "decoded_video_packet_count differs from live")

        def wrong_live_boundaries(fixture: Path, data: dict[str, Any]) -> None:
            unit = data["control_previs_v2_units"][0]
            wrong = copy.deepcopy(unit["local_timeline"])
            first_duration = wrong[0]["duration_seconds"]
            wrong[0]["end_seconds"] = round(first_duration + 0.2, 3)
            wrong[1]["start_seconds"] = wrong[0]["end_seconds"]
            wrong[1]["duration_seconds"] = round(wrong[1]["end_seconds"] - wrong[1]["start_seconds"], 3)
            media_path = fixture / unit["file_path"]
            live = write_test_video(media_path, wrong)
            unit["file_sha256"] = sha256_file(media_path)
            unit["actual_duration_seconds"] = live["duration_seconds"]
            unit["media_probe"] = live
            seal(unit)
        expect_invalid("live chapter boundary mismatch", mutate_fixture(p3, root / "bad_live_boundary", wrong_live_boundaries), "do not exactly encode manifest boundaries")

        def path_escape(_fixture: Path, data: dict[str, Any]) -> None:
            v1 = data["timing_animatic_v1"]
            v1["file_path"] = "../outside.mp4"
            seal(v1)
        expect_invalid("media path traversal", mutate_fixture(v1_only, root / "bad_path", path_escape), "escapes package root")

        def input_path_escape(_fixture: Path, data: dict[str, Any]) -> None:
            data["input_file_evidence"][0]["copied_file_path"] = "../../outside.png"
        expect_invalid("input path traversal", mutate_fixture(v1_only, root / "bad_input_path", input_path_escape), "escapes package root")

        def tamper_prompt(fixture: Path, data: dict[str, Any]) -> None:
            record = next(item for item in data["input_file_evidence"] if item["role"] == "storyboard_generation_prompt")
            (fixture / record["copied_file_path"]).write_text("tampered", encoding="utf-8")
        expect_invalid("input prompt bytes rehashed", mutate_fixture(v1_only, root / "bad_prompt_hash", tamper_prompt), "copied input file_sha256 mismatch")

        def tamper_keyframe_prompt(fixture: Path, data: dict[str, Any]) -> None:
            record = next(item for item in data["input_file_evidence"] if item["role"] == "keyframe_generation_prompt")
            (fixture / record["copied_file_path"]).write_text("tampered keyframe prompt", encoding="utf-8")
        expect_invalid("keyframe prompt bytes rehashed", mutate_fixture(p3, root / "bad_keyframe_prompt_hash", tamper_keyframe_prompt), "copied input file_sha256 mismatch")

        def tamper_source_snapshot(fixture: Path, data: dict[str, Any]) -> None:
            ref = data["source_authorities"]["shot_contract"]
            snapshot = json.loads((fixture / ref["snapshot_path"]).read_text(encoding="utf-8"))
            snapshot["timeline"]["total_duration_seconds"] = 99.0
            write_json(fixture / ref["snapshot_path"], snapshot)
        expect_invalid("source snapshot bytes rehashed", mutate_fixture(v1_only, root / "bad_source_hash", tamper_source_snapshot), "snapshot_file_sha256 mismatch")

        def forge_self_consistent_source(fixture: Path, data: dict[str, Any]) -> None:
            ref = data["source_authorities"]["shot_contract"]
            path = fixture / ref["snapshot_path"]
            source = json.loads(path.read_text(encoding="utf-8"))
            source["version"] = "9.0.0"
            seal(source)
            write_json(path, source)
            ref.update({
                "version": source["version"],
                "sha256": source["sha256"],
                "snapshot_file_sha256": sha256_file(path),
            })
            for artifact in [data, data["timing_animatic_v1"]]:
                for dep in artifact["dependencies"]:
                    if dep["artifact_id"] == ref["artifact_id"]:
                        dep.update({"version": ref["version"], "sha256": ref["sha256"]})
                if artifact is not data:
                    seal(artifact)
        expect_invalid(
            "self-consistent fake authority rejected by Canon",
            mutate_fixture(v1_only, root / "bad_fake_authority", forge_self_consistent_source),
            "Canon version differs from artifact",
        )

        no_canon_project = root / "bad_missing_canon"
        shutil.copytree(v1_only.parent, no_canon_project)
        no_canon = no_canon_project / "previs-package"
        (no_canon_project / "00_project_canon/PROJECT_CANON_MANIFEST.json").unlink()
        expect_invalid("approved package requires actual Canon", no_canon, "requires the actual Project Canon manifest")

        def canon_locator_escape(fixture: Path, _data: dict[str, Any]) -> None:
            path = fixture.parent / "00_project_canon/PROJECT_CANON_MANIFEST.json"
            canon = json.loads(path.read_text(encoding="utf-8"))
            entry = next(item for item in canon["active_artifacts"] if item["artifact_id"] == "SHOT_CONTRACT")
            entry["locator"] = "../outside.json"
            canon["sha256"] = canonical_artifact_hash(canon)
            write_json(path, canon)
        expect_invalid(
            "Canon locator escape rejected",
            mutate_fixture(v1_only, root / "bad_canon_locator", canon_locator_escape),
            "locator must be a safe project-relative path",
        )

        def canon_slot_alias(fixture: Path, _data: dict[str, Any]) -> None:
            path = fixture.parent / "00_project_canon/PROJECT_CANON_MANIFEST.json"
            canon = json.loads(path.read_text(encoding="utf-8"))
            entry = next(item for item in canon["active_artifacts"] if item["artifact_id"] == "PROVIDER_PREFLIGHT")
            entry["artifact_slot"] = "prompt_preflight_ir"
            canon["sha256"] = canonical_artifact_hash(canon)
            write_json(path, canon)
        expect_invalid(
            "P1 legacy slot alias rejected",
            mutate_fixture(p3, root / "bad_p1_slot_alias", canon_slot_alias),
            "Canon artifact_slot must be generation_unit_preflight_plan",
        )

        def previs_root_slot_drift(fixture: Path, data: dict[str, Any]) -> None:
            path = fixture.parent / "00_project_canon/PROJECT_CANON_MANIFEST.json"
            canon = json.loads(path.read_text(encoding="utf-8"))
            entry = next(item for item in canon["active_artifacts"] if item["artifact_id"] == data["artifact_id"])
            entry["artifact_slot"] = "control_previs_v2_manifest"
            canon["sha256"] = canonical_artifact_hash(canon)
            write_json(path, canon)
        expect_invalid(
            "Previs root unstable slot rejected",
            mutate_fixture(p3, root / "bad_previs_root_slot", previs_root_slot_drift),
            "replacement must preserve artifact_slot",
        )

        def drop_v1_predecessor(fixture: Path, _data: dict[str, Any]) -> None:
            path = fixture.parent / "00_project_canon/PROJECT_CANON_MANIFEST.json"
            canon = json.loads(path.read_text(encoding="utf-8"))
            canon["superseded_artifacts"] = []
            canon["sha256"] = canonical_artifact_hash(canon)
            write_json(path, canon)
        expect_invalid(
            "V2 requires versioned V1 root predecessor",
            mutate_fixture(p3, root / "bad_missing_v1_predecessor", drop_v1_predecessor),
            "endpoints must be known active or superseded artifacts",
        )

        def v1_primary_record_conflated(fixture: Path, _data: dict[str, Any]) -> None:
            path = fixture.parent / "00_project_canon/PROJECT_CANON_MANIFEST.json"
            canon = json.loads(path.read_text(encoding="utf-8"))
            entry = next(item for item in canon["active_artifacts"] if item["artifact_slot"] == "timing_animatic_v1")
            entry["locator"] = entry["artifact_record_locator"]
            entry["file_sha256"] = entry["artifact_record_file_sha256"]
            canon["sha256"] = canonical_artifact_hash(canon)
            write_json(path, canon)
        expect_invalid(
            "media primary and artifact record cannot be conflated",
            mutate_fixture(p3, root / "bad_primary_record_conflation", v1_primary_record_conflated),
            "Canon primary locator differs from artifact primary file",
        )

        def corrupt_motion_primary(fixture: Path, data: dict[str, Any]) -> None:
            track = data["motion_physics_tracks"][0]
            canon_path = fixture.parent / "00_project_canon/PROJECT_CANON_MANIFEST.json"
            canon = json.loads(canon_path.read_text(encoding="utf-8"))
            entry = next(item for item in canon["active_artifacts"] if item["artifact_id"] == track["artifact_id"])
            primary = fixture.parent / entry["locator"]
            write_json(primary, {"arbitrary": "not the motion artifact"})
            entry["file_sha256"] = sha256_file(primary)
            canon["sha256"] = canonical_artifact_hash(canon)
            write_json(canon_path, canon)
        expect_invalid(
            "motion primary JSON must equal record",
            mutate_fixture(p3, root / "bad_motion_primary", corrupt_motion_primary),
            "motion-track primary JSON differs from artifact record",
        )

        def receipt_drift(fixture: Path, _data: dict[str, Any]) -> None:
            path = fixture / "00_manifest/MANIFEST_UPDATE_RECEIPT.json"
            receipt = json.loads(path.read_text(encoding="utf-8"))
            receipt["resulting_manifest_sha256"] = "3" * 64
            write_json(path, receipt)
        expect_invalid(
            "receipt must bind post Canon",
            mutate_fixture(v1_only, root / "bad_receipt", receipt_drift),
            "resulting_manifest_sha256 must equal canonical manifest sha256",
        )

        def structure_storyboard_in_v2(fixture: Path, data: dict[str, Any]) -> None:
            ref = data["source_authorities"]["storyboard"]
            path = fixture / ref["snapshot_path"]
            source = json.loads(path.read_text(encoding="utf-8"))
            source["storyboard_stage"] = "structure_draft"
            for frame in source["frames"]:
                frame["stage"] = "structure_draft"
                frame["is_model_input_eligible"] = False
            seal(source)
            write_json(path, source)
            ref.update({"sha256": source["sha256"], "snapshot_file_sha256": sha256_file(path)})
            for dep in data["dependencies"]:
                if dep["artifact_id"] == ref["artifact_id"]:
                    dep["sha256"] = ref["sha256"]
        expect_invalid("V2 rejects structure storyboard", mutate_fixture(p3, root / "bad_v2_storyboard_stage", structure_storyboard_in_v2), "requires look_applied_final")

        def provider_limit_drift(_fixture: Path, data: dict[str, Any]) -> None:
            unit = data["control_previs_v2_units"][0]
            unit["provider_max_duration_seconds"] = 30.0
            seal(unit)
        expect_invalid("provider self-report rejected", mutate_fixture(p3, root / "bad_provider_limit", provider_limit_drift), "provider max differs")

        def provider_profile_without_matching_snapshot(fixture: Path, data: dict[str, Any]) -> None:
            ref = data["source_authorities"]["provider_capability"]
            path = fixture / ref["snapshot_path"]
            source = json.loads(path.read_text(encoding="utf-8"))
            source["profiles"][0]["effective_limits"]["max_duration_seconds"] = 30.0
            seal(source)
            write_json(path, source)
            ref.update({"sha256": source["sha256"], "snapshot_file_sha256": sha256_file(path)})
            for dep in data["dependencies"]:
                if dep["artifact_id"] == ref["artifact_id"]:
                    dep["sha256"] = ref["sha256"]
        expect_invalid(
            "provider profile cannot outrun local schema snapshot",
            mutate_fixture(p3, root / "bad_provider_snapshot_projection", provider_profile_without_matching_snapshot),
            "snapshot effective_limits differs from runtime profile",
        )

        def provider_video_projection_drift(fixture: Path, data: dict[str, Any]) -> None:
            mutate_authority(
                fixture,
                data,
                "provider_capability",
                lambda value: value["profiles"][0]["input_constraints"]["video"].update({
                    "accepted_video_codecs": ["hevc"],
                }),
            )

        expect_invalid(
            "provider video constraints require exact local projection",
            mutate_fixture(
                p3, root / "bad_provider_video_projection", provider_video_projection_drift,
            ),
            "snapshot video_input_constraints differs from runtime profile",
        )

        def provider_live_video_constraints(fixture: Path, data: dict[str, Any]) -> None:
            ref = data["source_authorities"]["provider_capability"]
            source_path = fixture / ref["snapshot_path"]
            source = json.loads(source_path.read_text(encoding="utf-8"))
            profile = source["profiles"][0]
            video = profile["input_constraints"]["video"]
            video.update({
                "accepted_media_types": ["video/webm"],
                "accepted_containers": ["webm"],
                "accepted_video_codecs": ["vp9"],
                "max_file_bytes": 1,
                "min_duration_seconds": 20.0,
                "max_duration_seconds": 30.0,
                "min_width_px": 128,
                "min_height_px": 64,
                "min_aspect_ratio": 2.0,
                "min_fps": 30.0,
                "audio_track_policy": "required",
            })
            evidence_record = next(
                item for item in data["input_file_evidence"]
                if item["role"] == "provider_schema_snapshot"
            )
            projection_path = fixture / evidence_record["copied_file_path"]
            projection = json.loads(projection_path.read_text(encoding="utf-8"))
            projection["video_input_constraints"] = copy.deepcopy(video)
            projection_bytes = json.dumps(projection, sort_keys=True).encode("utf-8")
            projection_hash = write_bytes(projection_path, projection_bytes)
            evidence_record["file_sha256"] = projection_hash
            evidence_record["upstream_declared_file_sha256"] = projection_hash
            profile["evidence"][0]["snapshot_file_sha256"] = projection_hash
            seal(source)
            write_json(source_path, source)
            ref.update({
                "sha256": source["sha256"],
                "snapshot_file_sha256": sha256_file(source_path),
            })
            for dependency in data["dependencies"]:
                if dependency["artifact_id"] == ref["artifact_id"]:
                    dependency.update(dependency_from(ref))

        constrained = mutate_fixture(
            p3, root / "bad_live_provider_video_constraints", provider_live_video_constraints,
        )
        expect_invalid_all(
            "live ffprobe must satisfy every projected provider video input constraint",
            constrained,
            [
                "live media type is outside provider video input constraints",
                "live container is outside provider video input constraints",
                "live video codec is outside provider video input constraints",
                "live file bytes exceed provider video input constraints",
                "live duration is below provider video input constraints",
                "live width is below provider video input constraints",
                "live height is below provider video input constraints",
                "live aspect ratio is below provider video input constraints",
                "live frame rate is below provider video input constraints",
                "provider video input constraints require an audio track",
            ],
        )

        def missing_provider_cap(_fixture: Path, data: dict[str, Any]) -> None:
            data["source_authorities"]["provider_capability"] = None
        expect_invalid("provider capability required", mutate_fixture(p3, root / "bad_provider_cap", missing_provider_cap), "requires core keyframe")

        def v1_keyframe_dep(_fixture: Path, data: dict[str, Any]) -> None:
            data["timing_animatic_v1"]["dependencies"].append(dependency_from(data["source_authorities"]["keyframe_pack"] or data["source_authorities"]["shot_contract"]))
            seal(data["timing_animatic_v1"])
        expect_invalid("V1 extra dependency", mutate_fixture(v1_only, root / "bad_v1_dep", v1_keyframe_dep), "exactly equal required authorities")

        def v1_claims_downstream_authority(_fixture: Path, data: dict[str, Any]) -> None:
            data["source_authorities"]["keyframe_pack"] = copy.deepcopy(data["source_authorities"]["shot_contract"])
        expect_invalid(
            "V1 stage cannot claim K1/P1/provider",
            mutate_fixture(v1_only, root / "bad_v1_downstream_authority", v1_claims_downstream_authority),
            "V1-ready stage must not bind K1/K2/P1/provider authorities",
        )

        def root_extra(_fixture: Path, data: dict[str, Any]) -> None:
            data["surprise"] = True
        expect_invalid("root extra field", mutate_fixture(v1_only, root / "bad_root_extra", root_extra), "extra fields forbidden")

        def v1_extra(_fixture: Path, data: dict[str, Any]) -> None:
            data["timing_animatic_v1"]["surprise"] = True
            seal(data["timing_animatic_v1"])
        expect_invalid("V1 extra field", mutate_fixture(v1_only, root / "bad_v1_extra", v1_extra), "extra fields forbidden")

        def unit_extra(_fixture: Path, data: dict[str, Any]) -> None:
            data["control_previs_v2_units"][0]["surprise"] = True
            seal(data["control_previs_v2_units"][0])
        expect_invalid("V2 extra field", mutate_fixture(p3, root / "bad_unit_extra", unit_extra), "extra fields forbidden")

        def timeline_extra(_fixture: Path, data: dict[str, Any]) -> None:
            data["timing_animatic_v1"]["timeline"][0]["surprise"] = True
            seal(data["timing_animatic_v1"])
        expect_invalid("timeline extra field", mutate_fixture(v1_only, root / "bad_timeline_extra", timeline_extra), "extra fields forbidden")

        def probe_extra(_fixture: Path, data: dict[str, Any]) -> None:
            data["timing_animatic_v1"]["media_probe"]["surprise"] = True
            seal(data["timing_animatic_v1"])
        expect_invalid("probe extra field", mutate_fixture(v1_only, root / "bad_probe_extra", probe_extra), "extra fields forbidden")

        def authority_extra(_fixture: Path, data: dict[str, Any]) -> None:
            data["source_authorities"]["shot_contract"]["surprise"] = True
        expect_invalid("authority extra field", mutate_fixture(v1_only, root / "bad_authority_extra", authority_extra), "extra fields forbidden")

        def bad_liquid(_fixture: Path, data: dict[str, Any]) -> None:
            track = next(item for item in data["motion_physics_tracks"] if item["motion_class"] == "liquid")
            del track["parameters"]["volume_continuity"]
            seal(track)
            unit = next(item for item in data["control_previs_v2_units"] if track["track_id"] in item["motion_track_ids"])
            for dep in unit["dependencies"]:
                if dep["artifact_id"] == track["artifact_id"]:
                    dep["sha256"] = track["sha256"]
            seal(unit)
        expect_invalid("liquid physics", mutate_fixture(p3, root / "bad_liquid", bad_liquid), "liquid parameters missing")

        def motion_extra(_fixture: Path, data: dict[str, Any]) -> None:
            track = data["motion_physics_tracks"][0]
            track["surprise"] = True
            seal(track)
        expect_invalid("motion root extra field", mutate_fixture(p3, root / "bad_motion_extra", motion_extra), "extra fields forbidden")

        def motion_parameter_extra(_fixture: Path, data: dict[str, Any]) -> None:
            track = data["motion_physics_tracks"][0]
            track["parameters"]["invented_parameter"] = "forbidden"
            seal(track)
        expect_invalid("motion parameter extra field", mutate_fixture(p3, root / "bad_motion_parameter_extra", motion_parameter_extra), "parameters contain forbidden extras")

        def motion_wrong_dependency(_fixture: Path, data: dict[str, Any]) -> None:
            track = data["motion_physics_tracks"][0]
            track["dependencies"] = track["dependencies"][:-1]
            seal(track)
        expect_invalid("motion exact dependencies", mutate_fixture(p3, root / "bad_motion_dep", motion_wrong_dependency), "dependency records must exactly equal required authorities")

        def motion_anchor_outside(_fixture: Path, data: dict[str, Any]) -> None:
            track = data["motion_physics_tracks"][0]
            track["absolute_anchors"][0]["time_seconds"] = 99.0
            seal(track)
        expect_invalid("motion anchor timing", mutate_fixture(p3, root / "bad_motion_anchor", motion_anchor_outside), "absolute anchor is outside affected Shot timing")

        def use_t2v(_fixture: Path, data: dict[str, Any]) -> None:
            data["generation_modes_used"].append("text_to_video")
        expect_invalid("T2V fallback", mutate_fixture(p3, root / "bad_t2v", use_t2v), "prohibited mode")

        def use_classic_i2v(_fixture: Path, data: dict[str, Any]) -> None:
            data["generation_modes_used"].append("standalone_single_image_to_video")
        expect_invalid(
            "standalone classic single-image I2V fallback",
            mutate_fixture(p3, root / "bad_classic_i2v", use_classic_i2v),
            "standalone single-image I2V generation are forbidden",
        )

        def omit_classic_i2v_deny(_fixture: Path, data: dict[str, Any]) -> None:
            data["forbidden_generation_modes"].remove("standalone_single_image_to_video")
        expect_invalid(
            "standalone single-image I2V deny marker required",
            mutate_fixture(p3, root / "missing_classic_i2v_deny", omit_classic_i2v_deny),
            "must include text_to_video, first_last_frame, and standalone_single_image_to_video",
        )

        expect_invalid("ffprobe missing fail-closed", v1_only, "probe failed closed", "/definitely/missing/ffprobe")

    print(
        "PASS: real V1/V2 media and builder, ffprobe duration/streams/fps/resolution/frame+packet counts/chapters, "
        "actual Project Canon and receipt binding, exact provider video-constraint projection plus live ffprobe gates, "
        "source/input/prompt hashes, standalone-I2V exclusion without rejecting Omni image references, "
        "V1/V2 eligibility, N=3/7/15/17, physics and adversarial closure"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
