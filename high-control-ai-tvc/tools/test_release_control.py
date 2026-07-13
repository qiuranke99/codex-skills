#!/usr/bin/env python3
"""Isolated regression tests for GitHub-first release activation."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import PIL  # type: ignore
import manage_skills as manager
import release_control as release


def _uuid7_for_ms(milliseconds: int) -> str:
    prefix = f"{milliseconds:012x}"
    return f"{prefix[:8]}-{prefix[8:]}-7000-8000-000000000000"


def _git(arguments: list[str], cwd: Path) -> str:
    result = release._run([release._git_executable(), *arguments], cwd=cwd)
    return result.stdout.strip()


def _write_fixture(author: Path, repository: str, remote_url: str, repository_id: int) -> None:
    skill = author / "fixture-production-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: fixture-production-skill\ndescription: Fixture production Skill.\n---\n\n# Fixture\n",
        encoding="utf-8",
        newline="\n",
    )
    independent = author / "fixture-independent-skill"
    independent.mkdir()
    (independent / "SKILL.md").write_text(
        "---\nname: fixture-independent-skill\ndescription: Fixture independent Skill.\n---\n\n# Independent\n",
        encoding="utf-8",
        newline="\n",
    )
    subsystem = author / "high-control-ai-tvc"
    (subsystem / "config").mkdir(parents=True)
    manifest = {
        "schema_version": "high-control-ai-tvc-suite.v1",
        "suite_id": release.DEFAULT_SUITE_ID,
        "source_authority": {
            "repository": repository,
            "remote_url": remote_url,
            "branch": "main",
            "github_repository_id": repository_id,
            "revision_policy": "github_main_latest_validated_immutable_snapshot",
        },
        "independent_skills": ["fixture-independent-skill"],
        "skills": [{"name": "fixture-production-skill", "tier": "core"}],
    }
    (subsystem / "SUITE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    requirements = {
        "expected_distribution": {"skill_count": 1, "core_skill_count": 1, "optional_skill_count": 0}
    }
    (subsystem / "config" / "runtime-requirements.json").write_text(
        json.dumps(requirements, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def _validation(snapshot: Path) -> dict[str, object]:
    if not (snapshot / "fixture-production-skill" / "SKILL.md").is_file():
        raise AssertionError("fixture snapshot is incomplete")
    return {
        "status": "pass",
        "command": ["fixture-validator"],
        "completed_at": release._utc_now(),
        "python_executable": str(Path(sys.executable).resolve()),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "pillow_version": PIL.__version__,
    }


def main() -> int:
    saved = {
        "CANONICAL_REPOSITORY": release.CANONICAL_REPOSITORY,
        "CANONICAL_REMOTE_URL": release.CANONICAL_REMOTE_URL,
        "CANONICAL_BRANCH": release.CANONICAL_BRANCH,
        "CANONICAL_REPOSITORY_ID": release.CANONICAL_REPOSITORY_ID,
    }
    original_thread = os.environ.get("CODEX_THREAD_ID")
    official, legacy = release.discovery_roots()
    for discovery in (official, legacy):
        state_root = release._release_state_paths(discovery, release.DEFAULT_SUITE_ID)["root"]
        if state_root != discovery.parent / ".ai-tvc-releases":
            raise AssertionError(f"known discovery root did not use the short release-state path: {state_root}")
    with tempfile.TemporaryDirectory(prefix="ai-tvc-release-test-") as temporary:
        root = Path(temporary)
        author = root / "author"
        remote = root / "authority.git"
        target = root / "discovery"
        project = root / "project"
        author.mkdir()
        _git(["init", "--initial-branch=main"], author)
        _git(["config", "user.name", "Release Test"], author)
        _git(["config", "user.email", "release-test@example.invalid"], author)
        repository = "fixture-owner/fixture-repository"
        repository_id = 424242
        remote_url = str(remote)
        _write_fixture(author, repository, remote_url, repository_id)
        _git(["add", "."], author)
        _git(["commit", "-m", "fixture A"], author)
        _git(["clone", "--bare", str(author), str(remote)], root)
        _git(["remote", "add", "origin", str(remote)], author)
        local_manifest_path = author / "high-control-ai-tvc" / "SUITE_MANIFEST.json"
        authoritative_manifest_bytes = local_manifest_path.read_bytes()
        stale_local_manifest = json.loads(authoritative_manifest_bytes.decode("utf-8"))
        stale_local_manifest["skills"] = []
        local_manifest_path.write_text(json.dumps(stale_local_manifest), encoding="utf-8")
        target.mkdir()
        link_mode = "junction" if os.name == "nt" else "symlink"
        manager._create_link(
            author / "fixture-independent-skill",
            target / "fixture-independent-skill",
            link_mode,
        )

        try:
            release.CANONICAL_REPOSITORY = repository
            release.CANONICAL_REMOTE_URL = remote_url
            release.CANONICAL_BRANCH = "main"
            release.CANONICAL_REPOSITORY_ID = repository_id

            def remote_head() -> str:
                return release._run_git(
                    ["ls-remote", "--exit-code", str(remote), "refs/heads/main"]
                ).split()[0]

            os.environ["CODEX_THREAD_ID"] = _uuid7_for_ms(int(time.time() * 1000) - 10_000)
            first = release.sync_release(
                target,
                mode="copy",
                validation_runner=_validation,
                remote_head_reader=remote_head,
                github_identity_reader=remote_head,
            )
            if not first["ready_latest"] or not first["restart_required"]:
                raise AssertionError("remote inventory was not authoritative over a stale local manifest")
            first_receipt = release._load_release_receipt(
                release._release_state_paths(target, release.DEFAULT_SUITE_ID)["receipt"]
            )
            if first_receipt.get("snapshot_write_protection", {}).get("protected") is not True:
                raise AssertionError("release receipt did not attest OS-level snapshot write protection")
            if set(first_receipt["skills"]) != {
                "fixture-production-skill",
                "fixture-independent-skill",
            }:
                raise AssertionError("manifest-declared independent Skill was omitted from release inventory")
            if first_receipt["content_equivalent_migration"]["adopted"] != ["fixture-independent-skill"]:
                raise AssertionError("pre-suite exact link was not migrated through the guarded bridge")
            local_manifest_path.write_bytes(authoritative_manifest_bytes)
            same_process = release.production_check(target, remote_head_reader=remote_head)
            if same_process["ready_latest"] or "PROCESS_RESTART_REQUIRED" not in str(same_process["errors"]):
                raise AssertionError("activating Codex task was allowed to use a potentially cached release")

            os.environ["CODEX_THREAD_ID"] = _uuid7_for_ms(int(time.time() * 1000) + 1_000)
            current = release.production_check(target, remote_head_reader=remote_head)
            if not current["ready_latest"]:
                raise AssertionError(f"fresh task could not attest the release: {current}")

            saved_transport_query = release.query_remote_head
            saved_api_query = release.query_github_identity_and_head
            try:
                release.query_remote_head = lambda: (_ for _ in ()).throw(
                    release.ReleaseControlError("Git transport is unavailable in the runtime sandbox")
                )
                release.query_github_identity_and_head = remote_head
                api_runtime = release.production_check(target)
            finally:
                release.query_remote_head = saved_transport_query
                release.query_github_identity_and_head = saved_api_query
            if not api_runtime["ready_latest"]:
                raise AssertionError(
                    f"runtime gate depended on Git transport instead of GitHub API identity: {api_runtime}"
                )

            (project / "00_project_canon").mkdir(parents=True)
            project_check = release.production_check(
                target,
                cwd=project,
                project_root=project,
                remote_head_reader=remote_head,
            )
            runtime_lock = project / "00_project_canon" / "SYSTEM_RUNTIME_LOCK.json"
            if not project_check["ready_latest"] or not runtime_lock.is_file():
                raise AssertionError("stage gate did not persist the project release lock")
            if json.loads(runtime_lock.read_text(encoding="utf-8"))["release_commit"] != first["release_commit"]:
                raise AssertionError("project runtime lock does not bind the active release")
            pending = project / "00_project_canon" / "PENDING_PROJECT_CANON_TRANSACTION.json"
            pending.write_text("{}", encoding="utf-8")
            pending_check = release.production_check(
                target,
                cwd=project,
                project_root=project,
                remote_head_reader=remote_head,
            )
            if pending_check["ready_latest"] or "PROJECT_RELEASE_MIGRATION_REQUIRED" not in str(
                pending_check["errors"]
            ):
                raise AssertionError("release migration crossed an active Project Canon transaction")
            pending.unlink()

            paths = release._release_state_paths(target, release.DEFAULT_SUITE_ID)
            receipt = release._load_release_receipt(paths["receipt"])
            snapshot = Path(receipt["snapshot_root"])
            skill_file = snapshot / "fixture-production-skill" / "SKILL.md"
            original_skill = skill_file.read_bytes()
            try:
                skill_file.write_bytes(original_skill + b"\nblocked tamper\n")
            except OSError:
                pass
            else:
                raise AssertionError("immutable snapshot accepted an ordinary write")

            # Deliberately use the release controller's maintenance-only thaw
            # path to prove that integrity checks still reject a privileged
            # mutation even if OS protection is intentionally removed.
            release._thaw_snapshot(snapshot)
            skill_file.write_bytes(original_skill + b"\ntamper\n")
            drift = release.production_check(target, remote_head_reader=remote_head)
            if drift["ready_latest"] or "SOURCE_TREE_DRIFT" not in str(drift["errors"]):
                raise AssertionError("tampered immutable snapshot was accepted")
            skill_file.write_bytes(original_skill)
            release._freeze_snapshot(snapshot)

            install_skill = target / "fixture-production-skill" / "SKILL.md"
            original_install = install_skill.read_bytes()
            install_skill.write_bytes(original_install + b"\ninstalled tamper\n")
            installed_drift = release.production_check(target, remote_head_reader=remote_head)
            if installed_drift["ready_latest"]:
                raise AssertionError("tampered installed copy was accepted")
            install_skill.write_bytes(original_install)

            project_duplicate = project / ".agents" / "skills" / "fixture-production-skill"
            project_duplicate.mkdir(parents=True)
            (project_duplicate / "SKILL.md").write_text("duplicate", encoding="utf-8")
            duplicate = release.production_check(target, cwd=project, remote_head_reader=remote_head)
            if duplicate["ready_latest"] or "DISCOVERY_AMBIGUOUS" not in str(duplicate["errors"]):
                raise AssertionError("workspace discovery shadow was accepted")
            shutil.rmtree(project)

            saved_receipt = paths["receipt"].read_bytes()
            tampered_receipt = json.loads(saved_receipt.decode("utf-8"))
            tampered_receipt["repository"]["full_name"] = "attacker/fork"
            paths["receipt"].write_text(json.dumps(tampered_receipt), encoding="utf-8")
            wrong_remote = release.production_check(target, remote_head_reader=remote_head)
            if wrong_remote["ready_latest"] or "canonical repository identity" not in str(wrong_remote["errors"]):
                raise AssertionError("wrong repository identity in receipt was accepted")
            paths["receipt"].write_bytes(saved_receipt)

            paths["lock"].write_text(
                json.dumps({"pid": os.getpid(), "host": release.socket.gethostname()}), encoding="utf-8"
            )
            concurrent = release.production_check(target, remote_head_reader=remote_head)
            if concurrent["ready_latest"] or "CONCURRENT_UPDATE" not in str(concurrent["errors"]):
                raise AssertionError("active release lock was ignored")
            paths["lock"].unlink()

            offline = release.production_check(
                target,
                remote_head_reader=lambda: (_ for _ in ()).throw(release.ReleaseControlError("REMOTE_UNVERIFIED")),
            )
            if offline["ready_latest"]:
                raise AssertionError("offline state was marked GitHub-latest")

            (author / "fixture-production-skill" / "SKILL.md").write_text(
                "---\nname: fixture-production-skill\ndescription: Fixture production Skill B.\n---\n\n# Fixture B\n",
                encoding="utf-8",
                newline="\n",
            )
            _git(["add", "."], author)
            _git(["commit", "-m", "fixture B"], author)
            _git(["push", "origin", "main"], author)
            update_required = release.production_check(target, remote_head_reader=remote_head)
            if update_required["ready_latest"] or "UPDATE_REQUIRED" not in str(update_required["errors"]):
                raise AssertionError("remote advance did not block the old release")

            second = release.sync_release(
                target,
                mode="copy",
                validation_runner=_validation,
                remote_head_reader=remote_head,
                github_identity_reader=remote_head,
            )
            if second["release_commit"] == first["release_commit"]:
                raise AssertionError("sync did not activate the advanced GitHub revision")

            unstable_value = second["release_commit"]
            old_value = first["release_commit"]
            calls = 0

            def unstable_head() -> str:
                nonlocal calls
                calls += 1
                return unstable_value if calls % 2 else old_value

            try:
                release.sync_release(
                    target,
                    mode="copy",
                    validation_runner=_validation,
                    remote_head_reader=unstable_head,
                    github_identity_reader=lambda: unstable_value,
                )
            except release.ReleaseControlError as exc:
                if "REMOTE_UNSTABLE" not in str(exc):
                    raise
            else:
                raise AssertionError("remote movement during validation was accepted")

            tree = _git(["rev-parse", "HEAD^{tree}"], author)
            rewritten = _git(["commit-tree", tree, "-m", "forced unrelated root"], author)
            _git(["push", "--force", "origin", f"{rewritten}:refs/heads/main"], author)
            try:
                release.sync_release(
                    target,
                    mode="copy",
                    validation_runner=_validation,
                    remote_head_reader=remote_head,
                    github_identity_reader=remote_head,
                )
            except release.ReleaseControlError as exc:
                if "REMOTE_HISTORY_REWRITTEN" not in str(exc):
                    raise
            else:
                raise AssertionError("non-descendant GitHub main rewrite was auto-activated")
        finally:
            test_paths = release._release_state_paths(target, release.DEFAULT_SUITE_ID)
            releases_root = test_paths["releases"]
            if releases_root.is_dir():
                for snapshot_root in releases_root.rglob("repo"):
                    if snapshot_root.is_dir():
                        release._thaw_snapshot(snapshot_root)
            for key, value in saved.items():
                setattr(release, key, value)
            if original_thread is None:
                os.environ.pop("CODEX_THREAD_ID", None)
            else:
                os.environ["CODEX_THREAD_ID"] = original_thread
    print("OK: GitHub-first release control regression tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
