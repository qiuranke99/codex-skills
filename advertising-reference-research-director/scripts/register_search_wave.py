#!/usr/bin/env python3
"""Prospectively append a search wave without rewriting old plan/capture hashes.

The draft contains new approaches only. No CLI timestamp override is provided.
Run before issuing any new query; a hash is not external chronology attestation.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
from pathlib import Path
from _contract_utils import ContractError, read_json, read_jsonl, write_json
from _evidence_binding import approach_registration_bindings, approach_wave_sha256
from _json_schema_subset import validate


def append_wave(registry, draft, *, wave_id, trigger):
    approach_registration_bindings(registry)
    result = copy.deepcopy(registry)
    if not isinstance(draft, list) or not draft:
        raise ContractError("draft must be a nonempty array of new approaches")
    existing = {a["approach_id"] for a in result["approaches"]}
    agents = {a["agent_id"] for a in result["agents"]}
    for item in draft:
        if item["approach_id"] in existing or item["executing_agent_id"] not in agents:
            raise ContractError("new approach ID or registered executor invalid")
        if item.get("started_at") is not None or item.get("status") != "planned":
            raise ContractError("cannot preregister an already-started approach")
        if any(item.get(k) for k in ("returned_count", "qualified_count", "qualification_rate", "failure_records")):
            raise ContractError("new wave cannot contain retrospective yield/failures")
    append = result.setdefault("append_only_plan", {"base_approach_ids": [a["approach_id"] for a in result["approaches"]], "waves": []})
    parent = append["waves"][-1]["plan_sha256"] if append["waves"] else result["registration"]["plan_sha256"]
    wave = {"wave_id": wave_id, "parent_plan_sha256": parent,
            "frozen_at": datetime.now(timezone.utc).isoformat(), "trigger": trigger,
            "approach_ids": [a["approach_id"] for a in draft], "plan_sha256": "0" * 64}
    result["approaches"].extend(copy.deepcopy(draft))
    wave["plan_sha256"] = approach_wave_sha256(result, wave)
    append["waves"].append(wave)
    approach_registration_bindings(result)
    schema = read_json(Path(__file__).resolve().parent.parent / "references/approach_registry.schema.json")
    errors = validate(result, schema)
    if errors:
        raise ContractError(f"wave registry schema errors: {errors}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--wave-id", required=True)
    parser.add_argument("--trigger", required=True)
    args = parser.parse_args()
    path = args.run_dir / "01_orchestration/approach_registry.json"
    if path.resolve() == args.draft.resolve():
        raise ContractError("draft cannot overwrite registry input")
    before = path.read_bytes()
    draft = read_json(args.draft)
    new_ids = {a["approach_id"] for a in draft}
    # A candidate/capture already attributed to the new IDs is not preregistration.
    for pattern in ("**/candidate_ledger.jsonl", "**/browser_capture_records.jsonl"):
        for ledger in args.run_dir.glob(pattern):
            for row in read_jsonl(ledger):
                if row.get("approach_id", row.get("agent_trace", {}).get("approach_id")) in new_ids:
                    raise ContractError("new wave already has candidate/capture activity")
    result = append_wave(read_json(path), draft, wave_id=args.wave_id, trigger=args.trigger)
    if path.read_bytes() != before:
        raise ContractError("registry changed concurrently; reread before append")
    write_json(path, result)
    print(result["append_only_plan"]["waves"][-1]["plan_sha256"])


if __name__ == "__main__":
    main()
