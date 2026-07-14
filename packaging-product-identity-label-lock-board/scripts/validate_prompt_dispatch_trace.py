#!/usr/bin/env python3
"""Validate the prompt-first, thin-worker dispatch timeline for one packaging run."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


RELEASE_GATE_LIMIT_MS = 60_000
PROMPT_TOTAL_LIMIT_MS = 180_000
PROMPT_AFTER_GATE_LIMIT_MS = 120_000
WORKER_SPAWN_LIMIT_MS = 30_000
WORKER_SUBMIT_LIMIT_MS = 90_000
IMAGEGEN_WAIT_LIMIT_MS = 900_000
RAW_PREVIEW_LIMIT_MS = 60_000
TOTAL_AUTOMATIC_LIMIT_MS = 1_200_000
UPDATE_GAP_LIMIT_MS = 60_000

TERMINAL_STATUSES = {
    "ACCEPTED",
    "BLOCKED_RELEASE_GATE",
    "BLOCKED_REFERENCE_MATERIALIZATION",
    "BLOCKED_PROMPT_READY_TIMEOUT",
    "BLOCKED_WORKER_START_TIMEOUT",
    "BLOCKED_WORKER_SUBMIT_TIMEOUT",
    "BLOCKED_IMAGEGEN_TIMEOUT",
    "BLOCKED_VALIDATION",
    "REJECTED_AFTER_MAX_ATTEMPTS",
}
WORKER_STATUSES = {
    "ACCEPTED",
    "BLOCKED_WORKER_SUBMIT_TIMEOUT",
    "BLOCKED_IMAGEGEN_TIMEOUT",
    "BLOCKED_VALIDATION",
    "REJECTED_AFTER_MAX_ATTEMPTS",
}
SUBMITTED_STATUSES = {
    "ACCEPTED",
    "BLOCKED_IMAGEGEN_TIMEOUT",
    "BLOCKED_VALIDATION",
    "REJECTED_AFTER_MAX_ATTEMPTS",
}


class TraceError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TraceError("blocked_dispatch_trace_json", f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise TraceError("blocked_dispatch_trace_json", "dispatch trace must be one JSON object")
    return value


def integer(value: Any, field: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise TraceError("blocked_dispatch_trace_field", f"{field} must be a non-negative integer")
    return value


def path_with_hash(trace: dict[str, Any], path_field: str, sha_field: str) -> Path:
    path = Path(str(trace.get(path_field, ""))).expanduser().resolve()
    if not path.is_file():
        raise TraceError("blocked_dispatch_artifact_missing", f"missing artifact for {path_field}: {path}")
    if sha256(path) != trace.get(sha_field):
        raise TraceError("blocked_dispatch_artifact_hash", f"hash mismatch for {path_field}: {path}")
    return path


def validate_update_cadence(trace: dict[str, Any], start: int, end: int) -> None:
    updates = trace.get("user_visible_update_elapsed_ms")
    if not isinstance(updates, list) or not updates:
        raise TraceError("blocked_dispatch_update_cadence", "user-visible update timeline is required")
    values = [integer(value, "user_visible_update_elapsed_ms") for value in updates]
    if values != sorted(set(values)):
        raise TraceError("blocked_dispatch_update_cadence", "user-visible update times must be unique and ordered")
    bounded = [value for value in values if start <= value <= end]
    if not bounded or bounded[0] != start or bounded[-1] != end:
        raise TraceError("blocked_dispatch_update_cadence", "updates must include prompt publication and terminal time")
    if any(right - left > UPDATE_GAP_LIMIT_MS for left, right in zip(bounded, bounded[1:])):
        raise TraceError("blocked_dispatch_update_cadence", "user-visible status gap exceeded 60 seconds")


def validate(trace: dict[str, Any]) -> dict[str, Any]:
    if trace.get("schema_version") != "packaging_prompt_dispatch_trace.v1":
        raise TraceError("blocked_dispatch_trace_schema", "unsupported prompt dispatch trace schema")
    terminal_status = trace.get("terminal_status")
    if terminal_status not in TERMINAL_STATUSES:
        raise TraceError("blocked_dispatch_terminal_status", f"unsupported terminal status: {terminal_status!r}")
    release_elapsed = integer(trace.get("release_gate_completed_elapsed_ms"), "release_gate_completed_elapsed_ms")
    if release_elapsed > RELEASE_GATE_LIMIT_MS:
        raise TraceError("blocked_release_gate_timeout", "release gate exceeded 60 seconds")
    prompt_path = path_with_hash(trace, "generation_prompt_path", "generation_prompt_sha256")
    prompt_publication = trace.get("prompt_publication")
    if not isinstance(prompt_publication, dict) or prompt_publication.get("mode") != "inline_complete_prompt":
        raise TraceError("blocked_prompt_not_inline", "the complete prompt must be published inline")
    prompt_elapsed = integer(prompt_publication.get("elapsed_ms"), "prompt_publication.elapsed_ms")
    if prompt_publication.get("published_sha256") != sha256(prompt_path):
        raise TraceError("blocked_prompt_publication_hash", "published prompt bytes do not match the frozen prompt")
    if prompt_elapsed > PROMPT_TOTAL_LIMIT_MS or prompt_elapsed - release_elapsed > PROMPT_AFTER_GATE_LIMIT_MS:
        raise TraceError("blocked_prompt_ready_timeout", "complete prompt missed its publication deadline")
    terminal_elapsed = integer(trace.get("terminal_elapsed_ms"), "terminal_elapsed_ms")
    if terminal_elapsed < prompt_elapsed:
        raise TraceError("blocked_dispatch_event_order", "terminal time precedes prompt publication")
    terminal_publication = trace.get("terminal_prompt_publication")
    if not isinstance(terminal_publication, dict) or terminal_publication.get("mode") != "inline_complete_prompt":
        raise TraceError("blocked_terminal_prompt_missing", "terminal result must repeat the complete prompt inline")
    if terminal_publication.get("published_sha256") != sha256(prompt_path):
        raise TraceError("blocked_terminal_prompt_hash", "terminal prompt bytes do not match the frozen prompt")

    provider_count = None
    if terminal_status != "BLOCKED_RELEASE_GATE" and terminal_status != "BLOCKED_REFERENCE_MATERIALIZATION":
        pack_path = path_with_hash(trace, "generation_reference_pack_path", "generation_reference_pack_sha256")
        pack = read_json(pack_path)
        if pack.get("schema_version") != "packaging_generation_reference_pack.v1":
            raise TraceError("blocked_generation_reference_manifest", "unsupported provider reference pack schema")
        provider_count = integer(pack.get("provider_reference_count"), "provider_reference_count")
        references = pack.get("provider_references")
        if not 1 <= provider_count <= 5 or not isinstance(references, list) or len(references) != provider_count:
            raise TraceError("blocked_generation_reference_count", "imagegen provider pack must contain one to five references")

    worker = trace.get("worker")
    if terminal_status in WORKER_STATUSES:
        if not isinstance(worker, dict):
            raise TraceError("blocked_worker_trace_missing", "worker dispatch evidence is required")
        worker_spawned = integer(worker.get("spawned_elapsed_ms"), "worker.spawned_elapsed_ms")
        if worker_spawned < prompt_elapsed or worker_spawned - prompt_elapsed > WORKER_SPAWN_LIMIT_MS:
            raise TraceError("blocked_worker_start_timeout", "thin worker was not spawned within 30 seconds after prompt publication")
        if worker.get("fork_turns") != "none" or worker.get("task_mentions_skill") is not False:
            raise TraceError("blocked_worker_context", "worker must use fork_turns=none and must not retrigger the Skill")
        if worker.get("first_tool") != "imagegen" or worker.get("pre_imagegen_tool_call_count") != 0:
            raise TraceError("blocked_worker_first_tool", "worker first tool must be imagegen with no preceding tool call")
        if worker.get("reran_release_gate") is not False:
            raise TraceError("blocked_worker_release_gate_repeat", "worker must not rerun the parent release gate")
        if terminal_status in SUBMITTED_STATUSES:
            submitted = integer(worker.get("imagegen_submitted_elapsed_ms"), "worker.imagegen_submitted_elapsed_ms")
            if submitted < worker_spawned or submitted - worker_spawned > WORKER_SUBMIT_LIMIT_MS:
                raise TraceError("blocked_worker_submit_timeout", "imagegen submission missed the 90-second worker deadline")
            if worker.get("imagegen_tool_call_count") != 1:
                raise TraceError("blocked_worker_image_call_count", "worker must make exactly one imagegen tool call")
            if worker.get("imagegen_reference_count") != provider_count:
                raise TraceError("blocked_generation_reference_count", "imagegen reference count differs from provider pack")
            if worker.get("imagegen_reference_count", 0) > 5:
                raise TraceError("blocked_generation_reference_count", "imagegen received more than five references")
        else:
            if worker.get("imagegen_tool_call_count") not in {0, None}:
                raise TraceError("blocked_worker_submit_state", "unsubmitted worker cannot claim an imagegen call")

    if terminal_status == "ACCEPTED":
        assert isinstance(worker, dict)
        submitted = integer(worker.get("imagegen_submitted_elapsed_ms"), "worker.imagegen_submitted_elapsed_ms")
        image_ready = integer(worker.get("image_ready_elapsed_ms"), "worker.image_ready_elapsed_ms")
        raw_preview = integer(worker.get("raw_preview_published_elapsed_ms"), "worker.raw_preview_published_elapsed_ms")
        if not submitted <= image_ready <= submitted + IMAGEGEN_WAIT_LIMIT_MS:
            raise TraceError("blocked_imagegen_timeout", "image generation exceeded the 15-minute wait budget")
        if not image_ready <= raw_preview <= image_ready + RAW_PREVIEW_LIMIT_MS:
            raise TraceError("blocked_raw_preview_timeout", "raw preview was not shown within 60 seconds")
        if worker.get("image_generation_end_count") != 1 or worker.get("bound_png") is not True:
            raise TraceError("blocked_success_without_image", "accepted status requires one image end event and a bound PNG")
        success_claimed = integer(worker.get("success_claimed_elapsed_ms"), "worker.success_claimed_elapsed_ms")
        if success_claimed < image_ready or success_claimed > terminal_elapsed:
            raise TraceError("blocked_premature_success_claim", "success was claimed before the image existed")
    elif terminal_status == "BLOCKED_IMAGEGEN_TIMEOUT":
        assert isinstance(worker, dict)
        submitted = integer(worker.get("imagegen_submitted_elapsed_ms"), "worker.imagegen_submitted_elapsed_ms")
        if terminal_elapsed - submitted > IMAGEGEN_WAIT_LIMIT_MS + UPDATE_GAP_LIMIT_MS:
            raise TraceError("blocked_imagegen_timeout_state", "imagegen timeout was not terminated promptly")
        if worker.get("retry_started_while_call_unknown") is not False:
            raise TraceError("blocked_orphan_retry", "do not retry while the first image call state is unknown")

    automatic_elapsed = integer(trace.get("automatic_generation_elapsed_ms"), "automatic_generation_elapsed_ms")
    if automatic_elapsed > TOTAL_AUTOMATIC_LIMIT_MS:
        raise TraceError("blocked_total_generation_budget", "automatic generation work exceeded 20 minutes")
    validate_update_cadence(trace, prompt_elapsed, terminal_elapsed)
    return {
        "ok": True,
        "terminal_status": terminal_status,
        "prompt_sha256": sha256(prompt_path),
        "provider_reference_count": provider_count,
        "prompt_published_elapsed_ms": prompt_elapsed,
        "terminal_elapsed_ms": terminal_elapsed,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = validate(read_json(args.trace.expanduser().resolve()))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TraceError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}), file=sys.stderr)
        raise SystemExit(2)
    except OSError as exc:
        print(json.dumps({"ok": False, "error_code": "blocked_dispatch_filesystem", "detail": str(exc)}), file=sys.stderr)
        raise SystemExit(2)
