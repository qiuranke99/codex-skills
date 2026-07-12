#!/usr/bin/env python3
"""Safely install, inspect, update, or uninstall this suite's Codex skills."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from suite_common import (
    DEFAULT_SUITE_ID,
    REPO_ROOT,
    SuiteConfigurationError,
    load_distribution,
    other_known_discovery_root,
    select_skills,
    suite_id_from_manifest,
)


OWNER_MARKER = ".high-control-ai-tvc-owner.json"
RECEIPT_SCHEMA_VERSION = "1.0.0"


class InstallSafetyError(RuntimeError):
    """Raised when an operation cannot prove that it is safe."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _lexists(path: Path) -> bool:
    return os.path.lexists(str(path))


def _is_windows_junction(path: Path) -> bool:
    if os.name != "nt" or path.is_symlink() or not _lexists(path):
        return False
    native = getattr(os.path, "isjunction", None)
    if native is not None:
        try:
            return bool(native(str(path)))
        except OSError:
            return False
    try:
        attrs = path.stat(follow_symlinks=False).st_file_attributes
    except (AttributeError, OSError):
        return False
    return bool(attrs & 0x400) and path.is_dir()  # FILE_ATTRIBUTE_REPARSE_POINT


def _entry_kind(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if _is_windows_junction(path):
        return "junction"
    if path.is_dir():
        return "copy"
    if _lexists(path):
        return "other"
    return "missing"


def _resolved(path: Path) -> str:
    return str(path.resolve(strict=False))


def _tree_digest(root: Path, ignore_owner_marker: bool = False) -> str:
    digest = hashlib.sha256()
    if not root.is_dir():
        raise InstallSafetyError(f"cannot hash missing directory: {root}")
    for path in sorted(root.rglob("*"), key=lambda value: value.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if ignore_owner_marker and relative == OWNER_MARKER:
            continue
        if path.is_symlink():
            digest.update(b"L\0")
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(os.readlink(path).encode("utf-8"))
        elif path.is_file():
            digest.update(b"F\0")
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
    return digest.hexdigest()


def _state_paths(target: Path, suite_id: str) -> Tuple[Path, Path]:
    state_root = target / f".{suite_id}"
    return state_root, state_root / "install-receipt.json"


def _validate_receipt_storage(receipt_path: Path) -> None:
    """Reject redirected or unrelated suite state before reading or mutating it."""
    state_root = receipt_path.parent
    if _lexists(state_root):
        kind = _entry_kind(state_root)
        if kind != "copy":
            raise InstallSafetyError(
                f"suite state root must be a real local directory, not {kind}: {state_root}"
            )
        if not state_root.is_dir():
            raise InstallSafetyError(f"suite state root is not a directory: {state_root}")
    if _lexists(receipt_path):
        if receipt_path.is_symlink() or _is_windows_junction(receipt_path) or not receipt_path.is_file():
            raise InstallSafetyError(f"suite receipt must be a real regular file: {receipt_path}")
    elif _lexists(state_root):
        try:
            unexpected = [item.name for item in state_root.iterdir()]
        except OSError as exc:
            raise InstallSafetyError(f"cannot inspect suite state root {state_root}: {exc}") from exc
        if unexpected:
            raise InstallSafetyError(
                f"suite state root exists without a receipt and is not empty; refusing to adopt it: {state_root}"
            )


def _load_receipt(path: Path, suite_id: str) -> Dict[str, Any]:
    _validate_receipt_storage(path)
    if not path.is_file():
        return {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "suite_id": suite_id,
            "installed_at": None,
            "updated_at": None,
            "entries": {},
        }
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InstallSafetyError(f"managed receipt is unreadable; refusing mutation: {path}: {exc}") from exc
    if not isinstance(receipt, dict) or receipt.get("suite_id") != suite_id:
        raise InstallSafetyError(f"managed receipt has the wrong suite identity: {path}")
    if not isinstance(receipt.get("entries"), dict):
        raise InstallSafetyError(f"managed receipt entries are invalid: {path}")
    return receipt


def _write_json_atomic(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as output:
            json.dump(value, output, ensure_ascii=False, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _read_copy_marker(destination: Path) -> Dict[str, Any] | None:
    marker_path = destination / OWNER_MARKER
    if not marker_path.is_file():
        return None
    try:
        value = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _copy_is_owned(destination: Path, suite_id: str, name: str) -> bool:
    marker = _read_copy_marker(destination)
    return bool(marker and marker.get("suite_id") == suite_id and marker.get("skill_name") == name)


def _managed_entry_is_safe(
    destination: Path,
    receipt_entry: Dict[str, Any],
    suite_id: str,
    name: str,
    require_unchanged_copy: bool,
) -> Tuple[bool, str]:
    kind = _entry_kind(destination)
    recorded_method = receipt_entry.get("method")
    if kind != recorded_method:
        return False, f"entry kind changed from {recorded_method} to {kind}"
    if kind in {"symlink", "junction"}:
        recorded_source = receipt_entry.get("source")
        if not isinstance(recorded_source, str) or _resolved(destination) != _resolved(Path(recorded_source)):
            return False, "link target no longer matches the managed receipt"
        return True, "managed link target verified"
    if kind == "copy":
        if not _copy_is_owned(destination, suite_id, name):
            return False, "copy ownership marker is missing or does not match"
        if require_unchanged_copy:
            recorded_digest = receipt_entry.get("installed_digest")
            current_digest = _tree_digest(destination, ignore_owner_marker=True)
            if not isinstance(recorded_digest, str) or current_digest != recorded_digest:
                return False, "managed copy contains changes; preserving it"
        return True, "managed copy ownership verified"
    return False, f"unsupported managed entry kind: {kind}"


def _remove_link_only(path: Path, kind: str) -> None:
    if kind == "symlink":
        path.unlink()
        return
    if kind == "junction" and os.name == "nt":
        os.rmdir(path)
        return
    raise InstallSafetyError(f"refusing to remove non-link entry as {kind}: {path}")


def _create_link(source: Path, destination: Path, method: str) -> None:
    if method == "symlink":
        try:
            destination.symlink_to(source, target_is_directory=True)
        except OSError as exc:
            suffix = " On Windows, enable Developer Mode or use --mode junction/copy."
            raise InstallSafetyError(f"could not create symlink {destination}: {exc}.{suffix}") from exc
        return
    if method == "junction":
        if os.name != "nt":
            raise InstallSafetyError("junction mode is available only on Windows")
        if "%" in str(source) or "%" in str(destination):
            raise InstallSafetyError(
                "junction mode refuses literal '%' in source or destination paths because cmd.exe expands environment tokens; use a stable path without '%' or explicit copy mode"
            )
        command = f'mklink /J "{destination}" "{source}"'
        result = subprocess.run(
            ["cmd.exe", "/d", "/v:off", "/s", "/c", command],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.returncode != 0 or not _lexists(destination):
            raise InstallSafetyError(
                f"could not create junction {destination}: {result.stdout.strip()}; use --mode copy if the filesystem does not support junctions"
            )
        return
    raise InstallSafetyError(f"unsupported link method: {method}")


def _stage_entry(source: Path, destination: Path, suite_id: str, name: str, method: str) -> Tuple[Path, str]:
    stage = destination.parent / f".{name}.stage-{os.getpid()}"
    if _lexists(stage):
        raise InstallSafetyError(f"staging path already exists: {stage}")
    try:
        source_digest = _tree_digest(source)
        if method == "copy":
            shutil.copytree(source, stage, symlinks=True)
            marker = {
                "schema_version": RECEIPT_SCHEMA_VERSION,
                "suite_id": suite_id,
                "skill_name": name,
                "source_at_install": str(source.resolve()),
                "source_digest": source_digest,
            }
            _write_json_atomic(stage / OWNER_MARKER, marker)
        else:
            _create_link(source, stage, method)
            if _resolved(stage) != _resolved(source):
                raise InstallSafetyError(
                    f"staged {method} target identity mismatch: {stage} resolves to {_resolved(stage)}, expected {_resolved(source)}"
                )
        return stage, source_digest
    except Exception:
        kind = _entry_kind(stage)
        if kind in {"symlink", "junction"}:
            _remove_link_only(stage, kind)
        elif stage.is_dir():
            shutil.rmtree(stage)
        raise


def _remove_managed_path(path: Path, kind: str) -> None:
    if kind in {"symlink", "junction"}:
        _remove_link_only(path, kind)
    elif kind == "copy":
        shutil.rmtree(path)
    elif kind != "missing":
        raise InstallSafetyError(f"refusing to remove unexpected entry: {path}")


def _commit_staged_entry(stage: Path, destination: Path, old_kind: str) -> Path | None:
    """Swap one staged entry into place while retaining the prior entry.

    The caller owns the returned backup until the suite receipt has committed.
    This makes a multi-Skill install reversible as one transaction.
    """
    if old_kind == "missing":
        stage.rename(destination)
        return None
    backup = destination.parent / f".{destination.name}.backup-{os.getpid()}"
    if _lexists(backup):
        raise InstallSafetyError(f"backup path already exists: {backup}")
    destination.rename(backup)
    try:
        stage.rename(destination)
    except Exception:
        backup.rename(destination)
        raise
    return backup


def _cleanup_staged_entry(path: Path) -> None:
    kind = _entry_kind(path)
    if kind in {"symlink", "junction"}:
        _remove_link_only(path, kind)
    elif kind == "copy":
        shutil.rmtree(path)
    elif kind != "missing":
        raise InstallSafetyError(f"cannot clean unexpected staged entry: {path}")


def _rollback_install_commits(committed: List[Tuple[Path, str, Path | None]]) -> List[str]:
    """Best-effort reverse every committed destination and report any failure."""
    errors: List[str] = []
    for destination, old_kind, backup in reversed(committed):
        try:
            current_kind = _entry_kind(destination)
            if current_kind != "missing":
                _remove_managed_path(destination, current_kind)
            if backup is not None and _lexists(backup):
                backup.rename(destination)
            elif old_kind != "missing":
                raise InstallSafetyError(f"prior managed entry backup is missing: {backup}")
        except Exception as exc:
            errors.append(f"{destination}: {exc}")
    return errors


def _default_mode(requested: str) -> str:
    if requested != "auto":
        return requested
    return "junction" if os.name == "nt" else "symlink"


def _check_parallel_discovery(target: Path, names: Iterable[str]) -> List[str]:
    other = other_known_discovery_root(target)
    if other is None:
        return []
    return [name for name in names if _lexists(other / name)]


def inspect_installation(
    repo_root: Path,
    target: Path,
    profile: str,
) -> Dict[str, Any]:
    manifest, _requirements, skills, distribution_errors = load_distribution(repo_root)
    suite_id = suite_id_from_manifest(manifest)
    selected = select_skills(skills, profile)
    _state_root, receipt_path = _state_paths(target, suite_id)
    errors = list(distribution_errors)
    try:
        receipt = _load_receipt(receipt_path, suite_id)
    except InstallSafetyError as exc:
        receipt = {"entries": {}}
        errors.append(str(exc))
    receipt_entries = receipt.get("entries", {})
    results = []

    for skill in selected:
        name = skill["name"]
        destination = target / name
        kind = _entry_kind(destination)
        entry = receipt_entries.get(name)
        state = "missing"
        detail = "not installed"
        if kind != "missing" and not isinstance(entry, dict):
            state = "collision"
            detail = "entry exists but is not owned by this suite receipt"
        elif isinstance(entry, dict):
            safe, detail = _managed_entry_is_safe(
                destination, entry, suite_id, name, require_unchanged_copy=False
            )
            if not safe:
                state = "unsafe"
            elif kind == "copy":
                installed_digest = _tree_digest(destination, ignore_owner_marker=True)
                source_digest = _tree_digest(repo_root / name)
                if installed_digest != source_digest:
                    state = "out_of_date_or_modified"
                    detail = "copy differs from the current repository; update is blocked if local edits are present"
                else:
                    state = "installed"
            else:
                current_source = _resolved(repo_root / name)
                if _resolved(destination) != current_source:
                    state = "out_of_date"
                    detail = "managed link points to another checkout"
                else:
                    state = "installed"
        results.append(
            {
                "name": name,
                "tier": skill["tier"],
                "state": state,
                "method": kind,
                "target": str(destination),
                "detail": detail,
            }
        )

    duplicates = _check_parallel_discovery(target, [skill["name"] for skill in selected])
    if duplicates:
        errors.append(
            "same-name entries also exist in the other known discovery root: " + ", ".join(duplicates)
        )
    ready = not errors and all(item["state"] == "installed" for item in results)
    return {
        "schema_version": "1.0.0",
        "suite_id": suite_id,
        "repo_root": str(repo_root.resolve()),
        "target_root": str(target.expanduser().absolute()),
        "profile": profile,
        "ready": ready,
        "errors": errors,
        "parallel_discovery_duplicates": duplicates,
        "skills": results,
    }


def install(repo_root: Path, target: Path, profile: str, requested_mode: str) -> Dict[str, Any]:
    manifest, _requirements, skills, errors = load_distribution(repo_root)
    if errors:
        raise SuiteConfigurationError("; ".join(errors))
    suite_id = suite_id_from_manifest(manifest)
    selected = select_skills(skills, profile)
    mode = _default_mode(requested_mode)
    target = target.expanduser().absolute()

    duplicates = _check_parallel_discovery(target, [skill["name"] for skill in selected])
    if duplicates:
        raise InstallSafetyError(
            "installation would create duplicate discovery entries across ~/.agents/skills and ~/.codex/skills: "
            + ", ".join(duplicates)
        )

    target.mkdir(parents=True, exist_ok=True)
    state_root, receipt_path = _state_paths(target, suite_id)
    receipt = _load_receipt(receipt_path, suite_id)
    entries = receipt["entries"]

    # Complete the safety scan before making the first change.
    for skill in selected:
        name = skill["name"]
        destination = target / name
        if not _lexists(destination):
            continue
        entry = entries.get(name)
        if not isinstance(entry, dict):
            raise InstallSafetyError(f"collision at {destination}; no suite ownership receipt, so nothing was changed")
        safe, detail = _managed_entry_is_safe(
            destination, entry, suite_id, name, require_unchanged_copy=True
        )
        if not safe:
            raise InstallSafetyError(f"cannot update {destination}: {detail}")

    changed = []
    unchanged = []
    staged: List[Tuple[Dict[str, Any], Path, Path, str, Path, str]] = []
    for skill in selected:
        name = skill["name"]
        source = (repo_root / name).resolve()
        destination = target / name
        existing = entries.get(name)

        if isinstance(existing, dict) and _entry_kind(destination) == mode:
            if mode in {"symlink", "junction"} and _resolved(destination) == str(source):
                unchanged.append(name)
                continue
            if mode == "copy" and _tree_digest(destination, True) == _tree_digest(source):
                unchanged.append(name)
                continue

        old_kind = _entry_kind(destination)
        if old_kind not in {"missing", "copy", "symlink", "junction"}:
            raise InstallSafetyError(f"refusing to replace unexpected entry: {destination}")
        try:
            stage, installed_digest = _stage_entry(source, destination, suite_id, name, mode)
        except Exception:
            cleanup_errors = []
            for _skill, _source, _destination, _old_kind, prior_stage, _digest in staged:
                try:
                    _cleanup_staged_entry(prior_stage)
                except Exception as cleanup_exc:
                    cleanup_errors.append(f"{prior_stage}: {cleanup_exc}")
            if cleanup_errors:
                raise InstallSafetyError(
                    "staging failed and one or more earlier staged entries could not be cleaned: "
                    + "; ".join(cleanup_errors)
                )
            raise
        staged.append((skill, source, destination, old_kind, stage, installed_digest))
        changed.append(name)

    # Do not mutate the prior receipt until every selected Skill has staged.
    new_entries = dict(entries)
    for skill, source, destination, _old_kind, _stage, installed_digest in staged:
        name = skill["name"]
        new_entries[name] = {
            "skill_name": name,
            "tier": skill["tier"],
            "method": mode,
            "source": str(source),
            "destination": str(destination),
            "installed_digest": installed_digest,
        }

    now = _utc_now()
    new_receipt = dict(receipt)
    if new_receipt.get("installed_at") is None:
        new_receipt["installed_at"] = now
    new_receipt["updated_at"] = now
    new_receipt["schema_version"] = RECEIPT_SCHEMA_VERSION
    new_receipt["suite_id"] = suite_id
    new_receipt["repo_root"] = str(repo_root.resolve())
    new_receipt["entries"] = new_entries

    committed: List[Tuple[Path, str, Path | None]] = []
    try:
        for _skill, _source, destination, old_kind, stage, _digest in staged:
            backup = _commit_staged_entry(stage, destination, old_kind)
            committed.append((destination, old_kind, backup))
        _validate_receipt_storage(receipt_path)
        _write_json_atomic(receipt_path, new_receipt)
    except Exception as exc:
        rollback_errors = _rollback_install_commits(committed)
        cleanup_errors = []
        for _skill, _source, _destination, _old_kind, stage, _digest in staged:
            try:
                _cleanup_staged_entry(stage)
            except Exception as cleanup_exc:
                cleanup_errors.append(f"{stage}: {cleanup_exc}")
        details = rollback_errors + cleanup_errors
        if details:
            raise InstallSafetyError(
                f"install transaction failed ({exc}) and automatic rollback was incomplete: "
                + "; ".join(details)
            ) from exc
        raise InstallSafetyError(f"install transaction failed and was fully rolled back: {exc}") from exc

    cleanup_warnings = []
    for _destination, old_kind, backup in committed:
        if backup is None:
            continue
        try:
            _remove_managed_path(backup, old_kind)
        except Exception as exc:
            cleanup_warnings.append(f"committed prior-entry backup preserved at {backup}: {exc}")

    return {
        "schema_version": "1.0.0",
        "action": "install",
        "suite_id": suite_id,
        "mode": mode,
        "profile": profile,
        "target_root": str(target),
        "changed": changed,
        "unchanged": unchanged,
        "receipt": str(receipt_path),
        "cleanup_warnings": cleanup_warnings,
        "success": True,
        "next_required_action": "run the audit/preflight command before production use",
    }


def adopt_exact_links(
    repo_root: Path,
    target: Path,
    profile: str,
    allow_missing: bool = False,
) -> Dict[str, Any]:
    """Explicitly receipt exact pre-existing links; never adopt copies.

    ``allow_missing`` supports a legacy installation that predates some current
    Skill packages. Missing entries remain missing and can be created by a
    subsequent ordinary install; every existing entry must still prove an exact
    link to this checkout before the receipt is written.
    """
    manifest, _requirements, skills, errors = load_distribution(repo_root)
    if errors:
        raise SuiteConfigurationError("; ".join(errors))
    suite_id = suite_id_from_manifest(manifest)
    selected = select_skills(skills, profile)
    target = target.expanduser().absolute()
    duplicates = _check_parallel_discovery(target, [skill["name"] for skill in selected])
    if duplicates:
        raise InstallSafetyError(
            "adoption would preserve duplicate discovery entries across ~/.agents/skills and ~/.codex/skills: "
            + ", ".join(duplicates)
        )
    if not target.is_dir():
        raise InstallSafetyError(f"adoption target does not exist: {target}")
    _state_root, receipt_path = _state_paths(target, suite_id)
    receipt = _load_receipt(receipt_path, suite_id)
    entries = receipt["entries"]

    planned = []
    unchanged = []
    missing = []
    # Validate every selected entry before writing the receipt.
    for skill in selected:
        name = skill["name"]
        source = (repo_root / name).resolve()
        destination = target / name
        kind = _entry_kind(destination)
        existing = entries.get(name)
        if isinstance(existing, dict):
            safe, detail = _managed_entry_is_safe(
                destination, existing, suite_id, name, require_unchanged_copy=True
            )
            if not safe:
                raise InstallSafetyError(f"cannot retain existing receipt for {destination}: {detail}")
            unchanged.append(name)
            continue
        if kind == "missing" and allow_missing:
            missing.append(name)
            continue
        if kind not in {"symlink", "junction"}:
            raise InstallSafetyError(
                f"cannot adopt {destination}: expected an exact symlink/junction, found {kind}"
            )
        if _resolved(destination) != str(source):
            raise InstallSafetyError(
                f"cannot adopt {destination}: it resolves to {_resolved(destination)}, expected {source}"
            )
        if not (source / "SKILL.md").is_file():
            raise InstallSafetyError(f"cannot adopt {destination}: source SKILL.md is missing")
        planned.append((skill, source, destination, kind, _tree_digest(source)))

    for skill, source, destination, kind, digest in planned:
        entries[skill["name"]] = {
            "skill_name": skill["name"],
            "tier": skill["tier"],
            "method": kind,
            "source": str(source),
            "destination": str(destination),
            "installed_digest": digest,
            "adopted_exact_link": True,
        }
    if not planned and not unchanged:
        raise InstallSafetyError(
            "adoption found no exact existing links to receipt; run install instead of creating an empty adoption receipt"
        )
    now = _utc_now()
    if receipt.get("installed_at") is None:
        receipt["installed_at"] = now
    receipt.update({
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "suite_id": suite_id,
        "repo_root": str(repo_root.resolve()),
        "updated_at": now,
        "entries": entries,
    })
    _validate_receipt_storage(receipt_path)
    _write_json_atomic(receipt_path, receipt)
    return {
        "schema_version": "1.0.0",
        "action": "adopt",
        "suite_id": suite_id,
        "profile": profile,
        "target_root": str(target),
        "adopted": [item[0]["name"] for item in planned],
        "unchanged": unchanged,
        "missing_preserved": missing,
        "receipt": str(receipt_path),
        "success": True,
    }


def uninstall(repo_root: Path, target: Path, profile: str) -> Dict[str, Any]:
    manifest, _requirements, skills, errors = load_distribution(repo_root)
    if errors:
        raise SuiteConfigurationError("; ".join(errors))
    suite_id = suite_id_from_manifest(manifest)
    selected = select_skills(skills, profile)
    target = target.expanduser().absolute()
    state_root, receipt_path = _state_paths(target, suite_id)
    receipt = _load_receipt(receipt_path, suite_id)
    had_receipt = receipt_path.is_file()
    entries = receipt["entries"]

    # Prove all removals before deleting anything.
    planned = []
    already_missing = []
    for skill in selected:
        name = skill["name"]
        entry = entries.get(name)
        if not isinstance(entry, dict):
            continue
        destination = target / name
        if _entry_kind(destination) == "missing":
            if entry.get("method") not in {"copy", "symlink", "junction"}:
                raise InstallSafetyError(f"cannot recover missing {destination}: receipt method is invalid")
            planned.append((name, destination, entry["method"], True))
            already_missing.append(name)
            continue
        safe, detail = _managed_entry_is_safe(
            destination, entry, suite_id, name, require_unchanged_copy=True
        )
        if not safe:
            raise InstallSafetyError(f"cannot uninstall {destination}: {detail}")
        planned.append((name, destination, entry["method"], False))

    removed = []
    for name, destination, method, was_missing in planned:
        if not was_missing:
            if method in {"symlink", "junction"}:
                _remove_link_only(destination, method)
            elif method == "copy":
                shutil.rmtree(destination)
            else:
                raise InstallSafetyError(f"unsupported managed method in receipt: {method}")
        entries.pop(name, None)
        if not was_missing:
            removed.append(name)

        # Persist after every entry. If persistence fails after a deletion, a
        # later run recognizes the receipt-owned missing path and converges.
        receipt["updated_at"] = _utc_now()
        receipt["entries"] = entries
        _validate_receipt_storage(receipt_path)
        if entries:
            _write_json_atomic(receipt_path, receipt)
        elif receipt_path.is_file():
            receipt_path.unlink()

    if had_receipt and not entries:
        if receipt_path.is_file():
            _validate_receipt_storage(receipt_path)
            receipt_path.unlink()
        elif _lexists(receipt_path):
            _validate_receipt_storage(receipt_path)
        try:
            state_root.rmdir()
        except FileNotFoundError:
            pass
        except OSError:
            # Preserve unexpected files in the state directory.
            pass

    return {
        "schema_version": "1.0.0",
        "action": "uninstall",
        "suite_id": suite_id,
        "profile": profile,
        "target_root": str(target),
        "removed": removed,
        "receipt_owned_missing_recovered": already_missing,
        "preserved_unmanaged_entries": True,
        "success": True,
    }


def _print_text(result: Dict[str, Any]) -> None:
    action = result.get("action", "status")
    if action == "install":
        print(f"OK: installed/updated {len(result['changed'])} skill(s); {len(result['unchanged'])} already current")
        print(f"Target: {result['target_root']}")
        print(f"Method: {result['mode']}; profile: {result['profile']}")
        for warning in result.get("cleanup_warnings", []):
            print(f"WARN: {warning}")
        print("Next: run tools/install.sh audit (macOS) or tools\\install.ps1 audit (Windows).")
        return
    if action == "uninstall":
        print(f"OK: removed {len(result['removed'])} suite-owned skill entry/entries")
        print("Unmanaged entries and changed managed copies were not removed.")
        return
    if action == "adopt":
        print(f"OK: explicitly adopted {len(result['adopted'])} exact link(s); {len(result['unchanged'])} already receipt-owned")
        if result.get("missing_preserved"):
            print(f"Missing entries preserved for a later install: {len(result['missing_preserved'])}")
        print("No link target or Skill content was changed.")
        return
    print(f"Suite: {result['suite_id']}")
    print(f"Target: {result['target_root']}")
    for item in result["skills"]:
        symbol = "OK" if item["state"] == "installed" else "FAIL"
        print(f"[{symbol}] {item['name']}: {item['state']} ({item['method']})")
    for error in result["errors"]:
        print(f"[FAIL] {error}")
    print("READY" if result["ready"] else "NOT READY")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "adopt", "status", "uninstall"), nargs="?", default="install")
    parser.add_argument("--target", type=Path, default=Path.home() / ".agents" / "skills")
    parser.add_argument("--profile", choices=("all", "core"), default="all")
    parser.add_argument("--mode", choices=("auto", "junction", "symlink", "copy"), default="auto")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="for adopt only: receipt exact existing links and leave missing manifest entries for a later install",
    )
    args = parser.parse_args()

    try:
        if args.allow_missing and args.action != "adopt":
            raise InstallSafetyError("--allow-missing is valid only with the explicit adopt action")
        if args.action == "install":
            result = install(REPO_ROOT, args.target, args.profile, args.mode)
        elif args.action == "adopt":
            result = adopt_exact_links(REPO_ROOT, args.target, args.profile, args.allow_missing)
        elif args.action == "uninstall":
            result = uninstall(REPO_ROOT, args.target, args.profile)
        else:
            result = inspect_installation(REPO_ROOT, args.target, args.profile)
    except (InstallSafetyError, SuiteConfigurationError, OSError) as exc:
        result = {
            "schema_version": "1.0.0",
            "action": args.action,
            "success": False,
            "error": str(exc),
        }
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_text(result)
    if args.action == "status" and not result["ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
