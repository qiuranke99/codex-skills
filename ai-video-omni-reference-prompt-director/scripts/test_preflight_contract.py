#!/usr/bin/env python3
"""Positive and adversarial tests for standalone Prompt P1 validation."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

import test_contract as fixture
import validate_preflight_package as preflight
import validate_prompt_package as shared


P2_ONLY_FILES = (
    shared.COMPILE_SNAPSHOT,
    shared.MANIFEST_RECEIPT,
    shared.IR_PATH,
    shared.LOCKFILE,
    shared.BINDINGS,
    shared.UNIT_PROMPTS,
    shared.REPAIR_PROMPTS,
    shared.PAYLOAD,
    shared.FEEDBACK,
    *shared.TEXT_FILES,
)


def mutate_plan(root: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    path = root / shared.PREFLIGHT_PLAN
    value = json.loads(path.read_text(encoding="utf-8"))
    mutate(value)
    fixture.finalize(value)
    fixture.write_json(path, value)


def prepare_case(project_root: Path, remove_p2: bool = True) -> tuple[Path, Path]:
    root = project_root / "prompt_preflight_package"
    fixture.create_package(root, project_root)
    canon = project_root / preflight.DEFAULT_CANON
    canon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / shared.PREFLIGHT_SNAPSHOT, canon)
    if remove_p2:
        for relative in P2_ONLY_FILES:
            path = root / relative
            if path.is_file():
                path.unlink()
    return root, canon


def run_case(mutator: Callable[[Path, Path, Path], None] | None = None) -> list[str]:
    with tempfile.TemporaryDirectory() as temp:
        project_root = Path(temp)
        root, canon = prepare_case(project_root)
        if mutator is not None:
            mutator(root, project_root, canon)
        return preflight.validate_preflight_package(root, project_root, canon)


def expect_error(name: str, mutator: Callable[[Path, Path, Path], None], needle: str) -> None:
    errors = run_case(mutator)
    if not any(needle in error for error in errors):
        raise AssertionError(f"{name}: expected {needle!r}, got {errors}")


def build_unit_decisions(root: Path, unit_id: str, unit_shots: list[str]) -> dict[str, Any]:
    snapshot = json.loads((root / shared.PREFLIGHT_SNAPSHOT).read_text(encoding="utf-8"))
    decisions: list[dict[str, Any]] = []
    used_ids: list[str] = []
    for entry in snapshot["active_artifacts"]:
        control_roles, primary_control_role = fixture.control_roles_for(entry["artifact_type"])
        entry_scope = set(entry["affected_shot_uids"])
        controlled = [uid for uid in unit_shots if uid in entry_scope]
        is_global = entry["artifact_slot"] in shared.PREFLIGHT_REQUIRED_GLOBAL_SLOTS
        if is_global:
            controlled = list(unit_shots)
        relevant = bool(controlled)
        if relevant:
            is_visual = shared.preflight_requires_visual_transport(entry)
            is_packaging = entry["owner_skill"] == "packaging-product-identity-label-lock-board"
            decision = "selected_direct" if is_packaging else "transported_via_atlas_planned" if is_visual else "inline_text"
            modality = "image" if is_visual else "text"
            group_id = f"ATLAS_PLAN_{unit_id}" if is_visual and not is_packaging else None
            used_ids.append(entry["artifact_id"])
        else:
            decision = "irrelevant"
            modality = "text"
            group_id = None
        decisions.append({
            "artifact": {field: entry[field] for field in ("artifact_id", "owner_skill", "version", "sha256")},
            "artifact_slot": entry["artifact_slot"],
            "artifact_type": entry["artifact_type"],
            "control_roles": control_roles,
            "control_role": primary_control_role,
            "decision": decision,
            "transport_modality": modality,
            "transport_group_id": group_id,
            "controlled_shot_uids": controlled,
            "reason": "Two-unit adversarial fixture classification.",
        })
    duration = sum(fixture.DURATIONS[fixture.SHOTS.index(uid)] for uid in unit_shots)
    return {
        "generation_unit_id": unit_id,
        "ordered_shot_uids": list(unit_shots),
        "target_duration_seconds": duration,
        "timing_sensitive": True,
        "control_previs_requirement": "required",
        "required_modalities": ["text", "image", "video"],
        "planned_reference_counts": {"image": 2, "video": 1, "audio": 0, "total_multimodal": 3},
        "planned_reference_artifact_ids": used_ids,
        "artifact_decisions": decisions,
        "planned_future_inputs": [{
            "planned_input_id": f"BOUNDARY_SUPPLEMENT:{unit_id}",
            "producer_skill": "ai-video-keyframe-continuity-pack",
            "control_role": "keyframe_boundary_supplement",
            "transport_modality": "text",
            "controlled_shot_uids": list(unit_shots),
            "reason": "Every unit consumes the P1-bound K2 authority.",
        }, {
            "planned_input_id": f"CONTROL_PREVIS_V2:{unit_id}",
            "producer_skill": "ai-video-timed-animatic-previs-director",
            "control_role": "control_previs_v2",
            "transport_modality": "video",
            "controlled_shot_uids": list(unit_shots),
            "reason": "Timing-sensitive unit reserves one V2 control reference.",
        }],
        "split_reason": "Two-unit adversarial fixture split at a whole Shot UID boundary.",
        "continuity_boundary_in": "fixture boundary in",
        "continuity_boundary_out": "fixture boundary out",
        "preflight_status": "ready",
    }


def main() -> int:
    errors = run_case()
    if errors:
        raise AssertionError(f"valid standalone P1 package rejected: {errors}")

    registered_profiles = (
        ("character-casting-lock-board", "character_asset:cast", "CHARACTER_CASTING_LOCK_BOARD_ASSET"),
        ("character-final-lock-board", "character_asset:final", "CHARACTER_FINAL_LOCK_BOARD_ASSET"),
        ("single-face-character-lock-board", "character_asset:single", "SINGLE_FACE_CHARACTER_LOCK_BOARD_ASSET"),
        ("multi-angle-product-identity-lock-board", "product_asset:hero", "MULTI_ANGLE_PRODUCT_IDENTITY_ASSET"),
        ("packaging-product-identity-label-lock-board", "packaging_asset:hero", "PACKAGING_PRODUCT_IDENTITY_ASSET"),
        ("material-sensitive-product-master-asset-board", "material_asset:hero", "MATERIAL_SENSITIVE_PRODUCT_ASSET"),
        ("scene-canon-asset-pack", "scene_asset:hero", "SCENE_CANON_ASSET"),
    )
    for index, (owner, slot, artifact_type) in enumerate(registered_profiles):
        artifact_id = f"REGISTERED_ASSET_{index}"
        ref = {"artifact_id": artifact_id, "owner_skill": owner, "version": "1.0.0", "sha256": "a" * 64}
        active = {
            artifact_id: {
                **ref,
                "artifact_slot": slot,
                "artifact_type": artifact_type,
                "approval_status": "user_approved",
                "stale_reason": None,
                "eligible_for_downstream": True,
                "affected_shot_uids": ["S001"],
            }
        }
        plan = {
            "dependencies": [ref],
            "approval_status": "assistant_validated",
            "stale_reason": None,
            "plan_status": "ready_for_boundary_supplement",
            "blocked_reasons": [],
            "generation_units": [{
                "generation_unit_id": "GU001",
                "ordered_shot_uids": ["S001"],
                "target_duration_seconds": 1.0,
                "control_previs_requirement": "exempt_single_static_shot",
                "required_modalities": ["text"],
                "planned_reference_counts": {"image": 0, "video": 0, "audio": 0, "total_multimodal": 0},
                "planned_reference_artifact_ids": [artifact_id],
                "artifact_decisions": [{
                    "artifact": ref,
                    "artifact_slot": slot,
                    "artifact_type": artifact_type,
                    "control_roles": ["identity"],
                    "control_role": "identity",
                    "decision": "inline_text",
                    "transport_modality": "text",
                    "transport_group_id": None,
                    "controlled_shot_uids": ["S001"],
                    "reason": "Adversarial attempt to suppress registered visual evidence.",
                }],
                "planned_future_inputs": [],
                "preflight_status": "ready",
            }],
        }
        profile_errors = shared.validate_preflight_decision_matrix(
            plan,
            active,
            {"supported_modalities": ["text", "image", "video", "audio"]},
            {
                "max_duration_seconds": 15,
                "max_image_inputs": 9,
                "max_video_inputs": 3,
                "max_audio_inputs": 3,
                "max_total_multimodal_inputs": 15,
            },
        )
        if not any("visual control artifact must remain a planned image transport" in error for error in profile_errors):
            raise AssertionError(f"registered owner inline-text suppression passed for {owner}: {profile_errors}")

    audio_ref = {
        "artifact_id": "VOICE_REFERENCE_001", "owner_skill": "voice-canon-owner",
        "version": "1.0.0", "sha256": "b" * 64,
    }
    audio_active = {
        audio_ref["artifact_id"]: {
            **audio_ref, "artifact_slot": "voice_audio:lead", "artifact_type": "VOICE_AUDIO_REFERENCE",
            "approval_status": "user_approved", "stale_reason": None, "eligible_for_downstream": True,
            "affected_shot_uids": ["S001"],
        }
    }
    audio_plan = {
        "dependencies": [audio_ref], "approval_status": "assistant_validated", "stale_reason": None,
        "plan_status": "ready_for_boundary_supplement", "blocked_reasons": [],
        "generation_units": [{
            "generation_unit_id": "GU001", "ordered_shot_uids": ["S001"],
            "target_duration_seconds": 1.0, "control_previs_requirement": "exempt_single_static_shot",
            "required_modalities": ["text"],
            "planned_reference_counts": {"image": 0, "video": 0, "audio": 0, "total_multimodal": 0},
            "planned_reference_artifact_ids": [audio_ref["artifact_id"]],
            "artifact_decisions": [{
                "artifact": audio_ref, "artifact_slot": "voice_audio:lead",
                "artifact_type": "VOICE_AUDIO_REFERENCE", "control_roles": ["dialogue_voice"],
                "control_role": "dialogue_voice", "decision": "inline_text",
                "transport_modality": "text", "transport_group_id": None,
                "controlled_shot_uids": ["S001"], "reason": "malicious audio-to-text collapse",
            }],
            "planned_atlas_groups": [], "planned_future_inputs": [], "preflight_status": "ready",
        }],
    }
    audio_errors = shared.validate_preflight_decision_matrix(
        audio_plan, audio_active,
        {"supported_modalities": ["text", "audio"], "input_constraints": {"image": None, "video": None, "audio": {}}},
        {
            "max_duration_seconds": 15, "max_image_inputs": 0, "max_video_inputs": 0,
            "max_audio_inputs": 3, "max_total_multimodal_inputs": 3,
        },
    )
    if not any("relevant audio control media must remain selected_direct or conflict" in error for error in audio_errors):
        raise AssertionError(f"audio Canon was silently collapsed to text: {audio_errors}")

    with tempfile.TemporaryDirectory() as temp:
        project_root = Path(temp)
        root, canon = prepare_case(project_root)
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent / "validate_preflight_package.py"),
                str(root),
                "--project-root", str(project_root),
                "--project-canon-manifest", str(canon),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.returncode != 0 or "standalone Prompt P1 package is valid" not in result.stdout:
            raise AssertionError(f"P1 CLI rejected the no-P2 positive package: {result.stdout}")

    expect_error(
        "omitted active asset",
        lambda root, _project, _canon: mutate_plan(
            root, lambda value: value["generation_units"][0]["artifact_decisions"].pop()
        ),
        "artifact decisions must cover every preflight Canon active artifact exactly",
    )

    def fake_counts(root: Path, _project: Path, _canon: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            value["generation_units"][0]["planned_reference_counts"] = {
                "image": 3, "video": 1, "audio": 0, "total_multimodal": 4,
            }
        mutate_plan(root, mutate)
    expect_error("fake counts", fake_counts, "planned_reference_counts must be derived exactly")

    def forged_ref(root: Path, _project: Path, _canon: Path) -> None:
        mutate_plan(
            root,
            lambda value: value["generation_units"][0]["artifact_decisions"][0]["artifact"].update(
                {"sha256": "f" * 64}
            ),
        )
    expect_error("forged artifact ref", forged_ref, "artifact ref differs from the active Canon")

    def narrowed_scope(root: Path, _project: Path, _canon: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            decision = next(
                item for item in value["generation_units"][0]["artifact_decisions"]
                if item["artifact"]["artifact_id"] == fixture.PRODUCT_ASSET_ID
            )
            decision["controlled_shot_uids"] = ["S001"]
        mutate_plan(root, mutate)
    expect_error(
        "narrowed controlled scope",
        narrowed_scope,
        "controlled_shot_uids must exactly equal Canon scope intersected with unit scope",
    )

    def visual_as_text(root: Path, _project: Path, _canon: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            decision = next(
                item for item in value["generation_units"][0]["artifact_decisions"]
                if item["artifact"]["artifact_id"] == fixture.PRODUCT_ASSET_ID
            )
            decision.update({
                "decision": "inline_text",
                "transport_modality": "text",
                "transport_group_id": None,
            })
        mutate_plan(root, mutate)
    expect_error(
        "visual control reclassified as text",
        visual_as_text,
        "visual control artifact must remain a planned image transport or conflict",
    )

    def fixed_owner_role_narrowing(root: Path, _project: Path, _canon: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            decision = next(
                item for item in value["generation_units"][0]["artifact_decisions"]
                if item["artifact"]["artifact_id"] == fixture.CHARACTER_ASSET_ID
            )
            decision["control_roles"] = ["identity"]
        mutate_plan(root, mutate)
    expect_error(
        "fixed-owner role narrowing",
        fixed_owner_role_narrowing,
        "control_roles must exactly equal the fixed-owner Canon export authorization",
    )

    def tamper_preflight_atlas_build(root: Path, _project: Path, _canon: Path) -> None:
        mutate_plan(
            root,
            lambda value: value["generation_units"][0]["planned_atlas_groups"][0]["preflight_build"].update(
                {"file_sha256": "0" * 64}
            ),
        )
    expect_error(
        "preflight atlas dry-build tamper",
        tamper_preflight_atlas_build,
        "preflight_build must exactly equal the deterministic dry-build receipt projection",
    )

    def single_source_atlas_group(root: Path, _project: Path, _canon: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            unit = value["generation_units"][0]
            source_decisions = [
                item for item in unit["artifact_decisions"]
                if item["decision"] == "transported_via_atlas_planned"
            ]
            isolated = source_decisions[-1]
            isolated["transport_group_id"] = "ATLAS_PLAN_SINGLE"
            original_group = unit["planned_atlas_groups"][0]
            original_group["source_artifact_ids"] = original_group["source_artifact_ids"][:-1]
            second_group = json.loads(json.dumps(original_group))
            second_group.update({
                "transport_group_id": "ATLAS_PLAN_SINGLE",
                "planned_atlas_id": "ATLAS_SINGLE",
                "source_artifact_ids": [isolated["artifact"]["artifact_id"]],
            })
            unit["planned_atlas_groups"].append(second_group)
            unit["planned_reference_counts"].update({"image": 3, "total_multimodal": 4})
        mutate_plan(root, mutate)
    expect_error(
        "single-source planned atlas",
        single_source_atlas_group,
        "deterministic atlas requires at least two source artifacts",
    )

    def out_of_scope_selection(root: Path, _project: Path, _canon: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            first = build_unit_decisions(root, "GU001", ["S001"])
            second = build_unit_decisions(root, "GU002", fixture.SHOTS[1:])
            decision = next(
                item for item in second["artifact_decisions"]
                if item["artifact"]["artifact_id"] == "SB_S001"
            )
            decision.update({
                "decision": "selected_direct",
                "transport_modality": "image",
                "transport_group_id": None,
                "controlled_shot_uids": ["S002"],
            })
            second["planned_reference_artifact_ids"] = [
                item["artifact"]["artifact_id"] for item in second["artifact_decisions"]
                if item["decision"] in shared.PREFLIGHT_USED_DECISIONS
            ]
            second["planned_reference_counts"] = {
                "image": 3, "video": 1, "audio": 0, "total_multimodal": 4,
            }
            value["generation_units"] = [first, second]
        mutate_plan(root, mutate)
    expect_error(
        "out-of-scope asset selected into another unit",
        out_of_scope_selection,
        "out-of-scope active artifact must be classified irrelevant",
    )

    def packaging_atlas(root: Path, _project: Path, canon: Path) -> None:
        snapshot_path = root / shared.PREFLIGHT_SNAPSHOT
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        entry = next(item for item in snapshot["active_artifacts"] if item["artifact_id"] == fixture.PRODUCT_ASSET_ID)
        entry["artifact_slot"] = "packaging_asset:hero"
        entry["artifact_type"] = "PACKAGING_PRODUCT_IDENTITY_ASSET"
        fixture.finalize(snapshot)
        fixture.write_json(snapshot_path, snapshot)
        fixture.write_json(canon, snapshot)

        plan_path = root / shared.PREFLIGHT_PLAN
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        decision = next(
            item for item in plan["generation_units"][0]["artifact_decisions"]
            if item["artifact"]["artifact_id"] == fixture.PRODUCT_ASSET_ID
        )
        decision["artifact_slot"] = entry["artifact_slot"]
        decision["artifact_type"] = entry["artifact_type"]
        plan["project_canon_read_receipt"].update({
            "manifest_sha256": snapshot["sha256"],
            "manifest_version": snapshot["version"],
            "snapshot_file_sha256": fixture.file_hash(snapshot_path),
        })
        fixture.finalize(plan)
        fixture.write_json(plan_path, plan)
    expect_error(
        "packaging evidence planned through atlas",
        packaging_atlas,
        "packaging, label, or microcopy evidence must remain a direct image binding",
    )

    expect_error(
        "blocked plan cannot pass standalone gate",
        lambda root, _project, _canon: mutate_plan(
            root, lambda value: value.update({"plan_status": "blocked_capacity"})
        ),
        "standalone success requires ready_for_boundary_supplement",
    )
    expect_error(
        "blocked approval cannot pass standalone gate",
        lambda root, _project, _canon: mutate_plan(
            root, lambda value: value.update({"approval_status": "blocked"})
        ),
        "standalone success requires assistant_validated or user_approved",
    )
    expect_error(
        "blocked reasons cannot pass standalone gate",
        lambda root, _project, _canon: mutate_plan(
            root, lambda value: value.update({"blocked_reasons": ["unresolved"]})
        ),
        "standalone success requires an empty blocked_reasons list",
    )

    def generic_fixed_owner_record(root: Path, project_root: Path, canon: Path) -> None:
        snapshot_path = root / shared.PREFLIGHT_SNAPSHOT
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        entry = next(
            item for item in snapshot["active_artifacts"]
            if item["artifact_id"] == fixture.CHARACTER_ASSET_ID
        )
        generic = fixture.envelope(
            entry["artifact_id"],
            entry["owner_skill"],
            list(entry["affected_shot_uids"]),
            list(entry["dependencies"]),
            status=entry["approval_status"],
            version=entry["version"],
        )
        fixture.finalize(generic)
        record_path = project_root / entry["artifact_record_locator"]
        fixture.write_json(record_path, generic)
        entry["sha256"] = generic["sha256"]
        entry["artifact_record_file_sha256"] = fixture.file_hash(record_path)
        fixture.finalize(snapshot)
        fixture.write_json(snapshot_path, snapshot)
        fixture.write_json(canon, snapshot)

        plan_path = root / shared.PREFLIGHT_PLAN
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        next(
            item for item in plan["dependencies"]
            if item["artifact_id"] == fixture.CHARACTER_ASSET_ID
        )["sha256"] = generic["sha256"]
        next(
            item for item in plan["generation_units"][0]["artifact_decisions"]
            if item["artifact"]["artifact_id"] == fixture.CHARACTER_ASSET_ID
        )["artifact"]["sha256"] = generic["sha256"]
        plan["project_canon_read_receipt"].update({
            "manifest_sha256": snapshot["sha256"],
            "manifest_version": snapshot["version"],
            "snapshot_file_sha256": fixture.file_hash(snapshot_path),
        })
        fixture.finalize(plan)
        fixture.write_json(plan_path, plan)
    expect_error(
        "generic record impersonates fixed owner",
        generic_fixed_owner_record,
        "asset export record must contain exact fields",
    )

    expect_error(
        "missing source Canon",
        lambda _root, _project, canon: canon.unlink(),
        "P1 source Canon: unreadable JSON",
    )

    def split_inside_shot(root: Path, _project: Path, _canon: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            value["generation_units"][0]["ordered_shot_uids"][0] = "S001_PART_A"
        mutate_plan(root, mutate)
    expect_error("non-whole-shot unit", split_inside_shot, "units must preserve exact shot order")

    def provider_over_limit(root: Path, _project: Path, _canon: Path) -> None:
        def mutate(value: dict[str, Any]) -> None:
            unit = value["generation_units"][0]
            for index in range(10):
                unit["planned_future_inputs"].append({
                    "planned_input_id": f"BOUNDARY_RESERVE_{index:02d}",
                    "producer_skill": "ai-video-keyframe-continuity-pack",
                    "control_role": "keyframe_boundary_anchor",
                    "transport_modality": "image",
                    "controlled_shot_uids": list(fixture.SHOTS),
                    "reason": "Adversarial capacity fixture.",
                })
            unit["planned_reference_counts"] = {
                "image": 12, "video": 1, "audio": 0, "total_multimodal": 13,
            }
        mutate_plan(root, mutate)
    expect_error("provider capacity", provider_over_limit, "planned image count exceeds effective provider/backend capacity")

    print(
        "PASS: standalone P1 accepts a no-P2 package and rejects omitted Canon assets, narrowed or "
        "out-of-scope controls, all seven registered visual owners as inline text, packaging-atlas "
        "transport, audio-to-text collapse, fixed-owner role narrowing, atlas dry-build tamper, one-panel atlas plans, "
        "generic fixed-owner records, false-ready states, fake counts, "
        "forged refs, missing Canon, within-shot units, and provider over-capacity plans"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
