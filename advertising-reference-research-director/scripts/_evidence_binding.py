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
    projection = {
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
            if not registry.get("append_only_plan") or item.get("approach_id") in registry["append_only_plan"]["base_approach_ids"]
        ],
    }
    # Legacy hashes are byte-for-byte unchanged. Capacity policy is prospective:
    # adding it to an old plan changes the hash and cannot silently relax it.
    if registry.get("independence_policy", {}).get("profile"):
        projection["independence_policy"] = registry["independence_policy"]
    return projection


def approach_plan_sha256(registry: dict[str, Any]) -> str:
    return canonical_sha256(approach_plan_projection(registry))


def approach_wave_sha256(registry: dict[str, Any], wave: dict[str, Any]) -> str:
    plans = approach_plan_projection({**registry, "append_only_plan": None})["approaches"]
    return canonical_sha256({
        "base_plan_sha256": registry["registration"]["plan_sha256"],
        "wave_id": wave["wave_id"], "parent_plan_sha256": wave["parent_plan_sha256"],
        "frozen_at": wave["frozen_at"], "trigger": wave["trigger"],
        "approach_ids": wave["approach_ids"],
        "approaches": [p for p in plans if p["approach_id"] in wave["approach_ids"]],
    })


def approach_registration_bindings(registry: dict[str, Any]) -> dict[str, tuple[str, str]]:
    """Validate the append chain; bind each immutable approach to its own freeze.

    Raises ValueError for malformed or rewritten history. This is internal
    consistency, not external timestamp attestation.
    """
    base = registry["registration"]
    validate_capacity4_registration(registry)
    if approach_plan_sha256(registry) != base["plan_sha256"]:
        raise ValueError("base plan hash mismatch")
    agent_roles = {
        a["agent_id"]: {a["role"], *a.get("additional_roles", [])}
        for a in registry["agents"]
    }
    discovery_roles = {"search_scout", "credit_graph_scout", "authenticated_source_operator"}
    capacity4 = registry.get("independence_policy", {}).get("profile") == "capacity4_staged_v1"
    for approach in registry["approaches"]:
        roles = agent_roles.get(approach.get("executing_agent_id"), set())
        if not roles & discovery_roles or (capacity4 and "search_scout" not in roles):
            raise ValueError("approach executor lacks an eligible discovery role; capacity4 permits only its finder identity")
    ids = [a["approach_id"] for a in registry["approaches"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate approach IDs")
    append = registry.get("append_only_plan")
    base_ids = append["base_approach_ids"] if append else ids
    if len(base_ids) != len(set(base_ids)) or not set(base_ids).issubset(ids):
        raise ValueError("invalid base approach IDs")
    bindings = {i: (base["plan_sha256"], base["frozen_at"]) for i in base_ids}
    previous = base["plan_sha256"]
    previous_time = base["frozen_at"]
    from datetime import datetime
    stamp = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
    wave_ids = set()
    for wave in append.get("waves", []) if append else []:
        if wave["wave_id"] in wave_ids or wave["parent_plan_sha256"] != previous:
            raise ValueError("duplicate wave or broken parent hash")
        wave_ids.add(wave["wave_id"])
        if stamp(wave["frozen_at"]) <= stamp(previous_time):
            raise ValueError("wave freeze is not strictly after its parent")
        assigned = wave["approach_ids"]
        if not assigned or len(assigned) != len(set(assigned)) or set(assigned) & bindings.keys() or not set(assigned).issubset(ids):
            raise ValueError("wave approaches overlap, are empty, or are missing")
        if approach_wave_sha256(registry, wave) != wave["plan_sha256"]:
            raise ValueError("wave plan hash mismatch")
        bindings.update({i: (wave["plan_sha256"], wave["frozen_at"]) for i in assigned})
        previous, previous_time = wave["plan_sha256"], wave["frozen_at"]
    if set(bindings) != set(ids):
        raise ValueError("unregistered appended approaches")
    query_ids = [q["query_id"] for a in registry["approaches"] for q in a["queries"]]
    if len(query_ids) != len(set(query_ids)):
        raise ValueError("query IDs must be globally unique across waves")
    return bindings


def validate_capacity4_registration(registry: dict[str, Any]) -> None:
    """Check the prospective four-actor assignment before any searches start."""
    if registry.get("independence_policy", {}).get("profile") != "capacity4_staged_v1":
        return
    agents = registry.get("agents", [])
    roles = {a["agent_id"]: {a["role"], *a.get("additional_roles", [])} for a in agents}
    owners = lambda role: {aid for aid, assigned in roles.items() if role in assigned}
    groups = [owners("search_scout"), owners("capture_operator"), owners("verification_agent"), owners("adversarial_auditor")]
    if (len(agents) != 4 or len(roles) != 4 or any(len(s) != 1 for s in groups)
            or len(set().union(*groups)) != 4
            or owners("relevance_curator") != groups[0]
            or owners("root_synthesizer") != groups[1]
            or owners("diversity_curator") != groups[2]
            or any(roles[aid] != {"adversarial_auditor"} for aid in groups[3])
            or registry["independence_policy"].get("decision_roles_use_distinct_agent_ids") is not False):
        raise ValueError("capacity4 must prospectively assign exactly four real actors to finder/relevance, capture/root, verifier/diversity, auditor-only")


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

    projection = {
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
    # New policies are opt-in and hash-bound. Preserve byte projections for
    # historical runs which did not declare them; never silently reinterpret one.
    if "coverage_policy" in intent:
        projection["coverage_policy"] = intent["coverage_policy"]
    if "profile" in intent.get("diversity_requirements", {}):
        projection["diversity_requirements"] = intent["diversity_requirements"]
    return projection


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
