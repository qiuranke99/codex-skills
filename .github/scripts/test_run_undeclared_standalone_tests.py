#!/usr/bin/env python3
"""Temporary-fixture regression tests for the retained undeclared-test runner."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import run_undeclared_standalone_tests as runner


class UndeclaredRunnerTests(unittest.TestCase):
    def package(self, root: Path, name: str, program: str) -> Path:
        package = root / name
        (package / "scripts").mkdir(parents=True)
        (package / "SKILL.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")
        (package / "scripts" / "test_contract.py").write_text(program, encoding="utf-8")
        return package

    def test_discovers_every_top_level_test_file_and_skips_declared_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = self.package(root, "first", "pass\n")
            (first / "scripts" / "test_extra.py").write_text("pass\n", encoding="utf-8")
            (first / "scripts" / "helper.py").write_text("pass\n", encoding="utf-8")
            declared = self.package(root, "declared", "raise AssertionError('must not execute twice')\n")
            (declared / "standalone-validation.json").write_text("{}\n", encoding="utf-8")
            targets, skipped = runner.discover_targets(root)
            self.assertEqual([(target.package, target.relative_test.as_posix()) for target in targets], [("first", "scripts/test_contract.py"), ("first", "scripts/test_extra.py")])
            self.assertEqual(skipped, ["declared"])

    def test_real_isolation_does_not_expose_siblings_or_mutate_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.package(root, "first", "from pathlib import Path\nimport os\nassert not Path('../sibling').exists()\nassert 'PYTHONPATH' not in os.environ\nassert Path(os.environ['HOME']).is_dir()\nPath('only-in-copy.txt').write_text('temporary')\n")
            self.package(root, "sibling", "pass\n")
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            passed, detail = runner.run_target(root, runner.TestTarget("first", Path("scripts/test_contract.py")), 10)
            self.assertTrue(passed, detail)
            after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_failure_and_timeout_are_not_reported_as_success(self) -> None:
        for program, expected in (("raise SystemExit(7)\n", "exit=7"), ("import time\ntime.sleep(2)\n", "TIMEOUT")):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.package(root, "first", program)
                passed, detail = runner.run_target(root, runner.TestTarget("first", Path("scripts/test_contract.py")), 0.2)
                self.assertFalse(passed)
                self.assertIn(expected, detail)


if __name__ == "__main__":
    unittest.main(verbosity=2)
