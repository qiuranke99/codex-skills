#!/usr/bin/env python3
"""Validate Google Omni video segments for temporal structure and product locks."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REQUIRED_SEGMENT_FIELDS = [
    "segment_id",
    "time_range",
    "purpose",
    "source_shots",
    "first_frame",
    "last_frame",
    "camera_plan",
    "subject_motion",
    "environment_motion",
    "continuity_lock",
    "visual_style",
    "negative_constraints",
]

PRODUCT_WORDS = re.compile(
    r"product|packshot|bottle|jar|tube|box|package|packaging|label|logo|brand|perfume|fragrance|serum|cream|"
    r"产品|包装|瓶|瓶身|罐|管|盒|标签|标贴|文字|品牌|商标|香水|香氛|精华|面霜",
    re.IGNORECASE,
)
PRODUCT_MARK_WORDS = re.compile(
    r"label|logo|wordmark|text|mark|packaging|brand|layout|cap|pump|shape|proportion|"
    r"文字|标签|标贴|品牌|商标|版式|包装|瓶盖|喷头|形状|比例",
    re.IGNORECASE,
)
RIGID_WORDS = re.compile(
    r"rigid|still|stable|unchanged|fixed|cap (?:stays|remains)|label (?:stays|remains|fixed)|"
    r"刚体|稳定|不变|固定|瓶盖不动|瓶盖保持|标签固定|标签不动",
    re.IGNORECASE,
)
UNSAFE_PRODUCT_REBUILD = re.compile(
    r"\b(product|bottle|jar|tube|package|perfume|fragrance)\b[^.\n]{0,80}"
    r"\b(appear|appears|emerge|emerges|rise|rises|rotate|rotates|spin|spins|form|forms|generate|generates|"
    r"assemble|assembles|materialize|materializes|morph|morphs|transform|transforms|open|opens|separate|separates|"
    r"float|floats|lift|lifts|detach|detaches)\b|"
    r"\b(cap|lid|atomizer)\b[^.\n]{0,60}\b(open|opens|separate|separates|float|floats|lift|lifts|detach|detaches)\b|"
    r"产品[^。\n]{0,80}(生成|出现|升起|旋转|变形|变成|组装|凝结|开盖|分离|漂浮)|"
    r"瓶盖[^。\n]{0,60}(打开|分离|漂浮|升起|脱离)",
    re.IGNORECASE,
)
PRODUCT_DRIFT_WORDS = re.compile(
    r"generic|blank|fake|new brand|new logo|changed label|changed cap|duplicate|extra bottle|"
    r"通用|空白|假品牌|假标签|新品牌|新logo|改变标签|改变瓶盖|多个瓶|重复瓶",
    re.IGNORECASE,
)
NEGATED_CLAUSE = re.compile(
    r"^\s*(no|not|never|do not|don't|without|禁止|不要|不能|不可|不)\b",
    re.IGNORECASE,
)
UNSAFE_POSITIVE_FIELDS = [
    "purpose",
    "first_frame",
    "last_frame",
    "camera_plan",
    "subject_motion",
    "environment_motion",
]
PRODUCT_VISIBILITY_VALUES = {"full_visible", "partial_visible", "detail_only", "not_visible"}
REQUIRED_REFERENCE_FIELDS = ["product_identity_reference", "product_identity_role"]
REQUIRED_LOCK_FIELDS = [
    "source_reference",
    "product_name_text",
    "primary_label_text",
    "label_layout",
    "packaging_shape",
    "color_material_marks",
    "required_visible_marks",
    "forbidden_changes",
    "rigid_body_rule",
    "allowed_angles_or_views",
    "forbidden_product_motion",
]


def load_payload(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def text_blob(*values: object) -> str:
    chunks: list[str] = []
    for value in values:
        if isinstance(value, dict):
            chunks.append(text_blob(*value.values()))
        elif isinstance(value, list):
            chunks.append(text_blob(*value))
        else:
            chunks.append(str(value))
    return " ".join(chunks)


def has_nonempty(value: object) -> bool:
    if isinstance(value, list):
        return any(str(item).strip() for item in value)
    return bool(str(value).strip())


def is_product_video(payload: dict) -> bool:
    if isinstance(payload.get("product_identity_lock"), dict):
        return True
    if isinstance(payload.get("required_reference_setup"), dict):
        setup = payload["required_reference_setup"]
        if "product_identity" in text_blob(setup).lower():
            return True
    return bool(PRODUCT_WORDS.search(text_blob(payload.get("segments", []))))


def segment_mentions_product(segment: dict) -> bool:
    return bool(PRODUCT_WORDS.search(text_blob(segment)))


def has_unsafe_product_rebuild(segment: dict) -> bool:
    """Detect product reconstruction in positive motion fields, not in bans."""
    positive_blob = text_blob(*(segment.get(field, "") for field in UNSAFE_POSITIVE_FIELDS))
    for clause in re.split(r"[.;。；\n]+", positive_blob):
        clause = clause.strip()
        if not clause or NEGATED_CLAUSE.search(clause):
            continue
        if UNSAFE_PRODUCT_REBUILD.search(clause):
            return True
    return False


def validate_product_video(payload: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not is_product_video(payload):
        return errors, warnings

    setup = payload.get("required_reference_setup")
    if not isinstance(setup, dict):
        errors.append("video: product video requires required_reference_setup")
    else:
        for field in REQUIRED_REFERENCE_FIELDS:
            if not has_nonempty(setup.get(field)):
                errors.append(f"required_reference_setup: missing {field}")
        if "product_identity" not in str(setup.get("product_identity_role", "")).lower():
            errors.append("required_reference_setup: product_identity_role must mark the reference as product_identity")

    lock = payload.get("product_identity_lock")
    if not isinstance(lock, dict):
        errors.append("video: product video requires product_identity_lock")
    else:
        for field in REQUIRED_LOCK_FIELDS:
            if not has_nonempty(lock.get(field)):
                errors.append(f"product_identity_lock: missing {field}")

    global_negative = str(payload.get("global_negative_constraints", ""))
    if not PRODUCT_DRIFT_WORDS.search(global_negative):
        warnings.append("video: global_negative_constraints should reject generic/blank/fake/changed product variants")

    for idx, segment in enumerate(payload.get("segments", []), start=1):
        sid = segment.get("segment_id", f"segment-{idx}")
        segment_blob = text_blob(segment)
        mentions_product = segment_mentions_product(segment)
        visibility = str(segment.get("product_visibility", "")).strip()
        product_visible = visibility and visibility != "not_visible"

        if has_unsafe_product_rebuild(segment):
            errors.append(f"{sid}: unsafe product rebuild language detected")

        if mentions_product or product_visible:
            if visibility not in PRODUCT_VISIBILITY_VALUES:
                errors.append(f"{sid}: product segment requires product_visibility")
            if visibility == "not_visible" and mentions_product:
                errors.append(f"{sid}: product_visibility cannot be not_visible when segment text mentions product")
            if not has_nonempty(segment.get("product_identity_reference")):
                errors.append(f"{sid}: product segment requires product_identity_reference")
            if not has_nonempty(segment.get("product_motion_rule")):
                errors.append(f"{sid}: product segment requires product_motion_rule")

            identity_blob = text_blob(
                segment.get("product_motion_rule", ""),
                segment.get("subject_motion", ""),
                segment.get("continuity_lock", ""),
                segment.get("last_frame", ""),
                segment.get("negative_constraints", ""),
            )
            if not RIGID_WORDS.search(identity_blob):
                errors.append(f"{sid}: product segment must state rigid/still/unchanged product motion")
            if not PRODUCT_MARK_WORDS.search(identity_blob):
                errors.append(f"{sid}: product segment must preserve package shape, label/text/logo/mark/cap/layout")
            if not PRODUCT_DRIFT_WORDS.search(str(segment.get("negative_constraints", ""))):
                errors.append(f"{sid}: negative_constraints must reject generic/blank/fake/changed product variants")

    return errors, warnings


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_video_segments.py <video_segments.json>", file=sys.stderr)
        return 2

    payload = load_payload(sys.argv[1])
    errors: list[str] = []
    warnings: list[str] = []

    segments = payload.get("segments", [])
    if not isinstance(segments, list) or not segments:
        errors.append("video: missing segments")
        segments = []

    for idx, segment in enumerate(segments, start=1):
        sid = segment.get("segment_id", f"segment-{idx}") if isinstance(segment, dict) else f"segment-{idx}"
        if not isinstance(segment, dict):
            errors.append(f"{sid}: segment must be an object")
            continue
        for field in REQUIRED_SEGMENT_FIELDS:
            if not has_nonempty(segment.get(field)):
                errors.append(f"{sid}: missing {field}")

    product_errors, product_warnings = validate_product_video(payload)
    errors.extend(product_errors)
    warnings.extend(product_warnings)

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
