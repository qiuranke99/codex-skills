#!/usr/bin/env python3
"""Positive and adversarial tests for PROJECT_CANON_MANIFEST."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_project_canon_manifest import (
    _is_safe_project_locator,
    canonical_hash,
    validate_manifest,
    verify_artifact_files,
)
from validate_manifest_update_receipt import validate_receipt
from validate_project_canon_transition import validate_transition


def artifact(slot: str, artifact_id: str, owner: str, dependencies: list[dict[str, str]]) -> dict[str, object]:
    return {
        "artifact_slot": slot,
        "artifact_id": artifact_id,
        "artifact_type": slot.upper(),
        "owner_skill": owner,
        "version": "1.0.0",
        "sha256": ("a" if artifact_id == "SHOT" else "b") * 64,
        "approval_status": "user_approved",
        "stale_reason": None,
        "eligible_for_downstream": True,
        "affected_shot_uids": ["S001"],
        "locator": f"artifacts/{artifact_id}.json",
        "file_sha256": "f" * 64,
        "artifact_record_locator": f"artifacts/{artifact_id}.json",
        "artifact_record_file_sha256": "f" * 64,
        "dependencies": dependencies,
    }


def fixture() -> dict[str, object]:
    shot = artifact("professional_shot_contract", "SHOT", "ai-video-shot-script-director", [])
    look_dep = {"artifact_id": "SHOT", "owner_skill": "ai-video-shot-script-director", "version": "1.0.0", "sha256": "a" * 64}
    look = artifact("global_look_contract", "LOOK", "ai-video-global-look-lock", [look_dep])
    return {
        "contract_version": "ai-video-artifact-v1",
        "artifact_id": "PROJECT_CANON_MANIFEST_TEST",
        "owner_skill": "ai-video-shot-script-director",
        "version": "1.0.0",
        "sha256": None,
        "approval_status": "draft",
        "dependencies": [],
        "affected_shot_uids": ["S001"],
        "stale_reason": None,
        "schema_version": "ai-video-project-canon-manifest.v1",
        "project_id": "TEST",
        "manifest_role": "artifact_registry_only",
        "manifest_update_policy": "validated_atomic_delta_no_reverse_dependency",
        "current_phase": "global_look",
        "revision_counter": 2,
        "updated_by_skill": "ai-video-global-look-lock",
        "base_manifest_sha256": "c" * 64,
        "canonical_shot_uids": ["S001"],
        "active_artifacts": [shot, look],
        "superseded_artifacts": [],
        "dependency_edges": [{"producer_artifact_id": "SHOT", "consumer_artifact_id": "LOOK", "producer_sha256": "a" * 64, "affected_shot_uids": ["S001"]}],
        "stale_events": [],
        "unresolved_change_requests": [],
    }


def historical_stale_fixture() -> dict[str, object]:
    value = fixture()
    old_producer = copy.deepcopy(value["active_artifacts"][0])
    old_producer.update({"artifact_id": "SHOT_A1", "locator": "artifacts/SHOT_A1.json", "artifact_record_locator": "artifacts/SHOT_A1.json"})
    new_producer = copy.deepcopy(old_producer)
    new_producer.update({
        "artifact_id": "SHOT_A2", "version": "2.0.0", "sha256": "c" * 64,
        "locator": "artifacts/SHOT_A2.json", "artifact_record_locator": "artifacts/SHOT_A2.json",
    })
    old_history = copy.deepcopy(old_producer)
    old_history["eligible_for_downstream"] = False
    old_history["superseded_by_artifact_id"] = "SHOT_A2"
    consumer = copy.deepcopy(value["active_artifacts"][1])
    consumer["dependencies"] = [{
        "artifact_id": "SHOT_A1", "owner_skill": old_producer["owner_skill"],
        "version": old_producer["version"], "sha256": old_producer["sha256"],
    }]
    consumer.update({"approval_status": "stale", "stale_reason": "SHOT_A1 was replaced by SHOT_A2", "eligible_for_downstream": False})
    value["active_artifacts"] = [new_producer, consumer]
    value["superseded_artifacts"] = [old_history]
    value["dependency_edges"] = [{
        "producer_artifact_id": "SHOT_A1", "consumer_artifact_id": "LOOK",
        "producer_sha256": old_producer["sha256"], "affected_shot_uids": ["S001"],
    }]
    value["stale_events"] = [{
        "event_id": "STALE_A2_TO_LOOK", "changed_artifact_id": "SHOT_A2",
        "stale_artifact_ids": ["LOOK"], "affected_shot_uids": ["S001"],
        "reason": "LOOK consumed immutable SHOT_A1 and must be rebuilt against SHOT_A2",
    }]
    return value


def transition_pair() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    base = fixture()
    base["active_artifacts"] = [base["active_artifacts"][0]]
    base["dependency_edges"] = []
    base["version"] = "1.0.0"
    base["revision_counter"] = 1
    base["updated_by_skill"] = "ai-video-shot-script-director"
    base["approval_status"] = "assistant_validated"
    base["sha256"] = canonical_hash(base)
    post = copy.deepcopy(base)
    look = artifact("global_look_contract", "LOOK", "ai-video-global-look-lock", [{
        "artifact_id": "SHOT", "owner_skill": "ai-video-shot-script-director", "version": "1.0.0", "sha256": "a" * 64,
    }])
    post["active_artifacts"].append(look)
    post["dependency_edges"] = [{
        "producer_artifact_id": "SHOT", "consumer_artifact_id": "LOOK",
        "producer_sha256": "a" * 64, "affected_shot_uids": ["S001"],
    }]
    post.update({
        "version": "1.1.0", "revision_counter": 2, "updated_by_skill": "ai-video-global-look-lock",
        "base_manifest_sha256": base["sha256"], "current_phase": "global_look", "sha256": None,
    })
    post["sha256"] = canonical_hash(post)
    receipt = {
        "schema_version": "ai-video-manifest-update-receipt.v1",
        "canonical_manifest_locator": "00_project_canon/PROJECT_CANON_MANIFEST.json",
        "updated_by_skill": "ai-video-global-look-lock",
        "base_manifest_sha256": base["sha256"],
        "resulting_manifest_sha256": post["sha256"],
        "registered_artifact_ids": ["LOOK"],
        "delta_status": "applied",
    }
    return base, post, receipt


def assert_valid(name: str, value: dict[str, object]) -> None:
    errors = validate_manifest(value)
    if errors:
        raise AssertionError(f"{name} unexpectedly failed: {errors}")


def assert_invalid(name: str, value: dict[str, object], needle: str) -> None:
    errors = validate_manifest(value)
    if not any(needle in error for error in errors):
        raise AssertionError(f"{name} did not fail with {needle!r}: {errors}")


def main() -> int:
    for unsafe_locator in (r"artifacts\SHOT.json", r"C:\project\SHOT.json", "/absolute/SHOT.json", "../SHOT.json"):
        if _is_safe_project_locator(unsafe_locator):
            raise AssertionError(f"non-portable project locator was accepted: {unsafe_locator}")
    base = fixture()
    assert_valid("valid draft registry", base)

    frozen = copy.deepcopy(base)
    frozen["approval_status"] = "assistant_validated"
    frozen["sha256"] = canonical_hash(frozen)
    assert_valid("valid frozen registry", frozen)

    reverse = copy.deepcopy(base)
    reverse["active_artifacts"][1]["dependencies"] = [{
        "artifact_id": reverse["artifact_id"],
        "owner_skill": "ai-video-shot-script-director",
        "version": "1.0.0",
        "sha256": "d" * 64,
    }]
    assert_invalid("reverse dependency", reverse, "reverse dependency")

    cycle = copy.deepcopy(base)
    cycle["active_artifacts"][0]["dependencies"] = [{
        "artifact_id": "LOOK", "owner_skill": "ai-video-global-look-lock", "version": "1.0.0", "sha256": "b" * 64,
    }]
    cycle["dependency_edges"].append({"producer_artifact_id": "LOOK", "consumer_artifact_id": "SHOT", "producer_sha256": "b" * 64, "affected_shot_uids": ["S001"]})
    assert_invalid("cycle", cycle, "dependency cycle")

    stale_eligible = copy.deepcopy(base)
    stale_eligible["active_artifacts"][1]["approval_status"] = "stale"
    stale_eligible["active_artifacts"][1]["stale_reason"] = "shot changed"
    assert_invalid("stale eligible", stale_eligible, "cannot be downstream-eligible")

    stale_ancestor = copy.deepcopy(base)
    stale_ancestor["active_artifacts"][0]["approval_status"] = "stale"
    stale_ancestor["active_artifacts"][0]["stale_reason"] = "source script changed"
    stale_ancestor["active_artifacts"][0]["eligible_for_downstream"] = False
    assert_invalid("stale ancestor propagation", stale_ancestor, "must be stale/blocked because producer SHOT is stale")

    historical = historical_stale_fixture()
    assert_valid("active stale consumer retains exact superseded producer lock", historical)
    historical_eligible = copy.deepcopy(historical)
    historical_eligible["active_artifacts"][1].update({"approval_status": "user_approved", "stale_reason": None, "eligible_for_downstream": True})
    assert_invalid("eligible consumer cannot use superseded producer", historical_eligible, "only while stale/blocked")
    missing_stale_event = copy.deepcopy(historical)
    missing_stale_event["stale_events"] = []
    assert_invalid("historical active dependency requires complete event", missing_stale_event, "requires exactly one complete stale_event")

    history_with_dependency = copy.deepcopy(historical)
    old_look = copy.deepcopy(history_with_dependency["active_artifacts"][1])
    old_look.update({
        "artifact_id": "LOOK_B0", "version": "0.9.0", "sha256": "d" * 64,
        "approval_status": "user_approved", "stale_reason": None, "eligible_for_downstream": False,
        "locator": "artifacts/LOOK_B0.json", "artifact_record_locator": "artifacts/LOOK_B0.json",
        "superseded_by_artifact_id": "LOOK",
    })
    history_with_dependency["superseded_artifacts"].append(old_look)
    history_with_dependency["dependency_edges"].append({
        "producer_artifact_id": "SHOT_A1", "consumer_artifact_id": "LOOK_B0",
        "producer_sha256": "a" * 64, "affected_shot_uids": ["S001"],
    })
    assert_valid("superseded consumer dependency resolves through historical DAG", history_with_dependency)
    forged_history_lock = copy.deepcopy(history_with_dependency)
    forged_history_lock["superseded_artifacts"][1]["dependencies"][0]["sha256"] = "e" * 64
    assert_invalid("forged historical dependency lock", forged_history_lock, "lock does not match registered")
    historical_cycle = copy.deepcopy(history_with_dependency)
    historical_cycle["superseded_artifacts"][0]["dependencies"] = [{
        "artifact_id": "LOOK_B0", "owner_skill": "ai-video-global-look-lock", "version": "0.9.0", "sha256": "d" * 64,
    }]
    historical_cycle["dependency_edges"].append({
        "producer_artifact_id": "LOOK_B0", "consumer_artifact_id": "SHOT_A1",
        "producer_sha256": "d" * 64, "affected_shot_uids": ["S001"],
    })
    assert_invalid("historical dependency cycle", historical_cycle, "dependency cycle")

    draft_entry = copy.deepcopy(base)
    draft_entry["active_artifacts"][1]["approval_status"] = "draft"
    draft_entry["active_artifacts"][1]["sha256"] = None
    draft_entry["active_artifacts"][1]["eligible_for_downstream"] = False
    draft_entry["dependency_edges"][0]["consumer_artifact_id"] = "LOOK"
    assert_valid("draft active registry entry", draft_entry)

    malformed = copy.deepcopy(base)
    malformed["canonical_shot_uids"] = [["unhashable"]]
    assert_invalid("malformed shot UID fails closed", malformed, "canonical_shot_uids must be a string array")

    root_extra = copy.deepcopy(base)
    root_extra["out_of_scope_override"] = True
    assert_invalid("root extra rejected", root_extra, "unexpected root fields")

    entry_extra = copy.deepcopy(base)
    entry_extra["active_artifacts"][0]["extra"] = "forbidden"
    assert_invalid("artifact entry extra rejected", entry_extra, "exact artifact-entry fields")

    traversal = copy.deepcopy(base)
    traversal["active_artifacts"][0]["locator"] = "../outside.json"
    assert_invalid("artifact locator traversal rejected", traversal, "safe project-relative")

    half_pair = copy.deepcopy(base)
    half_pair["active_artifacts"][0]["file_sha256"] = None
    assert_invalid("locator/hash half-pair rejected", half_pair, "supplied together")

    record_half_pair = copy.deepcopy(base)
    record_half_pair["active_artifacts"][0]["artifact_record_file_sha256"] = None
    assert_invalid("artifact record locator/hash half-pair rejected", record_half_pair, "record locator and hash")

    edge_extra = copy.deepcopy(base)
    edge_extra["dependency_edges"][0]["extra"] = "forbidden"
    assert_invalid("edge extra rejected", edge_extra, "exact dependency-edge fields")

    garbage_collections = copy.deepcopy(base)
    garbage_collections["superseded_artifacts"] = [{}]
    garbage_collections["stale_events"] = [{}]
    garbage_collections["unresolved_change_requests"] = [{}]
    errors = validate_manifest(garbage_collections)
    for needle in ("exact superseded-entry fields", "exact stale-event fields", "exact change-request fields"):
        if not any(needle in error for error in errors):
            raise AssertionError(f"garbage collection did not fail with {needle!r}: {errors}")

    nested_hash = copy.deepcopy(frozen)
    nested_hash["active_artifacts"][1]["dependencies"][0]["sha256"] = "e" * 64
    if canonical_hash(nested_hash) == frozen["sha256"]:
        raise AssertionError("nested dependency hash was excluded from manifest hash")

    receipt = {
        "schema_version": "ai-video-manifest-update-receipt.v1",
        "canonical_manifest_locator": "00_project_canon/PROJECT_CANON_MANIFEST.json",
        "updated_by_skill": "ai-video-global-look-lock",
        "base_manifest_sha256": "1" * 64,
        "resulting_manifest_sha256": "2" * 64,
        "registered_artifact_ids": ["LOOK"],
        "delta_status": "applied",
    }
    if validate_receipt(receipt, "ai-video-global-look-lock", {"LOOK"}):
        raise AssertionError("valid manifest update receipt rejected")
    duplicate_receipt = copy.deepcopy(receipt)
    duplicate_receipt["registered_artifact_ids"] = ["LOOK", "LOOK"]
    if not validate_receipt(duplicate_receipt):
        raise AssertionError("duplicate receipt IDs were accepted")

    bound_receipt = copy.deepcopy(receipt)
    bound_receipt["base_manifest_sha256"] = frozen["base_manifest_sha256"]
    bound_receipt["resulting_manifest_sha256"] = frozen["sha256"]
    if validate_receipt(bound_receipt, "ai-video-global-look-lock", {"LOOK"}, frozen):
        raise AssertionError("receipt bound to actual canonical manifest was rejected")
    wrong_result = copy.deepcopy(bound_receipt)
    wrong_result["resulting_manifest_sha256"] = "3" * 64
    if not any("must equal canonical manifest sha256" in item for item in validate_receipt(wrong_result, canonical_manifest=frozen)):
        raise AssertionError("receipt with fake resulting hash was accepted")

    transition_base, transition_post, transition_receipt = transition_pair()
    if validate_transition(transition_base, transition_post, "ai-video-global-look-lock", transition_receipt, {"LOOK"}, {"SHOT"}):
        raise AssertionError("valid immutable-base atomic transition was rejected")
    stale_base_attack = copy.deepcopy(transition_post)
    stale_base_attack["base_manifest_sha256"] = "9" * 64
    stale_base_attack["sha256"] = canonical_hash(stale_base_attack)
    if not any("actual base snapshot" in item for item in validate_transition(transition_base, stale_base_attack, "ai-video-global-look-lock")):
        raise AssertionError("stale/fake base snapshot attack was accepted")
    owner_only_attack = copy.deepcopy(transition_post)
    owner_only_attack["active_artifacts"][0]["artifact_type"] = "FORGED_BY_LOOK"
    owner_only_attack["sha256"] = canonical_hash(owner_only_attack)
    owner_errors = validate_transition(transition_base, owner_only_attack, "ai-video-global-look-lock")
    if not any("another owner's artifact content/identity" in item for item in owner_errors):
        raise AssertionError(f"owner-only delta attack was accepted: {owner_errors}")
    preserved_attack = copy.deepcopy(transition_post)
    preserved_attack["active_artifacts"][0]["stale_reason"] = "fake preservation"
    preserved_attack["active_artifacts"][0]["approval_status"] = "stale"
    preserved_attack["active_artifacts"][0]["eligible_for_downstream"] = False
    preserved_attack["sha256"] = canonical_hash(preserved_attack)
    preserved_errors = validate_transition(transition_base, preserved_attack, "ai-video-global-look-lock", preserved_artifact_ids={"SHOT"})
    if not any("declared preserved artifact changed" in item for item in preserved_errors):
        raise AssertionError(f"fake preserved-artifact claim was accepted: {preserved_errors}")

    with tempfile.TemporaryDirectory() as transition_tmp:
        transition_root = Path(transition_tmp)
        base_path = transition_root / "BASE_PROJECT_CANON_SNAPSHOT.json"
        post_path = transition_root / "PROJECT_CANON_MANIFEST.json"
        receipt_path = transition_root / "MANIFEST_UPDATE_RECEIPT.json"
        base_path.write_text(json.dumps(transition_base, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        post_path.write_text(json.dumps(transition_post, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        receipt_path.write_text(json.dumps(transition_receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        snapshot_file_hash = hashlib.sha256(base_path.read_bytes()).hexdigest()
        command = [
            sys.executable, str(Path(__file__).with_name("validate_project_canon_transition.py")),
            str(base_path), str(post_path), "--base-snapshot-file-sha256", snapshot_file_hash,
            "--updated-by-skill", "ai-video-global-look-lock", "--receipt", str(receipt_path),
            "--expected-registered-artifact-id", "LOOK", "--preserved-artifact-id", "SHOT",
        ]
        if subprocess.run(command, capture_output=True, text=True).returncode != 0:
            raise AssertionError("raw-hash-bound atomic transition CLI rejected valid base/post bytes")
        stale_file_hash_command = copy.deepcopy(command)
        stale_file_hash_command[stale_file_hash_command.index(snapshot_file_hash)] = "0" * 64
        if subprocess.run(stale_file_hash_command, capture_output=True, text=True).returncode == 0:
            raise AssertionError("atomic transition CLI accepted a forged base snapshot raw file hash")

    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        artifact_path = project / "artifacts/SHOT.json"
        artifact_path.parent.mkdir(parents=True)
        real_artifact = {
            "contract_version": "ai-video-artifact-v1",
            "artifact_id": "SHOT",
            "owner_skill": "ai-video-shot-script-director",
            "version": "1.0.0",
            "sha256": None,
            "approval_status": "assistant_validated",
            "dependencies": [],
            "affected_shot_uids": ["S001"],
            "stale_reason": None,
        }
        real_artifact["sha256"] = canonical_hash(real_artifact)
        artifact_path.write_text(json.dumps(real_artifact, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        verified = fixture()
        verified["active_artifacts"] = [artifact("professional_shot_contract", "SHOT", "ai-video-shot-script-director", [])]
        verified["active_artifacts"][0].update({
            "sha256": real_artifact["sha256"],
            "approval_status": real_artifact["approval_status"],
            "file_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            "artifact_record_file_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        })
        verified["dependency_edges"] = []
        if validate_manifest(verified) or verify_artifact_files(verified, project):
            raise AssertionError("real registered artifact bytes were rejected")

        pseudo_artifact = copy.deepcopy(real_artifact)
        pseudo_artifact["approval_status"] = "user_approved"
        pseudo_artifact["sha256"] = "9" * 64
        artifact_path.write_text(json.dumps(pseudo_artifact, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        verified["active_artifacts"][0]["sha256"] = pseudo_artifact["sha256"]
        verified["active_artifacts"][0]["file_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        verified["active_artifacts"][0]["artifact_record_file_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        if not any("pseudo/non-canonical" in item for item in verify_artifact_files(verified, project)):
            raise AssertionError("JSON artifact pseudo hash was accepted")

        artifact_path.write_bytes(b"tampered bytes")
        if not any("file_sha256 mismatch" in item for item in verify_artifact_files(verified, project)):
            raise AssertionError("registered artifact byte drift was accepted")

        binary_path = project / "artifacts/LOOK_REFERENCE.bin"
        binary_path.write_bytes(b"reference pixels")
        record_path = project / "owned_artifacts/LOOK_REFERENCE_ASSET_TEST.json"
        binary_record = {
            "contract_version": "ai-video-artifact-v1",
            "artifact_id": "LOOK_REFERENCE_ASSET_TEST",
            "owner_skill": "ai-video-global-look-lock",
            "version": "1.0.0",
            "sha256": "8" * 64,
            "approval_status": "assistant_validated",
            "dependencies": [],
            "affected_shot_uids": ["S001"],
            "stale_reason": None,
        }
        record_path.parent.mkdir(parents=True, exist_ok=True)
        record_path.write_text(json.dumps(binary_record, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        binary_canon = fixture()
        binary_canon["active_artifacts"] = [{
            "artifact_slot": "global_look_reference:test",
            "artifact_id": binary_record["artifact_id"],
            "artifact_type": "global_look_reference",
            "owner_skill": binary_record["owner_skill"],
            "version": binary_record["version"],
            "sha256": binary_record["sha256"],
            "approval_status": binary_record["approval_status"],
            "stale_reason": None,
            "eligible_for_downstream": True,
            "affected_shot_uids": ["S001"],
            "locator": "artifacts/LOOK_REFERENCE.bin",
            "file_sha256": hashlib.sha256(binary_path.read_bytes()).hexdigest(),
            "artifact_record_locator": "owned_artifacts/LOOK_REFERENCE_ASSET_TEST.json",
            "artifact_record_file_sha256": hashlib.sha256(record_path.read_bytes()).hexdigest(),
            "dependencies": [],
        }]
        binary_canon["dependency_edges"] = []
        if not any("pseudo/non-canonical" in item for item in verify_artifact_files(binary_canon, project)):
            raise AssertionError("binary artifact pseudo hash was accepted despite record sidecar")

        binary_record["sha256"] = canonical_hash(binary_record)
        record_path.write_text(json.dumps(binary_record, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        overlay = copy.deepcopy(binary_canon)
        overlay_entry = overlay["active_artifacts"][0]
        overlay_entry.update({
            "sha256": binary_record["sha256"],
            "artifact_record_file_sha256": hashlib.sha256(record_path.read_bytes()).hexdigest(),
            "approval_status": "stale", "stale_reason": "replacement invalidated this control",
            "eligible_for_downstream": False,
        })
        overlay["stale_events"] = [{
            "event_id": "STALE_OVERLAY_TEST", "changed_artifact_id": binary_record["artifact_id"],
            "stale_artifact_ids": [binary_record["artifact_id"]], "affected_shot_uids": ["S001"],
            "reason": "replacement invalidated this control",
        }]
        overlay_errors = verify_artifact_files(overlay, project)
        if overlay_errors:
            raise AssertionError(f"event-bound stale registry overlay was rejected: {overlay_errors}")
        overlay["stale_events"] = []
        if not any("event-bound Canon stale overlay" in item for item in verify_artifact_files(overlay, project)):
            raise AssertionError("status-divergent stale overlay without an event was accepted")

    print("PASS: PROJECT_CANON_MANIFEST DAG/hash tests and shared update-receipt tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
