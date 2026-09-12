#!/usr/bin/env python3
"""Check the source manifest against real package entries and the human index.

This is a read-only source inventory check, not installation or runtime approval.
Only the inventory's simple, single-line SKILL name field is parsed here; the
separate standalone validator owns package contracts, scripts and isolation.
"""

from __future__ import annotations

import argparse
import json
import re
import stat
import sys
from pathlib import Path
from typing import Any


NAME = re.compile(r"[a-z0-9][a-z0-9_-]*")
INDEX_ENTRY = re.compile(r"\[([^\]\r\n]+)\]\(([^)\r\n]+)\)")


class InventoryError(ValueError):
    """The source inventory is incomplete, inconsistent or unsafe to inspect."""


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InventoryError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def real_entry(path: Path, *, directory: bool = False) -> None:
    info = path.lstat()
    redirected = stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )
    if redirected:
        raise InventoryError(f"redirected inventory entry is forbidden: {path}")
    expected = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not expected:
        raise InventoryError(f"expected a real {'directory' if directory else 'file'}: {path}")


def read_text(path: Path) -> str:
    real_entry(path)
    return path.read_text(encoding="utf-8")


def skill_name(path: Path) -> str:
    lines = read_text(path).splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise InventoryError(f"missing SKILL frontmatter: {path}")
    frontmatter = lines[1:lines.index("---", 1)]
    values = [line[len("name:"):].strip() for line in frontmatter if line.startswith("name:")]
    if len(values) != 1:
        raise InventoryError(f"expected exactly one top-level SKILL name: {path}")
    value = values[0]
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    if not NAME.fullmatch(value):
        raise InventoryError(f"invalid literal SKILL name: {path}")
    return value


def inventory_names(repo_root: Path) -> list[str]:
    inventory = json.loads(read_text(repo_root / "SKILLS_MANIFEST.json"), object_pairs_hook=unique_object)
    if (
        not isinstance(inventory, dict)
        or set(inventory) != {"schema_version", "aggregate_profile", "skills"}
        or inventory["schema_version"] != "codex-skills-inventory.v1"
        or inventory["aggregate_profile"] != "retired"
    ):
        raise InventoryError("invalid standalone inventory schema or aggregate profile")
    names = inventory["skills"]
    if not isinstance(names, list) or not names or not all(isinstance(name, str) and NAME.fullmatch(name) for name in names):
        raise InventoryError("skills must be a non-empty list of safe package names")
    if len(set(names)) != len(names):
        raise InventoryError("duplicate package names in inventory")
    return names


def indexed_names(repo_root: Path) -> list[str]:
    names: list[str] = []
    for number, line in enumerate(read_text(repo_root / "SKILLS_INDEX.md").splitlines(), 1):
        # Only the first column of actual table rows is an inventory entry.
        # A prose link cannot hide a missing table row or substitute a package.
        if not line.lstrip().startswith("|"):
            continue
        first_cell = line.strip().split("|", 2)[1].strip()
        link = INDEX_ENTRY.fullmatch(first_cell)
        if link is None:
            if "SKILL.md" in line or "[" in first_cell:
                raise InventoryError(f"malformed inventory table entry at line {number}")
            continue
        name, target = link.groups()
        if not NAME.fullmatch(name) or target != f"{name}/SKILL.md":
            raise InventoryError(f"inventory label/path mismatch at line {number}")
        names.append(name)
    if len(set(names)) != len(names):
        raise InventoryError("duplicate package rows in human index")
    return names


def validate_inventory(repo_root: Path, expected_count: int | None = None) -> dict[str, Any]:
    repo_root = repo_root.resolve(strict=True)
    real_entry(repo_root, directory=True)
    names = inventory_names(repo_root)
    if expected_count is not None and len(names) != expected_count:
        raise InventoryError(f"expected {expected_count} packages, inventory declares {len(names)}")
    # Include hidden top-level SKILLs and invalid entry types: neither should
    # silently disappear merely because normal discovery would ignore them.
    discovered: list[str] = []
    for child in sorted(repo_root.iterdir()):
        entry = child / "SKILL.md"
        if child.name in names or entry.exists() or entry.is_symlink():
            real_entry(child, directory=True)
            actual_name = skill_name(entry)
            if actual_name != child.name:
                raise InventoryError(f"SKILL identity differs from directory: {child.name} != {actual_name}")
            discovered.append(child.name)
    if set(names) != set(discovered):
        raise InventoryError(f"manifest/filesystem mismatch: declared-only={sorted(set(names) - set(discovered))}; disk-only={sorted(set(discovered) - set(names))}")
    indexed = indexed_names(repo_root)
    if set(names) != set(indexed):
        raise InventoryError(f"manifest/index mismatch: declared-only={sorted(set(names) - set(indexed))}; index-only={sorted(set(indexed) - set(names))}")
    if (repo_root / "high-control-ai-tvc").exists() or (repo_root / "high-control-ai-tvc").is_symlink():
        raise InventoryError("retired aggregate directory remains in current source inventory")
    return {"status": "pass", "schema_version": "codex-skills-inventory-check.v1", "package_count": len(names), "skills": sorted(names), "evidence": ["manifest_schema", "real_top_level_files", "skill_frontmatter_identity", "human_index_label_and_target", "retired_aggregate_absent"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--expected-count", type=int)
    args = parser.parse_args()
    if args.expected_count is not None and args.expected_count < 1:
        parser.error("--expected-count must be positive")
    try:
        report = validate_inventory(args.repo_root, args.expected_count)
    except (InventoryError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
