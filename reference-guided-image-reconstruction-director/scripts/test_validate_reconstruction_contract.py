#!/usr/bin/env python3
"""Behavior tests for validate_reconstruction_contract.py."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from validate_reconstruction_contract import (  # noqa: E402
    REQUIRED_REMOVAL_CLEANUP,
    validate_contract,
)


def base_intent() -> dict:
    return {"preserve_all": True, "remove": [], "explicit_exceptions": []}


def prompt_only_lifecycle_fields() -> dict:
    return {
        "execution_boundary": "manual_external_prompt_only",
        "delivery_state": "prompt_plan",
        "external_result_provenance": [],
        "platform_parameter_guidance": {
            "semantic_target": "preserve source dimensions unless the user chooses an external high-resolution setting",
            "prompt_guarantees_dimensions": False,
            "dimensions_fact_state": "unknown",
            "dimensions_evidence_type": "none",
            "actual_pixel_dimensions": None,
            "settings_evidence": "No external-platform resolution control has been established.",
        },
    }


def mark_user_imported_external_result(
    contract: dict,
    result_id: str = "external_candidate_001",
    result_kind: str = "candidate_result",
) -> dict:
    if not any(asset.get("id") == result_id for asset in contract.get("assets", [])):
        contract.setdefault("assets", []).append(
            {
                "id": result_id,
                "kind": result_kind,
                "approved": False,
                "exact_attributes": [],
            }
        )
    contract["delivery_state"] = "imported_external_candidate"
    contract["external_result_provenance"] = [
        {
            "result_id": result_id,
            "origin": "user_manual_external_generation",
            "imported_by_user": True,
            "provenance": (
                "The user manually generated this result on an external platform "
                "and imported it for read-only QA."
            ),
        }
    ]
    return contract


def valid_pixel_contract() -> dict:
    contract = {
        "version": "2.0",
        "target_id": "target",
        "assets": [
            {
                "id": "target",
                "kind": "target",
                "contamination_risk": "low",
                "exact_attributes": [],
            }
        ],
        "intent": base_intent(),
        "authority": [
            {
                "attribute": "frame.composition",
                "primary": ["target"],
                "allow": [],
                "deny": [],
                "role_state": "known",
                "evidence": "The target supplies the frame to preserve.",
            }
        ],
        "reference_permissions": [],
        "stages": [{"id": "restore", "kind": "pixel", "inputs": ["target"]}],
        "truth_sensitive": [],
        "status": "prompt_package_ready",
    }
    contract.update(prompt_only_lifecycle_fields())
    return contract


def valid_isomorphic_contract() -> dict:
    contract = {
        "version": "2.0",
        "target_id": "target",
        "assets": [
            {
                "id": "target",
                "kind": "target",
                "contamination_risk": "medium",
                "exact_attributes": [],
            },
            {"id": "surface_ref", "kind": "reference", "exact_attributes": []},
        ],
        "intent": base_intent(),
        "authority": [
            {
                "attribute": "frame.composition",
                "primary": ["target"],
                "allow": [],
                "deny": ["surface_ref"],
            },
            {
                "attribute": "appearance.material",
                "primary": ["surface_ref"],
                "allow": [],
                "deny": ["target"],
            },
        ],
        "reference_permissions": [
            {
                "asset_id": "surface_ref",
                "role_state": "known",
                "role_evidence": "The user declared this source as material evidence.",
                "allow_attributes": ["appearance.material"],
                "deny_attributes": ["protected_structure.*"],
                "allow_entities": [],
                "deny_entities": [],
            }
        ],
        "stages": [
            {"id": "isomorphic", "kind": "isomorphic", "inputs": ["target", "surface_ref"]}
        ],
        "truth_sensitive": [],
        "status": "prompt_package_ready",
    }
    contract.update(prompt_only_lifecycle_fields())
    return contract


def valid_staged_contract() -> dict:
    contract = {
        "version": "2.0",
        "target_id": "target",
        "assets": [
            {
                "id": "target",
                "kind": "target",
                "contamination_risk": "high",
                "exact_attributes": [],
            },
            {
                "id": "master",
                "kind": "structure_master",
                "approved": True,
                "exact_attributes": [],
            },
            {"id": "surface_ref", "kind": "reference", "exact_attributes": []},
            {
                "id": "brand_art",
                "kind": "exact_asset",
                "exact_attributes": ["graphics.brand_text"],
            },
        ],
        "intent": {
            "preserve_all": True,
            "remove": ["temporary_object"],
            "explicit_exceptions": [
                {
                    "entity": "temporary_object",
                    "cleanup": list(REQUIRED_REMOVAL_CLEANUP),
                }
            ],
        },
        "authority": [
            {
                "attribute": "frame.composition",
                "primary": ["master"],
                "allow": ["target"],
                "deny": ["surface_ref"],
            },
            {
                "attribute": "appearance.material",
                "primary": ["surface_ref"],
                "allow": [],
                "deny": ["target"],
            },
            {
                "attribute": "graphics.brand_text",
                "primary": ["brand_art"],
                "allow": [],
                "deny": ["surface_ref"],
            },
        ],
        "reference_permissions": [
            {
                "asset_id": "surface_ref",
                "role_state": "inferred",
                "role_evidence": "Visible surface response supports a bounded material role.",
                "allow_attributes": ["appearance.material"],
                "deny_attributes": ["protected_structure.*", "graphics.brand_text"],
                "allow_entities": [],
                "deny_entities": ["temporary_object"],
            }
        ],
        "stages": [
            {"id": "structure", "kind": "structure", "inputs": ["target"]},
            {"id": "realism", "kind": "realism", "inputs": ["master", "surface_ref"]},
            {
                "id": "exact_composite",
                "kind": "composite",
                "inputs": ["brand_art"],
                "base_stage_id": "realism",
            },
        ],
        "truth_sensitive": [
            {
                "attribute": "graphics.brand_text",
                "required_exact": True,
                "evidence_ids": ["brand_art"],
            }
        ],
        "status": "candidate_unapproved",
    }
    contract.update(prompt_only_lifecycle_fields())
    return mark_user_imported_external_result(contract)


def valid_blocked_contract() -> dict:
    contract = {
        "assets": [{"id": "target", "kind": "target"}],
        "intent": base_intent(),
        "authority": [
            {
                "attribute": "structure.hidden_geometry",
                "primary": [],
                "allow": [],
                "deny": [],
                "unresolved": True,
                "reason": "The supplied image does not reveal the hidden geometry.",
                "role_state": "unknown",
            }
        ],
        "reference_permissions": [],
        "stages": [
            {
                "id": "blocked_evidence",
                "kind": "blocked",
                "inputs": ["target"],
                "reason": "Exact hidden geometry evidence is missing.",
            }
        ],
        "truth_sensitive": [],
        "status": "blocked_missing_evidence",
    }
    contract.update(prompt_only_lifecycle_fields())
    return contract


def error_codes(result: dict) -> set[str]:
    return {entry["code"] for entry in result["errors"]}


def run_cli_raw_json(raw_json: str) -> subprocess.CompletedProcess[str]:
    script = SCRIPT_DIR / "validate_reconstruction_contract.py"
    with tempfile.TemporaryDirectory() as temp_dir:
        contract_path = Path(temp_dir) / "raw_contract.json"
        contract_path.write_text(raw_json, encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-B", str(script), str(contract_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )


def duplicate_json_fragment(raw_json: str, original: str, replacement: str) -> str:
    if raw_json.count(original) != 1:
        raise AssertionError(f"Expected exactly one raw JSON fragment: {original!r}")
    return raw_json.replace(original, replacement, 1)


class ContractBehaviorTests(unittest.TestCase):
    def assertValid(self, contract: dict) -> dict:  # noqa: N802
        result = validate_contract(contract)
        self.assertTrue(result["valid"], json.dumps(result, ensure_ascii=False, indent=2))
        return result

    def assertCode(self, contract: dict, code: str) -> dict:  # noqa: N802
        result = validate_contract(contract)
        self.assertFalse(result["valid"], result)
        self.assertIn(code, error_codes(result), result)
        return result

    def assertDuplicateJsonRejected(self, raw_json: str) -> None:  # noqa: N802
        run = run_cli_raw_json(raw_json)
        self.assertEqual(2, run.returncode, run.stderr)
        result = json.loads(run.stdout)
        self.assertFalse(result["valid"], result)
        self.assertEqual("E_DUPLICATE_JSON_KEY", result["errors"][0]["code"])

    def test_valid_target_only_zero_reference_pixel_restore(self) -> None:
        result = self.assertValid(valid_pixel_contract())
        self.assertEqual(0, result["summary"]["references"])

    def test_valid_pixel_restore_with_mask(self) -> None:
        contract = valid_pixel_contract()
        contract["assets"].append({"id": "mask", "kind": "mask"})
        contract["stages"][0]["inputs"].append("mask")
        self.assertValid(contract)

    def test_valid_single_stage_isomorphic(self) -> None:
        self.assertValid(valid_isomorphic_contract())

    def test_valid_staged_contract(self) -> None:
        result = self.assertValid(valid_staged_contract())
        self.assertEqual("temporary_object", result["normalized_exceptions"][0]["entity"])

    def test_valid_fresh_two_stage_prompt_package(self) -> None:
        contract = valid_staged_contract()
        result_id = contract["external_result_provenance"][0]["result_id"]
        contract["assets"] = [
            asset for asset in contract["assets"] if asset["id"] != result_id
        ]
        contract["delivery_state"] = "prompt_plan"
        contract["external_result_provenance"] = []
        contract["status"] = "prompt_package_ready"
        self.assertValid(contract)

    def test_valid_scoped_target_reuse(self) -> None:
        contract = valid_staged_contract()
        contract["stages"][1]["inputs"].append("target")
        contract["stages"][1]["target_reuse"] = {
            "justification": "The target is the only evidence for a visible non-structural surface mark.",
            "allowed_attributes": ["appearance.unique_surface_mark"],
            "deny_protected_structure": True,
        }
        self.assertValid(contract)

    def test_valid_blocked_plan(self) -> None:
        self.assertValid(valid_blocked_contract())

    def test_valid_bounded_proxy_status_with_blocked_plan(self) -> None:
        contract = valid_blocked_contract()
        contract["status"] = "bounded_proxy_only"
        self.assertValid(contract)

    def test_valid_structure_master_candidate_status(self) -> None:
        contract = valid_pixel_contract()
        contract["stages"][0] = {
            "id": "structure",
            "kind": "structure",
            "inputs": ["target"],
        }
        contract["status"] = "structure_master_candidate"
        mark_user_imported_external_result(
            contract,
            "external_structure_master_001",
            "structure_master",
        )
        self.assertValid(contract)

    def test_valid_qa_failed_retry_ready_status(self) -> None:
        contract = valid_pixel_contract()
        contract["status"] = "qa_failed_directional_retry_ready"
        mark_user_imported_external_result(contract, "external_failed_candidate_001")
        self.assertValid(contract)

    def test_valid_unknown_reference_when_not_uploaded(self) -> None:
        contract = valid_pixel_contract()
        contract["assets"].append({"id": "unused_ref", "kind": "reference"})
        contract["authority"][0]["deny"] = ["unused_ref"]
        contract["reference_permissions"] = [
            {
                "asset_id": "unused_ref",
                "role_state": "unknown",
                "role_evidence": "The image is readable but its intended role is not declared.",
                "allow_attributes": [],
                "deny_attributes": ["protected_structure.*"],
                "allow_entities": [],
                "deny_entities": [],
            }
        ]
        self.assertValid(contract)

    def test_valid_hierarchical_protected_deny_shorthand(self) -> None:
        contract = valid_isomorphic_contract()
        contract["reference_permissions"][0]["deny_attributes"] = ["frame.*", "structure.*"]
        self.assertValid(contract)

    def test_appearance_texture_scale_is_not_structural(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["attribute"] = "appearance.texture_scale"
        contract["reference_permissions"][0]["allow_attributes"] = ["appearance.texture_scale"]
        self.assertValid(contract)

    def test_assets_only_contract_fails(self) -> None:
        result = validate_contract({"assets": [{"id": "target", "kind": "target"}]})
        self.assertFalse(result["valid"])
        self.assertIn("E_REQUIRED_TOP_LEVEL", error_codes(result))

    def test_intent_wrong_type_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["intent"] = []
        self.assertCode(contract, "E_INTENT_TYPE")

    def test_authority_wrong_type_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["authority"] = {}
        self.assertCode(contract, "E_AUTHORITY_TYPE")

    def test_reference_permissions_wrong_type_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["reference_permissions"] = {}
        self.assertCode(contract, "E_REFERENCE_PERMISSIONS_TYPE")

    def test_stages_wrong_type_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["stages"] = {}
        self.assertCode(contract, "E_STAGES_TYPE")

    def test_truth_sensitive_wrong_type_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["truth_sensitive"] = {}
        self.assertCode(contract, "E_TRUTH_SENSITIVE_TYPE")

    def test_authority_empty_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["authority"] = []
        self.assertCode(contract, "E_AUTHORITY_EMPTY")

    def test_authority_empty_row_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["authority"] = [
            {"attribute": "appearance.material", "primary": [], "allow": [], "deny": []}
        ]
        self.assertCode(contract, "E_AUTHORITY_ROW_EMPTY")

    def test_stages_empty_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["stages"] = []
        self.assertCode(contract, "E_STAGES_EMPTY")

    def test_reference_permissions_missing_top_level_fails(self) -> None:
        contract = valid_pixel_contract()
        del contract["reference_permissions"]
        self.assertCode(contract, "E_REQUIRED_TOP_LEVEL")

    def test_truth_sensitive_missing_top_level_fails(self) -> None:
        contract = valid_pixel_contract()
        del contract["truth_sensitive"]
        self.assertCode(contract, "E_REQUIRED_TOP_LEVEL")

    def test_status_missing_fails(self) -> None:
        contract = valid_pixel_contract()
        del contract["status"]
        self.assertCode(contract, "E_STATUS")

    def test_privileged_status_locked_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["status"] = "LOCKED"
        self.assertCode(contract, "E_STATUS")

    def test_privileged_status_approved_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["status"] = "approved"
        self.assertCode(contract, "E_STATUS")

    def test_privileged_status_final_bug_free_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["status"] = "final_bug_free"
        self.assertCode(contract, "E_STATUS")

    def test_duplicate_asset_id_fails(self) -> None:
        contract = valid_isomorphic_contract()
        contract["assets"].append({"id": "surface_ref", "kind": "reference"})
        self.assertCode(contract, "E_DUPLICATE_ASSET_ID")

    def test_multiple_primary_authorities_fail(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["primary"] = ["surface_ref", "target"]
        self.assertCode(contract, "E_MULTIPLE_PRIMARY_AUTHORITIES")

    def test_authority_allow_requires_permission_allow(self) -> None:
        contract = valid_isomorphic_contract()
        contract["reference_permissions"][0]["allow_attributes"] = []
        self.assertCode(contract, "E_AUTHORITY_PERMISSION_ALLOW_MISSING")

    def test_authority_allow_conflicts_with_permission_deny(self) -> None:
        contract = valid_isomorphic_contract()
        contract["reference_permissions"][0]["deny_attributes"].append("appearance.material")
        self.assertCode(contract, "E_AUTHORITY_PERMISSION_DENY_CONFLICT")

    def test_authority_deny_conflicts_with_permission_allow(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["primary"] = []
        contract["authority"][1]["deny"] = ["surface_ref"]
        self.assertCode(contract, "E_AUTHORITY_DENY_PERMISSION_ALLOW_CONFLICT")

    def test_authority_deny_requires_permission_deny(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["primary"] = []
        contract["authority"][1]["deny"] = ["surface_ref"]
        contract["reference_permissions"][0]["allow_attributes"] = []
        self.assertCode(contract, "E_AUTHORITY_DENY_PERMISSION_MISSING")

    def test_permission_allow_requires_authority_assignment(self) -> None:
        contract = valid_isomorphic_contract()
        contract["reference_permissions"][0]["allow_attributes"].append("appearance.lighting")
        self.assertCode(contract, "E_PERMISSION_ALLOW_WITHOUT_AUTHORITY")

    def test_broad_permission_cannot_exceed_narrow_authority(self) -> None:
        contract = valid_isomorphic_contract()
        contract["reference_permissions"][0]["allow_attributes"] = ["appearance.*"]
        self.assertCode(contract, "E_PERMISSION_ALLOW_WITHOUT_AUTHORITY")

    def test_broad_authority_can_bound_matching_broad_permission(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["attribute"] = "appearance.*"
        contract["reference_permissions"][0]["allow_attributes"] = ["appearance.*"]
        self.assertValid(contract)

    def test_reference_permission_record_required(self) -> None:
        contract = valid_isomorphic_contract()
        contract["reference_permissions"] = []
        self.assertCode(contract, "E_REFERENCE_PERMISSION_MISSING")

    def test_reference_deny_scope_cannot_be_empty(self) -> None:
        contract = valid_isomorphic_contract()
        contract["reference_permissions"][0]["deny_attributes"] = []
        self.assertCode(contract, "E_REFERENCE_DENY_EMPTY")

    def test_reference_deny_must_cover_all_protected_structure(self) -> None:
        contract = valid_isomorphic_contract()
        contract["reference_permissions"][0]["deny_attributes"] = ["frame.*"]
        self.assertCode(contract, "E_REFERENCE_PROTECTED_DENY_INCOMPLETE")

    def test_reference_unlimited_authority_fails(self) -> None:
        contract = valid_isomorphic_contract()
        contract["reference_permissions"][0]["allow_attributes"] = ["*"]
        self.assertCode(contract, "E_REFERENCE_UNLIMITED_AUTHORITY")

    def test_reference_protected_hierarchy_authority_fails(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["attribute"] = "structure.object_count"
        contract["reference_permissions"][0]["allow_attributes"] = ["structure.object_count"]
        self.assertCode(contract, "E_REFERENCE_PROTECTED_STRUCTURE")

    def test_reference_frame_crop_authority_fails(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["attribute"] = "frame.crop"
        contract["reference_permissions"][0]["allow_attributes"] = ["frame.crop"]
        self.assertCode(contract, "E_REFERENCE_PROTECTED_STRUCTURE")

    def test_reference_frame_wildcard_permission_fails(self) -> None:
        contract = valid_isomorphic_contract()
        contract["reference_permissions"][0]["allow_attributes"] = ["frame.*"]
        self.assertCode(contract, "E_REFERENCE_PROTECTED_PERMISSION")

    def test_contamination_risk_wrong_type_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["assets"][0]["contamination_risk"] = ["high"]
        self.assertCode(contract, "E_CONTAMINATION_RISK")

    def test_contamination_risk_unknown_enum_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["assets"][0]["contamination_risk"] = "severe"
        self.assertCode(contract, "E_CONTAMINATION_RISK")

    def test_whitespace_high_risk_does_not_bypass_reuse_scope(self) -> None:
        contract = valid_staged_contract()
        contract["assets"][0]["contamination_risk"] = "high "
        contract["stages"][1]["inputs"].append("target")
        result = self.assertCode(contract, "E_TARGET_REUSE_SCOPE_REQUIRED")
        self.assertNotIn("E_CONTAMINATION_RISK", error_codes(result))

    def test_all_target_reuse_requires_scope_even_low_risk(self) -> None:
        contract = valid_staged_contract()
        contract["assets"][0]["contamination_risk"] = "low"
        contract["stages"][1]["inputs"].append("target")
        self.assertCode(contract, "E_TARGET_REUSE_SCOPE_REQUIRED")

    def test_target_reuse_semantically_empty_attribute_fails(self) -> None:
        contract = valid_staged_contract()
        contract["stages"][1]["inputs"].append("target")
        contract["stages"][1]["target_reuse"] = {
            "justification": "A bounded visible mark is absent from the master.",
            "allowed_attributes": ["!!!"],
            "deny_protected_structure": True,
        }
        self.assertCode(contract, "E_TARGET_REUSE_ATTRIBUTES_EMPTY")

    def test_target_reuse_structure_object_count_fails(self) -> None:
        contract = valid_staged_contract()
        contract["stages"][1]["inputs"].append("target")
        contract["stages"][1]["target_reuse"] = {
            "justification": "The target depicts a count.",
            "allowed_attributes": ["structure.object_count"],
            "deny_protected_structure": True,
        }
        self.assertCode(contract, "E_TARGET_REUSE_PROTECTED_STRUCTURE")

    def test_target_reuse_frame_wildcard_fails(self) -> None:
        contract = valid_staged_contract()
        contract["stages"][1]["inputs"].append("target")
        contract["stages"][1]["target_reuse"] = {
            "justification": "The target depicts the frame.",
            "allowed_attributes": ["frame.*"],
            "deny_protected_structure": True,
        }
        self.assertCode(contract, "E_TARGET_REUSE_PROTECTED_STRUCTURE")

    def test_remove_requires_exception_when_preserve_all_false(self) -> None:
        contract = valid_staged_contract()
        contract["intent"]["preserve_all"] = False
        contract["intent"]["explicit_exceptions"] = []
        self.assertCode(contract, "E_REMOVE_EXCEPTION_MISSING")

    def test_removal_cleanup_must_be_complete(self) -> None:
        contract = valid_staged_contract()
        contract["intent"]["explicit_exceptions"][0]["cleanup"] = ["cast_shadows"]
        self.assertCode(contract, "E_REMOVE_CLEANUP_INCOMPLETE")

    def test_reference_must_deny_every_removed_entity(self) -> None:
        contract = valid_staged_contract()
        contract["reference_permissions"][0]["deny_entities"] = []
        self.assertCode(contract, "E_REMOVED_ENTITY_NOT_DENIED")

    def test_unused_reference_must_still_deny_every_removed_entity(self) -> None:
        contract = valid_staged_contract()
        contract["stages"][1]["inputs"] = ["master"]
        contract["reference_permissions"][0]["deny_entities"] = []
        self.assertCode(contract, "E_REMOVED_ENTITY_NOT_DENIED")

    def test_removed_entity_cannot_be_reallowed(self) -> None:
        contract = valid_staged_contract()
        contract["reference_permissions"][0]["allow_entities"] = ["temporary_object"]
        self.assertCode(contract, "E_REMOVED_ENTITY_REALLOWED")

    def test_reference_allow_and_deny_entity_overlap_fails(self) -> None:
        contract = valid_staged_contract()
        contract["reference_permissions"][0]["allow_entities"] = ["temporary_object"]
        self.assertCode(contract, "E_REFERENCE_ENTITY_CONFLICT")

    def test_duplicate_stage_input_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["stages"][0]["inputs"] = ["target", "target"]
        self.assertCode(contract, "E_DUPLICATE_STAGE_INPUT")

    def test_structure_stage_requires_target(self) -> None:
        contract = valid_staged_contract()
        contract["stages"][0]["inputs"] = ["master"]
        self.assertCode(contract, "E_STRUCTURE_TARGET_REQUIRED")

    def test_structure_stage_rejects_reference(self) -> None:
        contract = valid_staged_contract()
        contract["stages"][0]["inputs"].append("surface_ref")
        self.assertCode(contract, "E_STRUCTURE_STAGE_REFERENCE")

    def test_realism_stage_requires_one_master(self) -> None:
        contract = valid_staged_contract()
        contract["stages"][1]["inputs"] = ["surface_ref"]
        self.assertCode(contract, "E_REALISM_MASTER_COUNT")

    def test_realism_stage_rejects_two_masters(self) -> None:
        contract = valid_staged_contract()
        contract["assets"].append(
            {"id": "master_two", "kind": "structure_master", "approved": True}
        )
        contract["stages"][1]["inputs"].append("master_two")
        self.assertCode(contract, "E_REALISM_MASTER_COUNT")

    def test_unapproved_master_rejected(self) -> None:
        contract = valid_staged_contract()
        contract["assets"][1]["approved"] = False
        self.assertCode(contract, "E_UNAPPROVED_MASTER_IN_REALISM")

    def test_asset_approved_wrong_type_fails(self) -> None:
        contract = valid_staged_contract()
        contract["assets"][1]["approved"] = "yes"
        self.assertCode(contract, "E_ASSET_APPROVED_TYPE")

    def test_pixel_stage_rejects_reference(self) -> None:
        contract = valid_isomorphic_contract()
        contract["stages"][0]["kind"] = "pixel"
        self.assertCode(contract, "E_PIXEL_SEMANTIC_INPUT")

    def test_pixel_stage_rejects_exact_asset(self) -> None:
        contract = valid_pixel_contract()
        contract["assets"].append({"id": "exact", "kind": "exact_asset"})
        contract["stages"][0]["inputs"].append("exact")
        self.assertCode(contract, "E_PIXEL_SEMANTIC_INPUT")

    def test_unknown_stage_input_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["stages"][0]["inputs"].append("missing")
        self.assertCode(contract, "E_UNKNOWN_STAGE_INPUT")

    def test_duplicate_stage_id_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["stages"].append({"id": "restore", "kind": "local", "inputs": ["target"]})
        self.assertCode(contract, "E_DUPLICATE_STAGE_ID")

    def test_exact_evidence_declared_but_unused_fails(self) -> None:
        contract = valid_staged_contract()
        contract["stages"] = contract["stages"][:2]
        self.assertCode(contract, "E_EXACT_EVIDENCE_UNUSED")

    def test_exact_evidence_in_blocked_stage_does_not_count_as_execution(self) -> None:
        contract = valid_staged_contract()
        contract["stages"] = [
            {
                "id": "blocked",
                "kind": "blocked",
                "inputs": ["target", "brand_art"],
                "reason": "A different exact source is missing.",
            }
        ]
        contract["status"] = "blocked_missing_evidence"
        contract["delivery_state"] = "prompt_plan"
        contract["external_result_provenance"] = []
        self.assertCode(contract, "E_EXACT_EVIDENCE_UNUSED")

    def test_truth_sensitive_missing_exact_evidence_fails(self) -> None:
        contract = valid_staged_contract()
        contract["assets"][3]["exact_attributes"] = []
        self.assertCode(contract, "E_EXACT_EVIDENCE_REQUIRED")

    def test_reference_invalid_role_state_fails(self) -> None:
        contract = valid_isomorphic_contract()
        contract["reference_permissions"][0]["role_state"] = "trusted"
        self.assertCode(contract, "E_REFERENCE_ROLE_STATE")

    def test_reference_role_requires_evidence(self) -> None:
        contract = valid_isomorphic_contract()
        contract["reference_permissions"][0]["role_evidence"] = " "
        self.assertCode(contract, "E_REFERENCE_ROLE_EVIDENCE")

    def test_unknown_reference_cannot_be_uploaded(self) -> None:
        contract = valid_isomorphic_contract()
        contract["reference_permissions"][0]["role_state"] = "unknown"
        self.assertCode(contract, "E_UNKNOWN_REFERENCE_UPLOADED")

    def test_authority_invalid_role_state_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["authority"][0]["role_state"] = "certain"
        self.assertCode(contract, "E_AUTHORITY_ROLE_STATE")

    def test_blocked_status_requires_blocked_stage(self) -> None:
        contract = valid_pixel_contract()
        contract["status"] = "blocked_missing_evidence"
        self.assertCode(contract, "E_BLOCKED_STATUS_PLAN")

    def test_blocked_stage_requires_blocked_status(self) -> None:
        contract = valid_blocked_contract()
        contract["status"] = "prompt_package_ready"
        self.assertCode(contract, "E_BLOCKED_STAGE_STATUS")

    def test_blocked_stage_requires_reason(self) -> None:
        contract = valid_blocked_contract()
        contract["stages"][0]["reason"] = ""
        self.assertCode(contract, "E_BLOCKED_REASON")

    def test_structure_candidate_status_requires_structure_stage(self) -> None:
        contract = valid_pixel_contract()
        contract["status"] = "structure_master_candidate"
        mark_user_imported_external_result(
            contract,
            "external_structure_master_invalid",
            "structure_master",
        )
        self.assertCode(contract, "E_STRUCTURE_STATUS_STAGE")

    def test_invalid_stage_kind_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["stages"][0]["kind"] = "magic"
        self.assertCode(contract, "E_STAGE_KIND")

    def test_r1_overlapping_hierarchical_authority_with_different_sources_fails(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["attribute"] = "appearance.*"
        contract["reference_permissions"][0]["allow_attributes"] = ["appearance.*"]
        contract["assets"].append(
            {"id": "material_ref", "kind": "reference", "exact_attributes": []}
        )
        contract["authority"].append(
            {
                "attribute": "appearance.material",
                "primary": ["material_ref"],
                "allow": [],
                "deny": ["target"],
            }
        )
        contract["reference_permissions"].append(
            {
                "asset_id": "material_ref",
                "role_state": "known",
                "role_evidence": "The user assigned the narrow material role.",
                "allow_attributes": ["appearance.material"],
                "deny_attributes": ["protected_structure.*"],
                "allow_entities": [],
                "deny_entities": [],
            }
        )
        contract["stages"][0]["inputs"].append("material_ref")
        self.assertCode(contract, "E_OVERLAPPING_AUTHORITY_SCOPES")

    def test_r1_overlapping_hierarchical_authority_same_sources_is_valid(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["attribute"] = "appearance.*"
        contract["reference_permissions"][0]["allow_attributes"] = ["appearance.*"]
        contract["authority"].append(
            {
                "attribute": "appearance.material",
                "primary": ["surface_ref"],
                "allow": [],
                "deny": ["target"],
            }
        )
        self.assertValid(contract)

    def test_r2_realism_master_must_be_first(self) -> None:
        contract = valid_staged_contract()
        contract["stages"][1]["inputs"] = ["surface_ref", "master"]
        self.assertCode(contract, "E_REALISM_MASTER_FIRST")

    def test_r2_realism_master_first_control_is_valid(self) -> None:
        contract = valid_staged_contract()
        self.assertEqual("master", contract["stages"][1]["inputs"][0])
        self.assertValid(contract)

    def test_r3_local_stage_without_target_fails(self) -> None:
        contract = valid_isomorphic_contract()
        contract["stages"][0] = {
            "id": "local",
            "kind": "local",
            "inputs": ["surface_ref"],
        }
        self.assertCode(contract, "E_LOCAL_TARGET_REQUIRED")

    def test_r3_local_stage_with_target_and_reference_is_valid(self) -> None:
        contract = valid_isomorphic_contract()
        contract["stages"][0]["kind"] = "local"
        self.assertValid(contract)

    def test_r4_unresolved_composition_cannot_enter_executable_stage(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][0] = {
            "attribute": "frame.composition",
            "primary": [],
            "allow": [],
            "deny": ["surface_ref"],
            "unresolved": True,
            "reason": "Composition ownership has not been adjudicated.",
        }
        result = self.assertCode(contract, "E_UNRESOLVED_AUTHORITY_EXECUTABLE")
        self.assertIn("E_STAGE_REQUIRED_AUTHORITY_UNRESOLVED", error_codes(result))

    def test_r4_unresolved_authority_in_blocked_only_plan_is_valid(self) -> None:
        self.assertValid(valid_blocked_contract())

    def test_r5_exact_asset_used_only_in_structure_does_not_count(self) -> None:
        contract = valid_staged_contract()
        contract["stages"] = [
            {
                "id": "structure",
                "kind": "structure",
                "inputs": ["target", "brand_art"],
            }
        ]
        result = self.assertCode(contract, "E_EXACT_EVIDENCE_UNUSED")
        self.assertIn("E_STAGE_ASSET_ROLE_INCOMPATIBLE", error_codes(result))

    def test_r5_exact_asset_used_in_composite_is_valid(self) -> None:
        contract = valid_staged_contract()
        self.assertIn("brand_art", contract["stages"][2]["inputs"])
        self.assertValid(contract)

    def test_r6_everything_wildcard_reference_authority_fails(self) -> None:
        contract = valid_isomorphic_contract()
        contract["reference_permissions"][0]["allow_attributes"] = ["everything.*"]
        self.assertCode(contract, "E_REFERENCE_UNLIMITED_AUTHORITY")

    def test_r6_bounded_appearance_wildcard_reference_authority_is_valid(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["attribute"] = "appearance.*"
        contract["reference_permissions"][0]["allow_attributes"] = ["appearance.*"]
        self.assertValid(contract)

    def test_r7_blocked_plan_cannot_mix_with_realism(self) -> None:
        contract = valid_blocked_contract()
        contract["assets"].append(
            {"id": "master", "kind": "structure_master", "approved": True}
        )
        contract["stages"].append(
            {"id": "realism", "kind": "realism", "inputs": ["master"]}
        )
        result = self.assertCode(contract, "E_BLOCKED_STAGE_EXCLUSIVE")
        self.assertIn("E_BLOCKED_STATUS_EXECUTION", error_codes(result))

    def test_r7_blocked_only_stage_set_is_valid(self) -> None:
        contract = valid_blocked_contract()
        self.assertEqual({"blocked"}, {stage["kind"] for stage in contract["stages"]})
        self.assertValid(contract)

    def test_r8_structure_candidate_cannot_include_realism(self) -> None:
        contract = valid_staged_contract()
        contract["stages"] = contract["stages"][:2]
        contract["truth_sensitive"] = []
        contract["status"] = "structure_master_candidate"
        self.assertCode(contract, "E_STRUCTURE_CANDIDATE_STAGE_SET")

    def test_r8_structure_candidate_structure_only_control_is_valid(self) -> None:
        contract = valid_pixel_contract()
        contract["stages"] = [
            {"id": "structure", "kind": "structure", "inputs": ["target"]}
        ]
        contract["status"] = "structure_master_candidate"
        mark_user_imported_external_result(
            contract,
            "external_structure_master_002",
            "structure_master",
        )
        self.assertValid(contract)

    def test_r9_target_reuse_style_wildcard_is_not_scoped(self) -> None:
        contract = valid_staged_contract()
        contract["stages"][1]["inputs"].append("target")
        contract["stages"][1]["target_reuse"] = {
            "justification": "Only a narrow visible appearance cue is needed.",
            "allowed_attributes": ["style.*"],
            "deny_protected_structure": True,
        }
        self.assertCode(contract, "E_TARGET_REUSE_ATTRIBUTE_NOT_SCOPED")

    def test_r9_target_reuse_concrete_attribute_control_is_valid(self) -> None:
        contract = valid_staged_contract()
        contract["stages"][1]["inputs"].append("target")
        contract["stages"][1]["target_reuse"] = {
            "justification": "A visible serial scratch is absent from the master.",
            "allowed_attributes": ["appearance.unique_surface_mark"],
            "deny_protected_structure": True,
        }
        self.assertValid(contract)

    def test_r10_unknown_reference_cannot_hold_authority_when_not_uploaded(self) -> None:
        contract = valid_isomorphic_contract()
        contract["reference_permissions"][0]["role_state"] = "unknown"
        contract["reference_permissions"][0]["role_evidence"] = (
            "The intended semantic role has not been established."
        )
        contract["stages"][0]["inputs"] = ["target"]
        self.assertCode(contract, "E_UNKNOWN_REFERENCE_AUTHORITY")

    def test_r10_unknown_reference_denied_and_not_uploaded_is_valid(self) -> None:
        contract = valid_pixel_contract()
        contract["assets"].append({"id": "unknown_ref", "kind": "reference"})
        contract["authority"][0]["deny"] = ["unknown_ref"]
        contract["reference_permissions"] = [
            {
                "asset_id": "unknown_ref",
                "role_state": "unknown",
                "role_evidence": "No role has been established.",
                "allow_attributes": [],
                "deny_attributes": ["protected_structure.*"],
                "allow_entities": [],
                "deny_entities": [],
            }
        ]
        self.assertValid(contract)

    def test_a_root_and_leaf_authority_with_different_sources_conflict(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["attribute"] = "appearance"
        contract["reference_permissions"][0]["allow_attributes"] = ["appearance"]
        contract["assets"].append({"id": "leaf_ref", "kind": "reference"})
        contract["authority"].append(
            {
                "attribute": "appearance.material",
                "primary": ["leaf_ref"],
                "allow": [],
                "deny": ["target"],
            }
        )
        contract["reference_permissions"].append(
            {
                "asset_id": "leaf_ref",
                "role_state": "known",
                "role_evidence": "The source is assigned only to the material leaf.",
                "allow_attributes": ["appearance.material"],
                "deny_attributes": ["protected_structure.*"],
                "allow_entities": [],
                "deny_entities": [],
            }
        )
        contract["stages"][0]["inputs"].append("leaf_ref")
        self.assertCode(contract, "E_OVERLAPPING_AUTHORITY_SCOPES")

    def test_a_root_and_leaf_authority_same_sources_is_valid(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["attribute"] = "appearance"
        contract["reference_permissions"][0]["allow_attributes"] = ["appearance"]
        contract["authority"].append(
            {
                "attribute": "appearance.material",
                "primary": ["surface_ref"],
                "allow": [],
                "deny": ["target"],
            }
        )
        self.assertValid(contract)

    def test_b_resolved_deny_only_authority_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["authority"][0]["primary"] = []
        contract["authority"][0]["deny"] = ["target"]
        self.assertCode(contract, "E_RESOLVED_AUTHORITY_PRIMARY_COUNT")

    def test_b_resolved_allow_only_authority_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["authority"][0]["primary"] = []
        contract["authority"][0]["allow"] = ["target"]
        self.assertCode(contract, "E_RESOLVED_AUTHORITY_PRIMARY_COUNT")

    def test_b_unresolved_deny_only_blocked_authority_is_valid(self) -> None:
        contract = valid_blocked_contract()
        contract["authority"][0]["deny"] = ["target"]
        self.assertValid(contract)

    def test_b_resolved_single_primary_control_is_valid(self) -> None:
        self.assertValid(valid_pixel_contract())

    def test_c_stage_required_authority_source_must_be_an_input(self) -> None:
        contract = valid_pixel_contract()
        contract["assets"].append({"id": "master", "kind": "structure_master"})
        contract["authority"][0]["primary"] = ["master"]
        self.assertCode(contract, "E_STAGE_REQUIRED_AUTHORITY_INPUT")

    def test_c_stage_required_authority_allow_source_input_is_valid(self) -> None:
        contract = valid_pixel_contract()
        contract["assets"].append({"id": "master", "kind": "structure_master"})
        contract["authority"][0]["primary"] = ["master"]
        contract["authority"][0]["allow"] = ["target"]
        contract["stages"][0] = {
            "id": "structure",
            "kind": "structure",
            "inputs": ["target"],
        }
        self.assertValid(contract)

    def test_d_required_exact_needs_covering_resolved_authority(self) -> None:
        contract = valid_staged_contract()
        contract["authority"] = contract["authority"][:2]
        self.assertCode(contract, "E_EXACT_AUTHORITY_MISSING")

    def test_d_required_exact_primary_must_be_exact_evidence(self) -> None:
        contract = valid_staged_contract()
        contract["authority"][2]["primary"] = ["target"]
        self.assertCode(contract, "E_EXACT_AUTHORITY_PRIMARY_EVIDENCE")

    def test_d_required_exact_root_authority_and_broad_evidence_are_valid(self) -> None:
        contract = valid_staged_contract()
        contract["authority"][2]["attribute"] = "graphics"
        contract["assets"][3]["exact_attributes"] = ["graphics.*"]
        contract["reference_permissions"][0]["deny_attributes"][1] = "graphics"
        self.assertValid(contract)

    def test_e_pixel_target_must_be_first(self) -> None:
        contract = valid_pixel_contract()
        contract["assets"].append({"id": "mask", "kind": "mask"})
        contract["stages"][0]["inputs"] = ["mask", "target"]
        self.assertCode(contract, "E_TARGET_MUST_BE_FIRST")

    def test_e_local_target_must_be_first(self) -> None:
        contract = valid_isomorphic_contract()
        contract["stages"][0]["kind"] = "local"
        contract["stages"][0]["inputs"] = ["surface_ref", "target"]
        self.assertCode(contract, "E_TARGET_MUST_BE_FIRST")

    def test_e_isomorphic_target_must_be_first(self) -> None:
        contract = valid_isomorphic_contract()
        contract["stages"][0]["inputs"] = ["surface_ref", "target"]
        self.assertCode(contract, "E_TARGET_MUST_BE_FIRST")

    def test_e_structure_target_must_be_first(self) -> None:
        contract = valid_pixel_contract()
        contract["assets"].append({"id": "mask", "kind": "mask"})
        contract["stages"][0] = {
            "id": "structure",
            "kind": "structure",
            "inputs": ["mask", "target"],
        }
        self.assertCode(contract, "E_TARGET_MUST_BE_FIRST")

    def test_e_target_first_controls_are_valid(self) -> None:
        pixel = valid_pixel_contract()
        pixel["assets"].append({"id": "mask", "kind": "mask"})
        pixel["stages"][0]["inputs"] = ["target", "mask"]
        local = valid_isomorphic_contract()
        local["stages"][0]["kind"] = "local"
        isomorphic = valid_isomorphic_contract()
        structure = valid_pixel_contract()
        structure["stages"][0]["kind"] = "structure"
        for contract in (pixel, local, isomorphic, structure):
            self.assertValid(contract)

    def test_f_rejects_multiple_trailing_wildcards(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["attribute"] = "appearance.*.*"
        contract["reference_permissions"][0]["allow_attributes"] = [
            "appearance.*.*"
        ]
        self.assertCode(contract, "E_ATTRIBUTE_SCOPE_GRAMMAR")

    def test_f_rejects_embedded_wildcard(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["attribute"] = "appearance.*.material"
        contract["reference_permissions"][0]["allow_attributes"] = [
            "appearance.*.material"
        ]
        self.assertCode(contract, "E_ATTRIBUTE_SCOPE_GRAMMAR")

    def test_f_qualified_path_and_one_trailing_wildcard_are_valid(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["attribute"] = "appearance.material.*"
        contract["reference_permissions"][0]["allow_attributes"] = [
            "appearance.material.*"
        ]
        self.assertValid(contract)

    def test_f_global_wildcard_is_valid_only_as_deny_umbrella(self) -> None:
        contract = valid_pixel_contract()
        contract["assets"].append({"id": "unknown_ref", "kind": "reference"})
        contract["authority"][0]["deny"] = ["unknown_ref"]
        contract["reference_permissions"] = [
            {
                "asset_id": "unknown_ref",
                "role_state": "unknown",
                "role_evidence": "No safe inheritance role is established.",
                "allow_attributes": [],
                "deny_attributes": ["*"],
                "allow_entities": [],
                "deny_entities": [],
            }
        ]
        self.assertValid(contract)

    def test_n14_composite_requires_exact_asset(self) -> None:
        contract = valid_staged_contract()
        contract["truth_sensitive"] = []
        contract["stages"][2]["inputs"] = ["master"]
        self.assertCode(contract, "E_COMPOSITE_EXACT_ASSET_REQUIRED")

    def test_n14_composite_with_exact_and_prior_base_stage_is_valid(self) -> None:
        self.assertValid(valid_staged_contract())

    def test_n15_composite_requires_base(self) -> None:
        contract = valid_staged_contract()
        del contract["stages"][2]["base_stage_id"]
        self.assertCode(contract, "E_COMPOSITE_BASE_REQUIRED")

    def test_n15_composite_with_asset_base_is_valid(self) -> None:
        contract = valid_staged_contract()
        contract["stages"][2]["inputs"] = ["target", "brand_art"]
        del contract["stages"][2]["base_stage_id"]
        self.assertValid(contract)

    def test_n15_composite_base_stage_must_be_prior(self) -> None:
        contract = valid_staged_contract()
        contract["stages"] = [
            contract["stages"][0],
            contract["stages"][2],
            contract["stages"][1],
        ]
        self.assertCode(contract, "E_COMPOSITE_BASE_STAGE_INVALID")

    def test_n16_candidate_unapproved_cannot_be_structure_only(self) -> None:
        contract = valid_pixel_contract()
        contract["stages"][0]["kind"] = "structure"
        contract["status"] = "candidate_unapproved"
        mark_user_imported_external_result(contract, "external_candidate_002")
        self.assertCode(contract, "E_CANDIDATE_UNAPPROVED_STRUCTURE_ONLY")

    def test_n16_prompt_package_ready_structure_only_is_valid(self) -> None:
        contract = valid_pixel_contract()
        contract["stages"][0]["kind"] = "structure"
        self.assertValid(contract)

    def test_n16_qa_retry_structure_only_is_valid(self) -> None:
        contract = valid_pixel_contract()
        contract["stages"][0]["kind"] = "structure"
        contract["status"] = "qa_failed_directional_retry_ready"
        mark_user_imported_external_result(contract, "external_failed_structure_001")
        self.assertValid(contract)

    def test_q9_non_primary_exact_evidence_use_does_not_satisfy_primary(self) -> None:
        contract = valid_staged_contract()
        contract["assets"].append(
            {
                "id": "brand_alt",
                "kind": "exact_asset",
                "exact_attributes": ["graphics.brand_text"],
            }
        )
        contract["truth_sensitive"][0]["evidence_ids"] = ["brand_art", "brand_alt"]
        contract["stages"][2]["inputs"] = ["brand_alt"]
        self.assertCode(contract, "E_EXACT_AUTHORITY_PRIMARY_UNUSED")

    def test_q9_primary_exact_evidence_used_with_unused_alternative_is_valid(self) -> None:
        contract = valid_staged_contract()
        contract["assets"].append(
            {
                "id": "brand_alt",
                "kind": "exact_asset",
                "exact_attributes": ["graphics.brand_text"],
            }
        )
        contract["truth_sensitive"][0]["evidence_ids"] = ["brand_art", "brand_alt"]
        self.assertValid(contract)

    def test_raw_scope_question_suffix_is_rejected(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["attribute"] = "appearance.*?"
        self.assertCode(contract, "E_ATTRIBUTE_SCOPE_GRAMMAR")

    def test_raw_scope_empty_segment_is_rejected(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["attribute"] = "appearance..material"
        self.assertCode(contract, "E_ATTRIBUTE_SCOPE_GRAMMAR")

    def test_raw_scope_punctuation_segment_is_rejected(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["attribute"] = "appearance.?.material"
        self.assertCode(contract, "E_ATTRIBUTE_SCOPE_GRAMMAR")

    def test_raw_scope_uppercase_is_explicitly_rejected(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["attribute"] = "Appearance.Material"
        self.assertCode(contract, "E_ATTRIBUTE_SCOPE_GRAMMAR")

    def test_raw_scope_leading_or_trailing_whitespace_is_rejected(self) -> None:
        contract = valid_isomorphic_contract()
        contract["authority"][1]["attribute"] = " appearance.material "
        self.assertCode(contract, "E_ATTRIBUTE_SCOPE_GRAMMAR")

    def test_lowercase_legacy_alias_is_valid_and_deterministic(self) -> None:
        contract = valid_pixel_contract()
        contract["authority"][0]["attribute"] = "composition"
        self.assertValid(contract)

    def test_raw_scope_grammar_applies_to_every_scope_entry(self) -> None:
        invalid_scope = "appearance.*?"

        authority = valid_pixel_contract()
        authority["authority"][0]["attribute"] = invalid_scope

        protected = valid_pixel_contract()
        protected["protected_structure"] = [invalid_scope]

        exact = valid_pixel_contract()
        exact["assets"][0]["exact_attributes"] = [invalid_scope]

        truth = valid_pixel_contract()
        truth["truth_sensitive"] = [
            {
                "attribute": invalid_scope,
                "required_exact": False,
                "evidence_ids": [],
            }
        ]

        reference_allow = valid_isomorphic_contract()
        reference_allow["reference_permissions"][0]["allow_attributes"] = [
            invalid_scope
        ]

        reference_deny = valid_isomorphic_contract()
        reference_deny["reference_permissions"][0]["deny_attributes"] = [
            invalid_scope
        ]

        target_reuse = valid_staged_contract()
        target_reuse["stages"][1]["inputs"].append("target")
        target_reuse["stages"][1]["target_reuse"] = {
            "justification": "Exercise the common scope parser.",
            "allowed_attributes": [invalid_scope],
            "deny_protected_structure": True,
        }

        cases = {
            "authority": authority,
            "protected_structure": protected,
            "exact_attributes": exact,
            "truth_sensitive": truth,
            "reference_allow": reference_allow,
            "reference_deny": reference_deny,
            "target_reuse": target_reuse,
        }
        for name, contract in cases.items():
            with self.subTest(scope_entry=name):
                self.assertCode(contract, "E_ATTRIBUTE_SCOPE_GRAMMAR")

    def test_prompt_only_execution_boundary_is_required(self) -> None:
        contract = valid_pixel_contract()
        del contract["execution_boundary"]
        result = self.assertCode(contract, "E_EXECUTION_BOUNDARY")
        self.assertIn("E_REQUIRED_TOP_LEVEL", error_codes(result))

    def test_direct_generation_boundary_fixture_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["execution_boundary"] = "codex_direct_image_generation"
        contract["user_request"] = (
            "Generate and edit the image directly inside Codex right now."
        )
        self.assertCode(contract, "E_EXECUTION_BOUNDARY")

    def test_execution_boundary_wrong_type_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["execution_boundary"] = ["manual_external_prompt_only"]
        self.assertCode(contract, "E_EXECUTION_BOUNDARY")

    def test_delivery_state_invalid_enum_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["delivery_state"] = "codex_generated"
        self.assertCode(contract, "E_DELIVERY_STATE")

    def test_external_result_provenance_wrong_type_fails(self) -> None:
        contract = valid_pixel_contract()
        contract["external_result_provenance"] = {}
        self.assertCode(contract, "E_EXTERNAL_RESULT_PROVENANCE_TYPE")

    def test_fresh_prompt_package_cannot_mint_candidate_status(self) -> None:
        contract = valid_pixel_contract()
        contract["status"] = "candidate_unapproved"
        self.assertCode(contract, "E_CANDIDATE_REQUIRES_IMPORTED_RESULT")

    def test_imported_candidate_requires_provenance_records(self) -> None:
        contract = valid_pixel_contract()
        contract["status"] = "candidate_unapproved"
        contract["delivery_state"] = "imported_external_candidate"
        self.assertCode(contract, "E_IMPORTED_RESULT_PROVENANCE_REQUIRED")

    def test_imported_candidate_origin_cannot_be_the_skill(self) -> None:
        contract = valid_staged_contract()
        contract["external_result_provenance"][0]["origin"] = "skill_generation"
        self.assertCode(contract, "E_EXTERNAL_RESULT_ORIGIN")

    def test_imported_candidate_origin_wrong_type_fails_without_crashing(self) -> None:
        contract = valid_staged_contract()
        contract["external_result_provenance"][0]["origin"] = [
            "user_manual_external_generation"
        ]
        self.assertCode(contract, "E_EXTERNAL_RESULT_ORIGIN")

    def test_imported_candidate_requires_true_user_import_flag(self) -> None:
        contract = valid_staged_contract()
        contract["external_result_provenance"][0]["imported_by_user"] = False
        self.assertCode(contract, "E_EXTERNAL_RESULT_IMPORT")

    def test_imported_candidate_requires_nonempty_provenance(self) -> None:
        contract = valid_staged_contract()
        contract["external_result_provenance"][0]["provenance"] = " "
        self.assertCode(contract, "E_EXTERNAL_RESULT_PROVENANCE_REQUIRED")

    def test_imported_candidate_provenance_must_bind_declared_asset(self) -> None:
        contract = valid_staged_contract()
        contract["external_result_provenance"][0]["result_id"] = "undeclared_result"
        self.assertCode(contract, "E_EXTERNAL_RESULT_ASSET_MISSING")

    def test_imported_candidate_result_ids_must_be_unique(self) -> None:
        contract = valid_staged_contract()
        contract["external_result_provenance"].append(
            copy.deepcopy(contract["external_result_provenance"][0])
        )
        self.assertCode(contract, "E_DUPLICATE_EXTERNAL_RESULT_ID")

    def test_structure_candidate_provenance_requires_structure_master_asset(self) -> None:
        contract = valid_pixel_contract()
        contract["stages"][0]["kind"] = "structure"
        contract["status"] = "structure_master_candidate"
        mark_user_imported_external_result(contract, "wrong_kind_result")
        self.assertCode(contract, "E_EXTERNAL_RESULT_KIND")

    def test_downstream_candidate_provenance_requires_candidate_result_asset(self) -> None:
        contract = valid_staged_contract()
        result_id = contract["external_result_provenance"][0]["result_id"]
        for asset in contract["assets"]:
            if asset["id"] == result_id:
                asset["kind"] = "structure_master"
        self.assertCode(contract, "E_EXTERNAL_RESULT_KIND")

    def test_imported_candidate_result_cannot_claim_approval(self) -> None:
        contract = valid_staged_contract()
        result_id = contract["external_result_provenance"][0]["result_id"]
        for asset in contract["assets"]:
            if asset["id"] == result_id:
                asset["approved"] = True
        self.assertCode(contract, "E_CANDIDATE_RESULT_ALREADY_APPROVED")

    def test_imported_candidate_result_is_not_a_stage_input(self) -> None:
        contract = valid_staged_contract()
        result_id = contract["external_result_provenance"][0]["result_id"]
        contract["stages"][1]["inputs"].append(result_id)
        self.assertCode(contract, "E_STAGE_ASSET_ROLE_INCOMPATIBLE")

    def test_prompt_plan_cannot_claim_external_result_provenance(self) -> None:
        contract = valid_pixel_contract()
        contract["external_result_provenance"] = copy.deepcopy(
            valid_staged_contract()["external_result_provenance"]
        )
        self.assertCode(contract, "E_PROMPT_PLAN_HAS_EXTERNAL_RESULT")

    def test_prompt_package_status_rejects_imported_candidate_delivery(self) -> None:
        contract = valid_pixel_contract()
        mark_user_imported_external_result(contract, "external_unrelated_001")
        self.assertCode(contract, "E_PROMPT_STATUS_DELIVERY_STATE")

    def test_laundry_direct_generation_wording_stays_prompt_only(self) -> None:
        contract = valid_pixel_contract()
        contract["user_request"] = (
            "Generate a high-resolution laundry room appliance reconstruction now."
        )
        result = self.assertValid(contract)
        self.assertEqual(
            "manual_external_prompt_only",
            result["summary"]["execution_boundary"],
        )
        self.assertEqual("prompt_plan", result["summary"]["delivery_state"])
        self.assertEqual(0, result["summary"]["imported_results"])

    def test_cli_duplicate_execution_boundary_key_is_rejected(self) -> None:
        raw = json.dumps(valid_pixel_contract())
        raw = duplicate_json_fragment(
            raw,
            '"execution_boundary": "manual_external_prompt_only"',
            (
                '"execution_boundary": "manual_external_prompt_only", '
                '"execution_boundary": "codex_direct_image_generation"'
            ),
        )
        self.assertDuplicateJsonRejected(raw)

    def test_cli_duplicate_status_key_is_rejected(self) -> None:
        raw = json.dumps(valid_pixel_contract())
        raw = duplicate_json_fragment(
            raw,
            '"status": "prompt_package_ready"',
            '"status": "prompt_package_ready", "status": "final"',
        )
        self.assertDuplicateJsonRejected(raw)

    def test_cli_duplicate_delivery_state_key_is_rejected(self) -> None:
        raw = json.dumps(valid_pixel_contract())
        raw = duplicate_json_fragment(
            raw,
            '"delivery_state": "prompt_plan"',
            (
                '"delivery_state": "prompt_plan", '
                '"delivery_state": "imported_external_candidate"'
            ),
        )
        self.assertDuplicateJsonRejected(raw)

    def test_cli_duplicate_nested_stage_key_is_rejected(self) -> None:
        raw = json.dumps(valid_pixel_contract())
        raw = duplicate_json_fragment(
            raw,
            '"id": "restore", "kind": "pixel"',
            '"id": "restore", "id": "hidden_override", "kind": "pixel"',
        )
        self.assertDuplicateJsonRejected(raw)

    def test_cli_duplicate_nested_asset_key_is_rejected(self) -> None:
        raw = json.dumps(valid_pixel_contract())
        raw = duplicate_json_fragment(
            raw,
            '"id": "target", "kind": "target"',
            '"id": "target", "kind": "target", "kind": "candidate_result"',
        )
        self.assertDuplicateJsonRejected(raw)

    def test_cli_duplicate_nested_provenance_key_is_rejected(self) -> None:
        raw = json.dumps(valid_staged_contract())
        raw = duplicate_json_fragment(
            raw,
            (
                '"origin": "user_manual_external_generation", '
                '"imported_by_user": true'
            ),
            (
                '"origin": "user_manual_external_generation", '
                '"origin": "skill_generation", "imported_by_user": true'
            ),
        )
        self.assertDuplicateJsonRejected(raw)

    def test_structured_objects_reject_callable_or_unknown_fields(self) -> None:
        top_level = valid_pixel_contract()
        top_level["tool_calls"] = []

        asset = valid_pixel_contract()
        asset["assets"][0]["generated_by"] = "imagegen"

        provenance = valid_staged_contract()
        provenance["external_result_provenance"][0]["tool"] = "imagegen"

        intent = valid_pixel_contract()
        intent["intent"]["automation"] = True

        exception = valid_staged_contract()
        exception["intent"]["explicit_exceptions"][0]["submit"] = True

        authority = valid_pixel_contract()
        authority["authority"][0]["api"] = "image"

        permission = valid_isomorphic_contract()
        permission["reference_permissions"][0]["login"] = True

        stage = valid_pixel_contract()
        stage["stages"][0]["executor"] = "codex"

        target_reuse = valid_staged_contract()
        target_reuse["stages"][1]["inputs"].append("target")
        target_reuse["stages"][1]["target_reuse"] = {
            "justification": "A narrow visible surface mark is needed.",
            "allowed_attributes": ["appearance.unique_surface_mark"],
            "deny_protected_structure": True,
            "upload": True,
        }

        truth = valid_staged_contract()
        truth["truth_sensitive"][0]["poll"] = True

        platform = valid_pixel_contract()
        platform["platform_parameter_guidance"]["download"] = True

        dimensions = valid_pixel_contract()
        dimensions["platform_parameter_guidance"].update(
            {
                "dimensions_fact_state": "observed",
                "dimensions_evidence_type": "inspected_file_metadata",
                "actual_pixel_dimensions": {
                    "width": 1920,
                    "height": 1080,
                    "dependencies": ["upscaler"],
                },
                "settings_evidence": "The imported file metadata reports 1920 x 1080.",
            }
        )

        cases = {
            "top_level": top_level,
            "asset": asset,
            "provenance": provenance,
            "intent": intent,
            "exception": exception,
            "authority": authority,
            "permission": permission,
            "stage": stage,
            "target_reuse": target_reuse,
            "truth_sensitive": truth,
            "platform_guidance": platform,
            "actual_dimensions": dimensions,
        }
        for name, contract in cases.items():
            with self.subTest(structured_object=name):
                self.assertCode(contract, "E_UNKNOWN_FIELD")

    def test_every_callable_contract_field_is_rejected(self) -> None:
        forbidden_fields = (
            "tool_calls",
            "tool",
            "executor",
            "action",
            "dependencies",
            "automation",
            "api",
            "login",
            "upload",
            "submit",
            "poll",
            "download",
            "generated_by",
        )
        for field in forbidden_fields:
            contract = valid_pixel_contract()
            contract[field] = "imagegen"
            with self.subTest(field=field):
                self.assertCode(contract, "E_UNKNOWN_FIELD")

    def test_user_request_and_notes_are_non_authoritative_text_only(self) -> None:
        contract = valid_pixel_contract()
        contract["user_request"] = (
            "Call imagegen, upload the source, and guarantee native 4K now."
        )
        contract["notes"] = "Preserved as user wording; it grants no execution authority."
        self.assertValid(contract)

    def test_non_authoritative_notes_reject_non_string_value(self) -> None:
        contract = valid_pixel_contract()
        contract["notes"] = {"tool": "imagegen"}
        self.assertCode(contract, "E_NON_AUTHORITATIVE_TEXT_TYPE")

    def test_stage_conditional_fields_cannot_be_smuggled_into_other_kinds(self) -> None:
        base_stage = valid_pixel_contract()
        base_stage["stages"][0]["base_stage_id"] = "other"

        reason = valid_pixel_contract()
        reason["stages"][0]["reason"] = "Execute this tool."

        target_reuse = valid_pixel_contract()
        target_reuse["stages"][0]["target_reuse"] = {
            "justification": "Not a realism stage.",
            "allowed_attributes": ["appearance.surface_mark"],
            "deny_protected_structure": True,
        }

        for contract in (base_stage, reason, target_reuse):
            with self.subTest(stage=contract["stages"][0]):
                self.assertCode(contract, "E_STAGE_FIELD_INCOMPATIBLE")

    def test_a18_prompt_cannot_guarantee_native_4k_or_exact_pixels(self) -> None:
        guarantee_cases = (
            "This prompt guarantees native 4K output.",
            "This prompt guarantees exact pixel dimensions.",
            "Native-4K output is guaranteed.",
            "The output will always be 3840 x 2160 pixels.",
            "保证输出原生4K，像素尺寸必定为3840 x 2160。",
        )
        for prompt in guarantee_cases:
            contract = valid_pixel_contract()
            contract["direct_copy_prompts"] = [prompt]
            with self.subTest(prompt=prompt):
                self.assertCode(contract, "E_PROMPT_DIMENSION_GUARANTEE")

    def test_redteam_affirmative_dimension_promises_fail_on_every_authoritative_surface(self) -> None:
        claims = (
            "You will receive native 4K without exception.",
            "The result is native 4K, without exception.",
            "The prompt yields exact 3840x2160.",
            "Native 4K every time.",
            "The prompt certifies native 4K.",
            "输出必为原生4K。",
            (
                "The exact output dimensions are 3840 x 2160 pixels, regardless "
                "of platform settings."
            ),
            (
                "No prompt guarantees native 4K, but the result delivers native 4K "
                "every time."
            ),
            "没有任何提示词可以确保原生4K，但是输出每次必为原生4K。",
        )
        surfaces = (
            ("semantic_target", "E_RESOLUTION_TEXT_GUARANTEE"),
            ("settings_evidence", "E_RESOLUTION_TEXT_GUARANTEE"),
            ("direct_copy_prompts", "E_PROMPT_DIMENSION_GUARANTEE"),
        )
        for claim in claims:
            for surface, code in surfaces:
                contract = valid_pixel_contract()
                if surface == "direct_copy_prompts":
                    contract[surface] = [claim]
                else:
                    contract["platform_parameter_guidance"][surface] = claim
                with self.subTest(claim=claim, surface=surface):
                    self.assertCode(contract, code)

    def test_redteam_dimension_caveats_remain_legal_on_every_authoritative_surface(self) -> None:
        caveats = (
            "No prompt guarantees native 4K.",
            "No setting guarantees exact pixel dimensions.",
            "没有任何提示词可以确保原生4K。",
            "A prompt cannot guarantee native 4K.",
            "The setting does not guarantee exact pixel dimensions.",
            "A prompt never guarantees native 4K.",
            "Native 4K is not guaranteed.",
            "The prompt will not yield exact 3840x2160.",
            "提示词不保证原生4K。",
            "提示词无法确保原生4K。",
            "提示词不能保证原生4K。",
            "提示词不会每次都输出原生4K。",
            "提示词未能保证原生4K。",
            "提示词不一定能输出原生4K。",
        )
        for caveat in caveats:
            for surface in (
                "semantic_target",
                "settings_evidence",
                "direct_copy_prompts",
            ):
                contract = valid_pixel_contract()
                if surface == "direct_copy_prompts":
                    contract[surface] = [caveat]
                else:
                    contract["platform_parameter_guidance"][surface] = caveat
                with self.subTest(caveat=caveat, surface=surface):
                    self.assertValid(contract)

    def test_deterministic_dimension_equivalents_fail_on_every_authoritative_surface(self) -> None:
        claims = (
            "The exact output dimensions are 3840 x 2160 pixels, irrespective of settings.",
            "The exact output dimensions are 3840 x 2160 pixels, independent of platform controls.",
            "The exact output dimensions are 3840 x 2160 pixels in all cases.",
            "The exact output dimensions are 3840 x 2160 pixels, no matter the platform settings.",
            "精确输出尺寸为3840 x 2160像素，无论平台设置如何。",
            "精确输出尺寸为3840 x 2160像素，不受平台设置影响。",
            "在所有情况下，精确输出尺寸为3840 x 2160像素。",
        )
        surfaces = (
            ("semantic_target", "E_RESOLUTION_TEXT_GUARANTEE"),
            ("settings_evidence", "E_RESOLUTION_TEXT_GUARANTEE"),
            ("direct_copy_prompts", "E_PROMPT_DIMENSION_GUARANTEE"),
        )
        for claim in claims:
            for surface, code in surfaces:
                contract = valid_pixel_contract()
                if surface == "direct_copy_prompts":
                    contract[surface] = [claim]
                else:
                    contract["platform_parameter_guidance"][surface] = claim
                with self.subTest(claim=claim, surface=surface):
                    self.assertCode(contract, code)

    def test_unknown_dimension_output_facts_fail_on_every_authoritative_surface(self) -> None:
        claims = (
            "The output is native 4K.",
            "The exact output dimensions are 3840 x 2160 pixels.",
            "The exact result pixel dimensions are 3840 × 2160 pixels.",
            "输出为原生4K。",
            "输出尺寸为3840×2160像素。",
            "结果像素尺寸是3840 x 2160像素。",
        )
        surfaces = (
            ("semantic_target", "E_RESOLUTION_TEXT_GUARANTEE"),
            ("settings_evidence", "E_RESOLUTION_TEXT_GUARANTEE"),
            ("direct_copy_prompts", "E_PROMPT_DIMENSION_GUARANTEE"),
        )
        for claim in claims:
            for surface, code in surfaces:
                contract = valid_pixel_contract()
                self.assertEqual(
                    contract["platform_parameter_guidance"]["dimensions_fact_state"],
                    "unknown",
                )
                self.assertEqual(
                    contract["platform_parameter_guidance"]["dimensions_evidence_type"],
                    "none",
                )
                self.assertIsNone(
                    contract["platform_parameter_guidance"]["actual_pixel_dimensions"]
                )
                if surface == "direct_copy_prompts":
                    contract[surface] = [claim]
                else:
                    contract["platform_parameter_guidance"][surface] = claim
                with self.subTest(claim=claim, surface=surface):
                    self.assertCode(contract, code)

    def test_negated_dimension_targets_and_caveats_are_legal_on_every_authoritative_surface(self) -> None:
        statements = (
            "Create a 4K-quality result as a non-guaranteed target.",
            "Regardless of platform settings, native 4K is not guaranteed.",
            (
                "No matter what the platform settings are, exact 3840 x 2160 "
                "output is not guaranteed."
            ),
            "无论平台设置如何，原生4K也不能保证。",
        )
        for statement in statements:
            for surface in (
                "semantic_target",
                "settings_evidence",
                "direct_copy_prompts",
            ):
                contract = valid_pixel_contract()
                if surface == "direct_copy_prompts":
                    contract[surface] = [statement]
                else:
                    contract["platform_parameter_guidance"][surface] = statement
                with self.subTest(statement=statement, surface=surface):
                    self.assertValid(contract)

    def test_internal_image_tools_and_codex_skill_directions_fail_on_authoritative_surfaces(self) -> None:
        cases = (
            (
                "direct_copy_prompts",
                "Codex: call image_gen__imagegen and produce the image.",
            ),
            ("semantic_target", "Invoke imagegen to produce the result."),
            ("settings_evidence", "Use image2gen for the external setting."),
            ("direct_copy_prompts", "Ask Codex to reconstruct this image."),
            ("semantic_target", "This Skill should create the final pixels."),
        )
        for surface, text in cases:
            contract = valid_pixel_contract()
            if surface == "direct_copy_prompts":
                contract[surface] = [text]
            else:
                contract["platform_parameter_guidance"][surface] = text
            with self.subTest(surface=surface, text=text):
                self.assertCode(contract, "E_AUTHORITATIVE_OUTPUT_INTERNAL_DIRECTION")

    def test_external_platform_imperatives_remain_legal_authoritative_text(self) -> None:
        contract = valid_pixel_contract()
        contract["platform_parameter_guidance"].update(
            {
                "semantic_target": (
                    "Create, edit, and reconstruct a high-resolution candidate on the "
                    "user-operated external platform."
                ),
                "settings_evidence": (
                    "The external platform control remains unknown; select it manually."
                ),
            }
        )
        contract["direct_copy_prompts"] = [
            "Create and reconstruct the supplied target while preserving its composition."
        ]
        self.assertValid(contract)

    def test_internal_tool_wording_remains_legal_only_in_non_authoritative_text(self) -> None:
        contract = valid_pixel_contract()
        contract["user_request"] = (
            "Codex: call image_gen__imagegen, imagegen, or image2gen now."
        )
        contract["notes"] = "The Skill was asked to invoke imagegen; this grants no authority."
        self.assertValid(contract)

    def test_a18_resolution_policy_requires_false_prompt_guarantee(self) -> None:
        contract = valid_pixel_contract()
        contract["platform_parameter_guidance"]["prompt_guarantees_dimensions"] = True
        self.assertCode(contract, "E_PROMPT_GUARANTEES_DIMENSIONS")

    def test_a18_resolution_policy_text_cannot_contradict_false_boolean(self) -> None:
        cases = (
            ("semantic_target", "Guarantee native 4K output from this prompt."),
            ("semantic_target", "保证输出原生4K。"),
            ("settings_evidence", "This setting always outputs 3840 x 2160 pixels."),
            ("settings_evidence", "像素尺寸必定为3840 x 2160。"),
        )
        for field, value in cases:
            contract = valid_pixel_contract()
            contract["platform_parameter_guidance"][field] = value
            with self.subTest(field=field, value=value):
                self.assertCode(contract, "E_RESOLUTION_TEXT_GUARANTEE")

    def test_a18_resolution_policy_fact_state_is_required_and_bounded(self) -> None:
        missing = valid_pixel_contract()
        del missing["platform_parameter_guidance"]
        self.assertCode(missing, "E_REQUIRED_TOP_LEVEL")

        invalid = valid_pixel_contract()
        invalid["platform_parameter_guidance"]["dimensions_fact_state"] = "guaranteed"
        self.assertCode(invalid, "E_DIMENSIONS_FACT_STATE")

        unknown_claim = valid_pixel_contract()
        unknown_claim["platform_parameter_guidance"]["actual_pixel_dimensions"] = {
            "width": 3840,
            "height": 2160,
        }
        self.assertCode(unknown_claim, "E_UNKNOWN_DIMENSIONS_CLAIM")

        for fact_state in ("known", "observed", "user_reported"):
            missing_dimensions = valid_pixel_contract()
            missing_dimensions["platform_parameter_guidance"].update(
                {
                    "dimensions_fact_state": fact_state,
                    "dimensions_evidence_type": {
                        "known": "authoritative_record",
                        "observed": "inspected_file_metadata",
                        "user_reported": "user_report",
                    }[fact_state],
                }
            )
            with self.subTest(fact_state=fact_state):
                self.assertCode(
                    missing_dimensions,
                    "E_DIMENSIONS_EVIDENCE_REQUIRED",
                )

    def test_a18_resolution_policy_legal_controls(self) -> None:
        for fact_state in ("known", "observed", "user_reported"):
            contract = valid_pixel_contract()
            contract["platform_parameter_guidance"].update(
                {
                    "dimensions_fact_state": fact_state,
                    "dimensions_evidence_type": {
                        "known": "authoritative_record",
                        "observed": "inspected_file_metadata",
                        "user_reported": "user_report",
                    }[fact_state],
                    "actual_pixel_dimensions": {"width": 3840, "height": 2160},
                    "settings_evidence": "The user or imported file establishes these dimensions.",
                }
            )
            contract["direct_copy_prompts"] = [
                (
                    "Target high-resolution detail where platform settings support it; "
                    "actual pixel dimensions are not guaranteed by prompt text."
                )
            ]
            with self.subTest(fact_state=fact_state):
                self.assertValid(contract)

        unknown = valid_pixel_contract()
        unknown["direct_copy_prompts"] = [
            "Use a 4K semantic quality target; actual dimensions depend on manual platform settings."
        ]
        unknown["platform_parameter_guidance"].update(
            {
                "semantic_target": "Target high-resolution detail without claiming pixel dimensions.",
                "settings_evidence": (
                    "External-platform resolution controls have not been observed; "
                    "the prompt cannot guarantee native 4K，且提示词不能保证原生4K。"
                ),
            }
        )
        self.assertValid(unknown)

    def test_dimensions_evidence_type_is_required_and_matches_fact_state(self) -> None:
        missing = valid_pixel_contract()
        del missing["platform_parameter_guidance"]["dimensions_evidence_type"]
        self.assertCode(missing, "E_REQUIRED_FIELD")

        invalid = valid_pixel_contract()
        invalid["platform_parameter_guidance"]["dimensions_evidence_type"] = "claim"
        self.assertCode(invalid, "E_DIMENSIONS_EVIDENCE_TYPE")

        mismatches = (
            ("unknown", "user_report"),
            ("known", "inspected_file_metadata"),
            ("observed", "authoritative_record"),
            ("user_reported", "none"),
        )
        for fact_state, evidence_type in mismatches:
            contract = valid_pixel_contract()
            contract["platform_parameter_guidance"].update(
                {
                    "dimensions_fact_state": fact_state,
                    "dimensions_evidence_type": evidence_type,
                    "actual_pixel_dimensions": (
                        None
                        if fact_state == "unknown"
                        else {"width": 1920, "height": 1080}
                    ),
                }
            )
            with self.subTest(fact_state=fact_state, evidence_type=evidence_type):
                self.assertCode(contract, "E_DIMENSIONS_EVIDENCE_TYPE_MISMATCH")

    def test_nonunknown_dimensions_reject_explicit_missingness_evidence(self) -> None:
        contract = valid_pixel_contract()
        contract["platform_parameter_guidance"].update(
            {
                "dimensions_fact_state": "known",
                "dimensions_evidence_type": "authoritative_record",
                "actual_pixel_dimensions": {"width": 3840, "height": 2160},
                "settings_evidence": "No pixel dimensions are known or evidenced.",
            }
        )
        self.assertCode(contract, "E_DIMENSIONS_EVIDENCE_CONTRADICTION")

    def test_all_four_dimension_fact_and_evidence_pairs_are_legal(self) -> None:
        cases = (
            ("unknown", "none", None, "No pixel dimensions are known."),
            (
                "known",
                "authoritative_record",
                {"width": 3840, "height": 2160},
                "An authoritative supplied record states 3840 x 2160.",
            ),
            (
                "observed",
                "inspected_file_metadata",
                {"width": 1920, "height": 1080},
                "Read-only inspection observed file metadata of 1920 x 1080.",
            ),
            (
                "user_reported",
                "user_report",
                {"width": 2048, "height": 2048},
                "The user reports selecting 2048 x 2048.",
            ),
        )
        for fact_state, evidence_type, dimensions, evidence in cases:
            contract = valid_pixel_contract()
            contract["platform_parameter_guidance"].update(
                {
                    "dimensions_fact_state": fact_state,
                    "dimensions_evidence_type": evidence_type,
                    "actual_pixel_dimensions": dimensions,
                    "settings_evidence": evidence,
                }
            )
            with self.subTest(fact_state=fact_state):
                self.assertValid(contract)

    def test_observed_matching_declarative_file_dimensions_are_legal(self) -> None:
        statements = (
            "The inspected file dimensions are 3840 x 2160 pixels.",
            "经检查，文件尺寸为3840×2160像素。",
        )
        for statement in statements:
            for surface in (
                "semantic_target",
                "settings_evidence",
                "direct_copy_prompts",
            ):
                contract = valid_pixel_contract()
                contract["platform_parameter_guidance"].update(
                    {
                        "dimensions_fact_state": "observed",
                        "dimensions_evidence_type": "inspected_file_metadata",
                        "actual_pixel_dimensions": {"width": 3840, "height": 2160},
                        "settings_evidence": statement,
                    }
                )
                if surface == "direct_copy_prompts":
                    contract[surface] = [statement]
                else:
                    contract["platform_parameter_guidance"][surface] = statement
                with self.subTest(statement=statement, surface=surface):
                    self.assertValid(contract)

    def test_inspected_file_dimension_facts_require_exact_observed_binding(self) -> None:
        statement = "The inspected file dimensions are 3840 x 2160 pixels."
        cases = (
            (
                "observed_mismatch",
                "observed",
                "inspected_file_metadata",
                {"width": 1920, "height": 1080},
                "Read-only inspection observed file metadata of 1920 x 1080.",
            ),
            (
                "unknown",
                "unknown",
                "none",
                None,
                "No external-platform resolution control has been established.",
            ),
            (
                "known",
                "known",
                "authoritative_record",
                {"width": 3840, "height": 2160},
                "An authoritative supplied record states 3840 x 2160.",
            ),
            (
                "user_reported",
                "user_reported",
                "user_report",
                {"width": 3840, "height": 2160},
                "The user reports selecting 3840 x 2160.",
            ),
        )
        for case_name, fact_state, evidence_type, dimensions, safe_evidence in cases:
            for surface in (
                "semantic_target",
                "settings_evidence",
                "direct_copy_prompts",
            ):
                contract = valid_pixel_contract()
                contract["platform_parameter_guidance"].update(
                    {
                        "dimensions_fact_state": fact_state,
                        "dimensions_evidence_type": evidence_type,
                        "actual_pixel_dimensions": dimensions,
                        "settings_evidence": safe_evidence,
                    }
                )
                if surface == "direct_copy_prompts":
                    contract[surface] = [statement]
                else:
                    contract["platform_parameter_guidance"][surface] = statement
                with self.subTest(case=case_name, surface=surface):
                    self.assertCode(contract, "E_INSPECTED_FILE_DIMENSION_BINDING")

    def test_categorical_native_4k_output_claims_fail_in_all_evidenced_states(self) -> None:
        claims = ("The output is native 4K.", "输出为原生4K。")
        states = (
            (
                "known",
                "authoritative_record",
                "An authoritative supplied record states 3840 x 2160.",
            ),
            (
                "observed",
                "inspected_file_metadata",
                "Read-only inspection observed file metadata of 3840 x 2160.",
            ),
            (
                "user_reported",
                "user_report",
                "The user reports selecting 3840 x 2160.",
            ),
        )
        surfaces = (
            ("semantic_target", "E_RESOLUTION_TEXT_GUARANTEE"),
            ("settings_evidence", "E_RESOLUTION_TEXT_GUARANTEE"),
            ("direct_copy_prompts", "E_PROMPT_DIMENSION_GUARANTEE"),
        )
        for claim in claims:
            for fact_state, evidence_type, safe_evidence in states:
                for surface, code in surfaces:
                    contract = valid_pixel_contract()
                    contract["platform_parameter_guidance"].update(
                        {
                            "dimensions_fact_state": fact_state,
                            "dimensions_evidence_type": evidence_type,
                            "actual_pixel_dimensions": {
                                "width": 3840,
                                "height": 2160,
                            },
                            "settings_evidence": safe_evidence,
                        }
                    )
                    if surface == "direct_copy_prompts":
                        contract[surface] = [claim]
                    else:
                        contract["platform_parameter_guidance"][surface] = claim
                    with self.subTest(
                        claim=claim,
                        fact_state=fact_state,
                        surface=surface,
                    ):
                        self.assertCode(contract, code)

    def test_declarative_output_dimensions_must_match_structured_dimensions(self) -> None:
        statements = (
            "The output dimensions are 3840 x 2160 pixels.",
            "The exact result pixel dimensions are 3840 × 2160 pixels.",
            "输出尺寸为3840×2160像素。",
            "结果像素尺寸是3840 x 2160像素。",
        )
        states = (
            (
                "known",
                "authoritative_record",
                "An authoritative supplied record states 1920 x 1080.",
            ),
            (
                "observed",
                "inspected_file_metadata",
                "Read-only inspection observed file metadata of 1920 x 1080.",
            ),
            (
                "user_reported",
                "user_report",
                "The user reports selecting 1920 x 1080.",
            ),
        )
        for statement in statements:
            for fact_state, evidence_type, safe_evidence in states:
                for surface in (
                    "semantic_target",
                    "settings_evidence",
                    "direct_copy_prompts",
                ):
                    contract = valid_pixel_contract()
                    contract["platform_parameter_guidance"].update(
                        {
                            "dimensions_fact_state": fact_state,
                            "dimensions_evidence_type": evidence_type,
                            "actual_pixel_dimensions": {
                                "width": 1920,
                                "height": 1080,
                            },
                            "settings_evidence": safe_evidence,
                        }
                    )
                    if surface == "direct_copy_prompts":
                        contract[surface] = [statement]
                    else:
                        contract["platform_parameter_guidance"][surface] = statement
                    with self.subTest(
                        statement=statement,
                        fact_state=fact_state,
                        surface=surface,
                    ):
                        self.assertCode(
                            contract,
                            "E_DECLARATIVE_OUTPUT_DIMENSION_BINDING",
                        )

    def test_matching_declarative_output_dimensions_are_legal_in_evidenced_states(self) -> None:
        statements = (
            "The output dimensions are 3840 x 2160 pixels.",
            "The exact result pixel dimensions are 3840 × 2160 pixels.",
            "输出尺寸为3840×2160像素。",
            "结果像素尺寸是3840 x 2160像素。",
        )
        states = (
            (
                "known",
                "authoritative_record",
                "An authoritative supplied record states 3840 x 2160.",
            ),
            (
                "observed",
                "inspected_file_metadata",
                "Read-only inspection observed file metadata of 3840 x 2160.",
            ),
            (
                "user_reported",
                "user_report",
                "The user reports selecting 3840 x 2160.",
            ),
        )
        for statement in statements:
            for fact_state, evidence_type, safe_evidence in states:
                for surface in (
                    "semantic_target",
                    "settings_evidence",
                    "direct_copy_prompts",
                ):
                    contract = valid_pixel_contract()
                    contract["platform_parameter_guidance"].update(
                        {
                            "dimensions_fact_state": fact_state,
                            "dimensions_evidence_type": evidence_type,
                            "actual_pixel_dimensions": {
                                "width": 3840,
                                "height": 2160,
                            },
                            "settings_evidence": safe_evidence,
                        }
                    )
                    if surface == "direct_copy_prompts":
                        contract[surface] = [statement]
                    else:
                        contract["platform_parameter_guidance"][surface] = statement
                    with self.subTest(
                        statement=statement,
                        fact_state=fact_state,
                        surface=surface,
                    ):
                        self.assertValid(contract)

    def test_a19_prompt_plan_cannot_contain_candidate_result(self) -> None:
        contract = valid_pixel_contract()
        contract["assets"].append(
            {"id": "stray_candidate", "kind": "candidate_result", "approved": False}
        )
        self.assertCode(contract, "E_PROMPT_PLAN_CANDIDATE_RESULT")

    def test_a19_prompt_plan_without_candidate_result_is_valid(self) -> None:
        self.assertValid(valid_pixel_contract())

    def test_a20_imported_state_rejects_unbound_candidate_result(self) -> None:
        contract = valid_staged_contract()
        contract["assets"].append(
            {"id": "unbound_candidate", "kind": "candidate_result", "approved": False}
        )
        self.assertCode(contract, "E_UNBOUND_CANDIDATE_RESULT")

    def test_a20_imported_state_allows_multiple_fully_bound_candidates(self) -> None:
        contract = valid_staged_contract()
        contract["assets"].append(
            {"id": "external_candidate_002", "kind": "candidate_result", "approved": False}
        )
        contract["external_result_provenance"].append(
            {
                "result_id": "external_candidate_002",
                "origin": "user_manual_external_generation",
                "imported_by_user": True,
                "provenance": "The user imported a second external candidate for comparison.",
            }
        )
        self.assertValid(contract)

    def test_a23_candidate_result_approved_true_always_fails(self) -> None:
        prompt_plan = valid_pixel_contract()
        prompt_plan["assets"].append(
            {"id": "invalid_candidate", "kind": "candidate_result", "approved": True}
        )
        self.assertCode(prompt_plan, "E_CANDIDATE_RESULT_APPROVED")

        imported = valid_staged_contract()
        result_id = imported["external_result_provenance"][0]["result_id"]
        for asset in imported["assets"]:
            if asset["id"] == result_id:
                asset["approved"] = True
        self.assertCode(imported, "E_CANDIDATE_RESULT_APPROVED")

    def test_a23_bound_candidate_result_approved_false_is_valid(self) -> None:
        self.assertValid(valid_staged_contract())

    def test_cli_valid_invalid_and_malformed_json_exit_codes(self) -> None:
        script = SCRIPT_DIR / "validate_reconstruction_contract.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            contract_path = Path(temp_dir) / "contract.json"
            contract_path.write_text(json.dumps(valid_staged_contract()), encoding="utf-8")
            valid_run = subprocess.run(
                [sys.executable, "-B", str(script), str(contract_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(0, valid_run.returncode, valid_run.stderr)
            self.assertTrue(json.loads(valid_run.stdout)["valid"])

            invalid = valid_staged_contract()
            invalid["status"] = "final"
            contract_path.write_text(json.dumps(invalid), encoding="utf-8")
            invalid_run = subprocess.run(
                [sys.executable, "-B", str(script), str(contract_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(1, invalid_run.returncode, invalid_run.stderr)
            self.assertIn("E_STATUS", error_codes(json.loads(invalid_run.stdout)))

            contract_path.write_text("{not valid json", encoding="utf-8")
            malformed_run = subprocess.run(
                [sys.executable, "-B", str(script), str(contract_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(2, malformed_run.returncode, malformed_run.stderr)
            self.assertEqual("E_INPUT_JSON", json.loads(malformed_run.stdout)["errors"][0]["code"])

    def test_cli_assets_only_contract_exits_one(self) -> None:
        script = SCRIPT_DIR / "validate_reconstruction_contract.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            contract_path = Path(temp_dir) / "assets_only.json"
            contract_path.write_text(
                json.dumps({"assets": [{"id": "target", "kind": "target"}]}),
                encoding="utf-8",
            )
            run = subprocess.run(
                [sys.executable, "-B", str(script), str(contract_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(1, run.returncode, run.stderr)
            self.assertIn("E_REQUIRED_TOP_LEVEL", error_codes(json.loads(run.stdout)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
