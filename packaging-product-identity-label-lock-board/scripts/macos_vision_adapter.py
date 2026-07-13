#!/usr/bin/env python3
"""Strict result-file transport for the bundled macOS Vision adapter."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Sequence


RESULT_SCHEMA = "packaging-macos-vision-result.v1"
INVOCATION_ID = re.compile(r"^[a-f0-9]{32}$")
MAX_RESULT_BYTES = 32 * 1024 * 1024


class VisionAdapterError(RuntimeError):
    """The Vision process did not return one strictly bound result file."""


def _strict_object(data: bytes, label: str) -> dict[str, Any]:
    try:
        text = data.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise VisionAdapterError(f"{label} is not one strict UTF-8 JSON object: {exc}") from exc
    if not isinstance(value, dict):
        raise VisionAdapterError(f"{label} root must be an object")
    return value


def _diagnostic_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def run_macos_vision(
    script: Path,
    paths: Sequence[Path],
    languages: Sequence[str],
    *,
    timeout: float = 120,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
    platform_name: str | None = None,
    swift_path: str | None = None,
    invocation_id_factory: Callable[[], str] = lambda: secrets.token_hex(16),
) -> tuple[list[dict[str, Any]], str]:
    """Run Vision with a unique atomic result file; stdout is diagnostic only."""
    observed_platform = platform_name or platform.system()
    swift = swift_path or shutil.which("swift")
    if observed_platform != "Darwin" or not swift or not script.is_file():
        raise VisionAdapterError("blocked_ocr_capability: bundled macOS Vision OCR adapter is unavailable")
    if not paths:
        raise VisionAdapterError("Vision input list must not be empty")

    canonical_paths: list[Path] = []
    for path in paths:
        candidate = path.resolve(strict=False)
        if not candidate.is_file():
            raise VisionAdapterError(f"Vision input is missing or not a regular file: {path}")
        canonical_paths.append(candidate)
    expected_paths = [str(path) for path in canonical_paths]

    invocation_id = invocation_id_factory()
    if not isinstance(invocation_id, str) or INVOCATION_ID.fullmatch(invocation_id) is None:
        raise VisionAdapterError("Vision invocation id must be 32 lowercase hexadecimal characters")

    with tempfile.TemporaryDirectory(prefix="packaging-vision-result-") as temporary:
        result_path = Path(temporary) / "result.json"
        if result_path.exists():
            raise VisionAdapterError("Vision result path was not fresh")
        environment = dict(os.environ)
        environment["PACKAGING_OCR_LANGUAGES"] = ",".join(languages)
        command = [
            swift,
            str(script),
            "--result-file",
            str(result_path),
            "--invocation-id",
            invocation_id,
            "--",
            *expected_paths,
        ]
        try:
            result = runner(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
                timeout=timeout,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise VisionAdapterError(f"bundled macOS Vision OCR could not run: {exc}") from exc
        stdout = result.stdout if isinstance(result.stdout, bytes) else str(result.stdout or "").encode("utf-8")
        stderr = result.stderr if isinstance(result.stderr, bytes) else str(result.stderr or "").encode("utf-8")
        if result.returncode != 0:
            raise VisionAdapterError(
                "bundled macOS Vision OCR failed "
                f"(exit={result.returncode}, stdout_bytes={len(stdout)}, stdout_sha256={_diagnostic_digest(stdout)}, "
                f"stderr_bytes={len(stderr)}, stderr_sha256={_diagnostic_digest(stderr)})"
            )
        if result_path.is_symlink() or not result_path.is_file():
            raise VisionAdapterError("bundled macOS Vision OCR did not create one regular result file")
        size = result_path.stat().st_size
        if size < 2 or size > MAX_RESULT_BYTES:
            raise VisionAdapterError(f"bundled macOS Vision OCR result size is invalid: {size}")
        payload = _strict_object(result_path.read_bytes(), "bundled macOS Vision OCR result")

    if payload.get("schema_version") != RESULT_SCHEMA:
        raise VisionAdapterError("bundled macOS Vision OCR result schema differs")
    if payload.get("invocation_id") != invocation_id:
        raise VisionAdapterError("bundled macOS Vision OCR result invocation id differs")
    if payload.get("input_paths") != expected_paths:
        raise VisionAdapterError("bundled macOS Vision OCR input path order differs")
    observations = payload.get("observations")
    if not isinstance(observations, list) or len(observations) != len(expected_paths):
        raise VisionAdapterError("bundled macOS Vision OCR result count differs")
    if not all(isinstance(item, dict) for item in observations):
        raise VisionAdapterError("bundled macOS Vision OCR returned a malformed observation")
    observed_paths = [item.get("file_path") for item in observations]
    if observed_paths != expected_paths:
        raise VisionAdapterError("bundled macOS Vision OCR observation path order differs")
    return observations, platform.mac_ver()[0] or "unknown-macos"
