#!/usr/bin/env python3
"""Deterministically extract rough-script documents while preserving source order."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree


TIME_RE = re.compile(r"(?<!\d)(\d+(?:\.\d+)?)\s*[–—-]\s*(\d+(?:\.\d+)?)\s*(?:s|秒)\b", re.IGNORECASE)
SHOT_RE = re.compile(r"^\s*(\d{1,3})\s*$")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_text(payload: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-16", "gb18030"):
        try:
            return payload.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("source text cannot be decoded as UTF-8, UTF-16, or GB18030")


def normalize_text(value: str) -> str:
    return (
        value.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u2028", "\n")
        .replace("\x0b", "\n")
        .replace("\x07", "\t")
        .replace("\x00", "")
        .strip()
        + "\n"
    )


def _docx_xml_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        raw = archive.read("word/document.xml")
    root = ElementTree.fromstring(raw)
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    lines: list[str] = []
    for paragraph in root.iter(namespace + "p"):
        chunks: list[str] = []
        for node in paragraph.iter():
            if node.tag == namespace + "t" and node.text:
                chunks.append(node.text)
            elif node.tag == namespace + "tab":
                chunks.append("\t")
            elif node.tag in {namespace + "br", namespace + "cr"}:
                chunks.append("\n")
        lines.append("".join(chunks))
    return "\n".join(lines)


def _run_textutil(path: Path, runner: Callable[..., Any]) -> str:
    result = runner(
        ["textutil", "-convert", "txt", "-stdout", str(path)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"textutil conversion failed: {detail or 'unknown error'}")
    text, _ = decode_text(result.stdout)
    return text


def extract_source(path: Path, runner: Callable[..., Any] = subprocess.run) -> tuple[str, str, str]:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".csv", ".tsv"}:
        text, encoding = decode_text(path.read_bytes())
        return normalize_text(text), "direct_text_decode", encoding
    if suffix in {".doc", ".rtf", ".docx"}:
        try:
            return normalize_text(_run_textutil(path, runner)), "textutil_stdout", "decoded_output"
        except (FileNotFoundError, RuntimeError, ValueError, OSError):
            if suffix == ".docx":
                return normalize_text(_docx_xml_text(path)), "docx_xml_fallback", "utf-8_xml"
            raise
    try:
        return normalize_text(_run_textutil(path, runner)), "textutil_stdout_unknown_extension", "decoded_output"
    except (FileNotFoundError, RuntimeError, ValueError, OSError) as exc:
        raise ValueError(f"unsupported or unreadable source document {path.name}: {exc}") from exc


def analyze_extraction(text: str) -> dict[str, object]:
    tokens = [token.strip() for token in re.split(r"[\t\n]+", text) if token.strip()]
    shots: list[str] = []
    times: list[str] = []
    for index, token in enumerate(tokens):
        match = SHOT_RE.fullmatch(token)
        if match and index + 1 < len(tokens) and TIME_RE.search(tokens[index + 1]):
            shots.append(match.group(1).zfill(2))
        times.extend(item.group(0) for item in TIME_RE.finditer(token))
    return {
        "detected_shot_numbers": shots,
        "detected_time_tokens": times,
        "shot_order_is_strictly_preserved": len(shots) == len(set(shots)),
    }


def build_report(path: Path, method: str, encoding: str, text: str) -> dict[str, object]:
    return {
        "schema_version": "ai-video-source-extraction-report.v1",
        "source_name": path.name,
        "source_file_sha256": file_sha256(path),
        "source_size_bytes": path.stat().st_size,
        "extraction_method": method,
        "decoded_encoding": encoding,
        "normalization": ["line_endings_to_lf", "legacy_table_u0007_to_tab", "nul_removed"],
        "output_encoding": "utf-8",
        **analyze_extraction(text),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if not args.source.is_file():
        print(f"ERROR: source file does not exist: {args.source}", file=sys.stderr)
        return 2
    try:
        text, method, encoding = extract_source(args.source)
        report = build_report(args.source, method, encoding, text)
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
