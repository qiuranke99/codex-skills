#!/usr/bin/env python3
"""Build one exact artifact-backed final result for the accepted product-board attempt."""

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


def require_inside(run_dir: Path, path: Path) -> Path:
    resolved = path.expanduser().resolve()
    try:
        common = os.path.commonpath([normalized_path(run_dir), normalized_path(resolved)])
    except ValueError as exc:
        raise PublicationError("blocked_publication_artifact_location", str(exc)) from exc
    if common != normalized_path(run_dir):
        raise PublicationError(
            "blocked_publication_artifact_location",
            f"publication artifact is outside the run directory: {resolved}",
        )
    return resolved


def exact_prompt(path: Path) -> tuple[str, str]:
    if not path.is_file():
        raise PublicationError("blocked_prompt_pair_integrity", f"prompt sidecar missing: {path}")
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf") or b"\r" in data or data.endswith(b"\n"):
        raise PublicationError(
            "blocked_prompt_pair_integrity",
            f"prompt sidecar must be UTF-8 without BOM, use LF internally, and have no terminal line break: {path}",
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
        raise PublicationError(code, f"JSON artifact must be UTF-8/LF without BOM: {path}")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicationError(code, str(exc)) from exc
    if not isinstance(value, dict):
        raise PublicationError(code, f"JSON artifact is not an object: {path}")
    return value, data


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def same_path(left: Any, right: Path) -> bool:
    return isinstance(left, str) and normalized_path(Path(left)) == normalized_path(right)


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
    if accepted.get("schema_version") != "multi_angle_accepted_attempt.v1":
        raise PublicationError("blocked_accepted_attempt_invalid", "unexpected accepted-attempt schema")
    attempt_id = accepted.get("attempt_id")
    if not isinstance(attempt_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", attempt_id):
        raise PublicationError("blocked_accepted_attempt_invalid", "invalid accepted attempt ID")

    accepted_paths = {
        "generation_prompt_path": generation_path,
        "board_path": board,
        "worker_result_path": worker_path,
        "inspection_path": inspection_path,
    }
    for field, expected_path in accepted_paths.items():
        if not same_path(accepted.get(field), expected_path):
            raise PublicationError(
                "blocked_accepted_attempt_mismatch",
                f"accepted attempt {field} does not match publication input",
            )

    generation_text, generation_sha = exact_prompt(generation_path)
    enhancement_text, enhancement_sha = exact_prompt(enhancement_path)
    if not board.is_file():
        raise PublicationError("blocked_publication_board_missing", f"board missing: {board}")
    board_sha = sha256_bytes(board.read_bytes())
    if accepted.get("generation_prompt_sha256") != generation_sha or accepted.get("image_sha256") != board_sha:
        raise PublicationError(
            "blocked_accepted_attempt_mismatch",
            "accepted attempt hashes do not match generation prompt and board",
        )

    worker, _ = load_json(worker_path, "blocked_worker_result_invalid")
    inspection, _ = load_json(inspection_path, "blocked_board_inspection_invalid")
    reference_manifest, reference_manifest_bytes = load_json(
        manifest_path,
        "blocked_reference_manifest_invalid",
    )
    if reference_manifest.get("schema_version") != "multi_angle_reference_bundle.v1":
        raise PublicationError("blocked_reference_manifest_invalid", "unexpected reference schema")

    if not all(
        [
            inspection.get("inspected") is True,
            inspection.get("assistant_qa_status") in {"passed", "conditional"},
            inspection.get("image_sha256") == board_sha,
            same_path(inspection.get("board_path"), board),
            inspection.get("attempt_id") == attempt_id,
        ]
    ):
        raise PublicationError(
            "blocked_board_inspection_invalid",
            "inspection record does not bind an accepted visual review to the board",
        )

    if not all(
        [
            worker.get("ok") is True,
            worker.get("prompt_sha_match") is True,
            worker.get("reference_mode") == "frozen_manifest",
            worker.get("reference_count", 0) > 0,
            worker.get("generation_prompt_sha256") == generation_sha,
            worker.get("tool_prompt_sha256") == generation_sha,
            worker.get("image_sha256") == board_sha,
            worker.get("reference_manifest_sha256") == sha256_bytes(reference_manifest_bytes),
            same_path(worker.get("run_image_path"), board),
        ]
    ):
        raise PublicationError(
            "blocked_publication_provenance_mismatch",
            "worker result does not bind board, prompt, and reference manifest",
        )

    if not handoff_path.is_file():
        raise PublicationError("blocked_4k_handoff_missing", f"handoff missing: {handoff_path}")
    handoff_text = handoff_path.read_text(encoding="utf-8")
    if not re.search(r'(?m)^\s*aspect_ratio:\s*["\']16:9["\']\s*$', handoff_text) or not re.search(
        r'(?m)^\s*image_size:\s*["\']4K["\']\s*$', handoff_text
    ):
        raise PublicationError(
            "blocked_4k_handoff_invalid",
            "handoff lacks exact 16:9 and 4K controls",
        )

    payload = (
        f"![Multi-Angle Product Identity Lock Board](<{board.as_posix()}>)\n\n"
        f"final_generation_prompt:\n{generation_text}\n\n"
        f"generation_prompt_sha256: {generation_sha}\n\n"
        f"final_4k_enhancement_prompt:\n{enhancement_text}\n\n"
        f"4k_enhancement_prompt_sha256: {enhancement_sha}\n\n"
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
    result = {
        "ok": True,
        "contract": "multi_angle_final_main_result.v1",
        "attempt_id": attempt_id,
        "output_path": str(output),
        "output_sha256": sha256_bytes(output.read_bytes()),
        "generation_prompt_sha256": generation_sha,
        "4k_enhancement_prompt_sha256": enhancement_sha,
        "image_sha256": board_sha,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
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
