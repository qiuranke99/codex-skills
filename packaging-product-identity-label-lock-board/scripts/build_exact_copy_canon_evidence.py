#!/usr/bin/env python3
"""Build v2 Canon authority evidence from one validated COMPLETE packaging run."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from validate_packaging_run import validate_run


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: dict[str, Any]) -> str:
    payload = copy.deepcopy(value)
    payload.pop("sha256", None)
    return hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()


def strict_child(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return path.resolve() != root.resolve()
    except ValueError:
        return False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--asset-key", required=True)
    parser.add_argument("--primary-view-id", default="ROT_0000")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project_root = args.project_root.resolve()
    run_root = args.run_root.resolve()
    output = args.output.resolve()
    if not project_root.is_dir() or not strict_child(run_root, project_root):
        print("ERROR: run root must be a strict child of the project root")
        return 2
    if not strict_child(output, project_root):
        print("ERROR: output must be a project-relative child path")
        return 2
    errors = validate_run(run_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    manifest_path = run_root / "00_manifest/run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("stage") != "COMPLETE"
        or manifest.get("exact_copy_mode") != "all_visible_product_native_copy"
        or manifest.get("allow_geometry_only_preview") is not False
    ):
        print("ERROR: Canon exact authority requires a COMPLETE all-visible exact-copy run")
        return 1
    asset_qa_path = run_root / manifest["paths"]["asset_qa"]
    asset_qa = json.loads(asset_qa_path.read_text(encoding="utf-8"))
    matches = [
        item for item in asset_qa["assets"]
        if item.get("view_id") == args.primary_view_id
    ]
    if len(matches) != 1:
        print("ERROR: primary view must identify exactly one approved master")
        return 1
    primary = matches[0]
    post_path = run_root / manifest["paths"]["post_composite_verification"]
    post = json.loads(post_path.read_text(encoding="utf-8"))
    post_matches = [
        item for item in post.get("asset_results", [])
        if item.get("asset_id") == primary.get("asset_id")
        and item.get("view_id") == primary.get("view_id")
        and item.get("asset_file_sha256") == primary.get("file_sha256")
    ]
    if len(post_matches) != 1:
        print("ERROR: primary master lacks one exact post-verification result")
        return 1
    post_result = post_matches[0]
    run_root_locator = run_root.relative_to(project_root).as_posix()
    role_mapping = {
        "exact_copy_bundle": ("exact_copy_bundle", "exact_copy_bundle_file_sha256"),
        "coverage_matrix": ("coverage_matrix", "coverage_matrix_sha256"),
        "generation_prompt_index": ("generation_prompt_index", "generation_prompt_index_sha256"),
        "asset_qa": ("asset_qa", "asset_qa_sha256"),
        "continuity_qa": ("continuity_qa", "continuity_qa_sha256"),
        "post_composite_verification": (
            "post_composite_verification", "post_composite_verification_sha256"
        ),
    }
    locks = {
        role: {
            "locator": (Path(run_root_locator) / manifest["paths"][path_key]).as_posix(),
            "file_sha256": manifest["hashes"][hash_key],
        }
        for role, (path_key, hash_key) in role_mapping.items()
    }
    validator_path = Path(__file__).resolve().with_name("validate_packaging_run.py")
    evidence: dict[str, Any] = {
        "schema_version": "packaging-exact-copy-canon-evidence.v2",
        "owner_skill": "packaging-product-identity-label-lock-board",
        "asset_key": args.asset_key,
        "primary_asset_sha256": primary["file_sha256"],
        "packaging_run": {
            "run_root_locator": run_root_locator,
            "run_manifest_locator": (Path(run_root_locator) / "00_manifest/run_manifest.json").as_posix(),
            "run_manifest_file_sha256": sha256_file(manifest_path),
            "run_id": manifest["run_id"],
            "contract_version": manifest["contract_version"],
        },
        "validator_file_sha256": sha256_file(validator_path),
        "run_artifact_locks": locks,
        "primary_member": {
            "asset_id": primary["asset_id"],
            "view_id": primary["view_id"],
            "locator": (Path(run_root_locator) / primary["file_path"]).as_posix(),
            "file_sha256": primary["file_sha256"],
            "post_result_id": post_result["result_id"],
            "post_result_sha256": canonical_hash(post_result),
        },
        "sha256": None,
    }
    evidence["sha256"] = canonical_hash(evidence)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "PASS",
        "evidence_locator": output.relative_to(project_root).as_posix(),
        "evidence_file_sha256": sha256_file(output),
        "evidence_semantic_sha256": evidence["sha256"],
        "primary_asset_locator": evidence["primary_member"]["locator"],
        "primary_asset_sha256": evidence["primary_asset_sha256"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
