#!/usr/bin/env python3
"""Static contract checks for the standalone Cinematic World Builder."""

from __future__ import annotations

import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
SKILL = SKILL_DIR / "SKILL.md"
METADATA = SKILL_DIR / "agents" / "openai.yaml"
ASPECTS = [
    "居民",
    "动物",
    "建筑",
    "景观",
    "日常生活",
    "旅行或运动",
    "声音或文化",
    "权力或强度",
    "肖像",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_no_external_runtime_markers() -> None:
    forbidden = (
        "HIGH_CONTROL_" + "RELEASE_GATE_V2",
        "high-control-" + "ai-tvc",
        "release-" + "control.ps1",
        "release-" + "control.sh",
        "ready_" + "latest=true",
    )
    for path in (SKILL, METADATA, Path(__file__).resolve()):
        text = path.read_text(encoding="utf-8")
        for marker in forbidden:
            require(marker not in text, f"external runtime marker {marker!r} remains in {path.relative_to(SKILL_DIR)}")


def main() -> int:
    for path in (SKILL, METADATA):
        require(path.is_file(), f"missing standalone package file: {path.relative_to(SKILL_DIR)}")

    skill = SKILL.read_text(encoding="utf-8")
    metadata = METADATA.read_text(encoding="utf-8")
    frontmatter = skill.split("---", 2)
    require(len(frontmatter) == 3, "SKILL.md must contain YAML frontmatter")
    require(re.search(r"(?m)^name:\s*cinematic_world_builder\s*$", frontmatter[1]) is not None, "frontmatter name mismatch")
    require("## Standalone Runtime Contract" in skill, "standalone runtime contract is missing")

    aspect_block = skill.split("## 必须生成的 9 个方面", 1)[1].split("## 方面定义", 1)[0]
    parsed = [(int(index), title.strip()) for index, title in re.findall(r"(?m)^(\d+)\.\s+(.+)$", aspect_block)]
    require(parsed == list(enumerate(ASPECTS, start=1)), "the fixed nine-aspect registry drifted")
    require("必须正好生成以下 9 个方面" in skill, "exact-nine contract is missing")
    require("无干净数字锐度，无CGI外观，无海报构图，无居中肖像，无黑条" in skill, "required negative suffix is missing")
    require("是否正好 9 个方面" in skill, "nine-aspect self-check is missing")

    require('display_name: "Cinematic World Builder"' in metadata, "display metadata is missing")
    require("$cinematic_world_builder" in metadata, "default invocation metadata is missing")
    require("allow_implicit_invocation: true" in metadata, "implicit invocation policy is missing")
    assert_no_external_runtime_markers()

    print("cinematic world standalone contract: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
