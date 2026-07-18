#!/usr/bin/env python3
"""Static contract checks for the standalone Cinematic Shot Image Explorer."""

from __future__ import annotations

import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
SKILL = SKILL_DIR / "SKILL.md"
EXAMPLES = SKILL_DIR / "examples.md"
TEST_CASES = SKILL_DIR / "test_cases.md"
METADATA = SKILL_DIR / "agents" / "openai.yaml"


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
    for path in (SKILL, EXAMPLES, TEST_CASES, METADATA, Path(__file__).resolve()):
        text = path.read_text(encoding="utf-8")
        for marker in forbidden:
            require(marker not in text, f"external runtime marker {marker!r} remains in {path.relative_to(SKILL_DIR)}")


def main() -> int:
    for path in (SKILL, EXAMPLES, TEST_CASES, METADATA):
        require(path.is_file(), f"missing standalone package file: {path.relative_to(SKILL_DIR)}")

    skill = SKILL.read_text(encoding="utf-8")
    examples = EXAMPLES.read_text(encoding="utf-8")
    tests = TEST_CASES.read_text(encoding="utf-8")
    metadata = METADATA.read_text(encoding="utf-8")

    frontmatter = skill.split("---", 2)
    require(len(frontmatter) == 3, "SKILL.md must contain YAML frontmatter")
    require(re.search(r"(?m)^name:\s*cinematic_shot_image_explorer\s*$", frontmatter[1]) is not None, "frontmatter name mismatch")
    require("## Standalone Runtime Contract" in skill, "standalone runtime contract is missing")
    require("blocked_image_generation_runtime" in skill, "safe image-runtime failure state is missing")
    require("精确 10 个提示" in skill, "exact-ten output contract is missing")
    require("无干净数字锐度、无CGI外观、无海报构图、无居中肖像、无黑边" in skill, "required negative suffix is missing")
    require("只输出提示词，不生成图片" in skill and "跳过生图步骤" in skill, "prompt-only exception is missing")

    acceptance = tests.split("## Acceptance tests", 1)[1].split("## Quick validation checklist", 1)[0]
    numbered = [int(value) for value in re.findall(r"(?m)^(\d+)\.\s", acceptance)]
    require(numbered == list(range(1, 16)), "acceptance tests must remain exactly 1 through 15")
    require(".agents/skills/" not in tests, "quick validation retains a workspace-specific install path")
    for index in range(1, 4):
        require(f"## Example {index}:" in examples, f"example {index} is missing")

    require('display_name: "Cinematic Shot Image Explorer"' in metadata, "display metadata is missing")
    require("$cinematic_shot_image_explorer" in metadata, "default invocation metadata is missing")
    require("allow_implicit_invocation: true" in metadata, "implicit invocation policy is missing")
    assert_no_external_runtime_markers()

    print("cinematic shot standalone contract: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
