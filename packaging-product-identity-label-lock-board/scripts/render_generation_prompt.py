#!/usr/bin/env python3
"""Render the packaging generation template with a complete copy block and no placeholders."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


PLACEHOLDER_RE = re.compile(r"\{\{([a-z0-9_]+)\}\}")


class RenderError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_text(path: Path, code: str) -> tuple[str, bytes]:
    if not path.is_file():
        raise RenderError(code, f"missing input: {path}")
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise RenderError(code, f"input must be UTF-8/LF without BOM: {path}")
    try:
        return data.decode("utf-8"), data
    except UnicodeDecodeError as exc:
        raise RenderError(code, str(exc)) from exc


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--values", required=True, type=Path)
    parser.add_argument("--copy-block", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()

    template, template_bytes = read_text(args.template.expanduser().resolve(), "blocked_prompt_template_invalid")
    copy_block, copy_block_bytes = read_text(args.copy_block.expanduser().resolve(), "blocked_copy_block_missing")
    values_text, values_bytes = read_text(args.values.expanduser().resolve(), "blocked_prompt_values_invalid")
    try:
        values = json.loads(values_text)
    except json.JSONDecodeError as exc:
        raise RenderError("blocked_prompt_values_invalid", str(exc)) from exc
    if not isinstance(values, dict):
        raise RenderError("blocked_prompt_values_invalid", "values must be a JSON object")
    values = {**values, "copy_contract_block": copy_block.rstrip("\n")}
    required = set(PLACEHOLDER_RE.findall(template))
    missing = sorted(key for key in required if key not in values or not isinstance(values[key], (str, int)))
    if missing:
        raise RenderError("blocked_prompt_values_missing", f"missing template values: {missing}")
    prompt = template
    for key in sorted(required):
        prompt = prompt.replace("{{" + key + "}}", str(values[key]))
    remaining = sorted(set(PLACEHOLDER_RE.findall(prompt)))
    if remaining:
        raise RenderError("blocked_prompt_placeholder_leak", f"unresolved placeholders: {remaining}")
    prompt = prompt.rstrip("\n") + "\n"
    output = args.output.expanduser().resolve()
    write_text(output, prompt)
    prompt_bytes = prompt.encode("utf-8")
    receipt = {
        "schema_version": "packaging_generation_prompt_receipt.v1",
        "template_sha256": sha256(template_bytes),
        "values_sha256": sha256(values_bytes),
        "copy_block_sha256": sha256(copy_block_bytes),
        "generation_prompt_sha256": sha256(prompt_bytes),
        "generation_prompt_content_sha256": sha256(prompt_bytes[:-1]),
        "copy_block_embedded_verbatim": copy_block.rstrip("\n") in prompt,
        "unresolved_placeholder_count": 0,
    }
    write_text(args.receipt.expanduser().resolve(), json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"ok": True, **receipt}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RenderError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "detail": exc.detail}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
