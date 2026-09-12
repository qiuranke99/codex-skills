#!/usr/bin/env python3
"""Real temporary filesystem positive/negative inventory checks."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import validate_skill_inventory as inventory


class InventoryTests(unittest.TestCase):
    def fixture(self, root: Path) -> dict[str, object]:
        value = {"schema_version": "codex-skills-inventory.v1", "aggregate_profile": "retired", "skills": ["alpha", "beta_skill"]}
        (root / "SKILLS_MANIFEST.json").write_text(json.dumps(value), encoding="utf-8")
        (root / "SKILLS_INDEX.md").write_text("| Skill | Purpose |\n| --- | --- |\n| [alpha](alpha/SKILL.md) | first |\n| [beta_skill](beta_skill/SKILL.md) | second |\n", encoding="utf-8")
        for name in value["skills"]:
            directory = root / name
            directory.mkdir()
            (directory / "SKILL.md").write_text(f"---\nname: {name}\ndescription: fixture\n---\n", encoding="utf-8")
        return value

    def test_real_inventory_and_cli_pass_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(inventory.validate_inventory(root, 2)["package_count"], 2)
            completed = subprocess.run([sys.executable, "-B", str(Path(inventory.__file__)), "--repo-root", str(root), "--expected-count", "2"], capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["status"], "pass")
            after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_actual_missing_extra_identity_and_nonfile_entries_fail(self) -> None:
        for mutation in ("missing", "extra", "identity", "directory", "hidden", "retired"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.fixture(root)
                entry = root / "alpha" / "SKILL.md"
                if mutation == "missing":
                    entry.unlink()
                elif mutation == "identity":
                    entry.write_text("---\nname: impostor\n---\n", encoding="utf-8")
                elif mutation == "directory":
                    entry.unlink()
                    entry.mkdir()
                elif mutation == "retired":
                    (root / "high-control-ai-tvc").mkdir()
                else:
                    name = "extra" if mutation == "extra" else ".hidden"
                    (root / name).mkdir()
                    (root / name / "SKILL.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")
                with self.assertRaises((inventory.InventoryError, OSError)):
                    inventory.validate_inventory(root)

    def test_manifest_rejects_omission_duplicates_traversal_and_wrong_profile(self) -> None:
        for mutation in ("omission", "duplicate", "traversal", "profile", "extra_key", "not_object"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                value = self.fixture(root)
                if mutation == "omission":
                    value["skills"] = ["alpha"]
                elif mutation == "duplicate":
                    value["skills"] = ["alpha", "alpha"]
                elif mutation == "traversal":
                    value["skills"] = ["../alpha"]
                elif mutation == "profile":
                    value["aggregate_profile"] = "active"
                elif mutation == "extra_key":
                    value["other"] = True
                else:
                    value = []
                (root / "SKILLS_MANIFEST.json").write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(inventory.InventoryError):
                    inventory.validate_inventory(root)

    def test_duplicate_json_keys_and_frontmatter_names_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            path = root / "SKILLS_MANIFEST.json"
            path.write_text(path.read_text(encoding="utf-8").replace('"skills":', '"skills": [], "skills":'), encoding="utf-8")
            with self.assertRaisesRegex(inventory.InventoryError, "duplicate JSON key"):
                inventory.validate_inventory(root)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            (root / "alpha" / "SKILL.md").write_text("---\nname: alpha\nname: alpha\n---\n", encoding="utf-8")
            with self.assertRaisesRegex(inventory.InventoryError, "exactly one"):
                inventory.validate_inventory(root)

    def test_human_index_requires_real_unique_table_label_and_target(self) -> None:
        for replacement in ("", "[alpha](alpha/SKILL.md)\n", "| [alpha](beta_skill/SKILL.md) | x |\n", "| [alpha](https://example.invalid/SKILL.md) | x |\n", "| [alpha](alpha/SKILL.md) | x |\n| [alpha](alpha/SKILL.md) | y |\n", "| alpha [alias](alpha/SKILL.md) | x |\n"):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.fixture(root)
                (root / "SKILLS_INDEX.md").write_text(replacement, encoding="utf-8")
                with self.assertRaises(inventory.InventoryError):
                    inventory.validate_inventory(root)

    def test_wrong_count_and_bad_utf8_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            with self.assertRaisesRegex(inventory.InventoryError, "expected 17"):
                inventory.validate_inventory(root, 17)
            (root / "alpha" / "SKILL.md").write_bytes(b"\xff")
            with self.assertRaises(UnicodeError):
                inventory.validate_inventory(root)

    def test_redirected_entry_detection_is_cross_python_version(self) -> None:
        # The attribute branch catches Windows junctions even on Python 3.11,
        # which has no Path.is_junction; release-controller tests use real links.
        info = mock.Mock(st_mode=0o100644, st_file_attributes=0x400)
        with mock.patch.object(Path, "lstat", return_value=info):
            with self.assertRaisesRegex(inventory.InventoryError, "redirected"):
                inventory.real_entry(Path("fixture"))

    @unittest.skipIf(sys.platform == "win32", "POSIX symlink fixture; Windows reparse attributes tested separately")
    def test_real_symlink_entry_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            entry = root / "alpha" / "SKILL.md"
            entry.unlink()
            entry.symlink_to(root / "beta_skill" / "SKILL.md")
            with self.assertRaisesRegex(inventory.InventoryError, "redirected"):
                inventory.validate_inventory(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
