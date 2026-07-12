#!/usr/bin/env python3
"""Create a non-destructive project skeleton outside the suite repository."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from suite_common import REPO_ROOT, SuiteConfigurationError, load_distribution, suite_id_from_manifest


SKELETON_VERSION = "1.1.0"
MARKER_NAME = ".ai-tvc-project.json"
DIRECTORIES = (
    "00_project_canon",
    "01_sources",
    "02_shot_contract",
    "03_canon_assets",
    "04_global_look",
    "05_storyboard",
    "06_previs",
    "outputs",
    "10_user_review",
    "99_archive",
)


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _read_marker(path: Path, suite_id: str) -> Dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or value.get("suite_id") != suite_id:
        return None
    return value


def _project_readme(name: str) -> str:
    return f"""# {name}

这是 High-Control AI TVC Production System 的项目工作区，不是 Skill 安装目录。

## 从这里开始

1. 把客户原始脚本放入 `01_sources/script/original/`，其他已获授权参考放入 `01_sources/` 的对应分类目录；保留原文件，不要覆盖。
2. 在 Codex 中打开本项目目录。
3. 设置 `<SYSTEM_ROOT>` 为当前 `codex-skills/high-control-ai-tvc` 的绝对路径，使用其 `docs/CODEX_PROMPTS.md` Master Prompt，要求 Codex 从粗脚本开始执行完整 SOP。
4. 第一阶段由 `ai-video-shot-script-director` 创建真实的 `00_project_canon/PROJECT_CANON_MANIFEST.json`。本骨架不会伪造 Canon。

## 目录职责

- `00_project_canon/`：全项目唯一 Canon；只能通过各 Skill 的原子更新合同修改。
- `01_sources/`：用户原始脚本、brief、参考图/视频及来源说明；脚本原件使用 `script/original/`。
- `02_shot_contract/`：专业镜头合同及其人类可读版本。
- `03_canon_assets/`：人物、产品、包装、材质、场景等已锁定资产包。
- `04_global_look/`：全局影调合同、Look States、Shot Deltas 与独立参考图。
- `05_storyboard/`：一镜一文件的可替换故事板及审阅板。
- `06_previs/`：V1 Timing Animatic 与 V2 Control Previs。
- `outputs/`：由 Keyframe 与 Prompt Owner 按其合同创建 K1/K2、P1/P2 package；骨架不预造假 package。
- `10_user_review/`：第三方候选证据与人工审阅意见；Codex 必须把反馈路由给唯一上游 owner。
- `99_archive/`：可选只读快照；不能冒充当前 Canon。

## 边界

本项目不默认执行付费视频生成，不包含音乐、最终剪辑、调色或独立视频成片 QC。旧 `.doc` 在 Windows 上应先用 Word 另存为 `.docx`。
"""


def create_project(destination: Path, project_name: str) -> Dict[str, Any]:
    manifest, _requirements, _skills, errors = load_distribution(REPO_ROOT)
    if errors:
        raise SuiteConfigurationError("; ".join(errors))
    suite_id = suite_id_from_manifest(manifest)
    destination = destination.expanduser().absolute()
    repo_root = REPO_ROOT.resolve()
    destination_resolved = destination.resolve(strict=False)
    if _is_within(destination_resolved, repo_root) or _is_within(repo_root, destination_resolved):
        raise RuntimeError("project directory must be outside the suite repository")

    marker_path = destination / MARKER_NAME
    if destination.exists():
        marker = _read_marker(marker_path, suite_id)
        if marker is None and any(destination.iterdir()):
            raise RuntimeError("destination is non-empty and has no matching suite project marker; refusing to adopt it")
    else:
        destination.mkdir(parents=True)

    created: List[str] = []
    existing: List[str] = []
    for relative in DIRECTORIES:
        path = destination / relative
        if path.exists() and not path.is_dir():
            raise RuntimeError(f"project skeleton collision: {path} is not a directory")
        if path.is_dir():
            existing.append(relative)
        else:
            path.mkdir()
            created.append(relative)

    readme = destination / "README.md"
    if not readme.exists():
        readme.write_text(_project_readme(project_name), encoding="utf-8")
        created.append("README.md")
    elif not readme.is_file():
        raise RuntimeError(f"project README collision: {readme}")
    else:
        existing.append("README.md")

    if not marker_path.exists():
        marker = {
            "schema_version": "ai-tvc-project-skeleton.v1",
            "skeleton_version": SKELETON_VERSION,
            "suite_id": suite_id,
            "project_name": project_name,
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "canon_initialized": False,
            "note": "This marker is not Project Canon and carries no production authority.",
        }
        marker_path.write_text(json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        created.append(MARKER_NAME)
    else:
        existing.append(MARKER_NAME)

    return {
        "schema_version": "1.0.0",
        "success": True,
        "suite_id": suite_id,
        "project_root": str(destination),
        "project_name": project_name,
        "created": created,
        "existing_preserved": existing,
        "canon_created": False,
        "customer_assets_copied": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--name", help="human-readable project name; defaults to the destination folder name")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    name = args.name or args.destination.expanduser().name
    if not name.strip():
        print("ERROR: project name cannot be empty", file=sys.stderr)
        return 2
    try:
        result = create_project(args.destination, name.strip())
    except (OSError, RuntimeError, SuiteConfigurationError) as exc:
        if args.format == "json":
            print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"OK: project skeleton ready at {result['project_root']}")
        print("No customer assets or Project Canon were created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
