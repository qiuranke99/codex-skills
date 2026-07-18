#!/usr/bin/env python3
"""Freeze one returned worker spawn against the deterministic exec artifact set."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from material_contract import (
    ATTEMPT_RE,
    MaterialContractError,
    create_only_bytes,
    load_json_file,
    load_reference_manifest,
    load_source_contract,
    pretty_json_bytes,
    read_prompt_bytes,
    render_worker_exec_bytes,
    require_exact_keys,
    require_exact_path,
    require_inside,
    require_prompt_block_once,
    sha256_bytes,
)


UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
EXEC_RECEIPT_KEYS = {
    "schema_version",
    "attempt_id",
    "worker_run_nonce",
    "generation_prompt_path",
    "generation_prompt_sha256",
    "reference_manifest_path",
    "reference_manifest_sha256",
    "ordered_reference_bundle_sha256",
    "ordered_reference_paths",
    "source_contract_path",
    "source_contract_sha256",
    "prompt_block_sha256",
    "exec_source_path",
    "exec_source_sha256",
    "call_contract",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--attempt-dir", required=True, type=Path)
    parser.add_argument("--worker-spawn", required=True, type=Path)
    parser.add_argument("--agent-path", required=True)
    parser.add_argument("--parent-thread-id", required=True)
    parser.add_argument("--not-before-ms", required=True, type=int)
    parser.add_argument("--worker-run-nonce", required=True)
    parser.add_argument("--expected-prompt", required=True, type=Path)
    parser.add_argument("--reference-manifest", required=True, type=Path)
    parser.add_argument("--source-contract", required=True, type=Path)
    parser.add_argument("--exec-source", required=True, type=Path)
    parser.add_argument("--exec-receipt", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_dir = args.run_dir.expanduser().resolve(strict=False)
    attempt_dir = require_inside(
        run_dir, args.attempt_dir, "blocked_worker_spawn_scope", "attempt directory"
    )
    attempt_id = attempt_dir.name
    if (
        not ATTEMPT_RE.fullmatch(attempt_id)
        or attempt_dir.parent != (run_dir / "attempts").resolve(strict=False)
        or not attempt_dir.is_dir()
    ):
        raise MaterialContractError(
            "blocked_worker_spawn_scope", "attempt must be an existing direct run/attempts/01..03 directory"
        )
    spawn_path = require_exact_path(
        args.worker_spawn,
        attempt_dir / "worker_spawn.json",
        "blocked_worker_spawn_scope",
        "worker spawn record",
    )
    prompt_path = require_inside(
        attempt_dir, args.expected_prompt, "blocked_worker_spawn_scope", "generation prompt"
    )
    exec_path = require_exact_path(
        args.exec_source,
        attempt_dir / "worker_exec.js",
        "blocked_worker_spawn_scope",
        "worker exec source",
    )
    receipt_path = require_exact_path(
        args.exec_receipt,
        attempt_dir / "worker_exec.json",
        "blocked_worker_spawn_scope",
        "worker exec receipt",
    )
    if prompt_path.parent != attempt_dir:
        raise MaterialContractError(
            "blocked_worker_spawn_scope", "generation prompt must be directly inside the attempt"
        )
    if (
        not args.agent_path.startswith("/root/")
        or ".." in args.agent_path.split("/")
        or "\\" in args.agent_path
    ):
        raise MaterialContractError(
            "blocked_worker_agent_path_invalid", "agent path must be one canonical /root/... path"
        )
    if not UUID_RE.fullmatch(args.parent_thread_id):
        raise MaterialContractError(
            "blocked_worker_parent_mismatch", "parent thread id must be a canonical UUID"
        )
    if args.not_before_ms < 0:
        raise MaterialContractError(
            "blocked_worker_checkpoint_invalid", "spawn checkpoint must be non-negative"
        )
    if not re.fullmatch(r"[0-9a-f]{32}", args.worker_run_nonce):
        raise MaterialContractError(
            "blocked_worker_nonce_invalid", "worker nonce must be exactly 32 lowercase hex characters"
        )

    manifest_record = load_reference_manifest(args.reference_manifest, run_dir)
    contract_record = load_source_contract(args.source_contract, run_dir, manifest_record)
    prompt_bytes = read_prompt_bytes(
        prompt_path, "blocked_worker_prompt_sidecar_invalid", "generation prompt"
    )
    require_prompt_block_once(
        prompt_bytes,
        contract_record["prompt_block_bytes"],
        "blocked_worker_prompt_contract_mismatch",
    )
    if not exec_path.is_file():
        raise MaterialContractError("blocked_worker_exec_missing", f"worker exec source missing: {exec_path}")
    exec_bytes = exec_path.read_bytes()
    expected_exec = render_worker_exec_bytes(
        args.worker_run_nonce,
        prompt_bytes.decode("utf-8"),
        manifest_record["paths"],
    )
    if exec_bytes != expected_exec:
        raise MaterialContractError(
            "blocked_worker_exec_source_mismatch", "worker exec source is not the deterministic render"
        )
    receipt, receipt_bytes = load_json_file(
        receipt_path, "blocked_worker_exec_receipt_invalid", "worker exec receipt"
    )
    require_exact_keys(receipt, EXEC_RECEIPT_KEYS, "blocked_worker_exec_receipt_invalid", "worker exec receipt")
    expected_receipt_values = {
        "schema_version": "material_render_worker_exec.v1",
        "attempt_id": attempt_id,
        "worker_run_nonce": args.worker_run_nonce,
        "generation_prompt_path": str(prompt_path),
        "generation_prompt_sha256": sha256_bytes(prompt_bytes),
        "reference_manifest_path": str(args.reference_manifest.expanduser().resolve(strict=False)),
        "reference_manifest_sha256": manifest_record["sha256"],
        "ordered_reference_bundle_sha256": manifest_record["ordered_bundle_sha256"],
        "ordered_reference_paths": [str(path) for path in manifest_record["paths"]],
        "source_contract_path": str(args.source_contract.expanduser().resolve(strict=False)),
        "source_contract_sha256": contract_record["sha256"],
        "prompt_block_sha256": contract_record["prompt_block_sha256"],
        "exec_source_path": str(exec_path),
        "exec_source_sha256": sha256_bytes(exec_bytes),
        "call_contract": "exactly_one_imagegen;no_decision;empty_worker_final",
    }
    if receipt != expected_receipt_values:
        raise MaterialContractError(
            "blocked_worker_exec_receipt_invalid", "worker exec receipt does not match current frozen artifacts"
        )

    spawn = {
        "schema_version": "material_worker_spawn.v2",
        "attempt_id": attempt_id,
        "agent_path": args.agent_path,
        "parent_thread_id": args.parent_thread_id,
        "worker_spawn_not_before_ms": args.not_before_ms,
        "worker_run_nonce": args.worker_run_nonce,
        "generation_prompt_path": str(prompt_path),
        "generation_prompt_sha256": sha256_bytes(prompt_bytes),
        "reference_manifest_path": str(args.reference_manifest.expanduser().resolve(strict=False)),
        "reference_manifest_sha256": manifest_record["sha256"],
        "source_contract_path": str(args.source_contract.expanduser().resolve(strict=False)),
        "source_contract_sha256": contract_record["sha256"],
        "prompt_block_sha256": contract_record["prompt_block_sha256"],
        "worker_exec_source_path": str(exec_path),
        "worker_exec_source_sha256": sha256_bytes(exec_bytes),
        "worker_exec_receipt_path": str(receipt_path),
        "worker_exec_receipt_sha256": sha256_bytes(receipt_bytes),
        "pre_spawn_state": "one_non_decision_worker_spawned_unresolved",
    }
    spawn_bytes = pretty_json_bytes(spawn)
    created = create_only_bytes(
        spawn_path,
        spawn_bytes,
        code="blocked_worker_spawn_conflict",
        idempotent=True,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "schema_version": spawn["schema_version"],
                "attempt_id": attempt_id,
                "worker_spawn_path": str(spawn_path),
                "worker_spawn_sha256": sha256_bytes(spawn_bytes),
                "worker_exec_source_sha256": spawn["worker_exec_source_sha256"],
                "idempotent": not created,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MaterialContractError as exc:
        print(
            json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}),
            file=sys.stderr,
        )
        raise SystemExit(2)
    except OSError as exc:
        print(
            json.dumps(
                {"ok": False, "error_code": "blocked_worker_spawn_filesystem", "detail": str(exc)}
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)
