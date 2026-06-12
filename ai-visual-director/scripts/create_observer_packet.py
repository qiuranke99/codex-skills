#!/usr/bin/env python3
"""Create a compact Shadow Observer packet for ai-visual-director runs."""

from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_FILES = [
    "00_input_manifest.json",
    "01_reference_roles.md",
    "02_director_brief.json",
    "03_shot_plan.json",
    "04_storyboard_image_prompts.md",
    "validator.json",
    "08_google_omni_video_prompts.md",
    "09_qc_report.md",
    "_observer/events.jsonl",
    "_observer/candidate_rules.json",
]


def read_excerpt(path: Path, max_chars: int) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[TRUNCATED]\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--max-chars-per-file", type=int, default=12000)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    out = args.out or (run_dir / "_observer" / "observer_packet.md")

    parts = [
        "# AI Visual Director Shadow Observer Packet",
        "",
        "Read-only observer task:",
        "- Extract testable workflow-improvement evidence, not taste judgments.",
        "- Do not rewrite deliverables.",
        "- Do not approve or reject the work.",
        "- Prefer candidate rules only when evidence is repeated, severe, or user-confirmed.",
        "- Focus on reusable skill improvements, not one-off preferences.",
        "",
        f"Run directory: {run_dir}",
        "",
    ]

    for rel in DEFAULT_FILES:
        path = run_dir / rel
        if not path.exists():
            parts.extend([f"## {rel}", "", "[missing]", ""])
            continue
        parts.extend([
            f"## {rel}",
            "",
            "```",
            read_excerpt(path, args.max_chars_per_file),
            "```",
            "",
        ])

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
