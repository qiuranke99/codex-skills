#!/usr/bin/env python3
"""Import browser receipts and optionally create offline HTTP-shaped placeholders.

The legacy ``--http-precheck`` switch performs no network request. It validates
the URL shape and emits ``outcome=blocked`` so an operator can see which item
still needs browser verification. This avoids SSRF and DNS-rebinding exposure
while preserving the receipt contract. Only an independent browser or manual
visual receipt with the required media evidence may be ``qualified``.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from _contract_utils import (
    ContractError,
    get_path,
    parse_timestamp,
    read_json,
    read_records,
    same_artifact,
    write_jsonl,
)
from _json_schema_subset import validate as validate_schema
from _qualification_rules import media_evidence_errors
from _url_policy import assert_safe_public_http_url


QUALIFYING_SURFACES = {"in_app_browser", "chrome_authenticated", "manual_visual_review"}
RIGHTS_KEYS = {
    "discoverable",
    "viewable",
    "shareable_without_session",
    "downloadable",
    "internal_board_use",
    "commercial_reuse",
}


def _assert_public_http_url(url: str) -> None:
    """Backward-compatible wrapper around the package-wide URL authority."""

    assert_safe_public_http_url(url)


def _candidate_id(candidate: dict[str, Any]) -> str:
    value = candidate.get("candidate_id")
    if not isinstance(value, str) or not value:
        raise ContractError("candidate is missing candidate_id")
    return value


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _receipt_id(candidate_id: str, checked_at: str, surface: str) -> str:
    material = f"{candidate_id}|{checked_at}|{surface}".encode("utf-8")
    return "receipt_" + hashlib.sha256(material).hexdigest()[:16]


def receipt_has_browser_media_evidence(receipt: dict[str, Any], modality: str) -> bool:
    verifier = receipt.get("verifier")
    surface = verifier.get("verification_surface") if isinstance(verifier, dict) else None
    if surface not in QUALIFYING_SURFACES or receipt.get("outcome") != "qualified":
        return False
    return not media_evidence_errors(receipt, modality)


def normalize_browser_receipt(
    receipt: dict[str, Any], candidate: dict[str, Any], pack_id: str
) -> dict[str, Any]:
    cid = _candidate_id(candidate)
    schema = read_json(Path(__file__).resolve().parent.parent / "references/verification_receipt.schema.json")
    schema_errors = validate_schema(receipt, schema)
    if schema_errors:
        raise ContractError(f"receipt for {cid} violates the receipt schema: {schema_errors[:5]}")
    if receipt.get("candidate_id") != cid:
        raise ContractError(f"browser receipt candidate_id mismatch for {cid}")
    expected = {
        "run_id": candidate.get("run_id"),
        "intent_id": candidate.get("intent_id"),
        "intent_version": candidate.get("intent_version"),
        "pack_id": pack_id,
        "source_id": get_path(candidate, "source.source_id", default=None),
        "modality": candidate.get("modality"),
    }
    mismatches = [field for field, value in expected.items() if receipt.get(field) != value]
    if mismatches:
        raise ContractError(f"receipt for {cid} has foreign or stale bindings: {mismatches}")
    receipt_id = receipt.get("receipt_id")
    if not isinstance(receipt_id, str) or not receipt_id:
        raise ContractError(f"receipt for {cid} is missing receipt_id")
    verifier = receipt.get("verifier")
    surface = verifier.get("verification_surface") if isinstance(verifier, dict) else None
    finder_id = get_path(candidate, "agent_trace.finder_agent_id", default=None)
    if not isinstance(verifier, dict):
        raise ContractError(f"receipt for {cid} is missing verifier identity")
    if verifier.get("finder_agent_id") != finder_id:
        raise ContractError(f"receipt for {cid} does not bind the candidate finder")
    if verifier.get("independence_asserted") is not True:
        raise ContractError(f"receipt for {cid} does not assert verifier independence")
    verifier_id = verifier.get("verifier_agent_id")
    if not isinstance(verifier_id, str) or not verifier_id or verifier_id == finder_id:
        raise ContractError(f"receipt for {cid} has a missing or non-independent verifier")
    parse_timestamp(receipt.get("checked_at"), f"receipt[{cid}].checked_at")
    if receipt.get("outcome") == "qualified":
        if surface not in QUALIFYING_SURFACES:
            raise ContractError(f"qualified receipt for {cid} lacks browser/manual visual evidence")
        if not receipt_has_browser_media_evidence(receipt, str(candidate.get("modality", ""))):
            raise ContractError(f"qualified receipt for {cid} lacks modality-specific browser evidence")
    return dict(receipt)


def _rights(candidate: dict[str, Any]) -> dict[str, Any]:
    value = candidate.get("rights_scope")
    if isinstance(value, dict) and set(value) == RIGHTS_KEYS:
        return value
    return {
        key: {"state": "unknown", "basis": "HTTP transport precheck cannot determine usage rights."}
        for key in RIGHTS_KEYS
    }


def _blocked_receipt(
    candidate: dict[str, Any], verifier_id: str, *, access: dict[str, Any], evidence_locator: str,
    pack_id: str = "unassigned_pack"
) -> dict[str, Any]:
    checked = _now()
    checked_at = _iso(checked)
    cid = _candidate_id(candidate)
    modality = candidate.get("modality")
    finder = get_path(candidate, "agent_trace.finder_agent_id", default="unknown_finder")
    if verifier_id == finder:
        raise ContractError(f"transport verifier must differ from finder for {cid}")
    asset_locator = get_path(candidate, "object.asset_locator", default=None) or "unverified-asset-locator"
    if modality == "image":
        image_render = {
            "rendered": False,
            "asset_locator": str(asset_locator),
            "natural_width": 1,
            "natural_height": 1,
            "placeholder_detected": True,
        }
        video_playback = None
    else:
        image_render = None
        video_playback = {
            "player_present": False,
            "playback_started": False,
            "observed_progress_seconds": 0,
            "duration_seconds": None,
            "specific_work_matched": False,
        }
    source_url = get_path(candidate, "object.canonical_url", "source.discovered_url", default=evidence_locator)
    return {
        "schema_version": "1.1.0",
        "receipt_id": _receipt_id(cid, checked_at, "http"),
        "run_id": str(candidate.get("run_id", "unknown-run")),
        "intent_id": str(candidate.get("intent_id", "unknown-intent")),
        "intent_version": str(candidate.get("intent_version", "v1")),
        "pack_id": pack_id,
        "candidate_id": cid,
        "source_id": str(get_path(candidate, "source.source_id", default="unknown-source")),
        "modality": modality,
        "checked_at": checked_at,
        "freshness": {
            "window_minutes": 30,
            "expires_at": _iso(checked + timedelta(minutes=30)),
            "status": "fresh",
            "reverification_required": True,
        },
        "verifier": {
            "finder_agent_id": str(finder),
            "verifier_agent_id": verifier_id,
            "verification_surface": "http",
            "independence_asserted": True,
        },
        "access_state": access,
        "media_check": {
            "status": "failed",
            "kind": modality,
            "image_render": image_render,
            "video_playback": video_playback,
        },
        "object_match": {
            "status": "uncertain",
            "matched_title": False,
            "matched_stable_id": None,
            "rationale": "HTTP transport cannot identify the rendered creative object.",
        },
        "provenance_check": {
            "status": "failed",
            "accountable_url": source_url,
            "accountable_owner": None,
            "source_signal": "discovery_only",
            "matched_object": False,
        },
        "rights_scope": _rights(candidate),
        "dedup_check": {
            "status": "uncertain",
            "exact_url_checked": False,
            "stable_id_checked": False,
            "campaign_version_checked": False,
            "near_duplicate_group_id": get_path(candidate, "dedup.near_duplicate_group_id", default=None),
            "fingerprint_capture_ids": [],
            "comparison_set_sha256": None,
            "phash_distance_threshold": None,
            "manual_version_review_ref": None,
        },
        "evidence_level": "E0_LEAD",
        "evidence": [{"kind": "url", "locator": evidence_locator, "captured_at": checked_at}],
        "capture_bindings": [],
        "failure_codes": [
            "PAGE_NOT_RENDERED",
            "IMAGE_NOT_RENDERED" if modality == "image" else "VIDEO_NOT_PLAYABLE",
            "PROVENANCE_UNCONFIRMED",
        ],
        "outcome": "blocked",
    }


def http_precheck(
    candidate: dict[str, Any], verifier_id: str, timeout: float, pack_id: str = "unassigned_pack"
) -> dict[str, Any]:
    url = get_path(candidate, "object.canonical_url", "source.discovered_url", default="")
    access = {
        "mode": "public",
        "state": "blocked",
        "checked_url": url or "https://invalid.local/missing-url",
        "page_rendered": False,
        "canonical_url_resolved": False,
        "shareable_without_session": "unknown",
        "http_status": None,
        "challenge_detected": False,
    }
    if not isinstance(url, str) or not url:
        return _blocked_receipt(candidate, verifier_id, access=access, evidence_locator=access["checked_url"], pack_id=pack_id)
    _assert_public_http_url(url)
    _ = timeout  # retained for CLI compatibility; no network request is made
    return _blocked_receipt(candidate, verifier_id, access=access, evidence_locator=url, pack_id=pack_id)


def build_receipts(
    candidates: list[dict[str, Any]],
    imported_receipts: list[dict[str, Any]],
    run_http_precheck: bool,
    verifier_id: str,
    timeout: float,
    pack_id: str = "unassigned_pack",
) -> list[dict[str, Any]]:
    if not math.isfinite(timeout) or timeout <= 0:
        raise ContractError("timeout must be a finite positive number")
    candidate_id_list = [_candidate_id(candidate) for candidate in candidates]
    if len(candidate_id_list) != len(set(candidate_id_list)):
        raise ContractError("candidate_id values must be unique before receipt import")
    wrong_pack = [
        cid
        for cid, candidate in zip(candidate_id_list, candidates)
        if candidate.get("pack_id") != pack_id
    ]
    if wrong_pack:
        raise ContractError(f"candidates do not bind requested pack_id {pack_id}: {wrong_pack}")
    by_candidate: dict[str, list[dict[str, Any]]] = {}
    for receipt in imported_receipts:
        cid = receipt.get("candidate_id")
        if not isinstance(cid, str) or not cid:
            raise ContractError("imported receipt is missing candidate_id")
        by_candidate.setdefault(cid, []).append(receipt)
    candidate_ids = set(candidate_id_list)
    unknown = sorted(set(by_candidate) - candidate_ids)
    if unknown:
        raise ContractError(f"receipts reference unknown candidates: {unknown}")

    result: list[dict[str, Any]] = []
    for candidate in candidates:
        cid = _candidate_id(candidate)
        available = by_candidate.get(cid, [])
        if available:
            normalized = [normalize_browser_receipt(item, candidate, pack_id) for item in available]
            normalized.sort(key=lambda item: parse_timestamp(item["checked_at"]))
            result.extend(normalized)
        else:
            # A missing browser receipt remains blocked. --http-precheck validates only
            # URL shape and never opens the target or upgrades the outcome.
            result.append(http_precheck(candidate, verifier_id, timeout, pack_id=pack_id) if run_http_precheck else _blocked_receipt(
                candidate,
                verifier_id,
                access={
                    "mode": "public",
                    "state": "blocked",
                    "checked_url": get_path(candidate, "object.canonical_url", default="https://invalid.local/missing"),
                    "page_rendered": False,
                    "canonical_url_resolved": False,
                    "shareable_without_session": "unknown",
                    "http_status": None,
                    "challenge_detected": False,
                },
                evidence_locator=get_path(candidate, "object.canonical_url", default="https://invalid.local/missing"),
                pack_id=pack_id,
            ))
    receipt_ids: set[str] = set()
    candidate_times: set[tuple[str, datetime]] = set()
    for receipt in result:
        receipt_id = receipt["receipt_id"]
        checked_at = parse_timestamp(receipt["checked_at"])
        time_key = (receipt["candidate_id"], checked_at)
        if receipt_id in receipt_ids:
            raise ContractError(f"duplicate receipt_id is forbidden: {receipt_id}")
        if time_key in candidate_times:
            raise ContractError(
                f"ambiguous receipt history for {receipt['candidate_id']} at {receipt['checked_at']}"
            )
        receipt_ids.add(receipt_id)
        candidate_times.add(time_key)
    return result


def _latest_by_candidate(receipts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        candidate_id = receipt["candidate_id"]
        if candidate_id not in latest or parse_timestamp(receipt["checked_at"]) > parse_timestamp(
            latest[candidate_id]["checked_at"]
        ):
            latest[candidate_id] = receipt
    return latest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--offline-receipts")
    parser.add_argument(
        "--http-precheck", action="store_true",
        help="legacy offline placeholder: validate URL shape, make no network request, remain blocked",
    )
    parser.add_argument("--verifier-id", default="transport_precheck")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--output", required=True)
    parser.add_argument("--pack-id", required=True, help="pack contract id bound into generated receipts")
    parser.add_argument("--require-qualified", action="store_true")
    args = parser.parse_args(argv)
    try:
        if same_artifact(args.candidates, args.output):
            raise ContractError("output must not overwrite the candidate ledger")
        if args.offline_receipts and same_artifact(args.candidates, args.offline_receipts):
            raise ContractError("candidate ledger cannot also be an offline receipt ledger")
        candidates = read_records(args.candidates)
        import_paths: list[str] = []
        output_path = Path(args.output)
        if output_path.exists():
            import_paths.append(args.output)
        if args.offline_receipts and not any(
            same_artifact(args.offline_receipts, item) for item in import_paths
        ):
            import_paths.append(args.offline_receipts)
        imported_by_id: dict[str, dict[str, Any]] = {}
        for import_path in import_paths:
            for receipt in read_records(import_path):
                receipt_id = receipt.get("receipt_id")
                if not isinstance(receipt_id, str) or not receipt_id:
                    raise ContractError(f"receipt imported from {import_path} is missing receipt_id")
                prior = imported_by_id.get(receipt_id)
                if prior is not None and prior != receipt:
                    raise ContractError(f"conflicting receipt_id across history sources: {receipt_id}")
                imported_by_id[receipt_id] = receipt
        imported = list(imported_by_id.values())
        receipts = build_receipts(candidates, imported, args.http_precheck, args.verifier_id, args.timeout, args.pack_id)
        write_jsonl(args.output, receipts)
    except ContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.require_qualified:
        candidates_by_id = {_candidate_id(item): item for item in candidates}
        latest = _latest_by_candidate(receipts)
        if any(
            not receipt_has_browser_media_evidence(receipt, candidates_by_id[receipt["candidate_id"]]["modality"])
            for receipt in latest.values()
        ):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
