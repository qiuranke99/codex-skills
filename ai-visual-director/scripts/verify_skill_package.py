#!/usr/bin/env python3
"""Verify the ai-visual-director skill is self-contained and runnable."""

from __future__ import annotations

import json
import py_compile
import subprocess
import sys
import tempfile
import hashlib
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
    "references/workflow_contract.md",
    "references/cinematic_language_decision_matrix.md",
    "references/observer_protocol.md",
    "references/director_kernel.md",
    "references/world_class_tvc_principles.md",
    "references/shot_spec_template.md",
    "references/good_shotlist_examples.md",
    "references/blue_gray_previs_style_bible.md",
    "assets/blue_gray_previs_reference.jpeg",
    "scripts/route_project.py",
    "scripts/validate_shot_plan.py",
    "scripts/validate_video_segments.py",
    "scripts/validate_run_package.py",
    "scripts/score_audit.py",
    "scripts/observe_run.py",
    "scripts/create_observer_packet.py",
    "scripts/package_skill.py",
    "scripts/verify_skill_package.py",
    "tests/test_validate_product_identity_lock.py",
    "tests/test_validate_video_product_lock.py",
    "tests/test_validate_run_package.py",
    "tests/test_cinematic_language_routing.py",
]


def fail(message: str) -> None:
    raise SystemExit(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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

    manifest_path = skill_dir / "references/source_manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for entry in manifest.get("canonical_packaged_references", []):
                rel = entry.get("path")
                expected_hash = entry.get("sha256")
                if not rel or not expected_hash:
                    errors.append(f"source_manifest.json entry missing path or sha256: {entry!r}")
                    continue
                if rel == "references/source_manifest.json":
                    errors.append("source_manifest.json must not self-hash")
                    continue
                path = skill_dir / rel
                if not path.exists():
                    errors.append(f"source_manifest.json references missing file: {rel}")
                    continue
                actual_hash = sha256_file(path)
                if actual_hash != expected_hash:
                    errors.append(
                        f"source_manifest.json hash mismatch for {rel}: expected {expected_hash}, got {actual_hash}"
                    )
        except Exception as exc:
            errors.append(f"source_manifest.json manifest check failed: {exc}")

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
                "storyboard_sheet_count": 2,
                "panel_count": 18,
                "video_segment_count": 4,
                "cinematic_language_reference_required": False,
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

    product_identity_test = skill_dir / "tests/test_validate_product_identity_lock.py"
    if product_identity_test.exists():
        test_proc = subprocess.run(
            [sys.executable, str(product_identity_test)],
            text=True,
            capture_output=True,
            check=False,
        )
        if test_proc.returncode != 0:
            errors.append(
                "product identity validator regression test failed: "
                f"{test_proc.stderr.strip() or test_proc.stdout.strip()}"
            )

    video_product_test = skill_dir / "tests/test_validate_video_product_lock.py"
    if video_product_test.exists():
        test_proc = subprocess.run(
            [sys.executable, str(video_product_test)],
            text=True,
            capture_output=True,
            check=False,
        )
        if test_proc.returncode != 0:
            errors.append(
                "video product identity validator regression test failed: "
                f"{test_proc.stderr.strip() or test_proc.stdout.strip()}"
            )

    run_package_test = skill_dir / "tests/test_validate_run_package.py"
    if run_package_test.exists():
        test_proc = subprocess.run(
            [sys.executable, str(run_package_test)],
            text=True,
            capture_output=True,
            check=False,
        )
        if test_proc.returncode != 0:
            errors.append(
                "run package validator regression test failed: "
                f"{test_proc.stderr.strip() or test_proc.stdout.strip()}"
            )

    cinematic_language_test = skill_dir / "tests/test_cinematic_language_routing.py"
    if cinematic_language_test.exists():
        test_proc = subprocess.run(
            [sys.executable, str(cinematic_language_test)],
            text=True,
            capture_output=True,
            check=False,
        )
        if test_proc.returncode != 0:
            errors.append(
                "cinematic language routing regression test failed: "
                f"{test_proc.stderr.strip() or test_proc.stdout.strip()}"
            )

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
