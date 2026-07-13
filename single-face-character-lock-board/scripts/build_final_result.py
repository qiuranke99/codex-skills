#!/usr/bin/env python3
"""Build the exact artifact-backed final main-result payload for one accepted board."""

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


def exact_prompt(path: Path) -> tuple[str, str]:
    if not path.is_file():
        raise PublicationError("blocked_prompt_pair_integrity", f"prompt sidecar missing: {path}")
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise PublicationError(
            "blocked_prompt_pair_integrity",
            f"prompt sidecar must be UTF-8/LF without BOM: {path}",
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", required=True, type=Path)
    parser.add_argument("--generation-prompt", required=True, type=Path)
    parser.add_argument("--enhancement-prompt", required=True, type=Path)
    parser.add_argument("--worker-result", required=True, type=Path)
    parser.add_argument("--inspection", required=True, type=Path)
    parser.add_argument("--reference-manifest", required=True, type=Path)
    parser.add_argument("--handoff", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    board = args.board.expanduser().resolve()
    output = args.output.expanduser().resolve()
    run_dir = args.generation_prompt.expanduser().resolve().parent
    for path in [
        board,
        args.enhancement_prompt.expanduser().resolve(),
        args.worker_result.expanduser().resolve(),
        args.inspection.expanduser().resolve(),
        args.reference_manifest.expanduser().resolve(),
        args.handoff.expanduser().resolve(),
        output,
    ]:
        if path.parent != run_dir:
            raise PublicationError(
                "blocked_publication_artifact_location",
                f"publication artifact must live directly in one run directory: {path}",
            )
    if not board.is_file():
        raise PublicationError("blocked_publication_board_missing", f"board missing: {board}")

    generation_text, generation_sha = exact_prompt(args.generation_prompt)
    enhancement_text, enhancement_sha = exact_prompt(args.enhancement_prompt)
    worker, _ = load_json(args.worker_result, "blocked_worker_result_invalid")
    inspection, _ = load_json(args.inspection, "blocked_board_inspection_invalid")
    _, reference_manifest_bytes = load_json(
        args.reference_manifest,
        "blocked_reference_manifest_invalid",
    )
    if not args.handoff.is_file():
        raise PublicationError("blocked_4k_handoff_missing", f"handoff missing: {args.handoff}")
    handoff_text = args.handoff.read_text(encoding="utf-8")
    if not re.search(r'(?m)^\s*aspect_ratio:\s*["\']16:9["\']\s*$', handoff_text) or not re.search(
        r'(?m)^\s*image_size:\s*["\']4K["\']\s*$', handoff_text
    ):
        raise PublicationError(
            "blocked_4k_handoff_invalid",
            "handoff lacks exact 16:9 and 4K controls",
        )

    board_sha = sha256_bytes(board.read_bytes())
    if not all(
        [
            inspection.get("inspected") is True,
            inspection.get("assistant_qa_status") in {"passed", "conditional"},
            inspection.get("image_sha256") == board_sha,
            normalized_path(Path(inspection.get("board_path", ""))) == normalized_path(board),
        ]
    ):
        raise PublicationError(
            "blocked_board_inspection_invalid",
            "inspection record does not bind an accepted visual review to the board",
        )
    required_worker_values = [
        worker.get("ok") is True,
        worker.get("contract") == "delegated_image_worker_result.v3",
        worker.get("binding_mode") == "parent_spawn_cipher_chain_v1",
        isinstance(worker.get("parent_spawn_call_id"), str),
        bool(re.fullmatch(r"[0-9a-f]{64}", str(worker.get("task_delivery_ciphertext_sha256", "")))),
        worker.get("prompt_sha_match") is True,
        worker.get("reference_mode") == "frozen_manifest",
        worker.get("reference_count", 0) > 0,
        worker.get("generation_prompt_sha256") == generation_sha,
        worker.get("tool_prompt_sha256") == generation_sha,
        worker.get("image_sha256") == board_sha,
        worker.get("reference_manifest_sha256") == sha256_bytes(reference_manifest_bytes),
        normalized_path(Path(worker.get("run_image_path", ""))) == normalized_path(board),
    ]
    if not all(required_worker_values):
        raise PublicationError(
            "blocked_publication_provenance_mismatch",
            "worker result does not bind the board, generation prompt, and reference manifest",
        )

    board_target = board.as_posix()
    payload = (
        f"![Single-Face Character Lock Board](<{board_target}>)\n\n"
        f"final_generation_prompt:\n{generation_text}\n\n"
        f"generation_prompt_sha256: {generation_sha}\n\n"
        f"final_4k_enhancement_prompt:\n{enhancement_text}\n\n"
        f"4k_enhancement_prompt_sha256: {enhancement_sha}\n\n"
        "main_result_prompt_pair_status: published\n"
        "task_finalization_status: final_main_result_published"
    )
    write_text(output, payload)
    result = {
        "ok": True,
        "contract": "single_face_final_main_result.v1",
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
