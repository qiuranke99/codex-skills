#!/usr/bin/env python3
"""GitHub-first activation for the explicitly selected High-Control aggregate profile."""

from __future__ import annotations

import argparse
import csv
import errno
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Tuple

from manage_skills import (
    InstallSafetyError,
    RECEIPT_SCHEMA_VERSION,
    _entry_kind,
    _lexists,
    _load_receipt,
    _read_json_object,
    _state_paths,
    _tree_digest,
    _write_json_atomic,
    adopt_content_equivalent_links,
    inspect_installation,
    install,
)
from suite_common import (
    DEFAULT_SUITE_ID,
    SuiteConfigurationError,
    discovery_roots,
    load_distribution,
    managed_inventory,
    select_skills,
    suite_id_from_manifest,
)


CANONICAL_REPOSITORY = "qiuranke99/codex-skills"
CANONICAL_REMOTE_URL = "https://github.com/qiuranke99/codex-skills.git"
CANONICAL_BRANCH = "main"
CANONICAL_REPOSITORY_ID = 1264973746
RELEASE_SCHEMA_VERSION = "high-control-ai-tvc-release-receipt.v2"
RELEASE_STATE_SCHEMA_VERSION = "high-control-ai-tvc-release-state.v1"
MAX_REMOTE_STABILITY_ATTEMPTS = 3


class ReleaseControlError(RuntimeError):
    """Raised when optional aggregate release evidence cannot be proved."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _codex_thread_created_ms(thread_id: str) -> int:
    try:
        parsed = uuid.UUID(thread_id)
    except (ValueError, AttributeError) as exc:
        raise ReleaseControlError(f"PROCESS_RESTART_REQUIRED: invalid CODEX_THREAD_ID: {thread_id!r}") from exc
    if parsed.version != 7:
        raise ReleaseControlError(f"PROCESS_RESTART_REQUIRED: CODEX_THREAD_ID is not UUIDv7: {thread_id}")
    return int(parsed.hex[:12], 16)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(
    command: List[str],
    *,
    cwd: Path | None = None,
    timeout: int = 120,
    env: Dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd is not None else None,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReleaseControlError(f"command could not run: {command[0]}: {exc}") from exc
    if result.returncode != 0:
        detail = result.stdout.strip()[-4000:]
        raise ReleaseControlError(
            f"command failed with exit {result.returncode}: {' '.join(command)}\n{detail}"
        )
    return result


def _git_executable() -> str:
    git = shutil.which("git")
    if not git:
        raise ReleaseControlError("git is required but was not found in PATH")
    return git


def _run_git(
    arguments: List[str],
    *,
    git_dir: Path | None = None,
    timeout: int = 120,
) -> str:
    command = [_git_executable()]
    if git_dir is not None:
        command.extend(["--git-dir", str(git_dir)])
    command.extend(arguments)
    return _run(command, timeout=timeout).stdout.strip()


def normalize_remote_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    if normalized.startswith("git@github.com:"):
        normalized = "https://github.com/" + normalized[len("git@github.com:") :]
    if normalized.startswith("ssh://git@github.com/"):
        normalized = "https://github.com/" + normalized[len("ssh://git@github.com/") :]
    return normalized.lower()


def _assert_canonical_manifest(manifest: Dict[str, Any]) -> None:
    authority = manifest.get("source_authority")
    expected = {
        "repository": CANONICAL_REPOSITORY,
        "remote_url": CANONICAL_REMOTE_URL,
        "branch": CANONICAL_BRANCH,
        "github_repository_id": CANONICAL_REPOSITORY_ID,
        "revision_policy": "github_main_latest_validated_immutable_snapshot",
    }
    if not isinstance(authority, dict):
        raise ReleaseControlError("SUITE_MANIFEST.json source_authority is missing")
    for key, wanted in expected.items():
        actual = authority.get(key)
        if key == "remote_url" and isinstance(actual, str):
            if normalize_remote_url(actual) == normalize_remote_url(str(wanted)):
                continue
        if actual != wanted:
            raise ReleaseControlError(
                f"SUITE_MANIFEST.json source_authority.{key}={actual!r}; expected {wanted!r}"
            )
    if "source_commit" in manifest:
        raise ReleaseControlError(
            "SUITE_MANIFEST.json must not use self-referential source_commit; release commits belong in runtime receipts"
        )


def _release_state_paths(target: Path, suite_id: str) -> Dict[str, Path]:
    target = target.expanduser().absolute()
    official, legacy = discovery_roots()
    known = {
        os.path.normcase(str(official.expanduser().resolve(strict=False))),
        os.path.normcase(str(legacy.expanduser().resolve(strict=False))),
    }
    identity = os.path.normcase(str(target.resolve(strict=False)))
    suffix = "" if identity in known else "-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:8]
    root = target.parent / f".ai-tvc-releases{suffix}"
    return {
        "root": root,
        "marker": root / "release-state.json",
        "lock": root / "release.lock",
        "cache": root / "cache.git",
        "releases": root / "releases",
        "receipt": root / "release-receipt.json",
    }


def _validate_real_directory(path: Path, label: str) -> None:
    if _lexists(path):
        kind = _entry_kind(path)
        if kind != "copy" or not path.is_dir():
            raise ReleaseControlError(f"{label} must be a real local directory, not {kind}: {path}")


def _prepare_release_state(target: Path, suite_id: str) -> Dict[str, Path]:
    paths = _release_state_paths(target, suite_id)
    target.mkdir(parents=True, exist_ok=True)
    _validate_real_directory(paths["root"], "release state root")
    if not paths["root"].exists():
        paths["root"].mkdir()
    marker = paths["marker"]
    if marker.exists():
        if marker.is_symlink() or not marker.is_file():
            raise ReleaseControlError(f"release state marker must be a regular file: {marker}")
        try:
            value = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ReleaseControlError(f"release state marker is unreadable: {marker}: {exc}") from exc
        if value.get("schema_version") != RELEASE_STATE_SCHEMA_VERSION or value.get("suite_id") != suite_id:
            raise ReleaseControlError(f"release state marker has the wrong identity: {marker}")
    else:
        unexpected = [item.name for item in paths["root"].iterdir()]
        if unexpected:
            raise ReleaseControlError(
                f"release state root exists without its marker and is not empty: {paths['root']}"
            )
        _write_json_atomic(
            marker,
            {
                "schema_version": RELEASE_STATE_SCHEMA_VERSION,
                "suite_id": suite_id,
                "canonical_repository": CANONICAL_REPOSITORY,
                "created_at": _utc_now(),
            },
        )
    for key in ("cache", "releases"):
        _validate_real_directory(paths[key], key)
    paths["releases"].mkdir(exist_ok=True)
    return paths


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


@contextmanager
def _release_lock(paths: Dict[str, Path]) -> Iterator[None]:
    lock_path = paths["lock"]
    payload = {
        "schema_version": "high-control-ai-tvc-release-lock.v1",
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "created_at": _utc_now(),
    }
    for _attempt in range(2):
        try:
            descriptor = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            try:
                existing = json.loads(lock_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ReleaseControlError(f"CONCURRENT_UPDATE: unreadable release lock: {lock_path}: {exc}") from exc
            owner_pid = existing.get("pid")
            owner_host = existing.get("host")
            if owner_host == socket.gethostname() and isinstance(owner_pid, int) and not _pid_alive(owner_pid):
                lock_path.unlink()
                continue
            raise ReleaseControlError(
                f"CONCURRENT_UPDATE: release transaction already active on {owner_host} pid={owner_pid}"
            )
        else:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            break
    else:
        raise ReleaseControlError("CONCURRENT_UPDATE: could not acquire the release lock")
    try:
        yield
    finally:
        try:
            current = json.loads(lock_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            current = {}
        if current.get("pid") == os.getpid() and current.get("host") == socket.gethostname():
            lock_path.unlink(missing_ok=True)


def _assert_no_url_rewrite() -> None:
    git = _git_executable()
    result = subprocess.run(
        [git, "config", "--global", "--get-regexp", r"^url\..*\.insteadof$"],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise ReleaseControlError(f"cannot inspect Git URL rewrite configuration: {result.stdout.strip()}")
    canonical = CANONICAL_REMOTE_URL.lower()
    for line in result.stdout.splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2 and canonical.startswith(parts[1].strip().lower()):
            raise ReleaseControlError(
                f"WRONG_REMOTE: a global Git insteadOf rule rewrites the canonical GitHub URL: {line.strip()}"
            )


def query_remote_head() -> str:
    _assert_no_url_rewrite()
    try:
        output = _run_git(
            ["ls-remote", "--exit-code", CANONICAL_REMOTE_URL, f"refs/heads/{CANONICAL_BRANCH}"],
            timeout=90,
        )
    except ReleaseControlError as exc:
        raise ReleaseControlError(f"REMOTE_UNVERIFIED: {exc}") from exc
    fields = output.split()
    if len(fields) < 2 or fields[1] != f"refs/heads/{CANONICAL_BRANCH}":
        raise ReleaseControlError(f"REMOTE_UNVERIFIED: unexpected ls-remote response: {output!r}")
    commit = fields[0].lower()
    if len(commit) not in (40, 64) or any(character not in "0123456789abcdef" for character in commit):
        raise ReleaseControlError(f"REMOTE_UNVERIFIED: invalid Git object id: {commit!r}")
    return commit


def query_github_identity_and_head() -> str:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "high-control-ai-tvc-release-control",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not github_token:
        gh = shutil.which("gh")
        if gh:
            try:
                token_result = subprocess.run(
                    [gh, "auth", "token"],
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    timeout=15,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError):
                token_result = None
            if token_result is not None and token_result.returncode == 0:
                github_token = token_result.stdout.strip()
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    def read_json(url: str) -> Dict[str, Any]:
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                value = json.loads(response.read().decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, urllib.error.URLError) as exc:
            raise ReleaseControlError(f"REMOTE_UNVERIFIED: GitHub API request failed: {url}: {exc}") from exc
        if not isinstance(value, dict):
            raise ReleaseControlError(f"REMOTE_UNVERIFIED: GitHub API returned a non-object: {url}")
        return value

    repository = read_json(f"https://api.github.com/repos/{CANONICAL_REPOSITORY}")
    if (
        repository.get("id") != CANONICAL_REPOSITORY_ID
        or str(repository.get("full_name", "")).lower() != CANONICAL_REPOSITORY.lower()
        or repository.get("default_branch") != CANONICAL_BRANCH
    ):
        raise ReleaseControlError("WRONG_REMOTE: GitHub repository identity does not match the suite authority")
    reference = read_json(
        f"https://api.github.com/repos/{CANONICAL_REPOSITORY}/git/ref/heads/{CANONICAL_BRANCH}"
    )
    object_value = reference.get("object")
    commit = object_value.get("sha") if isinstance(object_value, dict) else None
    if not isinstance(commit, str):
        raise ReleaseControlError("REMOTE_UNVERIFIED: GitHub ref response lacks a commit sha")
    return commit.lower()


def _ensure_cache(cache: Path) -> None:
    _validate_real_directory(cache, "Git object cache")
    if not cache.exists():
        _run([_git_executable(), "init", "--bare", str(cache)])
    bare = _run_git(["rev-parse", "--is-bare-repository"], git_dir=cache)
    if bare != "true":
        raise ReleaseControlError(f"Git object cache is not bare: {cache}")


def _fetch_exact(cache: Path, commit: str) -> None:
    _ensure_cache(cache)
    refspec = f"+refs/heads/{CANONICAL_BRANCH}:refs/remotes/origin/{CANONICAL_BRANCH}"
    _run_git(["fetch", "--force", "--no-tags", CANONICAL_REMOTE_URL, refspec], git_dir=cache, timeout=300)
    fetched = _run_git(["rev-parse", f"refs/remotes/origin/{CANONICAL_BRANCH}"], git_dir=cache).lower()
    if fetched != commit:
        raise ReleaseControlError(f"REMOTE_HEAD_CHANGED_DURING_FETCH: expected {commit}, fetched {fetched}")
    _run_git(["cat-file", "-e", f"{commit}^{{commit}}"], git_dir=cache)


def _git_is_ancestor(cache: Path, ancestor: str, descendant: str) -> bool:
    command = [
        _git_executable(),
        "--git-dir",
        str(cache),
        "merge-base",
        "--is-ancestor",
        ancestor,
        descendant,
    ]
    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
        check=False,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise ReleaseControlError(f"cannot compare release history: {result.stdout.strip()}")


def _read_git_blob(cache: Path, oid: str) -> bytes:
    command = [_git_executable(), "--git-dir", str(cache), "cat-file", "blob", oid]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReleaseControlError(f"cannot read Git blob {oid}: {exc}") from exc
    if result.returncode != 0:
        raise ReleaseControlError(
            f"cannot read Git blob {oid}: {result.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return result.stdout


def _materialize_git_tree(cache: Path, commit: str, destination: Path) -> None:
    destination.mkdir(parents=True)
    destination_resolved = destination.resolve()
    if os.name == "nt":
        longest = max(
            (len(str((destination / Path(relative)).resolve(strict=False))), relative)
            for relative in _git_tree_records(cache, commit)
        )
        if longest[0] >= 248:
            raise ReleaseControlError(
                f"WINDOWS_PATH_BUDGET: snapshot path length {longest[0]} is unsafe for {longest[1]!r}; "
                f"use a shorter discovery parent than {destination.parent}"
            )
    for relative, (mode, _kind, oid) in _git_tree_records(cache, commit).items():
        if relative.startswith("/") or ".." in Path(relative).parts:
            raise ReleaseControlError(f"unsafe path in Git tree: {relative!r}")
        output = destination / Path(relative)
        try:
            output.resolve(strict=False).relative_to(destination_resolved)
        except ValueError as exc:
            raise ReleaseControlError(f"Git tree path escapes snapshot root: {relative!r}") from exc
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(_read_git_blob(cache, oid))
        if os.name != "nt":
            output.chmod(0o755 if mode == "100755" else 0o644)


def _git_tree_records(cache: Path, commit: str) -> Dict[str, Tuple[str, str, str]]:
    output = _run_git(["ls-tree", "-r", "-z", "--full-tree", commit], git_dir=cache)
    records: Dict[str, Tuple[str, str, str]] = {}
    for raw in output.split("\0"):
        if not raw:
            continue
        try:
            metadata, path = raw.split("\t", 1)
            mode, kind, oid = metadata.split(" ", 2)
        except ValueError as exc:
            raise ReleaseControlError(f"cannot parse Git tree record: {raw!r}") from exc
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ReleaseControlError(f"unsupported Git tree entry {mode} {kind}: {path}")
        records[path] = (mode, kind, oid.lower())
    return records


def _git_blob_oid(data: bytes, algorithm: str) -> str:
    try:
        digest = hashlib.new(algorithm)
    except ValueError as exc:
        raise ReleaseControlError(f"unsupported Git object format: {algorithm}") from exc
    digest.update(f"blob {len(data)}\0".encode("ascii"))
    digest.update(data)
    return digest.hexdigest()


def verify_snapshot_against_git(cache: Path, commit: str, snapshot: Path) -> Dict[str, Any]:
    if not snapshot.is_dir() or snapshot.is_symlink():
        raise ReleaseControlError(f"SOURCE_TREE_DRIFT: snapshot is not a real directory: {snapshot}")
    _run_git(["fsck", "--strict", "--no-reflogs", commit], git_dir=cache, timeout=300)
    algorithm = _run_git(["rev-parse", "--show-object-format"], git_dir=cache) or "sha1"
    records = _git_tree_records(cache, commit)
    actual = {
        path.relative_to(snapshot).as_posix()
        for path in snapshot.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    expected = set(records)
    if actual != expected:
        raise ReleaseControlError(
            "SOURCE_TREE_DRIFT: snapshot inventory differs from Git; "
            f"missing={sorted(expected - actual)[:20]}; extra={sorted(actual - expected)[:20]}"
        )
    for relative, (mode, _kind, oid) in records.items():
        path = snapshot / Path(relative)
        if path.is_symlink():
            raise ReleaseControlError(f"SOURCE_TREE_DRIFT: unexpected symlink in snapshot: {relative}")
        data = path.read_bytes()
        actual_oid = _git_blob_oid(data, algorithm)
        if actual_oid != oid:
            raise ReleaseControlError(f"SOURCE_TREE_DRIFT: Git blob mismatch: {relative}")
        if os.name != "nt" and mode == "100755" and not os.access(path, os.X_OK):
            raise ReleaseControlError(f"SOURCE_TREE_DRIFT: executable bit was lost: {relative}")
        if os.name != "nt" and mode == "100644" and path.stat().st_mode & 0o111:
            raise ReleaseControlError(f"SOURCE_TREE_DRIFT: unexpected executable bit: {relative}")
    tree_oid = _run_git(["rev-parse", f"{commit}^{{tree}}"], git_dir=cache).lower()
    return {"git_object_format": algorithm, "git_tree_oid": tree_oid, "file_count": len(records)}


def _windows_current_sid() -> str:
    result = _run(["whoami", "/user", "/fo", "csv", "/nh"], timeout=30)
    rows = list(csv.reader(result.stdout.splitlines()))
    if len(rows) != 1 or len(rows[0]) < 2 or not rows[0][1].startswith("S-"):
        raise ReleaseControlError("SNAPSHOT_PROTECTION_FAILED: cannot resolve the current Windows SID")
    return rows[0][1]


def _freeze_snapshot(snapshot: Path) -> Dict[str, Any]:
    """Make a validated commit snapshot read-only for the current OS user."""
    if not snapshot.is_dir() or snapshot.is_symlink():
        raise ReleaseControlError(f"SNAPSHOT_PROTECTION_FAILED: invalid snapshot root: {snapshot}")
    if os.name == "nt":
        sid = _windows_current_sid()
        # Normalize descendants to inherited ACLs first.  Combining recursive
        # inheritance removal and grant in one icacls call can strip child read
        # access before the grant propagates.
        _run(["icacls", str(snapshot), "/reset", "/T", "/C", "/Q"], timeout=300)
        _run(["icacls", str(snapshot), "/inheritance:r"], timeout=300)
        _run(
            [
                "icacls",
                str(snapshot),
                "/grant:r",
                f"*{sid}:(OI)(CI)RX",
            ],
            timeout=300,
        )
        method = "windows_icacls_current_sid_rx"
    else:
        files = [path for path in snapshot.rglob("*") if path.is_file()]
        directories = [snapshot, *(path for path in snapshot.rglob("*") if path.is_dir())]
        for path in files:
            path.chmod(0o555 if path.stat().st_mode & 0o111 else 0o444)
        for path in sorted(directories, key=lambda item: len(item.parts), reverse=True):
            path.chmod(0o555)
        method = "posix_no_write_bits"
    evidence = _assert_snapshot_write_protection(snapshot)
    evidence["method"] = method
    return evidence


def _thaw_snapshot(snapshot: Path) -> None:
    """Restore owner write access before quarantining or deleting a release snapshot."""
    if not snapshot.exists() or snapshot.is_symlink():
        return
    if os.name == "nt":
        _run(["icacls", str(snapshot), "/inheritance:e"], timeout=300)
        _run(["icacls", str(snapshot), "/reset", "/T", "/C", "/Q"], timeout=300)
    else:
        directories = [snapshot, *(path for path in snapshot.rglob("*") if path.is_dir())]
        for path in directories:
            path.chmod(0o755)
        for path in snapshot.rglob("*"):
            if path.is_file():
                path.chmod(0o755 if path.stat().st_mode & 0o111 else 0o644)


def _assert_snapshot_write_protection(snapshot: Path) -> Dict[str, Any]:
    if not snapshot.is_dir() or snapshot.is_symlink():
        raise ReleaseControlError(f"SNAPSHOT_PROTECTION_FAILED: invalid snapshot root: {snapshot}")
    if os.name != "nt":
        writable = [
            path.relative_to(snapshot).as_posix() or "."
            for path in [snapshot, *snapshot.rglob("*")]
            if path.stat().st_mode & 0o222
        ]
        if writable:
            raise ReleaseControlError(
                f"SNAPSHOT_PROTECTION_FAILED: write bits remain on {writable[:20]}"
            )

    # Prove both directory creation and existing-file write-open are denied.  A
    # root POSIX process can override mode bits, so mode inspection is the only
    # meaningful check in that exceptional test/container context.
    can_probe = os.name == "nt" or not hasattr(os, "geteuid") or os.geteuid() != 0
    if can_probe:
        probe = snapshot / f".write-probe-{uuid.uuid4().hex}"
        try:
            probe.write_bytes(b"probe")
        except OSError as exc:
            if exc.errno not in {errno.EACCES, errno.EPERM, errno.EROFS} and getattr(exc, "winerror", None) != 5:
                raise
        else:
            probe.unlink(missing_ok=True)
            raise ReleaseControlError("SNAPSHOT_PROTECTION_FAILED: snapshot accepted a new file")

        first_file = next((path for path in snapshot.rglob("*") if path.is_file()), None)
        if first_file is None:
            raise ReleaseControlError("SNAPSHOT_PROTECTION_FAILED: snapshot contains no files")
        try:
            with first_file.open("ab"):
                pass
        except OSError as exc:
            if exc.errno not in {errno.EACCES, errno.EPERM, errno.EROFS} and getattr(exc, "winerror", None) != 5:
                raise
        else:
            raise ReleaseControlError("SNAPSHOT_PROTECTION_FAILED: snapshot accepted a file write handle")

    return {
        "protected": True,
        "platform": sys.platform,
        "snapshot_root": str(snapshot.resolve()),
    }


def _materialize_snapshot(cache: Path, releases: Path, commit: str) -> Path:
    final_root = releases / commit
    final_repo = final_root / "repo"
    if os.name == "nt":
        longest_final = max(
            (len(str((final_repo / Path(relative)).resolve(strict=False))), relative)
            for relative in _git_tree_records(cache, commit)
        )
        if longest_final[0] >= 248:
            raise ReleaseControlError(
                f"WINDOWS_PATH_BUDGET: final snapshot path length {longest_final[0]} is unsafe for "
                f"{longest_final[1]!r}; use a shorter discovery parent than {releases.parent}"
            )
    if final_repo.is_dir():
        try:
            verify_snapshot_against_git(cache, commit, final_repo)
        except ReleaseControlError:
            quarantine = releases / f".{commit}.corrupt-{int(time.time())}-{uuid.uuid4().hex[:8]}"
            _thaw_snapshot(final_repo)
            final_root.rename(quarantine)
        else:
            return final_repo
    stage_root = releases / f".stage-{commit[:12]}-{uuid.uuid4().hex[:8]}"
    repo = stage_root / "repo"
    stage_root.mkdir()
    try:
        _materialize_git_tree(cache, commit, repo)
        verify_snapshot_against_git(cache, commit, repo)
        stage_root.rename(final_root)
    except Exception:
        if stage_root.exists():
            shutil.rmtree(stage_root, ignore_errors=True)
        raise
    return final_repo


def _default_validation(snapshot: Path) -> Dict[str, Any]:
    _manifest, requirements, _skills, distribution_errors = load_distribution(snapshot)
    if distribution_errors:
        raise ReleaseControlError("VALIDATION_FAILED: " + "; ".join(distribution_errors))
    python_config = requirements.get("python", {})
    tested = python_config.get("tested_major_minor", []) if isinstance(python_config, dict) else []
    current_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    if current_python not in tested:
        raise ReleaseControlError(
            f"RUNTIME_DEPENDENCY_DRIFT: Python {current_python} is not in tested versions {tested}"
        )
    packages = python_config.get("packages", {}) if isinstance(python_config, dict) else {}
    expected_pillow = packages.get("Pillow") if isinstance(packages, dict) else None
    try:
        import PIL  # type: ignore

        pillow_version = PIL.__version__
    except (ImportError, AttributeError):
        pillow_version = None
    if pillow_version != expected_pillow:
        raise ReleaseControlError(
            f"RUNTIME_DEPENDENCY_DRIFT: Pillow={pillow_version or 'missing'}; expected {expected_pillow}"
        )
    for executable in requirements.get("executables", []):
        name = executable.get("name") if isinstance(executable, dict) else None
        if not isinstance(name, str) or not shutil.which(name):
            raise ReleaseControlError(f"RUNTIME_DEPENDENCY_DRIFT: required executable is missing: {name!r}")
    ffmpeg = shutil.which("ffmpeg")
    required_encoders = requirements.get("ffmpeg_required_encoders", [])
    if ffmpeg and isinstance(required_encoders, list):
        encoders = _run([ffmpeg, "-hide_banner", "-encoders"], timeout=60).stdout
        missing = [name for name in required_encoders if name not in encoders]
        if missing:
            raise ReleaseControlError(
                "RUNTIME_DEPENDENCY_DRIFT: ffmpeg lacks required encoders: " + ", ".join(missing)
            )
    validator = snapshot / "high-control-ai-tvc" / "tools" / "validate_distribution.py"
    command = [sys.executable, str(validator), "--run-suite-tests"]
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.monotonic()
    result = _run(command, cwd=snapshot / "high-control-ai-tvc", timeout=1800, env=environment)
    return {
        "command": command,
        "python_executable": str(Path(sys.executable).resolve()),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "pillow_version": pillow_version,
        "completed_at": _utc_now(),
        "duration_seconds": round(time.monotonic() - started, 3),
        "output_sha256": hashlib.sha256(result.stdout.encode("utf-8")).hexdigest(),
        "output_tail": result.stdout.strip()[-2000:],
        "status": "pass",
    }


def _skill_release_records(
    cache: Path,
    snapshot: Path,
    commit: str,
    skills: List[Dict[str, str]],
) -> Dict[str, Dict[str, str]]:
    records: Dict[str, Dict[str, str]] = {}
    for skill in skills:
        name = skill["name"]
        tree_oid = _run_git(["rev-parse", f"{commit}:{name}"], git_dir=cache).lower()
        records[name] = {
            "tier": skill["tier"],
            "source": str((snapshot / name).resolve()),
            "tree_oid": tree_oid,
            "tree_digest": _tree_digest(snapshot / name),
        }
    return records


def _load_release_receipt(path: Path) -> Dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ReleaseControlError(f"RECEIPT_MISSING: release receipt is not a regular file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseControlError(f"RECEIPT_STALE_OR_TAMPERED: {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema_version") != RELEASE_SCHEMA_VERSION:
        raise ReleaseControlError(f"RECEIPT_STALE_OR_TAMPERED: unsupported release receipt: {path}")
    return value


def _existing_target_candidates(suite_id: str) -> List[Path]:
    candidates: List[Path] = []
    official, legacy = discovery_roots()
    codex_home = os.environ.get("CODEX_HOME")
    roots = [official, legacy]
    if codex_home:
        roots.append(Path(codex_home).expanduser() / "skills")
    seen = set()
    for root in roots:
        identity = os.path.normcase(str(root.resolve(strict=False)))
        if identity in seen:
            continue
        seen.add(identity)
        release_receipt = _release_state_paths(root, suite_id)["receipt"]
        _state_root, install_receipt = _state_paths(root, suite_id)
        if release_receipt.is_file() or install_receipt.is_file():
            candidates.append(root)
    return candidates


def resolve_target(target: Path | None, suite_id: str = DEFAULT_SUITE_ID) -> Path:
    if target is not None:
        return target.expanduser().absolute()
    candidates = _existing_target_candidates(suite_id)
    if len(candidates) > 1:
        raise ReleaseControlError(
            "DISCOVERY_AMBIGUOUS: multiple existing suite discovery roots require an explicit --target: "
            + ", ".join(str(path) for path in candidates)
        )
    if candidates:
        return candidates[0].expanduser().absolute()
    official, _legacy = discovery_roots()
    return official.expanduser().absolute()


def _known_discovery_roots(primary: Path, cwd: Path | None = None) -> List[Path]:
    roots = [primary]
    roots.extend(discovery_roots())
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        roots.append(Path(codex_home).expanduser() / "skills")
    cursor = (cwd or Path.cwd()).resolve(strict=False)
    for ancestor in (cursor, *cursor.parents):
        roots.append(ancestor / ".agents" / "skills")
        roots.append(ancestor / ".codex" / "skills")
    unique: List[Path] = []
    identities = set()
    for root in roots:
        identity = os.path.normcase(str(root.expanduser().resolve(strict=False)))
        if identity not in identities:
            identities.add(identity)
            unique.append(root.expanduser().absolute())
    return unique


def _discovery_conflicts(primary: Path, names: Iterable[str], cwd: Path | None = None) -> Dict[str, List[str]]:
    conflicts: Dict[str, List[str]] = {}
    for name in names:
        locations = [str(root / name) for root in _known_discovery_roots(primary, cwd) if _lexists(root / name)]
        if len(locations) != 1 or os.path.normcase(locations[0]) != os.path.normcase(str(primary / name)):
            conflicts[name] = locations
    return conflicts


def _write_project_runtime_lock(
    project_root: Path,
    receipt: Dict[str, Any],
    release_receipt_path: Path,
    active_system_root: Path,
) -> Path:
    project_root = project_root.expanduser().absolute()
    if not project_root.is_dir():
        raise ReleaseControlError(f"project root does not exist: {project_root}")
    canon_root = project_root / "00_project_canon"
    if not canon_root.is_dir() or canon_root.is_symlink():
        raise ReleaseControlError(f"project Canon directory is missing or redirected: {canon_root}")
    pending_transaction = canon_root / "PENDING_PROJECT_CANON_TRANSACTION.json"
    if pending_transaction.exists():
        raise ReleaseControlError(
            f"PROJECT_RELEASE_MIGRATION_REQUIRED: Canon transaction must finish or roll back first: {pending_transaction}"
        )
    lock_path = canon_root / "SYSTEM_RUNTIME_LOCK.json"
    previous_commit = None
    if lock_path.exists():
        previous = _read_json_object(lock_path, "project runtime lock")
        previous_commit = previous.get("release_commit")
    value = {
        "schema_version": "high-control-ai-tvc-system-runtime-lock.v1",
        "suite_id": receipt["suite_id"],
        "release_commit": receipt["release_commit"],
        "previous_release_commit": previous_commit if previous_commit != receipt["release_commit"] else None,
        "release_tree_oid": receipt["release_tree_oid"],
        "manifest_sha256": receipt["manifest_sha256"],
        "runtime_requirements_sha256": receipt["runtime_requirements_sha256"],
        "skills": receipt["skills"],
        "active_system_root": str(active_system_root),
        "release_receipt": str(release_receipt_path),
        "release_receipt_sha256": _sha256_file(release_receipt_path),
        "codex_thread_id": os.environ.get("CODEX_THREAD_ID"),
        "observed_at": _utc_now(),
        "authority_status": "aggregate_ready_latest",
        "scope": "optional_aggregate_profile",
        "controls_individual_skill_availability": False,
    }
    _write_json_atomic(lock_path, value)
    return lock_path


def sync_release(
    target: Path | None = None,
    *,
    mode: str = "auto",
    profile: str = "all",
    validation_runner: Callable[[Path], Dict[str, Any]] | None = None,
    remote_head_reader: Callable[[], str] | None = None,
    github_identity_reader: Callable[[], str] | None = None,
    installation_runner: Callable[[Path, Path, str, str], Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    suite_id = DEFAULT_SUITE_ID
    if profile != "all":
        raise ReleaseControlError(
            "aggregate sync requires profile=all; core is an install-only compatibility subset"
        )
    target = resolve_target(target, suite_id)
    paths = _prepare_release_state(target, suite_id)
    validation_runner = validation_runner or _default_validation
    remote_head_reader = remote_head_reader or query_remote_head
    github_identity_reader = github_identity_reader or query_github_identity_and_head
    installation_runner = installation_runner or install

    with _release_lock(paths):
        prior_commit: str | None = None
        if paths["receipt"].is_file():
            prior_receipt = _load_release_receipt(paths["receipt"])
            prior_value = prior_receipt.get("release_commit")
            if not isinstance(prior_value, str):
                raise ReleaseControlError("RECEIPT_STALE_OR_TAMPERED: prior release commit is missing")
            prior_commit = prior_value.lower()
        for stability_attempt in range(1, MAX_REMOTE_STABILITY_ATTEMPTS + 1):
            first = remote_head_reader().lower()
            github_head = github_identity_reader().lower()
            if first != github_head:
                if stability_attempt == MAX_REMOTE_STABILITY_ATTEMPTS:
                    raise ReleaseControlError(
                        f"REMOTE_UNSTABLE: Git transport head {first} differs from GitHub API head {github_head}"
                    )
                continue
            _fetch_exact(paths["cache"], first)
            if prior_commit and prior_commit != first and not _git_is_ancestor(paths["cache"], prior_commit, first):
                raise ReleaseControlError(
                    f"REMOTE_HISTORY_REWRITTEN: prior release {prior_commit} is not an ancestor of GitHub main {first}"
                )
            snapshot = _materialize_snapshot(paths["cache"], paths["releases"], first)
            git_evidence = verify_snapshot_against_git(paths["cache"], first, snapshot)
            manifest, _requirements, skills, distribution_errors = load_distribution(snapshot)
            skills, inventory_errors = managed_inventory(manifest, skills, snapshot)
            distribution_errors.extend(inventory_errors)
            if distribution_errors:
                raise ReleaseControlError("VALIDATION_FAILED: " + "; ".join(distribution_errors))
            _assert_canonical_manifest(manifest)
            if suite_id_from_manifest(manifest) != suite_id:
                raise ReleaseControlError("VALIDATION_FAILED: remote suite identity changed")
            selected = select_skills(skills, profile)
            validation = validation_runner(snapshot)
            git_evidence_after = verify_snapshot_against_git(paths["cache"], first, snapshot)
            if git_evidence != git_evidence_after:
                raise ReleaseControlError("VALIDATION_FAILED: validation changed the immutable Git snapshot")
            second = remote_head_reader().lower()
            if first != second:
                if stability_attempt == MAX_REMOTE_STABILITY_ATTEMPTS:
                    raise ReleaseControlError(
                        f"REMOTE_UNSTABLE: GitHub main advanced during validation ({first} -> {second})"
                    )
                continue

            adoption = adopt_content_equivalent_links(snapshot, target, profile)
            install_result = installation_runner(snapshot, target, profile, mode)
            third = remote_head_reader().lower()
            if first != third:
                if stability_attempt == MAX_REMOTE_STABILITY_ATTEMPTS:
                    raise ReleaseControlError(
                        f"REMOTE_UNSTABLE: GitHub main advanced during activation ({first} -> {third})"
                    )
                continue

            install_status = inspect_installation(snapshot, target, profile)
            if not install_status["ready"]:
                raise ReleaseControlError(f"INSTALLED_TREE_DRIFT: {install_status}")
            conflicts = _discovery_conflicts(target, [skill["name"] for skill in selected])
            if conflicts:
                raise ReleaseControlError(f"DISCOVERY_AMBIGUOUS: {conflicts}")
            _install_state, install_receipt_path = _state_paths(target, suite_id)
            install_receipt = _load_receipt(install_receipt_path, suite_id)
            if set(install_receipt.get("entries", {})) != {skill["name"] for skill in selected}:
                raise ReleaseControlError("PARTIAL_OR_OBSOLETE_INVENTORY: install receipt is not exactly the manifest inventory")

            snapshot_write_protection = _freeze_snapshot(snapshot)
            frozen_git_evidence = verify_snapshot_against_git(paths["cache"], first, snapshot)
            if git_evidence != frozen_git_evidence:
                raise ReleaseControlError("SNAPSHOT_PROTECTION_FAILED: freezing changed Git content evidence")

            skill_records = _skill_release_records(paths["cache"], snapshot, first, selected)
            receipt = {
                "schema_version": RELEASE_SCHEMA_VERSION,
                "suite_id": suite_id,
                "scope": "optional_aggregate_profile",
                "controls_individual_skill_availability": False,
                "repository": {
                    "github_repository_id": CANONICAL_REPOSITORY_ID,
                    "full_name": CANONICAL_REPOSITORY,
                    "remote_url": CANONICAL_REMOTE_URL,
                    "branch": CANONICAL_BRANCH,
                },
                "release_commit": first,
                "release_tree_oid": git_evidence["git_tree_oid"],
                "git_object_format": git_evidence["git_object_format"],
                "snapshot_root": str(snapshot.resolve()),
                "snapshot_tree_digest": _tree_digest(snapshot),
                "snapshot_write_protection": snapshot_write_protection,
                "manifest_sha256": _sha256_file(snapshot / "high-control-ai-tvc" / "SUITE_MANIFEST.json"),
                "runtime_requirements_sha256": _sha256_file(
                    snapshot / "high-control-ai-tvc" / "config" / "runtime-requirements.json"
                ),
                "skills": skill_records,
                "validation": validation,
                "content_equivalent_migration": adoption,
                "activation": {
                    "target_root": str(target),
                    "profile": profile,
                    "mode": install_result.get("mode", mode),
                    "install_receipt": str(install_receipt_path),
                    "install_receipt_sha256": _sha256_file(install_receipt_path),
                    "activating_codex_thread_id": os.environ.get("CODEX_THREAD_ID"),
                    "activated_at": _utc_now(),
                    "activated_at_unix_ms": int(time.time() * 1000),
                },
                "remote_observations": [first, second, third],
                "created_at": _utc_now(),
            }
            _write_json_atomic(paths["receipt"], receipt)
            result = production_check(
                target,
                profile=profile,
                ignore_current_process=True,
                ignore_lock=True,
                remote_head_reader=remote_head_reader,
            )
            if not result.get("aggregate_profile_ready", result.get("ready_latest", False)):
                raise ReleaseControlError(f"activation self-check failed: {result}")
            return {
                "schema_version": "high-control-ai-tvc-sync-result.v2",
                "success": True,
                "ready_latest": True,
                "aggregate_profile_ready": True,
                "scope": "optional_aggregate_profile",
                "controls_individual_skill_availability": False,
                "release_commit": first,
                "active_system_root": str(snapshot / "high-control-ai-tvc"),
                "target_root": str(target),
                "release_receipt": str(paths["receipt"]),
                "install_receipt": str(install_receipt_path),
                "validation": validation,
                "remote_stability_attempt": stability_attempt,
                "restart_required": True,
                "restart_instruction": "Start a new Codex task before using the updated aggregate profile.",
            }
        raise ReleaseControlError("REMOTE_UNSTABLE: no stable GitHub main revision was observed")


def _add_check(checks: List[Dict[str, str]], check_id: str, status: str, detail: str) -> None:
    checks.append({"id": check_id, "status": status, "detail": detail})


def production_check(
    target: Path | None = None,
    *,
    profile: str = "all",
    cwd: Path | None = None,
    project_root: Path | None = None,
    ignore_current_process: bool = False,
    ignore_lock: bool = False,
    remote_head_reader: Callable[[], str] | None = None,
) -> Dict[str, Any]:
    """Check aggregate-profile activation; never decide standalone Skill availability."""
    checks: List[Dict[str, str]] = []
    try:
        if profile != "all":
            raise ReleaseControlError(
                "aggregate check supports only profile=all; core is an install-only compatibility subset"
            )
        target = resolve_target(target)
        paths = _release_state_paths(target, DEFAULT_SUITE_ID)
        if paths["lock"].exists() and not ignore_lock:
            raise ReleaseControlError("CONCURRENT_UPDATE: release activation is in progress")
        receipt = _load_release_receipt(paths["receipt"])
        repository = receipt.get("repository")
        expected_repository = {
            "github_repository_id": CANONICAL_REPOSITORY_ID,
            "full_name": CANONICAL_REPOSITORY,
            "remote_url": CANONICAL_REMOTE_URL,
            "branch": CANONICAL_BRANCH,
        }
        if repository != expected_repository:
            raise ReleaseControlError("RECEIPT_STALE_OR_TAMPERED: canonical repository identity differs")
        if (
            receipt.get("scope") != "optional_aggregate_profile"
            or receipt.get("controls_individual_skill_availability") is not False
        ):
            raise ReleaseControlError(
                "RECEIPT_STALE_OR_TAMPERED: release receipt is not explicitly aggregate-scoped"
            )
        # Runtime gates execute inside Codex sandboxes.  On Windows those sandboxes
        # can deny Schannel credential acquisition even for a public Git
        # ls-remote, while direct HTTPS remains available.  Use the GitHub API
        # identity+ref check here; sync_release still cross-checks Git transport
        # against the API before it fetches and activates Git objects.
        first = (remote_head_reader or query_github_identity_and_head)().lower()
        commit = receipt.get("release_commit")
        if commit != first:
            raise ReleaseControlError(f"UPDATE_REQUIRED: active={commit}; GitHub main={first}")
        _add_check(checks, "github_main_latest", "pass", f"GitHub main={first}")

        expected_snapshot = (paths["releases"] / first / "repo").resolve()
        snapshot_raw = receipt.get("snapshot_root")
        if not isinstance(snapshot_raw, str) or Path(snapshot_raw).resolve() != expected_snapshot:
            raise ReleaseControlError("RECEIPT_STALE_OR_TAMPERED: snapshot path is not commit-addressed")
        snapshot = expected_snapshot
        git_evidence = verify_snapshot_against_git(paths["cache"], first, snapshot)
        if receipt.get("release_tree_oid") != git_evidence["git_tree_oid"]:
            raise ReleaseControlError("RECEIPT_STALE_OR_TAMPERED: Git tree OID differs")
        if receipt.get("snapshot_tree_digest") != _tree_digest(snapshot):
            raise ReleaseControlError("SOURCE_TREE_DRIFT: snapshot digest differs from release receipt")
        _add_check(checks, "snapshot_integrity", "pass", f"Git tree={git_evidence['git_tree_oid']}")

        protection = receipt.get("snapshot_write_protection")
        actual_protection = _assert_snapshot_write_protection(snapshot)
        if not isinstance(protection, dict) or any(
            protection.get(key) != actual_protection.get(key)
            for key in ("protected", "platform", "snapshot_root")
        ) or protection.get("method") not in {
            "windows_icacls_current_sid_rx",
            "posix_no_write_bits",
        }:
            raise ReleaseControlError("RECEIPT_STALE_OR_TAMPERED: snapshot write-protection evidence differs")
        _add_check(
            checks,
            "snapshot_write_protection",
            "pass",
            f"{protection['method']} rejects snapshot writes",
        )

        manifest, _requirements, skills, errors = load_distribution(snapshot)
        skills, inventory_errors = managed_inventory(manifest, skills, snapshot)
        errors.extend(inventory_errors)
        if errors:
            raise ReleaseControlError("VALIDATION_FAILED: " + "; ".join(errors))
        _assert_canonical_manifest(manifest)
        suite_id = suite_id_from_manifest(manifest)
        if suite_id != receipt.get("suite_id"):
            raise ReleaseControlError("RECEIPT_STALE_OR_TAMPERED: suite identity differs")
        if receipt.get("activation", {}).get("profile") != "all":
            raise ReleaseControlError("PARTIAL_RELEASE: aggregate validation requires the all profile")
        if receipt.get("manifest_sha256") != _sha256_file(snapshot / "high-control-ai-tvc" / "SUITE_MANIFEST.json"):
            raise ReleaseControlError("RECEIPT_STALE_OR_TAMPERED: manifest digest differs")
        if receipt.get("runtime_requirements_sha256") != _sha256_file(
            snapshot / "high-control-ai-tvc" / "config" / "runtime-requirements.json"
        ):
            raise ReleaseControlError("RUNTIME_DEPENDENCY_DRIFT: runtime requirements digest differs")
        validation = receipt.get("validation")
        if not isinstance(validation, dict) or validation.get("status") != "pass":
            raise ReleaseControlError("VALIDATION_FAILED: release validation evidence is missing")
        runtime_python = validation.get("python_executable")
        if not isinstance(runtime_python, str) or not Path(runtime_python).is_file():
            raise ReleaseControlError("RUNTIME_DEPENDENCY_DRIFT: validated Python executable is unavailable")
        runtime_probe = _run(
            [
                runtime_python,
                "-c",
                "import json,sys,PIL; print(json.dumps({'python': '.'.join(map(str,sys.version_info[:3])), 'pillow': PIL.__version__}))",
            ],
            timeout=30,
        )
        try:
            runtime_value = json.loads(runtime_probe.stdout.strip())
        except json.JSONDecodeError as exc:
            raise ReleaseControlError("RUNTIME_DEPENDENCY_DRIFT: validated Python probe is invalid") from exc
        if (
            runtime_value.get("python") != validation.get("python_version")
            or runtime_value.get("pillow") != validation.get("pillow_version")
        ):
            raise ReleaseControlError("RUNTIME_DEPENDENCY_DRIFT: validated Python/Pillow runtime changed")
        _add_check(
            checks,
            "validated_runtime",
            "pass",
            f"Python={runtime_value['python']} Pillow={runtime_value['pillow']}",
        )
        selected = select_skills(skills, "all")
        expected_names = {skill["name"] for skill in selected}
        receipt_skills = receipt.get("skills")
        if not isinstance(receipt_skills, dict) or set(receipt_skills) != expected_names:
            raise ReleaseControlError("PARTIAL_OR_OBSOLETE_INVENTORY: release receipt inventory differs")
        actual_records = _skill_release_records(paths["cache"], snapshot, first, selected)
        if receipt_skills != actual_records:
            raise ReleaseControlError("SOURCE_TREE_DRIFT: per-Skill release records differ")
        _add_check(checks, "aggregate_skill_inventory", "pass", f"all {len(selected)} aggregate member trees match Git")

        installation = inspect_installation(snapshot, target, "all")
        if not installation["ready"]:
            detail = installation["errors"] or [
                f"{item['name']}={item['state']}" for item in installation["skills"] if item["state"] != "installed"
            ]
            raise ReleaseControlError(f"INSTALLED_TREE_DRIFT: {detail}")
        _install_state, install_receipt_path = _state_paths(target, suite_id)
        install_receipt = _load_receipt(install_receipt_path, suite_id)
        if (
            install_receipt.get("schema_version") != RECEIPT_SCHEMA_VERSION
            or install_receipt.get("scope") != "optional_aggregate_profile"
            or install_receipt.get("controls_individual_skill_availability") is not False
            or install_receipt.get("repo_root") != str(snapshot.resolve())
            or not isinstance(install_receipt.get("transaction_id"), str)
        ):
            raise ReleaseControlError("RECEIPT_STALE_OR_TAMPERED: install receipt lacks release-v2 identity")
        if set(install_receipt.get("entries", {})) != expected_names:
            raise ReleaseControlError("PARTIAL_OR_OBSOLETE_INVENTORY: install receipt inventory differs")
        activation = receipt.get("activation")
        if not isinstance(activation, dict):
            raise ReleaseControlError("RECEIPT_STALE_OR_TAMPERED: activation evidence is missing")
        if activation.get("install_receipt") != str(install_receipt_path):
            raise ReleaseControlError("RECEIPT_STALE_OR_TAMPERED: install receipt path differs")
        if activation.get("install_receipt_sha256") != _sha256_file(install_receipt_path):
            raise ReleaseControlError("RECEIPT_STALE_OR_TAMPERED: install receipt digest differs")
        _add_check(checks, "installed_aggregate_release", "pass", "aggregate discovery entries and receipt match the release")

        conflicts = _discovery_conflicts(target, expected_names, cwd)
        if conflicts:
            raise ReleaseControlError(f"DISCOVERY_AMBIGUOUS: {conflicts}")
        _add_check(checks, "aggregate_discovery_uniqueness", "pass", "each aggregate-selected slug has one active discovery entry")

        current_thread = os.environ.get("CODEX_THREAD_ID")
        activated_at_ms = activation.get("activated_at_unix_ms")
        if not ignore_current_process:
            if not current_thread or not isinstance(activated_at_ms, int):
                raise ReleaseControlError(
                    "PROCESS_RESTART_REQUIRED: run the aggregate check inside a new Codex task"
                )
            thread_created_ms = _codex_thread_created_ms(current_thread)
            if thread_created_ms <= activated_at_ms:
                raise ReleaseControlError(
                    "PROCESS_RESTART_REQUIRED: this Codex task predates the active release and may cache older Skill instructions"
                )
            _add_check(
                checks,
                "process_generation",
                "pass",
                f"Codex task {current_thread} was created after release activation",
            )
        else:
            _add_check(checks, "process_generation", "pass", "activation self-check bypassed process age only")

        second = (remote_head_reader or query_github_identity_and_head)().lower()
        if second != first:
            raise ReleaseControlError(f"REMOTE_HEAD_CHANGED_DURING_CHECK: {first} -> {second}")
        _add_check(checks, "remote_stability", "pass", f"GitHub main remained {second}")
        runtime_lock_path = None
        active_system_root = snapshot / "high-control-ai-tvc"
        if project_root is not None:
            runtime_lock_path = _write_project_runtime_lock(
                project_root,
                receipt,
                paths["receipt"],
                active_system_root,
            )
            _add_check(checks, "project_runtime_lock", "pass", str(runtime_lock_path))
        return {
            "schema_version": "high-control-ai-tvc-production-check.v2",
            "ready_latest": True,
            "aggregate_profile_ready": True,
            "scope": "optional_aggregate_profile",
            "controls_individual_skill_availability": False,
            "result": "aggregate_ready_latest",
            "release_commit": first,
            "active_system_root": str(active_system_root),
            "runtime_python": receipt.get("validation", {}).get("python_executable"),
            "release_receipt": str(paths["receipt"]),
            "project_runtime_lock": str(runtime_lock_path) if runtime_lock_path is not None else None,
            "target_root": str(target),
            "checks": checks,
            "errors": [],
        }
    except (InstallSafetyError, OSError, ReleaseControlError, SuiteConfigurationError) as exc:
        _add_check(checks, "aggregate_release_evidence", "fail", str(exc))
        return {
            "schema_version": "high-control-ai-tvc-production-check.v2",
            "ready_latest": False,
            "aggregate_profile_ready": False,
            "scope": "optional_aggregate_profile",
            "controls_individual_skill_availability": False,
            "result": "aggregate_not_ready_latest",
            "release_commit": None,
            "active_system_root": None,
            "runtime_python": None,
            "release_receipt": None,
            "project_runtime_lock": None,
            "target_root": str(target) if target is not None else None,
            "checks": checks,
            "errors": [str(exc)],
        }


def _print_text(result: Dict[str, Any]) -> None:
    for item in result.get("checks", []):
        symbol = "OK" if item.get("status") == "pass" else "FAIL"
        print(f"[{symbol}] {item.get('id')}: {item.get('detail')}")
    if result.get("success") or result.get("aggregate_profile_ready") or result.get("ready_latest"):
        print(f"AGGREGATE_READY_LATEST {result.get('release_commit')}")
        if result.get("restart_required"):
            print(result.get("restart_instruction"))
    else:
        for error in result.get("errors", []):
            print(f"ERROR: {error}")
        print("AGGREGATE_NOT_READY_LATEST")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    sync_parser = subparsers.add_parser("sync", help="fetch, validate, and atomically activate the optional aggregate profile")
    sync_parser.add_argument("--target", type=Path)
    sync_parser.add_argument("--mode", choices=("auto", "junction", "symlink", "copy"), default="auto")
    sync_parser.add_argument("--profile", choices=("all",), default="all")
    sync_parser.add_argument("--format", choices=("text", "json"), default="text")
    check_parser = subparsers.add_parser("check", help="prove the active aggregate release is still GitHub main")
    check_parser.add_argument("--target", type=Path)
    check_parser.add_argument("--profile", choices=("all",), default="all")
    check_parser.add_argument("--project-root", type=Path)
    check_parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()

    try:
        if args.action == "sync":
            result = sync_release(args.target, mode=args.mode, profile=args.profile)
        else:
            result = production_check(
                args.target,
                profile=args.profile,
                cwd=args.project_root,
                project_root=args.project_root,
            )
    except (InstallSafetyError, OSError, ReleaseControlError, SuiteConfigurationError) as exc:
        result = {
            "success": False,
            "ready_latest": False,
            "aggregate_profile_ready": False,
            "scope": "optional_aggregate_profile",
            "controls_individual_skill_availability": False,
            "result": "aggregate_not_ready_latest",
            "errors": [str(exc)],
            "checks": [],
        }
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_text(result)
    return 0 if result.get("success") or result.get("aggregate_profile_ready") or result.get("ready_latest") else 1


if __name__ == "__main__":
    raise SystemExit(main())
