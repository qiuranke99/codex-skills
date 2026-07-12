#!/usr/bin/env python3
"""Integration and adversarial tests for the Keyframe Continuity Pack."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


HERE = Path(__file__).resolve().parent
SUITE_ROOT = HERE.parents[1]

VALIDATOR_SPEC = importlib.util.spec_from_file_location("keyframe_validator", HERE / "validate_keyframe_package.py")
assert VALIDATOR_SPEC and VALIDATOR_SPEC.loader
validator = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(validator)

STORYBOARD_SCRIPTS = SUITE_ROOT / "ai-video-modular-storyboard/scripts"
if str(STORYBOARD_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(STORYBOARD_SCRIPTS))
STORYBOARD_SPEC = importlib.util.spec_from_file_location("storyboard_fixture_builder", STORYBOARD_SCRIPTS / "test_contract.py")
assert STORYBOARD_SPEC and STORYBOARD_SPEC.loader
storyboard_fixture = importlib.util.module_from_spec(STORYBOARD_SPEC)
STORYBOARD_SPEC.loader.exec_module(storyboard_fixture)

SHOT_SCRIPTS = SUITE_ROOT / "ai-video-shot-script-director/scripts"
if str(SHOT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHOT_SCRIPTS))
from validate_project_canon_manifest import canonical_hash as canonical_project_canon_hash  # type: ignore  # noqa: E402


OWNER = "ai-video-keyframe-continuity-pack"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_ref(value: dict[str, Any]) -> dict[str, Any]:
    return {field: value[field] for field in ("artifact_id", "owner_skill", "version", "sha256")}


def envelope(
    artifact_id: str,
    shots: list[str],
    owner: str = OWNER,
    dependencies: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    value = {
        "contract_version": "ai-video-artifact-v1",
        "artifact_id": artifact_id,
        "owner_skill": owner,
        "version": "1.0.0",
        "sha256": None,
        "approval_status": "assistant_validated",
        "dependencies": dependencies or [],
        "affected_shot_uids": shots,
        "stale_reason": None,
    }
    value["sha256"] = validator.canonical_envelope_hash(value)
    return value


def canon_entry(
    artifact: dict[str, Any],
    slot: str,
    artifact_type: str,
    locator: str,
    binary_hash: str,
    *,
    record_locator: str | None = None,
    record_file_hash: str | None = None,
) -> dict[str, Any]:
    if record_locator is None:
        record_locator = locator
        record_file_hash = binary_hash
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
        "artifact_record_locator": record_locator,
        "artifact_record_file_sha256": record_file_hash,
        "dependencies": artifact["dependencies"],
    }


def rebuild_edges(canon: dict[str, Any]) -> None:
    active = canon["active_artifacts"]
    by_id = {entry["artifact_id"]: entry for entry in active}
    edges: list[dict[str, Any]] = []
    for consumer in active:
        for dep in consumer["dependencies"]:
            producer = by_id[dep["artifact_id"]]
            edges.append({
                "producer_artifact_id": producer["artifact_id"],
                "consumer_artifact_id": consumer["artifact_id"],
                "producer_sha256": producer["sha256"],
                "affected_shot_uids": consumer["affected_shot_uids"],
            })
    canon["dependency_edges"] = edges


def apply_canon_update(
    project: Path,
    entries: list[dict[str, Any]],
    updated_by: str,
    phase: str,
) -> dict[str, Any]:
    path = project / "00_project_canon/PROJECT_CANON_MANIFEST.json"
    canon = json.loads(path.read_text(encoding="utf-8"))
    base_hash = canon["sha256"]
    active = {entry["artifact_slot"]: entry for entry in canon["active_artifacts"]}
    for entry in entries:
        if entry["artifact_slot"] in active:
            raise AssertionError(f"fixture attempted implicit slot overwrite: {entry['artifact_slot']}")
        active[entry["artifact_slot"]] = entry
    canon["active_artifacts"] = list(active.values())
    major, minor, patch = (int(part) for part in canon["version"].split("."))
    canon["version"] = f"{major}.{minor}.{patch + 1}"
    canon["revision_counter"] += 1
    canon["updated_by_skill"] = updated_by
    canon["current_phase"] = phase
    canon["base_manifest_sha256"] = base_hash
    rebuild_edges(canon)
    canon["sha256"] = canonical_project_canon_hash(canon)
    write_json(path, canon)
    return canon


def inventory_from_entry(entry: dict[str, Any], authority_type: str) -> dict[str, Any]:
    return {
        "artifact_id": entry["artifact_id"],
        "owner_skill": entry["owner_skill"],
        "version": entry["version"],
        "sha256": entry["sha256"],
        "locator": entry["locator"],
        "file_sha256": entry["file_sha256"],
        "authority_type": authority_type,
        "approval_status": entry["approval_status"],
        "affected_shot_uids": entry["affected_shot_uids"],
    }


def write_timing_authority(project: Path, uids: list[str], shot_ref: dict[str, Any], storyboard_ref: dict[str, Any]) -> dict[str, Any]:
    timing = envelope(
        "TIMING_ANIMATIC_V1",
        uids,
        "ai-video-timed-animatic-previs-director",
        [shot_ref, storyboard_ref],
    )
    timing.update({
        "schema_version": "ai-video-timing-animatic-test.v1",
        "shot_timing_records": [
            {"shot_uid": uid, "start_seconds": float(index - 1), "end_seconds": float(index)}
            for index, uid in enumerate(uids, 1)
        ],
    })
    timing["sha256"] = validator.canonical_envelope_hash(timing)
    rel = "04_timing/TIMING_ANIMATIC_V1.json"
    write_json(project / rel, timing)
    entry = canon_entry(timing, "timing_animatic_v1", "timing_animatic_v1", rel, file_hash(project / rel))
    apply_canon_update(project, [entry], "ai-video-timed-animatic-previs-director", "timing_animatic_v1")
    return entry


def current_canon(project: Path) -> dict[str, Any]:
    return json.loads((project / "00_project_canon/PROJECT_CANON_MANIFEST.json").read_text(encoding="utf-8"))


def make_authorities(project: Path, uids: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    canon = current_canon(project)
    by_type = {entry["artifact_type"]: entry for entry in canon["active_artifacts"]}
    shot_entry = by_type["shot_contract"]
    look_entry = by_type["global_look"]
    storyboard_entry = by_type["storyboard_manifest"]
    look_reference_entries = [entry for entry in canon["active_artifacts"] if entry["artifact_type"] == "global_look_reference"]
    if len(uids) > 1:
        timing_entry = write_timing_authority(project, uids, {
            field: shot_entry[field] for field in ("artifact_id", "owner_skill", "version", "sha256")
        }, {
            field: storyboard_entry[field] for field in ("artifact_id", "owner_skill", "version", "sha256")
        })
    else:
        timing_entry = None
    authorities = [
        inventory_from_entry(shot_entry, "shot_contract"),
        inventory_from_entry(storyboard_entry, "storyboard"),
        inventory_from_entry(look_entry, "global_look"),
        *[inventory_from_entry(entry, "global_look_reference") for entry in look_reference_entries],
    ]
    for authority_type in ("product", "packaging", "scene"):
        authorities.extend(
            inventory_from_entry(entry, authority_type)
            for entry in canon["active_artifacts"]
            if entry["artifact_type"] == authority_type
        )
    if timing_entry is not None:
        authorities.append(inventory_from_entry(timing_entry, "timing_animatic_v1"))
    shot = json.loads((project / shot_entry["locator"]).read_text(encoding="utf-8"))
    look = json.loads((project / look_entry["locator"]).read_text(encoding="utf-8"))
    storyboard = json.loads((project / storyboard_entry["locator"]).read_text(encoding="utf-8"))
    return authorities, shot, look, storyboard


def write_receipt(package: Path, canon: dict[str, Any], registered: set[str]) -> None:
    write_json(package / "00_manifest/MANIFEST_UPDATE_RECEIPT.json", {
        "schema_version": "ai-video-manifest-update-receipt.v1",
        "canonical_manifest_locator": "00_project_canon/PROJECT_CANON_MANIFEST.json",
        "updated_by_skill": OWNER,
        "base_manifest_sha256": canon["base_manifest_sha256"],
        "resulting_manifest_sha256": canon["sha256"],
        "registered_artifact_ids": sorted(registered),
        "delta_status": "applied",
    })


def keyframe_owned_entries(project: Path, package: Path, manifest: dict[str, Any], projections: list[tuple[str, dict[str, Any]]]) -> tuple[list[dict[str, Any]], set[str]]:
    manifest_rel = str((package / "00_manifest/KEYFRAME_CONTINUITY_MANIFEST.json").relative_to(project))
    entries = [canon_entry(manifest, "keyframe_continuity_manifest", "keyframe_continuity_manifest", manifest_rel, file_hash(project / manifest_rel))]
    registered = {manifest["artifact_id"]}
    for record in manifest["shot_records"]:
        for frame in record["keyframes"]:
            artifact = frame["artifact"]
            rel = str((package / frame["file_path"]).relative_to(project))
            record_rel = str((package / f"00_manifest/owned_artifacts/{artifact['artifact_id']}.json").relative_to(project))
            write_json(project / record_rel, artifact)
            entries.append(canon_entry(
                artifact,
                f"keyframe:{frame['keyframe_id']}",
                "keyframe",
                rel,
                frame["file_sha256"],
                record_locator=record_rel,
                record_file_hash=file_hash(project / record_rel),
            ))
            registered.add(artifact["artifact_id"])
    for rel, projection in projections:
        project_rel = str((package / rel).relative_to(project))
        entries.append(canon_entry(projection, f"keyframe_projection:{projection['projection_type']}", projection["projection_type"], project_rel, file_hash(project / project_rel)))
        registered.add(projection["artifact_id"])
    return entries, registered


def build_k1(
    project: Path,
    count: int = 1,
    *,
    label_heavy: bool = False,
    promote_storyboard: bool = False,
) -> tuple[Path, dict[str, Any], set[str]]:
    storyboard_fixture.create_package(
        project / "03_storyboard", count, project_root=project, intrinsic_text=label_heavy
    )
    uids = [f"SHT_{index:03d}" for index in range(1, count + 1)]
    authorities, shot_authority, look_authority, storyboard_authority = make_authorities(project, uids)
    package = project / "05_keyframes"
    package.mkdir(parents=True, exist_ok=True)
    for rel in ("00_manifest/KEYFRAME_CONTINUITY_MANIFEST.md", "04_reports/PROMOTION_REPORT.md", "04_reports/QA_REPORT.md", "04_reports/INVALIDATION_REPORT.md"):
        path = package / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture evidence\n", encoding="utf-8")

    authority_refs = [
        {field: authority[field] for field in ("artifact_id", "owner_skill", "version", "sha256")}
        for authority in authorities
    ]
    story_frames = {frame["shot_uid"]: frame for frame in storyboard_authority["frames"]}
    look_states = {state["state_id"]: state for state in look_authority["look_states"]}
    assignments = {item["shot_uid"]: item for item in look_authority["shot_look_assignments"]}
    reference_artifact_by_id = {
        item["reference_id"]: item["artifact"]["artifact_id"] for item in look_authority["look_reference_set"]
    }
    shot_records: list[dict[str, Any]] = []
    for uid in uids:
        assignment = assignments[uid]
        state = look_states[assignment["state_id"]]
        image_rel = f"01_keyframes/{uid}/KF_{uid}.bin"
        image = package / image_rel
        image.parent.mkdir(parents=True, exist_ok=True)
        if promote_storyboard:
            source_image = project / "03_storyboard" / story_frames[uid]["file_path"]
            image.write_bytes(source_image.read_bytes())
        else:
            image.write_bytes(f"keyframe-{uid}".encode("utf-8"))
        prompt_rel = f"01_keyframes/{uid}/KF_{uid}_generation_prompt.md"
        prompt = package / prompt_rel
        if not promote_storyboard:
            prompt.write_text(
                "Independent full-frame Omni reference anchor\n"
                "Use storyboard, keyframe, and approved asset images as ordinary image references inside Omni R2V.\n"
                f"{shot_authority['global_directing_prompt_full']}\n"
                f"{look_authority['global_look_prompt_full']}\n"
                f"{assignment['state_id']}\n{state['state_prompt_full']}\n"
                + "\n".join(reference_artifact_by_id[ref_id] for ref_id in state["reference_ids"])
                + f"\n{assignment['shot_look_delta_prompt_full']}\n",
                encoding="utf-8",
            )
        frame_artifact = envelope(f"KF_{uid}", [uid], OWNER, authority_refs)
        route = "validated_storyboard_promotion" if promote_storyboard else "independent_keyframe"
        record = {
            "shot_uid": uid,
            "storyboard_artifact_id": story_frames[uid]["artifact_id"],
            "required_authority_artifact_ids": [item["artifact_id"] for item in authorities],
            "global_directing_prompt_full": shot_authority["global_directing_prompt_full"],
            "global_look_artifact_id": look_authority["artifact_id"],
            "global_look_prompt_full": look_authority["global_look_prompt_full"],
            "look_state_id": assignment["state_id"],
            "look_state_prompt_full": state["state_prompt_full"],
            "shot_look_delta_prompt_full": assignment["shot_look_delta_prompt_full"],
            "look_reference_asset_ids": [reference_artifact_by_id[ref_id] for ref_id in state["reference_ids"]],
            "anchor_route": route,
            "keyframes": [{
                "artifact": frame_artifact,
                "keyframe_id": frame_artifact["artifact_id"],
                "shot_uid": uid,
                "frame_role": "primary_anchor",
                "usage_mode": "omni_reference_anchor",
                "source_mode": route,
                "file_path": image_rel,
                "file_sha256": file_hash(image),
                "prompt_path": None if promote_storyboard else prompt_rel,
                "prompt_file_sha256": None if promote_storyboard else file_hash(prompt),
                "time_anchor": {
                    "source": "v1_timing_animatic" if count > 1 else "shot_contract_static_state",
                    "timecode_seconds": float(uids.index(uid)) if count > 1 else None,
                    "relative_state": "primary_control_state",
                },
                "terminal_generation_call": "not_applicable_promoted" if promote_storyboard else "executed",
                "generation_turn": None if promote_storyboard else 1,
                "inspection_turn": 2,
                "visual_qa_status": "passed",
                "promotion_evidence": copy.deepcopy(validator.PROMOTION_EVIDENCE_GATES) if promote_storyboard else [],
            }],
            "character_state_ledger": [],
            "product_state_ledger": [],
            "material_control_required": False,
            "material_control_reason": "no source-supported dynamic material state is required",
            "material_anchor_keyframe_ids": [],
            "material_state_trajectory": [],
            "dynamic_state_ladder": [{
                "state_id": f"STATE_{uid}",
                "order": 1,
                "time_anchor": {
                    "source": "v1_timing_animatic" if count > 1 else "shot_contract_static_state",
                    "timecode_seconds": float(uids.index(uid)) if count > 1 else None,
                    "relative_state": "primary_control_state",
                },
                "subject_pose_state": "source-supported primary control state",
                "object_material_state": "approved intrinsic state preserved",
                "camera_blocking_state": "storyboard framing retained",
                "transition_intent": "hold continuity into the next approved shot",
            }],
            "continuity_in": "project opening" if uid == uids[0] else f"handoff from {uids[uids.index(uid)-1]}",
            "continuity_out": "project ending" if uid == uids[-1] else f"handoff to {uids[uids.index(uid)+1]}",
        }
        shot_records.append(record)

    timing = (
        {"mode": "single_static_shot_exemption", "artifact_id": None, "owner_skill": None, "version": None, "sha256": None}
        if count == 1
        else {
            "mode": "v1_timing_animatic",
            **{field: authorities[-1][field] for field in ("artifact_id", "owner_skill", "version", "sha256")},
        }
    )
    manifest = envelope("KEYFRAME_CONTINUITY_K1", uids, OWNER, authority_refs)
    manifest.update({
        "schema_version": "ai-video-keyframe-continuity-pack.v1",
        "manifest_role": "core_keyframe_authority_before_generation_unit_preflight",
        "project_id": f"FIXTURE_{count}",
        "package_id": "KEYFRAME_CONTINUITY_K1",
        "package_status": "packaged",
        "assistant_qa_status": "passed",
        "production_approval_status": "not_granted",
        "forbidden_video_generation_modes": [
            "text_to_video", "first_last_frame", "standalone_single_image_to_video",
        ],
        "timing_source": timing,
        "authority_inventory": authorities,
        "scripted_shot_uids": uids,
        "shot_records": shot_records,
        "inferred_execution_decisions": [],
        "upstream_change_requests": [],
        "qa_report_path": "04_reports/QA_REPORT.md",
        "invalidation_report_path": "04_reports/INVALIDATION_REPORT.md",
    })
    manifest["sha256"] = validator.canonical_envelope_hash(manifest)
    write_json(package / "00_manifest/KEYFRAME_CONTINUITY_MANIFEST.json", manifest)

    manifest_ref = artifact_ref(manifest)
    projections: list[tuple[str, dict[str, Any]]] = []
    for index, (rel, projection_type, source_field) in enumerate((
        ("02_ledgers/CHARACTER_STATE_LEDGER.json", "character_state_ledger", "character_state_ledger"),
        ("02_ledgers/PRODUCT_STATE_LEDGER.json", "product_state_ledger", "product_state_ledger"),
        ("02_ledgers/MATERIAL_STATE_TRAJECTORY.json", "material_state_trajectory", "material_state_trajectory"),
        ("02_ledgers/DYNAMIC_STATE_LADDER.json", "dynamic_state_ladder", "dynamic_state_ladder"),
    ), 1):
        projection = envelope(f"K1_PROJECTION_{index}", uids, OWNER, [manifest_ref])
        projection.update({
            "schema_version": "ai-video-keyframe-continuity-projection.v1",
            "projection_type": projection_type,
            "records": [{"shot_uid": record["shot_uid"], "data": record[source_field]} for record in shot_records],
        })
        projection["sha256"] = validator.canonical_envelope_hash(projection)
        write_json(package / rel, projection)
        projections.append((rel, projection))

    entries, registered = keyframe_owned_entries(project, package, manifest, projections)
    canon = apply_canon_update(project, entries, OWNER, "core_keyframes_k1")
    write_receipt(package, canon, registered)
    return package, manifest, registered


def add_k2(project: Path, package: Path, registered: set[str]) -> tuple[dict[str, Any], set[str]]:
    manifest = json.loads((package / "00_manifest/KEYFRAME_CONTINUITY_MANIFEST.json").read_text(encoding="utf-8"))
    uids = manifest["scripted_shot_uids"]
    core_ref = artifact_ref(manifest)
    p1 = envelope(
        "PROMPT_PREFLIGHT_P1",
        uids,
        "ai-video-omni-reference-prompt-director",
        [core_ref],
    )
    p1.update({"schema_version": "ai-video-prompt-preflight-test.v1"})
    p1["sha256"] = validator.canonical_envelope_hash(p1)
    p1_rel = "06_prompt_preflight/PROMPT_PREFLIGHT_P1.json"
    write_json(project / p1_rel, p1)
    p1_entry = canon_entry(p1, "generation_unit_preflight_plan", "generation_unit_preflight_p1", p1_rel, file_hash(project / p1_rel))
    apply_canon_update(project, [p1_entry], "ai-video-omni-reference-prompt-director", "generation_unit_preflight_p1")

    p1_ref = artifact_ref(p1)
    supplement = envelope("KEYFRAME_BOUNDARY_K2", uids, OWNER, [core_ref, p1_ref])
    if len(uids) == 1:
        units = [{"generation_unit_id": "GU001", "ordered_shot_uids": uids}]
        boundaries: list[dict[str, Any]] = []
        exemption: str | None = "single_generation_unit"
    else:
        units = [
            {"generation_unit_id": f"GU{index:03d}", "ordered_shot_uids": [uid]}
            for index, uid in enumerate(uids, 1)
        ]
        frame_ids = {record["shot_uid"]: record["keyframes"][0]["keyframe_id"] for record in manifest["shot_records"]}
        boundaries = []
        for index in range(len(units) - 1):
            left_uid = units[index]["ordered_shot_uids"][-1]
            right_uid = units[index + 1]["ordered_shot_uids"][0]
            boundaries.append({
                "boundary_id": f"BOUNDARY_{index + 1:03d}",
                "boundary_type": "between_shots",
                "from_generation_unit_id": units[index]["generation_unit_id"],
                "to_generation_unit_id": units[index + 1]["generation_unit_id"],
                "from_shot_uid": left_uid,
                "to_shot_uid": right_uid,
                "from_keyframe_id": frame_ids[left_uid],
                "to_keyframe_id": frame_ids[right_uid],
                "locked_character_state": "preserve approved identity and state ledger",
                "locked_product_material_state": "preserve approved intrinsic product/material state",
                "locked_spatial_state": "preserve scripted screen direction and handoff",
                "locked_scene_look_state": "preserve authoritative Look Core, State and Delta",
            })
        exemption = None
    supplement.update({
        "schema_version": "ai-video-keyframe-boundary-supplement.v1",
        "project_id": manifest["project_id"],
        "core_keyframe_manifest": core_ref,
        "prompt_preflight": p1_ref,
        "scripted_shot_uids": uids,
        "generation_units": units,
        "supplemental_keyframes": [],
        "cross_generation_unit_boundaries": boundaries,
        "exemption": exemption,
    })
    supplement["sha256"] = validator.canonical_envelope_hash(supplement)
    supplement_rel_package = "03_boundaries/BOUNDARY_SUPPLEMENT.json"
    write_json(package / supplement_rel_package, supplement)
    supplement_rel_project = str((package / supplement_rel_package).relative_to(project))
    entry = canon_entry(supplement, "keyframe_boundary_supplement_k2", "boundary_supplement_k2", supplement_rel_project, file_hash(project / supplement_rel_project))
    canon = apply_canon_update(project, [entry], OWNER, "boundary_supplement_k2")
    registered = set(registered)
    registered.add(supplement["artifact_id"])
    write_receipt(package, canon, registered)
    return supplement, registered


def build_fixture(
    root: Path,
    count: int = 1,
    k2: bool = False,
    *,
    label_heavy: bool = False,
    promote_storyboard: bool = False,
) -> tuple[Path, Path]:
    project = root / "project"
    package, _, registered = build_k1(
        project, count, label_heavy=label_heavy, promote_storyboard=promote_storyboard
    )
    if k2:
        add_k2(project, package, registered)
    return project, package


def errors_for(project: Path, package: Path) -> list[str]:
    canon = current_canon(project)
    return validator.validate_package(package, canon, project)


def mutate_manifest(package: Path, mutator: Callable[[dict[str, Any]], None], reseal: bool = True) -> None:
    path = package / "00_manifest/KEYFRAME_CONTINUITY_MANIFEST.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    mutator(value)
    if reseal:
        value["sha256"] = validator.canonical_envelope_hash(value)
    write_json(path, value)


def expect_attack(
    name: str,
    mutator: Callable[[Path, Path], None],
    needle: str,
    *, count: int = 1,
    k2: bool = False,
    label_heavy: bool = False,
    promote_storyboard: bool = False,
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project, package = build_fixture(
            Path(tmp), count, k2,
            label_heavy=label_heavy,
            promote_storyboard=promote_storyboard,
        )
        mutator(project, package)
        errors = errors_for(project, package)
        if not any(needle in item for item in errors):
            raise AssertionError(f"{name}: expected {needle!r}, got {errors}")


def main() -> int:
    json.loads((HERE.parent / "references/keyframe_manifest.schema.json").read_text(encoding="utf-8"))
    json.loads((HERE.parent / "references/boundary_supplement.schema.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        project, package = build_fixture(Path(tmp), 1, False)
        assert not errors_for(project, package), errors_for(project, package)
    with tempfile.TemporaryDirectory() as tmp:
        project, package = build_fixture(Path(tmp), 1, True)
        assert not errors_for(project, package), errors_for(project, package)
    with tempfile.TemporaryDirectory() as tmp:
        project, package = build_fixture(Path(tmp), 2, True)
        assert not errors_for(project, package), errors_for(project, package)
    with tempfile.TemporaryDirectory() as tmp:
        project, package = build_fixture(
            Path(tmp), 1, False, label_heavy=True, promote_storyboard=True
        )
        assert not errors_for(project, package), errors_for(project, package)

    expect_attack(
        "endpoint usage mode",
        lambda _project, package: mutate_manifest(package, lambda value: value["shot_records"][0]["keyframes"][0].__setitem__("usage_mode", "first_frame")),
        "omni_reference_anchor",
    )
    expect_attack(
        "manifest pseudo hash",
        lambda _project, package: mutate_manifest(package, lambda value: value.__setitem__("sha256", "0" * 64), reseal=False),
        "hash mismatch",
    )

    def mutate_prompt_bytes(_project: Path, package: Path) -> None:
        (package / "01_keyframes/SHT_001/KF_SHT_001_generation_prompt.md").write_text("mutated", encoding="utf-8")

    expect_attack("prompt byte drift", mutate_prompt_bytes, "prompt_file_sha256 mismatch")

    def inject_classic_i2v(_project: Path, package: Path) -> None:
        manifest_path = package / "00_manifest/KEYFRAME_CONTINUITY_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        frame = manifest["shot_records"][0]["keyframes"][0]
        prompt = package / frame["prompt_path"]
        prompt.write_text(
            prompt.read_text(encoding="utf-8")
            + "\nUse classic single-image I2V as the complete video generation route.\n",
            encoding="utf-8",
        )
        frame["prompt_file_sha256"] = file_hash(prompt)
        manifest["sha256"] = validator.canonical_envelope_hash(manifest)
        write_json(manifest_path, manifest)

    expect_attack(
        "classic standalone single-image I2V prompt",
        inject_classic_i2v,
        "forbidden generation mode in prompt: classic single-image i2v",
    )

    expect_attack(
        "standalone single-image I2V deny marker required",
        lambda _project, package: mutate_manifest(
            package,
            lambda value: value["forbidden_video_generation_modes"].remove(
                "standalone_single_image_to_video"
            ),
        ),
        "must exactly deny T2V, first/last-frame, and standalone single-image I2V",
    )

    def omit_state(_project: Path, package: Path) -> None:
        manifest_path = package / "00_manifest/KEYFRAME_CONTINUITY_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        frame = manifest["shot_records"][0]["keyframes"][0]
        prompt = package / frame["prompt_path"]
        prompt.write_text(prompt.read_text(encoding="utf-8").replace(manifest["shot_records"][0]["look_state_prompt_full"], "STATE OMITTED"), encoding="utf-8")
        frame["prompt_file_sha256"] = file_hash(prompt)
        manifest["sha256"] = validator.canonical_envelope_hash(manifest)
        write_json(manifest_path, manifest)

    expect_attack("exact Look State omitted", omit_state, "exact look_state_prompt_full missing")
    expect_attack(
        "material state without trajectory",
        lambda _project, package: mutate_manifest(package, lambda value: value["shot_records"][0]["keyframes"][0].__setitem__("frame_role", "material_state")),
        "material_state frame requires",
    )

    def remove_look(_project: Path, package: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            value["authority_inventory"] = [item for item in value["authority_inventory"] if item["authority_type"] != "global_look"]
            value["dependencies"] = [artifact_ref(item) for item in value["authority_inventory"]]
        mutate_manifest(package, mutate)

    expect_attack("missing Global Look", remove_look, "missing required global_look")

    def traversal(_project: Path, package: Path) -> None:
        outside = package.parent / "outside.bin"
        outside.write_bytes(b"outside")
        def mutate(value: dict[str, Any]) -> None:
            frame = value["shot_records"][0]["keyframes"][0]
            frame["file_path"] = "../outside.bin"
            frame["file_sha256"] = file_hash(outside)
        mutate_manifest(package, mutate)

    expect_attack("keyframe path traversal", traversal, "escapes package root")

    def wrong_frame_dependencies(_project: Path, package: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            artifact = value["shot_records"][0]["keyframes"][0]["artifact"]
            artifact["dependencies"] = [{"artifact_id": "WRONG", "owner_skill": "wrong", "version": "1.0.0", "sha256": "f" * 64}]
            artifact["sha256"] = validator.canonical_envelope_hash(artifact)
        mutate_manifest(package, mutate)

    expect_attack("wrong per-frame authority locks", wrong_frame_dependencies, "exactly lock required shot authorities")

    def fake_inventory_locator(_project: Path, package: Path) -> None:
        mutate_manifest(package, lambda value: value["authority_inventory"][0].__setitem__("locator", "../forged.json"))

    expect_attack("authority locator traversal", fake_inventory_locator, "locator/file_sha256 required")

    def fake_inventory_hash(_project: Path, package: Path) -> None:
        mutate_manifest(package, lambda value: value["authority_inventory"][0].__setitem__("file_sha256", "0" * 64))

    expect_attack("authority byte hash forgery", fake_inventory_hash, "not the exact active Project Canon artifact")

    def direct_semantic_forgery(_project: Path, package: Path) -> None:
        mutate_manifest(package, lambda value: value["shot_records"][0].__setitem__("global_directing_prompt_full", "FORGED DIRECTING BLOCK " * 10))

    expect_attack("self-reported directing differs from authority", direct_semantic_forgery, "differs from real Shot Contract")

    def delta_semantic_forgery(_project: Path, package: Path) -> None:
        mutate_manifest(package, lambda value: value["shot_records"][0].__setitem__("shot_look_delta_prompt_full", "FORGED DELTA"))

    expect_attack("self-reported Delta differs from authority", delta_semantic_forgery, "differs from real Global Look authority")

    def fake_reference_asset_id(_project: Path, package: Path) -> None:
        mutate_manifest(package, lambda value: value["shot_records"][0].__setitem__("look_reference_asset_ids", ["LOOK_REFERENCE_ASSET_FORGED"]))

    expect_attack("internal or forged reference ID cannot become model input", fake_reference_asset_id, "must be an exact required global_look_reference authority")

    def extra_manifest_field(_project: Path, package: Path) -> None:
        mutate_manifest(package, lambda value: value.__setitem__("override", True))

    expect_attack("manifest extra field", extra_manifest_field, "must contain exact fields")

    def fake_receipt(_project: Path, package: Path) -> None:
        path = package / "00_manifest/MANIFEST_UPDATE_RECEIPT.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["resulting_manifest_sha256"] = "7" * 64
        write_json(path, receipt)

    expect_attack("receipt not bound to Canon", fake_receipt, "must equal canonical manifest sha256")

    def swap_keyframe_primary_bytes(project: Path, _package: Path) -> None:
        forged = project / "forged/KF_SHT_001.bin"
        forged.parent.mkdir(parents=True, exist_ok=True)
        forged.write_bytes(b"different but internally hashed keyframe bytes")
        canon_path = project / "00_project_canon/PROJECT_CANON_MANIFEST.json"
        canon = json.loads(canon_path.read_text(encoding="utf-8"))
        entry_record = next(item for item in canon["active_artifacts"] if item["artifact_id"] == "KF_SHT_001")
        entry_record["locator"] = "forged/KF_SHT_001.bin"
        entry_record["file_sha256"] = file_hash(forged)
        canon["sha256"] = canonical_project_canon_hash(canon)
        write_json(canon_path, canon)

    expect_attack("Canon cannot swap keyframe primary bytes behind valid record sidecar", swap_keyframe_primary_bytes, "primary keyframe bytes are not the exact active Project Canon entry")

    def within_shot(_project: Path, package: Path) -> None:
        path = package / "03_boundaries/BOUNDARY_SUPPLEMENT.json"
        supplement = json.loads(path.read_text(encoding="utf-8"))
        supplement["cross_generation_unit_boundaries"][0]["boundary_type"] = "within_shot_split"
        supplement["sha256"] = validator.canonical_envelope_hash(supplement)
        write_json(path, supplement)

    expect_attack("within-shot split", within_shot, "only between_shots boundaries are legal", count=2, k2=True)

    def unrequested_storyboard_drift(project: Path, _package: Path) -> None:
        path = project / "03_storyboard/00_manifest/STORYBOARD_MANIFEST.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["frames"][0]["file_sha256"] = "1" * 64
        value["frames"][0]["sha256"] = storyboard_fixture.canonical_artifact_hash(value["frames"][0])
        value["sha256"] = storyboard_fixture.canonical_artifact_hash(value)
        write_json(path, value)

    expect_attack("upstream Storyboard bytes drift", unrequested_storyboard_drift, "Project Canon invalid")

    def drop_promoted_label_source(_project: Path, package: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            record = value["shot_records"][0]
            record["required_authority_artifact_ids"] = [
                artifact_id for artifact_id in record["required_authority_artifact_ids"]
                if artifact_id != "PACKAGING_LABEL_SOURCE"
            ]
            artifact = record["keyframes"][0]["artifact"]
            artifact["dependencies"] = [
                dep for dep in artifact["dependencies"]
                if dep["artifact_id"] != "PACKAGING_LABEL_SOURCE"
            ]
            artifact["sha256"] = validator.canonical_envelope_hash(artifact)
        mutate_manifest(package, mutate)

    expect_attack(
        "promoted label source cannot be dropped",
        drop_promoted_label_source,
        "intrinsic text source authorities must remain required Keyframe authorities",
        label_heavy=True,
        promote_storyboard=True,
    )

    print("OK: real-authority K1/P1/K2 integration, source-bound label-heavy promotion, and 18 adversarial Keyframe cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
