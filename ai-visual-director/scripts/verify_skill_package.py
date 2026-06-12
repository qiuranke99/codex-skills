#!/usr/bin/env python3
"""Verify the ai-visual-director skill is self-contained and runnable."""

from __future__ import annotations

import json
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path


REQUIRED_FILES = [
    "SKILL.md",
    "agents/openai.yaml",
    "references/intake.schema.json",
    "references/shot_plan.schema.json",
    "references/video_segments.schema.json",
    "references/audit.schema.json",
    "references/observer_event.schema.json",
    "references/rule_candidate.schema.json",
    "references/source_manifest.json",
    "references/observer_protocol.md",
    "references/director_kernel.md",
    "references/world_class_tvc_principles.md",
    "references/shot_spec_template.md",
    "references/good_shotlist_examples.md",
    "references/blue_gray_previs_style_bible.md",
    "assets/blue_gray_previs_reference.jpeg",
    "scripts/route_project.py",
    "scripts/validate_shot_plan.py",
    "scripts/score_audit.py",
    "scripts/observe_run.py",
    "scripts/create_observer_packet.py",
    "scripts/package_skill.py",
    "scripts/verify_skill_package.py",
]


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_skill_package.py <skill_dir>", file=sys.stderr)
        return 2

    skill_dir = Path(sys.argv[1]).resolve()
    if not skill_dir.exists():
        fail(f"missing skill dir: {skill_dir}")

    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED_FILES:
        path = skill_dir / rel
        if not path.exists():
            errors.append(f"missing required file: {rel}")

    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8") if (skill_dir / "SKILL.md").exists() else ""
    forbidden_refs = ["../../../01_", "../../../02_", "Storyboard 模版/"]
    for ref in forbidden_refs:
        if ref in text:
            errors.append(f"SKILL.md still references non-packaged path: {ref}")

    for rel in [
        "references/intake.schema.json",
        "references/shot_plan.schema.json",
        "references/video_segments.schema.json",
        "references/audit.schema.json",
        "references/observer_event.schema.json",
        "references/rule_candidate.schema.json",
        "references/source_manifest.json",
    ]:
        path = skill_dir / rel
        if path.exists():
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"invalid JSON {rel}: {exc}")

    for path in sorted((skill_dir / "scripts").glob("*.py")):
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            errors.append(f"python compile failed {path.name}: {exc}")

    route_script = skill_dir / "scripts/route_project.py"
    if route_script.exists():
        sample = {
            "brief": "高端护肤隔离霜产品广告，纯净花萃，玻璃科技感，40s，Google omni 10s/段",
            "duration_seconds": 40,
            "video_segment_seconds": 10,
            "reference_images": [{"path": "image1.jpg"}, {"path": "image2.jpg"}, {"path": "image3.jpg"}],
        }
        proc = subprocess.run(
            [sys.executable, str(route_script)],
            input=json.dumps(sample, ensure_ascii=False),
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            errors.append(f"route_project.py sample failed: {proc.stderr.strip()}")
        else:
            routed = json.loads(proc.stdout)
            expected = {
                "project_type": "premium_product_ad",
                "production_mode": "standard_fast",
                "storyboard_sheet_count": 3,
                "panel_count": 27,
                "video_segment_count": 4,
            }
            for key, value in expected.items():
                if routed.get(key) != value:
                    errors.append(f"route sample expected {key}={value}, got {routed.get(key)!r}")

    observer_script = skill_dir / "scripts/observe_run.py"
    if observer_script.exists():
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "observer_probe"
            append_proc = subprocess.run(
                [
                    sys.executable,
                    str(observer_script),
                    "--strict",
                    "append",
                    "--run-dir",
                    str(run_dir),
                    "--stage",
                    "post_image_qc",
                    "--event-type",
                    "image_qc_issue",
                    "--severity",
                    "severe",
                    "--failure-codes",
                    "readable_text",
                    "--evidence",
                    "readable text detected in generated storyboard sheet",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            if append_proc.returncode != 0:
                errors.append(f"observe_run.py append failed: {append_proc.stderr.strip()}")
            events = run_dir / "_observer/events.jsonl"
            out = run_dir / "_observer/candidate_rules.json"
            propose_proc = subprocess.run(
                [
                    sys.executable,
                    str(observer_script),
                    "--strict",
                    "propose-rules",
                    "--events",
                    str(events),
                    "--out",
                    str(out),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            if propose_proc.returncode != 0:
                errors.append(f"observe_run.py propose-rules failed: {propose_proc.stderr.strip()}")
            elif out.exists():
                candidates = json.loads(out.read_text(encoding="utf-8"))
                if not candidates.get("candidate_rules"):
                    errors.append("observe_run.py expected a severe event to create a candidate rule")
            else:
                errors.append("observe_run.py did not create candidate_rules.json")
            aggregate_out = run_dir / "_observer/aggregate_candidate_rules.json"
            aggregate_proc = subprocess.run(
                [
                    sys.executable,
                    str(observer_script),
                    "--strict",
                    "aggregate-runs",
                    "--root",
                    str(Path(tmp)),
                    "--out",
                    str(aggregate_out),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            if aggregate_proc.returncode != 0:
                errors.append(f"observe_run.py aggregate-runs failed: {aggregate_proc.stderr.strip()}")
            elif aggregate_out.exists():
                aggregate = json.loads(aggregate_out.read_text(encoding="utf-8"))
                if aggregate.get("source_event_file_count") != 1:
                    errors.append("observe_run.py aggregate-runs expected one source events file")
            else:
                errors.append("observe_run.py did not create aggregate candidate rules")

    result = {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "checked_file_count": len(REQUIRED_FILES),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
