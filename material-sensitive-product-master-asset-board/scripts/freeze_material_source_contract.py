#!/usr/bin/env python3
"""Freeze material_source_contract.v1 and its hash-locked prompt block."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from material_contract import (
    MaterialContractError,
    canonical_json_bytes,
    create_only_bytes,
    load_json_file,
    load_reference_manifest,
    normalize_source_contract_draft,
    pretty_json_bytes,
    render_material_prompt_block,
    require_exact_path,
    sha256_bytes,
    source_contract_core,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--reference-manifest", required=True, type=Path)
    parser.add_argument("--source-ledger", required=True, type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--prompt-block", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_dir = args.run_dir.expanduser().resolve(strict=False)
    manifest_record = load_reference_manifest(args.reference_manifest, run_dir)
    contract_path = require_exact_path(
        args.contract,
        run_dir / "sources" / "material-source-contract.json",
        "blocked_material_source_contract_location",
        "material source contract",
    )
    block_path = require_exact_path(
        args.prompt_block,
        run_dir / "sources" / "material-prompt-block.md",
        "blocked_material_source_contract_location",
        "material prompt block",
    )
    draft, _ = load_json_file(
        args.source_ledger.expanduser().resolve(strict=False),
        "blocked_material_source_contract_invalid",
        "material source ledger draft",
    )
    normalized = normalize_source_contract_draft(draft, manifest_record)
    normalized["reference_manifest_path"] = str(
        run_dir / "sources" / "reference-manifest.json"
    )
    core = source_contract_core(normalized)
    core_sha = sha256_bytes(canonical_json_bytes(core))
    block_bytes = render_material_prompt_block(core, core_sha)
    contract = {
        **core,
        "contract_core_sha256": core_sha,
        "prompt_block_path": str(block_path),
        "prompt_block_sha256": sha256_bytes(block_bytes),
        "immutability_contract": "create_only_idempotent;rehash_at_every_transition",
    }
    contract_bytes = pretty_json_bytes(contract)

    for path, data, label in (
        (block_path, block_bytes, "prompt block"),
        (contract_path, contract_bytes, "source contract"),
    ):
        if path.exists() and (not path.is_file() or path.read_bytes() != data):
            raise MaterialContractError(
                "blocked_material_source_contract_conflict",
                f"create-only {label} exists with different bytes: {path}",
            )

    created: list[Path] = []
    try:
        if create_only_bytes(
            block_path,
            block_bytes,
            code="blocked_material_source_contract_conflict",
            idempotent=True,
        ):
            created.append(block_path)
        if create_only_bytes(
            contract_path,
            contract_bytes,
            code="blocked_material_source_contract_conflict",
            idempotent=True,
        ):
            created.append(contract_path)
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
                "schema_version": contract["schema_version"],
                "contract_path": str(contract_path),
                "contract_sha256": sha256_bytes(contract_bytes),
                "contract_core_sha256": core_sha,
                "prompt_block_path": str(block_path),
                "prompt_block_sha256": sha256_bytes(block_bytes),
                "reference_manifest_sha256": manifest_record["sha256"],
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
                {
                    "ok": False,
                    "error_code": "blocked_material_source_contract_filesystem",
                    "detail": str(exc),
                }
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)
