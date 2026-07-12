#!/usr/bin/env python3
"""Positive and adversarial contract tests for ai-video-shot-script-director."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Callable

from validate_shot_contract import canonical_sha256, validate_contract, verify_declared_file_hashes
from revision_evidence import revision_semantic_view, semantic_diff_pointers


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "references" / "shot_contract.template.json"


def load_template() -> dict:
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def freeze(record: dict, status: str = "assistant_validated") -> dict:
    record["approval_status"] = status
    record["sha256"] = canonical_sha256(record)
    return record


def poetic_pass() -> dict:
    return freeze(load_template())


def functional_pass() -> dict:
    record = load_template()
    record["source_inputs"].append({
        "source_id": "SOURCE_BRIEF_001",
        "locator": "user-provided/product-brief.pdf",
        "source_type": "product_evidence",
        "file_sha256": None,
        "integrity_status": "runtime_reference_bound",
        "authority_scope": ["product statement"],
        "extraction_status": "complete",
    })
    record["source_classification"].update({
        "creative_mode": "functional_demonstration",
        "primary_mode": "functional_demonstration",
        "narrative_logic": "literal_state_change",
        "product_expression": "supported_operation",
        "literal_usage_demo": True,
    })
    record["shots"][0]["submode"] = "functional_demonstration"
    record["shots"][0]["initial_state"] = "supported source state before application"
    record["shots"][0]["action_path"] = ["perform the source-supported application step"]
    record["shots"][0]["ending_state"] = "source-supported visible end state"
    record["claim_boundary"]["supplied_claims"] = [{
        "claim_id": "CLAIM_001",
        "text": "User-supplied product statement",
        "source_reference_ids": ["SOURCE_BRIEF_001"],
    }]
    record["claim_boundary"]["used_claim_ids"] = ["CLAIM_001"]
    record["claim_boundary"]["claim_generation_status"] = "source_supported_claims_only"
    return freeze(record)


def bad_timing() -> dict:
    record = poetic_pass()
    record["timeline"]["total_duration_seconds"] = 3.0
    record["sha256"] = canonical_sha256(record)
    return record


def invented_claim() -> dict:
    record = functional_pass()
    record["claim_boundary"]["used_claim_ids"].append("CLAIM_INVENTED_EFFICACY")
    record["sha256"] = canonical_sha256(record)
    return record


def bad_selective_revision() -> dict:
    record = poetic_pass()
    record["revision_scope"].update({
        "mode": "selective_revision",
        "requested_shot_uids": [],
        "actually_changed_shot_uids": ["S001"],
        "global_fields_changed": False,
        "expanded_dependency_reasons": [],
    })
    record["sha256"] = canonical_sha256(record)
    return record


def changed_nested_dependency_hash_detected() -> tuple[dict, dict]:
    record = load_template()
    record["dependencies"] = [{
        "artifact_id": "PRODUCT_001",
        "owner_skill": "material-sensitive-product-master-asset-board",
        "version": "1.0.0",
        "sha256": "a" * 64,
    }]
    frozen = freeze(record)
    mutated = copy.deepcopy(frozen)
    mutated["dependencies"][0]["sha256"] = "b" * 64
    return frozen, mutated


def invalid_dependency_version() -> dict:
    record = load_template()
    record["dependencies"] = [{
        "artifact_id": "PRODUCT_001",
        "owner_skill": "material-sensitive-product-master-asset-board",
        "version": "latest",
        "sha256": "a" * 64,
    }]
    return record


def dependency_extra_field() -> dict:
    record = load_template()
    record["dependencies"] = [{
        "artifact_id": "PRODUCT_001",
        "owner_skill": "material-sensitive-product-master-asset-board",
        "version": "1.0.0",
        "sha256": "a" * 64,
        "extra": "forbidden",
    }]
    return record


def malformed_affected_scope() -> dict:
    record = load_template()
    record["affected_shot_uids"] = [None]
    return record


def root_extra_field() -> dict:
    record = load_template()
    record["out_of_scope_override"] = True
    return record


def isolated_hard_fact_blocker_pass() -> dict:
    record = load_template()
    record["isolated_blockers"] = [{
        "blocker_id": "BLOCKER_TARGET_PRODUCT",
        "blocker_type": "target_product_source_conflict",
        "required_fact": "which of two contradictory source packages is the advertised product",
        "reason": "choosing either would change the work's commercial identity",
        "affected_shot_uids": ["S001"],
        "unaffected_work_completed": True,
    }]
    return freeze(record, "blocked")


def ordinary_directing_gap_cannot_block() -> dict:
    record = load_template()
    record["isolated_blockers"] = [{
        "blocker_id": "BLOCKER_CAMERA_HEIGHT",
        "blocker_type": "missing_camera_height",
        "required_fact": "camera height",
        "reason": "the rough script did not specify professional camera language",
        "affected_shot_uids": ["S001"],
        "unaffected_work_completed": True,
    }]
    return freeze(record, "blocked")


def blocker_cannot_abandon_unaffected_work() -> dict:
    record = isolated_hard_fact_blocker_pass()
    record["isolated_blockers"][0]["unaffected_work_completed"] = False
    record["sha256"] = canonical_sha256(record)
    return record


def selective_revision_pair() -> tuple[dict, dict]:
    previous = poetic_pass()
    current = copy.deepcopy(previous)
    current["version"] = "1.0.1"
    current["shots"][0]["composition"] = "subject remains centered while a foreground occluder creates measured parallax"
    current["revision_scope"].update({
        "mode": "selective_revision",
        "requested_shot_uids": ["S001"],
        "actually_changed_shot_uids": ["S001"],
        "global_fields_changed": False,
        "expanded_dependency_reasons": [],
        "invalidated_artifact_ids": ["STORYBOARD_S001"],
        "preserved_artifact_ids": ["PRODUCT_CANON_001"],
        "predecessor_artifact": {field: previous[field] for field in ("artifact_id", "owner_skill", "version", "sha256")},
    })
    current["revision_scope"]["changed_json_pointers"] = semantic_diff_pointers(
        revision_semantic_view(previous), revision_semantic_view(current)
    )
    current["sha256"] = canonical_sha256(current)
    return previous, current


def run_case(name: str, factory: Callable[[], dict], should_pass: bool) -> bool:
    errors = validate_contract(factory())
    passed = not errors
    ok = passed == should_pass
    print(f"{'PASS' if ok else 'FAIL'} {name}: validator={'pass' if passed else 'fail'}")
    if not ok:
        for error in errors:
            print(f"  {error}")
    return ok


def main() -> int:
    results = [
        run_case("poetic structured draft", poetic_pass, True),
        run_case("source-supported functional ad", functional_pass, True),
        run_case("time budget mismatch", bad_timing, False),
        run_case("invented efficacy claim", invented_claim, False),
        run_case("invalid selective revision", bad_selective_revision, False),
        run_case("dependency version is not SemVer", invalid_dependency_version, False),
        run_case("dependency extra field", dependency_extra_field, False),
        run_case("malformed affected scope fails closed", malformed_affected_scope, False),
        run_case("root extra field", root_extra_field, False),
        run_case("isolated genuine hard fact preserves completed work", isolated_hard_fact_blocker_pass, True),
        run_case("ordinary directing gap cannot become blocker", ordinary_directing_gap_cannot_block, False),
        run_case("hard blocker cannot abandon unaffected work", blocker_cannot_abandon_unaffected_work, False),
    ]
    original, mutated = changed_nested_dependency_hash_detected()
    nested_ok = not validate_contract(original) and any("sha256 mismatch" in item for item in validate_contract(mutated))
    print(f"{'PASS' if nested_ok else 'FAIL'} nested dependency hash participates in envelope hash")
    results.append(nested_ok)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_path = root / "source.doc"
        source_path.write_bytes(b"verified source bytes")
        record = load_template()
        record["source_inputs"][0]["locator"] = "source.doc"
        record["source_inputs"][0]["integrity_status"] = "verified_bytes"
        record["source_inputs"][0]["file_sha256"] = hashlib.sha256(source_path.read_bytes()).hexdigest()
        file_ok = not verify_declared_file_hashes(record, root)
        record["source_inputs"][0]["locator"] = str(source_path.resolve())
        file_ok = file_ok and any("project-root-relative" in item for item in verify_declared_file_hashes(record, root))
        outside_path = root.parent / "outside-source.doc"
        outside_path.write_bytes(b"outside verified bytes")
        record["source_inputs"][0]["locator"] = "../outside-source.doc"
        record["source_inputs"][0]["file_sha256"] = hashlib.sha256(outside_path.read_bytes()).hexdigest()
        file_ok = file_ok and any("project-root-relative" in item for item in verify_declared_file_hashes(record, root))
        record["source_inputs"][0]["locator"] = "source.doc"
        record["source_inputs"][0]["file_sha256"] = hashlib.sha256(source_path.read_bytes()).hexdigest()
        source_path.write_bytes(b"mutated")
        file_ok = file_ok and any("file_sha256 mismatch" in item for item in verify_declared_file_hashes(record, root))
    print(f"{'PASS' if file_ok else 'FAIL'} verified source bytes are root-confined and re-hashed")
    results.append(file_ok)
    previous, current = selective_revision_pair()
    revision_errors = validate_contract(current, previous)
    revision_ok = not revision_errors
    print(f"{'PASS' if revision_ok else 'FAIL'} selective revision binds one predecessor and real field diff")
    if revision_errors:
        print("  " + "\n  ".join(revision_errors))
    results.append(revision_ok)

    same_version = copy.deepcopy(current)
    same_version["version"] = previous["version"]
    same_version["sha256"] = canonical_sha256(same_version)
    same_version_ok = any("SemVer must be greater" in item for item in validate_contract(same_version, previous))
    print(f"{'PASS' if same_version_ok else 'FAIL'} same-version revision attack fails closed")
    results.append(same_version_ok)

    unreported = copy.deepcopy(current)
    unreported["shots"][0]["lens_intent"] = "long-lens compression not declared in revision evidence"
    unreported["sha256"] = canonical_sha256(unreported)
    unreported_ok = any("changed_json_pointers does not exactly match" in item for item in validate_contract(unreported, previous))
    print(f"{'PASS' if unreported_ok else 'FAIL'} undeclared field-level change fails closed")
    results.append(unreported_ok)

    fake_predecessor = copy.deepcopy(current)
    fake_predecessor["revision_scope"]["predecessor_artifact"]["sha256"] = "9" * 64
    fake_predecessor["sha256"] = canonical_sha256(fake_predecessor)
    fake_predecessor_ok = any("does not match actual predecessor" in item for item in validate_contract(fake_predecessor, previous))
    print(f"{'PASS' if fake_predecessor_ok else 'FAIL'} forged predecessor lock fails closed")
    results.append(fake_predecessor_ok)

    fake_preserved = copy.deepcopy(current)
    fake_preserved["revision_scope"]["preserved_artifact_ids"] = ["STORYBOARD_S001"]
    fake_preserved["sha256"] = canonical_sha256(fake_preserved)
    fake_preserved_ok = any("must be disjoint" in item for item in validate_contract(fake_preserved, previous))
    print(f"{'PASS' if fake_preserved_ok else 'FAIL'} invalidated artifact cannot be falsely declared preserved")
    results.append(fake_preserved_ok)
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
