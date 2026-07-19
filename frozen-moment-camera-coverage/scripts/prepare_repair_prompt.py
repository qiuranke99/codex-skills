#!/usr/bin/env python3
"""Freeze one attempt-scoped repair prompt without mutating the base coverage contract."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import resolve_worker_image as resolver
from validate_coverage_package import (
    ContractError,
    read_json,
    reject_prompt_control_text,
    resolve_artifact,
    sha256_file,
    validate_package,
)


def write_bytes_atomic(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(value)
        os.replace(temporary, path)
    finally:
        if temporary.exists() and not temporary.is_symlink():
            temporary.unlink()


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    write_bytes_atomic(
        path,
        (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )


def relative_artifact(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError as exc:
        raise ContractError("blocked_repair_prompt_invalid", f"artifact escapes run root: {path}") from exc


def repair_prompt_text(
    *,
    parent_prompt: str,
    view_id: str,
    attempt_id: str,
    previous_attempt_id: str,
    failure_codes: list[str],
    repair_scope: list[str],
    deviations: list[str],
) -> str:
    lines = [
        parent_prompt.rstrip(),
        "",
        f"【版本化修复尝试：{view_id} / {attempt_id}】",
        f"上一绑定尝试 {previous_attempt_id} 未通过主代理实图检查。本段只收窄该机位的失败项；此前提示词及所有已通过冻结项继续具有完整约束力。",
        "",
        "必须原样保留：人物身份与可见年龄、骨架姿态、身体根位置、头部方向、视线、表情、双手与环境接触、服装与不对称细节、场景拓扑、动作时相、世界空间光源、色彩与胶片质感。不得用人物移动、转身、重新表演、镜像、裁切或后期变焦来替代相机合同。",
        "",
        "只修复以下已验证失败：",
    ]
    lines.extend(f"- [{code}]" for code in failure_codes)
    lines.extend(["", "修复范围："])
    lines.extend(f"- {item}" for item in repair_scope)
    if deviations:
        lines.extend(["", "上一尝试的可观察偏差（不得复现）："])
        lines.extend(f"- {item}" for item in deviations)
    lines.extend(
        [
            "",
            "修复优先级：先满足源证据、Frozen Moment Canon、该机位 Camera Contract 与可见性合同，再保持原始审美；若两者冲突，不得牺牲冻结事实换取更完整或更漂亮的画面。",
            "输出仍是一张独立完整电影静帧；不要输出解释、文字、网格、对比板或多个候选。",
            "",
        ]
    )
    return "\n".join(lines)


def prepare_repair(
    run_root: Path,
    *,
    view_id: str,
    attempt_id: str,
    attempt_revision: int,
) -> dict[str, Any]:
    root = run_root.resolve()
    validate_package(root, "state")
    manifest_path = root / "00_manifest" / "COVERAGE_MANIFEST.json"
    manifest = read_json(manifest_path, "blocked_repair_prompt_invalid")
    view_id = view_id.upper()
    if not re.fullmatch(r"V[A-Z0-9_-]{1,31}", view_id):
        raise ContractError("blocked_repair_prompt_invalid", "view id is invalid")
    expected_attempt_id = f"{view_id}_A{attempt_revision:02d}"
    if attempt_id != expected_attempt_id:
        raise ContractError(
            "blocked_repair_prompt_invalid",
            f"attempt id must bind its immutable revision: {expected_attempt_id}",
        )
    maximum = manifest.get("job", {}).get("max_attempts_per_view")
    if not isinstance(maximum, int) or not 2 <= attempt_revision <= maximum:
        raise ContractError("blocked_attempt_budget", "repair revision is outside the frozen attempt budget")
    view = next((item for item in manifest.get("views", []) if item.get("view_id") == view_id), None)
    base_prompt_record = next((item for item in manifest.get("prompts", []) if item.get("view_id") == view_id), None)
    if not isinstance(view, dict) or not isinstance(base_prompt_record, dict):
        raise ContractError("blocked_repair_prompt_invalid", "repair view or base prompt does not exist")
    prior_attempts = [
        item for item in manifest.get("attempts", [])
        if isinstance(item, dict) and item.get("view_id") == view_id
        and isinstance(item.get("attempt_revision"), int) and item["attempt_revision"] < attempt_revision
    ]
    if not prior_attempts:
        raise ContractError("blocked_repair_prompt_invalid", "repair requires a prior bound and inspected attempt")
    previous = max(prior_attempts, key=lambda item: item["attempt_revision"])
    if (
        previous.get("attempt_revision") != attempt_revision - 1
        or previous.get("decision") not in {"rejected", "repair_required"}
        or view.get("status") != "repair_required"
        or manifest.get("state", {}).get("current") != "repair_required"
    ):
        raise ContractError("blocked_repair_prompt_invalid", "run is not at the immediately preceding repair gate")
    if any(
        item.get("view_id") == view_id and item.get("attempt_revision") >= attempt_revision
        for item in manifest.get("attempts", []) if isinstance(item, dict)
    ):
        raise ContractError("blocked_repair_prompt_invalid", "repair revision is already bound or superseded")
    inspection_path = resolve_artifact(root, previous.get("inspection_path"), "blocked_repair_prompt_invalid")
    if sha256_file(inspection_path) != previous.get("inspection_sha256"):
        raise ContractError("blocked_repair_prompt_invalid", "previous inspection changed")
    inspection = read_json(inspection_path, "blocked_repair_prompt_invalid")
    failure_codes = inspection.get("failure_codes")
    repair_scope = inspection.get("repair_scope")
    deviations = inspection.get("observed_deviations", [])
    if (
        inspection.get("decision") not in {"rejected", "repair_required"}
        or not isinstance(failure_codes, list) or not failure_codes
        or not all(isinstance(item, str) and item.strip() for item in failure_codes)
        or not isinstance(repair_scope, list) or not repair_scope
        or not all(isinstance(item, str) and item.strip() for item in repair_scope)
        or not isinstance(deviations, list)
        or not all(isinstance(item, str) and item.strip() for item in deviations)
    ):
        raise ContractError("blocked_repair_prompt_invalid", "previous inspection lacks bounded repair evidence")
    reject_prompt_control_text(
        {"repair_scope": repair_scope, "observed_deviations": deviations},
        "repair_publication",
    )
    previous_worker_path = resolve_artifact(
        root, previous.get("worker_result_path"), "blocked_repair_prompt_invalid"
    )
    if sha256_file(previous_worker_path) != previous.get("worker_result_sha256"):
        raise ContractError("blocked_repair_prompt_invalid", "previous worker result changed")
    previous_worker = read_json(previous_worker_path, "blocked_repair_prompt_invalid")
    try:
        inspection_ms = int(
            datetime.fromisoformat(str(inspection.get("inspected_at_utc", "")).replace("Z", "+00:00")).timestamp()
            * 1000
        )
    except (ValueError, TypeError) as exc:
        raise ContractError("blocked_repair_prompt_invalid", "previous inspection timestamp is invalid") from exc
    completion_ms = previous_worker.get("parent_completion_activity_ms")
    if not isinstance(completion_ms, int) or isinstance(completion_ms, bool) or completion_ms <= 0:
        raise ContractError("blocked_repair_prompt_invalid", "previous worker completion timestamp is invalid")
    publication_ms = max(int(time.time() * 1000), completion_ms, inspection_ms)
    parent_prompt_path = resolve_artifact(root, previous.get("prompt_path"), "blocked_repair_prompt_invalid")
    base_prompt_path = resolve_artifact(root, base_prompt_record.get("prompt_path"), "blocked_repair_prompt_invalid")
    if (
        sha256_file(parent_prompt_path) != previous.get("prompt_sha256")
        or sha256_file(base_prompt_path) != base_prompt_record.get("prompt_sha256")
    ):
        raise ContractError("blocked_repair_prompt_invalid", "parent or base prompt changed")
    try:
        parent_text = parent_prompt_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError("blocked_repair_prompt_invalid", f"parent prompt is not UTF-8: {exc}") from exc
    prompt_text = repair_prompt_text(
        parent_prompt=parent_text,
        view_id=view_id,
        attempt_id=attempt_id,
        previous_attempt_id=previous["attempt_id"],
        failure_codes=failure_codes,
        repair_scope=repair_scope,
        deviations=deviations,
    )
    prompt_path = root / "00_manifest" / "repair-prompts" / view_id / f"{attempt_id}.zh.txt"
    receipt_path = root / "00_manifest" / "repair-prompts" / view_id / f"{attempt_id}.publication.json"
    if prompt_path.exists() or receipt_path.exists():
        if not prompt_path.is_file() or not receipt_path.is_file() or prompt_path.is_symlink() or receipt_path.is_symlink():
            raise ContractError("blocked_repair_prompt_invalid", "repair publication destination is incomplete or linked")
        if prompt_path.read_text(encoding="utf-8") != prompt_text:
            raise ContractError("blocked_repair_prompt_invalid", "existing repair prompt conflicts with deterministic bytes")
        authority = resolver.load_repair_publication(
            run_root=root,
            manifest=manifest,
            publication_path=receipt_path.resolve(),
            expected_prompt=prompt_path.resolve(),
            view_id=view_id,
            attempt_id=attempt_id,
            attempt_revision=attempt_revision,
        )
        return {
            "prompt_path": str(prompt_path.resolve()),
            "prompt_sha256": authority["prompt_sha256"],
            "publication_path": str(receipt_path.resolve()),
            "publication_sha256": authority["publication_sha256"],
            "published_at_unix_ms": authority["published_at_unix_ms"],
            "idempotent": True,
        }
    receipt = {
        "schema_version": "frozen_moment_repair_prompt_publication.v1",
        "publication_status": "repair_prompt_frozen",
        "published_at_utc": datetime.fromtimestamp(publication_ms / 1000, tz=timezone.utc).isoformat(),
        "published_at_unix_ms": publication_ms,
        "run_id": manifest["job"]["job_id"],
        "view_id": view_id,
        "attempt_id": attempt_id,
        "attempt_revision": attempt_revision,
        "previous_attempt_id": previous["attempt_id"],
        "previous_attempt_revision": previous["attempt_revision"],
        "previous_image_sha256": previous["image_sha256"],
        "previous_inspection_path": previous["inspection_path"],
        "previous_inspection_sha256": previous["inspection_sha256"],
        "base_prompt_path": base_prompt_record["prompt_path"],
        "base_prompt_sha256": base_prompt_record["prompt_sha256"],
        "parent_prompt_path": previous["prompt_path"],
        "parent_prompt_sha256": previous["prompt_sha256"],
        "repair_prompt_path": relative_artifact(root, prompt_path),
        "repair_prompt_sha256": "",
        "coverage_contract_sha256": manifest["coverage_contract_sha256"],
        "source_evidence_sha256": manifest["source_evidence"]["source_evidence_sha256"],
        "moment_canon_sha256": manifest["moment_canon"]["moment_canon_sha256"],
        "camera_contract_sha256": view["camera_contract_sha256"],
        "reference_plan_sha256": base_prompt_record["reference_plan_sha256"],
        "failure_codes": failure_codes,
        "repair_scope": repair_scope,
    }
    try:
        write_bytes_atomic(prompt_path, prompt_text.encode("utf-8"))
        receipt["repair_prompt_sha256"] = sha256_file(prompt_path)
        write_json_atomic(receipt_path, receipt)
        authority = resolver.load_repair_publication(
            run_root=root,
            manifest=manifest,
            publication_path=receipt_path.resolve(),
            expected_prompt=prompt_path.resolve(),
            view_id=view_id,
            attempt_id=attempt_id,
            attempt_revision=attempt_revision,
        )
    except Exception:
        for created in (receipt_path, prompt_path):
            if created.exists() and not created.is_symlink() and created.is_file():
                created.unlink()
        raise
    return {
        "prompt_path": str(prompt_path.resolve()),
        "prompt_sha256": authority["prompt_sha256"],
        "publication_path": str(receipt_path.resolve()),
        "publication_sha256": authority["publication_sha256"],
        "published_at_unix_ms": authority["published_at_unix_ms"],
        "idempotent": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--view-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--attempt-revision", required=True, type=int)
    args = parser.parse_args()
    try:
        result = prepare_repair(
            args.run_root,
            view_id=args.view_id,
            attempt_id=args.attempt_id,
            attempt_revision=args.attempt_revision,
        )
    except (ContractError, resolver.ContractError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        code = exc.code if hasattr(exc, "code") else "blocked_repair_prompt_invalid"
        print(json.dumps({"ok": False, "error_code": code, "detail": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
