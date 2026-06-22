#!/usr/bin/env python3
"""Validate Google Omni video segments for temporal structure and product visual-fidelity locks."""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path


REQUIRED_SEGMENT_FIELDS = [
    "segment_id",
    "time_range",
    "purpose",
    "aspect_ratio",
    "source_shots",
    "first_frame",
    "last_frame",
    "story_beats",
    "camera_plan",
    "lens_progression",
    "transition_grammar",
    "edit_bridge",
    "motivated_camera_path",
    "cut_strategy",
    "subject_motion",
    "environment_motion",
    "motion_continuity",
    "continuity_lock",
    "visual_style",
    "anti_plastic_constraints",
    "omni_prompt",
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
PRODUCT_DRIFT_WORDS = re.compile(
    r"generic|blank|fake|wrong text|no text|missing text|new brand|new logo|changed label|changed cap|"
    r"duplicate|extra bottle|extra emblem|extra badge|front plaque|metal plate|"
    r"通用|空白|无字|错字|文字错误|假品牌|假标签|新品牌|新logo|改变标签|改变瓶盖|多个瓶|重复瓶|金属片|铭牌|徽章",
    re.IGNORECASE,
)
VISUAL_FIDELITY_WORDS = re.compile(
    r"exact|match|same|preserve|supplied|original|reference|no-extra|no extra|unchanged visual|visual facts|"
    r"准确|一致|保持|保留|参考图|原始|真实|不得新增|不新增|视觉事实",
    re.IGNORECASE,
)
CAMERA_MOTION_WORDS = re.compile(
    r"dolly|truck|pan|tilt|push|pull|orbit|arc|crane|pedestal|handheld|locked|tracking|follow|rack focus|"
    r"zoom|parallax|reveal|slide|drift|move|camera|"
    r"推|拉|摇|移|环绕|跟拍|手持|锁定|变焦|焦点|视差|揭示|滑过|运动|镜头",
    re.IGNORECASE,
)
ANTI_PLASTIC_POSITIVE_WORDS = re.compile(
    r"material|texture|tactile|grain|halation|lens|reflection|refraction|shadow|contact|imperfect|imperfection|"
    r"physical|real|natural|micro|specular|surface|glass|skin|metal|fabric|paper|motion blur|"
    r"材质|纹理|触感|颗粒|镜头|反射|折射|阴影|接触|瑕疵|物理|真实|自然|微|高光|表面|玻璃|皮肤|金属|织物|纸|运动模糊",
    re.IGNORECASE,
)
AI_PLASTIC_NEGATIVE_WORDS = re.compile(
    r"plastic|waxy|cgi|synthetic|over[- ]?smooth|overly smooth|rubber|melted|airbrushed|fake texture|"
    r"塑料|蜡感|CGI|合成感|过度光滑|橡胶|融化|磨皮|假纹理",
    re.IGNORECASE,
)
BAD_FULL_VIEW_TEXT = re.compile(
    r"blank label|no label|no text|no readable text|text-free|unlabeled|generic label|fake text|wrong text|"
    r"空白标签|无标签|无文字|不出现字|不显示文字|通用标签|假文字|错字",
    re.IGNORECASE,
)
POSITIVE_VISUAL_FIELDS = [
    "purpose",
    "first_frame",
    "last_frame",
    "camera_plan",
    "subject_motion",
    "environment_motion",
    "continuity_lock",
    "visual_style",
    "visible_product_text_or_marks",
    "product_visual_facts",
]
NEGATED_PREFIX_WORDS = ("no", "not", "without", "never", "禁止", "不要", "不能", "不可", "没有", "无")
PRODUCT_VISIBILITY_VALUES = {"full_visible", "partial_visible", "detail_only", "not_visible"}
REQUIRED_REFERENCE_FIELDS = ["product_identity_reference", "product_identity_role"]
REQUIRED_LOCK_FIELDS = [
    "source_reference",
    "product_name_text",
    "primary_label_text",
    "surface_text_inventory",
    "embossed_or_relief_marks",
    "label_layout",
    "packaging_shape",
    "physical_component_inventory",
    "color_material_marks",
    "required_visible_marks",
    "forbidden_changes",
    "forbidden_visual_additions",
    "full_view_fidelity_rule",
]
REQUIRED_INTERNAL_SHOT_FIELDS = [
    "shot_id",
    "time_span",
    "camera_state",
    "transition",
    "transition_grammar",
    "edit_bridge",
    "lens_progression_role",
    "shot_to_shot_causality",
    "motion_continuity",
    "purpose",
]
REQUIRED_VIDEO_AGENT_ROLES = {"director_agent", "google_omni_prompt_expert_agent"}
VIDEO_AGENT_OUTPUT_REQUIREMENTS = {
    "director_agent": ["source_shots", "segments"],
    "google_omni_prompt_expert_agent": ["segments", "omni_prompt"],
}


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
    if value is None:
        return False
    if isinstance(value, list):
        return any(str(item).strip() for item in value)
    return bool(str(value).strip())


def as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def ratio_key(value: object) -> str:
    text = normalized(str(value))
    match = re.search(r"(\d+(?:\.\d+)?)\s*[:x/]\s*(\d+(?:\.\d+)?)", text)
    if not match:
        return text
    width = float(match.group(1))
    height = float(match.group(2))
    if width <= 0 or height <= 0:
        return text
    if width.is_integer() and height.is_integer():
        divisor = math.gcd(int(width), int(height))
        return f"{int(width) // divisor}:{int(height) // divisor}"
    return f"{width:g}:{height:g}"


def evidence_blob(value: object) -> str:
    return normalized(text_blob(value))


def validate_agent_activation_ledger(payload: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    ledger = payload.get("agent_activation_ledger")
    if not isinstance(ledger, list) or not ledger:
        errors.append("agent_activation_ledger: missing required video agent activation ledger")
        return errors, warnings

    by_role: dict[str, dict] = {}
    for idx, entry in enumerate(ledger, start=1):
        if not isinstance(entry, dict):
            errors.append(f"agent_activation_ledger[{idx}]: entry must be an object")
            continue
        role = str(entry.get("agent_role", "")).strip()
        if role in by_role:
            errors.append(f"agent_activation_ledger: duplicate entry for {role}")
        if role:
            by_role[role] = entry
        if entry.get("status") != "completed":
            errors.append(f"agent_activation_ledger[{idx}]: {role or '<missing-role>'} status must be completed")
        for field in [
            "agent_role",
            "stage",
            "started_at",
            "input_evidence",
            "output_evidence",
            "decision_summary",
            "blocks_next_stage_until",
        ]:
            if field in {"input_evidence", "output_evidence"}:
                if not as_list(entry.get(field)):
                    errors.append(f"agent_activation_ledger[{idx}]: {role or '<missing-role>'} missing {field}")
            elif not str(entry.get(field, "")).strip():
                errors.append(f"agent_activation_ledger[{idx}]: {role or '<missing-role>'} missing {field}")
        if role and role not in REQUIRED_VIDEO_AGENT_ROLES:
            errors.append(f"agent_activation_ledger[{idx}]: unexpected video agent_role {role!r}")

    missing = sorted(REQUIRED_VIDEO_AGENT_ROLES - set(by_role))
    for role in missing:
        errors.append(f"agent_activation_ledger: missing required completed agent {role}")

    for role, needles in VIDEO_AGENT_OUTPUT_REQUIREMENTS.items():
        entry = by_role.get(role)
        if not entry:
            continue
        output_blob = evidence_blob(entry.get("output_evidence", ""))
        for needle in needles:
            if normalized(needle) not in output_blob:
                errors.append(f"agent_activation_ledger: {role} output_evidence must reference {needle}")

    return errors, warnings


def positive_segment_blob(segment: dict) -> str:
    return text_blob(*(segment.get(field, "") for field in POSITIVE_VISUAL_FIELDS))


def visible_text_lines(lock: dict) -> list[str]:
    lines = []
    for value in [lock.get("product_name_text"), lock.get("primary_label_text")]:
        for item in as_list(value):
            if "unreadable_from_reference" not in normalized(item):
                lines.append(item)
    unique = []
    for line in lines:
        if normalized(line) not in {normalized(item) for item in unique}:
            unique.append(line)
    return unique


def missing_full_view_text_lines(lock: dict, segment: dict) -> list[str]:
    blob = normalized(text_blob(
        segment.get("visible_product_text_or_marks", ""),
        segment.get("product_visual_facts", ""),
        segment.get("last_frame", ""),
        segment.get("continuity_lock", ""),
    ))
    missing = []
    for line in visible_text_lines(lock):
        if normalized(line) not in blob:
            missing.append(line)
    return missing


def forbidden_visual_additions(lock: dict) -> list[str]:
    additions = []
    for field in ["forbidden_visual_additions", "forbidden_changes"]:
        additions.extend(as_list(lock.get(field)))
    return additions


def positive_mentions_forbidden_addition(lock: dict, segment: dict) -> str | None:
    clauses = [normalized(clause) for clause in re.split(r"[.;。；\n]+", positive_segment_blob(segment))]
    for addition in forbidden_visual_additions(lock):
        normalized_addition = normalized(addition)
        if not normalized_addition:
            continue
        for clause in clauses:
            if normalized_addition not in clause:
                continue
            if any(f"{prefix} {normalized_addition}" in clause for prefix in NEGATED_PREFIX_WORDS):
                continue
            return addition
    return None


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
        lock = {}
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
                segment.get("visible_product_text_or_marks", ""),
                segment.get("product_visual_facts", ""),
                segment.get("forbidden_visual_additions", ""),
                segment.get("product_motion_rule", ""),
                segment.get("subject_motion", ""),
                segment.get("continuity_lock", ""),
                segment.get("last_frame", ""),
                segment.get("negative_constraints", ""),
            )
            if not VISUAL_FIDELITY_WORDS.search(identity_blob):
                errors.append(f"{sid}: product segment must state that product visual facts match the real reference")
            if not PRODUCT_MARK_WORDS.search(identity_blob):
                errors.append(f"{sid}: product segment must preserve package shape, label/text/logo/mark/cap/layout")
            if not PRODUCT_DRIFT_WORDS.search(str(segment.get("negative_constraints", ""))):
                errors.append(f"{sid}: negative_constraints must reject generic/blank/fake/changed product variants")
            if visibility == "full_visible":
                if not has_nonempty(segment.get("visible_product_text_or_marks")):
                    errors.append(f"{sid}: full-visible product segment requires visible_product_text_or_marks")
                if not has_nonempty(segment.get("product_visual_facts")):
                    errors.append(f"{sid}: full-visible product segment requires product_visual_facts")
                if not has_nonempty(segment.get("forbidden_visual_additions")):
                    errors.append(f"{sid}: full-visible product segment requires forbidden_visual_additions")
                missing_text = missing_full_view_text_lines(lock, segment) if lock else []
                if missing_text:
                    errors.append(
                        f"{sid}: full-visible product segment must carry exact visible product text: "
                        + ", ".join(missing_text)
                    )
                forbidden = positive_mentions_forbidden_addition(lock, segment) if lock else None
                if forbidden:
                    errors.append(f"{sid}: positive visual description contains forbidden visual addition: {forbidden}")
                if BAD_FULL_VIEW_TEXT.search(positive_segment_blob(segment)):
                    errors.append(f"{sid}: full-visible product segment cannot blank, suppress, fake, or generalize product text")

    return errors, warnings


def validate_video_story(payload: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    story = payload.get("video_story")
    required = [
        "logline",
        "story_arc",
        "world_rule",
        "emotional_turn",
        "duration_strategy",
        "anti_plastic_strategy",
    ]
    if not isinstance(story, dict):
        errors.append("video_story: missing story engine for video prompts")
        return errors, warnings
    for field in required:
        if not has_nonempty(story.get(field)):
            errors.append(f"video_story: missing {field}")
    arc = story.get("story_arc")
    if not isinstance(arc, list) or len([item for item in arc if str(item).strip()]) < 2:
        errors.append("video_story: story_arc must contain at least 2 beats")
    anti_plastic = text_blob(story.get("anti_plastic_strategy", ""))
    if not ANTI_PLASTIC_POSITIVE_WORDS.search(anti_plastic):
        errors.append("video_story: anti_plastic_strategy must specify material, lens, light, texture, or physical-detail controls")
    return errors, warnings


def validate_requested_aspect_ratio(payload: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    requested_raw = str(payload.get("requested_video_aspect_ratio", "")).strip()
    requested = ratio_key(requested_raw)
    if not requested_raw:
        errors.append("video: requested_video_aspect_ratio is required so Google Omni prompts keep the final frame orientation")
        return errors, warnings

    for idx, segment in enumerate(payload.get("segments", []), start=1):
        if not isinstance(segment, dict):
            continue
        sid = segment.get("segment_id", f"segment-{idx}")
        segment_ratio = ratio_key(segment.get("aspect_ratio", ""))
        if segment_ratio != requested:
            errors.append(
                f"{sid}: aspect_ratio {segment.get('aspect_ratio')!r} must match requested_video_aspect_ratio {payload.get('requested_video_aspect_ratio')!r}"
            )
        segment_text = normalized(text_blob(
            segment.get("first_frame", ""),
            segment.get("last_frame", ""),
            segment.get("camera_plan", ""),
            segment.get("visual_style", ""),
            segment.get("omni_prompt", ""),
        ))
        if requested not in segment_text and "vertical" not in segment_text and "portrait" not in segment_text and "竖" not in segment_text:
            errors.append(f"{sid}: segment prompt must state the {requested} or vertical/portrait framing contract")

    return errors, warnings


def validate_temporal_segments(payload: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for idx, segment in enumerate(payload.get("segments", []), start=1):
        if not isinstance(segment, dict):
            continue
        sid = segment.get("segment_id", f"segment-{idx}")
        story_beats = segment.get("story_beats")
        if not isinstance(story_beats, list) or not story_beats:
            errors.append(f"{sid}: story_beats must be a non-empty list")

        source_shots = segment.get("source_shots")
        internal_shots = segment.get("internal_shots")
        if isinstance(source_shots, list) and len(source_shots) > 1:
            if not isinstance(internal_shots, list) or not internal_shots:
                errors.append(
                    f"{sid}: multi-shot segment requires internal_shots with time spans, transitions, and shot purposes"
                )
            elif len(internal_shots) != len(source_shots):
                errors.append(
                    f"{sid}: internal_shots has {len(internal_shots)} entries, "
                    f"but source_shots has {len(source_shots)}"
                )
        if isinstance(internal_shots, list):
            for shot_idx, internal_shot in enumerate(internal_shots, start=1):
                if not isinstance(internal_shot, dict):
                    errors.append(f"{sid}: internal_shots[{shot_idx}] must be an object")
                    continue
                for field in REQUIRED_INTERNAL_SHOT_FIELDS:
                    if not has_nonempty(internal_shot.get(field)):
                        errors.append(f"{sid}: internal_shots[{shot_idx}] missing {field}")
        if (
            isinstance(story_beats, list)
            and len(story_beats) > 4
            and not isinstance(internal_shots, list)
            and all(re.search(r"\b(panel|shot)\s*\d+\b|SH_\d{3}", str(beat), re.IGNORECASE) for beat in story_beats)
        ):
            errors.append(
                f"{sid}: dense storyboard-panel list needs internal_shots with time spans, transitions, and shot purposes"
            )

        first_frame = normalized(str(segment.get("first_frame", "")))
        last_frame = normalized(str(segment.get("last_frame", "")))
        if first_frame and last_frame and first_frame == last_frame:
            errors.append(f"{sid}: first_frame and last_frame cannot be identical; video needs temporal change")

        camera_plan = str(segment.get("camera_plan", ""))
        if camera_plan and not CAMERA_MOTION_WORDS.search(camera_plan):
            errors.append(f"{sid}: camera_plan must name a physical camera state or movement")

        motion_blob = text_blob(
            segment.get("subject_motion", ""),
            segment.get("environment_motion", ""),
            segment.get("motion_continuity", ""),
            segment.get("cut_strategy", ""),
            segment.get("omni_prompt", ""),
        )
        if not CAMERA_MOTION_WORDS.search(text_blob(camera_plan, motion_blob)):
            errors.append(f"{sid}: segment must describe camera, subject, or environment motion instead of a static storyboard frame")

        anti_plastic = text_blob(segment.get("anti_plastic_constraints", ""), segment.get("negative_constraints", ""))
        if not ANTI_PLASTIC_POSITIVE_WORDS.search(anti_plastic):
            errors.append(f"{sid}: anti_plastic_constraints must specify real material, lens, texture, light, shadow, or physical-detail behavior")
        if not AI_PLASTIC_NEGATIVE_WORDS.search(anti_plastic):
            warnings.append(f"{sid}: consider naming plastic/CGI/waxy/over-smoothed failure modes in anti_plastic or negative constraints")

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

    agent_errors, agent_warnings = validate_agent_activation_ledger(payload)
    errors.extend(agent_errors)
    warnings.extend(agent_warnings)

    product_errors, product_warnings = validate_product_video(payload)
    errors.extend(product_errors)
    warnings.extend(product_warnings)

    story_errors, story_warnings = validate_video_story(payload)
    errors.extend(story_errors)
    warnings.extend(story_warnings)

    aspect_errors, aspect_warnings = validate_requested_aspect_ratio(payload)
    errors.extend(aspect_errors)
    warnings.extend(aspect_warnings)

    temporal_errors, temporal_warnings = validate_temporal_segments(payload)
    errors.extend(temporal_errors)
    warnings.extend(temporal_warnings)

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
