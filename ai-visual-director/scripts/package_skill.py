#!/usr/bin/env python3
"""Package the self-contained ai-visual-director skill as a tar.gz archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path


EXCLUDE_DIRS = {"__pycache__", ".pytest_cache"}
EXCLUDE_SUFFIXES = {".pyc", ".tmp"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(skill_dir: Path):
    for path in sorted(skill_dir.rglob("*")):
        if path.is_dir():
            continue
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        if path.suffix in EXCLUDE_SUFFIXES:
            continue
        yield path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument("--out", type=Path, default=Path("dist"))
    args = parser.parse_args()

    skill_dir = args.skill_dir.resolve()
    if not (skill_dir / "SKILL.md").exists():
        raise SystemExit(f"missing SKILL.md in {skill_dir}")

    skill_name = skill_dir.name
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_path = out_dir / f"{skill_name}-{timestamp}.tar.gz"
    manifest_path = out_dir / f"{skill_name}-{timestamp}.manifest.json"

    files = []
    with tarfile.open(archive_path, "w:gz") as tar:
        for path in iter_files(skill_dir):
            arcname = Path(skill_name) / path.relative_to(skill_dir)
            tar.add(path, arcname=str(arcname))
            files.append({
                "path": str(arcname),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            })

    manifest = {
        "skill_name": skill_name,
        "created_at_utc": timestamp,
        "archive": archive_path.name,
        "file_count": len(files),
        "files": files,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "archive": str(archive_path),
        "manifest": str(manifest_path),
        "file_count": len(files),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
