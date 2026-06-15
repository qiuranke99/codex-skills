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
PRODUCT_PROJECT_TYPES = {"premium_product_ad", "product_ad"}
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
PRODUCT_DRIFT_WORDS = re.compile(
    r"generic|blank|fake|wrong text|no text|missing text|new brand|new logo|changed label|changed cap|"
    r"duplicate|extra bottle|extra emblem|extra badge|front plaque|metal plate",
    re.IGNORECASE,
)
PACKSHOT_EXCEPTION_WORDS = re.compile(
    r"packshot[- ]only|catalog|catalogue|e-?commerce|listing|sku|detail board|product-only board",
    re.IGNORECASE,
)
PRODUCT_DOMINANT_WORDS = re.compile(
    r"product|packshot|bottle|jar|tube|box|package|packaging|label|logo|brand|serum|cream|lipstick|fragrance|"
    r"front-facing|full supplied|hero product|product hero|full bottle|full product|"
    r"浜у搧|鍖呰|鐡秥鐡惰韩|缃恷绠鐩抾鏍囩|鏍囪创|鍝佺墝|鍟嗘爣|绮惧崕|闈㈤湝|鍙ｇ孩|棣欐按",
    re.IGNORECASE,
)
REQUIRED_CREATIVE_CONCEPT_FIELDS = [
    "big_idea",
    "audience_desire",
    "story_tension",
    "world_rule",
    "visual_mechanism",
    "scene_ladder",
    "signature_images",
]
REQUIRED_CREATIVE_SHOT_FIELDS = [
    "scene_arena",
    "scene_role",
    "dramatic_event",
    "visual_mechanism",
]
WEAK_CREATIVE_WORDS = re.compile(
    r"^(premium|luxury|beautiful|elegant|cinematic|high-end)$|"
    r"\b(looks? premium|look beautiful|high-end feeling|beauty shot|nice mood)\b",
    re.IGNORECASE,
)
WEAK_DRAMATIC_EVENT_WORDS = re.compile(
    r"^(light|highlight|camera|product|bottle|label|cap|ribbon|petal)\s+"
    r"(sweeps?|travels?|drifts?|holds?|settles?|appears?|reveals?|catches?|shows?)\b|"
    r"\b(light sweeps? across|holds still|looks premium|soft lavender reflection makes it look premium)\b",
    re.IGNORECASE,
)
VISUAL_FIDELITY_WORDS = re.compile(
    r"exact|match|same|preserve|supplied|original|reference|unchanged|visual facts|real product|locked",
    re.IGNORECASE,
)
BAD_FULL_VIEW_TEXT = re.compile(
    r"blank label|no label|no text|no readable text|text-free|unlabeled|generic label|fake text|wrong text",
    re.IGNORECASE,
)
POSITIVE_PRODUCT_VISUAL_FIELDS = [
    "shot_purpose",
    "main_subject",
    "main_action",
    "composition",
    "foreground",
    "midground",
    "background",
    "reference_parity",
    "continuity_lock",
    "must_preserve",
    "product_identity_action",
    "visible_product_text_or_marks",
    "product_visual_facts",
]
FULL_VISIBLE_PRODUCT_FIELDS = [
    "visible_product_text_or_marks",
    "product_visual_facts",
    "forbidden_visual_additions",
]
NEGATED_PREFIX_WORDS = ("no", "not", "without", "never")
PRODUCT_VISIBILITY_VALUES = {"full_visible", "partial_visible", "detail_only", "not_visible"}
REQUIRED_PRODUCT_LOCK_FIELDS = [
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
    if value is None:
        return False
    if isinstance(value, list):
        return any(str(item).strip() for item in value)
    return bool(str(value).strip())


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


def as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def normalized(value: object) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().lower()


def visible_text_lines(lock: dict) -> list[str]:
    lines: list[str] = []
    for value in [lock.get("product_name_text"), lock.get("primary_label_text")]:
        for item in as_list(value):
            if "unreadable_from_reference" not in normalized(item):
                lines.append(item)

    unique: list[str] = []
    seen: set[str] = set()
    for line in lines:
        key = normalized(line)
        if key not in seen:
            seen.add(key)
            unique.append(line)
    return unique


def missing_full_view_text_lines(lock: dict, shot: dict) -> list[str]:
    blob = normalized(text_blob(
        shot.get("visible_product_text_or_marks", ""),
        shot.get("product_visual_facts", ""),
        shot.get("product_identity_action", ""),
        shot.get("continuity_lock", ""),
        shot.get("must_preserve", ""),
    ))
    return [line for line in visible_text_lines(lock) if normalized(line) not in blob]


def forbidden_visual_additions(lock: dict) -> list[str]:
    additions: list[str] = []
    for field in ["forbidden_visual_additions", "forbidden_changes"]:
        additions.extend(as_list(lock.get(field)))
    return additions


def positive_shot_blob(shot: dict) -> str:
    return text_blob(*(shot.get(field, "") for field in POSITIVE_PRODUCT_VISUAL_FIELDS))


def positive_mentions_forbidden_addition(lock: dict, shot: dict) -> str | None:
    clauses = [normalized(clause) for clause in re.split(r"[.;,\n]+", positive_shot_blob(shot))]
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


def is_packshot_exception(plan: dict) -> bool:
    return bool(PACKSHOT_EXCEPTION_WORDS.search(text_blob(
        plan.get("project_title", ""),
        plan.get("visual_strategy", ""),
        plan.get("continuity_locks", []),
    )))


def shot_mentions_product(shot: dict) -> bool:
    blob = " ".join(
        str(shot.get(field, ""))
        for field in [
            "scene",
            "shot_purpose",
            "shot_size",
            "main_subject",
            "main_action",
            "composition",
            "foreground",
            "midground",
            "background",
        ]
    )
    return bool(PRODUCT_APPEARANCE_WORDS.search(blob))


def product_dominates_positive_subject(shot: dict) -> bool:
    return bool(PRODUCT_DOMINANT_WORDS.search(text_blob(
        shot.get("shot_size", ""),
        shot.get("main_subject", ""),
        shot.get("main_action", ""),
        shot.get("composition", ""),
        shot.get("foreground", ""),
        shot.get("midground", ""),
        shot.get("background", ""),
    )))


def is_concrete_creative_value(value: object) -> bool:
    if isinstance(value, list):
        return len([item for item in value if is_concrete_creative_value(item)]) >= 3
    text = str(value).strip()
    if not has_concrete_language(text):
        return False
    if WEAK_CREATIVE_WORDS.search(text):
        return False
    return True


def is_weak_dramatic_event(value: object) -> bool:
    text = re.sub(r"\s+", " ", str(value).strip())
    if len(text) < 28:
        return True
    return bool(WEAK_DRAMATIC_EVENT_WORDS.search(text))


def validate_creative_director_standard(plan: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not is_product_plan(plan) or is_packshot_exception(plan):
        return errors, warnings

    concept = plan.get("creative_concept")
    if not isinstance(concept, dict):
        errors.append("plan: product ad requires creative_concept before shot planning")
        concept = {}

    for field in REQUIRED_CREATIVE_CONCEPT_FIELDS:
        value = concept.get(field)
        if not is_concrete_creative_value(value):
            errors.append(f"creative_concept: missing or weak {field}")

    for field in ["scene_ladder", "signature_images"]:
        values = [norm(item) for item in as_list(concept.get(field)) if norm(item)]
        if len(set(values)) < 3:
            errors.append(f"creative_concept: {field} needs at least 3 distinct entries")

    for sheet in plan.get("sheets", []):
        sheet_id = sheet.get("sheet_id", "<unknown>")
        shots = [shot for shot in sheet.get("shots", []) if isinstance(shot, dict)]
        if len(shots) != 9:
            continue

        scene_arenas: set[str] = set()
        visual_mechanisms: set[str] = set()
        scene_roles: set[str] = set()
        weak_event_count = 0

        for shot in shots:
            sid = shot.get("shot_id", "<unknown-shot>")
            for field in REQUIRED_CREATIVE_SHOT_FIELDS:
                value = shot.get(field)
                if field == "scene_role":
                    if len(str(value).strip()) < 4:
                        errors.append(f"{sid}: missing or weak {field}")
                elif not is_concrete_creative_value(value):
                    errors.append(f"{sid}: missing or weak {field}")

            if str(shot.get("scene_arena", "")).strip():
                scene_arenas.add(norm(shot.get("scene_arena", "")))
            if str(shot.get("visual_mechanism", "")).strip():
                visual_mechanisms.add(norm(shot.get("visual_mechanism", "")))
            if str(shot.get("scene_role", "")).strip():
                scene_roles.add(norm(shot.get("scene_role", "")))

            if is_weak_dramatic_event(shot.get("dramatic_event", "")):
                weak_event_count += 1
                errors.append(f"{sid}: weak dramatic_event; name an on-screen event, tension, or transformation")

        if len(scene_arenas) < 3:
            errors.append(f"{sheet_id}: needs at least 3 distinct scene_arena values, found {len(scene_arenas)}")
        if len(visual_mechanisms) < 3:
            errors.append(f"{sheet_id}: needs at least 3 distinct visual_mechanism values, found {len(visual_mechanisms)}")
        if len(scene_roles) < 4:
            errors.append(f"{sheet_id}: needs at least 4 distinct scene_role values, found {len(scene_roles)}")
        if weak_event_count > 2:
            errors.append(f"{sheet_id}: too many weak dramatic events ({weak_event_count}/9)")

    return errors, warnings


def validate_product_visibility_rhythm(plan: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not is_product_plan(plan) or is_packshot_exception(plan):
        return errors, warnings

    all_shots: list[dict] = [
        shot
        for sheet in plan.get("sheets", [])
        for shot in sheet.get("shots", [])
        if isinstance(shot, dict)
    ]
    if not all_shots:
        return errors, warnings

    valid_visibility_shots = [
        shot for shot in all_shots if str(shot.get("product_visibility", "")).strip() in PRODUCT_VISIBILITY_VALUES
    ]
    if valid_visibility_shots:
        not_visible_count = sum(
            1 for shot in valid_visibility_shots if str(shot.get("product_visibility", "")).strip() == "not_visible"
        )
        minimum_not_visible = max(1, len(valid_visibility_shots) // 12)
        if not_visible_count < minimum_not_visible:
            errors.append(
                "plan: product storyboard needs at least "
                f"{minimum_not_visible} product-not-visible origin/world/benefit beat(s), found {not_visible_count}"
            )

        first_full_index = next(
            (
                idx
                for idx, shot in enumerate(valid_visibility_shots, start=1)
                if str(shot.get("product_visibility", "")).strip() == "full_visible"
            ),
            None,
        )
        if first_full_index is not None and first_full_index <= 2 and len(valid_visibility_shots) >= 9:
            errors.append(
                "plan: first full-visible product reveal arrives too early; build at least two origin/detail/partial beats first"
            )

    for sheet in plan.get("sheets", []):
        sheet_id = sheet.get("sheet_id", "<unknown>")
        shots = [shot for shot in sheet.get("shots", []) if isinstance(shot, dict)]
        if len(shots) != 9:
            continue

        visibility_values = [str(shot.get("product_visibility", "")).strip() for shot in shots]
        if any(value not in PRODUCT_VISIBILITY_VALUES for value in visibility_values):
            continue

        full_visible_count = visibility_values.count("full_visible")
        detail_or_partial_count = visibility_values.count("detail_only") + visibility_values.count("partial_visible")
        not_visible_count = visibility_values.count("not_visible")
        non_product_led_count = sum(1 for shot in shots if not product_dominates_positive_subject(shot))

        if full_visible_count > 4:
            errors.append(
                f"{sheet_id}: too many full-visible product shots ({full_visible_count}/9); "
                "avoid packshot wall rhythm unless the brief explicitly asks for a catalog or packshot-only board"
            )
        if detail_or_partial_count < 3:
            errors.append(
                f"{sheet_id}: needs at least 3 detail_only/partial_visible transition or proof shots, "
                f"found {detail_or_partial_count}"
            )
        if not_visible_count < 1:
            errors.append(
                f"{sheet_id}: needs at least 1 product-not-visible origin/world/benefit/metaphor shot"
            )
        if non_product_led_count < 2:
            errors.append(
                f"{sheet_id}: needs at least 2 non-product-led storyboard panels; "
                "do not let product identity lock consume every composition"
            )

    return errors, warnings


def validate_product_identity(plan: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not is_product_plan(plan):
        return errors, warnings

    lock = plan.get("product_identity_lock")
    if not isinstance(lock, dict):
        errors.append("plan: product ad/reference requires product_identity_lock")
        lock = {}
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
            product_visible = visibility in PRODUCT_VISIBILITY_VALUES and visibility != "not_visible"

            if visibility not in PRODUCT_VISIBILITY_VALUES:
                errors.append(f"{sid}: product plan shot requires product_visibility")
                continue

            if visibility == "not_visible" and mentions_product:
                errors.append(f"{sid}: product_visibility cannot be not_visible when positive shot content describes the product")
                continue

            if product_visible:
                if visibility not in PRODUCT_VISIBILITY_VALUES:
                    errors.append(f"{sid}: product shot requires product_visibility")

                if not has_concrete_language(action) or action.lower() in {"not applicable", "n/a", "none"}:
                    errors.append(f"{sid}: product shot requires concrete product_identity_action")

                identity_blob = text_blob(
                    shot.get("product_identity_action", ""),
                    shot.get("visible_product_text_or_marks", ""),
                    shot.get("product_visual_facts", ""),
                    shot.get("forbidden_visual_additions", ""),
                    shot.get("must_preserve", ""),
                    shot.get("continuity_lock", ""),
                    shot.get("reference_parity", ""),
                    shot.get("avoid", ""),
                )
                if not VISUAL_FIDELITY_WORDS.search(identity_blob):
                    errors.append(f"{sid}: product shot must state that product visual facts match the real reference")
                if not PRODUCT_MARK_WORDS.search(identity_blob):
                    errors.append(
                        f"{sid}: visible product must preserve package marks, label/text/logo/layout, or state why none are provided"
                    )
                if not PRODUCT_DRIFT_WORDS.search(str(shot.get("avoid", ""))):
                    errors.append(f"{sid}: avoid field must reject generic/blank/fake/changed product variants")

                avoid_text = str(shot.get("avoid", ""))
                if PRODUCT_TEXT_BAN_WORDS.search(avoid_text) and "product" not in avoid_text.lower() and "产品" not in avoid_text:
                    errors.append(f"{sid}: avoid field bans readable text/logos without a product-packaging exception")

                if visibility == "full_visible":
                    for field in FULL_VISIBLE_PRODUCT_FIELDS:
                        if not nonempty_product_lock_value(shot.get(field)):
                            errors.append(f"{sid}: full-visible product shot requires {field}")
                    missing_text = missing_full_view_text_lines(lock, shot) if lock else []
                    if missing_text:
                        errors.append(
                            f"{sid}: full-visible product shot must carry exact visible product text: "
                            + ", ".join(missing_text)
                        )
                    forbidden = positive_mentions_forbidden_addition(lock, shot) if lock else None
                    if forbidden:
                        errors.append(f"{sid}: positive visual description contains forbidden visual addition: {forbidden}")
                    if BAD_FULL_VIEW_TEXT.search(positive_shot_blob(shot)):
                        errors.append(f"{sid}: full-visible product shot cannot blank, suppress, fake, or generalize product text")

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

    rhythm_errors, rhythm_warnings = validate_product_visibility_rhythm(plan)
    errors.extend(rhythm_errors)
    warnings.extend(rhythm_warnings)

    creative_errors, creative_warnings = validate_creative_director_standard(plan)
    errors.extend(creative_errors)
    warnings.extend(creative_warnings)

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
