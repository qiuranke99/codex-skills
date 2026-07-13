#!/usr/bin/env python3
"""Build one hash-bound packaging generation receipt from a delegated worker result."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from PIL import Image


class ReceiptError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ReceiptError(f"{label} not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"{label} is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ReceiptError(f"{label} must be a JSON object")
    return data


def inside(root: Path, path: Path, label: str) -> Path:
    root = root.resolve()
    path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ReceiptError(f"{label} must stay inside run root: {path}") from exc
    return path


def run_path(root: Path, locator: Any, label: str) -> Path:
    if not isinstance(locator, str) or not locator:
        raise ReceiptError(f"{label} locator is missing")
    raw = Path(locator)
    return inside(root, raw if raw.is_absolute() else root / raw, label)


def one(records: Any, key: str, value: str, label: str) -> dict[str, Any]:
    if not isinstance(records, list):
        raise ReceiptError(f"{label} must be an array")
    matches = [item for item in records if isinstance(item, dict) and item.get(key) == value]
    if len(matches) != 1:
        raise ReceiptError(f"{label} must contain exactly one {key}={value!r}")
    return matches[0]


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--view-id", required=True)
    parser.add_argument("--worker-result", required=True, type=Path)
    parser.add_argument("--reference-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.run_root.expanduser().resolve()
    worker_arg = args.worker_result.expanduser()
    reference_arg = args.reference_manifest.expanduser()
    output_arg = args.output.expanduser()
    worker_result_path = inside(root, worker_arg if worker_arg.is_absolute() else root / worker_arg, "worker result")
    reference_manifest_path = inside(
        root,
        reference_arg if reference_arg.is_absolute() else root / reference_arg,
        "reference manifest",
    )
    output_path = inside(root, output_arg if output_arg.is_absolute() else root / output_arg, "generation receipt")

    manifest = load_json(root / "00_manifest/run_manifest.json", "run manifest")
    paths = manifest.get("paths") or {}
    coverage = load_json(run_path(root, paths.get("coverage_matrix"), "coverage matrix"), "coverage matrix")
    source_manifest = load_json(run_path(root, paths.get("source_manifest"), "source manifest"), "source manifest")
    prompt_index = load_json(run_path(root, paths.get("generation_prompt_index"), "generation prompt index"), "generation prompt index")
    view = one(coverage.get("views"), "view_id", args.view_id, "coverage views")
    prompt = one(prompt_index.get("prompts"), "view_id", args.view_id, "generation prompts")
    sources = {
        item.get("source_id"): item
        for item in source_manifest.get("sources") or []
        if isinstance(item, dict) and isinstance(item.get("source_id"), str)
    }

    prompt_path = run_path(root, prompt.get("prompt_path"), "generation prompt")
    prompt_sha = sha256_file(prompt_path)
    if prompt.get("prompt_sha256") != prompt_sha:
        raise ReceiptError("generation prompt index hash does not match prompt bytes")

    reference_manifest = load_json(reference_manifest_path, "reference manifest")
    if reference_manifest.get("schema_version") != "packaging_reference_bundle.v1":
        raise ReceiptError("unexpected reference manifest schema")
    entries = reference_manifest.get("ordered_references")
    if not isinstance(entries, list) or not entries:
        raise ReceiptError("reference manifest must contain ordered_references")
    expected_source_ids = view.get("source_refs") or []
    if not isinstance(expected_source_ids, list) or not expected_source_ids:
        raise ReceiptError("coverage view must name source_refs")
    if [item.get("alias") for item in entries] != expected_source_ids:
        raise ReceiptError("frozen reference aliases must exactly preserve coverage source_refs order")
    submitted_frozen: list[dict[str, Any]] = []
    for rank, (entry, source_id) in enumerate(zip(entries, expected_source_ids, strict=True), 1):
        source = sources.get(source_id)
        if not isinstance(source, dict):
            raise ReceiptError(f"unknown source reference: {source_id}")
        frozen_path = run_path(root, entry.get("frozen_path"), f"frozen reference {source_id}")
        frozen_sha = sha256_file(frozen_path)
        if entry.get("index") != rank or entry.get("sha256") != frozen_sha:
            raise ReceiptError(f"frozen reference manifest mismatch for {source_id}")
        if source.get("file_sha256") != frozen_sha:
            raise ReceiptError(f"frozen reference bytes do not match source manifest for {source_id}")
        submitted_frozen.append(
            {
                "rank": rank,
                "reference_id": source_id,
                "frozen_path": str(frozen_path.relative_to(root)).replace("\\", "/"),
                "file_sha256": frozen_sha,
            }
        )
    manifest_payload = canonical_json(entries)
    if reference_manifest.get("ordered_bundle_sha256") != sha256_text(manifest_payload):
        raise ReceiptError("reference manifest ordered bundle self-hash mismatch")

    worker = load_json(worker_result_path, "worker result")
    required_worker_strings = (
        "agent_path",
        "worker_thread_id",
        "worker_turn_id",
        "parent_thread_id",
        "image_generation_call_id",
        "prompt_binding_mode",
    )
    if worker.get("ok") is not True or worker.get("contract") != "delegated_image_worker_result.v1":
        raise ReceiptError("worker result contract did not pass")
    if any(not isinstance(worker.get(key), str) or not worker.get(key) for key in required_worker_strings):
        raise ReceiptError("worker result is missing required provenance identifiers")
    nonce = str(worker["agent_path"]).rsplit("_", 1)[-1]
    if not re.fullmatch(r"[0-9a-f]{32}", nonce):
        raise ReceiptError("worker agent path must end with the complete 32-hex nonce")
    if worker.get("generation_prompt_sha256") != prompt_sha or worker.get("tool_prompt_sha256") != prompt_sha:
        raise ReceiptError("worker prompt bytes do not match the frozen generation prompt")
    if worker.get("prompt_sha_match") is not True:
        raise ReceiptError("worker prompt binding did not pass")
    reference_manifest_sha = sha256_file(reference_manifest_path)
    if worker.get("reference_manifest_sha256") != reference_manifest_sha:
        raise ReceiptError("worker result does not bind the reference manifest bytes")
    if worker.get("ordered_reference_bundle_sha256") != reference_manifest.get("ordered_bundle_sha256"):
        raise ReceiptError("worker result does not bind the ordered reference bundle")
    if worker.get("reference_count") != len(entries):
        raise ReceiptError("worker result reference count mismatch")

    raw_path = run_path(root, worker.get("run_image_path"), "raw generated master")
    expected_raw = run_path(
        root,
        f"05_masters_raw/{view.get('family')}/{args.view_id}.png",
        "expected raw generated master",
    )
    if raw_path != expected_raw:
        raise ReceiptError("worker output path does not match the canonical raw-master path")
    raw_sha = sha256_file(raw_path)
    if worker.get("image_sha256") != raw_sha:
        raise ReceiptError("worker result does not bind the raw-master bytes")
    with Image.open(raw_path) as image:
        image.load()
        width, height = image.size
    if width * 9 != height * 16 or width < 1280 or height < 720:
        raise ReceiptError("raw master must be a decoded horizontal 16:9 image at least 1280x720")
    if worker.get("width_px") != width or worker.get("height_px") != height:
        raise ReceiptError("worker result dimensions do not match the raw master")

    semantic_bindings: list[dict[str, Any]] = []
    for source_id in expected_source_ids:
        source = sources[source_id]
        semantic_bindings.append(
            {
                "role": "source_reference",
                "reference_id": source_id,
                "source_id": source_id,
                "locator": source.get("file_path"),
                "file_sha256": source.get("file_sha256"),
            }
        )
    for parent_view_id in view.get("parent_anchor_view_ids") or []:
        matches = [
            (source_id, sources[source_id])
            for source_id in expected_source_ids
            if source_id in sources and sources[source_id].get("view_id") == parent_view_id
        ]
        if len(matches) != 1:
            raise ReceiptError(f"parent anchor {parent_view_id} lacks one source-bound asset")
        source_id, source = matches[0]
        semantic_bindings.append(
            {
                "role": "parent_anchor",
                "reference_id": parent_view_id,
                "source_id": source_id,
                "locator": source.get("file_path"),
                "file_sha256": source.get("file_sha256"),
            }
        )
    semantic_bindings.sort(key=lambda item: (item["role"], item["reference_id"], item["source_id"]))

    result = {
        "schema_version": "packaging-generation-receipt.v2",
        "asset_id": view.get("asset_id"),
        "view_id": args.view_id,
        "prompt_sha256": prompt_sha,
        "output_path": str(raw_path.relative_to(root)).replace("\\", "/"),
        "output_file_sha256": raw_sha,
        "generation_mode": "independent_full_frame",
        "worker_transport_mode": "delegated_single_image_worker",
        "output_pixel_dimensions": {"width": width, "height": height},
        "post_generation_resize_applied": False,
        "reference_ids": expected_source_ids,
        "source_reference_bindings": semantic_bindings,
        "submitted_reference_bindings": submitted_frozen,
        "submitted_reference_set_sha256": sha256_text(canonical_json(submitted_frozen)),
        "worker_provenance": {
            "contract": worker["contract"],
            "result_path": str(worker_result_path.relative_to(root)).replace("\\", "/"),
            "result_sha256": sha256_file(worker_result_path),
            "agent_path": worker["agent_path"],
            "worker_thread_id": worker["worker_thread_id"],
            "worker_turn_id": worker["worker_turn_id"],
            "parent_thread_id": worker["parent_thread_id"],
            "image_generation_call_id": worker["image_generation_call_id"],
            "prompt_binding_mode": worker["prompt_binding_mode"],
            "reference_manifest_path": str(reference_manifest_path.relative_to(root)).replace("\\", "/"),
            "reference_manifest_sha256": reference_manifest_sha,
            "ordered_reference_bundle_sha256": reference_manifest["ordered_bundle_sha256"],
        },
    }
    write_json(output_path, result)
    print(json.dumps({"status": "PASS", "receipt": str(output_path), "sha256": sha256_file(output_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ReceiptError, OSError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "detail": str(exc)}, sort_keys=True))
        raise SystemExit(2)
