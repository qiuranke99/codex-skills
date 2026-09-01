#!/usr/bin/env python3
"""Run package-local Python tests that have no standalone validation manifest.

The root isolation validator executes each package's declared
``standalone-validation.json`` command. This companion covers packages that
already contain ``scripts/test*.py`` but do not yet declare such a command.
It discovers packages from top-level ``SKILL.md`` files, copies one package at
a time into an otherwise empty discovery root, clears Python path overrides,
and runs only that copied package's tests.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class TestTarget:
    package: str
    relative_test: Path


def discover_targets(repo_root: Path) -> tuple[list[TestTarget], list[str]]:
    targets: list[TestTarget] = []
    skipped_declared: list[str] = []
    for package_root in sorted(repo_root.iterdir(), key=lambda path: path.name.casefold()):
        if not package_root.is_dir() or not (package_root / "SKILL.md").is_file():
            continue
        if (package_root / "standalone-validation.json").is_file():
            skipped_declared.append(package_root.name)
            continue
        scripts_root = package_root / "scripts"
        if not scripts_root.is_dir():
            continue
        for test_path in sorted(scripts_root.glob("test*.py"), key=lambda path: path.name.casefold()):
            if test_path.is_file() and not test_path.is_symlink():
                targets.append(TestTarget(package_root.name, test_path.relative_to(package_root)))
    return targets, skipped_declared


def isolated_environment(home: Path, temporary: Path) -> dict[str, str]:
    environment = dict(os.environ)
    for key in ("PYTHONHOME", "PYTHONPATH"):
        environment.pop(key, None)
    environment.update(
        {
            "HOME": str(home),
            "USERPROFILE": str(home),
            "CODEX_HOME": str(home / ".codex"),
            "TEMP": str(temporary),
            "TMP": str(temporary),
            "TMPDIR": str(temporary),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        }
    )
    return environment


def run_target(repo_root: Path, target: TestTarget, timeout_seconds: float) -> tuple[bool, str]:
    source_package = repo_root / target.package
    with tempfile.TemporaryDirectory(prefix="standalone-package-tests-") as raw_temporary:
        isolation_root = Path(raw_temporary).resolve(strict=True)
        discovery_root = isolation_root / "discovery"
        discovery_root.mkdir()
        copied_package = discovery_root / target.package
        shutil.copytree(
            source_package,
            copied_package,
            ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", ".git", ".venv", "venv", "node_modules"
            ),
        )
        home = isolation_root / "home"
        temporary = isolation_root / "tmp"
        home.mkdir()
        temporary.mkdir()
        command = [sys.executable, "-B", str(target.relative_test)]
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                cwd=copied_package,
                env=isolated_environment(home, temporary),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = time.monotonic() - started
            output = "\n".join(
                part
                for part in (
                    exc.stdout if isinstance(exc.stdout, str) else "",
                    exc.stderr if isinstance(exc.stderr, str) else "",
                )
                if part
            )
            return False, (
                f"TIMEOUT after {elapsed:.1f}s (limit {timeout_seconds:.1f}s)"
                + (f"\n{output}" if output else "")
            )
        elapsed = time.monotonic() - started
        output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).rstrip()
        if completed.returncode != 0:
            return False, (
                f"exit={completed.returncode} after {elapsed:.1f}s"
                + (f"\n{output}" if output else "")
            )
        return True, f"{elapsed:.1f}s"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root (defaults to two levels above this script)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=180.0,
        help="maximum seconds for each test file (default: 180)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    if not repo_root.is_dir():
        print(f"ERROR: repository root is not a directory: {repo_root}", file=sys.stderr, flush=True)
        return 2
    if args.timeout <= 0 or args.timeout > 600:
        print(
            "ERROR: timeout must be greater than zero and no more than 600 seconds",
            file=sys.stderr,
            flush=True,
        )
        return 2

    targets, skipped_declared = discover_targets(repo_root)
    failures = 0
    for target in targets:
        label = f"{target.package}/{target.relative_test.as_posix()}"
        passed, detail = run_target(repo_root, target, args.timeout)
        if passed:
            print(f"PASS {label} ({detail})", flush=True)
        else:
            failures += 1
            print(f"FAIL {label}: {detail}", file=sys.stderr, flush=True)

    print(
        "SUMMARY "
        f"tests={len(targets)} passed={len(targets) - failures} failed={failures} "
        f"packages_with_declared_validation={len(skipped_declared)}",
        flush=True,
    )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
