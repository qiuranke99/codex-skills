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
PRODUCT_PROJECT_TYPES = {"premium_product_ad"}
PRODUCT_ROLE_WORDS = {"product_identity"}
PRODUCT_APPEARANCE_WORDS = re.compile(
    r"product|packshot|bottle|jar|tube|box|package|packaging|label|logo|brand|serum|cream|lipstick|fragrance|"
    r"产品|包装|瓶|瓶身|罐|管|盒|标签|标贴|文字|品牌|商标|精华|面霜|口红|香水",
    re.IGNORECASE,
)
PRODUCT_MARK_WORDS = re.compile(
    r"label|logo|wordmark|text|mark|packaging|brand|layout|文字|标签|标贴|品牌|商标|版式|包装",
    re.IGNORECASE,
)
PRODUCT_TEXT_BAN_WORDS = re.compile(
    r"no readable text|no text|no labels|no logos|without readable text|无文字|不要文字|不要标签|不要logo|不要商标",
    re.IGNORECASE,
)
PRODUCT_VISIBILITY_VALUES = {"full_visible", "partial_visible", "detail_only", "not_visible"}
REQUIRED_PRODUCT_LOCK_FIELDS = [
    "source_reference",
    "product_name_text",
    "primary_label_text",
    "label_layout",
    "packaging_shape",
    "color_material_marks",
    "required_visible_marks",
    "forbidden_changes",
]


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


def nonempty_product_lock_value(value: object) -> bool:
    if isinstance(value, list):
        return any(str(item).strip() for item in value)
    return bool(str(value).strip())


def is_product_plan(plan: dict) -> bool:
    if str(plan.get("project_type", "")).strip() in PRODUCT_PROJECT_TYPES:
        return True
    for role in plan.get("reference_roles", []):
        if str(role.get("role", "")).strip() in PRODUCT_ROLE_WORDS:
            return True
    search_blob = " ".join(
        str(value)
        for value in [
            plan.get("project_title", ""),
            plan.get("visual_strategy", ""),
            " ".join(str(item) for item in plan.get("continuity_locks", [])),
        ]
    )
    return bool(PRODUCT_APPEARANCE_WORDS.search(search_blob))


def shot_mentions_product(shot: dict) -> bool:
    blob = " ".join(
        str(shot.get(field, ""))
        for field in [
            "shot_purpose",
            "main_subject",
            "main_action",
            "composition",
            "reference_parity",
            "continuity_lock",
            "must_preserve",
            "avoid",
        ]
    )
    return bool(PRODUCT_APPEARANCE_WORDS.search(blob))


def validate_product_identity(plan: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not is_product_plan(plan):
        return errors, warnings

    lock = plan.get("product_identity_lock")
    if not isinstance(lock, dict):
        errors.append("plan: product ad/reference requires product_identity_lock")
    else:
        for field in REQUIRED_PRODUCT_LOCK_FIELDS:
            if not nonempty_product_lock_value(lock.get(field)):
                errors.append(f"product_identity_lock: missing {field}")

    for sheet in plan.get("sheets", []):
        for shot in sheet.get("shots", []):
            sid = shot.get("shot_id", "<unknown-shot>")
            visibility = str(shot.get("product_visibility", "")).strip()
            action = str(shot.get("product_identity_action", "")).strip()
            mentions_product = shot_mentions_product(shot)
            product_visible = visibility and visibility != "not_visible"

            if mentions_product or product_visible:
                if visibility not in PRODUCT_VISIBILITY_VALUES:
                    errors.append(f"{sid}: product shot requires product_visibility")
                elif visibility == "not_visible":
                    errors.append(f"{sid}: product_visibility cannot be not_visible when the shot mentions the product")

                if not has_concrete_language(action) or action.lower() in {"not applicable", "n/a", "none"}:
                    errors.append(f"{sid}: product shot requires concrete product_identity_action")

                identity_blob = " ".join(
                    str(shot.get(field, ""))
                    for field in [
                        "product_identity_action",
                        "must_preserve",
                        "continuity_lock",
                        "reference_parity",
                    ]
                )
                if not PRODUCT_MARK_WORDS.search(identity_blob):
                    errors.append(
                        f"{sid}: visible product must preserve package marks, label/text/logo/layout, or state why none are provided"
                    )

                avoid_text = str(shot.get("avoid", ""))
                if PRODUCT_TEXT_BAN_WORDS.search(avoid_text) and "product" not in avoid_text.lower() and "产品" not in avoid_text:
                    errors.append(f"{sid}: avoid field bans readable text/logos without a product-packaging exception")

            elif visibility and visibility not in PRODUCT_VISIBILITY_VALUES:
                errors.append(f"{sid}: product_visibility has invalid value {visibility!r}")

    return errors, warnings


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

    product_errors, product_warnings = validate_product_identity(plan)
    errors.extend(product_errors)
    warnings.extend(product_warnings)

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
