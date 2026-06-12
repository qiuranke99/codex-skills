#!/usr/bin/env python3
"""Route a visual brief into storyboard and video generation counts.

Input: intake JSON on stdin or as the first file argument.
Output: route decision JSON on stdout.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path


DEFAULT_SEGMENT_SECONDS = 10
SECONDS_PER_STORYBOARD_SHEET = 13.5
ALLOWED_PRODUCTION_MODES = {"standard_fast", "rush", "premium_pitch", "certification"}


ROUTE_TEMPLATES = {
    "premium_product_ad": {
        "arc": [
            "ingredient or world origin",
            "product reveal",
            "material or texture proof",
            "use action",
            "benefit visualization",
            "final packshot payoff",
        ],
        "required_shot_language": [
            "establishing/world shot",
            "macro or insert detail",
            "3/4 hero product shot",
            "use-action close-up",
            "benefit metaphor shot",
            "final packshot",
        ],
    },
    "beauty_or_fashion": {
        "arc": [
            "identity establish",
            "texture or styling detail",
            "gesture and transformation",
            "motion or pose escalation",
            "beauty payoff",
        ],
        "required_shot_language": [
            "identity medium shot",
            "macro material detail",
            "mirror or touch action",
            "profile or 3/4 beauty shot",
            "final hero frame",
        ],
    },
    "narrative_or_surreal": {
        "arc": [
            "normal baseline",
            "first anomaly or reveal",
            "scale or stakes proof",
            "reaction",
            "consequence",
            "emotional payoff",
        ],
        "required_shot_language": [
            "normal baseline wide shot",
            "subjective discovery shot",
            "scale-proof shot",
            "reaction close-up",
            "payoff wide shot",
        ],
    },
    "food_or_beverage": {
        "arc": [
            "ingredient origin",
            "preparation action",
            "texture proof",
            "serving context",
            "appetite payoff",
        ],
        "required_shot_language": [
            "ingredient macro",
            "process action",
            "texture insert",
            "human serving shot",
            "final table hero",
        ],
    },
    "architecture_or_space": {
        "arc": [
            "spatial establish",
            "material detail",
            "human scale proof",
            "circulation",
            "hero reveal",
        ],
        "required_shot_language": [
            "wide establishing shot",
            "low-angle spatial shot",
            "material insert",
            "human scale shot",
            "final hero perspective",
        ],
    },
    "tech_or_science": {
        "arc": [
            "problem",
            "mechanism",
            "proof visualization",
            "human use",
            "clean payoff",
        ],
        "required_shot_language": [
            "problem setup",
            "mechanism insert",
            "proof visualization",
            "human-use shot",
            "final clear-result shot",
        ],
    },
}


KEYWORDS = [
    ("premium_product_ad", r"product|packshot|cream|serum|bottle|jar|primer|skincare|护肤|隔离霜|产品|包装|精华|面霜|口红|香水"),
    ("beauty_or_fashion", r"beauty|fashion|model|makeup|skin|hair|妆|美妆|时装|模特|肤感|造型"),
    ("food_or_beverage", r"food|drink|coffee|tea|dessert|ingredient|餐|饮|咖啡|茶|甜品|食材"),
    ("architecture_or_space", r"architecture|interior|hotel|store|space|建筑|室内|酒店|空间|展厅"),
    ("tech_or_science", r"tech|device|app|robot|science|medical|科技|设备|科学|医疗|机制"),
    ("narrative_or_surreal", r"story|scene|character|surreal|giant|film|narrative|故事|人物|角色|超现实|电影|巨人"),
]


def read_intake() -> dict:
    if len(sys.argv) > 1:
        return json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    return json.load(sys.stdin)


def infer_project_type(brief: str) -> str:
    for route, pattern in KEYWORDS:
        if re.search(pattern, brief, flags=re.IGNORECASE):
            return route
    return "narrative_or_surreal"


def infer_production_mode(intake: dict, brief: str) -> str:
    explicit = str(intake.get("production_mode", "")).strip()
    if explicit in ALLOWED_PRODUCTION_MODES:
        return explicit

    if re.search(r"rush|快速|今天|马上|草案|draft", brief, flags=re.IGNORECASE):
        return "rush"
    if re.search(r"pitch|campaign|launch|提案|竞稿|发布会|大客户|高预算|多方向", brief, flags=re.IGNORECASE):
        return "premium_pitch"
    if re.search(r"audit|score|benchmark|certification|审计|评分|基准|认证|评测", brief, flags=re.IGNORECASE):
        return "certification"
    return "standard_fast"


def escalation_triggers(intake: dict, brief: str) -> list[str]:
    triggers: list[str] = []
    if re.search(r"医疗|医美|药|financial|finance|legal|celebrity|明星|名人|监管|疗效|功效宣称", brief, flags=re.IGNORECASE):
        triggers.append("regulated_or_likeness_risk")
    if re.search(r"像.*香奈儿|像.*Chanel|像.*Dior|像.*Apple|模仿|复刻", brief, flags=re.IGNORECASE):
        triggers.append("brand_imitation_risk")
    if "duration_seconds" not in intake:
        triggers.append("duration_missing_defaulted")
    if len(intake.get("reference_images", [])) > 6:
        triggers.append("many_reference_images_need_role_discipline")
    if intake.get("conflicting_reference_roles"):
        triggers.append("declared_reference_conflict")
    return triggers


def main() -> int:
    intake = read_intake()
    brief = str(intake.get("brief", "")).strip()
    if not brief:
        print("brief is required", file=sys.stderr)
        return 2

    duration = float(intake.get("duration_seconds") or 30)
    segment_seconds = float(intake.get("video_segment_seconds") or DEFAULT_SEGMENT_SECONDS)
    if duration <= 0 or segment_seconds <= 0:
        print("duration_seconds and video_segment_seconds must be positive", file=sys.stderr)
        return 2

    project_type = infer_project_type(brief)
    production_mode = infer_production_mode(intake, brief)
    triggers = escalation_triggers(intake, brief)
    sheet_count = max(1, math.ceil(duration / SECONDS_PER_STORYBOARD_SHEET))
    video_segment_count = max(1, math.ceil(duration / segment_seconds))

    result = {
        "project_type": project_type,
        "production_mode": production_mode,
        "escalation_required": bool(triggers) or production_mode in {"premium_pitch", "certification"},
        "escalation_triggers": triggers,
        "duration_seconds": duration,
        "storyboard_sheet_count": sheet_count,
        "panel_count": sheet_count * 9,
        "video_segment_seconds": segment_seconds,
        "video_segment_count": video_segment_count,
        "route_template": ROUTE_TEMPLATES[project_type],
        "reference_image_count": len(intake.get("reference_images", [])),
        "notes": [
            "Storyboard sheet count and video segment count are intentionally separate.",
            "Revise route if reference images or explicit user requirements contradict keyword inference.",
        ],
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
