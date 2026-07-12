#!/usr/bin/env python3
"""Cross-platform destructive-safety tests, isolated entirely in temp paths."""

from __future__ import annotations

import os
import tempfile
import sys
from pathlib import Path

import manage_skills as manager
import suite_common as common
from manage_skills import InstallSafetyError, _create_link, adopt_exact_links, inspect_installation, install, uninstall
from new_project import create_project
from setup_runtime import validate_venv_identity
from suite_common import REPO_ROOT, load_distribution


def main() -> int:
    manifest, _requirements, skills, errors = load_distribution(REPO_ROOT)
    if errors:
        raise AssertionError(errors)
    first_name = skills[0]["name"]

    try:
        validate_venv_identity(
            Path(tempfile.gettempdir()) / "not-the-system-python-prefix",
            Path(sys.executable),
            [f"{sys.version_info.major}.{sys.version_info.minor}"],
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("runtime identity check accepted the system interpreter as a fake venv")

    with tempfile.TemporaryDirectory(prefix="ai tvc install test ") as temporary:
        root = Path(temporary)
        target = root / "Discovery Root With Spaces"

        first = install(REPO_ROOT, target, "all", "copy")
        if len(first["changed"]) != len(skills):
            raise AssertionError("first install did not create every manifest skill")
        second = install(REPO_ROOT, target, "all", "copy")
        if second["changed"] or len(second["unchanged"]) != len(skills):
            raise AssertionError("copy install is not idempotent")
        if not inspect_installation(REPO_ROOT, target, "all")["ready"]:
            raise AssertionError("fresh managed copy is not ready")

        changed_file = target / first_name / "SKILL.md"
        original = changed_file.read_text(encoding="utf-8")
        changed_file.write_text(original + "\nlocal edit that must be preserved\n", encoding="utf-8")
        try:
            uninstall(REPO_ROOT, target, "all")
        except InstallSafetyError:
            pass
        else:
            raise AssertionError("uninstall deleted a changed managed copy")
        if not changed_file.is_file():
            raise AssertionError("changed managed copy was not preserved")
        changed_file.write_text(original, encoding="utf-8")

        removed = uninstall(REPO_ROOT, target, "all")
        if len(removed["removed"]) != len(skills):
            raise AssertionError("clean uninstall did not remove every suite-owned copy")
        if any((target / item["name"]).exists() for item in skills):
            raise AssertionError("clean uninstall left a managed skill entry")

        linked_target = root / "Linked Discovery Root"
        linked_mode = "junction" if os.name == "nt" else "symlink"
        if os.name == "nt":
            percent_destination = root / "Literal %TEMP% Junction" / first_name
            percent_destination.parent.mkdir()
            try:
                _create_link(REPO_ROOT / first_name, percent_destination, "junction")
            except InstallSafetyError:
                pass
            else:
                raise AssertionError("junction creation accepted a literal percent-token path")
            if os.path.lexists(str(percent_destination)):
                raise AssertionError("rejected percent-token junction left a destination")
        install(REPO_ROOT, linked_target, "all", linked_mode)
        if not inspect_installation(REPO_ROOT, linked_target, "all")["ready"]:
            raise AssertionError(f"fresh {linked_mode} installation is not ready")
        uninstall(REPO_ROOT, linked_target, "all")
        if any(os.path.lexists(str(linked_target / item["name"])) for item in skills):
            raise AssertionError(f"{linked_mode} uninstall left a managed entry")

        adopted_target = root / "Pre-existing Exact Links"
        adopted_target.mkdir()
        for item in skills:
            _create_link(REPO_ROOT / item["name"], adopted_target / item["name"], linked_mode)
        adopted = adopt_exact_links(REPO_ROOT, adopted_target, "all")
        if len(adopted["adopted"]) != len(skills):
            raise AssertionError("explicit exact-link adoption did not receipt every Skill")
        if not inspect_installation(REPO_ROOT, adopted_target, "all")["ready"]:
            raise AssertionError("adopted exact links are not ready")
        uninstall(REPO_ROOT, adopted_target, "all")

        partial_target = root / "Partial Legacy Exact Links"
        partial_target.mkdir()
        legacy_subset = skills[:9]
        for item in legacy_subset:
            _create_link(REPO_ROOT / item["name"], partial_target / item["name"], linked_mode)
        partial = adopt_exact_links(REPO_ROOT, partial_target, "all", allow_missing=True)
        if len(partial["adopted"]) != len(legacy_subset):
            raise AssertionError("partial legacy adoption did not receipt every existing exact link")
        if len(partial["missing_preserved"]) != len(skills) - len(legacy_subset):
            raise AssertionError("partial legacy adoption did not preserve the exact missing set")
        install(REPO_ROOT, partial_target, "all", linked_mode)
        if not inspect_installation(REPO_ROOT, partial_target, "all")["ready"]:
            raise AssertionError("partial adoption followed by install is not ready")
        uninstall(REPO_ROOT, partial_target, "all")

        refused_adoption = root / "Copy Cannot Be Adopted"
        refused_entry = refused_adoption / first_name
        refused_entry.mkdir(parents=True)
        refused_sentinel = refused_entry / "SKILL.md"
        refused_sentinel.write_text("unmanaged copy", encoding="utf-8")
        try:
            adopt_exact_links(REPO_ROOT, refused_adoption, "core")
        except InstallSafetyError:
            pass
        else:
            raise AssertionError("explicit adoption accepted a normal directory/copy")
        if refused_sentinel.read_text(encoding="utf-8") != "unmanaged copy":
            raise AssertionError("refused adoption modified the collision")

        collision_target = root / "Collision Target"
        collision = collision_target / first_name
        collision.mkdir(parents=True)
        sentinel = collision / "DO_NOT_DELETE.txt"
        sentinel.write_text("unmanaged", encoding="utf-8")
        try:
            install(REPO_ROOT, collision_target, "all", "copy")
        except InstallSafetyError:
            pass
        else:
            raise AssertionError("installer adopted an unmanaged collision")
        if sentinel.read_text(encoding="utf-8") != "unmanaged":
            raise AssertionError("unmanaged collision was modified")

        staging_failure_target = root / "Injected Staging Failure"
        original_stage_entry = manager._stage_entry
        stage_call_count = 0

        def fail_second_stage(*args, **kwargs):
            nonlocal stage_call_count
            stage_call_count += 1
            if stage_call_count == 2:
                raise OSError("injected second-stage failure")
            return original_stage_entry(*args, **kwargs)

        manager._stage_entry = fail_second_stage
        try:
            try:
                manager.install(REPO_ROOT, staging_failure_target, "all", "copy")
            except OSError:
                pass
            else:
                raise AssertionError("injected staging failure did not stop install")
        finally:
            manager._stage_entry = original_stage_entry
        if any(os.path.lexists(str(staging_failure_target / item["name"])) for item in skills):
            raise AssertionError("staging failure left a visible Skill entry")
        if list(staging_failure_target.glob(".*.stage-*")):
            raise AssertionError("staging failure left a temporary staged entry")

        post_commit_receipt_failure = root / "Post Commit Receipt Failure"
        original_write_json = manager._write_json_atomic
        install_receipt_failed = False

        def fail_install_receipt(path, value):
            nonlocal install_receipt_failed
            if path.name == "install-receipt.json" and not install_receipt_failed:
                install_receipt_failed = True
                raise OSError("injected post-commit receipt failure")
            return original_write_json(path, value)

        manager._write_json_atomic = fail_install_receipt
        try:
            try:
                manager.install(REPO_ROOT, post_commit_receipt_failure, "all", "copy")
            except InstallSafetyError:
                pass
            else:
                raise AssertionError("post-commit receipt failure did not fail install")
        finally:
            manager._write_json_atomic = original_write_json
        if any(os.path.lexists(str(post_commit_receipt_failure / item["name"])) for item in skills):
            raise AssertionError("post-commit receipt failure left an unreceipted Skill entry")
        if list(post_commit_receipt_failure.glob(".*.stage-*")) or list(
            post_commit_receipt_failure.glob(".*.backup-*")
        ):
            raise AssertionError("post-commit receipt rollback left stage or backup residue")
        manager.install(REPO_ROOT, post_commit_receipt_failure, "all", "copy")
        manager.uninstall(REPO_ROOT, post_commit_receipt_failure, "all")

        receipt_failure_target = root / "Receipt Failure Rollback"
        receipt_failure_target.mkdir()
        state_blocker = receipt_failure_target / f'.{manifest["suite_id"]}'
        state_blocker.write_text("unmanaged state-root collision", encoding="utf-8")
        try:
            manager.install(REPO_ROOT, receipt_failure_target, "all", "copy")
        except InstallSafetyError:
            pass
        else:
            raise AssertionError("receipt failure did not fail the transaction")
        if any(os.path.lexists(str(receipt_failure_target / item["name"])) for item in skills):
            raise AssertionError("receipt failure left an unreceipted Skill entry")
        if state_blocker.read_text(encoding="utf-8") != "unmanaged state-root collision":
            raise AssertionError("receipt failure modified the unmanaged state-root blocker")

        state_redirect_target = root / "Redirected State Root"
        external_state = root / "Unrelated External State"
        state_redirect_target.mkdir()
        external_state.mkdir()
        external_sentinel = external_state / "DO_NOT_TOUCH.txt"
        external_sentinel.write_text("external user data", encoding="utf-8")
        _create_link(
            external_state,
            state_redirect_target / f'.{manifest["suite_id"]}',
            linked_mode,
        )
        try:
            manager.install(REPO_ROOT, state_redirect_target, "all", "copy")
        except InstallSafetyError:
            pass
        else:
            raise AssertionError("installer accepted a redirected suite state root")
        if external_sentinel.read_text(encoding="utf-8") != "external user data":
            raise AssertionError("redirected state-root refusal modified external user data")
        if (external_state / "install-receipt.json").exists():
            raise AssertionError("installer wrote a receipt through a redirected state root")

        partial_uninstall_target = root / "Partial Uninstall Recovery"
        manager.install(REPO_ROOT, partial_uninstall_target, "all", linked_mode)
        original_remove_link = manager._remove_link_only
        remove_call_count = 0

        def fail_second_remove(*args, **kwargs):
            nonlocal remove_call_count
            remove_call_count += 1
            if remove_call_count == 2:
                raise OSError("injected second-removal failure")
            return original_remove_link(*args, **kwargs)

        manager._remove_link_only = fail_second_remove
        try:
            try:
                manager.uninstall(REPO_ROOT, partial_uninstall_target, "all")
            except OSError:
                pass
            else:
                raise AssertionError("injected partial uninstall failure did not stop uninstall")
        finally:
            manager._remove_link_only = original_remove_link
        manager.uninstall(REPO_ROOT, partial_uninstall_target, "all")
        if any(os.path.lexists(str(partial_uninstall_target / item["name"])) for item in skills):
            raise AssertionError("partial uninstall could not converge on retry")

        receipt_recovery_target = root / "Removed Before Receipt Recovery"
        manager.install(REPO_ROOT, receipt_recovery_target, "all", linked_mode)
        original_write_json = manager._write_json_atomic
        write_failed = False

        def fail_first_receipt_write(path, value):
            nonlocal write_failed
            if path.name == "install-receipt.json" and not write_failed:
                write_failed = True
                raise OSError("injected receipt persistence failure")
            return original_write_json(path, value)

        manager._write_json_atomic = fail_first_receipt_write
        try:
            try:
                manager.uninstall(REPO_ROOT, receipt_recovery_target, "all")
            except OSError:
                pass
            else:
                raise AssertionError("receipt persistence failure did not stop uninstall")
        finally:
            manager._write_json_atomic = original_write_json
        recovered = manager.uninstall(REPO_ROOT, receipt_recovery_target, "all")
        if not recovered["receipt_owned_missing_recovered"]:
            raise AssertionError("uninstall did not recognize a receipt-owned missing path")
        if any(os.path.lexists(str(receipt_recovery_target / item["name"])) for item in skills):
            raise AssertionError("receipt persistence recovery left a managed Skill entry")

        official_root = root / "Discovery Identity" / ".agents" / "skills"
        legacy_root = root / "Discovery Identity" / ".codex" / "skills"
        official_root.mkdir(parents=True)
        legacy_collision = legacy_root / first_name
        legacy_collision.mkdir(parents=True)
        alias_root = root / "Discovery Identity Alias"
        _create_link(official_root, alias_root, linked_mode)
        original_discovery_roots = common.discovery_roots
        common.discovery_roots = lambda: (official_root, legacy_root)
        try:
            try:
                manager.install(REPO_ROOT, alias_root, "all", linked_mode)
            except InstallSafetyError:
                pass
            else:
                raise AssertionError("resolved discovery-root alias bypassed duplicate protection")
        finally:
            common.discovery_roots = original_discovery_roots
        if any(os.path.lexists(str(official_root / item["name"])) for item in skills):
            raise AssertionError("duplicate-protection test mutated the official discovery root")

        project = root / "Client Projects" / "Example TVC"
        first_project = create_project(project, "Example TVC")
        second_project = create_project(project, "Example TVC")
        if first_project["canon_created"] or second_project["canon_created"]:
            raise AssertionError("project helper fabricated Canon")
        if (project / "00_project_canon" / "PROJECT_CANON_MANIFEST.json").exists():
            raise AssertionError("project helper wrote a false canonical manifest")
        if not second_project["existing_preserved"]:
            raise AssertionError("project helper is not idempotent")

        unrelated = root / "Unrelated Existing Project"
        unrelated.mkdir()
        unrelated_sentinel = unrelated / "customer.txt"
        unrelated_sentinel.write_text("preserve", encoding="utf-8")
        try:
            create_project(unrelated, "Should Fail")
        except RuntimeError:
            pass
        else:
            raise AssertionError("project helper adopted an unrelated non-empty directory")
        if unrelated_sentinel.read_text(encoding="utf-8") != "preserve":
            raise AssertionError("project helper modified unrelated content")

    print("PASS: install/update/status/uninstall and project-skeleton safety lifecycle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
