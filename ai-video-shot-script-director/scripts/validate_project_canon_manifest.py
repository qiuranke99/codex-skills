#!/usr/bin/env python3
"""Validate PROJECT_CANON_MANIFEST without third-party dependencies."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
SHA = re.compile(r"^[a-f0-9]{64}$")
APPROVALS = {"draft", "assistant_validated", "user_approved", "stale", "blocked"}
ROOT_FIELDS = {
    "contract_version", "artifact_id", "owner_skill", "version", "sha256",
    "approval_status", "dependencies", "affected_shot_uids", "stale_reason",
    "schema_version", "project_id", "manifest_role", "manifest_update_policy",
    "current_phase", "revision_counter", "updated_by_skill", "base_manifest_sha256",
    "canonical_shot_uids", "active_artifacts", "superseded_artifacts",
    "dependency_edges", "stale_events", "unresolved_change_requests",
}
ARTIFACT_FIELDS = {
    "artifact_slot", "artifact_id", "artifact_type", "owner_skill", "version", "sha256",
    "approval_status", "stale_reason", "eligible_for_downstream", "affected_shot_uids",
    "locator", "file_sha256", "artifact_record_locator", "artifact_record_file_sha256", "dependencies",
}
EDGE_FIELDS = {"producer_artifact_id", "consumer_artifact_id", "producer_sha256", "affected_shot_uids"}
STALE_EVENT_FIELDS = {"event_id", "changed_artifact_id", "stale_artifact_ids", "affected_shot_uids", "reason"}
CHANGE_REQUEST_FIELDS = {"request_id", "requesting_skill", "target_owner_skill", "affected_shot_uids", "reason", "required_resolution"}
PHASES = {
    "intake", "professional_script", "canon_assets", "global_look", "storyboard_structure",
    "storyboard_final", "timing_animatic_v1", "keyframes", "core_keyframes_k1",
    "prompt_preflight", "generation_unit_preflight_p1", "boundary_supplement_k2",
    "control_previs_v2", "prompt_compile", "prompt_compile_p2", "user_review_revision",
}


def canonical_hash(record: dict[str, Any]) -> str:
    payload = copy.deepcopy(record)
    payload.pop("sha256", None)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA.fullmatch(value))


def _is_semver(value: Any) -> bool:
    return isinstance(value, str) and bool(SEMVER.fullmatch(value))


def _is_safe_project_locator(value: Any) -> bool:
    if not _is_text(value):
        return False
    if "\\" in value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        return False
    return ".." not in PurePosixPath(value).parts


def verify_artifact_files(data: dict[str, Any], project_root: Path) -> list[str]:
    """Bind primary bytes and a complete canonical artifact-record sidecar."""
    errors: list[str] = []
    root = project_root.resolve()
    for collection in ("active_artifacts", "superseded_artifacts"):
        entries = data.get(collection)
        for index, entry in enumerate(entries if isinstance(entries, list) else []):
            if not isinstance(entry, dict):
                continue
            locator = entry.get("locator")
            file_hash = entry.get("file_sha256")
            record_locator = entry.get("artifact_record_locator")
            record_file_hash = entry.get("artifact_record_file_sha256")
            label = f"{collection}[{index}]"
            if locator is None and file_hash is None and record_locator is None and record_file_hash is None:
                continue
            if not _is_safe_project_locator(locator) or not _is_sha(file_hash) or not _is_safe_project_locator(record_locator) or not _is_sha(record_file_hash):
                errors.append(f"{label} primary/record locator hash pairs are not verifiable")
                continue
            candidate = (root / locator).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                errors.append(f"{label} locator escapes project root")
                continue
            if not candidate.is_file():
                errors.append(f"{label} artifact file missing: {locator}")
                continue
            actual_file_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if actual_file_hash != file_hash:
                errors.append(f"{label} file_sha256 mismatch")
                continue
            record_path = (root / record_locator).resolve()
            try:
                record_path.relative_to(root)
            except ValueError:
                errors.append(f"{label} artifact_record_locator escapes project root")
                continue
            if record_path.suffix.lower() != ".json" or not record_path.is_file():
                errors.append(f"{label} artifact record must be an existing JSON file")
                continue
            if hashlib.sha256(record_path.read_bytes()).hexdigest() != record_file_hash:
                errors.append(f"{label} artifact_record_file_sha256 mismatch")
                continue
            try:
                artifact = json.loads(record_path.read_text(encoding="utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                errors.append(f"{label} JSON artifact record unreadable: {exc}")
                continue
            if not isinstance(artifact, dict):
                errors.append(f"{label} JSON artifact record root must be object")
                continue
            for field in ("artifact_id", "owner_skill", "version", "sha256", "dependencies", "affected_shot_uids"):
                if artifact.get(field) != entry.get(field):
                    errors.append(f"{label} artifact record {field} differs from Canon entry")
            status_matches = (
                artifact.get("approval_status") == entry.get("approval_status")
                and artifact.get("stale_reason") == entry.get("stale_reason")
            )
            if not status_matches:
                overlay_allowed = (
                    collection == "active_artifacts"
                    and artifact.get("approval_status") in {"assistant_validated", "user_approved"}
                    and artifact.get("stale_reason") is None
                    and entry.get("approval_status") in {"stale", "blocked"}
                    and entry.get("eligible_for_downstream") is False
                    and isinstance(entry.get("stale_reason"), str)
                    and bool(entry["stale_reason"].strip())
                )
                matching_events = [
                    event for event in data.get("stale_events", [])
                    if isinstance(event, dict)
                    and entry.get("artifact_id") in event.get("stale_artifact_ids", [])
                    and event.get("affected_shot_uids") == entry.get("affected_shot_uids")
                    and event.get("reason") == entry.get("stale_reason")
                ]
                if not overlay_allowed or len(matching_events) != 1:
                    errors.append(
                        f"{label} artifact record status differs without one exact event-bound Canon stale overlay"
                    )
            artifact_hash = artifact.get("sha256")
            if artifact_hash is not None:
                try:
                    expected = canonical_hash(artifact)
                except (TypeError, ValueError) as exc:
                    errors.append(f"{label} artifact record is not canonical: {exc}")
                else:
                    if artifact_hash != expected:
                        errors.append(f"{label} artifact record carries a pseudo/non-canonical sha256")
    return errors


def _validate_manifest(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(ROOT_FIELDS - data.keys())
    if missing:
        errors.append("missing root fields: " + ", ".join(missing))
    extra = sorted(set(data) - ROOT_FIELDS)
    if extra:
        errors.append("unexpected root fields: " + ", ".join(extra))

    if data.get("contract_version") != "ai-video-artifact-v1":
        errors.append("contract_version must be ai-video-artifact-v1")
    if data.get("schema_version") != "ai-video-project-canon-manifest.v1":
        errors.append("schema_version must be ai-video-project-canon-manifest.v1")
    if data.get("owner_skill") != "ai-video-shot-script-director":
        errors.append("owner_skill must be ai-video-shot-script-director")
    if data.get("manifest_role") != "artifact_registry_only":
        errors.append("manifest_role must be artifact_registry_only")
    if data.get("manifest_update_policy") != "validated_atomic_delta_no_reverse_dependency":
        errors.append("invalid manifest_update_policy")
    if not _is_text(data.get("artifact_id")) or not str(data["artifact_id"]).startswith("PROJECT_CANON_MANIFEST_"):
        errors.append("artifact_id must start with PROJECT_CANON_MANIFEST_")
    if not _is_semver(data.get("version")):
        errors.append("version must be SemVer x.y.z")
    if not _is_text(data.get("project_id")):
        errors.append("project_id is required")
    if not _is_text(data.get("updated_by_skill")):
        errors.append("updated_by_skill is required")
    if data.get("current_phase") not in PHASES:
        errors.append("current_phase invalid")
    if not isinstance(data.get("revision_counter"), int) or isinstance(data.get("revision_counter"), bool) or data.get("revision_counter", -1) < 0:
        errors.append("revision_counter must be a non-negative integer")
    if data.get("dependencies") != []:
        errors.append("manifest envelope dependencies must stay empty to prevent hash cycles")

    approval = data.get("approval_status")
    if approval not in APPROVALS:
        errors.append("invalid approval_status")
    digest = data.get("sha256")
    if approval == "draft":
        if digest is not None:
            errors.append("draft manifest sha256 must be null")
    elif not _is_sha(digest):
        errors.append("non-draft manifest requires canonical sha256")
    else:
        try:
            expected = canonical_hash(data)
        except (TypeError, ValueError) as exc:
            errors.append(f"manifest is not canonical JSON: {exc}")
        else:
            if digest != expected:
                errors.append(f"manifest sha256 mismatch: expected {expected}")

    stale_reason = data.get("stale_reason")
    if approval == "stale" and not _is_text(stale_reason):
        errors.append("stale manifest requires stale_reason")
    if approval != "stale" and stale_reason is not None:
        errors.append("non-stale manifest must have stale_reason null")
    base_hash = data.get("base_manifest_sha256")
    if base_hash is not None and not _is_sha(base_hash):
        errors.append("base_manifest_sha256 must be null or sha256")

    shot_uids = data.get("canonical_shot_uids")
    if not isinstance(shot_uids, list) or not all(_is_text(uid) for uid in shot_uids):
        errors.append("canonical_shot_uids must be a string array")
        shot_uids = []
    elif len(shot_uids) != len(set(shot_uids)):
        errors.append("canonical_shot_uids must be unique")
    if data.get("affected_shot_uids") != shot_uids:
        errors.append("affected_shot_uids must exactly equal canonical_shot_uids")
    shot_set = set(shot_uids)

    active = data.get("active_artifacts")
    if not isinstance(active, list):
        errors.append("active_artifacts must be an array")
        active = []
    active_by_id: dict[str, dict[str, Any]] = {}
    slots: list[str] = []
    manifest_id = data.get("artifact_id")
    for index, entry in enumerate(active):
        label = f"active_artifacts[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue
        if set(entry) != ARTIFACT_FIELDS:
            errors.append(f"{label} must contain exact artifact-entry fields")
        entry_id = entry.get("artifact_id")
        slot = entry.get("artifact_slot")
        if not _is_text(entry_id) or not _is_text(slot) or not _is_text(entry.get("artifact_type")) or not _is_text(entry.get("owner_skill")):
            errors.append(f"{label} missing identity fields")
            continue
        if entry_id == manifest_id:
            errors.append(f"{label} must not register the manifest itself")
        if entry_id in active_by_id:
            errors.append(f"duplicate active artifact_id {entry_id}")
        active_by_id[entry_id] = entry
        slots.append(slot)
        if not _is_semver(entry.get("version")):
            errors.append(f"{label} version invalid")
        status = entry.get("approval_status")
        if status not in APPROVALS:
            errors.append(f"{label} invalid approval_status")
        if status == "draft":
            if entry.get("sha256") is not None:
                errors.append(f"{label} draft sha256 must be null")
        elif not _is_sha(entry.get("sha256")):
            errors.append(f"{label} non-draft hash invalid")
        eligible = entry.get("eligible_for_downstream")
        if not isinstance(eligible, bool):
            errors.append(f"{label} eligible_for_downstream must be boolean")
        if eligible and (status not in {"assistant_validated", "user_approved"} or entry.get("stale_reason") is not None):
            errors.append(f"{label} cannot be downstream-eligible")
        if status == "stale" and not _is_text(entry.get("stale_reason")):
            errors.append(f"{label} stale artifact requires stale_reason")
        if status != "stale" and entry.get("stale_reason") is not None:
            errors.append(f"{label} non-stale artifact must have stale_reason null")
        scope = entry.get("affected_shot_uids")
        if not isinstance(scope, list) or not all(_is_text(uid) for uid in scope) or not set(scope).issubset(shot_set):
            errors.append(f"{label} affected_shot_uids must be a subset of canonical shots")
        file_hash = entry.get("file_sha256")
        if file_hash is not None and not _is_sha(file_hash):
            errors.append(f"{label} file_sha256 invalid")
        locator = entry.get("locator")
        record_locator = entry.get("artifact_record_locator")
        record_file_hash = entry.get("artifact_record_file_sha256")
        if locator is not None and not _is_safe_project_locator(locator):
            errors.append(f"{label} locator must be a safe project-relative path")
        if (locator is None) != (file_hash is None):
            errors.append(f"{label} locator and file_sha256 must be supplied together")
        if (record_locator is None) != (record_file_hash is None):
            errors.append(f"{label} artifact record locator and hash must be supplied together")
        if record_locator is not None and (not _is_safe_project_locator(record_locator) or not str(record_locator).lower().endswith(".json")):
            errors.append(f"{label} artifact_record_locator must be a safe project-relative JSON path")
        if record_file_hash is not None and not _is_sha(record_file_hash):
            errors.append(f"{label} artifact_record_file_sha256 invalid")
        if eligible and (not _is_safe_project_locator(locator) or not _is_sha(file_hash) or not _is_safe_project_locator(record_locator) or not str(record_locator).lower().endswith(".json") or not _is_sha(record_file_hash)):
            errors.append(f"{label} downstream-eligible artifact requires verifiable primary and artifact-record locator/hash pairs")
        deps = entry.get("dependencies")
        if not isinstance(deps, list):
            errors.append(f"{label} dependencies must be an array")
            continue
        for dep_index, dep in enumerate(deps):
            dep_label = f"{label}.dependencies[{dep_index}]"
            if not isinstance(dep, dict) or set(dep) != {"artifact_id", "owner_skill", "version", "sha256"}:
                errors.append(f"{dep_label} must contain exact dependency fields")
                continue
            if dep.get("artifact_id") == manifest_id:
                errors.append(f"{dep_label} reverse dependency on manifest is forbidden")
            if not _is_text(dep.get("artifact_id")) or not _is_text(dep.get("owner_skill")) or not _is_semver(dep.get("version")) or not _is_sha(dep.get("sha256")):
                errors.append(f"{dep_label} values invalid")
    if len(slots) != len(set(slots)):
        errors.append("active_artifacts must have at most one entry per artifact_slot")

    # Index history before validating edges.  A current stale/blocked consumer is
    # allowed to retain the exact producer lock it actually consumed even after
    # that producer has been superseded; rewriting that dependency to the new
    # producer would falsify provenance.
    superseded = data.get("superseded_artifacts")
    if not isinstance(superseded, list):
        errors.append("superseded_artifacts must be an array")
        superseded = []
    superseded_by_id: dict[str, dict[str, Any]] = {}
    for entry in superseded:
        if isinstance(entry, dict) and _is_text(entry.get("artifact_id")) and entry.get("artifact_id") not in superseded_by_id:
            superseded_by_id[entry["artifact_id"]] = entry
    all_by_id = {**superseded_by_id, **active_by_id}

    edges = data.get("dependency_edges")
    if not isinstance(edges, list):
        errors.append("dependency_edges must be an array")
        edges = []
    graph: dict[str, set[str]] = {artifact_id: set() for artifact_id in all_by_id}
    edge_keys: set[tuple[str, str]] = set()
    for index, edge in enumerate(edges):
        label = f"dependency_edges[{index}]"
        if not isinstance(edge, dict):
            errors.append(f"{label} must be an object")
            continue
        if set(edge) != EDGE_FIELDS:
            errors.append(f"{label} must contain exact dependency-edge fields")
        producer = edge.get("producer_artifact_id")
        consumer = edge.get("consumer_artifact_id")
        if producer not in all_by_id or consumer not in all_by_id:
            errors.append(f"{label} endpoints must be known active or superseded artifacts")
            continue
        if producer == consumer:
            errors.append(f"{label} self dependency is forbidden")
        if edge.get("producer_sha256") != all_by_id[producer].get("sha256"):
            errors.append(f"{label} producer_sha256 does not match registered producer")
        edge_scope = edge.get("affected_shot_uids")
        if not isinstance(edge_scope, list) or not set(edge_scope).issubset(shot_set):
            errors.append(f"{label} affected_shot_uids invalid")
        edge_key = (producer, consumer)
        if edge_key in edge_keys:
            errors.append(f"{label} duplicate dependency edge")
        edge_keys.add(edge_key)
        graph.setdefault(producer, set()).add(consumer)

    historical_active_dependencies: list[tuple[str, str]] = []
    for consumer_id, entry in active_by_id.items():
        for dep in entry.get("dependencies", []):
            if not isinstance(dep, dict):
                continue
            producer_id = dep.get("artifact_id")
            producer = active_by_id.get(producer_id)
            producer_is_history = False
            if producer is None:
                producer = superseded_by_id.get(producer_id)
                producer_is_history = producer is not None
            if producer is None:
                errors.append(f"{consumer_id} dependency {producer_id!r} is not registered")
                continue
            if dep.get("owner_skill") != producer.get("owner_skill") or dep.get("version") != producer.get("version") or dep.get("sha256") != producer.get("sha256"):
                errors.append(f"{consumer_id} dependency lock does not match registered {producer_id}")
            consumer_status = entry.get("approval_status")
            producer_status = producer.get("approval_status")
            if producer_is_history:
                if consumer_status not in {"stale", "blocked"} or entry.get("eligible_for_downstream") is not False or not _is_text(entry.get("stale_reason")):
                    errors.append(f"{consumer_id} may retain superseded dependency {producer_id} only while stale/blocked and downstream-ineligible")
                else:
                    historical_active_dependencies.append((producer_id, consumer_id))
            elif entry.get("eligible_for_downstream") is True and producer.get("eligible_for_downstream") is not True:
                errors.append(f"{consumer_id} downstream-eligible consumer depends on ineligible producer {producer_id}")
            if not producer_is_history and producer_status in {"stale", "blocked"} and consumer_status not in {"stale", "blocked"}:
                errors.append(f"{consumer_id} must be stale/blocked because producer {producer_id} is {producer_status}")
            if (producer_id, consumer_id) not in edge_keys:
                errors.append(f"missing dependency_edge {producer_id} -> {consumer_id}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            errors.append(f"dependency cycle detected at {node}")
            return
        if node in visited:
            return
        visiting.add(node)
        for next_node in graph.get(node, set()):
            visit(next_node)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)

    superseded_ids: set[str] = set()
    for index, entry in enumerate(superseded):
        label = f"superseded_artifacts[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue
        if set(entry) != ARTIFACT_FIELDS | {"superseded_by_artifact_id"}:
            errors.append(f"{label} must contain exact superseded-entry fields")
        entry_id = entry.get("artifact_id")
        if not _is_text(entry_id) or entry_id in superseded_ids:
            errors.append(f"{label} artifact_id missing or duplicate")
        elif entry_id in active_by_id:
            errors.append(f"{label} artifact_id must not also be active")
        else:
            superseded_ids.add(entry_id)
        if not _is_text(entry.get("artifact_slot")) or not _is_text(entry.get("artifact_type")) or not _is_text(entry.get("owner_skill")):
            errors.append(f"{label} missing identity fields")
        if not _is_semver(entry.get("version")) or not _is_sha(entry.get("sha256")):
            errors.append(f"{label} version/hash invalid")
        locator = entry.get("locator")
        file_hash = entry.get("file_sha256")
        record_locator = entry.get("artifact_record_locator")
        record_file_hash = entry.get("artifact_record_file_sha256")
        if not _is_safe_project_locator(locator) or not _is_sha(file_hash) or not _is_safe_project_locator(record_locator) or not str(record_locator).lower().endswith(".json") or not _is_sha(record_file_hash):
            errors.append(f"{label} superseded artifact requires verifiable primary and artifact-record locator/hash pairs")
        if entry.get("eligible_for_downstream") is not False:
            errors.append(f"{label} must not be downstream-eligible")
        replacement = entry.get("superseded_by_artifact_id")
        replacement_entry = all_by_id.get(replacement)
        if replacement_entry is None or replacement == entry_id:
            errors.append(f"{label} superseded_by_artifact_id must identify a different registered artifact")
        else:
            for field in ("artifact_slot", "artifact_type", "owner_skill"):
                if replacement_entry.get(field) != entry.get(field):
                    errors.append(f"{label} replacement must preserve {field}")
            if _is_semver(entry.get("version")) and _is_semver(replacement_entry.get("version")):
                old_version = tuple(int(part) for part in entry["version"].split("."))
                new_version = tuple(int(part) for part in replacement_entry["version"].split("."))
                if new_version <= old_version:
                    errors.append(f"{label} replacement version must be greater than superseded version")
        deps = entry.get("dependencies")
        if not isinstance(deps, list):
            errors.append(f"{label} dependencies must be an array")
        else:
            for dep_index, dep in enumerate(deps):
                if not isinstance(dep, dict) or set(dep) != {"artifact_id", "owner_skill", "version", "sha256"}:
                    errors.append(f"{label}.dependencies[{dep_index}] must contain exact dependency fields")
                    continue
                producer_id = dep.get("artifact_id")
                producer = all_by_id.get(producer_id)
                if producer is None:
                    errors.append(f"{label}.dependencies[{dep_index}] references unregistered historical producer {producer_id!r}")
                    continue
                if any(dep.get(field) != producer.get(field) for field in ("owner_skill", "version", "sha256")):
                    errors.append(f"{label}.dependencies[{dep_index}] lock does not match registered {producer_id}")
                if (producer_id, entry_id) not in edge_keys:
                    errors.append(f"missing dependency_edge {producer_id} -> {entry_id}")

    # Supersession itself is historical provenance and must also be acyclic.
    supersession_graph: dict[str, str] = {
        entry_id: str(entry.get("superseded_by_artifact_id"))
        for entry_id, entry in superseded_by_id.items()
        if _is_text(entry.get("superseded_by_artifact_id"))
    }
    for start in supersession_graph:
        seen: set[str] = set()
        node = start
        while node in supersession_graph:
            if node in seen:
                errors.append(f"supersession cycle detected at {node}")
                break
            seen.add(node)
            node = supersession_graph[node]

    stale_events = data.get("stale_events")
    if not isinstance(stale_events, list):
        errors.append("stale_events must be an array")
        stale_events = []
    event_ids: set[str] = set()
    known_ids = set(active_by_id) | superseded_ids
    for index, event in enumerate(stale_events):
        label = f"stale_events[{index}]"
        if not isinstance(event, dict) or set(event) != STALE_EVENT_FIELDS:
            errors.append(f"{label} must contain exact stale-event fields")
            continue
        event_id = event.get("event_id")
        if not _is_text(event_id) or event_id in event_ids:
            errors.append(f"{label} event_id missing or duplicate")
        else:
            event_ids.add(event_id)
        if event.get("changed_artifact_id") not in known_ids:
            errors.append(f"{label} changed_artifact_id unknown")
        stale_ids = event.get("stale_artifact_ids")
        if not isinstance(stale_ids, list) or not stale_ids or not all(_is_text(item) for item in stale_ids) or len(stale_ids) != len(set(stale_ids)) or not set(stale_ids).issubset(known_ids):
            errors.append(f"{label} stale_artifact_ids invalid")
        scope = event.get("affected_shot_uids")
        if not isinstance(scope, list) or not all(_is_text(item) for item in scope) or not set(scope).issubset(shot_set):
            errors.append(f"{label} affected_shot_uids invalid")
        if not _is_text(event.get("reason")):
            errors.append(f"{label} reason required")

    # A stale current consumer that retains an immutable historical producer
    # lock needs an exact propagation event.  The event names the replacement
    # that caused staleness, the current consumer, and precisely the consumer's
    # affected shot scope.
    for producer_id, consumer_id in historical_active_dependencies:
        replacement_id = superseded_by_id[producer_id].get("superseded_by_artifact_id")
        consumer_scope = active_by_id[consumer_id].get("affected_shot_uids")
        matches = [
            event for event in stale_events
            if isinstance(event, dict)
            and event.get("changed_artifact_id") == replacement_id
            and isinstance(event.get("stale_artifact_ids"), list)
            and consumer_id in event["stale_artifact_ids"]
            and event.get("affected_shot_uids") == consumer_scope
            and _is_text(event.get("reason"))
        ]
        if len(matches) != 1:
            errors.append(
                f"{consumer_id} historical dependency {producer_id} requires exactly one complete stale_event from replacement {replacement_id}"
            )

    # Every declared edge must be backed by the consumer's exact dependency
    # lock.  This rejects fabricated history edges that are not present in the
    # immutable consumer artifact.
    for producer_id, consumer_id in edge_keys:
        consumer = all_by_id.get(consumer_id)
        producer = all_by_id.get(producer_id)
        if consumer is None or producer is None:
            continue
        deps = consumer.get("dependencies")
        backed = any(
            isinstance(dep, dict)
            and dep.get("artifact_id") == producer_id
            and all(dep.get(field) == producer.get(field) for field in ("owner_skill", "version", "sha256"))
            for dep in deps if isinstance(deps, list)
        )
        if not backed:
            errors.append(f"dependency_edge {producer_id} -> {consumer_id} is not backed by the consumer dependency lock")

    requests = data.get("unresolved_change_requests")
    if not isinstance(requests, list):
        errors.append("unresolved_change_requests must be an array")
        requests = []
    request_ids: set[str] = set()
    for index, request in enumerate(requests):
        label = f"unresolved_change_requests[{index}]"
        if not isinstance(request, dict) or set(request) != CHANGE_REQUEST_FIELDS:
            errors.append(f"{label} must contain exact change-request fields")
            continue
        request_id = request.get("request_id")
        if not _is_text(request_id) or request_id in request_ids:
            errors.append(f"{label} request_id missing or duplicate")
        else:
            request_ids.add(request_id)
        for field in ("requesting_skill", "target_owner_skill", "reason", "required_resolution"):
            if not _is_text(request.get(field)):
                errors.append(f"{label} {field} required")
        scope = request.get("affected_shot_uids")
        if not isinstance(scope, list) or not all(_is_text(item) for item in scope) or not set(scope).issubset(shot_set):
            errors.append(f"{label} affected_shot_uids invalid")

    return errors


def validate_manifest(data: dict[str, Any]) -> list[str]:
    try:
        return _validate_manifest(data)
    except (TypeError, KeyError, AttributeError, ValueError, OverflowError) as exc:
        return [f"malformed manifest rejected safely: {type(exc).__name__}: {exc}"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--verify-files-root", type=Path, help="resolve every registered locator and verify file/envelope hashes")
    args = parser.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read manifest: {exc}")
        return 2
    if not isinstance(data, dict):
        print("ERROR: manifest root must be an object")
        return 2
    errors = validate_manifest(data)
    if data.get("approval_status") != "draft" and args.verify_files_root is None:
        errors.append("non-draft Project Canon requires --verify-files-root")
    if args.verify_files_root is not None:
        errors.extend(verify_artifact_files(data, args.verify_files_root))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: PROJECT_CANON_MANIFEST is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
