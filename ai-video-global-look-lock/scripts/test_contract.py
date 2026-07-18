#!/usr/bin/env python3
"""Positive and adversarial tests for ai-video-global-look-lock."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Callable

from validate_global_look import canonical_sha256, render_shot_look_delta_prompt, validate_canon_registration, validate_look, verify_declared_file_hashes
from ai_video_input_contracts import canonical_hash, revision_semantic_view, semantic_diff_pointers


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "references" / "global_look_contract.template.json"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def entry(artifact: dict, slot: str, artifact_type: str, locator: str, binary_hash: str, record_locator: str, record_hash: str) -> dict:
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
        "artifact_record_file_sha256": record_hash,
        "dependencies": artifact["dependencies"],
    }


def template() -> dict:
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def approve_references(record: dict) -> None:
    state_refs = {state["state_id"]: set(state["reference_ids"]) for state in record["look_states"]}
    assigned_state = {item["shot_uid"]: item["state_id"] for item in record["shot_look_assignments"]}
    for index, ref in enumerate(record["look_reference_set"], start=1):
        ref.update({
            "approval_status": "approved",
            "inspection_status": "passed",
            "integrity_status": "verified_bytes",
            "file_sha256": f"{index:x}" * 64,
            "actual_dimensions": {"width": 1920, "height": 1080},
            "intrinsic_boundary_check": "passed",
        })
        if ref["source_type"] == "machine_generated":
            ref["generation_prompt_sha256"] = "f" * 64
        artifact = ref["artifact"]
        artifact["dependencies"] = copy.deepcopy(record["dependencies"])
        artifact["affected_shot_uids"] = [
            uid for uid in record["project_shot_uids"]
            if ref["reference_id"] in state_refs.get(assigned_state.get(uid), set())
        ]
        artifact["approval_status"] = "assistant_validated"
        artifact["sha256"] = canonical_sha256(artifact)


def freeze(record: dict) -> dict:
    approve_references(record)
    for risk in record["look_risk_coverage"]:
        risk["coverage_status"] = "covered"
    record["three_layer_lock"]["textual_contract_frozen"] = True
    record["three_layer_lock"]["visual_reference_set_approved"] = True
    record["approval_status"] = "assistant_validated"
    record["sha256"] = canonical_sha256(record)
    return record


def multi_state_pass() -> dict:
    return freeze(template())


def single_state_pass() -> dict:
    record = template()
    record["project_constraints"]["multiple_look_states"] = False
    record["project_shot_uids"] = ["S001"]
    record["affected_shot_uids"] = ["S001"]
    record["look_states"] = [record["look_states"][0]]
    record["look_reference_set"] = [record["look_reference_set"][0]]
    record["look_reference_set"][0]["applicable_state_ids"] = ["LOOK_STATE_FIELD"]
    record["shot_look_assignments"] = [record["shot_look_assignments"][0]]
    for risk in record["look_risk_coverage"]:
        risk["state_ids"] = ["LOOK_STATE_FIELD"]
        risk["reference_ids"] = ["LOOK_REF_HERO_001"]
        risk["affected_shot_uids"] = ["S001"]
    record["revision_scope"]["changed_state_ids"] = ["LOOK_STATE_FIELD"]
    record["revision_scope"]["changed_shot_uids"] = ["S001"]
    return freeze(record)


def missing_state_reference() -> dict:
    record = multi_state_pass()
    record["look_states"][1]["reference_ids"] = []
    record["sha256"] = canonical_sha256(record)
    return record


def missing_product_boundary() -> dict:
    record = multi_state_pass()
    record["intrinsic_product_boundaries"] = []
    record["sha256"] = canonical_sha256(record)
    return record


def broken_three_layer_lock() -> dict:
    record = multi_state_pass()
    record["three_layer_lock"]["exact_prompt_injection_required"] = False
    record["sha256"] = canonical_sha256(record)
    return record


def bad_core_revision_scope() -> dict:
    record = multi_state_pass()
    record["revision_scope"].update({
        "mode": "core_revision",
        "look_core_changed": True,
        "invalidated_artifact_ids": ["STORYBOARD_S001"],
    })
    record["affected_shot_uids"] = ["S001"]
    record["sha256"] = canonical_sha256(record)
    return record


def cropped_multipanel_reference() -> dict:
    record = multi_state_pass()
    record["look_reference_set"][0]["derived_from_multipanel"] = True
    record["look_reference_set"][0]["independent_full_frame"] = False
    record["sha256"] = canonical_sha256(record)
    return record


def uncovered_declared_risk() -> dict:
    record = multi_state_pass()
    record["look_risk_coverage"][0]["coverage_status"] = "planned"
    record["sha256"] = canonical_sha256(record)
    return record


def nested_hash_pair() -> tuple[dict, dict]:
    original = multi_state_pass()
    mutated = copy.deepcopy(original)
    mutated["dependencies"][0]["sha256"] = "b" * 64
    return original, mutated


def dependency_extra_field() -> dict:
    record = multi_state_pass()
    record["dependencies"][0]["extra"] = "forbidden"
    record["sha256"] = canonical_sha256(record)
    return record


def malformed_shot_scope() -> dict:
    record = template()
    record["affected_shot_uids"] = [["unhashable"]]
    return record


def root_extra_field() -> dict:
    record = multi_state_pass()
    record["out_of_scope_override"] = True
    record["sha256"] = canonical_sha256(record)
    return record


def core_prompt_drift() -> dict:
    record = multi_state_pass()
    record["look_core"]["lighting_architecture"] = ["a completely contradictory flat frontal flash rule"]
    record["sha256"] = canonical_sha256(record)
    return record


def delta_prompt_paraphrase() -> dict:
    record = multi_state_pass()
    record["shot_look_assignments"][0]["shot_look_delta_prompt_full"] = (
        "SHOT LOOK DELTA: no local change is needed; keep the approved Core."
    )
    record["sha256"] = canonical_sha256(record)
    return record


def delta_prompt_wrong_boolean() -> dict:
    record = multi_state_pass()
    prompt = record["shot_look_assignments"][0]["shot_look_delta_prompt_full"]
    record["shot_look_assignments"][0]["shot_look_delta_prompt_full"] = prompt.replace("active: false", "active: true")
    record["sha256"] = canonical_sha256(record)
    return record


def forged_reference_artifact_id() -> dict:
    record = multi_state_pass()
    record["look_reference_set"][0]["artifact"]["artifact_id"] = "LOOK_REF_HERO_001"
    record["look_reference_set"][0]["artifact"]["sha256"] = canonical_sha256(record["look_reference_set"][0]["artifact"])
    record["sha256"] = canonical_sha256(record)
    return record


def reference_artifact_scope_drift() -> dict:
    record = multi_state_pass()
    record["look_reference_set"][0]["artifact"]["affected_shot_uids"] = ["S001"]
    record["look_reference_set"][0]["artifact"]["sha256"] = canonical_sha256(record["look_reference_set"][0]["artifact"])
    record["sha256"] = canonical_sha256(record)
    return record


def shot_delta_revision_pair() -> tuple[dict, dict]:
    previous = multi_state_pass()
    current = copy.deepcopy(previous)
    current["version"] = "1.0.1"
    delta = current["shot_look_assignments"][0]["shot_look_delta"]
    delta.update({
        "active": True,
        "scope": ["atmosphere"],
        "description": "slightly reduce haze around the hero silhouette",
        "reason": "preserve product separation without changing the approved Core",
    })
    current["shot_look_assignments"][0]["shot_look_delta_prompt_full"] = render_shot_look_delta_prompt(delta)
    current["revision_scope"].update({
        "mode": "shot_delta_revision",
        "requested_state_ids": [],
        "changed_state_ids": [],
        "requested_shot_uids": ["S001"],
        "changed_shot_uids": ["S001"],
        "look_core_changed": False,
        "invalidated_artifact_ids": ["STORYBOARD_S001"],
        "preserved_artifact_ids": ["STORYBOARD_S002"],
        "predecessor_artifact": {field: previous[field] for field in ("artifact_id", "owner_skill", "version", "sha256")},
    })
    current["revision_scope"]["changed_json_pointers"] = semantic_diff_pointers(
        revision_semantic_view(previous), revision_semantic_view(current)
    )
    current["sha256"] = canonical_sha256(current)
    return previous, current


def state_revision_pair() -> tuple[dict, dict]:
    previous = multi_state_pass()
    current = copy.deepcopy(previous)
    current["version"] = "1.1.0"
    current["look_states"][0]["name"] = "field daylight hero state refined"
    current["revision_scope"].update({
        "mode": "state_revision",
        "requested_state_ids": ["LOOK_STATE_FIELD"],
        "changed_state_ids": ["LOOK_STATE_FIELD"],
        "requested_shot_uids": [],
        "changed_shot_uids": ["S001"],
        "look_core_changed": False,
        "invalidated_artifact_ids": ["STORYBOARD_S001"],
        "preserved_artifact_ids": ["STORYBOARD_S002"],
        "predecessor_artifact": {field: previous[field] for field in ("artifact_id", "owner_skill", "version", "sha256")},
    })
    current["revision_scope"]["changed_json_pointers"] = semantic_diff_pointers(
        revision_semantic_view(previous), revision_semantic_view(current)
    )
    current["sha256"] = canonical_sha256(current)
    return previous, current


def run_case(name: str, factory: Callable[[], dict], should_pass: bool) -> bool:
    errors = validate_look(factory())
    passed = not errors
    ok = passed == should_pass
    print(f"{'PASS' if ok else 'FAIL'} {name}: validator={'pass' if passed else 'fail'}")
    if not ok:
        for error in errors:
            print(f"  {error}")
    return ok


def canon_registration_integration() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        shot = {
            "contract_version": "ai-video-artifact-v1",
            "artifact_id": "SHOT_CONTRACT_LOOK_TEST",
            "owner_skill": "ai-video-shot-script-director",
            "version": "1.0.0",
            "sha256": None,
            "approval_status": "assistant_validated",
            "dependencies": [],
            "affected_shot_uids": ["SHT_001", "SHT_002"],
            "stale_reason": None,
        }
        shot["sha256"] = canonical_hash(shot)
        shot_rel = "01_script/SHOT_CONTRACT.json"
        write_json(project / shot_rel, shot)

        look = multi_state_pass()
        shot_ref = {field: shot[field] for field in ("artifact_id", "owner_skill", "version", "sha256")}
        look["dependencies"] = [shot_ref]
        record_rels: dict[str, str] = {}
        for index, reference in enumerate(look["look_reference_set"], 1):
            binary_rel = f"02_global_look/references/{reference['reference_id']}.bin"
            binary_path = project / binary_rel
            binary_path.parent.mkdir(parents=True, exist_ok=True)
            binary_path.write_bytes(f"look-reference-{index}".encode("utf-8"))
            reference["locator"] = binary_rel
            reference["file_sha256"] = file_hash(binary_path)
            prompt_path = project / f"02_global_look/prompts/{reference['reference_id']}.md"
            prompt_path.parent.mkdir(parents=True, exist_ok=True)
            prompt_path.write_text(f"frozen generation prompt {index}", encoding="utf-8")
            reference["generation_prompt_sha256"] = file_hash(prompt_path)
            artifact = reference["artifact"]
            artifact["dependencies"] = [shot_ref]
            artifact["sha256"] = canonical_sha256(artifact)
            record_rel = f"02_global_look/owned_artifacts/{artifact['artifact_id']}.json"
            write_json(project / record_rel, artifact)
            record_rels[reference["reference_id"]] = record_rel
        look["sha256"] = canonical_sha256(look)
        look_rel = "02_global_look/GLOBAL_LOOK.json"
        write_json(project / look_rel, look)

        active = [
            entry(shot, "professional_shot_contract", "shot_contract", shot_rel, file_hash(project / shot_rel), shot_rel, file_hash(project / shot_rel)),
            entry(look, "global_look_contract", "global_look", look_rel, file_hash(project / look_rel), look_rel, file_hash(project / look_rel)),
        ]
        for reference in look["look_reference_set"]:
            artifact = reference["artifact"]
            record_rel = record_rels[reference["reference_id"]]
            active.append(entry(
                artifact,
                f"global_look_reference:{artifact['artifact_id']}",
                "global_look_reference",
                reference["locator"],
                reference["file_sha256"],
                record_rel,
                file_hash(project / record_rel),
            ))
        edges = []
        for consumer in active[1:]:
            edges.append({
                "producer_artifact_id": shot["artifact_id"],
                "consumer_artifact_id": consumer["artifact_id"],
                "producer_sha256": shot["sha256"],
                "affected_shot_uids": consumer["affected_shot_uids"],
            })
        canon = {
            "contract_version": "ai-video-artifact-v1",
            "artifact_id": "PROJECT_CANON_MANIFEST_LOOK_TEST",
            "owner_skill": "ai-video-shot-script-director",
            "version": "1.0.0",
            "sha256": None,
            "approval_status": "assistant_validated",
            "dependencies": [],
            "affected_shot_uids": look["project_shot_uids"],
            "stale_reason": None,
            "schema_version": "ai-video-project-canon-manifest.v1",
            "project_id": "LOOK_TEST",
            "manifest_role": "artifact_registry_only",
            "manifest_update_policy": "validated_atomic_delta_no_reverse_dependency",
            "current_phase": "global_look",
            "revision_counter": 1,
            "updated_by_skill": "ai-video-global-look-lock",
            "base_manifest_sha256": "e" * 64,
            "canonical_shot_uids": look["project_shot_uids"],
            "active_artifacts": active,
            "superseded_artifacts": [],
            "dependency_edges": edges,
            "stale_events": [],
            "unresolved_change_requests": [],
        }
        canon["sha256"] = canonical_hash(canon)
        receipt = {
            "schema_version": "ai-video-manifest-update-receipt.v1",
            "canonical_manifest_locator": "00_project_canon/PROJECT_CANON_MANIFEST.json",
            "updated_by_skill": "ai-video-global-look-lock",
            "base_manifest_sha256": canon["base_manifest_sha256"],
            "resulting_manifest_sha256": canon["sha256"],
            "registered_artifact_ids": [look["artifact_id"], *[ref["artifact"]["artifact_id"] for ref in look["look_reference_set"]]],
            "delta_status": "applied",
        }
        integration_errors = [*validate_look(look), *verify_declared_file_hashes(look, project), *validate_canon_registration(look, canon, project, receipt)]
        if integration_errors:
            print("  Canon integration errors:", integration_errors)
            return False

        unregistered = copy.deepcopy(canon)
        removed_id = look["look_reference_set"][0]["artifact"]["artifact_id"]
        unregistered["active_artifacts"] = [item for item in unregistered["active_artifacts"] if item["artifact_id"] != removed_id]
        unregistered["dependency_edges"] = [item for item in unregistered["dependency_edges"] if item["consumer_artifact_id"] != removed_id]
        unregistered["sha256"] = canonical_hash(unregistered)
        unregistered_errors = validate_canon_registration(look, unregistered, project)
        if not any("nested artifact is not registered" in item for item in unregistered_errors):
            print("  Unregistered-reference errors:", unregistered_errors)
            return False

        tampered = project / look["look_reference_set"][0]["locator"]
        tampered.write_bytes(b"tampered pixels")
        tamper_errors = [*verify_declared_file_hashes(look, project), *validate_canon_registration(look, canon, project)]
        if not any("file_sha256 mismatch" in item for item in tamper_errors):
            print("  Tampered-reference errors:", tamper_errors)
            return False
    return True


def main() -> int:
    results = [
        run_case("single-scene one-State look", single_state_pass, True),
        run_case("multi-scene Core plus States", multi_state_pass, True),
        run_case("missing State visual coverage", missing_state_reference, False),
        run_case("missing product intrinsic boundary", missing_product_boundary, False),
        run_case("broken three-layer inheritance", broken_three_layer_lock, False),
        run_case("Core revision with partial invalidation", bad_core_revision_scope, False),
        run_case("reference cropped from multipanel", cropped_multipanel_reference, False),
        run_case("declared look risk remains unproved", uncovered_declared_risk, False),
        run_case("dependency extra field", dependency_extra_field, False),
        run_case("malformed shot scope fails closed", malformed_shot_scope, False),
        run_case("root extra field", root_extra_field, False),
        run_case("Core structured rule missing from frozen prompt", core_prompt_drift, False),
        run_case("Delta paraphrase cannot replace frozen authority", delta_prompt_paraphrase, False),
        run_case("Delta prompt boolean must equal structured authority", delta_prompt_wrong_boolean, False),
        run_case("look reference internal ID cannot impersonate artifact ID", forged_reference_artifact_id, False),
        run_case("look reference artifact scope follows State assignments", reference_artifact_scope_drift, False),
    ]
    original, mutated = nested_hash_pair()
    hash_ok = not validate_look(original) and any("sha256 mismatch" in item for item in validate_look(mutated))
    print(f"{'PASS' if hash_ok else 'FAIL'} nested dependency hash participates in envelope hash")
    results.append(hash_ok)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_path = root / "look.jpg"
        source_path.write_bytes(b"verified look source")
        record = template()
        record["source_inputs"][0]["locator"] = "look.jpg"
        record["source_inputs"][0]["integrity_status"] = "verified_bytes"
        record["source_inputs"][0]["file_sha256"] = hashlib.sha256(source_path.read_bytes()).hexdigest()
        file_ok = not verify_declared_file_hashes(record, root)
        record["source_inputs"][0]["locator"] = str(source_path.resolve())
        file_ok = file_ok and any("project-root-relative" in item for item in verify_declared_file_hashes(record, root))
        outside_path = root.parent / "outside-look.jpg"
        outside_path.write_bytes(b"outside verified look")
        record["source_inputs"][0]["locator"] = "../outside-look.jpg"
        record["source_inputs"][0]["file_sha256"] = hashlib.sha256(outside_path.read_bytes()).hexdigest()
        file_ok = file_ok and any("project-root-relative" in item for item in verify_declared_file_hashes(record, root))
        record["source_inputs"][0]["locator"] = "look.jpg"
        record["source_inputs"][0]["file_sha256"] = hashlib.sha256(source_path.read_bytes()).hexdigest()
        source_path.write_bytes(b"mutated")
        file_ok = file_ok and any("file_sha256 mismatch" in item for item in verify_declared_file_hashes(record, root))
    print(f"{'PASS' if file_ok else 'FAIL'} verified look-source bytes are root-confined and re-hashed")
    results.append(file_ok)
    previous_delta, current_delta = shot_delta_revision_pair()
    delta_revision_errors = validate_look(current_delta, previous_delta)
    delta_revision_ok = not delta_revision_errors
    print(f"{'PASS' if delta_revision_ok else 'FAIL'} shot-Delta revision binds predecessor and exact field diff")
    if delta_revision_errors:
        print("  " + "\n  ".join(delta_revision_errors))
    results.append(delta_revision_ok)

    previous_state, current_state = state_revision_pair()
    state_revision_errors = validate_look(current_state, previous_state)
    state_revision_ok = not state_revision_errors
    print(f"{'PASS' if state_revision_ok else 'FAIL'} State revision derives exact affected State and Shot IDs")
    if state_revision_errors:
        print("  " + "\n  ".join(state_revision_errors))
    results.append(state_revision_ok)

    same_version = copy.deepcopy(current_delta)
    same_version["version"] = previous_delta["version"]
    same_version["sha256"] = canonical_sha256(same_version)
    same_version_ok = any("SemVer must be greater" in item for item in validate_look(same_version, previous_delta))
    print(f"{'PASS' if same_version_ok else 'FAIL'} Global Look same-version revision attack fails closed")
    results.append(same_version_ok)

    unreported = copy.deepcopy(current_delta)
    unreported["shot_look_assignments"][1]["shot_look_delta"]["reason"] = "an undeclared change to a second shot"
    unreported["shot_look_assignments"][1]["shot_look_delta_prompt_full"] = render_shot_look_delta_prompt(unreported["shot_look_assignments"][1]["shot_look_delta"])
    unreported["sha256"] = canonical_sha256(unreported)
    unreported_ok = any("changed_json_pointers does not exactly match" in item for item in validate_look(unreported, previous_delta))
    print(f"{'PASS' if unreported_ok else 'FAIL'} Global Look undeclared field change fails closed")
    results.append(unreported_ok)

    fake_preserved = copy.deepcopy(current_delta)
    fake_preserved["revision_scope"]["preserved_artifact_ids"] = ["STORYBOARD_S001"]
    fake_preserved["sha256"] = canonical_sha256(fake_preserved)
    fake_preserved_ok = any("must be disjoint" in item for item in validate_look(fake_preserved, previous_delta))
    print(f"{'PASS' if fake_preserved_ok else 'FAIL'} Global Look invalidated artifact cannot be declared preserved")
    results.append(fake_preserved_ok)
    canon_ok = canon_registration_integration()
    print(f"{'PASS' if canon_ok else 'FAIL'} root plus first-class look-reference assets bind to Canon/receipt and real bytes")
    results.append(canon_ok)
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
