#!/usr/bin/env python3
"""Exercise positive and adversarial modular storyboard fixtures."""

from __future__ import annotations

import binascii
import copy
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path
from typing import Any, Callable

from validate_storyboard_package import canonical_artifact_hash, sha256_file, validate_package
from ai_video_input_contracts import canonical_hash

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
SHOT_TEMPLATE = json.loads((SKILL_ROOT / "references/input_fixtures/shot_contract.template.json").read_text(encoding="utf-8"))
LOOK_TEMPLATE = json.loads((SKILL_ROOT / "references/input_fixtures/global_look_contract.template.json").read_text(encoding="utf-8"))
DIRECTING = SHOT_TEMPLATE["global_directing_prompt_full"]
LOOK_CORE = LOOK_TEMPLATE["global_look_prompt_full"]
LOOK_STATE_ID = LOOK_TEMPLATE["look_states"][0]["state_id"]
LOOK_STATE = LOOK_TEMPLATE["look_states"][0]["state_prompt_full"]
LOOK_REF_ID = LOOK_TEMPLATE["look_states"][0]["reference_ids"][0]
LOOK_REF_ASSET_ID = LOOK_TEMPLATE["look_reference_set"][0]["artifact"]["artifact_id"]
LOOK_DELTA = LOOK_TEMPLATE["shot_look_assignments"][0]["shot_look_delta_prompt_full"]


def render_shot_look_delta_prompt(delta: dict[str, Any]) -> str:
    active = "true" if delta.get("active") is True else "false"
    preserves = "true" if delta.get("preserves_look_core") is True else "false"
    scope = json.dumps(delta.get("scope"), ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return "\n".join((
        "SHOT LOOK DELTA — FROZEN STRUCTURED AUTHORITY",
        f"active: {active}", f"scope: {scope}",
        f"description: {delta.get('description')}", f"reason: {delta.get('reason')}",
        f"preserves_look_core: {preserves}",
    ))


canonical_look_hash = canonical_hash
canonical_project_canon_hash = canonical_hash
canonical_shot_hash = canonical_hash
OWNER = "ai-video-modular-storyboard"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)


def write_png(path: Path, width: int = 32, height: int = 18, rgb: tuple[int, int, int] = (90, 100, 110)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    scanline = b"\x00" + bytes(rgb) * width
    payload = b"".join(scanline for _ in range(height))
    data = b"\x89PNG\r\n\x1a\n"
    data += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += png_chunk(b"IDAT", zlib.compress(payload))
    data += png_chunk(b"IEND", b"")
    path.write_bytes(data)


def dependency(artifact_id: str, owner_skill: str, version: str, digest: str) -> dict[str, Any]:
    return {"artifact_id": artifact_id, "owner_skill": owner_skill, "version": version, "sha256": digest}


def seal(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact["sha256"] = canonical_artifact_hash(artifact)
    return artifact


def envelope(artifact_id: str, version: str, uids: list[str], dependencies: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "contract_version": "ai-video-artifact-v1",
        "artifact_id": artifact_id,
        "owner_skill": "ai-video-modular-storyboard",
        "version": version,
        "sha256": None,
        "approval_status": "assistant_validated",
        "dependencies": dependencies or [],
        "affected_shot_uids": uids,
        "stale_reason": None,
    }


def build_shot_authority(root: Path, uids: list[str], durations: list[float]) -> tuple[dict[str, Any], str]:
    """Write a real validated Shot Contract used as the test authority."""
    record = copy.deepcopy(SHOT_TEMPLATE)
    record.update({
        "artifact_id": "SHOT_CONTRACT",
        "version": "3.0.0",
        "project_id": f"FIXTURE_{len(uids)}",
        "affected_shot_uids": uids,
        "approval_status": "assistant_validated",
    })
    source_shot = SHOT_TEMPLATE["shots"][0]
    shots: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []
    keyframes: list[dict[str, Any]] = []
    previs: list[dict[str, Any]] = []
    continuity: list[dict[str, Any]] = []
    for index, (uid, duration) in enumerate(zip(uids, durations), 1):
        shot = copy.deepcopy(source_shot)
        shot.update({"shot_uid": uid, "display_no": index, "target_duration_seconds": duration})
        shot["continuity_in"] = "project opening state" if index == 1 else f"continuation from {uids[index - 2]}"
        shot["continuity_out"] = "project ending state" if index == len(uids) else f"handoff to {uids[index]}"
        shots.append(shot)
        asset = copy.deepcopy(SHOT_TEMPLATE["asset_requirement_map"][0])
        asset["shot_uid"] = uid
        assets.append(asset)
        keyframe = copy.deepcopy(SHOT_TEMPLATE["keyframe_requirement_map"][0])
        keyframe["shot_uid"] = uid
        keyframes.append(keyframe)
        previs_record = copy.deepcopy(SHOT_TEMPLATE["previs_requirement_map"][0])
        previs_record["shot_uid"] = uid
        previs.append(previs_record)
        if index > 1:
            continuity.append({
                "from_shot_uid": uids[index - 2],
                "to_shot_uid": uid,
                "continuity_type": "conceptual",
                "preserved_state": ["product identity", "global directing grammar"],
                "cut_reason": "preserve the approved scripted order",
            })
    record["shots"] = shots
    record["timeline"] = {
        "total_duration_seconds": sum(durations),
        "numerical_tolerance_seconds": 0.001,
        "shot_count": len(uids),
    }
    record["continuity_map"] = continuity
    record["asset_requirement_map"] = assets
    record["keyframe_requirement_map"] = keyframes
    record["previs_requirement_map"] = previs
    record["inferred_directing_decisions"][0]["field_path"] = f"shots[{uids[0]}].visible_emotional_expression"
    record["revision_scope"]["actually_changed_shot_uids"] = uids
    record["sha256"] = canonical_shot_hash(record)
    rel = "authorities/SHOT_CONTRACT.json"
    write_json(root / rel, record)
    return record, rel


def build_look_authority(root: Path, uids: list[str], shot: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Write a real validated Global Look whose exact prompts are inherited downstream."""
    record = copy.deepcopy(LOOK_TEMPLATE)
    record.update({
        "artifact_id": "GLOBAL_LOOK",
        "version": "2.0.0",
        "project_id": f"FIXTURE_{len(uids)}",
        "project_shot_uids": uids,
        "affected_shot_uids": uids,
        "approval_status": "assistant_validated",
        "dependencies": [dependency(shot["artifact_id"], shot["owner_skill"], shot["version"], shot["sha256"])],
    })
    record["project_constraints"]["multiple_look_states"] = False
    state = copy.deepcopy(LOOK_TEMPLATE["look_states"][0])
    state["reference_ids"] = [LOOK_REF_ID]
    record["look_states"] = [state]
    reference = copy.deepcopy(LOOK_TEMPLATE["look_reference_set"][0])
    reference.update({
        "reference_id": LOOK_REF_ID,
        "locator": "authorities/look/LOOK_REF_HERO.png",
        "applicable_state_ids": [LOOK_STATE_ID],
        "approval_status": "approved",
        "inspection_status": "passed",
        "integrity_status": "verified_bytes",
        "actual_dimensions": {"width": 32, "height": 18},
        "independent_full_frame": True,
        "derived_from_multipanel": False,
        "intrinsic_boundary_check": "passed",
    })
    write_png(root / reference["locator"], width=32, height=18, rgb=(120, 96, 72))
    reference["file_sha256"] = sha256_file(root / reference["locator"])
    reference_prompt = "Independent hero Global Look reference proving Core and State without changing product or character identity."
    prompt_path = root / "authorities/look/LOOK_REF_HERO_generation_prompt.md"
    prompt_path.write_text(reference_prompt, encoding="utf-8")
    reference["generation_prompt_sha256"] = sha256_file(prompt_path)
    reference["artifact"]["dependencies"] = copy.deepcopy(record["dependencies"])
    reference["artifact"]["affected_shot_uids"] = uids
    reference["artifact"]["approval_status"] = "assistant_validated"
    reference["artifact"]["sha256"] = canonical_look_hash(reference["artifact"])
    record["look_reference_set"] = [reference]
    base_assignment = copy.deepcopy(LOOK_TEMPLATE["shot_look_assignments"][0])
    base_assignment["state_id"] = LOOK_STATE_ID
    base_assignment["shot_look_delta_prompt_full"] = render_shot_look_delta_prompt(base_assignment["shot_look_delta"])
    record["shot_look_assignments"] = []
    for uid in uids:
        assignment = copy.deepcopy(base_assignment)
        assignment["shot_uid"] = uid
        record["shot_look_assignments"].append(assignment)
    for risk in record["look_risk_coverage"]:
        risk.update({
            "state_ids": [LOOK_STATE_ID],
            "reference_ids": [LOOK_REF_ID],
            "affected_shot_uids": uids,
            "coverage_status": "covered",
        })
    record["three_layer_lock"]["textual_contract_frozen"] = True
    record["three_layer_lock"]["visual_reference_set_approved"] = True
    record["revision_scope"].update({
        "changed_state_ids": [LOOK_STATE_ID],
        "changed_shot_uids": uids,
    })
    record["sha256"] = canonical_look_hash(record)
    rel = "authorities/GLOBAL_LOOK.json"
    write_json(root / rel, record)
    return record, rel


def canon_entry(
    artifact: dict[str, Any], slot: str, artifact_type: str, locator: str, file_hash: str,
    *, eligible: bool = True, record_locator: str | None = None, record_file_hash: str | None = None,
) -> dict[str, Any]:
    if record_locator is None:
        record_locator = locator
        record_file_hash = file_hash
    return {
        "artifact_slot": slot,
        "artifact_id": artifact["artifact_id"],
        "artifact_type": artifact_type,
        "owner_skill": artifact["owner_skill"],
        "version": artifact["version"],
        "sha256": artifact["sha256"],
        "approval_status": artifact["approval_status"],
        "stale_reason": artifact["stale_reason"],
        "eligible_for_downstream": eligible,
        "affected_shot_uids": artifact["affected_shot_uids"],
        "locator": locator,
        "file_sha256": file_hash,
        "artifact_record_locator": record_locator,
        "artifact_record_file_sha256": record_file_hash,
        "dependencies": artifact["dependencies"],
    }


def materialize_owned_record(root: Path, artifact: dict[str, Any], namespace: str) -> tuple[str, str]:
    rel = f"{namespace}/owned_artifacts/{artifact['artifact_id']}.json"
    write_json(root / rel, artifact)
    return rel, sha256_file(root / rel)


def build_intrinsic_text_asset(project_root: Path, uids: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    artifact = {
        "contract_version": "ai-video-artifact-v1",
        "artifact_id": "PACKAGING_LABEL_SOURCE",
        "owner_skill": "packaging-product-identity-label-lock-board",
        "version": "1.0.0",
        "sha256": None,
        "approval_status": "assistant_validated",
        "dependencies": [],
        "affected_shot_uids": uids,
        "stale_reason": None,
    }
    artifact["sha256"] = canonical_artifact_hash(artifact)
    asset_rel = "authorities/packaging/PACKAGING_LABEL_SOURCE.png"
    write_png(project_root / asset_rel, width=32, height=18, rgb=(180, 150, 90))
    record_rel = "authorities/packaging/PACKAGING_LABEL_SOURCE.json"
    write_json(project_root / record_rel, artifact)
    entry = canon_entry(
        artifact,
        "packaging_label:PACKAGING_LABEL_SOURCE",
        "packaging",
        asset_rel,
        sha256_file(project_root / asset_rel),
        record_locator=record_rel,
        record_file_hash=sha256_file(project_root / record_rel),
    )
    return artifact, entry


def build_project_canon(
    project_root: Path,
    package_root: Path,
    uids: list[str],
    shot: dict[str, Any],
    shot_rel: str,
    look: dict[str, Any] | None,
    look_rel: str | None,
    manifest: dict[str, Any],
    frames: list[dict[str, Any]],
    board: dict[str, Any],
    base_manifest: dict[str, Any] | None,
    base_rel: str | None,
    extra_active_entries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    def project_rel(path: Path) -> str:
        return path.resolve().relative_to(project_root.resolve()).as_posix()

    active = [canon_entry(shot, "shot_contract", "shot_contract", shot_rel, sha256_file(project_root / shot_rel))]
    active.extend(copy.deepcopy(extra_active_entries or []))
    if look is not None and look_rel is not None:
        active.append(canon_entry(look, "global_look", "global_look", look_rel, sha256_file(project_root / look_rel)))
        for reference in look["look_reference_set"]:
            reference_artifact = reference["artifact"]
            record_rel, record_hash = materialize_owned_record(project_root, reference_artifact, "authorities/look")
            active.append(canon_entry(
                reference_artifact,
                f"global_look_reference:{reference_artifact['artifact_id']}",
                "global_look_reference",
                reference["locator"],
                reference["file_sha256"],
                record_locator=record_rel,
                record_file_hash=record_hash,
            ))
    manifest_locator = project_rel(package_root / "00_manifest/STORYBOARD_MANIFEST.json")
    active.append(canon_entry(manifest, "storyboard_manifest", "storyboard_manifest", manifest_locator, sha256_file(package_root / "00_manifest/STORYBOARD_MANIFEST.json")))
    for frame in frames:
        package_record_rel, record_hash = materialize_owned_record(package_root, frame, "00_manifest")
        record_rel = project_rel(package_root / package_record_rel)
        active.append(canon_entry(frame, f"storyboard_frame:{frame['shot_uid']}", "storyboard_frame", project_rel(package_root / frame["file_path"]), frame["file_sha256"], record_locator=record_rel, record_file_hash=record_hash))
    package_board_record_rel, board_record_hash = materialize_owned_record(package_root, board, "00_manifest")
    board_record_rel = project_rel(package_root / package_board_record_rel)
    active.append(canon_entry(board, "storyboard_review_board", "storyboard_review_board", project_rel(package_root / board["file_path"]), board["file_sha256"], record_locator=board_record_rel, record_file_hash=board_record_hash))
    active_by_id = {entry["artifact_id"]: entry for entry in active}
    edges: list[dict[str, Any]] = []
    for consumer in active:
        for dep in consumer["dependencies"]:
            producer = active_by_id[dep["artifact_id"]]
            edges.append({
                "producer_artifact_id": producer["artifact_id"],
                "consumer_artifact_id": consumer["artifact_id"],
                "producer_sha256": producer["sha256"],
                "affected_shot_uids": consumer["affected_shot_uids"],
            })
    superseded: list[dict[str, Any]] = []
    if base_manifest is not None and base_rel is not None:
        prior = canon_entry(
            base_manifest,
            "storyboard_manifest",
            "storyboard_manifest",
            project_rel(package_root / base_rel),
            sha256_file(package_root / base_rel),
            eligible=False,
        )
        prior["superseded_by_artifact_id"] = manifest["artifact_id"]
        superseded.append(prior)
        for dep in prior["dependencies"]:
            producer = active_by_id[dep["artifact_id"]]
            edges.append({
                "producer_artifact_id": producer["artifact_id"],
                "consumer_artifact_id": prior["artifact_id"],
                "producer_sha256": producer["sha256"],
                "affected_shot_uids": prior["affected_shot_uids"],
            })
    canon = {
        "contract_version": "ai-video-artifact-v1",
        "artifact_id": f"PROJECT_CANON_MANIFEST_FIXTURE_{len(uids)}",
        "owner_skill": "ai-video-shot-script-director",
        "version": "1.0.0",
        "sha256": None,
        "approval_status": "assistant_validated",
        "dependencies": [],
        "affected_shot_uids": uids,
        "stale_reason": None,
        "schema_version": "ai-video-project-canon-manifest.v1",
        "project_id": f"FIXTURE_{len(uids)}",
        "manifest_role": "artifact_registry_only",
        "manifest_update_policy": "validated_atomic_delta_no_reverse_dependency",
        "current_phase": "storyboard_final" if look is not None else "storyboard_structure",
        "revision_counter": 1,
        "updated_by_skill": "ai-video-modular-storyboard",
        "base_manifest_sha256": "e" * 64,
        "canonical_shot_uids": uids,
        "active_artifacts": active,
        "superseded_artifacts": superseded,
        "dependency_edges": edges,
        "stale_events": [],
        "unresolved_change_requests": [],
    }
    canon["sha256"] = canonical_project_canon_hash(canon)
    write_json(project_root / "00_project_canon/PROJECT_CANON_MANIFEST.json", canon)
    return canon


def create_package(
    root: Path,
    count: int,
    replacement_count: int = 0,
    stage: str = "look_applied_final",
    project_root: Path | None = None,
    intrinsic_text: bool = False,
) -> dict[str, Any]:
    project_root = project_root or root
    uids = [f"SHT_{index:03d}" for index in range(1, count + 1)]
    durations = [1.0 + (order % 4) * 0.25 for order in range(1, count + 1)]
    shot_authority, shot_rel = build_shot_authority(project_root, uids, durations)
    look_authority: dict[str, Any] | None = None
    look_rel: str | None = None
    if stage == "look_applied_final":
        look_authority, look_rel = build_look_authority(project_root, uids, shot_authority)
    shot_contract = {field: shot_authority[field] for field in ("artifact_id", "owner_skill", "version", "sha256", "approval_status")}
    global_look = {field: look_authority[field] for field in ("artifact_id", "owner_skill", "version", "sha256", "approval_status")} if look_authority else None
    base_dependencies = [dependency(shot_authority["artifact_id"], shot_authority["owner_skill"], shot_authority["version"], shot_authority["sha256"])]
    if look_authority:
        base_dependencies.append(dependency(look_authority["artifact_id"], look_authority["owner_skill"], look_authority["version"], look_authority["sha256"]))
    frame_dependencies = copy.deepcopy(base_dependencies)
    if look_authority:
        frame_dependencies.extend([
            dependency(ref["artifact"]["artifact_id"], ref["artifact"]["owner_skill"], ref["artifact"]["version"], ref["artifact"]["sha256"])
            for ref in look_authority["look_reference_set"]
        ])
    intrinsic_text_ref: dict[str, Any] | None = None
    extra_active_entries: list[dict[str, Any]] = []
    if intrinsic_text:
        intrinsic_asset, intrinsic_entry = build_intrinsic_text_asset(project_root, uids)
        intrinsic_text_ref = dependency(
            intrinsic_asset["artifact_id"], intrinsic_asset["owner_skill"],
            intrinsic_asset["version"], intrinsic_asset["sha256"],
        )
        frame_dependencies.append(copy.deepcopy(intrinsic_text_ref))
        extra_active_entries.append(intrinsic_entry)
    frames: list[dict[str, Any]] = []
    old_records: list[dict[str, Any]] = []

    for order, uid in enumerate(uids, 1):
        version = "1.0.1" if order <= replacement_count else "1.0.0"
        file_version = 2 if order <= replacement_count else 1
        rel = f"01_frames/{uid}/{stage}_v{file_version:02d}.png"
        write_png(root / rel, rgb=((50 + order * 7) % 256, (80 + file_version * 20) % 256, (100 + order * 3) % 256))
        prompt_rel = f"01_frames/{uid}/{stage}_v{file_version:02d}_generation_prompt.md"
        prompt_text = DIRECTING
        if stage == "look_applied_final":
            prompt_text += f"\n{LOOK_CORE}\n{LOOK_STATE_ID}\n{LOOK_STATE}\n{LOOK_REF_ASSET_ID}\n{LOOK_DELTA}\n"
        if intrinsic_text_ref is not None:
            prompt_text += f"\nINTRINSIC TEXT SOURCE: {intrinsic_text_ref['artifact_id']} — preserve only source-authorized packaging text; do not invent copy.\n"
        (root / prompt_rel).write_text(prompt_text, encoding="utf-8")
        frame = envelope(f"SB_FRAME_{uid}", version, [uid], copy.deepcopy(frame_dependencies))
        frame.update({
            "shot_uid": uid,
            "display_order": order,
            "target_duration_seconds": durations[order - 1],
            "stage": stage,
            "file_path": rel,
            "file_sha256": sha256_file(root / rel),
            "generation_prompt_path": prompt_rel,
            "generation_prompt_file_sha256": sha256_file(root / prompt_rel),
            "global_directing_prompt_full": DIRECTING,
            "global_look_artifact_id": "GLOBAL_LOOK" if stage == "look_applied_final" else None,
            "global_look_prompt_full": LOOK_CORE if stage == "look_applied_final" else None,
            "look_state_id": LOOK_STATE_ID if stage == "look_applied_final" else None,
            "look_state_prompt_full": LOOK_STATE if stage == "look_applied_final" else None,
            "shot_look_delta_prompt_full": LOOK_DELTA if stage == "look_applied_final" else None,
            "look_reference_asset_ids": [LOOK_REF_ASSET_ID] if stage == "look_applied_final" else [],
            "actual_pixel_dimensions": {"width": 32, "height": 18},
            "generation_mode": "independent_full_frame",
            "independently_generated": True,
            "derived_from_multipanel": False,
            "is_model_input_eligible": stage == "look_applied_final",
            "content_cleanliness": {
                "no_shot_number_overlay": True,
                "no_duration_overlay": True,
                "no_editorial_caption_overlay": True,
                "no_arrow_overlay": True,
                "no_grid": True,
                "no_ui": True,
                "no_watermark": True,
                "no_layout_chrome": True,
                "intrinsic_text_policy": "source_authorized_only" if intrinsic_text_ref is not None else "none_visible",
                "intrinsic_text_source_refs": [copy.deepcopy(intrinsic_text_ref)] if intrinsic_text_ref is not None else [],
            },
        })
        seal(frame)
        frames.append(frame)
        if version == "1.0.1":
            old_records.append({
                "shot_uid": uid,
                "artifact_id": frame["artifact_id"],
                "version": "1.0.0",
                "sha256": str(order % 10) * 64,
                "file_sha256": str((order + 1) % 10) * 64,
            })

    board_rel = "02_review_board/storyboard_review_board.png"
    write_png(root / board_rel, width=64, height=36, rgb=(20, 20, 20))
    columns = min(5, max(1, __import__("math").ceil(__import__("math").sqrt(count * 16 / 9))))
    board = envelope(
        "STORYBOARD_REVIEW_BOARD",
        "1.0.1" if replacement_count else "1.0.0",
        uids,
        [dependency(frame["artifact_id"], "ai-video-modular-storyboard", frame["version"], frame["sha256"]) for frame in frames],
    )
    board.update({
        "board_type": "deterministic_human_review_composite",
        "is_model_input": False,
        "deterministic": True,
        "file_path": board_rel,
        "file_sha256": sha256_file(root / board_rel),
        "valid_cell_count": count,
        "cell_shot_uids": uids,
        "source_frame_hashes": {frame["shot_uid"]: frame["file_sha256"] for frame in frames},
        "layout": {"columns": columns, "rows": __import__("math").ceil(count / columns), "cell_width": 640, "image_height": 360, "label_height": 44, "padding": 16},
    })
    seal(board)

    transactions: list[dict[str, Any]] = []
    base_manifest: dict[str, Any] | None = None
    base_rel: str | None = None
    if replacement_count:
        requested = uids[:replacement_count]
        base_frames = copy.deepcopy(frames)
        for order, base_frame in enumerate(base_frames[:replacement_count], 1):
            old_rel = f"01_frames/{base_frame['shot_uid']}/{stage}_v01.png"
            write_png(root / old_rel, rgb=((25 + order * 5) % 256, 70, (90 + order * 3) % 256))
            old_prompt_rel = f"01_frames/{base_frame['shot_uid']}/{stage}_v01_generation_prompt.md"
            old_prompt_text = DIRECTING
            if stage == "look_applied_final":
                old_prompt_text += f"\n{LOOK_CORE}\n{LOOK_STATE_ID}\n{LOOK_STATE}\n{LOOK_REF_ASSET_ID}\n{LOOK_DELTA}\n"
            if intrinsic_text_ref is not None:
                old_prompt_text += f"\nINTRINSIC TEXT SOURCE: {intrinsic_text_ref['artifact_id']} — preserve only source-authorized packaging text; do not invent copy.\n"
            (root / old_prompt_rel).write_text(old_prompt_text, encoding="utf-8")
            base_frame.update({
                "version": "1.0.0",
                "file_path": old_rel,
                "file_sha256": sha256_file(root / old_rel),
                "generation_prompt_path": old_prompt_rel,
                "generation_prompt_file_sha256": sha256_file(root / old_prompt_rel),
            })
            seal(base_frame)
        old_records = [
            {field: frame[field] for field in ("shot_uid", "artifact_id", "version", "sha256", "file_sha256")}
            for frame in base_frames[:replacement_count]
        ]
        base_board_rel = "02_review_board/pre_transactions/TX_REPLACE_BASE_board.png"
        write_png(root / base_board_rel, width=64, height=36, rgb=(18, 18, 18))
        base_board = envelope(
            "STORYBOARD_REVIEW_BOARD_PRE_TX",
            "0.9.0",
            uids,
            [dependency(frame["artifact_id"], OWNER, frame["version"], frame["sha256"]) for frame in base_frames],
        )
        base_board.update({
            "board_type": "deterministic_human_review_composite",
            "is_model_input": False,
            "deterministic": True,
            "file_path": base_board_rel,
            "file_sha256": sha256_file(root / base_board_rel),
            "valid_cell_count": count,
            "cell_shot_uids": uids,
            "source_frame_hashes": {frame["shot_uid"]: frame["file_sha256"] for frame in base_frames},
            "layout": copy.deepcopy(board["layout"]),
        })
        seal(base_board)
        base_manifest = envelope("STORYBOARD_MANIFEST_PRE_TX", "0.9.0", uids, base_dependencies)
        base_manifest.update({
            "schema_version": "ai-video-modular-storyboard.v1",
            "project_id": f"FIXTURE_{count}",
            "package_status": "assistant_validated",
            "storyboard_stage": stage,
            "script_shot_count": count,
            "shot_contract": shot_contract,
            "global_look": global_look,
            "frames": base_frames,
            "review_board": base_board,
            "transactions": [],
            "downstream_invalidations": [],
        })
        seal(base_manifest)
        base_rel = "00_manifest/pre_transactions/TX_REPLACE_BASE.json"
        write_json(root / base_rel, base_manifest)
        base_ref = {field: base_manifest[field] for field in ("artifact_id", "owner_skill", "version", "sha256")}
        tx = envelope(
            "STORYBOARD_TX_REPLACE",
            "1.0.0",
            requested,
            [base_ref, *[dependency(frame["artifact_id"], "ai-video-modular-storyboard", frame["version"], frame["sha256"]) for frame in frames[:replacement_count]]],
        )
        tx.update({
            "transaction_id": "TX_REPLACE",
            "mode": "replace_frames",
            "status": "applied",
            "requested_shot_uids": requested,
            "atomic_commit": True,
            "route_to_shot_contract": False,
            "base_manifest_path": base_rel,
            "base_manifest_file_sha256": sha256_file(root / base_rel),
            "base_manifest_ref": base_ref,
            "old_frames": old_records,
            "new_frames": [
                {field: frame[field] for field in ("shot_uid", "artifact_id", "version", "sha256", "file_sha256")}
                for frame in frames[:replacement_count]
            ],
            "unaffected_hash_assertions": {frame["shot_uid"]: frame["file_sha256"] for frame in frames[replacement_count:]},
            "downstream_invalidations": ["review_board", "dependent_keyframes", "affected_previs", "affected_prompts"],
        })
        seal(tx)
        transactions.append(tx)

    manifest = envelope("STORYBOARD_MANIFEST", "1.0.0", uids, base_dependencies)
    manifest.update({
        "schema_version": "ai-video-modular-storyboard.v1",
        "project_id": f"FIXTURE_{count}",
        "package_status": "assistant_validated",
        "storyboard_stage": stage,
        "script_shot_count": count,
        "shot_contract": shot_contract,
        "global_look": global_look,
        "frames": frames,
        "review_board": board,
        "transactions": transactions,
        "downstream_invalidations": [],
    })
    seal(manifest)
    write_json(root / "00_manifest/STORYBOARD_MANIFEST.json", manifest)
    canon = build_project_canon(
        project_root, root, uids, shot_authority, shot_rel, look_authority, look_rel,
        manifest, frames, board, base_manifest, base_rel,
        extra_active_entries,
    )
    write_json(root / "00_manifest/MANIFEST_UPDATE_RECEIPT.json", {
        "schema_version": "ai-video-manifest-update-receipt.v1",
        "updated_by_skill": "ai-video-modular-storyboard",
        "canonical_manifest_locator": "00_project_canon/PROJECT_CANON_MANIFEST.json",
        "base_manifest_sha256": canon["base_manifest_sha256"],
        "resulting_manifest_sha256": canon["sha256"],
        "registered_artifact_ids": [manifest["artifact_id"], *[frame["artifact_id"] for frame in frames], board["artifact_id"]],
        "delta_status": "applied"
    })
    write_json(root / "02_review_board/storyboard_review_board.metadata.json", {
        "board_type": board["board_type"], "is_model_input": False,
        "valid_cell_count": count, "cell_shot_uids": uids,
        "source_frame_hashes": board["source_frame_hashes"], "file_sha256": board["file_sha256"]
    })
    qa_dir = root / "04_qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    (qa_dir / "continuity_report.md").write_text("Continuity checked for every adjacent shot.\n", encoding="utf-8")
    write_json(qa_dir / "validation_report.json", {"status": "passed", "validated_manifest_sha256": manifest["sha256"]})
    return manifest


def save_manifest(root: Path, manifest: dict[str, Any], reseal: bool = True) -> None:
    if reseal and manifest.get("approval_status") != "draft":
        manifest["sha256"] = canonical_artifact_hash(manifest)
    write_json(root / "00_manifest/STORYBOARD_MANIFEST.json", manifest)


def expect_valid(name: str, root: Path, project_root: Path | None = None) -> None:
    project_root = project_root or root
    canon_path = project_root / "00_project_canon/PROJECT_CANON_MANIFEST.json"
    canon = json.loads(canon_path.read_text(encoding="utf-8"))
    errors = validate_package(root, canon, project_root)
    if errors:
        raise AssertionError(f"{name} expected valid, got: {errors}")


def expect_invalid(name: str, root: Path, needle: str, project_root: Path | None = None) -> None:
    project_root = project_root or root
    canon_path = project_root / "00_project_canon/PROJECT_CANON_MANIFEST.json"
    canon = json.loads(canon_path.read_text(encoding="utf-8"))
    errors = validate_package(root, canon, project_root)
    if not any(needle in error for error in errors):
        raise AssertionError(f"{name} expected error containing {needle!r}, got: {errors}")


def mutate_fixture(base: Path, name: str, mutator: Callable[[dict[str, Any]], None]) -> Path:
    target = base.parent / name
    shutil.copytree(base, target)
    manifest_path = target / "00_manifest/STORYBOARD_MANIFEST.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    mutator(data)
    save_manifest(target, data)
    return target


def fully_reseal_current_storyboard(root: Path, mutator: Callable[[dict[str, Any]], None]) -> None:
    """Reseal package, owned records, Project Canon, receipt, and validation evidence after an attack mutation."""
    manifest_path = root / "00_manifest/STORYBOARD_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mutator(manifest)
    seal(manifest)
    write_json(manifest_path, manifest)

    board = manifest["review_board"]
    board_record_path = root / f"00_manifest/owned_artifacts/{board['artifact_id']}.json"
    write_json(board_record_path, board)

    canon_path = root / "00_project_canon/PROJECT_CANON_MANIFEST.json"
    canon = json.loads(canon_path.read_text(encoding="utf-8"))
    previous_canon_hash = canon["sha256"]
    for entry in canon["active_artifacts"]:
        if entry["artifact_id"] == manifest["artifact_id"]:
            entry.update({
                "version": manifest["version"],
                "sha256": manifest["sha256"],
                "file_sha256": sha256_file(manifest_path),
                "artifact_record_file_sha256": sha256_file(manifest_path),
                "dependencies": copy.deepcopy(manifest["dependencies"]),
            })
        elif entry["artifact_id"] == board["artifact_id"]:
            entry.update({
                "version": board["version"],
                "sha256": board["sha256"],
                "artifact_record_file_sha256": sha256_file(board_record_path),
                "dependencies": copy.deepcopy(board["dependencies"]),
            })
    active_by_id = {entry["artifact_id"]: entry for entry in canon["active_artifacts"]}
    canon["dependency_edges"] = [
        {
            "producer_artifact_id": dep["artifact_id"],
            "consumer_artifact_id": consumer["artifact_id"],
            "producer_sha256": active_by_id[dep["artifact_id"]]["sha256"],
            "affected_shot_uids": consumer["affected_shot_uids"],
        }
        for consumer in canon["active_artifacts"]
        for dep in consumer["dependencies"]
    ]
    major, minor, patch_version = (int(part) for part in canon["version"].split("."))
    canon["version"] = f"{major}.{minor}.{patch_version + 1}"
    canon["revision_counter"] += 1
    canon["base_manifest_sha256"] = previous_canon_hash
    canon["updated_by_skill"] = OWNER
    canon["sha256"] = canonical_project_canon_hash(canon)
    write_json(canon_path, canon)

    receipt_path = root / "00_manifest/MANIFEST_UPDATE_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["base_manifest_sha256"] = canon["base_manifest_sha256"]
    receipt["resulting_manifest_sha256"] = canon["sha256"]
    write_json(receipt_path, receipt)
    write_json(root / "04_qa/validation_report.json", {
        "status": "passed",
        "validated_manifest_sha256": manifest["sha256"],
    })


def main() -> int:
    json.loads((SKILL_ROOT / "references/storyboard_manifest.schema.json").read_text(encoding="utf-8"))
    json.loads((SKILL_ROOT / "references/change_transaction.schema.json").read_text(encoding="utf-8"))
    json.loads((SKILL_ROOT / "references/storyboard_manifest_template.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        independent_project = root / "independent_project"
        independent_package = independent_project / "03_storyboard_package"
        create_package(independent_package, 3, project_root=independent_project)
        expect_valid("independent package_root/project_root", independent_package, independent_project)
        positives: dict[int, Path] = {}
        for count in (1, 3, 7, 15, 17):
            fixture = root / f"positive_{count}"
            create_package(fixture, count)
            expect_valid(f"N={count}", fixture)
            positives[count] = fixture
        one = root / "replace_one"
        create_package(one, 3, replacement_count=1)
        expect_valid("replace one", one)
        two = root / "replace_two"
        create_package(two, 7, replacement_count=2)
        expect_valid("replace two", two)
        draft = root / "structure_draft"
        create_package(draft, 3, stage="structure_draft")
        expect_valid("structure draft", draft)
        label_heavy = root / "label_heavy"
        create_package(label_heavy, 1, intrinsic_text=True)
        expect_valid("source-authorized label-heavy frame", label_heavy)

        base = positives[3]
        count_bad = mutate_fixture(base, "bad_count", lambda data: data.__setitem__("script_shot_count", 4))
        expect_invalid("count mismatch", count_bad, "cardinality mismatch")

        def multipanel(data: dict[str, Any]) -> None:
            data["frames"][0]["derived_from_multipanel"] = True
            seal(data["frames"][0])
        expect_invalid("multipanel", mutate_fixture(base, "bad_multipanel", multipanel), "never derived from multipanel")

        def board_input(data: dict[str, Any]) -> None:
            data["review_board"]["is_model_input"] = True
            seal(data["review_board"])
        expect_invalid("board as input", mutate_fixture(base, "bad_board_input", board_input), "never be a model input")

        def bad_hash(data: dict[str, Any]) -> None:
            data["frames"][0]["sha256"] = "0" * 64
        expect_invalid("artifact hash", mutate_fixture(base, "bad_hash", bad_hash), "canonical artifact sha256 mismatch")

        root_drift = base.parent / "bad_root_hash"
        shutil.copytree(base, root_drift)
        root_manifest_path = root_drift / "00_manifest/STORYBOARD_MANIFEST.json"
        root_manifest = json.loads(root_manifest_path.read_text(encoding="utf-8"))
        root_manifest["project_id"] = "MUTATED_WITHOUT_REHASH"
        save_manifest(root_drift, root_manifest, reseal=False)
        expect_invalid("root semantic hash", root_drift, "canonical artifact sha256 mismatch")

        def structure_eligible(data: dict[str, Any]) -> None:
            data["frames"][0]["is_model_input_eligible"] = True
            seal(data["frames"][0])
        expect_invalid("structure draft eligibility", mutate_fixture(draft, "bad_structure_eligible", structure_eligible), "eligibility must be false")

        look_prompt_drift = base.parent / "bad_look_prompt_drift"
        shutil.copytree(base, look_prompt_drift)
        drift_manifest_path = look_prompt_drift / "00_manifest/STORYBOARD_MANIFEST.json"
        drift_manifest = json.loads(drift_manifest_path.read_text(encoding="utf-8"))
        drift_frame = drift_manifest["frames"][0]
        drift_prompt_path = look_prompt_drift / drift_frame["generation_prompt_path"]
        drift_prompt_path.write_text(drift_prompt_path.read_text(encoding="utf-8").replace(LOOK_STATE, "STATE OMITTED"), encoding="utf-8")
        drift_frame["generation_prompt_file_sha256"] = sha256_file(drift_prompt_path)
        seal(drift_frame)
        save_manifest(look_prompt_drift, drift_manifest)
        expect_invalid("static prompt loses exact Look State", look_prompt_drift, "exact look_state_prompt_full missing")

        def malformed_authority(data: dict[str, Any]) -> None:
            data["shot_contract"].pop("version", None)
        expect_invalid("malformed authority fails closed", mutate_fixture(base, "bad_malformed_authority", malformed_authority), "version")

        def invented_intrinsic_text_source(data: dict[str, Any]) -> None:
            fake_ref = dependency("INVENTED_LABEL_SOURCE", "invented-owner", "1.0.0", "9" * 64)
            frame = data["frames"][0]
            frame["content_cleanliness"]["intrinsic_text_policy"] = "source_authorized_only"
            frame["content_cleanliness"]["intrinsic_text_source_refs"] = [fake_ref]
            frame["dependencies"].append(fake_ref)
            seal(frame)
        expect_invalid(
            "invented label source fails closed",
            mutate_fixture(base, "bad_invented_label_source", invented_intrinsic_text_source),
            "not an exact downstream-eligible Project Canon artifact",
        )

        def leakage(data: dict[str, Any]) -> None:
            tx_source = json.loads((one / "00_manifest/STORYBOARD_MANIFEST.json").read_text(encoding="utf-8"))["transactions"][0]
            data["transactions"] = [tx_source]
            tx = data["transactions"][0]
            tx["new_frames"] = [{field: data["frames"][0][field] for field in ("shot_uid", "artifact_id", "version", "sha256", "file_sha256")}]
            tx["old_frames"][0]["version"] = "9.0.0"
            tx["unaffected_hash_assertions"]["SHT_002"] = "f" * 64
            seal(tx)
        expect_invalid("transaction leakage", mutate_fixture(base, "bad_leakage", leakage), "unaffected shot SHT_002 hash changed")

        anchored_attack = root / "bad_anchored_unrequested_change"
        shutil.copytree(one, anchored_attack)
        attack_manifest_path = anchored_attack / "00_manifest/STORYBOARD_MANIFEST.json"
        attack_manifest = json.loads(attack_manifest_path.read_text(encoding="utf-8"))
        unrequested = attack_manifest["frames"][1]
        unrequested_file = anchored_attack / unrequested["file_path"]
        write_png(unrequested_file, rgb=(250, 10, 10))
        unrequested["file_sha256"] = sha256_file(unrequested_file)
        seal(unrequested)
        attack_manifest["transactions"][0]["unaffected_hash_assertions"][unrequested["shot_uid"]] = unrequested["file_sha256"]
        seal(attack_manifest["transactions"][0])
        attack_manifest["review_board"]["source_frame_hashes"][unrequested["shot_uid"]] = unrequested["file_sha256"]
        seal(attack_manifest["review_board"])
        save_manifest(anchored_attack, attack_manifest)
        expect_invalid("unrequested change cannot rewrite transaction evidence", anchored_attack, "current storyboard manifest is not the active Project Canon entry")

        same_root_version = root / "bad_same_root_transaction_version"
        shutil.copytree(one, same_root_version)
        def hold_root_version(manifest: dict[str, Any]) -> None:
            base_manifest = json.loads((same_root_version / manifest["transactions"][0]["base_manifest_path"]).read_text(encoding="utf-8"))
            manifest["version"] = base_manifest["version"]
        fully_reseal_current_storyboard(same_root_version, hold_root_version)
        expect_invalid(
            "fully resealed transaction cannot retain root version",
            same_root_version,
            "current Storyboard manifest version must exceed pre-transaction manifest version",
        )

        same_board_version = root / "bad_same_board_transaction_version"
        shutil.copytree(one, same_board_version)
        def hold_board_version(manifest: dict[str, Any]) -> None:
            base_manifest = json.loads((same_board_version / manifest["transactions"][0]["base_manifest_path"]).read_text(encoding="utf-8"))
            manifest["review_board"]["version"] = base_manifest["review_board"]["version"]
            seal(manifest["review_board"])
        fully_reseal_current_storyboard(same_board_version, hold_board_version)
        expect_invalid(
            "fully resealed changed-source board cannot retain version",
            same_board_version,
            "changed review-board sources require current board version to exceed pre-transaction board version",
        )

        def local_reorder(data: dict[str, Any]) -> None:
            tx = envelope("TX_REORDER", "1.0.0", ["SHT_001", "SHT_002"])
            tx.update({
                "transaction_id": "TX_REORDER",
                "mode": "reorder_request",
                "status": "applied",
                "requested_shot_uids": ["SHT_001", "SHT_002"],
                "atomic_commit": True,
                "route_to_shot_contract": False,
            })
            seal(tx)
            data["transactions"] = [tx]
        expect_invalid("local reorder", mutate_fixture(base, "bad_reorder", local_reorder), "route upstream")

        subprocess.run(
            [sys.executable, str(HERE / "build_review_board.py"), str(base), "--output", "02_review_board/smoke.png", "--metadata", "02_review_board/smoke.json"],
            check=True,
            capture_output=True,
            text=True,
        )
        metadata = json.loads((base / "02_review_board/smoke.json").read_text(encoding="utf-8"))
        if metadata["valid_cell_count"] != 3 or metadata["is_model_input"] is not False:
            raise AssertionError("review-board builder metadata contract failed")
    print("PASS: storyboard schema parse, N=1/3/7/15/17, source-authorized intrinsic text, versioned atomic replacement, reorder, independence, hash, and board tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
