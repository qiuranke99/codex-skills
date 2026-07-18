#!/usr/bin/env python3
"""Render the only permitted image-worker exec source as deterministic bytes."""

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
    load_reference_manifest,
    load_source_contract,
    pretty_json_bytes,
    read_prompt_bytes,
    render_worker_exec_bytes,
    require_exact_path,
    require_inside,
    require_prompt_block_once,
    sha256_bytes,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--attempt-dir", required=True, type=Path)
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
        run_dir,
        args.attempt_dir,
        "blocked_worker_exec_scope",
        "attempt directory",
    )
    attempt_id = attempt_dir.name
    if (
        not ATTEMPT_RE.fullmatch(attempt_id)
        or attempt_dir.parent != (run_dir / "attempts").resolve(strict=False)
        or not attempt_dir.is_dir()
    ):
        raise MaterialContractError(
            "blocked_worker_exec_scope",
            "attempt directory must be an existing direct run/attempts/01..03 directory",
        )
    if not re.fullmatch(r"[0-9a-f]{32}", args.worker_run_nonce):
        raise MaterialContractError(
            "blocked_worker_nonce_invalid", "worker nonce must be exactly 32 lowercase hex characters"
        )
    prompt_path = require_inside(
        attempt_dir,
        args.expected_prompt,
        "blocked_worker_exec_scope",
        "generation prompt",
    )
    if prompt_path.parent != attempt_dir:
        raise MaterialContractError(
            "blocked_worker_exec_scope", "generation prompt must be directly inside the attempt"
        )
    exec_path = require_exact_path(
        args.exec_source,
        attempt_dir / "worker_exec.js",
        "blocked_worker_exec_scope",
        "worker exec source",
    )
    receipt_path = require_exact_path(
        args.exec_receipt,
        attempt_dir / "worker_exec.json",
        "blocked_worker_exec_scope",
        "worker exec receipt",
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
    prompt_text = prompt_bytes.decode("utf-8")
    exec_bytes = render_worker_exec_bytes(
        args.worker_run_nonce,
        prompt_text,
        manifest_record["paths"],
    )
    receipt = {
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
    receipt_bytes = pretty_json_bytes(receipt)
    for path, data, label in (
        (exec_path, exec_bytes, "worker exec source"),
        (receipt_path, receipt_bytes, "worker exec receipt"),
    ):
        if path.exists() and (not path.is_file() or path.read_bytes() != data):
            raise MaterialContractError(
                "blocked_worker_exec_conflict",
                f"create-only {label} exists with different bytes: {path}",
            )
    created: list[Path] = []
    try:
        if create_only_bytes(
            exec_path,
            exec_bytes,
            code="blocked_worker_exec_conflict",
            idempotent=True,
        ):
            created.append(exec_path)
        if create_only_bytes(
            receipt_path,
            receipt_bytes,
            code="blocked_worker_exec_conflict",
            idempotent=True,
        ):
            created.append(receipt_path)
    except BaseException:
        for path in reversed(created):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    print(
        json.dumps(
            {
                "ok": True,
                "schema_version": receipt["schema_version"],
                "attempt_id": attempt_id,
                "exec_source_path": str(exec_path),
                "exec_source_sha256": receipt["exec_source_sha256"],
                "exec_receipt_path": str(receipt_path),
                "exec_receipt_sha256": sha256_bytes(receipt_bytes),
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
                {"ok": False, "error_code": "blocked_worker_exec_filesystem", "detail": str(exc)}
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)
