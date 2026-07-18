#!/usr/bin/env python3
"""Contract tests for validate_standalone_skills.py.

All fixtures live under a TemporaryDirectory.  Every test snapshots the
fixture repository before validation and asserts that validation did not
modify it.  The repo-root escape fixture also declares a malicious test that
would create an external sentinel if the validator executed it; static safety
validation must reject and skip that command.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


VALIDATOR = Path(__file__).with_name("validate_standalone_skills.py")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _metadata() -> str:
    return """\
interface:
  display_name: "Fixture Skill"
  short_description: "A deterministic standalone validation fixture."
  default_prompt: "Use this fixture only in validator tests."
policy:
  allow_implicit_invocation: false
"""


def _create_skill(
    repo_root: Path,
    name: str,
    *,
    skill_body: str,
    scripts: dict[str, str] | None = None,
    test_command: list[str] | None = None,
) -> Path:
    package = repo_root / name
    package.mkdir(parents=True)
    _write_text(
        package / "SKILL.md",
        f"""---
name: {name}
description: "Temporary standalone validator fixture."
---

# {name}

{skill_body.strip()}
""",
    )
    _write_text(package / "agents" / "openai.yaml", _metadata())
    for relative, source in (scripts or {}).items():
        _write_text(package / relative, source)
    if test_command is not None:
        _write_text(
            package / "standalone-validation.json",
            json.dumps(
                {
                    "version": 1,
                    "deterministic_test": {
                        "command": test_command,
                        "timeout_seconds": 5,
                    },
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )
    return package


def _tree_snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*"), key=lambda value: value.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            snapshot[relative + "/"] = "directory"
        elif path.is_file():
            snapshot[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            snapshot[relative] = "other"
    return snapshot


def _run_validator(repo_root: Path, expected_count: int) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    environment = dict(os.environ)
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONUTF8": "1",
        }
    )
    environment.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(VALIDATOR),
            "--repo-root",
            str(repo_root),
            "--expected-count",
            str(expected_count),
            "--timeout",
            "8",
            "--compact",
        ],
        cwd=repo_root,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - makes failures actionable
        raise AssertionError(
            f"validator did not emit JSON\nstdout={completed.stdout!r}\nstderr={completed.stderr!r}"
        ) from exc
    return completed, report


def _issue_codes(report: dict[str, Any]) -> set[str]:
    codes = {issue["code"] for issue in report.get("issues", [])}
    for package in report.get("packages", []):
        codes.update(issue["code"] for issue in package.get("issues", []))
    return codes


class StandaloneSkillValidatorTests(unittest.TestCase):
    maxDiff = None

    def test_green_isolated_package_runs_declared_deterministic_test(self) -> None:
        with tempfile.TemporaryDirectory(prefix="standalone-green-") as temporary:
            repo_root = Path(temporary) / "repo"
            repo_root.mkdir()
            _create_skill(
                repo_root,
                "green-skill",
                skill_body="Run `python scripts/test_contract.py` as the deterministic package check.",
                scripts={
                    "scripts/test_contract.py": """\
from pathlib import Path
from helper import EXPECTED_SKILL_FILE


def main() -> None:
    assert Path(EXPECTED_SKILL_FILE).is_file()
    assert Path("agents/openai.yaml").is_file()


if __name__ == "__main__":
    main()
""",
                    "scripts/helper.py": 'EXPECTED_SKILL_FILE = "SKILL.md"\n',
                },
                test_command=["{python}", "scripts/test_contract.py"],
            )
            before = _tree_snapshot(repo_root)

            completed, report = _run_validator(repo_root, 1)

            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["exit_code"], 0)
            self.assertEqual(report["summary"]["packages_total"], 1)
            self.assertEqual(report["packages"][0]["checks"]["deterministic_test"]["status"], "pass")
            self.assertEqual(_tree_snapshot(repo_root), before, "validator modified the source fixture repository")

    def test_forbidden_high_control_gate_is_red_and_non_mutating(self) -> None:
        with tempfile.TemporaryDirectory(prefix="standalone-gate-red-") as temporary:
            repo_root = Path(temporary) / "repo"
            repo_root.mkdir()
            _create_skill(
                repo_root,
                "gate-coupled-skill",
                skill_body="""
## HIGH_CONTROL_RELEASE_GATE_V2

Run `../high-control-ai-tvc/tools/release-control.ps1` and require
`SUITE_MANIFEST.json`, `ready_latest=true`, and the mandatory suite receipt.
""",
            )
            before = _tree_snapshot(repo_root)

            completed, report = _run_validator(repo_root, 1)

            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(completed.returncode, report["exit_code"])
            self.assertIn("E_FORBIDDEN_RELEASE_GATE", _issue_codes(report))
            self.assertEqual(_tree_snapshot(repo_root), before, "red gate validation wrote to the source repo")

    def test_sibling_python_import_is_red_and_non_mutating(self) -> None:
        with tempfile.TemporaryDirectory(prefix="standalone-sibling-red-") as temporary:
            repo_root = Path(temporary) / "repo"
            repo_root.mkdir()
            _create_skill(
                repo_root,
                "primary-skill",
                skill_body="Run `python scripts/check.py` for local validation.",
                scripts={
                    "scripts/check.py": """\
from sibling_skill.helper import VALUE

assert VALUE == 1
"""
                },
            )
            _create_skill(
                repo_root,
                "sibling_skill",
                skill_body="This package has no declared executable script.",
                scripts={"helper.py": "VALUE = 1\n"},
            )
            before = _tree_snapshot(repo_root)

            completed, report = _run_validator(repo_root, 2)

            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(completed.returncode, report["exit_code"])
            self.assertIn("E_SIBLING_IMPORT", _issue_codes(report))
            primary = next(package for package in report["packages"] if package["name"] == "primary-skill")
            self.assertEqual(primary["status"], "fail")
            self.assertEqual(_tree_snapshot(repo_root), before, "sibling-import validation wrote to the source repo")

    def test_repo_root_escape_is_red_skips_test_and_creates_no_external_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="standalone-root-red-") as temporary:
            repo_root = Path(temporary) / "repo"
            repo_root.mkdir()
            outside_sentinel = repo_root / "outside-write.txt"
            escaped_sentinel_literal = outside_sentinel.as_posix()
            _create_skill(
                repo_root,
                "root-coupled-skill",
                skill_body="Run `python scripts/test_escape.py` as the deterministic package check.",
                scripts={
                    "scripts/test_escape.py": f"""\
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTERNAL_SENTINEL = Path(r"{escaped_sentinel_literal}")
EXTERNAL_SENTINEL.write_text("validator executed unsafe code", encoding="utf-8")
"""
                },
                test_command=["{python}", "scripts/test_escape.py"],
            )
            before = _tree_snapshot(repo_root)

            completed, report = _run_validator(repo_root, 1)

            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(completed.returncode, report["exit_code"])
            self.assertIn("E_REPO_ROOT_PATH", _issue_codes(report))
            package = report["packages"][0]
            root_issues = [issue for issue in package["issues"] if issue["code"] == "E_REPO_ROOT_PATH"]
            self.assertTrue(
                any("parents[2]" in issue.get("evidence", "") for issue in root_issues),
                root_issues,
            )
            self.assertEqual(package["checks"]["deterministic_test"]["status"], "skipped")
            self.assertEqual(package["checks"]["deterministic_test"]["reason"], "static_safety_violation")
            self.assertFalse(outside_sentinel.exists(), "unsafe declared test escaped its isolation boundary")
            self.assertEqual(_tree_snapshot(repo_root), before, "repo-root red validation wrote to the source repo")


if __name__ == "__main__":
    unittest.main(verbosity=2)
