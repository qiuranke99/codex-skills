#!/usr/bin/env python3
"""Publish and verify the frozen-moment-camera-coverage standalone Skill.

This controller is intentionally outside the optional High-Control aggregate.
It materializes only the target package from an exact GitHub ``main`` commit,
freezes that package, activates one discovery link, and writes a package-scoped
receipt.  It never installs or rewrites sibling Skills.
"""

from __future__ import annotations

import argparse
import ast
import base64
import csv
import errno
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Iterator


SKILL_NAME = "frozen-moment-camera-coverage"
REPOSITORY = "qiuranke99/codex-skills"
REPOSITORY_ID = 1264973746
REMOTE_URL = "https://github.com/qiuranke99/codex-skills.git"
BRANCH = "main"
RECEIPT_SCHEMA = "frozen-moment-camera-coverage-release.v1"
STATE_SCHEMA = "frozen-moment-camera-coverage-release-state.v1"
LOCK_SCHEMA = "frozen-moment-camera-coverage-release-lock.v1"
TRANSACTION_SCHEMA = "frozen-moment-camera-coverage-release-transaction.v1"
SHA_RE = re.compile(r"^[0-9a-f]{40,64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TRANSACTION_ID_RE = re.compile(r"^[0-9a-f]{32}$")
EXPECTED_STANDALONE_PACKAGES = 18
EXPECTED_AGGREGATE_MEMBERS = 15
EXPECTED_AGGREGATE_EXCLUSIONS = 3
EXPECTED_EXCLUDED_SKILLS = {
    "advertising-reference-research-director",
    "complex-product-identity-reconstruction-asset-locking",
    SKILL_NAME,
}


def _noop_fault(_point: str) -> None:
    """Test seam for simulating abrupt process termination at durable phases."""


_fault: Callable[[str], None] = _noop_fault


class ReleaseError(RuntimeError):
    """A fail-closed release contract violation."""


def _run(
    command: list[str],
    *,
    cwd: Path | None = None,
    input_bytes: bytes | None = None,
    binary_output: bool = False,
    timeout: int = 300,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[Any]:
    binary = input_bytes is not None or binary_output
    result = subprocess.run(
        command,
        cwd=cwd,
        input=input_bytes,
        text=not binary,
        encoding=None if binary else "utf-8",
        errors=None if binary else "replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        output = result.stdout.decode("utf-8", "replace") if binary else result.stdout
        raise ReleaseError(f"COMMAND_FAILED: {' '.join(command)}: {output.strip()}")
    return result


def _git(repo_root: Path, arguments: list[str], *, binary: bool = False, input_bytes: bytes | None = None) -> Any:
    result = _run(
        ["git", *arguments],
        cwd=repo_root,
        input_bytes=input_bytes,
        binary_output=binary,
    )
    if binary or input_bytes is not None:
        return result.stdout
    return result.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    descriptor = os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_bytes(
        path,
        (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )


def _atomic_restore(path: Path, prior: bytes | None) -> None:
    if prior is None:
        if path.exists():
            if path.is_symlink() or _is_reparse(path) or not path.is_file():
                raise ReleaseError(f"UNSAFE_PATH: refusing to remove redirected receipt: {path}")
            path.unlink()
            _fsync_directory(path.parent)
        return
    _atomic_bytes(path, prior)


def _tree_manifest(root: Path) -> list[dict[str, Any]]:
    _assert_real_tree(root, "package tree")
    resolved_root = root.resolve(strict=True)
    result: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if _is_reparse(path):
            raise ReleaseError(f"SOURCE_TREE_DRIFT: reparse point inside package: {path}")
        try:
            path.resolve(strict=True).relative_to(resolved_root)
        except (OSError, ValueError) as exc:
            raise ReleaseError(f"SOURCE_TREE_DRIFT: package path escapes root: {path}") from exc
        if path.is_file():
            result.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
    return result


def _is_junction(path: Path) -> bool:
    native = getattr(os.path, "isjunction", None)
    try:
        return bool(native and native(path))
    except OSError:
        return False


def _lexists(path: Path) -> bool:
    return os.path.lexists(str(path))


def _is_reparse(path: Path) -> bool:
    if not _lexists(path):
        return False
    if path.is_symlink() or _is_junction(path):
        return True
    try:
        attributes = path.stat(follow_symlinks=False).st_file_attributes
    except (AttributeError, OSError):
        return False
    return bool(attributes & 0x400)


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.path.expanduser(str(path))))


def _assert_no_reparse_chain(path: Path, label: str) -> None:
    cursor = _absolute(path)
    while True:
        if _is_reparse(cursor):
            raise ReleaseError(f"UNSAFE_PATH: {label} contains a redirected component: {cursor}")
        parent = cursor.parent
        if parent == cursor:
            break
        cursor = parent


def _real_directory(path: Path, label: str) -> None:
    if _lexists(path) and (_is_reparse(path) or not path.is_dir()):
        raise ReleaseError(f"UNSAFE_PATH: {label} must be a real directory: {path}")


def _real_file(path: Path, label: str) -> None:
    if not path.is_file() or _is_reparse(path):
        raise ReleaseError(f"UNSAFE_PATH: {label} must be a real regular file: {path}")


def _assert_real_tree(root: Path, label: str) -> None:
    _real_directory(root, label)
    if not root.is_dir():
        raise ReleaseError(f"UNSAFE_PATH: {label} does not exist: {root}")
    for item in root.rglob("*"):
        if _is_reparse(item):
            raise ReleaseError(f"UNSAFE_PATH: {label} contains a reparse point: {item}")


def _within(child: Path, parent: Path) -> bool:
    child_value = os.path.normcase(str(_absolute(child)))
    parent_value = os.path.normcase(str(_absolute(parent)))
    try:
        return os.path.commonpath([child_value, parent_value]) == parent_value
    except ValueError:
        return False


def validate_roots(repo_root: Path, state_root: Path, discovery_root: Path) -> tuple[Path, Path, Path]:
    repo = repo_root.resolve(strict=True)
    state = _absolute(state_root)
    discovery = _absolute(discovery_root)
    _assert_no_reparse_chain(state, "state root")
    _assert_no_reparse_chain(discovery, "discovery root")
    if _within(state, repo) or _within(repo, state):
        raise ReleaseError("UNSAFE_PATH: state root and authoring repository must be disjoint")
    if _within(state, discovery) or _within(discovery, state):
        raise ReleaseError("UNSAFE_PATH: state root and discovery root must be disjoint")
    return repo, state, discovery


def state_paths(state_root: Path) -> dict[str, Path]:
    root = _absolute(state_root)
    return {
        "root": root,
        "marker": root / "state.json",
        "releases": root / "releases",
        "receipts": root / "receipts",
        "receipt": root / "active-release.json",
        "lock": root / "release.lock",
        "journal": root / "transaction.json",
    }


def prepare_state(state_root: Path) -> dict[str, Path]:
    paths = state_paths(state_root)
    _assert_no_reparse_chain(paths["root"], "release state root")
    _real_directory(paths["root"], "release state root")
    paths["root"].mkdir(parents=True, exist_ok=True)
    if _lexists(paths["marker"]):
        _real_file(paths["marker"], "release state marker")
        value = json.loads(paths["marker"].read_text(encoding="utf-8"))
        if value != {"schema_version": STATE_SCHEMA, "skill_name": SKILL_NAME}:
            raise ReleaseError("WRONG_STATE_ROOT: state marker identity differs")
    else:
        unexpected = [item.name for item in paths["root"].iterdir()]
        if unexpected:
            raise ReleaseError(f"WRONG_STATE_ROOT: unmarked state root is not empty: {unexpected}")
        _atomic_json(paths["marker"], {"schema_version": STATE_SCHEMA, "skill_name": SKILL_NAME})
    for key, label in (("releases", "releases root"), ("receipts", "receipts root")):
        _real_directory(paths[key], label)
        paths[key].mkdir(exist_ok=True)
    return paths


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        kernel32.GetExitCodeProcess.restype = ctypes.c_int
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_int
        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5  # access denied still proves the process exists
        try:
            exit_code = ctypes.c_uint32()
            return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))) and exit_code.value == still_active
        finally:
            kernel32.CloseHandle(handle)
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
def _release_lock(paths: dict[str, Path]) -> Iterator[None]:
    lock_path = paths["lock"]
    lock_id = uuid.uuid4().hex
    payload = {
        "schema_version": LOCK_SCHEMA,
        "skill_name": SKILL_NAME,
        "lock_id": lock_id,
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "created_at_unix_ms": int(time.time() * 1000),
    }
    for _attempt in range(2):
        try:
            descriptor = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            try:
                _real_file(lock_path, "release lock")
                existing = json.loads(lock_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ReleaseError) as exc:
                raise ReleaseError(f"CONCURRENT_UPDATE: unreadable release lock: {lock_path}: {exc}") from exc
            owner_pid = existing.get("pid")
            owner_host = existing.get("host")
            if owner_host == socket.gethostname() and isinstance(owner_pid, int) and not _pid_alive(owner_pid):
                lock_path.unlink()
                continue
            raise ReleaseError(
                f"CONCURRENT_UPDATE: release transaction active on {owner_host} pid={owner_pid}"
            )
        else:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(_canonical_json(payload) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
            break
    else:
        raise ReleaseError("CONCURRENT_UPDATE: could not acquire release lock")
    try:
        yield
    finally:
        try:
            current = json.loads(lock_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            current = {}
        if current.get("lock_id") == lock_id:
            lock_path.unlink(missing_ok=True)


def _github_identity_and_head() -> str:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "frozen-moment-camera-coverage-release",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    def read(url: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                value = json.loads(response.read().decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, urllib.error.URLError) as exc:
            raise ReleaseError(f"REMOTE_UNVERIFIED: {url}: {exc}") from exc
        if not isinstance(value, dict):
            raise ReleaseError("REMOTE_UNVERIFIED: GitHub returned a non-object")
        return value

    repository = read(f"https://api.github.com/repos/{REPOSITORY}")
    if (
        repository.get("id") != REPOSITORY_ID
        or str(repository.get("full_name", "")).lower() != REPOSITORY.lower()
        or repository.get("default_branch") != BRANCH
    ):
        raise ReleaseError("WRONG_REMOTE: GitHub repository identity differs")
    reference = read(f"https://api.github.com/repos/{REPOSITORY}/git/ref/heads/{BRANCH}")
    object_value = reference.get("object")
    commit = object_value.get("sha") if isinstance(object_value, dict) else None
    if not isinstance(commit, str) or not SHA_RE.fullmatch(commit.lower()):
        raise ReleaseError("REMOTE_UNVERIFIED: GitHub branch response lacks a valid commit")
    return commit.lower()


def _validate_commit(commit: str, label: str = "accepted commit") -> str:
    if not isinstance(commit, str):
        raise ReleaseError(f"INVALID_COMMIT: {label} must be a 40-character hexadecimal commit")
    value = commit.lower()
    if not COMMIT_RE.fullmatch(value):
        raise ReleaseError(f"INVALID_COMMIT: {label} must be a 40-character hexadecimal commit")
    return value


def remote_head(repo_root: Path, expected_commit: str | None = None) -> str:
    origin = _git(repo_root, ["remote", "get-url", "origin"])
    normalized = origin.removesuffix("/").removesuffix(".git").lower()
    if normalized not in {
        REMOTE_URL.removesuffix(".git").lower(),
        f"git@github.com:{REPOSITORY}".lower(),
        f"ssh://git@github.com/{REPOSITORY}".lower(),
    }:
        raise ReleaseError(f"WRONG_REMOTE: origin is {origin}")
    result = _git(repo_root, ["ls-remote", "--exit-code", "origin", f"refs/heads/{BRANCH}"])
    fields = result.split()
    if len(fields) != 2 or fields[1] != f"refs/heads/{BRANCH}" or not SHA_RE.fullmatch(fields[0].lower()):
        raise ReleaseError(f"REMOTE_UNVERIFIED: unexpected ls-remote output: {result!r}")
    transport_head = fields[0].lower()
    github_head = _github_identity_and_head()
    if transport_head != github_head:
        raise ReleaseError(f"REMOTE_UNSTABLE: transport={transport_head}; github={github_head}")
    if expected_commit is not None and transport_head != _validate_commit(expected_commit):
        raise ReleaseError(
            f"ACCEPTED_COMMIT_MISMATCH: accepted={expected_commit.lower()}; remote={transport_head}"
        )
    return transport_head


def fetch_exact(repo_root: Path, commit: str) -> None:
    commit = _validate_commit(commit)
    _git(
        repo_root,
        ["fetch", "--force", "--no-tags", "origin", f"+refs/heads/{BRANCH}:refs/remotes/origin/{BRANCH}"],
    )
    fetched = _git(repo_root, ["rev-parse", f"refs/remotes/origin/{BRANCH}"]).lower()
    if fetched != commit:
        raise ReleaseError(f"REMOTE_HEAD_CHANGED_DURING_FETCH: expected={commit}; fetched={fetched}")
    _git(repo_root, ["cat-file", "-e", f"{commit}^{{commit}}"])


def git_tree_records(repo_root: Path, commit: str) -> dict[str, dict[str, str]]:
    raw = _git(repo_root, ["ls-tree", "-r", "-z", commit, "--", SKILL_NAME], binary=True)
    records: dict[str, dict[str, str]] = {}
    prefix = f"{SKILL_NAME}/"
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        header, raw_path = entry.split(b"\t", 1)
        mode, kind, oid = header.decode("ascii").split()
        path = raw_path.decode("utf-8")
        if not path.startswith(prefix) or kind != "blob" or mode == "120000":
            raise ReleaseError(f"SOURCE_TREE_DRIFT: unsupported package Git entry: {path}")
        records[path[len(prefix) :]] = {"mode": mode, "oid": oid}
    if "SKILL.md" not in records or "agents/openai.yaml" not in records:
        raise ReleaseError("VALIDATION_FAILED: committed package lacks required Skill files")
    return records


def package_tree_oid(repo_root: Path, commit: str) -> str:
    value = _git(repo_root, ["rev-parse", f"{commit}:{SKILL_NAME}"]).lower()
    if not SHA_RE.fullmatch(value):
        raise ReleaseError("SOURCE_TREE_DRIFT: invalid package tree OID")
    return value


def _git_blob_oid(data: bytes, algorithm: str) -> str:
    try:
        digest = hashlib.new(algorithm)
    except ValueError as exc:
        raise ReleaseError(f"SOURCE_TREE_DRIFT: unsupported Git object format: {algorithm}") from exc
    digest.update(f"blob {len(data)}\0".encode("ascii"))
    digest.update(data)
    return digest.hexdigest()


def verify_snapshot(repo_root: Path, commit: str, package: Path) -> dict[str, Any]:
    commit = _validate_commit(commit, "snapshot commit")
    _assert_real_tree(package, "snapshot package")
    records = git_tree_records(repo_root, commit)
    algorithm = _git(repo_root, ["rev-parse", "--show-object-format"]) or "sha1"
    actual_files = {item["path"] for item in _tree_manifest(package)}
    if actual_files != set(records):
        raise ReleaseError(
            f"SOURCE_TREE_DRIFT: missing={sorted(set(records) - actual_files)}; "
            f"extra={sorted(actual_files - set(records))}"
        )
    for relative, record in records.items():
        path = package / relative
        oid = _git_blob_oid(path.read_bytes(), algorithm)
        if oid != record["oid"]:
            raise ReleaseError(f"SOURCE_TREE_DRIFT: Git blob mismatch: {relative}")
        if os.name != "nt":
            executable = bool(path.stat().st_mode & 0o111)
            if (record["mode"] == "100755") != executable:
                raise ReleaseError(f"SOURCE_TREE_DRIFT: executable mode mismatch: {relative}")
    return {
        "package_tree_oid": package_tree_oid(repo_root, commit),
        "file_manifest": _tree_manifest(package),
    }


def materialize_snapshot(repo_root: Path, commit: str, releases: Path) -> Path:
    commit = _validate_commit(commit)
    _real_directory(releases, "releases root")
    if not releases.is_dir():
        raise ReleaseError(f"UNSAFE_PATH: releases root does not exist: {releases}")
    commit_root = releases / commit
    if not _within(commit_root, releases):
        raise ReleaseError(f"UNSAFE_PATH: commit release root escapes releases root: {commit_root}")
    _real_directory(commit_root, "commit release root")
    commit_root.mkdir(exist_ok=True)
    package = commit_root / "package"
    if _lexists(package):
        _real_directory(package, "snapshot package")
        verify_snapshot(repo_root, commit, package)
        return package
    records = git_tree_records(repo_root, commit)
    if os.name == "nt":
        longest = max(
            (len(str(package.joinpath(*PurePosixPath(relative).parts))), relative)
            for relative in records
        )
        if longest[0] >= 248:
            raise ReleaseError(
                f"WINDOWS_PATH_BUDGET: snapshot path length {longest[0]} is unsafe for {longest[1]!r}"
            )
    stage = commit_root / f".stage-{uuid.uuid4().hex}"
    _real_directory(stage, "snapshot staging root")
    stage.mkdir()
    try:
        extracted = stage / SKILL_NAME
        for relative, record in records.items():
            pure = PurePosixPath(relative)
            if pure.is_absolute() or ".." in pure.parts or not pure.parts:
                raise ReleaseError(f"UNSAFE_GIT_PATH: {relative}")
            destination = extracted.joinpath(*pure.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(_git(repo_root, ["cat-file", "blob", record["oid"]], binary=True))
            if os.name != "nt" and record["mode"] == "100755":
                destination.chmod(0o755)
        verify_snapshot(repo_root, commit, extracted)
        os.replace(extracted, package)
        _real_directory(package, "snapshot package")
    finally:
        if stage.exists():
            _real_directory(stage, "snapshot staging root")
            shutil.rmtree(stage)
    return package


def aggregate_boundary(repo_root: Path, commit: str) -> dict[str, Any]:
    raw_bytes = _git(
        repo_root,
        ["show", f"{commit}:high-control-ai-tvc/SUITE_MANIFEST.json"],
        binary=True,
    )
    try:
        manifest = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseError("AGGREGATE_BOUNDARY_VIOLATION: manifest is not valid UTF-8 JSON") from exc
    members = [item.get("name") for item in manifest.get("skills", []) if isinstance(item, dict)]
    excluded = manifest.get("excluded_from_aggregate_profile", [])
    if SKILL_NAME in members or SKILL_NAME not in excluded:
        raise ReleaseError("AGGREGATE_BOUNDARY_VIOLATION: target must be excluded and unmanaged")
    top_level = _git(repo_root, ["ls-tree", "-d", "--name-only", commit]).splitlines()
    standalone = 0
    for name in top_level:
        probe = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}:{name}/SKILL.md"],
            cwd=repo_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        standalone += probe.returncode == 0
    declared = manifest.get("standalone_package_count")
    if (
        declared != standalone
        or len(members) + len(excluded) != standalone
        or standalone != EXPECTED_STANDALONE_PACKAGES
        or len(members) != EXPECTED_AGGREGATE_MEMBERS
        or len(excluded) != EXPECTED_AGGREGATE_EXCLUSIONS
        or set(excluded) != EXPECTED_EXCLUDED_SKILLS
    ):
        raise ReleaseError(
            f"AGGREGATE_BOUNDARY_VIOLATION: declared={declared}; discovered={standalone}; "
            f"managed={len(members)}; excluded={len(excluded)}; exclusion_set={sorted(excluded)}"
        )
    return {
        "manifest_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "standalone_package_count": standalone,
        "aggregate_member_count": len(members),
        "aggregate_exclusion_count": len(excluded),
        "target_excluded": True,
    }


def trusted_python(python: Path) -> Path:
    candidate = _absolute(python)
    _assert_no_reparse_chain(candidate, "trusted Python")
    if _is_reparse(candidate) or not candidate.is_file():
        raise ReleaseError(f"RUNTIME_UNAVAILABLE: trusted Python must be a real executable file: {candidate}")
    return candidate.resolve(strict=True)


def run_validation(package: Path, python: Path) -> dict[str, Any]:
    _assert_real_tree(package, "validation package")
    python = trusted_python(python)
    skill = (package / "SKILL.md").read_text(encoding="utf-8")
    metadata = (package / "agents" / "openai.yaml").read_text(encoding="utf-8")
    if not skill.startswith("---\n") or f"name: {SKILL_NAME}" not in skill.split("---", 2)[1]:
        raise ReleaseError("VALIDATION_FAILED: invalid SKILL.md identity")
    if "allow_implicit_invocation: false" not in metadata:
        raise ReleaseError("VALIDATION_FAILED: Skill is not explicit-only")
    scripts = sorted((package / "scripts").glob("*.py"))
    for script in scripts:
        try:
            ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            raise ReleaseError(f"VALIDATION_FAILED: Python syntax invalid: {script}: {exc}") from exc
    config_path = package / "standalone-validation.json"
    if not config_path.is_file():
        raise ReleaseError("VALIDATION_FAILED: standalone-validation.json is missing")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    test = config.get("deterministic_test")
    command = test.get("command") if isinstance(test, dict) else None
    if (
        not isinstance(command, list)
        or not command
        or command[0] != "{python}"
        or any(not isinstance(argument, str) for argument in command)
    ):
        raise ReleaseError("VALIDATION_FAILED: deterministic test command is invalid")
    expanded = [str(python), *command[1:]]
    for argument in expanded[1:]:
        if isinstance(argument, str) and (Path(argument).is_absolute() or ".." in Path(argument).parts):
            raise ReleaseError("VALIDATION_FAILED: test command escapes package")
    validation_env = os.environ.copy()
    validation_env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = _run(expanded, cwd=package, timeout=int(test.get("timeout_seconds", 180)), env=validation_env)
    count_match = re.search(r"Ran\s+(\d+)\s+tests?\b", result.stdout)
    if not count_match or int(count_match.group(1)) < 1 or not re.search(r"^OK\s*$", result.stdout, flags=re.MULTILINE):
        raise ReleaseError("VALIDATION_FAILED: deterministic test output lacks a passing unittest receipt")
    probe = _run(
        [str(python), "-c", "import json,sys,PIL; print(json.dumps({'python':'.'.join(map(str,sys.version_info[:3])),'pillow':PIL.__version__}))"],
        cwd=package,
        env=validation_env,
    )
    runtime = json.loads(probe.stdout.strip())
    normalized_output = re.sub(
        r"Ran\s+(\d+)\s+tests?\s+in\s+[0-9.]+s",
        lambda match: f"Ran {match.group(1)} tests in <time>s",
        result.stdout,
    )
    return {
        "status": "pass",
        "python_executable": str(python.resolve()),
        "python_version": runtime["python"],
        "pillow_version": runtime["pillow"],
        "deterministic_test": expanded[1:],
        "deterministic_test_count": int(count_match.group(1)),
        "deterministic_output_sha256": hashlib.sha256(normalized_output.encode("utf-8")).hexdigest(),
    }


def _windows_sid() -> str:
    result = _run(["whoami", "/user", "/fo", "csv", "/nh"], timeout=30)
    rows = list(csv.reader(result.stdout.splitlines()))
    if len(rows) != 1 or len(rows[0]) < 2 or not rows[0][1].startswith("S-"):
        raise ReleaseError("SNAPSHOT_PROTECTION_FAILED: cannot resolve current SID")
    return rows[0][1]


def assert_write_protection(package: Path) -> dict[str, Any]:
    _assert_real_tree(package, "protected snapshot")
    directories = [package, *(path for path in package.rglob("*") if path.is_dir())]
    files = [path for path in package.rglob("*") if path.is_file()]
    if not files:
        raise ReleaseError("SNAPSHOT_PROTECTION_FAILED: package contains no files")
    if os.name != "nt":
        writable = [str(path) for path in [package, *package.rglob("*")] if path.stat().st_mode & 0o222]
        if writable:
            raise ReleaseError(f"SNAPSHOT_PROTECTION_FAILED: write bits remain: {writable[:10]}")
    can_probe = os.name == "nt" or not hasattr(os, "geteuid") or os.geteuid() != 0
    if can_probe:
        for directory in directories:
            probe = directory / f".write-probe-{uuid.uuid4().hex}"
            try:
                probe.write_bytes(b"probe")
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EPERM, errno.EROFS} and getattr(exc, "winerror", None) != 5:
                    raise
            else:
                probe.unlink(missing_ok=True)
                raise ReleaseError(f"SNAPSHOT_PROTECTION_FAILED: directory accepted a new file: {directory}")
        for existing in files:
            try:
                existing.open("ab").close()
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EPERM, errno.EROFS} and getattr(exc, "winerror", None) != 5:
                    raise
            else:
                raise ReleaseError(f"SNAPSHOT_PROTECTION_FAILED: file accepted write-open: {existing}")
    method = "windows_icacls_current_sid_rx" if os.name == "nt" else "posix_no_write_bits"
    principal_sid = _windows_sid() if os.name == "nt" else None
    return {
        "protected": True,
        "platform": os.name,
        "snapshot_root": str(package.resolve()),
        "method": method,
        "principal_sid": principal_sid,
        "checked_file_count": len(files),
        "checked_directory_count": len(directories),
    }


def freeze(package: Path) -> dict[str, Any]:
    _assert_real_tree(package, "snapshot package before freeze")
    if os.name == "nt":
        sid = _windows_sid()
        _run(["icacls", str(package), "/reset", "/T", "/C", "/Q"])
        _run(["icacls", str(package), "/inheritance:r"])
        _run(["icacls", str(package), "/grant:r", f"*{sid}:(OI)(CI)RX"])
        _run(["icacls", str(package), "/verify", "/T", "/C", "/Q"])
    else:
        for path in package.rglob("*"):
            if path.is_file():
                path.chmod(0o555 if path.stat().st_mode & 0o111 else 0o444)
        for path in sorted([package, *(item for item in package.rglob("*") if item.is_dir())], key=lambda item: len(item.parts), reverse=True):
            path.chmod(0o555)
    return assert_write_protection(package)


def thaw(package: Path) -> None:
    """Maintenance/test helper: restore owner write access without following reparse points."""

    if not _lexists(package):
        return
    _assert_real_tree(package, "snapshot package before thaw")
    if os.name == "nt":
        _run(["icacls", str(package), "/inheritance:e"])
        _run(["icacls", str(package), "/reset", "/T", "/C", "/Q"])
    else:
        for directory in [package, *(path for path in package.rglob("*") if path.is_dir())]:
            directory.chmod(0o755)
        for path in package.rglob("*"):
            if path.is_file():
                path.chmod(0o755 if path.stat().st_mode & 0o111 else 0o644)


def _create_link(link: Path, target: Path) -> None:
    _real_directory(link.parent, "junction parent")
    _assert_real_tree(target, "junction target")
    if _lexists(link):
        raise ReleaseError(f"DISCOVERY_COLLISION: staged link already exists: {link}")
    if os.name == "nt":
        powershell = shutil.which("powershell.exe") or shutil.which("pwsh") or shutil.which("powershell")
        if powershell is None:
            raise ReleaseError("RUNTIME_UNAVAILABLE: PowerShell is required to create a Windows junction")
        env = os.environ.copy()
        env["FROZEN_SKILL_LINK"] = str(link)
        env["FROZEN_SKILL_TARGET"] = str(target)
        _run(
            [
                powershell,
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "New-Item -ItemType Junction -Path $env:FROZEN_SKILL_LINK -Target $env:FROZEN_SKILL_TARGET -ErrorAction Stop | Out-Null",
            ],
            env=env,
        )
    else:
        link.symlink_to(target, target_is_directory=True)
    if not (link.is_symlink() or _is_junction(link)) or link.resolve(strict=True) != target.resolve(strict=True):
        raise ReleaseError(f"DISCOVERY_ACTIVATION_FAILED: staged link target differs: {link}")


def _remove_link(link: Path) -> None:
    if link.is_symlink():
        link.unlink()
    elif _is_junction(link):
        os.rmdir(link)
    else:
        raise ReleaseError(f"UNSAFE_PATH: refusing to remove non-link discovery entry: {link}")


def discovery_conflicts(discovery_root: Path, cwd: Path | None = None) -> list[str]:
    home = Path.home()
    roots = [home / ".codex" / "skills", home / ".agents" / "skills"]
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        roots.append(Path(codex_home).expanduser() / "skills")
    cursor = (cwd or Path.cwd()).resolve(strict=False)
    for ancestor in (cursor, *cursor.parents):
        roots.append(ancestor / ".agents" / "skills")
        roots.append(ancestor / ".codex" / "skills")
    selected = os.path.normcase(str(_absolute(discovery_root)))
    conflicts: list[str] = []
    seen: set[str] = set()
    for root in roots:
        identity = os.path.normcase(str(_absolute(root)))
        if identity in seen:
            continue
        seen.add(identity)
        entry = _absolute(root) / SKILL_NAME
        if identity != selected and _lexists(entry):
            conflicts.append(str(entry))
    return conflicts


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(_absolute(left))) == os.path.normcase(str(_absolute(right)))


def _link_target(link: Path) -> Path | None:
    if not _lexists(link):
        return None
    if not (link.is_symlink() or _is_junction(link)):
        raise ReleaseError(f"DISCOVERY_COLLISION: discovery entry is not a link: {link}")
    try:
        return link.resolve(strict=True)
    except OSError as exc:
        raise ReleaseError(f"DISCOVERY_DRIFT: broken discovery link: {link}") from exc


def _receipt_error(message: str) -> ReleaseError:
    return ReleaseError(f"RECEIPT_STALE_OR_TAMPERED: {message}")


def _manifest_identity(value: Any) -> str:
    if not isinstance(value, list) or not value:
        raise _receipt_error("file manifest is missing")
    prior = ""
    for item in value:
        if not isinstance(item, dict) or set(item) != {"path", "bytes", "sha256"}:
            raise _receipt_error("file manifest entry shape differs")
        relative = item["path"]
        if not isinstance(relative, str) or not relative or PurePosixPath(relative).is_absolute() or ".." in PurePosixPath(relative).parts:
            raise _receipt_error("file manifest contains an unsafe path")
        if relative <= prior or not isinstance(item["bytes"], int) or item["bytes"] < 0:
            raise _receipt_error("file manifest ordering or size differs")
        if not isinstance(item["sha256"], str) or not SHA256_RE.fullmatch(item["sha256"]):
            raise _receipt_error("file manifest digest is invalid")
        prior = relative
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def validate_receipt_identity(
    value: Any,
    paths: dict[str, Path],
    discovery_root: Path,
    *,
    expected_python: Path | None = None,
    accepted_commit: str | None = None,
    expected_release_commit: str | None = None,
) -> dict[str, Any]:
    expected_keys = {
        "schema_version", "skill_name", "scope", "controls_aggregate_members", "repository",
        "accepted_remote_commit", "release_commit", "package_tree_oid", "file_manifest",
        "file_manifest_sha256", "snapshot_root", "snapshot_write_protection", "aggregate_boundary",
        "validation", "canonical_comparison", "remote_observations", "previous_release",
        "rollback_active", "activation",
    }
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise _receipt_error("top-level shape differs")
    if (
        value["schema_version"] != RECEIPT_SCHEMA
        or value["skill_name"] != SKILL_NAME
        or value["scope"] != "standalone_skill_release"
        or value["controls_aggregate_members"] is not False
        or value["repository"] != {
            "github_repository_id": REPOSITORY_ID,
            "full_name": REPOSITORY,
            "remote_url": REMOTE_URL,
            "branch": BRANCH,
        }
    ):
        raise _receipt_error("receipt identity differs")
    remote = _validate_commit(value["accepted_remote_commit"], "receipt accepted remote")
    commit = _validate_commit(value["release_commit"], "receipt release")
    if accepted_commit is not None and remote != _validate_commit(accepted_commit):
        raise _receipt_error("accepted remote commit differs")
    if expected_release_commit is not None and commit != _validate_commit(expected_release_commit):
        raise _receipt_error("release commit differs")
    rollback = value["rollback_active"]
    if not isinstance(rollback, bool) or (not rollback and commit != remote) or (rollback and commit == remote):
        raise _receipt_error("rollback state is inconsistent")
    if not isinstance(value["package_tree_oid"], str) or not SHA_RE.fullmatch(value["package_tree_oid"]):
        raise _receipt_error("package tree OID is invalid")
    package = paths["releases"] / commit / "package"
    if not isinstance(value["snapshot_root"], str) or not _same_path(Path(value["snapshot_root"]), package):
        raise _receipt_error("snapshot root differs")
    manifest_digest = _manifest_identity(value["file_manifest"])
    if value["file_manifest_sha256"] != manifest_digest:
        raise _receipt_error("file manifest digest differs")
    expected_file_count = len(value["file_manifest"])
    expected_directories = {"."}
    for entry in value["file_manifest"]:
        parent = PurePosixPath(entry["path"]).parent
        while parent != PurePosixPath("."):
            expected_directories.add(parent.as_posix())
            parent = parent.parent
    expected_directory_count = len(expected_directories)
    protection = value["snapshot_write_protection"]
    if not isinstance(protection, dict) or set(protection) != {
        "protected", "platform", "snapshot_root", "method", "principal_sid",
        "checked_file_count", "checked_directory_count",
    }:
        raise _receipt_error("write protection evidence shape differs")
    expected_method = "windows_icacls_current_sid_rx" if os.name == "nt" else "posix_no_write_bits"
    if (
        protection["protected"] is not True
        or protection["platform"] != os.name
        or protection["method"] != expected_method
        or not _same_path(Path(protection["snapshot_root"]), package)
        or not isinstance(protection["checked_file_count"], int)
        or protection["checked_file_count"] != expected_file_count
        or not isinstance(protection["checked_directory_count"], int)
        or protection["checked_directory_count"] != expected_directory_count
        or (os.name == "nt" and (not isinstance(protection["principal_sid"], str) or not protection["principal_sid"].startswith("S-")))
        or (os.name != "nt" and protection["principal_sid"] is not None)
    ):
        raise _receipt_error("write protection evidence differs")
    boundary = value["aggregate_boundary"]
    if not isinstance(boundary, dict) or boundary != {
        "manifest_sha256": boundary.get("manifest_sha256"),
        "standalone_package_count": EXPECTED_STANDALONE_PACKAGES,
        "aggregate_member_count": EXPECTED_AGGREGATE_MEMBERS,
        "aggregate_exclusion_count": EXPECTED_AGGREGATE_EXCLUSIONS,
        "target_excluded": True,
    } or not isinstance(boundary["manifest_sha256"], str) or not SHA256_RE.fullmatch(boundary["manifest_sha256"]):
        raise _receipt_error("aggregate boundary evidence differs")
    validation = value["validation"]
    if not isinstance(validation, dict) or set(validation) != {
        "status", "python_executable", "python_version", "pillow_version", "deterministic_test",
        "deterministic_test_count", "deterministic_output_sha256",
    }:
        raise _receipt_error("validation evidence shape differs")
    recorded_python = validation.get("python_executable")
    if not isinstance(recorded_python, str) or not Path(recorded_python).is_absolute():
        raise _receipt_error("validation executable is invalid")
    if expected_python is not None and not _same_path(Path(recorded_python), trusted_python(expected_python)):
        raise _receipt_error("validation executable differs from --python")
    if (
        validation.get("status") != "pass"
        or not isinstance(validation.get("python_version"), str)
        or not isinstance(validation.get("pillow_version"), str)
        or not isinstance(validation.get("deterministic_test"), list)
        or not all(isinstance(item, str) for item in validation["deterministic_test"])
        or not isinstance(validation.get("deterministic_test_count"), int)
        or validation["deterministic_test_count"] < 1
        or not isinstance(validation.get("deterministic_output_sha256"), str)
        or not SHA256_RE.fullmatch(validation["deterministic_output_sha256"])
    ):
        raise _receipt_error("validation evidence differs")
    comparison = value["canonical_comparison"]
    if comparison is not None and (
        not isinstance(comparison, dict)
        or set(comparison) != {"canonical_root", "file_manifest_sha256"}
        or not isinstance(comparison["canonical_root"], str)
        or not Path(comparison["canonical_root"]).is_absolute()
        or not isinstance(comparison["file_manifest_sha256"], str)
        or not SHA256_RE.fullmatch(comparison["file_manifest_sha256"])
    ):
        raise _receipt_error("canonical comparison evidence differs")
    observations = value["remote_observations"]
    if not isinstance(observations, list) or len(observations) < 3 or any(item != remote for item in observations):
        raise _receipt_error("remote observations differ")
    previous = value["previous_release"]
    if previous is not None:
        if not isinstance(previous, dict) or set(previous) != {"release_commit", "package_tree_oid", "snapshot_root"}:
            raise _receipt_error("previous release shape differs")
        previous_commit = _validate_commit(previous["release_commit"], "previous release")
        if not isinstance(previous["package_tree_oid"], str) or not SHA_RE.fullmatch(previous["package_tree_oid"]):
            raise _receipt_error("previous release tree OID is invalid")
        if not _same_path(Path(previous["snapshot_root"]), paths["releases"] / previous_commit / "package"):
            raise _receipt_error("previous release snapshot differs")
    activation = value["activation"]
    destination = discovery_root / SKILL_NAME
    if not isinstance(activation, dict) or set(activation) != {
        "transaction_id", "discovery_root", "discovery_entry", "activated_at_unix_ms", "codex_thread_id"
    }:
        raise _receipt_error("activation shape differs")
    if (
        not isinstance(activation["transaction_id"], str)
        or not TRANSACTION_ID_RE.fullmatch(activation["transaction_id"])
        or not _same_path(Path(activation["discovery_root"]), discovery_root)
        or not _same_path(Path(activation["discovery_entry"]), destination)
        or not isinstance(activation["activated_at_unix_ms"], int)
        or activation["activated_at_unix_ms"] < 0
        or not (activation["codex_thread_id"] is None or isinstance(activation["codex_thread_id"], str))
    ):
        raise _receipt_error("activation identity differs")
    return value


def load_receipt(
    path: Path,
    paths: dict[str, Path],
    discovery_root: Path,
    *,
    expected_python: Path | None = None,
    accepted_commit: str | None = None,
    expected_release_commit: str | None = None,
) -> dict[str, Any]:
    _real_file(path, "release receipt")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _receipt_error(f"receipt is unreadable: {path}") from exc
    return validate_receipt_identity(
        value,
        paths,
        discovery_root,
        expected_python=expected_python,
        accepted_commit=accepted_commit,
        expected_release_commit=expected_release_commit,
    )


def _canonical_comparison(canonical: Path | None, manifest: list[dict[str, Any]]) -> dict[str, str] | None:
    if canonical is None:
        return None
    canonical = _absolute(canonical)
    _assert_no_reparse_chain(canonical, "canonical package")
    actual = _tree_manifest(canonical)
    if actual != manifest:
        raise ReleaseError("CANONICAL_DRIFT: canonical package differs from the accepted Git snapshot")
    return {
        "canonical_root": str(canonical),
        "file_manifest_sha256": hashlib.sha256(_canonical_json(actual)).hexdigest(),
    }


TRANSACTION_PHASES = {
    "candidate", "prepared", "switching", "switched", "receipt_committed", "verified", "rolling_back"
}


def _delete_real_file(path: Path) -> None:
    if not _lexists(path):
        return
    _real_file(path, "transaction state file")
    path.unlink()
    _fsync_directory(path.parent)


def _prior_receipt_bytes(transaction: dict[str, Any]) -> bytes | None:
    encoded = transaction["prior"]["receipt_base64"]
    if encoded is None:
        return None
    try:
        return base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError) as exc:
        raise ReleaseError("TRANSACTION_TAMPERED: prior receipt encoding is invalid") from exc


def _validate_transaction(value: Any, paths: dict[str, Path], discovery_root: Path) -> dict[str, Any]:
    expected_keys = {
        "schema_version", "skill_name", "transaction_id", "phase", "state_root", "discovery_root",
        "destination", "temporary", "backup", "candidate", "prior", "post_activation_remote",
        "created_at_unix_ms",
    }
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise ReleaseError("TRANSACTION_TAMPERED: journal shape differs")
    transaction_id = value["transaction_id"]
    if (
        value["schema_version"] != TRANSACTION_SCHEMA
        or value["skill_name"] != SKILL_NAME
        or not isinstance(transaction_id, str)
        or not TRANSACTION_ID_RE.fullmatch(transaction_id)
        or value["phase"] not in TRANSACTION_PHASES
        or not isinstance(value["created_at_unix_ms"], int)
    ):
        raise ReleaseError("TRANSACTION_TAMPERED: journal identity differs")
    destination = discovery_root / SKILL_NAME
    temporary = discovery_root / f".{SKILL_NAME}.tx-{transaction_id}.new"
    backup = discovery_root / f".{SKILL_NAME}.tx-{transaction_id}.old"
    expected_paths = {
        "state_root": paths["root"], "discovery_root": discovery_root, "destination": destination,
        "temporary": temporary, "backup": backup,
    }
    for field, expected in expected_paths.items():
        recorded = value[field]
        if not isinstance(recorded, str) or not _same_path(Path(recorded), expected):
            raise ReleaseError(f"TRANSACTION_TAMPERED: {field} differs")
    candidate = value["candidate"]
    if not isinstance(candidate, dict) or set(candidate) != {"snapshot_root", "receipt"}:
        raise ReleaseError("TRANSACTION_TAMPERED: candidate shape differs")
    receipt = validate_receipt_identity(candidate["receipt"], paths, discovery_root)
    if not isinstance(candidate["snapshot_root"], str) or not _same_path(
        Path(candidate["snapshot_root"]), Path(receipt["snapshot_root"])
    ):
        raise ReleaseError("TRANSACTION_TAMPERED: candidate snapshot differs")
    post_remote = value["post_activation_remote"]
    if post_remote is not None and post_remote != receipt["accepted_remote_commit"]:
        raise ReleaseError("TRANSACTION_TAMPERED: post-activation remote differs")
    prior = value["prior"]
    if not isinstance(prior, dict) or set(prior) != {"target", "receipt_base64", "receipt_sha256"}:
        raise ReleaseError("TRANSACTION_TAMPERED: prior state shape differs")
    raw = _prior_receipt_bytes(value)
    if raw is None:
        if prior != {"target": None, "receipt_base64": None, "receipt_sha256": None}:
            raise ReleaseError("TRANSACTION_TAMPERED: empty prior state differs")
    else:
        if not isinstance(prior["receipt_sha256"], str) or hashlib.sha256(raw).hexdigest() != prior["receipt_sha256"]:
            raise ReleaseError("TRANSACTION_TAMPERED: prior receipt digest differs")
        try:
            prior_value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ReleaseError("TRANSACTION_TAMPERED: prior receipt is unreadable") from exc
        prior_receipt = validate_receipt_identity(prior_value, paths, discovery_root)
        if not isinstance(prior["target"], str) or not _same_path(
            Path(prior["target"]), Path(prior_receipt["snapshot_root"])
        ):
            raise ReleaseError("TRANSACTION_TAMPERED: prior target differs")
    return value


def _load_transaction(paths: dict[str, Path], discovery_root: Path) -> dict[str, Any]:
    _real_file(paths["journal"], "transaction journal")
    try:
        value = json.loads(paths["journal"].read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseError("TRANSACTION_TAMPERED: journal is unreadable") from exc
    return _validate_transaction(value, paths, discovery_root)


def _write_transaction(paths: dict[str, Path], transaction: dict[str, Any], phase: str) -> None:
    if phase not in TRANSACTION_PHASES:
        raise ReleaseError(f"TRANSACTION_INVALID: unsupported phase {phase}")
    transaction["phase"] = phase
    _validate_transaction(transaction, paths, Path(transaction["discovery_root"]))
    _atomic_json(paths["journal"], transaction)


def _begin_transaction(
    paths: dict[str, Path], discovery_root: Path, package: Path, receipt: dict[str, Any]
) -> dict[str, Any]:
    if _lexists(paths["journal"]):
        raise ReleaseError("TRANSACTION_RECOVERY_REQUIRED: unresolved journal exists")
    destination = discovery_root / SKILL_NAME
    prior_raw: bytes | None = None
    prior_target = _link_target(destination)
    if _lexists(paths["receipt"]):
        prior_receipt = load_receipt(paths["receipt"], paths, discovery_root)
        prior_raw = paths["receipt"].read_bytes()
        if prior_target is None or not _same_path(prior_target, Path(prior_receipt["snapshot_root"])):
            raise ReleaseError("DISCOVERY_DRIFT: active receipt and discovery target differ")
    elif prior_target is not None:
        raise ReleaseError("DISCOVERY_COLLISION: discovery entry exists without an active receipt")
    transaction_id = receipt["activation"]["transaction_id"]
    transaction = {
        "schema_version": TRANSACTION_SCHEMA,
        "skill_name": SKILL_NAME,
        "transaction_id": transaction_id,
        "phase": "candidate",
        "state_root": str(paths["root"]),
        "discovery_root": str(discovery_root),
        "destination": str(destination),
        "temporary": str(discovery_root / f".{SKILL_NAME}.tx-{transaction_id}.new"),
        "backup": str(discovery_root / f".{SKILL_NAME}.tx-{transaction_id}.old"),
        "candidate": {"snapshot_root": str(package), "receipt": receipt},
        "prior": {
            "target": str(prior_target) if prior_target is not None else None,
            "receipt_base64": base64.b64encode(prior_raw).decode("ascii") if prior_raw is not None else None,
            "receipt_sha256": hashlib.sha256(prior_raw).hexdigest() if prior_raw is not None else None,
        },
        "post_activation_remote": None,
        "created_at_unix_ms": int(time.time() * 1000),
    }
    _write_transaction(paths, transaction, "candidate")
    return transaction


def _prepare_transaction(paths: dict[str, Path], transaction: dict[str, Any]) -> None:
    temporary = Path(transaction["temporary"])
    backup = Path(transaction["backup"])
    if _lexists(temporary) or _lexists(backup):
        raise ReleaseError("DISCOVERY_COLLISION: transaction staging path already exists")
    _create_link(temporary, Path(transaction["candidate"]["snapshot_root"]))
    _write_transaction(paths, transaction, "prepared")
    _fault("after_prepared")


def _activate_transaction(paths: dict[str, Path], transaction: dict[str, Any]) -> None:
    destination = Path(transaction["destination"])
    temporary = Path(transaction["temporary"])
    backup = Path(transaction["backup"])
    candidate = Path(transaction["candidate"]["snapshot_root"])
    prior_value = transaction["prior"]["target"]
    prior = Path(prior_value) if prior_value is not None else None
    current = _link_target(destination)
    if (prior is None and current is not None) or (prior is not None and (current is None or not _same_path(current, prior))):
        raise ReleaseError("DISCOVERY_DRIFT: discovery changed before activation")
    if _link_target(temporary) is None or not _same_path(_link_target(temporary), candidate):
        raise ReleaseError("DISCOVERY_ACTIVATION_FAILED: staged link differs")
    _write_transaction(paths, transaction, "switching")
    if current is not None:
        os.replace(destination, backup)
    _fault("after_backup")
    os.replace(temporary, destination)
    active = _link_target(destination)
    if active is None or not _same_path(active, candidate):
        raise ReleaseError("DISCOVERY_ACTIVATION_FAILED: candidate link differs")
    _fault("after_new_active")
    _write_transaction(paths, transaction, "switched")


def _rollback_transaction(paths: dict[str, Path], transaction: dict[str, Any]) -> None:
    _write_transaction(paths, transaction, "rolling_back")
    destination = Path(transaction["destination"])
    temporary = Path(transaction["temporary"])
    backup = Path(transaction["backup"])
    candidate = Path(transaction["candidate"]["snapshot_root"])
    prior_value = transaction["prior"]["target"]
    prior = Path(prior_value) if prior_value is not None else None
    active = _link_target(destination)
    if active is not None:
        if _same_path(active, candidate):
            _remove_link(destination)
        elif prior is None or not _same_path(active, prior):
            raise ReleaseError("ROLLBACK_UNSAFE: discovery target is neither candidate nor prior")
    staged = _link_target(temporary)
    if staged is not None:
        if not _same_path(staged, candidate):
            raise ReleaseError("ROLLBACK_UNSAFE: staged link target differs")
        _remove_link(temporary)
    saved = _link_target(backup)
    if saved is not None:
        if prior is None or not _same_path(saved, prior):
            raise ReleaseError("ROLLBACK_UNSAFE: backup link target differs")
        active = _link_target(destination)
        if active is None:
            os.replace(backup, destination)
        elif _same_path(active, prior):
            _remove_link(backup)
        else:
            raise ReleaseError("ROLLBACK_UNSAFE: cannot restore prior discovery target")
    stable = _link_target(destination)
    if (prior is None and stable is not None) or (prior is not None and (stable is None or not _same_path(stable, prior))):
        raise ReleaseError("ROLLBACK_FAILED: prior discovery state was not restored")
    _atomic_restore(paths["receipt"], _prior_receipt_bytes(transaction))
    _delete_real_file(paths["journal"])


def _finalize_transaction(paths: dict[str, Path], transaction: dict[str, Any]) -> None:
    candidate = Path(transaction["candidate"]["snapshot_root"])
    destination = Path(transaction["destination"])
    active = _link_target(destination)
    if active is None or not _same_path(active, candidate):
        raise ReleaseError("TRANSACTION_FINALIZE_FAILED: candidate discovery target is not active")
    for field in ("temporary", "backup"):
        entry = Path(transaction[field])
        target = _link_target(entry)
        if target is not None:
            prior_value = transaction["prior"]["target"]
            if field == "backup" and prior_value is None:
                raise ReleaseError("TRANSACTION_FINALIZE_FAILED: unexpected backup without prior target")
            expected = candidate if field == "temporary" else Path(prior_value)
            if not _same_path(target, expected):
                raise ReleaseError(f"TRANSACTION_FINALIZE_FAILED: {field} target differs")
            _remove_link(entry)
    _delete_real_file(paths["journal"])


def _recover_transaction(paths: dict[str, Path], discovery_root: Path) -> str | None:
    if not _lexists(paths["journal"]):
        return None
    transaction = _load_transaction(paths, discovery_root)
    if transaction["phase"] == "verified":
        try:
            active_receipt = load_receipt(paths["receipt"], paths, discovery_root)
            committed = active_receipt["activation"]["transaction_id"] == transaction["transaction_id"]
            active = _link_target(Path(transaction["destination"]))
            candidate = Path(transaction["candidate"]["snapshot_root"])
            committed = committed and active is not None and _same_path(active, candidate)
        except (OSError, ReleaseError):
            committed = False
        if committed:
            _finalize_transaction(paths, transaction)
            return "finalized_verified_transaction"
    _rollback_transaction(paths, transaction)
    return "rolled_back_incomplete_transaction"


def _check_locked(
    repo_root: Path,
    paths: dict[str, Path],
    discovery_root: Path,
    python: Path,
    accepted_commit: str,
    canonical: Path | None,
    *,
    expected_remote: str | None = None,
    allow_journal: bool = False,
) -> dict[str, Any]:
    if _lexists(paths["journal"]) and not allow_journal:
        raise ReleaseError("TRANSACTION_RECOVERY_REQUIRED: run sync to recover the durable journal")
    receipt = load_receipt(
        paths["receipt"], paths, discovery_root, expected_python=python, accepted_commit=accepted_commit
    )
    head = expected_remote or remote_head(repo_root, accepted_commit)
    if head != accepted_commit:
        raise ReleaseError(f"ACCEPTED_COMMIT_MISMATCH: accepted={accepted_commit}; remote={head}")
    commit = receipt["release_commit"]
    package = paths["releases"] / commit / "package"
    git_evidence = verify_snapshot(repo_root, commit, package)
    if receipt["package_tree_oid"] != git_evidence["package_tree_oid"]:
        raise _receipt_error("package tree OID differs")
    if receipt["file_manifest"] != git_evidence["file_manifest"]:
        raise ReleaseError("SOURCE_TREE_DRIFT: file manifest differs")
    protection = assert_write_protection(package)
    if receipt["snapshot_write_protection"] != protection:
        raise _receipt_error("write protection evidence differs")
    boundary = aggregate_boundary(repo_root, commit)
    if receipt["aggregate_boundary"] != boundary:
        raise _receipt_error("aggregate boundary differs")
    destination = discovery_root / SKILL_NAME
    active = _link_target(destination)
    if active is None or not _same_path(active, package):
        raise ReleaseError("DISCOVERY_DRIFT: exact discovery link is not active")
    conflicts = discovery_conflicts(discovery_root)
    if conflicts:
        raise ReleaseError(f"DISCOVERY_AMBIGUOUS: {conflicts}")
    comparison = _canonical_comparison(canonical, git_evidence["file_manifest"])
    if canonical is not None and comparison != receipt["canonical_comparison"]:
        raise _receipt_error("canonical comparison evidence differs")
    validation = run_validation(package, python)
    if validation != receipt["validation"]:
        raise ReleaseError("RUNTIME_OR_VALIDATION_DRIFT: validation evidence differs")
    return {
        "status": "STANDALONE_READY_LATEST",
        "integrity_ready": True,
        "ready_latest": True,
        "rollback_active": False,
        "skill_name": SKILL_NAME,
        "release_commit": commit,
        "package_tree_oid": git_evidence["package_tree_oid"],
        "discovery_entry": str(destination),
        "snapshot_root": str(package),
        "aggregate_boundary": boundary,
        "canonical_compared": comparison is not None,
    }


def check(
    repo_root: Path,
    state_root: Path,
    discovery_root: Path,
    python: Path,
    accepted_commit: str,
    canonical: Path | None = None,
) -> dict[str, Any]:
    repo_root, state_root, discovery_root = validate_roots(repo_root, state_root, discovery_root)
    python = trusted_python(python)
    accepted_commit = _validate_commit(accepted_commit)
    paths = prepare_state(state_root)
    _real_directory(discovery_root, "discovery root")
    if not discovery_root.is_dir():
        raise ReleaseError(f"DISCOVERY_MISSING: {discovery_root}")
    with _release_lock(paths):
        return _check_locked(repo_root, paths, discovery_root, python, accepted_commit, canonical)


def sync(
    repo_root: Path,
    state_root: Path,
    discovery_root: Path,
    python: Path,
    accepted_commit: str,
    canonical: Path | None = None,
) -> dict[str, Any]:
    repo_root, state_root, discovery_root = validate_roots(repo_root, state_root, discovery_root)
    python = trusted_python(python)
    accepted_commit = _validate_commit(accepted_commit)
    paths = prepare_state(state_root)
    _real_directory(discovery_root, "discovery root")
    discovery_root.mkdir(parents=True, exist_ok=True)
    with _release_lock(paths):
        _recover_transaction(paths, discovery_root)
        conflicts = discovery_conflicts(discovery_root)
        if conflicts:
            raise ReleaseError(f"DISCOVERY_AMBIGUOUS: {conflicts}")
        first = remote_head(repo_root, accepted_commit)
        fetch_exact(repo_root, accepted_commit)
        package = materialize_snapshot(repo_root, accepted_commit, paths["releases"])
        git_evidence = verify_snapshot(repo_root, accepted_commit, package)
        boundary = aggregate_boundary(repo_root, accepted_commit)
        validation = run_validation(package, python)
        second = remote_head(repo_root, accepted_commit)
        comparison = _canonical_comparison(canonical, git_evidence["file_manifest"])
        protection = freeze(package)
        verify_snapshot(repo_root, accepted_commit, package)
        third = remote_head(repo_root, accepted_commit)
        previous_release = None
        if _lexists(paths["receipt"]):
            previous = load_receipt(paths["receipt"], paths, discovery_root)
            previous_release = {
                "release_commit": previous["release_commit"],
                "package_tree_oid": previous["package_tree_oid"],
                "snapshot_root": previous["snapshot_root"],
            }
        transaction_id = uuid.uuid4().hex
        destination = discovery_root / SKILL_NAME
        receipt = {
            "schema_version": RECEIPT_SCHEMA,
            "skill_name": SKILL_NAME,
            "scope": "standalone_skill_release",
            "controls_aggregate_members": False,
            "repository": {
                "github_repository_id": REPOSITORY_ID,
                "full_name": REPOSITORY,
                "remote_url": REMOTE_URL,
                "branch": BRANCH,
            },
            "accepted_remote_commit": accepted_commit,
            "release_commit": accepted_commit,
            "package_tree_oid": git_evidence["package_tree_oid"],
            "file_manifest": git_evidence["file_manifest"],
            "file_manifest_sha256": hashlib.sha256(_canonical_json(git_evidence["file_manifest"])).hexdigest(),
            "snapshot_root": str(package),
            "snapshot_write_protection": protection,
            "aggregate_boundary": boundary,
            "validation": validation,
            "canonical_comparison": comparison,
            "remote_observations": [first, second, third],
            "previous_release": previous_release,
            "rollback_active": False,
            "activation": {
                "transaction_id": transaction_id,
                "discovery_root": str(discovery_root),
                "discovery_entry": str(destination),
                "activated_at_unix_ms": int(time.time() * 1000),
                "codex_thread_id": os.environ.get("CODEX_THREAD_ID"),
            },
        }
        validate_receipt_identity(receipt, paths, discovery_root, expected_python=python, accepted_commit=accepted_commit)
        transaction = _begin_transaction(paths, discovery_root, package, receipt)
        try:
            _prepare_transaction(paths, transaction)
            _activate_transaction(paths, transaction)
            _atomic_json(paths["receipt"], receipt)
            _fault("after_receipt_commit")
            _write_transaction(paths, transaction, "receipt_committed")
            result = _check_locked(
                repo_root, paths, discovery_root, python, accepted_commit, canonical,
                expected_remote=accepted_commit, allow_journal=True,
            )
            fourth = remote_head(repo_root, accepted_commit)
            receipt["remote_observations"].append(fourth)
            _atomic_json(paths["receipt"], receipt)
            transaction["candidate"]["receipt"] = receipt
            transaction["post_activation_remote"] = fourth
            _write_transaction(paths, transaction, "verified")
            _fault("after_verified")
            _finalize_transaction(paths, transaction)
            return result
        except Exception:
            if _lexists(paths["journal"]):
                current = _load_transaction(paths, discovery_root)
                _rollback_transaction(paths, current)
            raise


def default_state_root() -> Path:
    return Path.home() / ".codex" / ".standalone-skill-releases" / SKILL_NAME


def default_discovery_root() -> Path:
    return Path.home() / ".codex" / "skills"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("command", choices=("sync", "check"))
    result.add_argument("--repo-root", type=Path, default=Path.cwd())
    result.add_argument("--state-root", type=Path, default=default_state_root())
    result.add_argument("--discovery-root", type=Path, default=default_discovery_root())
    result.add_argument("--python", type=Path, default=Path(sys.executable))
    result.add_argument("--commit", required=True, help="Explicitly accepted 40-hex main commit")
    result.add_argument("--canonical", type=Path, help="Optional real package tree to compare with the accepted snapshot")
    return result


def main(argv: Iterable[str] | None = None) -> int:
    arguments = parser().parse_args(list(argv) if argv is not None else None)
    try:
        repo_root = arguments.repo_root.resolve(strict=True)
        if not (repo_root / ".git").exists():
            raise ReleaseError(f"REPOSITORY_INVALID: {repo_root}")
        if arguments.command == "sync":
            result = sync(
                repo_root, arguments.state_root, arguments.discovery_root,
                arguments.python, arguments.commit, arguments.canonical,
            )
        else:
            result = check(
                repo_root, arguments.state_root, arguments.discovery_root,
                arguments.python, arguments.commit, arguments.canonical,
            )
    except (OSError, TypeError, ValueError, json.JSONDecodeError, ReleaseError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "STANDALONE_NOT_READY", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
