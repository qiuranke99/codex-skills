#!/usr/bin/env python3
"""Audit cinematic-composition prompt output for the skill contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


NEGATIVE_TAILS = [
    "无干净数字锐度、无CGI外观、无海报构图、无居中肖像、无黑边",
    "no clean digital sharpness, no CGI look, no poster composition, no centered portrait, no black bars",
]

BANNED_PATTERNS = [
    r"\bepic\b",
    r"\bbeautiful\b",
    r"\bcool\b",
    r"\bposter\b",
    r"\bportrait\b",
    r"\bblack bars?\b",
    r"\bletterbox(?:ed)?\b",
    r"\bstyle of\b",
    r"\bdirected by\b",
    r"史诗般的",
    r"美丽",
    r"很酷",
    r"艺术家风格",
    r"导演风格",
]

COMPOSITION_MARKERS = [
    "低角度",
    "高角度",
    "俯视",
    "顶视",
    "肩后",
    "前景遮挡",
    "反射",
    "剪影",
    "框中框",
    "消失点",
    "负空间",
    "长焦",
    "手持",
    "对角线",
    "对称",
    "不对称",
    "隐藏",
    "环境尺度",
    "主观视角",
    "分层",
    "low angle",
    "high angle",
    "overhead",
    "top-down",
    "over-the-shoulder",
    "foreground obstruction",
    "reflection",
    "silhouette",
    "frame-within-frame",
    "vanishing point",
    "negative space",
    "telephoto",
    "handheld",
    "diagonal",
    "symmetrical",
    "asymmetrical",
    "hidden",
    "environmental scale",
    "subjective",
    "layered",
]


def split_items(text: str) -> list[tuple[int, str]]:
    matches = list(re.finditer(r"(?m)^\s*(\d{1,2})\.\s+\*\*.+?\*\*", text))
    items: list[tuple[int, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        items.append((int(match.group(1)), text[start:end].strip()))
    return items


def strip_negative_tail(text: str) -> str:
    stripped = text
    for tail in NEGATIVE_TAILS:
        stripped = stripped.replace(tail, "")
    return stripped


def extract_composition(section: str) -> str:
    match = re.search(r"\*\*(?:构图|Composition)\s*[:：]\s*(.+?)\*\*", section, re.I)
    return match.group(1).strip() if match else ""


def marker_count(compositions: list[str]) -> int:
    combined = " ".join(compositions).lower()
    return sum(1 for marker in COMPOSITION_MARKERS if marker.lower() in combined)


def audit(path: Path) -> tuple[bool, dict[str, object]]:
    text = path.read_text(encoding="utf-8")
    items = split_items(text)
    errors: list[str] = []
    warnings: list[str] = []

    if len(items) != 10:
        errors.append(f"expected exactly 10 numbered items, found {len(items)}")

    numbers = [number for number, _ in items]
    if numbers != list(range(1, 11)):
        errors.append(f"expected item numbers 1-10, found {numbers}")

    compositions: list[str] = []
    for number, section in items:
        if not re.search(rf"(?m)^\s*{number}\.\s+\*\*.+?\*\*", section):
            errors.append(f"item {number}: missing bold title")

        composition = extract_composition(section)
        if not composition:
            errors.append(f"item {number}: missing composition line")
        else:
            compositions.append(composition)

        if not re.search(r"(?:提示|Prompt)\s*[:：]", section, re.I):
            errors.append(f"item {number}: missing prompt label")

        if not any(tail in section for tail in NEGATIVE_TAILS):
            errors.append(f"item {number}: missing default negative phrase")

        positive_text = strip_negative_tail(section)
        for pattern in BANNED_PATTERNS:
            if re.search(pattern, positive_text, re.I):
                errors.append(f"item {number}: banned or weak wording matches /{pattern}/")

    normalized = [re.sub(r"\s+", "", comp.lower()) for comp in compositions]
    if len(set(normalized)) != len(normalized):
        errors.append("composition concepts are not unique")

    family_hits = marker_count(compositions)
    if family_hits < 8:
        warnings.append(f"only {family_hits} known composition-family markers detected; manually verify diversity")

    report = {
        "path": str(path),
        "passed": not errors,
        "item_count": len(items),
        "numbers": numbers,
        "unique_compositions": len(set(normalized)),
        "composition_family_marker_hits": family_hits,
        "errors": errors,
        "warnings": warnings,
    }
    return not errors, report


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: audit_cinematic_prompts.py <prompt-output.md>", file=sys.stderr)
        return 2

    path = Path(argv[1])
    ok, report = audit(path)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
