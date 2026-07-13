#!/usr/bin/env python3
"""Freeze one prompt as canonical image-tool transport bytes.

The image-tool prompt is a JSON string. Canonical sidecars therefore use
UTF-8 without BOM, LF for internal line breaks, and no terminal line break.
The emitted hash is calculated only after the output is reopened.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def canonicalize(raw: bytes) -> bytes:
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.rstrip("\n")
    if not text:
        raise ValueError("prompt must contain non-newline UTF-8 text")
    return text.encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--result-json", type=Path)
    args = parser.parse_args()

    frozen = canonicalize(args.input.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(frozen)
    reread = args.output.read_bytes()
    if reread != frozen:
        raise RuntimeError("frozen prompt reread mismatch")

    result = {
        "schema": "multi_angle_frozen_prompt.v1",
        "path": str(args.output.resolve()),
        "size_bytes": len(reread),
        "sha256": hashlib.sha256(reread).hexdigest(),
        "utf8_without_bom": True,
        "internal_line_endings": "LF",
        "terminal_line_break": False,
    }
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.result_json:
        args.result_json.parent.mkdir(parents=True, exist_ok=True)
        args.result_json.write_text(serialized, encoding="utf-8", newline="\n")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
