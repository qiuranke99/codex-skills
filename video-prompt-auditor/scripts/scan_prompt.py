#!/usr/bin/env python3
"""Locate review candidates in UTF-8 prompts; never certify cinematic quality.

Exit 0 means a scan was produced (always NEEDS_SEMANTIC_REVIEW), 2 means invalid
input or unsafe output. Quoted and negated terms are deliberately retained for
contextual review instead of being silently declared errors or exceptions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

PATTERNS = (
    ("weak_camera_wording", re.compile(
        r"微横移|小幅升高|轻后撤|缓慢升高|微(?:微)?(?:推近|推进|后撤|平移|拉远)|"
        r"(?:轻微|轻轻|小幅(?:度)?|略微|细微)(?:地)?(?:向[前后左右上下])?"
        r"(?:横移|平移|升高|抬升|后撤|推进|推近|拉远|移动|退后)|"
        r"(?:subtle|slight|slightly|minimal|gently|slowly)\s+(?:\w+\s+){0,2}"
        r"(?:dolly|track|rise|rises|rising|raise|raises|pull\s*back|push\s*in)", re.I)),
    ("possible_scale_or_frame_lock", re.compile(
        r"(?:始终|全程|严格)?(?:保持|固定|锁定).{0,18}?"
        r"(?:构图|景别|视点|机位|主体大小|主体尺度|占画比例|参考帧)|"
        r"(?:构图|景别|视点|主体大小|主体尺度|占画比例)(?:始终|全程)?不变|"
        r"(?:fixed|unchanged|identical)\s+(?:framing|composition|scale|viewpoint)", re.I)),
    ("music_mention_requires_design_review", re.compile(
        r"音乐|配乐|BGM|soundtrack|background\s+music|music", re.I)),
)
SHOT_MARKER = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:[-*]\s*)?(?:\*\*)?"
    r"(?P<label>S\d{1,3}|Shot\s+\d{1,3}|镜头\s*[0-9一二三四五六七八九十百]+|第[0-9一二三四五六七八九十百]+镜)"
    r"(?=$|\s|[:：、，,|｜（(\[\]】\-—.*])", re.I)


def scan(data: bytes, expected_sha256: str | None = None) -> dict:
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None:
        if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
            raise ValueError("expected SHA-256 must be exactly 64 hexadecimal characters")
        if digest != expected_sha256.lower():
            raise ValueError("input version mismatch: SHA-256 differs from the prior scan")
    text = data.decode("utf-8-sig")
    if not text.strip():
        raise ValueError("empty prompt cannot be reviewed")
    lines = text.splitlines()
    hits, markers = [], []
    for number, line in enumerate(lines, 1):
        marker = SHOT_MARKER.match(line)
        if marker:
            markers.append({"label": marker.group("label"), "line": number})
        for category, pattern in PATTERNS:
            for match in pattern.finditer(line):
                hits.append({
                    "category": category,
                    "text": match.group(),
                    "line": number,
                    "column": match.start() + 1,
                    "context": line,
                    "disposition": "unreviewed_mention",
                })
    hits.sort(key=lambda item: (item["line"], item["column"], item["category"]))
    return {
        "schema": "video-prompt-scan.v1",
        "status": "NEEDS_SEMANTIC_REVIEW",
        "input_sha256": digest,
        "input_bytes": len(data),
        "line_count": len(lines),
        "candidate_mentions": hits,
        "explicit_shot_markers": markers,
        "coverage": {
            "source_text_scanned": True,
            "all_shots_identified": "unverified",
            "reference_playback": "not_performed",
            "music_listening": "not_performed",
            "semantic_review": "not_performed",
            "generated_video_review": "not_performed",
        },
        "next_checks": [
            "Read each mention in context, including quotations and prohibitions.",
            "Identify every actual shot, including unnumbered and repeated labels.",
            "Review start/end framing, substantial scale change, event and timing.",
            "Research multiple distinct videos with actual playback and listening.",
            "Review music development, edit points, constraints and generation risks.",
        ],
    }


def write_new_report(path: Path, report: dict, source: Path) -> None:
    # Never replace either the source or an earlier receipt, including symlinks.
    if path.resolve() == source.resolve():
        raise ValueError("output must not replace the prompt")
    if path.exists() or path.is_symlink():
        raise ValueError("output already exists; choose a new report path")
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", type=Path, help="UTF-8 prompt file")
    parser.add_argument("--out", type=Path, help="new JSON report path; parent must exist")
    parser.add_argument("--expect-sha256", help="reject changed input before reusing a scan")
    args = parser.parse_args(argv)
    try:
        if not args.prompt.is_file():
            raise ValueError("prompt must be an existing regular readable file")
        report = scan(args.prompt.read_bytes(), args.expect_sha256)
        if args.out:
            write_new_report(args.out, report, args.prompt)
            print(json.dumps({"status": report["status"], "report": str(args.out),
                              "input_sha256": report["input_sha256"]}, ensure_ascii=False))
        else:
            print(json.dumps(report, ensure_ascii=False, indent=2))
    except (OSError, UnicodeError, ValueError) as error:
        print(json.dumps({"status": "INVALID_INPUT_OR_OUTPUT", "error": str(error)},
                         ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
