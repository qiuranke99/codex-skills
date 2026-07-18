#!/usr/bin/env python3
"""Strict, schema-backed validator for advertising-reference research runs."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from _contract_utils import ContractError, parse_timestamp, read_json, read_jsonl, same_artifact, write_json
from _evidence_binding import (
    CANONICALIZATION,
    REPORT_TRUST_STATEMENT,
    approach_plan_sha256,
    canonical_sha256,
    curation_input_sha256,
    dedup_comparison_set_sha256,
    intent_constraints_sha256,
)
from _json_schema_subset import SchemaViolation, assert_schema_supported, validate as validate_schema
from build_review_gallery import build_gallery
from deduplicate_candidates import find_duplicate_groups, normalize_url
from verify_candidates import QUALIFYING_SURFACES, receipt_has_browser_media_evidence
from _qualification_rules import (
    HIGH_RISK_RIGHTS,
    MAX_FUTURE_SKEW,
    expected_dedup_status,
    media_evidence_errors,
)
from _url_policy import public_http_host


SHARED_PATHS = {
    "intent": "00_intent/intent_brief.json",
    "approaches": "01_orchestration/approach_registry.json",
}
PACK_PATHS = {
    "candidates": "02_candidates/candidate_ledger.jsonl",
    "receipts": "03_verification/verification_receipts.jsonl",
    "captures": "03_verification/browser_capture_records.jsonl",
    "shortlist": "04_selection/shortlist_30.json",
    "selected": "04_selection/selected_20.json",
    "rejected": "04_selection/rejected_10.json",
    "feedback": "05_feedback/feedback_ledger.jsonl",
    "board": "06_output/reference_board.html",
    "report": "06_output/verification_report.json",
}
SCHEMAS = {
    "intent": "intent_brief.schema.json",
    "approaches": "approach_registry.schema.json",
    "candidates": "candidate_item.schema.json",
    "receipts": "verification_receipt.schema.json",
    "captures": "browser_capture_record.schema.json",
    "shortlist": "shortlist_30.schema.json",
    "selected": "selected_20.schema.json",
    "rejected": "rejected_10.schema.json",
    "feedback": "feedback_event.schema.json",
    "report": "verification_report.schema.json",
}
RIGHTS_KEYS = {
    "discoverable",
    "viewable",
    "shareable_without_session",
    "downloadable",
    "internal_board_use",
    "commercial_reuse",
}
PROVENANCE_SIGNALS = {
    "original_owner",
    "creator_credit",
    "accountable_curator",
    "official_distribution",
}
_MISSING = object()


@dataclass
class Finding:
    code: str
    message: str
    artifact: str | None = None
    candidate_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.artifact:
            result["artifact"] = self.artifact
        if self.candidate_id:
            result["candidate_id"] = self.candidate_id
        return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _ids(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    return [item.get("candidate_id") for item in items if isinstance(item, dict) and isinstance(item.get("candidate_id"), str)]


def _string_set(value: Any) -> set[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return set(value)


def _global_feedback_semantic_projection(event: dict[str, Any]) -> dict[str, Any]:
    """Project a cross-pack correction without pack-local execution bindings."""
    semantic_keys = (
        "schema_version",
        "feedback_id",
        "timestamp",
        "run_id",
        "intent_id",
        "feedback_class",
        "signal_class",
        "user_evidence_or_quote",
        "failed_assumption",
        "error_layer",
        "constraint_delta",
        "repair_start_phase",
        "scope",
        "scope_evidence",
        "external_persistence_state",
        "confidence",
        "supersedes",
        "intent_version_before",
        "intent_version_after",
        "user_confirmed_persistence",
    )
    return {key: event.get(key) for key in semantic_keys}


def _http_host(value: Any) -> str | None:
    try:
        return public_http_host(value)
    except ContractError:
        return None


def _normalized_domain(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    host = value.strip().rstrip(".").lower()
    return host[4:] if host.startswith("www.") else host


def _site_domain(value: Any) -> str | None:
    """Conservatively collapse subdomains for diversity and identity accounting."""
    host = _normalized_domain(value)
    if host is None:
        return None
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return host
    labels = host.split(".")
    if len(labels) < 2:
        return host
    common_second_level = {"ac", "co", "com", "edu", "gov", "net", "org"}
    if len(labels) >= 3 and len(labels[-1]) == 2 and labels[-2] in common_second_level:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def _json_pointer_value(document: Any, pointer: Any) -> Any:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        return _MISSING
    value = document
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict) and token in value:
            value = value[token]
        elif isinstance(value, list) and token.isdigit() and int(token) < len(value):
            value = value[int(token)]
        else:
            return _MISSING
    return value


def _json_diff_paths(before: Any, after: Any, base: str = "") -> set[str]:
    """Return canonical JSON-pointer paths whose values changed."""

    if isinstance(before, dict) and isinstance(after, dict):
        paths: set[str] = set()
        for key in set(before) | set(after):
            token = str(key).replace("~", "~0").replace("/", "~1")
            path = f"{base}/{token}"
            if key not in before or key not in after:
                paths.add(path)
            else:
                paths.update(_json_diff_paths(before[key], after[key], path))
        return paths
    if isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            return {base}
        paths: set[str] = set()
        for index, (before_item, after_item) in enumerate(zip(before, after)):
            paths.update(_json_diff_paths(before_item, after_item, f"{base}/{index}"))
        return paths
    return set() if before == after else {base}


@dataclass
class PackValidator:
    run_root: Path
    pack_root: Path
    pack_contract: dict[str, Any]
    schemas_root: Path
    validation_now: datetime
    findings: list[Finding] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    artifact_files: dict[str, Path] = field(default_factory=dict)

    def fail(self, code: str, message: str, artifact: str | None = None, candidate_id: str | None = None) -> None:
        self.findings.append(Finding(code, message, artifact, candidate_id))

    def _time(self, value: Any, label: str, code: str = "FRESHNESS-01", candidate_id: str | None = None) -> datetime | None:
        try:
            parsed = parse_timestamp(value, label)
        except ContractError as exc:
            self.fail(code, str(exc), candidate_id=candidate_id)
            return None
        if parsed > self.validation_now + MAX_FUTURE_SKEW:
            self.fail(code, f"{label} is later than the trusted validation clock plus allowed skew", candidate_id=candidate_id)
        return parsed

    def _resolve_evidence_ref(self, ref: Any, code: str, label: str) -> Path | None:
        """Resolve a declared artifact ref without permitting traversal or arbitrary roots.

        Intent and orchestration artifacts are run-shared in parallel mode. Every other
        ref is pack-local. This keeps shared refs usable without treating the pack root
        as an escape hatch.
        """
        if not isinstance(ref, str) or not ref:
            self.fail(code, f"{label} must be a non-empty relative path")
            return None
        if ref.startswith(("00_intent/", "01_orchestration/")):
            root = self.run_root
        else:
            root = self.pack_root
        path = (root / ref).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError:
            self.fail(code, f"{label} escapes its allowed root: {ref}")
            return None
        return path

    def _resolve_report_path(self, ref: Any, code: str, label: str) -> Path | None:
        """Resolve a report-manifest path relative to the shared run root."""
        if not isinstance(ref, str) or not ref:
            self.fail(code, f"{label} must be a non-empty relative path")
            return None
        raw = Path(ref)
        if raw.is_absolute():
            self.fail(code, f"{label} must be relative to the run root: {ref}")
            return None
        path = (self.run_root / raw).resolve()
        try:
            path.relative_to(self.run_root.resolve())
        except ValueError:
            self.fail(code, f"{label} escapes the run root: {ref}")
            return None
        return path

    def _load(self) -> bool:
        for key, relative in SHARED_PATHS.items():
            path = self.run_root / relative
            self.artifact_files[key] = path
        for key, relative in PACK_PATHS.items():
            path = self.pack_root / relative
            self.artifact_files[key] = path
        for key, path in self.artifact_files.items():
            if path.is_symlink():
                self.fail("ARTIFACT_INTEGRITY", f"required artifact must not be a symlink: {path}", str(path))
                continue
            try:
                path.resolve().relative_to(self.run_root.resolve())
            except ValueError:
                self.fail("ARTIFACT_INTEGRITY", f"required artifact escapes the run root: {path}", str(path))
                continue
            if not path.is_file():
                self.fail("ARTIFACT_MISSING", f"required artifact missing: {path}", str(path))
                continue
            if key == "board":
                self.artifacts[key] = None
                continue
            try:
                self.artifacts[key] = read_jsonl(path) if path.suffix == ".jsonl" else read_json(path)
            except ContractError as exc:
                self.fail("ARTIFACT_PARSE", str(exc), str(path))
        return not self.findings

    def _schema_check(self) -> None:
        for key, schema_name in SCHEMAS.items():
            if key not in self.artifacts:
                continue
            schema_path = self.schemas_root / schema_name
            if not schema_path.is_file():
                self.fail("SCHEMA_MISSING", f"missing checked-in schema {schema_name}")
                continue
            schema = read_json(schema_path)
            try:
                assert_schema_supported(schema)
            except SchemaViolation as exc:
                self.fail("SCHEMA_UNSUPPORTED", str(exc), str(schema_path))
                continue
            values = self.artifacts[key] if key in {"candidates", "receipts", "captures", "feedback"} else [self.artifacts[key]]
            if not isinstance(values, list):
                values = [values]
            for index, value in enumerate(values):
                try:
                    errors = validate_schema(value, schema)
                except SchemaViolation as exc:
                    self.fail("SCHEMA_UNSUPPORTED", str(exc), str(schema_path))
                    continue
                for error in errors:
                    cid = value.get("candidate_id") if isinstance(value, dict) else None
                    self.fail("SCHEMA-01", error, f"{self.artifact_files[key]}#{index}", cid)

    def _validate_route(self) -> tuple[str, str, str]:
        intent = self.artifacts["intent"]
        version = intent["intent_version"]
        route = intent["modality_route"]
        routing = intent["routing"]
        strategy = routing["strategy"]
        if len(intent.get("clarification_questions", [])) > 3:
            self.fail("INTENT-01", "clarification_questions exceeds 3 questions")
        if not intent.get("route_reason_codes"):
            self.fail("ROUTE-01", "route_reason_codes must explain the route")
        if not intent.get("route_evidence", {}).get("evidence"):
            self.fail("ROUTE-01", "route_evidence must explain the route")
        expected_strategy = "single_modality" if route in {"image", "video"} else strategy
        if route in {"image", "video"} and strategy != expected_strategy:
            self.fail("ROUTE-01", "single modality must use single_modality strategy")
        pack_id = self.pack_contract.get("pack_id")
        modality = self.pack_contract.get("modality")
        root_identity = {
            "run_id": intent.get("run_id"),
            "intent_id": intent.get("intent_id"),
            "intent_version": version,
        }
        for artifact_name in ("approaches", "report"):
            artifact = self.artifacts[artifact_name]
            for key, expected in root_identity.items():
                if artifact.get(key) != expected:
                    self.fail("ROUTE-02", f"{artifact_name} {key} does not bind the root intent")
        if self.artifacts["report"].get("pack_id") != pack_id:
            self.fail("ROUTE-02", "report pack_id does not match routing pack contract")
        if self.pack_contract.get("qualified_target") != 30 or self.pack_contract.get("selected_target") != 20:
            self.fail("ROUTE-02", "every pack contract must freeze exact qualified=30 and selected=20 targets")
        if strategy == "single_modality" and modality != route:
            self.fail("ROUTE-01", "pack modality does not match single modality route")
        if strategy == "unified_territory" and modality != "mixed":
            self.fail("ROUTE-02", "unified territory pack must have modality=mixed")
        reason_codes = set(intent.get("route_reason_codes", []))
        required_route_codes = {
            "image": {"explicit_image_request", "static_composition_need"},
            "video": {"explicit_video_request", "temporal_mechanism_need"},
            "both": {"explicit_both_request", "mixed_decision_need"},
        }
        incompatible_route_codes = {
            "image": {"explicit_video_request", "explicit_both_request", "temporal_mechanism_need", "mixed_decision_need"},
            "video": {"explicit_image_request", "explicit_both_request", "static_composition_need", "mixed_decision_need"},
            "both": {"explicit_image_request", "explicit_video_request", "static_composition_need", "temporal_mechanism_need"},
        }
        if not (reason_codes & required_route_codes[route]) or reason_codes & incompatible_route_codes[route]:
            self.fail("ROUTE-01", "route reason codes contradict or fail to support modality_route")
        if intent.get("route_evidence", {}).get("declared_by_user") is True:
            explicit_code = f"explicit_{route}_request"
            if explicit_code not in reason_codes:
                self.fail("ROUTE-01", "user-declared route evidence lacks the matching explicit route code")
        approval = intent.get("approval", {})
        if approval.get("state") == "draft" or not approval.get("approved_at") or not approval.get("approved_by"):
            self.fail("INTENT-01", "a completed pack requires a frozen or user-confirmed intent approval")
        return version, strategy, str(modality)

    def _validate_intent_alignment(self, candidate: dict[str, Any], reference_time: datetime) -> None:
        cid = candidate["candidate_id"]
        intent = self.artifacts["intent"]
        alignment = candidate.get("intent_alignment", {})
        if alignment.get("intent_constraints_sha256") != intent_constraints_sha256(intent):
            self.fail("RELEVANCE-01", "candidate is not bound to the frozen intent constraints", candidate_id=cid)
        if alignment.get("subject_match") is not True:
            self.fail("RELEVANCE-01", "candidate subject does not match the frozen subject", candidate_id=cid)
        if not isinstance(alignment.get("decision_relevance"), str) or len(alignment["decision_relevance"].strip()) < 20:
            self.fail("RELEVANCE-01", "candidate lacks substantive decision relevance evidence", candidate_id=cid)

        scene_scale = intent["scene_scale"]
        if scene_scale not in {"mixed", "unspecified"} and alignment.get("observed_scene_scale") != scene_scale:
            self.fail("RELEVANCE-01", "candidate scene scale contradicts the frozen intent", candidate_id=cid)
        human_presence = intent["human_presence"]
        if human_presence not in {"mixed", "unspecified"} and alignment.get("observed_human_presence") != human_presence:
            self.fail("RELEVANCE-01", "candidate human presence contradicts the frozen intent", candidate_id=cid)

        if set(alignment.get("visual_axes_matched", [])) != set(intent["visual_axes"]):
            self.fail("RELEVANCE-01", "candidate does not account for every frozen visual axis", candidate_id=cid)
        expected_temporal = set(intent["temporal_axes"]) if candidate["modality"] == "video" else set()
        if set(alignment.get("temporal_axes_matched", [])) != expected_temporal:
            self.fail("RELEVANCE-01", "candidate temporal-axis evidence contradicts its modality and intent", candidate_id=cid)

        must_have = {item.get("criterion") for item in alignment.get("must_have_evidence", [])}
        must_not = {
            item.get("criterion")
            for item in alignment.get("must_not_have_checks", [])
            if item.get("absent") is True
        }
        if must_have != set(intent["must_have"]):
            self.fail("RELEVANCE-01", "candidate must-have evidence does not exactly cover the frozen criteria", candidate_id=cid)
        if must_not != set(intent["must_not_have"]):
            self.fail("RELEVANCE-01", "candidate exclusions do not exactly cover the frozen must-not criteria", candidate_id=cid)

        positive_labels = {item["label"] for item in intent["positive_anchors"]}
        negative_labels = {item["label"] for item in intent["negative_anchors"]}
        positive_assessments = alignment.get("positive_anchor_assessments", [])
        negative_assessments = alignment.get("negative_anchor_assessments", [])
        if {item.get("label") for item in positive_assessments} != positive_labels or any(
            item.get("status") == "conflicts" for item in positive_assessments
        ):
            self.fail("RELEVANCE-01", "positive-anchor assessment is incomplete or conflicting", candidate_id=cid)
        if {item.get("label") for item in negative_assessments} != negative_labels or any(
            item.get("status") != "neutral" for item in negative_assessments
        ):
            self.fail("RELEVANCE-01", "negative-anchor avoidance is incomplete or conflicting", candidate_id=cid)

        candidate_region = candidate["object"].get("region")
        candidate_language = candidate["object"].get("language")
        region_matches = isinstance(candidate_region, str) and (
            candidate_region.casefold() in {item.casefold() for item in intent["market_region"]}
            or "global" in {item.casefold() for item in intent["market_region"]}
        )
        language_matches = isinstance(candidate_language, str) and candidate_language.casefold() in {
            item.casefold() for item in intent["languages"]
        }
        region_status = alignment.get("market_region_status")
        language_status = alignment.get("language_status")
        if (region_matches and region_status != "match") or (not region_matches and region_status != "transferable"):
            self.fail("RELEVANCE-01", "candidate market-region status contradicts object metadata and intent", candidate_id=cid)
        if (language_matches and language_status != "match") or (not language_matches and language_status != "transferable"):
            self.fail("RELEVANCE-01", "candidate language status contradicts object metadata and intent", candidate_id=cid)
        if (region_status == "transferable" or language_status == "transferable") and (
            not isinstance(alignment.get("transfer_rationale"), str)
            or len(alignment["transfer_rationale"].strip()) < 20
        ):
            self.fail("RELEVANCE-01", "cross-market or cross-language transfer needs substantive rationale", candidate_id=cid)

        content_max_age_days = intent["freshness_need"].get("content_max_age_days")
        if content_max_age_days is not None:
            publish_date = candidate["object"].get("publish_date")
            try:
                published = date.fromisoformat(publish_date) if isinstance(publish_date, str) else None
            except ValueError:
                published = None
            age_days = (reference_time.date() - published).days if published is not None else None
            if age_days is None or age_days < 0 or age_days > content_max_age_days:
                self.fail("RELEVANCE-01", "candidate violates frozen content_max_age_days", candidate_id=cid)

        compatible_states = {
            "allowed": {"allowed"},
            "prohibited": {"prohibited", "not_applicable"},
            "permission_required": {"permission_required", "unknown", "prohibited"},
            "unknown": {"allowed", "permission_required", "unknown", "prohibited", "not_applicable"},
            "not_applicable": {"not_applicable"},
        }
        rights_compatible = all(
            candidate["rights_scope"][key]["state"] in compatible_states[intent["rights_scope"][key]["state"]]
            for key in RIGHTS_KEYS
        )
        if alignment.get("rights_compatible") is not rights_compatible or not rights_compatible:
            self.fail("RIGHTS-01", "candidate rights evidence is incompatible with the frozen intent", candidate_id=cid)

    def _validate_mode_and_registration(self) -> tuple[str, dict[str, dict[str, Any]]]:
        intent = self.artifacts["intent"]
        report = self.artifacts["report"]
        registry = self.artifacts["approaches"]
        mode = intent["run_mode"]
        expected = {
            "test_fixture": ("synthetic_fixture", "fixture_contract_pass", False, "synthetic_fixture"),
            "retrospective_smoke": (
                "retrospective_reconstruction",
                "retrospective_smoke_pass",
                False,
                "retrospective_import",
            ),
            "production_live": (
                "preregistered",
                "production_contract_eligible",
                True,
                "direct_browser_observation",
            ),
        }
        registration_kind, acceptance_class, contract_eligible, capture_origin = expected[mode]
        registration = registry["registration"]
        if report.get("run_mode") != mode:
            self.fail("MODE-01", "verification report run_mode differs from intent")
        if report.get("acceptance_class") != acceptance_class:
            self.fail("MODE-01", "verification report acceptance_class overstates or mislabels its run mode")
        if report.get("production_contract_eligible") is not contract_eligible:
            self.fail("MODE-01", "verification report production_contract_eligible claim differs from run mode")
        if report.get("production_deliverable") is not False:
            self.fail("ATTEST-01", "unsigned package evidence must never claim production_deliverable=true")
        trust_boundary = report.get("trust_boundary", {})
        if trust_boundary.get("browser_action_attested") is not False:
            self.fail("ATTEST-01", "package validation cannot attest that a browser action occurred")
        if trust_boundary.get("claim_scope") != "contract_eligible_only":
            self.fail("ATTEST-01", "verification report must limit its claim to contract eligibility")
        if report.get("trust_boundary", {}).get("statement") != REPORT_TRUST_STATEMENT:
            self.fail("REPORT-01", "verification report trust-boundary statement is not canonical")
        if registration.get("kind") != registration_kind:
            self.fail("MODE-01", "approach registration kind differs from run mode")
        if registration.get("canonicalization") != CANONICALIZATION:
            self.fail("PREREG-01", "unsupported approach-plan canonicalization")
        computed_plan_sha = approach_plan_sha256(registry)
        if registration.get("plan_sha256") != computed_plan_sha:
            self.fail("PREREG-01", "approach registration plan hash does not match the immutable plan projection")

        capture_index: dict[str, dict[str, Any]] = {}
        for record in self.artifacts["captures"]:
            capture_id = record.get("capture_id")
            if capture_id in capture_index:
                self.fail("CAPTURE-01", f"duplicate capture_id: {capture_id}")
                continue
            capture_index[capture_id] = record
            if record.get("record_origin") != capture_origin:
                self.fail("CAPTURE-02", "capture origin is incompatible with run mode", candidate_id=record.get("candidate_id"))
            if record.get("approach_plan_sha256") != computed_plan_sha:
                self.fail("CAPTURE-01", "capture is not bound to the frozen approach plan", candidate_id=record.get("candidate_id"))
            for key in ("run_id", "intent_id", "intent_version"):
                if record.get(key) != intent.get(key):
                    self.fail("CAPTURE-01", f"capture {key} does not bind the root intent", candidate_id=record.get("candidate_id"))
            if record.get("pack_id") != self.pack_contract.get("pack_id"):
                self.fail("CAPTURE-01", "capture pack_id differs from pack contract", candidate_id=record.get("candidate_id"))
            self._time(record.get("captured_at"), f"capture[{capture_id}].captured_at", "CAPTURE-01", record.get("candidate_id"))
            observation = record.get("observation", {})
            if _http_host(observation.get("canonical_url")) is None:
                self.fail("CAPTURE-01", "capture observation canonical URL is unsafe", candidate_id=record.get("candidate_id"))
            source_record = record.get("source_record")
            if mode in {"retrospective_smoke", "production_live"}:
                if not isinstance(source_record, dict):
                    self.fail("CAPTURE-01", "non-fixture capture lacks a retained source-record binding", candidate_id=record.get("candidate_id"))
                else:
                    path = self._resolve_evidence_ref(source_record.get("path"), "CAPTURE-01", "capture source record")
                    if path is not None:
                        forbidden = {
                            self.artifact_files["captures"].resolve(),
                            self.artifact_files["receipts"].resolve(),
                            self.artifact_files["report"].resolve(),
                        }
                        if path.resolve() in forbidden:
                            self.fail("CAPTURE-01", "capture source record cannot self-reference a derived artifact")
                        elif not path.is_file():
                            self.fail("CAPTURE-01", f"capture source record does not exist: {source_record.get('path')}")
                        elif source_record.get("sha256") != _sha256(path):
                            self.fail("CAPTURE-01", "capture source-record hash mismatch", candidate_id=record.get("candidate_id"))
                        elif source_record.get("json_pointer") is not None:
                            try:
                                source_value = read_jsonl(path) if path.suffix == ".jsonl" else read_json(path)
                            except ContractError as exc:
                                self.fail("CAPTURE-01", f"cannot parse capture source record: {exc}")
                            else:
                                if _json_pointer_value(source_value, source_record["json_pointer"]) is _MISSING:
                                    self.fail("CAPTURE-01", "capture source-record JSON pointer does not resolve")

        frozen_at = self._time(registration.get("frozen_at"), "approach registration frozen_at", "PREREG-01")
        approval_at = intent.get("approval", {}).get("approved_at")
        approval_time = self._time(approval_at, "intent approval approved_at", "PREREG-01") if approval_at else None
        captured = [
            self._time(item.get("captured_at"), f"capture[{item.get('capture_id')}].captured_at", "CAPTURE-01")
            for item in self.artifacts["captures"]
        ]
        captured = [item for item in captured if item is not None]
        if mode == "production_live":
            if not captured:
                self.fail("CAPTURE-02", "production_live requires direct browser capture records")
            if approval_time is None or (frozen_at is not None and approval_time > frozen_at):
                self.fail("PREREG-01", "production intent approval must precede or equal plan freeze")
            search_started = [
                self._time(
                    item.get("started_at"),
                    f"approach[{item.get('approach_id')}].started_at",
                    "PREREG-01",
                )
                for item in registry.get("approaches", [])
            ]
            discovered = [
                self._time(
                    item.get("discovered_at"),
                    f"candidate[{item.get('candidate_id')}].discovered_at",
                    "PREREG-01",
                )
                for item in self.artifacts["candidates"]
            ]
            activity = [
                ("search", item) for item in search_started if item is not None
            ] + [
                ("discovery", item) for item in discovered if item is not None
            ] + [
                ("capture", item) for item in captured
            ]
            if not activity:
                self.fail("PREREG-01", "production_live has no search, discovery, or capture chronology")
            else:
                first_kind, first_time = min(activity, key=lambda value: value[1])
                if frozen_at is None or frozen_at >= first_time:
                    self.fail(
                        "PREREG-01",
                        f"approved production plan must be frozen before earliest {first_kind} activity",
                    )
        return mode, capture_index

    def _validate_capture_bindings(
        self,
        candidate: dict[str, Any],
        receipt: dict[str, Any],
        capture_index: dict[str, dict[str, Any]],
    ) -> None:
        cid = candidate["candidate_id"]
        purposes: set[str] = set()
        bound_records: list[tuple[dict[str, Any], set[str]]] = []
        for binding in receipt.get("capture_bindings", []):
            binding_purposes = set(binding.get("purposes", []))
            purposes.update(binding_purposes)
            record = capture_index.get(binding.get("capture_id"))
            if record is None:
                self.fail("CAPTURE-01", "receipt references a missing capture record", candidate_id=cid)
                continue
            if binding.get("record_sha256") != canonical_sha256(record):
                self.fail("CAPTURE-01", "receipt capture-record hash mismatch", candidate_id=cid)
            bound_records.append((record, binding_purposes))
        if purposes != {"access", "media", "object_match", "provenance"}:
            self.fail("CAPTURE-01", "qualified receipt must bind capture evidence for all four purposes", candidate_id=cid)
        if not bound_records:
            return
        approach_id = candidate["agent_trace"]["approach_id"]
        finder_id = candidate["agent_trace"]["finder_agent_id"]
        verifier_id = receipt["verifier"]["verifier_agent_id"]
        agent_roles = {
            item["agent_id"]: {item["role"], *item.get("additional_roles", [])}
            for item in self.artifacts["approaches"]["agents"]
        }
        bound_surfaces: set[str] = set()
        capture_times: list[datetime] = []
        for record, record_purposes in bound_records:
            if record.get("candidate_id") != cid or record.get("approach_id") != approach_id:
                self.fail("CAPTURE-01", "capture candidate/approach binding differs from receipt", candidate_id=cid)
            operator_id = record.get("operator_agent_id")
            operator_roles = agent_roles.get(operator_id, set())
            if (
                operator_id in {finder_id, verifier_id}
                or not operator_roles & {"authenticated_source_operator", "capture_operator"}
            ):
                self.fail(
                    "CAPTURE-01",
                    "capture operator is unregistered, incompatible, or not independent from finder and verifier",
                    candidate_id=cid,
                )
            bound_surfaces.add(str(record.get("surface")))
            captured = self._time(record.get("captured_at"), f"capture[{record.get('capture_id')}].captured_at", "CAPTURE-01", cid)
            if captured is not None:
                capture_times.append(captured)
            observation = record.get("observation", {})
            if observation.get("canonical_url") != candidate["object"]["canonical_url"]:
                self.fail("CAPTURE-01", "capture canonical URL differs from candidate", candidate_id=cid)
            if "media" in record_purposes:
                fingerprint = observation.get("dedup_fingerprint")
                expected_fingerprint = candidate.get("dedup", {}).get("fingerprint")
                expected_capture_id = (
                    expected_fingerprint.get("evidence_capture_id")
                    if isinstance(expected_fingerprint, dict)
                    else None
                )
                comparable = (
                    {
                        key: fingerprint.get(key)
                        for key in (
                            "method", "exact_or_manifest_sha256", "perceptual_hash",
                            "sample_count", "sampled_at_seconds",
                        )
                    }
                    if isinstance(fingerprint, dict)
                    else None
                )
                expected_comparable = (
                    {
                        key: expected_fingerprint.get(key)
                        for key in (
                            "method", "exact_or_manifest_sha256", "perceptual_hash",
                            "sample_count", "sampled_at_seconds",
                        )
                    }
                    if isinstance(expected_fingerprint, dict)
                    else None
                )
                if (
                    comparable is None
                    or comparable != expected_comparable
                    or record.get("capture_id") != expected_capture_id
                    or fingerprint.get("input_asset_locator") != candidate["object"]["asset_locator"]
                ):
                    self.fail("DEDUP-01", "media capture fingerprint does not bind the candidate asset", candidate_id=cid)
                else:
                    expected_method = (
                        "image_content_sha256_dhash64"
                        if candidate["modality"] == "image"
                        else "video_sample_manifest_sha256_dhash64"
                    )
                    sample_count = fingerprint["sample_count"]
                    sampled_at = fingerprint["sampled_at_seconds"]
                    if fingerprint["method"] != expected_method:
                        self.fail("DEDUP-01", "fingerprint method does not match candidate modality", candidate_id=cid)
                    if candidate["modality"] == "image" and (sample_count != 1 or sampled_at != []):
                        self.fail("DEDUP-01", "image fingerprint must represent one exact image sample", candidate_id=cid)
                    if candidate["modality"] == "video" and (
                        sample_count < 3 or len(sampled_at) != sample_count
                    ):
                        self.fail("DEDUP-01", "video fingerprint requires at least three declared frame samples", candidate_id=cid)
                    if candidate["modality"] == "video":
                        duration = (receipt["media_check"].get("video_playback") or {}).get("duration_seconds")
                        strictly_increasing = all(
                            left < right for left, right in zip(sampled_at, sampled_at[1:])
                        )
                        if (
                            not isinstance(duration, (int, float))
                            or not strictly_increasing
                            or any(timestamp < 0 or timestamp > duration for timestamp in sampled_at)
                        ):
                            self.fail(
                                "DEDUP-01",
                                "video fingerprint sample timestamps must be strictly increasing and within bound duration",
                                candidate_id=cid,
                            )
                    computed_at = self._time(
                        fingerprint.get("computed_at"),
                        f"capture[{record.get('capture_id')}].dedup_fingerprint.computed_at",
                        "DEDUP-01",
                        cid,
                    )
                    captured_at = self._time(
                        record.get("captured_at"),
                        f"capture[{record.get('capture_id')}].captured_at",
                        "CAPTURE-01",
                        cid,
                    )
                    if computed_at is not None and captured_at is not None and computed_at != captured_at:
                        self.fail("DEDUP-01", "fingerprint computation time is not bound to its capture", candidate_id=cid)
            if "access" in record_purposes and observation.get("access_state") != receipt["access_state"]:
                self.fail("CAPTURE-01", "capture access observation differs from receipt", candidate_id=cid)
            session_free_observed = record.get("trust_boundary", {}).get("session_free_access_observed")
            observed_shareability = observation.get("access_state", {}).get("shareable_without_session")
            if session_free_observed != observed_shareability:
                self.fail(
                    "CAPTURE-01",
                    "capture trust boundary differs from its access observation",
                    candidate_id=cid,
                )
            if "access" in record_purposes and session_free_observed != receipt["access_state"]["shareable_without_session"]:
                self.fail(
                    "CAPTURE-01",
                    "capture session-free observation differs from the bound receipt",
                    candidate_id=cid,
                )
            if "media" in record_purposes and (
                observation.get("media_check") != receipt["media_check"]
                or observation.get("asset_locator") != candidate["object"]["asset_locator"]
            ):
                self.fail("CAPTURE-01", "capture media observation differs from candidate/receipt", candidate_id=cid)
            if "object_match" in record_purposes and (
                observation.get("object_match") != receipt["object_match"]
                or observation.get("stable_id") != candidate["object"].get("stable_id")
            ):
                self.fail("CAPTURE-01", "capture object-match observation differs from candidate/receipt", candidate_id=cid)
            if "provenance" in record_purposes and observation.get("provenance_check") != receipt["provenance_check"]:
                self.fail("CAPTURE-01", "capture provenance observation differs from receipt", candidate_id=cid)
            if record.get("phase") != "final_verification":
                self.fail("CAPTURE-01", "E4 receipt must bind a final_verification capture", candidate_id=cid)
        checked_at = self._time(receipt.get("checked_at"), f"receipt[{cid}].checked_at", "CAPTURE-01", cid)
        if checked_at is not None and (not capture_times or max(capture_times) != checked_at):
            self.fail("CAPTURE-01", "receipt checked_at must equal its latest bound capture time", candidate_id=cid)
        if receipt["access_state"]["mode"] == "signed_chrome" and "chrome_authenticated" not in bound_surfaces:
            self.fail("CAPTURE-01", "signed_chrome receipt lacks a bound authenticated Chrome capture", candidate_id=cid)

    def _validate_temporal_contract(self) -> None:
        intent = self.artifacts["intent"]
        report = self.artifacts["report"]
        generated = self._time(report.get("generated_at"), "report.generated_at")
        delivery = self._time(report.get("delivery_reference_time"), "report.delivery_reference_time")
        if generated is not None and delivery is not None and delivery > generated:
            self.fail("FRESHNESS-01", "delivery_reference_time occurs after report generation")
        self._time(intent.get("created_at"), "intent.created_at")
        approval = intent.get("approval", {}).get("approved_at")
        if approval is not None:
            self._time(approval, "intent.approval.approved_at")
        for index, question in enumerate(intent.get("clarification_questions", [])):
            self._time(question.get("asked_at"), f"intent.clarification_questions[{index}].asked_at")
        self._time(self.artifacts["approaches"].get("created_at"), "approach_registry.created_at")
        for artifact_name in ("shortlist", "selected", "rejected"):
            created = self._time(self.artifacts[artifact_name].get("created_at"), f"{artifact_name}.created_at")
            if created is not None and generated is not None and created > generated:
                self.fail("FRESHNESS-01", f"{artifact_name} was created after report generation")
        audit_completed = self._time(report.get("adversarial_audit", {}).get("completed_at"), "report.adversarial_audit.completed_at")
        if audit_completed is not None and generated is not None and audit_completed > generated:
            self.fail("AUDIT-01", "adversarial audit completed after report generation")
        for index, event in enumerate(self.artifacts["feedback"]):
            event_time = self._time(event.get("timestamp"), f"feedback[{index}].timestamp", "FEEDBACK-01")
            applied_time = self._time(
                event.get("agent_trace", {}).get("applied_at"),
                f"feedback[{index}].agent_trace.applied_at",
                "FEEDBACK-01",
            )
            if event_time is not None and applied_time is not None and applied_time < event_time:
                self.fail("FEEDBACK-01", "feedback applied_at precedes its timestamp")
            if applied_time is not None and generated is not None and applied_time > generated:
                self.fail("FEEDBACK-01", "feedback was applied after report generation")

    def _validate_pool(self, intent_version: str, modality: str) -> tuple[list[str], list[str], list[str]]:
        shortlist = self.artifacts["shortlist"]
        selected = self.artifacts["selected"]
        rejected = self.artifacts["rejected"]
        shortlist_ids = shortlist.get("candidate_ids", [])
        shortlist_item_ids = _ids(shortlist.get("items"))
        selected_ids = _ids(selected.get("items"))
        rejected_ids = _ids(rejected.get("items"))
        if shortlist.get("qualified_candidate_count") != 30 or len(shortlist_ids) != 30:
            self.fail("POOL-01", "qualified shortlist must contain exactly 30 candidates")
        if selected.get("selected_candidate_count") != 20 or len(selected_ids) != 20:
            self.fail("POOL-01", "selected artifact must contain exactly 20 candidates")
        if rejected.get("rejected_candidate_count") != 10 or len(rejected_ids) != 10:
            self.fail("POOL-01", "rejected artifact must contain exactly 10 candidates")
        if set(shortlist_ids) != set(shortlist_item_ids):
            self.fail("POOL-01", "shortlist candidate_ids and item ids differ")
        if set(shortlist["partition"]["selected_candidate_ids"]) != set(selected_ids):
            self.fail("POOL-01", "shortlist selected partition differs from selected_20")
        if set(shortlist["partition"]["rejected_candidate_ids"]) != set(rejected_ids):
            self.fail("POOL-01", "shortlist rejected partition differs from rejected_10")
        if set(selected_ids) & set(rejected_ids) or set(selected_ids) | set(rejected_ids) != set(shortlist_ids):
            self.fail("POOL-01", "20/10 partition must be disjoint and exactly cover the 30")
        for artifact_name in ("shortlist", "selected", "rejected"):
            artifact = self.artifacts[artifact_name]
            if artifact.get("run_id") != self.artifacts["intent"].get("run_id"):
                self.fail("POOL-01", f"{artifact_name} run_id drift")
            if artifact.get("intent_id") != self.artifacts["intent"].get("intent_id"):
                self.fail("POOL-01", f"{artifact_name} intent_id drift")
            if artifact.get("intent_version") != intent_version:
                self.fail("POOL-01", f"{artifact_name} intent_version drift")
            if artifact.get("pack_id") != self.pack_contract.get("pack_id"):
                self.fail("POOL-01", f"{artifact_name} pack_id drift")
        if shortlist.get("modality") != modality:
            self.fail("ROUTE-01", "shortlist modality differs from pack contract")
        ranks = [item.get("rank") for item in selected.get("items", [])]
        if sorted(ranks) != list(range(1, 21)):
            self.fail("CURATION-01", "selected ranks must be unique and complete 1..20")
        for item in selected.get("items", []):
            for key in ("why_fit", "decision_supported", "transferable_mechanism", "do_not_copy"):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    self.fail("CURATION-01", f"selected item lacks {key}", candidate_id=item.get("candidate_id"))
        for item in rejected.get("items", []):
            dominated = item.get("dominated_by_candidate_ids")
            if not isinstance(dominated, list) or not dominated or not set(dominated).issubset(selected_ids):
                self.fail("CURATION-01", "rejected item must be dominated by selected candidate(s)", candidate_id=item.get("candidate_id"))
            if not item.get("dominance_reason"):
                self.fail("CURATION-01", "rejected item lacks dominance_reason", candidate_id=item.get("candidate_id"))
        return shortlist_ids, selected_ids, rejected_ids

    def _candidate_index(self) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        for candidate in self.artifacts["candidates"]:
            cid = candidate.get("candidate_id")
            if cid in index:
                self.fail("CANDIDATE-01", "duplicate candidate_id in ledger", candidate_id=cid)
            else:
                index[cid] = candidate
        return index

    def _validate_dominance(
        self,
        candidates: dict[str, dict[str, Any]],
        selected_ids: list[str],
        rejected_ids: list[str],
    ) -> None:
        selected_rows = {item["candidate_id"]: item for item in self.artifacts["selected"]["items"]}
        rejected_rows = {item["candidate_id"]: item for item in self.artifacts["rejected"]["items"]}
        dimensions = {
            "relevance",
            "craft_signal",
            "source_authority",
            "freshness",
            "access_reliability",
            "link_durability",
            "evidence_completeness",
            "rights_risk",
            "diversity_contribution",
        }
        for rejected_id in rejected_ids:
            row = rejected_rows[rejected_id]
            declared_dimension = row["dominance_dimension"]
            for selected_id in row["dominated_by_candidate_ids"]:
                if selected_id not in selected_ids:
                    continue
                selected_scores = candidates[selected_id]["evaluation_dimensions"]
                rejected_scores = candidates[rejected_id]["evaluation_dimensions"]
                deltas: dict[str, float] = {}
                for dimension in dimensions:
                    selected_score = selected_scores[dimension]["score"]
                    rejected_score = rejected_scores[dimension]["score"]
                    deltas[dimension] = (
                        rejected_score - selected_score
                        if dimension == "rights_risk"
                        else selected_score - rejected_score
                    )
                if all(delta == 0 for delta in deltas.values()):
                    tie = row.get("score_tie_break")
                    selected_stable_id = candidates[selected_id]["object"].get("stable_id")
                    rejected_stable_id = candidates[rejected_id]["object"].get("stable_id")
                    valid_tie = (
                        tie
                        == {
                            "key": "object.stable_id",
                            "order": "ascending_lexicographic",
                            "applies_when": "all_dimensions_equal",
                        }
                        and isinstance(selected_stable_id, str)
                        and isinstance(rejected_stable_id, str)
                        and selected_stable_id < rejected_stable_id
                        and selected_rows[selected_id]["rank"] < row["shortlist_rank"]
                    )
                    if not valid_tie:
                        self.fail(
                            "CURATION-02",
                            "exact score-vector tie lacks a valid structured lexicographic tie-break",
                            candidate_id=rejected_id,
                        )
                    continue
                if any(delta < 0 for delta in deltas.values()):
                    self.fail(
                        "CURATION-02",
                        "declared selected comparator is worse on at least one dimension and therefore does not Pareto-dominate",
                        candidate_id=rejected_id,
                    )
                    continue
                if deltas[declared_dimension] <= 0:
                    self.fail(
                        "CURATION-02",
                        "dominance_dimension must name one of the comparator's strict improvements",
                        candidate_id=rejected_id,
                    )
                    continue
                if row.get("score_tie_break") is not None:
                    self.fail(
                        "CURATION-02",
                        "score_tie_break is allowed only for an exact score-vector tie",
                        candidate_id=rejected_id,
                    )

    def _receipt_index(self) -> dict[str, dict[str, Any]]:
        by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
        seen_receipt_ids: dict[str, str] = {}
        for receipt in self.artifacts["receipts"]:
            cid = receipt.get("candidate_id")
            receipt_id = receipt.get("receipt_id")
            if receipt_id in seen_receipt_ids:
                self.fail(
                    "VERIFY-01",
                    f"duplicate receipt_id is bound to multiple receipt rows: {receipt_id}",
                    candidate_id=cid,
                )
            elif isinstance(receipt_id, str):
                seen_receipt_ids[receipt_id] = str(cid)
            by_candidate[cid].append(receipt)
        result: dict[str, dict[str, Any]] = {}
        for cid, receipts in by_candidate.items():
            try:
                parsed_receipts = [
                    (parse_timestamp(receipt.get("checked_at")), receipt)
                    for receipt in receipts
                ]
                instants = [instant for instant, _ in parsed_receipts]
                if len(instants) != len(set(instants)):
                    self.fail(
                        "VERIFY-01",
                        "multiple receipts for one candidate represent the same UTC instant",
                        candidate_id=cid,
                    )
                result[cid] = max(parsed_receipts, key=lambda item: item[0])[1]
            except ContractError as exc:
                self.fail("FRESHNESS-01", str(exc), candidate_id=cid)
        return result

    def _validate_ledger_closure(
        self,
        candidates: dict[str, dict[str, Any]],
        receipt_index: dict[str, dict[str, Any]],
        shortlist_ids: list[str],
        capture_index: dict[str, dict[str, Any]],
    ) -> None:
        """Require every ledger row to belong to this pack and close every evidence edge."""
        intent = self.artifacts["intent"]
        pack_id = self.pack_contract["pack_id"]
        pack_modality = self.pack_contract["modality"]
        allowed_modalities = {"image", "video"} if pack_modality == "mixed" else {pack_modality}
        root_identity = {
            "run_id": intent["run_id"],
            "intent_id": intent["intent_id"],
            "intent_version": intent["intent_version"],
        }
        final_statuses = {"qualified", "selected", "rejected"}
        final_candidate_ids = {
            cid for cid, candidate in candidates.items() if candidate.get("status") in final_statuses
        }
        if final_candidate_ids != set(shortlist_ids) or len(final_candidate_ids) != 30:
            self.fail(
                "POOL-01",
                "candidate ledger must contain exactly the shortlist 30 in qualified/selected/rejected states",
            )

        for cid, candidate in candidates.items():
            for key, expected in root_identity.items():
                if candidate.get(key) != expected:
                    self.fail("CANDIDATE-01", f"candidate {key} does not bind the root intent", candidate_id=cid)
            if candidate.get("pack_id") != pack_id:
                self.fail("CANDIDATE-01", "candidate pack_id differs from pack contract", candidate_id=cid)
            if candidate.get("modality") not in allowed_modalities:
                self.fail("ROUTE-01", "candidate modality does not bind the pack route", candidate_id=cid)
            latest = receipt_index.get(cid)
            declared_receipt_id = candidate.get("verification_receipt_id")
            if declared_receipt_id is not None:
                if latest is None or declared_receipt_id != latest.get("receipt_id"):
                    self.fail(
                        "VERIFY-01",
                        "candidate verification_receipt_id must bind its latest receipt",
                        candidate_id=cid,
                    )
            if candidate.get("status") in final_statuses and latest is None:
                self.fail("VERIFY-01", "final candidate lacks a verification receipt", candidate_id=cid)

        bound_capture_ids: set[str] = set()
        for receipt in self.artifacts["receipts"]:
            cid = receipt.get("candidate_id")
            candidate = candidates.get(cid)
            if candidate is None:
                self.fail("VERIFY-01", "receipt references a candidate absent from the ledger", candidate_id=cid)
                continue
            for key, expected in root_identity.items():
                if receipt.get(key) != expected:
                    self.fail("VERIFY-01", f"receipt {key} does not bind the root intent", candidate_id=cid)
            if receipt.get("pack_id") != pack_id:
                self.fail("VERIFY-01", "receipt pack_id differs from pack contract", candidate_id=cid)
            if receipt.get("modality") != candidate.get("modality"):
                self.fail("ROUTE-01", "receipt modality differs from its candidate", candidate_id=cid)
            if receipt.get("source_id") != candidate.get("source", {}).get("source_id"):
                self.fail("VERIFY-01", "receipt source_id differs from its candidate", candidate_id=cid)
            if receipt.get("outcome") == "qualified" and cid not in final_candidate_ids:
                self.fail("VERIFY-01", "qualified receipt is bound to a non-final candidate", candidate_id=cid)
            for binding in receipt.get("capture_bindings", []):
                capture_id = binding.get("capture_id")
                record = capture_index.get(capture_id)
                if record is None:
                    self.fail("CAPTURE-01", "receipt references a missing capture record", candidate_id=cid)
                    continue
                bound_capture_ids.add(capture_id)
                if binding.get("record_sha256") != canonical_sha256(record):
                    self.fail("CAPTURE-01", "receipt capture-record hash mismatch", candidate_id=cid)
                if record.get("candidate_id") != cid:
                    self.fail("CAPTURE-01", "receipt capture is bound to a different candidate", candidate_id=cid)

        for capture_id, record in capture_index.items():
            cid = record.get("candidate_id")
            candidate = candidates.get(cid)
            if candidate is None:
                self.fail("CAPTURE-01", "capture references a candidate absent from the ledger", candidate_id=cid)
                continue
            for key, expected in root_identity.items():
                if record.get(key) != expected:
                    self.fail("CAPTURE-01", f"capture {key} does not bind the root intent", candidate_id=cid)
            if record.get("pack_id") != pack_id:
                self.fail("CAPTURE-01", "capture pack_id differs from pack contract", candidate_id=cid)
            if capture_id not in bound_capture_ids:
                self.fail("CAPTURE-01", "capture is orphaned from the receipt ledger", candidate_id=cid)
            if record.get("approach_id") != candidate.get("agent_trace", {}).get("approach_id"):
                self.fail("CAPTURE-01", "capture approach_id differs from its candidate", candidate_id=cid)

    def _validate_candidate_and_receipt(
        self,
        candidate: dict[str, Any],
        receipt: dict[str, Any],
        expected_status: str,
        reference_time: datetime,
        window_minutes: int,
    ) -> tuple[str, str]:
        cid = candidate["candidate_id"]
        intent = self.artifacts["intent"]
        root_identity = {
            "run_id": intent.get("run_id"),
            "intent_id": intent.get("intent_id"),
            "intent_version": intent.get("intent_version"),
        }
        for key, expected in root_identity.items():
            if candidate.get(key) != expected:
                self.fail("CANDIDATE-01", f"candidate {key} does not bind the root intent", candidate_id=cid)
            if receipt.get(key) != expected:
                self.fail("VERIFY-01", f"receipt {key} does not bind the root intent", candidate_id=cid)
        if candidate.get("status") != expected_status:
            self.fail("CANDIDATE-01", f"candidate status must be {expected_status}", candidate_id=cid)
        if candidate.get("pack_id") != self.pack_contract.get("pack_id"):
            self.fail("CANDIDATE-01", "candidate pack_id differs from pack contract", candidate_id=cid)
        if candidate.get("verification_receipt_id") != receipt.get("receipt_id"):
            self.fail("VERIFY-01", "candidate verification_receipt_id does not bind latest receipt", candidate_id=cid)
        if receipt.get("candidate_id") != cid:
            self.fail("VERIFY-01", "receipt candidate_id does not bind candidate", candidate_id=cid)
        if receipt.get("intent_id") != candidate.get("intent_id") or receipt.get("intent_version") != candidate.get("intent_version"):
            self.fail("VERIFY-01", "receipt intent binding differs from candidate", candidate_id=cid)
        if receipt.get("pack_id") != self.pack_contract.get("pack_id"):
            self.fail("VERIFY-01", "receipt pack_id differs from pack contract", candidate_id=cid)
        pack_modality = self.pack_contract.get("modality")
        allowed_modalities = {"image", "video"} if pack_modality == "mixed" else {pack_modality}
        if candidate.get("modality") not in allowed_modalities or receipt.get("modality") != candidate.get("modality"):
            self.fail("ROUTE-01", "candidate/receipt modality does not bind the pack route", candidate_id=cid)
        object_type = candidate.get("object", {}).get("object_type")
        if candidate.get("modality") == "image" and object_type != "project_image":
            self.fail("ROUTE-01", "qualified image candidate must use object_type=project_image", candidate_id=cid)
        if candidate.get("modality") == "video" and object_type not in {"specific_video_work", "specific_cut"}:
            self.fail("ROUTE-01", "qualified video candidate must identify a specific video work or cut", candidate_id=cid)
        self._validate_intent_alignment(candidate, reference_time)
        if receipt.get("source_id") != candidate.get("source", {}).get("source_id"):
            self.fail("VERIFY-01", "receipt source_id does not bind candidate source", candidate_id=cid)
        finder = candidate["agent_trace"]["finder_agent_id"]
        verifier = receipt["verifier"]["verifier_agent_id"]
        if receipt["verifier"]["finder_agent_id"] != finder or verifier == finder:
            self.fail("AGENT-01", "finder/verifier identity is not independently bound", candidate_id=cid)
        if receipt["verifier"].get("independence_asserted") is not True:
            self.fail("AGENT-01", "receipt does not assert finder/verifier independence", candidate_id=cid)
        if receipt["verifier"]["verification_surface"] not in QUALIFYING_SURFACES:
            self.fail("VERIFY-01", "HTTP/API-only verification cannot qualify media", candidate_id=cid)
        if receipt.get("outcome") != "qualified":
            self.fail("VERIFY-01", "shortlist receipt outcome must be qualified", candidate_id=cid)
        if receipt.get("evidence_level") != "E4_QUALIFIED":
            self.fail("VERIFY-01", "qualified receipt needs the implemented E4 evidence contract", candidate_id=cid)
        if receipt.get("failure_codes") != []:
            self.fail("VERIFY-03", "qualified receipt failure_codes must be empty", candidate_id=cid)
        checked_at = self._time(receipt["checked_at"], f"receipt[{cid}].checked_at", candidate_id=cid)
        discovered_at = self._time(candidate["discovered_at"], f"candidate[{cid}].discovered_at", candidate_id=cid)
        expires = self._time(
            receipt["freshness"]["expires_at"], f"receipt[{cid}].freshness.expires_at", candidate_id=cid
        )
        if checked_at is not None and discovered_at is not None and discovered_at > checked_at:
            self.fail("FRESHNESS-01", "candidate discovery occurs after its verification receipt", candidate_id=cid)
        if checked_at is not None and expires is not None:
            age = (reference_time - checked_at).total_seconds()
            expected_expiry = checked_at + timedelta(minutes=window_minutes)
            if age < 0 or age > window_minutes * 60 or expires < reference_time:
                self.fail("FRESHNESS-01", "receipt is outside delivery freshness window", candidate_id=cid)
            if expires != expected_expiry:
                self.fail("FRESHNESS-01", "receipt expiry must equal checked_at plus the frozen window", candidate_id=cid)
        if receipt["freshness"]["status"] != "fresh" or receipt["freshness"]["reverification_required"]:
            self.fail("FRESHNESS-01", "receipt freshness declaration is not fresh/final", candidate_id=cid)
        if receipt["freshness"].get("window_minutes") != window_minutes:
            self.fail("FRESHNESS-01", "receipt freshness window differs from the frozen intent", candidate_id=cid)
        access = receipt["access_state"]
        candidate_access = candidate["access_state"]
        if access != candidate_access:
            self.fail("VERIFY-01", "receipt access_state does not bind candidate access_state", candidate_id=cid)
        canonical_url = candidate["object"]["canonical_url"]
        discovered_url = candidate["source"]["discovered_url"]
        for label, url in (("canonical_url", canonical_url), ("discovered_url", discovered_url)):
            if _http_host(url) is None:
                self.fail("VERIFY-01", f"{label} must be a credential-free http/https URL", candidate_id=cid)
        if _http_host(discovered_url) != _normalized_domain(candidate["source"]["domain"]):
            self.fail("PROVENANCE-01", "source.domain does not match source.discovered_url host", candidate_id=cid)
        if access.get("checked_url") != canonical_url:
            self.fail("VERIFY-01", "checked_url must equal the resolved candidate canonical_url", candidate_id=cid)
        if (
            access["state"] not in {"accessible", "session_bound"}
            or not access["page_rendered"]
            or not access["canonical_url_resolved"]
            or access["challenge_detected"]
        ):
            self.fail("VERIFY-03", "soft 404/challenge/unrendered pages cannot qualify", candidate_id=cid)
        if isinstance(access.get("http_status"), int) and access["http_status"] >= 400:
            self.fail("VERIFY-03", "HTTP error status cannot be declared accessible", candidate_id=cid)
        if access["state"] == "session_bound" and access["mode"] not in {"signed_chrome", "subscription", "geo_or_age_gated"}:
            self.fail("VERIFY-03", "session_bound access requires a session-capable access mode", candidate_id=cid)
        access_policy = intent["access_policy"]
        allowed_modes = {
            "public": access_policy["allow_public_web"],
            "signed_chrome": access_policy["allow_signed_chrome"],
            "subscription": access_policy["allow_subscription"],
            "geo_or_age_gated": access_policy["allow_geo_or_age_gated"],
        }
        if not allowed_modes.get(access["mode"], False):
            self.fail("VERIFY-03", "receipt uses an access mode forbidden by the intent", candidate_id=cid)
        if access_policy["public_shareable_required_for_delivery"] and (
            access["state"] != "accessible" or access["shareable_without_session"] is not True
        ):
            self.fail("VERIFY-03", "delivery requires a publicly shareable accessible link", candidate_id=cid)
        if access["mode"] != "public" and access["shareable_without_session"] is True:
            self.fail(
                "VERIFY-03",
                "session-capable access cannot self-assert public shareability; a final public receipt is required",
                candidate_id=cid,
            )
        media_errors = media_evidence_errors(receipt, candidate["modality"])
        if not receipt_has_browser_media_evidence(receipt, candidate["modality"]) or media_errors:
            self.fail(
                "VERIFY-02",
                "modality-specific media evidence failed: " + "; ".join(media_errors or ["browser/manual surface missing"]),
                candidate_id=cid,
            )
        object_match = receipt["object_match"]
        if object_match["status"] != "matched" or not (
            object_match.get("matched_title") is True or object_match.get("matched_stable_id") is True
        ):
            self.fail("VERIFY-03", "specific creative object was not matched", candidate_id=cid)
        if candidate["modality"] == "video" and object_match.get("matched_stable_id") is not True:
            self.fail("VERIFY-03", "qualified video must match a stable work ID, not title alone", candidate_id=cid)
        evidence = receipt.get("evidence", [])
        captured_times: list[datetime] = []
        for evidence_index, evidence_item in enumerate(evidence):
            captured = self._time(
                evidence_item.get("captured_at"),
                f"receipt[{cid}].evidence[{evidence_index}].captured_at",
                candidate_id=cid,
            )
            if captured is not None:
                captured_times.append(captured)
                if checked_at is not None and captured > checked_at:
                    self.fail("FRESHNESS-01", "receipt evidence was captured after checked_at", candidate_id=cid)
        if checked_at is not None and checked_at not in captured_times:
            self.fail("VERIFY-02", "at least one evidence item must be captured at checked_at", candidate_id=cid)
        url_locators = {item.get("locator") for item in evidence if item.get("kind") == "url"}
        if canonical_url not in url_locators:
            self.fail("VERIFY-02", "receipt evidence does not contain the candidate canonical_url", candidate_id=cid)
        accountable_url = candidate["provenance_check"].get("accountable_url")
        if accountable_url not in url_locators:
            self.fail("PROVENANCE-01", "receipt evidence does not contain the accountable provenance URL", candidate_id=cid)
        asset_locator = candidate["object"]["asset_locator"]
        if candidate["modality"] == "image":
            image_render = receipt["media_check"].get("image_render") or {}
            locator_evidence = {item.get("locator") for item in evidence if item.get("kind") == "dom_locator"}
            if image_render.get("asset_locator") != asset_locator or asset_locator not in locator_evidence:
                self.fail("VERIFY-02", "image render/evidence locator does not bind candidate asset_locator", candidate_id=cid)
        else:
            progress_evidence = {item.get("locator") for item in evidence if item.get("kind") == "player_progress"}
            if asset_locator not in progress_evidence:
                self.fail("VERIFY-02", "video progress evidence does not bind candidate asset_locator", candidate_id=cid)
            if not isinstance(candidate["object"].get("stable_id"), str) or not candidate["object"]["stable_id"].strip():
                self.fail("VERIFY-03", "qualified video lacks a stable_id", candidate_id=cid)
            if not isinstance(asset_locator, str) or not asset_locator.strip():
                self.fail("VERIFY-03", "qualified video lacks an asset_locator", candidate_id=cid)
        provenance = receipt["provenance_check"]
        if provenance != candidate["provenance_check"]:
            self.fail("PROVENANCE-01", "receipt provenance does not bind candidate provenance", candidate_id=cid)
        if (
            provenance["status"] != "passed"
            or provenance["source_signal"] not in PROVENANCE_SIGNALS
            or not provenance["matched_object"]
            or not isinstance(provenance.get("accountable_owner"), str)
            or len(provenance["accountable_owner"].strip()) < 3
            or not isinstance(provenance.get("accountable_url"), str)
            or not provenance["accountable_url"].strip()
        ):
            self.fail("PROVENANCE-01", "accountable provenance is missing", candidate_id=cid)
        if _http_host(provenance.get("accountable_url")) is None:
            self.fail("PROVENANCE-01", "accountable provenance URL must use credential-free http/https", candidate_id=cid)
        if provenance.get("accountable_url") not in {canonical_url, candidate["source"]["discovered_url"]}:
            self.fail("PROVENANCE-01", "accountable provenance URL is not bound to the canonical or discovered object", candidate_id=cid)
        if provenance.get("source_signal") != candidate["source"].get("evidence_tier"):
            self.fail("PROVENANCE-01", "candidate and receipt provenance tiers differ", candidate_id=cid)
        if candidate["source"]["evidence_tier"] == "discovery_only":
            self.fail("PROVENANCE-01", "discovery_only candidates cannot enter the qualified 30", candidate_id=cid)
        if candidate["rights_scope"] != receipt["rights_scope"] or set(candidate["rights_scope"]) != RIGHTS_KEYS:
            self.fail("RIGHTS-01", "candidate and receipt must bind the same six-dimensional rights assessment", candidate_id=cid)
        for dimension, assessment in candidate["rights_scope"].items():
            if not isinstance(assessment.get("basis"), str) or len(assessment["basis"].strip()) < 12:
                self.fail("RIGHTS-01", f"rights dimension {dimension} lacks a substantive basis", candidate_id=cid)
            if dimension in HIGH_RISK_RIGHTS and assessment.get("state") == "allowed":
                self.fail(
                    "RIGHTS-01",
                    f"qualified reference cannot infer {dimension}=allowed from visibility or a self-declared basis",
                    candidate_id=cid,
                )
        shareable_state = candidate["rights_scope"]["shareable_without_session"]["state"]
        expected_shareable_state = {
            True: "allowed",
            False: "prohibited",
            "unknown": "unknown",
        }.get(access["shareable_without_session"])
        if shareable_state != expected_shareable_state:
            self.fail("RIGHTS-01", "shareability access evidence and rights state disagree", candidate_id=cid)
        expected_status = expected_dedup_status(candidate["dedup"]["version_relation"])
        if receipt["dedup_check"]["status"] != expected_status or expected_status not in {"unique", "authorized_version"}:
            self.fail("DEDUP-01", "version relation and receipt dedup eligibility disagree", candidate_id=cid)
        if candidate["dedup"]["canonical_url_key"] != normalize_url(canonical_url):
            self.fail("DEDUP-01", "candidate canonical_url_key is not the normalized canonical URL", candidate_id=cid)
        stable_id = candidate["object"].get("stable_id")
        expected_stable_key = f"{candidate['source']['source_id']}:{stable_id}" if stable_id else None
        if candidate["dedup"]["stable_id_key"] != expected_stable_key:
            self.fail("DEDUP-01", "candidate stable_id_key does not bind source_id and stable_id", candidate_id=cid)
        if receipt["dedup_check"].get("near_duplicate_group_id") != candidate["dedup"].get("near_duplicate_group_id"):
            self.fail("DEDUP-01", "receipt near-duplicate group differs from candidate", candidate_id=cid)
        if expected_status == "authorized_version" and not candidate["dedup"].get("near_duplicate_group_id"):
            self.fail("DEDUP-01", "authorized version needs an explicit near-duplicate group", candidate_id=cid)
        required_checks = ("exact_url_checked", "stable_id_checked", "campaign_version_checked")
        if any(receipt["dedup_check"].get(key) is not True for key in required_checks):
            self.fail("DEDUP-01", "URL, stable-ID, and campaign-version dedup checks must be performed", candidate_id=cid)
        fingerprint = candidate["dedup"].get("fingerprint")
        expected_capture_ids = [fingerprint.get("evidence_capture_id")] if isinstance(fingerprint, dict) else []
        if receipt["dedup_check"].get("fingerprint_capture_ids") != expected_capture_ids:
            self.fail("DEDUP-01", "receipt fingerprint capture IDs do not bind candidate evidence", candidate_id=cid)
        return finder, verifier

    def _validate_dedup(self, candidates: list[dict[str, Any]], receipts: dict[str, dict[str, Any]]) -> None:
        comparison_sha256 = dedup_comparison_set_sha256(candidates)
        for candidate in candidates:
            cid = candidate["candidate_id"]
            receipt = receipts.get(cid)
            if receipt is None:
                self.fail("DEDUP-01", "candidate is missing its dedup verification receipt", candidate_id=cid)
                continue
            dedup_check = receipt["dedup_check"]
            if dedup_check.get("comparison_set_sha256") != comparison_sha256:
                self.fail("DEDUP-01", "receipt is not bound to the exact final-30 fingerprint comparison set", candidate_id=cid)
            if dedup_check.get("phash_distance_threshold") != 6:
                self.fail("DEDUP-01", "receipt perceptual-hash threshold differs from the validator threshold", candidate_id=cid)
            if dedup_check.get("status") == "unique" and dedup_check.get("manual_version_review_ref") is not None:
                self.fail("DEDUP-01", "unique candidate must not cite an authorized-version review", candidate_id=cid)
        groups = find_duplicate_groups(candidates)
        unacceptable = []
        authorized_members: set[str] = set()
        for group in groups:
            reasons = set(group["reasons"])
            members = group["candidate_ids"]
            hard_identity = bool(reasons & {"canonical_url", "stable_key", "exact_hash", "work_id"})
            missing_receipts = [cid for cid in members if cid not in receipts]
            if missing_receipts:
                unacceptable.append({**group, "missing_receipt_ids": missing_receipts})
                continue
            authorized = all(receipts[cid]["dedup_check"]["status"] == "authorized_version" for cid in members)
            if hard_identity or not authorized:
                unacceptable.append(group)
                continue
            group_ids = {candidates_by_id["candidate_id"]: candidates_by_id for candidates_by_id in candidates}
            near_group_ids = {group_ids[cid]["dedup"].get("near_duplicate_group_id") for cid in members}
            review_refs = {receipts[cid]["dedup_check"].get("manual_version_review_ref") for cid in members}
            if len(near_group_ids) != 1 or None in near_group_ids or len(review_refs) != 1 or None in review_refs:
                unacceptable.append({**group, "reason": "authorized versions lack one shared group/review"})
                continue
            review_ref = next(iter(review_refs))
            review_path = self._resolve_evidence_ref(review_ref, "DEDUP-01", "authorized version review")
            if review_path is None or not review_path.is_file():
                unacceptable.append({**group, "reason": "authorized version review is missing"})
                continue
            try:
                review = read_json(review_path)
                review_schema = read_json(self.schemas_root / "dedup_version_review.schema.json")
                assert_schema_supported(review_schema)
                review_errors = validate_schema(review, review_schema)
            except (ContractError, SchemaViolation) as exc:
                self.fail("DEDUP-01", f"cannot validate authorized version review: {exc}")
                continue
            if review_errors:
                self.fail("DEDUP-01", f"authorized version review violates schema: {review_errors}")
                continue
            expected_identity = (
                self.artifacts["intent"]["run_id"],
                self.artifacts["intent"]["intent_id"],
                self.artifacts["intent"]["intent_version"],
                self.pack_contract["pack_id"],
            )
            observed_identity = (
                review.get("run_id"), review.get("intent_id"),
                review.get("intent_version"), review.get("pack_id"),
            )
            if (
                observed_identity != expected_identity
                or review.get("near_duplicate_group_id") != next(iter(near_group_ids))
                or set(review.get("candidate_ids", [])) != set(members)
            ):
                self.fail("DEDUP-01", "authorized version review does not bind run/pack/group members")
                continue
            evidence_index = {
                row.get("candidate_id"): row
                for row in review.get("fingerprint_evidence", [])
                if isinstance(row, dict)
            }
            if set(evidence_index) != set(members) or len(evidence_index) != len(review.get("fingerprint_evidence", [])):
                self.fail("DEDUP-01", "authorized version review fingerprint evidence does not exactly cover the group")
                continue
            evidence_mismatch = False
            for cid in members:
                fingerprint = group_ids[cid]["dedup"]["fingerprint"]
                expected_evidence = {
                    "candidate_id": cid,
                    "capture_id": fingerprint["evidence_capture_id"],
                    "exact_or_manifest_sha256": fingerprint["exact_or_manifest_sha256"],
                    "perceptual_hash": fingerprint["perceptual_hash"],
                    "comparison_set_sha256": comparison_sha256,
                }
                if evidence_index[cid] != expected_evidence:
                    evidence_mismatch = True
            if evidence_mismatch:
                self.fail("DEDUP-01", "authorized version review fingerprint evidence is stale or mismatched")
                continue
            try:
                reviewed_at = parse_timestamp(review["reviewed_at"])
                latest_receipt = max(parse_timestamp(receipts[cid]["checked_at"]) for cid in members)
                delivery_time = parse_timestamp(self.artifacts["report"]["delivery_reference_time"])
            except ContractError as exc:
                self.fail("DEDUP-01", str(exc))
                continue
            if reviewed_at < latest_receipt or reviewed_at > delivery_time:
                self.fail("DEDUP-01", "authorized version review time must follow fingerprints and precede delivery")
                continue
            authorized_members.update(members)
        if unacceptable:
            self.fail("DEDUP-01", f"unacceptable duplicate groups: {unacceptable}")
        declared_authorized = {
            cid for cid, receipt in receipts.items()
            if cid in {item["candidate_id"] for item in candidates}
            and receipt["dedup_check"]["status"] == "authorized_version"
        }
        if declared_authorized != authorized_members:
            self.fail("DEDUP-01", "authorized-version candidates do not exactly match validated duplicate groups")
        self.metrics["duplicate_groups"] = groups

    def _validate_diversity(self, selected: list[dict[str, Any]]) -> None:
        domains = [_site_domain(item["source"]["domain"]) or "invalid-domain" for item in selected]
        families = [item["source"]["source_family_id"] for item in selected]
        territories = [item["diversity"]["territory_id"] for item in selected]
        campaigns = [item["dedup"]["campaign_group_id"] for item in selected if item["dedup"]["campaign_group_id"]]
        creators = [item["dedup"]["creator_group_id"] for item in selected if item["dedup"]["creator_group_id"]]
        near_groups = [item["dedup"]["near_duplicate_group_id"] for item in selected if item["dedup"]["near_duplicate_group_id"]]
        computed = {
            "distinct_domains": len(set(domains)),
            "distinct_source_families": len(set(families)),
            "territory_count": len(set(territories)),
            "max_per_domain": max(Counter(domains).values()),
            "max_per_campaign_or_creator": max([1] + list(Counter(campaigns).values()) + list(Counter(creators).values())),
            "max_per_near_duplicate_group": max([1] + list(Counter(near_groups).values())),
        }
        declared = self.artifacts["selected"]["diversity_policy"]
        report_declared = self.artifacts["report"]["diversity"]
        for key, value in computed.items():
            if declared.get(key) != value or report_declared.get(key) != value:
                self.fail("DIVERSITY-01", f"declared diversity metric {key} does not equal computed {value}")
        requirements = self.artifacts["intent"]["diversity_requirements"]
        if (
            declared.get("broad_brief") is not requirements["broad_brief"]
            or report_declared.get("broad_brief") is not requirements["broad_brief"]
        ):
            self.fail("DIVERSITY-01", "selected/report broad_brief flags must equal the frozen intent")
        violations = []
        # A narrow-brief declaration explains concentration; it must not silently
        # disable the declared diversity contract.  Any threshold exception still
        # requires an evidence-bearing waiver and a registered approver.
        if computed["distinct_domains"] < requirements["min_domains"]:
            violations.append("min_domains")
        if computed["distinct_source_families"] < requirements["min_source_families"]:
            violations.append("min_source_families")
        if not requirements["territory_count_min"] <= computed["territory_count"] <= requirements["territory_count_max"]:
            violations.append("territory_count")
        if computed["max_per_domain"] > requirements["max_per_domain"]:
            violations.append("max_per_domain")
        if computed["max_per_campaign_or_creator"] > requirements["max_per_campaign_or_creator"]:
            violations.append("max_per_campaign_or_creator")
        if computed["max_per_near_duplicate_group"] > requirements["max_per_near_duplicate_group"]:
            violations.append("max_per_near_duplicate_group")
        waiver = declared.get("waiver")
        if waiver != report_declared.get("waiver"):
            self.fail("DIVERSITY-01", "selected and report diversity waivers differ")
        if violations and not (
            isinstance(waiver, dict) and waiver.get("reason") and waiver.get("evidence") and waiver.get("approved_by")
        ):
            self.fail("DIVERSITY-01", f"diversity violations require an evidence-bearing waiver: {violations}")
        if violations and isinstance(waiver, dict):
            declared_constraints = set(waiver.get("constraints", []))
            uncovered = sorted(set(violations) - declared_constraints)
            overclaimed = sorted(declared_constraints - set(violations))
            registered_approvers = {
                self.artifacts["selected"]["curation_trace"]["diversity_curator_id"],
                self.artifacts["selected"]["curation_trace"]["root_synthesizer_id"],
            }
            if uncovered:
                self.fail("DIVERSITY-01", f"waiver does not cover violations: {uncovered}")
            if overclaimed:
                self.fail("DIVERSITY-01", f"waiver claims constraints that are not violated: {overclaimed}")
            if waiver.get("approved_by") not in registered_approvers:
                self.fail("DIVERSITY-01", "waiver approver is not the registered diversity curator or root synthesizer")
            if not isinstance(waiver.get("reason"), str) or len(waiver["reason"].strip()) < 20:
                self.fail("DIVERSITY-01", "waiver reason is not substantive")
            if not isinstance(waiver.get("remaining_risk"), str) or len(waiver["remaining_risk"].strip()) < 20:
                self.fail("DIVERSITY-01", "waiver remaining_risk is not substantive")
            for ref in waiver.get("evidence", []):
                path = self._resolve_evidence_ref(ref, "DIVERSITY-01", "waiver evidence ref")
                if path is None:
                    continue
                if not path.is_file():
                    self.fail("DIVERSITY-01", f"waiver evidence ref does not exist: {ref}")
                elif path.resolve() in {
                    self.artifact_files["report"].resolve(),
                    self.artifact_files["selected"].resolve(),
                }:
                    self.fail("DIVERSITY-01", "waiver cannot use its own declaration as evidence")
        expected_status = "waived" if violations else "passed"
        if report_declared.get("status") != expected_status:
            self.fail("DIVERSITY-01", "report diversity status does not match computed outcome")
        self.metrics["diversity"] = {**computed, "violations": violations}

    def _validate_route_quota(
        self,
        strategy: str,
        candidates: list[dict[str, Any]],
        selected_candidates: list[dict[str, Any]],
    ) -> None:
        if strategy != "unified_territory":
            return
        quota = self.artifacts["intent"]["routing"]["unified_territory_quota"]
        modalities = Counter(item["modality"] for item in candidates)
        selected_modalities = Counter(item["modality"] for item in selected_candidates)
        territories: dict[str, set[str]] = defaultdict(set)
        for item in candidates:
            territories[item["diversity"]["territory_id"]].add(item["modality"])
        cross_modal = sum(1 for modalities_present in territories.values() if modalities_present == {"image", "video"})
        if quota["image_qualified_target"] + quota["video_qualified_target"] != 30:
            self.fail("ROUTE-02", "unified qualified image/video targets must sum to 30")
        if quota["image_selected_target"] + quota["video_selected_target"] != 20:
            self.fail("ROUTE-02", "unified selected image/video targets must sum to 20")
        if (
            modalities["image"] != quota["image_qualified_target"]
            or modalities["video"] != quota["video_qualified_target"]
        ):
            self.fail("ROUTE-02", "unified qualified image/video exact quota is not met")
        if (
            selected_modalities["image"] != quota["image_selected_target"]
            or selected_modalities["video"] != quota["video_selected_target"]
        ):
            self.fail("ROUTE-02", "unified selected image/video exact quota is not met")
        if cross_modal < quota["cross_modal_territory_min"]:
            self.fail("ROUTE-02", "cross-modal territory minimum is not met")

    def _validate_agents(self, finder_ids: set[str], verifier_ids: set[str]) -> None:
        registry = self.artifacts["approaches"]
        agent_rows = registry["agents"]
        agent_roles = {
            item["agent_id"]: {item["role"], *item.get("additional_roles", [])}
            for item in agent_rows
        }
        if len(agent_roles) != len(agent_rows):
            self.fail("AGENT-01", "agent registry contains duplicate agent_id values")
        session_owners = [item for item in agent_rows if item["session_owner"]]
        if len(session_owners) > 1:
            self.fail("AGENT-01", "only one agent may own the signed Chrome session")
        signed_chrome_used = any(
            item.get("access_state", {}).get("mode") == "signed_chrome"
            for item in self.artifacts["candidates"]
        )
        if signed_chrome_used:
            if len(session_owners) != 1:
                self.fail("AGENT-01", "signed Chrome evidence requires exactly one registered session owner")
            elif "authenticated_source_operator" not in agent_roles.get(session_owners[0]["agent_id"], set()):
                self.fail("AGENT-01", "signed Chrome session owner lacks authenticated_source_operator responsibility")
        approach_rows = registry["approaches"]
        all_approaches = {item["approach_id"]: item for item in approach_rows}
        if len(all_approaches) != len(approach_rows):
            self.fail("AGENT-01", "approach registry contains duplicate approach_id values")
        failure_ids = [
            record["failure_id"]
            for item in approach_rows
            for record in item["failure_records"]
        ]
        if len(failure_ids) != len(set(failure_ids)):
            self.fail("AGENT-01", "failure_id values must be unique across the entire run")
        query_ids = [query["query_id"] for item in approach_rows for query in item["queries"]]
        if len(query_ids) != len(set(query_ids)):
            self.fail("AGENT-01", "query_id values must be unique across the entire run")
        expected_packs = {
            item["pack_id"]: item["modality"]
            for item in self.artifacts["intent"]["routing"]["pack_contracts"]
        }
        registered_pack_ids = {item["pack_id"] for item in approach_rows}
        if registered_pack_ids != set(expected_packs):
            self.fail("AGENT-01", "approach registry pack IDs do not exactly match routing pack contracts")
        for approach in approach_rows:
            if approach["modality"] != expected_packs.get(approach["pack_id"]):
                self.fail("AGENT-01", f"approach modality differs from its pack contract: {approach['approach_id']}")
        pack_id = self.pack_contract["pack_id"]
        approaches = {
            approach_id: item
            for approach_id, item in all_approaches.items()
            if item["pack_id"] == pack_id
        }
        if len(approaches) < 3:
            self.fail("AGENT-01", "each pack requires at least three independently registered approaches")
        completed = [item for item in approaches.values() if item["status"] == "complete"]
        completed_methods = {item["method"] for item in completed}
        if len(completed_methods) < 3:
            self.fail("AGENT-01", "at least three distinct approach methods are required")
        candidate_rows_by_approach: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for candidate in self.artifacts["candidates"]:
            candidate_rows_by_approach[candidate["agent_trace"]["approach_id"]].append(candidate)
        receipt_by_id = {receipt["receipt_id"]: receipt for receipt in self.artifacts["receipts"]}
        final_statuses = {"qualified", "selected", "rejected"}
        for approach in approaches.values():
            returned = approach["returned_count"]
            qualified = approach["qualified_count"]
            expected_rate = round(qualified / returned, 3) if returned else 0
            contributed = candidate_rows_by_approach.get(approach["approach_id"], [])
            final_contributed = [item for item in contributed if item["status"] in final_statuses]
            nonfinal_ids = {
                item["candidate_id"] for item in contributed if item["status"] not in final_statuses
            }
            executor_roles = agent_roles.get(approach["executing_agent_id"], set())
            if not executor_roles & {"search_scout", "credit_graph_scout", "authenticated_source_operator"}:
                self.fail("AGENT-01", f"approach executor is absent or incompatible for {approach['approach_id']}")
            if approach["status"] not in {"complete", "abandoned"}:
                self.fail("AGENT-01", f"completed run contains nonterminal approach {approach['approach_id']}")
            if approach["status"] == "complete" and returned == 0:
                self.fail("AGENT-01", f"complete approach has no execution yield for {approach['approach_id']}")
            if returned != len(contributed) or qualified != len(final_contributed):
                self.fail("AGENT-01", f"approach yield counts do not reconcile to the candidate ledger for {approach['approach_id']}")
            if qualified > returned or abs(approach["qualification_rate"] - expected_rate) > 0.002:
                self.fail("AGENT-01", f"approach yield arithmetic is inconsistent for {approach['approach_id']}")
            if approach["status"] == "abandoned" and qualified != 0:
                self.fail("AGENT-01", f"abandoned approach cannot claim qualified yield for {approach['approach_id']}")
            failure_records = approach["failure_records"]
            if (approach["status"] == "abandoned" or nonfinal_ids) and not failure_records:
                self.fail("AGENT-01", f"approach failures are not recorded for {approach['approach_id']}")
            if failure_records and not isinstance(approach.get("next_round_adjustment"), str):
                self.fail("AGENT-01", f"approach failure lacks a next-round adjustment for {approach['approach_id']}")
            queries = {query["query_id"]: query for query in approach["queries"]}
            grounded_candidate_ids: list[str] = []
            grounded_receipt_ids: list[str] = []
            failure_paths: set[tuple[str, str, int]] = set()
            started_at = self._time(
                approach.get("started_at"),
                f"approach[{approach['approach_id']}].started_at",
                "AGENT-01",
            )
            for record in failure_records:
                path = (record["query_id"], record["source_family_id"], record["round"])
                if path in failure_paths:
                    self.fail("AGENT-01", f"duplicate failure path without new evidence for {approach['approach_id']}")
                failure_paths.add(path)
                query = queries.get(record["query_id"])
                if query is None or query["round"] != record["round"]:
                    self.fail("AGENT-01", f"failure record does not bind a registered query/round for {approach['approach_id']}")
                if record["source_family_id"] not in approach["source_family_ids"]:
                    self.fail("AGENT-01", f"failure record source family is absent from {approach['approach_id']}")
                observed_at = self._time(
                    record.get("observed_at"),
                    f"failure[{record.get('failure_id')}].observed_at",
                    "AGENT-01",
                )
                if started_at is not None and observed_at is not None and observed_at < started_at:
                    self.fail("AGENT-01", f"failure record predates its approach start for {approach['approach_id']}")
                record_candidate_ids = record["candidate_ids"]
                record_receipt_ids = record["receipt_ids"]
                grounded_candidate_ids.extend(record_candidate_ids)
                grounded_receipt_ids.extend(record_receipt_ids)
                if not record_candidate_ids and not record_receipt_ids and record["failure_code"] != "zero_yield":
                    self.fail("AGENT-01", f"failure record lacks candidate/receipt evidence for {approach['approach_id']}")
                if record["failure_code"] == "zero_yield" and (returned != 0 or record_candidate_ids or record_receipt_ids):
                    self.fail("AGENT-01", f"zero_yield failure contradicts ledger evidence for {approach['approach_id']}")
                for candidate_id in record_candidate_ids:
                    candidate = next((item for item in contributed if item["candidate_id"] == candidate_id), None)
                    if candidate is None or candidate["status"] in final_statuses:
                        self.fail("AGENT-01", f"failure record references a foreign or final candidate for {approach['approach_id']}")
                    elif candidate["agent_trace"]["query_id"] != record["query_id"]:
                        self.fail("AGENT-01", f"failure record query does not match its candidate evidence for {approach['approach_id']}")
                    elif candidate["source"]["source_family_id"] != record["source_family_id"]:
                        self.fail("AGENT-01", f"failure record source family does not match its candidate evidence for {approach['approach_id']}")
                for receipt_id in record_receipt_ids:
                    receipt = receipt_by_id.get(receipt_id)
                    if receipt is None or receipt.get("candidate_id") not in record_candidate_ids:
                        self.fail("AGENT-01", f"failure receipt does not bind a failed candidate for {approach['approach_id']}")
            if len(grounded_candidate_ids) != len(set(grounded_candidate_ids)):
                self.fail("AGENT-01", f"failed candidate is counted more than once for {approach['approach_id']}")
            if len(grounded_receipt_ids) != len(set(grounded_receipt_ids)):
                self.fail("AGENT-01", f"failure receipt is counted more than once for {approach['approach_id']}")
            if set(grounded_candidate_ids) != nonfinal_ids:
                self.fail("AGENT-01", f"failure records do not exactly cover non-final returned candidates for {approach['approach_id']}")
            expected_failure_receipt_ids = {
                receipt["receipt_id"]
                for receipt in self.artifacts["receipts"]
                if receipt.get("candidate_id") in nonfinal_ids
            }
            if set(grounded_receipt_ids) != expected_failure_receipt_ids:
                self.fail("AGENT-01", f"failure records do not exactly cover failed-candidate receipts for {approach['approach_id']}")
        coverage_rows = registry["coverage"]
        coverage_ids = [item["pack_id"] for item in coverage_rows]
        if len(coverage_ids) != len(set(coverage_ids)) or set(coverage_ids) != set(expected_packs):
            self.fail("AGENT-01", "coverage rows must uniquely and exactly match routing pack contracts")
        coverage = next((item for item in coverage_rows if item["pack_id"] == pack_id), None)
        if coverage is None:
            self.fail("AGENT-01", "pack is missing its approach coverage declaration")
            coverage = {
                "declared_distinct_method_count": 0,
                "covered_methods": [],
                "required_distinct_method_count": 3,
                "modality": None,
            }
        if (
            coverage.get("modality") != self.pack_contract["modality"]
            or
            coverage["declared_distinct_method_count"] != len(completed_methods)
            or set(coverage["covered_methods"]) != completed_methods
            or coverage["required_distinct_method_count"] > len(completed_methods)
        ):
            self.fail("AGENT-01", "approach coverage declaration does not match terminal executed methods")
        if self.artifacts["intent"]["run_mode"] != "retrospective_smoke":
            created_at = self._time(registry.get("created_at"), "approach registry created_at", "PREREG-01")
            discovered = [
                self._time(item.get("discovered_at"), f"candidate[{item.get('candidate_id')}].discovered_at", "PREREG-01")
                for item in self.artifacts["candidates"]
            ]
            discovered = [item for item in discovered if item is not None]
            if created_at is not None and discovered and created_at > min(discovered):
                self.fail("PREREG-01", "approach registry was created after discovery began")
        source_registry = read_json(self.schemas_root / "source_registry.json")
        registered_families = {item["family_id"] for item in source_registry["families"]}
        registered_sources = {item["source_id"]: item for item in source_registry["sources"]}
        candidate_families = {item["source"]["source_family_id"] for item in self.artifacts["candidates"]}
        approach_families = {
            family_id for item in approaches.values() for family_id in item["source_family_ids"]
        }
        unknown_families = (candidate_families | approach_families) - registered_families
        if unknown_families:
            self.fail("PROVENANCE-01", f"run uses source families absent from source_registry: {sorted(unknown_families)}")
        site_bindings: dict[str, set[tuple[str, str]]] = defaultdict(set)
        for candidate in self.artifacts["candidates"]:
            source = candidate["source"]
            domain = _normalized_domain(source["domain"])
            source_id = source["source_id"]
            family_id = source["source_family_id"]
            if domain is None:
                self.fail("PROVENANCE-01", "candidate source.domain is empty", candidate_id=candidate.get("candidate_id"))
                continue
            site_domain = _site_domain(domain)
            if site_domain is None:
                self.fail("PROVENANCE-01", "candidate source.domain has no accountable site domain", candidate_id=candidate.get("candidate_id"))
                continue
            site_bindings[site_domain].add((source_id, family_id))
            registered = registered_sources.get(source_id)
            if registered is not None:
                registered_host = _http_host(registered["canonical_url"])
                if family_id != registered["family_id"] or domain != registered_host:
                    self.fail("PROVENANCE-01", "candidate source conflicts with its checked-in registry entry", candidate_id=candidate.get("candidate_id"))
                if candidate.get("modality") not in registered.get("modalities", []):
                    self.fail("PROVENANCE-01", "candidate modality is not supported by its checked-in source", candidate_id=candidate.get("candidate_id"))
            elif source_id != f"runtime:{domain}":
                self.fail(
                    "PROVENANCE-01",
                    "unregistered sources must use deterministic runtime:<source.domain> identity",
                    candidate_id=candidate.get("candidate_id"),
                )
        for domain, bindings in site_bindings.items():
            if len(bindings) != 1:
                self.fail("PROVENANCE-01", f"registrable site domain {domain} maps to multiple source/family identities: {sorted(bindings)}")
        candidate_by_id = {item["candidate_id"]: item for item in self.artifacts["candidates"]}
        shortlist_by_approach: Counter[str] = Counter()
        shortlist_id_set = set(self.artifacts["shortlist"]["candidate_ids"])
        for cid, candidate in candidate_by_id.items():
            trace = candidate["agent_trace"]
            if cid in shortlist_id_set:
                shortlist_by_approach[trace["approach_id"]] += 1
            approach = approaches.get(trace["approach_id"])
            if approach is None or approach["executing_agent_id"] != trace["finder_agent_id"]:
                self.fail("AGENT-01", "candidate finder is not bound to its approach executor", candidate_id=cid)
            elif trace["query_id"] not in {item["query_id"] for item in approach["queries"]}:
                self.fail("AGENT-01", "candidate query_id is absent from its registered approach", candidate_id=cid)
            elif candidate["source"]["source_family_id"] not in approach["source_family_ids"]:
                self.fail("PROVENANCE-01", "candidate source family is absent from its pre-registered approach", candidate_id=cid)
        for approach_id, final_count in shortlist_by_approach.items():
            approach = approaches.get(approach_id)
            if approach is None:
                continue
            if approach["qualified_count"] < final_count:
                self.fail("AGENT-01", f"approach {approach_id} claims fewer qualified items than it contributed to the final 30")
        separation = self.artifacts["report"]["agent_separation"]
        relevance = separation["relevance_curator_agent_id"]
        diversity = separation["diversity_curator_agent_id"]
        root_synthesizer = separation["root_synthesizer_agent_id"]
        auditor = separation["auditor_agent_id"]
        for artifact_name in ("selected", "rejected"):
            trace = self.artifacts[artifact_name]["curation_trace"]
            if trace["relevance_curator_id"] != relevance or trace["diversity_curator_id"] != diversity:
                self.fail("AGENT-01", f"{artifact_name} curation trace differs from report")
            if "root_synthesizer" not in agent_roles.get(trace["root_synthesizer_id"], set()):
                self.fail("AGENT-01", f"{artifact_name} lacks a registered root synthesizer")
            for ref_key, reviewer_id in (
                ("relevance_review_ref", trace["relevance_curator_id"]),
                ("diversity_review_ref", trace["diversity_curator_id"]),
                ("resolution_ref", trace["root_synthesizer_id"]),
            ):
                ref = trace[ref_key]
                path = self._resolve_evidence_ref(ref, "AGENT-01", f"{artifact_name} {ref_key}")
                if path is None:
                    continue
                if not path.is_file():
                    self.fail("AGENT-01", f"{artifact_name} {ref_key} does not exist: {ref}")
                    continue
                try:
                    review = read_json(path)
                except ContractError as exc:
                    self.fail("AGENT-01", f"cannot parse {ref}: {exc}")
                    continue
                if not isinstance(review, dict):
                    self.fail("AGENT-01", f"{artifact_name} {ref_key} must contain a JSON object")
                    continue
                if review.get("run_id") != self.artifacts["intent"]["run_id"] or reviewer_id not in {
                    review.get("reviewer"), review.get("synthesizer")
                }:
                    self.fail("AGENT-01", f"{artifact_name} {ref_key} is not bound to its run/reviewer")
                if (
                    review.get("intent_id") != self.artifacts["intent"]["intent_id"]
                    or review.get("intent_version") != self.artifacts["intent"]["intent_version"]
                    or review.get("pack_id") != self.pack_contract["pack_id"]
                ):
                    self.fail("AGENT-01", f"{artifact_name} {ref_key} is not bound to intent/version/pack")
                if not isinstance(review.get("rationale"), str) or not review["rationale"].strip():
                    self.fail("AGENT-01", f"{artifact_name} {ref_key} lacks a substantive rationale")
                shortlist_ids = set(self.artifacts["shortlist"]["candidate_ids"])
                if ref_key == "relevance_review_ref":
                    if review.get("verdict") != "pass":
                        self.fail("AGENT-01", f"{artifact_name} relevance review did not pass")
                    if _string_set(review.get("ordered_candidate_ids")) != shortlist_ids:
                        self.fail("AGENT-01", f"{artifact_name} relevance review does not cover the shortlist 30")
                if ref_key == "diversity_review_ref":
                    if review.get("verdict") != "pass":
                        self.fail("AGENT-01", f"{artifact_name} diversity review did not pass")
                    expected_metrics = {
                        key: value for key, value in self.metrics.get("diversity", {}).items() if key != "violations"
                    }
                    if review.get("metrics") != expected_metrics:
                        self.fail("AGENT-01", f"{artifact_name} diversity review metrics differ from validator computation")
                if ref_key == "resolution_ref":
                    if review.get("decision") != "accepted_20_10_partition":
                        self.fail("AGENT-01", f"{artifact_name} resolution review lacks an accepted 20/10 decision")
                    if (
                        _string_set(review.get("selected")) != set(_ids(self.artifacts["selected"]["items"]))
                        or _string_set(review.get("rejected")) != set(_ids(self.artifacts["rejected"]["items"]))
                    ):
                        self.fail("AGENT-01", f"{artifact_name} resolution review does not bind the final 20/10")
        selected_trace = self.artifacts["selected"]["curation_trace"]
        rejected_trace = self.artifacts["rejected"]["curation_trace"]
        if selected_trace != rejected_trace:
            self.fail("AGENT-01", "selected and rejected artifacts do not share one curation handoff trace")
        if selected_trace["root_synthesizer_id"] != root_synthesizer:
            self.fail("AGENT-01", "report root synthesizer differs from the curation trace")

        capture_operator_ids = {
            record["operator_agent_id"] for record in self.artifacts["captures"]
        }
        if (
            set(separation["finder_agent_ids"]) != finder_ids
            or set(separation["capture_operator_agent_ids"]) != capture_operator_ids
            or set(separation["verifier_agent_ids"]) != verifier_ids
        ):
            self.fail("AGENT-01", "report agent sets do not match candidate/receipt evidence")
        role_sets = [
            finder_ids,
            capture_operator_ids,
            verifier_ids,
            {relevance},
            {diversity},
            {root_synthesizer},
            {auditor},
        ]
        if any(left & right for index, left in enumerate(role_sets) for right in role_sets[index + 1:]):
            self.fail("AGENT-01", "decision-critical finder/capture/verifier/curator/root/auditor agent IDs must be pairwise disjoint")
        for agent_id in finder_ids:
            if not agent_roles.get(agent_id, set()) & {"search_scout", "credit_graph_scout", "authenticated_source_operator"}:
                self.fail("AGENT-01", f"finder {agent_id} has an incompatible registry role")
        for agent_id in capture_operator_ids:
            if not agent_roles.get(agent_id, set()) & {"capture_operator", "authenticated_source_operator"}:
                self.fail("AGENT-01", f"capture operator {agent_id} has an incompatible registry role")
        for agent_id in verifier_ids:
            if "verification_agent" not in agent_roles.get(agent_id, set()):
                self.fail("AGENT-01", f"verifier {agent_id} is not registered as verification_agent")
        if "relevance_curator" not in agent_roles.get(relevance, set()) or "diversity_curator" not in agent_roles.get(diversity, set()):
            self.fail("AGENT-01", "both independent curator roles must be registered")
        if "root_synthesizer" not in agent_roles.get(root_synthesizer, set()):
            self.fail("AGENT-01", "root synthesizer is not registered")

        review_specs = {
            "relevance": (selected_trace["relevance_review_ref"], "relevance_review.schema.json", relevance),
            "diversity": (selected_trace["diversity_review_ref"], "diversity_review.schema.json", diversity),
            "resolution": (selected_trace["resolution_ref"], "resolution_review.schema.json", root_synthesizer),
        }
        review_docs: dict[str, dict[str, Any]] = {}
        review_paths: dict[str, Path] = {}
        for review_kind, (ref, schema_name, expected_agent) in review_specs.items():
            path = self._resolve_evidence_ref(ref, "AGENT-01", f"{review_kind} review")
            if path is None or not path.is_file():
                continue
            try:
                document = read_json(path)
                schema = read_json(self.schemas_root / schema_name)
                assert_schema_supported(schema)
                errors = validate_schema(document, schema)
            except (ContractError, SchemaViolation) as exc:
                self.fail("AGENT-01", f"cannot validate {review_kind} review: {exc}")
                continue
            if errors:
                self.fail("AGENT-01", f"{review_kind} review violates schema: {errors}")
                continue
            agent_field = "synthesizer" if review_kind == "resolution" else "reviewer"
            if document.get(agent_field) != expected_agent:
                self.fail("AGENT-01", f"{review_kind} review is attributed to the wrong agent")
            review_docs[review_kind] = document
            review_paths[review_kind] = path

        expected_curation_input = curation_input_sha256(
            self.artifacts["intent"],
            self.artifacts["shortlist"],
            self.artifacts["candidates"],
            self.artifacts["receipts"],
        )
        if len(review_docs) == 3:
            relevance_review = review_docs["relevance"]
            diversity_review = review_docs["diversity"]
            resolution_review = review_docs["resolution"]
            if {
                relevance_review.get("input_contract_sha256"),
                diversity_review.get("input_contract_sha256"),
                resolution_review.get("input_contract_sha256"),
            } != {expected_curation_input}:
                self.fail("AGENT-01", "blind curators and root resolution are not bound to one frozen input contract")
            if (
                resolution_review.get("relevance_review_ref") != selected_trace["relevance_review_ref"]
                or resolution_review.get("diversity_review_ref") != selected_trace["diversity_review_ref"]
                or resolution_review.get("relevance_review_sha256") != _sha256(review_paths["relevance"])
                or resolution_review.get("diversity_review_sha256") != _sha256(review_paths["diversity"])
            ):
                self.fail("AGENT-01", "root resolution does not hash-bind both frozen curator reviews")
            try:
                shortlist_created = parse_timestamp(self.artifacts["shortlist"]["created_at"])
                latest_receipt = max(parse_timestamp(item["checked_at"]) for item in self.artifacts["receipts"])
                relevance_started = parse_timestamp(relevance_review["started_at"])
                relevance_completed = parse_timestamp(relevance_review["completed_at"])
                diversity_started = parse_timestamp(diversity_review["started_at"])
                diversity_completed = parse_timestamp(diversity_review["completed_at"])
                resolution_started = parse_timestamp(resolution_review["started_at"])
                resolution_completed = parse_timestamp(resolution_review["completed_at"])
                selected_created = parse_timestamp(self.artifacts["selected"]["created_at"])
                rejected_created = parse_timestamp(self.artifacts["rejected"]["created_at"])
            except ContractError as exc:
                self.fail("AGENT-01", str(exc))
                resolution_completed = None
            else:
                frozen_input_time = max(shortlist_created, latest_receipt)
                if relevance_started < frozen_input_time or diversity_started < frozen_input_time:
                    self.fail("AGENT-01", "curation began before the qualified input set was frozen")
                if relevance_completed < relevance_started or diversity_completed < diversity_started:
                    self.fail("AGENT-01", "curator review completion predates its start")
                if resolution_started <= max(relevance_completed, diversity_completed):
                    self.fail("AGENT-01", "root resolution began before both blind curator reviews were frozen")
                if resolution_completed < resolution_started:
                    self.fail("AGENT-01", "root resolution completion predates its start")
                if min(selected_created, rejected_created) < resolution_completed:
                    self.fail("AGENT-01", "final partition artifacts predate root resolution completion")
            self.metrics["curation_resolution_completed_at"] = resolution_review.get("completed_at")

        for receipt in self.artifacts["receipts"]:
            review_ref = receipt.get("dedup_check", {}).get("manual_version_review_ref")
            if review_ref is None:
                continue
            path = self._resolve_evidence_ref(review_ref, "AGENT-01", "dedup version review independence")
            if path is not None and path.is_file():
                try:
                    dedup_review = read_json(path)
                except ContractError as exc:
                    self.fail("AGENT-01", str(exc))
                else:
                    if dedup_review.get("reviewer") != diversity:
                        self.fail("AGENT-01", "authorized-version review must be owned by the independent diversity curator")

        operative = finder_ids | capture_operator_ids | verifier_ids | {relevance, diversity, root_synthesizer}
        if "adversarial_auditor" not in agent_roles.get(auditor, set()) or auditor in operative:
            self.fail("AUDIT-01", "auditor must be registered and independent from operative agents")
        if not separation["no_self_approval"] or not separation["decision_roles_disjoint"] or not separation["auditor_independent"]:
            self.fail("AUDIT-01", "report does not assert independent adversarial audit")
        audit = self.artifacts["report"]["adversarial_audit"]
        required_checks = {"soft_404", "media_truth", "provenance", "deduplication", "diversity", "rights_separation"}
        if audit["auditor_id"] != auditor or audit["outcome"] != "pass":
            self.fail("AUDIT-01", "adversarial audit must be passed by the registered independent auditor")
        if not operative.issubset(set(audit["independent_from"])):
            self.fail("AUDIT-01", "adversarial audit independence list does not cover operative agents")
        if not required_checks.issubset(set(audit["checks"])):
            self.fail("AUDIT-01", "adversarial audit lacks required attack checks")
        if set(audit["candidate_ids"]) != set(self.artifacts["shortlist"]["candidate_ids"]):
            self.fail("AUDIT-01", "adversarial audit must cover all 30 candidates")
        try:
            audit_time = parse_timestamp(audit["completed_at"])
            latest_receipt = max(parse_timestamp(item["checked_at"]) for item in self.artifacts["receipts"])
            delivery_time = parse_timestamp(self.artifacts["report"]["delivery_reference_time"])
            if audit_time < latest_receipt or audit_time > delivery_time:
                self.fail("AUDIT-01", "adversarial audit time must follow receipts and not exceed delivery time")
            resolution_completed_at = self.metrics.get("curation_resolution_completed_at")
            if resolution_completed_at is not None and audit_time <= parse_timestamp(resolution_completed_at):
                self.fail("AUDIT-01", "adversarial audit must begin after the curation resolution is complete")
        except ContractError as exc:
            self.fail("AUDIT-01", str(exc))
        for ref in audit["evidence_refs"]:
            path = self._resolve_evidence_ref(ref, "AUDIT-01", "audit evidence ref")
            if path is None:
                continue
            if not path.is_file():
                self.fail("AUDIT-01", f"audit evidence ref does not exist: {ref}")
        receipt_evidence_path = self.artifact_files["receipts"].resolve()
        resolved_audit_refs = {
            path for ref in audit["evidence_refs"]
            if (path := self._resolve_evidence_ref(ref, "AUDIT-01", "audit evidence ref")) is not None
        }
        if receipt_evidence_path not in resolved_audit_refs:
            self.fail("AUDIT-01", "adversarial audit evidence must include the bound verification receipt ledger")

        audit_artifact_path = self._resolve_evidence_ref(
            "07_audit/adversarial_audit_results.json", "AUDIT-01", "adversarial audit artifact"
        )
        if audit_artifact_path not in resolved_audit_refs:
            self.fail("AUDIT-01", "adversarial audit must cite 07_audit/adversarial_audit_results.json")
        elif audit_artifact_path is not None and audit_artifact_path.is_file():
            try:
                audit_artifact = read_json(audit_artifact_path)
            except ContractError as exc:
                self.fail("AUDIT-01", f"cannot parse adversarial audit artifact: {exc}")
            else:
                if not isinstance(audit_artifact, dict):
                    self.fail("AUDIT-01", "adversarial audit artifact must contain a JSON object")
                    audit_artifact = {}
                identity = (
                    audit_artifact.get("run_id"), audit_artifact.get("intent_id"),
                    audit_artifact.get("intent_version"), audit_artifact.get("pack_id"),
                )
                expected_identity = (
                    self.artifacts["intent"]["run_id"], self.artifacts["intent"]["intent_id"],
                    self.artifacts["intent"]["intent_version"], self.pack_contract["pack_id"],
                )
                if identity != expected_identity or audit_artifact.get("auditor_id") != auditor:
                    self.fail("AUDIT-01", "adversarial audit artifact is not bound to run/intent/pack/auditor")
                if _string_set(audit_artifact.get("candidate_ids")) != set(self.artifacts["shortlist"]["candidate_ids"]):
                    self.fail("AUDIT-01", "adversarial audit artifact does not cover the shortlist 30")
                if audit_artifact.get("overall_outcome") != "pass":
                    self.fail("AUDIT-01", "adversarial audit artifact overall_outcome must be pass")
                check_rows = audit_artifact.get("checks")
                if not isinstance(check_rows, list):
                    self.fail("AUDIT-01", "adversarial audit artifact checks must be a list")
                else:
                    check_index = {
                        row.get("check"): row for row in check_rows
                        if isinstance(row, dict) and isinstance(row.get("check"), str)
                    }
                    if len(check_index) != len(check_rows) or set(check_index) != set(audit["checks"]):
                        self.fail("AUDIT-01", "adversarial audit artifact checks must exactly and uniquely match the report")
                    for check in audit["checks"]:
                        row = check_index.get(check)
                        if not isinstance(row, dict):
                            continue
                        if row.get("outcome") != "pass":
                            self.fail("AUDIT-01", f"adversarial audit check {check} did not pass")
                        if not isinstance(row.get("rationale"), str) or not row["rationale"].strip():
                            self.fail("AUDIT-01", f"adversarial audit check {check} lacks rationale")
                        evidence_refs = row.get("evidence_refs")
                        if _string_set(evidence_refs) is None:
                            self.fail("AUDIT-01", f"adversarial audit check {check} evidence_refs must be a string list")
                            evidence_refs = []
                        evidence_paths = {
                            path for ref in evidence_refs
                            if (path := self._resolve_evidence_ref(ref, "AUDIT-01", f"audit check {check} evidence")) is not None
                        }
                        if receipt_evidence_path not in evidence_paths:
                            self.fail("AUDIT-01", f"adversarial audit check {check} is not bound to receipts")

    def _validate_feedback(self, intent_version: str) -> None:
        events = self.artifacts["feedback"]
        if not events:
            if intent_version != "v1":
                self.fail("FEEDBACK-01", "an advanced intent version requires a feedback event chain")
            return

        candidates = self.artifacts["candidates"]
        registry = self.artifacts["approaches"]
        candidate_ids = {item["candidate_id"] for item in candidates}
        pack_id = self.pack_contract["pack_id"]
        pack_approaches = [item for item in registry["approaches"] if item["pack_id"] == pack_id]
        approach_ids = {item["approach_id"] for item in pack_approaches}
        query_ids = {
            query["query_id"]
            for approach in pack_approaches
            for query in approach["queries"]
        }
        event_ids = [event["feedback_id"] for event in events]
        if len(event_ids) != len(set(event_ids)):
            self.fail("FEEDBACK-01", "feedback_id values must be unique")
        if events[0]["intent_version_before"] != "v1":
            self.fail("FEEDBACK-01", "feedback version history must begin at v1")
        try:
            current_version_number = int(intent_version.removeprefix("v"))
        except (AttributeError, ValueError):
            current_version_number = 0
        if current_version_number != len(events) + 1:
            self.fail("FEEDBACK-01", "intent version must equal v1 plus exactly one increment per feedback event")

        class_layers = {
            "intent_correction": "intent",
            "route_correction": "route",
            "query_correction": "query",
            "source_correction": "source",
            "access_correction": "access",
            "selection_correction": "scoring",
            "diversity_correction": "diversity",
            "presentation_correction": "presentation",
            "rights_correction": "rights",
        }
        agent_roles = {
            item["agent_id"]: {item["role"], *item.get("additional_roles", [])}
            for item in registry["agents"]
        }

        previous_after: str | None = None
        previous_completed_at: datetime | None = None
        invalidated_paths = {
            "intent_brief": ("00_intent/",),
            "approach_registry": ("01_orchestration/",),
            "candidate": ("02_candidates/",),
            "verification_receipt": ("03_verification/verification_receipts",),
            "browser_capture_record": ("03_verification/browser_capture_records",),
            "relevance_review": ("04_selection/review/relevance",),
            "diversity_review": ("04_selection/review/diversity",),
            "resolution_review": ("04_selection/review/resolution",),
            "shortlist_30": ("04_selection/shortlist_30",),
            "selected_20": ("04_selection/selected_20",),
            "rejected_10": ("04_selection/rejected_10",),
            "reference_board": ("06_output/reference_board",),
            "adversarial_audit": ("07_audit/adversarial_audit_results",),
            "verification_report": ("06_output/verification_report",),
        }
        phase_order = {
            phase: index
            for index, phase in enumerate(
                ("intent_freeze", "routing", "orchestration", "discovery", "verification", "selection", "output")
            )
        }
        earliest_repair_phase = {
            "intent": "intent_freeze",
            "route": "routing",
            "query": "orchestration",
            "source": "discovery",
            "access": "verification",
            "scoring": "selection",
            "diversity": "selection",
            "presentation": "output",
            "rights": "intent_freeze",
        }

        current_refs: dict[str, Path] = {
            "intent": self.artifact_files["intent"].resolve(),
            "approaches": self.artifact_files["approaches"].resolve(),
            "candidates": self.artifact_files["candidates"].resolve(),
            "captures": self.artifact_files["captures"].resolve(),
            "receipts": self.artifact_files["receipts"].resolve(),
            "shortlist": self.artifact_files["shortlist"].resolve(),
            "selected": self.artifact_files["selected"].resolve(),
            "rejected": self.artifact_files["rejected"].resolve(),
            "board": self.artifact_files["board"].resolve(),
        }
        selected_trace = self.artifacts["selected"]["curation_trace"]
        for key, field in (
            ("relevance_review", "relevance_review_ref"),
            ("diversity_review", "diversity_review_ref"),
            ("resolution_review", "resolution_ref"),
        ):
            resolved = self._resolve_evidence_ref(
                selected_trace[field], "FEEDBACK-01", f"feedback closure {key}"
            )
            if resolved is not None:
                current_refs[key] = resolved.resolve()
        audit_path = self._resolve_evidence_ref(
            "07_audit/adversarial_audit_results.json", "FEEDBACK-01", "feedback closure audit"
        )
        if audit_path is not None:
            current_refs["audit"] = audit_path.resolve()

        full_closure = set(current_refs.values())
        minimum_closure_keys = {
            "intent": set(current_refs),
            "route": set(current_refs),
            "query": set(current_refs),
            "source": set(current_refs),
            "access": {
                "intent", "captures", "receipts", "shortlist", "selected", "rejected",
                "relevance_review", "diversity_review", "resolution_review", "board", "audit",
            },
            "scoring": {
                "intent", "candidates", "shortlist", "selected", "rejected",
                "relevance_review", "diversity_review", "resolution_review", "board", "audit",
            },
            "diversity": {
                "intent", "selected", "rejected", "diversity_review", "resolution_review", "board", "audit",
            },
            "presentation": {"intent", "board"},
            "rights": {
                "intent", "candidates", "captures", "receipts", "shortlist", "selected", "rejected",
                "relevance_review", "diversity_review", "resolution_review", "board", "audit",
            },
        }
        artifact_type_by_key = {
            "intent": "intent_brief",
            "approaches": "approach_registry",
            "candidates": "candidate",
            "captures": "browser_capture_record",
            "receipts": "verification_receipt",
            "shortlist": "shortlist_30",
            "selected": "selected_20",
            "rejected": "rejected_10",
            "relevance_review": "relevance_review",
            "diversity_review": "diversity_review",
            "resolution_review": "resolution_review",
            "board": "reference_board",
            "audit": "adversarial_audit",
        }
        current_path_by_type = {
            artifact_type_by_key[key]: path
            for key, path in current_refs.items()
            if key in artifact_type_by_key
        }

        for event_index, event in enumerate(events):
            before, after = event["intent_version_before"], event["intent_version_after"]
            if event.get("run_id") != self.artifacts["intent"]["run_id"] or event.get("intent_id") != self.artifacts["intent"]["intent_id"]:
                self.fail("FEEDBACK-01", "feedback event does not bind the root run/intent")
            if event.get("pack_id") != pack_id:
                self.fail("FEEDBACK-01", "feedback event does not bind the current pack")
            layer = event["error_layer"]
            if class_layers.get(event["feedback_class"]) != layer:
                self.fail("FEEDBACK-01", "feedback_class and earliest error_layer disagree")
            delta_keys = [
                (delta["target_artifact_type"], delta["path"])
                for delta in event["constraint_delta"]
            ]
            if len(delta_keys) != len(set(delta_keys)):
                self.fail("FEEDBACK-01", "one feedback event cannot mutate the same target/path more than once")
            delta_targets = {delta["target_artifact_type"] for delta in event["constraint_delta"]}
            if layer in {"intent", "route", "rights"} and "intent_brief" not in delta_targets:
                self.fail("FEEDBACK-01", f"{layer} feedback must change the versioned intent model")
            if layer in {"query", "source"} and "approach_registry" not in delta_targets:
                self.fail("FEEDBACK-01", f"{layer} feedback must change the versioned approach model")
            try:
                before_number = int(before.removeprefix("v"))
                after_number = int(after.removeprefix("v"))
            except (AttributeError, ValueError):
                self.fail("FEEDBACK-01", "feedback intent versions must use monotonic vN identifiers")
                before_number = after_number = 0
            if after_number != before_number + 1:
                self.fail("FEEDBACK-01", "feedback event must advance intent_version by exactly one")
            if previous_after is not None and before != previous_after:
                self.fail("FEEDBACK-01", "feedback version chain is discontinuous")
            previous_after = after
            if not event["constraint_delta"]:
                self.fail("FEEDBACK-01", "feedback event must contain a concrete constraint_delta")
            if not event["invalidated_artifact_refs"]:
                self.fail("FEEDBACK-01", "feedback event must identify invalidated downstream artifacts")

            invalid_candidate_ids = set(event["invalidated_candidate_ids"])
            invalid_approach_ids = set(event["invalidated_approach_ids"])
            invalid_query_ids = set(event["invalidated_query_ids"])
            if unknown := invalid_candidate_ids - candidate_ids:
                self.fail("FEEDBACK-01", f"feedback references unknown candidate IDs: {sorted(unknown)}")
            if unknown := invalid_approach_ids - approach_ids:
                self.fail("FEEDBACK-01", f"feedback references unknown approach IDs: {sorted(unknown)}")
            if unknown := invalid_query_ids - query_ids:
                self.fail("FEEDBACK-01", f"feedback references unknown query IDs: {sorted(unknown)}")
            if layer in {"intent", "route"} and (
                invalid_candidate_ids != candidate_ids
                or invalid_approach_ids != approach_ids
                or invalid_query_ids != query_ids
            ):
                self.fail("FEEDBACK-01", f"{layer} feedback must invalidate the complete pack discovery lineage")
            if layer == "query" and not (invalid_approach_ids or invalid_query_ids):
                self.fail("FEEDBACK-01", "query feedback must invalidate a real approach_id or query_id")
            if layer == "query":
                expected_candidates = {
                    item["candidate_id"]
                    for item in candidates
                    if item["agent_trace"]["approach_id"] in invalid_approach_ids
                    or item["agent_trace"]["query_id"] in invalid_query_ids
                }
                if invalid_candidate_ids != expected_candidates:
                    self.fail("FEEDBACK-01", "query feedback candidate invalidation does not close its approach/query lineage")
            if layer == "source" and not (invalid_candidate_ids or invalid_approach_ids or invalid_query_ids):
                self.fail("FEEDBACK-01", "source feedback must invalidate a real candidate, approach, or query ID")
            if layer in {"access", "scoring", "diversity", "rights"} and not invalid_candidate_ids:
                self.fail("FEEDBACK-01", f"{layer} feedback must invalidate at least one real candidate_id")
            declared_phase = event["repair_start_phase"]
            earliest_phase = earliest_repair_phase[layer]
            if phase_order[declared_phase] > phase_order[earliest_phase]:
                self.fail(
                    "FEEDBACK-01",
                    f"{layer} feedback repair starts too late at {declared_phase}; it must start no later than {earliest_phase}",
                )

            supersedes = event.get("supersedes")
            if supersedes is not None and supersedes not in event_ids[:event_index]:
                self.fail("FEEDBACK-01", "feedback supersedes must reference an earlier feedback event")
            prior_same_paths = [
                prior["feedback_id"]
                for prior in events[:event_index]
                if {
                    (delta.get("target_artifact_type"), delta.get("path"))
                    for delta in prior.get("constraint_delta", []) if isinstance(delta, dict)
                }
                & {
                    (delta.get("target_artifact_type"), delta.get("path"))
                    for delta in event.get("constraint_delta", []) if isinstance(delta, dict)
                }
            ]
            if prior_same_paths and supersedes != prior_same_paths[-1]:
                self.fail("FEEDBACK-01", "a repeated constraint path must supersede its immediately prior feedback event")
            if not prior_same_paths and supersedes is not None:
                self.fail("FEEDBACK-01", "supersedes cannot point to an unrelated prior correction")

            invalidated_ref_types: dict[str, str] = {}
            for invalidated in event["invalidated_artifact_refs"]:
                ref = invalidated.get("ref") if isinstance(invalidated, dict) else None
                artifact_type = invalidated.get("artifact_type") if isinstance(invalidated, dict) else None
                expected_prefixes = invalidated_paths.get(artifact_type)
                if (
                    not isinstance(ref, str)
                    or expected_prefixes is None
                    or not any(ref.startswith(prefix) for prefix in expected_prefixes)
                ):
                    self.fail("FEEDBACK-01", "feedback invalidated artifact_type does not match its ref path")
                path = self._resolve_evidence_ref(ref, "FEEDBACK-01", "feedback invalidated artifact ref")
                if path is None:
                    continue
                if not path.is_file():
                    self.fail("FEEDBACK-01", f"feedback invalidated artifact ref does not exist: {ref}")
                    continue
                if ref in invalidated_ref_types and invalidated_ref_types[ref] != artifact_type:
                    self.fail("FEEDBACK-01", "one invalidated ref cannot claim multiple artifact types")
                invalidated_ref_types[ref] = artifact_type

            delta_documents: dict[str, tuple[str, str, dict[str, Any], dict[str, Any]]] = {}
            for delta in event["constraint_delta"]:
                target_type = delta["target_artifact_type"]
                before_ref = delta["before_ref"]
                after_ref = delta["after_ref"]
                if invalidated_ref_types.get(before_ref) != target_type:
                    self.fail("FEEDBACK-01", "delta before_ref must be declared as an invalidated artifact of the same type")
                expected_prefixes = invalidated_paths[target_type]
                if not any(before_ref.startswith(prefix) for prefix in expected_prefixes) or not any(
                    after_ref.startswith(prefix) for prefix in expected_prefixes
                ):
                    self.fail("FEEDBACK-01", "delta before/after refs do not match target_artifact_type")
                    continue
                before_path = self._resolve_evidence_ref(before_ref, "FEEDBACK-01", "feedback delta before_ref")
                after_path = self._resolve_evidence_ref(after_ref, "FEEDBACK-01", "feedback delta after_ref")
                if before_path is None or after_path is None or not before_path.is_file() or not after_path.is_file():
                    self.fail("FEEDBACK-01", "feedback delta before/after evidence is missing")
                    continue
                try:
                    before_document = read_json(before_path)
                    after_document = read_json(after_path)
                except ContractError as exc:
                    self.fail("FEEDBACK-01", f"cannot parse feedback delta evidence: {exc}")
                    continue
                existing_documents = delta_documents.get(target_type)
                if existing_documents is not None and existing_documents[:2] != (before_ref, after_ref):
                    self.fail("FEEDBACK-01", "all deltas for one target must share one before/after model pair")
                else:
                    delta_documents[target_type] = (
                        before_ref, after_ref, before_document, after_document
                    )
                expected_identity_before = (
                    self.artifacts["intent"]["run_id"], self.artifacts["intent"]["intent_id"], before
                )
                expected_identity_after = (
                    self.artifacts["intent"]["run_id"], self.artifacts["intent"]["intent_id"], after
                )
                if (
                    before_document.get("run_id"), before_document.get("intent_id"), before_document.get("intent_version")
                ) != expected_identity_before:
                    self.fail("FEEDBACK-01", "delta before_ref does not bind run/intent/version_before")
                if (
                    after_document.get("run_id"), after_document.get("intent_id"), after_document.get("intent_version")
                ) != expected_identity_after:
                    self.fail("FEEDBACK-01", "delta after_ref does not bind run/intent/version_after")
                if event_index == len(events) - 1:
                    expected_current = (
                        self.artifact_files["intent"] if target_type == "intent_brief" else self.artifact_files["approaches"]
                    ).resolve()
                    if after_path.resolve() != expected_current:
                        self.fail("FEEDBACK-01", "final feedback delta after_ref must be the current model artifact")
                before_value = _json_pointer_value(before_document, delta["path"])
                after_value = _json_pointer_value(after_document, delta["path"])
                before_exists = before_value is not _MISSING
                after_exists = after_value is not _MISSING
                if before_exists != delta["before_exists"] or after_exists != delta["after_exists"]:
                    self.fail("FEEDBACK-01", f"constraint delta existence flags are false at {delta['path']}")
                if before_exists and before_value != delta["before"]:
                    self.fail("FEEDBACK-01", f"constraint delta before value does not match at {delta['path']}")
                if after_exists and after_value != delta["after"]:
                    self.fail("FEEDBACK-01", f"constraint delta after value does not match at {delta['path']}")
                expected_existence = {
                    "add": (False, True),
                    "remove": (True, False),
                    "replace": (True, True),
                }[delta["operation"]]
                if (delta["before_exists"], delta["after_exists"]) != expected_existence:
                    self.fail("FEEDBACK-01", f"constraint delta operation/existence semantics disagree at {delta['path']}")

            declared_paths_by_target: dict[str, set[str]] = defaultdict(set)
            for delta in event["constraint_delta"]:
                declared_paths_by_target[delta["target_artifact_type"]].add(delta["path"])
            for target_type, (_, _, before_document, after_document) in delta_documents.items():
                allowed_roots = declared_paths_by_target[target_type] | {"/intent_version"}
                if target_type == "approach_registry":
                    allowed_roots.add("/registration/plan_sha256")
                undeclared = sorted(
                    changed_path
                    for changed_path in _json_diff_paths(before_document, after_document)
                    if not any(
                        changed_path == allowed
                        or changed_path.startswith(allowed + "/")
                        for allowed in allowed_roots
                    )
                )
                if undeclared:
                    self.fail(
                        "FEEDBACK-01",
                        f"before/after model contains undeclared changes for {target_type}: {undeclared}",
                    )
            completion = event["completion_evidence"]
            if completion["status"] != "applied" or not completion["artifact_bindings"]:
                self.fail("FEEDBACK-01", "feedback repair lacks applied completion evidence")
            resolved_completion: dict[str, Path] = {}
            for binding in completion["artifact_bindings"]:
                artifact_type = binding["artifact_type"]
                ref = binding["ref"]
                if artifact_type in resolved_completion:
                    self.fail("FEEDBACK-01", f"duplicate feedback completion artifact_type: {artifact_type}")
                path = self._resolve_evidence_ref(ref, "FEEDBACK-01", "feedback completion ref")
                if path is None:
                    continue
                if not path.is_file():
                    self.fail("FEEDBACK-01", f"feedback completion ref does not exist: {ref}")
                    continue
                expected_prefixes = invalidated_paths.get(artifact_type)
                if expected_prefixes is None or not any(ref.startswith(prefix) for prefix in expected_prefixes):
                    self.fail("FEEDBACK-01", "feedback completion artifact_type does not match its ref path")
                if binding["sha256"] != _sha256(path):
                    self.fail("FEEDBACK-01", f"feedback completion hash mismatch: {ref}")
                if path.resolve() in resolved_completion.values():
                    self.fail("FEEDBACK-01", f"duplicate feedback completion path: {ref}")
                resolved_completion[artifact_type] = path.resolve()
            required_keys = minimum_closure_keys[layer]
            required_types = {artifact_type_by_key[key] for key in required_keys if key in artifact_type_by_key}
            if set(resolved_completion) != required_types:
                self.fail(
                    "FEEDBACK-01",
                    f"feedback completion types do not exactly close {layer} repair: "
                    f"missing={sorted(required_types - set(resolved_completion))} "
                    f"extra={sorted(set(resolved_completion) - required_types)}",
                )
            if event_index == len(events) - 1:
                for artifact_type in required_types:
                    if resolved_completion.get(artifact_type) != current_path_by_type[artifact_type]:
                        self.fail("FEEDBACK-01", "final feedback completion must bind the current repaired artifact chain")
            else:
                for artifact_type in required_types:
                    if resolved_completion.get(artifact_type) == current_path_by_type[artifact_type]:
                        self.fail("FEEDBACK-01", "superseded feedback completion must preserve versioned historical artifacts")

            try:
                event_time = parse_timestamp(event["timestamp"])
                applied_time = parse_timestamp(event["agent_trace"]["applied_at"])
                completed_time = parse_timestamp(completion["completed_at"])
                delivery_time = parse_timestamp(self.artifacts["report"]["delivery_reference_time"])
            except ContractError as exc:
                self.fail("FEEDBACK-01", str(exc))
            else:
                if not event_time <= applied_time <= completed_time <= delivery_time:
                    self.fail("FEEDBACK-01", "feedback event/applied/completed/delivery chronology is invalid")
                if previous_completed_at is not None and event_time < previous_completed_at:
                    self.fail("FEEDBACK-01", "a new correction arrived before the prior repair was completed")
                previous_completed_at = completed_time
            if "root_synthesizer" not in agent_roles.get(event["agent_trace"]["recorded_by"], set()):
                self.fail("FEEDBACK-01", "feedback recorder must be a registered root synthesizer")
            if "root_synthesizer" not in agent_roles.get(event["agent_trace"]["applied_by"], set()):
                self.fail("FEEDBACK-01", "feedback applier must be a registered root synthesizer")

            scope = event["scope"]
            signal_class = event["signal_class"]
            scope_evidence = event["scope_evidence"]
            supporting_ids = scope_evidence["supporting_feedback_ids"]
            if any(item not in event_ids[:event_index] for item in supporting_ids):
                self.fail("FEEDBACK-01", "scope promotion evidence must reference earlier feedback IDs")
            if signal_class == "inferred_session_signal" and scope != "session":
                self.fail("FEEDBACK-01", "an inferred session signal cannot be promoted")
            if scope == "session" and (
                scope_evidence["basis"] != "current_run_only"
                or supporting_ids
                or event["user_confirmed_persistence"]
                or signal_class not in {"explicit_hard_constraint", "explicit_soft_preference", "inferred_session_signal"}
            ):
                self.fail("FEEDBACK-01", "session feedback has contradictory promotion evidence")
            if scope == "project":
                promoted = (
                    scope_evidence["basis"] == "explicit_user_confirmation"
                    and event["user_confirmed_persistence"]
                ) or (
                    scope_evidence["basis"] == "repeated_corrections"
                    and len(supporting_ids) >= 2
                )
                if signal_class != "confirmed_project_rule" or not promoted:
                    self.fail("FEEDBACK-01", "project scope lacks confirmation or two prior supporting corrections")
            if scope == "global" and (
                signal_class != "confirmed_global_rule"
                or scope_evidence["basis"] != "explicit_user_confirmation"
                or not event["user_confirmed_persistence"]
            ):
                self.fail("FEEDBACK-01", "global scope requires an explicitly confirmed global rule")
            if event["external_persistence_state"] != "not_applied_by_skill":
                self.fail("FEEDBACK-01", "the skill ledger cannot claim external durable-memory mutation")
        if previous_after != intent_version:
            self.fail("FEEDBACK-01", "final feedback version must equal current intent version")

    def _validate_referenced_evidence_contract(self) -> None:
        """Require hash coverage for every variable evidence file the validator reads."""
        required: dict[Path, set[str]] = defaultdict(set)

        def add_ref(ref: Any, purpose: str, code: str, label: str) -> None:
            path = self._resolve_evidence_ref(ref, code, label)
            if path is not None:
                required[path.resolve()].add(purpose)

        for artifact_name in ("selected", "rejected"):
            trace = self.artifacts[artifact_name]["curation_trace"]
            add_ref(trace["relevance_review_ref"], "relevance_review", "AGENT-01", "relevance review")
            add_ref(trace["diversity_review_ref"], "diversity_review", "AGENT-01", "diversity review")
            add_ref(trace["resolution_ref"], "resolution_review", "AGENT-01", "curation resolution")

        add_ref(
            "07_audit/adversarial_audit_results.json",
            "adversarial_audit",
            "AUDIT-01",
            "adversarial audit artifact",
        )
        for event in self.artifacts["feedback"]:
            for invalidated in event["invalidated_artifact_refs"]:
                if invalidated["artifact_type"] == "intent_brief":
                    add_ref(
                        invalidated["ref"],
                        "feedback_intent_snapshot",
                        "FEEDBACK-01",
                        "feedback intent snapshot",
                    )
        waiver = self.artifacts["selected"].get("diversity_policy", {}).get("waiver")
        if isinstance(waiver, dict):
            for ref in waiver.get("evidence", []):
                add_ref(ref, "diversity_waiver_evidence", "DIVERSITY-01", "waiver evidence")
        for receipt in self.artifacts["receipts"]:
            review_ref = receipt.get("dedup_check", {}).get("manual_version_review_ref")
            if review_ref is not None:
                add_ref(review_ref, "dedup_version_review", "DEDUP-01", "authorized version review")

        declared_rows = self.artifacts["report"]["referenced_evidence_contract"]
        declared: dict[Path, tuple[dict[str, Any], set[str]]] = {}
        raw_paths: set[str] = set()
        for row in declared_rows:
            raw_path = row.get("path")
            path = self._resolve_report_path(raw_path, "ARTIFACT_INTEGRITY", "referenced evidence path")
            if path is None:
                continue
            resolved = path.resolve()
            if raw_path in raw_paths or resolved in declared:
                self.fail("ARTIFACT_INTEGRITY", f"duplicate referenced evidence path: {raw_path}")
                continue
            raw_paths.add(raw_path)
            purposes = set(row.get("purposes", []))
            declared[resolved] = (row, purposes)

        if set(declared) != set(required):
            missing = sorted(str(path.relative_to(self.run_root.resolve())) for path in set(required) - set(declared))
            extra = sorted(str(path.relative_to(self.run_root.resolve())) for path in set(declared) - set(required))
            self.fail(
                "ARTIFACT_INTEGRITY",
                f"referenced_evidence_contract does not exactly cover validator-read evidence; missing={missing}, extra={extra}",
            )
        for path, purposes in required.items():
            entry = declared.get(path)
            if entry is None:
                continue
            row, declared_purposes = entry
            expected_relative = str(path.relative_to(self.run_root.resolve()))
            if row.get("path") != expected_relative:
                self.fail(
                    "ARTIFACT_INTEGRITY",
                    f"referenced evidence path is not canonical run-root-relative form: {row.get('path')}",
                )
            if declared_purposes != purposes:
                self.fail(
                    "ARTIFACT_INTEGRITY",
                    f"referenced evidence purposes mismatch for {expected_relative}: expected {sorted(purposes)}",
                )
            if not path.is_file():
                self.fail("ARTIFACT_INTEGRITY", f"referenced evidence does not exist: {expected_relative}")
            elif row.get("sha256") != _sha256(path):
                self.fail("ARTIFACT_INTEGRITY", f"referenced evidence hash mismatch: {expected_relative}")

    def _validate_report_and_artifacts(
        self, shortlist_ids: list[str], receipt_index: dict[str, dict[str, Any]], checked_times: list[datetime]
    ) -> None:
        report = self.artifacts["report"]
        if report["final_status"] != "pass":
            self.fail("REPORT-01", "completed run report final_status must be pass")
        if report["counts"] != {"qualified": 30, "selected": 20, "rejected": 10}:
            self.fail("POOL-01", "report counts do not equal 30/20/10")
        if not all(report["gates"].values()):
            self.fail("REPORT-01", "every final gate must be true")
        reverify = report["final_reverification"]
        if len(reverify) != 30 or {item["candidate_id"] for item in reverify} != set(shortlist_ids):
            self.fail("FRESHNESS-01", "final_reverification must cover exactly the shortlist 30")
        for item in reverify:
            receipt = receipt_index.get(item["candidate_id"])
            if not receipt or item["receipt_id"] != receipt["receipt_id"] or item["checked_at"] != receipt["checked_at"]:
                self.fail("FRESHNESS-01", "final_reverification entry is not bound to latest receipt", candidate_id=item["candidate_id"])
            elif (
                item["access_status"] != receipt["access_state"]["state"]
                or item["media_status"] != receipt["media_check"]["status"]
                or item["provenance_status"] != receipt["provenance_check"]["status"]
                or item["freshness_status"] != receipt["freshness"]["status"]
            ):
                self.fail("REPORT-01", "final_reverification summary differs from receipt", candidate_id=item["candidate_id"])
        summary = report["freshness_summary"]
        if checked_times:
            oldest = min(checked_times)
            newest = max(checked_times)
            if parse_timestamp(summary["oldest_checked_at"]) != oldest or parse_timestamp(summary["newest_checked_at"]) != newest:
                self.fail("FRESHNESS-01", "freshness summary timestamps do not match receipts")
        if summary["fresh_count"] != 30 or summary["stale_count"] != 0:
            self.fail("FRESHNESS-01", "freshness summary must say 30 fresh / 0 stale")
        rights_summary = report["rights_summary"]
        shortlist_receipts = [receipt_index[cid] for cid in shortlist_ids if cid in receipt_index]
        computed_rights = {
            "assessed_count": len(shortlist_receipts),
            "session_bound_count": sum(item["access_state"]["state"] == "session_bound" for item in shortlist_receipts),
            "shareable_without_session_count": sum(item["access_state"]["shareable_without_session"] is True for item in shortlist_receipts),
            "commercial_reuse_unknown_or_restricted_count": sum(
                item["rights_scope"]["commercial_reuse"]["state"] != "allowed" for item in shortlist_receipts
            ),
            "downloaded_video_count": 0,
        }
        if rights_summary != computed_rights:
            self.fail("RIGHTS-01", f"rights_summary does not equal receipt evidence: {computed_rights}")

        expected_types = {
            "intent_brief": self.artifact_files["intent"],
            "approach_registry": self.artifact_files["approaches"],
            "candidate_ledger": self.artifact_files["candidates"],
            "verification_receipts": self.artifact_files["receipts"],
            "browser_capture_records": self.artifact_files["captures"],
            "shortlist_30": self.artifact_files["shortlist"],
            "selected_20": self.artifact_files["selected"],
            "rejected_10": self.artifact_files["rejected"],
            "feedback_ledger": self.artifact_files["feedback"],
            "reference_board": self.artifact_files["board"],
        }
        expected_schema_ids = {
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
        contracts = report["artifact_contract"]
        contract_types = [item["artifact_type"] for item in contracts]
        if len(contracts) != 10 or len(contract_types) != len(set(contract_types)) or set(contract_types) != set(expected_types):
            self.fail("ARTIFACT_INTEGRITY", "artifact_contract must bind exactly the ten durable artifacts")
        by_type = {item["artifact_type"]: item for item in contracts}
        for artifact_type, path in expected_types.items():
            entry = by_type.get(artifact_type)
            if not entry:
                continue
            if path.is_symlink():
                self.fail("ARTIFACT_INTEGRITY", f"core artifact must be a regular file, not a symlink: {artifact_type}")
                continue
            declared = (self.run_root / entry["path"]).resolve()
            try:
                expected_relative = path.resolve().relative_to(self.run_root.resolve()).as_posix()
            except ValueError:
                self.fail("ARTIFACT_INTEGRITY", f"core artifact escapes the run root: {artifact_type}")
                continue
            if (
                entry["path"] != expected_relative
                or declared != path.resolve()
                or entry["schema_id"] != expected_schema_ids[artifact_type]
                or entry["sha256"] != _sha256(path)
            ):
                self.fail("ARTIFACT_INTEGRITY", f"artifact hash/path mismatch for {artifact_type}")
        self._validate_referenced_evidence_contract()
        board_text = self.artifact_files["board"].read_text(encoding="utf-8")
        try:
            expected_board = build_gallery(self.pack_root)
        except ContractError as exc:
            self.fail("ARTIFACT_INTEGRITY", f"cannot deterministically rebuild reference board: {exc}")
        else:
            if board_text != expected_board:
                self.fail("ARTIFACT_INTEGRITY", "reference board is not the deterministic rendering of validated artifacts")

    def validate(self) -> dict[str, Any]:
        if not self._load():
            return self.result()
        self._schema_check()
        if any(item.code in {"SCHEMA-01", "SCHEMA_MISSING", "SCHEMA_UNSUPPORTED"} for item in self.findings):
            return self.result()
        run_mode, capture_index = self._validate_mode_and_registration()
        self._validate_temporal_contract()
        intent_version, strategy, modality = self._validate_route()
        shortlist_ids, selected_ids, rejected_ids = self._validate_pool(intent_version, modality)
        candidates = self._candidate_index()
        missing = sorted(set(shortlist_ids) - set(candidates))
        if missing:
            self.fail("POOL-01", f"shortlist references candidates absent from ledger: {missing}")
            return self.result()
        self._validate_dominance(candidates, selected_ids, rejected_ids)
        receipt_index = self._receipt_index()
        self._validate_ledger_closure(candidates, receipt_index, shortlist_ids, capture_index)
        try:
            reference_time = parse_timestamp(self.artifacts["report"]["delivery_reference_time"])
        except ContractError as exc:
            self.fail("FRESHNESS-01", str(exc))
            reference_time = datetime.now(timezone.utc)
        if reference_time > self.validation_now + MAX_FUTURE_SKEW:
            self.fail("FRESHNESS-01", "delivery_reference_time is later than the trusted validation clock")
        window = self.artifacts["intent"]["freshness_need"]["final_receipt_window_minutes"]
        if run_mode == "production_live" and self.validation_now - reference_time > timedelta(minutes=window):
            self.fail("FRESHNESS-01", "production_live validation is outside its delivery window")
        if (
            self.artifacts["report"]["freshness_summary"]["receipt_window_minutes"] != window
            or self.artifacts["report"]["freshness_window_minutes"] != window
        ):
            self.fail("FRESHNESS-01", "report and intent freshness windows differ")
        finder_ids: set[str] = set()
        verifier_ids: set[str] = set()
        checked_times: list[datetime] = []
        shortlist_candidates: list[dict[str, Any]] = []
        for cid in shortlist_ids:
            candidate = candidates[cid]
            shortlist_candidates.append(candidate)
            receipt = receipt_index.get(cid)
            if receipt is None:
                self.fail("VERIFY-01", "candidate lacks a verification receipt", candidate_id=cid)
                continue
            expected_status = "selected" if cid in selected_ids else "rejected"
            finder, verifier = self._validate_candidate_and_receipt(candidate, receipt, expected_status, reference_time, window)
            self._validate_capture_bindings(candidate, receipt, capture_index)
            finder_ids.add(finder)
            verifier_ids.add(verifier)
            try:
                checked_times.append(parse_timestamp(receipt["checked_at"]))
            except ContractError:
                pass
            shortlist_item = next(item for item in self.artifacts["shortlist"]["items"] if item["candidate_id"] == cid)
            if shortlist_item["verification_receipt_id"] != receipt["receipt_id"]:
                self.fail("VERIFY-01", "shortlist item receipt binding drift", candidate_id=cid)
            expected_shortlist_summary = {
                "qualification_status": receipt["outcome"],
                "freshness_status": receipt["freshness"]["status"],
                "access_status": receipt["access_state"]["state"],
                "media_status": receipt["media_check"]["status"],
                "provenance_status": receipt["provenance_check"]["status"],
                "dedup_status": receipt["dedup_check"]["status"],
                "territory_id": candidate["diversity"]["territory_id"],
            }
            if any(shortlist_item.get(key) != value for key, value in expected_shortlist_summary.items()):
                self.fail("VERIFY-01", "shortlist summary differs from bound candidate/receipt", candidate_id=cid)
            selection_items = self.artifacts["selected"]["items"] if cid in selected_ids else self.artifacts["rejected"]["items"]
            selection_item = next((item for item in selection_items if item["candidate_id"] == cid), None)
            if selection_item is None:
                self.fail("POOL-01", "partition id is absent from its selection artifact", candidate_id=cid)
            elif selection_item["verification_receipt_id"] != receipt["receipt_id"]:
                self.fail("VERIFY-01", "selection item receipt binding drift", candidate_id=cid)
        # Independence is run-ledger global, not limited to the final 30. A
        # curator/auditor must not hide discovery or verification work in a
        # quarantined candidate or failed receipt.
        finder_ids = {
            item["agent_trace"]["finder_agent_id"]
            for item in self.artifacts["candidates"]
        }
        verifier_ids = {
            item["verifier"]["verifier_agent_id"]
            for item in self.artifacts["receipts"]
        }
        selected_candidates = [candidates[cid] for cid in selected_ids]
        self._validate_route_quota(strategy, shortlist_candidates, selected_candidates)
        self._validate_dedup(shortlist_candidates, receipt_index)
        self._validate_diversity(selected_candidates)
        self._validate_agents(finder_ids, verifier_ids)
        self._validate_feedback(intent_version)
        self._validate_report_and_artifacts(shortlist_ids, receipt_index, checked_times)
        self.metrics.update(
            {
                "pack_id": self.pack_contract.get("pack_id"),
                "pack_modality": modality,
                "run_mode": run_mode,
                "production_contract_eligible": run_mode == "production_live",
                "production_deliverable": False,
                "qualified": len(shortlist_ids),
                "selected": len(selected_ids),
                "rejected": len(rejected_ids),
                "finder_count": len(finder_ids),
                "verifier_count": len(verifier_ids),
            }
        )
        return self.result()

    def result(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_contract.get("pack_id"),
            "status": "PASS" if not self.findings else "FAIL",
            "finding_count": len(self.findings),
            "findings": [item.as_dict() for item in self.findings],
            "metrics": self.metrics,
        }


def validate_run(
    run_dir: str | Path,
    *,
    validation_now: datetime | None = None,
    require_production_deliverable: bool = False,
    require_production_contract_eligible: bool = False,
) -> dict[str, Any]:
    root = Path(run_dir)
    trusted_now = validation_now or datetime.now(timezone.utc)
    if trusted_now.tzinfo is None:
        raise ValueError("validation_now must include a timezone")
    trusted_now = trusted_now.astimezone(timezone.utc)
    intent_path = root / SHARED_PATHS["intent"]
    try:
        intent = read_json(intent_path)
        strategy = intent["routing"]["strategy"]
        pack_contracts = intent["routing"]["pack_contracts"]
    except (ContractError, KeyError, TypeError) as exc:
        return {
            "contract": "advertising-reference-research-run-v1",
            "run_dir": str(root.resolve()),
            "status": "FAIL",
            "finding_count": 1,
            "findings": [{"code": "INTENT-01", "message": f"cannot resolve routing contract: {exc}"}],
            "packs": [],
        }
    if not isinstance(pack_contracts, list) or not pack_contracts or not all(isinstance(item, dict) for item in pack_contracts):
        return {
            "contract": "advertising-reference-research-run-v1",
            "run_dir": str(root.resolve()),
            "status": "FAIL",
            "finding_count": 1,
            "findings": [{"code": "ROUTE-02", "message": "routing.pack_contracts must be a non-empty array of pack contracts"}],
            "packs": [],
        }
    invalid_pack_contracts = [
        index for index, item in enumerate(pack_contracts)
        if not isinstance(item.get("pack_id"), str)
        or not item["pack_id"]
        or item.get("modality") not in ("image", "video", "mixed")
        or item.get("qualified_target") != 30
        or item.get("selected_target") != 20
    ]
    if invalid_pack_contracts:
        return {
            "contract": "advertising-reference-research-run-v1",
            "run_dir": str(root.resolve()),
            "status": "FAIL",
            "finding_count": 1,
            "findings": [{
                "code": "ROUTE-02",
                "message": f"invalid pack contract fields at indexes {invalid_pack_contracts}",
            }],
            "packs": [],
        }
    pack_ids = [item["pack_id"] for item in pack_contracts]
    if len(pack_ids) != len(set(pack_ids)):
        return {
            "contract": "advertising-reference-research-run-v1",
            "run_dir": str(root.resolve()),
            "status": "FAIL",
            "finding_count": 1,
            "findings": [{"code": "ROUTE-02", "message": "pack contract IDs must be unique"}],
            "packs": [],
        }
    schemas_root = Path(__file__).resolve().parent.parent / "references"
    if strategy == "parallel_packs":
        expected = set(pack_ids)
        if len(pack_contracts) != 2 or {item["modality"] for item in pack_contracts} != {"image", "video"}:
            return {
                "contract": "advertising-reference-research-run-v1",
                "run_dir": str(root.resolve()),
                "status": "FAIL",
                "finding_count": 1,
                "findings": [{"code": "ROUTE-02", "message": "parallel_packs requires one image and one video 30/20 contract"}],
                "packs": [],
            }
        actual = {path.name for path in (root / "packs").iterdir() if path.is_dir()} if (root / "packs").is_dir() else set()
        if actual != expected:
            return {
                "contract": "advertising-reference-research-run-v1",
                "run_dir": str(root.resolve()),
                "status": "FAIL",
                "finding_count": 1,
                "findings": [{"code": "ROUTE-02", "message": f"parallel pack directories {sorted(actual)} do not equal {sorted(expected)}"}],
                "packs": [],
            }
        pack_results = [
            PackValidator(root, root / "packs" / item["pack_id"], item, schemas_root, trusted_now).validate()
            for item in pack_contracts
        ]
    else:
        if len(pack_contracts) != 1:
            pack_results = [{"status": "FAIL", "findings": [{"code": "ROUTE-02", "message": "single/unified run needs one pack contract"}], "finding_count": 1}]
        else:
            pack_results = [PackValidator(root, root, pack_contracts[0], schemas_root, trusted_now).validate()]
    findings = [finding for pack in pack_results for finding in pack.get("findings", [])]
    if strategy == "parallel_packs" and len(pack_contracts) == 2:
        global_chains: list[list[dict[str, Any]]] = []
        try:
            for contract in pack_contracts:
                rows = read_jsonl(root / "packs" / contract["pack_id"] / PACK_PATHS["feedback"])
                global_chains.append([row for row in rows if row.get("scope") == "global"])
        except ContractError as exc:
            findings.append({"code": "FEEDBACK-01", "message": f"cannot compare parallel global feedback: {exc}"})
        else:
            semantic_chains = [
                [_global_feedback_semantic_projection(event) for event in chain]
                for chain in global_chains
            ]
            if canonical_sha256(semantic_chains[0]) != canonical_sha256(semantic_chains[1]):
                findings.append({"code": "FEEDBACK-01", "message": "parallel packs have divergent global feedback chains"})
                for pack in pack_results:
                    pack["status"] = "FAIL"
                    pack["finding_count"] = int(pack.get("finding_count", 0)) + 1
    production_contract_eligible = (
        intent.get("run_mode") == "production_live"
        and bool(pack_results)
        and not findings
        and all(item.get("status") == "PASS" for item in pack_results)
    )
    if require_production_contract_eligible and not production_contract_eligible:
        findings.append(
            {
                "code": "MODE-01",
                "message": "production contract eligibility requires a passing production_live run; fixture/smoke PASS is insufficient",
            }
        )
    if require_production_deliverable:
        findings.append(
            {
                "code": "ATTEST-01",
                "message": "package-local unsigned evidence cannot prove production delivery; use --require-production-contract-eligible and obtain separate trusted external attestation before any delivery claim",
            }
        )
    return {
        "contract": "advertising-reference-research-run-v1",
        "run_dir": str(root.resolve()),
        "strategy": strategy,
        "run_mode": intent.get("run_mode"),
        "production_contract_eligible": production_contract_eligible,
        "production_deliverable": False,
        "status": "PASS" if pack_results and not findings and all(item.get("status") == "PASS" for item in pack_results) else "FAIL",
        "finding_count": len(findings),
        "findings": findings,
        "packs": pack_results,
        "validated_at": trusted_now.isoformat().replace("+00:00", "Z"),
        "validator_boundary": (
            "PASS validates strict JSON, schema, hash bindings, temporal and semantic consistency, and declared point-in-time browser captures. "
            "Capture records are not cryptographically attested: PASS can establish production contract eligibility but never production delivery, prove that the declared observation occurred, reopen third-party pages, or grant reuse rights."
        ),
    }


def _nested_relative_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            refs.update(_nested_relative_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.update(_nested_relative_refs(item))
    elif isinstance(value, str):
        raw = Path(value)
        if (
            "/" in value
            and not raw.is_absolute()
            and not value.startswith(("http://", "https://"))
            and raw.suffix.lower() in {".json", ".jsonl", ".html", ".txt", ".png", ".jpg", ".jpeg", ".webp"}
        ):
            refs.add(value)
    return refs


def _protected_validation_inputs(run_dir: str | Path) -> set[Path]:
    """Resolve every static or referenced run artifact the validator may read."""

    root = Path(run_dir).expanduser().resolve(strict=False)
    pack_roots = [root]
    packs_dir = root / "packs"
    if packs_dir.is_dir():
        pack_roots.extend(path for path in packs_dir.iterdir() if path.is_dir())
    protected = {
        *(root / relative for relative in SHARED_PATHS.values()),
        *(pack_root / relative for pack_root in pack_roots for relative in PACK_PATHS.values()),
    }
    schemas_root = Path(__file__).resolve().parent.parent / "references"
    protected.update(schemas_root / schema_name for schema_name in SCHEMAS.values())

    queue = [path for path in protected if path.is_file() and path.suffix.lower() in {".json", ".jsonl"}]
    visited: set[Path] = set()
    while queue:
        path = queue.pop()
        resolved_path = path.resolve(strict=False)
        if resolved_path in visited:
            continue
        visited.add(resolved_path)
        try:
            value = read_jsonl(path) if path.suffix.lower() == ".jsonl" else read_json(path)
        except ContractError:
            continue
        for ref in _nested_relative_refs(value):
            for base in [root, *pack_roots]:
                candidate = (base / ref).resolve(strict=False)
                try:
                    candidate.relative_to(root)
                except ValueError:
                    continue
                if candidate.is_file() and candidate not in protected:
                    protected.add(candidate)
                    if candidate.suffix.lower() in {".json", ".jsonl"}:
                        queue.append(candidate)
    return {path.resolve(strict=False) for path in protected}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output")
    parser.add_argument(
        "--require-production-deliverable",
        action="store_true",
        help="legacy fail-closed flag: unsigned package evidence can never prove production delivery",
    )
    parser.add_argument(
        "--require-production-contract-eligible",
        action="store_true",
        help="fail unless this is a passing preregistered production_live contract",
    )
    args = parser.parse_args(argv)
    try:
        if args.output and any(
            same_artifact(args.output, protected)
            for protected in _protected_validation_inputs(args.run_dir)
        ):
            raise ContractError("validator output must not overwrite a run contract or evidence artifact")
        result = validate_run(
            args.run_dir,
            require_production_deliverable=args.require_production_deliverable,
            require_production_contract_eligible=args.require_production_contract_eligible,
        )
        if args.output:
            write_json(args.output, result)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    except ContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
