#!/usr/bin/env python3
"""Deterministic quality gate for the reference-video-product-adapter skill."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"

REQUIRED_FILES = [
    "SKILL.md",
    "agents/openai.yaml",
    "references/role-contracts.md",
    "references/output-contracts.md",
    "references/prompt-blocks.md",
    "references/risk-checks.md",
    "assets/templates/product_pack.md",
    "assets/templates/reference_video_link.md",
    "assets/templates/local_video_ingest_report.md",
    "assets/templates/shot_list_template.md",
    "assets/schemas/video_metadata.schema.json",
    "assets/schemas/product_pack.schema.json",
    "assets/schemas/reference_breakdown.schema.json",
    "assets/schemas/product_mapping.schema.json",
    "assets/schemas/adaptation_brief.schema.json",
    "assets/schemas/shot_list.schema.json",
    "assets/schemas/storyboard_panel_spec.schema.json",
    "examples/output/04-shot-list/shot_list.json",
    "examples/output/05-storyboard/storyboard_panel_spec.json",
    "examples/output/06-video-platform/video_platform_prompt.md",
    "scripts/validate_output_package.py",
    "scripts/ingest_local_video.py",
    "scripts/create_shot_list_docx.py",
]

ROLE_NAMES = [
    "Local Video Ingest Agent",
    "Reference Video Analyst",
    "Adaptation Boundary Agent",
    "Product Mapping Agent",
    "Adaptation Brief Agent",
    "Shot List Agent",
    "Storyboard Agent",
    "Video Prompt Agent",
    "Checker Node",
]

REQUIRED_PHRASES = [
    "Use the storyboard as sequential shot guidance, not as a static collage",
    "Do not invent product benefits",
    "Do not treat a reference video as permission to copy exact protected expression",
    "reference_breakdown",
    "product_mapping",
    "shot_list",
    "storyboard_panel_spec",
    "video_platform_prompt",
    "local_video_ingest_report",
    "ffmpeg",
    "ffprobe",
]


class Check:
    def __init__(self, name: str, weight: int, ok: bool, detail: str = "") -> None:
        self.name = name
        self.weight = weight
        self.ok = ok
        self.detail = detail


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def load_json(relative_path: str) -> object:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def main() -> int:
    skill = read(SKILL)
    all_text = "\n".join(read(path) for path in ROOT.rglob("*.md"))
    fm = frontmatter(skill)
    checks: list[Check] = []

    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    checks.append(Check("required files exist", 12, not missing, ", ".join(missing)))

    checks.append(Check("frontmatter name matches", 6, fm.get("name") == "reference-video-product-adapter", str(fm)))
    desc = fm.get("description", "")
    checks.append(Check("description starts with Use when", 6, desc.startswith("Use when"), desc))
    checks.append(Check("description stays concise", 4, 80 <= len(desc) <= 500, f"{len(desc)} chars"))

    placeholder = re.search(r"\[TODO|TODO:|placeholder|Replace with", all_text, re.I)
    checks.append(Check("no placeholders", 8, placeholder is None, placeholder.group(0) if placeholder else ""))

    private_path_pattern = re.search(r"/Users/[^/\s]+/|/Volumes/[^/\s]+/", all_text)
    checks.append(
        Check(
            "no private absolute paths in skill docs",
            4,
            private_path_pattern is None,
            private_path_pattern.group(0) if private_path_pattern else "",
        )
    )

    missing_roles = [role for role in ROLE_NAMES if role not in all_text]
    checks.append(Check("all role contracts are documented", 10, not missing_roles, ", ".join(missing_roles)))

    missing_phrases = [phrase for phrase in REQUIRED_PHRASES if phrase not in all_text]
    checks.append(Check("core safety and output phrases exist", 10, not missing_phrases, ", ".join(missing_phrases)))

    try:
        for schema_path in (ROOT / "assets" / "schemas").glob("*.json"):
            json.loads(schema_path.read_text(encoding="utf-8"))
        checks.append(Check("schemas parse as JSON", 8, True))
    except json.JSONDecodeError as exc:
        checks.append(Check("schemas parse as JSON", 8, False, str(exc)))

    for schema_name in [
        "reference_breakdown.schema.json",
        "product_mapping.schema.json",
        "adaptation_brief.schema.json",
        "shot_list.schema.json",
        "storyboard_panel_spec.schema.json",
        "video_metadata.schema.json",
    ]:
        schema = load_json(f"assets/schemas/{schema_name}")
        checks.append(Check(f"{schema_name} has required list", 4, bool(schema.get("required")), str(schema)))

    shot_list = load_json("examples/output/04-shot-list/shot_list.json")
    shots = shot_list.get("shots", []) if isinstance(shot_list, dict) else []
    checks.append(Check("sample shot list has 6-9 shots", 8, 6 <= len(shots) <= 9, f"{len(shots)} shots"))
    source_ok = all(isinstance(shot, dict) and shot.get("source_refs") for shot in shots)
    checks.append(Check("sample shots have source refs", 8, source_ok))
    risk_ok = all(isinstance(shot, dict) and "risk_flags" in shot for shot in shots)
    checks.append(Check("sample shots have risk flags", 5, risk_ok))

    panel_spec = load_json("examples/output/05-storyboard/storyboard_panel_spec.json")
    guidance = panel_spec.get("sequential_guidance", "") if isinstance(panel_spec, dict) else ""
    checks.append(Check("sample storyboard has sequential guidance", 8, "static collage" in guidance))

    video_prompt = read(ROOT / "examples/output/06-video-platform/video_platform_prompt.md")
    checks.append(Check("sample video prompt protects asset roles", 6, "Image A" in video_prompt and "Image B" in video_prompt))
    checks.append(Check("sample video prompt blocks invented text", 6, "no invented subtitles" in video_prompt and "no random logo changes" in video_prompt))

    validator = ROOT / "scripts" / "validate_output_package.py"
    result = subprocess.run(
        [sys.executable, str(validator), str(ROOT / "examples" / "output")],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    checks.append(Check("sample output package validates", 12, result.returncode == 0, result.stdout.strip()))

    docx_path = ROOT / "examples" / "output" / "04-shot-list" / "shot_list.docx"
    checks.append(Check("sample shot_list.docx exists", 5, docx_path.exists()))

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg and ffprobe:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            video_path = tmp_path / "sample.mp4"
            package_path = tmp_path / "package"
            create_video = subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc=duration=1:size=160x90:rate=10",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=1000:duration=1",
                    "-shortest",
                    "-pix_fmt",
                    "yuv420p",
                    str(video_path),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            ingest = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "ingest_local_video.py"),
                    str(video_path),
                    str(package_path),
                    "--frames",
                    "3",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            metadata = package_path / "01-input" / "local-video" / "video_metadata.json"
            contact_sheet = package_path / "01-input" / "local-video" / "contact_sheet.jpg"
            frame = package_path / "01-input" / "local-video" / "frames" / "frame_001.jpg"
            local_ok = (
                create_video.returncode == 0
                and ingest.returncode == 0
                and metadata.exists()
                and contact_sheet.exists()
                and frame.exists()
            )
            checks.append(Check("local video ingest smoke test passes", 12, local_ok, ingest.stdout.strip() or create_video.stdout.strip()))
    else:
        checks.append(Check("local video ingest dependencies exist", 12, False, "ffmpeg and ffprobe are required"))

    score = sum(check.weight for check in checks if check.ok)
    total = sum(check.weight for check in checks)
    print(f"Reference Video Product Adapter quality score: {score}/{total}")
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        detail = f" - {check.detail}" if check.detail else ""
        print(f"{status:4} {check.weight:>2} {check.name}{detail}")

    return 0 if score == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
