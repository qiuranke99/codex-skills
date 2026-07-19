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

import inspection_runtime
import resolve_worker_image as worker_resolver
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
    state_db: Path | None = None,
    codex_home: Path | None = None,
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
    inspector_thread_id = inspected.get("inspector_task_id")
    inspected_at_utc = inspected.get("inspected_at_utc")
    if not isinstance(inspector_thread_id, str) or not isinstance(inspected_at_utc, str):
        raise ContractError("inspection_runtime_identity_invalid", "inspection lacks exact inspector task and time")
    revision = worker.get("attempt_revision")
    maximum = manifest["job"]["max_attempts_per_view"]
    existing_revisions = [
        item.get("attempt_revision")
        for item in manifest.get("attempts", [])
        if item.get("view_id") == view_id
    ]
    if (
        not isinstance(revision, int)
        or isinstance(revision, bool)
        or not 1 <= revision <= maximum
        or any(not isinstance(item, int) for item in existing_revisions)
        or revision != len(existing_revisions) + 1
    ):
        raise ContractError("attempt_ledger_invalid", "bound attempt revisions must be contiguous from one")
    reference_path = resolve_artifact(root, worker.get("reference_manifest_path"), "worker_result_lineage_mismatch")
    image_path = resolve_artifact(root, worker.get("run_image_path"), "image_missing")
    authority_mode = worker.get("prompt_authority_mode", "base_prompt")
    repair_publication_path: Path | None = None
    repair_publication_sha256: str | None = None
    if authority_mode == "repair_prompt":
        repair_publication_path = resolve_artifact(
            root, worker.get("repair_publication_path"), "blocked_repair_prompt_invalid"
        )
        authority = worker_resolver.load_repair_publication(
            run_root=root,
            manifest=manifest,
            publication_path=repair_publication_path,
            expected_prompt=Path(str(worker.get("generation_prompt_path", ""))).resolve(),
            view_id=view_id,
            attempt_id=attempt_id,
            attempt_revision=revision,
        )
        repair_publication_sha256 = authority["publication_sha256"]
        if worker.get("repair_publication_sha256") != repair_publication_sha256:
            raise ContractError("blocked_repair_prompt_invalid", "worker repair publication hash differs")
        prompt_path = authority["prompt_path"]
        prompt_sha256 = authority["prompt_sha256"]
    elif authority_mode == "base_prompt":
        if worker.get("repair_publication_path") is not None or worker.get("repair_publication_sha256") is not None:
            raise ContractError("blocked_repair_prompt_invalid", "base prompt worker claims repair publication fields")
        prompt_path = resolve_artifact(root, prompt["prompt_path"], "attempt_prompt_mismatch")
        prompt_sha256 = prompt["prompt_sha256"]
    else:
        raise ContractError("blocked_repair_prompt_invalid", "worker prompt authority mode is invalid")
    if (
        Path(str(worker.get("generation_prompt_path", ""))).resolve() != prompt_path
        or worker.get("generation_prompt_sha256") != prompt_sha256
        or worker.get("tool_prompt_sha256") != prompt_sha256
    ):
        raise ContractError("attempt_prompt_mismatch", "worker prompt does not match its frozen authority")
    resolved_codex_home = (codex_home or worker_resolver.default_codex_home()).resolve()
    resolved_state_db = (state_db or (resolved_codex_home / "state_5.sqlite")).resolve()
    try:
        inspector_rollout = worker_resolver.resolve_thread_rollout(
            resolved_state_db,
            inspector_thread_id,
            "inspection_runtime_state_unavailable",
        )
        pixel_proof, pixel_events = inspection_runtime.find_pixel_open(
            events=worker_resolver.read_rollout(inspector_rollout),
            inspector_thread_id=inspector_thread_id,
            image_path=image_path,
            image_sha256=sha256_file(image_path),
            inspected_at_utc=inspected_at_utc,
        )
    except (worker_resolver.ContractError, inspection_runtime.InspectionRuntimeError) as exc:
        code = getattr(exc, "code", "inspection_runtime_invalid")
        raise ContractError(code, str(exc)) from exc
    runtime_slice_path = inspection.with_name("main-inspection-runtime.jsonl")
    runtime_receipt_path = inspection.with_name("main-inspection-runtime-receipt.json")
    runtime_slice_bytes = inspection_runtime.snapshot_bytes(pixel_events)
    runtime_receipt = {
        **pixel_proof,
        "run_id": manifest["job"]["job_id"],
        "view_id": view_id,
        "attempt_id": attempt_id,
        "inspected_at_utc": inspected_at_utc,
        "source_rollout_path": str(inspector_rollout.resolve()),
        "rollout_slice_path": relative_artifact(root, runtime_slice_path, "inspection_runtime_invalid"),
        "rollout_slice_sha256": worker_resolver.sha256_bytes(runtime_slice_bytes),
    }
    runtime_receipt_bytes = (
        json.dumps(runtime_receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    runtime_originals = {
        runtime_slice_path: runtime_slice_path.read_bytes() if runtime_slice_path.is_file() else None,
        runtime_receipt_path: runtime_receipt_path.read_bytes() if runtime_receipt_path.is_file() else None,
    }
    attempt = {
        "view_id": view_id,
        "attempt_id": attempt_id,
        "attempt_revision": revision,
        "prompt_path": relative_artifact(root, prompt_path, "attempt_prompt_mismatch"),
        "prompt_sha256": prompt_sha256,
        "prompt_authority_mode": authority_mode,
        "reference_manifest_path": relative_artifact(root, reference_path, "worker_result_lineage_mismatch"),
        "reference_manifest_sha256": sha256_file(reference_path),
        "worker_result_path": relative_artifact(root, worker_path, "worker_result_missing"),
        "worker_result_sha256": sha256_file(worker_path),
        "image_path": relative_artifact(root, image_path, "image_missing"),
        "image_sha256": sha256_file(image_path),
        "inspection_path": relative_artifact(root, inspection, "inspection_missing"),
        "inspection_sha256": sha256_file(inspection),
        "inspection_runtime_receipt_path": relative_artifact(
            root, runtime_receipt_path, "inspection_runtime_invalid"
        ),
        "inspection_runtime_receipt_sha256": worker_resolver.sha256_bytes(runtime_receipt_bytes),
        "decision": decision,
        "failure_codes": inspected.get("failure_codes", []),
    }
    if repair_publication_path is not None:
        attempt["repair_publication_path"] = relative_artifact(
            root, repair_publication_path, "blocked_repair_prompt_invalid"
        )
        attempt["repair_publication_sha256"] = repair_publication_sha256
    manifest["attempts"].append(attempt)
    attempts_for_view = [item for item in manifest["attempts"] if item.get("view_id") == view_id]
    if decision == "approved":
        view["status"] = "view_approved"
    elif revision >= maximum:
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
        write_bytes_atomic(runtime_slice_path, runtime_slice_bytes)
        write_bytes_atomic(runtime_receipt_path, runtime_receipt_bytes)
        write_json_atomic(publication_path, publication)
        write_json_atomic(manifest_path, manifest)
        evidence = validate_package(root, "state")
    except Exception:
        write_bytes_atomic(publication_path, original_publication)
        write_bytes_atomic(manifest_path, original_manifest)
        for path, value in runtime_originals.items():
            if value is None:
                if path.is_file() and not path.is_symlink():
                    path.unlink()
            else:
                write_bytes_atomic(path, value)
        raise
    return {"attempt": attempt, "state": manifest["state"], "validation": evidence}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--view-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--worker-result", required=True, type=Path)
    parser.add_argument("--inspection", required=True, type=Path)
    parser.add_argument("--state-db", type=Path)
    parser.add_argument("--codex-home", type=Path)
    args = parser.parse_args()
    try:
        result = record_decision(
            args.run_root,
            view_id=args.view_id,
            attempt_id=args.attempt_id,
            worker_result_path=args.worker_result,
            inspection_path=args.inspection,
            state_db=args.state_db,
            codex_home=args.codex_home,
        )
    except (ContractError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        code = exc.code if isinstance(exc, ContractError) else "attempt_record_failed"
        print(json.dumps({"ok": False, "error_code": code, "detail": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
