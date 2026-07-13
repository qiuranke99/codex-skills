#!/usr/bin/env python3
"""Build an exact final prompt-pair result from one accepted material-board attempt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


class PublicationError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_path(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def require_inside(root: Path, path: Path) -> Path:
    resolved = path.expanduser().resolve()
    try:
        common = os.path.commonpath([normalized_path(root), normalized_path(resolved)])
    except ValueError as exc:
        raise PublicationError("blocked_publication_artifact_location", str(exc)) from exc
    if common != normalized_path(root):
        raise PublicationError(
            "blocked_publication_artifact_location",
            f"artifact is outside the run directory: {resolved}",
        )
    return resolved


def exact_prompt(path: Path) -> tuple[str, str]:
    if not path.is_file():
        raise PublicationError("blocked_prompt_pair_integrity", f"prompt sidecar missing: {path}")
    data = path.read_bytes()
    if not data or data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise PublicationError(
            "blocked_prompt_pair_integrity",
            f"prompt sidecar must be non-empty UTF-8/LF without BOM: {path}",
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PublicationError("blocked_prompt_pair_integrity", str(exc)) from exc
    return text, sha256_bytes(data)


def load_json(path: Path, code: str) -> tuple[dict[str, Any], bytes]:
    if not path.is_file():
        raise PublicationError(code, f"JSON artifact missing: {path}")
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise PublicationError(code, f"JSON must be UTF-8/LF without BOM: {path}")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicationError(code, str(exc)) from exc
    if not isinstance(value, dict):
        raise PublicationError(code, f"JSON artifact is not an object: {path}")
    return value, data


def same_path(value: Any, expected: Path) -> bool:
    return isinstance(value, str) and normalized_path(Path(value)) == normalized_path(expected)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--accepted-attempt", required=True, type=Path)
    parser.add_argument("--board", required=True, type=Path)
    parser.add_argument("--generation-prompt", required=True, type=Path)
    parser.add_argument("--enhancement-prompt", required=True, type=Path)
    parser.add_argument("--worker-result", required=True, type=Path)
    parser.add_argument("--inspection", required=True, type=Path)
    parser.add_argument("--reference-manifest", required=True, type=Path)
    parser.add_argument("--handoff", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-output-bytes", type=int)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    if not run_dir.is_dir():
        raise PublicationError("blocked_publication_run_missing", f"run directory missing: {run_dir}")

    accepted_path = require_inside(run_dir, args.accepted_attempt)
    board = require_inside(run_dir, args.board)
    generation_path = require_inside(run_dir, args.generation_prompt)
    enhancement_path = require_inside(run_dir, args.enhancement_prompt)
    worker_path = require_inside(run_dir, args.worker_result)
    inspection_path = require_inside(run_dir, args.inspection)
    manifest_path = require_inside(run_dir, args.reference_manifest)
    handoff_path = require_inside(run_dir, args.handoff)
    output = require_inside(run_dir, args.output)

    accepted, _ = load_json(accepted_path, "blocked_accepted_attempt_invalid")
    if accepted.get("schema_version") != "material_accepted_attempt.v1":
        raise PublicationError("blocked_accepted_attempt_invalid", "unexpected accepted-attempt schema")
    attempt_id = accepted.get("attempt_id")
    if not isinstance(attempt_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", attempt_id):
        raise PublicationError("blocked_accepted_attempt_invalid", "invalid accepted attempt ID")
    attempt_dir = (run_dir / "attempts" / attempt_id).resolve()
    if not attempt_dir.is_dir():
        raise PublicationError("blocked_accepted_attempt_invalid", f"attempt directory missing: {attempt_dir}")

    attempt_artifacts = {
        "generation_prompt_path": generation_path,
        "enhancement_prompt_path": enhancement_path,
        "board_path": board,
        "worker_result_path": worker_path,
        "inspection_path": inspection_path,
        "handoff_path": handoff_path,
    }
    for field, path in attempt_artifacts.items():
        if path.parent != attempt_dir:
            raise PublicationError(
                "blocked_accepted_attempt_mismatch",
                f"{field} is not directly inside the accepted attempt directory",
            )
        if not same_path(accepted.get(field), path):
            raise PublicationError(
                "blocked_accepted_attempt_mismatch",
                f"accepted attempt does not bind {field}",
            )

    generation_text, generation_sha = exact_prompt(generation_path)
    enhancement_text, enhancement_sha = exact_prompt(enhancement_path)
    if not board.is_file():
        raise PublicationError("blocked_publication_board_missing", f"board missing: {board}")
    board_sha = sha256_bytes(board.read_bytes())
    if not all(
        [
            accepted.get("generation_prompt_sha256") == generation_sha,
            accepted.get("4k_enhancement_prompt_sha256") == enhancement_sha,
            accepted.get("image_sha256") == board_sha,
        ]
    ):
        raise PublicationError(
            "blocked_accepted_attempt_mismatch",
            "accepted attempt hashes do not match its prompt pair and board",
        )

    worker, worker_bytes = load_json(worker_path, "blocked_worker_result_invalid")
    inspection, inspection_bytes = load_json(inspection_path, "blocked_board_inspection_invalid")
    manifest, manifest_bytes = load_json(manifest_path, "blocked_reference_manifest_invalid")
    if not all(
        [
            accepted.get("worker_result_sha256") == sha256_bytes(worker_bytes),
            accepted.get("inspection_sha256") == sha256_bytes(inspection_bytes),
        ]
    ):
        raise PublicationError(
            "blocked_accepted_attempt_mismatch",
            "accepted attempt does not bind worker-result and inspection hashes",
        )
    expected_manifest = run_dir / "sources" / "reference-manifest.json"
    if manifest_path != expected_manifest:
        raise PublicationError(
            "blocked_reference_manifest_invalid",
            f"reference manifest must be exactly {expected_manifest}",
        )
    if manifest.get("schema_version") != "material_reference_bundle.v1":
        raise PublicationError("blocked_reference_manifest_invalid", "unexpected reference schema")
    if not all(
        [
            worker.get("ok") is True,
            worker.get("contract") == "delegated_product_image_worker_result.v1",
            worker.get("prompt_sha_match") is True,
            worker.get("reference_mode") == "frozen_manifest",
            worker.get("reference_bytes_verified") is True,
            worker.get("reference_count", 0) > 0,
            worker.get("generation_prompt_sha256") == generation_sha,
            worker.get("tool_prompt_sha256") == generation_sha,
            worker.get("image_sha256") == board_sha,
            worker.get("reference_manifest_sha256") == sha256_bytes(manifest_bytes),
            same_path(worker.get("run_image_path"), board),
        ]
    ):
        raise PublicationError(
            "blocked_publication_provenance_mismatch",
            "worker result does not bind board, prompt, and material reference manifest",
        )
    if not all(
        [
            inspection.get("inspected") is True,
            inspection.get("attempt_id") == attempt_id,
            inspection.get("assistant_qa_status") in {"passed", "conditional"},
            inspection.get("image_sha256") == board_sha,
            inspection.get("prompt_bound") == "pass",
            inspection.get("single_board_contract") == "pass",
            inspection.get("material_evidence_present") == "pass",
            same_path(inspection.get("board_path"), board),
        ]
    ):
        raise PublicationError(
            "blocked_board_inspection_invalid",
            "inspection does not bind a material-aware visual review to the accepted board",
        )

    if not handoff_path.is_file():
        raise PublicationError("blocked_4k_handoff_missing", f"handoff missing: {handoff_path}")
    handoff_bytes = handoff_path.read_bytes()
    if handoff_bytes.startswith(b"\xef\xbb\xbf") or b"\r" in handoff_bytes:
        raise PublicationError("blocked_4k_handoff_invalid", "handoff must be UTF-8/LF without BOM")
    try:
        handoff = handoff_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PublicationError("blocked_4k_handoff_invalid", str(exc)) from exc
    if not re.search(r'(?m)^\s*aspect_ratio:\s*["\']16:9["\']\s*$', handoff) or not re.search(
        r'(?m)^\s*image_size:\s*["\']4K["\']\s*$', handoff
    ):
        raise PublicationError("blocked_4k_handoff_invalid", "handoff lacks exact 16:9 and 4K controls")
    for required_handoff_term in ["codex_asset_board:", "original_source_references:"]:
        if required_handoff_term not in handoff:
            raise PublicationError(
                "blocked_4k_handoff_invalid",
                f"handoff lacks required reference bundle term: {required_handoff_term}",
            )
    if accepted.get("handoff_sha256") != sha256_bytes(handoff_bytes):
        raise PublicationError("blocked_accepted_attempt_mismatch", "accepted handoff hash does not match")

    production_approval = inspection.get("production_approval_status", "not_granted")
    if production_approval not in {"not_granted", "user_granted", "external_pipeline_granted"}:
        raise PublicationError("blocked_board_inspection_invalid", "invalid production approval status")

    payload = (
        f"![Material-Sensitive Product Master Asset Board](<{board.as_posix()}>)\n\n"
        f"final_generation_prompt:\n{generation_text}\n\n"
        f"generation_prompt_sha256: {generation_sha}\n\n"
        f"final_4k_enhancement_prompt:\n{enhancement_text}\n\n"
        f"4k_enhancement_prompt_sha256: {enhancement_sha}\n\n"
        f"assistant_qa_status: {inspection['assistant_qa_status']}\n"
        f"observed_pixel_dimensions: {worker.get('width_px')}x{worker.get('height_px')}\n"
        f"worker_thread_id: {worker.get('worker_thread_id')}\n"
        f"image_generation_call_id: {worker.get('image_generation_call_id')}\n"
        "external_4k_status: handoff_ready\n"
        f"production_approval_status: {production_approval}\n\n"
        "main_result_prompt_pair_status: published\n"
        "task_finalization_status: final_main_result_published"
    )
    payload_bytes = payload.encode("utf-8")
    if args.max_output_bytes is not None and len(payload_bytes) > args.max_output_bytes:
        raise PublicationError(
            "blocked_final_output_capacity",
            f"final payload is {len(payload_bytes)} bytes, above limit {args.max_output_bytes}",
        )
    write_text(output, payload)
    print(
        json.dumps(
            {
                "ok": True,
                "contract": "material_sensitive_final_main_result.v1",
                "attempt_id": attempt_id,
                "output_path": str(output),
                "output_sha256": sha256_bytes(output.read_bytes()),
                "generation_prompt_sha256": generation_sha,
                "4k_enhancement_prompt_sha256": enhancement_sha,
                "image_sha256": board_sha,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PublicationError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}), file=sys.stderr)
        raise SystemExit(2)
    except OSError as exc:
        print(
            json.dumps({"ok": False, "error_code": "blocked_publication_filesystem", "detail": str(exc)}),
            file=sys.stderr,
        )
        raise SystemExit(2)
