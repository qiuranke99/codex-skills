#!/usr/bin/env python3
"""Validate a completed ai-visual-director run directory."""

from __future__ import annotations

import json
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
    "08_google_omni_video_prompts.md",
    "09_final_qc_report.md",
]

JSON_ARTIFACTS = [
    "00_route_decision.json",
    "02_shot_plan.json",
    "03_director_qc.json",
]

OPTIONAL_VIDEO_JSON = [
    "08_google_omni_video_prompts.json",
    "video_segments.json",
]


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


def run_validator(script: Path, artifact: Path) -> tuple[bool, dict | str]:
    proc = subprocess.run(
        [sys.executable, str(script), str(artifact)],
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
    prompt_text = normalized(prompt_path.read_text(encoding="utf-8")) if prompt_path.exists() else ""
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
        shot_plan_path = run_dir / "02_shot_plan.json"
        if shot_plan_path.exists():
            ok, payload = run_validator(skill_dir / "scripts" / "validate_shot_plan.py", shot_plan_path)
            if not ok:
                errors.append(f"02_shot_plan.json failed validate_shot_plan.py: {payload}")

        shot_plan = loaded_json.get("02_shot_plan.json", {})
        if shot_plan:
            errors.extend(validate_product_storyboard_prompt(run_dir, shot_plan))

        video_json = next((run_dir / rel for rel in OPTIONAL_VIDEO_JSON if (run_dir / rel).exists()), None)
        if video_json:
            checked.append(video_json.name)
            ok, payload = run_validator(skill_dir / "scripts" / "validate_video_segments.py", video_json)
            if not ok:
                errors.append(f"{video_json.name} failed validate_video_segments.py: {payload}")
        else:
            warnings.append("no structured video prompt JSON found; markdown-only video prompts were not schema-validated")

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
