#!/usr/bin/env python3
"""Deterministic security and recovery tests for the standalone release controller."""

from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("manage_standalone_skill_release.py")
SPEC = importlib.util.spec_from_file_location("standalone_release", MODULE_PATH)
assert SPEC and SPEC.loader
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


class SimulatedCrash(BaseException):
    """Bypass the manager's ordinary exception rollback like process termination would."""


class StandaloneReleaseTests(unittest.TestCase):
    maxDiff = None

    def make_repo(self, root: Path) -> tuple[Path, str]:
        repo = root / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=repo, check=True)
        package = repo / release.SKILL_NAME
        write(
            package / "SKILL.md",
            f"---\nname: {release.SKILL_NAME}\ndescription: fixture release controller package\n---\n\n# Fixture\n",
        )
        write(
            package / "agents" / "openai.yaml",
            "interface:\n  display_name: Fixture\npolicy:\n  allow_implicit_invocation: false\n",
        )
        write(
            package / "scripts" / "test_contract.py",
            "import unittest\n"
            "class ContractTest(unittest.TestCase):\n"
            "    def test_fixture(self):\n"
            "        self.assertTrue(True)\n"
            "if __name__ == '__main__':\n"
            "    unittest.main(verbosity=2)\n",
        )
        write(
            package / "standalone-validation.json",
            json.dumps(
                {"deterministic_test": {"command": ["{python}", "scripts/test_contract.py"], "timeout_seconds": 30}}
            )
            + "\n",
        )
        write(
            repo / "independent-fixture-skill" / "SKILL.md",
            "---\nname: independent-fixture-skill\ndescription: unrelated fixture\n---\n",
        )
        write(repo / "independent-fixture-skill" / "marker.txt", "unrelated\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)
        return repo, self.head(repo)

    def head(self, repo: Path) -> str:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()

    def change_package(self, repo: Path, marker: str) -> str:
        package = repo / release.SKILL_NAME
        write(
            package / "SKILL.md",
            f"---\nname: {release.SKILL_NAME}\ndescription: fixture {marker}\n---\n\n# Fixture {marker}\n",
        )
        subprocess.run(["git", "add", str(package / "SKILL.md")], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", marker], cwd=repo, check=True)
        return self.head(repo)

    def legacy_receipt(self, receipt: dict[str, object]) -> dict[str, object]:
        value = json.loads(json.dumps(receipt))
        value["schema_version"] = release.LEGACY_RECEIPT_SCHEMA
        value["controls_aggregate_members"] = False
        value["aggregate_boundary"] = {
            "manifest_sha256": "a" * 64,
            "standalone_package_count": 21,
            "aggregate_member_count": 15,
            "aggregate_exclusion_count": 6,
            "target_excluded": True,
        }
        return value

    @contextlib.contextmanager
    def sandbox(self):
        temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        root = Path(temporary.name)
        try:
            yield root
        finally:
            discovery = root / "discovery"
            if discovery.is_dir() and not release._is_reparse(discovery):
                for entry in list(discovery.iterdir()):
                    if entry.is_symlink() or release._is_junction(entry):
                        release._remove_link(entry)
            state = root / "state"
            if state.is_dir() and not release._is_reparse(state):
                releases = state / "releases"
                if releases.is_dir() and not release._is_reparse(releases):
                    for commit_root in list(releases.iterdir()):
                        package = commit_root / "package"
                        if package.is_dir() and not release._is_reparse(package):
                            for child in list(package.rglob("*")):
                                if child.is_symlink() or release._is_junction(child):
                                    release._remove_link(child)
                            release.thaw(package)
            for entry in list(root.iterdir()):
                if entry.is_symlink() or release._is_junction(entry):
                    release._remove_link(entry)
            temporary.cleanup()

    def make_directory_link(self, link: Path, target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        link.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            powershell = shutil.which("powershell.exe") or shutil.which("pwsh") or shutil.which("powershell")
            self.assertIsNotNone(powershell)
            environment = os.environ.copy()
            environment["TEST_LINK"] = str(link)
            environment["TEST_TARGET"] = str(target)
            subprocess.run(
                [
                    str(powershell), "-NoProfile", "-NonInteractive", "-Command",
                    "New-Item -ItemType Junction -Path $env:TEST_LINK -Target $env:TEST_TARGET -ErrorAction Stop | Out-Null",
                ],
                env=environment,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        else:
            link.symlink_to(target, target_is_directory=True)
        self.assertTrue(link.is_symlink() or release._is_junction(link))

    @contextlib.contextmanager
    def offline_remote(self, commit: str, outcomes: list[object] | None = None):
        queue = list(outcomes) if outcomes is not None else None

        def observe(_repo: Path, expected: str | None = None) -> str:
            self.assertEqual(expected, commit)
            outcome = queue.pop(0) if queue is not None else commit
            if isinstance(outcome, BaseException):
                raise outcome
            return str(outcome)

        with (
            mock.patch.object(release, "remote_head", side_effect=observe) as remote,
            mock.patch.object(release, "fetch_exact") as fetch,
            mock.patch.object(release, "discovery_conflicts", return_value=[]),
        ):
            yield remote, fetch

    def sync_fixture(
        self, repo: Path, commit: str, state: Path, discovery: Path, canonical: Path | None = None
    ) -> dict[str, object]:
        with self.offline_remote(commit):
            return release.sync(repo, state, discovery, Path(sys.executable), commit, canonical)

    def test_materialize_and_verify_exact_target_tree_without_shared_inventory(self) -> None:
        with self.sandbox() as root:
            repo, commit = self.make_repo(root)
            releases = root / "releases"
            releases.mkdir()
            package = release.materialize_snapshot(repo, commit, releases)
            evidence = release.verify_snapshot(repo, commit, package)
            self.assertEqual(evidence["package_tree_oid"], release.package_tree_oid(repo, commit))
            self.assertEqual(
                {item["path"] for item in evidence["file_manifest"]},
                {"SKILL.md", "agents/openai.yaml", "scripts/test_contract.py", "standalone-validation.json"},
            )
            self.assertFalse((package / "independent-fixture-skill").exists())

    def test_snapshot_content_tamper_is_rejected(self) -> None:
        with self.sandbox() as root:
            repo, commit = self.make_repo(root)
            releases = root / "releases"
            releases.mkdir()
            package = release.materialize_snapshot(repo, commit, releases)
            (package / "SKILL.md").write_text("tamper\n", encoding="utf-8")
            with self.assertRaisesRegex(release.ReleaseError, "Git blob mismatch"):
                release.verify_snapshot(repo, commit, package)

    def test_validation_is_reproducible_and_writes_no_bytecode(self) -> None:
        with self.sandbox() as root:
            repo, _commit = self.make_repo(root)
            package = repo / release.SKILL_NAME
            first = release.run_validation(package, Path(sys.executable))
            second = release.run_validation(package, Path(sys.executable))
            self.assertEqual(first, second)
            self.assertEqual(first["deterministic_test_count"], 1)
            self.assertFalse(any(path.name == "__pycache__" for path in package.rglob("__pycache__")))

    def test_unrelated_skill_change_does_not_change_target_tree(self) -> None:
        with self.sandbox() as root:
            repo, first_commit = self.make_repo(root)
            first_tree = release.package_tree_oid(repo, first_commit)
            write(repo / "independent-fixture-skill" / "marker.txt", "changed independently\n")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "unrelated change"], cwd=repo, check=True)
            second_commit = self.head(repo)
            self.assertNotEqual(first_commit, second_commit)
            self.assertEqual(first_tree, release.package_tree_oid(repo, second_commit))
            releases = root / "releases"
            releases.mkdir()
            package = release.materialize_snapshot(repo, second_commit, releases)
            release.verify_snapshot(repo, second_commit, package)
            self.assertFalse((package / "marker.txt").exists())

    def test_real_sync_and_check_use_real_junction_acl_and_optional_canonical(self) -> None:
        with self.sandbox() as root:
            repo, commit = self.make_repo(root)
            state, discovery = root / "state", root / "discovery"
            canonical = repo / release.SKILL_NAME
            with self.offline_remote(commit) as (remote, fetch):
                result = release.sync(repo, state, discovery, Path(sys.executable), commit, canonical)
                checked = release.check(repo, state, discovery, Path(sys.executable), commit, canonical)
            self.assertEqual(result["status"], "STANDALONE_READY_LATEST")
            self.assertEqual(checked["status"], "STANDALONE_READY_LATEST")
            self.assertTrue(checked["canonical_compared"])
            self.assertTrue((discovery / release.SKILL_NAME).is_symlink() or release._is_junction(discovery / release.SKILL_NAME))
            receipt = json.loads((state / "active-release.json").read_text(encoding="utf-8"))
            protection = receipt["snapshot_write_protection"]
            self.assertEqual(protection["method"], "windows_icacls_current_sid_rx" if os.name == "nt" else "posix_no_write_bits")
            self.assertGreaterEqual(protection["checked_file_count"], 4)
            self.assertGreaterEqual(protection["checked_directory_count"], 3)
            self.assertEqual(remote.call_count, 5)
            fetch.assert_called_once_with(repo.resolve(), commit)
            self.assertFalse((state / "transaction.json").exists())

    def test_v2_receipt_is_strictly_package_scoped(self) -> None:
        with self.sandbox() as root:
            repo, commit = self.make_repo(root)
            state, discovery = root / "state", root / "discovery"
            self.sync_fixture(repo, commit, state, discovery)
            receipt = json.loads((state / "active-release.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["schema_version"], release.RECEIPT_SCHEMA)
            self.assertEqual(
                set(receipt),
                {
                    "schema_version", "skill_name", "scope", "repository",
                    "accepted_remote_commit", "release_commit", "package_tree_oid", "file_manifest",
                    "file_manifest_sha256", "snapshot_root", "snapshot_write_protection", "validation",
                    "canonical_comparison", "remote_observations", "previous_release", "rollback_active",
                    "activation",
                },
            )

    def test_legacy_active_receipt_requires_sync_and_migrates_with_rollback(self) -> None:
        with self.sandbox() as root:
            repo, first_commit = self.make_repo(root)
            state, discovery = root / "state", root / "discovery"
            self.sync_fixture(repo, first_commit, state, discovery)
            receipt_path = state / "active-release.json"
            current = json.loads(receipt_path.read_text(encoding="utf-8"))
            legacy = self.legacy_receipt(current)
            unknown = json.loads(json.dumps(legacy))
            unknown["unexpected"] = True
            with self.assertRaisesRegex(release.ReleaseError, "legacy top-level shape differs"):
                release.validate_receipt_identity(
                    unknown, release.state_paths(state), discovery, allow_legacy=True
                )
            wrong_type = json.loads(json.dumps(legacy))
            wrong_type["aggregate_boundary"]["aggregate_member_count"] = "15"
            with self.assertRaisesRegex(release.ReleaseError, "legacy release metadata differs"):
                release.validate_receipt_identity(
                    wrong_type, release.state_paths(state), discovery, allow_legacy=True
                )
            write(receipt_path, json.dumps(legacy, sort_keys=True) + "\n")
            legacy_bytes = receipt_path.read_bytes()
            prior_target = (discovery / release.SKILL_NAME).resolve(strict=True)

            with mock.patch.object(release, "remote_head") as remote:
                with self.assertRaisesRegex(release.ReleaseError, "LEGACY_RECEIPT_REQUIRES_SYNC"):
                    release.check(repo, state, discovery, Path(sys.executable), first_commit)
            remote.assert_not_called()

            second_commit = self.change_package(repo, "legacy-migration")
            outcomes: list[object] = [
                second_commit,
                second_commit,
                second_commit,
                release.ReleaseError("REMOTE_UNSTABLE: advanced"),
            ]
            with self.offline_remote(second_commit, outcomes):
                with self.assertRaisesRegex(release.ReleaseError, "REMOTE_UNSTABLE"):
                    release.sync(repo, state, discovery, Path(sys.executable), second_commit)
            self.assertEqual(receipt_path.read_bytes(), legacy_bytes)
            self.assertEqual((discovery / release.SKILL_NAME).resolve(strict=True), prior_target)
            self.assertFalse((state / "transaction.json").exists())

            with self.offline_remote(second_commit):
                result = release.sync(repo, state, discovery, Path(sys.executable), second_commit)
            migrated = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "STANDALONE_READY_LATEST")
            self.assertEqual(migrated["schema_version"], release.RECEIPT_SCHEMA)
            self.assertEqual(len(migrated), 17)
            self.assertEqual(migrated["previous_release"]["release_commit"], first_commit)

    def test_discovery_conflicts_detect_duplicate_in_another_root(self) -> None:
        with self.sandbox() as root:
            home = root / "home"
            selected = home / ".agents" / "skills"
            duplicate = home / ".codex" / "skills" / release.SKILL_NAME
            selected.mkdir(parents=True)
            duplicate.mkdir(parents=True)
            cwd = root / "project"
            cwd.mkdir()
            with (
                mock.patch.object(release.Path, "home", return_value=home),
                mock.patch.dict(os.environ, {"CODEX_HOME": ""}, clear=False),
            ):
                conflicts = release.discovery_conflicts(selected, cwd=cwd)
            self.assertTrue(any(release._same_path(Path(path), duplicate) for path in conflicts))
            self.assertFalse(
                any(
                    release._same_path(Path(path), selected / release.SKILL_NAME)
                    for path in conflicts
                )
            )

    def test_accepted_commit_mismatch_stops_before_materialization(self) -> None:
        with self.sandbox() as root:
            repo, commit = self.make_repo(root)
            state, discovery = root / "state", root / "discovery"
            with (
                mock.patch.object(
                    release, "remote_head", side_effect=release.ReleaseError("ACCEPTED_COMMIT_MISMATCH: fixture")
                ),
                mock.patch.object(release, "materialize_snapshot") as materialize,
                mock.patch.object(release, "discovery_conflicts", return_value=[]),
            ):
                with self.assertRaisesRegex(release.ReleaseError, "ACCEPTED_COMMIT_MISMATCH"):
                    release.sync(repo, state, discovery, Path(sys.executable), commit)
            materialize.assert_not_called()
            self.assertFalse((discovery / release.SKILL_NAME).exists())

    def test_invalid_commit_is_rejected_before_state_creation_and_cli_requires_commit(self) -> None:
        with self.sandbox() as root:
            repo, _commit = self.make_repo(root)
            state, discovery = root / "state", root / "discovery"
            with self.assertRaisesRegex(release.ReleaseError, "INVALID_COMMIT"):
                release.sync(repo, state, discovery, Path(sys.executable), "abc")
            self.assertFalse(state.exists())
            with self.assertRaises(SystemExit):
                release.parser().parse_args(["sync"])

    def test_receipt_executable_tamper_is_rejected_before_remote_or_execution(self) -> None:
        with self.sandbox() as root:
            repo, commit = self.make_repo(root)
            state, discovery = root / "state", root / "discovery"
            self.sync_fixture(repo, commit, state, discovery)
            receipt_path = state / "active-release.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            fake = root / "benign-but-unaccepted-python.exe"
            fake.write_bytes(b"not executable")
            receipt["validation"]["python_executable"] = str(fake)
            write(receipt_path, json.dumps(receipt, sort_keys=True) + "\n")
            with (
                mock.patch.object(release, "run_validation") as validation,
                mock.patch.object(release, "remote_head") as remote,
                mock.patch.object(release, "discovery_conflicts", return_value=[]),
            ):
                with self.assertRaisesRegex(release.ReleaseError, "validation executable differs"):
                    release.check(repo, state, discovery, Path(sys.executable), commit)
            validation.assert_not_called()
            remote.assert_not_called()

    def test_receipt_full_acl_evidence_tamper_is_rejected_before_execution(self) -> None:
        with self.sandbox() as root:
            repo, commit = self.make_repo(root)
            state, discovery = root / "state", root / "discovery"
            self.sync_fixture(repo, commit, state, discovery)
            receipt_path = state / "active-release.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["snapshot_write_protection"]["checked_file_count"] += 1
            write(receipt_path, json.dumps(receipt, sort_keys=True) + "\n")
            with (
                mock.patch.object(release, "run_validation") as validation,
                mock.patch.object(release, "remote_head") as remote,
                mock.patch.object(release, "discovery_conflicts", return_value=[]),
            ):
                with self.assertRaisesRegex(release.ReleaseError, "write protection evidence"):
                    release.check(repo, state, discovery, Path(sys.executable), commit)
            validation.assert_not_called()
            remote.assert_not_called()

    def test_state_root_reparse_is_rejected_before_remote(self) -> None:
        with self.sandbox() as root:
            repo, commit = self.make_repo(root)
            actual_state = root / "external-state"
            state = root / "state"
            self.make_directory_link(state, actual_state)
            with mock.patch.object(release, "remote_head") as remote:
                with self.assertRaisesRegex(release.ReleaseError, "state root.*redirected"):
                    release.sync(repo, state, root / "discovery", Path(sys.executable), commit)
            remote.assert_not_called()
            release._remove_link(state)

    def test_snapshot_package_reparse_is_rejected_even_when_content_matches(self) -> None:
        with self.sandbox() as root:
            repo, commit = self.make_repo(root)
            releases = root / "releases"
            releases.mkdir()
            package = release.materialize_snapshot(repo, commit, releases)
            external = root / "external-package"
            shutil.copytree(package, external)
            shutil.rmtree(package)
            self.make_directory_link(package, external)
            with self.assertRaisesRegex(release.ReleaseError, "snapshot package must be a real directory"):
                release.verify_snapshot(repo, commit, package)
            release._remove_link(package)

    def test_snapshot_child_reparse_escape_is_rejected(self) -> None:
        with self.sandbox() as root:
            repo, commit = self.make_repo(root)
            releases = root / "releases"
            releases.mkdir()
            package = release.materialize_snapshot(repo, commit, releases)
            child = package / "escape"
            self.make_directory_link(child, root / "outside")
            with self.assertRaisesRegex(release.ReleaseError, "contains a reparse point"):
                release.verify_snapshot(repo, commit, package)
            release._remove_link(child)

    def test_snapshot_stage_reparse_is_rejected(self) -> None:
        with self.sandbox() as root:
            repo, commit = self.make_repo(root)
            releases = root / "releases"
            releases.mkdir()
            commit_root = releases / commit
            commit_root.mkdir()
            fixed = mock.Mock(hex="a" * 32)
            stage = commit_root / f".stage-{fixed.hex}"
            self.make_directory_link(stage, root / "outside-stage")
            with mock.patch.object(release.uuid, "uuid4", return_value=fixed):
                with self.assertRaisesRegex(release.ReleaseError, "snapshot staging root must be a real directory"):
                    release.materialize_snapshot(repo, commit, releases)
            release._remove_link(stage)

    def test_trusted_python_reparse_parent_is_rejected(self) -> None:
        with self.sandbox() as root:
            actual = root / "python-real"
            actual.mkdir()
            executable = actual / Path(sys.executable).name
            shutil.copy2(sys.executable, executable)
            linked = root / "python-linked"
            self.make_directory_link(linked, actual)
            with self.assertRaisesRegex(release.ReleaseError, "trusted Python.*redirected"):
                release.trusted_python(linked / executable.name)
            release._remove_link(linked)

    @unittest.skipIf(os.name == "nt", "POSIX executable aliases may be symlinks; Windows reparse executables stay forbidden")
    def test_trusted_python_allows_final_posix_symlink(self) -> None:
        with self.sandbox() as root:
            alias = root / "python-alias"
            alias.symlink_to(Path(sys.executable).resolve())
            self.assertEqual(release.trusted_python(alias), Path(sys.executable).resolve())

    def test_active_receipt_write_failure_atomically_restores_prior_release(self) -> None:
        with self.sandbox() as root:
            repo, first_commit = self.make_repo(root)
            state, discovery = root / "state", root / "discovery"
            self.sync_fixture(repo, first_commit, state, discovery)
            prior_receipt = (state / "active-release.json").read_bytes()
            prior_target = (discovery / release.SKILL_NAME).resolve(strict=True)
            second_commit = self.change_package(repo, "second")
            original_atomic_json = release._atomic_json

            def fail_active(path: Path, value: dict[str, object]) -> None:
                if release._same_path(path, state / "active-release.json"):
                    raise OSError("simulated receipt write failure")
                original_atomic_json(path, value)

            with self.offline_remote(second_commit), mock.patch.object(release, "_atomic_json", side_effect=fail_active):
                with self.assertRaisesRegex(OSError, "simulated receipt write failure"):
                    release.sync(repo, state, discovery, Path(sys.executable), second_commit)
            self.assertEqual((state / "active-release.json").read_bytes(), prior_receipt)
            self.assertEqual((discovery / release.SKILL_NAME).resolve(strict=True), prior_target)
            self.assertFalse((state / "transaction.json").exists())

    def test_post_activation_remote_advance_rolls_back_first_install(self) -> None:
        with self.sandbox() as root:
            repo, commit = self.make_repo(root)
            state, discovery = root / "state", root / "discovery"
            outcomes: list[object] = [commit, commit, commit, release.ReleaseError("REMOTE_UNSTABLE: advanced")]
            with self.offline_remote(commit, outcomes):
                with self.assertRaisesRegex(release.ReleaseError, "REMOTE_UNSTABLE"):
                    release.sync(repo, state, discovery, Path(sys.executable), commit)
            self.assertFalse(release._lexists(discovery / release.SKILL_NAME))
            self.assertFalse((state / "active-release.json").exists())
            self.assertFalse((state / "transaction.json").exists())

    def test_process_restart_recovers_crash_to_last_verified_release(self) -> None:
        with self.sandbox() as root:
            repo, first_commit = self.make_repo(root)
            state, discovery = root / "state", root / "discovery"
            self.sync_fixture(repo, first_commit, state, discovery)
            prior_receipt = (state / "active-release.json").read_bytes()
            prior_target = (discovery / release.SKILL_NAME).resolve(strict=True)
            second_commit = self.change_package(repo, "crash-candidate")

            def crash(point: str) -> None:
                if point == "after_new_active":
                    raise SimulatedCrash("simulated process termination")

            with self.offline_remote(second_commit), mock.patch.object(release, "_fault", side_effect=crash):
                with self.assertRaises(SimulatedCrash):
                    release.sync(repo, state, discovery, Path(sys.executable), second_commit)
            self.assertTrue((state / "transaction.json").is_file())
            with (
                mock.patch.object(release, "remote_head", side_effect=release.ReleaseError("STOP_AFTER_RECOVERY")),
                mock.patch.object(release, "fetch_exact"),
                mock.patch.object(release, "discovery_conflicts", return_value=[]),
            ):
                with self.assertRaisesRegex(release.ReleaseError, "STOP_AFTER_RECOVERY"):
                    release.sync(repo, state, discovery, Path(sys.executable), second_commit)
            self.assertFalse((state / "transaction.json").exists())
            self.assertEqual((state / "active-release.json").read_bytes(), prior_receipt)
            self.assertEqual((discovery / release.SKILL_NAME).resolve(strict=True), prior_target)

    def test_process_restart_recovers_legacy_candidate_journal(self) -> None:
        with self.sandbox() as root:
            repo, first_commit = self.make_repo(root)
            state, discovery = root / "state", root / "discovery"
            self.sync_fixture(repo, first_commit, state, discovery)
            prior_receipt = (state / "active-release.json").read_bytes()
            prior_target = (discovery / release.SKILL_NAME).resolve(strict=True)
            second_commit = self.change_package(repo, "legacy-crash-candidate")

            def crash(point: str) -> None:
                if point == "after_new_active":
                    raise SimulatedCrash("simulated process termination")

            with self.offline_remote(second_commit), mock.patch.object(release, "_fault", side_effect=crash):
                with self.assertRaises(SimulatedCrash):
                    release.sync(repo, state, discovery, Path(sys.executable), second_commit)
            journal_path = state / "transaction.json"
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
            journal["candidate"]["receipt"] = self.legacy_receipt(journal["candidate"]["receipt"])
            write(journal_path, json.dumps(journal, sort_keys=True) + "\n")

            with (
                mock.patch.object(release, "remote_head", side_effect=release.ReleaseError("STOP_AFTER_RECOVERY")),
                mock.patch.object(release, "fetch_exact"),
                mock.patch.object(release, "discovery_conflicts", return_value=[]),
            ):
                with self.assertRaisesRegex(release.ReleaseError, "STOP_AFTER_RECOVERY"):
                    release.sync(repo, state, discovery, Path(sys.executable), second_commit)
            self.assertFalse(journal_path.exists())
            self.assertEqual((state / "active-release.json").read_bytes(), prior_receipt)
            self.assertEqual((discovery / release.SKILL_NAME).resolve(strict=True), prior_target)

    def test_check_refuses_unrecovered_journal(self) -> None:
        with self.sandbox() as root:
            repo, commit = self.make_repo(root)
            state, discovery = root / "state", root / "discovery"
            self.sync_fixture(repo, commit, state, discovery)
            write(state / "transaction.json", "{}\n")
            with mock.patch.object(release, "remote_head") as remote:
                with self.assertRaisesRegex(release.ReleaseError, "TRANSACTION_RECOVERY_REQUIRED"):
                    release.check(repo, state, discovery, Path(sys.executable), commit)
            remote.assert_not_called()

    def test_release_lock_excludes_concurrent_update(self) -> None:
        with self.sandbox() as root:
            paths = release.prepare_state(root / "state")
            with release._release_lock(paths):
                with self.assertRaisesRegex(release.ReleaseError, "CONCURRENT_UPDATE"):
                    with release._release_lock(paths):
                        self.fail("second lock acquisition must not succeed")
            self.assertFalse(paths["lock"].exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
