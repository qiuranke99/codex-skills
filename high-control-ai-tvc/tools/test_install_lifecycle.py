#!/usr/bin/env python3
"""Cross-platform destructive-safety tests, isolated entirely in temp paths."""

from __future__ import annotations

import os
import shutil
import tempfile
import sys
from pathlib import Path

import manage_skills as manager
import new_project as project_manager
import suite_common as common
from manage_skills import InstallSafetyError, _create_link, adopt_exact_links, inspect_installation, install, uninstall
from new_project import create_project
from setup_runtime import validate_venv_identity
from suite_common import REPO_ROOT, load_distribution, managed_inventory


def main() -> int:
    manifest, _requirements, skills, errors = load_distribution(REPO_ROOT)
    skills, inventory_errors = managed_inventory(manifest, skills, REPO_ROOT)
    errors.extend(inventory_errors)
    if errors:
        raise AssertionError(errors)
    excluded_names = set(manifest.get("excluded_from_aggregate_profile", []))
    managed_names = {item["name"] for item in skills}
    if excluded_names & managed_names:
        raise AssertionError("aggregate-excluded entries leaked into managed_inventory")
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
        linked_mode = "junction" if os.name == "nt" else "symlink"

        first = install(REPO_ROOT, target, "all", "copy")
        if len(first["changed"]) != len(skills):
            raise AssertionError("first install did not create every manifest skill")
        if (
            first.get("scope") != "optional_aggregate_profile"
            or first.get("controls_individual_skill_availability") is not False
        ):
            raise AssertionError("install result did not preserve the optional aggregate boundary")

        # Simulate a legacy receipt that incorrectly claimed a standalone
        # package excluded from this aggregate profile. Migration must release
        # only the receipt claim and preserve the discovery entry byte-for-byte.
        standalone_name = next(iter(excluded_names))
        standalone_source = (REPO_ROOT / standalone_name).resolve()
        standalone_entry = target / standalone_name
        _create_link(standalone_source, standalone_entry, linked_mode)
        _state_root, legacy_receipt_path = manager._state_paths(target, manifest["suite_id"])
        legacy_receipt = manager._load_receipt(legacy_receipt_path, manifest["suite_id"])
        legacy_receipt["entries"][standalone_name] = {
            "skill_name": standalone_name,
            "tier": "independent",
            "method": linked_mode,
            "source": str(standalone_source),
            "destination": str(standalone_entry),
            "installed_digest": manager._tree_digest(standalone_source),
        }
        manager._write_json_atomic(legacy_receipt_path, legacy_receipt)

        second = install(REPO_ROOT, target, "all", "copy")
        if second["changed"] or len(second["unchanged"]) != len(skills):
            raise AssertionError("copy install is not idempotent")
        if second["released_legacy_receipt_entries"] != [standalone_name]:
            raise AssertionError("legacy standalone ownership was not released from aggregate receipt")
        if standalone_entry.resolve() != standalone_source:
            raise AssertionError("aggregate install changed the standalone discovery entry")
        current_receipt = manager._load_receipt(legacy_receipt_path, manifest["suite_id"])
        if (
            current_receipt.get("scope") != "optional_aggregate_profile"
            or current_receipt.get("controls_individual_skill_availability") is not False
        ):
            raise AssertionError("install receipt did not preserve the optional aggregate boundary")
        if standalone_name in current_receipt["entries"]:
            raise AssertionError("standalone Skill remained in the aggregate install receipt")
        if not inspect_installation(REPO_ROOT, target, "all")["ready"]:
            raise AssertionError("fresh managed copy is not ready")

        changed_file = target / first_name / "SKILL.md"
        # Preserve the exact installed bytes.  Reading and rewriting through
        # text mode would silently convert LF to CRLF on Windows and make the
        # restored copy look locally modified even though its content is the
        # same to a human reviewer.
        original = changed_file.read_bytes()
        changed_file.write_bytes(original + b"\nlocal edit that must be preserved\n")
        try:
            uninstall(REPO_ROOT, target, "all")
        except InstallSafetyError:
            pass
        else:
            raise AssertionError("uninstall deleted a changed managed copy")
        if not changed_file.is_file():
            raise AssertionError("changed managed copy was not preserved")
        changed_file.write_bytes(original)

        removed = uninstall(REPO_ROOT, target, "all")
        if len(removed["removed"]) != len(skills):
            raise AssertionError("clean uninstall did not remove every aggregate-owned copy")
        if any((target / item["name"]).exists() for item in skills):
            raise AssertionError("clean uninstall left a managed skill entry")
        if not os.path.lexists(str(standalone_entry)) or standalone_entry.resolve() != standalone_source:
            raise AssertionError("aggregate uninstall removed or changed the standalone Skill")
        manager._remove_link_only(standalone_entry, linked_mode)

        linked_target = root / "Linked Discovery Root"
        if os.name == "nt":
            percent_destination = root / "Literal %TEMP% Junction" / first_name
            percent_destination.parent.mkdir()
            _create_link(REPO_ROOT / first_name, percent_destination, "junction")
            if percent_destination.resolve() != (REPO_ROOT / first_name).resolve():
                raise AssertionError("literal percent-token junction resolved to the wrong target")
            manager._remove_link_only(percent_destination, "junction")
            if os.path.lexists(str(percent_destination)):
                raise AssertionError("literal percent-token junction cleanup left a destination")
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

        alternate_repo = root / "Alternate Git Snapshot"
        shutil.copytree(
            REPO_ROOT,
            alternate_repo,
            ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache"),
        )
        alternate_skill = alternate_repo / first_name / "SKILL.md"
        alternate_skill.write_bytes(alternate_skill.read_bytes() + b"\ntransaction generation B\n")

        interrupted_target = root / "Interrupted Install Recovery"
        manager.install(REPO_ROOT, interrupted_target, "all", linked_mode)
        original_commit_stage = manager._commit_staged_entry
        commit_calls = 0

        def interrupt_after_first_commit(*args, **kwargs):
            nonlocal commit_calls
            result = original_commit_stage(*args, **kwargs)
            commit_calls += 1
            if commit_calls == 1:
                raise KeyboardInterrupt("simulated process death after first visible generation switch")
            return result

        manager._commit_staged_entry = interrupt_after_first_commit
        try:
            try:
                manager.install(alternate_repo, interrupted_target, "all", linked_mode)
            except KeyboardInterrupt:
                pass
            else:
                raise AssertionError("simulated process death did not interrupt install")
        finally:
            manager._commit_staged_entry = original_commit_stage
        interrupted_status = manager.inspect_installation(REPO_ROOT, interrupted_target, "all")
        if interrupted_status["ready"] or not any(
            "incomplete install transaction" in error for error in interrupted_status["errors"]
        ):
            raise AssertionError("mixed-generation interrupted install was not fail-closed")
        recovered_install = manager.install(alternate_repo, interrupted_target, "all", linked_mode)
        if recovered_install["recovery"]["action"] != "rolled_back_uncommitted_transaction":
            raise AssertionError("interrupted uncommitted install was not rolled back before retry")
        if not manager.inspect_installation(alternate_repo, interrupted_target, "all")["ready"]:
            raise AssertionError("recovered install did not converge on the complete new generation")
        manager.uninstall(alternate_repo, interrupted_target, "all")

        committed_cleanup_target = root / "Committed Cleanup Recovery"
        manager.install(REPO_ROOT, committed_cleanup_target, "all", linked_mode)
        original_remove_managed = manager._remove_managed_path
        cleanup_failed = False

        def fail_first_backup_cleanup(path, kind):
            nonlocal cleanup_failed
            if ".backup-" in path.name and not cleanup_failed:
                cleanup_failed = True
                raise OSError("simulated process death during committed backup cleanup")
            return original_remove_managed(path, kind)

        manager._remove_managed_path = fail_first_backup_cleanup
        try:
            committed_result = manager.install(alternate_repo, committed_cleanup_target, "all", linked_mode)
        finally:
            manager._remove_managed_path = original_remove_managed
        if not committed_result["cleanup_warnings"]:
            raise AssertionError("committed cleanup failure did not retain recovery evidence")
        finalized_install = manager.install(alternate_repo, committed_cleanup_target, "all", linked_mode)
        if finalized_install["recovery"]["action"] != "finalized_committed_transaction":
            raise AssertionError("committed install cleanup was not finalized on retry")
        if list(committed_cleanup_target.glob(".*.backup-*")) or list(
            committed_cleanup_target.glob(".*.stage-*")
        ):
            raise AssertionError("committed transaction recovery left backup or stage residue")
        manager.uninstall(alternate_repo, committed_cleanup_target, "all")

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

        original_production_check = project_manager.production_check
        project_manager.production_check = lambda *_args, **_kwargs: {
            "ready_latest": True,
            "aggregate_profile_ready": True,
            "release_commit": "f" * 40,
            "active_system_root": str(REPO_ROOT / "high-control-ai-tvc"),
            "errors": [],
        }
        project = root / "Client Projects" / "Example TVC"
        not_opted_in = root / "Client Projects" / "Not Opted In"
        try:
            create_project(not_opted_in, "Not Opted In")
        except RuntimeError as exc:
            if "--aggregate-managed" not in str(exc):
                raise
        else:
            raise AssertionError("project helper accepted a project without explicit aggregate opt-in")
        if not_opted_in.exists():
            raise AssertionError("project helper mutated a destination before aggregate opt-in")

        first_project = create_project(project, "Example TVC", aggregate_managed=True)
        second_project = create_project(project, "Example TVC", aggregate_managed=True)
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
            try:
                create_project(unrelated, "Should Fail", aggregate_managed=True)
            except RuntimeError:
                pass
            else:
                raise AssertionError("project helper adopted an unrelated non-empty directory")
        finally:
            project_manager.production_check = original_production_check
        if unrelated_sentinel.read_text(encoding="utf-8") != "preserve":
            raise AssertionError("project helper modified unrelated content")

    print("PASS: install/update/status/uninstall and project-skeleton safety lifecycle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
