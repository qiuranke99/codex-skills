#!/usr/bin/env python3
"""Deterministic contract, adversarial, dedup, receipt, gallery, and BOTH tests."""

from __future__ import annotations

import copy
import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

import _contract_utils as contract_utils
from _contract_utils import ContractError, read_json, read_jsonl, write_json, write_jsonl
from _evidence_binding import (
    CANONICALIZATION,
    REPORT_TRUST_STATEMENT,
    approach_plan_sha256,
    canonical_sha256,
    curation_input_sha256,
    dedup_comparison_set_sha256,
    intent_constraints_sha256,
)
import build_review_gallery
from build_review_gallery import build_gallery
import deduplicate_candidates
from deduplicate_candidates import build_report as build_dedup_report
from _json_schema_subset import SchemaViolation, assert_schema_supported, validate as validate_schema
import verify_candidates
import validate_research_run
from validate_research_run import validate_run


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = PACKAGE_ROOT / "tests/fixtures"


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _rights() -> dict[str, Any]:
    return {
        "discoverable": {"state": "allowed", "basis": "Public item discovery was observed."},
        "viewable": {"state": "allowed", "basis": "Browser rendering was observed."},
        "shareable_without_session": {"state": "allowed", "basis": "Public canonical link was observed."},
        "downloadable": {"state": "unknown", "basis": "No download right was asserted."},
        "internal_board_use": {"state": "permission_required", "basis": "Use depends on project policy."},
        "commercial_reuse": {"state": "permission_required", "basis": "Reference access grants no reuse right."},
    }


def _dimension(index: int, name: str) -> dict[str, Any]:
    score = 50 - index % 20 if name == "rights_risk" else 70 + index % 20
    return {"score": score, "rationale": f"Evidence-backed {name} assessment for item {index}."}


def _make_intent(run_id: str, modality: str, pack_contracts: list[dict[str, Any]], strategy: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "intent_id": "intent_fixture",
        "intent_version": "v2",
        "run_mode": "test_fixture",
        "created_at": "2026-07-13T00:00:00Z",
        "decision_to_inform": "Choose transferable advertising art-direction references.",
        "deliverable_type": "reference_board",
        "modality_route": modality,
        "routing": {
            "strategy": strategy,
            "pack_contracts": pack_contracts,
            "unified_territory_quota": (
                {
                    "image_qualified_target": 15,
                    "video_qualified_target": 15,
                    "image_selected_target": 10,
                    "video_selected_target": 10,
                    "cross_modal_territory_min": 5,
                }
                if strategy == "unified_territory"
                else None
            ),
        },
        "subject": "premium personal care campaign",
        "scene_scale": "large_scale_set",
        "human_presence": "full_body_single",
        "visual_axes": ["monumental set", "controlled material palette"],
        "temporal_axes": [] if modality == "image" else ["camera movement", "edit rhythm"],
        "must_have": ["specific creative object"],
        "must_not_have": ["product-only tabletop still life"],
        "positive_anchors": [],
        "negative_anchors": [],
        "market_region": ["global"],
        "languages": ["en"],
        "freshness_need": {
            "content_max_age_days": None,
            "registry_reverify_max_age_days": 30,
            "final_receipt_window_minutes": 30,
        },
        "access_policy": {
            "allow_public_web": True,
            "allow_signed_chrome": True,
            "allow_subscription": False,
            "allow_geo_or_age_gated": False,
            "public_shareable_required_for_delivery": True,
            "fallback_on_blocked": True,
        },
        "rights_scope": _rights(),
        "diversity_requirements": {
            "broad_brief": True,
            "min_domains": 5,
            "min_source_families": 4,
            "territory_count_min": 4,
            "territory_count_max": 6,
            "max_per_domain": 4,
            "max_per_campaign_or_creator": 2,
            "max_per_near_duplicate_group": 1,
        },
        "clarification_questions": [
            {
                "question": "Static or temporal decision?",
                "answer": modality,
                "asked_at": "2026-07-13T00:00:00Z",
                "effect_on_intent": "Froze the modality route.",
            }
        ],
        "route_reason_codes": [
            "explicit_image_request" if modality == "image" else (
                "explicit_video_request" if modality == "video" else "explicit_both_request"
            )
        ],
        "route_evidence": {
            "declared_by_user": True,
            "evidence": [f"User needs a {modality} reference pack."],
            "confidence": 1.0,
        },
        "assumptions": [
            {
                "statement": "Public shareability is preferred.",
                "basis": "default_contract",
                "confidence": 0.8,
                "reversible": True,
            }
        ],
        "approval": {"state": "inferred_and_frozen", "approved_at": "2026-07-13T00:01:00Z", "approved_by": "root"},
    }


def _make_registry(run_id: str, pack_contracts: list[dict[str, Any]]) -> dict[str, Any]:
    agents = []
    for index in range(4):
        agents.append({"agent_id": f"finder_{index}", "role": "search_scout", "access_scope": ["public"], "session_owner": False})
        agents.append({"agent_id": f"capture_operator_{index}", "role": "capture_operator", "access_scope": ["public"], "session_owner": False})
        agents.append({"agent_id": f"verifier_{index}", "role": "verification_agent", "access_scope": ["public"], "session_owner": False})
    agents.extend(
        [
            {"agent_id": "curator_relevance", "role": "relevance_curator", "access_scope": ["public"], "session_owner": False},
            {"agent_id": "curator_diversity", "role": "diversity_curator", "access_scope": ["public"], "session_owner": False},
            {"agent_id": "auditor_red", "role": "adversarial_auditor", "access_scope": ["public"], "session_owner": False},
            {"agent_id": "root", "role": "root_synthesizer", "access_scope": ["public"], "session_owner": False},
        ]
    )
    methods = ["direct_category", "visual_temporal_mechanism", "credit_graph", "challenger"]
    families = ["first_party", "awards", "photography_editorial", "craft_credits"]
    yields = [(15, 12), (9, 6), (9, 6), (9, 6)]
    approaches = []
    coverage = []
    for contract in pack_contracts:
        pack_id = contract["pack_id"]
        modality = contract["modality"]
        for index, method in enumerate(methods):
            returned, qualified = yields[index]
            approaches.append(
                {
                    "approach_id": f"{pack_id}_approach_{index}",
                    "pack_id": pack_id,
                    "modality": modality,
                    "decision_axis": "static_reference" if modality == "image" else (
                        "temporal_reference" if modality == "video" else "cross_modal_reference"
                    ),
                    "method": method,
                    "hypothesis": f"Independent method {method} contributes non-correlated evidence.",
                    "queries": [{"query_id": f"{pack_id}_query_{index}", "query_text": f"fixture query {index}", "locale": "en", "round": 1}],
                    "source_family_ids": [families[index]],
                    "executing_agent_id": f"finder_{index}",
                    "favored_route_disclosed": False,
                    "started_at": f"2026-07-13T00:06:0{index}Z",
                    "returned_count": returned,
                    "qualified_count": qualified,
                    "qualification_rate": round(qualified / returned, 3),
                    "failure_records": [
                        {
                            "failure_id": f"failure_{pack_id}_{index}",
                            "query_id": f"{pack_id}_query_{index}",
                            "source_family_id": families[index],
                            "round": 1,
                            "failure_code": "screened_out",
                            "candidate_ids": [
                                f"candidate_{pack_id}_screened_{index}_{offset}"
                                for offset in range(returned - qualified)
                            ],
                            "receipt_ids": [],
                            "observed_at": "2026-07-13T00:12:00Z",
                            "reason": "These returned candidates failed the registered lane's relevance screen.",
                            "fallback_action": "Retain the evidence rows and adjust the next query without repeating the failed path.",
                        }
                    ],
                    "next_round_adjustment": "Use the recorded fallback while preserving the failed candidate evidence.",
                    "status": "complete",
                }
            )
        coverage.append(
            {
                "pack_id": pack_id,
                "modality": modality,
                "required_distinct_method_count": 3,
                "declared_distinct_method_count": 4,
                "covered_methods": methods,
                "coverage_asserted": True,
            }
        )
    registry = {
        "schema_version": "1.4.0",
        "registry_id": "approach_registry_fixture",
        "run_id": run_id,
        "intent_id": "intent_fixture",
        "intent_version": "v2",
        "created_at": "2026-07-13T00:05:00Z",
        "registration": {
            "kind": "synthetic_fixture",
            "frozen_at": "2026-07-13T00:05:00Z",
            "plan_sha256": "0" * 64,
            "canonicalization": CANONICALIZATION,
        },
        "independence_policy": {
            "finder_cannot_approve_own_candidate": True,
            "verifier_must_differ_from_finder": True,
            "capture_operator_must_differ_from_finder_and_verifier": True,
            "decision_roles_use_distinct_agent_ids": True,
            "blind_curators_share_frozen_input": True,
            "final_auditor_independent": True,
            "scouts_route_blinded": True,
        },
        "agents": agents,
        "approaches": approaches,
        "coverage": coverage,
    }
    registry["registration"]["plan_sha256"] = approach_plan_sha256(registry)
    return registry


def _candidate(
    run_id: str,
    modality: str,
    index: int,
    pack_id: str = "unassigned_pack",
    intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if intent is None:
        contract = {"pack_id": pack_id, "modality": modality, "qualified_target": 30, "selected_target": 20}
        intent = _make_intent(run_id, modality, [contract], "single_modality")
    cid = f"candidate_{modality}_{index:02d}"
    domain_index = index % 5
    domain = f"source{domain_index}.example"
    url = f"https://{domain}/work/{cid}"
    family_index = domain_index % 4
    family = ["first_party", "awards", "photography_editorial", "craft_credits"][family_index]
    status = "selected" if index < 20 else "rejected"
    dimensions = {
        name: _dimension(index, name)
        for name in (
            "relevance",
            "craft_signal",
            "source_authority",
            "freshness",
            "access_reliability",
            "link_durability",
            "evidence_completeness",
            "rights_risk",
            "diversity_contribution",
        )
    }
    return {
        "schema_version": "1.2.0",
        "candidate_id": cid,
        "run_id": run_id,
        "intent_id": "intent_fixture",
        "intent_version": "v2",
        "pack_id": pack_id,
        "discovered_at": "2026-07-13T00:10:00Z",
        "modality": modality,
        "object": {
            "object_type": "project_image" if modality == "image" else "specific_video_work",
            "title": f"Reference {index}",
            "campaign": f"campaign_{index}",
            "brand": f"brand_{index}",
            "creator": f"creator_{index}",
            "publish_date": "2026-01-01",
            "region": "global",
            "language": "en",
            "stable_id": f"stable_{modality}_{index}",
            "canonical_url": url,
            "asset_locator": f"asset-{modality}-{index}",
        },
        "source": {
            "source_id": f"runtime:{domain}",
            "source_family_id": family,
            "domain": domain,
            "discovered_url": url,
            "evidence_tier": "original_owner",
        },
        "access_state": {
            "mode": "public",
            "state": "accessible",
            "checked_url": url,
            "page_rendered": True,
            "canonical_url_resolved": True,
            "shareable_without_session": True,
            "http_status": 200,
            "challenge_detected": False,
        },
        "provenance_check": {
            "status": "passed",
            "accountable_url": url,
            "accountable_owner": f"owner_{index}",
            "source_signal": "original_owner",
            "matched_object": True,
        },
        "rights_scope": _rights(),
        "intent_alignment": {
            "intent_constraints_sha256": intent_constraints_sha256(intent),
            "decision_relevance": "This reference directly informs the frozen advertising art-direction decision.",
            "subject_match": True,
            "observed_scene_scale": intent["scene_scale"],
            "observed_human_presence": intent["human_presence"],
            "visual_axes_matched": list(intent["visual_axes"]),
            "temporal_axes_matched": list(intent["temporal_axes"]) if modality == "video" else [],
            "must_have_evidence": [
                {
                    "criterion": criterion,
                    "evidence": f"Visible candidate evidence satisfies required criterion: {criterion}.",
                }
                for criterion in intent["must_have"]
            ],
            "must_not_have_checks": [
                {
                    "criterion": criterion,
                    "absent": True,
                    "evidence": f"Independent review confirms excluded feature is absent: {criterion}.",
                }
                for criterion in intent["must_not_have"]
            ],
            "positive_anchor_assessments": [
                {"label": anchor["label"], "status": "aligned", "rationale": "Candidate preserves the transferable positive anchor mechanism."}
                for anchor in intent["positive_anchors"]
            ],
            "negative_anchor_assessments": [
                {"label": anchor["label"], "status": "neutral", "rationale": "Candidate avoids the negative anchor failure mode without copying it."}
                for anchor in intent["negative_anchors"]
            ],
            "market_region_status": "match",
            "language_status": "match",
            "transfer_rationale": None,
            "rights_compatible": True,
        },
        "evaluation_dimensions": dimensions,
        "dedup": {
            "canonical_url_key": url,
            "stable_id_key": f"runtime:{domain}:stable_{modality}_{index}",
            "fingerprint": {
                "method": "image_content_sha256_dhash64" if modality == "image" else "video_sample_manifest_sha256_dhash64",
                "exact_or_manifest_sha256": hashlib.sha256(f"exact:{cid}".encode()).hexdigest(),
                "perceptual_hash": hashlib.sha256(f"perceptual:{cid}".encode()).hexdigest()[:16],
                "sample_count": 1 if modality == "image" else 3,
                "sampled_at_seconds": [] if modality == "image" else [0.0, 1.0, 2.0],
                "evidence_capture_id": "capture_" + cid.removeprefix("candidate_"),
            },
            "near_duplicate_group_id": None,
            "campaign_group_id": f"campaign_group_{index}",
            "creator_group_id": f"creator_group_{index}",
            "version_relation": "unique",
        },
        "diversity": {
            "territory_id": f"territory_{index % 5}",
            "visual_mechanism_tags": ["controlled_set"],
            "temporal_mechanism_tags": [] if modality == "image" else ["measured_motion"],
            "discipline_tags": ["advertising"],
        },
        "agent_trace": {
            "finder_agent_id": f"finder_{family_index}",
            "approach_id": f"{pack_id}_approach_{family_index}",
            "query_id": f"{pack_id}_query_{family_index}",
            "discovery_lane": "fixture_lane",
            "finder_decision": "screened_in",
        },
        "status": status,
        "verification_receipt_id": f"receipt_{modality}_{index:02d}",
    }


def _screened_candidate(
    run_id: str,
    pack_id: str,
    pack_modality: str,
    intent: dict[str, Any],
    approach_index: int,
    offset: int,
) -> dict[str, Any]:
    modality = (
        "image" if (approach_index + offset) % 2 == 0 else "video"
    ) if pack_modality == "mixed" else pack_modality
    candidate = _candidate(
        run_id,
        modality,
        100 + approach_index * 3 + offset,
        pack_id,
        intent,
    )
    candidate_id = f"candidate_{pack_id}_screened_{approach_index}_{offset}"
    domain = f"screened-{approach_index}-{offset}-{pack_id.replace('_', '-')}.example"
    url = f"https://{domain}/work/{candidate_id}"
    family = ["first_party", "awards", "photography_editorial", "craft_credits"][approach_index]
    candidate.update(
        {
            "candidate_id": candidate_id,
            "status": "quarantined",
            "verification_receipt_id": None,
        }
    )
    candidate["object"].update(
        {
            "title": f"Screened reference {approach_index}-{offset}",
            "campaign": f"screened_campaign_{approach_index}_{offset}",
            "brand": f"screened_brand_{approach_index}_{offset}",
            "creator": f"screened_creator_{approach_index}_{offset}",
            "stable_id": f"stable_{pack_id}_screened_{approach_index}_{offset}",
            "canonical_url": url,
            "asset_locator": f"asset-{pack_id}-screened-{approach_index}-{offset}",
        }
    )
    candidate["source"].update(
        {
            "source_id": f"runtime:{domain}",
            "source_family_id": family,
            "domain": domain,
            "discovered_url": url,
        }
    )
    candidate["access_state"]["checked_url"] = url
    candidate["provenance_check"].update(
        {
            "accountable_url": url,
            "accountable_owner": f"screened_owner_{approach_index}_{offset}",
        }
    )
    candidate["dedup"].update(
        {
            "canonical_url_key": url,
            "stable_id_key": f"runtime:{domain}:{candidate['object']['stable_id']}",
            "campaign_group_id": f"screened_campaign_group_{approach_index}_{offset}",
            "creator_group_id": f"screened_creator_group_{approach_index}_{offset}",
        }
    )
    candidate["agent_trace"].update(
        {
            "finder_agent_id": f"finder_{approach_index}",
            "approach_id": f"{pack_id}_approach_{approach_index}",
            "query_id": f"{pack_id}_query_{approach_index}",
            "discovery_lane": "fixture_screened_lane",
            "finder_decision": "screened_out",
        }
    )
    return candidate


def _receipt(candidate: dict[str, Any], checked_at: datetime, pack_id: str) -> dict[str, Any]:
    modality = candidate["modality"]
    cid = candidate["candidate_id"]
    finder = candidate["agent_trace"]["finder_agent_id"]
    verifier_index = (int(finder.rsplit("_", 1)[1]) + 1) % 4
    if modality == "image":
        image_render = {
            "rendered": True,
            "asset_locator": candidate["object"]["asset_locator"],
            "natural_width": 1600,
            "natural_height": 900,
            "placeholder_detected": False,
        }
        video_playback = None
    else:
        image_render = None
        video_playback = {
            "player_present": True,
            "playback_started": True,
            "observed_progress_seconds": 2.5,
            "duration_seconds": 30.0,
            "specific_work_matched": True,
        }
    return {
        "schema_version": "1.1.0",
        "receipt_id": candidate["verification_receipt_id"],
        "run_id": candidate["run_id"],
        "intent_id": candidate["intent_id"],
        "intent_version": candidate["intent_version"],
        "pack_id": pack_id,
        "candidate_id": cid,
        "source_id": candidate["source"]["source_id"],
        "modality": modality,
        "checked_at": _iso(checked_at),
        "freshness": {
            "window_minutes": 30,
            "expires_at": _iso(checked_at + timedelta(minutes=30)),
            "status": "fresh",
            "reverification_required": False,
        },
        "verifier": {
            "finder_agent_id": finder,
            "verifier_agent_id": f"verifier_{verifier_index}",
            "verification_surface": "in_app_browser",
            "independence_asserted": True,
        },
        "access_state": copy.deepcopy(candidate["access_state"]),
        "media_check": {"status": "passed", "kind": modality, "image_render": image_render, "video_playback": video_playback},
        "object_match": {"status": "matched", "matched_title": True, "matched_stable_id": True, "rationale": "Visible object and stable ID match."},
        "provenance_check": copy.deepcopy(candidate["provenance_check"]),
        "rights_scope": copy.deepcopy(candidate["rights_scope"]),
        "dedup_check": {
            "status": "unique",
            "exact_url_checked": True,
            "stable_id_checked": True,
            "campaign_version_checked": True,
            "near_duplicate_group_id": None,
            "fingerprint_capture_ids": [candidate["dedup"]["fingerprint"]["evidence_capture_id"]],
            "comparison_set_sha256": "0" * 64,
            "phash_distance_threshold": 6,
            "manual_version_review_ref": None,
        },
        "evidence_level": "E4_QUALIFIED",
        "evidence": [
            {"kind": "url", "locator": candidate["object"]["canonical_url"], "captured_at": _iso(checked_at)},
            {
                "kind": "dom_locator" if modality == "image" else "player_progress",
                "locator": candidate["object"]["asset_locator"],
                "captured_at": _iso(checked_at),
            },
        ],
        "capture_bindings": [],
        "failure_codes": [],
        "outcome": "qualified",
    }


def _capture_record(
    candidate: dict[str, Any],
    receipt: dict[str, Any],
    pack_id: str,
    plan_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "capture_id": "capture_" + candidate["candidate_id"].removeprefix("candidate_"),
        "run_id": candidate["run_id"],
        "intent_id": candidate["intent_id"],
        "intent_version": candidate["intent_version"],
        "pack_id": pack_id,
        "phase": "final_verification",
        "candidate_id": candidate["candidate_id"],
        "approach_id": candidate["agent_trace"]["approach_id"],
        "approach_plan_sha256": plan_sha256,
        "captured_at": receipt["checked_at"],
        "operator_agent_id": "capture_operator_" + candidate["agent_trace"]["finder_agent_id"].rsplit("_", 1)[1],
        "surface": receipt["verifier"]["verification_surface"],
        "record_origin": "synthetic_fixture",
        "observation": {
            "canonical_url": candidate["object"]["canonical_url"],
            "asset_locator": candidate["object"]["asset_locator"],
            "stable_id": candidate["object"]["stable_id"],
            "access_state": copy.deepcopy(receipt["access_state"]),
            "media_check": copy.deepcopy(receipt["media_check"]),
            "object_match": copy.deepcopy(receipt["object_match"]),
            "provenance_check": copy.deepcopy(receipt["provenance_check"]),
            "dedup_fingerprint": {
                "method": candidate["dedup"]["fingerprint"]["method"],
                "input_asset_locator": candidate["object"]["asset_locator"],
                "exact_or_manifest_sha256": candidate["dedup"]["fingerprint"]["exact_or_manifest_sha256"],
                "perceptual_hash": candidate["dedup"]["fingerprint"]["perceptual_hash"],
                "sample_count": candidate["dedup"]["fingerprint"]["sample_count"],
                "sampled_at_seconds": candidate["dedup"]["fingerprint"]["sampled_at_seconds"],
                "computed_at": receipt["checked_at"],
                "tool_name": "fixture-fingerprint",
                "tool_version": "1.0.0",
            },
        },
        "source_record": None,
        "trust_boundary": {
            "cryptographic_authenticity": "not_attested",
            "rights_granted": False,
            "session_free_access_observed": receipt["access_state"]["shareable_without_session"],
        },
    }


def _feedback(
    run_id: str,
    pack_id: str,
    candidate_ids: list[str],
    approach_ids: list[str],
    query_ids: list[str],
    artifact_bindings: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "1.2.0",
        "feedback_id": "feedback_fixture",
        "timestamp": "2026-07-13T00:20:00Z",
        "run_id": run_id,
        "intent_id": "intent_fixture",
        "pack_id": pack_id,
        "feedback_class": "intent_correction",
        "signal_class": "explicit_hard_constraint",
        "user_evidence_or_quote": "The initial route was too product-still-life oriented.",
        "failed_assumption": "Product-category terms would surface the required large-scale model scene.",
        "error_layer": "intent",
        "constraint_delta": [
            {
                "target_artifact_type": "intent_brief",
                "before_ref": "00_intent/intent_brief.v1.snapshot.json",
                "after_ref": "00_intent/intent_brief.json",
                "operation": "replace",
                "path": "/scene_scale",
                "before_exists": True,
                "after_exists": True,
                "before": "tabletop",
                "after": "large_scale_set",
                "reason": "User explicitly corrected the scene scale.",
            }
        ],
        "invalidated_candidate_ids": candidate_ids,
        "invalidated_approach_ids": approach_ids,
        "invalidated_query_ids": query_ids,
        "invalidated_artifact_refs": [
            {
                "artifact_type": "intent_brief",
                "ref": "00_intent/intent_brief.v1.snapshot.json",
                "reason": "The prior scene-scale assumption was replaced."
            }
        ],
        "repair_start_phase": "intent_freeze",
        "completion_evidence": {
            "status": "applied",
            "completed_at": "2026-07-13T00:59:01Z",
            "artifact_bindings": artifact_bindings,
        },
        "scope": "session",
        "scope_evidence": {
            "basis": "current_run_only",
            "supporting_feedback_ids": [],
            "counterexamples_considered": "The correction is specific to this brief and does not establish a cross-project preference.",
            "scope_owner": run_id,
            "reversal_procedure": "Revert the v2 intent to its bound v1 snapshot if the user withdraws the correction.",
        },
        "external_persistence_state": "not_applied_by_skill",
        "confidence": 1.0,
        "supersedes": None,
        "intent_version_before": "v1",
        "intent_version_after": "v2",
        "user_confirmed_persistence": False,
        "agent_trace": {"recorded_by": "root", "applied_by": "root", "applied_at": "2026-07-13T00:21:00Z"},
    }


def _artifact_paths(run_root: Path, pack_root: Path) -> dict[str, Path]:
    return {
        "intent_brief": run_root / "00_intent/intent_brief.json",
        "approach_registry": run_root / "01_orchestration/approach_registry.json",
        "candidate_ledger": pack_root / "02_candidates/candidate_ledger.jsonl",
        "verification_receipts": pack_root / "03_verification/verification_receipts.jsonl",
        "browser_capture_records": pack_root / "03_verification/browser_capture_records.jsonl",
        "shortlist_30": pack_root / "04_selection/shortlist_30.json",
        "selected_20": pack_root / "04_selection/selected_20.json",
        "rejected_10": pack_root / "04_selection/rejected_10.json",
        "feedback_ledger": pack_root / "05_feedback/feedback_ledger.jsonl",
        "reference_board": pack_root / "06_output/reference_board.html",
    }


def _feedback_current_paths(run_root: Path, pack_root: Path) -> dict[str, Path]:
    return {
        "intent_brief": run_root / "00_intent/intent_brief.json",
        "approach_registry": run_root / "01_orchestration/approach_registry.json",
        "candidate": pack_root / "02_candidates/candidate_ledger.jsonl",
        "browser_capture_record": pack_root / "03_verification/browser_capture_records.jsonl",
        "verification_receipt": pack_root / "03_verification/verification_receipts.jsonl",
        "shortlist_30": pack_root / "04_selection/shortlist_30.json",
        "selected_20": pack_root / "04_selection/selected_20.json",
        "rejected_10": pack_root / "04_selection/rejected_10.json",
        "relevance_review": pack_root / "04_selection/review/relevance.json",
        "diversity_review": pack_root / "04_selection/review/diversity.json",
        "resolution_review": pack_root / "04_selection/review/resolution.json",
        "reference_board": pack_root / "06_output/reference_board.html",
        "adversarial_audit": pack_root / "07_audit/adversarial_audit_results.json",
    }


def _feedback_completion_bindings(run_root: Path, pack_root: Path) -> list[dict[str, Any]]:
    return [
        {
            "artifact_type": artifact_type,
            "ref": path.relative_to(
                run_root if artifact_type in {"intent_brief", "approach_registry"} else pack_root
            ).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for artifact_type, path in _feedback_current_paths(run_root, pack_root).items()
    ]


def _referenced_evidence_contract(run_root: Path, pack_root: Path) -> list[dict[str, Any]]:
    purposes_by_path: dict[Path, set[str]] = {}

    def resolve(ref: str) -> Path:
        if ref.startswith(("00_intent/", "01_orchestration/")):
            return run_root / ref
        return pack_root / ref

    def bind(ref: str, purpose: str) -> None:
        path = resolve(ref)
        purposes_by_path.setdefault(path, set()).add(purpose)

    for artifact_name in ("selected_20.json", "rejected_10.json"):
        trace = read_json(pack_root / "04_selection" / artifact_name)["curation_trace"]
        bind(trace["relevance_review_ref"], "relevance_review")
        bind(trace["diversity_review_ref"], "diversity_review")
        bind(trace["resolution_ref"], "resolution_review")
    bind("07_audit/adversarial_audit_results.json", "adversarial_audit")
    for event in read_jsonl(pack_root / "05_feedback/feedback_ledger.jsonl"):
        for invalidated in event["invalidated_artifact_refs"]:
            if invalidated["artifact_type"] == "intent_brief":
                bind(invalidated["ref"], "feedback_intent_snapshot")
    waiver = read_json(pack_root / "04_selection/selected_20.json")["diversity_policy"].get("waiver")
    if isinstance(waiver, dict):
        for ref in waiver.get("evidence", []):
            bind(ref, "diversity_waiver_evidence")
    for receipt in read_jsonl(pack_root / "03_verification/verification_receipts.jsonl"):
        review_ref = receipt.get("dedup_check", {}).get("manual_version_review_ref")
        if review_ref is not None:
            bind(review_ref, "dedup_version_review")

    return [
        {
            "path": contract_utils.canonical_relative_path(path, run_root),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "purposes": sorted(purposes),
        }
        for path, purposes in sorted(purposes_by_path.items(), key=lambda item: str(item[0]))
    ]


def _refresh_report_contracts(
    run_root: Path,
    pack_root: Path,
    *,
    refresh_curation: bool = True,
    refresh_feedback: bool = True,
) -> None:
    if refresh_curation:
        intent = read_json(run_root / "00_intent/intent_brief.json")
        shortlist = read_json(pack_root / "04_selection/shortlist_30.json")
        candidates = read_jsonl(pack_root / "02_candidates/candidate_ledger.jsonl")
        receipts = read_jsonl(pack_root / "03_verification/verification_receipts.jsonl")
        input_hash = curation_input_sha256(intent, shortlist, candidates, receipts)
        relevance_path = pack_root / "04_selection/review/relevance.json"
        diversity_path = pack_root / "04_selection/review/diversity.json"
        resolution_path = pack_root / "04_selection/review/resolution.json"
        if relevance_path.is_file() and diversity_path.is_file() and resolution_path.is_file():
            relevance_review = read_json(relevance_path)
            diversity_review = read_json(diversity_path)
            resolution_review = read_json(resolution_path)
            relevance_review["input_contract_sha256"] = input_hash
            diversity_review["input_contract_sha256"] = input_hash
            write_json(relevance_path, relevance_review)
            write_json(diversity_path, diversity_review)
            resolution_review["input_contract_sha256"] = input_hash
            resolution_review["relevance_review_sha256"] = hashlib.sha256(relevance_path.read_bytes()).hexdigest()
            resolution_review["diversity_review_sha256"] = hashlib.sha256(diversity_path.read_bytes()).hexdigest()
            write_json(resolution_path, resolution_review)
    feedback_path = pack_root / "05_feedback/feedback_ledger.jsonl"
    if refresh_feedback and feedback_path.is_file():
        feedback_events = read_jsonl(feedback_path)
        if feedback_events:
            current_bindings = _feedback_completion_bindings(run_root, pack_root)
            for event in feedback_events:
                event["completion_evidence"]["artifact_bindings"] = copy.deepcopy(current_bindings)
                if event["error_layer"] in {"intent", "route"}:
                    candidates = read_jsonl(pack_root / "02_candidates/candidate_ledger.jsonl")
                    registry = read_json(run_root / "01_orchestration/approach_registry.json")
                    pack_approaches = [
                        item for item in registry["approaches"] if item["pack_id"] == event["pack_id"]
                    ]
                    event["invalidated_candidate_ids"] = [item["candidate_id"] for item in candidates]
                    event["invalidated_approach_ids"] = [item["approach_id"] for item in pack_approaches]
                    event["invalidated_query_ids"] = [
                        query["query_id"] for item in pack_approaches for query in item["queries"]
                    ]
            write_jsonl(feedback_path, feedback_events)
    report_path = pack_root / "06_output/verification_report.json"
    report = read_json(report_path)
    paths = _artifact_paths(run_root, pack_root)
    for item in report["artifact_contract"]:
        item["sha256"] = hashlib.sha256(paths[item["artifact_type"]].read_bytes()).hexdigest()
    report["referenced_evidence_contract"] = _referenced_evidence_contract(run_root, pack_root)
    write_json(report_path, report)


def _refresh_candidate_intent_bindings(run_root: Path, pack_root: Path) -> None:
    intent = read_json(run_root / "00_intent/intent_brief.json")
    path = pack_root / "02_candidates/candidate_ledger.jsonl"
    candidates = read_jsonl(path)
    for candidate in candidates:
        candidate["intent_alignment"]["intent_constraints_sha256"] = intent_constraints_sha256(intent)
    write_jsonl(path, candidates)
    _refresh_report_contracts(run_root, pack_root)


def _refresh_approach_plan_bindings(run_root: Path) -> None:
    registry_path = run_root / "01_orchestration/approach_registry.json"
    registry = read_json(registry_path)
    registry["registration"]["plan_sha256"] = approach_plan_sha256(registry)
    write_json(registry_path, registry)
    intent = read_json(run_root / "00_intent/intent_brief.json")
    parallel = intent["routing"]["strategy"] == "parallel_packs"
    for contract in intent["routing"]["pack_contracts"]:
        pack_root = run_root / "packs" / contract["pack_id"] if parallel else run_root
        captures_path = pack_root / "03_verification/browser_capture_records.jsonl"
        captures = read_jsonl(captures_path)
        for capture in captures:
            capture["approach_plan_sha256"] = registry["registration"]["plan_sha256"]
        write_jsonl(captures_path, captures)
        capture_index = {capture["capture_id"]: capture for capture in captures}
        receipts_path = pack_root / "03_verification/verification_receipts.jsonl"
        receipts = read_jsonl(receipts_path)
        for receipt in receipts:
            for binding in receipt["capture_bindings"]:
                binding["record_sha256"] = canonical_sha256(capture_index[binding["capture_id"]])
        write_jsonl(receipts_path, receipts)
        _refresh_report_contracts(run_root, pack_root)


def _make_pack(run_root: Path, pack_root: Path, run_id: str, pack_id: str, modality: str) -> None:
    generated_at = datetime(2026, 7, 13, 1, 0, tzinfo=timezone.utc)
    checked_at = generated_at - timedelta(minutes=5)
    candidate_modalities = (
        ["image" if index % 2 == 0 else "video" for index in range(30)]
        if modality == "mixed"
        else [modality] * 30
    )
    intent = read_json(run_root / "00_intent/intent_brief.json")
    candidates = [
        _candidate(run_id, candidate_modality, index, pack_id, intent)
        for index, candidate_modality in enumerate(candidate_modalities)
    ]
    receipts = [_receipt(candidate, checked_at, pack_id) for candidate in candidates]
    comparison_set_sha256 = dedup_comparison_set_sha256(candidates)
    for receipt in receipts:
        receipt["dedup_check"]["comparison_set_sha256"] = comparison_set_sha256
    plan_sha256 = read_json(run_root / "01_orchestration/approach_registry.json")["registration"]["plan_sha256"]
    captures = [
        _capture_record(candidate, receipt, pack_id, plan_sha256)
        for candidate, receipt in zip(candidates, receipts)
    ]
    for receipt, capture in zip(receipts, captures):
        receipt["capture_bindings"] = [
            {
                "capture_id": capture["capture_id"],
                "record_sha256": canonical_sha256(capture),
                "purposes": ["access", "media", "object_match", "provenance"],
            }
        ]
    selected_ids = [item["candidate_id"] for item in candidates[:20]]
    rejected_ids = [item["candidate_id"] for item in candidates[20:]]
    shortlist = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "intent_id": "intent_fixture",
        "intent_version": "v2",
        "pack_id": pack_id,
        "modality": modality,
        "created_at": "2026-07-13T00:56:00Z",
        "qualified_candidate_count": 30,
        "candidate_ids": selected_ids + rejected_ids,
        "items": [
            {
                "candidate_id": item["candidate_id"],
                "verification_receipt_id": item["verification_receipt_id"],
                "qualification_status": "qualified",
                "freshness_status": "fresh",
                "access_status": "accessible",
                "media_status": "passed",
                "provenance_status": "passed",
                "dedup_status": "unique",
                "territory_id": item["diversity"]["territory_id"],
            }
            for item in candidates
        ],
        "partition": {"selected_candidate_ids": selected_ids, "rejected_candidate_ids": rejected_ids},
        "integrity_assertions": {
            "ids_unique": True,
            "partition_disjoint": True,
            "union_equals_shortlist": True,
            "all_receipts_fresh": True,
            "all_access_verified": True,
            "all_media_verified": True,
            "all_provenance_confirmed": True,
            "no_placeholder_or_dead": True,
            "finder_verifier_separated": True,
        },
    }
    selected = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "intent_id": "intent_fixture",
        "intent_version": "v2",
        "pack_id": pack_id,
        "created_at": "2026-07-13T00:58:01Z",
        "selected_candidate_count": 20,
        "items": [
            {
                "candidate_id": item["candidate_id"],
                "rank": index + 1,
                "verification_receipt_id": item["verification_receipt_id"],
                "territory_id": item["diversity"]["territory_id"],
                "why_fit": "Directly fits the frozen brief.",
                "decision_supported": "Supports art-direction selection.",
                "transferable_mechanism": "Transfer the composition and set-scale mechanism.",
                "do_not_copy": "Do not copy protected expression or unsupported claims.",
                "source_tags": [item["source"]["evidence_tier"]],
                "access_tags": [item["access_state"]["mode"]],
                "rights_tags": ["reference_only"],
                "diversity_contribution": f"Adds {item['diversity']['territory_id']}.",
            }
            for index, item in enumerate(candidates[:20])
        ],
        "curation_trace": {
            "relevance_curator_id": "curator_relevance",
            "diversity_curator_id": "curator_diversity",
            "root_synthesizer_id": "root",
            "relevance_review_ref": "04_selection/review/relevance.json",
            "diversity_review_ref": "04_selection/review/diversity.json",
            "resolution_ref": "04_selection/review/resolution.json"
        },
        "diversity_policy": {
            "broad_brief": True,
            "distinct_domains": 5,
            "distinct_source_families": 4,
            "territory_count": 5,
            "max_per_domain": 4,
            "max_per_campaign_or_creator": 1,
            "max_per_near_duplicate_group": 1,
            "waiver": None,
        },
        "integrity_assertions": {
            "selected_subset_of_shortlist": True,
            "candidate_ids_unique": True,
            "ranks_unique_and_complete": True,
            "all_receipts_fresh": True,
            "all_rights_assessed": True,
        },
    }
    rejected = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "intent_id": "intent_fixture",
        "intent_version": "v2",
        "pack_id": pack_id,
        "created_at": "2026-07-13T00:58:01Z",
        "rejected_candidate_count": 10,
        "items": [
            {
                "candidate_id": item["candidate_id"],
                "shortlist_rank": 21 + index,
                "verification_receipt_id": item["verification_receipt_id"],
                "qualified_before_selection": True,
                "dominance_dimension": "diversity_contribution",
                "dominance_reason": "A selected candidate contributes the same mechanism with stronger set coverage.",
                "stronger_candidate_class": "selected core anchor",
                "dominated_by_candidate_ids": [selected_ids[10 + index]],
                "score_tie_break": None,
                "reuse_condition": "Reopen if the selected source becomes unavailable.",
            }
            for index, item in enumerate(candidates[20:])
        ],
        "curation_trace": {
            "relevance_curator_id": "curator_relevance",
            "diversity_curator_id": "curator_diversity",
            "root_synthesizer_id": "root",
            "relevance_review_ref": "04_selection/review/relevance.json",
            "diversity_review_ref": "04_selection/review/diversity.json",
            "resolution_ref": "04_selection/review/resolution.json"
        },
        "integrity_assertions": {
            "rejected_subset_of_shortlist": True,
            "disjoint_from_selected": True,
            "union_with_selected_equals_shortlist": True,
            "candidate_ids_unique": True,
            "all_were_qualified": True,
            "all_have_dominance_reason": True,
        },
    }
    screened_candidates = [
        _screened_candidate(run_id, pack_id, modality, intent, approach_index, offset)
        for approach_index in range(4)
        for offset in range(3)
    ]
    write_jsonl(pack_root / "02_candidates/candidate_ledger.jsonl", candidates + screened_candidates)
    write_jsonl(pack_root / "03_verification/verification_receipts.jsonl", receipts)
    write_jsonl(pack_root / "03_verification/browser_capture_records.jsonl", captures)
    write_json(pack_root / "04_selection/shortlist_30.json", shortlist)
    write_json(pack_root / "04_selection/selected_20.json", selected)
    write_json(pack_root / "04_selection/rejected_10.json", rejected)
    before_intent = copy.deepcopy(read_json(run_root / "00_intent/intent_brief.json"))
    before_intent["intent_version"] = "v1"
    before_intent["scene_scale"] = "tabletop"
    write_json(run_root / "00_intent/intent_brief.v1.snapshot.json", before_intent)
    curation_input_hash = curation_input_sha256(intent, shortlist, candidates, receipts)
    relevance_review_path = pack_root / "04_selection/review/relevance.json"
    diversity_review_path = pack_root / "04_selection/review/diversity.json"
    write_json(
        relevance_review_path,
        {
            "schema_version": "1.0.0",
            "review_id": f"relevance_review_{pack_id}",
            "review_type": "relevance",
            "run_id": run_id,
            "intent_id": "intent_fixture",
            "intent_version": "v2",
            "pack_id": pack_id,
            "reviewer": "curator_relevance",
            "input_contract_sha256": curation_input_hash,
            "started_at": "2026-07-13T00:56:01Z",
            "completed_at": "2026-07-13T00:57:00Z",
            "counterpart_review_unseen": True,
            "finder_outputs_frozen": True,
            "verdict": "pass",
            "rationale": "All 30 qualified items were independently ordered against the frozen decision.",
            "ordered_candidate_ids": selected_ids + rejected_ids,
        },
    )
    write_json(
        diversity_review_path,
        {
            "schema_version": "1.0.0",
            "review_id": f"diversity_review_{pack_id}",
            "review_type": "diversity",
            "run_id": run_id,
            "intent_id": "intent_fixture",
            "intent_version": "v2",
            "pack_id": pack_id,
            "reviewer": "curator_diversity",
            "input_contract_sha256": curation_input_hash,
            "started_at": "2026-07-13T00:56:01Z",
            "completed_at": "2026-07-13T00:57:00Z",
            "counterpart_review_unseen": True,
            "finder_outputs_frozen": True,
            "verdict": "pass",
            "rationale": "Computed concentration matches the declared broad-brief policy.",
            "metrics": {
                "distinct_domains": 5,
                "distinct_source_families": 4,
                "territory_count": 5,
                "max_per_domain": 4,
                "max_per_campaign_or_creator": 1,
                "max_per_near_duplicate_group": 1,
            },
        },
    )
    write_json(
        pack_root / "04_selection/review/resolution.json",
        {
            "schema_version": "1.0.0",
            "resolution_id": f"resolution_review_{pack_id}",
            "run_id": run_id,
            "intent_id": "intent_fixture",
            "intent_version": "v2",
            "pack_id": pack_id,
            "synthesizer": "root",
            "input_contract_sha256": curation_input_hash,
            "relevance_review_ref": "04_selection/review/relevance.json",
            "relevance_review_sha256": hashlib.sha256(relevance_review_path.read_bytes()).hexdigest(),
            "diversity_review_ref": "04_selection/review/diversity.json",
            "diversity_review_sha256": hashlib.sha256(diversity_review_path.read_bytes()).hexdigest(),
            "started_at": "2026-07-13T00:57:01Z",
            "completed_at": "2026-07-13T00:58:00Z",
            "decision": "accepted_20_10_partition",
            "rationale": "The final partition reconciles relevance and diversity reviews.",
            "selected": selected_ids,
            "rejected": rejected_ids,
        },
    )
    (pack_root / "06_output").mkdir(parents=True, exist_ok=True)
    (pack_root / "06_output/reference_board.html").write_text(build_gallery(pack_root), encoding="utf-8")
    audit_checks = [
        "soft_404", "media_truth", "object_match", "provenance", "deduplication",
        "diversity", "rights_separation", "agent_independence", "freshness",
    ]
    write_json(
        pack_root / "07_audit/adversarial_audit_results.json",
        {
            "run_id": run_id,
            "intent_id": "intent_fixture",
            "intent_version": "v2",
            "pack_id": pack_id,
            "auditor_id": "auditor_red",
            "candidate_ids": selected_ids + rejected_ids,
            "checks": [
                {
                    "check": check,
                    "outcome": "pass",
                    "affected_candidate_ids": [],
                    "evidence_refs": ["03_verification/verification_receipts.jsonl"],
                    "rationale": f"Fixture adversarial replay passed {check}.",
                }
                for check in audit_checks
            ],
            "overall_outcome": "pass",
        },
    )
    registry = read_json(run_root / "01_orchestration/approach_registry.json")
    pack_approaches = [item for item in registry["approaches"] if item["pack_id"] == pack_id]
    write_jsonl(
        pack_root / "05_feedback/feedback_ledger.jsonl",
        [
            _feedback(
                run_id,
                pack_id,
                [item["candidate_id"] for item in candidates + screened_candidates],
                [item["approach_id"] for item in pack_approaches],
                [query["query_id"] for item in pack_approaches for query in item["queries"]],
                _feedback_completion_bindings(run_root, pack_root),
            )
        ],
    )

    paths = _artifact_paths(run_root, pack_root)
    artifact_contract = []
    schema_map = {
        "intent_brief": "intent_brief.schema.json",
        "approach_registry": "approach_registry.schema.json",
        "candidate_ledger": "candidate_item.schema.json",
        "verification_receipts": "verification_receipt.schema.json",
        "browser_capture_records": "browser_capture_record.schema.json",
        "shortlist_30": "shortlist_30.schema.json",
        "selected_20": "selected_20.schema.json",
        "rejected_10": "rejected_10.schema.json",
        "feedback_ledger": "feedback_event.schema.json",
        "reference_board": None,
    }
    for artifact_type, path in paths.items():
        artifact_contract.append(
            {
                "artifact_type": artifact_type,
                "path": contract_utils.canonical_relative_path(path, run_root),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "schema_id": schema_map[artifact_type],
            }
        )
    agent_ids = {item["agent_trace"]["finder_agent_id"] for item in candidates}
    capture_operator_ids = {item["operator_agent_id"] for item in captures}
    verifier_ids = {item["verifier"]["verifier_agent_id"] for item in receipts}
    report = {
        "schema_version": "1.2.0",
        "report_id": f"verification_report_{pack_id}",
        "run_id": run_id,
        "intent_id": "intent_fixture",
        "intent_version": "v2",
        "pack_id": pack_id,
        "run_mode": "test_fixture",
        "acceptance_class": "fixture_contract_pass",
        "production_contract_eligible": False,
        "production_deliverable": False,
        "trust_boundary": {
            "cryptographic_authenticity": "not_attested",
            "browser_action_attested": False,
            "claim_scope": "contract_eligible_only",
            "rights_granted": False,
            "statement": REPORT_TRUST_STATEMENT,
        },
        "generated_at": _iso(generated_at),
        "delivery_reference_time": _iso(generated_at),
        "freshness_window_minutes": 30,
        "final_status": "pass",
        "artifact_contract": artifact_contract,
        "referenced_evidence_contract": _referenced_evidence_contract(run_root, pack_root),
        "counts": {"qualified": 30, "selected": 20, "rejected": 10},
        "final_reverification": [
            {
                "candidate_id": item["candidate_id"],
                "receipt_id": item["receipt_id"],
                "checked_at": item["checked_at"],
                "freshness_status": "fresh",
                "access_status": "accessible",
                "media_status": "passed",
                "provenance_status": "passed",
            }
            for item in receipts
        ],
        "gates": {
            "intent_frozen": True,
            "route_contract_valid": True,
            "exactly_30_qualified": True,
            "exactly_20_selected": True,
            "exactly_10_rejected": True,
            "partition_disjoint": True,
            "partition_union_exact": True,
            "access_verified": True,
            "media_verified": True,
            "object_match_verified": True,
            "provenance_confirmed": True,
            "no_placeholder_or_dead": True,
            "dedup_passed": True,
            "diversity_passed_or_waived": True,
            "finder_verifier_separated": True,
            "rights_assessed": True,
            "receipts_within_window": True,
            "final_reverification_passed": True,
            "feedback_chain_valid": True,
        },
        "diversity": {
            "broad_brief": True,
            "distinct_domains": 5,
            "distinct_source_families": 4,
            "territory_count": 5,
            "max_per_domain": 4,
            "max_per_campaign_or_creator": 1,
            "max_per_near_duplicate_group": 1,
            "waiver": None,
            "status": "passed",
        },
        "agent_separation": {
            "finder_agent_ids": sorted(agent_ids),
            "capture_operator_agent_ids": sorted(capture_operator_ids),
            "verifier_agent_ids": sorted(verifier_ids),
            "relevance_curator_agent_id": "curator_relevance",
            "diversity_curator_agent_id": "curator_diversity",
            "root_synthesizer_agent_id": "root",
            "auditor_agent_id": "auditor_red",
            "no_self_approval": True,
            "decision_roles_disjoint": True,
            "auditor_independent": True,
        },
        "adversarial_audit": {
            "auditor_id": "auditor_red",
            "independent_from": sorted(agent_ids | capture_operator_ids | verifier_ids | {"curator_relevance", "curator_diversity", "root"}),
            "completed_at": "2026-07-13T00:59:00Z",
            "checks": [
                "soft_404",
                "media_truth",
                "object_match",
                "provenance",
                "deduplication",
                "diversity",
                "rights_separation",
                "agent_independence",
                "freshness"
            ],
            "candidate_ids": selected_ids + rejected_ids,
            "outcome": "pass",
            "evidence_refs": [
                "03_verification/verification_receipts.jsonl",
                "07_audit/adversarial_audit_results.json"
            ]
        },
        "rights_summary": {
            "assessed_count": 30,
            "session_bound_count": 0,
            "shareable_without_session_count": 30,
            "commercial_reuse_unknown_or_restricted_count": 30,
            "downloaded_video_count": 0,
        },
        "freshness_summary": {
            "receipt_window_minutes": 30,
            "oldest_checked_at": _iso(checked_at),
            "newest_checked_at": _iso(checked_at),
            "fresh_count": 30,
            "stale_count": 0,
        },
        "failures": [],
    }
    write_json(pack_root / "06_output/verification_report.json", report)


def make_valid_run(root: Path, modality: str = "image") -> None:
    run_id = "fixture_run"
    pack_id = f"{modality}_pack"
    contract = {"pack_id": pack_id, "modality": modality, "qualified_target": 30, "selected_target": 20}
    write_json(root / "00_intent/intent_brief.json", _make_intent(run_id, modality, [contract], "single_modality"))
    write_json(root / "01_orchestration/approach_registry.json", _make_registry(run_id, [contract]))
    _make_pack(root, root, run_id, pack_id, modality)


def make_parallel_run(root: Path) -> None:
    run_id = "parallel_fixture_run"
    contracts = [
        {"pack_id": "image_pack", "modality": "image", "qualified_target": 30, "selected_target": 20},
        {"pack_id": "video_pack", "modality": "video", "qualified_target": 30, "selected_target": 20},
    ]
    write_json(root / "00_intent/intent_brief.json", _make_intent(run_id, "both", contracts, "parallel_packs"))
    write_json(root / "01_orchestration/approach_registry.json", _make_registry(run_id, contracts))
    for contract in contracts:
        _make_pack(root, root / "packs" / contract["pack_id"], run_id, contract["pack_id"], contract["modality"])


def make_unified_run(root: Path) -> None:
    run_id = "unified_fixture_run"
    contract = {"pack_id": "mixed_pack", "modality": "mixed", "qualified_target": 30, "selected_target": 20}
    write_json(root / "00_intent/intent_brief.json", _make_intent(run_id, "both", [contract], "unified_territory"))
    write_json(root / "01_orchestration/approach_registry.json", _make_registry(run_id, [contract]))
    _make_pack(root, root, run_id, "mixed_pack", "mixed")


def _convert_contract_simulation(root: Path, mode: str) -> None:
    """Exercise non-fixture mode contracts without claiming real browser attestation."""
    if mode not in {"retrospective_smoke", "production_live"}:
        raise AssertionError(f"unsupported contract simulation mode: {mode}")
    _rewrite_json(root / "00_intent/intent_brief.json", lambda value: value.update({"run_mode": mode}))
    _rewrite_json(
        root / "00_intent/intent_brief.v1.snapshot.json",
        lambda value: value.update({"run_mode": mode}),
    )

    registry_path = root / "01_orchestration/approach_registry.json"
    registry = read_json(registry_path)
    registry["registration"]["kind"] = (
        "retrospective_reconstruction" if mode == "retrospective_smoke" else "preregistered"
    )
    registry["registration"]["plan_sha256"] = approach_plan_sha256(registry)
    write_json(registry_path, registry)

    source_path = root / "03_verification/source_records.jsonl"
    source_rows = [
        {
            "source_record_id": f"contract_simulation_{index:02d}",
            "contract_simulation": True,
            "browser_action_attested": False,
            "note": "Deterministic contract exercise only; this is not evidence that a browser action occurred.",
        }
        for index in range(30)
    ]
    write_jsonl(source_path, source_rows)
    source_sha = hashlib.sha256(source_path.read_bytes()).hexdigest()

    captures_path = root / "03_verification/browser_capture_records.jsonl"
    captures = read_jsonl(captures_path)
    origin = "retrospective_import" if mode == "retrospective_smoke" else "direct_browser_observation"
    for index, capture in enumerate(captures):
        capture.update(
            {
                "record_origin": origin,
                "approach_plan_sha256": registry["registration"]["plan_sha256"],
                "source_record": {
                    "path": "03_verification/source_records.jsonl",
                    "sha256": source_sha,
                    "json_pointer": f"/{index}",
                },
            }
        )
    write_jsonl(captures_path, captures)

    capture_index = {capture["capture_id"]: capture for capture in captures}
    receipts_path = root / "03_verification/verification_receipts.jsonl"
    receipts = read_jsonl(receipts_path)
    for receipt in receipts:
        for binding in receipt["capture_bindings"]:
            binding["record_sha256"] = canonical_sha256(capture_index[binding["capture_id"]])
    write_jsonl(receipts_path, receipts)

    report_path = root / "06_output/verification_report.json"
    report = read_json(report_path)
    report.update(
        {
            "run_mode": mode,
            "acceptance_class": (
                "retrospective_smoke_pass" if mode == "retrospective_smoke" else "production_contract_eligible"
            ),
            "production_contract_eligible": mode == "production_live",
            "production_deliverable": False,
        }
    )
    write_json(report_path, report)
    _refresh_report_contracts(root, root)


def _rewrite_json(path: Path, mutation) -> None:
    value = read_json(path)
    mutation(value)
    write_json(path, value)


def _rewrite_jsonl(path: Path, mutation) -> None:
    value = read_jsonl(path)
    mutation(value)
    write_jsonl(path, value)


def mutate(root: Path, mutation: str) -> None:
    if mutation == "drop_selected_item":
        _rewrite_json(root / "04_selection/selected_20.json", lambda value: value["items"].pop())
    elif mutation == "drop_receipt":
        _rewrite_jsonl(root / "03_verification/verification_receipts.jsonl", lambda value: value.pop())
    elif mutation == "stale_receipt":
        def change(rows):
            rows[0]["checked_at"] = "2026-07-13T00:00:00Z"
            rows[0]["freshness"]["expires_at"] = "2026-07-13T00:30:00Z"
        _rewrite_jsonl(root / "03_verification/verification_receipts.jsonl", change)
    elif mutation == "video_without_playback":
        def change_candidates(rows):
            rows[0]["modality"] = "video"
            rows[0]["object"]["object_type"] = "specific_video_work"
        def change_receipts(rows):
            rows[0]["modality"] = "video"
            rows[0]["media_check"] = {
                "status": "passed",
                "kind": "video",
                "image_render": None,
                "video_playback": {"player_present": True, "playback_started": False, "observed_progress_seconds": 0, "duration_seconds": 30, "specific_work_matched": True},
            }
        _rewrite_jsonl(root / "02_candidates/candidate_ledger.jsonl", change_candidates)
        _rewrite_jsonl(root / "03_verification/verification_receipts.jsonl", change_receipts)
    elif mutation == "discovery_only_provenance":
        def change(rows):
            rows[0]["provenance_check"]["source_signal"] = "discovery_only"
        _rewrite_jsonl(root / "03_verification/verification_receipts.jsonl", change)
    elif mutation == "duplicate_url":
        def change(rows):
            rows[1]["object"]["canonical_url"] = rows[0]["object"]["canonical_url"]
            rows[1]["dedup"]["canonical_url_key"] = rows[0]["dedup"]["canonical_url_key"]
        _rewrite_jsonl(root / "02_candidates/candidate_ledger.jsonl", change)
    elif mutation == "collapse_diversity":
        def change(rows):
            for row in rows[:20]:
                row["source"]["domain"] = "one.example"
                row["source"]["source_family_id"] = "one_family"
                row["diversity"]["territory_id"] = "one_territory"
        _rewrite_jsonl(root / "02_candidates/candidate_ledger.jsonl", change)
    elif mutation == "finder_is_verifier":
        def change(rows):
            rows[0]["verifier"]["verifier_agent_id"] = rows[0]["verifier"]["finder_agent_id"]
        _rewrite_jsonl(root / "03_verification/verification_receipts.jsonl", change)
    elif mutation == "audit_fail":
        def change(value):
            value["agent_separation"]["auditor_agent_id"] = value["agent_separation"]["relevance_curator_agent_id"]
            value["agent_separation"]["auditor_independent"] = False
        _rewrite_json(root / "06_output/verification_report.json", change)
    elif mutation == "feedback_same_version":
        def change(rows):
            rows[0]["intent_version_after"] = rows[0]["intent_version_before"]
        _rewrite_jsonl(root / "05_feedback/feedback_ledger.jsonl", change)
    elif mutation == "remove_rights_dimension":
        def change(rows):
            rows[0]["rights_scope"].pop("commercial_reuse")
        _rewrite_jsonl(root / "02_candidates/candidate_ledger.jsonl", change)
    elif mutation == "http_precheck_receipt":
        def change(rows):
            rows[0]["verifier"]["verification_surface"] = "http"
        _rewrite_jsonl(root / "03_verification/verification_receipts.jsonl", change)
    elif mutation == "foreign_root_identity":
        def change(rows):
            for row in rows:
                row.update({"run_id": "foreign_run", "intent_id": "foreign_intent", "intent_version": "v1"})
        _rewrite_jsonl(root / "02_candidates/candidate_ledger.jsonl", change)
        _rewrite_jsonl(root / "03_verification/verification_receipts.jsonl", change)
    elif mutation == "unrelated_receipt_binding":
        def change(rows):
            rows[0]["source_id"] = "foreign_source"
            rows[0]["access_state"]["checked_url"] = "https://foreign.example/unrelated"
        _rewrite_jsonl(root / "03_verification/verification_receipts.jsonl", change)
    elif mutation == "foreign_asset_evidence":
        def change(rows):
            rows[0]["media_check"]["image_render"]["asset_locator"] = "foreign-asset"
            rows[0]["evidence"] = [
                item if item["kind"] == "url" else {**item, "locator": "foreign-asset"}
                for item in rows[0]["evidence"]
            ]
        _rewrite_jsonl(root / "03_verification/verification_receipts.jsonl", change)
    elif mutation == "empty_passed_provenance":
        def change_candidates(rows):
            rows[0]["provenance_check"]["accountable_url"] = None
            rows[0]["provenance_check"]["accountable_owner"] = None
        def change_receipts(rows):
            rows[0]["provenance_check"]["accountable_url"] = None
            rows[0]["provenance_check"]["accountable_owner"] = None
        _rewrite_jsonl(root / "02_candidates/candidate_ledger.jsonl", change_candidates)
        _rewrite_jsonl(root / "03_verification/verification_receipts.jsonl", change_receipts)
    elif mutation == "accessible_hard_404":
        def change(rows):
            rows[0]["access_state"]["http_status"] = 404
        _rewrite_jsonl(root / "02_candidates/candidate_ledger.jsonl", change)
        _rewrite_jsonl(root / "03_verification/verification_receipts.jsonl", change)
    elif mutation == "forbidden_access_mode":
        def change(value):
            value["access_policy"]["allow_public_web"] = False
        _rewrite_json(root / "00_intent/intent_brief.json", change)
    elif mutation == "feedback_pending":
        def change(rows):
            rows[0]["completion_evidence"]["status"] = "pending"
        _rewrite_jsonl(root / "05_feedback/feedback_ledger.jsonl", change)
    elif mutation == "approaches_planned":
        def change(value):
            for approach in value["approaches"]:
                approach["status"] = "planned"
        _rewrite_json(root / "01_orchestration/approach_registry.json", change)
    elif mutation == "missing_audit_evidence":
        def change(value):
            value["adversarial_audit"]["evidence_refs"] = ["does/not/exist.json"]
        _rewrite_json(root / "06_output/verification_report.json", change)
    elif mutation == "blank_reference_board":
        (root / "06_output/reference_board.html").write_text("", encoding="utf-8")
    elif mutation == "rights_summary_mismatch":
        def change(value):
            value["rights_summary"]["shareable_without_session_count"] = 0
        _rewrite_json(root / "06_output/verification_report.json", change)
    elif mutation == "unknown_source_identity":
        def change_candidates(rows):
            rows[0]["source"]["source_id"] = "invented_source"
        def change_receipts(rows):
            rows[0]["source_id"] = "invented_source"
        _rewrite_jsonl(root / "02_candidates/candidate_ledger.jsonl", change_candidates)
        _rewrite_jsonl(root / "03_verification/verification_receipts.jsonl", change_receipts)
    elif mutation == "source_domain_url_mismatch":
        def change(rows):
            rows[0]["source"]["domain"] = "spoofed.example"
            rows[0]["source"]["source_id"] = "runtime:spoofed.example"
        _rewrite_jsonl(root / "02_candidates/candidate_ledger.jsonl", change)
    elif mutation == "javascript_canonical_url":
        def change(rows):
            rows[0]["object"]["canonical_url"] = "javascript:alert(1)"
        _rewrite_jsonl(root / "02_candidates/candidate_ledger.jsonl", change)
    elif mutation == "feedback_missing_invalidated_ref":
        def change(rows):
            rows[0]["invalidated_artifact_refs"][0]["ref"] = "00_intent/missing-v1.json"
        _rewrite_jsonl(root / "05_feedback/feedback_ledger.jsonl", change)
    elif mutation == "empty_relevance_review":
        write_json(root / "04_selection/review/relevance.json", {"run_id": "fixture_run", "reviewer": "curator_relevance"})
    elif mutation == "audit_artifact_self_assertion":
        def change(value):
            value["overall_outcome"] = "fail"
            value["checks"][0]["outcome"] = "fail"
            value["checks"][0]["rationale"] = ""
        _rewrite_json(root / "07_audit/adversarial_audit_results.json", change)
    elif mutation == "malformed_pack_contracts":
        def change(value):
            value["routing"]["pack_contracts"] = {"pack_id": "image_pack"}
        _rewrite_json(root / "00_intent/intent_brief.json", change)
    elif mutation == "foreign_review_identity":
        for relative in (
            "04_selection/review/relevance.json",
            "04_selection/review/diversity.json",
            "04_selection/review/resolution.json",
        ):
            _rewrite_json(
                root / relative,
                lambda value: value.update({
                    "intent_id": "foreign_intent", "intent_version": "v1", "pack_id": "foreign_pack"
                }),
            )
    elif mutation == "feedback_wrong_completion_artifacts":
        def change_feedback(rows):
            rows[0]["completion_evidence"]["artifact_bindings"] = [
                next(
                    item for item in rows[0]["completion_evidence"]["artifact_bindings"]
                    if item["artifact_type"] == "relevance_review"
                )
            ]
        _rewrite_jsonl(root / "05_feedback/feedback_ledger.jsonl", change_feedback)
        report = read_json(root / "06_output/verification_report.json")
        feedback_hash = hashlib.sha256((root / "05_feedback/feedback_ledger.jsonl").read_bytes()).hexdigest()
        for item in report["artifact_contract"]:
            if item["artifact_type"] == "feedback_ledger":
                item["sha256"] = feedback_hash
        write_json(root / "06_output/verification_report.json", report)
    elif mutation == "subdomain_diversity_spoof":
        candidates = read_jsonl(root / "02_candidates/candidate_ledger.jsonl")
        receipts = read_jsonl(root / "03_verification/verification_receipts.jsonl")
        for index, (candidate, receipt) in enumerate(zip(candidates, receipts)):
            host = f"s{index}.one-publisher.example"
            url = f"https://{host}/work/{candidate['candidate_id']}"
            source_id = f"runtime:{host}"
            candidate["object"]["canonical_url"] = url
            candidate["source"].update({"source_id": source_id, "domain": host, "discovered_url": url})
            candidate["provenance_check"]["accountable_url"] = url
            candidate["access_state"]["checked_url"] = url
            candidate["dedup"]["canonical_url_key"] = url
            candidate["dedup"]["stable_id_key"] = f"{source_id}:{candidate['object']['stable_id']}"
            receipt["source_id"] = source_id
            receipt["access_state"]["checked_url"] = url
            receipt["provenance_check"]["accountable_url"] = url
            receipt["evidence"] = [
                {**item, "locator": url} if item["kind"] == "url" else item
                for item in receipt["evidence"]
            ]
        write_jsonl(root / "02_candidates/candidate_ledger.jsonl", candidates)
        write_jsonl(root / "03_verification/verification_receipts.jsonl", receipts)
    elif mutation == "feedback_false_delta":
        def change(rows):
            rows[0]["constraint_delta"][0].update({"before": "wrong_before", "after": "wrong_after"})
        _rewrite_jsonl(root / "05_feedback/feedback_ledger.jsonl", change)
    elif mutation == "feedback_mislabeled_snapshot":
        def change(rows):
            rows[0]["invalidated_artifact_refs"][0]["artifact_type"] = "verification_report"
        _rewrite_jsonl(root / "05_feedback/feedback_ledger.jsonl", change)
    elif mutation == "registered_source_wrong_modality":
        candidates = read_jsonl(root / "02_candidates/candidate_ledger.jsonl")
        receipts = read_jsonl(root / "03_verification/verification_receipts.jsonl")
        candidate, receipt = candidates[0], receipts[0]
        url = "https://vimeo.com/work/fixture-image"
        candidate["object"]["canonical_url"] = url
        candidate["source"].update({
            "source_id": "vimeo_staff_picks",
            "source_family_id": "curated_film_culture",
            "domain": "vimeo.com",
            "discovered_url": url,
        })
        candidate["provenance_check"]["accountable_url"] = url
        candidate["access_state"]["checked_url"] = url
        candidate["dedup"]["canonical_url_key"] = url
        candidate["dedup"]["stable_id_key"] = f"vimeo_staff_picks:{candidate['object']['stable_id']}"
        receipt["source_id"] = "vimeo_staff_picks"
        receipt["access_state"]["checked_url"] = url
        receipt["provenance_check"]["accountable_url"] = url
        receipt["evidence"] = [
            {**item, "locator": url} if item["kind"] == "url" else item
            for item in receipt["evidence"]
        ]
        write_jsonl(root / "02_candidates/candidate_ledger.jsonl", candidates)
        write_jsonl(root / "03_verification/verification_receipts.jsonl", receipts)
    elif mutation == "feedback_two_event_false_bridge":
        intent_path = root / "00_intent/intent_brief.json"
        intent_v2 = read_json(intent_path)
        write_json(root / "00_intent/intent_brief.v2.snapshot.json", intent_v2)
        intent_v3 = copy.deepcopy(intent_v2)
        intent_v3.update({"intent_version": "v3", "scene_scale": "architecture"})
        write_json(intent_path, intent_v3)
        _rewrite_json(root / "01_orchestration/approach_registry.json", lambda value: value.update({"intent_version": "v3"}))
        for relative in ("02_candidates/candidate_ledger.jsonl", "03_verification/verification_receipts.jsonl"):
            _rewrite_jsonl(root / relative, lambda rows: [row.update({"intent_version": "v3"}) for row in rows])
        for relative in ("04_selection/shortlist_30.json", "04_selection/selected_20.json", "04_selection/rejected_10.json"):
            _rewrite_json(root / relative, lambda value: value.update({"intent_version": "v3"}))
        for relative in (
            "04_selection/review/relevance.json",
            "04_selection/review/diversity.json",
            "04_selection/review/resolution.json",
        ):
            _rewrite_json(root / relative, lambda value: value.update({"intent_version": "v3"}))
        _rewrite_json(root / "07_audit/adversarial_audit_results.json", lambda value: value.update({"intent_version": "v3"}))
        events = read_jsonl(root / "05_feedback/feedback_ledger.jsonl")
        events[0]["constraint_delta"][0]["after"] = "macro_product"
        second = copy.deepcopy(events[0])
        second.update({
            "feedback_id": "feedback_second",
            "timestamp": "2026-07-13T00:30:00Z",
            "supersedes": events[0]["feedback_id"],
            "intent_version_before": "v2",
            "intent_version_after": "v3",
        })
        second["constraint_delta"] = [{
            "target_artifact_type": "intent_brief",
            "before_ref": "00_intent/intent_brief.v2.snapshot.json",
            "after_ref": "00_intent/intent_brief.json",
            "operation": "replace",
            "path": "/scene_scale",
            "before_exists": True,
            "after_exists": True,
            "before": "large_scale_set",
            "after": "architecture",
            "reason": "Second correction changes the scene scale again.",
        }]
        second["invalidated_artifact_refs"] = [{
            "artifact_type": "intent_brief",
            "ref": "00_intent/intent_brief.v2.snapshot.json",
            "reason": "The v2 scene scale was superseded.",
        }]
        second["agent_trace"]["applied_at"] = "2026-07-13T00:31:00Z"
        write_jsonl(root / "05_feedback/feedback_ledger.jsonl", [events[0], second])
        report_path = root / "06_output/verification_report.json"
        report = read_json(report_path)
        report["intent_version"] = "v3"
        write_json(report_path, report)
        _refresh_report_contracts(root, root, refresh_feedback=False)
    elif mutation == "missing_candidate_approach":
        def change(rows):
            rows[0]["agent_trace"].update({"approach_id": "missing_approach", "query_id": "missing_query"})
        _rewrite_jsonl(root / "02_candidates/candidate_ledger.jsonl", change)
    elif mutation == "missing_receipt_duplicate_group":
        def change_candidates(rows):
            rows[1]["object"]["canonical_url"] = rows[0]["object"]["canonical_url"]
            rows[1]["dedup"]["canonical_url_key"] = rows[0]["dedup"]["canonical_url_key"]
        def change_receipts(rows):
            rows.pop(0)
        _rewrite_jsonl(root / "02_candidates/candidate_ledger.jsonl", change_candidates)
        _rewrite_jsonl(root / "03_verification/verification_receipts.jsonl", change_receipts)
    elif mutation == "referenced_evidence_missing":
        _rewrite_json(
            root / "06_output/verification_report.json",
            lambda value: value["referenced_evidence_contract"].pop(),
        )
    elif mutation == "core_artifact_contract_duplicate":
        _rewrite_json(
            root / "06_output/verification_report.json",
            lambda value: value["artifact_contract"].append(
                copy.deepcopy(value["artifact_contract"][0])
            ),
        )
    elif mutation == "core_artifact_schema_id_drift":
        _rewrite_json(
            root / "06_output/verification_report.json",
            lambda value: value["artifact_contract"][0].update(
                {"schema_id": "wrong.schema.json"}
            ),
        )
    elif mutation == "core_artifact_noncanonical_path":
        _rewrite_json(
            root / "06_output/verification_report.json",
            lambda value: value["artifact_contract"][0].update(
                {"path": "00_intent/../00_intent/intent_brief.json"}
            ),
        )
    elif mutation == "referenced_evidence_duplicate":
        _rewrite_json(
            root / "06_output/verification_report.json",
            lambda value: value["referenced_evidence_contract"].append(
                copy.deepcopy(value["referenced_evidence_contract"][0])
            ),
        )
    elif mutation == "referenced_evidence_hash_mismatch":
        _rewrite_json(
            root / "06_output/verification_report.json",
            lambda value: value["referenced_evidence_contract"][0].update({"sha256": "0" * 64}),
        )
    elif mutation == "referenced_evidence_purpose_mismatch":
        _rewrite_json(
            root / "06_output/verification_report.json",
            lambda value: value["referenced_evidence_contract"][0].update(
                {"purposes": ["diversity_waiver_evidence"]}
            ),
        )
    elif mutation == "feedback_unknown_ids":
        def change_feedback_ids(rows):
            rows[0].update(
                {
                    "invalidated_candidate_ids": ["candidate_missing"],
                    "invalidated_approach_ids": ["approach_missing"],
                    "invalidated_query_ids": ["query_missing"],
                }
            )
        _rewrite_jsonl(root / "05_feedback/feedback_ledger.jsonl", change_feedback_ids)
        _refresh_report_contracts(root, root, refresh_feedback=False)
    elif mutation == "feedback_report_self_proof":
        _rewrite_jsonl(
            root / "05_feedback/feedback_ledger.jsonl",
            lambda rows: rows[0]["completion_evidence"].update(
                {"validator_ref": "06_output/verification_report.json"}
            ),
        )
    elif mutation == "capture_session_free_mismatch":
        captures_path = root / "03_verification/browser_capture_records.jsonl"
        captures = read_jsonl(captures_path)
        captures[0]["trust_boundary"]["session_free_access_observed"] = False
        write_jsonl(captures_path, captures)
        capture_index = {capture["capture_id"]: capture for capture in captures}
        receipts_path = root / "03_verification/verification_receipts.jsonl"
        receipts = read_jsonl(receipts_path)
        for binding in receipts[0]["capture_bindings"]:
            binding["record_sha256"] = canonical_sha256(capture_index[binding["capture_id"]])
        write_jsonl(receipts_path, receipts)
        _refresh_report_contracts(root, root)
    elif mutation == "report_trust_statement_drift":
        _rewrite_json(
            root / "06_output/verification_report.json",
            lambda value: value["trust_boundary"].update({"statement": "This altered statement overclaims trust."}),
        )
    else:
        raise AssertionError(f"unknown mutation {mutation}")


def assert_code(result: dict[str, Any], code: str, case_id: str) -> None:
    observed = {item["code"] for item in result["findings"]}
    if result["status"] != "FAIL" or code not in observed:
        raise AssertionError(f"{case_id}: expected {code}, got status={result['status']} codes={sorted(observed)}")


def test_validator_and_adversarial() -> None:
    blueprint = read_json(FIXTURES / "valid_run_blueprint.json")
    if blueprint["candidate_count"] != 30 or blueprint["selected_count"] != 20 or blueprint["rejected_count"] != 10:
        raise AssertionError("valid blueprint does not freeze 30/20/10")
    with tempfile.TemporaryDirectory() as temp:
        valid_root = Path(temp) / "valid"
        make_valid_run(valid_root)
        result = validate_run(valid_root)
        if result["status"] != "PASS":
            raise AssertionError(f"valid fixture failed: {json.dumps(result, ensure_ascii=False, indent=2)}")
        for case in read_json(FIXTURES / "adversarial_cases.json"):
            case_root = Path(temp) / case["case_id"]
            shutil.copytree(valid_root, case_root)
            mutate(case_root, case["mutation"])
            assert_code(validate_run(case_root), case["expected_code"], case["case_id"])
        initial_root = Path(temp) / "initial_no_feedback"
        shutil.copytree(valid_root, initial_root)
        _rewrite_json(initial_root / "00_intent/intent_brief.json", lambda value: value.update({"intent_version": "v1"}))
        _rewrite_json(initial_root / "01_orchestration/approach_registry.json", lambda value: value.update({"intent_version": "v1"}))
        initial_intent = read_json(initial_root / "00_intent/intent_brief.json")
        candidate_rows = read_jsonl(initial_root / "02_candidates/candidate_ledger.jsonl")
        for row in candidate_rows:
            row["intent_version"] = "v1"
            row["intent_alignment"]["intent_constraints_sha256"] = intent_constraints_sha256(initial_intent)
        write_jsonl(initial_root / "02_candidates/candidate_ledger.jsonl", candidate_rows)
        _rewrite_jsonl(
            initial_root / "03_verification/verification_receipts.jsonl",
            lambda rows: [row.update({"intent_version": "v1"}) for row in rows],
        )
        registry = read_json(initial_root / "01_orchestration/approach_registry.json")
        registry["registration"]["plan_sha256"] = approach_plan_sha256(registry)
        write_json(initial_root / "01_orchestration/approach_registry.json", registry)
        captures = read_jsonl(initial_root / "03_verification/browser_capture_records.jsonl")
        for capture in captures:
            capture.update({"intent_version": "v1", "approach_plan_sha256": registry["registration"]["plan_sha256"]})
        write_jsonl(initial_root / "03_verification/browser_capture_records.jsonl", captures)
        capture_by_id = {item["capture_id"]: item for item in captures}
        receipts = read_jsonl(initial_root / "03_verification/verification_receipts.jsonl")
        for receipt in receipts:
            for binding in receipt["capture_bindings"]:
                binding["record_sha256"] = canonical_sha256(capture_by_id[binding["capture_id"]])
        write_jsonl(initial_root / "03_verification/verification_receipts.jsonl", receipts)
        for relative in ("04_selection/shortlist_30.json", "04_selection/selected_20.json", "04_selection/rejected_10.json"):
            _rewrite_json(initial_root / relative, lambda value: value.update({"intent_version": "v1"}))
        for relative in (
            "04_selection/review/relevance.json",
            "04_selection/review/diversity.json",
            "04_selection/review/resolution.json",
        ):
            _rewrite_json(initial_root / relative, lambda value: value.update({"intent_version": "v1"}))
        _rewrite_json(
            initial_root / "07_audit/adversarial_audit_results.json",
            lambda value: value.update({"intent_version": "v1"}),
        )
        write_jsonl(initial_root / "05_feedback/feedback_ledger.jsonl", [])
        report_path = initial_root / "06_output/verification_report.json"
        report = read_json(report_path)
        report["intent_version"] = "v1"
        write_json(report_path, report)
        _refresh_report_contracts(initial_root, initial_root)
        initial_result = validate_run(initial_root)
        if initial_result["status"] != "PASS":
            raise AssertionError(f"honest initial v1/no-feedback run failed: {json.dumps(initial_result, ensure_ascii=False, indent=2)}")

        waiver_root = Path(temp) / "aligned_waiver"
        shutil.copytree(valid_root, waiver_root)
        _rewrite_json(
            waiver_root / "00_intent/intent_brief.json",
            lambda value: value["diversity_requirements"].update({"min_domains": 6}),
        )
        _rewrite_json(
            waiver_root / "00_intent/intent_brief.v1.snapshot.json",
            lambda value: value["diversity_requirements"].update({"min_domains": 6}),
        )
        waiver = {
            "constraints": ["min_domains"],
            "reason": "The qualified decision set has five accountable domains; a sixth would reduce relevance.",
            "evidence": ["04_selection/review/diversity.json"],
            "remaining_risk": "One fewer independent domain than the broad-brief default.",
            "approved_by": "curator_diversity",
        }
        _rewrite_json(
            waiver_root / "04_selection/selected_20.json",
            lambda value: value["diversity_policy"].update({"waiver": waiver}),
        )
        waiver_report_path = waiver_root / "06_output/verification_report.json"
        waiver_report = read_json(waiver_report_path)
        waiver_report["diversity"].update({"waiver": waiver, "status": "waived"})
        write_json(waiver_report_path, waiver_report)
        _refresh_report_contracts(waiver_root, waiver_root)
        waiver_result = validate_run(waiver_root)
        if waiver_result["status"] != "PASS":
            raise AssertionError(f"aligned diversity waiver failed: {json.dumps(waiver_result, ensure_ascii=False, indent=2)}")

        narrow_bypass_root = Path(temp) / "narrow_without_waiver"
        shutil.copytree(valid_root, narrow_bypass_root)
        _rewrite_json(
            narrow_bypass_root / "00_intent/intent_brief.json",
            lambda value: value["diversity_requirements"].update({"broad_brief": False, "min_domains": 6}),
        )
        narrow_report_path = narrow_bypass_root / "06_output/verification_report.json"
        narrow_report = read_json(narrow_report_path)
        narrow_paths = _artifact_paths(narrow_bypass_root, narrow_bypass_root)
        for item in narrow_report["artifact_contract"]:
            item["sha256"] = hashlib.sha256(narrow_paths[item["artifact_type"]].read_bytes()).hexdigest()
        write_json(narrow_report_path, narrow_report)
        assert_code(
            validate_run(narrow_bypass_root),
            "DIVERSITY-01",
            "narrow_brief_cannot_bypass_diversity_waiver",
        )

        multi_owner_root = Path(temp) / "multiple_session_owners"
        shutil.copytree(valid_root, multi_owner_root)
        _rewrite_json(
            multi_owner_root / "01_orchestration/approach_registry.json",
            lambda value: [item.update({"session_owner": index < 2}) for index, item in enumerate(value["agents"])],
        )
        multi_owner_report_path = multi_owner_root / "06_output/verification_report.json"
        multi_owner_report = read_json(multi_owner_report_path)
        multi_owner_paths = _artifact_paths(multi_owner_root, multi_owner_root)
        for item in multi_owner_report["artifact_contract"]:
            item["sha256"] = hashlib.sha256(multi_owner_paths[item["artifact_type"]].read_bytes()).hexdigest()
        write_json(multi_owner_report_path, multi_owner_report)
        assert_code(validate_run(multi_owner_root), "AGENT-01", "multiple_signed_session_owners")

        missing_operator_role_root = Path(temp) / "signed_without_operator_role"
        shutil.copytree(valid_root, missing_operator_role_root)
        _rewrite_json(
            missing_operator_role_root / "01_orchestration/approach_registry.json",
            lambda value: value["agents"][1].update({"session_owner": True}),
        )
        _rewrite_jsonl(
            missing_operator_role_root / "02_candidates/candidate_ledger.jsonl",
            lambda rows: [row["access_state"].update({"mode": "signed_chrome"}) for row in rows],
        )
        _rewrite_jsonl(
            missing_operator_role_root / "03_verification/verification_receipts.jsonl",
            lambda rows: [row["access_state"].update({"mode": "signed_chrome"}) for row in rows],
        )
        missing_role_report_path = missing_operator_role_root / "06_output/verification_report.json"
        missing_role_report = read_json(missing_role_report_path)
        missing_role_paths = _artifact_paths(missing_operator_role_root, missing_operator_role_root)
        for item in missing_role_report["artifact_contract"]:
            item["sha256"] = hashlib.sha256(missing_role_paths[item["artifact_type"]].read_bytes()).hexdigest()
        write_json(missing_role_report_path, missing_role_report)
        assert_code(
            validate_run(missing_operator_role_root),
            "AGENT-01",
            "signed_chrome_requires_authenticated_operator_role",
        )

        malformed_values = [[], {}, 1, None]
        for field in ("pack_id", "modality"):
            missing_root = Path(temp) / f"missing_{field}"
            make_parallel_run(missing_root)
            _rewrite_json(
                missing_root / "00_intent/intent_brief.json",
                lambda value, field=field: value["routing"]["pack_contracts"][0].pop(field),
            )
            assert_code(validate_run(missing_root), "ROUTE-02", f"missing_{field}")
            for index, malformed in enumerate(malformed_values):
                malformed_root = Path(temp) / f"malformed_{field}_{index}"
                make_parallel_run(malformed_root)
                _rewrite_json(
                    malformed_root / "00_intent/intent_brief.json",
                    lambda value, field=field, malformed=malformed: value["routing"]["pack_contracts"][0].update(
                        {field: malformed}
                    ),
                )
                assert_code(validate_run(malformed_root), "ROUTE-02", f"malformed_{field}_{index}")


def test_parallel_both() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "parallel"
        make_parallel_run(root)
        result = validate_run(root)
        if result["status"] != "PASS" or len(result["packs"]) != 2:
            raise AssertionError(f"parallel BOTH run failed: {json.dumps(result, ensure_ascii=False, indent=2)}")
        shutil.rmtree(root / "packs/video_pack")
        assert_code(validate_run(root), "ROUTE-02", "parallel_missing_video_pack")
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "unified"
        make_unified_run(root)
        result = validate_run(root)
        if result["status"] != "PASS":
            raise AssertionError(f"unified BOTH run failed: {json.dumps(result, ensure_ascii=False, indent=2)}")
        def break_quota(value):
            value["routing"]["unified_territory_quota"]["image_selected_target"] = 11
            value["routing"]["unified_territory_quota"]["video_selected_target"] = 9
        _rewrite_json(root / "00_intent/intent_brief.json", break_quota)
        assert_code(validate_run(root), "ROUTE-02", "unified_selected_quota_mismatch")


def test_full_ledger_and_pack_isolation() -> None:
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        valid_root = temp_root / "valid"
        make_valid_run(valid_root)

        def cloned(name: str) -> Path:
            root = temp_root / name
            shutil.copytree(valid_root, root)
            return root

        extra_quarantined = cloned("extra_quarantined_is_explicitly_allowed")
        rows = read_jsonl(extra_quarantined / "02_candidates/candidate_ledger.jsonl")
        extra = copy.deepcopy(rows[0])
        extra.update(
            {
                "candidate_id": "candidate_image_quarantined_extra",
                "status": "quarantined",
                "verification_receipt_id": None,
            }
        )
        extra["agent_trace"]["finder_decision"] = "screened_out"
        rows.append(extra)
        write_jsonl(extra_quarantined / "02_candidates/candidate_ledger.jsonl", rows)
        registry_path = extra_quarantined / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        approach = next(item for item in registry["approaches"] if item["approach_id"] == "image_pack_approach_0")
        approach["returned_count"] += 1
        approach["qualification_rate"] = round(approach["qualified_count"] / approach["returned_count"], 3)
        approach["failure_records"][0]["candidate_ids"].append(extra["candidate_id"])
        write_json(registry_path, registry)
        _refresh_report_contracts(extra_quarantined, extra_quarantined)
        result = validate_run(extra_quarantined)
        if result["status"] != "PASS":
            raise AssertionError(f"valid quarantined ledger row failed: {json.dumps(result, ensure_ascii=False, indent=2)}")

        extra_qualified = cloned("extra_31st_qualified_candidate")
        rows = read_jsonl(extra_qualified / "02_candidates/candidate_ledger.jsonl")
        extra = copy.deepcopy(rows[0])
        extra["candidate_id"] = "candidate_image_qualified_extra"
        extra["status"] = "qualified"
        rows.append(extra)
        write_jsonl(extra_qualified / "02_candidates/candidate_ledger.jsonl", rows)
        _refresh_report_contracts(extra_qualified, extra_qualified)
        assert_code(validate_run(extra_qualified), "POOL-01", "extra_31st_qualified_candidate")

        foreign_candidate = cloned("foreign_pack_candidate_anywhere_in_ledger")
        rows = read_jsonl(foreign_candidate / "02_candidates/candidate_ledger.jsonl")
        extra = copy.deepcopy(rows[0])
        extra.update(
            {
                "candidate_id": "candidate_image_foreign_pack",
                "pack_id": "foreign_pack",
                "status": "raw",
                "verification_receipt_id": None,
            }
        )
        extra["agent_trace"]["finder_decision"] = "screened_out"
        rows.append(extra)
        write_jsonl(foreign_candidate / "02_candidates/candidate_ledger.jsonl", rows)
        _refresh_report_contracts(foreign_candidate, foreign_candidate)
        assert_code(validate_run(foreign_candidate), "CANDIDATE-01", "foreign_pack_candidate_anywhere_in_ledger")

        orphan_capture = cloned("orphan_capture")
        captures = read_jsonl(orphan_capture / "03_verification/browser_capture_records.jsonl")
        extra_capture = copy.deepcopy(captures[0])
        extra_capture["capture_id"] = "capture_orphan"
        captures.append(extra_capture)
        write_jsonl(orphan_capture / "03_verification/browser_capture_records.jsonl", captures)
        _refresh_report_contracts(orphan_capture, orphan_capture)
        assert_code(validate_run(orphan_capture), "CAPTURE-01", "orphan_capture")

        orphan_receipt = cloned("orphan_receipt")
        receipts = read_jsonl(orphan_receipt / "03_verification/verification_receipts.jsonl")
        extra_receipt = copy.deepcopy(receipts[0])
        extra_receipt.update(
            {
                "receipt_id": "receipt_orphan",
                "candidate_id": "candidate_missing_from_ledger",
            }
        )
        receipts.append(extra_receipt)
        write_jsonl(orphan_receipt / "03_verification/verification_receipts.jsonl", receipts)
        _refresh_report_contracts(orphan_receipt, orphan_receipt)
        assert_code(validate_run(orphan_receipt), "VERIFY-01", "orphan_receipt")

    with tempfile.TemporaryDirectory() as temp:
        parallel_root = Path(temp) / "parallel"
        make_parallel_run(parallel_root)
        image_ledger = parallel_root / "packs/image_pack/02_candidates/candidate_ledger.jsonl"
        video_rows = read_jsonl(parallel_root / "packs/video_pack/02_candidates/candidate_ledger.jsonl")
        image_rows = read_jsonl(image_ledger)
        foreign = copy.deepcopy(video_rows[0])
        foreign.update({"status": "quarantined", "verification_receipt_id": None})
        foreign["agent_trace"]["finder_decision"] = "screened_out"
        image_rows.append(foreign)
        write_jsonl(image_ledger, image_rows)
        _refresh_report_contracts(parallel_root, parallel_root / "packs/image_pack")
        assert_code(validate_run(parallel_root), "CANDIDATE-01", "parallel_foreign_pack_row")

        isolated_root = Path(temp) / "approach_isolation"
        make_parallel_run(isolated_root)
        registry_path = isolated_root / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        video_approach = next(
            item for item in registry["approaches"] if item["approach_id"] == "video_pack_approach_0"
        )
        video_approach["pack_id"] = "image_pack"
        write_json(registry_path, registry)
        _refresh_approach_plan_bindings(isolated_root)
        assert_code(validate_run(isolated_root), "AGENT-01", "parallel_approach_pack_isolation")


def test_approach_accounting_and_failure_registry() -> None:
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        valid_root = temp_root / "valid"
        make_valid_run(valid_root)
        baseline_candidates = read_jsonl(valid_root / "02_candidates/candidate_ledger.jsonl")
        registry = read_json(valid_root / "01_orchestration/approach_registry.json")
        if len(baseline_candidates) != 42:
            raise AssertionError("fixture must preserve 30 final plus 12 failed returned candidates")
        for approach in registry["approaches"]:
            contributed = [
                item for item in baseline_candidates
                if item["agent_trace"]["approach_id"] == approach["approach_id"]
            ]
            final = [item for item in contributed if item["status"] in {"qualified", "selected", "rejected"}]
            if approach["returned_count"] != len(contributed) or approach["qualified_count"] != len(final):
                raise AssertionError(f"fixture approach accounting is not ledger-derived: {approach['approach_id']}")

        def cloned(name: str) -> Path:
            root = temp_root / name
            shutil.copytree(valid_root, root)
            return root

        inflated = cloned("inflated_self_reported_yield")
        registry_path = inflated / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        registry["approaches"][0].update(
            {"returned_count": 999, "qualified_count": 999, "qualification_rate": 1.0}
        )
        write_json(registry_path, registry)
        _refresh_report_contracts(inflated, inflated)
        assert_code(validate_run(inflated), "AGENT-01", "inflated_self_reported_yield")

        ungrounded = cloned("ungrounded_failure_record")
        registry_path = ungrounded / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        registry["approaches"][0]["failure_records"][0]["candidate_ids"] = []
        write_json(registry_path, registry)
        _refresh_report_contracts(ungrounded, ungrounded)
        assert_code(validate_run(ungrounded), "AGENT-01", "ungrounded_failure_record")

        foreign_failed_candidate = cloned("failure_record_crosses_approach")
        registry_path = foreign_failed_candidate / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        registry["approaches"][0]["failure_records"][0]["candidate_ids"][0] = (
            "candidate_image_pack_screened_1_0"
        )
        write_json(registry_path, registry)
        _refresh_report_contracts(foreign_failed_candidate, foreign_failed_candidate)
        assert_code(validate_run(foreign_failed_candidate), "AGENT-01", "failure_record_crosses_approach")

        wrong_query = cloned("failure_record_query_round_mismatch")
        registry_path = wrong_query / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        registry["approaches"][0]["failure_records"][0]["query_id"] = "image_pack_query_1"
        write_json(registry_path, registry)
        _refresh_report_contracts(wrong_query, wrong_query)
        assert_code(validate_run(wrong_query), "AGENT-01", "failure_record_query_round_mismatch")

        unrelated_registered_query = cloned("failure_record_uses_unrelated_registered_query")
        registry_path = unrelated_registered_query / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        approach = registry["approaches"][0]
        approach["queries"].append(
            {
                "query_id": "image_pack_query_0_unrelated",
                "query_text": "registered but unrelated query path",
                "locale": "en",
                "round": 1,
            }
        )
        approach["failure_records"][0]["query_id"] = "image_pack_query_0_unrelated"
        write_json(registry_path, registry)
        _refresh_approach_plan_bindings(unrelated_registered_query)
        assert_code(
            validate_run(unrelated_registered_query),
            "AGENT-01",
            "failure_record_uses_unrelated_registered_query",
        )

        unrelated_registered_source = cloned("failure_record_uses_unrelated_registered_source")
        registry_path = unrelated_registered_source / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        approach = registry["approaches"][0]
        approach["source_family_ids"].append("awards")
        approach["failure_records"][0]["source_family_id"] = "awards"
        write_json(registry_path, registry)
        _refresh_approach_plan_bindings(unrelated_registered_source)
        assert_code(
            validate_run(unrelated_registered_source),
            "AGENT-01",
            "failure_record_uses_unrelated_registered_source",
        )

        duplicate_failure_id = cloned("duplicate_failure_id")
        registry_path = duplicate_failure_id / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        registry["approaches"][1]["failure_records"][0]["failure_id"] = (
            registry["approaches"][0]["failure_records"][0]["failure_id"]
        )
        write_json(registry_path, registry)
        _refresh_report_contracts(duplicate_failure_id, duplicate_failure_id)
        assert_code(validate_run(duplicate_failure_id), "AGENT-01", "duplicate_failure_id")

        zero_yield = cloned("grounded_zero_yield_abandoned_lane")
        registry_path = zero_yield / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        abandoned = copy.deepcopy(registry["approaches"][0])
        abandoned.update(
            {
                "approach_id": "image_pack_approach_zero_yield",
                "hypothesis": "A preregistered lane can honestly return zero items and remain auditable.",
                "queries": [
                    {
                        "query_id": "image_pack_query_zero_yield",
                        "query_text": "fixture query with zero observed yield",
                        "locale": "en",
                        "round": 1,
                    }
                ],
                "returned_count": 0,
                "qualified_count": 0,
                "qualification_rate": 0,
                "failure_records": [
                    {
                        "failure_id": "failure_image_pack_zero_yield",
                        "query_id": "image_pack_query_zero_yield",
                        "source_family_id": "first_party",
                        "round": 1,
                        "failure_code": "zero_yield",
                        "candidate_ids": [],
                        "receipt_ids": [],
                        "observed_at": "2026-07-13T00:12:00Z",
                        "reason": "The registered query returned no candidate objects on its observed surface.",
                        "fallback_action": "Switch to the declared adjacent source family without repeating this path.",
                    }
                ],
                "next_round_adjustment": "Switch to the declared adjacent source family without repeating this path.",
                "status": "abandoned",
            }
        )
        registry["approaches"].append(abandoned)
        write_json(registry_path, registry)
        _refresh_approach_plan_bindings(zero_yield)
        zero_yield_result = validate_run(zero_yield)
        if zero_yield_result["status"] != "PASS":
            raise AssertionError(
                f"grounded zero-yield abandoned lane was rejected: {json.dumps(zero_yield_result, ensure_ascii=False, indent=2)}"
            )

        anchored_receipt = cloned("failed_receipt_is_grounded")
        candidates_path = anchored_receipt / "02_candidates/candidate_ledger.jsonl"
        candidates = read_jsonl(candidates_path)
        failed_candidate = next(
            item for item in candidates
            if item["candidate_id"] == "candidate_image_pack_screened_0_0"
        )
        failed_candidate["verification_receipt_id"] = "receipt_screened_0_0"
        write_jsonl(candidates_path, candidates)
        failed_receipt = _receipt(
            failed_candidate,
            datetime(2026, 7, 13, 0, 55, tzinfo=timezone.utc),
            "image_pack",
        )
        failed_receipt.update(
            {
                "evidence_level": "E3_MEDIA_CONFIRMED",
                "failure_codes": ["OTHER"],
                "outcome": "failed",
            }
        )
        receipts_path = anchored_receipt / "03_verification/verification_receipts.jsonl"
        receipts = read_jsonl(receipts_path)
        receipts.append(failed_receipt)
        write_jsonl(receipts_path, receipts)
        registry_path = anchored_receipt / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        registry["approaches"][0]["failure_records"][0]["receipt_ids"].append(
            failed_receipt["receipt_id"]
        )
        write_json(registry_path, registry)
        _refresh_report_contracts(anchored_receipt, anchored_receipt)
        anchored_result = validate_run(anchored_receipt)
        if anchored_result["status"] != "PASS":
            raise AssertionError(
                f"properly grounded failed receipt was rejected: {json.dumps(anchored_result, ensure_ascii=False, indent=2)}"
            )

        missing_receipt_ground = cloned("failed_receipt_missing_from_failure_record")
        candidates_path = missing_receipt_ground / "02_candidates/candidate_ledger.jsonl"
        candidates = read_jsonl(candidates_path)
        failed_candidate = next(
            item for item in candidates
            if item["candidate_id"] == "candidate_image_pack_screened_0_0"
        )
        failed_candidate["verification_receipt_id"] = "receipt_screened_0_0"
        write_jsonl(candidates_path, candidates)
        failed_receipt = _receipt(
            failed_candidate,
            datetime(2026, 7, 13, 0, 55, tzinfo=timezone.utc),
            "image_pack",
        )
        failed_receipt.update(
            {
                "evidence_level": "E3_MEDIA_CONFIRMED",
                "failure_codes": ["OTHER"],
                "outcome": "failed",
            }
        )
        receipts_path = missing_receipt_ground / "03_verification/verification_receipts.jsonl"
        receipts = read_jsonl(receipts_path)
        receipts.append(failed_receipt)
        write_jsonl(receipts_path, receipts)
        _refresh_report_contracts(missing_receipt_ground, missing_receipt_ground)
        assert_code(
            validate_run(missing_receipt_ground),
            "AGENT-01",
            "failed_receipt_missing_from_failure_record",
        )


def test_dedup_and_gallery() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "run"
        make_valid_run(root)
        candidates = read_jsonl(root / "02_candidates/candidate_ledger.jsonl")
        candidates[1]["object"]["canonical_url"] = candidates[0]["object"]["canonical_url"] + "?utm_source=test"
        report = build_dedup_report(candidates)
        if report["duplicate_group_count"] < 1:
            raise AssertionError("canonical URL normalization failed to detect tracking duplicate")
        candidates[0]["object"]["title"] = "<script>alert(1)</script>"
        write_jsonl(root / "02_candidates/candidate_ledger.jsonl", candidates)
        rendered = build_gallery(root)
        if "<script>alert(1)</script>" in rendered or "&lt;script&gt;alert(1)&lt;/script&gt;" not in rendered:
            raise AssertionError("gallery did not HTML-escape candidate content")


def test_dedup_fingerprint_evidence() -> None:
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        valid_root = temp_root / "valid"
        make_valid_run(valid_root)

        video_out_of_range = temp_root / "video_sample_timestamp_out_of_range"
        make_valid_run(video_out_of_range, modality="video")
        video_candidates_path = video_out_of_range / "02_candidates/candidate_ledger.jsonl"
        video_candidates = read_jsonl(video_candidates_path)
        video_candidates[0]["dedup"]["fingerprint"]["sampled_at_seconds"] = [0.0, 1.0, 9999.0]
        write_jsonl(video_candidates_path, video_candidates)
        video_captures_path = video_out_of_range / "03_verification/browser_capture_records.jsonl"
        video_captures = read_jsonl(video_captures_path)
        video_captures[0]["observation"]["dedup_fingerprint"]["sampled_at_seconds"] = [0.0, 1.0, 9999.0]
        write_jsonl(video_captures_path, video_captures)
        video_capture_index = {item["capture_id"]: item for item in video_captures}
        comparison_sha = dedup_comparison_set_sha256(video_candidates[:30])
        video_receipts_path = video_out_of_range / "03_verification/verification_receipts.jsonl"
        video_receipts = read_jsonl(video_receipts_path)
        for receipt in video_receipts:
            receipt["dedup_check"]["comparison_set_sha256"] = comparison_sha
            for binding in receipt["capture_bindings"]:
                binding["record_sha256"] = canonical_sha256(video_capture_index[binding["capture_id"]])
        write_jsonl(video_receipts_path, video_receipts)
        (video_out_of_range / "06_output/reference_board.html").write_text(
            build_gallery(video_out_of_range), encoding="utf-8"
        )
        _refresh_report_contracts(video_out_of_range, video_out_of_range)
        assert_code(
            validate_run(video_out_of_range),
            "DEDUP-01",
            "video_sample_timestamp_out_of_range",
        )

        def cloned(name: str) -> Path:
            root = temp_root / name
            shutil.copytree(valid_root, root)
            return root

        missing_fingerprint = cloned("final_candidate_missing_fingerprint")
        _rewrite_jsonl(
            missing_fingerprint / "02_candidates/candidate_ledger.jsonl",
            lambda rows: rows[0]["dedup"].update({"fingerprint": None}),
        )
        _refresh_report_contracts(missing_fingerprint, missing_fingerprint)
        assert_code(validate_run(missing_fingerprint), "SCHEMA-01", "final_candidate_missing_fingerprint")

        missing_capture_fingerprint = cloned("media_capture_missing_fingerprint")
        captures_path = missing_capture_fingerprint / "03_verification/browser_capture_records.jsonl"
        captures = read_jsonl(captures_path)
        captures[0]["observation"]["dedup_fingerprint"] = None
        write_jsonl(captures_path, captures)
        capture_index = {item["capture_id"]: item for item in captures}
        receipts_path = missing_capture_fingerprint / "03_verification/verification_receipts.jsonl"
        receipts = read_jsonl(receipts_path)
        for binding in receipts[0]["capture_bindings"]:
            binding["record_sha256"] = canonical_sha256(capture_index[binding["capture_id"]])
        write_jsonl(receipts_path, receipts)
        _refresh_report_contracts(missing_capture_fingerprint, missing_capture_fingerprint)
        assert_code(validate_run(missing_capture_fingerprint), "DEDUP-01", "media_capture_missing_fingerprint")

        stale_comparison = cloned("stale_comparison_set_hash")
        candidates_path = stale_comparison / "02_candidates/candidate_ledger.jsonl"
        candidates = read_jsonl(candidates_path)
        candidates[0]["dedup"]["fingerprint"]["perceptual_hash"] = "f" * 16
        write_jsonl(candidates_path, candidates)
        captures_path = stale_comparison / "03_verification/browser_capture_records.jsonl"
        captures = read_jsonl(captures_path)
        captures[0]["observation"]["dedup_fingerprint"]["perceptual_hash"] = "f" * 16
        write_jsonl(captures_path, captures)
        capture_index = {item["capture_id"]: item for item in captures}
        receipts_path = stale_comparison / "03_verification/verification_receipts.jsonl"
        receipts = read_jsonl(receipts_path)
        for binding in receipts[0]["capture_bindings"]:
            binding["record_sha256"] = canonical_sha256(capture_index[binding["capture_id"]])
        write_jsonl(receipts_path, receipts)
        (stale_comparison / "06_output/reference_board.html").write_text(
            build_gallery(stale_comparison), encoding="utf-8"
        )
        _refresh_report_contracts(stale_comparison, stale_comparison)
        assert_code(validate_run(stale_comparison), "DEDUP-01", "stale_comparison_set_hash")

        duplicate_fingerprint = cloned("duplicate_fingerprint_cannot_self_assert_unique")
        candidates_path = duplicate_fingerprint / "02_candidates/candidate_ledger.jsonl"
        candidates = read_jsonl(candidates_path)
        candidates[1]["dedup"]["fingerprint"]["perceptual_hash"] = candidates[0]["dedup"]["fingerprint"]["perceptual_hash"]
        write_jsonl(candidates_path, candidates)
        captures_path = duplicate_fingerprint / "03_verification/browser_capture_records.jsonl"
        captures = read_jsonl(captures_path)
        captures[1]["observation"]["dedup_fingerprint"]["perceptual_hash"] = candidates[1]["dedup"]["fingerprint"]["perceptual_hash"]
        write_jsonl(captures_path, captures)
        capture_index = {item["capture_id"]: item for item in captures}
        comparison_sha = dedup_comparison_set_sha256(candidates[:30])
        receipts_path = duplicate_fingerprint / "03_verification/verification_receipts.jsonl"
        receipts = read_jsonl(receipts_path)
        for receipt in receipts:
            receipt["dedup_check"]["comparison_set_sha256"] = comparison_sha
            for binding in receipt["capture_bindings"]:
                binding["record_sha256"] = canonical_sha256(capture_index[binding["capture_id"]])
        write_jsonl(receipts_path, receipts)
        (duplicate_fingerprint / "06_output/reference_board.html").write_text(
            build_gallery(duplicate_fingerprint), encoding="utf-8"
        )
        _refresh_report_contracts(duplicate_fingerprint, duplicate_fingerprint)
        assert_code(
            validate_run(duplicate_fingerprint),
            "DEDUP-01",
            "duplicate_fingerprint_cannot_self_assert_unique",
        )

        exact_fingerprint = cloned("exact_fingerprint_duplicate")
        candidates_path = exact_fingerprint / "02_candidates/candidate_ledger.jsonl"
        candidates = read_jsonl(candidates_path)
        candidates[1]["dedup"]["fingerprint"]["exact_or_manifest_sha256"] = candidates[0]["dedup"]["fingerprint"]["exact_or_manifest_sha256"]
        write_jsonl(candidates_path, candidates)
        captures_path = exact_fingerprint / "03_verification/browser_capture_records.jsonl"
        captures = read_jsonl(captures_path)
        captures[1]["observation"]["dedup_fingerprint"]["exact_or_manifest_sha256"] = candidates[1]["dedup"]["fingerprint"]["exact_or_manifest_sha256"]
        write_jsonl(captures_path, captures)
        capture_index = {item["capture_id"]: item for item in captures}
        comparison_sha = dedup_comparison_set_sha256(candidates[:30])
        receipts_path = exact_fingerprint / "03_verification/verification_receipts.jsonl"
        receipts = read_jsonl(receipts_path)
        for receipt in receipts:
            receipt["dedup_check"]["comparison_set_sha256"] = comparison_sha
            for binding in receipt["capture_bindings"]:
                binding["record_sha256"] = canonical_sha256(capture_index[binding["capture_id"]])
        write_jsonl(receipts_path, receipts)
        (exact_fingerprint / "06_output/reference_board.html").write_text(
            build_gallery(exact_fingerprint), encoding="utf-8"
        )
        _refresh_report_contracts(exact_fingerprint, exact_fingerprint)
        assert_code(validate_run(exact_fingerprint), "DEDUP-01", "exact_fingerprint_duplicate")

        def configure_authorized_group(root: Path, with_review: bool) -> None:
            candidates_path = root / "02_candidates/candidate_ledger.jsonl"
            candidates = read_jsonl(candidates_path)
            left, right = candidates[0], candidates[20]
            group_id = "near_group_authorized_fixture"
            right["dedup"]["fingerprint"]["perceptual_hash"] = left["dedup"]["fingerprint"]["perceptual_hash"]
            for candidate in (left, right):
                candidate["dedup"].update(
                    {"near_duplicate_group_id": group_id, "version_relation": "regional_version"}
                )
            write_jsonl(candidates_path, candidates)
            captures_path = root / "03_verification/browser_capture_records.jsonl"
            captures = read_jsonl(captures_path)
            capture_by_candidate = {item["candidate_id"]: item for item in captures}
            right_capture = capture_by_candidate[right["candidate_id"]]
            right_capture["observation"]["dedup_fingerprint"]["perceptual_hash"] = right["dedup"]["fingerprint"]["perceptual_hash"]
            write_jsonl(captures_path, captures)
            capture_index = {item["capture_id"]: item for item in captures}
            comparison_sha = dedup_comparison_set_sha256(candidates[:30])
            review_ref = "04_selection/review/dedup-version-group.json" if with_review else None
            receipts_path = root / "03_verification/verification_receipts.jsonl"
            receipts = read_jsonl(receipts_path)
            for receipt in receipts:
                receipt["dedup_check"]["comparison_set_sha256"] = comparison_sha
                if receipt["candidate_id"] in {left["candidate_id"], right["candidate_id"]}:
                    receipt["dedup_check"].update(
                        {
                            "status": "authorized_version",
                            "near_duplicate_group_id": group_id,
                            "manual_version_review_ref": review_ref,
                        }
                    )
                for binding in receipt["capture_bindings"]:
                    binding["record_sha256"] = canonical_sha256(capture_index[binding["capture_id"]])
            write_jsonl(receipts_path, receipts)
            shortlist_path = root / "04_selection/shortlist_30.json"
            shortlist = read_json(shortlist_path)
            for item in shortlist["items"]:
                if item["candidate_id"] in {left["candidate_id"], right["candidate_id"]}:
                    item["dedup_status"] = "authorized_version"
            write_json(shortlist_path, shortlist)
            if with_review:
                write_json(
                    root / review_ref,
                    {
                        "schema_version": "1.0.0",
                        "review_id": "dedup_review_authorized_fixture",
                        "run_id": left["run_id"],
                        "intent_id": left["intent_id"],
                        "intent_version": left["intent_version"],
                        "pack_id": left["pack_id"],
                        "near_duplicate_group_id": group_id,
                        "candidate_ids": [left["candidate_id"], right["candidate_id"]],
                        "decision": "authorized_version_comparison",
                        "reviewer": "curator_diversity",
                        "reviewed_at": "2026-07-13T00:58:00Z",
                        "rationale": "The two fingerprint-near assets are retained solely to compare a declared regional version difference.",
                        "fingerprint_evidence": [
                            {
                                "candidate_id": candidate["candidate_id"],
                                "capture_id": candidate["dedup"]["fingerprint"]["evidence_capture_id"],
                                "exact_or_manifest_sha256": candidate["dedup"]["fingerprint"]["exact_or_manifest_sha256"],
                                "perceptual_hash": candidate["dedup"]["fingerprint"]["perceptual_hash"],
                                "comparison_set_sha256": comparison_sha,
                            }
                            for candidate in (left, right)
                        ],
                    },
                )
            (root / "06_output/reference_board.html").write_text(build_gallery(root), encoding="utf-8")
            _refresh_report_contracts(root, root)

        missing_review = cloned("authorized_version_missing_review")
        configure_authorized_group(missing_review, with_review=False)
        assert_code(validate_run(missing_review), "DEDUP-01", "authorized_version_missing_review")

        authorized = cloned("authorized_version_with_bound_review")
        configure_authorized_group(authorized, with_review=True)
        authorized_result = validate_run(authorized)
        if authorized_result["status"] != "PASS":
            raise AssertionError(
                f"bound authorized-version review failed: {json.dumps(authorized_result, ensure_ascii=False, indent=2)}"
            )

        stale_review = cloned("authorized_version_stale_review_evidence")
        configure_authorized_group(stale_review, with_review=True)
        _rewrite_json(
            stale_review / "04_selection/review/dedup-version-group.json",
            lambda value: value["fingerprint_evidence"][0].update({"perceptual_hash": "0" * 16}),
        )
        _refresh_report_contracts(stale_review, stale_review)
        assert_code(
            validate_run(stale_review),
            "DEDUP-01",
            "authorized_version_stale_review_evidence",
        )

        wrong_reviewer = cloned("authorized_version_wrong_reviewer")
        configure_authorized_group(wrong_reviewer, with_review=True)
        _rewrite_json(
            wrong_reviewer / "04_selection/review/dedup-version-group.json",
            lambda value: value.update({"reviewer": "verifier_0"}),
        )
        _refresh_report_contracts(wrong_reviewer, wrong_reviewer)
        assert_code(validate_run(wrong_reviewer), "AGENT-01", "authorized_version_wrong_reviewer")


def test_pareto_dominance() -> None:
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        valid_root = temp_root / "valid"
        make_valid_run(valid_root)

        def cloned(name: str) -> Path:
            root = temp_root / name
            shutil.copytree(valid_root, root)
            return root

        def comparison_pair(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
            rejected_artifact = read_json(root / "04_selection/rejected_10.json")
            rejected_row = rejected_artifact["items"][0]
            selected_id = rejected_row["dominated_by_candidate_ids"][0]
            candidates = read_jsonl(root / "02_candidates/candidate_ledger.jsonl")
            by_id = {item["candidate_id"]: item for item in candidates}
            return candidates, by_id[selected_id], by_id[rejected_row["candidate_id"]], rejected_artifact

        tradeoff = cloned("tradeoff_is_not_dominance")
        candidates, selected, rejected, _ = comparison_pair(tradeoff)
        for dimension in selected["evaluation_dimensions"]:
            selected["evaluation_dimensions"][dimension]["score"] = 50
            rejected["evaluation_dimensions"][dimension]["score"] = 50
        selected["evaluation_dimensions"]["diversity_contribution"]["score"] = 60
        selected["evaluation_dimensions"]["craft_signal"]["score"] = 49
        write_jsonl(tradeoff / "02_candidates/candidate_ledger.jsonl", candidates)
        (tradeoff / "06_output/reference_board.html").write_text(build_gallery(tradeoff), encoding="utf-8")
        _refresh_report_contracts(tradeoff, tradeoff)
        assert_code(validate_run(tradeoff), "CURATION-02", "tradeoff_is_not_dominance")

        wrong_declared_axis = cloned("declared_axis_must_be_strict_improvement")
        candidates, selected, rejected, _ = comparison_pair(wrong_declared_axis)
        for dimension in selected["evaluation_dimensions"]:
            selected["evaluation_dimensions"][dimension]["score"] = 50
            rejected["evaluation_dimensions"][dimension]["score"] = 50
        selected["evaluation_dimensions"]["craft_signal"]["score"] = 60
        write_jsonl(wrong_declared_axis / "02_candidates/candidate_ledger.jsonl", candidates)
        (wrong_declared_axis / "06_output/reference_board.html").write_text(
            build_gallery(wrong_declared_axis), encoding="utf-8"
        )
        _refresh_report_contracts(wrong_declared_axis, wrong_declared_axis)
        assert_code(
            validate_run(wrong_declared_axis),
            "CURATION-02",
            "declared_axis_must_be_strict_improvement",
        )

        missing_tie = cloned("exact_tie_requires_tie_break")
        candidates, selected, rejected, _ = comparison_pair(missing_tie)
        for dimension in selected["evaluation_dimensions"]:
            selected["evaluation_dimensions"][dimension]["score"] = 50
            rejected["evaluation_dimensions"][dimension]["score"] = 50
        write_jsonl(missing_tie / "02_candidates/candidate_ledger.jsonl", candidates)
        (missing_tie / "06_output/reference_board.html").write_text(build_gallery(missing_tie), encoding="utf-8")
        _refresh_report_contracts(missing_tie, missing_tie)
        assert_code(validate_run(missing_tie), "CURATION-02", "exact_tie_requires_tie_break")

        valid_tie = cloned("exact_tie_with_deterministic_tie_break")
        candidates, selected, rejected, rejected_artifact = comparison_pair(valid_tie)
        for dimension in selected["evaluation_dimensions"]:
            selected["evaluation_dimensions"][dimension]["score"] = 50
            rejected["evaluation_dimensions"][dimension]["score"] = 50
        rejected_artifact["items"][0]["score_tie_break"] = {
            "key": "object.stable_id",
            "order": "ascending_lexicographic",
            "applies_when": "all_dimensions_equal",
        }
        write_jsonl(valid_tie / "02_candidates/candidate_ledger.jsonl", candidates)
        write_json(valid_tie / "04_selection/rejected_10.json", rejected_artifact)
        (valid_tie / "06_output/reference_board.html").write_text(build_gallery(valid_tie), encoding="utf-8")
        _refresh_report_contracts(valid_tie, valid_tie)
        valid_tie_result = validate_run(valid_tie)
        if valid_tie_result["status"] != "PASS":
            raise AssertionError(
                f"valid deterministic exact tie failed: {json.dumps(valid_tie_result, ensure_ascii=False, indent=2)}"
            )


def test_agent_independence_and_blind_handoffs() -> None:
    with tempfile.TemporaryDirectory() as temp:
        valid_root = Path(temp) / "valid"
        make_valid_run(valid_root)
        baseline = validate_run(valid_root)
        if baseline["status"] != "PASS":
            raise AssertionError(f"agent-independence baseline failed: {json.dumps(baseline, ensure_ascii=False, indent=2)}")

        def cloned(name: str) -> Path:
            root = Path(temp) / name
            shutil.copytree(valid_root, root)
            return root

        global_overlap = cloned("verifier_is_other_candidate_finder")
        receipts_path = global_overlap / "03_verification/verification_receipts.jsonl"
        receipts = read_jsonl(receipts_path)
        receipts[0]["verifier"]["verifier_agent_id"] = "finder_1"
        write_jsonl(receipts_path, receipts)
        registry_path = global_overlap / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        next(item for item in registry["agents"] if item["agent_id"] == "finder_1")["additional_roles"] = ["verification_agent"]
        write_json(registry_path, registry)
        _refresh_approach_plan_bindings(global_overlap)
        report_path = global_overlap / "06_output/verification_report.json"
        report = read_json(report_path)
        verifier_ids = {item["verifier"]["verifier_agent_id"] for item in receipts}
        report["agent_separation"]["verifier_agent_ids"] = sorted(verifier_ids)
        report["adversarial_audit"]["independent_from"] = sorted(set(report["adversarial_audit"]["independent_from"]) | verifier_ids)
        write_json(report_path, report)
        _refresh_report_contracts(global_overlap, global_overlap)
        assert_code(validate_run(global_overlap), "AGENT-01", "verifier_is_other_candidate_finder")

        capture_overlap = cloned("capture_operator_is_verifier")
        receipts = read_jsonl(capture_overlap / "03_verification/verification_receipts.jsonl")
        captures_path = capture_overlap / "03_verification/browser_capture_records.jsonl"
        captures = read_jsonl(captures_path)
        captures[0]["operator_agent_id"] = receipts[0]["verifier"]["verifier_agent_id"]
        write_jsonl(captures_path, captures)
        registry_path = capture_overlap / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        next(
            item for item in registry["agents"]
            if item["agent_id"] == receipts[0]["verifier"]["verifier_agent_id"]
        )["additional_roles"] = ["capture_operator"]
        write_json(registry_path, registry)
        _refresh_approach_plan_bindings(capture_overlap)
        report_path = capture_overlap / "06_output/verification_report.json"
        report = read_json(report_path)
        capture_ids = {item["operator_agent_id"] for item in read_jsonl(captures_path)}
        report["agent_separation"]["capture_operator_agent_ids"] = sorted(capture_ids)
        report["adversarial_audit"]["independent_from"] = sorted(set(report["adversarial_audit"]["independent_from"]) | capture_ids)
        write_json(report_path, report)
        _refresh_report_contracts(capture_overlap, capture_overlap)
        assert_code(validate_run(capture_overlap), "AGENT-01", "capture_operator_is_verifier")

        curator_overlap = cloned("same_relevance_and_diversity_curator")
        registry_path = curator_overlap / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        next(item for item in registry["agents"] if item["agent_id"] == "curator_relevance")["additional_roles"] = ["diversity_curator"]
        write_json(registry_path, registry)
        for artifact_name in ("selected_20.json", "rejected_10.json"):
            _rewrite_json(
                curator_overlap / "04_selection" / artifact_name,
                lambda value: value["curation_trace"].update({"diversity_curator_id": "curator_relevance"}),
            )
        _rewrite_json(curator_overlap / "04_selection/review/diversity.json", lambda value: value.update({"reviewer": "curator_relevance"}))
        _refresh_approach_plan_bindings(curator_overlap)
        report_path = curator_overlap / "06_output/verification_report.json"
        report = read_json(report_path)
        report["agent_separation"]["diversity_curator_agent_id"] = "curator_relevance"
        write_json(report_path, report)
        _refresh_report_contracts(curator_overlap, curator_overlap)
        assert_code(validate_run(curator_overlap), "AGENT-01", "same_relevance_and_diversity_curator")

        root_auditor_overlap = cloned("root_is_adversarial_auditor")
        registry_path = root_auditor_overlap / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        next(item for item in registry["agents"] if item["agent_id"] == "auditor_red")["additional_roles"] = ["root_synthesizer"]
        write_json(registry_path, registry)
        for artifact_name in ("selected_20.json", "rejected_10.json"):
            _rewrite_json(
                root_auditor_overlap / "04_selection" / artifact_name,
                lambda value: value["curation_trace"].update({"root_synthesizer_id": "auditor_red"}),
            )
        _rewrite_json(root_auditor_overlap / "04_selection/review/resolution.json", lambda value: value.update({"synthesizer": "auditor_red"}))
        _refresh_approach_plan_bindings(root_auditor_overlap)
        report_path = root_auditor_overlap / "06_output/verification_report.json"
        report = read_json(report_path)
        report["agent_separation"]["root_synthesizer_agent_id"] = "auditor_red"
        write_json(report_path, report)
        _refresh_report_contracts(root_auditor_overlap, root_auditor_overlap)
        assert_code(validate_run(root_auditor_overlap), "AGENT-01", "root_is_adversarial_auditor")

        curator_finder_overlap = cloned("curator_is_finder")
        registry_path = curator_finder_overlap / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        next(item for item in registry["agents"] if item["agent_id"] == "finder_0")["additional_roles"] = ["relevance_curator"]
        write_json(registry_path, registry)
        for artifact_name in ("selected_20.json", "rejected_10.json"):
            _rewrite_json(
                curator_finder_overlap / "04_selection" / artifact_name,
                lambda value: value["curation_trace"].update({"relevance_curator_id": "finder_0"}),
            )
        _rewrite_json(curator_finder_overlap / "04_selection/review/relevance.json", lambda value: value.update({"reviewer": "finder_0"}))
        _refresh_approach_plan_bindings(curator_finder_overlap)
        report_path = curator_finder_overlap / "06_output/verification_report.json"
        report = read_json(report_path)
        report["agent_separation"]["relevance_curator_agent_id"] = "finder_0"
        write_json(report_path, report)
        _refresh_report_contracts(curator_finder_overlap, curator_finder_overlap)
        assert_code(validate_run(curator_finder_overlap), "AGENT-01", "curator_is_finder")

        quarantined_curator_finder = cloned("quarantined_finder_is_relevance_curator")
        candidates_path = quarantined_curator_finder / "02_candidates/candidate_ledger.jsonl"
        candidates = read_jsonl(candidates_path)
        screened = next(item for item in candidates if item["status"] == "quarantined")
        old_approach_id = screened["agent_trace"]["approach_id"]
        new_approach_id = "image_pack_curator_quarantined_lane"
        new_query_id = "image_pack_curator_quarantined_query"
        screened["agent_trace"].update(
            {
                "finder_agent_id": "curator_relevance",
                "approach_id": new_approach_id,
                "query_id": new_query_id,
            }
        )
        write_jsonl(candidates_path, candidates)
        registry_path = quarantined_curator_finder / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        relevance_agent = next(item for item in registry["agents"] if item["agent_id"] == "curator_relevance")
        relevance_agent["additional_roles"] = ["search_scout"]
        old_approach = next(item for item in registry["approaches"] if item["approach_id"] == old_approach_id)
        old_approach["failure_records"][0]["candidate_ids"].remove(screened["candidate_id"])
        old_approach["returned_count"] -= 1
        old_approach["qualification_rate"] = round(
            old_approach["qualified_count"] / old_approach["returned_count"], 3
        )
        registry["approaches"].append(
            {
                "approach_id": new_approach_id,
                "pack_id": "image_pack",
                "modality": "image",
                "decision_axis": "static_reference",
                "method": "challenger",
                "hypothesis": "A quarantined challenger lane tests whether a curator can conceal discovery work.",
                "queries": [{"query_id": new_query_id, "query_text": "curator overlap attack", "locale": "en", "round": 1}],
                "source_family_ids": [screened["source"]["source_family_id"]],
                "executing_agent_id": "curator_relevance",
                "favored_route_disclosed": False,
                "started_at": "2026-07-13T00:06:59Z",
                "returned_count": 1,
                "qualified_count": 0,
                "qualification_rate": 0,
                "failure_records": [
                    {
                        "failure_id": "failure_image_pack_curator_quarantined_lane",
                        "query_id": new_query_id,
                        "source_family_id": screened["source"]["source_family_id"],
                        "round": 1,
                        "failure_code": "screened_out",
                        "candidate_ids": [screened["candidate_id"]],
                        "receipt_ids": [],
                        "observed_at": "2026-07-13T00:12:00Z",
                        "reason": "The quarantined candidate failed the registered relevance screen after discovery.",
                        "fallback_action": "Keep the failed evidence and hand off a distinct challenger lane to a different scout.",
                    }
                ],
                "next_round_adjustment": "Assign the next discovery attempt to a non-curator scout with a distinct execution identity.",
                "status": "abandoned",
            }
        )
        write_json(registry_path, registry)
        _refresh_approach_plan_bindings(quarantined_curator_finder)
        assert_code(
            validate_run(quarantined_curator_finder),
            "AGENT-01",
            "quarantined_finder_is_relevance_curator",
        )

        mismatched_input = cloned("curators_use_different_input_hashes")
        relevance_path = mismatched_input / "04_selection/review/relevance.json"
        _rewrite_json(relevance_path, lambda value: value.update({"input_contract_sha256": "a" * 64}))
        _rewrite_json(
            mismatched_input / "04_selection/review/resolution.json",
            lambda value: value.update({"relevance_review_sha256": hashlib.sha256(relevance_path.read_bytes()).hexdigest()}),
        )
        _refresh_report_contracts(mismatched_input, mismatched_input, refresh_curation=False)
        assert_code(validate_run(mismatched_input), "AGENT-01", "curators_use_different_input_hashes")

        stale_review_hash = cloned("resolution_uses_stale_curator_hash")
        _rewrite_json(
            stale_review_hash / "04_selection/review/relevance.json",
            lambda value: value.update({"rationale": "This changed relevance rationale remains substantive but invalidates the frozen handoff hash."}),
        )
        _refresh_report_contracts(stale_review_hash, stale_review_hash, refresh_curation=False)
        assert_code(validate_run(stale_review_hash), "AGENT-01", "resolution_uses_stale_curator_hash")

        early_resolution = cloned("resolution_starts_before_reviews_complete")
        _rewrite_json(
            early_resolution / "04_selection/review/resolution.json",
            lambda value: value.update({"started_at": "2026-07-13T00:56:30Z"}),
        )
        _refresh_report_contracts(early_resolution, early_resolution, refresh_curation=False)
        assert_code(validate_run(early_resolution), "AGENT-01", "resolution_starts_before_reviews_complete")

        early_audit = cloned("audit_precedes_resolution")
        _rewrite_json(
            early_audit / "06_output/verification_report.json",
            lambda value: value["adversarial_audit"].update({"completed_at": "2026-07-13T00:57:30Z"}),
        )
        assert_code(validate_run(early_audit), "AUDIT-01", "audit_precedes_resolution")


def test_feedback_learning_chain() -> None:
    with tempfile.TemporaryDirectory() as temp:
        valid_root = Path(temp) / "valid"
        make_valid_run(valid_root)

        def cloned(name: str) -> Path:
            root = Path(temp) / name
            shutil.copytree(valid_root, root)
            return root

        def rewrite_event(root: Path, mutation) -> None:
            _rewrite_jsonl(root / "05_feedback/feedback_ledger.jsonl", mutation)
            _refresh_report_contracts(root, root, refresh_feedback=False)

        class_layer = cloned("feedback_class_layer_mismatch")
        rewrite_event(class_layer, lambda rows: rows[0].update({"feedback_class": "query_correction"}))
        assert_code(validate_run(class_layer), "FEEDBACK-01", "feedback_class_layer_mismatch")

        wrong_start = cloned("feedback_history_does_not_start_v1")
        rewrite_event(
            wrong_start,
            lambda rows: rows[0].update({"intent_version_before": "v2", "intent_version_after": "v3"}),
        )
        assert_code(validate_run(wrong_start), "FEEDBACK-01", "feedback_history_does_not_start_v1")

        duplicate_delta = cloned("duplicate_feedback_target_path")
        rewrite_event(
            duplicate_delta,
            lambda rows: rows[0]["constraint_delta"].append(copy.deepcopy(rows[0]["constraint_delta"][0])),
        )
        assert_code(validate_run(duplicate_delta), "FEEDBACK-01", "duplicate_feedback_target_path")

        false_operation = cloned("feedback_operation_existence_lie")
        rewrite_event(
            false_operation,
            lambda rows: rows[0]["constraint_delta"][0].update({"operation": "add"}),
        )
        assert_code(validate_run(false_operation), "FEEDBACK-01", "feedback_operation_existence_lie")

        undeclared_model_drift = cloned("feedback_before_model_has_undeclared_subject_drift")
        _rewrite_json(
            undeclared_model_drift / "00_intent/intent_brief.v1.snapshot.json",
            lambda value: value.update({"subject": "undeclared historical subject drift"}),
        )
        _refresh_report_contracts(undeclared_model_drift, undeclared_model_drift)
        undeclared_result = validate_run(undeclared_model_drift)
        assert_code(
            undeclared_result,
            "FEEDBACK-01",
            "feedback_before_model_has_undeclared_subject_drift",
        )
        if not any("undeclared changes" in item["message"] for item in undeclared_result["findings"]):
            raise AssertionError("undeclared model drift did not exercise exact delta closure")

        granular_query = cloned("granular_query_correction_is_valid")
        registry_path = granular_query / "01_orchestration/approach_registry.json"
        current_registry = read_json(registry_path)
        query_path = "/" + "approaches/0/queries/0/query_text"
        query_before = "fixture query 0 before correction"
        query_after = "fixture query 0 after correction"
        before_registry = copy.deepcopy(current_registry)
        before_registry["intent_version"] = "v1"
        before_registry["approaches"][0]["queries"][0]["query_text"] = query_before
        before_registry["registration"]["plan_sha256"] = approach_plan_sha256(before_registry)
        before_registry_path = granular_query / "01_orchestration/approach_registry.v1.snapshot.json"
        write_json(before_registry_path, before_registry)
        current_registry["approaches"][0]["queries"][0]["query_text"] = query_after
        write_json(registry_path, current_registry)
        _refresh_approach_plan_bindings(granular_query)
        current_registry = read_json(registry_path)
        approach_id = current_registry["approaches"][0]["approach_id"]
        query_id = current_registry["approaches"][0]["queries"][0]["query_id"]
        affected_candidates = [
            item["candidate_id"]
            for item in read_jsonl(granular_query / "02_candidates/candidate_ledger.jsonl")
            if item["agent_trace"]["approach_id"] == approach_id
            or item["agent_trace"]["query_id"] == query_id
        ]
        event = read_jsonl(granular_query / "05_feedback/feedback_ledger.jsonl")[0]
        event.update(
            {
                "feedback_class": "query_correction",
                "error_layer": "query",
                "repair_start_phase": "orchestration",
                "constraint_delta": [
                    {
                        "target_artifact_type": "approach_registry",
                        "before_ref": "01_orchestration/approach_registry.v1.snapshot.json",
                        "after_ref": "01_orchestration/approach_registry.json",
                        "operation": "replace",
                        "path": query_path,
                        "before_exists": True,
                        "after_exists": True,
                        "before": query_before,
                        "after": query_after,
                        "reason": "The query wording was corrected without changing unrelated approach fields.",
                    }
                ],
                "invalidated_candidate_ids": affected_candidates,
                "invalidated_approach_ids": [approach_id],
                "invalidated_query_ids": [query_id],
                "invalidated_artifact_refs": [
                    {
                        "artifact_type": "approach_registry",
                        "ref": "01_orchestration/approach_registry.v1.snapshot.json",
                        "reason": "The prior query wording was superseded.",
                    }
                ],
                "completion_evidence": {
                    **event["completion_evidence"],
                    "artifact_bindings": _feedback_completion_bindings(granular_query, granular_query),
                },
            }
        )
        write_jsonl(granular_query / "05_feedback/feedback_ledger.jsonl", [event])
        _refresh_report_contracts(granular_query, granular_query, refresh_feedback=False)
        granular_result = validate_run(granular_query)
        if granular_result["status"] != "PASS":
            raise AssertionError(
                "granular query correction was rejected: "
                + json.dumps(granular_result, ensure_ascii=False, indent=2)
            )

        query_keyword_only = cloned("query_correction_without_approach_delta")
        rewrite_event(
            query_keyword_only,
            lambda rows: rows[0].update(
                {
                    "feedback_class": "query_correction",
                    "error_layer": "query",
                    "repair_start_phase": "orchestration",
                }
            ),
        )
        assert_code(validate_run(query_keyword_only), "FEEDBACK-01", "query_correction_without_approach_delta")

        unconfirmed_project = cloned("unconfirmed_project_promotion")
        rewrite_event(
            unconfirmed_project,
            lambda rows: rows[0].update(
                {
                    "scope": "project",
                    "signal_class": "confirmed_project_rule",
                    "scope_evidence": {
                        **rows[0]["scope_evidence"],
                        "basis": "explicit_user_confirmation",
                    },
                    "user_confirmed_persistence": False,
                }
            ),
        )
        assert_code(validate_run(unconfirmed_project), "FEEDBACK-01", "unconfirmed_project_promotion")

        inferred_global = cloned("inferred_signal_promoted_global")
        rewrite_event(
            inferred_global,
            lambda rows: rows[0].update(
                {
                    "scope": "global",
                    "signal_class": "inferred_session_signal",
                    "scope_evidence": {
                        **rows[0]["scope_evidence"],
                        "basis": "explicit_user_confirmation",
                    },
                    "user_confirmed_persistence": True,
                }
            ),
        )
        assert_code(validate_run(inferred_global), "FEEDBACK-01", "inferred_signal_promoted_global")

        stale_completion = cloned("feedback_completion_hash_mismatch")
        rewrite_event(
            stale_completion,
            lambda rows: rows[0]["completion_evidence"]["artifact_bindings"][0].update({"sha256": "0" * 64}),
        )
        assert_code(validate_run(stale_completion), "FEEDBACK-01", "feedback_completion_hash_mismatch")

        reversed_time = cloned("feedback_completion_precedes_application")
        rewrite_event(
            reversed_time,
            lambda rows: rows[0]["completion_evidence"].update({"completed_at": "2026-07-13T00:20:30Z"}),
        )
        assert_code(validate_run(reversed_time), "FEEDBACK-01", "feedback_completion_precedes_application")

        unrelated_supersedes = cloned("feedback_supersedes_unrelated_path")
        mutate(unrelated_supersedes, "feedback_two_event_false_bridge")
        intent_path = unrelated_supersedes / "00_intent/intent_brief.json"
        intent = read_json(intent_path)
        intent["human_presence"] = "full_body_group"
        write_json(intent_path, intent)
        events = read_jsonl(unrelated_supersedes / "05_feedback/feedback_ledger.jsonl")
        events[1]["constraint_delta"][0].update(
            {
                "path": "/human_presence",
                "before": "full_body_single",
                "after": "full_body_group",
            }
        )
        write_jsonl(unrelated_supersedes / "05_feedback/feedback_ledger.jsonl", events)
        _refresh_report_contracts(unrelated_supersedes, unrelated_supersedes, refresh_feedback=False)
        result = validate_run(unrelated_supersedes)
        assert_code(result, "FEEDBACK-01", "feedback_supersedes_unrelated_path")
        if not any("unrelated prior correction" in item["message"] for item in result["findings"]):
            raise AssertionError("feedback_supersedes_unrelated_path did not exercise the supersession guard")


def test_http_boundary() -> None:
    candidate = _candidate("fixture_run", "image", 0)
    candidate["object"]["canonical_url"] = "https://example.com/work/image"
    candidate["source"]["discovered_url"] = candidate["object"]["canonical_url"]

    receipt = verify_candidates.http_precheck(candidate, "transport_verifier", 1.0)
    if receipt["outcome"] != "blocked" or receipt["verifier"]["verification_surface"] != "http":
        raise AssertionError("HTTP precheck crossed the browser verification boundary")
    if receipt["access_state"]["http_status"] is not None or receipt["access_state"]["canonical_url_resolved"]:
        raise AssertionError("offline HTTP placeholder claimed a network observation")
    if verify_candidates.receipt_has_browser_media_evidence(receipt, "image"):
        raise AssertionError("HTTP precheck was incorrectly accepted as browser media evidence")
    receipt_errors = validate_schema(
        receipt, read_json(PACKAGE_ROOT / "references/verification_receipt.schema.json")
    )
    if receipt_errors:
        raise AssertionError(f"HTTP boundary receipt is not schema-valid: {receipt_errors}")
    for unsafe in (
        "file:///etc/passwd",
        "http://127.0.0.1/admin",
        "http://[::1]/",
        "http://169.254.169.254/latest/meta-data/",
        "http://user:pass@example.com/",
    ):
        try:
            verify_candidates._assert_public_http_url(unsafe)
        except ContractError:
            pass
        else:
            raise AssertionError(f"unsafe transport URL was accepted: {unsafe}")


def test_tool_fail_closed_and_history_safety() -> None:
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)

        def expected_cli_error(entrypoint, arguments: list[str]) -> int:
            with contextlib.redirect_stderr(io.StringIO()):
                return entrypoint(arguments)

        protected = temp_root / "atomic.json"
        protected.write_text('{"preserved":true}\n', encoding="utf-8")
        original_replace = contract_utils.os.replace

        def fail_replace(_source, _destination) -> None:
            raise OSError("injected replace failure")

        contract_utils.os.replace = fail_replace
        try:
            try:
                write_json(protected, {"preserved": False})
            except ContractError:
                pass
            else:
                raise AssertionError("atomic writer ignored an injected replace failure")
        finally:
            contract_utils.os.replace = original_replace
        if protected.read_text(encoding="utf-8") != '{"preserved":true}\n':
            raise AssertionError("atomic replace failure modified the prior artifact")
        if list(temp_root.glob(".atomic.json.*.tmp")):
            raise AssertionError("atomic replace failure leaked a sibling temporary file")

        symlink_target = temp_root / "symlink-target.json"
        symlink_target.write_text('{"preserved":true}\n', encoding="utf-8")
        symlink_output = temp_root / "symlink-output.json"
        try:
            symlink_output.symlink_to(symlink_target)
        except OSError:
            pass
        else:
            try:
                write_json(symlink_output, {"preserved": False})
            except ContractError:
                pass
            else:
                raise AssertionError("atomic writer followed a leaf symlink")
            if symlink_target.read_text(encoding="utf-8") != '{"preserved":true}\n':
                raise AssertionError("symlink refusal did not preserve its target")

        valid_root = temp_root / "valid"
        make_valid_run(valid_root)
        all_candidates = read_jsonl(valid_root / "02_candidates/candidate_ledger.jsonl")
        candidate = all_candidates[0]
        pack_id = candidate["pack_id"]
        current_receipt = next(
            item
            for item in read_jsonl(valid_root / "03_verification/verification_receipts.jsonl")
            if item["candidate_id"] == candidate["candidate_id"]
        )
        historical_receipt = copy.deepcopy(current_receipt)
        historical_receipt.update(
            {
                "receipt_id": "receipt_historical_blocked",
                "checked_at": "2026-07-13T00:40:00Z",
                "outcome": "blocked",
                "evidence_level": "E0_LEAD",
                "failure_codes": ["PAGE_NOT_RENDERED"],
            }
        )
        historical_receipt["freshness"].update(
            {"expires_at": "2026-07-13T01:10:00Z", "reverification_required": True}
        )
        history = verify_candidates.build_receipts(
            [candidate],
            [current_receipt, historical_receipt],
            False,
            "transport_verifier",
            1.0,
            pack_id,
        )
        if [item["receipt_id"] for item in history] != [
            "receipt_historical_blocked",
            current_receipt["receipt_id"],
        ]:
            raise AssertionError("receipt importer discarded or reordered historical receipts")
        latest = verify_candidates._latest_by_candidate(history)[candidate["candidate_id"]]
        if latest["receipt_id"] != current_receipt["receipt_id"] or not verify_candidates.receipt_has_browser_media_evidence(
            latest, candidate["modality"]
        ):
            raise AssertionError("latest receipt selection used stale history")

        candidate_path = temp_root / "one-candidate.jsonl"
        offline_path = temp_root / "new-receipt.jsonl"
        history_path = temp_root / "receipt-history.jsonl"
        write_jsonl(candidate_path, [candidate])
        write_jsonl(offline_path, [current_receipt])
        write_jsonl(history_path, [historical_receipt])
        verify_args = [
            "--candidates", str(candidate_path),
            "--offline-receipts", str(offline_path),
            "--output", str(history_path),
            "--pack-id", pack_id,
            "--require-qualified",
        ]
        if verify_candidates.main(verify_args) != 0:
            raise AssertionError("receipt CLI rejected a qualified latest receipt")
        if len(read_jsonl(history_path)) != 2:
            raise AssertionError("receipt CLI erased existing history during atomic replacement")
        if verify_candidates.main([
            "--candidates", str(candidate_path),
            "--output", str(history_path),
            "--pack-id", pack_id,
            "--require-qualified",
        ]) != 0:
            raise AssertionError("receipt CLI could not safely re-import its existing output history")

        foreign = copy.deepcopy(current_receipt)
        foreign["intent_id"] = "foreign_intent"
        for label, receipts, timeout in (
            ("foreign receipt binding", [foreign], 1.0),
            ("duplicate receipt id", [historical_receipt, {**historical_receipt, "checked_at": "2026-07-13T00:39:00Z"}], 1.0),
            ("ambiguous receipt time", [historical_receipt, {**historical_receipt, "receipt_id": "receipt_same_time"}], 1.0),
            ("non-finite timeout", [current_receipt], float("nan")),
        ):
            try:
                verify_candidates.build_receipts(
                    [candidate], receipts, False, "transport_verifier", timeout, pack_id
                )
            except ContractError:
                pass
            else:
                raise AssertionError(f"receipt importer accepted {label}")

        candidate_bytes = candidate_path.read_bytes()
        if expected_cli_error(verify_candidates.main, [
            "--candidates", str(candidate_path),
            "--output", str(candidate_path),
            "--pack-id", pack_id,
        ]) != 2 or candidate_path.read_bytes() != candidate_bytes:
            raise AssertionError("receipt CLI overwrote its candidate input")

        malformed_hash = copy.deepcopy(candidate)
        malformed_hash["dedup"]["fingerprint"]["perceptual_hash"] = "not-hex"
        for label, candidates, threshold in (
            ("negative perceptual threshold", [candidate], -1),
            ("oversized perceptual threshold", [candidate], 65),
            ("malformed perceptual hash", [malformed_hash], 6),
        ):
            try:
                build_dedup_report(candidates, phash_distance=threshold)
            except ContractError:
                pass
            else:
                raise AssertionError(f"dedup tool accepted {label}")
        if expected_cli_error(deduplicate_candidates.main, [
            "--candidates", str(candidate_path),
            "--output", str(candidate_path),
        ]) != 2 or candidate_path.read_bytes() != candidate_bytes:
            raise AssertionError("dedup CLI overwrote its candidate input")

        intent_path = valid_root / "00_intent/intent_brief.json"
        intent_bytes = intent_path.read_bytes()
        if expected_cli_error(validate_research_run.main, [
            "--run-dir", str(valid_root),
            "--output", str(intent_path),
        ]) != 2 or intent_path.read_bytes() != intent_bytes:
            raise AssertionError("validator CLI overwrote a required run artifact")
        historical_model_path = valid_root / "00_intent/intent_brief.v1.snapshot.json"
        historical_model_bytes = historical_model_path.read_bytes()
        if expected_cli_error(validate_research_run.main, [
            "--run-dir", str(valid_root),
            "--output", str(historical_model_path),
        ]) != 2 or historical_model_path.read_bytes() != historical_model_bytes:
            raise AssertionError("validator CLI overwrote referenced historical evidence")
        safe_validation_output = temp_root / "validator-result.json"
        if validate_research_run.main([
            "--run-dir", str(valid_root),
            "--output", str(safe_validation_output),
        ]) != 0:
            raise AssertionError("validator rejected a non-clobbering output path")

        same_instant = temp_root / "same-instant-receipts"
        shutil.copytree(valid_root, same_instant)
        same_instant_receipts_path = same_instant / "03_verification/verification_receipts.jsonl"
        same_instant_receipts = read_jsonl(same_instant_receipts_path)
        alternate_offset = copy.deepcopy(same_instant_receipts[0])
        alternate_offset.update(
            {
                "receipt_id": "receipt_same_instant_alternate_offset",
                "checked_at": "2026-07-13T08:55:00+08:00",
            }
        )
        same_instant_receipts.append(alternate_offset)
        write_jsonl(same_instant_receipts_path, same_instant_receipts)
        _refresh_report_contracts(same_instant, same_instant)
        assert_code(
            validate_run(same_instant),
            "VERIFY-01",
            "alternate_timezone_same_instant_receipt_tie",
        )

        ledger_bytes = (valid_root / "02_candidates/candidate_ledger.jsonl").read_bytes()
        if expected_cli_error(build_review_gallery.main, [
            "--run-dir", str(valid_root),
            "--output", str(valid_root / "02_candidates/candidate_ledger.jsonl"),
        ]) != 2 or (valid_root / "02_candidates/candidate_ledger.jsonl").read_bytes() != ledger_bytes:
            raise AssertionError("gallery CLI overwrote a source contract artifact")


def test_strict_evidence_boundaries() -> None:
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        duplicate_path = temp_root / "duplicate.json"
        duplicate_path.write_text('{"final_status":"fail","final_status":"pass"}\n', encoding="utf-8")
        for path, raw in (
            (duplicate_path, None),
            (temp_root / "nan.json", '{"score":NaN}\n'),
            (temp_root / "infinity.json", '{"score":Infinity}\n'),
            (temp_root / "overflow.json", '{"score":1e999}\n'),
        ):
            if raw is not None:
                path.write_text(raw, encoding="utf-8")
            try:
                read_json(path)
            except ContractError:
                pass
            else:
                raise AssertionError(f"strict JSON loader accepted unsafe numeric/key input: {path.name}")

        protected = temp_root / "protected.json"
        protected.write_text('{"preserved":true}\n', encoding="utf-8")
        try:
            write_json(protected, {"score": float("nan")})
        except ContractError:
            pass
        else:
            raise AssertionError("strict JSON writer serialized NaN")
        if protected.read_text(encoding="utf-8") != '{"preserved":true}\n':
            raise AssertionError("failed strict serialization partially overwrote the destination")

        valid_root = temp_root / "valid"
        make_valid_run(valid_root)
        fixture_result = validate_run(valid_root)
        if fixture_result["status"] != "PASS" or fixture_result["production_contract_eligible"] or fixture_result["production_deliverable"]:
            raise AssertionError("test fixture did not remain a non-production PASS")
        assert_code(
            validate_run(valid_root, require_production_contract_eligible=True),
            "MODE-01",
            "fixture_cannot_cross_production_gate",
        )

        def cloned(name: str) -> Path:
            root = temp_root / name
            shutil.copytree(valid_root, root)
            return root

        route_contradiction = cloned("route_reason_contradicts_modality")
        _rewrite_json(
            route_contradiction / "00_intent/intent_brief.json",
            lambda value: value.update({"route_reason_codes": ["explicit_video_request"]}),
        )
        _refresh_report_contracts(route_contradiction, route_contradiction)
        assert_code(validate_run(route_contradiction), "ROUTE-01", "route_reason_contradicts_modality")

        draft_intent = cloned("draft_intent_cannot_complete")
        _rewrite_json(
            draft_intent / "00_intent/intent_brief.json",
            lambda value: value["approval"].update({"state": "draft"}),
        )
        _refresh_report_contracts(draft_intent, draft_intent)
        assert_code(validate_run(draft_intent), "INTENT-01", "draft_intent_cannot_complete")

        dead_scene_constraint = cloned("scene_scale_constraint_is_live")
        _rewrite_json(
            dead_scene_constraint / "00_intent/intent_brief.json",
            lambda value: value.update({"scene_scale": "architecture"}),
        )
        _refresh_candidate_intent_bindings(dead_scene_constraint, dead_scene_constraint)
        assert_code(validate_run(dead_scene_constraint), "RELEVANCE-01", "scene_scale_constraint_is_live")

        stale_content = cloned("content_max_age_is_live")
        _rewrite_json(
            stale_content / "00_intent/intent_brief.json",
            lambda value: value["freshness_need"].update({"content_max_age_days": 1}),
        )
        _refresh_candidate_intent_bindings(stale_content, stale_content)
        assert_code(validate_run(stale_content), "RELEVANCE-01", "content_max_age_is_live")

        region_contradiction = cloned("market_region_and_language_are_live")
        _rewrite_jsonl(
            region_contradiction / "02_candidates/candidate_ledger.jsonl",
            lambda rows: rows[0]["object"].update({"region": "unlisted-market", "language": "zz"}),
        )
        _refresh_report_contracts(region_contradiction, region_contradiction)
        assert_code(
            validate_run(region_contradiction),
            "RELEVANCE-01",
            "market_region_and_language_are_live",
        )

        object_type_mismatch = cloned("image_cannot_use_video_object_type")
        _rewrite_jsonl(
            object_type_mismatch / "02_candidates/candidate_ledger.jsonl",
            lambda rows: rows[0]["object"].update({"object_type": "specific_video_work"}),
        )
        _refresh_report_contracts(object_type_mismatch, object_type_mismatch)
        assert_code(validate_run(object_type_mismatch), "SCHEMA-01", "image_cannot_use_video_object_type")

        broad_flag_contradiction = cloned("broad_brief_flags_must_bind_intent")
        _rewrite_json(
            broad_flag_contradiction / "04_selection/selected_20.json",
            lambda value: value["diversity_policy"].update({"broad_brief": False}),
        )
        _rewrite_json(
            broad_flag_contradiction / "06_output/verification_report.json",
            lambda value: value["diversity"].update({"broad_brief": False}),
        )
        _refresh_report_contracts(broad_flag_contradiction, broad_flag_contradiction)
        assert_code(
            validate_run(broad_flag_contradiction),
            "DIVERSITY-01",
            "broad_brief_flags_must_bind_intent",
        )

        rights_contradiction = cloned("intent_rights_scope_is_live")
        candidates = read_jsonl(rights_contradiction / "02_candidates/candidate_ledger.jsonl")
        receipts = read_jsonl(rights_contradiction / "03_verification/verification_receipts.jsonl")
        candidates[0]["rights_scope"]["commercial_reuse"] = {
            "state": "allowed",
            "basis": "Unsafe fixture overclaim used only to prove rejection.",
        }
        receipts[0]["rights_scope"] = copy.deepcopy(candidates[0]["rights_scope"])
        write_jsonl(rights_contradiction / "02_candidates/candidate_ledger.jsonl", candidates)
        write_jsonl(rights_contradiction / "03_verification/verification_receipts.jsonl", receipts)
        _refresh_report_contracts(rights_contradiction, rights_contradiction)
        assert_code(validate_run(rights_contradiction), "RIGHTS-01", "intent_rights_scope_is_live")

        core_symlink = cloned("core_artifact_symlink_escape")
        intent_path = core_symlink / "00_intent/intent_brief.json"
        outside_intent = temp_root / "outside-intent.json"
        shutil.copy2(intent_path, outside_intent)
        intent_path.unlink()
        try:
            intent_path.symlink_to(outside_intent)
        except OSError:
            shutil.copy2(outside_intent, intent_path)
        else:
            assert_code(validate_run(core_symlink), "ARTIFACT_INTEGRITY", "core_artifact_symlink_escape")

        trusted_contract_time = datetime(2026, 7, 13, 1, 25, tzinfo=timezone.utc)
        retrospective = cloned("retrospective_contract_simulation")
        _convert_contract_simulation(retrospective, "retrospective_smoke")
        retrospective_result = validate_run(retrospective, validation_now=trusted_contract_time)
        if retrospective_result["status"] != "PASS" or retrospective_result["production_contract_eligible"] or retrospective_result["production_deliverable"]:
            raise AssertionError(
                f"retrospective contract simulation failed: {json.dumps(retrospective_result, ensure_ascii=False, indent=2)}"
            )
        if "not cryptographically attested" not in retrospective_result["validator_boundary"]:
            raise AssertionError("retrospective simulation lost the explicit no-browser-attestation boundary")
        assert_code(
            validate_run(
                retrospective,
                validation_now=trusted_contract_time,
                require_production_contract_eligible=True,
            ),
            "MODE-01",
            "retrospective_cannot_cross_production_gate",
        )

        production = cloned("production_contract_simulation")
        _convert_contract_simulation(production, "production_live")
        source_rows = read_jsonl(production / "03_verification/source_records.jsonl")
        if not all(row["contract_simulation"] and not row["browser_action_attested"] for row in source_rows):
            raise AssertionError("production contract simulation accidentally claimed real browser attestation")
        production_result = validate_run(production, validation_now=trusted_contract_time)
        if (
            production_result["status"] != "PASS"
            or not production_result["production_contract_eligible"]
            or production_result["production_deliverable"]
        ):
            raise AssertionError(
                f"production contract simulation failed: {json.dumps(production_result, ensure_ascii=False, indent=2)}"
            )
        if "not cryptographically attested" not in production_result["validator_boundary"]:
            raise AssertionError("production simulation lost the explicit no-browser-attestation boundary")
        contract_gate_result = validate_run(
            production,
            validation_now=trusted_contract_time,
            require_production_contract_eligible=True,
        )
        if contract_gate_result["status"] != "PASS":
            raise AssertionError(
                f"passing production contract did not satisfy --require-production-contract-eligible: "
                f"{json.dumps(contract_gate_result, ensure_ascii=False, indent=2)}"
            )
        assert_code(
            validate_run(
                production,
                validation_now=trusted_contract_time,
                require_production_deliverable=True,
            ),
            "ATTEST-01",
            "unsigned_production_simulation_cannot_cross_delivery_gate",
        )

        late_freeze = temp_root / "production_plan_frozen_after_discovery"
        shutil.copytree(production, late_freeze)
        registry_path = late_freeze / "01_orchestration/approach_registry.json"
        registry = read_json(registry_path)
        registry["registration"]["frozen_at"] = "2026-07-13T00:15:00Z"
        registry["registration"]["plan_sha256"] = approach_plan_sha256(registry)
        write_json(registry_path, registry)
        captures_path = late_freeze / "03_verification/browser_capture_records.jsonl"
        captures = read_jsonl(captures_path)
        for capture in captures:
            capture["approach_plan_sha256"] = registry["registration"]["plan_sha256"]
        write_jsonl(captures_path, captures)
        capture_index = {item["capture_id"]: item for item in captures}
        receipts_path = late_freeze / "03_verification/verification_receipts.jsonl"
        receipts = read_jsonl(receipts_path)
        for receipt in receipts:
            for binding in receipt["capture_bindings"]:
                binding["record_sha256"] = canonical_sha256(capture_index[binding["capture_id"]])
        write_jsonl(receipts_path, receipts)
        _refresh_report_contracts(late_freeze, late_freeze)
        assert_code(
            validate_run(late_freeze, validation_now=trusted_contract_time),
            "PREREG-01",
            "production_plan_frozen_after_search_and_discovery",
        )

        duplicate_receipt = cloned("duplicate_receipt_id")
        _rewrite_jsonl(
            duplicate_receipt / "03_verification/verification_receipts.jsonl",
            lambda rows: rows[1].update({"receipt_id": rows[0]["receipt_id"]}),
        )
        assert_code(validate_run(duplicate_receipt), "VERIFY-01", "duplicate_receipt_id")

        future = cloned("future_clock")
        _rewrite_json(
            future / "06_output/verification_report.json",
            lambda value: value.update({"generated_at": "2099-01-01T00:00:00Z"}),
        )
        assert_code(validate_run(future), "FRESHNESS-01", "future_timestamp")

        tiny_image = cloned("tiny_image")
        _rewrite_jsonl(
            tiny_image / "03_verification/verification_receipts.jsonl",
            lambda rows: rows[0]["media_check"]["image_render"].update({"natural_width": 1, "natural_height": 1}),
        )
        assert_code(validate_run(tiny_image), "SCHEMA-01", "tiny_image_cannot_qualify")

        overrun_video = temp_root / "overrun_video"
        make_valid_run(overrun_video, "video")
        _rewrite_jsonl(
            overrun_video / "03_verification/verification_receipts.jsonl",
            lambda rows: rows[0]["media_check"]["video_playback"].update(
                {"observed_progress_seconds": 9999.0, "duration_seconds": 1.0}
            ),
        )
        assert_code(validate_run(overrun_video), "VERIFY-02", "video_progress_exceeds_duration")

        title_only = temp_root / "title_only_video"
        shutil.copytree(overrun_video, title_only)
        _rewrite_jsonl(
            title_only / "03_verification/verification_receipts.jsonl",
            lambda rows: rows[0]["object_match"].update({"matched_stable_id": False}),
        )
        assert_code(validate_run(title_only), "SCHEMA-01", "video_title_only_match")

        rights_allowed = cloned("high_risk_rights_allowed")
        for relative in ("02_candidates/candidate_ledger.jsonl", "03_verification/verification_receipts.jsonl"):
            _rewrite_jsonl(
                rights_allowed / relative,
                lambda rows: rows[0]["rights_scope"]["commercial_reuse"].update(
                    {"state": "allowed", "basis": "A self-declared line incorrectly claims permission."}
                ),
            )
        assert_code(validate_run(rights_allowed), "RIGHTS-01", "high_risk_rights_allowed")

        signed_shareable = cloned("signed_chrome_shareable")
        for relative in ("02_candidates/candidate_ledger.jsonl", "03_verification/verification_receipts.jsonl"):
            _rewrite_jsonl(
                signed_shareable / relative,
                lambda rows: rows[0]["access_state"].update({"mode": "signed_chrome", "shareable_without_session": True}),
            )
        assert_code(validate_run(signed_shareable), "VERIFY-03", "signed_chrome_cannot_self_assert_public")

        duplicate_approach = cloned("duplicate_approach")
        _rewrite_json(
            duplicate_approach / "01_orchestration/approach_registry.json",
            lambda value: value["approaches"][1].update({"approach_id": value["approaches"][0]["approach_id"]}),
        )
        assert_code(validate_run(duplicate_approach), "AGENT-01", "duplicate_approach_id")

        duplicate_query = cloned("duplicate_query")
        _rewrite_json(
            duplicate_query / "01_orchestration/approach_registry.json",
            lambda value: value["approaches"][1]["queries"][0].update(
                {"query_id": value["approaches"][0]["queries"][0]["query_id"]}
            ),
        )
        assert_code(validate_run(duplicate_query), "AGENT-01", "duplicate_query_id")

        ghost_executor = cloned("ghost_executor")
        _rewrite_json(
            ghost_executor / "01_orchestration/approach_registry.json",
            lambda value: value["approaches"][0].update({"executing_agent_id": "ghost_agent"}),
        )
        assert_code(validate_run(ghost_executor), "AGENT-01", "ghost_executor")

        empty_complete = cloned("empty_complete")
        _rewrite_json(
            empty_complete / "01_orchestration/approach_registry.json",
            lambda value: value["approaches"][0].update(
                {"returned_count": 0, "qualified_count": 0, "qualification_rate": 0}
            ),
        )
        assert_code(validate_run(empty_complete), "AGENT-01", "empty_complete_approach")

        repost = cloned("repost_candidate")
        _rewrite_jsonl(
            repost / "02_candidates/candidate_ledger.jsonl",
            lambda rows: rows[0]["dedup"].update({"version_relation": "repost"}),
        )
        assert_code(validate_run(repost), "SCHEMA-01", "repost_cannot_qualify")

        self_proof = cloned("report_self_proof")
        _rewrite_json(
            self_proof / "06_output/verification_report.json",
            lambda value: value.update({"validator": {"status": "pass"}}),
        )
        assert_code(validate_run(self_proof), "SCHEMA-01", "report_cannot_self_validate")

        missing_waiver = cloned("missing_waiver_evidence")
        _rewrite_json(
            missing_waiver / "00_intent/intent_brief.json",
            lambda value: value["diversity_requirements"].update({"min_domains": 6}),
        )
        waiver = {
            "constraints": ["min_domains"],
            "reason": "Five sources were retained for relevance, but the exception still needs real evidence.",
            "evidence": ["04_selection/review/does-not-exist.json"],
            "remaining_risk": "The source set remains one domain below the frozen broad-brief threshold.",
            "approved_by": "curator_diversity",
        }
        _rewrite_json(
            missing_waiver / "04_selection/selected_20.json",
            lambda value: value["diversity_policy"].update({"waiver": waiver}),
        )
        _rewrite_json(
            missing_waiver / "06_output/verification_report.json",
            lambda value: value["diversity"].update({"waiver": waiver, "status": "waived"}),
        )
        assert_code(validate_run(missing_waiver), "DIVERSITY-01", "missing_waiver_evidence")

        inverted = cloned("inverted_dominance")
        def invert_scores(rows):
            selected = rows[10]
            rejected = rows[20]
            for dimension in selected["evaluation_dimensions"]:
                selected["evaluation_dimensions"][dimension]["score"] = 0 if dimension != "rights_risk" else 100
                rejected["evaluation_dimensions"][dimension]["score"] = 100 if dimension != "rights_risk" else 0
        _rewrite_jsonl(inverted / "02_candidates/candidate_ledger.jsonl", invert_scores)
        assert_code(validate_run(inverted), "CURATION-02", "inverted_dominance")

        capture_drift = cloned("capture_hash_drift")
        _rewrite_jsonl(
            capture_drift / "03_verification/browser_capture_records.jsonl",
            lambda rows: rows[0]["observation"].update({"asset_locator": "drifted-asset"}),
        )
        assert_code(validate_run(capture_drift), "CAPTURE-01", "capture_hash_drift")

        mode_overclaim = cloned("mode_overclaim")
        _rewrite_json(
            mode_overclaim / "00_intent/intent_brief.json",
            lambda value: value.update({"run_mode": "production_live"}),
        )
        assert_code(validate_run(mode_overclaim), "MODE-01", "fixture_relabelled_as_production")

        parallel = temp_root / "parallel_global_feedback"
        make_parallel_run(parallel)
        for pack_id in ("image_pack", "video_pack"):
            _rewrite_jsonl(
                parallel / "packs" / pack_id / "05_feedback/feedback_ledger.jsonl",
                lambda rows: rows[0].update(
                    {
                        "scope": "global",
                        "signal_class": "confirmed_global_rule",
                        "scope_evidence": {
                            "basis": "explicit_user_confirmation",
                            "supporting_feedback_ids": [],
                            "counterexamples_considered": "The user explicitly confirmed this rule despite possible context-specific exceptions.",
                            "scope_owner": "user",
                            "reversal_procedure": "Record an explicit superseding global correction and stop applying the earlier rule.",
                        },
                        "user_confirmed_persistence": True,
                    }
                ),
            )
            _refresh_report_contracts(parallel, parallel / "packs" / pack_id)
        parallel_result = validate_run(parallel)
        if parallel_result["status"] != "PASS":
            raise AssertionError(
                "semantically identical global feedback with pack-local bindings failed: "
                + json.dumps(parallel_result, ensure_ascii=False, indent=2)
            )

        parallel_drift = temp_root / "parallel_global_feedback_drift"
        shutil.copytree(parallel, parallel_drift)
        _rewrite_jsonl(
            parallel_drift / "packs/video_pack/05_feedback/feedback_ledger.jsonl",
            lambda rows: rows[0].update({"user_evidence_or_quote": "Divergent global correction."}),
        )
        _refresh_report_contracts(parallel_drift, parallel_drift / "packs/video_pack")
        assert_code(validate_run(parallel_drift), "FEEDBACK-01", "parallel_global_feedback_drift")

        unsafe_gallery = cloned("unsafe_gallery")
        _rewrite_jsonl(
            unsafe_gallery / "02_candidates/candidate_ledger.jsonl",
            lambda rows: rows[0]["object"].update({"canonical_url": "javascript:alert(1)"}),
        )
        try:
            build_gallery(unsafe_gallery)
        except ContractError:
            pass
        else:
            raise AssertionError("gallery rendered an unsafe clickable URL")


def test_schema_keyword_enforcement() -> None:
    if validate_schema({"value": 1}, {"anyOf": [{"required": ["value"]}, {"required": ["other"]}] }):
        raise AssertionError("anyOf rejected a valid branch")
    if not validate_schema({"value": 1}, {"oneOf": [{"required": ["value"]}, {"required": ["value"]}]}):
        raise AssertionError("oneOf failed to reject two matching branches")
    if not validate_schema("forbidden", {"not": {"const": "forbidden"}}):
        raise AssertionError("not failed to reject the forbidden instance")
    contains_schema = {"type": "array", "contains": {"const": "needed"}, "minContains": 1, "maxContains": 1}
    if validate_schema(["needed"], contains_schema) or not validate_schema(["other"], contains_schema):
        raise AssertionError("contains/minContains did not enforce membership")
    try:
        validate_schema({}, {"type": "object", "silentlyIgnoredSecurityGate": True})
    except SchemaViolation:
        pass
    else:
        raise AssertionError("unsupported JSON-Schema keyword was silently ignored")
    for schema_path in sorted((PACKAGE_ROOT / "references").glob("*.schema.json")):
        assert_schema_supported(read_json(schema_path))
    registry = read_json(PACKAGE_ROOT / "references/source_registry.json")
    registry_errors = validate_schema(
        registry,
        read_json(PACKAGE_ROOT / "references/source_registry.schema.json"),
    )
    if registry_errors:
        raise AssertionError(f"checked-in source registry violates schema: {registry_errors[:10]}")
    family_ids = [item["family_id"] for item in registry["families"]]
    source_ids = [item["source_id"] for item in registry["sources"]]
    if len(family_ids) != len(set(family_ids)) or len(source_ids) != len(set(source_ids)):
        raise AssertionError("source registry contains duplicate family_id or source_id")
    unknown_family_refs = sorted({item["family_id"] for item in registry["sources"]} - set(family_ids))
    unknown_fallback_refs = sorted(
        {fallback for item in registry["sources"] for fallback in item["fallback_source_ids"]} - set(source_ids)
    )
    if unknown_family_refs or unknown_fallback_refs:
        raise AssertionError(
            f"source registry has dangling references: families={unknown_family_refs} fallbacks={unknown_fallback_refs}"
        )
    overstated = [
        item["source_id"]
        for item in registry["sources"]
        if item.get("status") != "unverified"
        or item.get("last_verified_at") is not None
        or item.get("last_verification_basis") is not None
    ]
    if overstated:
        raise AssertionError(f"source registry overstates unperformed live verification: {overstated}")


def test_package_standalone_gate() -> None:
    windows_relative = contract_utils.canonical_relative_path(
        PureWindowsPath(r"C:\research\run\packs\image_pack\06_output\reference_board.html"),
        PureWindowsPath(r"C:\research\run"),
    )
    if windows_relative != "packs/image_pack/06_output/reference_board.html":
        raise AssertionError(f"contract path is not platform-neutral: {windows_relative}")
    powershell_text = (PACKAGE_ROOT / "scripts/preflight.ps1").read_text(encoding="utf-8")
    for marker in (
        "function Invoke-PythonCommand",
        '$ErrorActionPreference = "Continue"',
        "$Command.Path",
        "run_name='__main__'",
    ):
        if marker not in powershell_text:
            raise AssertionError(f"PowerShell 5.1 compatibility guard is missing: {marker}")
    if 'run_name="__main__"' in powershell_text:
        raise AssertionError("PowerShell 5.1 strips nested double quotes from the Python -c argument")
    skill_text = (PACKAGE_ROOT / "SKILL.md").read_text(encoding="utf-8")
    preflight = "\n".join(skill_text.splitlines()[:35])
    for marker in (
        "Standalone Package Preflight",
        "standalone_package",
        "package_contract_ready=true",
        "does not inspect, invoke, or depend on any",
    ):
        if marker not in preflight:
            raise AssertionError(f"package standalone gate is missing or too late: {marker}")
    forbidden = ("HIGH_CONTROL_RELEASE_GATE", "release-control", "SUITE_MANIFEST", "ready_latest")
    checked = [PACKAGE_ROOT / "SKILL.md", PACKAGE_ROOT / "references" / "activation_and_release_boundary.md"]
    for path in checked:
        text = path.read_text(encoding="utf-8")
        for marker in forbidden:
            if marker in text:
                raise AssertionError(f"standalone package retains forbidden sibling coupling {marker}: {path}")


def main() -> int:
    tests = [
        test_validator_and_adversarial,
        test_parallel_both,
        test_full_ledger_and_pack_isolation,
        test_approach_accounting_and_failure_registry,
        test_dedup_and_gallery,
        test_dedup_fingerprint_evidence,
        test_pareto_dominance,
        test_agent_independence_and_blind_handoffs,
        test_feedback_learning_chain,
        test_http_boundary,
        test_tool_fail_closed_and_history_safety,
        test_strict_evidence_boundaries,
        test_schema_keyword_enforcement,
        test_package_standalone_gate,
    ]
    failures = []
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:  # deterministic harness should report every failed family
            failures.append((test.__name__, str(exc)))
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(json.dumps({"failures": failures}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(f"PASS all {len(tests)} test families")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
