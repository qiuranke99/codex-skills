#!/usr/bin/env python3
"""Validate a completed ai-visual-director run directory."""

from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from pathlib import Path


REQUIRED_ARTIFACTS = [
    "00_route_decision.json",
    "01_reference_roles.md",
    "02_shot_plan.json",
    "03_director_qc.json",
    "04_storyboard_image_prompts.md",
    "05_agent_orchestration.json",
    "08_google_omni_video_prompts.md",
    "09_final_qc_report.md",
    "11_video_generation_handoff.md",
]

JSON_ARTIFACTS = [
    "00_route_decision.json",
    "02_shot_plan.json",
    "03_director_qc.json",
    "05_agent_orchestration.json",
]

OPTIONAL_VIDEO_JSON = [
    "08_google_omni_video_prompts.json",
    "video_segments.json",
]

PRODUCT_VISIBILITY_VALUES = {"full_visible", "partial_visible", "detail_only", "not_visible"}
PRODUCT_PROJECT_TYPES = {"premium_product_ad", "product_ad"}
PRODUCT_ROLE_WORDS = {"product_identity"}
PRODUCT_APPEARANCE_WORDS = re.compile(
    r"product|packshot|bottle|jar|tube|box|package|packaging|label|logo|brand|serum|cream|lipstick|fragrance|"
    r"产品|包装|瓶|瓶身|罐|管|盒|标签|标贴|文字|品牌|商标|精华|面霜|口红|香水",
    re.IGNORECASE,
)
NOT_VISIBLE_PROMPT_WORDS = re.compile(
    r"not_visible|not visible|no product|no bottle|no package|no label|product absent|package absent",
    re.IGNORECASE,
)
CREATIVE_PROMPT_BLOCKS = [
    "story engine",
    "creative concept",
    "world rule",
    "beat map",
    "scene ladder",
    "visual mechanism",
    "anti-plastic",
]
CREATIVE_PANEL_FIELDS = [
    "scene_arena",
    "scene_role",
    "dramatic_event",
    "visual_mechanism",
]
SEGMENT_HANDOFF_WORDS = re.compile(
    r"exactly one segment|one temporal segment|one segment prompt at a time|"
    r"selected temporal segment|paste exactly one",
    re.IGNORECASE,
)
PRODUCT_REFERENCE_WORDS = re.compile(
    r"product identity reference|product reference|original product image|product image",
    re.IGNORECASE,
)


def load_json(path: Path) -> tuple[dict | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, str(exc)


def as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def normalized(value: object) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().lower()


def visible_product_text_lines(lock: dict) -> list[str]:
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


def is_product_plan(plan: dict) -> bool:
    if isinstance(plan.get("product_identity_lock"), dict):
        return True
    if str(plan.get("project_type", "")).strip() in PRODUCT_PROJECT_TYPES:
        return True
    for role in plan.get("reference_roles", []):
        if str(role.get("role", "")).strip() in PRODUCT_ROLE_WORDS:
            return True
    return bool(PRODUCT_APPEARANCE_WORDS.search(text_blob(
        plan.get("project_title", ""),
        plan.get("visual_strategy", ""),
        plan.get("continuity_locks", []),
    )))


def iter_shots(plan: dict) -> list[dict]:
    return [
        shot
        for sheet in plan.get("sheets", [])
        for shot in sheet.get("shots", [])
        if isinstance(shot, dict)
    ]


def shot_prompt_snippet(prompt_text: str, shot_id: str, max_chars: int = 420) -> str:
    match = re.search(r"(?:^|\n)\s*-\s*" + re.escape(shot_id) + r"\b", prompt_text, flags=re.IGNORECASE)
    if not match:
        match = re.search(re.escape(shot_id), prompt_text, flags=re.IGNORECASE)
    if not match:
        return ""
    return prompt_text[match.start() : match.start() + max_chars]


def run_validator(script: Path, artifact: Path, extra_args: list[str] | None = None) -> tuple[bool, dict | str]:
    extra_args = extra_args or []
    proc = subprocess.run(
        [sys.executable, str(script), str(artifact), *extra_args],
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        payload: dict | str = json.loads(proc.stdout)
    except Exception:
        payload = proc.stderr.strip() or proc.stdout.strip()
    return proc.returncode == 0, payload


def validate_product_storyboard_prompt(run_dir: Path, shot_plan: dict) -> list[str]:
    errors: list[str] = []
    lock = shot_plan.get("product_identity_lock")
    if not isinstance(lock, dict):
        return errors

    prompt_path = run_dir / "04_storyboard_image_prompts.md"
    prompt_raw = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    prompt_text = normalized(prompt_raw)
    for line in visible_product_text_lines(lock):
        if normalized(line) not in prompt_text:
            errors.append(
                "04_storyboard_image_prompts.md: missing exact visible product text from product_identity_lock: "
                + line
            )

    for field in ["surface_text_inventory", "embossed_or_relief_marks", "physical_component_inventory"]:
        if normalized(field.replace("_", " ")) not in prompt_text and not any(
            normalized(item) in prompt_text for item in as_list(lock.get(field))
        ):
            errors.append(f"04_storyboard_image_prompts.md: missing product lock evidence for {field}")

    if is_product_plan(shot_plan):
        for block in CREATIVE_PROMPT_BLOCKS:
            if block not in prompt_text:
                errors.append(f"04_storyboard_image_prompts.md: missing {block.title()} block")

        if "product visibility rhythm" not in prompt_text:
            errors.append(
                "04_storyboard_image_prompts.md: missing Product Visibility Rhythm block; "
                "per-panel visibility must counterbalance the global product lock"
            )

        for shot in iter_shots(shot_plan):
            shot_id = str(shot.get("shot_id", "")).strip()
            visibility = str(shot.get("product_visibility", "")).strip()
            if not shot_id or visibility not in PRODUCT_VISIBILITY_VALUES:
                continue
            snippet = shot_prompt_snippet(prompt_raw, shot_id)
            if not snippet:
                errors.append(f"04_storyboard_image_prompts.md: missing panel prompt for {shot_id}")
                continue
            snippet_norm = normalized(snippet)
            if visibility not in snippet_norm:
                errors.append(
                    f"04_storyboard_image_prompts.md: {shot_id} prompt must state product_visibility: {visibility}"
                )
            for field in CREATIVE_PANEL_FIELDS:
                if field not in snippet_norm:
                    errors.append(f"04_storyboard_image_prompts.md: {shot_id} prompt must state {field}")
            if visibility == "not_visible" and not NOT_VISIBLE_PROMPT_WORDS.search(snippet):
                errors.append(
                    f"04_storyboard_image_prompts.md: {shot_id} not_visible panel must explicitly forbid product/package/bottle/text"
                )

    return errors


def validate_video_generation_handoff(run_dir: Path, route: dict, shot_plan: dict) -> list[str]:
    errors: list[str] = []
    path = run_dir / "11_video_generation_handoff.md"
    if not path.exists():
        return errors

    raw = path.read_text(encoding="utf-8")
    text = normalized(raw)

    required_pairs = [
        ("Required Reference Setup", "required reference setup"),
        ("Product Identity Lock", "product identity lock"),
    ]
    for label, needle in required_pairs:
        if needle not in text:
            errors.append(f"11_video_generation_handoff.md: missing {label} usage rule")

    if not SEGMENT_HANDOFF_WORDS.search(raw):
        errors.append(
            "11_video_generation_handoff.md: must instruct the user to paste exactly one temporal segment prompt at a time"
        )

    if not (
        "not the primary video-model input" in text
        or "not the sole input" in text
        or "not upload the fixed-grid storyboard sheet as the only reference" in text
    ):
        errors.append(
            "11_video_generation_handoff.md: must state that the storyboard sheet is not the primary/sole video-model input"
        )

    if "not a clip count" not in text and "not a single-shot generation plan" not in text:
        errors.append(
            "11_video_generation_handoff.md: must state that the storyboard is not a clip count or single-shot generation plan"
        )
    if "not equal" not in text:
        errors.append("11_video_generation_handoff.md: must state 'not equal'")

    segment_count = int(route.get("video_segment_count", 0) or 0)
    if segment_count > 1 and "separately" not in text:
        errors.append(
            "11_video_generation_handoff.md: multi-segment runs must say segments are generated or evaluated separately"
        )

    if is_product_plan(shot_plan) and not PRODUCT_REFERENCE_WORDS.search(raw):
        errors.append(
            "11_video_generation_handoff.md: product runs must prioritize the product identity/reference image"
        )

    return errors


def validate_director_qc_agent_evidence(qc: dict) -> list[str]:
    errors: list[str] = []
    evidence = qc.get("director_agent_evidence")
    if not isinstance(evidence, dict):
        errors.append("03_director_qc.json: missing director_agent_evidence")
        return errors
    if str(evidence.get("agent_role", "")).strip() != "director_agent":
        errors.append("03_director_qc.json: director_agent_evidence.agent_role must be director_agent")
    refs = evidence.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        errors.append("03_director_qc.json: director_agent_evidence.evidence_refs must be a non-empty list")
    elif not any("05_agent_orchestration.json" in str(ref) for ref in refs):
        errors.append("03_director_qc.json: director_agent_evidence must reference 05_agent_orchestration.json")
    return errors


def numeric(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate_timing_consistency(route: dict, shot_plan: dict, video_payload: dict | None) -> list[str]:
    errors: list[str] = []
    duration = numeric(route.get("duration_seconds"))
    segment_seconds = numeric(route.get("video_segment_seconds"))
    if duration is None or segment_seconds is None:
        errors.append("00_route_decision.json: missing duration_seconds or video_segment_seconds")
        return errors
    if duration <= 0 or segment_seconds <= 0:
        errors.append("00_route_decision.json: duration_seconds and video_segment_seconds must be positive")
        return errors

    expected_segments = max(1, math.ceil(duration / segment_seconds))
    route_segments = int(route.get("video_segment_count", 0) or 0)
    if route_segments != expected_segments:
        errors.append(
            f"00_route_decision.json: video_segment_count={route_segments} does not match "
            f"ceil(duration_seconds/video_segment_seconds)={expected_segments}"
        )

    route_sheets = int(route.get("storyboard_sheet_count", 0) or 0)
    if route_sheets < 1:
        errors.append("00_route_decision.json: storyboard_sheet_count must be at least 1")
    if route_sheets != route_segments:
        errors.append(
            "00_route_decision.json: storyboard_sheet_count must equal video_segment_count for the Google Omni speed path"
        )

    route_owned_panel_fields = [
        "tempo_profile",
        "average_seconds_per_shot",
        "panel_count",
        "panel_count_source",
        "panels_per_sheet",
        "grid_layouts",
        "shots_per_video_segment",
        "max_panels_per_sheet",
    ]
    for field in route_owned_panel_fields:
        if field in route:
            errors.append(
                f"00_route_decision.json: {field} is director/shot-plan owned and must not be emitted by route_project"
            )

    if shot_plan:
        for field in ["duration_seconds", "storyboard_sheet_count", "video_segment_count"]:
            route_value = numeric(route.get(field))
            shot_value = numeric(shot_plan.get(field))
            if route_value is not None and shot_value is not None:
                values_match = math.isclose(route_value, shot_value)
            else:
                values_match = normalized(route.get(field)) == normalized(shot_plan.get(field))
            if field in route and field in shot_plan and not values_match:
                errors.append(f"02_shot_plan.json: {field}={shot_plan[field]!r} does not match route value {route[field]!r}")

    if video_payload is not None:
        segments = video_payload.get("segments")
        if isinstance(segments, list) and len(segments) != expected_segments:
            errors.append(
                f"08_google_omni_video_prompts.json: segment count {len(segments)} does not match route video_segment_count={expected_segments}"
            )

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_run_package.py <run_dir>", file=sys.stderr)
        return 2

    run_dir = Path(sys.argv[1]).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    checked: list[str] = []

    if not run_dir.exists() or not run_dir.is_dir():
        errors.append(f"run directory does not exist: {run_dir}")
    else:
        for rel in REQUIRED_ARTIFACTS:
            path = run_dir / rel
            checked.append(rel)
            if not path.exists():
                errors.append(f"missing required run artifact: {rel}")
            elif path.is_file() and path.stat().st_size == 0:
                errors.append(f"empty required run artifact: {rel}")

        loaded_json: dict[str, dict] = {}
        for rel in JSON_ARTIFACTS:
            path = run_dir / rel
            if not path.exists():
                continue
            payload, error = load_json(path)
            if error:
                errors.append(f"invalid JSON {rel}: {error}")
            elif isinstance(payload, dict):
                loaded_json[rel] = payload
            else:
                errors.append(f"invalid JSON {rel}: root must be an object")

        skill_dir = Path(__file__).resolve().parents[1]
        orchestration_path = run_dir / "05_agent_orchestration.json"
        if orchestration_path.exists():
            ok, payload = run_validator(
                skill_dir / "scripts" / "validate_agent_orchestration.py",
                orchestration_path,
                [str(run_dir)],
            )
            if not ok:
                errors.append(f"05_agent_orchestration.json failed validate_agent_orchestration.py: {payload}")

        shot_plan_path = run_dir / "02_shot_plan.json"
        if shot_plan_path.exists():
            ok, payload = run_validator(skill_dir / "scripts" / "validate_shot_plan.py", shot_plan_path)
            if not ok:
                errors.append(f"02_shot_plan.json failed validate_shot_plan.py: {payload}")

        qc = loaded_json.get("03_director_qc.json", {})
        if qc:
            errors.extend(validate_director_qc_agent_evidence(qc))

        shot_plan = loaded_json.get("02_shot_plan.json", {})
        if shot_plan:
            errors.extend(validate_product_storyboard_prompt(run_dir, shot_plan))
            errors.extend(
                validate_video_generation_handoff(
                    run_dir,
                    loaded_json.get("00_route_decision.json", {}),
                    shot_plan,
                )
            )

        route = loaded_json.get("00_route_decision.json", {})
        video_json = next((run_dir / rel for rel in OPTIONAL_VIDEO_JSON if (run_dir / rel).exists()), None)
        video_payload: dict | None = None
        if video_json:
            checked.append(video_json.name)
            payload, error = load_json(video_json)
            if error:
                errors.append(f"invalid JSON {video_json.name}: {error}")
            elif isinstance(payload, dict):
                video_payload = payload
            else:
                errors.append(f"invalid JSON {video_json.name}: root must be an object")
            ok, payload = run_validator(skill_dir / "scripts" / "validate_video_segments.py", video_json)
            if not ok:
                errors.append(f"{video_json.name} failed validate_video_segments.py: {payload}")
        else:
            errors.append("missing structured video prompt JSON; markdown-only Google Omni prompts cannot be validated")

        if route:
            errors.extend(validate_timing_consistency(route, shot_plan, video_payload))

    result = {
        "ok": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "checked": checked,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
