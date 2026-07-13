#!/usr/bin/env python3
"""Cross-platform adversarial tests for the macOS Vision result protocol."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

from macos_vision_adapter import RESULT_SCHEMA, VisionAdapterError, run_macos_vision


INVOCATION = "0123456789abcdef0123456789abcdef"


def envelope(command: list[str], *, mutate: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    result_path = Path(command[command.index("--result-file") + 1])
    invocation = command[command.index("--invocation-id") + 1]
    inputs = command[command.index("--") + 1:]
    value: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA,
        "invocation_id": invocation,
        "input_paths": inputs,
        "observations": [
            {
                "file_path": path,
                "width": 1,
                "height": 1,
                "coordinate_origin": "bottom_left_normalized",
                "text_observations": [],
                "code_observations": [],
            }
            for path in inputs
        ],
    }
    if mutate:
        mutate(value)
    result_path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
        newline="",
    )
    return value


def expect_failure(
    script: Path,
    images: list[Path],
    runner: Callable[..., subprocess.CompletedProcess[bytes]],
    marker: str,
) -> None:
    try:
        run_macos_vision(
            script,
            images,
            ["en-US"],
            runner=runner,
            platform_name="Darwin",
            swift_path="swift-fixture",
            invocation_id_factory=lambda: INVOCATION,
        )
    except VisionAdapterError as exc:
        if marker not in str(exc):
            raise AssertionError(f"failure used the wrong reason: {exc}") from exc
    else:
        raise AssertionError(f"invalid Vision result was accepted: {marker}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="vision-protocol-") as temporary:
        root = Path(temporary)
        script = root / "adapter.swift"
        script.write_text("// fixture\n", encoding="utf-8")
        images = [root / "front.png", root / "back.png"]
        for image in images:
            image.write_bytes(b"fixture")

        def noisy_success(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            envelope(command)
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=b'{"framework":"diagnostic"}\n[]\n',
                stderr=b"Vision framework diagnostic\n",
            )

        observations, _version = run_macos_vision(
            script,
            images,
            ["en-US"],
            runner=noisy_success,
            platform_name="Darwin",
            swift_path="swift-fixture",
            invocation_id_factory=lambda: INVOCATION,
        )
        if [item["file_path"] for item in observations] != [str(path.resolve()) for path in images]:
            raise AssertionError("diagnostic stdout changed the result-file authority")

        def trailing_document(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            envelope(command)
            output = Path(command[command.index("--result-file") + 1])
            output.write_bytes(output.read_bytes() + b"\n{}")
            return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

        expect_failure(script, images, trailing_document, "not one strict UTF-8 JSON object")

        def missing_result(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

        expect_failure(script, images, missing_result, "did not create one regular result file")

        def invalid_utf8(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            output = Path(command[command.index("--result-file") + 1])
            output.write_bytes(b"\xff\xfe")
            return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

        expect_failure(script, images, invalid_utf8, "not one strict UTF-8 JSON object")

        def wrong_nonce(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            envelope(command, mutate=lambda value: value.update(invocation_id="f" * 32))
            return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

        expect_failure(script, images, wrong_nonce, "invocation id differs")

        def wrong_order(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            envelope(command, mutate=lambda value: value.update(input_paths=list(reversed(value["input_paths"]))))
            return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

        expect_failure(script, images, wrong_order, "input path order differs")

        def nonzero_with_valid_result(
            command: list[str], **_kwargs: Any
        ) -> subprocess.CompletedProcess[bytes]:
            envelope(command)
            return subprocess.CompletedProcess(command, 9, stdout=b"noise", stderr=b"failure")

        expect_failure(script, images, nonzero_with_valid_result, "exit=9")

    print("OK: macOS Vision result-file protocol rejected authority confusion")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
