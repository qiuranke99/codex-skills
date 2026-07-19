#!/usr/bin/env python3
"""Atomically record one bound worker attempt and main-agent decision."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from validate_coverage_package import ContractError, read_json, resolve_artifact, sha256_file, validate_package


def write_bytes_atomic(path: Path, value: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_bytes(value)
    os.replace(temporary, path)


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    write_bytes_atomic(path, (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def relative_artifact(root: Path, path: Path, code: str) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ContractError(code, f"artifact escapes run root: {resolved}") from exc


def record_decision(
    run_root: Path,
    *,
    view_id: str,
    attempt_id: str,
    worker_result_path: Path,
    inspection_path: Path,
) -> dict[str, Any]:
    root = run_root.resolve()
    manifest_path = root / "00_manifest" / "COVERAGE_MANIFEST.json"
    publication_path = root / "00_manifest" / "PROMPT_PUBLICATION.json"
    original_manifest = manifest_path.read_bytes()
    original_publication = publication_path.read_bytes()
    manifest = read_json(manifest_path, "package_manifest_invalid")
    publication = read_json(publication_path, "prompt_publication_invalid")
    view_id = view_id.upper()
    view = next((item for item in manifest.get("views", []) if item.get("view_id") == view_id), None)
    prompt = next((item for item in manifest.get("prompts", []) if item.get("view_id") == view_id), None)
    if not isinstance(view, dict) or not isinstance(prompt, dict):
        raise ContractError("attempt_ledger_invalid", f"unknown view or prompt: {view_id}")
    if any(item.get("attempt_id") == attempt_id for item in manifest.get("attempts", [])):
        raise ContractError("attempt_ledger_invalid", f"attempt already recorded: {attempt_id}")
    worker_path = resolve_artifact(root, str(worker_result_path), "worker_result_missing")
    inspection = resolve_artifact(root, str(inspection_path), "inspection_missing")
    worker = read_json(worker_path, "worker_result_invalid")
    inspected = read_json(inspection, "inspection_invalid")
    decision = inspected.get("decision")
    if decision not in {"approved", "rejected", "repair_required"}:
        raise ContractError("inspection_invalid", "inspection decision is invalid")
    if (
        worker.get("schema_version") != "frozen_moment_view_worker_result.v1"
        or worker.get("ok") is not True
        or worker.get("run_id") != manifest["job"]["job_id"]
        or worker.get("view_id") != view_id
        or worker.get("attempt_id") != attempt_id
        or inspected.get("run_id") != manifest["job"]["job_id"]
        or inspected.get("view_id") != view_id
        or inspected.get("attempt_id") != attempt_id
    ):
        raise ContractError("attempt_ledger_invalid", "worker or inspection identity differs")
    reference_path = resolve_artifact(root, worker.get("reference_manifest_path"), "worker_result_lineage_mismatch")
    image_path = resolve_artifact(root, worker.get("run_image_path"), "image_missing")
    attempt = {
        "view_id": view_id,
        "attempt_id": attempt_id,
        "attempt_revision": worker.get("attempt_revision"),
        "prompt_path": prompt["prompt_path"],
        "prompt_sha256": prompt["prompt_sha256"],
        "reference_manifest_path": relative_artifact(root, reference_path, "worker_result_lineage_mismatch"),
        "reference_manifest_sha256": sha256_file(reference_path),
        "worker_result_path": relative_artifact(root, worker_path, "worker_result_missing"),
        "worker_result_sha256": sha256_file(worker_path),
        "image_path": relative_artifact(root, image_path, "image_missing"),
        "image_sha256": sha256_file(image_path),
        "inspection_path": relative_artifact(root, inspection, "inspection_missing"),
        "inspection_sha256": sha256_file(inspection),
        "decision": decision,
        "failure_codes": inspected.get("failure_codes", []),
    }
    manifest["attempts"].append(attempt)
    attempts_for_view = [item for item in manifest["attempts"] if item.get("view_id") == view_id]
    if decision == "approved":
        view["status"] = "view_approved"
    elif len(attempts_for_view) >= manifest["job"]["max_attempts_per_view"]:
        view["status"] = "blocked_attempt_budget"
    else:
        view["status"] = "repair_required"
    required = [item["view_id"] for item in manifest["views"] if item.get("required")]
    approved = [
        required_id for required_id in required
        if any(item.get("view_id") == required_id and item.get("decision") == "approved" for item in manifest["attempts"])
    ]
    manifest["qa"].update(
        {
            "required_view_ids": required,
            "approved_required_view_ids": approved,
            "all_required_views_approved": approved == required,
            "max_parallel_workers": 1,
            "unknown_inflight_call_count": 0,
            "runtime_evidence_origin": "live_runtime",
        }
    )
    if approved == required:
        manifest["state"] = {"current": "all_required_views_approved", "terminal_state": None}
    elif decision == "approved":
        manifest["state"] = {"current": "view_approved", "terminal_state": None}
    elif view["status"] == "blocked_attempt_budget":
        manifest["state"] = {"current": "blocked_attempt_budget", "terminal_state": None}
    else:
        manifest["state"] = {"current": "repair_required", "terminal_state": None}
    if publication.get("first_worker_spawn_event_index") is None:
        publication_ms = publication.get("published_at_unix_ms")
        spawn_ms = worker.get("parent_spawn_activity_ms")
        if not isinstance(publication_ms, int) or not isinstance(spawn_ms, int) or spawn_ms < publication_ms:
            raise ContractError("prompt_publication_invalid", "first worker predates prompt publication")
        publication["first_worker_spawn_event_index"] = worker.get("parent_spawn_event_index")
        publication["first_worker_spawn_elapsed_ms"] = spawn_ms - publication_ms
    try:
        write_json_atomic(publication_path, publication)
        write_json_atomic(manifest_path, manifest)
        evidence = validate_package(root, "state")
    except Exception:
        write_bytes_atomic(publication_path, original_publication)
        write_bytes_atomic(manifest_path, original_manifest)
        raise
    return {"attempt": attempt, "state": manifest["state"], "validation": evidence}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--view-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--worker-result", required=True, type=Path)
    parser.add_argument("--inspection", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = record_decision(
            args.run_root,
            view_id=args.view_id,
            attempt_id=args.attempt_id,
            worker_result_path=args.worker_result,
            inspection_path=args.inspection,
        )
    except (ContractError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        code = exc.code if isinstance(exc, ContractError) else "attempt_record_failed"
        print(json.dumps({"ok": False, "error_code": code, "detail": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
