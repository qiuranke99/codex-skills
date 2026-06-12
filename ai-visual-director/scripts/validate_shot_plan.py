#!/usr/bin/env python3
"""Validate director-level variety and completeness in a shot plan JSON."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REQUIRED_SHOT_FIELDS = [
    "shot_id",
    "aspect_ratio",
    "scene",
    "duration",
    "shot_purpose",
    "shot_size",
    "camera_angle",
    "lens_feel",
    "camera_movement",
    "cut_logic",
    "attention_order",
    "eye_trace",
    "depth_strategy",
    "reference_parity",
    "main_subject",
    "main_action",
    "body_pose",
    "composition",
    "foreground",
    "midground",
    "background",
    "scale_reference",
    "continuity_lock",
    "must_preserve",
    "avoid",
]

ABSTRACT_WORDS = re.compile(r"\b(cinematic|premium|beautiful|luxury|elegant)\b|高级|电影感|奢华|好看|精致")
CENTERED_WORDS = re.compile(r"center|centered|symmetrical|居中|正中|对称", re.IGNORECASE)
STATIC_WORDS = re.compile(r"locked|static|still|no movement|固定|静止", re.IGNORECASE)
ESTABLISHING_WORDS = re.compile(r"wide|establish|world|环境|全景|远景", re.IGNORECASE)
MACRO_WORDS = re.compile(r"macro|insert|detail|close-up|extreme close|特写|微距|细节", re.IGNORECASE)
ANGLE_SPECIAL_WORDS = re.compile(r"low|high|top|overhead|ground|aerial|低机位|高机位|俯拍|仰拍|顶拍|地面", re.IGNORECASE)


def load_plan(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def has_concrete_language(text: str) -> bool:
    text = str(text).strip()
    if len(text) < 12:
        return False
    if ABSTRACT_WORDS.search(text) and len(text) < 40:
        return False
    return True


def validate_sheet(sheet: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    sheet_id = sheet.get("sheet_id", "<unknown>")
    shots = sheet.get("shots", [])

    if len(shots) != 9:
        errors.append(f"{sheet_id}: expected exactly 9 shots, found {len(shots)}")

    shot_sizes = set()
    camera_angles = set()
    movements = set()
    has_establishing = False
    macro_count = 0
    has_special_angle = False

    centered_static_run = 0
    for idx, shot in enumerate(shots, start=1):
        sid = shot.get("shot_id", f"{sheet_id}/shot-{idx}")
        for field in REQUIRED_SHOT_FIELDS:
            if not str(shot.get(field, "")).strip():
                errors.append(f"{sid}: missing {field}")

        for field in [
            "shot_purpose",
            "main_action",
            "composition",
            "attention_order",
            "eye_trace",
            "depth_strategy",
            "reference_parity",
            "foreground",
            "midground",
            "background",
            "scale_reference",
        ]:
            if field in shot and not has_concrete_language(str(shot.get(field, ""))):
                warnings.append(f"{sid}: weak or abstract {field}: {shot.get(field)!r}")

        attention = str(shot.get("attention_order", ""))
        if attention and not re.search(r"1|first|首先|第一", attention, flags=re.IGNORECASE):
            warnings.append(f"{sid}: attention_order should explicitly state first/second/third read")

        shot_sizes.add(norm(shot.get("shot_size", "")))
        camera_angles.add(norm(shot.get("camera_angle", "")))
        movements.add(norm(shot.get("camera_movement", "")))

        blob = " ".join(str(shot.get(field, "")) for field in ["shot_purpose", "shot_size", "camera_angle", "main_action", "composition"])
        if ESTABLISHING_WORDS.search(blob):
            has_establishing = True
        if MACRO_WORDS.search(blob):
            macro_count += 1
        if ANGLE_SPECIAL_WORDS.search(blob):
            has_special_angle = True

        centered_static = CENTERED_WORDS.search(str(shot.get("composition", ""))) and STATIC_WORDS.search(str(shot.get("camera_movement", "")))
        centered_static_run = centered_static_run + 1 if centered_static else 0
        if centered_static_run >= 3:
            errors.append(f"{sid}: 3 consecutive centered static shots detected")

    if len([x for x in shot_sizes if x]) < 5:
        errors.append(f"{sheet_id}: needs at least 5 distinct shot-size choices, found {len(shot_sizes)}")
    if len([x for x in camera_angles if x]) < 4:
        errors.append(f"{sheet_id}: needs at least 4 distinct camera-angle choices, found {len(camera_angles)}")
    if len([x for x in movements if x]) < 3:
        errors.append(f"{sheet_id}: needs at least 3 distinct camera-movement states, found {len(movements)}")
    if not has_establishing:
        errors.append(f"{sheet_id}: missing establishing/world/wide shot")
    if macro_count < 2:
        errors.append(f"{sheet_id}: needs at least 2 macro/insert/detail shots, found {macro_count}")
    if not has_special_angle:
        errors.append(f"{sheet_id}: missing high/low/top/overhead/ground-level camera angle")

    return errors, warnings


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_shot_plan.py <shot_plan.json>", file=sys.stderr)
        return 2

    plan = load_plan(sys.argv[1])
    errors: list[str] = []
    warnings: list[str] = []

    sheets = plan.get("sheets", [])
    if not sheets:
        errors.append("plan: missing sheets")

    expected_sheets = plan.get("storyboard_sheet_count")
    if expected_sheets is not None and len(sheets) != int(expected_sheets):
        errors.append(f"plan: storyboard_sheet_count={expected_sheets}, but sheets has {len(sheets)}")

    if not plan.get("continuity_locks"):
        errors.append("plan: missing continuity_locks")

    for sheet in sheets:
        sheet_errors, sheet_warnings = validate_sheet(sheet)
        errors.extend(sheet_errors)
        warnings.extend(sheet_warnings)

    result = {
        "ok": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
