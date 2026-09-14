#!/usr/bin/env python3
"""Read-only quantity checkpoint. A search batch is never a delivery quota.

This helper suggests the next work stage; it neither searches nor grants media
qualification. Counts before full validation are explicitly provisional.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from _contract_utils import ContractError, read_json, read_jsonl
from _qualification_rules import media_evidence_errors
from validate_research_run import PACK_PATHS, SHARED_PATHS, validate_run
from verify_candidates import QUALIFYING_SURFACES


def _load(path: Path, *, lines: bool = False) -> Any:
    if not path.is_file():
        return [] if lines else {}
    return read_jsonl(path) if lines else read_json(path)


def _ids(items: Any) -> set[str]:
    return {item["candidate_id"] for item in items if isinstance(item, dict)
            and isinstance(item.get("candidate_id"), str) and item["candidate_id"]}


def _distinct_media_ids(candidates: list[dict[str, Any]]) -> set[str]:
    """Collapse either identity alias, including bridges between earlier groups."""
    parents: dict[str, str] = {}
    aliases: dict[tuple[str, str, str], str] = {}

    def representative(cid: str) -> str:
        while parents[cid] != cid:
            parents[cid] = parents[parents[cid]]
            cid = parents[cid]
        return cid

    for candidate in candidates:
        cid, modality = candidate["candidate_id"], candidate["modality"]
        obj = candidate.get("object", {})
        keys = []
        if obj.get("stable_id"):
            keys.append((modality, "stable_id", obj["stable_id"]))
        if obj.get("canonical_url"):
            url = urlsplit(obj["canonical_url"])
            canonical = urlunsplit((url.scheme.lower(), url.netloc.lower(), url.path, url.query, ""))
            keys.append((modality, "canonical_url", canonical))
        if not keys:
            continue
        parents.setdefault(cid, cid)
        for key in keys:
            if key in aliases:
                parents[representative(cid)] = representative(aliases[key])
            aliases[key] = cid
    return {representative(cid) for cid in parents}


def checkpoint(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir).resolve()
    intent = _load(root / SHARED_PATHS["intent"])
    contracts = intent.get("routing", {}).get("pack_contracts", [])
    if not contracts:
        raise ContractError("freeze the intent and explicit 30/20 pack contracts first")
    registry = _load(root / SHARED_PATHS["approaches"])
    packs = []
    parallel = intent["routing"]["strategy"] == "parallel_packs"
    for contract in contracts:
        if contract.get("qualified_target") != 30 or contract.get("selected_target") != 20:
            raise ContractError("quantity checkpoint requires the maintained 30/20 contract")
        pack_id = contract["pack_id"]
        pack_root = (root / "packs" / pack_id).resolve() if parallel else root
        if not pack_root.is_relative_to(root):
            raise ContractError("pack path escapes run directory")
        identity = {key: intent[key] for key in ("run_id", "intent_id", "intent_version")}
        identity["pack_id"] = pack_id

        def belongs(record: dict[str, Any]) -> bool:
            return all(record.get(key) == value for key, value in identity.items())

        candidates = [c for c in _load(pack_root / PACK_PATHS["candidates"], lines=True) if belongs(c)]
        receipts = [r for r in _load(pack_root / PACK_PATHS["receipts"], lines=True) if belongs(r)]
        captures = [c for c in _load(pack_root / PACK_PATHS["captures"], lines=True) if belongs(c)]
        # Current candidate receipt pointers exclude superseded historical receipts.
        receipt_by_id = {r["receipt_id"]: r for r in receipts}
        capture_by_id = {c["capture_id"]: c for c in captures}
        media_candidates, pending = [], set()
        for candidate in candidates:
            cid = candidate["candidate_id"]
            if candidate.get("status") not in {"raw", "screened", "qualified", "selected", "rejected"}:
                continue
            receipt = receipt_by_id.get(candidate.get("verification_receipt_id"), {})
            provenance = receipt.get("provenance_check", {})
            matching_capture = any(
                c.get("candidate_id") == cid
                and c.get("observation", {}).get("media_check") == receipt.get("media_check")
                and c.get("observation", {}).get("provenance_check") == provenance
                for c in capture_by_id.values()
            )
            media_ready = (
                receipt.get("candidate_id") == cid
                and receipt.get("pack_id") == pack_id
                and receipt.get("verifier", {}).get("verification_surface") in QUALIFYING_SURFACES
                and not media_evidence_errors(receipt, candidate.get("modality"))
                and provenance.get("status") == "passed"
                and provenance.get("matched_object") is True
                and matching_capture
            )
            if media_ready:
                # Only suppress obvious identity duplicates here. Full cross-source
                # and perceptual dedup remains mandatory in validate_run.
                media_candidates.append(candidate)
            elif candidate.get("status") in {"raw", "screened"}:
                pending.add(cid)
        ready = _distinct_media_ids(media_candidates)
        candidate_ids = _ids(candidates)
        shortlisted = _ids(_load(pack_root / PACK_PATHS["shortlist"]).get("items", [])) & candidate_ids
        selected = _ids(_load(pack_root / PACK_PATHS["selected"]).get("items", [])) & candidate_ids
        rejected = _ids(_load(pack_root / PACK_PATHS["rejected"]).get("items", [])) & candidate_ids
        approaches = [a for a in registry.get("approaches", []) if a.get("pack_id") == pack_id]
        exhausted = bool(approaches) and all(a.get("status") in {"complete", "abandoned"} for a in approaches)
        if len(shortlisted) == 30 and len(selected) == 20 and len(rejected) == 10:
            stage = "validate_full_package"
        elif len(ready) >= 30:
            stage = "curate_and_verify_full_pool"
        elif pending:
            stage = "verify_backlog_and_expand_search"
        else:
            stage = "register_new_search_wave" if exhausted else "continue_discovery"
        packs.append({
            "pack_id": pack_id, "next_action": stage,
            "raw_distinct_candidates": len(_ids(candidates)),
            "media_ready_provisional": len(ready), "pending_media_candidates": len(pending),
            "shortlist_declared": len(shortlisted), "selected_declared": len(selected),
            "rejected_declared": len(rejected), "selected_gap": max(0, 20 - len(selected)),
            "provisional_pool_gap": max(0, 30 - len(ready)),
            "registered_queries_exhausted": exhausted,
            "recovery": "Change population, creator graph, market, or search method; freeze a new wave before searching. Do not repeat unchanged blocked paths or relax hard brief constraints.",
        })
    all_counts_met = all(p["next_action"] == "validate_full_package" for p in packs)
    validation = validate_run(root, require_production_contract_eligible=True) if all_counts_met else None
    contract_ready = bool(validation and validation.get("status") == "PASS"
                          and validation.get("production_contract_eligible") is True)
    return {
        "contract": "research-quantity-checkpoint-v1", "run_dir": str(root),
        "status": "contract_ready_external_review_required" if contract_ready else "continue_work",
        "production_deliverable": False, "packs": packs,
        "validation": validation,
        "boundary": "Provisional media counts are not qualified references. Fresh validation checks contracts, not browser authenticity. Only explicit user cancellation/budget exhaustion or evidenced external blockage can pause an undersized run as incomplete; exhausting an initial batch is not completion.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = checkpoint(args.run_dir)
    except (ContractError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"status": "repair_inputs", "production_deliverable": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
