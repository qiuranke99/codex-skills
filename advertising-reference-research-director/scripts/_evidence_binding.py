#!/usr/bin/env python3
"""Canonical integrity projections for plans and imported browser capture records.

These hashes bind finalized artifacts to one another. They are not digital
signatures and do not prove that a browser tool or human actually made the
declared observation.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


CANONICALIZATION = "sorted-json-v1"
REPORT_TRUST_STATEMENT = (
    "Hash bindings establish internal artifact consistency only; browser actions are not "
    "cryptographically attested, contract eligibility is not production delivery, third-party "
    "access may change, and no reuse rights are granted."
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def approach_plan_projection(registry: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": registry.get("run_id"),
        "intent_id": registry.get("intent_id"),
        "intent_version": registry.get("intent_version"),
        "registration": {
            "kind": registry.get("registration", {}).get("kind"),
            "frozen_at": registry.get("registration", {}).get("frozen_at"),
            "canonicalization": registry.get("registration", {}).get("canonicalization"),
        },
        "agents": [
            {
                "agent_id": item.get("agent_id"),
                "role": item.get("role"),
                "additional_roles": item.get("additional_roles", []),
                "access_scope": item.get("access_scope"),
                "session_owner": item.get("session_owner"),
            }
            for item in registry.get("agents", [])
        ],
        "approaches": [
            {
                "approach_id": item.get("approach_id"),
                "pack_id": item.get("pack_id"),
                "modality": item.get("modality"),
                "decision_axis": item.get("decision_axis"),
                "method": item.get("method"),
                "hypothesis": item.get("hypothesis"),
                "queries": item.get("queries"),
                "source_family_ids": item.get("source_family_ids"),
                "executing_agent_id": item.get("executing_agent_id"),
                "favored_route_disclosed": item.get("favored_route_disclosed"),
            }
            for item in registry.get("approaches", [])
        ],
    }


def approach_plan_sha256(registry: dict[str, Any]) -> str:
    return canonical_sha256(approach_plan_projection(registry))


def dedup_comparison_projection(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project the final comparison set onto identity and media-fingerprint evidence."""
    return sorted(
        [
            {
                "candidate_id": item.get("candidate_id"),
                "modality": item.get("modality"),
                "canonical_url_key": item.get("dedup", {}).get("canonical_url_key"),
                "stable_id_key": item.get("dedup", {}).get("stable_id_key"),
                "fingerprint": item.get("dedup", {}).get("fingerprint"),
                "near_duplicate_group_id": item.get("dedup", {}).get("near_duplicate_group_id"),
                "version_relation": item.get("dedup", {}).get("version_relation"),
            }
            for item in candidates
        ],
        key=lambda item: str(item.get("candidate_id")),
    )


def dedup_comparison_set_sha256(candidates: list[dict[str, Any]]) -> str:
    return canonical_sha256(dedup_comparison_projection(candidates))


def intent_constraints_projection(intent: dict[str, Any]) -> dict[str, Any]:
    """Project every frozen field that can change candidate relevance or eligibility."""

    return {
        "run_id": intent.get("run_id"),
        "intent_id": intent.get("intent_id"),
        "intent_version": intent.get("intent_version"),
        "decision_to_inform": intent.get("decision_to_inform"),
        "subject": intent.get("subject"),
        "modality_route": intent.get("modality_route"),
        "routing": intent.get("routing"),
        "scene_scale": intent.get("scene_scale"),
        "human_presence": intent.get("human_presence"),
        "visual_axes": intent.get("visual_axes"),
        "temporal_axes": intent.get("temporal_axes"),
        "must_have": intent.get("must_have"),
        "must_not_have": intent.get("must_not_have"),
        "positive_anchors": intent.get("positive_anchors"),
        "negative_anchors": intent.get("negative_anchors"),
        "market_region": intent.get("market_region"),
        "languages": intent.get("languages"),
        "content_max_age_days": intent.get("freshness_need", {}).get("content_max_age_days"),
        "rights_scope": intent.get("rights_scope"),
    }


def intent_constraints_sha256(intent: dict[str, Any]) -> str:
    return canonical_sha256(intent_constraints_projection(intent))


def curation_input_projection(
    intent: dict[str, Any],
    shortlist: dict[str, Any],
    candidates: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Bind both blind curators to the same frozen, qualified input set."""

    ordered_ids = shortlist.get("candidate_ids", [])
    candidate_index = {item.get("candidate_id"): item for item in candidates}
    receipt_index = {item.get("candidate_id"): item for item in receipts}
    return {
        "intent_constraints": intent_constraints_projection(intent),
        "shortlist": shortlist,
        "candidates": [candidate_index.get(candidate_id) for candidate_id in ordered_ids],
        "receipts": [receipt_index.get(candidate_id) for candidate_id in ordered_ids],
    }


def curation_input_sha256(
    intent: dict[str, Any],
    shortlist: dict[str, Any],
    candidates: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
) -> str:
    return canonical_sha256(curation_input_projection(intent, shortlist, candidates, receipts))
