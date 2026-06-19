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
ALLOWED_PRODUCTION_MODES = {"standard_fast", "rush", "premium_pitch", "certification"}
CINEMATIC_LANGUAGE_REFERENCE = "references/cinematic_language_decision_matrix.md"


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


CINEMATIC_LANGUAGE_TRIGGER_PATTERNS = [
    (
        "vfx_or_virtual_production",
        r"\bvfx\b|visual effects|virtual production|led volume|greenscreen|green screen|bluescreen|blue screen|"
        r"tracking marker|lens grid|distortion chart|witness camera|hdri|light probe|composit|cgi?\b|"
        r"虚拟制作|绿幕|蓝幕|跟踪点|镜头畸变|畸变标定|视效|特效|合成|见证机位|灯光探针",
    ),
    (
        "sound_design_or_sound_editing",
        r"sound design|sound bridge|j-cut|l-cut|foley|ambience|voiceover|voice-over|\bvo\b|adr|\bmos\b|"
        r"dialogue|diegetic|non-diegetic|声音设计|声桥|声画|音效|环境声|拟音|旁白|对白|同期声|无声拍摄",
    ),
    (
        "production_handoff_or_camera_report",
        r"camera report|camera handoff|dp handoff|production handoff|timecode|time code|scene[- /]?shot[- /]?take|"
        r"focus mark|t-stop|f-stop|take metadata|交付|可追溯|现场记录|摄影指导交接|机位报告|时间码|焦点距离|焦点标记",
    ),
    (
        "color_pipeline_or_delivery",
        r"\baces\b|\blut\b|show lut|color pipeline|color space|rec\.?709|rec\.?2020|dci-p3|\bhdr\b|\bsdr\b|"
        r"\bdi\b|idt|odt|色彩管线|调色|色彩空间|输出色彩|交付色彩|现场lut",
    ),
    (
        "advanced_optics_or_motion_texture",
        r"anamorphic|spherical|lens character|filtration|filter system|pro-mist|glimmerglass|polarizer|\bnd\b|"
        r"shutter angle|frame rate|slow motion|speed ramp|time-lapse|rack focus|follow focus|split diopter|"
        r"变形宽银幕|球面镜头|镜头质感|滤镜|快门角|帧率|升格|降格|变速|延时|焦点转移|跟焦|分裂焦",
    ),
    (
        "complex_continuity_or_coverage",
        r"180[- ]?degree|axis crossing|cross[- ]?line|eyeline match|screen direction|match on action|coverage|"
        r"master shot|safety shot|30[- ]?degree|jump cut|axis|eyeline|轴线|过轴|跨线|视线匹配|银幕方向|动作匹配|"
        r"覆盖策略|主镜头|保护镜头|跳切",
    ),
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
    if "duration_seconds" not in intake and infer_duration_seconds(intake, brief)[1] == "default_missing":
        triggers.append("duration_missing_defaulted")
    if len(intake.get("reference_images", [])) > 6:
        triggers.append("many_reference_images_need_role_discipline")
    if intake.get("conflicting_reference_roles"):
        triggers.append("declared_reference_conflict")
    return triggers


TIME_PATTERN = re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>s|sec|secs|second|seconds|秒)", re.IGNORECASE)
SEGMENT_TIME_PATTERN = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?:s|sec|secs|second|seconds|秒)\s*(?:/|每)?\s*(?:segment|segments|seg|clip|clips|段|条)",
    re.IGNORECASE,
)
DURATION_CONTEXT_PATTERN = re.compile(
    r"(?:duration|length|runtime|total|video|film|ad|spot|时长|总长|视频|广告|短片|片子|成片)[^\d]{0,12}"
    r"(?P<value>\d+(?:\.\d+)?)\s*(?:s|sec|secs|second|seconds|秒)",
    re.IGNORECASE,
)


def _time_mentions(brief: str) -> list[tuple[float, tuple[int, int]]]:
    mentions = []
    for match in TIME_PATTERN.finditer(brief):
        mentions.append((float(match.group("value")), match.span()))
    return mentions


def infer_segment_seconds(intake: dict, brief: str) -> tuple[float, str]:
    if "video_segment_seconds" in intake and intake.get("video_segment_seconds") not in (None, ""):
        return float(intake["video_segment_seconds"]), "intake.video_segment_seconds"
    match = SEGMENT_TIME_PATTERN.search(brief)
    if match:
        return float(match.group("value")), "brief.segment_seconds"
    return float(DEFAULT_SEGMENT_SECONDS), "default"


def infer_duration_seconds(intake: dict, brief: str) -> tuple[float, str]:
    if "duration_seconds" in intake and intake.get("duration_seconds") not in (None, ""):
        return float(intake["duration_seconds"]), "intake.duration_seconds"

    explicit = DURATION_CONTEXT_PATTERN.search(brief)
    if explicit:
        return float(explicit.group("value")), "brief.duration_context"

    segment_spans = [match.span() for match in SEGMENT_TIME_PATTERN.finditer(brief)]
    candidates = [
        value
        for value, span in _time_mentions(brief)
        if not any(span[0] >= seg_span[0] and span[1] <= seg_span[1] for seg_span in segment_spans)
    ]
    if candidates:
        return max(candidates), "brief.time_mention"
    return 30.0, "default_missing"


def infer_cinematic_language_triggers(
    intake: dict,
    brief: str,
    project_type: str,
    production_mode: str,
    duration: float,
) -> list[str]:
    triggers: list[str] = []
    if intake.get("advanced_cinematic_language") or intake.get("complex_delivery_mode"):
        triggers.append("explicit_user_or_intake_flag")

    for trigger, pattern in CINEMATIC_LANGUAGE_TRIGGER_PATTERNS:
        if re.search(pattern, brief, flags=re.IGNORECASE):
            triggers.append(trigger)

    if production_mode == "certification":
        triggers.append("certification_mode")
    elif production_mode == "premium_pitch" and duration >= 30:
        triggers.append("premium_pitch_complexity")

    if project_type in {"architecture_or_space", "tech_or_science"} and duration >= 30:
        triggers.append("complex_project_type")

    unique: list[str] = []
    for trigger in triggers:
        if trigger not in unique:
            unique.append(trigger)
    return unique


def cinematic_language_depth(triggers: list[str]) -> str:
    l3_triggers = {
        "vfx_or_virtual_production",
        "production_handoff_or_camera_report",
        "color_pipeline_or_delivery",
        "certification_mode",
    }
    if any(trigger in l3_triggers for trigger in triggers):
        return "L3"
    if triggers:
        return "L2"
    return "default"


def storyboard_sheet_count(duration: float) -> int:
    """Return storyboard sheet count for director keyframes, not edit count."""
    if duration <= 30:
        return 1
    if duration <= 60:
        return 2
    return max(3, math.ceil(duration / 30))


def recommended_story_beat_count(duration: float) -> int:
    if duration <= 10:
        return 3
    if duration <= 20:
        return 4
    if duration <= 30:
        return 5
    if duration <= 60:
        return 6
    return min(9, max(7, math.ceil(duration / 10)))


def select_story_beats(project_type: str, duration: float) -> list[str]:
    arc = ROUTE_TEMPLATES[project_type]["arc"]
    target = recommended_story_beat_count(duration)
    if len(arc) >= target:
        return arc[:target]
    beats = list(arc)
    fillers = [
        "inciting visual rule",
        "escalation or complication",
        "human or material proof",
        "return bridge",
        "memory image",
    ]
    for filler in fillers:
        if len(beats) >= target:
            break
        if filler not in beats:
            beats.append(filler)
    return beats[:target]


def main() -> int:
    intake = read_intake()
    brief = str(intake.get("brief", "")).strip()
    if not brief:
        print("brief is required", file=sys.stderr)
        return 2

    duration, duration_source = infer_duration_seconds(intake, brief)
    segment_seconds, segment_seconds_source = infer_segment_seconds(intake, brief)
    if duration <= 0 or segment_seconds <= 0:
        print("duration_seconds and video_segment_seconds must be positive", file=sys.stderr)
        return 2

    project_type = infer_project_type(brief)
    production_mode = infer_production_mode(intake, brief)
    triggers = escalation_triggers(intake, brief)
    sheet_count = storyboard_sheet_count(duration)
    video_segment_count = max(1, math.ceil(duration / segment_seconds))
    story_beats = select_story_beats(project_type, duration)
    cinematic_triggers = infer_cinematic_language_triggers(
        intake=intake,
        brief=brief,
        project_type=project_type,
        production_mode=production_mode,
        duration=duration,
    )
    cinematic_reference_required = bool(cinematic_triggers)

    result = {
        "project_type": project_type,
        "production_mode": production_mode,
        "escalation_required": bool(triggers) or production_mode in {"premium_pitch", "certification"},
        "escalation_triggers": triggers,
        "cinematic_language_reference_required": cinematic_reference_required,
        "cinematic_language_triggers": cinematic_triggers,
        "cinematic_language_depth": cinematic_language_depth(cinematic_triggers),
        "recommended_references": [CINEMATIC_LANGUAGE_REFERENCE] if cinematic_reference_required else [],
        "duration_seconds": duration,
        "duration_source": duration_source,
        "storyboard_sheet_count": sheet_count,
        "panel_count": sheet_count * 9,
        "storyboard_panel_semantics": (
            "Each storyboard panel is a director keyframe or narrative evidence frame, "
            "not a required video cut. Do not map 9 panels to 9 quick-cut video shots."
        ),
        "recommended_story_beat_count": len(story_beats),
        "recommended_story_beats": story_beats,
        "omni_prompt_mode": "temporal_segment_motion_contract",
        "max_story_beats_per_video_segment": 4,
        "max_source_keyframes_per_video_segment": 4,
        "video_segment_seconds": segment_seconds,
        "video_segment_seconds_source": segment_seconds_source,
        "video_segment_count": video_segment_count,
        "route_template": ROUTE_TEMPLATES[project_type],
        "reference_image_count": len(intake.get("reference_images", [])),
        "notes": [
            "Storyboard panels are keyframes, not a one-to-one edit list.",
            "Storyboard sheet count and video segment count are intentionally separate.",
            "Google Omni prompts should describe temporal story beats, camera motion, subject motion, environment motion, and continuity; do not paste all storyboard panels as cuts.",
            "Revise route if reference images or explicit user requirements contradict keyword inference.",
        ],
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
