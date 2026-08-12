from __future__ import annotations

import re
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SKILL_TEXT = (PACKAGE_ROOT / "SKILL.md").read_text(encoding="utf-8")
HANDBOOK_TEXT = (
    PACKAGE_ROOT / "references" / "blender-production-handbook.md"
).read_text(encoding="utf-8")


REQUIRED = {
    "SKILL.md": (
        "Permit concurrent Blender processes",
        "machine-wide or project-wide lock",
        '"all Blender idle" condition',
        "exact writable resource or live MCP session",
        "without stopping unrelated running lanes",
    ),
    "references/blender-production-handbook.md": (
        "同一项目或不同项目中的多个 background Blender lane 并行",
        "项目级／机器级 lock、lockfile、lease、marker",
        "每个 lane 必须独占自己的可写 `.blend`、输出文件模式、模拟／烘焙缓存",
        "使用 MCP 时，每个交互\nlane 还必须拥有独立 session 或 endpoint",
        "项目根目录、仓库路径、线程树、项目 ID、进程名称",
        "仅关闭并重开本 lane 自有的 Blender 实例",
        "关闭、终止或干扰其他 lane 的 Blender 进程或 MCP",
        "节流尚未启动的\nlane",
        "不因进程数量中止无冲突任务",
        "不设固定进程数",
    ),
}

FORBIDDEN = {
    "references/blender-production-handbook.md": (
        "- 单进程 background Blender；",
        "大型场景保持单进程。",
    ),
}

NEGATION_RE = re.compile(
    r"\b(?:never|do\s+not|don't|must\s+not|shall\s+not|may\s+not|"
    r"cannot|can't|forbid(?:s|den)?|prohibit(?:s|ed)?)\b|"
    r"禁止|不得|不能|不可|严禁|不应|无需|不要",
    re.IGNORECASE,
)
DIRECTIVE_RE = re.compile(
    r"\b(?:must|shall|required|require|only|single|wait|keep)\b|"
    r"必须|应当|需要|只能|仅允许|保持|等待|先获得|先获取",
    re.IGNORECASE,
)
GLOBAL_SCOPE_RE = re.compile(
    r"\b(?:machine[- ]wide|project[- ]wide|global|all\s+blender|"
    r"every\s+blender|entire\s+(?:machine|project))\b|"
    r"机器级|项目级|全局|整台机器|整个项目|所有\s*Blender|"
    r"全部\s*Blender|任意\s*Blender|其他\s*Blender|其余\s*Blender",
    re.IGNORECASE,
)
SERIALIZATION_RE = re.compile(
    r"\b(?:lock|lockfile|lease|marker|mutex|single[- ]process|"
    r"exit|idle)\b|锁|互斥|单进程|退出|空闲",
    re.IGNORECASE,
)

FORBIDDEN_DIRECTIVE_EXAMPLES = (
    "所有 Blender lane 必须先获得项目级全局锁，等待其他 Blender 全部退出。",
    "同一项目只能保持单进程，所有 Blender 空闲后才能开始。",
    "All Blender lanes must acquire a project-wide lock and wait until every Blender process exits.",
    "Keep a machine-wide single-process gate for every Blender task.",
)

ALLOWED_DIRECTIVE_EXAMPLES = (
    "禁止创建或等待项目级／机器级 lock。",
    "Never wait for all Blender processes to become idle.",
    "只有同一可写 .blend 实际冲突时才串行化。",
    "Resource pressure may delay a lane that has not started.",
)


def normalise_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def global_serialization_directives(text: str) -> list[str]:
    collapsed = normalise_whitespace(text)
    sentences = re.split(r"(?<=[。！？.!?；;])\s*", collapsed)
    conflicts: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or NEGATION_RE.search(sentence):
            continue
        if (
            DIRECTIVE_RE.search(sentence)
            and GLOBAL_SCOPE_RE.search(sentence)
            and SERIALIZATION_RE.search(sentence)
        ):
            conflicts.append(sentence)
    return conflicts


def main() -> int:
    documents = {
        "SKILL.md": SKILL_TEXT,
        "references/blender-production-handbook.md": HANDBOOK_TEXT,
    }
    failures: list[str] = []

    for name, snippets in REQUIRED.items():
        document = normalise_whitespace(documents[name])
        for snippet in snippets:
            if normalise_whitespace(snippet) not in document:
                failures.append(f"{name}: missing required concurrency rule: {snippet!r}")

    for name, snippets in FORBIDDEN.items():
        for snippet in snippets:
            if snippet in documents[name]:
                failures.append(f"{name}: forbidden global serialization rule remains: {snippet!r}")

    for name, text in documents.items():
        for sentence in global_serialization_directives(text):
            failures.append(f"{name}: positive global serialization directive remains: {sentence!r}")

    for example in FORBIDDEN_DIRECTIVE_EXAMPLES:
        if not global_serialization_directives(example):
            failures.append(f"detector missed forbidden example: {example!r}")

    for example in ALLOWED_DIRECTIVE_EXAMPLES:
        if global_serialization_directives(example):
            failures.append(f"detector rejected allowed example: {example!r}")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1

    print("PASS: Blender concurrency contract forbids project/machine locks and preserves exact-resource isolation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
